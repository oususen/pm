"""LineGanttPlanViewSet のスケジュール調整系サービス"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from production.models_line_backlog import LineBacklog
from production.models_line_gantt_plan import LineGanttPlan
from production.models_plan_change_log import ProductionPlanChangeLog


def bulk_update(viewset, request, **deps):
    """
    ガントのドラッグ調整結果を一括保存する。
    期待payload: [{ plan_id, process_id, output_product_id?, start_time?, end_time?, quantity? }, ...]
    """
    updates = request.data
    if not isinstance(updates, list) or not updates:
        return Response({'detail': 'updates must be a non-empty list'}, status=status.HTTP_400_BAD_REQUEST)

    updated_count = 0
    change_log_count = 0
    change_user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
    change_reason = '工程ガント数量編集'

    with transaction.atomic():
        for raw_update in updates:
            normalized = normalize_single_update(raw_update)
            if normalized is None:
                continue

            plan = LineGanttPlan.objects.filter(plan_id=normalized['plan_id']).first()
            if not plan or not plan.processes_plan:
                continue

            update_result = apply_process_schedule_update(plan, normalized)
            if not update_result['changed']:
                continue

            updated_count += 1
            plan_start, plan_end = recalculate_plan_datetimes(update_result['processes_plan'])
            if plan_start:
                plan.start_datetime = plan_start
            if plan_end:
                plan.end_datetime = plan_end
            plan.processes_plan = update_result['processes_plan']
            plan.save()

            if not update_result['quantity_changed']:
                continue

            quantity_change_logs = sync_backlog_quantity_for_gantt_update(
                plan=plan,
                process_id=normalized['process_id'],
                matched_output_product_id=update_result['matched_output_product_id'],
                plan_id=normalized['plan_id'],
                quantity_int_value=normalized['quantity_int_value'],
                before_quantity_value=update_result['before_quantity_value'],
                change_user=change_user,
                change_reason=change_reason,
            )
            change_log_count += quantity_change_logs

    return Response({'updated': updated_count, 'change_logs': change_log_count})


def normalize_single_update(update):
    if not isinstance(update, dict):
        return None

    plan_id = update.get('plan_id')
    process_id = update.get('process_id')
    if not plan_id or not process_id:
        return None

    try:
        process_id = int(process_id)
    except Exception:
        return None

    output_product_id = update.get('output_product_id')
    if output_product_id in [None, '']:
        output_product_id = None
    else:
        try:
            output_product_id = int(output_product_id)
        except Exception:
            output_product_id = None

    has_quantity = 'quantity' in update
    quantity_int_value = None
    if has_quantity:
        try:
            quantity_value = Decimal(str(update.get('quantity')))
            if quantity_value < 0:
                has_quantity = False
            else:
                quantity_int_value = int(quantity_value.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        except Exception:
            has_quantity = False

    return {
        'plan_id': plan_id,
        'process_id': process_id,
        'output_product_id': output_product_id,
        'start_time': update.get('start_time'),
        'end_time': update.get('end_time'),
        'has_quantity': has_quantity,
        'quantity_int_value': quantity_int_value,
    }


def apply_process_schedule_update(plan, normalized):
    processes_plan = list(plan.processes_plan)
    changed = False
    matched_output_product_id = None
    quantity_changed = False
    before_quantity_value = None

    for proc in processes_plan:
        if str(proc.get('process_id')) != str(normalized['process_id']):
            continue

        proc_output_product_id = proc.get('output_product_id')
        if normalized['output_product_id'] is not None and str(proc_output_product_id) != str(normalized['output_product_id']):
            continue

        matched_output_product_id = proc_output_product_id
        if normalized['start_time']:
            proc['start_time'] = normalized['start_time']
            changed = True
        if normalized['end_time']:
            proc['end_time'] = normalized['end_time']
            changed = True
        if normalized['has_quantity'] and normalized['quantity_int_value'] is not None:
            before_qty = normalize_process_quantity(proc.get('quantity'))
            if before_qty != normalized['quantity_int_value']:
                proc['quantity'] = normalized['quantity_int_value']
                changed = True
                quantity_changed = True
                before_quantity_value = before_qty
        break

    return {
        'processes_plan': processes_plan,
        'changed': changed,
        'matched_output_product_id': matched_output_product_id,
        'quantity_changed': quantity_changed,
        'before_quantity_value': before_quantity_value,
    }


def normalize_process_quantity(value):
    try:
        return int(Decimal(str(value or 0)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except Exception:
        return 0


def recalculate_plan_datetimes(processes_plan):
    starts = []
    ends = []
    for proc in processes_plan:
        try:
            starts.append(datetime.fromisoformat(proc['start_time']))
            ends.append(datetime.fromisoformat(proc['end_time']))
        except Exception:
            continue
    return (min(starts) if starts else None, max(ends) if ends else None)


def sync_backlog_quantity_for_gantt_update(*, plan, process_id, matched_output_product_id, plan_id, quantity_int_value, before_quantity_value, change_user, change_reason):
    if quantity_int_value is None or not matched_output_product_id:
        return 0

    try:
        matched_output_product_id = int(matched_output_product_id)
    except Exception:
        return 0

    backlog_qs = LineBacklog.objects.filter(
        line_id=plan.line_id,
        process_id=process_id,
        product_id=matched_output_product_id,
        plan_id=plan_id,
    )
    backlog_rows = list(backlog_qs)
    if backlog_rows:
        backlog_qs.update(plan_qty=quantity_int_value)
        return create_quantity_change_logs(
            backlog_rows=backlog_rows,
            fallback_plan=None,
            process_id=process_id,
            product_id=matched_output_product_id,
            before_quantity_value=before_quantity_value,
            after_quantity_value=quantity_int_value,
            plan_id=plan_id,
            change_user=change_user,
            change_reason=change_reason,
        )

    return create_quantity_change_logs(
        backlog_rows=[],
        fallback_plan=plan,
        process_id=process_id,
        product_id=matched_output_product_id,
        before_quantity_value=before_quantity_value,
        after_quantity_value=quantity_int_value,
        plan_id=plan_id,
        change_user=change_user,
        change_reason=change_reason,
    )


def create_quantity_change_logs(*, backlog_rows, fallback_plan, process_id, product_id, before_quantity_value, after_quantity_value, plan_id, change_user, change_reason):
    created_count = 0
    if backlog_rows:
        for row in backlog_rows:
            before_qty = int(row.plan_qty or 0)
            if before_qty == after_quantity_value:
                continue
            ProductionPlanChangeLog.objects.create(
                plan_date=row.plan_date,
                product_id=row.product_id,
                process_id=row.process_id,
                line_id=row.line_id,
                sequence_no=row.sequence_no,
                plan_id=row.plan_id,
                before_qty=before_qty,
                after_qty=after_quantity_value,
                reason=change_reason,
                changed_by=change_user,
            )
            created_count += 1
        return created_count

    if fallback_plan is None or before_quantity_value is None:
        return 0

    ProductionPlanChangeLog.objects.create(
        plan_date=fallback_plan.plan_date,
        product_id=product_id,
        process_id=process_id,
        line_id=fallback_plan.line_id,
        sequence_no=fallback_plan.sequence_no,
        plan_id=plan_id,
        before_qty=before_quantity_value,
        after_qty=after_quantity_value,
        reason=change_reason,
        changed_by=change_user,
    )
    return 1
