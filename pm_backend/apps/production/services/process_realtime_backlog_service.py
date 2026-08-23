from datetime import timedelta
from decimal import Decimal

from django.db.models import F

from masters.models import BOM
from orders.utils.calendar_utils import get_business_today
from production.models_line_backlog import LineBacklog
from production.models_process_realtime import ProcessRealtimeRecord
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

    line = getattr(session.process, 'line', None)
    if line:
        LineBacklog.objects.filter(
            line_id=line.id,
            product_id=session.product_id,
            plan_date__range=[session.plan_date, today],
            sequence_no=0,
        ).update(
            stock_qty=F('stock_qty') + delta,
            planned_stock_qty=F('planned_stock_qty') + delta,
            progress_qty=F('progress_qty') + delta,
            planned_progress_qty=F('planned_progress_qty') + delta,
        )

    boms = BOM.objects.filter(
        parent_product_id=session.product_id,
        is_active=True,
        is_coproduct=False,
    ).prefetch_related('items')
    child_product_ids = set()

    for bom in boms:
        for item in bom.items.all():
            child_id = item.child_product_id
            qty_per = item.quantity or 0
            if not child_id or qty_per == 0:
                continue
            child_product_ids.add(int(child_id))

            child_delta = int(round(Decimal(str(delta)) * qty_per))
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


def recalculate_inventory_after_session_change(session_obj):
    if not session_obj:
        return
    plan_date = getattr(session_obj, 'plan_date', None)
    process = getattr(session_obj, 'process', None)
    line_id = getattr(process, 'line_id', None)
    if not plan_date or not line_id:
        return

    end_date = (
        LineBacklog.objects.filter(line_id=line_id)
        .order_by('-plan_date')
        .values_list('plan_date', flat=True)
        .first()
    ) or plan_date

    from production.inventory.inventory_calculator import recalculate_inventory_for_line

    recalculate_inventory_for_line(
        line_id=line_id,
        start_date=plan_date,
        end_date=end_date,
        include_progress=True,
        line_final_only=False,
        guard_cutoff=plan_date - timedelta(days=1),
    )
