from datetime import date, datetime, timedelta
from collections import defaultdict
from decimal import Decimal, InvalidOperation

import django_filters
from django.db import transaction
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from orders.core.models import KubotaSakaiDueAdjustment, OrderLine
from .serializers import KubotaSakaiDueAdjustmentSerializer


KUBOTA_CUSTOMER_CODE = '000196'


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except ValueError:
        return None


def _parse_decimal(value):
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _source_order_no(order_line):
    """FIRM は OrderLine.customer_order_no、FORECAST は NULL。"""
    order_type = getattr(order_line.order, 'order_type', None) if order_line.order_id else None
    if order_type == 'FORECAST':
        return None
    value = (order_line.customer_order_no or '').strip()
    return value or None


def _group_key(product_code, ship_to_code, source_order_no):
    return (
        str(product_code or ''),
        str(ship_to_code or ''),
        str(source_order_no or ''),
    )


def _group_key_to_str(key_tuple):
    return '||'.join(key_tuple)


class KubotaSakaiDueAdjustmentFilter(django_filters.FilterSet):
    adjusted_due_date__gte = django_filters.DateFilter(field_name='adjusted_due_date', lookup_expr='gte')
    adjusted_due_date__lte = django_filters.DateFilter(field_name='adjusted_due_date', lookup_expr='lte')
    order_line = django_filters.NumberFilter(field_name='order_line_id')
    order_line__in = django_filters.BaseInFilter(field_name='order_line_id', lookup_expr='in')

    class Meta:
        model = KubotaSakaiDueAdjustment
        fields = ['order_line', 'order_line__in', 'adjusted_due_date__gte', 'adjusted_due_date__lte']


class KubotaSakaiDueAdjustmentViewSet(viewsets.ModelViewSet):
    queryset = KubotaSakaiDueAdjustment.objects.select_related(
        'order_line',
        'order_line__order',
        'order_line__order__customer',
        'order_line__product',
        'adjusted_by',
    )
    serializer_class = KubotaSakaiDueAdjustmentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = KubotaSakaiDueAdjustmentFilter
    search_fields = ['order_line__product_code', 'order_line__product__product_name']
    ordering_fields = ['adjusted_due_date', 'split_no', 'id']
    ordering = ['order_line_id', 'split_no']

    def get_queryset(self):
        return super().get_queryset().filter(
            order_line__order__status='OPEN',
            order_line__order__customer__customer_code=KUBOTA_CUSTOMER_CODE,
        )

    # ---------- grid ----------
    @action(detail=False, methods=['get'])
    def grid(self, request):
        start_date = _parse_date(request.query_params.get('start_date'))
        horizon_days = int(request.query_params.get('horizon_days') or 30)
        if horizon_days < 1:
            horizon_days = 1
        if horizon_days > 180:
            horizon_days = 180
        if not start_date:
            start_date = date.today()
        end_date = start_date + timedelta(days=horizon_days - 1)
        keyword = (request.query_params.get('keyword') or '').strip()

        # 対象 OrderLine 抽出: Kubota顧客 + OPEN + (元納期 in 範囲 OR 調整行 in 範囲)
        line_qs = OrderLine.objects.select_related('order', 'order__customer', 'product').filter(
            order__status='OPEN',
            order__customer__customer_code=KUBOTA_CUSTOMER_CODE,
        ).filter(
            Q(due_date__range=(start_date, end_date))
            | Q(kubota_sakai_due_adjustments__adjusted_due_date__range=(start_date, end_date))
        ).distinct()

        if keyword:
            line_qs = line_qs.filter(
                Q(product_code__icontains=keyword)
                | Q(product__product_name__icontains=keyword)
            )

        line_qs = line_qs.order_by('product_code', 'due_date', 'ship_to_code', 'order__order_no', 'line_no', 'id')
        line_list = list(line_qs)

        # FIRM/FORECAST 重複排除: (product_code, due_date, ship_to_code) で FIRM 有→同日同場所の FORECAST を除外
        firm_key_set = set()
        for line in line_list:
            order_type = getattr(line.order, 'order_type', None)
            if order_type == 'FIRM':
                firm_key_set.add((line.product_code, line.due_date, line.ship_to_code or ''))

        surviving_lines = []
        for line in line_list:
            order_type = getattr(line.order, 'order_type', None)
            key = (line.product_code, line.due_date, line.ship_to_code or '')
            if order_type == 'FORECAST' and key in firm_key_set:
                continue
            surviving_lines.append(line)

        # 二段グルーピング: 外側=(品番, 納入場所), 内側=(注番)
        outer_groups = {}
        for line in surviving_lines:
            src_order_no = _source_order_no(line)
            ship_to_code = line.ship_to_code or ''
            outer_key_str = _group_key_to_str((str(line.product_code or ''), str(ship_to_code or '')))
            if outer_key_str not in outer_groups:
                outer_groups[outer_key_str] = {
                    'group_key': outer_key_str,
                    'product_code': line.product_code,
                    'product_name': line.product.product_name if line.product else '',
                    'ship_to_code': ship_to_code or None,
                    'ship_to_name': ship_to_code or None,
                    'lines_map': {},
                }
            lines_map = outer_groups[outer_key_str]['lines_map']
            line_key_str = _group_key_to_str(_group_key(line.product_code, ship_to_code, src_order_no))
            if line_key_str not in lines_map:
                lines_map[line_key_str] = {
                    'line_key': line_key_str,
                    'order_line_ids': [],
                    'source_order_no': src_order_no,
                    'order_type': getattr(line.order, 'order_type', None),
                    'source_qty_by_date': defaultdict(lambda: Decimal('0')),
                }
            lines_map[line_key_str]['order_line_ids'].append(line.id)
            if line.due_date:
                lines_map[line_key_str]['source_qty_by_date'][line.due_date.isoformat()] += (line.quantity or Decimal('0'))
            if getattr(line.order, 'order_type', None) == 'FIRM':
                lines_map[line_key_str]['order_type'] = 'FIRM'

        # 既存 adjustments を order_line_id で集める
        line_id_list = [line.id for line in surviving_lines]
        adjustments = list(
            KubotaSakaiDueAdjustment.objects.filter(order_line_id__in=line_id_list).order_by(
                'order_line_id', 'split_no'
            )
        )
        adj_by_line = defaultdict(list)
        for adj in adjustments:
            adj_by_line[adj.order_line_id].append(adj)

        rows = []
        for outer_key_str, og in outer_groups.items():
            lines_out = []
            for line_key_str, li in og['lines_map'].items():
                agg_by_date = defaultdict(lambda: {
                    'adjusted_qty': Decimal('0'),
                    'remaining_qty': Decimal('0'),
                    'customer_approved': False,
                    'note': '',
                })
                for oid in li['order_line_ids']:
                    for adj in adj_by_line.get(oid, []):
                        cell = agg_by_date[adj.adjusted_due_date.isoformat()]
                        cell['adjusted_qty'] += (adj.adjusted_qty or Decimal('0'))
                        cell['remaining_qty'] = adj.remaining_qty or Decimal('0')
                        cell['customer_approved'] = cell['customer_approved'] or bool(adj.customer_approved)
                        if not cell['note'] and adj.note:
                            cell['note'] = adj.note

                adjustment_rows = [
                    {
                        'adjusted_due_date': d,
                        'adjusted_qty': str(payload['adjusted_qty']),
                        'remaining_qty': str(payload['remaining_qty']),
                        'customer_approved': payload['customer_approved'],
                        'note': payload['note'],
                    }
                    for d, payload in sorted(agg_by_date.items())
                ]
                source_qty_by_date = {d: str(q) for d, q in sorted(li['source_qty_by_date'].items())}
                total_source_qty = sum(li['source_qty_by_date'].values(), Decimal('0'))
                lines_out.append({
                    'line_key': li['line_key'],
                    'order_line_ids': li['order_line_ids'],
                    'source_order_no': li['source_order_no'],
                    'order_type': li['order_type'],
                    'source_qty_by_date': source_qty_by_date,
                    'source_qty_total': str(total_source_qty),
                    'adjustments': adjustment_rows,
                })

            # 注番付き FIRM を先、内示（NULL）を後に
            lines_out.sort(key=lambda x: (x['source_order_no'] is None, x['source_order_no'] or ''))

            rows.append({
                'group_key': og['group_key'],
                'product_code': og['product_code'],
                'product_name': og['product_name'],
                'ship_to_code': og['ship_to_code'],
                'ship_to_name': og['ship_to_name'],
                'lines': lines_out,
            })

        rows.sort(key=lambda r: (r['product_code'] or '', r['ship_to_code'] or ''))

        return Response({
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'horizon_days': horizon_days,
            'rows': rows,
        })

    # ---------- bulk_save ----------
    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        rows = request.data.get('rows')
        if not isinstance(rows, list):
            return Response({'detail': 'rows は配列で指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

        # 対象 order_line を一括取得
        all_line_ids = []
        for row in rows:
            ids = row.get('order_line_ids')
            if isinstance(ids, list):
                for v in ids:
                    try:
                        all_line_ids.append(int(v))
                    except (TypeError, ValueError):
                        pass

        if not all_line_ids:
            return Response({'detail': '保存対象がありません。'}, status=status.HTTP_400_BAD_REQUEST)

        line_qs = OrderLine.objects.select_related('order', 'order__customer', 'product').filter(
            id__in=all_line_ids,
            order__status='OPEN',
            order__customer__customer_code=KUBOTA_CUSTOMER_CODE,
        )
        line_map = {line.id: line for line in line_qs}

        missing_ids = sorted(set(all_line_ids) - set(line_map.keys()))
        if missing_ids:
            return Response(
                {'detail': '対象外の受注明細が含まれています。', 'missing_order_line_ids': missing_ids},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validation_errors = []
        payload_map = {}

        for row in rows:
            order_line_ids = row.get('order_line_ids')
            if not isinstance(order_line_ids, list) or not order_line_ids:
                continue

            group_lines = [line_map.get(int(line_id)) for line_id in order_line_ids if line_map.get(int(line_id))]
            if not group_lines:
                continue

            entries = row.get('adjustments')
            if not isinstance(entries, list):
                validation_errors.append({
                    'group_key': row.get('group_key'),
                    'detail': 'adjustments は配列で指定してください。',
                })
                continue

            # source_qty の合計（FIRM/FORECAST 区別なくグループ内合計）
            total_base_qty = Decimal('0')
            for line in group_lines:
                total_base_qty += (line.quantity or Decimal('0'))

            normalized_entries = []
            total = Decimal('0')
            for idx, entry in enumerate(entries, start=1):
                adjusted_due_date = _parse_date(entry.get('adjusted_due_date'))
                adjusted_qty = _parse_decimal(entry.get('adjusted_qty'))
                note = str(entry.get('note') or '')
                customer_approved = bool(entry.get('customer_approved'))

                if not adjusted_due_date:
                    validation_errors.append({
                        'group_key': row.get('group_key'),
                        'split_no': idx,
                        'detail': '調整後納期が不正です。',
                    })
                    continue
                if adjusted_qty is None or adjusted_qty <= 0:
                    validation_errors.append({
                        'group_key': row.get('group_key'),
                        'split_no': idx,
                        'detail': '調整後数量は0より大きい値を指定してください。',
                    })
                    continue

                has_backward = any((adjusted_due_date > line.due_date) for line in group_lines)
                if has_backward and not customer_approved:
                    validation_errors.append({
                        'group_key': row.get('group_key'),
                        'split_no': idx,
                        'detail': '後ろ倒し分は顧客承認済みチェックが必要です。',
                    })
                    continue

                normalized_entries.append({
                    'adjusted_due_date': adjusted_due_date,
                    'adjusted_qty': adjusted_qty,
                    'customer_approved': customer_approved,
                    'note': note,
                })
                total += adjusted_qty

            if validation_errors:
                continue

            if total != total_base_qty:
                validation_errors.append({
                    'group_key': row.get('group_key'),
                    'detail': f'数量合計不一致: 元数量={total_base_qty} / 調整後合計={total}',
                })
                continue

            payload_map[row.get('group_key') or str(len(payload_map))] = {
                'lines': group_lines,
                'entries': normalized_entries,
            }

        if validation_errors:
            return Response(
                {'detail': '入力エラーがあります。', 'errors': validation_errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user if request.user and request.user.is_authenticated else None
        created_total = 0
        affected_calc_keys = set()

        with transaction.atomic():
            # 既存調整を group 単位で全削除
            for payload in payload_map.values():
                line_ids = [line.id for line in payload['lines']]
                # 削除前に影響を受けそうな calc key を記録（削除対象の既存値も含む）
                for existing in KubotaSakaiDueAdjustment.objects.filter(order_line_id__in=line_ids):
                    affected_calc_keys.add((
                        existing.order_line.product_code if existing.order_line_id else '',
                        existing.ship_to_code or '',
                        existing.source_order_no or '',
                    ))
                KubotaSakaiDueAdjustment.objects.filter(order_line_id__in=line_ids).delete()

            create_items = []
            for payload in payload_map.values():
                lines = sorted(payload['lines'], key=lambda x: (x.order.order_no, x.line_no, x.id))
                line_remaining = {line.id: (line.quantity or Decimal('0')) for line in lines}
                split_no_map = defaultdict(int)

                for entry in payload['entries']:
                    remaining_entry_qty = Decimal(entry['adjusted_qty'])
                    for line in lines:
                        if remaining_entry_qty <= 0:
                            break
                        available = line_remaining[line.id]
                        if available <= 0:
                            continue
                        alloc_qty = min(available, remaining_entry_qty)
                        line_remaining[line.id] = available - alloc_qty
                        remaining_entry_qty -= alloc_qty

                        if entry['adjusted_due_date'] < line.due_date:
                            adjustment_type = 'forward'
                        elif entry['adjusted_due_date'] > line.due_date:
                            adjustment_type = 'backward'
                        else:
                            adjustment_type = 'just'

                        split_no_map[line.id] += 1
                        src_order_no = _source_order_no(line)
                        ship_to_code = line.ship_to_code or None

                        create_items.append(KubotaSakaiDueAdjustment(
                            order_line_id=line.id,
                            split_no=split_no_map[line.id],
                            adjusted_due_date=entry['adjusted_due_date'],
                            adjusted_qty=alloc_qty,
                            remaining_qty=Decimal('0'),  # 後で再計算
                            adjustment_type=adjustment_type,
                            customer_approved=entry['customer_approved'],
                            adjusted_by=user,
                            adjusted_at=datetime.now(),
                            note=entry['note'],
                            source_order_no=src_order_no,
                            source_due_date=line.due_date,
                            source_qty=(line.quantity or Decimal('0')),
                            ship_to_code=ship_to_code,
                            ship_to_name=ship_to_code,
                        ))

                        affected_calc_keys.add((
                            line.product_code or '',
                            ship_to_code or '',
                            src_order_no or '',
                        ))

                    if remaining_entry_qty > 0:
                        validation_errors.append({
                            'group_key': None,
                            'detail': '受注明細数量への配分に失敗しました。',
                        })

            if validation_errors:
                transaction.set_rollback(True)
                return Response(
                    {'detail': '入力エラーがあります。', 'errors': validation_errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            KubotaSakaiDueAdjustment.objects.bulk_create(create_items)
            created_total = len(create_items)

            # remaining_qty を calc key ごとに時系列再計算
            self._recalculate_remaining(affected_calc_keys)

        return Response({
            'saved_groups': len(payload_map),
            'saved_adjustments': created_total,
            'affected_calc_keys': len(affected_calc_keys),
        })

    def _recalculate_remaining(self, calc_keys):
        """calc_key = (product_code, ship_to_code, source_order_no)
        それぞれについて日付昇順で running balance を計算し、該当行の remaining_qty を更新する。
        """
        for product_code, ship_to_code, source_order_no in calc_keys:
            qs = KubotaSakaiDueAdjustment.objects.filter(
                order_line__product_code=product_code,
                ship_to_code=(ship_to_code or None),
            )
            if source_order_no:
                qs = qs.filter(source_order_no=source_order_no)
            else:
                qs = qs.filter(source_order_no__isnull=True)

            rows = list(qs)
            if not rows:
                continue

            # source_qty を order_line_id 単位で重複排除（同一 order_line の複数分割行で二重計上しない）
            source_by_line = {}
            adjusted_by_date = defaultdict(lambda: Decimal('0'))
            for r in rows:
                if r.order_line_id not in source_by_line and r.source_due_date:
                    source_by_line[r.order_line_id] = (r.source_due_date, r.source_qty or Decimal('0'))
                adjusted_by_date[r.adjusted_due_date] += (r.adjusted_qty or Decimal('0'))

            source_by_date = defaultdict(lambda: Decimal('0'))
            for src_date, src_qty in source_by_line.values():
                source_by_date[src_date] += src_qty

            all_dates = sorted(set(source_by_date.keys()) | set(adjusted_by_date.keys()))
            running_at_date = {}
            running = Decimal('0')
            for d in all_dates:
                running += source_by_date.get(d, Decimal('0')) - adjusted_by_date.get(d, Decimal('0'))
                running_at_date[d] = running

            for r in rows:
                new_val = running_at_date.get(r.adjusted_due_date, Decimal('0'))
                if r.remaining_qty != new_val:
                    r.remaining_qty = new_val
                    r.save(update_fields=['remaining_qty'])
