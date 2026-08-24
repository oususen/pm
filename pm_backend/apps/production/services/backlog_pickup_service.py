"""LineBacklogViewSet の取り込み・展開系サービス"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response

from masters.models import (
    BOM,
    BOMItem,
    Calendar,
    CalendarDay,
    KubotaSakaiTruck,
    Line,
    Process,
    ProcessCycleTime,
    Product,
    RoutingStep,
    Supplier,
)
from masters.services.routing_service import (
    build_effective_routing_q,
    build_effective_routing_range_q,
    normalize_routing_reference_datetime,
)
from production.inventory.lead_time_utils import resolve_lead_days_for_step
from production.inventory.trace_debug import trace_log
from production.models import LineDemand
from production.models_line_backlog import LineBacklog
from production.models_line_gantt_plan import LineGanttPlan
from production.models_line_plan import LinePlan
from production.services.recalc_start_date import (
    resolve_inventory_effective_start_date,
    resolve_product_recalc_start_date,
)
from purchase.process_resolver import (
    is_outsource_process,
    resolve_purchase_line as resolve_supplier_purchase_line,
    resolve_supplier_process,
)
from shipping.services.email_service import EmailService

logger = logging.getLogger(__name__)


def _resolve_admin_notification_emails():
    User = get_user_model()
    emails = set(
        User.objects.filter(is_active=True, smtp_config__is_active=True, smtp_config__is_admin=True)
        .exclude(email='')
        .values_list('email', flat=True)
    )
    return sorted(emails)


def _notify_backlog_process_resolution_failure(details):
    if not details:
        return

    first = details[0]
    subject = f"[進度空行補完エラー] 工程未解決 {first['line_code']} {first['product_code']}"
    body_lines = [
        '進度表示用空行補完で工程を解決できなかったため、処理を中断しました。',
        '',
    ]
    for detail in details[:50]:
        body_lines.append(
            f"日付: {detail['plan_date']} / ライン: {detail['line_code']} / "
            f"品番: {detail['product_code']} / 理由: {detail['reason']}"
        )
    if len(details) > 50:
        body_lines.append(f"... 他 {len(details) - 50} 件")
    body = '\n'.join(body_lines)

    logger.error(body)

    to_emails = _resolve_admin_notification_emails()
    if not to_emails:
        logger.warning('進度空行補完の工程未解決メール通知をスキップ: 管理者メールアドレスが見つかりません')
        return

    result = EmailService().send_plain_email(
        to_emails=to_emails,
        subject=subject,
        body=body,
    )
    if not result.get('success'):
        logger.warning('進度空行補完の工程未解決メール通知に失敗: %s', result.get('message'))

def seed_progress_backlogs_from_demand(viewset, request, **deps):
    self = viewset
    _parse_optional_date = deps.get('parse_optional_date')
    _parse_product_ids = deps.get('parse_product_ids')
    INVALID_SEQUENCE_SORT_VALUE = deps.get('invalid_sequence_sort_value')
    FLOOR_SHIPPING_PM_SEQUENCE_THRESHOLD = deps.get('floor_shipping_pm_sequence_threshold')
    _is_floor_shipping_delivery_line = deps.get('is_floor_shipping_delivery_line')
    """
    進度表示用に、LineDemand から LineBacklog の空行(sequence_no=0)を補完する。
    - 需要(order_qty/demand_qty_plan)は設定しない
    - 既存行があるキーは作成しない
    """
    start_dt = _parse_optional_date(request.data.get('start_date'))
    end_dt = _parse_optional_date(request.data.get('end_date'))
    if not start_dt or not end_dt:
        return Response({'detail': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)
    if start_dt > end_dt:
        return Response({'detail': 'start_date must be <= end_date'}, status=status.HTTP_400_BAD_REQUEST)
    
    line_search = str(request.data.get('line_search') or '').strip()
    process_search = str(request.data.get('process_search') or '').strip()
    product_search = str(request.data.get('product_search') or '').strip()
    
    demand_qs = LineDemand.objects.filter(
        plan_date__gte=start_dt,
        plan_date__lte=end_dt,
        product_id__isnull=False,
        line_id__isnull=False,
    )
    
    if line_search:
        demand_qs = demand_qs.filter(
            Q(line__line_code__iexact=line_search) | Q(line__line_name__icontains=line_search)
        )
    if product_search:
        demand_qs = demand_qs.filter(
            Q(product__product_code__icontains=product_search) |
            Q(product__product_name__icontains=product_search) |
            Q(product_code__icontains=product_search)
        )
    if process_search:
        process_q = (
            Q(routing_step__process__process_code__iexact=process_search) |
            Q(routing_step__process__process_name__icontains=process_search)
        )
        lower_kw = process_search.lower()
        if lower_kw in {'purchase', '購買'}:
            process_q = process_q | Q(line__line_type='PURCHASE')
        demand_qs = demand_qs.filter(process_q)
    
    demand_rows = list(
        demand_qs.values(
            'line_id',
            'product_id',
            'plan_date',
            'routing_step__process_id',
            'line__line_code',
            'product__product_code',
            'product_code',
            'line__line_type',
        ).distinct()
    )
    if not demand_rows:
        return Response({'created': 0, 'candidates': 0, 'skipped_no_process': 0})

    candidate_keys = set()
    skipped_no_process = 0
    unresolved_details = []
    for row in demand_rows:
        line_id = row.get('line_id')
        product_id = row.get('product_id')
        plan_date = row.get('plan_date')
        process_id = row.get('routing_step__process_id')

        if line_id and product_id and plan_date and not process_id:
            unresolved_details.append({
                'plan_date': plan_date.isoformat() if hasattr(plan_date, 'isoformat') else str(plan_date),
                'line_code': row.get('line__line_code') or str(line_id),
                'product_code': row.get('product__product_code') or row.get('product_code') or str(product_id),
                'reason': 'LineDemand.routing_step.process 未設定',
            })
            continue

        if not line_id or not product_id or not plan_date or not process_id:
            skipped_no_process += 1
            continue
        candidate_keys.add((line_id, process_id, product_id, plan_date))

    if unresolved_details:
        _notify_backlog_process_resolution_failure(unresolved_details)
        return Response(
            {
                'detail': '進度表示用空行補完で工程を解決できません。管理者に連絡してください。',
                'code': 'BACKLOG_PROCESS_MISSING',
                'errors': unresolved_details,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not candidate_keys:
        return Response({'created': 0, 'candidates': 0, 'skipped_no_process': skipped_no_process})
    
    line_ids = {k[0] for k in candidate_keys}
    process_ids = {k[1] for k in candidate_keys}
    product_ids = {k[2] for k in candidate_keys}
    existing_keys = set(
        LineBacklog.objects.filter(
            line_id__in=line_ids,
            process_id__in=process_ids,
            product_id__in=product_ids,
            plan_date__gte=start_dt,
            plan_date__lte=end_dt,
            sequence_no=0,
        ).values_list('line_id', 'process_id', 'product_id', 'plan_date')
    )
    
    to_create = []
    for line_id, process_id, product_id, plan_date in sorted(candidate_keys):
        if (line_id, process_id, product_id, plan_date) in existing_keys:
            continue
        to_create.append(LineBacklog(
            plan_date=plan_date,
            process_id=process_id,
            product_id=product_id,
            line_id=line_id,
            sequence_no=0,
            order_qty=0,
            demand_qty_plan=0,
            plan_qty=0,
            actual_qty=0,
        ))
    
    if to_create:
        LineBacklog.objects.bulk_create(
            to_create,
            batch_size=1000,
            ignore_conflicts=True,
        )
    
    return Response({
        'created': len(to_create),
        'candidates': len(candidate_keys),
        'skipped_no_process': skipped_no_process,
    })

def resolve_upstream_lines(viewset, request, **deps):
    self = viewset
    _parse_optional_date = deps.get('parse_optional_date')
    _parse_product_ids = deps.get('parse_product_ids')
    INVALID_SEQUENCE_SORT_VALUE = deps.get('invalid_sequence_sort_value')
    FLOOR_SHIPPING_PM_SEQUENCE_THRESHOLD = deps.get('floor_shipping_pm_sequence_threshold')
    _is_floor_shipping_delivery_line = deps.get('is_floor_shipping_delivery_line')
    """
    BOM/ルーティングから前ライン候補を抽出する。
    
    期待payload: { line_id?, product_ids: [int] }
    """
    line_id = request.data.get('line_id')
    product_ids = request.data.get('product_ids', [])
    
    if isinstance(product_ids, str):
        product_ids = [p for p in product_ids.split(',') if p.strip()]
    if not isinstance(product_ids, (list, tuple)) or not product_ids:
        return Response({'line_ids': []})
    
    try:
        parent_ids = {int(p) for p in product_ids}
    except (TypeError, ValueError):
        return Response({'detail': 'product_ids must be numeric'}, status=status.HTTP_400_BAD_REQUEST)
    
    bom_items = BOMItem.objects.filter(
        bom__is_active=True,
        bom__parent_product_id__in=parent_ids,
    )
    child_ids = set(bom_items.values_list('child_product_id', flat=True))
    if not child_ids:
        return Response({'line_ids': []})
    
    routing_steps = RoutingStep.objects.filter(
        Q(output_product_id__in=child_ids) | Q(routing__product_id__in=child_ids),
        line_id__isnull=False,
    ).filter(build_effective_routing_q(prefix='routing__'))
    line_ids = sorted(set(routing_steps.values_list('line_id', flat=True)))
    
    if line_id:
        try:
            line_id = int(line_id)
            line_ids = [lid for lid in line_ids if lid != line_id]
        except (TypeError, ValueError):
            pass
    
    return Response({
        'line_ids': line_ids,
        'child_product_ids': sorted(child_ids),
    })

def pickup(viewset, request, **deps):
    self = viewset
    _parse_optional_date = deps.get('parse_optional_date')
    _parse_product_ids = deps.get('parse_product_ids')
    INVALID_SEQUENCE_SORT_VALUE = deps.get('invalid_sequence_sort_value')
    FLOOR_SHIPPING_PM_SEQUENCE_THRESHOLD = deps.get('floor_shipping_pm_sequence_threshold')
    _is_floor_shipping_delivery_line = deps.get('is_floor_shipping_delivery_line')
    _is_kubota_delivery_line = deps.get('is_kubota_delivery_line')
    """
    ラインの需要を取得・計算する。
    
    処理フロー：
    1. LineBacklogにデータがあればそのまま返す
    2. なければ需要を計算：
       - 後ラインからplan_qtyを集計 × BOM個数 → order_qty
       - 後ラインがなければLineDemandから → order_qty（最終ライン）
    3. 計算結果をLineBacklogに保存して返す
    
    期待payload: { line_id, start_date?, end_date? }
    """
    import logging
    import time
    from masters.models import BOM, BOMItem, RoutingStep
    from collections import defaultdict
    
    logger = logging.getLogger(__name__)
    pickup_start = time.perf_counter()
    phase_start = pickup_start
    
    line_id = request.data.get('line_id')
    if not line_id:
        return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')
    try:
        requested_product_ids = set(_parse_product_ids(request.data.get('product_ids')))
    except ValueError as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    start_dt = _parse_optional_date(start_date)
    end_dt = _parse_optional_date(end_date)
    if start_dt and end_dt:
        start_dt = resolve_inventory_effective_start_date(
            int(line_id), start_dt, end_dt,
        )
    routing_candidate_q = build_effective_routing_range_q(start_dt, end_dt, prefix='routing__')
    
    # このラインで生産される全製品を特定（中間品、単品完成品、ライン最終品、工程最終品を含む）
    target_products = set()
    final_products = set()  # ライン最終品
    intermediate_products = set()  # 中間品
    product_process_map = {}
    product_step_map = {}
    
    # このラインに属する全工程を取得し、全ての製品を対象とする
    from django.db.models import Q  # 安全側でローカルインポート（UnboundLocalError対策）
    steps_on_line = RoutingStep.objects.filter(
        Q(line_id=line_id) | Q(line__isnull=True, process__line_id=line_id)
    ).filter(
        routing_candidate_q
    ).select_related('output_product', 'routing__product', 'process')
    
    current_line_steps_by_product = defaultdict(list)
    current_line_steps_by_routing_output = defaultdict(list)
    product_process_ids_map = defaultdict(set)
    steps_on_line_count = 0
    max_source_lt_days = 0
    for step in steps_on_line:
        steps_on_line_count += 1
        product = step.output_product or step.routing.product
        if product:
            target_products.add(product.id)
            product_process_map[product.id] = step.process_id
            product_process_ids_map[product.id].add(step.process_id)
            current_line_steps_by_product[product.id].append(step)
            if product.id not in product_step_map:
                product_step_map[product.id] = step
        if step.routing_id and getattr(step.routing, 'product_id', None) and step.output_product_id:
            current_line_steps_by_routing_output[(step.routing.product_id, step.output_product_id)].append(step)
    
            # ライン最終品と中間品を分類
            # is_final_product がTrueなら最終品扱い
            if product.is_final_product:
                final_products.add(product.id)
            else:
                intermediate_products.add(product.id)
    
        # 需要元データの取得上限をLT分だけ先まで広げるための最大LT
        try:
            if step.time_unit == 'MINUTE':
                step_lt = int(getattr(getattr(step, 'line', None), 'lead_time_days', 0) or 0)
            else:
                step_lt = int(step.lead_time_days or 0)
            if step_lt > max_source_lt_days:
                max_source_lt_days = step_lt
        except Exception:
            pass
    
    logger.info(
        "pickup: line_id=%s steps_on_line=%s target_products=%s final_products=%s intermediate_products=%s",
        line_id,
        steps_on_line_count,
        len(target_products),
        len(final_products),
        len(intermediate_products),
    )
    
    if requested_product_ids:
        target_products &= requested_product_ids
        final_products &= target_products
        intermediate_products &= target_products
        product_process_map = {
            product_id: process_id
            for product_id, process_id in product_process_map.items()
            if product_id in target_products
        }
        product_process_ids_map = {
            product_id: process_ids
            for product_id, process_ids in product_process_ids_map.items()
            if product_id in target_products
        }
        current_line_steps_by_product = {
            product_id: steps
            for product_id, steps in current_line_steps_by_product.items()
            if product_id in target_products
        }
        product_step_map = {
            product_id: step
            for product_id, step in product_step_map.items()
            if product_id in target_products
        }
    
    if not target_products:
        return Response([])
    source_end_dt = (end_dt + timedelta(days=max_source_lt_days + 7)) if end_dt else None
    routing_source_q = build_effective_routing_range_q(
        start_dt,
        source_end_dt or end_dt,
        prefix='routing__',
    )
    
    logger.info(
        "pickup: phase=setup line_id=%s target_products=%s final_products=%s intermediate_products=%s time=%.3fs",
        line_id,
        len(target_products),
        len(final_products),
        len(intermediate_products),
        time.perf_counter() - phase_start,
    )

    # 需要を計算：(product_id, plan_date, process_id, parent_product_id) -> order_qty
    demand_map = defaultdict(Decimal)
    demand_actual_map = defaultdict(Decimal)
    demand_parent_date_map = {}  # (product_id, plan_date, process_id, parent_product_id) -> 親の元plan_date
    
    # 使用するカレンダ（ライン紐付があれば優先、無ければdaiso）
    line_obj = Line.objects.filter(id=line_id).first()
    calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(calendar_code='daiso').values_list('id', flat=True).first()
    
    default_calendar_id = Calendar.objects.filter(calendar_code='daiso').values_list('id', flat=True).first()
    
    # CalendarDayを一括取得してキャッシュ化（N+1問題を解消）
    calendar_day_cache_by_id = {}
    
    def get_calendar_day_cache(target_calendar_id):
        cache = calendar_day_cache_by_id.get(target_calendar_id)
        if cache is not None:
            return cache
        cache = {}
        if target_calendar_id:
            # 期間を広めに取得（リードタイム分を考慮して前後60日）
            cache_start = (start_dt - timedelta(days=60)) if start_dt else None
            cache_end = (end_dt + timedelta(days=60)) if end_dt else None
            cal_qs = CalendarDay.objects.filter(calendar_id=target_calendar_id)
            if cache_start:
                cal_qs = cal_qs.filter(target_date__gte=cache_start)
            if cache_end:
                cal_qs = cal_qs.filter(target_date__lte=cache_end)
            for cal in cal_qs:
                cache[cal.target_date] = cal.is_working_day
        calendar_day_cache_by_id[target_calendar_id] = cache
        return cache
    
    def is_working_day_by_calendar(target_calendar_id, check_date):
        # カレンダ未設定 → 週末判定（月〜金を稼働日）
        if not target_calendar_id:
            return check_date.weekday() < 5
        cache = get_calendar_day_cache(target_calendar_id)
        if check_date in cache:
            return cache[check_date]
        cal = CalendarDay.objects.filter(calendar_id=target_calendar_id, target_date=check_date).first()
        is_work = cal.is_working_day if cal is not None else check_date.weekday() < 5
        cache[check_date] = is_work
        return is_work
    
    def is_line_working_day(check_date):
        return is_working_day_by_calendar(calendar_id, check_date)
    
    def shift_business_days_by_calendar(target_calendar_id, target_date, days):
        """
        稼働日で日付をシフトする。
        days > 0 なら過去方向へ、days < 0 なら未来方向へ。
        カレンダが無い場合は週末判定（土日非稼働）、さらに無ければ暦日でシフト。
        """
    
        if not days:
            if not target_calendar_id:
                return target_date
            if is_working_day_by_calendar(target_calendar_id, target_date):
                return target_date
            current = target_date
            while True:
                current = current - timedelta(days=1)
                if is_working_day_by_calendar(target_calendar_id, current):
                    return current
        step = -1 if days > 0 else 1  # 正:過去へ、負:未来へ
        remaining = abs(int(days))
        current = target_date
        while remaining > 0:
            current = current + timedelta(days=step)
            if is_working_day_by_calendar(target_calendar_id, current):
                remaining -= 1
        return current
    
    def shift_business_days(target_date, days):
        return shift_business_days_by_calendar(calendar_id, target_date, days)
    
    gantt_usage_cache = {}
    downstream_backlog_cache = {}
    
    def build_line_start_map(line_id, product_ids):
        key = (
            line_id,
            tuple(sorted(product_ids)),
            start_date,
            end_date,
            source_end_dt,
        )
        if key in gantt_usage_cache:
            return gantt_usage_cache[key]
    
        gantt_start = time.perf_counter()
        qs = LineGanttPlan.objects.filter(
            line_id=line_id,
            product_id__in=product_ids,
        ).only('plan_id', 'start_datetime', 'plan_qty')
    
        usage_map = {}
        plan_id_set = set()
        gantt_rows = 0
        for plan in qs:
            gantt_rows += 1
            start_dt_value = plan.start_datetime
            if not start_dt_value:
                continue
            # 日替わり8時ルール: 8時より前は前日扱い
            def apply_day_boundary(dt_val):
                """日替わり時刻（8時）を考慮した日付を取得"""
                if hasattr(dt_val, 'hour') and dt_val.hour < 8:
                    return (dt_val - timedelta(days=1)).date()
                return dt_val.date() if hasattr(dt_val, 'date') else dt_val
    
            try:
                plan_day = apply_day_boundary(start_dt_value)
            except Exception:
                try:
                    ts = str(start_dt_value).replace('Z', '+00:00')
                    parsed_dt = datetime.fromisoformat(ts)
                    plan_day = apply_day_boundary(parsed_dt)
                except Exception:
                    continue
            if start_dt and plan_day < start_dt:
                continue
            if source_end_dt and plan_day > source_end_dt:
                continue
            try:
                qty = Decimal(str(plan.plan_qty or 0))
            except Exception:
                qty = Decimal('0')
            if qty == 0:
                continue
            if plan.plan_id:
                plan_id_set.add(plan.plan_id)
            usage_map[plan_day] = usage_map.get(plan_day, Decimal('0')) + qty
    
        gantt_usage_cache[key] = (usage_map, plan_id_set)
        logger.info(
            "pickup: gantt_plans line_id=%s products=%s rows=%s time=%.3fs",
            line_id,
            len(product_ids),
            gantt_rows,
            time.perf_counter() - gantt_start,
        )
        return usage_map, plan_id_set
    
    def get_downstream_backlog_rows(target_line_id, target_ids):
        cache_key = (
            target_line_id,
            tuple(sorted(target_ids)),
            start_dt,
            source_end_dt or end_dt,
        )
        if cache_key in downstream_backlog_cache:
            return downstream_backlog_cache[cache_key]
    
        qs = LineBacklog.objects.filter(
            line_id=target_line_id,
            product_id__in=target_ids,
        )
        if start_dt:
            qs = qs.filter(plan_date__gte=start_dt)
        if source_end_dt or end_dt:
            qs = qs.filter(plan_date__lte=source_end_dt or end_dt)
        rows = list(qs.values_list('product_id', 'plan_date', 'plan_qty', 'plan_id', 'sequence_no', 'actual_qty'))
        downstream_backlog_cache[cache_key] = rows
        return rows
    
    def sort_sequence_value(value):
        try:
            seq = int(value or 0)
        except (TypeError, ValueError):
            seq = 0
        return seq if seq > 0 else INVALID_SEQUENCE_SORT_VALUE
    
    def resolve_lead_time_days(current_product_id, bom_item=None):
        """統一ルール: step.lead_time_days を使用（0 有効、未設定時のみ line fallback）。"""
        step = product_step_map.get(current_product_id)
        if step is not None:
            try:
                return resolve_lead_days_for_step(step)
            except Exception:
                return 0
        if bom_item and bom_item.lead_time_days:
            return bom_item.lead_time_days
        return 0
    
    def get_effective_current_output_steps(product_id, reference_date=None):
        steps = []
        for step in current_line_steps_by_product.get(product_id, []):
            if getattr(step, 'output_product_id', None) != product_id:
                continue
            steps.append(step)
        return sorted(steps, key=lambda s: ((s.step_no or 0), s.id or 0))
    
    def filter_bom_items_by_current_routing(product_id, bom_items, reference_date=None):
        current_steps = get_effective_current_output_steps(product_id, reference_date)
        if not current_steps or not bom_items:
            return bom_items
    
        filtered = []
        for bom_item in bom_items:
            parent_product_id = getattr(getattr(bom_item, 'bom', None), 'parent_product_id', None)
            if not parent_product_id:
                continue
            matched = False
            for current_step in current_steps:
                routing_product_id = getattr(getattr(current_step, 'routing', None), 'product_id', None)
                if not routing_product_id:
                    continue
                parent_steps = current_line_steps_by_routing_output.get((routing_product_id, parent_product_id), [])
                if not parent_steps:
                    continue
                current_step_no = current_step.step_no or 0
                for parent_step in parent_steps:
                    parent_step_no = parent_step.step_no or 0
                    if parent_step_no > current_step_no:
                        matched = True
                        break
                if matched:
                    break
            if matched:
                filtered.append(bom_item)
        return filtered or bom_items
    
    def resolve_target_process_ids_for_parent(product_id, parent_product_id=None, reference_date=None):
        child_steps = get_effective_current_output_steps(product_id, reference_date)
        if not child_steps:
            fallback_process_id = product_process_map.get(product_id)
            return [fallback_process_id] if fallback_process_id else []
        if len(child_steps) == 1 or not parent_product_id:
            return [child_steps[0].process_id]
    
        consumer_steps = get_effective_current_output_steps(parent_product_id, reference_date)
        if len(consumer_steps) == 1:
            consumer_step_no = consumer_steps[0].step_no or 0
            earlier_steps = [s for s in child_steps if (s.step_no or 0) < consumer_step_no]
            if earlier_steps:
                chosen = max(earlier_steps, key=lambda s: ((s.step_no or 0), s.id or 0))
                return [chosen.process_id]
    
        fallback_process_id = product_process_map.get(product_id)
        if fallback_process_id:
            return [fallback_process_id]
        return [child_steps[0].process_id]
    
    def add_demand(product_id, plan_date, qty, parent_product_id=None, actual_qty=None, parent_plan_date=None):
        process_ids = resolve_target_process_ids_for_parent(product_id, parent_product_id, plan_date)
        for process_id in process_ids:
            if not process_id:
                continue
            demand_map[(product_id, plan_date, process_id, parent_product_id)] += qty
            if actual_qty is not None:
                demand_actual_map[(product_id, plan_date, process_id, parent_product_id)] += actual_qty
            if parent_plan_date is not None:
                key = (product_id, plan_date, process_id, parent_product_id)
                prev = demand_parent_date_map.get(key)
                if prev is None or parent_plan_date > prev:
                    demand_parent_date_map[key] = parent_plan_date
            trace_log(
                line_id, product_id, plan_date,
                f'pickup需要加算: process_id={process_id}, parent_product_id={parent_product_id}, '
                f'qty={qty} (累計={demand_map[(product_id, plan_date, process_id, parent_product_id)]})'
            )
    
    # 既存バックログを先に取得し、ゼロ需要でもレコードを返せるよう初期化
    backlog_qs = self.get_queryset().filter(line_id=line_id, product_id__in=target_products).select_related('product', 'process')
    if start_date:
        backlog_qs = backlog_qs.filter(plan_date__gte=start_date)
    if end_date:
        backlog_qs = backlog_qs.filter(plan_date__lte=end_date)
    existing_backlogs = list(backlog_qs)
    for existing in existing_backlogs:
        demand_map[(existing.product_id, existing.plan_date, existing.process_id, None)] = Decimal('0')
        demand_actual_map[(existing.product_id, existing.plan_date, existing.process_id, None)] = Decimal('0')
    logger.info("pickup: existing_backlogs=%s", len(existing_backlogs))
    
    # 最終品はLineDemandから、中間品は後工程から需要を取得
    
    phase_start = time.perf_counter()

    # A. 最終品（is_final_product=True）はLineDemandから取得
    if final_products:
        demand_qs = LineDemand.objects.filter(
            line_id=line_id,
            product_id__in=final_products,
        )
        if start_dt:
            demand_qs = demand_qs.filter(plan_date__gte=start_dt)
        if source_end_dt or end_dt:
            demand_qs = demand_qs.filter(plan_date__lte=source_end_dt or end_dt)
    
        line_demands = list(demand_qs)
        logger.info("pickup: line_demands=%s", len(line_demands))
    
        firm_map = defaultdict(Decimal)
        forecast_map = defaultdict(Decimal)
        shifted_keys = set()
        for ld in line_demands:
            if not ld.product_id:
                continue
            key = (ld.product_id, ld.plan_date)
            firm_qty = Decimal(str(ld.firm_qty or 0))
            forecast_qty = Decimal(str(ld.forecast_qty or 0))
            if firm_qty > 0:
                firm_map[key] += firm_qty
            if forecast_qty > 0:
                forecast_map[key] += forecast_qty
            if ld.is_shifted or ld.firm_is_shifted or ld.forecast_is_shifted:
                shifted_keys.add(key)
    
        for key in set(firm_map) | set(forecast_map):
            firm_qty = firm_map.get(key, Decimal('0'))
            forecast_qty = forecast_map.get(key, Decimal('0'))
            # 前倒しで同日に重なった需要のみ、確定＋内示を合算する。
            # 前倒しが無い場合は「確定優先」。
            if key in shifted_keys and firm_qty > 0 and forecast_qty > 0:
                demand_qty = firm_qty + forecast_qty
            else:
                demand_qty = firm_qty if firm_qty > 0 else forecast_qty
            add_demand(key[0], key[1], demand_qty, None, actual_qty=demand_qty)

    logger.info(
        "pickup: phase=final_demand line_id=%s rows=%s demand_keys=%s demand_actual_keys=%s time=%.3fs",
        line_id,
        len(line_demands) if final_products else 0,
        len(demand_map),
        len(demand_actual_map),
        time.perf_counter() - phase_start,
    )
    
    # B. 中間品は後工程から需要を取得
    
    # 1. 後ライン（次工程）から需要を取得（RoutingStepベース）
    # ロジック：
    #   ステップ1: 現在ラインのoutput_product（例：中間品C）を特定
    #   ステップ2: 中間品Cを子部品として使う親製品（例：中間品B）をBOMから探す
    #   ステップ3: 親製品を出力するラインをRoutingStepから探す
    #   ステップ4: そのライン（例：溶接ライン）のLineBacklogから計画数を取得
    #   ステップ5: BOM個数を掛けて現在ラインの必要数を計算
    downstream_found = False
    
    phase_start = time.perf_counter()

    # 中間品がある場合、関連データを一括取得（N+1問題を解消）
    bom_items_by_child = {}
    parent_product_ids = set()
    if intermediate_products:
        all_bom_items = list(BOMItem.objects.filter(
            child_product_id__in=intermediate_products,
            bom__is_coproduct=False,
        ).select_related('bom', 'bom__parent_product'))
        logger.info("pickup: bom_items_for_intermediate=%s", len(all_bom_items))
        for bom_item in all_bom_items:
            child_id = bom_item.child_product_id
            if child_id not in bom_items_by_child:
                bom_items_by_child[child_id] = []
            bom_items_by_child[child_id].append(bom_item)
            if bom_item.bom and bom_item.bom.parent_product_id:
                parent_product_ids.add(bom_item.bom.parent_product_id)
    
    # 親製品を出力するRoutingStepを一括取得
    downstream_steps_by_product = {}
    if parent_product_ids:
        all_downstream_steps = list(RoutingStep.objects.filter(
            output_product_id__in=parent_product_ids
        ).filter(
            routing_source_q
        ).select_related('routing', 'routing__product', 'line'))
        logger.info("pickup: downstream_steps=%s", len(all_downstream_steps))
        for d_step in all_downstream_steps:
            prod_id = d_step.output_product_id
            if prod_id not in downstream_steps_by_product:
                downstream_steps_by_product[prod_id] = []
            downstream_steps_by_product[prod_id].append(d_step)
    
    logger.info(
        "pickup: phase=intermediate_prefetch line_id=%s bom_children=%s bom_items=%s parent_products=%s downstream_steps=%s time=%.3fs",
        line_id,
        len(bom_items_by_child),
        sum(len(items) for items in bom_items_by_child.values()),
        len(parent_product_ids),
        sum(len(items) for items in downstream_steps_by_product.values()),
        time.perf_counter() - phase_start,
    )

    phase_start = time.perf_counter()
    for product_id in intermediate_products:
        # 現在ラインのoutput_product（例：ブレーキラインなら中間品C）
        current_output_product = product_id
    
        # ステップ2: この製品を子部品として使うBOMを取得（キャッシュから）
        bom_items = filter_bom_items_by_current_routing(
            current_output_product,
            bom_items_by_child.get(current_output_product, []),
            start_dt,
        )
    
        for bom_item in bom_items:
            parent_product = bom_item.bom.parent_product
            if not parent_product:
                continue
    
            qty_per = bom_item.quantity or Decimal('0')
            if qty_per == 0:
                continue
    
            # ステップ3: 親製品を出力するライン（後工程）をRoutingStepから特定（キャッシュから）
            downstream_steps = downstream_steps_by_product.get(parent_product.id, [])
            # 同一(line, process, output_product, routing)が完全に重複している場合だけスキップ
            seen_steps = set()
            processed_line_keys = set()
            for d_step in downstream_steps:
                step_key = (d_step.line_id, d_step.process_id, d_step.output_product_id, d_step.routing_id)
                if step_key in seen_steps:
                    continue
                seen_steps.add(step_key)
                downstream_line_id = d_step.line_id
                if not downstream_line_id:
                    continue
                # 親品番需要は「後工程ライン単位で1回」だけ参照する
                line_key = (downstream_line_id, parent_product.id)
                if line_key in processed_line_keys:
                    continue
                processed_line_keys.add(line_key)
    
                # リードタイム（日）を考慮：現ラインのRoutingStep > Line > BOM明細 の順で優先
                lt_days = resolve_lead_time_days(current_output_product, bom_item)
    
                # 後工程需要の根拠数量は LineBacklog(seq>0) を正とする
                backlog_rows = get_downstream_backlog_rows(downstream_line_id, [parent_product.id])
    
                # ステップ5: 後工程の計画数 × BOM個数 = 現在ラインの必要数
                total_qty_per = qty_per
    
                if _is_floor_shipping_delivery_line(getattr(d_step, 'line', None)):
                    delivery_line = getattr(d_step, 'line', None)
                    delivery_calendar_id = getattr(delivery_line, 'calendar_id', None) or default_calendar_id
                    selected_rows_by_date = {}
                    actual_by_date = {}
                    for _, plan_date, plan_qty, _backlog_plan_id, sequence_no, row_actual_qty in backlog_rows:
                        qty = Decimal(str(plan_qty or 0))
                        if int(sequence_no or 0) == 0:
                            act = Decimal(str(row_actual_qty or 0))
                            if act > 0:
                                actual_by_date[plan_date] = actual_by_date.get(plan_date, Decimal('0')) + act
                        if qty == 0:
                            continue
                        selected_rows_by_date.setdefault(plan_date, []).append((qty, sequence_no))
    
                    for plan_date, lots in selected_rows_by_date.items():
                        ordered_lots = sorted(lots, key=lambda item: sort_sequence_value(item[1]))
                        for lot_index, (qty, _sequence_no) in enumerate(ordered_lots):
                            seq_value = sort_sequence_value(_sequence_no)
                            force_pm_by_sequence = (
                                seq_value != INVALID_SEQUENCE_SORT_VALUE and
                                seq_value > FLOOR_SHIPPING_PM_SEQUENCE_THRESHOLD
                            )
                            effective_lt_days = 1 if force_pm_by_sequence else (2 if lot_index == 0 else 1)
                            shifted_date = (
                                shift_business_days_by_calendar(
                                    delivery_calendar_id,
                                    plan_date,
                                    effective_lt_days,
                                )
                                if effective_lt_days else plan_date
                            )
                            shifted_date = shift_business_days(shifted_date, 0)
                            add_demand(current_output_product, shifted_date, qty * total_qty_per, parent_product.id)
                            downstream_found = True
                    for plan_date, act in actual_by_date.items():
                        shifted_date = shift_business_days(plan_date, lt_days) if lt_days else plan_date
                        shifted_date = shift_business_days(shifted_date, 0)
                        add_demand(current_output_product, shifted_date, Decimal('0'), parent_product.id,
                                   actual_qty=act * total_qty_per)
                    continue
    
                # --- クボタ配送ライン: plan_id から truck の arrival_day_offset で LT 決定 ---
                if _is_kubota_delivery_line(getattr(d_step, 'line', None)):
                    from shipping.views_kubota_sakai_trip_assignment import parse_truck_id_from_plan_id
                    kubota_line = getattr(d_step, 'line', None)
                    kubota_calendar_id = getattr(kubota_line, 'calendar_id', None) or default_calendar_id
    
                    # truck の arrival_day_offset キャッシュ
                    if not hasattr(self, '_kubota_truck_offset_cache'):
                        self._kubota_truck_offset_cache = {}
                    truck_offset_cache = self._kubota_truck_offset_cache
    
                    def _get_truck_offset(truck_id):
                        if truck_id not in truck_offset_cache:
                            truck = KubotaSakaiTruck.objects.filter(id=truck_id).first()
                            truck_offset_cache[truck_id] = getattr(truck, 'arrival_day_offset', 0) if truck else 0
                        return truck_offset_cache[truck_id]
    
                    kubota_rows_by_date = defaultdict(list)
                    kubota_actual_by_date = {}
                    for _, plan_date, plan_qty, backlog_plan_id, _seq, row_actual_qty in backlog_rows:
                        qty = Decimal(str(plan_qty or 0))
                        if int(_seq or 0) == 0:
                            act = Decimal(str(row_actual_qty or 0))
                            if act > 0:
                                kubota_actual_by_date[plan_date] = kubota_actual_by_date.get(plan_date, Decimal('0')) + act
                        if qty == 0:
                            continue
                        kubota_rows_by_date[plan_date].append((qty, backlog_plan_id))
    
                    for plan_date, lots in kubota_rows_by_date.items():
                        for qty, backlog_plan_id in lots:
                            truck_id = parse_truck_id_from_plan_id(backlog_plan_id)
                            if truck_id:
                                offset = _get_truck_offset(truck_id)
                                # offset=0（当日朝出発→当日着）→ LT=1（当日準備でOK）
                                # offset=1（前日夕出発→翌日着）→ LT=2（前日に準備必要）
                                effective_lt_days = 1 + offset
                            else:
                                effective_lt_days = lt_days or 2
                            shifted_date = (
                                shift_business_days_by_calendar(
                                    kubota_calendar_id,
                                    plan_date,
                                    effective_lt_days,
                                )
                                if effective_lt_days else plan_date
                            )
                            # クボタ便側カレンダで算出した需要日が自ライン休日に当たる場合は、
                            # 自ライン前営業日に寄せて在庫計算側との休日判定差異を吸収する。
                            shifted_date = shift_business_days(shifted_date, 0)
                            add_demand(current_output_product, shifted_date, qty * total_qty_per, parent_product.id)
                            downstream_found = True
                    for plan_date, act in kubota_actual_by_date.items():
                        shifted_date = shift_business_days(plan_date, lt_days) if lt_days else plan_date
                        shifted_date = shift_business_days(shifted_date, 0)
                        add_demand(current_output_product, shifted_date, Decimal('0'), parent_product.id,
                                   actual_qty=act * total_qty_per)
                    continue
    
                planned_map_by_date = {}
                actual_map_by_date = {}
                for _, plan_date, plan_qty, backlog_plan_id, _sequence_no, row_actual_qty in backlog_rows:
                    qty = Decimal(str(plan_qty or 0))
                    if int(_sequence_no or 0) == 0:
                        act = Decimal(str(row_actual_qty or 0))
                        if act > 0:
                            actual_map_by_date[plan_date] = actual_map_by_date.get(plan_date, Decimal('0')) + act
                        if qty == 0:
                            continue
                    planned_map_by_date[plan_date] = planned_map_by_date.get(plan_date, Decimal('0')) + qty

                for plan_date in set(planned_map_by_date) | set(actual_map_by_date):
                    qty = planned_map_by_date.get(plan_date, Decimal('0'))
                    act = actual_map_by_date.get(plan_date, Decimal('0'))
                    if qty == 0 and act == 0:
                        continue
                    shifted_date = shift_business_days(plan_date, lt_days) if lt_days else plan_date
                    shifted_date = shift_business_days(shifted_date, 0)
                    add_demand(current_output_product, shifted_date, qty * total_qty_per, parent_product.id,
                               actual_qty=act * total_qty_per, parent_plan_date=plan_date)
                    downstream_found = True
    
    logger.info(
        "pickup: phase=intermediate_expand_routing line_id=%s downstream_found=%s demand_keys=%s demand_actual_keys=%s parent_date_keys=%s gantt_cache=%s downstream_cache=%s time=%.3fs",
        line_id,
        downstream_found,
        len(demand_map),
        len(demand_actual_map),
        len(demand_parent_date_map),
        len(gantt_usage_cache),
        len(downstream_backlog_cache),
        time.perf_counter() - phase_start,
    )

    phase_start = time.perf_counter()

    # 2. RoutingStepベースの展開が失敗した場合、BOMベースの展開を試みる（中間品のみ）
    if not downstream_found and intermediate_products:
        # BOMItemを一括取得（line_idが現在ラインと一致するもの）
        bom_items_for_line = BOMItem.objects.filter(
            child_product_id__in=intermediate_products,
            line_id=line_id,
            bom__is_coproduct=False,
        ).select_related('bom', 'bom__parent_product')
    
        # 親製品IDを収集
        parent_ids_for_backlog = set()
        bom_items_by_child_line = {}
        for bom_item in bom_items_for_line:
            child_id = bom_item.child_product_id
            if child_id not in bom_items_by_child_line:
                bom_items_by_child_line[child_id] = []
            bom_items_by_child_line[child_id].append(bom_item)
            if bom_item.bom and bom_item.bom.parent_product_id:
                parent_ids_for_backlog.add(bom_item.bom.parent_product_id)
    
        # 親製品のLineBacklogを一括取得
        # RoutingStepで特定済みの後工程ラインのみ検索する（旧ルーティングのデータ混入防止）
        backlog_by_product = {}
        if parent_ids_for_backlog:
            valid_downstream_line_ids = set()
            for parent_id in parent_ids_for_backlog:
                for s in downstream_steps_by_product.get(parent_id, []):
                    if s.line_id:
                        valid_downstream_line_ids.add(s.line_id)
    
            backlog_qs_parent = LineBacklog.objects.filter(
                product_id__in=parent_ids_for_backlog,
            ).filter(
                models.Q(plan_qty__gt=0) | models.Q(actual_qty__gt=0)
            )
            if valid_downstream_line_ids:
                backlog_qs_parent = backlog_qs_parent.filter(line_id__in=valid_downstream_line_ids)
            if start_date:
                backlog_qs_parent = backlog_qs_parent.filter(plan_date__gte=start_date)
            if source_end_dt or end_date:
                backlog_qs_parent = backlog_qs_parent.filter(plan_date__lte=source_end_dt or end_date)
            for prod_id, plan_date, plan_qty, parent_actual_qty in backlog_qs_parent.values_list('product_id', 'plan_date', 'plan_qty', 'actual_qty'):
                if prod_id not in backlog_by_product:
                    backlog_by_product[prod_id] = []
                backlog_by_product[prod_id].append((plan_date, plan_qty, parent_actual_qty))
    
        for product_id in intermediate_products:
            current_output_product = product_id
            bom_items = filter_bom_items_by_current_routing(
                current_output_product,
                bom_items_by_child_line.get(current_output_product, []),
                start_dt,
            )
    
            for bom_item in bom_items:
                parent_product = bom_item.bom.parent_product
                if not parent_product:
                    continue
    
                qty_per = bom_item.quantity or Decimal('0')
                if qty_per == 0:
                    continue
    
                # 親製品のLineBacklogを取得（キャッシュから）
                backlog_items = backlog_by_product.get(parent_product.id, [])
    
                # リードタイムを考慮
                lt_days = resolve_lead_time_days(current_output_product, bom_item)
    
                for orig_plan_date, plan_qty, parent_actual_qty in backlog_items:
                    plan_date = orig_plan_date
                    if lt_days:
                        plan_date = shift_business_days(plan_date, lt_days)
                    plan_date = shift_business_days(plan_date, 0)
                    add_demand(
                        current_output_product,
                        plan_date,
                        Decimal(str(plan_qty or 0)) * qty_per,
                        parent_product.id,
                        actual_qty=Decimal(str(parent_actual_qty or 0)) * qty_per,
                        parent_plan_date=orig_plan_date,
                    )
                    downstream_found = True

    logger.info(
        "pickup: phase=intermediate_expand_fallback line_id=%s downstream_found=%s demand_keys=%s demand_actual_keys=%s parent_date_keys=%s time=%.3fs",
        line_id,
        downstream_found,
        len(demand_map),
        len(demand_actual_map),
        len(demand_parent_date_map),
        time.perf_counter() - phase_start,
    )
    
    # 4. LineBacklogに保存（order_qtyのみ更新、他の数量は維持）- bulk操作で高速化
    upserted_items = []
    upsert_start = time.perf_counter()
    try:
        phase_collect_start = time.perf_counter()

        # 対象キーを収集
        target_key_qty_map = defaultdict(Decimal)
        target_key_actual_map = defaultdict(Decimal)
        for (product_id, plan_date, process_id, _parent_product_id), order_qty in demand_map.items():
            if start_dt and plan_date < start_dt:
                continue
            if end_dt and plan_date > end_dt:
                continue
            key = (product_id, plan_date, process_id)
            target_key_qty_map[key] += order_qty
            trace_log(
                line_id, product_id, plan_date,
                f'pickup最終集計: process_id={process_id}, order_qty合計={target_key_qty_map[key]}'
            )
        for (product_id, plan_date, process_id, _parent_product_id), act_qty in demand_actual_map.items():
            if start_dt and plan_date < start_dt:
                continue
            if end_dt and plan_date > end_dt:
                continue
            key = (product_id, plan_date, process_id)
            target_key_actual_map[key] += act_qty
        target_keys = [
            (product_id, plan_date, process_id, order_qty, target_key_actual_map.get((product_id, plan_date, process_id), Decimal('0')))
            for (product_id, plan_date, process_id), order_qty in target_key_qty_map.items()
        ]
        target_key_set = set(target_key_qty_map.keys())
        logger.info(
            "pickup: phase=upsert_collect_keys line_id=%s qty_keys=%s actual_keys=%s target_keys=%s time=%.3fs",
            line_id,
            len(target_key_qty_map),
            len(target_key_actual_map),
            len(target_keys),
            time.perf_counter() - phase_collect_start,
        )

        # 期間内の全日付に対して、存在しない場合はsequence_no=0の行を用意する
        phase_fill_start = time.perf_counter()
        if start_dt and end_dt:
            # sequence_no=0(需要行)の存在だけを判定する。
            # 計画行(sequence_no>0)が存在していても、需要行が無ければ新規作成する。
            existing_any = set(
                LineBacklog.objects.filter(
                    line_id=line_id,
                    product_id__in=target_products,
                    plan_date__range=[start_dt, end_dt],
                    sequence_no=0,
                ).values_list('product_id', 'plan_date', 'process_id')
            )
            total_days = (end_dt - start_dt).days + 1
            for product_id in target_products:
                process_ids = sorted(product_process_ids_map.get(product_id, set()))
                if not process_ids:
                    fallback_process_id = product_process_map.get(product_id)
                    process_ids = [fallback_process_id] if fallback_process_id else []
                for offset in range(total_days):
                    plan_date = start_dt + timedelta(days=offset)
                    for process_id in process_ids:
                        if not process_id:
                            continue
                        key = (product_id, plan_date, process_id)
                        if key in existing_any or key in target_key_set:
                            continue
                        target_keys.append((product_id, plan_date, process_id, Decimal('0'), Decimal('0')))
                        target_key_set.add(key)
        logger.info(
            "pickup: phase=upsert_fill_missing line_id=%s target_keys=%s time=%.3fs",
            line_id,
            len(target_keys),
            time.perf_counter() - phase_fill_start,
        )

        # DEMAND特例ルールを読み込み、demand_qty_plan の決定に使用
        phase_rule_start = time.perf_counter()
        demand_order_qty_processes = set()
        try:
            from system_settings.models import SystemSetting as SysSetting
            rule_row = SysSetting.objects.filter(key='production.planned_stock_calc_rules').first()
            if rule_row:
                import json as _json
                pickup_line_code = (line_obj.line_code or '').strip().upper() if line_obj else ''
                process_code_by_id = {}
                for pid in {process_id for _, _, process_id, _, _ in target_keys}:
                    proc = Process.objects.filter(id=pid).values_list('process_code', flat=True).first()
                    if proc:
                        process_code_by_id[pid] = str(proc).strip().upper()
                for item in _json.loads(rule_row.value or '[]'):
                    lc = str((item or {}).get('lineCode') or '').strip().upper()
                    pc = str((item or {}).get('processCode') or '').strip().upper()
                    ct = str((item or {}).get('calcTarget') or '').strip().upper()
                    st = str((item or {}).get('setting') or '').strip().upper()
                    if lc == pickup_line_code and ct == 'DEMAND' and st == 'ORDER_QTY':
                        for pid, pcode in process_code_by_id.items():
                            if pcode == pc:
                                demand_order_qty_processes.add(pid)
        except Exception as e:
            logger.warning("pickup: DEMAND特例ルール読み込み失敗: %s", e)
        logger.info(
            "pickup: phase=upsert_load_rules line_id=%s matched_processes=%s time=%.3fs",
            line_id,
            len(demand_order_qty_processes),
            time.perf_counter() - phase_rule_start,
        )

        # demand_qty_plan を親単位で判定してから合算
        phase_plan_map_start = time.perf_counter()
        now = datetime.now()
        today = (now - timedelta(days=1)).date() if now.hour < 8 else now.date()
        target_key_demand_plan_map = defaultdict(Decimal)
        all_demand_keys = set(demand_map.keys()) | set(demand_actual_map.keys())
        for full_key in all_demand_keys:
            product_id, plan_date, process_id, _parent_product_id = full_key
            if start_dt and plan_date < start_dt:
                continue
            if end_dt and plan_date > end_dt:
                continue
            oq = demand_map.get(full_key, Decimal('0'))
            oa = demand_actual_map.get(full_key, Decimal('0'))
            parent_date = demand_parent_date_map.get(full_key)
            key = (product_id, plan_date, process_id)
            if process_id in demand_order_qty_processes:
                target_key_demand_plan_map[key] += oq
            elif parent_date is not None and parent_date < today:
                # 親の日が過去（生産完了）: 実績があればその値、なければ0
                target_key_demand_plan_map[key] += oa
            else:
                # 親の日が今日以降 or 親日付なし: 計画値を使用
                target_key_demand_plan_map[key] += oq
        logger.info(
            "pickup: phase=upsert_build_demand_plan line_id=%s all_demand_keys=%s demand_plan_keys=%s time=%.3fs",
            line_id,
            len(all_demand_keys),
            len(target_key_demand_plan_map),
            time.perf_counter() - phase_plan_map_start,
        )

        if target_keys:
            # 既存レコードを一括取得（巨大ORを避ける）
            phase_existing_start = time.perf_counter()
            target_product_ids = sorted({product_id for product_id, _, _, _, _ in target_keys})
            target_process_ids = sorted({process_id for _, _, process_id, _, _ in target_keys})
            target_plan_dates = [plan_date for _, plan_date, _, _, _ in target_keys]
            existing_qs = LineBacklog.objects.filter(
                line_id=line_id,
                sequence_no=0,
                product_id__in=target_product_ids,
                process_id__in=target_process_ids,
            )
            if target_plan_dates:
                min_plan_date = min(target_plan_dates)
                max_plan_date = max(target_plan_dates)
                existing_qs = existing_qs.filter(plan_date__gte=min_plan_date, plan_date__lte=max_plan_date)
            existing_records = {
                (r.product_id, r.plan_date, r.process_id): r
                for r in existing_qs
            }
            logger.info(
                "pickup: phase=upsert_load_existing line_id=%s existing_records=%s time=%.3fs",
                line_id,
                len(existing_records),
                time.perf_counter() - phase_existing_start,
            )

            phase_prepare_start = time.perf_counter()
            to_create = []
            to_update = []
            for product_id, plan_date, process_id, order_qty, order_qty_actual in target_keys:
                demand_qty_plan = target_key_demand_plan_map.get((product_id, plan_date, process_id), Decimal('0'))
                key = (product_id, plan_date, process_id)
                if key in existing_records:
                    obj = existing_records[key]
                    obj.order_qty = order_qty
                    obj.order_qty_actual = order_qty_actual
                    obj.demand_qty_plan = demand_qty_plan
                    # sequence_no=0 は需要行なので、計画数は常に0を維持する
                    obj.plan_qty = 0
                    to_update.append(obj)
                else:
                    to_create.append(LineBacklog(
                        plan_date=plan_date,
                        process_id=process_id,
                        product_id=product_id,
                        line_id=line_id,
                        sequence_no=0,
                        order_qty=order_qty,
                        order_qty_actual=order_qty_actual,
                        demand_qty_plan=demand_qty_plan,
                            plan_qty=0,
                        ))
            logger.info(
                "pickup: phase=upsert_prepare_mutations line_id=%s create=%s update=%s time=%.3fs",
                line_id,
                len(to_create),
                len(to_update),
                time.perf_counter() - phase_prepare_start,
            )

            # bulk_create と bulk_update を実行
            phase_write_start = time.perf_counter()
            if to_create:
                LineBacklog.objects.bulk_create(to_create)
            if to_update:
                LineBacklog.objects.bulk_update(to_update, ['order_qty', 'order_qty_actual', 'demand_qty_plan', 'plan_qty'])
            logger.info(
                "pickup: phase=upsert_write line_id=%s create=%s update=%s time=%.3fs",
                line_id,
                len(to_create),
                len(to_update),
                time.perf_counter() - phase_write_start,
            )

            upserted_items = to_create + to_update
    
        logger.info(
            "pickup: upserted_items=%s (create=%s, update=%s) time=%.3fs",
            len(upserted_items),
            len(to_create) if target_keys else 0,
            len(to_update) if target_keys else 0,
            time.perf_counter() - upsert_start,
        )
    except Exception as e:
        logger.error(
            "pickup: upsert失敗 line_id=%s %.3fs: %s",
            line_id,
            time.perf_counter() - upsert_start,
            e,
            exc_info=True,
        )
        raise
    
    # 5. 最新状態を返す
    items_to_serialize = upserted_items
    if not items_to_serialize:
        existing_items = existing_backlogs
        if existing_items:
            items_to_serialize = existing_items
        else:
            placeholder_date = start_dt or end_dt or datetime.today().date()
            placeholders = []
            for product_id in target_products:
                process_id = product_process_map.get(product_id)
                if not process_id:
                    continue
                placeholders.append(LineBacklog(
                    plan_date=placeholder_date,
                    process_id=process_id,
                    product_id=product_id,
                    line_id=line_id,
                    sequence_no=0,
                    order_qty=0,
                    demand_qty_plan=0,
                    plan_qty=0,
                    actual_qty=0,
                    stock_qty=0,
                    planned_stock_qty=0,
                ))
            items_to_serialize = placeholders
    serialize_start = time.perf_counter()
    serializer = self.get_serializer(items_to_serialize, many=True)
    logger.info(
        "pickup: phase=serialize line_id=%s items=%s time=%.3fs",
        line_id,
        len(items_to_serialize),
        time.perf_counter() - serialize_start,
    )
    logger.info("pickup: total_time=%.3fs", time.perf_counter() - pickup_start)
    return Response(serializer.data)

def pickup_for_products(viewset, request, **deps):
    self = viewset
    _parse_optional_date = deps.get('parse_optional_date')
    _parse_product_ids = deps.get('parse_product_ids')
    INVALID_SEQUENCE_SORT_VALUE = deps.get('invalid_sequence_sort_value')
    FLOOR_SHIPPING_PM_SEQUENCE_THRESHOLD = deps.get('floor_shipping_pm_sequence_threshold')
    _is_floor_shipping_delivery_line = deps.get('is_floor_shipping_delivery_line')
    """表示中品番限定の需要再計算。画面の表示開始日は使わない。"""
    mutable_data = request.data.copy()
    line_id = mutable_data.get('line_id')
    end_date = mutable_data.get('end_date')
    try:
        requested_product_ids = _parse_product_ids(mutable_data.get('product_ids'))
    except ValueError as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    if line_id and end_date:
        try:
            end_dt = datetime.strptime(str(end_date), '%Y-%m-%d').date()
            effective_start_dt = resolve_product_recalc_start_date(
                int(line_id),
                end_dt,
                product_ids=requested_product_ids or None,
            )
            mutable_data['start_date'] = effective_start_dt.isoformat()
        except (TypeError, ValueError):
            pass
    request._full_data = mutable_data
    return pickup(viewset, request, **deps)

def pickup_purchase(viewset, request, **deps):
    self = viewset
    _parse_optional_date = deps.get('parse_optional_date')
    _parse_product_ids = deps.get('parse_product_ids')
    INVALID_SEQUENCE_SORT_VALUE = deps.get('invalid_sequence_sort_value')
    FLOOR_SHIPPING_PM_SEQUENCE_THRESHOLD = deps.get('floor_shipping_pm_sequence_threshold')
    _is_floor_shipping_delivery_line = deps.get('is_floor_shipping_delivery_line')
    """
    購買/外注部品の需要を集計してLineBacklogに反映する。
    
    期待payload: { supplier_id or line_id, start_date?, end_date? }
    """
    import time as _time
    from collections import defaultdict
    _t0 = _time.perf_counter()
    
    raw_supplier_id = request.data.get('supplier_id')
    raw_line_id = request.data.get('line_id')
    if not raw_supplier_id and not raw_line_id:
        return Response({'detail': 'supplier_id or line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        requested_product_ids = set(_parse_product_ids(request.data.get('product_ids')))
    except ValueError as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    supplier = None
    supplier_id = None
    if raw_supplier_id:
        try:
            supplier_id = int(raw_supplier_id)
        except (TypeError, ValueError):
            return Response({'detail': 'supplier_id must be numeric'}, status=status.HTTP_400_BAD_REQUEST)
        supplier = Supplier.objects.filter(id=supplier_id).first()
    elif raw_line_id:
        try:
            lookup_line_id = int(raw_line_id)
        except (TypeError, ValueError):
            return Response({'detail': 'line_id must be numeric'}, status=status.HTTP_400_BAD_REQUEST)
        line_for_supplier = Line.objects.filter(id=lookup_line_id).only('line_code').first()
        if line_for_supplier:
            supplier = Supplier.objects.filter(supplier_code=line_for_supplier.line_code).first()
            supplier_id = getattr(supplier, 'id', None)
        if not supplier:
            return Response({
                'detail': f'supplier not found for line_id={lookup_line_id}',
                'created': 0,
                'updated': 0,
                'items': 0,
                'line_id': lookup_line_id,
                'skipped': True,
            })
    if not supplier:
        return Response({'detail': 'supplier not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    line_obj = resolve_supplier_purchase_line(supplier)
    if not line_obj:
        return Response({'detail': 'purchase line not found'}, status=status.HTTP_400_BAD_REQUEST)
    line_id = line_obj.id
    
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')
    start_dt = _parse_optional_date(start_date)
    end_dt = _parse_optional_date(end_date)
    routing_source_q = build_effective_routing_range_q(start_dt, end_dt, prefix='routing__')
    
    _t1 = _time.perf_counter()
    logger.info('[pickup_purchase] setup: %.3fs', _t1 - _t0)
    
    bom_items = list(BOMItem.objects.filter(
        sourcing_type__in=['BUY', 'SUBCON'],
        supplier_id=supplier_id,
        bom__is_active=True,
    ).select_related('bom', 'bom__parent_product', 'child_product', 'process', 'line'))
    if requested_product_ids:
        bom_items = [item for item in bom_items if item.child_product_id in requested_product_ids]
    
    parent_to_children = defaultdict(list)
    parent_ids = set()
    child_ids = set()
    bom_child_ids = set()
    child_process_map = {}
    has_buy_items = False
    relation_keys = set()
    for item in bom_items:
        parent_id = item.bom.parent_product_id if item.bom_id else None
        if not parent_id:
            continue
        qty = Decimal(str(item.quantity or 0))
        if qty == 0:
            continue
        lead_time_days = item.lead_time_days or 0
        parent_ids.add(parent_id)
        child_ids.add(item.child_product_id)
        bom_child_ids.add(item.child_product_id)
        sourcing_type = str(item.sourcing_type or '').upper()
        if sourcing_type == 'BUY':
            has_buy_items = True
        resolved_process = resolve_supplier_process(
            supplier=supplier,
            line=line_obj,
            product=getattr(item, 'child_product', None),
            preferred_process_id=item.process_id,
            sourcing_type=sourcing_type,
            create_purchase_process=(sourcing_type == 'BUY'),
        )
        if resolved_process:
            child_process_map.setdefault(item.child_product_id, resolved_process.id)
        key = (parent_id, item.child_product_id, qty, int(lead_time_days or 0))
        if key in relation_keys:
            continue
        relation_keys.add(key)
        parent_to_children[parent_id].append((item.child_product_id, qty, lead_time_days))
    
    default_process = resolve_supplier_process(
        supplier=supplier,
        line=line_obj,
        create_purchase_process=has_buy_items or str(getattr(supplier, 'supplier_type', '') or '').lower() != 'outsource',
    )
    process_id = default_process.id if default_process else None
    
    # ルーティング工程（外作先）基準の紐付けを追加
    # BOMが無い丸ごと外作でも、RoutingStep.supplier から需要計算対象を決定する。
    routing_steps = RoutingStep.objects.filter(
        output_product_id__isnull=False,
    ).filter(
        routing_source_q
    ).filter(
        Q(supplier_id=supplier_id) | Q(line_id=line_id)
    ).select_related('routing', 'routing__product', 'output_product', 'process')
    if requested_product_ids:
        routing_steps = routing_steps.filter(output_product_id__in=requested_product_ids)
    
    # ルーティングステップのG工程 or 外作区分でBUY/SUBCONを判定
    # pickup_purchase文脈ではrouting_stepsは仕入先ライン限定のため、
    # process_code='G' または process.is_outsource=True の工程のみSUBCONとみなす
    for step in routing_steps:
        source_parent_id = None
        if step.routing_id and getattr(step.routing, 'product_id', None):
            source_parent_id = step.routing.product_id
        if not source_parent_id:
            source_parent_id = step.output_product_id
        child_id = step.output_product_id
        if not source_parent_id or not child_id:
            continue
    
        # 非最終品に対して最終品LineDemandを直接需要源にしない。
        # ルーティング由来の直結で source_parent が最終品、child が非最終品の場合は
        # parent_to_children に載せず、通常の親計画/BOM経由の需要だけを採用する。
        source_parent = getattr(step.routing, 'product', None) if step.routing_id else None
        child_product = getattr(step, 'output_product', None)
        if (
            source_parent
            and child_product
            and source_parent.is_final_product
            and not child_product.is_final_product
        ):
            continue
    
        # SUBCON判定（G工程または外作フラグ）
        process = getattr(step, 'process', None)
        if process and step.process_id and is_outsource_process(process):
            child_process_map.setdefault(child_id, step.process_id)
    
        qty = Decimal('1')
        lead_time_days = int(step.lead_time_days or 0)
        parent_ids.add(source_parent_id)
        child_ids.add(child_id)
        key = (source_parent_id, child_id, qty, lead_time_days)
        if key in relation_keys:
            continue
        relation_keys.add(key)
        parent_to_children[source_parent_id].append((child_id, qty, lead_time_days))
    
    _t2 = _time.perf_counter()
    logger.info('[pickup_purchase] bom+routing scan: %.3fs (parents=%d, children=%d, subcon=%d)', _t2 - _t1, len(parent_ids), len(child_ids), len([pid for pid in child_process_map.values() if pid]))
    
    calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(
        calendar_code='daiso'
    ).values_list('id', flat=True).first()
    
    # カレンダ日をキャッシュし、無い場合は週末判定にフォールバックする
    calendar_day_cache = {}
    if calendar_id:
        cache_start = (start_dt - timedelta(days=60)) if start_dt else None
        cache_end = (end_dt + timedelta(days=60)) if end_dt else None
        cal_qs = CalendarDay.objects.filter(calendar_id=calendar_id)
        if cache_start:
            cal_qs = cal_qs.filter(target_date__gte=cache_start)
        if cache_end:
            cal_qs = cal_qs.filter(target_date__lte=cache_end)
        for cal in cal_qs:
            calendar_day_cache[cal.target_date] = cal.is_working_day
    
    calendar_has_data = bool(calendar_day_cache)
    if calendar_id and not calendar_has_data:
        calendar_has_data = CalendarDay.objects.filter(calendar_id=calendar_id).exists()
    
    def is_working_day(check_date):
        if calendar_id and calendar_has_data:
            if check_date in calendar_day_cache:
                return calendar_day_cache[check_date]
            cal = CalendarDay.objects.filter(calendar_id=calendar_id, target_date=check_date).first()
            is_work = cal.is_working_day if cal is not None else False
            calendar_day_cache[check_date] = is_work
            return is_work
        return check_date.weekday() < 5
    
    # 親計画の検索範囲を end_dt の「翌出勤日」まで延長する。
    # 表示期間（30日/60日）の末日直後の出勤日の親計画も需要計算に含めることで、
    # 表示期間によって需要値が変わらないようにする。
    parent_orders = []
    if parent_ids:
        parent_qs = LineBacklog.objects.filter(product_id__in=parent_ids).select_related('line')
        if start_dt:
            parent_qs = parent_qs.filter(plan_date__gte=start_dt)
        if end_dt:
            # end_dt の翌日から最初の出勤日を探す（最大14日先まで）
            next_work = end_dt + timedelta(days=1)
            for _ in range(14):
                if is_working_day(next_work):
                    break
                next_work += timedelta(days=1)
            parent_qs = parent_qs.filter(plan_date__lte=next_work)
    
        # 親製品の数量を取得:
        # - 通常ライン: plan_qty > 0
        # - 外作ライン(OUTSOURCE): 計画を持たないため order_qty > 0 も対象にする
        # - 最終品はここでは除外し、LineDemandを親数量の基準として別途取り込む
        parent_orders = list(
            parent_qs.values(
                'product_id',
                'line_id',
                'line__line_type',
                'product__is_final_product',
                'plan_date',
                'plan_qty',
                'order_qty',
                'plan_id',
            ).filter(
                Q(plan_qty__gt=0) |
                Q(order_qty__gt=0, line__line_type='OUTSOURCE')
            ).exclude(product__is_final_product=True)
        )
    
    _t3 = _time.perf_counter()
    logger.info('[pickup_purchase] calendar+parent_orders: %.3fs (parent_orders=%d)', _t3 - _t2, len(parent_orders))
    
    # 最終品の親数量は LineDemand を基準にする（社内ラインpickupと同じ）
    final_parent_ids = set(
        Product.objects.filter(
            id__in=parent_ids,
            is_final_product=True,
        ).values_list('id', flat=True)
    )
    def _resolve_linedemand_qty(demand_row):
        """
        社内ライン最終品のpickupロジックと同一:
        - 前倒し重複(is_shifted)で firm/forecast が両方ある場合のみ合算
        - それ以外は firm 優先、無ければ forecast
        - 互換のため split未設定時のみ plan_qty を最後に参照
        """
        firm_qty = Decimal(str(demand_row.get('firm_qty') or 0))
        forecast_qty = Decimal(str(demand_row.get('forecast_qty') or 0))
        is_shifted = bool(demand_row.get('is_shifted'))
        if is_shifted and firm_qty > 0 and forecast_qty > 0:
            return firm_qty + forecast_qty
        if firm_qty > 0:
            return firm_qty
        if forecast_qty > 0:
            return forecast_qty
        return Decimal(str(demand_row.get('plan_qty') or 0))
    
    if final_parent_ids:
        final_demand_qs = LineDemand.objects.filter(product_id__in=final_parent_ids)
        if start_dt:
            final_demand_qs = final_demand_qs.filter(plan_date__gte=start_dt)
        if end_dt:
            final_demand_qs = final_demand_qs.filter(plan_date__lte=end_dt)
    
        for row in final_demand_qs.values(
            'product_id', 'plan_date', 'firm_qty', 'forecast_qty', 'is_shifted', 'plan_qty'
        ):
            qty = _resolve_linedemand_qty(row)
            if qty == 0:
                continue
            parent_orders.append({
                'product_id': row.get('product_id'),
                'line_id': None,
                'line__line_type': 'FINAL_DEMAND',
                'product__is_final_product': True,
                'plan_date': row.get('plan_date'),
                'plan_qty': qty,
                'order_qty': qty,
                'plan_id': None,
            })
    
    # 日替わり8時ルール: 8時より前は前日扱い
    def apply_day_boundary(dt_val):
        """日替わり時刻（8時）を考慮した日付を取得"""
        if hasattr(dt_val, 'hour') and dt_val.hour < 8:
            return (dt_val - timedelta(days=1)).date()
        return dt_val.date() if hasattr(dt_val, 'date') else dt_val
    
    # 親製品（中間品）から最終品を特定するマップを構築
    # parent_id -> [(line_id, final_product_id)]
    parent_to_final = {}
    if parent_ids:
        steps_qs = RoutingStep.objects.filter(
            output_product_id__in=parent_ids
        ).filter(
            routing_source_q
        ).select_related('routing', 'routing__product')
        for step in steps_qs:
            if step.routing and step.routing.product:
                if step.routing.product.is_line_final_product:
                    parent_id = step.output_product_id
                    final_id = step.routing.product_id
                    line_id_step = step.line_id
                    if parent_id not in parent_to_final:
                        parent_to_final[parent_id] = []
                    parent_to_final[parent_id].append((line_id_step, final_id))
    
    # ガント検索用の製品ID（親製品＋最終品）
    gantt_product_ids = set(parent_ids)
    for finals in parent_to_final.values():
        for _, final_id in finals:
            gantt_product_ids.add(final_id)
    
    def shift_business_days(target_date, days):
        MAX_SCAN = 365
        if not days:
            if is_working_day(target_date):
                return target_date
            current = target_date
            for _ in range(MAX_SCAN):
                current = current - timedelta(days=1)
                if is_working_day(current):
                    return current
            return target_date
    
        step = -1 if days > 0 else 1
        remaining = abs(int(days))
        current = target_date
        for _ in range(remaining * 3 + MAX_SCAN):
            current = current + timedelta(days=step)
            if is_working_day(current):
                remaining -= 1
                if remaining <= 0:
                    break
        return current
    
    demand_map = defaultdict(Decimal)
    for row in parent_orders:
        parent_id = row['product_id']
        line_id_parent = row.get('line_id')
        plan_date = row['plan_date']
    
        # 外作ライン(OUTSOURCE)は計画未作成時に order_qty（需要）を使用する
        if row.get('line__line_type') == 'OUTSOURCE':
            plan_qty = Decimal(str(row.get('order_qty') or 0))
        else:
            plan_qty = Decimal(str(row['plan_qty'] or 0))
    
        # 購買需要では、計画日(plan_date)を基準にLTをシフトする
        effective_date = plan_date
    
        if plan_qty == 0:
            continue
    
        # 需要 = 親数量 × 子BOM数量（LTを考慮して日付をシフト）
        for child_id, qty, lead_time_days in parent_to_children.get(parent_id, []):
            target_date = shift_business_days(effective_date, lead_time_days)
            demand_map[(child_id, target_date)] += plan_qty * qty
    
    # フォールバック: 購買ラインのLineDemand（内示/確定集計）を需要として取り込む
    # ただし、社内ライン最終品と同じ方針で「最終品のみ」を対象にする。
    # BOM展開で同一キーがある場合はBOM計算値を優先する。
    direct_qs = LineDemand.objects.filter(
        line_id=line_id,
        product__is_final_product=True,
    )
    if start_dt:
        direct_qs = direct_qs.filter(plan_date__gte=start_dt)
    if end_dt:
        direct_qs = direct_qs.filter(plan_date__lte=end_dt)
    if requested_product_ids:
        direct_qs = direct_qs.filter(product_id__in=requested_product_ids)
    
    direct_demand_product_ids = set()
    for row in direct_qs.values('product_id', 'plan_date', 'firm_qty', 'forecast_qty', 'is_shifted', 'plan_qty'):
        product_id = row.get('product_id')
        plan_date = row.get('plan_date')
        qty = _resolve_linedemand_qty(row)
        if not product_id or not plan_date or qty == 0:
            continue
        plan_date = shift_business_days(plan_date, 0)
        direct_demand_product_ids.add(product_id)
        # BOM展開対象品は、需要ソースを親計画由来（BOM）に統一する
        # ※ ルーティング由来品まで除外すると、丸外作でフォールバックが効かないため
        #    除外対象は BOM 由来の子品目に限定する。
        if product_id in bom_child_ids:
            continue
        key = (product_id, plan_date)
        if key not in demand_map:
            demand_map[key] = qty
    
    target_product_ids = set(child_ids) | direct_demand_product_ids
    if requested_product_ids:
        target_product_ids = set(requested_product_ids)
    
    product_map = {
        product.id: product
        for product in Product.objects.filter(id__in=target_product_ids)
    }
    for product_id in target_product_ids:
        if product_id in child_process_map:
            continue
        resolved_process = resolve_supplier_process(
            supplier=supplier,
            line=line_obj,
            product=product_map.get(product_id),
            create_purchase_process=has_buy_items or str(getattr(supplier, 'supplier_type', '') or '').lower() != 'outsource',
        )
        if resolved_process:
            child_process_map[product_id] = resolved_process.id
    
    _t4 = _time.perf_counter()
    logger.info('[pickup_purchase] demand calc: %.3fs (demand_map=%d, target_products=%d)', _t4 - _t3, len(demand_map), len(target_product_ids))
    
    # SUBCON品はG工程（または外作区分）、BUY品はPURCHASEプロセスで既存レコードを検索
    all_process_ids = set(child_process_map.values())
    if process_id:
        all_process_ids.add(process_id)
    existing_qs = LineBacklog.objects.filter(
        line_id=line_id,
        process_id__in=all_process_ids,
        product_id__in=target_product_ids,
    )
    if start_dt:
        existing_qs = existing_qs.filter(plan_date__gte=start_dt)
    if end_dt:
        existing_qs = existing_qs.filter(plan_date__lte=end_dt)
    
    # キーに process_id を含めてBUY/SUBCON両方を管理
    existing_map = {(obj.product_id, obj.plan_date, obj.process_id): obj for obj in existing_qs}
    
    _t5 = _time.perf_counter()
    logger.info('[pickup_purchase] existing query: %.3fs (existing=%d)', _t5 - _t4, len(existing_map))
    
    created = 0
    updated = 0
    to_create = []
    to_update = []
    touch_update = []
    touch_timestamp = datetime.now()
    
    for (child_id, plan_date), demand in demand_map.items():
        qty_val = int(demand)
        # SUBCON品はG工程（または外作区分）、BUY品はPURCHASEプロセス
        child_process_id = child_process_map.get(child_id, process_id)
        if not child_process_id:
            continue
        existing_obj = existing_map.pop((child_id, plan_date, child_process_id), None)
        if existing_obj:
            if (existing_obj.order_qty or 0) != qty_val or (existing_obj.demand_qty_plan or 0) != qty_val:
                existing_obj.order_qty = qty_val
                existing_obj.demand_qty_plan = qty_val
                to_update.append(existing_obj)
                updated += 1
            else:
                existing_obj.updated_at = touch_timestamp
                touch_update.append(existing_obj)
        else:
            to_create.append(LineBacklog(
                plan_date=plan_date,
                process_id=child_process_id,
                product_id=child_id,
                line_id=line_id,
                sequence_no=0,
                order_qty=qty_val,
                demand_qty_plan=qty_val,
            ))
            created += 1
    
    zero_update = []
    for obj in existing_map.values():
        if (obj.order_qty or 0) != 0 or (obj.demand_qty_plan or 0) != 0:
            obj.order_qty = 0
            obj.demand_qty_plan = 0
            zero_update.append(obj)
            updated += 1
    
    if to_create:
        LineBacklog.objects.bulk_create(to_create, batch_size=500, ignore_conflicts=True)
    if to_update:
        LineBacklog.objects.bulk_update(to_update, ['order_qty', 'demand_qty_plan', 'updated_at'], batch_size=500)
    if touch_update:
        LineBacklog.objects.bulk_update(touch_update, ['updated_at'], batch_size=500)
    if zero_update:
        LineBacklog.objects.bulk_update(zero_update, ['order_qty', 'demand_qty_plan', 'updated_at'], batch_size=500)
    
    _t6 = _time.perf_counter()
    logger.info('[pickup_purchase] DB write: %.3fs (created=%d, updated=%d, touched=%d, zeroed=%d)', _t6 - _t5, len(to_create), len(to_update), len(touch_update), len(zero_update))
    logger.info('[pickup_purchase] TOTAL: %.3fs', _t6 - _t0)
    
    return Response({'created': created, 'updated': updated, 'items': len(demand_map), 'line_id': line_id, 'process_id': process_id})

def pickup_purchase_for_products(viewset, request, **deps):
    self = viewset
    _parse_optional_date = deps.get('parse_optional_date')
    _parse_product_ids = deps.get('parse_product_ids')
    INVALID_SEQUENCE_SORT_VALUE = deps.get('invalid_sequence_sort_value')
    FLOOR_SHIPPING_PM_SEQUENCE_THRESHOLD = deps.get('floor_shipping_pm_sequence_threshold')
    _is_floor_shipping_delivery_line = deps.get('is_floor_shipping_delivery_line')
    """表示中品番限定の購買需要再計算。"""
    return pickup_purchase(viewset, request, **deps)

def expand_processes(viewset, request, **deps):
    self = viewset
    _parse_optional_date = deps.get('parse_optional_date')
    _parse_product_ids = deps.get('parse_product_ids')
    INVALID_SEQUENCE_SORT_VALUE = deps.get('invalid_sequence_sort_value')
    FLOOR_SHIPPING_PM_SEQUENCE_THRESHOLD = deps.get('floor_shipping_pm_sequence_threshold')
    _is_floor_shipping_delivery_line = deps.get('is_floor_shipping_delivery_line')
    """
    指定ラインの計画数量を工程レベルに展開する。
    期待payload: { line_id, start_date, end_date, items?: [{product_id, plan_date, plan_qty?, order_qty?, demand_qty_plan?}], read_only?: bool }
    read_only=True の場合、LineBacklogに保存せず計算結果のみを返す
    read_only=False の場合、計算結果をLineBacklogに保存（plan_qtyを計算値で更新）
    """
    from collections import defaultdict
    from masters.models import RoutingStep, Calendar, CalendarDay
    
    line_id = request.data.get('line_id')
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')
    items = request.data.get('items', [])
    read_only = request.data.get('read_only', False)  # デフォルトはFalse（保存する）
    auto_plan_mode = request.data.get('auto_plan_mode', False)
    if isinstance(auto_plan_mode, str):
        auto_plan_mode = auto_plan_mode.lower() in ['true', '1', 'yes']
    else:
        auto_plan_mode = bool(auto_plan_mode)
    include_coproduct_children = request.data.get('include_coproduct_children', False)
    if isinstance(include_coproduct_children, str):
        include_coproduct_children = include_coproduct_children.lower() in ['true', '1', 'yes']
    else:
        include_coproduct_children = bool(include_coproduct_children)
    use_coproduct = request.data.get('use_coproduct', True)
    if isinstance(use_coproduct, str):
        use_coproduct = use_coproduct.lower() in ['true', '1', 'yes']
    else:
        use_coproduct = bool(use_coproduct)
    force_direct_process = request.data.get('force_direct_process', False)
    if isinstance(force_direct_process, str):
        force_direct_process = force_direct_process.lower() in ['true', '1', 'yes']
    else:
        force_direct_process = bool(force_direct_process)
    apply_bom_multiplier = request.data.get('apply_bom_multiplier', True)
    if isinstance(apply_bom_multiplier, str):
        apply_bom_multiplier = apply_bom_multiplier.lower() in ['true', '1', 'yes']
    else:
        apply_bom_multiplier = bool(apply_bom_multiplier)
    
    if not line_id:
        return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not start_date or not end_date:
        return Response({'detail': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        line_id = int(line_id)
    except (TypeError, ValueError):
        return Response({'detail': 'line_id must be numeric'}, status=status.HTTP_400_BAD_REQUEST)
    
    def parse_date(val):
        if val is None:
            return None
        if hasattr(val, 'year'):
            return val
        try:
            return datetime.strptime(str(val), '%Y-%m-%d').date()
        except Exception:
            return None
    
    # 先に対象期間内のベース計画を集める（フロントからのitems優先、無ければDBから取得）
    base_plans = []
    if isinstance(items, list) and items:
        for it in items:
            plan_date = parse_date(it.get('plan_date'))
            if not plan_date:
                continue
            product_id = it.get('product_id')
            if not product_id:
                continue
            plan_qty_raw = it.get('plan_qty', 0)
            order_qty_raw = it.get('order_qty', 0)
            demand_qty_raw = it.get('demand_qty_plan', order_qty_raw)
            try:
                plan_qty = Decimal(str(plan_qty_raw or 0))
                order_qty = Decimal(str(order_qty_raw or 0))
                demand_qty_plan = Decimal(str(demand_qty_raw or 0))
            except Exception:
                continue
            # 期間外は除外
            if str(plan_date) < str(start_date) or str(plan_date) > str(end_date):
                continue
            base_plans.append({
                'product_id': product_id,
                'process_id': it.get('process_id'),
                'plan_date': plan_date,
                'plan_qty': plan_qty,
                'order_qty': order_qty,
                'demand_qty_plan': demand_qty_plan,
                'sequence_no': it.get('sequence_no'),
            })
    else:
        qs = LinePlan.objects.filter(line_id=line_id)
        qs = qs.filter(plan_date__gte=start_date, plan_date__lte=end_date)
        qs = qs.filter(plan_qty__gt=0)
        for obj in qs:
            base_plans.append({
                'product_id': obj.product_id,
                'process_id': obj.process_id,
                'plan_date': obj.plan_date,
                'plan_qty': Decimal(str(obj.plan_qty or 0)),
                'order_qty': Decimal('0'),
                'demand_qty_plan': Decimal('0'),
                'sequence_no': obj.sequence_no,
                'plan_id': obj.plan_id,
            })
    
    if not base_plans:
        return Response([])
    
    # 連産品（コプロダクト）用の補助マップ
    # child_to_parent: 子製品 -> (親セットID, qty_per)
    # parent_children: 親セット -> [(child_id, qty_per)]
    # copro_set_qty: (親セット, 日付) -> 必要セット数（子計画から逆算した最大値）
    # copro_driver: (親セット, 日付) -> 工数を計上する代表子ID（最優先:計画>0かつIDが小さいもの）
    copro_child_map = {}
    parent_children = {}
    copro_set_qty = {}
    copro_driver = {}
    plan_qty_map = {}
    
    # plan_qty_mapを先に作成（Decimal化）
    for plan in base_plans:
        try:
            plan_qty_map[(plan['product_id'], plan['plan_date'])] = Decimal(str(plan['plan_qty'] or 0))
        except Exception:
            plan_qty_map[(plan['product_id'], plan['plan_date'])] = Decimal('0')
    
    # is_coproduct=True のBOMから子→親の対応を構築（最新valid_from優先）
    # is_coproduct_driver=True の子製品のみを copro_child_map に登録（共用部品問題を回避）
    if use_coproduct:
        copro_boms = BOM.objects.filter(is_coproduct=True, is_active=True).order_by('-valid_from', '-id').prefetch_related('items')
        for bom in copro_boms:
            for item in bom.items.all():
                try:
                    qty_decimal = Decimal(item.quantity)
                except Exception:
                    continue
                if qty_decimal == 0:
                    continue
                # is_coproduct_driver=True の子製品のみを連産品展開の対象とする
                if item.is_coproduct_driver:
                    if item.child_product_id not in copro_child_map:
                        copro_child_map[item.child_product_id] = {
                            'parent_id': bom.parent_product_id,
                            'qty_per': qty_decimal,
                        }
                parent_children.setdefault(bom.parent_product_id, []).append((item.child_product_id, qty_decimal))
    
    # 親セットごとに日付別セット数と代表子を決定
    for parent_id, children in parent_children.items():
        # その親に紐づく日付一覧を抽出
        dates = set()
        for child_id, _ in children:
            for (pid, d), qty in plan_qty_map.items():
                if pid == child_id and qty is not None:
                    dates.add(d)
        for plan_date in dates:
            max_set = None
            driver_id = None
            for child_id, qty_per in children:
                if qty_per == 0:
                    continue
                qty = plan_qty_map.get((child_id, plan_date))
                if qty is None:
                    continue
                try:
                    set_qty = qty / qty_per
                except Exception:
                    continue
                if max_set is None or set_qty > max_set:
                    max_set = set_qty
                if qty > 0:
                    if driver_id is None or child_id < driver_id:
                        driver_id = child_id
            if max_set is not None:
                copro_set_qty[(parent_id, plan_date)] = max_set
            if driver_id is None and children:
                # 需要が0でも最小IDを代表として扱う
                driver_id = min(c[0] for c in children)
            if driver_id is not None:
                copro_driver[(parent_id, plan_date)] = driver_id
    
    # 標準BOMの数量マップ（親→子の使用数量／有効期間）を構築
    # 全BOM（非連産品）から数量マップを構築（多段BOMに対応）
    bom_qty_map = defaultdict(list)
    normal_boms = BOM.objects.filter(
        is_active=True,
        is_coproduct=False,
    ).order_by('-valid_from', '-id').prefetch_related('items')
    for bom in normal_boms:
        for item in bom.items.all():
            try:
                qty_decimal = Decimal(item.quantity)
            except Exception:
                continue
            if qty_decimal == 0:
                continue
            bom_qty_map[bom.parent_product_id].append({
                'child_id': item.child_product_id,
                'qty': qty_decimal,
                'valid_from': bom.valid_from,
                'valid_to': bom.valid_to,
            })
    
    def find_bom_multiplier(parent_id, target_id, plan_date, visited=None):
        """
        多段BOMを辿って parent_id -> ... -> target_id の数量倍率を返す。
        見つからない場合はNone。
        """
        if parent_id == target_id:
            return Decimal('1')
        if visited is None:
            visited = set()
        key = (parent_id, target_id)
        if key in visited:
            return None
        visited.add(key)
        for ent in bom_qty_map.get(parent_id, []):
            if plan_date < ent['valid_from']:
                continue
            if ent['valid_to'] and plan_date > ent['valid_to']:
                continue
            if ent['child_id'] == target_id:
                return ent['qty']
            sub = find_bom_multiplier(ent['child_id'], target_id, plan_date, visited)
            if sub is not None:
                try:
                    return ent['qty'] * sub
                except Exception:
                    return None
        return None
    
    fallback_process_aware_multiplier_cache = {}
    fallback_process_output_cache = {}
    
    def collect_descendant_process_multipliers(parent_id, plan_date):
        """
        非連産BOMを再帰展開し、parent_id配下の子孫品番倍率を「どの工程の出力分か」
        まで区別して返す。
    
        同一品番が当ライン上の複数工程で出力される場合（例: 06SUBが5連1STと
        5連3STの両方で出力される）、各工程の出力step_noと、その品番を消費する
        BOM親品番自身の出力step_noの前後関係でペアリングし、二重計上を防ぐ。
        （5連1ST産の06SUBは直後の5連2ST=01SUB組立で消費され、5連3ST産の06SUBは
        直後の5連4ST=4ST組立で消費される、という生産順序に基づく対応付け）
    
        ペアリングが一意に決まらない場合（消費側の出力工程が複数/不明など）は、
        従来通り該当する全工程に同額を計上する（安全側のフォールバック）。
    
        戻り値: {(product_id, process_id): Decimal倍率}
        """
        cache_key = (parent_id, plan_date)
        cached = fallback_process_aware_multiplier_cache.get(cache_key)
        if cached is not None:
            return cached
    
        def get_output_steps(product_id):
            steps = [
                s for s in steps_map.get(product_id, [])
                if s.output_product_id == product_id and is_step_effective_for_reference(s, plan_date)
            ]
            return sorted(steps, key=lambda s: (s.step_no or 0, s.id or 0))
    
        result = defaultdict(Decimal)
    
        def walk(current_id, current_multiplier, path):
            for ent in bom_qty_map.get(current_id, []):
                if plan_date < ent['valid_from']:
                    continue
                if ent['valid_to'] and plan_date > ent['valid_to']:
                    continue
                child_id = ent.get('child_id')
                qty = ent.get('qty')
                if not child_id:
                    continue
                if child_id in path:
                    continue
                try:
                    next_multiplier = Decimal(current_multiplier) * Decimal(qty)
                except Exception:
                    continue
                if next_multiplier == 0:
                    continue
    
                child_steps = get_output_steps(child_id)
                if len(child_steps) <= 1:
                    if child_steps:
                        result[(child_id, child_steps[0].process_id)] += next_multiplier
                    # 当ラインに出力工程が無い品番はここでは計上せず、より下位の子孫側で判定する
                else:
                    consumer_steps = get_output_steps(current_id) if current_id != parent_id else []
                    chosen = None
                    if len(consumer_steps) == 1:
                        consumer_step_no = consumer_steps[0].step_no or 0
                        earlier = [s for s in child_steps if (s.step_no or 0) < consumer_step_no]
                        if earlier:
                            chosen = max(earlier, key=lambda s: (s.step_no or 0))
                    if chosen is not None:
                        result[(child_id, chosen.process_id)] += next_multiplier
                    else:
                        # 消費側の工程が一意に決まらない場合は従来通り全工程に計上
                        # 同一process_idの重複ステップは1回だけ計上（複数ルーティングが同じ工程・同じ出力品を持つ場合の多重計上を防止）
                        seen_process_ids = set()
                        for cs in child_steps:
                            if cs.process_id not in seen_process_ids:
                                seen_process_ids.add(cs.process_id)
                                result[(child_id, cs.process_id)] += next_multiplier
    
                walk(child_id, next_multiplier, path | {child_id})
    
        walk(parent_id, Decimal('1'), {parent_id})
        fallback_process_aware_multiplier_cache[cache_key] = result
        return result
    
    def get_effective_output_products_for_process(process_id, plan_date):
        """
        指定工程で有効な出力品番ID集合を返す（同一工程の重複Routingを除外するための判定用）。
        """
        cache_key = (process_id, plan_date)
        cached = fallback_process_output_cache.get(cache_key)
        if cached is not None:
            return cached
        output_ids = set()
        for step in steps_by_process.get(process_id, []):
            if not step.output_product_id:
                continue
            if not is_step_effective_for_reference(step, plan_date):
                continue
            output_ids.add(step.output_product_id)
        fallback_process_output_cache[cache_key] = output_ids
        return output_ids
    
    def collect_fallback_process_targets(base_target_product_id, process_id, plan_date):
        """
        フォールバック展開時に、基準品番＋そのBOM子孫のうち
        当該工程で出力対象になっている品番を返す。
        """
        effective_output_ids = get_effective_output_products_for_process(process_id, plan_date)
        targets = {}
        if base_target_product_id in effective_output_ids:
            targets[base_target_product_id] = Decimal('1')
        descendant_process_multipliers = collect_descendant_process_multipliers(base_target_product_id, plan_date)
        for (descendant_id, descendant_process_id), multiplier in descendant_process_multipliers.items():
            if descendant_process_id != process_id:
                continue
            if descendant_id in effective_output_ids and multiplier != 0:
                targets[descendant_id] = targets.get(descendant_id, Decimal('0')) + Decimal(multiplier)
        return targets
    
    # ラインに紐づくカレンダがあれば使用、無ければdaisoを使用
    line_obj = Line.objects.filter(id=line_id).first()
    is_l2201_line = str(getattr(line_obj, 'line_code', '') or '').strip().upper() == 'L2201'
    calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(calendar_code='daiso').values_list('id', flat=True).first()
    calendar_work_map = {}
    if calendar_id:
        cal_qs = CalendarDay.objects.filter(
            calendar_id=calendar_id,
            target_date__gte=start_date,
            target_date__lte=end_date
        )
        for c in cal_qs:
            calendar_work_map[c.target_date] = c.work_minutes
    
    def shift_business_days(target_date, days):
        if not days:
            return target_date
        if not calendar_id:
            return target_date + timedelta(days=-days)
        step = -1 if days > 0 else 1
        remaining = abs(int(days))
        current = target_date
        while remaining > 0:
            current = current + timedelta(days=step)
            cal = CalendarDay.objects.filter(calendar_id=calendar_id, target_date=current).first()
            is_work = cal.is_working_day if cal is not None else True
            if is_work:
                remaining -= 1
        return current
    
    # 対象ラインのRoutingStepを製品別にグルーピング
    steps_map = defaultdict(list)
    steps_qs = RoutingStep.objects.filter(
        line_id=line_id,
        routing__is_active=True,
    ).select_related('routing', 'output_product', 'process')
    process_ids = set()
    products_with_own_steps_on_line = set()
    steps_by_process = defaultdict(list)
    cycle_product_ids = set(p['product_id'] for p in base_plans)
    for step in steps_qs:
        product_keys = []
        if step.output_product_id:
            product_keys.append(step.output_product_id)
        if step.routing_id and step.routing.product_id:
            product_keys.append(step.routing.product_id)
            products_with_own_steps_on_line.add(step.routing.product_id)
        process_ids.add(step.process_id)
        steps_by_process[step.process_id].append(step)
        if step.output_product_id:
            cycle_product_ids.add(step.output_product_id)
        if step.routing_id and step.routing.product_id:
            cycle_product_ids.add(step.routing.product_id)
        for pid in set(product_keys):
            steps_map[pid].append(step)
    
    line_final_plan_product_ids = set(
        Product.objects.filter(
            id__in={int(p['product_id']) for p in base_plans if p.get('product_id')},
            is_line_final_product=True,
        ).values_list('id', flat=True)
    )
    
    # ライン最終品フォールバック用: ルーティング未登録でもライン配下の全工程に展開
    line_processes_for_fallback = list(
        Process.objects.filter(line_id=line_id, is_active=True).order_by('process_code')
    )
    process_ids.update(p.id for p in line_processes_for_fallback)
    plan_process_map = Process.objects.in_bulk(
        [int(p['process_id']) for p in base_plans if p.get('process_id')]
    )
    
    def sort_steps_for_plan(steps):
        return sorted(steps, key=lambda s: (s.step_no or 0, getattr(s, 'parallel_group', 1) or 1, s.id or 0))
    
    def is_step_effective_for_reference(step, reference):
        routing = getattr(step, 'routing', None)
        if not routing or not getattr(routing, 'is_active', False):
            return False
        ref_dt = normalize_routing_reference_datetime(reference)
        valid_from_dt = getattr(routing, 'valid_from_datetime', None)
        valid_to_dt = getattr(routing, 'valid_to_datetime', None)
        if valid_from_dt and normalize_routing_reference_datetime(valid_from_dt) > ref_dt:
            return False
        if valid_to_dt and normalize_routing_reference_datetime(valid_to_dt) < ref_dt:
            return False
        return True
    
    def select_steps_for_plan_product(product_id, reference=None):
        steps = list(steps_map.get(product_id, []))
        if not steps:
            return []
        effective_steps = [step for step in steps if is_step_effective_for_reference(step, reference)]
        if not effective_steps:
            return []
        steps = effective_steps
        # L2201は従来どおり計画対象製品に紐づくRoutingを優先する。
        # それ以外のラインでここを変えると、既存展開ロジックの対象stepが変わる。
        if is_l2201_line:
            owned_steps = [step for step in steps if step.routing_id and step.routing.product_id == product_id]
            if owned_steps:
                return sort_steps_for_plan(owned_steps)
        return sort_steps_for_plan(steps)
    
    def should_fallback_to_line_processes(product_id):
        if product_id not in line_final_plan_product_ids:
            return False
        if not line_processes_for_fallback:
            return False
        # 他品番ルーティングのoutput_product一致だけでは「自品番ルーティングあり」とみなさない
        return product_id not in products_with_own_steps_on_line
    
    fallback_coproduct_target_cache = {}
    
    def resolve_fallback_target_product(product_id, process_id, plan_date):
        """
        ライン最終品フォールバック時の展開先品番を解決する。
        - 連産品ドライバ子品番が同工程に存在し、かつ親品番(product_id)の通常BOM配下にある場合
          => 連産親(ST...)へ置換
        - それ以外
          => 元の品番を使用
        戻り値: (target_product_id, child_target_product_id)
        """
        cache_key = (product_id, process_id, plan_date)
        cached = fallback_coproduct_target_cache.get(cache_key)
        if cached is not None:
            return cached
    
        steps_for_process = sort_steps_for_plan(steps_by_process.get(process_id, []))
        for step in steps_for_process:
            child_id = step.output_product_id
            if not child_id:
                continue
            copro_info = copro_child_map.get(child_id)
            if not copro_info:
                continue
            if find_bom_multiplier(product_id, child_id, plan_date) is None:
                continue
            resolved = (copro_info['parent_id'], child_id)
            fallback_coproduct_target_cache[cache_key] = resolved
            return resolved
    
        resolved = (product_id, None)
        fallback_coproduct_target_cache[cache_key] = resolved
        return resolved
    
    # サイクルタイムをまとめて取得（ライン特定優先、なければライン指定なしを使用）
    cycle_time_map = defaultdict(list)
    if process_ids and cycle_product_ids:
        ct_qs = ProcessCycleTime.objects.filter(
            process_id__in=process_ids,
            product_id__in=cycle_product_ids,
            is_active=True,
        ).filter(Q(line_id=line_id) | Q(line__isnull=True))
        for ct in ct_qs:
            cycle_time_map[(ct.product_id, ct.process_id)].append(ct)
    
    def pick_cycle_time(product_id, process_id, plan_date):
        candidates = cycle_time_map.get((product_id, process_id), [])
        best = None
        for ct in candidates:
            if ct.valid_from and plan_date < ct.valid_from:
                continue
            if ct.valid_to and plan_date > ct.valid_to:
                continue
            if best is None:
                best = ct
                continue
            # ライン指定がある方を優先
            if best.line_id is None and ct.line_id == line_id:
                best = ct
        return best
    
    created = 0
    updated = 0
    skipped = []
    upserted = []
    debug_stale_deleted_count = 0
    debug_stale_deleted_plan_ids_sample = []
    
    # 影響範囲（変更された計画に対応するライン内工程）を削除してから再作成する
    if isinstance(items, list) and items and not read_only:
        affected_keys = set()
        for plan in base_plans:
            product_id = plan['product_id']
            plan_date = plan['plan_date']
            sequence_no = plan.get('sequence_no')
            seq_key = sequence_no if sequence_no is not None else 1
            plan_process_id = plan.get('process_id')
            if force_direct_process and plan_process_id:
                affected_keys.add((product_id, plan_process_id, plan_date, seq_key))
                continue
            steps = select_steps_for_plan_product(product_id, plan_date)
            use_fallback = should_fallback_to_line_processes(product_id)
            if not steps or use_fallback:
                # ライン最終品フォールバック: ルーティング未登録でもライン配下の全工程に展開
                if use_fallback:
                    for proc in line_processes_for_fallback:
                        target_product_id, child_target_product_id = resolve_fallback_target_product(
                            product_id, proc.id, plan_date
                        )
                        # 旧データ掃除のため、工程日付キーの候補は常に削除対象に含める
                        affected_keys.add((product_id, proc.id, plan_date, seq_key))
                        if target_product_id and target_product_id != product_id:
                            affected_keys.add((target_product_id, proc.id, plan_date, seq_key))
                        if child_target_product_id and child_target_product_id != target_product_id:
                            affected_keys.add((child_target_product_id, proc.id, plan_date, seq_key))
                        fallback_targets = collect_fallback_process_targets(
                            target_product_id, proc.id, plan_date
                        )
                        child_fallback_targets = {}
                        if include_coproduct_children and child_target_product_id and child_target_product_id != target_product_id:
                            child_fallback_targets = collect_fallback_process_targets(
                                child_target_product_id, proc.id, plan_date
                            )
                        if target_product_id != product_id:
                            supplemental_targets = collect_fallback_process_targets(
                                product_id, proc.id, plan_date
                            )
                            for supplemental_id in supplemental_targets.keys():
                                if supplemental_id in fallback_targets or supplemental_id in child_fallback_targets:
                                    continue
                                affected_keys.add((supplemental_id, proc.id, plan_date, seq_key))
                        for expanded_target_id in fallback_targets.keys():
                            affected_keys.add((expanded_target_id, proc.id, plan_date, seq_key))
                        for child_expanded_target_id in child_fallback_targets.keys():
                            affected_keys.add((child_expanded_target_id, proc.id, plan_date, seq_key))
                elif is_l2201_line and product_id in line_final_plan_product_ids and plan_process_id:
                    affected_keys.add((product_id, plan_process_id, plan_date, seq_key))
                continue
            for step in sorted(steps, key=lambda s: s.step_no or 0):
                target_date = shift_business_days(plan_date, step.lead_time_days or 0)
                target_product_id = step.output_product_id or product_id
    
                copro_info_target = copro_child_map.get(target_product_id)
                child_target_product_id = None
                if copro_info_target:
                    if include_coproduct_children:
                        child_target_product_id = target_product_id
                    target_product_id = copro_info_target['parent_id']
    
                affected_keys.add((target_product_id, step.process_id, target_date, seq_key))
                if child_target_product_id and child_target_product_id != target_product_id:
                    affected_keys.add((child_target_product_id, step.process_id, target_date, seq_key))
    
        if affected_keys:
            q_filter = Q()
            for product_id, process_id, plan_date, seq_key in affected_keys:
                q_filter |= Q(
                    plan_date=plan_date,
                    process_id=process_id,
                    product_id=product_id,
                    line_id=line_id,
                    sequence_no=seq_key,
                )
            LineBacklog.objects.filter(q_filter).exclude(plan_id__startswith='SINGLEPROC_').delete()
    
    # 旧plan_id由来のstale行削除（items有無に関係なく実行）
    # 親計画のsequence_noが変更された際、旧sequence_noの子品展開行が残るのを防ぐ
    if not read_only and base_plans:
        # LinePlanに存在するplan_idは絶対に消さない（誤削除防止のガード）
        protected_plan_ids = set(
            LinePlan.objects.filter(
                line_id=line_id,
                plan_id__isnull=False,
            ).values_list('plan_id', flat=True)
        )
        plan_dates = sorted({p.get('plan_date') for p in base_plans if p.get('plan_date')})
        source_product_ids = sorted({int(p.get('product_id')) for p in base_plans if p.get('product_id')})
        product_code_map = {}
        if source_product_ids:
            product_code_map = {
                int(pid): str(code or '')
                for pid, code in Product.objects.filter(id__in=source_product_ids).values_list('id', 'product_code')
            }
        prefixes_by_date = {}
        for p in base_plans:
            dt = p.get('plan_date')
            pid = p.get('product_id')
            code = product_code_map.get(int(pid), '') if pid is not None else ''
            if not dt or not code:
                continue
            prefixes_by_date.setdefault(dt, set()).add(f"{code}_{dt.strftime('%Y%m%d')}_")
    
        stale_row_ids = []
        stale_plan_ids = []
        if protected_plan_ids is not None and prefixes_by_date and plan_dates:
            candidate_rows = LineBacklog.objects.filter(
                line_id=line_id,
                sequence_no__gt=0,
                plan_date__in=plan_dates,
            ).exclude(plan_id__isnull=True).exclude(plan_id='').only('id', 'plan_id', 'plan_date')
            for row in candidate_rows:
                pid_text = str(row.plan_id or '')
                if pid_text.startswith('SINGLEPROC_'):
                    continue
                if pid_text in protected_plan_ids:
                    continue
                prefixes = prefixes_by_date.get(row.plan_date) or set()
                if any(pid_text.startswith(prefix) for prefix in prefixes):
                    stale_row_ids.append(row.id)
                    stale_plan_ids.append(pid_text)
        if stale_row_ids:
            LineBacklog.objects.filter(id__in=stale_row_ids).delete()
        debug_stale_deleted_count = len(stale_row_ids)
        debug_stale_deleted_plan_ids_sample = stale_plan_ids[:10]
        logger.warning(
            '[expand_processes] stale rows deleted line=%s count=%s sample=%s',
            line_id,
            debug_stale_deleted_count,
            debug_stale_deleted_plan_ids_sample,
        )
    
    # 単独計画（SINGLEPROC_）で管理されている工程×日は工程展開しない
    subproc_protected_process_dates = set()
    if not read_only:
        plan_dates_all = sorted({p.get('plan_date') for p in base_plans if p.get('plan_date')})
        if plan_dates_all:
            subproc_pairs = LineBacklog.objects.filter(
                line_id=line_id,
                plan_date__in=plan_dates_all,
                sequence_no__gt=0,
                plan_id__startswith='SINGLEPROC_',
            ).values_list('process_id', 'plan_date').distinct()
            for proc_id, pdate in subproc_pairs:
                subproc_protected_process_dates.add((proc_id, pdate))
    
    # 集計結果を保持（共用部品の加算に対応）
    aggregated = {}
    
    for plan in base_plans:
        product_id = plan['product_id']
        plan_date = plan['plan_date']
        raw_plan_qty = plan['plan_qty']
        plan_qty = raw_plan_qty
        order_qty = plan['order_qty']
        demand_qty_plan = plan['demand_qty_plan']
        sequence_no = plan.get('sequence_no')
        parent_plan_id = plan.get('plan_id')  # 親（ライン最終品）のplan_id
        seq_key = sequence_no if sequence_no is not None else 1
        seen_target_keys = set() if auto_plan_mode else None
        plan_process_id = plan.get('process_id')
    
        if force_direct_process and plan_process_id:
            computed_time_min = None
            ct = pick_cycle_time(product_id, plan_process_id, plan_date)
            process_obj = plan_process_map.get(int(plan_process_id)) if plan_process_id else None
            if process_obj and process_obj.management_unit == 'MINUTE':
                if ct:
                    try:
                        computed_time_min = float(
                            (Decimal(plan_qty) * Decimal(ct.cycle_time_min or 0)) + Decimal(ct.setup_time_min or 0)
                        )
                    except Exception:
                        computed_time_min = None
    
            key = (product_id, plan_process_id, plan_date, seq_key)
            entry = aggregated.get(key)
            if not entry:
                entry = {
                    'plan_qty': Decimal('0'),
                    'order_qty': Decimal('0'),
                    'demand_qty_plan': Decimal('0'),
                    'time_min': Decimal('0'),
                    'plan_ids': set(),
                    'step': None,
                    'cycle_time': ct,
                    'routing_product_id': None,
                    'source_routing_step_id': None,
                    'step_no': None,
                }
                aggregated[key] = entry
            entry['plan_qty'] += Decimal(plan_qty or 0)
            entry['order_qty'] += Decimal(order_qty or 0)
            entry['demand_qty_plan'] += Decimal(demand_qty_plan or 0)
            if computed_time_min is not None:
                entry['time_min'] += Decimal(str(computed_time_min))
            if parent_plan_id:
                entry['plan_ids'].add(parent_plan_id)
            continue
    
        steps = select_steps_for_plan_product(product_id, plan_date)
        use_fallback = should_fallback_to_line_processes(product_id)
        if not steps or use_fallback:
            # ライン最終品フォールバック: ルーティング未登録でもライン配下の全工程に展開
            if use_fallback:
                for proc in line_processes_for_fallback:
                    target_product_id, child_target_product_id = resolve_fallback_target_product(
                        product_id, proc.id, plan_date
                    )
                    fallback_targets = collect_fallback_process_targets(
                        target_product_id, proc.id, plan_date
                    )
                    child_fallback_targets = {}
                    if include_coproduct_children and child_target_product_id and child_target_product_id != target_product_id:
                        child_fallback_targets = collect_fallback_process_targets(
                            child_target_product_id, proc.id, plan_date
                        )
                    if target_product_id != product_id:
                        # 連産品セットへのリダイレクトにより、当工程で同時に出力される
                        # 連産品ドライバ以外の品番（通常BOM経由でのみ辿れるもの。例: 06SUB）が
                        # 計上漏れになるため、元品番からの通常BOM展開で補完する。
                        # すでにリダイレクト側で計上済みの品番は補完しない（二重計上防止）。
                        supplemental_targets = collect_fallback_process_targets(
                            product_id, proc.id, plan_date
                        )
                        for supplemental_id, supplemental_multiplier in supplemental_targets.items():
                            if supplemental_id in fallback_targets or supplemental_id in child_fallback_targets:
                                continue
                            fallback_targets[supplemental_id] = supplemental_multiplier
                    for expanded_target_id, multiplier in fallback_targets.items():
                        scaled_plan_qty = Decimal(plan_qty or 0) * Decimal(multiplier or 0)
                        scaled_order_qty = Decimal(order_qty or 0) * Decimal(multiplier or 0)
                        scaled_demand_qty = Decimal(demand_qty_plan or 0) * Decimal(multiplier or 0)
    
                        computed_time_min = None
                        ct = pick_cycle_time(expanded_target_id, proc.id, plan_date)
                        if not ct and expanded_target_id != target_product_id:
                            ct = pick_cycle_time(target_product_id, proc.id, plan_date)
                        if not ct and child_target_product_id and child_target_product_id != expanded_target_id:
                            ct = pick_cycle_time(child_target_product_id, proc.id, plan_date)
                        if not ct and product_id != expanded_target_id:
                            ct = pick_cycle_time(product_id, proc.id, plan_date)
    
                        if proc.management_unit == 'MINUTE' and ct:
                            try:
                                computed_time_min = float(
                                    (Decimal(scaled_plan_qty) * Decimal(ct.cycle_time_min or 0)) + Decimal(ct.setup_time_min or 0)
                                )
                            except Exception:
                                computed_time_min = None
    
                        key = (expanded_target_id, proc.id, plan_date, seq_key)
                        entry = aggregated.get(key)
                        if not entry:
                            entry = {
                                'plan_qty': Decimal('0'),
                                'order_qty': Decimal('0'),
                                'demand_qty_plan': Decimal('0'),
                                'time_min': Decimal('0'),
                                'plan_ids': set(),
                                'step': None,
                                'cycle_time': ct,
                                'routing_product_id': None,
                                'source_routing_step_id': None,
                                'step_no': None,
                            }
                            aggregated[key] = entry
                        entry['plan_qty'] += Decimal(scaled_plan_qty or 0)
                        entry['order_qty'] += Decimal(scaled_order_qty or 0)
                        entry['demand_qty_plan'] += Decimal(scaled_demand_qty or 0)
                        if computed_time_min is not None:
                            entry['time_min'] += Decimal(str(computed_time_min))
                        if parent_plan_id:
                            entry['plan_ids'].add(parent_plan_id)
    
                    if child_fallback_targets:
                        for child_expanded_target_id, child_multiplier in child_fallback_targets.items():
                            scaled_child_plan_qty = Decimal(plan_qty or 0) * Decimal(child_multiplier or 0)
                            scaled_child_order_qty = Decimal(order_qty or 0) * Decimal(child_multiplier or 0)
                            scaled_child_demand_qty = Decimal(demand_qty_plan or 0) * Decimal(child_multiplier or 0)
                            child_key = (child_expanded_target_id, proc.id, plan_date, seq_key)
                            child_entry = aggregated.get(child_key)
                            if not child_entry:
                                child_entry = {
                                    'plan_qty': Decimal('0'),
                                    'order_qty': Decimal('0'),
                                    'demand_qty_plan': Decimal('0'),
                                    'time_min': Decimal('0'),
                                    'plan_ids': set(),
                                    'step': None,
                                    'cycle_time': ct,
                                    'routing_product_id': None,
                                    'source_routing_step_id': None,
                                    'step_no': None,
                                }
                                aggregated[child_key] = child_entry
                            child_entry['plan_qty'] += Decimal(scaled_child_plan_qty or 0)
                            child_entry['order_qty'] += Decimal(scaled_child_order_qty or 0)
                            child_entry['demand_qty_plan'] += Decimal(scaled_child_demand_qty or 0)
                            if parent_plan_id:
                                child_entry['plan_ids'].add(parent_plan_id)
                continue
            if is_l2201_line and product_id in line_final_plan_product_ids and plan_process_id:
                computed_time_min = None
                ct = pick_cycle_time(product_id, plan_process_id, plan_date)
                process_obj = plan_process_map.get(int(plan_process_id))
                if process_obj and process_obj.management_unit == 'MINUTE' and ct:
                    try:
                        computed_time_min = float(
                            (Decimal(plan_qty) * Decimal(ct.cycle_time_min or 0)) + Decimal(ct.setup_time_min or 0)
                        )
                    except Exception:
                        computed_time_min = None
    
                key = (product_id, plan_process_id, plan_date, seq_key)
                entry = aggregated.get(key)
                if not entry:
                    entry = {
                        'plan_qty': Decimal('0'),
                        'order_qty': Decimal('0'),
                        'demand_qty_plan': Decimal('0'),
                        'time_min': Decimal('0'),
                        'plan_ids': set(),
                        'step': None,
                        'cycle_time': ct,
                        'routing_product_id': None,
                        'source_routing_step_id': None,
                        'step_no': None,
                    }
                    aggregated[key] = entry
                entry['plan_qty'] += Decimal(plan_qty or 0)
                entry['order_qty'] += Decimal(order_qty or 0)
                entry['demand_qty_plan'] += Decimal(demand_qty_plan or 0)
                if computed_time_min is not None:
                    entry['time_min'] += Decimal(str(computed_time_min))
                if parent_plan_id:
                    entry['plan_ids'].add(parent_plan_id)
                continue
            skipped.append({'product_id': product_id, 'plan_date': plan_date, 'reason': 'RoutingStep not found on line'})
            continue
    
        for step in sorted(steps, key=lambda s: s.step_no or 0):
            # ライン最終品の場合はLTシフトしない（計画日＝完成日）
            lt_days = step.lead_time_days or 0
            if step.output_product and step.output_product.is_line_final_product:
                lt_days = 0
            target_date = shift_business_days(plan_date, lt_days)
            target_product_id = step.output_product_id or product_id
            plan_qty_step = plan_qty
            order_qty_step = order_qty
            demand_qty_step = demand_qty_plan
    
            # 連産品の子製品の場合、親製品に置き換える
            original_target_product_id = target_product_id
            copro_info_target = copro_child_map.get(target_product_id)
            child_target_product_id = None
            child_plan_qty = raw_plan_qty
            if copro_info_target:
                if include_coproduct_children:
                    child_target_product_id = original_target_product_id
                # 子製品を親製品に置き換え
                target_product_id = copro_info_target['parent_id']
    
            # 連産品（コプロダクト）の場合、セット数ベースで工数を計算
            time_qty = plan_qty_step
            is_copro_driver = True
    
            if copro_info_target:
                copro_key = (copro_info_target['parent_id'], plan_date)
                set_qty = copro_set_qty.get(copro_key)
                if set_qty is not None:
                    time_qty = set_qty
                    plan_qty_step = set_qty
                driver_id = copro_driver.get(copro_key)
                # 代表child以外は工数0として扱い、重複計上を防ぐ
                is_copro_driver = driver_id in (None, original_target_product_id, product_id)
    
            # 標準BOMの数量を掛けて「二個使い」などを反映
            # 連産品置き換え時（copro）は別ロジックで処理するため除外
            qty_multiplier = Decimal('1')
            if apply_bom_multiplier and (not copro_info_target) and target_product_id != product_id:
                # 多段BOMを遡って数量を算出（親=ライン最終品）
                multiplier = find_bom_multiplier(product_id, target_product_id, plan_date)
                if multiplier is not None:
                    qty_multiplier = multiplier
            plan_qty_step = plan_qty_step * qty_multiplier
            time_qty = time_qty * qty_multiplier
            order_qty_step = order_qty_step * qty_multiplier
            demand_qty_step = demand_qty_step * qty_multiplier
            child_plan_qty = child_plan_qty * qty_multiplier
    
            computed_time_min = None
            # サイクルタイム取得は元の製品IDで行う
            ct = pick_cycle_time(original_target_product_id, step.process_id, target_date)
            if not ct and step.routing_id and step.routing.product_id and step.routing.product_id != original_target_product_id:
                ct = pick_cycle_time(step.routing.product_id, step.process_id, target_date)
            if not ct and product_id != original_target_product_id:
                ct = pick_cycle_time(product_id, step.process_id, target_date)
    
            if step.process and step.process.management_unit == 'MINUTE':
                if ct:
                    try:
                        total_min = (Decimal(time_qty) * Decimal(ct.cycle_time_min or 0)) + Decimal(ct.setup_time_min or 0)
                        computed_time_min = float(total_min)
                    except Exception:
                        computed_time_min = None
                elif step.time_unit == 'MINUTE' and step.duration_min is not None:
                    # サイクルタイム未設定時はRoutingStepのduration_minを1個当たり時間として使用
                    try:
                        total_min = Decimal(time_qty) * Decimal(step.duration_min or 0)
                        computed_time_min = float(total_min)
                    except Exception:
                        computed_time_min = None
    
            if not is_copro_driver:
                computed_time_min = 0
    
            def add_aggregate(target_id, qty_value, time_value, ord_qty_value, dem_qty_value):
                key = (target_id, step.process_id, target_date, seq_key)
                entry = aggregated.get(key)
                if not entry:
                    entry = {
                        'plan_qty': Decimal('0'),
                        'order_qty': Decimal('0'),
                        'demand_qty_plan': Decimal('0'),
                        'time_min': Decimal('0'),
                        'plan_ids': set(),
                        'step': step,
                        'cycle_time': ct,
                        'routing_product_id': step.routing.product_id if step.routing_id and step.routing else None,
                        'source_routing_step_id': step.id if step else None,
                        'step_no': step.step_no if step else None,
                    }
                    aggregated[key] = entry
                entry['plan_qty'] += Decimal(qty_value or 0)
                entry['order_qty'] += Decimal(ord_qty_value or 0)
                entry['demand_qty_plan'] += Decimal(dem_qty_value or 0)
                if time_value is not None:
                    entry['time_min'] += Decimal(str(time_value))
                if parent_plan_id:
                    entry['plan_ids'].add(parent_plan_id)
    
            main_key = (target_product_id, step.process_id, target_date, seq_key)
            if auto_plan_mode:
                if main_key in seen_target_keys:
                    continue
                seen_target_keys.add(main_key)
            add_aggregate(target_product_id, plan_qty_step, computed_time_min, order_qty_step, demand_qty_step)
    
            if child_target_product_id and child_target_product_id != target_product_id:
                child_key = (child_target_product_id, step.process_id, target_date, seq_key)
                if auto_plan_mode:
                    if child_key in seen_target_keys:
                        continue
                    seen_target_keys.add(child_key)
                add_aggregate(child_target_product_id, child_plan_qty, 0, order_qty_step, demand_qty_step)
    
    for (target_id, process_id, target_date, seq_key), entry in aggregated.items():
        if (process_id, target_date) in subproc_protected_process_dates:
            continue
        plan_qty_value = int(entry['plan_qty'])
        order_qty_value = int(entry['order_qty'])
        demand_qty_value = int(entry['demand_qty_plan'])
        plan_ids = entry['plan_ids']
        plan_id_value = None
        if len(plan_ids) == 1:
            plan_id_value = next(iter(plan_ids))
    
        if read_only:
            obj = LineBacklog.objects.filter(
                plan_date=target_date,
                process_id=process_id,
                product_id=target_id,
                line_id=line_id,
                sequence_no=seq_key,
            ).first()
    
            if not obj:
                obj = LineBacklog(
                    plan_date=target_date,
                    process_id=process_id,
                    product_id=target_id,
                    line_id=line_id,
                    plan_qty=plan_qty_value,
                    order_qty=order_qty_value,
                    demand_qty_plan=demand_qty_value,
                    source_line_id=line_id,
                    source_routing_step_id=entry.get('source_routing_step_id'),
                    sequence_no=seq_key,
                )
        else:
            defaults_dict = {
                'order_qty': order_qty_value,
                'demand_qty_plan': demand_qty_value,
                'source_line_id': line_id,
                'source_routing_step_id': entry.get('source_routing_step_id'),
                'plan_qty': plan_qty_value,
                'sequence_no': seq_key,
            }
            if plan_id_value:
                defaults_dict['plan_id'] = plan_id_value
            else:
                defaults_dict['plan_id'] = None
    
            obj, is_created = LineBacklog.objects.update_or_create(
                plan_date=target_date,
                process_id=process_id,
                product_id=target_id,
                line_id=line_id,
                sequence_no=seq_key,
                defaults=defaults_dict
            )
            created += 1 if is_created else 0
            updated += 0 if is_created else 1
    
        obj.computed_time_min = float(entry['time_min']) if entry['time_min'] is not None else None
        obj.work_minutes = calendar_work_map.get(target_date)
        obj.step_no = entry.get('step_no')
        obj.cycle_time_min = float(entry['cycle_time'].cycle_time_min) if entry['cycle_time'] and entry['cycle_time'].cycle_time_min else None
        obj.routing_product_id = entry['routing_product_id']
        upserted.append(obj)
    
    serializer = self.get_serializer(upserted, many=True)
    return Response({
        'items': serializer.data,
        'created': created,
        'updated': updated,
        'skipped': skipped,
        'debug_stale_deleted_count': debug_stale_deleted_count,
        'debug_stale_deleted_plan_ids_sample': debug_stale_deleted_plan_ids_sample,
    })
