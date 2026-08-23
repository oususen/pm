from datetime import timedelta

from masters.models import Calendar, CalendarDay, Line
from orders.utils.calendar_utils import get_business_today
from production.models_line_backlog import LineBacklog


def _resolve_calendar_id(line_id):
    line_obj = Line.objects.filter(id=line_id).first()
    return getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(
        calendar_code='daiso'
    ).values_list('id', flat=True).first()


def _build_workday_helpers(calendar_id):
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

    return is_working_day, get_prev_working_day, shift_working_days


def resolve_inventory_effective_start_date(
    line_id,
    requested_start_date,
    end_date,
    product_ids=None,
    line_final_only=False,
    include_progress=False,
):
    from production.inventory.inventory_calculator import (
        _get_direct_parent_bom_lead_time,
        _get_max_parent_bom_lead_time,
    )

    calendar_id = _resolve_calendar_id(line_id)
    is_working_day, get_prev_working_day, shift_working_days = _build_workday_helpers(calendar_id)

    today = get_business_today()
    if not is_working_day(today):
        today = get_prev_working_day(today)
    stock_start_dt = get_prev_working_day(get_prev_working_day(today))

    target_product_ids = sorted({int(pid) for pid in (product_ids or []) if pid is not None})
    if target_product_ids:
        product_ids_for_line = target_product_ids
    else:
        product_qs = LineBacklog.objects.filter(
            line_id=line_id,
            plan_date__lte=end_date,
        )
        if line_final_only:
            product_qs = product_qs.filter(product__is_line_final_product=True)
        product_ids_for_line = list(product_qs.values_list('product_id', flat=True).distinct())

    # LT使い分け: 在庫=直親LT / 進度=累積LT（batch_adjust_info・progress_calculator と統一）
    lt_func = _get_max_parent_bom_lead_time if include_progress else _get_direct_parent_bom_lead_time
    max_lt = 0
    if product_ids_for_line:
        max_lt = max(
            (int(lt_func(pid) or 0) for pid in product_ids_for_line),
            default=0,
        )
    inventory_start_dt = shift_working_days(today, -(int(max_lt) + 1))
    return min(requested_start_date, stock_start_dt, inventory_start_dt)


def resolve_product_recalc_start_date(line_id, end_date, product_ids=None, progress_only=False):
    """
    表示品番だけ再計算用の内部開始日を返す。
    画面の表示開始日は使わず、計算上必要な開始日だけを採用する。
    在庫は直親LT、進度は累積LTを使用。
    """
    from production.inventory.inventory_calculator import (
        _get_direct_parent_bom_lead_time,
        _get_max_parent_bom_lead_time,
    )

    calendar_id = _resolve_calendar_id(line_id)
    is_working_day, get_prev_working_day, shift_working_days = _build_workday_helpers(calendar_id)

    today = get_business_today()
    if not is_working_day(today):
        today = get_prev_working_day(today)
    stock_start_dt = get_prev_working_day(get_prev_working_day(today))

    target_product_ids = sorted({int(pid) for pid in (product_ids or []) if pid is not None})
    if target_product_ids:
        product_ids_for_line = target_product_ids
    else:
        product_ids_for_line = list(
            LineBacklog.objects.filter(
                line_id=line_id,
                plan_date__lte=end_date,
            ).values_list('product_id', flat=True).distinct()
        )

    # LT使い分け: 在庫=直親LT / 進度=累積LT（batch_adjust_info・progress_calculator と統一）
    # 棚卸初期化(stocktake_initializer.py)は独自ロジックのため影響なし
    lt_func = _get_max_parent_bom_lead_time if progress_only else _get_direct_parent_bom_lead_time
    max_lt = 0
    if product_ids_for_line:
        max_lt = max(
            (int(lt_func(pid) or 0) for pid in product_ids_for_line),
            default=0,
        )
    inventory_start_dt = shift_working_days(today, -(int(max_lt) + 1))
    return min(stock_start_dt, inventory_start_dt)
