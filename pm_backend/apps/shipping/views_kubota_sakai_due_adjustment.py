from datetime import date, datetime, timedelta
from collections import defaultdict
from decimal import Decimal, InvalidOperation

import django_filters
from django.db import transaction
from django.db.models import Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from orders.core.models import KubotaSakaiDueAdjustment, OrderLine
from .serializers import KubotaSakaiDueAdjustmentSerializer


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
            order_line__order__customer__customer_code='000196',
            order_line__order__order_no__icontains='SAKAI',
            order_line__order__order_type='FIRM',
        )

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

        line_qs = OrderLine.objects.select_related('order', 'order__customer', 'product').filter(
            order__status='OPEN',
            order__customer__customer_code='000196',
            order__order_no__icontains='SAKAI',
            order__order_type='FIRM',
        )

        line_qs = line_qs.filter(
            Q(due_date__range=(start_date, end_date))
            | Q(kubota_sakai_due_adjustments__adjusted_due_date__range=(start_date, end_date))
        ).distinct()

        if keyword:
            line_qs = line_qs.filter(
                Q(product_code__icontains=keyword)
                | Q(product__product_name__icontains=keyword)
            )

        line_qs = line_qs.order_by('product_code', 'due_date', 'order__order_no', 'line_no', 'id')
        line_list = list(line_qs)
        line_id_list = [line.id for line in line_list]

        adjustments = KubotaSakaiDueAdjustment.objects.filter(order_line_id__in=line_id_list).order_by(
            'order_line_id', 'split_no'
        )
        adjustment_map = {}
        for item in adjustments:
            adjustment_map.setdefault(item.order_line_id, []).append({
                'id': item.id,
                'split_no': item.split_no,
                'adjusted_due_date': item.adjusted_due_date.isoformat(),
                'adjusted_qty': str(item.adjusted_qty),
                'remaining_qty': str(item.remaining_qty),
                'adjustment_type': item.adjustment_type,
                'customer_approved': item.customer_approved,
                'note': item.note or '',
            })

        grouped = {}
        grouped_adjustments = defaultdict(
            lambda: defaultdict(lambda: {'qty': Decimal('0'), 'remaining_qty': Decimal('0'), 'customer_approved': False})
        )
        for line in line_list:
            group_key = f"{line.product_code}__{line.due_date.isoformat()}"
            if group_key not in grouped:
                grouped[group_key] = {
                    'order_key': group_key,
                    'order_line_ids': [],
                    'product_code': line.product_code,
                    'product_name': line.product.product_name if line.product else '',
                    'due_date': line.due_date.isoformat(),
                    'quantity': Decimal('0'),
                }
            grouped[group_key]['order_line_ids'].append(line.id)
            grouped[group_key]['quantity'] += line.quantity

            for adj in adjustment_map.get(line.id, []):
                current = grouped_adjustments[group_key][adj['adjusted_due_date']]
                current['qty'] += Decimal(str(adj['adjusted_qty']))
                current['remaining_qty'] += Decimal(str(adj.get('remaining_qty') or '0'))
                current['customer_approved'] = current['customer_approved'] or bool(adj['customer_approved'])

        rows = []
        for key, item in grouped.items():
            adjustment_rows = [
                {
                    'adjusted_due_date': due_date,
                    'adjusted_qty': str(payload['qty']),
                    'remaining_qty': str(payload['remaining_qty']),
                    'customer_approved': payload['customer_approved'],
                    'note': '',
                }
                for due_date, payload in sorted(grouped_adjustments.get(key, {}).items())
            ]
            rows.append({
                'order_key': item['order_key'],
                'order_line_ids': item['order_line_ids'],
                'product_code': item['product_code'],
                'product_name': item['product_name'],
                'due_date': item['due_date'],
                'quantity': str(item['quantity']),
                'adjustments': adjustment_rows,
            })

        return Response({
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'horizon_days': horizon_days,
            'rows': rows,
        })

    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        rows = request.data.get('rows')
        if not isinstance(rows, list):
            return Response({'detail': 'rows は配列で指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

        line_ids = []
        for row in rows:
            ids = row.get('order_line_ids')
            if isinstance(ids, list):
                line_ids.extend(ids)

        line_qs = OrderLine.objects.select_related('order').filter(
            id__in=line_ids,
            order__status='OPEN',
            order__customer__customer_code='000196',
            order__order_no__icontains='SAKAI',
            order__order_type='FIRM',
        )
        line_map = {line.id: line for line in line_qs}

        missing_ids = sorted(set(line_ids) - set(line_map.keys()))
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
                    'order_key': row.get('order_key'),
                    'detail': 'adjustments は配列で指定してください。',
                })
                continue

            normalized_entries = []
            total = Decimal('0')
            for idx, entry in enumerate(entries, start=1):
                adjusted_due_date = _parse_date(entry.get('adjusted_due_date'))
                adjusted_qty = _parse_decimal(entry.get('adjusted_qty'))
                remaining_qty = _parse_decimal(entry.get('remaining_qty'))
                note = str(entry.get('note') or '')
                customer_approved = bool(entry.get('customer_approved'))

                if not adjusted_due_date:
                    validation_errors.append({
                        'order_key': row.get('order_key'),
                        'split_no': idx,
                        'detail': '調整後納期が不正です。',
                    })
                    continue
                if adjusted_qty is None or adjusted_qty <= 0:
                    validation_errors.append({
                        'order_key': row.get('order_key'),
                        'split_no': idx,
                        'detail': '調整後数量は0より大きい値を指定してください。',
                    })
                    continue

                has_backward = any((adjusted_due_date > line.due_date) for line in group_lines)
                if has_backward and not customer_approved:
                    validation_errors.append({
                        'order_key': row.get('order_key'),
                        'split_no': idx,
                        'detail': '後ろ倒し分は顧客承認済みチェックが必要です。',
                    })
                    continue

                normalized_entries.append({
                    'split_no': idx,
                    'adjusted_due_date': adjusted_due_date,
                    'adjusted_qty': adjusted_qty,
                    'remaining_qty': remaining_qty if remaining_qty is not None else Decimal('0'),
                    'customer_approved': customer_approved,
                    'note': note,
                })
                total += adjusted_qty

            if validation_errors:
                continue

            total_base_qty = sum((line.quantity for line in group_lines), Decimal('0'))
            if total != total_base_qty:
                validation_errors.append({
                    'order_key': row.get('order_key'),
                    'detail': f'数量合計不一致: 注文数量={total_base_qty} / 納入合計={total}',
                })
                continue

            payload_map[row.get('order_key') or str(group_lines[0].product_code)] = {
                'line_ids': [line.id for line in group_lines],
                'lines': group_lines,
                'entries': normalized_entries,
            }

        if validation_errors:
            return Response(
                {'detail': '入力エラーがあります。', 'errors': validation_errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user if request.user and request.user.is_authenticated else None

        with transaction.atomic():
            all_line_ids = []
            for group_payload in payload_map.values():
                all_line_ids.extend(group_payload['line_ids'])
            KubotaSakaiDueAdjustment.objects.filter(order_line_id__in=all_line_ids).delete()

            create_items = []
            for group_payload in payload_map.values():
                lines = sorted(group_payload['lines'], key=lambda x: (x.order.order_no, x.line_no, x.id))
                line_remaining = {line.id: Decimal(line.quantity) for line in lines}
                split_no_map = defaultdict(int)
                group_key = '__'.join([lines[0].product_code, lines[0].due_date.isoformat()]) if lines else ''

                for entry in group_payload['entries']:
                    remaining_qty = Decimal(entry['adjusted_qty'])
                    remaining_remaining_qty = Decimal(entry.get('remaining_qty') or 0)
                    entry_allocations = []
                    for line in lines:
                        if remaining_qty <= 0:
                            break
                        available = line_remaining[line.id]
                        if available <= 0:
                            continue
                        alloc_qty = min(available, remaining_qty)
                        entry_allocations.append((line, alloc_qty))
                        line_remaining[line.id] = available - alloc_qty
                        remaining_qty -= alloc_qty

                    if remaining_qty > 0:
                        validation_errors.append({
                            'order_key': group_key,
                            'detail': '納入数量の配分に失敗しました。',
                        })
                        break

                    allocated_total = sum((alloc_qty for _, alloc_qty in entry_allocations), Decimal('0'))
                    allocated_remaining_total = Decimal('0')
                    for alloc_idx, (line, alloc_qty) in enumerate(entry_allocations, start=1):
                        if alloc_idx == len(entry_allocations):
                            alloc_remaining_qty = remaining_remaining_qty - allocated_remaining_total
                        elif allocated_total > 0:
                            alloc_remaining_qty = (
                                remaining_remaining_qty * alloc_qty / allocated_total
                            ).quantize(Decimal('0.001'))
                        else:
                            alloc_remaining_qty = Decimal('0')
                        allocated_remaining_total += alloc_remaining_qty
                        if entry['adjusted_due_date'] < line.due_date:
                            adjustment_type = 'forward'
                        elif entry['adjusted_due_date'] > line.due_date:
                            adjustment_type = 'backward'
                        else:
                            adjustment_type = 'just'
                        split_no_map[line.id] += 1
                        create_items.append(
                            KubotaSakaiDueAdjustment(
                                order_line_id=line.id,
                                split_no=split_no_map[line.id],
                                adjusted_due_date=entry['adjusted_due_date'],
                                adjusted_qty=alloc_qty,
                                remaining_qty=alloc_remaining_qty,
                                adjustment_type=adjustment_type,
                                customer_approved=entry['customer_approved'],
                                adjusted_by=user,
                                adjusted_at=datetime.now(),
                                note=entry['note'],
                            )
                        )

                if any((qty > 0 for qty in line_remaining.values())):
                    validation_errors.append({
                        'order_key': group_key,
                        'detail': '受注明細数量への配分が完了しませんでした。',
                    })

            if validation_errors:
                transaction.set_rollback(True)
                return Response(
                    {'detail': '入力エラーがあります。', 'errors': validation_errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            KubotaSakaiDueAdjustment.objects.bulk_create(create_items)

        summary = KubotaSakaiDueAdjustment.objects.filter(order_line_id__in=line_ids).aggregate(
            total_rows=Sum('adjusted_qty')
        )
        return Response({
            'saved_order_groups': len(payload_map),
            'saved_order_lines': len(set(line_ids)),
            'saved_adjustments': KubotaSakaiDueAdjustment.objects.filter(order_line_id__in=line_ids).count(),
            'total_adjusted_qty': str(summary.get('total_rows') or Decimal('0')),
        })
