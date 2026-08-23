"""LineGanttPlanViewSet の生成系サービス"""
from datetime import datetime

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from production.models_line_gantt_plan import LineGanttPlan
from production.services.gantt_planning import generate_line_gantt_plans


def generate(viewset, request, **deps):
    logger = deps.get('logger')

    line_id = request.data.get('line_id')
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')
    clear_existing = bool(request.data.get('clear_existing'))
    final_process_start_time = request.data.get('final_process_start_time')
    adjust_to_break_end = request.data.get('adjust_to_break_end', False)

    if logger:
        logger.info(
            'line_gantt_plans.generate: line_id=%s start=%s end=%s clear=%s final_time=%s adjust=%s',
            line_id, start_date, end_date, clear_existing, final_process_start_time, adjust_to_break_end,
        )

    normalized = normalize_generate_payload(
        line_id=line_id,
        start_date=start_date,
        end_date=end_date,
        clear_existing=clear_existing,
        final_process_start_time=final_process_start_time,
        adjust_to_break_end=adjust_to_break_end,
    )
    if isinstance(normalized, Response):
        return normalized

    plans = generate_line_gantt_plans(
        normalized['line_id'],
        normalized['start_date'],
        normalized['end_date'],
        clear_existing=normalized['clear_existing'],
        final_process_start_time=normalized['final_process_start_time'],
        adjust_to_break_end=normalized['adjust_to_break_end'],
    )
    if logger:
        logger.info('line_gantt_plans.generate: plans=%s', len(plans))

    with transaction.atomic():
        upserted = upsert_generated_gantt_plans(plans)
        if normalized['clear_existing']:
            deleted_count = clear_stale_generated_gantt_plans(
                line_id=normalized['line_id'],
                start_date=normalized['start_date'],
                end_date=normalized['end_date'],
                plans=plans,
            )
            if logger:
                logger.info('line_gantt_plans.generate: cleared=%s', deleted_count)

    serializer = viewset.get_serializer(upserted, many=True)
    return Response(serializer.data)


def normalize_generate_payload(*, line_id, start_date, end_date, clear_existing, final_process_start_time, adjust_to_break_end):
    if not line_id:
        return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not start_date or not end_date:
        return Response({'detail': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        line_id = int(line_id)
    except (TypeError, ValueError):
        return Response({'detail': 'line_id must be numeric'}, status=status.HTTP_400_BAD_REQUEST)

    return {
        'line_id': line_id,
        'start_date': start_date,
        'end_date': end_date,
        'clear_existing': clear_existing,
        'final_process_start_time': final_process_start_time,
        'adjust_to_break_end': adjust_to_break_end,
    }


def upsert_generated_gantt_plans(plans):
    upserted = []
    for plan in plans:
        obj, _ = LineGanttPlan.objects.update_or_create(
            plan_id=plan['plan_id'],
            defaults=build_gantt_plan_defaults(plan),
        )
        upserted.append(obj)
    return upserted


def build_gantt_plan_defaults(plan):
    return {
        'line_id': plan['line_id'],
        'product_id': plan['product_id'],
        'plan_date': plan['plan_date'],
        'plan_qty': plan['plan_qty'],
        'sequence_no': plan['sequence_no'],
        'start_datetime': plan['start_datetime'],
        'end_datetime': plan['end_datetime'],
        'processes_plan': plan['processes_plan'],
    }


def clear_stale_generated_gantt_plans(*, line_id, start_date, end_date, plans):
    start_dt = parse_generate_date(start_date)
    end_dt = parse_generate_date(end_date)

    qs = LineGanttPlan.objects.filter(line_id=line_id)
    if start_dt:
        qs = qs.filter(plan_date__gte=start_dt)
    if end_dt:
        qs = qs.filter(plan_date__lte=end_dt)

    plan_ids = [plan['plan_id'] for plan in plans]
    if plan_ids:
        qs = qs.exclude(plan_id__in=plan_ids)

    qs = qs.exclude(plan_id__startswith='MANUAL_').exclude(plan_id__startswith='SINGLEPROC_')
    deleted_count, _ = qs.delete()
    return deleted_count


def parse_generate_date(value):
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except Exception:
        return None
