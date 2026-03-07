"""
棚卸初期化専用モジュール

普段の在庫・計画在庫・進度の日次再計算ロジック（inventory_calculator.py / progress_calculator.py）
とは分離し、棚卸時のみ使用する初期化ロジックをここにまとめる。
"""
import logging
from collections import defaultdict, deque
from datetime import timedelta
from decimal import Decimal

from orders.utils.calendar_utils import get_business_today
from production.models_line_backlog import LineBacklog
from production.models_production import StockAllocation
from masters.models import RoutingStep
from django.db.models import Q, Sum
from .inventory_calculator import (
    _calculate_parent_actual_shipment,
    _get_shipment_scrap_qty,
    aggregate_scrap_to_backlog,
    _build_firm_order_map,
    _get_max_parent_bom_lead_time,
)

logger = logging.getLogger(__name__)


def _convert_minute_duration_to_lt_days(duration_min):
    """
    分管理の所要時間を営業日換算LTに変換する。
    - 480分以下: 0日
    - 480分超: duration_min // 480 日
    """
    minutes = int(duration_min or 0)
    if minutes <= 480:
        return 0
    return max(minutes // 480, 0)


def _resolve_edge_lead_time_days(line_id, child_product_id, bom_item=None, step_cache=None):
    """
    親子エッジ（子→直親）用のLT解決。
    進度基準日計算の親子エッジLT解決。
    time_unitルールは通常解決と同一とし、親子情報（bom_item）がある場合はそれを参照して判定する。
    """
    return _resolve_stocktake_lead_time_days(
        line_id,
        child_product_id,
        bom_item=bom_item,
        step_cache=step_cache,
    )


def _resolve_final_product_lt_days(line_id, product_id):
    """
    最終品/ライン最終品向けLT解決。
    最終品はパイプライン需要控除の基準となるため、DAY工程優先・それ以外はラインLTを使用する。
    """
    step = (
        RoutingStep.objects.filter(
            routing__is_active=True,
            line_id=line_id,
        )
        .filter(
            Q(output_product_id=product_id)
            | Q(output_product_id__isnull=True, routing__product_id=product_id)
        )
        .select_related('line')
        .order_by('step_no', 'id')
        .first()
    )
    if step is not None:
        if getattr(step, 'time_unit', None) == 'DAY':
            step_lt = int(step.lead_time_days or 0)
            if step_lt > 0:
                return step_lt
        step_line = getattr(step, 'line', None)
        if step_line and int(step_line.lead_time_days or 0) > 0:
            return int(step_line.lead_time_days or 0)
    return 0


def _collect_stocktake_mapping_keys(stocktake_date, target_product_ids):
    """
    棚卸基準日の line_backlog 作成対象キーを収集する。

    優先順:
    1. RoutingStep（通常の生産ルーティング）
    2. 既存 line_backlog 履歴（購入品/外注品の既存運用を救済）
    3. Product マスタの line/process
    4. BOMItem（BUY/SUBCON）の line/process
    """
    from masters.models import BOMItem, Product

    target_product_ids = list(target_product_ids or [])
    if not target_product_ids:
        return set(), set()

    unique_keys = set()
    mapped_product_ids = set()

    step_qs = RoutingStep.objects.filter(
        routing__is_active=True,
        line_id__isnull=False,
    ).filter(
        Q(output_product_id__in=target_product_ids) |
        Q(output_product_id__isnull=True, routing__product_id__in=target_product_ids)
    ).select_related('routing')
    for step in step_qs:
        target_product_id = step.output_product_id or step.routing.product_id
        if target_product_id not in target_product_ids:
            continue
        if not step.process_id or not step.line_id:
            continue
        unique_keys.add((step.process_id, target_product_id, step.line_id))
        mapped_product_ids.add(target_product_id)

    # 既存履歴から復元（RoutingStep が無い購入品/外注品向け）
    history_rows = (
        LineBacklog.objects.filter(
            product_id__in=target_product_ids,
            plan_date__lte=stocktake_date,
            sequence_no=0,
            process_id__isnull=False,
            line_id__isnull=False,
        )
        .values('product_id', 'process_id', 'line_id')
        .distinct()
    )
    for row in history_rows:
        pid = row['product_id']
        process_id = row['process_id']
        line_id = row['line_id']
        unique_keys.add((process_id, pid, line_id))
        mapped_product_ids.add(pid)

    # Product マスタの設定を利用
    product_rows = Product.objects.filter(
        id__in=target_product_ids,
        process_id__isnull=False,
        line_id__isnull=False,
    ).values('id', 'process_id', 'line_id')
    for row in product_rows:
        pid = row['id']
        process_id = row['process_id']
        line_id = row['line_id']
        unique_keys.add((process_id, pid, line_id))
        mapped_product_ids.add(pid)

    # BOM購買/外注明細の line/process を利用
    bom_rows = (
        BOMItem.objects.filter(
            bom__is_active=True,
            bom__is_coproduct=False,
            child_product_id__in=target_product_ids,
            sourcing_type__in=['BUY', 'SUBCON'],
            process_id__isnull=False,
            line_id__isnull=False,
        )
        .values('child_product_id', 'process_id', 'line_id')
        .distinct()
    )
    for row in bom_rows:
        pid = row['child_product_id']
        process_id = row['process_id']
        line_id = row['line_id']
        unique_keys.add((process_id, pid, line_id))
        mapped_product_ids.add(pid)

    return unique_keys, mapped_product_ids


def _resolve_stocktake_lead_time_days(line_id, product_id, bom_item=None, step_cache=None):
    """
    棚卸専用のLT解決。

    優先順位:
    - time_unit=MINUTE:
      - 中間品は duration_min のみで解決（ラインLTへフォールバックしない）
      - 480分以下=0日、480分超=duration_min//480 日
    - time_unit=DAY:
      1. RoutingStep.lead_time_days
      2. RoutingStep.line.lead_time_days
      3. BOMItem.lead_time_days
      4. 0
    """
    step = None
    cache_key = (line_id, product_id)
    if step_cache is not None and cache_key in step_cache:
        step = step_cache[cache_key]
    else:
        step = (
            RoutingStep.objects.filter(
                routing__is_active=True,
                line_id=line_id,
            )
            .filter(
                Q(output_product_id=product_id)
                | Q(output_product_id__isnull=True, routing__product_id=product_id)
            )
            .select_related('line')
            .order_by('step_no', 'id')
            .first()
        )
        if step_cache is not None:
            step_cache[cache_key] = step

    # 分管理の中間品は duration_min のみを使用（ラインLTフォールバック禁止）
    if bom_item is not None and getattr(bom_item, 'time_unit', None) == 'MINUTE':
        return _convert_minute_duration_to_lt_days(getattr(bom_item, 'duration_min', 0))

    if step is not None:
        if getattr(step, 'time_unit', None) == 'MINUTE':
            return _convert_minute_duration_to_lt_days(getattr(step, 'duration_min', 0))

        lead_days = int(step.lead_time_days or 0)
        if lead_days > 0:
            return lead_days

        step_line = getattr(step, 'line', None)
        if step_line and int(step_line.lead_time_days or 0) > 0:
            return int(step_line.lead_time_days or 0)

    if bom_item is not None and getattr(bom_item, 'time_unit', None) == 'DAY':
        return max(int(getattr(bom_item, 'lead_time_days', 0) or 0), 0)

    return 0


def _stocktake_sum_parent_shipments(backlog, pick_qty, shift_fn=None, step_cache=None):
    """
    棚卸専用: 親出庫合算。
    LTは _resolve_stocktake_lead_time_days() で解決する。
    """
    from masters.models import BOMItem

    parent_bom_items = BOMItem.objects.filter(
        child_product=backlog.product,
        bom__is_active=True,
        bom__is_coproduct=False
    ).select_related('bom__parent_product')

    if not parent_bom_items.exists():
        return Decimal('0')

    total_shipment = Decimal('0')
    for bom_item in parent_bom_items:
        parent_product = bom_item.bom.parent_product
        if not parent_product:
            continue

        qty_per = bom_item.quantity or Decimal('0')
        if qty_per == 0:
            continue

        lead_days = _resolve_stocktake_lead_time_days(
            backlog.line_id,
            backlog.product_id,
            bom_item=bom_item,
            step_cache=step_cache,
        )
        parent_date = backlog.plan_date
        if shift_fn:
            parent_date = shift_fn(backlog.plan_date, lead_days)

        # 集約して取得（仕損の重複計上防止、および実績/計画の混在対応）
        downstream_groups = LineBacklog.objects.filter(
            product=parent_product,
            plan_date=parent_date,
        ).values('product_id', 'line_id', 'process_id', 'plan_date').annotate(
            actual_total=Sum('actual_qty'),
            plan_total=Sum('plan_qty'),
        )
        for group in downstream_groups:
            use_qty = pick_qty(group)
            if use_qty:
                total_shipment += Decimal(str(use_qty)) * Decimal(str(qty_per))

    return total_shipment


def _stocktake_calculate_parent_actual_shipment_only(backlog, shift_fn=None, step_cache=None):
    """
    棚卸専用: 計画在庫の過去分計算用。
    親の実績のみを集計し、計画値へのフォールバックを行わない。
    """
    def pick_qty(group):
        actual = group['actual_total'] or 0
        scrap = _get_shipment_scrap_qty(
            group['product_id'],
            group['line_id'],
            group['process_id'],
            group['plan_date']
        )
        return actual + scrap

    return _stocktake_sum_parent_shipments(
        backlog,
        pick_qty,
        shift_fn=shift_fn,
        step_cache=step_cache,
    )


def _stocktake_calculate_parent_planned_shipment(backlog, today, shift_fn, step_cache=None):
    """
    棚卸専用: 計画在庫向け出庫（計画 + 仕損）。
    """

    def pick_qty(group):
        plan = group['plan_total'] or 0
        scrap = _get_shipment_scrap_qty(
            group['product_id'],
            group['line_id'],
            group['process_id'],
            group['plan_date']
        )
        return plan + scrap

    return _stocktake_sum_parent_shipments(
        backlog,
        pick_qty,
        shift_fn=shift_fn,
        step_cache=step_cache,
    )


def get_progress_upper_bound_date():
    """
    進度初期化における上限日（実行業務日の前々営業日）を返す。
    """
    from masters.models import Calendar, CalendarDay

    today = get_business_today()
    calendar_id = Calendar.objects.filter(
        calendar_code='daiso'
    ).values_list('id', flat=True).first()

    def is_working_day(target_date):
        if not calendar_id:
            return target_date.weekday() < 5
        cal = CalendarDay.objects.filter(
            calendar_id=calendar_id,
            target_date=target_date,
        ).first()
        return cal.is_working_day if cal is not None else target_date.weekday() < 5

    def get_prev_working_day(target_date):
        prev_date = target_date - timedelta(days=1)
        while not is_working_day(prev_date):
            prev_date = prev_date - timedelta(days=1)
        return prev_date

    return get_prev_working_day(get_prev_working_day(today))


def resolve_progress_baseline_date(stocktake_date):
    """
    棚卸日から進度初期化に使う基準日を解決する

    ルール:
    - 上限日: 実行日の業務日付(8時区切り)に対する前々営業日
    - 候補: line_backlog(plan_date, sequence_no=0) のうち、
      plan_date <= min(stocktake_date, 上限日)
    - 基準日: 候補のうち最も新しい日付

    Args:
        stocktake_date: 棚卸日(date)

    Returns:
        tuple[date, date]: (resolved_baseline_date, upper_bound_date)
    """
    upper_bound = get_progress_upper_bound_date()
    cutoff_date = min(stocktake_date, upper_bound)

    resolved = (LineBacklog.objects.filter(
        sequence_no=0,
        plan_date__lte=cutoff_date,
    ).values_list('plan_date', flat=True).distinct().order_by('-plan_date').first())

    if not resolved:
        raise ValueError(
            f'line_backlog row not found on or before {cutoff_date.isoformat()}'
        )

    return resolved, upper_bound


def ensure_stocktake_backlogs(stocktake_date, location='MAIN'):
    """
    棚卸日に sequence_no=0 の line_backlog を用意する。
    t_stock_allocation の current_stock を棚卸在庫として使用する。

    Args:
        stocktake_date: 棚卸日(date)
        location: 保管場所（既定 MAIN）

    Returns:
        dict: {
            backlog_created, backlog_updated,
            allocation_count, mapped_product_count,
            unmapped_product_codes
        }
    """
    allocations = list(
        StockAllocation.objects.filter(location=location).select_related('product')
    )

    if not allocations:
        return {
            'backlog_created': 0,
            'backlog_updated': 0,
            'allocation_count': 0,
            'mapped_product_count': 0,
            'unmapped_product_codes': [],
        }

    stock_by_product_id = {}
    product_code_by_id = {}
    for alloc in allocations:
        stock_by_product_id[alloc.product_id] = int(alloc.current_stock or 0)
        product_code_by_id[alloc.product_id] = alloc.product.product_code

    target_product_ids = list(stock_by_product_id.keys())

    unique_keys, mapped_product_ids = _collect_stocktake_mapping_keys(
        stocktake_date,
        target_product_ids,
    )

    backlog_created = 0
    backlog_updated = 0

    for process_id, product_id, line_id in unique_keys:
        stock_int = stock_by_product_id.get(product_id, 0)
        obj, created = LineBacklog.objects.get_or_create(
            plan_date=stocktake_date,
            process_id=process_id,
            product_id=product_id,
            line_id=line_id,
            sequence_no=0,
            defaults={
                'demand_qty_plan': 0,
                'order_qty': 0,
                'plan_qty': 0,
                'actual_qty': 0,
                'stock_qty': stock_int,
                # planned_stock_qty は initialize_planned_stock() で算出する。
                # ensure時点では未確定のため0をセット。
                'planned_stock_qty': 0,
                'adjust_qty': 0,
                'scrap_adjust_qty': 0,
                'scrap_qty': 0,
                'actual_shipment_qty': 0,
                'progress_qty': 0,
                'planned_progress_qty': 0,
                'is_stocktake_fix': True,
            },
        )
        if created:
            backlog_created += 1
        else:
            obj.stock_qty = stock_int
            obj.planned_stock_qty = 0
            obj.progress_qty = 0
            obj.planned_progress_qty = 0
            obj.is_stocktake_fix = True
            obj.save(update_fields=[
                'stock_qty',
                'planned_stock_qty',
                'progress_qty',
                'planned_progress_qty',
                'is_stocktake_fix',
                'updated_at',
            ])
            backlog_updated += 1

    unmapped_product_codes = sorted([
        product_code_by_id[pid] for pid in target_product_ids if pid not in mapped_product_ids
    ])

    return {
        'backlog_created': backlog_created,
        'backlog_updated': backlog_updated,
        'allocation_count': len(allocations),
        'mapped_product_count': len(mapped_product_ids),
        'unmapped_product_codes': unmapped_product_codes,
    }


def recalculate_inventory_from_stocktake(line_id, baseline_date, end_date):
    """
    棚卸専用: 指定ラインの在庫・計画在庫を棚卸基準日から再計算する。

    通常の日次再計算（inventory_calculator.py）との違い:
    - 前々営業日ガードなし: 全日付を対象に計算する
    - 初期値は棚卸アンカー（is_stocktake_fix=True）の stock_qty を使用
    - 棚卸日より前のデータには依存しない
    """
    from masters.models import Line, Calendar, CalendarDay

    aggregate_scrap_to_backlog(line_id, baseline_date, end_date)
    firm_map = _build_firm_order_map(line_id, baseline_date, end_date)

    product_ids = list(
        LineBacklog.objects.filter(
            line_id=line_id,
            plan_date__range=[baseline_date, end_date],
        ).values_list('product_id', flat=True).distinct()
    )

    # カレンダー関連のセットアップ（ライン単位で共通）
    calendar_id = None
    workday_cache = {}
    if line_id:
        line_obj = Line.objects.filter(id=line_id).first()
        calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(
            calendar_code='daiso'
        ).values_list('id', flat=True).first()

    def is_working_day(target_date):
        if not calendar_id:
            return target_date.weekday() < 5
        if target_date in workday_cache:
            return workday_cache[target_date]
        cal = CalendarDay.objects.filter(
            calendar_id=calendar_id, target_date=target_date
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

    today = get_business_today()

    for product_id in product_ids:
        _stocktake_recalc_stock(
            line_id, product_id, baseline_date, end_date,
            firm_map, today, get_prev_working_day,
        )
        _stocktake_recalc_planned_stock(
            line_id, product_id, baseline_date, end_date,
            firm_map, today, get_prev_working_day, shift_working_days,
            is_working_day=is_working_day,
        )

    return {
        'line_id': line_id,
        'product_count': len(product_ids),
    }


def _build_global_stocktake_baseline_progress_map(baseline_date, is_working_day):
    """
    棚卸基準日の製品別進度（需要控除後）を全ライン集計で構築する。

    目的:
    - 異なるラインに存在する親製品の進度を、子製品の基準日計算で参照できるようにする
    - 親→子の順（浅い階層→深い階層）で進度を確定する
    """
    from masters.models import BOMItem
    from ..models import LineDemand

    def shift_working_days(target_date, days):
        if not days:
            return target_date
        step = 1 if days > 0 else -1
        remaining = abs(int(days))
        current = target_date
        while remaining > 0:
            current = current + timedelta(days=step)
            if is_working_day(current):
                remaining -= 1
        return current

    baseline_rows = list(
        LineBacklog.objects.filter(
            plan_date=baseline_date,
            sequence_no=0,
            is_stocktake_fix=True,
        )
        .values('product_id')
        .annotate(total_stock=Sum('stock_qty'))
    )
    if not baseline_rows:
        return {}

    stock_by_product = {
        row['product_id']: int(row.get('total_stock') or 0)
        for row in baseline_rows
        if row.get('product_id') is not None
    }
    product_ids = list(stock_by_product.keys())
    if not product_ids:
        return {}

    parent_to_children = defaultdict(list)
    child_to_parents = defaultdict(list)
    in_degree = {pid: 0 for pid in product_ids}
    step_cache = {}
    max_lt_days = 0

    # 子対象は基準日に棚卸行を持つ製品。親は他ラインの製品も含める。
    bom_items = list(
        BOMItem.objects.filter(
            bom__is_active=True,
            bom__is_coproduct=False,
            child_product_id__in=product_ids,
        ).select_related('bom')
    )
    for item in bom_items:
        parent_id = item.bom.parent_product_id
        child_id = item.child_product_id
        qty = item.quantity or Decimal('0')
        lead_days = _resolve_edge_lead_time_days(
            None,
            child_id,
            bom_item=item,
            step_cache=step_cache,
        )
        child_to_parents[child_id].append((parent_id, qty, lead_days))
        if lead_days > max_lt_days:
            max_lt_days = lead_days

        # トポロジカルソートは対象集合内の依存のみで組む
        if parent_id in in_degree:
            parent_to_children[parent_id].append((child_id, qty))
            in_degree[child_id] = in_degree.get(child_id, 0) + 1

    queue = deque(sorted([pid for pid in product_ids if in_degree.get(pid, 0) == 0]))
    sorted_products = []
    while queue:
        pid = queue.popleft()
        sorted_products.append(pid)
        for child_id, _qty in parent_to_children.get(pid, []):
            in_degree[child_id] -= 1
            if in_degree[child_id] == 0:
                queue.append(child_id)

    if len(sorted_products) < len(product_ids):
        missing = [pid for pid in product_ids if pid not in set(sorted_products)]
        sorted_products.extend(sorted(missing))

    parent_product_ids = {
        item.bom.parent_product_id
        for item in bom_items
        if item.bom.parent_product_id is not None
    }
    demand_product_ids = set(product_ids) | parent_product_ids

    demand_by_product = {}
    demand_dates = {baseline_date}
    for offset in range(1, max_lt_days + 1):
        demand_dates.add(shift_working_days(baseline_date, offset))
    if demand_dates:
        demand_qs = LineDemand.objects.filter(
            plan_date__in=demand_dates,
            product_id__in=demand_product_ids,
        )
        for demand in demand_qs:
            qty = Decimal('0')
            firm_qty = demand.firm_qty if demand.firm_qty and demand.firm_qty > 0 else Decimal('0')
            forecast_qty = demand.forecast_qty if demand.forecast_qty and demand.forecast_qty > 0 else Decimal('0')
            is_shifted = bool(getattr(demand, 'is_shifted', False))
            if is_shifted and firm_qty > 0 and forecast_qty > 0:
                qty = firm_qty + forecast_qty
            elif firm_qty > 0:
                qty = firm_qty
            elif forecast_qty > 0:
                qty = forecast_qty
            if not qty or not demand.product_id:
                continue
            key = (demand.plan_date, demand.product_id)
            demand_by_product[key] = demand_by_product.get(key, Decimal('0')) + qty

    progress_map = {}
    for pid in sorted_products:
        parent_consumed = Decimal('0')
        for parent_id, bom_qty, _lead_days in child_to_parents.get(pid, []):
            parent_progress = progress_map.get(parent_id, 0)
            parent_consumed += Decimal(str(parent_progress)) * (bom_qty or Decimal('0'))

        anchor_progress = stock_by_product.get(pid, 0) + int(parent_consumed)
        if child_to_parents.get(pid):
            parent_ltdemand = Decimal('0')
            for parent_id, bom_qty, lead_days in child_to_parents.get(pid, []):
                if not lead_days:
                    continue
                for offset in range(1, lead_days + 1):
                    target_date = shift_working_days(baseline_date, offset)
                    parent_qty = demand_by_product.get((target_date, parent_id), Decimal('0'))
                    parent_ltdemand += parent_qty * (bom_qty or Decimal('0'))
            progress_map[pid] = anchor_progress - int(parent_ltdemand)
        else:
            demand_qty = int(demand_by_product.get((baseline_date, pid), Decimal('0')) or 0)
            progress_map[pid] = anchor_progress - demand_qty

    return progress_map


def recalculate_progress_from_stocktake(line_id, baseline_date, end_date):
    """
    棚卸専用: 指定ラインの進度を棚卸基準日から再計算する。

    1. BOMを上位→下位で処理し、親の基準日進度（需要控除後）を子へ反映
    2. baseline_date 以降を日次で連鎖計算
    3. baseline_date より前のデータは参照しない
    """
    from masters.models import Line, Calendar, CalendarDay, BOMItem
    from ..models import LineDemand

    product_ids = list(
        LineBacklog.objects.filter(
            line_id=line_id,
            plan_date__range=[baseline_date, end_date],
        ).values_list('product_id', flat=True).distinct()
    )
    if not product_ids:
        return {'line_id': line_id, 'product_count': 0}

    calendar_id = None
    workday_cache = {}
    if line_id:
        line_obj = Line.objects.filter(id=line_id).first()
        calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(
            calendar_code='daiso'
        ).values_list('id', flat=True).first()

    def is_working_day(target_date):
        if not calendar_id:
            return target_date.weekday() < 5
        if target_date in workday_cache:
            return workday_cache[target_date]
        cal = CalendarDay.objects.filter(
            calendar_id=calendar_id,
            target_date=target_date
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
        step = 1 if days > 0 else -1
        remaining = abs(int(days))
        current = target_date
        while remaining > 0:
            current = current + timedelta(days=step)
            if is_working_day(current):
                remaining -= 1
        return current

    demand_by_step = {}
    demand_by_product = {}
    demand_qs = LineDemand.objects.filter(
        line_id=line_id,
        plan_date__range=[baseline_date, end_date],
    )
    for demand in demand_qs:
        qty = Decimal('0')
        firm_qty = demand.firm_qty if demand.firm_qty and demand.firm_qty > 0 else Decimal('0')
        forecast_qty = demand.forecast_qty if demand.forecast_qty and demand.forecast_qty > 0 else Decimal('0')
        is_shifted = bool(getattr(demand, 'is_shifted', False))
        if is_shifted and firm_qty > 0 and forecast_qty > 0:
            qty = firm_qty + forecast_qty
        elif firm_qty > 0:
            qty = firm_qty
        elif forecast_qty > 0:
            qty = forecast_qty
        if demand.routing_step_id:
            key = (demand.plan_date, demand.routing_step_id)
            demand_by_step[key] = demand_by_step.get(key, Decimal('0')) + qty
        if demand.product_id:
            key = (demand.plan_date, demand.product_id)
            demand_by_product[key] = demand_by_product.get(key, Decimal('0')) + qty

    # 全ライン集計の基準日進度（需要控除後）を先に作成
    global_baseline_progress_map = _build_global_stocktake_baseline_progress_map(
        baseline_date,
        is_working_day,
    )

    # 棚卸基準日の進度を「親(浅い)→子(深い)」で確定させるため、BOM順で処理する
    parent_to_children = defaultdict(list)
    child_to_parents = defaultdict(list)
    in_degree = {pid: 0 for pid in product_ids}

    bom_items = list(
        BOMItem.objects.filter(
            bom__is_active=True,
            bom__is_coproduct=False,
            child_product_id__in=product_ids,
        ).select_related('bom')
    )
    max_lt_days = 0
    lt_by_child_parent = defaultdict(dict)
    lt_step_cache = {}
    for item in bom_items:
        parent_id = item.bom.parent_product_id
        child_id = item.child_product_id
        qty = item.quantity or Decimal('0')
        lead_days = _resolve_edge_lead_time_days(
            line_id,
            child_id,
            bom_item=item,
            step_cache=lt_step_cache,
        )
        parent_to_children[parent_id].append((child_id, qty))
        child_to_parents[child_id].append((parent_id, qty))
        lt_by_child_parent[child_id][parent_id] = lead_days
        if lead_days > max_lt_days:
            max_lt_days = lead_days
        # 並び順はライン内製品の依存のみを対象にする
        if parent_id in in_degree:
            in_degree[child_id] = in_degree.get(child_id, 0) + 1

    parent_product_ids = {item.bom.parent_product_id for item in bom_items if item.bom.parent_product_id is not None}
    parent_demand_by_product = {}
    if parent_product_ids:
        demand_dates = set()
        for offset in range(1, max_lt_days + 1):
            demand_dates.add(shift_working_days(baseline_date, offset))
        if demand_dates:
            parent_demand_qs = LineDemand.objects.filter(
                plan_date__in=demand_dates,
                product_id__in=parent_product_ids,
            )
            for demand in parent_demand_qs:
                qty = Decimal('0')
                firm_qty = demand.firm_qty if demand.firm_qty and demand.firm_qty > 0 else Decimal('0')
                forecast_qty = demand.forecast_qty if demand.forecast_qty and demand.forecast_qty > 0 else Decimal('0')
                is_shifted = bool(getattr(demand, 'is_shifted', False))
                if is_shifted and firm_qty > 0 and forecast_qty > 0:
                    qty = firm_qty + forecast_qty
                elif firm_qty > 0:
                    qty = firm_qty
                elif forecast_qty > 0:
                    qty = forecast_qty
                if not qty or not demand.product_id:
                    continue
                key = (demand.plan_date, demand.product_id)
                parent_demand_by_product[key] = parent_demand_by_product.get(key, Decimal('0')) + qty

    queue = deque(sorted([pid for pid in product_ids if in_degree.get(pid, 0) == 0]))
    sorted_products = []
    while queue:
        pid = queue.popleft()
        sorted_products.append(pid)
        for child_id, _qty in parent_to_children.get(pid, []):
            in_degree[child_id] -= 1
            if in_degree[child_id] == 0:
                queue.append(child_id)

    if len(sorted_products) < len(product_ids):
        missing = [pid for pid in product_ids if pid not in set(sorted_products)]
        sorted_products.extend(sorted(missing))

    # 親が他ラインの場合でも参照できるよう、全ライン集計値で初期化
    baseline_progress_map = dict(global_baseline_progress_map)
    for product_id in sorted_products:
        baseline_progress = _stocktake_recalc_progress(
            line_id=line_id,
            product_id=product_id,
            start_date=baseline_date,
            end_date=end_date,
            demand_by_step=demand_by_step,
            demand_by_product=demand_by_product,
            is_working_day=is_working_day,
            get_prev_working_day=get_prev_working_day,
            shift_working_days=shift_working_days,
            child_to_parents=child_to_parents,
            baseline_progress_map=baseline_progress_map,
            lt_by_child_parent=lt_by_child_parent,
            parent_demand_by_product=parent_demand_by_product,
        )
        if baseline_progress is not None:
            baseline_progress_map[product_id] = baseline_progress

    return {'line_id': line_id, 'product_count': len(product_ids)}


def _stocktake_recalc_progress(
    line_id,
    product_id,
    start_date,
    end_date,
    demand_by_step,
    demand_by_product,
    is_working_day,
    get_prev_working_day,
    shift_working_days,
    child_to_parents=None,
    baseline_progress_map=None,
    lt_by_child_parent=None,
    parent_demand_by_product=None,
):
    """
    棚卸専用: 進度を日次再計算する。
    - 基準日のアンカーは「自製品在庫 + 親の基準日進度×BOM数」で算出
    - 基準日は、最終品は当日需要を控除、子品目は直親の翌日からLT日分需要を控除
    - start_date より前は参照しない
    """
    backlogs = list(LineBacklog.objects.filter(
        line_id=line_id,
        product_id=product_id,
        plan_date__range=[start_date, end_date],
    ).select_related('product').order_by('plan_date', 'sequence_no', 'id'))

    if not backlogs:
        return

    by_date = {}
    for backlog in backlogs:
        by_date.setdefault(backlog.plan_date, []).append(backlog)

    process_ids = {r.process_id for r in backlogs if r.process_id}
    step_map = {}
    if process_ids:
        steps = RoutingStep.objects.filter(
            line_id=line_id,
            process_id__in=process_ids,
        ).filter(
            Q(output_product_id=product_id) | Q(output_product_id__isnull=True, routing__product_id=product_id)
        ).select_related('routing', 'output_product')
        for step in steps:
            step_product_id = step.output_product_id or (step.routing.product_id if step.routing_id else None)
            if step_product_id != product_id:
                continue
            if step.process_id not in step_map:
                step_map[step.process_id] = step.id

    def pick_representative(rows):
        base_rows = [r for r in rows if r.sequence_no == 0]
        if base_rows:
            return min(base_rows, key=lambda r: r.id)
        return min(rows, key=lambda r: r.id)

    def pick_stocktake_anchor(rows):
        fix_rows = [r for r in rows if getattr(r, 'is_stocktake_fix', False)]
        if not fix_rows:
            return None
        seq0_fix_rows = [r for r in fix_rows if r.sequence_no == 0]
        candidates = seq0_fix_rows if seq0_fix_rows else fix_rows
        return min(candidates, key=lambda r: r.id)

    progress_by_date = {}
    planned_progress_by_date = {}
    last_progress = 0
    last_planned_progress = 0
    backlogs_to_update = []
    baseline_progress = None

    for plan_date in sorted(by_date.keys()):
        rows = by_date[plan_date]

        process_id = rows[0].process_id if rows else None
        step_id = step_map.get(process_id) if process_id else None
        demand_qty = Decimal('0')
        if step_id:
            demand_qty = demand_by_step.get((plan_date, step_id), Decimal('0'))
        if demand_qty == 0:
            demand_qty = demand_by_product.get((plan_date, product_id), Decimal('0'))
        progress_shipment = int(demand_qty or 0)

        anchor = pick_stocktake_anchor(rows)
        if anchor:
            # 基準日は、親進度を反映した上で需要を控除する。
            # 子品目は「自分のLT日分の直親需要（翌日から）」を控除する。
            parent_consumed = Decimal('0')
            if child_to_parents and baseline_progress_map is not None:
                for parent_id, bom_qty in child_to_parents.get(product_id, []):
                    parent_progress = baseline_progress_map.get(parent_id, 0)
                    parent_consumed += Decimal(str(parent_progress)) * (bom_qty or Decimal('0'))

            anchor_progress_qty = (anchor.stock_qty or 0) + int(parent_consumed)
            anchor_planned_progress_qty = anchor_progress_qty
            parent_lt_demand = Decimal('0')
            if child_to_parents and child_to_parents.get(product_id):
                for parent_id, bom_qty in child_to_parents.get(product_id, []):
                    lead_days = 0
                    if lt_by_child_parent and product_id in lt_by_child_parent:
                        lead_days = int(lt_by_child_parent[product_id].get(parent_id, 0) or 0)
                    if lead_days <= 0:
                        continue
                    for offset in range(1, lead_days + 1):
                        target_date = shift_working_days(plan_date, offset)
                        parent_qty = Decimal('0')
                        if parent_demand_by_product:
                            parent_qty = parent_demand_by_product.get((target_date, parent_id), Decimal('0'))
                        parent_lt_demand += parent_qty * (bom_qty or Decimal('0'))

            if child_to_parents and child_to_parents.get(product_id):
                progress_qty = anchor_progress_qty - int(parent_lt_demand)
                planned_progress_qty = anchor_planned_progress_qty - int(parent_lt_demand)
            else:
                progress_qty = anchor_progress_qty - progress_shipment
                planned_progress_qty = anchor_planned_progress_qty - progress_shipment
            rep = pick_representative(rows)
            for row in rows:
                row.progress_qty = 0
                row.planned_progress_qty = 0
            rep.progress_qty = progress_qty
            rep.planned_progress_qty = planned_progress_qty
            backlogs_to_update.extend(rows)
            progress_by_date[plan_date] = progress_qty
            planned_progress_by_date[plan_date] = planned_progress_qty
            last_progress = progress_qty
            last_planned_progress = planned_progress_qty
            if plan_date == start_date:
                baseline_progress = progress_qty
            continue

        actual_total = sum(r.actual_qty or 0 for r in rows)
        plan_total = sum(r.plan_qty or 0 for r in rows)
        adjust_total = sum(r.adjust_qty or 0 for r in rows)
        scrap_adjust_total = sum(r.scrap_adjust_qty or 0 for r in rows)

        prev_day = get_prev_working_day(plan_date)
        prev_progress = progress_by_date.get(prev_day, last_progress)
        prev_planned_progress = planned_progress_by_date.get(prev_day, last_planned_progress)

        if not is_working_day(plan_date):
            progress_qty = prev_progress
            planned_progress_qty = prev_planned_progress
        else:
            progress_qty = (
                prev_progress
                + actual_total
                - progress_shipment
                + adjust_total
                + scrap_adjust_total
            )
            planned_progress_qty = (
                prev_planned_progress
                + plan_total
                - progress_shipment
                + adjust_total
                + scrap_adjust_total
            )

        rep = pick_representative(rows)
        for row in rows:
            row.progress_qty = 0
            row.planned_progress_qty = 0
        rep.progress_qty = progress_qty
        rep.planned_progress_qty = planned_progress_qty
        progress_by_date[plan_date] = progress_qty
        planned_progress_by_date[plan_date] = planned_progress_qty
        last_progress = progress_qty
        last_planned_progress = planned_progress_qty
        if plan_date == start_date:
            baseline_progress = progress_qty
        backlogs_to_update.extend(rows)

    if backlogs_to_update:
        LineBacklog.objects.bulk_update(backlogs_to_update, ['progress_qty', 'planned_progress_qty'])

    return baseline_progress


def _stocktake_recalc_stock(line_id, product_id, start_date, end_date,
                             firm_map, today, get_prev_working_day):
    """
    棚卸専用: 実在庫を日次で再計算。

    - is_stocktake_fix 行の stock_qty を起点とし、翌日以降を連鎖計算する
    - ガード条件なし（全日付を計算対象にする）
    """
    backlogs = list(LineBacklog.objects.filter(
        line_id=line_id,
        product_id=product_id,
        plan_date__range=[start_date, end_date],
    ).select_related('product').order_by('plan_date', 'sequence_no', 'id'))

    if not backlogs:
        return

    by_date = {}
    for b in backlogs:
        by_date.setdefault(b.plan_date, []).append(b)

    def pick_representative(rows):
        base_rows = [r for r in rows if r.sequence_no == 0]
        if base_rows:
            return min(base_rows, key=lambda r: r.id)
        return min(rows, key=lambda r: r.id)

    def pick_stocktake_anchor(rows):
        fix_rows = [r for r in rows if getattr(r, 'is_stocktake_fix', False)]
        if not fix_rows:
            return None
        seq0_fix_rows = [r for r in fix_rows if r.sequence_no == 0]
        candidates = seq0_fix_rows if seq0_fix_rows else fix_rows
        return min(candidates, key=lambda r: r.id)

    last_stock = 0
    stock_by_date = {}
    backlogs_to_update = []
    firm_map = firm_map or {}

    for plan_date in sorted(by_date.keys()):
        rows = by_date[plan_date]
        sample = rows[0]
        is_final = bool(getattr(sample.product, 'is_final_product', False))

        # 棚卸アンカー: is_stocktake_fix 行の値を起点として採用し、計算はスキップ
        anchor = pick_stocktake_anchor(rows)
        if anchor:
            stock_qty = anchor.stock_qty or 0
            stock_by_date[plan_date] = stock_qty
            last_stock = stock_qty
            rep = pick_representative(rows)
            for row in rows:
                row.actual_shipment_qty = 0
                row.stock_qty = 0
            rep.stock_qty = stock_qty
            backlogs_to_update.extend(rows)
            continue

        actual_total = sum(r.actual_qty or 0 for r in rows)
        scrap_adjust_total = sum(r.scrap_adjust_qty or 0 for r in rows)

        if plan_date <= today:
            if is_final:
                actual_shipment = firm_map.get((sample.product_id, plan_date), Decimal('0'))
            else:
                actual_shipment = _calculate_parent_actual_shipment(sample)
        else:
            actual_shipment = Decimal('0')
        actual_shipment = int(actual_shipment or 0)

        prev_day = get_prev_working_day(plan_date)
        prev_stock = stock_by_date.get(prev_day, last_stock)

        stock_qty = (
            prev_stock
            + actual_total
            - actual_shipment
            + scrap_adjust_total
        )

        rep = pick_representative(rows)
        for row in rows:
            row.actual_shipment_qty = 0
            row.stock_qty = 0
        rep.actual_shipment_qty = actual_shipment
        rep.stock_qty = stock_qty
        stock_by_date[plan_date] = stock_qty
        last_stock = stock_qty
        backlogs_to_update.extend(rows)

    if backlogs_to_update:
        LineBacklog.objects.bulk_update(backlogs_to_update, ['stock_qty', 'actual_shipment_qty'])


def _stocktake_recalc_planned_stock(line_id, product_id, start_date, end_date,
                                     firm_map, today, get_prev_working_day, shift_working_days,
                                     is_working_day=None):
    """
    棚卸専用: 計画在庫を日次で再計算。

    - is_stocktake_fix 行の planned_stock_qty を起点とし、翌日以降を連鎖計算する
    - ガード条件なし（全日付を計算対象にする）
    """
    backlogs = list(LineBacklog.objects.filter(
        line_id=line_id,
        product_id=product_id,
        plan_date__range=[start_date, end_date],
    ).select_related('product').order_by('plan_date', 'sequence_no', 'id'))

    if not backlogs:
        return

    by_date = {}
    for b in backlogs:
        by_date.setdefault(b.plan_date, []).append(b)

    def pick_representative(rows):
        base_rows = [r for r in rows if r.sequence_no == 0]
        if base_rows:
            return min(base_rows, key=lambda r: r.id)
        return min(rows, key=lambda r: r.id)

    def pick_stocktake_anchor(rows):
        fix_rows = [r for r in rows if getattr(r, 'is_stocktake_fix', False)]
        if not fix_rows:
            return None
        seq0_fix_rows = [r for r in fix_rows if r.sequence_no == 0]
        candidates = seq0_fix_rows if seq0_fix_rows else fix_rows
        return min(candidates, key=lambda r: r.id)

    last_planned = 0
    planned_by_date = {}
    backlogs_to_update = []
    firm_map = firm_map or {}
    step_cache = {}

    for plan_date in sorted(by_date.keys()):
        rows = by_date[plan_date]
        sample = rows[0]

        # 棚卸アンカー: is_stocktake_fix 行の値を起点として採用
        anchor = pick_stocktake_anchor(rows)
        if anchor:
            planned_stock = anchor.planned_stock_qty or 0
            rep = pick_representative(rows)
            for row in rows:
                row.planned_stock_qty = 0
            rep.planned_stock_qty = planned_stock
            backlogs_to_update.extend(rows)
            planned_by_date[plan_date] = planned_stock
            last_planned = planned_stock
            continue

        plan_total = sum(r.plan_qty or 0 for r in rows)
        actual_total = sum(r.actual_qty or 0 for r in rows)
        order_total = sum(r.order_qty or 0 for r in rows)

        is_final = bool(getattr(sample.product, 'is_final_product', False))
        is_line_final = bool(getattr(sample.product, 'is_line_final_product', False))
        if is_final:
            firm_qty = firm_map.get((sample.product_id, plan_date), Decimal('0'))
            if plan_date <= today:
                planned_shipment = firm_qty
            else:
                planned_shipment = firm_qty if firm_qty > 0 else Decimal(str(order_total))
        elif is_line_final or bool(getattr(sample.product, 'is_purchase_product', False)) or getattr(sample, 'process_code', '') == 'PURCHASE':
            # is_line_final または 購入品の場合
            # LT後の日付が過去なら親の実績(Planフォールバックなし)、そうでなければ計需（order_total）
            # LTは親BOMの最大LTを使用する（最も遅い消費に合わせる）
            lt_days = _resolve_stocktake_lead_time_days(line_id, product_id, step_cache=step_cache)
            if lt_days == 0:
                lt_days = _get_max_parent_bom_lead_time(product_id)
            lt_shifted_date = shift_working_days(plan_date, lt_days)
            if lt_shifted_date < today:
                planned_shipment = _stocktake_calculate_parent_actual_shipment_only(
                    sample,
                    shift_fn=shift_working_days,
                    step_cache=step_cache,
                )
            else:
                planned_shipment = Decimal(str(order_total))
        else:
            # その他（通常の中間品）: 従来通り
            # 過去は実績のみ(Planフォールバックなし)、未来は計画
            lt_days = _resolve_stocktake_lead_time_days(line_id, product_id, step_cache=step_cache)
            lt_shifted_date = shift_working_days(plan_date, lt_days)
            if lt_shifted_date < today:
                planned_shipment = _stocktake_calculate_parent_actual_shipment_only(
                    sample,
                    shift_fn=shift_working_days,
                    step_cache=step_cache,
                )
            else:
                planned_shipment = _stocktake_calculate_parent_planned_shipment(
                    sample,
                    today,
                    shift_working_days,
                    step_cache=step_cache,
                )
        planned_shipment = int(planned_shipment or 0)

        prev_day = get_prev_working_day(plan_date)
        prev_planned = planned_by_date.get(prev_day, last_planned)

        # 非稼働日はキャリーフォワード
        if is_working_day is not None and not is_working_day(plan_date):
            planned_stock = prev_planned
        elif plan_date < today:
            planned_stock = prev_planned + actual_total - planned_shipment
        else:
            planned_stock = prev_planned + plan_total - planned_shipment

        rep = pick_representative(rows)
        for row in rows:
            row.planned_stock_qty = 0
        rep.planned_stock_qty = planned_stock
        planned_by_date[plan_date] = planned_stock
        last_planned = planned_stock
        backlogs_to_update.extend(rows)

    if backlogs_to_update:
        LineBacklog.objects.bulk_update(backlogs_to_update, ['planned_stock_qty'])


def initialize_progress_from_stocktake(baseline_date):
    """
    棚卸在庫から進度(progress_qty, planned_progress_qty)を初期化する

    計算順序（トポロジカルソート: BOM階層の上位→下位）:
    1. 最終品(is_final_product): 進度 = stock_qty（在庫がそのまま需要に対する先行分）
    2. 子部品: 進度 = stock_qty + Σ(親製品の進度 × BOM数量)
       - 親の進度分は子部品を既に消費済みなので加算する
       - 親が複数ラインにまたがる場合は全ライン合算

    Args:
        baseline_date: 棚卸基準日 (date)

    Returns:
        dict: { updated_count, final_count, child_count }
    """
    from masters.models import BOMItem, Product

    # 1. baseline_date の代表行（sequence_no=0）を取得
    backlogs = list(LineBacklog.objects.filter(
        plan_date=baseline_date,
        sequence_no=0,
    ).select_related('product'))

    if not backlogs:
        logger.warning("initialize_progress: baseline_date=%s にline_backlog行が見つかりません", baseline_date)
        return {'updated_count': 0, 'final_count': 0, 'child_count': 0}

    # product_id → [backlog, ...] のマップ（複数ラインにまたがる場合があるため）
    product_backlogs = defaultdict(list)
    for bl in backlogs:
        product_backlogs[bl.product_id].append(bl)

    target_product_ids = set(product_backlogs.keys())
    logger.info("initialize_progress: 対象製品数=%d, baseline_date=%s", len(target_product_ids), baseline_date)

    # 2. 対象製品間のBOM関係を取得（parent → child）
    bom_items = list(BOMItem.objects.filter(
        bom__is_active=True,
        bom__is_coproduct=False,
        bom__parent_product_id__in=target_product_ids,
        child_product_id__in=target_product_ids,
    ).select_related('bom'))

    # parent → [(child_id, qty), ...] と child → [(parent_id, qty), ...] のマップ
    parent_to_children = defaultdict(list)
    child_to_parents = defaultdict(list)
    for item in bom_items:
        parent_id = item.bom.parent_product_id
        child_id = item.child_product_id
        qty = item.quantity or Decimal('0')
        parent_to_children[parent_id].append((child_id, qty))
        child_to_parents[child_id].append((parent_id, qty))

    # 3. トポロジカルソート（BOM上位 → 下位）
    # in_degree = 親の数（対象製品内での）
    in_degree = defaultdict(int)
    for pid in target_product_ids:
        in_degree[pid] = 0
    for item in bom_items:
        child_id = item.child_product_id
        in_degree[child_id] += 1

    # ルート = in_degree が 0 の製品（最終品、または対象内に親がない製品）
    queue = deque()
    for pid in target_product_ids:
        if in_degree[pid] == 0:
            queue.append(pid)

    sorted_products = []
    while queue:
        pid = queue.popleft()
        sorted_products.append(pid)
        for child_id, _qty in parent_to_children.get(pid, []):
            in_degree[child_id] -= 1
            if in_degree[child_id] == 0:
                queue.append(child_id)

    # 循環チェック
    if len(sorted_products) < len(target_product_ids):
        missing = target_product_ids - set(sorted_products)
        logger.warning("initialize_progress: BOM循環の可能性あり。未処理製品: %s", missing)
        # 未処理製品も追加（循環は無視して処理を続行）
        sorted_products.extend(missing)

    # 4. 最終品フラグを取得
    final_flags = dict(
        Product.objects.filter(id__in=target_product_ids)
        .values_list('id', 'is_final_product')
    )

    # 5. 上位→下位の順で進度を計算
    # product_id → 全ライン合算の progress_qty
    progress_map = {}
    final_count = 0
    child_count = 0

    for pid in sorted_products:
        bl_list = product_backlogs.get(pid, [])
        if not bl_list:
            continue

        # 全ラインの stock_qty を合算
        total_stock = sum(bl.stock_qty or 0 for bl in bl_list)
        is_final = final_flags.get(pid, False)

        if is_final or pid not in child_to_parents:
            # 最終品、またはBOM上の親がない製品: 進度 = 在庫
            progress = total_stock
            final_count += 1
        else:
            # 子部品: 進度 = 在庫 + Σ(親の進度 × BOM数量)
            # 親の進度分は既に子部品を消費済み → 子の実質生産量は在庫+消費分
            parent_consumed = Decimal('0')
            for parent_id, bom_qty in child_to_parents[pid]:
                parent_progress = progress_map.get(parent_id, 0)
                parent_consumed += Decimal(str(parent_progress)) * bom_qty
            progress = total_stock + int(parent_consumed)
            child_count += 1

        progress_map[pid] = progress

        # 各ラインの代表行に進度を按分ではなく同値でセット
        # （ライン別の在庫に応じた按分は通常運用の再計算が行う）
        for bl in bl_list:
            bl.progress_qty = progress
            bl.planned_progress_qty = progress

    # 6. 一括更新
    if backlogs:
        LineBacklog.objects.bulk_update(backlogs, ['progress_qty', 'planned_progress_qty'])

    updated_count = final_count + child_count
    logger.info(
        "initialize_progress: 完了 updated=%d (最終品=%d, 子部品=%d)",
        updated_count, final_count, child_count
    )
    return {
        'updated_count': updated_count,
        'final_count': final_count,
        'child_count': child_count,
    }


def calculate_pipeline_demand(
    product_id,
    baseline_date,
    line_id=None,
    today=None,
    firm_map=None,
    final_flags=None,
):
    """
    計画在庫初期化用：パイプライン需要（LT期間中の親の需要）を計算する
    
    計画在庫(t) = 実在庫(t) - パイプライン需要
    パイプライン需要 = Σ(親iの需要(t + k)) for k in 1..LT_i
    """
    from masters.models import Calendar, CalendarDay, BOMItem, Product

    # カレンダー関連の準備（shift_working_days用）
    # 簡易的にdaisoカレンダーを使用（inventory_calculatorと同様）
    calendar_id = Calendar.objects.filter(calendar_code='daiso').values_list('id', flat=True).first()
    workday_cache = {}
    
    def is_working_day(target_date):
        if not calendar_id: return target_date.weekday() < 5
        if target_date in workday_cache: return workday_cache[target_date]
        cal = CalendarDay.objects.filter(calendar_id=calendar_id, target_date=target_date).first()
        res = cal.is_working_day if cal else target_date.weekday() < 5
        workday_cache[target_date] = res
        return res

    def shift_working_days(target_date, days):
        if not days: return target_date
        step = 1 if days > 0 else -1
        remaining = abs(int(days))
        current = target_date
        while remaining > 0:
            current = current + timedelta(days=step)
            if is_working_day(current):
                remaining -= 1
        return current

    # 先に製品区分を判定（最終品/ライン最終品は自需要をパイプライン需要として扱う）
    is_final = False
    is_line_final = False
    if final_flags and product_id in final_flags:
        is_final = bool(final_flags[product_id].get('is_final_product', False))
        is_line_final = bool(final_flags[product_id].get('is_line_final_product', False))
    else:
        product_flags = Product.objects.filter(id=product_id).values(
            'is_final_product',
            'is_line_final_product',
        ).first() or {}
        is_final = bool(product_flags.get('is_final_product', False))
        is_line_final = bool(product_flags.get('is_line_final_product', False))

    # 親BOMを取得（複数親対応）
    parent_bom_items = BOMItem.objects.filter(
        child_product_id=product_id,
        bom__is_active=True,
        bom__is_coproduct=False
    ).select_related('bom__parent_product')
    
    has_parents = parent_bom_items.exists()

    # 最終品、または (ライン最終品 かつ 親がいない場合): 基準日+1..+LT の自需要を積算
    if is_final or (is_line_final and not has_parents):
        lt = _resolve_final_product_lt_days(line_id, product_id)
        if lt <= 0:
            return 0

        if today is None:
            today = get_business_today()
        firm_map = firm_map or {}

        total_demand = Decimal('0')
        for k in range(1, lt + 1):
            target_date = shift_working_days(baseline_date, k)

            demand_qs = LineBacklog.objects.filter(
                product_id=product_id,
                plan_date=target_date,
                sequence_no=0,
            )
            if line_id is not None:
                demand_qs = demand_qs.filter(line_id=line_id)

            order_total = demand_qs.aggregate(total=Sum('order_qty')).get('total') or 0
            firm_qty = Decimal(str(firm_map.get((product_id, target_date), 0) or 0))

            if is_final:
                # 通常計算と同じ扱い:
                # 過去/今日=firmのみ、将来=firm優先で無ければorder
                if target_date <= today:
                    use_qty = firm_qty
                else:
                    use_qty = firm_qty if firm_qty > 0 else Decimal(str(order_total))
            else:
                # ライン最終品: 過去/今日は実需(firm_qty)優先、将来はorder_qty
                if target_date <= today:
                    use_qty = firm_qty if firm_qty > 0 else Decimal(str(order_total))
                else:
                    use_qty = Decimal(str(order_total))

            total_demand += use_qty

        return int(total_demand)

    if today is None:
        today = get_business_today()

    total_demand = Decimal('0')
    step_cache = {}

    for bom_item in parent_bom_items:
        parent_product = bom_item.bom.parent_product
        if not parent_product:
            continue
        
        qty_per = bom_item.quantity or Decimal('0')
        if qty_per == 0:
            continue
            
        lt = _resolve_stocktake_lead_time_days(
            line_id,
            product_id,
            bom_item=bom_item,
            step_cache=step_cache,
        )
        if lt == 0:
            continue
            
        # この親に対して、LT日数分だけ未来の需要を積算する
        for k in range(1, lt + 1):
            target_date = shift_working_days(baseline_date, k)
            
            # 親の計画/実績を取得
            # 複数ラインで生産されている可能性も考慮して合算
            parent_backlogs = LineBacklog.objects.filter(
                product_id=parent_product.id,
                plan_date=target_date
            )
            
            parent_daily_demand = Decimal('0')
            # scrapは(line_id, process_id)単位で1回だけ取得する
            # sequence_noが複数ある場合に同じScrapRecordが重複カウントされるのを防ぐ
            scrap_counted_keys = set()
            for bl in parent_backlogs:
                # 実績があれば実績+仕損、なければ計画を採用
                actual = bl.actual_qty or 0
                key = (bl.line_id, bl.process_id)
                if key not in scrap_counted_keys:
                    scrap = _get_shipment_scrap_qty(
                        bl.product_id, bl.line_id, bl.process_id, bl.plan_date
                    )
                    scrap_counted_keys.add(key)
                else:
                    scrap = Decimal('0')
                if target_date < today:
                    use_qty = actual + scrap
                else:
                    if actual > 0 or scrap > 0:
                        use_qty = actual + scrap
                    else:
                        use_qty = bl.plan_qty or 0
                parent_daily_demand += Decimal(str(use_qty))
            
            total_demand += parent_daily_demand * qty_per

    return int(total_demand)


def initialize_planned_stock(line_ids, baseline_date):
    """
    指定ライン・基準日の計画在庫を初期化する。
    実在庫からパイプライン需要を差し引いた値を planned_stock_qty にセットする。
    """
    target_backlogs = LineBacklog.objects.filter(
        line_id__in=line_ids,
        plan_date=baseline_date,
        is_stocktake_fix=True
    )

    backlogs = list(target_backlogs.select_related('product'))
    if not backlogs:
        logger.info("initialize_planned_stock: no target backlogs on %s", baseline_date)
        return 0

    today = get_business_today()
    line_ids_used = sorted({bl.line_id for bl in backlogs if bl.line_id is not None})

    # 最終品のfirm需要をライン単位でキャッシュ
    line_firm_map = {}
    for line_id in line_ids_used:
        line_products = [bl for bl in backlogs if bl.line_id == line_id]
        max_lt = 0
        lt_cache = {}
        for bl in line_products:
            lt_days = _resolve_stocktake_lead_time_days(
                line_id,
                bl.product_id,
                step_cache=lt_cache,
            )
            if lt_days > max_lt:
                max_lt = lt_days
        # 余裕を持って先の日付までfirm需要を取得
        firm_end = baseline_date + timedelta(days=max_lt + 30)
        line_firm_map[line_id] = _build_firm_order_map(line_id, baseline_date, firm_end)

    final_flags = {
        bl.product_id: {
            'is_final_product': bool(getattr(bl.product, 'is_final_product', False)),
            'is_line_final_product': bool(getattr(bl.product, 'is_line_final_product', False)),
        }
        for bl in backlogs
    }

    updated_count = 0
    for bl in backlogs:
        pipeline = calculate_pipeline_demand(
            bl.product_id,
            baseline_date,
            line_id=bl.line_id,
            today=today,
            firm_map=line_firm_map.get(bl.line_id, {}),
            final_flags=final_flags,
        )
        # 計画在庫 = 実在庫 - パイプライン需要
        new_planned = (bl.stock_qty or 0) - pipeline
        
        if bl.planned_stock_qty != new_planned:
            bl.planned_stock_qty = new_planned
            bl.save(update_fields=['planned_stock_qty'])
            updated_count += 1
            
    logger.info("initialize_planned_stock: updated %d records on %s", updated_count, baseline_date)
    return updated_count
