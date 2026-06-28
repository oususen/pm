"""サブ工程計画の保存サービス"""
import logging
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q

from masters.models import BOM, Product, RoutingStep
from production.models_line_backlog import LineBacklog
from production.models_line_gantt_plan import LineGanttPlan
from production.models_plan_change_log import ProductionPlanChangeLog

from .gantt_planning import (
    LineWorkCalendar,
    _load_gantt_start_time_by_line_process,
)

logger = logging.getLogger(__name__)


def _parse_date(val):
    if isinstance(val, str):
        return datetime.strptime(val, '%Y-%m-%d').date()
    return val


def _resolve_target_dates(target_dates):
    resolved = set()
    for raw in target_dates if isinstance(target_dates, list) else []:
        try:
            resolved.add(_parse_date(str(raw)))
        except (TypeError, ValueError):
            continue
    return resolved



def _build_cycle_time_by_product(line_id, process_id, product_ids):
    """
    計画品番のサイクルタイムを取得する。
    連産品親(ST品番)→driver子品番→RoutingStep(output_product=driver).duration_min
    連産品でない場合はrouting.product_idで直接検索。
    代表品（MAX duration_min）のサイクルタイムを使用。
    """
    if not product_ids:
        return {}

    # 連産品のdriver子品番を解決
    driver_map = {}  # {plan_product_id: driver_child_product_id}
    non_coproduct_ids = set()
    boms = (
        BOM.objects.filter(
            parent_product_id__in=product_ids,
            is_coproduct=True,
            is_active=True,
        )
        .prefetch_related('items')
    )
    bom_by_parent = {}
    for bom in boms:
        bom_by_parent[bom.parent_product_id] = bom

    for pid in product_ids:
        bom = bom_by_parent.get(pid)
        if bom:
            driver = bom.items.filter(is_coproduct_driver=True).first()
            if driver and driver.child_product_id:
                driver_map[pid] = driver.child_product_id
                continue
        non_coproduct_ids.add(pid)

    result = {}

    # 連産品: output_product_id=driver子品番で検索
    driver_child_ids = set(driver_map.values())
    if driver_child_ids:
        steps = (
            RoutingStep.objects.filter(
                line_id=line_id,
                process_id=process_id,
                routing__is_active=True,
                output_product_id__in=driver_child_ids,
                time_unit='MINUTE',
            )
            .filter(Q(duration_min__isnull=False) & Q(duration_min__gt=0))
            .select_related('routing')
        )
        best_by_child = {}
        for step in steps:
            child_id = step.output_product_id
            dur = float(step.duration_min or 0)
            prev = best_by_child.get(child_id)
            if not prev or dur > prev['cycle_time']:
                best_by_child[child_id] = {
                    'cycle_time': dur,
                    'step_no': step.step_no or 0,
                    'parallel_count': step.parallel_count or 1,
                    'parallel_group': getattr(step, 'parallel_group', 1) or 1,
                }
        for plan_pid, child_id in driver_map.items():
            if child_id in best_by_child:
                result[plan_pid] = best_by_child[child_id]

    # 非連産品: routing.product_id → output_product_id の順で検索
    if non_coproduct_ids:
        # まず routing.product_id で検索
        steps = (
            RoutingStep.objects.filter(
                line_id=line_id,
                process_id=process_id,
                routing__is_active=True,
                routing__product_id__in=non_coproduct_ids,
                time_unit='MINUTE',
            )
            .filter(Q(duration_min__isnull=False) & Q(duration_min__gt=0))
            .select_related('routing')
        )
        for step in steps:
            routing_product_id = step.routing.product_id
            dur = float(step.duration_min or 0)
            prev = result.get(routing_product_id)
            if not prev or dur > prev['cycle_time']:
                result[routing_product_id] = {
                    'cycle_time': dur,
                    'step_no': step.step_no or 0,
                    'parallel_count': step.parallel_count or 1,
                    'parallel_group': getattr(step, 'parallel_group', 1) or 1,
                }

        # routing.product_idで見つからなかった品番は output_product_id で検索
        remaining = non_coproduct_ids - set(result.keys())
        if remaining:
            steps = (
                RoutingStep.objects.filter(
                    line_id=line_id,
                    process_id=process_id,
                    routing__is_active=True,
                    output_product_id__in=remaining,
                    time_unit='MINUTE',
                )
                .filter(Q(duration_min__isnull=False) & Q(duration_min__gt=0))
            )
            for step in steps:
                pid = step.output_product_id
                dur = float(step.duration_min or 0)
                prev = result.get(pid)
                if not prev or dur > prev['cycle_time']:
                    result[pid] = {
                        'cycle_time': dur,
                        'step_no': step.step_no or 0,
                        'parallel_count': step.parallel_count or 1,
                        'parallel_group': getattr(step, 'parallel_group', 1) or 1,
                    }

    return result


def _align_to_working_start(calendar, target_dt):
    segments = calendar.get_segments(target_dt.date())
    if not segments:
        check_date = target_dt.date()
        for _ in range(31):
            check_date += timedelta(days=1)
            next_segments = calendar.get_segments(check_date)
            if next_segments:
                return next_segments[0][0]
        return target_dt
    for start_dt, end_dt in segments:
        if target_dt <= start_dt:
            return start_dt
        if start_dt <= target_dt < end_dt:
            return target_dt
    check_date = target_dt.date()
    for _ in range(31):
        check_date += timedelta(days=1)
        next_segments = calendar.get_segments(check_date)
        if next_segments:
            return next_segments[0][0]
    return target_dt


def _build_gantt_rows(*, line, process, parsed_entries, product_cache):
    if not parsed_entries:
        return []

    line_id = line.id
    process_id = process.id
    line_code = str(getattr(line, 'line_code', '') or '').strip().upper()
    process_code = str(getattr(process, 'process_code', '') or '').strip().upper()
    start_time_rules = _load_gantt_start_time_by_line_process()
    preferred_start_time = start_time_rules.get((line_code, process_code), time(8, 0))
    calendar = LineWorkCalendar(line)

    product_ids = {item['product_id'] for item in parsed_entries}
    cycle_by_product = _build_cycle_time_by_product(line_id, process_id, product_ids)

    grouped = defaultdict(list)
    for item in parsed_entries:
        grouped[item['plan_date']].append(item)

    gantt_rows = []
    for plan_date in sorted(grouped.keys()):
        day_entries = sorted(grouped[plan_date], key=lambda row: (row['seq'], row['product_id']))
        current_start = _align_to_working_start(
            calendar,
            datetime.combine(plan_date, preferred_start_time),
        )
        for item in day_entries:
            product = product_cache.get(item['product_id'])
            if not product:
                continue

            ct_info = cycle_by_product.get(item['product_id'], {})
            cycle_time_minutes = ct_info.get('cycle_time', 0.0)
            setup_time_minutes = 0.0
            process_number = ct_info.get('step_no', 0)
            parallel_group = ct_info.get('parallel_group', 1)
            parallel_count = ct_info.get('parallel_count', 1)
            total_minutes = float(item['plan_qty']) * cycle_time_minutes + setup_time_minutes
            effective_minutes = total_minutes / max(parallel_count, 1)
            if cycle_time_minutes <= 0 and setup_time_minutes <= 0:
                logger.warning(
                    'sub_process_plan: cycle time unresolved line_id=%s process_id=%s product_id=%s plan_date=%s seq=%s',
                    line_id,
                    process_id,
                    item['product_id'],
                    plan_date,
                    item['seq'],
                )
            start_dt = _align_to_working_start(calendar, current_start)
            end_dt = calendar.add_working_minutes(start_dt, effective_minutes) if effective_minutes > 0 else start_dt

            process_plan_entry = {
                'plan_id': item['plan_id'],
                'process_id': process_id,
                'process_name': process.process_name,
                'process_number': process_number,
                'start_time': start_dt.strftime('%Y-%m-%dT%H:%M:%S'),
                'end_time': end_dt.strftime('%Y-%m-%dT%H:%M:%S'),
                'quantity': float(item['plan_qty']),
                'cycle_time_minutes': cycle_time_minutes,
                'setup_time_minutes': setup_time_minutes,
                'total_minutes_required': round(effective_minutes, 1),
                'parallel_group': parallel_group,
                'parallel_count': parallel_count,
                'transfer_time_minutes': 0.0,
                'output_product_id': product.id,
                'output_product_code': product.product_code,
                'output_product_name': product.product_name,
            }
            gantt_rows.append({
                'plan_id': item['plan_id'],
                'line_id': line_id,
                'product_id': product.id,
                'plan_date': plan_date,
                'plan_qty': item['plan_qty'],
                'sequence_no': item['seq'],
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'processes_plan': [process_plan_entry],
            })
            current_start = end_dt

    return gantt_rows


def _resolve_coproduct_children(parent_product_id, plan_date, cache):
    cache_key = (parent_product_id, plan_date)
    if cache_key in cache:
        return cache[cache_key]

    bom = (
        BOM.objects.filter(
            parent_product_id=parent_product_id,
            is_active=True,
            is_coproduct=True,
            valid_from__lte=plan_date,
        )
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=plan_date))
        .prefetch_related('items')
        .order_by('-valid_from', '-id')
        .first()
    )
    if not bom:
        cache[cache_key] = []
        return cache[cache_key]

    children = []
    for item in bom.items.all():
        if not item.child_product_id:
            continue
        qty_per = Decimal(str(item.quantity or 0))
        if qty_per == 0:
            continue
        children.append({
            'product_id': item.child_product_id,
            'qty_per': qty_per,
        })
    cache[cache_key] = children
    return children


def _expand_backlog_entries_for_coproducts(parsed_entries):
    expanded_map = {}
    coproduct_cache = {}
    for item in parsed_entries:
        children = _resolve_coproduct_children(item['product_id'], item['plan_date'], coproduct_cache)
        if not children:
            key = (item['product_id'], item['plan_date'], item['seq'])
            expanded_map[key] = (expanded_map.get(key, 0) + int(item['plan_qty']))
            continue

        for child in children:
            child_qty = int(round(Decimal(str(item['plan_qty'])) * child['qty_per']))
            if child_qty <= 0:
                continue
            key = (child['product_id'], item['plan_date'], item['seq'])
            expanded_map[key] = expanded_map.get(key, 0) + child_qty
    return [
        {'product_id': product_id, 'plan_date': plan_date, 'plan_qty': plan_qty, 'seq': seq}
        for (product_id, plan_date, seq), plan_qty in expanded_map.items()
        if plan_qty > 0
    ]


def save_sub_process_plan(*, line, process, entries, target_dates=None, change_reason='サブ工程計画入力', change_user=None):
    """
    サブ工程計画を保存する。

    LinePlanは触らない。この工程のLineBacklog(seq>0)とLineGanttPlan(SINGLEPROC_)のみ操作。
    """
    line_id = line.id
    process_id = process.id

    parsed = []
    affected_dates = _resolve_target_dates(target_dates)
    affected_product_ids = set()
    for entry in entries if isinstance(entries, list) else []:
        try:
            product_id = int(entry['product_id'])
            plan_date = _parse_date(str(entry['plan_date']))
            plan_qty = int(entry.get('plan_qty', 0))
            seq = int(entry.get('sequence_no', 1))
        except (KeyError, TypeError, ValueError):
            continue
        affected_dates.add(plan_date)
        if plan_qty <= 0:
            continue
        affected_product_ids.add(product_id)
        parsed.append({'product_id': product_id, 'plan_date': plan_date, 'plan_qty': plan_qty, 'seq': seq})

    if not parsed and not affected_dates:
        raise ValueError('保存対象がありません')

    product_cache = {
        product.id: product
        for product in Product.objects.filter(id__in=affected_product_ids).only('id', 'product_code', 'product_name')
    }
    backlog_entries = _expand_backlog_entries_for_coproducts(parsed)
    backlog_product_ids = {item['product_id'] for item in backlog_entries}
    backlog_product_cache = {
        product.id: product
        for product in Product.objects.filter(id__in=backlog_product_ids).only('id')
    }

    deleted_backlog = 0
    deleted_gantt = 0
    created_backlog = 0
    created_gantt = 0

    with transaction.atomic():
        existing_backlogs = {}
        if affected_dates:
            existing_qs = LineBacklog.objects.filter(
                line_id=line_id,
                process_id=process_id,
                plan_date__in=affected_dates,
                sequence_no__gt=0,
            ).only('product_id', 'plan_date', 'sequence_no', 'plan_qty', 'plan_id')
            for row in existing_qs:
                key = (row.product_id, row.plan_date, row.sequence_no)
                existing_backlogs[key] = {'qty': int(row.plan_qty or 0), 'plan_id': row.plan_id}

            deleted = existing_qs.delete()
            deleted_backlog = deleted[0] if deleted else 0

            deleted = LineGanttPlan.objects.filter(
                plan_id__startswith=f'SINGLEPROC_{line_id}_{process_id}_',
                plan_date__in=affected_dates,
            ).delete()
            deleted_gantt = deleted[0] if deleted else 0

        backlog_creates = []
        saved_backlog_entries = []
        for item in parsed:
            item['plan_id'] = f"SINGLEPROC_{line_id}_{process_id}_{item['product_id']}_{item['plan_date'].strftime('%Y%m%d')}_{item['seq']}"
        for item in backlog_entries:
            product = backlog_product_cache.get(item['product_id'])
            if not product:
                continue
            plan_id = f"SINGLEPROC_{line_id}_{process_id}_{item['product_id']}_{item['plan_date'].strftime('%Y%m%d')}_{item['seq']}"
            saved_backlog_entries.append({
                'product_id': item['product_id'],
                'plan_date': item['plan_date'],
                'plan_qty': item['plan_qty'],
                'seq': item['seq'],
                'plan_id': plan_id,
            })
            backlog_creates.append(LineBacklog(
                plan_date=item['plan_date'],
                process_id=process_id,
                product_id=item['product_id'],
                line_id=line_id,
                sequence_no=item['seq'],
                plan_qty=item['plan_qty'],
                plan_id=plan_id,
            ))

        if backlog_creates:
            LineBacklog.objects.bulk_create(backlog_creates)
            created_backlog = len(backlog_creates)

        gantt_rows = _build_gantt_rows(
            line=line,
            process=process,
            parsed_entries=parsed,
            product_cache=product_cache,
        )
        gantt_creates = [
            LineGanttPlan(
                plan_id=row['plan_id'],
                line_id=row['line_id'],
                product_id=row['product_id'],
                plan_date=row['plan_date'],
                plan_qty=row['plan_qty'],
                sequence_no=row['sequence_no'],
                start_datetime=row['start_datetime'],
                end_datetime=row['end_datetime'],
                processes_plan=row['processes_plan'],
            )
            for row in gantt_rows
        ]
        if gantt_creates:
            LineGanttPlan.objects.bulk_create(gantt_creates)
            created_gantt = len(gantt_creates)

        for item in saved_backlog_entries:
            old_key = (item['product_id'], item['plan_date'], item['seq'])
            old = existing_backlogs.pop(old_key, None)
            before_qty = old['qty'] if old else 0
            if before_qty != item['plan_qty']:
                ProductionPlanChangeLog.objects.create(
                    plan_date=item['plan_date'],
                    product_id=item['product_id'],
                    process_id=process_id,
                    line_id=line_id,
                    sequence_no=item['seq'],
                    plan_id=item['plan_id'],
                    before_qty=before_qty,
                    after_qty=item['plan_qty'],
                    reason=change_reason,
                    changed_by=change_user,
                )

        for (product_id, plan_date, seq), old in existing_backlogs.items():
            if old['qty'] > 0:
                ProductionPlanChangeLog.objects.create(
                    plan_date=plan_date,
                    product_id=product_id,
                    process_id=process_id,
                    line_id=line_id,
                    sequence_no=seq,
                    plan_id=old.get('plan_id', ''),
                    before_qty=old['qty'],
                    after_qty=0,
                    reason=change_reason,
                    changed_by=change_user,
                )

    return {
        'deleted_backlog': deleted_backlog,
        'deleted_gantt': deleted_gantt,
        'created_backlog': created_backlog,
        'created_gantt': created_gantt,
    }
