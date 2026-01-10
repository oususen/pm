"""
工程実時間記録API
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.db.models import Sum
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.conf import settings
from decimal import Decimal, InvalidOperation
from datetime import datetime, time

from .models_process_realtime import ProcessRealtimeRecord
from .models_line_backlog import LineBacklog
from .serializers_process_realtime import (
    ProcessRealtimeRecordSerializer,
    ProcessRealtimeCreateSerializer,
    build_scrap_multiplier_map,
    build_scrap_multiplier_details,
    apply_scrap_return_to_stock,
)
from masters.models import Product, Process, Supplier, BOM
from ..quality.models_scrap import ScrapRecordDetail, ScrapRecord


class ProcessRealtimeRecordViewSet(viewsets.ModelViewSet):
    """工程実時間記録ViewSet"""

    queryset = ProcessRealtimeRecord.objects.all()
    serializer_class = ProcessRealtimeRecordSerializer

    def get_queryset(self):
        queryset = ProcessRealtimeRecord.objects.select_related('process', 'product', 'scrap_detail')

        process_id = self.request.query_params.get('process_id')
        if process_id:
            queryset = queryset.filter(process_id=process_id)

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            d = parse_date(start_date)
            if d:
                start_dt = datetime.combine(d, time.min)
                if settings.USE_TZ:
                    start_dt = timezone.make_aware(start_dt)
                queryset = queryset.filter(timestamp__gte=start_dt)
            else:
                queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            d = parse_date(end_date)
            if d:
                end_dt = datetime.combine(d, time.max)
                if settings.USE_TZ:
                    end_dt = timezone.make_aware(end_dt)
                queryset = queryset.filter(timestamp__lte=end_dt)
            else:
                queryset = queryset.filter(timestamp__lte=end_date)

        record_type = self.request.query_params.get('record_type')
        if record_type:
            queryset = queryset.filter(record_type=record_type)

        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        product_code = self.request.query_params.get('product_code')
        if product_code:
            queryset = queryset.filter(product_code=product_code)

        return queryset.order_by('-timestamp')

    def create(self, request, *args, **kwargs):
        serializer = ProcessRealtimeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        return Response(ProcessRealtimeRecordSerializer(record).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='status')
    def status(self, request):
        line_id = request.query_params.get('line_id')
        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        processes = Process.objects.filter(line_id=line_id, is_active=True).order_by('process_code')
        process_ids = list(processes.values_list('id', flat=True))
        if not process_ids:
            return Response([])

        today = timezone.now().date()
        start_dt = datetime.combine(today, time.min)
        end_dt = datetime.combine(today, time.max)
        if settings.USE_TZ:
            start_dt = timezone.make_aware(start_dt)
            end_dt = timezone.make_aware(end_dt)

        copro_child_ids = set()
        copro_boms = BOM.objects.filter(is_coproduct=True, is_active=True).prefetch_related('items')
        for bom in copro_boms:
            for item in bom.items.all():
                if item.child_product_id:
                    copro_child_ids.add(item.child_product_id)

        plan_qs = LineBacklog.objects.filter(
            line_id=line_id,
            plan_date=today,
            process_id__in=process_ids,
        )
        if copro_child_ids:
            plan_qs = plan_qs.exclude(product_id__in=copro_child_ids)
        plan_qs = plan_qs.values('process_id').annotate(total=Sum('plan_qty'))
        plan_map = {row['process_id']: row['total'] or 0 for row in plan_qs}

        output_qs = ProcessRealtimeRecord.objects.filter(
            process_id__in=process_ids,
            record_type='PRODUCTION',
            timestamp__gte=start_dt,
            timestamp__lte=end_dt,
        ).values('process_id').annotate(total=Sum('qty'))
        output_map = {row['process_id']: row['total'] or 0 for row in output_qs}

        state_map = {}
        latest_state_qs = ProcessRealtimeRecord.objects.filter(
            process_id__in=process_ids,
            equipment_state__isnull=False,
        ).order_by('-timestamp')
        for rec in latest_state_qs:
            if rec.process_id in state_map:
                continue
            state_map[rec.process_id] = {
                'state': rec.equipment_state,
                'timestamp': rec.timestamp,
            }

        product_map = {}
        latest_product_qs = ProcessRealtimeRecord.objects.filter(
            process_id__in=process_ids,
            record_type='PRODUCTION',
        ).order_by('-timestamp')
        for rec in latest_product_qs:
            if rec.process_id in product_map:
                continue
            code = (rec.product_code or '').strip() or None
            name = (rec.product_name or '').strip() or None
            if not code and not name:
                continue
            product_map[rec.process_id] = {
                'code': code,
                'name': name,
            }

        state_labels = dict(ProcessRealtimeRecord.EQUIPMENT_STATE_CHOICES)
        result = []
        for process in processes:
            today_plan = plan_map.get(process.id, 0) or 0
            today_output = output_map.get(process.id, 0) or 0
            if today_plan:
                achievement_rate = round((float(today_output) / float(today_plan)) * 100, 1)
            else:
                achievement_rate = 0
            progress = achievement_rate if today_plan else 0
            state_info = state_map.get(process.id, {})
            state = state_info.get('state') or 'STOPPED'
            product_info = product_map.get(process.id, {})

            result.append({
                'id': process.id,
                'process': process.id,
                'process_code': process.process_code,
                'process_name': process.process_name,
                'current_state': state,
                'state_display': state_labels.get(state, state),
                'state_started_at': state_info.get('timestamp'),
                'today_output': float(today_output),
                'today_plan': float(today_plan),
                'achievement_rate': achievement_rate,
                'current_product_code': product_info.get('code'),
                'current_product_name': product_info.get('name'),
                'last_update': state_info.get('timestamp'),
                'progress': progress,
            })

        return Response(result)

    @action(detail=True, methods=['get'], url_path='scrap-breakdown')
    def scrap_breakdown(self, request, pk=None):
        """仕損のBOM展開明細を返す"""
        record = self.get_object()
        if record.record_type != 'SCRAP' or not record.product_id:
            return Response([])

        details_qs = ScrapRecordDetail.objects.filter(scrap_record__process_record=record)
        # 既存明細がなければ（古いデータ用）作成してから返す
        if not details_qs.exists() and getattr(record, 'scrap_detail', None):
            qty = record.qty or 0
            gen_details = build_scrap_multiplier_details(record.product_id, qty)
            if gen_details:
                products = {
                    p.id: p for p in Product.objects.filter(id__in=[d['product_id'] for d in gen_details if d.get('product_id')])
                }
                objs = []
                for d in gen_details:
                    pid = d.get('product_id')
                    prod = products.get(pid) if pid else None
                    objs.append(ScrapRecordDetail(
                        scrap_record=record.scrap_detail,
                        product=prod,
                        product_code=prod.product_code if prod else None,
                        product_name=prod.product_name if prod else None,
                        process_id=d.get('process_id'),
                        line_id=d.get('line_id'),
                        supplier_id=d.get('supplier_id'),
                        sourcing_type=d.get('sourcing_type'),
                        deduct_qty=d.get('qty') or 0,
                    ))
                ScrapRecordDetail.objects.bulk_create(objs)
                details_qs = ScrapRecordDetail.objects.filter(scrap_record__process_record=record)

        # BOM展開結果に含まれる品目のみ表示（購入品はここで止める）
        qty = record.qty or 0
        allowed_ids = {
            d.get('product_id')
            for d in build_scrap_multiplier_details(record.product_id, qty)
            if d.get('product_id')
        }
        if allowed_ids:
            details_qs = details_qs.filter(product_id__in=allowed_ids)

        # 同じ(product_id, process_id, supplier_id)の組み合わせで集約（既存データの重複対策）
        from collections import defaultdict
        aggregated = defaultdict(lambda: {
            'deduct_qty': Decimal('0'),
            'detail_ids': [],
            'is_replenished_list': [],
        })

        products = {p.id: p for p in Product.objects.filter(id__in=details_qs.values_list('product_id', flat=True))}
        processes = {p.id: p for p in Process.objects.filter(id__in=details_qs.values_list('process_id', flat=True))}
        suppliers = {s.id: s for s in Supplier.objects.filter(id__in=details_qs.values_list('supplier_id', flat=True))}

        for d in details_qs:
            key = (d.product_id, d.process_id, d.supplier_id)
            p = products.get(d.product_id)
            proc = processes.get(d.process_id) if d.process_id else None
            supplier = suppliers.get(d.supplier_id) if d.supplier_id else None

            if key not in aggregated:
                aggregated[key] = {
                    'product_id': d.product_id,
                    'product_code': d.product_code or (p.product_code if p else None),
                    'product_name': d.product_name or (p.product_name if p else None),
                    'process_id': d.process_id,
                    'process_code': proc.process_code if proc else None,
                    'process_name': proc.process_name if proc else None,
                    'supplier_id': d.supplier_id,
                    'supplier_code': supplier.supplier_code if supplier else None,
                    'supplier_name': supplier.supplier_name if supplier else None,
                    'sourcing_type': d.sourcing_type,
                    'deduct_qty': Decimal('0'),
                    'detail_ids': [],
                    'is_replenished_list': [],
                    'replenished_at': d.replenished_at,
                    'replenished_by': d.replenished_by,
                }

            aggregated[key]['deduct_qty'] += (d.deduct_qty or Decimal('0'))
            aggregated[key]['detail_ids'].append(d.id)
            aggregated[key]['is_replenished_list'].append(d.is_replenished)

        details = []
        for key, item in aggregated.items():
            # 全明細が補充完了している場合のみ完了とする
            all_replenished = all(item['is_replenished_list']) if item['is_replenished_list'] else False
            details.append({
                'detail_id': item['detail_ids'][0],  # 代表IDとして最初のdetail_idを使用
                'product_id': item['product_id'],
                'product_code': item['product_code'],
                'product_name': item['product_name'],
                'deduct_qty': float(item['deduct_qty']),
                'process_id': item['process_id'],
                'process_code': item['process_code'],
                'process_name': item['process_name'],
                'supplier_id': item['supplier_id'],
                'supplier_code': item['supplier_code'],
                'supplier_name': item['supplier_name'],
                'sourcing_type': item['sourcing_type'],
                'is_replenished': all_replenished,
                'replenished_at': item['replenished_at'],
                'replenished_by': item['replenished_by'],
            })

        details.sort(key=lambda x: (x['product_code'] or '', x['product_id'] or 0))
        return Response(details)

    @action(detail=True, methods=['post'], url_path='mark-replenished')
    def mark_replenished(self, request, pk=None):
        """仕損補充完了フラグを立てる（全明細まとめて）"""
        record = self.get_object()
        if record.record_type != 'SCRAP':
            return Response({'detail': 'SCRAP以外は対象外です。'}, status=status.HTTP_400_BAD_REQUEST)
        sd = getattr(record, 'scrap_detail', None)
        if not sd:
            return Response({'detail': '対応する仕損記録がありません。'}, status=status.HTTP_400_BAD_REQUEST)
        from django.utils import timezone
        sd.is_replenished = True
        sd.replenished_at = timezone.now()
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            sd.replenished_by = getattr(user, 'username', None) or sd.replenished_by
        sd.save()
        ScrapRecordDetail.objects.filter(scrap_record=sd).update(
            is_replenished=True,
            replenished_at=sd.replenished_at,
            replenished_by=sd.replenished_by,
        )
        # ProcessRealtimeRecord の serializer で拾えるよう event_data にも反映（任意）
        record.event_data = record.event_data or {}
        record.event_data['is_replenished'] = True
        record.save(update_fields=['event_data'])
        return Response({
            'scrap_record_id': sd.id,
            'is_replenished': sd.is_replenished,
            'replenished_at': sd.replenished_at,
            'replenished_by': sd.replenished_by,
        })

    @action(detail=True, methods=['post'], url_path='mark-detail-replenished')
    def mark_detail_replenished(self, request, pk=None):
        """仕損明細単位で補充完了を立てる"""
        record = self.get_object()
        if record.record_type != 'SCRAP':
            return Response({'detail': 'SCRAP以外は対象外です。'}, status=status.HTTP_400_BAD_REQUEST)
        detail_id = request.data.get('detail_id')
        if not detail_id:
            return Response({'detail': 'detail_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            detail = ScrapRecordDetail.objects.get(id=detail_id, scrap_record__process_record=record)
        except ScrapRecordDetail.DoesNotExist:
            return Response({'detail': '明細が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        from django.utils import timezone
        detail.is_replenished = True
        detail.replenished_at = timezone.now()
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            detail.replenished_by = getattr(user, 'username', None) or detail.replenished_by
        detail.save()

        # すべて完了なら親も完了
        sd = getattr(record, 'scrap_detail', None)
        if sd:
            all_done = not ScrapRecordDetail.objects.filter(scrap_record=sd, is_replenished=False).exists()
            if all_done:
                sd.is_replenished = True
                sd.replenished_at = detail.replenished_at
                sd.replenished_by = detail.replenished_by
                sd.save()
                record.event_data = record.event_data or {}
                record.event_data['is_replenished'] = True
                record.save(update_fields=['event_data'])

        return Response({
            'detail_id': detail.id,
            'is_replenished': detail.is_replenished,
            'replenished_at': detail.replenished_at,
            'replenished_by': detail.replenished_by,
        })

    @action(detail=True, methods=['post'], url_path='scrap-disposition')
    def scrap_disposition(self, request, pk=None):
        """仕損の判定（戻し/仕損確定）"""
        record = self.get_object()
        if record.record_type != 'SCRAP':
            return Response({'detail': 'SCRAP以外は対象外です。'}, status=status.HTTP_400_BAD_REQUEST)
        sd = getattr(record, 'scrap_detail', None)
        if not sd:
            return Response({'detail': '対応する仕損記録がありません。'}, status=status.HTTP_400_BAD_REQUEST)

        action = (request.data.get('action') or '').strip().upper()
        if action not in ('RETURN', 'CONFIRM_SCRAP'):
            return Response({'detail': 'action is required (RETURN or CONFIRM_SCRAP)'}, status=status.HTTP_400_BAD_REQUEST)

        user = getattr(request, 'user', None)
        decided_by = None
        if user and getattr(user, 'is_authenticated', False):
            decided_by = getattr(user, 'username', None)

        with transaction.atomic():
            if action == 'RETURN':
                try:
                    qty = Decimal(str(request.data.get('qty')))
                except (InvalidOperation, TypeError):
                    return Response({'detail': 'qty must be a valid number.'}, status=status.HTTP_400_BAD_REQUEST)
                if qty <= 0:
                    return Response({'detail': 'qty must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)
                product_id = record.product_id
                if not product_id and record.product_code:
                    prod = Product.objects.filter(product_code=record.product_code).first()
                    product_id = prod.id if prod else None
                product_obj = sd.product
                if not product_obj and product_id:
                    product_obj = Product.objects.filter(id=product_id).first()
                if not product_id:
                    return Response({'detail': '製品が未設定のため在庫戻しができません。'}, status=status.HTTP_400_BAD_REQUEST)

                current_return = sd.return_qty or Decimal('0')
                scrap_qty = sd.qty or Decimal('0')
                new_return = current_return + qty
                if new_return > scrap_qty:
                    return Response({'detail': '戻し数量が仕損数量を超えています。'}, status=status.HTTP_400_BAD_REQUEST)

                multipliers = build_scrap_multiplier_map(product_id, qty)
                if multipliers:
                    apply_scrap_return_to_stock(multipliers)

                # 戻しは新規レコードとして登録（数量はマイナス）
                return_date = timezone.now().date()
                return_record = ScrapRecord.objects.create(
                    process=sd.process,
                    line=sd.line,
                    product=product_obj,
                    product_code=sd.product_code,
                    product_name=sd.product_name,
                    event_type='RETURN',
                    qty=-qty,
                    plan_date=return_date,
                    reason=sd.reason or '',
                    reason_detail=sd.reason_detail or '',
                    batch_no=sd.batch_no or '',
                    operator_name=sd.operator_name or '',
                    remarks=sd.remarks or '',
                    return_for=sd,
                    disposition_status='APPROVED',
                    decided_at=timezone.now(),
                    decided_by=decided_by,
                )

                details = build_scrap_multiplier_details(product_id, -qty)
                if details:
                    products = {
                        p.id: p for p in Product.objects.filter(
                            id__in=[d['product_id'] for d in details if d.get('product_id')]
                        )
                    }
                    objs = []
                    for d in details:
                        pid = d.get('product_id')
                        prod = products.get(pid) if pid else None
                        objs.append(ScrapRecordDetail(
                            scrap_record=return_record,
                            product=prod,
                            product_code=prod.product_code if prod else None,
                            product_name=prod.product_name if prod else None,
                            process_id=d.get('process_id'),
                            line_id=d.get('line_id'),
                            supplier_id=d.get('supplier_id'),
                            sourcing_type=d.get('sourcing_type'),
                            deduct_qty=d.get('qty') or Decimal('0'),
                        ))
                    ScrapRecordDetail.objects.bulk_create(objs)

                sd.return_qty = new_return
                if new_return == scrap_qty:
                    sd.disposition_status = 'APPROVED'
                else:
                    sd.disposition_status = 'PARTIAL'
                sd.decided_at = timezone.now()
                if decided_by:
                    sd.decided_by = decided_by
                sd.save()

                qty_int = int(qty)
                if qty_int and sd.line_id and sd.process_id and sd.product_id:
                    from django.db.models import F
                    LineBacklog.objects.get_or_create(
                        line_id=sd.line_id,
                        process_id=sd.process_id,
                        product_id=sd.product_id,
                        plan_date=return_date,
                        defaults={
                            'order_qty': 0,
                            'plan_qty': 0,
                            'actual_qty': 0,
                            'stock_qty': 0,
                            'planned_stock_qty': 0,
                            'adjust_qty': 0,
                            'scrap_qty': 0,
                            'actual_shipment_qty': 0,
                        }
                    )
                    LineBacklog.objects.filter(
                        line_id=sd.line_id,
                        process_id=sd.process_id,
                        product_id=sd.product_id,
                        plan_date=return_date,
                    ).update(scrap_qty=F('scrap_qty') - qty_int)
                    LineBacklog.objects.filter(
                        line_id=sd.line_id,
                        process_id=sd.process_id,
                        product_id=sd.product_id,
                        plan_date__gte=return_date,
                    ).update(
                        stock_qty=F('stock_qty') + qty_int,
                        planned_stock_qty=F('planned_stock_qty') + qty_int,
                    )
            elif action == 'CONFIRM_SCRAP':
                if (sd.return_qty or Decimal('0')) > 0:
                    sd.disposition_status = 'PARTIAL'
                else:
                    sd.disposition_status = 'REJECTED'
                sd.decided_at = timezone.now()
                if decided_by:
                    sd.decided_by = decided_by
                sd.save()

        return Response({
            'scrap_record_id': sd.id,
            'disposition_status': sd.disposition_status,
            'return_qty': sd.return_qty,
            'decided_at': sd.decided_at,
            'decided_by': sd.decided_by,
        })
