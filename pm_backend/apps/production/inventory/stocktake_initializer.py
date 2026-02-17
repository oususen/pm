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
from django.db.models import Q
from .inventory_calculator import (
    _get_max_parent_bom_lead_time,
    _calculate_parent_actual_shipment,
    _calculate_parent_actual_or_plan_shipment,
    _calculate_parent_planned_shipment,
    _get_shipment_scrap_qty,
    aggregate_scrap_to_backlog,
    _build_firm_order_map,
)

logger = logging.getLogger(__name__)


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

    step_qs = RoutingStep.objects.filter(
        routing__is_active=True,
        line_id__isnull=False,
    ).filter(
        Q(output_product_id__in=target_product_ids) |
        Q(output_product_id__isnull=True, routing__product_id__in=target_product_ids)
    ).select_related('routing')

    unique_keys = set()
    mapped_product_ids = set()
    for step in step_qs:
        target_product_id = step.output_product_id or step.routing.product_id
        if target_product_id not in stock_by_product_id:
            continue
        key = (step.process_id, target_product_id, step.line_id)
        unique_keys.add(key)
        mapped_product_ids.add(target_product_id)

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
                'planned_stock_qty': stock_int,
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
            obj.planned_stock_qty = stock_int
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
        )

    return {
        'line_id': line_id,
        'product_count': len(product_ids),
    }


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
        return min(base_rows, key=lambda r: r.id)

    last_stock = 0
    stock_by_date = {}
    backlogs_to_update = []
    firm_map = firm_map or {}

    for plan_date in sorted(by_date.keys()):
        rows = by_date[plan_date]
        sample = rows[0]
        is_final = bool(getattr(sample.product, 'is_final_product', False))

        # 棚卸アンカー: この値を起点として採用し、計算はスキップ
        if any(getattr(r, 'is_stocktake_fix', False) for r in rows):
            stock_qty = sample.stock_qty or 0
            stock_by_date[plan_date] = stock_qty
            last_stock = stock_qty
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
                                     firm_map, today, get_prev_working_day, shift_working_days):
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
        return min(base_rows, key=lambda r: r.id)

    last_planned = 0
    planned_by_date = {}
    backlogs_to_update = []
    firm_map = firm_map or {}

    for plan_date in sorted(by_date.keys()):
        rows = by_date[plan_date]
        sample = rows[0]

        # 棚卸アンカー: この値を起点として採用
        if any(getattr(r, 'is_stocktake_fix', False) for r in rows):
            planned_stock = sample.planned_stock_qty or 0
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
        elif is_line_final:
            planned_shipment = Decimal(str(order_total))
        else:
            if plan_date < today:
                planned_shipment = _calculate_parent_actual_or_plan_shipment(sample, shift_working_days)
            else:
                planned_shipment = _calculate_parent_planned_shipment(sample, today, shift_working_days)
        planned_shipment = int(planned_shipment or 0)

        prev_day = get_prev_working_day(plan_date)
        prev_planned = planned_by_date.get(prev_day, last_planned)

        if plan_date < today:
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


def calculate_pipeline_demand(product_id, baseline_date):
    """
    計画在庫初期化用：パイプライン需要（LT期間中の親の需要）を計算する
    
    計画在庫(t) = 実在庫(t) - パイプライン需要
    パイプライン需要 = Σ(親iの需要(t + k)) for k in 1..LT_i
    """
    from masters.models import Calendar, CalendarDay, BOMItem

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

    # 親BOMを取得（複数親対応）
    parent_bom_items = BOMItem.objects.filter(
        child_product_id=product_id,
        bom__is_active=True,
        bom__is_coproduct=False
    ).select_related('bom__parent_product')

    total_demand = Decimal('0')
    
    for bom_item in parent_bom_items:
        parent_product = bom_item.bom.parent_product
        if not parent_product:
            continue
        
        qty_per = bom_item.quantity or Decimal('0')
        if qty_per == 0:
            continue
            
        lt = bom_item.lead_time_days or 0
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
            for bl in parent_backlogs:
                # 実績があれば実績+仕損、なければ計画を採用
                actual = bl.actual_qty or 0
                scrap = _get_shipment_scrap_qty(
                    bl.product_id, bl.line_id, bl.process_id, bl.plan_date
                )
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
    
    updated_count = 0
    for bl in target_backlogs:
        pipeline = calculate_pipeline_demand(bl.product_id, baseline_date)
        # 計画在庫 = 実在庫 - パイプライン需要
        new_planned = (bl.stock_qty or 0) - pipeline
        
        if bl.planned_stock_qty != new_planned:
            bl.planned_stock_qty = new_planned
            bl.save(update_fields=['planned_stock_qty'])
            updated_count += 1
            
    logger.info("initialize_planned_stock: updated %d records on %s", updated_count, baseline_date)
    return updated_count
