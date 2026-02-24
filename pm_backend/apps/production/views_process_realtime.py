"""
工程実時間記録API
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.db.models import Sum
from django.utils.dateparse import parse_date, parse_datetime
from django.utils import timezone
from django.conf import settings
from decimal import Decimal, InvalidOperation
from datetime import datetime, time, timedelta

from .models_process_realtime import ProcessRealtimeRecord
from .models_process_work_session import ProcessWorkSession
from .models_line_backlog import LineBacklog
from .serializers_process_realtime import (
    ProcessRealtimeRecordSerializer,
    ProcessRealtimeCreateSerializer,
    ProcessWorkSessionSerializer,
    build_scrap_multiplier_details,
    _resolve_product_process_line,
    resolve_workday_date_for_process,
)
from .services.gantt_planning import LineWorkCalendar
from masters.models import Product, Process, Supplier, BOM
from quality.models_scrap import ScrapRecordDetail, ScrapRecord
from orders.utils.calendar_utils import get_business_today, DAY_BOUNDARY_HOUR


def _is_countable_session_for_actual(session_type, end_action):
    return str(session_type or '').upper() == 'WORK' and str(end_action or '').upper() in ('END', 'PAUSE')


def _adjust_backlog_actual_for_session(session_obj, delta_qty):
    if not session_obj or not delta_qty:
        return
    if not session_obj.product_id or not session_obj.process_id or not session_obj.plan_date:
        return

    line = getattr(session_obj.process, 'line', None)
    if not line:
        return

    backlog, _created = LineBacklog.objects.get_or_create(
        line=line,
        process_id=session_obj.process_id,
        product_id=session_obj.product_id,
        plan_date=session_obj.plan_date,
        sequence_no=0,
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
    backlog.actual_qty = (backlog.actual_qty or 0) + int(delta_qty)
    backlog.save(update_fields=['actual_qty'])


def _to_local_naive(dt):
    if not dt:
        return None
    if timezone.is_aware(dt):
        return timezone.localtime(dt).replace(tzinfo=None)
    return dt


def _normalize_input_datetime(dt):
    if not dt:
        return None
    if settings.USE_TZ:
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
    return timezone.localtime(dt).replace(tzinfo=None) if timezone.is_aware(dt) else dt


def _calculate_effective_work_seconds(calendar, started_at, ended_at):
    """
    ラインカレンダ（勤務パターン＋休憩）で区切った実作業秒数を返す。
    """
    start_dt = _to_local_naive(started_at)
    end_dt = _to_local_naive(ended_at)
    if not start_dt or not end_dt or end_dt <= start_dt:
        return 0

    # カレンダ未解決時は生時間差をフォールバックとして返す。
    if not calendar:
        return max(int((end_dt - start_dt).total_seconds()), 0)

    total_seconds = 0
    check_date = start_dt.date() - timedelta(days=1)
    last_date = end_dt.date() + timedelta(days=1)

    while check_date <= last_date:
        segments = calendar.get_segments(check_date) or []
        for seg_start, seg_end in segments:
            overlap_start = max(start_dt, seg_start)
            overlap_end = min(end_dt, seg_end)
            if overlap_end > overlap_start:
                total_seconds += int((overlap_end - overlap_start).total_seconds())
        check_date += timedelta(days=1)

    return max(total_seconds, 0)


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

    @action(detail=False, methods=['get'], url_path='sessions')
    def sessions(self, request):
        """
        開始〜終了セッションの一覧を返す。
        稼働時間分析と不整合検知の確認用。
        """
        queryset = ProcessWorkSession.objects.select_related(
            'process',
            'product',
            'start_record',
            'end_record',
        )

        process_id = request.query_params.get('process_id')
        if process_id:
            queryset = queryset.filter(process_id=process_id)

        line_id = request.query_params.get('line_id')
        if line_id:
            queryset = queryset.filter(process__line_id=line_id)

        product_id = request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        # 連産子への表示展開後にも適用できるよう、品番フィルタは後段で評価する。
        product_code = (request.query_params.get('product_code') or '').strip()

        status_param = (request.query_params.get('status') or '').strip().upper()
        if status_param:
            queryset = queryset.filter(status=status_param)

        session_type = (request.query_params.get('session_type') or '').strip().upper()
        if session_type:
            queryset = queryset.filter(session_type=session_type)

        start_date = request.query_params.get('start_date')
        if start_date:
            d = parse_date(start_date)
            if d:
                queryset = queryset.filter(started_at__date__gte=d)

        end_date = request.query_params.get('end_date')
        if end_date:
            d = parse_date(end_date)
            if d:
                queryset = queryset.filter(started_at__date__lte=d)

        has_issue = request.query_params.get('has_issue')
        if has_issue is not None:
            normalized = str(has_issue).strip().lower()
            if normalized in ('1', 'true', 'yes'):
                queryset = queryset.filter(issue_count__gt=0)
            elif normalized in ('0', 'false', 'no'):
                queryset = queryset.filter(issue_count=0)

        limit = request.query_params.get('limit')
        try:
            limit_value = int(limit) if limit is not None else 200
        except ValueError:
            limit_value = 200
        limit_value = max(1, min(limit_value, 2000))

        sessions = list(queryset.order_by('-started_at', '-id')[:limit_value])
        serializer = ProcessWorkSessionSerializer(sessions, many=True)
        base_rows = list(serializer.data or [])
        if not base_rows:
            return Response([])

        line_calendar_cache = {}
        effective_seconds_map = {}

        for session_obj in sessions:
            session_id = getattr(session_obj, 'id', None)
            if not session_id:
                continue
            process = getattr(session_obj, 'process', None)
            line = getattr(process, 'line', None) if process else None
            line_id = getattr(line, 'id', None) if line else None

            calendar = None
            if line_id is not None:
                if line_id not in line_calendar_cache:
                    try:
                        line_calendar_cache[line_id] = LineWorkCalendar(line)
                    except Exception:
                        line_calendar_cache[line_id] = None
                calendar = line_calendar_cache.get(line_id)

            ended_at = session_obj.ended_at or timezone.now()
            effective_seconds_map[session_id] = _calculate_effective_work_seconds(
                calendar=calendar,
                started_at=session_obj.started_at,
                ended_at=ended_at,
            )

        def enrich_row_metrics(target_row):
            session_id = target_row.get('id')
            effective_seconds = int(effective_seconds_map.get(session_id) or 0)
            target_row['effective_work_seconds'] = effective_seconds

            qty_raw = target_row.get('production_qty')
            try:
                qty = Decimal(str(qty_raw or 0))
            except (InvalidOperation, TypeError, ValueError):
                qty = Decimal('0')

            if effective_seconds > 0 and qty > 0:
                productivity = (qty * Decimal('3600')) / Decimal(str(effective_seconds))
                target_row['productivity_per_hour'] = float(productivity.quantize(Decimal('0.001')))
            else:
                target_row['productivity_per_hour'] = None

        session_ids = [row.get('id') for row in base_rows if row.get('id')]
        session_id_set = set(session_ids)
        child_rows_by_session = {}
        if session_ids:
            production_rows = list(ProcessRealtimeRecord.objects.filter(
                record_type='PRODUCTION',
                event_data__work_session_id__in=session_ids,
            ).values(
                'id',
                'product_id',
                'product_code',
                'product_name',
                'qty',
                'event_data',
            ))

            # 既存データ互換:
            # OPERATOR_ACTION=PAUSE の数量が中断セッションに紐付いている場合、
            # 直前で閉じた作業セッション（end_action=PAUSE 側）へ寄せて表示する。
            pause_action_record_ids = set()
            for rec in production_rows:
                event_data = rec.get('event_data') or {}
                operator_action = str(event_data.get('operator_action') or '').upper()
                if operator_action != 'PAUSE':
                    continue
                action_record_raw = event_data.get('operator_action_record_id')
                try:
                    action_record_id = int(action_record_raw)
                except (TypeError, ValueError):
                    continue
                pause_action_record_ids.add(action_record_id)

            pause_to_work_session = {}
            if pause_action_record_ids:
                work_rows = ProcessWorkSession.objects.filter(
                    end_record_id__in=list(pause_action_record_ids),
                    session_type='WORK',
                ).values('end_record_id', 'id')
                for work_row in work_rows:
                    end_record_id = work_row.get('end_record_id')
                    work_session_id = work_row.get('id')
                    if not end_record_id or not work_session_id:
                        continue
                    prev_id = pause_to_work_session.get(end_record_id)
                    if prev_id is None or work_session_id > prev_id:
                        pause_to_work_session[end_record_id] = work_session_id

            for rec in production_rows:
                event_data = rec.get('event_data') or {}
                session_id_raw = event_data.get('work_session_id')
                parent_record_id = event_data.get('coproduct_parent_record_id')
                if not session_id_raw or not parent_record_id:
                    # 連産子展開レコードのみ対象（親実績は表示置換に使わない）
                    continue
                try:
                    session_id = int(session_id_raw)
                except (TypeError, ValueError):
                    continue

                operator_action = str(event_data.get('operator_action') or '').upper()
                if operator_action == 'PAUSE':
                    action_record_raw = event_data.get('operator_action_record_id')
                    try:
                        action_record_id = int(action_record_raw)
                    except (TypeError, ValueError):
                        action_record_id = None
                    mapped_session_id = pause_to_work_session.get(action_record_id)
                    if mapped_session_id and mapped_session_id in session_id_set:
                        session_id = mapped_session_id

                child_rows_by_session.setdefault(session_id, []).append({
                    'source_record_id': rec.get('id'),
                    'product_id': rec.get('product_id'),
                    'product_code': (rec.get('product_code') or '').strip() or None,
                    'product_name': (rec.get('product_name') or '').strip() or None,
                    'production_qty': rec.get('qty') or 0,
                    'coproduct_parent_product_code': (
                        (event_data.get('coproduct_parent_product_code') or '').strip() or None
                    ),
                })

            for key, values in child_rows_by_session.items():
                values.sort(key=lambda x: (
                    x.get('product_code') or '',
                    x.get('product_id') or 0,
                    x.get('source_record_id') or 0,
                ))

        result_rows = []
        for row in base_rows:
            session_id = row.get('id')
            child_rows = child_rows_by_session.get(session_id) or []
            if child_rows:
                # 連産子がある場合は親ではなく子のみ表示
                for child in child_rows:
                    expanded = dict(row)
                    expanded['product'] = child.get('product_id')
                    expanded['product_code'] = child.get('product_code')
                    expanded['product_name'] = child.get('product_name')
                    expanded['production_qty'] = child.get('production_qty') or 0
                    expanded['is_coproduct_child'] = True
                    expanded['coproduct_parent_product_code'] = child.get('coproduct_parent_product_code')
                    enrich_row_metrics(expanded)
                    result_rows.append(expanded)
                continue

            expanded = dict(row)
            expanded['is_coproduct_child'] = False
            expanded['coproduct_parent_product_code'] = None
            enrich_row_metrics(expanded)
            result_rows.append(expanded)

        if product_code:
            keyword = product_code.lower()
            filtered_rows = []
            for row in result_rows:
                code = str(row.get('product_code') or '').lower()
                parent_code = str(row.get('coproduct_parent_product_code') or '').lower()
                if keyword in code or (parent_code and keyword in parent_code):
                    filtered_rows.append(row)
            result_rows = filtered_rows

        return Response(result_rows)

    @action(detail=False, methods=['patch', 'delete'], url_path=r'sessions/(?P<session_id>[^/.]+)')
    def session_detail(self, request, session_id=None):
        session = ProcessWorkSession.objects.select_related('process', 'product').filter(id=session_id).first()
        if not session:
            return Response({'detail': 'セッションが見つかりません。'}, status=status.HTTP_404_NOT_FOUND)

        if request.method.lower() == 'delete':
            with transaction.atomic():
                old_qty = int(session.production_qty or 0) if _is_countable_session_for_actual(
                    session.session_type, session.end_action
                ) else 0
                if old_qty:
                    _adjust_backlog_actual_for_session(session, -old_qty)

                ProcessRealtimeRecord.objects.filter(
                    record_type='PRODUCTION',
                    event_data__work_session_id=session.id,
                ).delete()
                session.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        payload = request.data or {}
        started_at = session.started_at
        ended_at = session.ended_at
        production_qty = session.production_qty

        if 'started_at' in payload:
            next_started = payload.get('started_at')
            parsed = parse_datetime(next_started) if isinstance(next_started, str) and next_started else None
            if next_started and parsed is None:
                return Response({'detail': 'started_at の形式が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
            started_at = _normalize_input_datetime(parsed)

        if 'ended_at' in payload:
            next_ended = payload.get('ended_at')
            parsed = parse_datetime(next_ended) if isinstance(next_ended, str) and next_ended else None
            if next_ended and parsed is None:
                return Response({'detail': 'ended_at の形式が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
            ended_at = _normalize_input_datetime(parsed)

        if 'production_qty' in payload:
            try:
                production_qty = Decimal(str(payload.get('production_qty') or 0))
            except (InvalidOperation, TypeError, ValueError):
                return Response({'detail': 'production_qty の形式が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
            if production_qty < 0:
                return Response({'detail': 'production_qty は0以上で入力してください。'}, status=status.HTTP_400_BAD_REQUEST)

        if started_at and ended_at and ended_at < started_at:
            return Response({'detail': '終了時刻は開始時刻以降にしてください。'}, status=status.HTTP_400_BAD_REQUEST)

        old_qty = int(session.production_qty or 0) if _is_countable_session_for_actual(session.session_type, session.end_action) else 0
        new_qty = int(production_qty or 0) if _is_countable_session_for_actual(session.session_type, session.end_action) else 0
        delta = new_qty - old_qty

        with transaction.atomic():
            session.started_at = started_at
            session.ended_at = ended_at
            session.production_qty = production_qty
            session.status = 'CLOSED' if ended_at else 'OPEN'
            if started_at and ended_at and ended_at >= started_at:
                session.duration_seconds = int((ended_at - started_at).total_seconds())
            else:
                session.duration_seconds = 0
            session.save(update_fields=[
                'started_at',
                'ended_at',
                'production_qty',
                'status',
                'duration_seconds',
                'updated_at',
            ])

            if delta:
                _adjust_backlog_actual_for_session(session, delta)

        serializer = ProcessWorkSessionSerializer(session)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='status')
    def status(self, request):
        line_id = request.query_params.get('line_id')
        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        processes = Process.objects.filter(line_id=line_id, is_active=True).order_by('process_code')
        process_ids = list(processes.values_list('id', flat=True))
        if not process_ids:
            return Response([])

        business_today = get_business_today()
        start_dt = datetime.combine(business_today, time(DAY_BOUNDARY_HOUR, 0))
        end_dt = start_dt + timedelta(days=1) - timedelta(microseconds=1)
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
            plan_date=business_today,
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

                # 戻しは新規レコードとして登録（数量はマイナス）
                now = timezone.now()
                if timezone.is_aware(now):
                    now = timezone.localtime(now).replace(tzinfo=None)
                ref_process = sd.process or sd.occurrence_process
                return_date = resolve_workday_date_for_process(ref_process, now)
                return_record = ScrapRecord.objects.create(
                    process=sd.process,
                    occurrence_process=sd.occurrence_process or sd.process,
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
                            is_backlog_processed=True,  # 即時反映済み（再集計での二重計上を防止）
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

                    # 自工程/他工程を判定（仕損登録時と同じロジック）
                    actual_process, actual_line = _resolve_product_process_line(
                        product_obj, sd.process
                    )
                    is_self = actual_process and actual_process.id == (
                        sd.process_id if sd.process_id else None
                    )

                    target_line_id = getattr(actual_line, 'id', sd.line_id)
                    target_process_id = getattr(actual_process, 'id', sd.process_id)

                    # 基礎データレコードを確保
                    LineBacklog.objects.get_or_create(
                        line_id=target_line_id,
                        process_id=target_process_id,
                        product_id=sd.product_id,
                        plan_date=return_date,
                        sequence_no=0,
                        defaults={
                            'order_qty': 0,
                            'plan_qty': 0,
                            'actual_qty': 0,
                            'stock_qty': 0,
                            'planned_stock_qty': 0,
                            'adjust_qty': 0,
                            'scrap_qty': 0,
                            'scrap_adjust_qty': 0,
                            'actual_shipment_qty': 0,
                        }
                    )

                    backlog_filter = dict(
                        line_id=target_line_id,
                        process_id=target_process_id,
                        product_id=sd.product_id,
                        plan_date=return_date,
                    )

                    if is_self:
                        # 自工程仕損の戻し: scrap_qty 減算 + actual_qty 加算
                        LineBacklog.objects.filter(**backlog_filter).update(
                            scrap_qty=F('scrap_qty') - qty_int
                        )
                        if sd.is_production_recorded:
                            LineBacklog.objects.filter(**backlog_filter).update(
                                actual_qty=F('actual_qty') + qty_int
                            )
                    else:
                        # 他工程仕損の戻し: scrap_adjust_qty をプラスに戻す
                        LineBacklog.objects.filter(**backlog_filter).update(
                            scrap_adjust_qty=F('scrap_adjust_qty') + qty_int
                        )

                # 子部品・前工程品のadjust_qtyを戻す（BOM展開分をプラス補正）
                details_for_adjust = build_scrap_multiplier_details(product_id, qty)
                if details_for_adjust:
                    from django.db.models import F
                    for d in details_for_adjust:
                        detail_line_id = d.get('line_id')
                        detail_process_id = d.get('process_id')
                        detail_product_id = d.get('product_id')
                        detail_qty = d.get('qty') or Decimal('0')
                        if not detail_line_id or not detail_process_id or not detail_product_id:
                            continue
                        if product_id and detail_product_id == product_id:
                            continue  # 自製品は上で処理済み
                        qty_child = int(detail_qty or 0)
                        if qty_child == 0:
                            continue
                        LineBacklog.objects.get_or_create(
                            line_id=detail_line_id,
                            process_id=detail_process_id,
                            product_id=detail_product_id,
                            plan_date=return_date,
                            sequence_no=0,
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
                            line_id=detail_line_id,
                            process_id=detail_process_id,
                            product_id=detail_product_id,
                            plan_date=return_date,
                        ).update(
                            adjust_qty=F('adjust_qty') + qty_child
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
