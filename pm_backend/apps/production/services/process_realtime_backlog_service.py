from collections import deque
from datetime import timedelta
from decimal import Decimal

from django.db.models import F

from masters.models import BOM, BOMItem, RoutingStep
from masters.services.routing_service import resolve_effective_routing
from orders.utils.calendar_utils import get_business_today
from production.models_line_backlog import LineBacklog
from production.models_process_realtime import ProcessRealtimeRecord
from production.inventory.lead_time_utils import resolve_lead_days_for_step
from production.serializers_process_realtime import _build_session_meta, expand_coproduct_children_production


BACKLOG_DEFAULTS = {
    'order_qty': 0,
    'plan_qty': 0,
    'actual_qty': 0,
    'stock_qty': 0,
    'planned_stock_qty': 0,
    'adjust_qty': 0,
    'scrap_qty': 0,
    'actual_shipment_qty': 0,
}


def _get_or_create_backlog(session_obj, product_id):
    line = getattr(session_obj.process, 'line', None)
    if not line:
        return None
    backlog, _created = LineBacklog.objects.get_or_create(
        line=line,
        process_id=session_obj.process_id,
        product_id=product_id,
        plan_date=session_obj.plan_date,
        sequence_no=0,
        defaults=BACKLOG_DEFAULTS,
    )
    return backlog


def adjust_backlog_actual_for_session(session_obj, delta_qty):
    if not session_obj or not delta_qty:
        return
    if not session_obj.product_id or not session_obj.process_id or not session_obj.plan_date:
        return

    backlog = _get_or_create_backlog(session_obj, session_obj.product_id)
    if not backlog:
        return
    backlog.actual_qty = (backlog.actual_qty or 0) + int(delta_qty)
    backlog.save(update_fields=['actual_qty'])


def adjust_coproduct_children_backlog(session_obj, delta_qty):
    if not session_obj or not delta_qty:
        return
    if not session_obj.product_id or not session_obj.process_id or not session_obj.plan_date:
        return

    coproduct_boms = BOM.objects.filter(
        parent_product_id=session_obj.product_id,
        is_active=True,
        is_coproduct=True,
    ).prefetch_related('items__child_product')

    for bom in coproduct_boms:
        for item in bom.items.select_related('child_product').all():
            child_product = item.child_product
            if not child_product:
                continue
            child_delta = int(round(Decimal(str(delta_qty)) * (item.quantity or 0)))
            if child_delta == 0:
                continue

            backlog = _get_or_create_backlog(session_obj, child_product.id)
            if not backlog:
                continue
            backlog.actual_qty = (backlog.actual_qty or 0) + child_delta
            backlog.save(update_fields=['actual_qty'])


def update_coproduct_children_records(session_obj, new_parent_qty):
    if not session_obj or not session_obj.product_id:
        return

    coproduct_boms = BOM.objects.filter(
        parent_product_id=session_obj.product_id,
        is_active=True,
        is_coproduct=True,
    ).prefetch_related('items__child_product')

    bom_ratio_map = {}
    for bom in coproduct_boms:
        for item in bom.items.select_related('child_product').all():
            if item.child_product_id:
                bom_ratio_map[item.child_product_id] = item.quantity or Decimal('0')

    if not bom_ratio_map:
        return

    child_records = ProcessRealtimeRecord.objects.filter(
        record_type='PRODUCTION',
        event_data__work_session_id=session_obj.id,
        product_id__in=list(bom_ratio_map.keys()),
    )

    for record in child_records:
        ratio = bom_ratio_map.get(record.product_id)
        if ratio is not None:
            record.qty = Decimal(str(new_parent_qty)) * ratio
            record.save(update_fields=['qty'])


def _resolve_session_production_deltas(session_obj, delta_qty):
    if not session_obj or not getattr(session_obj, 'product_id', None) or not delta_qty:
        return []

    coproduct_items = list(
        BOMItem.objects.filter(
            bom__parent_product_id=session_obj.product_id,
            bom__is_active=True,
            bom__is_coproduct=True,
        ).exclude(
            child_product_id__isnull=True,
        )
    )
    if not coproduct_items:
        return [(int(session_obj.product_id), int(delta_qty))]

    results = []
    for item in coproduct_items:
        child_delta = int(round(Decimal(str(delta_qty)) * (item.quantity or 0)))
        if child_delta == 0:
            continue
        results.append((int(item.child_product_id), child_delta))
    return results


def rebuild_session_production_records(session_obj):
    if not session_obj or not session_obj.process_id or not session_obj.product_id:
        return

    ProcessRealtimeRecord.objects.filter(
        record_type='PRODUCTION',
        event_data__work_session_id=session_obj.id,
    ).delete()

    qty_decimal = Decimal(str(session_obj.production_qty or 0))
    event_data = {
        'source': 'MANUAL_RECORD_EDIT',
        'operator_action': 'MANUAL',
        'work_session_id': session_obj.id,
        'is_manual_record_edit': True,
    }
    session_meta = _build_session_meta(session_obj)
    if session_meta:
        event_data['session'] = session_meta

    parent_record = ProcessRealtimeRecord.objects.create(
        process=session_obj.process,
        product=session_obj.product,
        product_code=session_obj.product_code,
        product_name=session_obj.product_name,
        record_type='PRODUCTION',
        qty=qty_decimal,
        equipment_state=None,
        event_data=event_data,
        operator_name=session_obj.operator_name or '',
    )

    expand_coproduct_children_production(
        process=session_obj.process,
        product=session_obj.product,
        parent_qty=qty_decimal,
        plan_date=session_obj.plan_date,
        operator_name=session_obj.operator_name or '',
        parent_record_id=parent_record.id,
        base_event_data=event_data,
        session=session_obj,
        session_issues=session_obj.issue_flags or [],
        skip_backlog=True,
    )


def adjust_backlog_scrap_for_session(session_obj, delta_qty):
    if not session_obj or not delta_qty:
        return
    if not session_obj.product_id or not session_obj.process_id or not session_obj.plan_date:
        return

    backlog = _get_or_create_backlog(session_obj, session_obj.product_id)
    if not backlog:
        return
    backlog.scrap_qty = (backlog.scrap_qty or 0) + int(delta_qty)
    backlog.save(update_fields=['scrap_qty'])


def apply_delta_to_inventory_and_progress(session, delta):
    if not delta or not session.product_id or not session.plan_date:
        return

    today = get_business_today()
    if session.plan_date > today:
        return

    child_product_ids = set()
    line = getattr(session.process, 'line', None)
    for source_product_id, source_delta in _resolve_session_production_deltas(session, delta):
        if line:
            LineBacklog.objects.filter(
                line_id=line.id,
                product_id=source_product_id,
                plan_date__range=[session.plan_date, today],
                sequence_no=0,
            ).update(
                stock_qty=F('stock_qty') + source_delta,
                planned_stock_qty=F('planned_stock_qty') + source_delta,
                progress_qty=F('progress_qty') + source_delta,
                planned_progress_qty=F('planned_progress_qty') + source_delta,
            )

        boms = BOM.objects.filter(
            parent_product_id=source_product_id,
            is_active=True,
            is_coproduct=False,
        ).prefetch_related('items')

        for bom in boms:
            for item in bom.items.all():
                child_id = item.child_product_id
                qty_per = item.quantity or 0
                if not child_id or qty_per == 0:
                    continue
                child_product_ids.add(int(child_id))

                child_delta = int(round(Decimal(str(source_delta)) * qty_per))
                if child_delta == 0:
                    continue

                LineBacklog.objects.filter(
                    product_id=child_id,
                    plan_date__range=[session.plan_date, today],
                    sequence_no=0,
                ).update(
                    stock_qty=F('stock_qty') - child_delta,
                    planned_stock_qty=F('planned_stock_qty') - child_delta,
                )
                LineBacklog.objects.filter(
                    product_id=child_id,
                    plan_date=session.plan_date,
                    sequence_no=0,
                ).update(
                    actual_shipment_qty=F('actual_shipment_qty') + child_delta,
                )

    if child_product_ids:
        recalculate_child_stock_after_record_edit(
            parent_plan_date=session.plan_date,
            today=today,
            child_product_ids=child_product_ids,
        )


def recalculate_child_stock_after_record_edit(parent_plan_date, today, child_product_ids):
    if not parent_plan_date or not today or parent_plan_date > today:
        return
    targets = sorted({int(pid) for pid in (child_product_ids or []) if pid})
    if not targets:
        return

    from masters.models import Calendar, CalendarDay, Line
    from production.inventory.inventory_calculator import (
        _build_demand_map,
        _get_max_parent_bom_lead_time,
        recalculate_planned_stock_qty,
        recalculate_stock_qty,
    )

    for child_id in targets:
        line_ids = list(
            LineBacklog.objects.filter(
                product_id=child_id,
                plan_date__range=[parent_plan_date, today],
                sequence_no=0,
            ).values_list('line_id', flat=True).distinct()
        )
        for line_id in line_ids:
            line_obj = Line.objects.filter(id=line_id).first()
            calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(
                calendar_code='daiso'
            ).values_list('id', flat=True).first()
            workday_cache = {}

            def is_working_day(target_date):
                if not calendar_id:
                    return target_date.weekday() < 5
                if target_date in workday_cache:
                    return workday_cache[target_date]
                cal = CalendarDay.objects.filter(
                    calendar_id=calendar_id,
                    target_date=target_date,
                ).first()
                is_work = cal.is_working_day if cal is not None else target_date.weekday() < 5
                workday_cache[target_date] = is_work
                return is_work

            def get_prev_working_day(target_date):
                prev_date = target_date - timedelta(days=1)
                while not is_working_day(prev_date):
                    prev_date = prev_date - timedelta(days=1)
                return prev_date

            def shift_working_days(target_date, days):
                if not days:
                    return target_date
                if not calendar_id:
                    return target_date + timedelta(days=days)
                step = 1 if days > 0 else -1
                remaining = abs(int(days))
                current = target_date
                while remaining > 0:
                    current = current + timedelta(days=step)
                    if is_working_day(current):
                        remaining -= 1
                return current

            stock_start = get_prev_working_day(get_prev_working_day(parent_plan_date))
            planned_start = shift_working_days(
                parent_plan_date,
                -(_get_max_parent_bom_lead_time(child_id) + 1),
            )
            demand_start = min(stock_start, planned_start)
            demand_map = _build_demand_map(line_id, demand_start, today)

            recalculate_stock_qty(
                line_id,
                child_id,
                stock_start,
                today,
                demand_map=demand_map,
                reference_today=parent_plan_date,
            )
            recalculate_planned_stock_qty(
                line_id,
                child_id,
                planned_start,
                today,
                demand_map=demand_map,
                reference_today=parent_plan_date,
            )


def _resolve_session_recalc_product_ids(session_obj):
    if not session_obj or not getattr(session_obj, 'product_id', None):
        return []

    child_product_ids = list(
        BOMItem.objects.filter(
            bom__parent_product_id=session_obj.product_id,
            bom__is_active=True,
            bom__is_coproduct=True,
        ).exclude(
            child_product_id__isnull=True,
        ).values_list('child_product_id', flat=True).distinct()
    )
    if child_product_ids:
        return sorted({int(pid) for pid in child_product_ids if pid})
    return [int(session_obj.product_id)]


def recalculate_inventory_after_session_change(session_obj):
    if not session_obj:
        return
    plan_date = getattr(session_obj, 'plan_date', None)
    process = getattr(session_obj, 'process', None)
    line_id = getattr(process, 'line_id', None)
    product_ids = _resolve_session_recalc_product_ids(session_obj)
    if not plan_date or not line_id:
        return

    for product_id in product_ids:
        recalculate_inventory_for_product_impact(
            line_id=line_id,
            product_id=product_id,
            plan_date=plan_date,
        )


def _resolve_line_calendar_id(line_id):
    from masters.models import Calendar, Line

    if not line_id:
        return None
    line_obj = Line.objects.filter(id=line_id).only('calendar_id').first()
    return getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(
        calendar_code='daiso'
    ).values_list('id', flat=True).first()


def _resolve_bom_item_line_id(bom_item):
    if getattr(bom_item, 'line_id', None):
        return int(bom_item.line_id)
    process = getattr(bom_item, 'process', None)
    if process and getattr(process, 'line_id', None):
        return int(process.line_id)
    return None


def _shift_working_days_for_line(line_id, target_date, days, line_calendar_cache=None, workday_cache=None):
    from masters.models import CalendarDay

    if not days:
        return target_date

    line_calendar_cache = line_calendar_cache if line_calendar_cache is not None else {}
    workday_cache = workday_cache if workday_cache is not None else {}
    calendar_id = line_calendar_cache.get(line_id)
    if calendar_id is None:
        calendar_id = _resolve_line_calendar_id(line_id)
        line_calendar_cache[line_id] = calendar_id

    def is_working_day(check_date):
        cache_key = (calendar_id, check_date)
        if cache_key in workday_cache:
            return workday_cache[cache_key]
        if not calendar_id:
            result = check_date.weekday() < 5
        else:
            cal = CalendarDay.objects.filter(
                calendar_id=calendar_id,
                target_date=check_date,
            ).first()
            result = cal.is_working_day if cal is not None else check_date.weekday() < 5
        workday_cache[cache_key] = result
        return result

    step = 1 if days > 0 else -1
    remaining = abs(int(days))
    current = target_date
    while remaining > 0:
        current = current + timedelta(days=step)
        if is_working_day(current):
            remaining -= 1
    return current


def _resolve_edge_lead_time_days_for_bom_item(bom_item, reference_date=None, routing_cache=None, step_cache=None):
    step_cache = step_cache if step_cache is not None else {}
    routing_cache = routing_cache if routing_cache is not None else {}

    parent_product_id = getattr(getattr(bom_item, 'bom', None), 'parent_product_id', None)
    child_product_id = getattr(bom_item, 'child_product_id', None)
    process_id = getattr(bom_item, 'process_id', None)
    line_id = _resolve_bom_item_line_id(bom_item)
    if not parent_product_id or not child_product_id:
        return None

    routing_key = (int(parent_product_id), reference_date)
    parent_routing = routing_cache.get(routing_key)
    if routing_key not in routing_cache:
        parent_routing = resolve_effective_routing(parent_product_id, reference=reference_date)
        routing_cache[routing_key] = parent_routing
    if not parent_routing:
        return None

    cache_key = (
        int(parent_product_id),
        int(child_product_id),
        int(process_id) if process_id else None,
        int(line_id) if line_id else None,
        reference_date,
    )
    if cache_key in step_cache:
        step = step_cache[cache_key]
    else:
        step_qs = RoutingStep.objects.filter(
            routing_id=parent_routing.id,
            output_product_id=child_product_id,
        ).select_related('line', 'process')

        if process_id:
            step = step_qs.filter(process_id=process_id).order_by('step_no', 'id').first()
        elif line_id:
            step = step_qs.filter(line_id=line_id).order_by('step_no', 'id').first()
        else:
            step = None
        step_cache[cache_key] = step

    if step is None:
        return None

    return resolve_lead_days_for_step(step)


def _collect_impacted_line_recalc_targets(line_id, product_id, plan_date):
    if not line_id or not product_id or not plan_date:
        if not line_id or not plan_date:
            return {}
        return {
            int(line_id): {
                'start_date': plan_date,
                'product_ids': set(),
            }
        }

    impacted = {
        int(line_id): {
            'start_date': plan_date,
            'product_ids': {int(product_id)},
        }
    }
    earliest_product_date = {int(product_id): plan_date}
    queue = deque([(int(product_id), plan_date)])
    line_calendar_cache = {}
    workday_cache = {}
    routing_cache = {}
    step_cache = {}

    while queue:
        child_product_id, child_start_date = queue.popleft()
        item_rows = BOMItem.objects.filter(
            child_product_id=child_product_id,
            bom__is_active=True,
            bom__is_coproduct=False,
        ).select_related('bom', 'process')

        for item in item_rows:
            parent_product_id = getattr(item.bom, 'parent_product_id', None)
            if not parent_product_id:
                continue
            parent_line_id = _resolve_bom_item_line_id(item)
            if not parent_line_id:
                continue
            lead_days = _resolve_edge_lead_time_days_for_bom_item(
                item,
                reference_date=child_start_date,
                routing_cache=routing_cache,
                step_cache=step_cache,
            )
            if lead_days is None:
                continue

            parent_start = _shift_working_days_for_line(
                parent_line_id,
                child_start_date,
                -lead_days,
                line_calendar_cache=line_calendar_cache,
                workday_cache=workday_cache,
            )

            line_target = impacted.setdefault(
                int(parent_line_id),
                {
                    'start_date': parent_start,
                    'product_ids': set(),
                }
            )
            if parent_start < line_target['start_date']:
                line_target['start_date'] = parent_start
            line_target['product_ids'].add(int(parent_product_id))

            prev_product_start = earliest_product_date.get(int(parent_product_id))
            if prev_product_start is None or parent_start < prev_product_start:
                earliest_product_date[int(parent_product_id)] = parent_start
                queue.append((int(parent_product_id), parent_start))

    return impacted


def recalculate_inventory_for_product_impact(*, line_id, product_id, plan_date):
    if not line_id or not plan_date:
        return

    impacted_targets = _collect_impacted_line_recalc_targets(line_id, product_id, plan_date)
    from production.inventory.inventory_calculator import recalculate_inventory_for_line

    for target_line_id, target in sorted(
        impacted_targets.items(),
        key=lambda x: (x[1]['start_date'], x[0]),
    ):
        start_date = target['start_date']
        product_ids = sorted(int(pid) for pid in target.get('product_ids', set()) if pid)
        end_qs = LineBacklog.objects.filter(line_id=target_line_id)
        if product_ids:
            end_qs = end_qs.filter(product_id__in=product_ids)
        end_date = (
            end_qs
            .order_by('-plan_date')
            .values_list('plan_date', flat=True)
            .first()
        ) or start_date

        recalculate_inventory_for_line(
            line_id=target_line_id,
            start_date=start_date,
            end_date=end_date,
            include_progress=True,
            line_final_only=False,
            product_ids=product_ids or None,
        )
