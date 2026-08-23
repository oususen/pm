"""LineGanttPlanViewSet の構造変更系サービス"""
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from masters.models import Line, Process, Product, RoutingStep
from orders.utils.calendar_utils import DAY_BOUNDARY_HOUR
from production.models_line_backlog import LineBacklog
from production.models_line_gantt_plan import LineGanttPlan
from production.models_plan_change_log import ProductionPlanChangeLog
from production.models_production import ProductionOrder


def manual_add(viewset, request, **deps):
    """
    工程ガントに手動バーを1件追加する。
    期待payload: { line_id, process_id, output_product_id, start_time, end_time, quantity, process_number? }
    """
    try:
        with transaction.atomic():
            created = create_manual_gantt_plan(
                line_id=request.data.get('line_id'),
                process_id=request.data.get('process_id'),
                output_product_id=request.data.get('output_product_id'),
                start_time=request.data.get('start_time'),
                end_time=request.data.get('end_time'),
                quantity_raw=request.data.get('quantity'),
                process_number_raw=request.data.get('process_number'),
            )
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    serializer = viewset.get_serializer(created)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


def bulk_structure_save(viewset, request, **deps):
    creates = request.data.get('creates') or []
    deletes = request.data.get('deletes') or []
    if not isinstance(creates, list) or not isinstance(deletes, list):
        return Response({'detail': 'creates と deletes は配列で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
    if not creates and not deletes:
        return Response({'detail': '保存対象がありません'}, status=status.HTTP_400_BAD_REQUEST)

    change_user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
    created_items = []
    deleted_count = 0
    try:
        with transaction.atomic():
            for create_item in creates:
                created_items.append(create_manual_gantt_plan(
                    line_id=create_item.get('line_id'),
                    process_id=create_item.get('process_id'),
                    output_product_id=create_item.get('output_product_id'),
                    start_time=create_item.get('start_time'),
                    end_time=create_item.get('end_time'),
                    quantity_raw=create_item.get('quantity'),
                    process_number_raw=create_item.get('process_number'),
                ))
            for delete_item in deletes:
                remove_gantt_process_entry(
                    plan_id=delete_item.get('plan_id'),
                    process_id=delete_item.get('process_id'),
                    output_product_id=delete_item.get('output_product_id'),
                    change_user=change_user,
                )
                deleted_count += 1
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except LookupError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)

    serializer = viewset.get_serializer(created_items, many=True)
    return Response({
        'created': len(created_items),
        'deleted': deleted_count,
        'created_items': serializer.data,
    })


def remove_process(viewset, request, **deps):
    """
    指定した1プロセスのガントバーを削除する。
    processes_plan から対象 process_id エントリのみ除去し、
    対応する LineBacklog(seq>0) も削除する。
    processes_plan が空になった場合は LineGanttPlan ごと削除。
    期待payload: { plan_id, process_id, output_product_id? }
    """
    change_user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
    try:
        with transaction.atomic():
            result = remove_gantt_process_entry(
                plan_id=request.data.get('plan_id'),
                process_id=request.data.get('process_id'),
                output_product_id=request.data.get('output_product_id'),
                change_user=change_user,
            )
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except LookupError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)

    return Response(result)


def parse_gantt_datetime_value(value):
    if not value:
        return None
    try:
        raw = str(value).strip()
        if raw.endswith('Z'):
            raw = raw[:-1] + '+00:00'
        dt = datetime.fromisoformat(raw)
    except Exception:
        return None
    if getattr(dt, 'tzinfo', None) is not None:
        try:
            dt = timezone.localtime(dt).replace(tzinfo=None)
        except Exception:
            dt = dt.replace(tzinfo=None)
    return dt


def create_manual_gantt_plan(*, line_id, process_id, output_product_id, start_time, end_time, quantity_raw, process_number_raw=None):
    line_id, process_id, output_product_id, quantity, start_dt, end_dt = normalize_manual_plan_inputs(
        line_id=line_id,
        process_id=process_id,
        output_product_id=output_product_id,
        start_time=start_time,
        end_time=end_time,
        quantity_raw=quantity_raw,
    )
    line, process, output_product, routing_step = resolve_manual_plan_context(
        line_id=line_id,
        process_id=process_id,
        output_product_id=output_product_id,
    )
    process_number = resolve_process_number(process_number_raw, routing_step)
    parallel_group = int(routing_step.parallel_group) if routing_step and routing_step.parallel_group else 1
    parallel_count = int(routing_step.parallel_count) if routing_step and routing_step.parallel_count else 1
    duration_minutes = max((end_dt - start_dt).total_seconds() / 60.0, 0.0)

    plan_date_anchor = start_dt if start_dt.hour >= DAY_BOUNDARY_HOUR else (start_dt - timedelta(days=1))
    plan_date = plan_date_anchor.date()
    plan_id = build_manual_plan_id(line_id=line_id, output_product_id=output_product_id, start_dt=start_dt)
    process_plan = build_manual_process_plan_entry(
        plan_id=plan_id,
        process=process,
        output_product=output_product,
        process_number=process_number,
        start_dt=start_dt,
        end_dt=end_dt,
        quantity=quantity,
        duration_minutes=duration_minutes,
        parallel_group=parallel_group,
        parallel_count=parallel_count,
    )

    return LineGanttPlan.objects.create(
        plan_id=plan_id,
        line_id=line.id,
        product_id=output_product.id,
        plan_date=plan_date,
        plan_qty=quantity,
        sequence_no=None,
        start_datetime=start_dt,
        end_datetime=end_dt,
        processes_plan=[process_plan],
    )


def normalize_manual_plan_inputs(*, line_id, process_id, output_product_id, start_time, end_time, quantity_raw):
    try:
        line_id = int(line_id)
        process_id = int(process_id)
        output_product_id = int(output_product_id)
    except (TypeError, ValueError):
        raise ValueError('line_id, process_id, output_product_id must be numeric')

    try:
        quantity = Decimal(str(quantity_raw)).quantize(Decimal('0.001'))
    except Exception:
        raise ValueError('quantity is invalid')
    if quantity <= 0:
        raise ValueError('quantity must be greater than 0')

    start_dt = parse_gantt_datetime_value(start_time)
    end_dt = parse_gantt_datetime_value(end_time)
    if not start_dt or not end_dt:
        raise ValueError('start_time and end_time must be ISO datetime')
    if end_dt <= start_dt:
        raise ValueError('end_time must be after start_time')

    return line_id, process_id, output_product_id, quantity, start_dt, end_dt


def resolve_manual_plan_context(*, line_id, process_id, output_product_id):
    line = Line.objects.filter(id=line_id).first()
    process = Process.objects.filter(id=process_id).first()
    output_product = Product.objects.filter(id=output_product_id).first()
    if not line or not process or not output_product:
        raise ValueError('line/process/product not found')

    routing_step = (
        RoutingStep.objects
        .filter(line_id=line_id, process_id=process_id)
        .filter(Q(output_product_id=output_product_id) | Q(output_product_id__isnull=True))
        .order_by('step_no', 'parallel_group')
        .first()
    )
    return line, process, output_product, routing_step


def resolve_process_number(process_number_raw, routing_step):
    try:
        process_number = int(process_number_raw) if process_number_raw not in [None, ''] else None
    except (TypeError, ValueError):
        process_number = None
    if process_number is None:
        process_number = int(routing_step.step_no) if routing_step and routing_step.step_no is not None else 0
    return process_number


def build_manual_plan_id(*, line_id, output_product_id, start_dt):
    return (
        f"MANUAL_{line_id}_{output_product_id}_"
        f"{start_dt.strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
    )


def build_manual_process_plan_entry(*, plan_id, process, output_product, process_number, start_dt, end_dt, quantity, duration_minutes, parallel_group, parallel_count):
    return {
        'plan_id': plan_id,
        'process_id': process.id,
        'process_name': process.process_name,
        'process_number': process_number,
        'start_time': start_dt.strftime('%Y-%m-%dT%H:%M:%S'),
        'end_time': end_dt.strftime('%Y-%m-%dT%H:%M:%S'),
        'quantity': float(quantity),
        'cycle_time_minutes': 0.0,
        'setup_time_minutes': 0.0,
        'total_minutes_required': round(duration_minutes, 1),
        'parallel_group': parallel_group,
        'parallel_count': parallel_count,
        'transfer_time_minutes': 0.0,
        'output_product_id': output_product.id,
        'output_product_code': output_product.product_code,
        'output_product_name': output_product.product_name,
    }


def remove_gantt_process_entry(*, plan_id, process_id, output_product_id=None, change_user=None):
    plan_id, process_id, output_product_id = normalize_remove_process_inputs(
        plan_id=plan_id,
        process_id=process_id,
        output_product_id=output_product_id,
    )

    plan = LineGanttPlan.objects.filter(plan_id=plan_id).first()
    if not plan or not plan.processes_plan:
        raise LookupError('対象の計画が見つかりません')

    remaining, removed_proc = split_remaining_and_removed_process(
        processes_plan=plan.processes_plan,
        process_id=process_id,
        output_product_id=output_product_id,
    )
    if removed_proc is None:
        raise LookupError('対象プロセスが見つかりません')

    backlog_filter = {'plan_id': plan_id, 'process_id': process_id, 'sequence_no__gt': 0}
    if output_product_id is not None:
        backlog_filter['product_id'] = output_product_id
    backlog_qs = LineBacklog.objects.filter(**backlog_filter)
    backlog_rows = list(backlog_qs)
    backlog_qs.delete()

    if remaining:
        plan_start, plan_end = recalculate_plan_datetimes(remaining)
        if plan_start:
            plan.start_datetime = plan_start
        if plan_end:
            plan.end_datetime = plan_end
        plan.processes_plan = remaining
        plan.save()
    else:
        ProductionOrder.objects.filter(order_no=plan_id).delete()
        plan.delete()

    create_process_removal_change_logs(
        plan=plan,
        plan_id=plan_id,
        process_id=process_id,
        output_product_id=output_product_id,
        removed_proc=removed_proc,
        backlog_rows=backlog_rows,
        change_user=change_user,
    )
    return {'deleted': True, 'plan_removed': not remaining}


def normalize_remove_process_inputs(*, plan_id, process_id, output_product_id):
    if not plan_id or not process_id:
        raise ValueError('plan_id と process_id は必須です')
    try:
        process_id = int(process_id)
    except Exception:
        raise ValueError('process_id が不正です')

    if output_product_id in [None, '']:
        output_product_id = None
    else:
        try:
            output_product_id = int(output_product_id)
        except Exception:
            output_product_id = None
    return plan_id, process_id, output_product_id


def split_remaining_and_removed_process(*, processes_plan, process_id, output_product_id):
    original = list(processes_plan)
    remaining = []
    removed_proc = None
    for proc in original:
        if removed_proc is None and str(proc.get('process_id')) == str(process_id):
            proc_out = proc.get('output_product_id')
            if output_product_id is not None and str(proc_out) != str(output_product_id):
                remaining.append(proc)
            else:
                removed_proc = proc
        else:
            remaining.append(proc)
    return remaining, removed_proc


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


def create_process_removal_change_logs(*, plan, plan_id, process_id, output_product_id, removed_proc, backlog_rows, change_user):
    change_reason = '工程ガントバー削除'
    before_qty = 0
    try:
        before_qty = int(Decimal(str(removed_proc.get('quantity') or 0)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except Exception:
        pass

    if backlog_rows:
        for row in backlog_rows:
            row_qty = int(row.plan_qty or 0)
            if row_qty == 0:
                continue
            ProductionPlanChangeLog.objects.create(
                plan_date=row.plan_date,
                product_id=row.product_id,
                process_id=row.process_id,
                line_id=row.line_id,
                sequence_no=row.sequence_no,
                plan_id=row.plan_id,
                before_qty=row_qty,
                after_qty=0,
                reason=change_reason,
                changed_by=change_user,
            )
        return

    if before_qty == 0:
        return

    resolved_product_id = output_product_id or removed_proc.get('output_product_id')
    try:
        resolved_product_id = int(resolved_product_id)
    except Exception:
        resolved_product_id = None

    if resolved_product_id:
        ProductionPlanChangeLog.objects.create(
            plan_date=plan.plan_date,
            product_id=resolved_product_id,
            process_id=process_id,
            line_id=plan.line_id,
            sequence_no=plan.sequence_no,
            plan_id=plan_id,
            before_qty=before_qty,
            after_qty=0,
            reason=change_reason,
            changed_by=change_user,
        )
