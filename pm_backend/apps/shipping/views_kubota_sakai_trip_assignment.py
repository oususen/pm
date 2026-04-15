from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from masters.models import Calendar, CalendarDay, KubotaSakaiTruck, Line, Process
from orders.core.models import KubotaSakaiDueAdjustment, KubotaSakaiTripAssignment, OrderLine
from production.models_line_backlog import LineBacklog
from system_settings.models import SystemSetting

from .serializers import KubotaSakaiTripAssignmentSerializer
from .services.truck_load_calculator import calculate_truck_load

KUBOTA_DELIVERY_LINE_CODE = 'KUBOTA_DELIVERY'
KUBOTA_DELIVERY_LINE_NAME = 'クボタ配送ライン'
KUBOTA_DELIVERY_PROCESS_CODE = 'KUBOTA_DELIVERY'
KUBOTA_DELIVERY_PROCESS_NAME = 'クボタ配送工程'


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except ValueError:
        return None


def _to_decimal(value, default='0'):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def _resolve_kubota_calendar():
    rows = Calendar.objects.all()
    code_hits = rows.filter(
        Q(calendar_code__iexact='kubota_sakai')
        | Q(calendar_code__iexact='kobota_sakai')
        | Q(calendar_code__icontains='kubota')
        | Q(calendar_code__icontains='kobota')
    )
    if code_hits.exists():
        return code_hits.order_by('id').first()
    name_hits = rows.filter(Q(calendar_name__icontains='クボタ') & Q(calendar_name__icontains='堺'))
    return name_hits.order_by('id').first()


def _build_calendar_day_map(calendar):
    if not calendar:
        return {}
    return {
        item.target_date: bool(item.is_working_day)
        for item in CalendarDay.objects.filter(calendar_id=calendar.id)
    }


def _is_working_day(target_date, calendar_map):
    if target_date in calendar_map:
        return bool(calendar_map[target_date])
    return target_date.weekday() < 5


def _subtract_business_days(target_date, days, calendar_map):
    current = target_date
    remaining = max(int(days or 0), 0)
    while remaining > 0:
        current -= timedelta(days=1)
        if _is_working_day(current, calendar_map):
            remaining -= 1
    return current


def _safe_product_name(order_line):
    if order_line.product_id and order_line.product:
        return order_line.product.product_name or ''
    return ''


def _build_load_item(order_line, qty):
    product = order_line.product
    container = getattr(product, 'used_container', None) if product else None
    unit_weight = Decimal('0')
    if product:
        if all(getattr(product, f, None) is not None for f in ('specific_gravity', 'size_length', 'size_width', 'size_thickness')):
            unit_weight = (
                _to_decimal(product.specific_gravity)
                * _to_decimal(product.size_length)
                * _to_decimal(product.size_width)
                * _to_decimal(product.size_thickness)
                / Decimal('1000000')
            )

    capacity = getattr(product, 'capacity', None) if product else None
    if not capacity and container:
        capacity = container.capacity

    return {
        'product_code': order_line.product_code,
        'qty': _to_decimal(qty),
        'unit_weight': unit_weight,
        'container': {
            'width': getattr(container, 'width', None) if container else None,
            'depth': getattr(container, 'depth', None) if container else None,
            'height': getattr(container, 'height', None) if container else None,
            'capacity': capacity or 1,
            'can_mix': getattr(container, 'can_mix', True) if container else True,
            'stackable': getattr(container, 'stackable', True) if container else True,
            'max_stack': getattr(container, 'max_stack', 999) if container else 999,
        },
    }


def _get_deadline_days():
    row = SystemSetting.objects.filter(key='kubota_sakai.assignment_deadline_days').first()
    if not row:
        return 3
    try:
        return max(int(row.value), 0)
    except Exception:
        return 3


def _line_available_qty_on_date(line, target_date, line_adjustments):
    adjustments = line_adjustments.get(line.id, [])
    if adjustments:
        return sum((_to_decimal(adj.adjusted_qty) for adj in adjustments if adj.adjusted_due_date == target_date), Decimal('0'))
    if line.due_date == target_date:
        return _to_decimal(line.quantity)
    return Decimal('0')


def _to_int_qty(value):
    qty = _to_decimal(value)
    if qty <= 0:
        return 0
    return int(qty.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _resolve_kubota_delivery_line_process():
    calendar = _resolve_kubota_calendar()
    existing_process = (
        Process.objects.select_related('line')
        .filter(
            Q(process_code='4902')
            | Q(process_name__icontains='クボタ配送')
        )
        .order_by('id')
        .first()
    )
    if existing_process and existing_process.line_id:
        line = existing_process.line
        line_updates = []
        if not line.is_active:
            line.is_active = True
            line_updates.append('is_active')
        if calendar and line.calendar_id != calendar.id:
            line.calendar = calendar
            line_updates.append('calendar')
        if line_updates:
            line.save(update_fields=line_updates)
        return line, existing_process

    existing_line = (
        Line.objects.filter(
            Q(line_code='L3102')
            | Q(line_name__icontains='クボタ配送ライン')
        )
        .order_by('id')
        .first()
    )
    if existing_line:
        if not existing_line.is_active or (calendar and existing_line.calendar_id != calendar.id):
            line_updates = []
            if not existing_line.is_active:
                existing_line.is_active = True
                line_updates.append('is_active')
            if calendar and existing_line.calendar_id != calendar.id:
                existing_line.calendar = calendar
                line_updates.append('calendar')
            existing_line.save(update_fields=line_updates)

        process = (
            Process.objects.filter(
                line_id=existing_line.id,
                process_name__icontains='クボタ配送',
            )
            .order_by('id')
            .first()
        )
        if process:
            return existing_line, process

        created_process = Process.objects.create(
            process_code=KUBOTA_DELIVERY_PROCESS_CODE,
            process_name=KUBOTA_DELIVERY_PROCESS_NAME,
            line=existing_line,
        )
        return existing_line, created_process

    line_defaults = {
        'line_name': KUBOTA_DELIVERY_LINE_NAME,
        'line_type': 'OTHER',
        'is_active': True,
    }
    if calendar:
        line_defaults['calendar'] = calendar
    line, created = Line.objects.get_or_create(
        line_code=KUBOTA_DELIVERY_LINE_CODE,
        defaults=line_defaults,
    )
    update_fields = []
    if line.line_name != KUBOTA_DELIVERY_LINE_NAME:
        line.line_name = KUBOTA_DELIVERY_LINE_NAME
        update_fields.append('line_name')
    if line.line_type != 'OTHER':
        line.line_type = 'OTHER'
        update_fields.append('line_type')
    if not line.is_active:
        line.is_active = True
        update_fields.append('is_active')
    if calendar and line.calendar_id != calendar.id:
        line.calendar = calendar
        update_fields.append('calendar')
    if update_fields and not created:
        line.save(update_fields=update_fields)

    process, p_created = Process.objects.get_or_create(
        process_code=KUBOTA_DELIVERY_PROCESS_CODE,
        defaults={
            'process_name': KUBOTA_DELIVERY_PROCESS_NAME,
            'line': line,
        },
    )
    process_updates = []
    if process.process_name != KUBOTA_DELIVERY_PROCESS_NAME:
        process.process_name = KUBOTA_DELIVERY_PROCESS_NAME
        process_updates.append('process_name')
    if process.line_id != line.id:
        process.line = line
        process_updates.append('line')
    if process_updates and not p_created:
        process.save(update_fields=process_updates)

    return line, process


def _sync_kubota_delivery_backlog_for_date(target_date):
    line, process = _resolve_kubota_delivery_line_process()
    assignments = list(
        KubotaSakaiTripAssignment.objects.select_related('order_line__product')
        .filter(departure_date=target_date)
        .order_by('order_line__product_code', 'order_line_id', 'id')
    )

    LineBacklog.objects.filter(
        line_id=line.id,
        process_id=process.id,
        plan_date=target_date,
        sequence_no__gt=0,
    ).delete()

    seq_by_product = defaultdict(int)
    to_create = []
    for assignment in assignments:
        product = assignment.order_line.product
        if not product:
            continue
        qty = _to_int_qty(assignment.qty)
        if qty <= 0:
            continue
        seq_by_product[product.id] += 1
        to_create.append(
            LineBacklog(
                plan_date=target_date,
                process_id=process.id,
                product_id=product.id,
                line_id=line.id,
                sequence_no=seq_by_product[product.id],
                plan_qty=qty,
                order_qty=0,
                demand_qty_plan=0,
            )
        )

    if to_create:
        LineBacklog.objects.bulk_create(to_create)


class KubotaSakaiTripAssignmentViewSet(viewsets.ModelViewSet):
    queryset = KubotaSakaiTripAssignment.objects.select_related('order_line', 'order_line__product', 'truck', 'created_by')
    serializer_class = KubotaSakaiTripAssignmentSerializer
    ordering = ['departure_date', 'truck_id', 'order_line_id', 'id']

    def get_queryset(self):
        return super().get_queryset().filter(
            order_line__order__status='OPEN',
            order_line__order__customer__customer_code='000196',
        )

    @action(detail=False, methods=['get'])
    def grid(self, request):
        target_date = _parse_date(request.query_params.get('target_date')) or date.today()
        keyword = str(request.query_params.get('keyword') or '').strip()

        line_qs = OrderLine.objects.select_related('product', 'order').filter(
            order__status='OPEN',
            order__customer__customer_code='000196',
        ).filter(
            Q(due_date=target_date)
            | Q(kubota_sakai_due_adjustments__adjusted_due_date=target_date)
        ).distinct()

        if keyword:
            line_qs = line_qs.filter(
                Q(product_code__icontains=keyword)
                | Q(product__product_name__icontains=keyword)
            )

        lines = list(line_qs.order_by('product_code', 'due_date', 'id'))
        line_ids = [line.id for line in lines]

        adjustments = KubotaSakaiDueAdjustment.objects.filter(order_line_id__in=line_ids).order_by('order_line_id', 'split_no')
        line_adjustments = defaultdict(list)
        for adj in adjustments:
            line_adjustments[adj.order_line_id].append(adj)

        assignments = KubotaSakaiTripAssignment.objects.filter(order_line_id__in=line_ids, departure_date=target_date).order_by('order_line_id', 'id')
        assignment_map = defaultdict(list)
        for item in assignments:
            assignment_map[item.order_line_id].append(item)

        calendar = _resolve_kubota_calendar()
        calendar_map = _build_calendar_day_map(calendar)
        deadline_days = _get_deadline_days()
        today = date.today()

        rows = []
        for line in lines:
            available_qty = _line_available_qty_on_date(line, target_date, line_adjustments)
            if available_qty <= 0:
                continue

            current_assignments = assignment_map.get(line.id, [])
            assigned_qty = sum((_to_decimal(a.qty) for a in current_assignments), Decimal('0'))
            unassigned_qty = available_qty - assigned_qty
            deadline_date = _subtract_business_days(target_date, deadline_days, calendar_map)
            overdue = unassigned_qty > 0 and today > deadline_date

            product = line.product
            container = getattr(product, 'used_container', None) if product else None

            rows.append({
                'order_line_id': line.id,
                'adjusted_due_date': target_date.isoformat(),
                'product_code': line.product_code,
                'product_name': _safe_product_name(line),
                'qty': str(available_qty),
                'assigned_qty': str(assigned_qty),
                'unassigned_qty': str(unassigned_qty),
                'container_name': getattr(container, 'name', '') if container else '',
                'capacity': getattr(product, 'capacity', None) if product else None,
                'overdue': overdue,
                'deadline_date': deadline_date.isoformat(),
                'allocations': [
                    {
                        'id': a.id,
                        'truck_id': a.truck_id,
                        'truck_name': a.truck.name if a.truck_id else '',
                        'qty': str(a.qty),
                    }
                    for a in current_assignments
                ],
            })

        trucks = list(KubotaSakaiTruck.objects.filter(is_active=True).order_by('display_order', 'name'))
        all_assignments_today = list(
            KubotaSakaiTripAssignment.objects.select_related('order_line', 'order_line__product', 'truck')
            .filter(departure_date=target_date, truck_id__in=[t.id for t in trucks])
            .order_by('truck_id', 'id')
        )
        per_truck = defaultdict(list)
        for assignment in all_assignments_today:
            per_truck[assignment.truck_id].append(assignment)

        truck_summaries = []
        for truck in trucks:
            load_items = [_build_load_item(a.order_line, a.qty) for a in per_truck.get(truck.id, [])]
            load = calculate_truck_load(load_items, truck)
            truck_summaries.append({
                'truck_id': truck.id,
                'truck_name': truck.name,
                'occupancy_percent': str(load['occupancy_percent']),
                'total_weight': str(load['total_weight']),
                'errors': load['errors'],
            })

        return Response({
            'target_date': target_date.isoformat(),
            'assignment_deadline_days': deadline_days,
            'rows': rows,
            'trucks': [
                {'id': t.id, 'name': t.name, 'default_use': t.default_use}
                for t in trucks
            ],
            'truck_summaries': truck_summaries,
        })

    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        target_date = _parse_date(request.data.get('target_date'))
        rows = request.data.get('rows')
        if not target_date:
            return Response({'detail': 'target_date は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(rows, list):
            return Response({'detail': 'rows は配列で指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

        line_ids = []
        truck_ids = set()
        for row in rows:
            line_id = row.get('order_line_id')
            if line_id:
                line_ids.append(int(line_id))
            for al in row.get('allocations') or []:
                truck_id = al.get('truck_id')
                if truck_id:
                    truck_ids.add(int(truck_id))

        line_qs = OrderLine.objects.select_related('product', 'order').filter(
            id__in=line_ids,
            order__status='OPEN',
            order__customer__customer_code='000196',
        )
        line_map = {line.id: line for line in line_qs}
        truck_map = {t.id: t for t in KubotaSakaiTruck.objects.filter(id__in=list(truck_ids), is_active=True)}

        line_adjustments = defaultdict(list)
        for adj in KubotaSakaiDueAdjustment.objects.filter(order_line_id__in=line_ids):
            line_adjustments[adj.order_line_id].append(adj)

        errors = []
        normalized = []
        for row in rows:
            line_id = int(row.get('order_line_id') or 0)
            line = line_map.get(line_id)
            if not line:
                errors.append({'order_line_id': line_id, 'detail': '対象外の受注明細です。'})
                continue

            available_qty = _line_available_qty_on_date(line, target_date, line_adjustments)
            allocations = row.get('allocations') or []
            if not isinstance(allocations, list):
                errors.append({'order_line_id': line_id, 'detail': 'allocations は配列で指定してください。'})
                continue

            normalized_allocations = []
            total = Decimal('0')
            for al in allocations:
                truck_id = int(al.get('truck_id') or 0)
                qty = _to_decimal(al.get('qty'))
                if qty <= 0:
                    continue
                truck = truck_map.get(truck_id)
                if not truck:
                    errors.append({'order_line_id': line_id, 'detail': f'便が不正です: {truck_id}'})
                    continue
                normalized_allocations.append({'truck_id': truck_id, 'qty': qty})
                total += qty

            if total > available_qty:
                errors.append({'order_line_id': line_id, 'detail': f'割付数量超過: available={available_qty} assigned={total}'})
                continue

            normalized.append({'line_id': line_id, 'allocations': normalized_allocations})

        if errors:
            return Response({'detail': '入力エラーがあります。', 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user if request.user and request.user.is_authenticated else None

        with transaction.atomic():
            KubotaSakaiTripAssignment.objects.filter(order_line_id__in=[n['line_id'] for n in normalized], departure_date=target_date).delete()
            create_items = []
            for row in normalized:
                for al in row['allocations']:
                    create_items.append(
                        KubotaSakaiTripAssignment(
                            order_line_id=row['line_id'],
                            truck_id=al['truck_id'],
                            departure_date=target_date,
                            qty=al['qty'],
                            created_by=user,
                        )
                    )
            if create_items:
                KubotaSakaiTripAssignment.objects.bulk_create(create_items)

            all_today = list(
                KubotaSakaiTripAssignment.objects.select_related('order_line', 'order_line__product', 'truck')
                .filter(departure_date=target_date)
            )
            per_truck = defaultdict(list)
            for item in all_today:
                per_truck[item.truck_id].append(item)

            save_errors = []
            for truck_id, items in per_truck.items():
                truck = items[0].truck
                load_items = [_build_load_item(item.order_line, item.qty) for item in items]
                load = calculate_truck_load(load_items, truck)
                if load['errors']:
                    save_errors.append({'truck_id': truck_id, 'truck_name': truck.name, 'errors': load['errors']})

            if save_errors:
                transaction.set_rollback(True)
                return Response({'detail': '便積載制約エラーがあります。', 'errors': save_errors}, status=status.HTTP_400_BAD_REQUEST)

            _sync_kubota_delivery_backlog_for_date(target_date)

        return Response({'saved_rows': len(normalized), 'saved_allocations': len(create_items)})
