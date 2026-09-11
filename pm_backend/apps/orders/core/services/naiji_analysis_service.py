"""汎用内示分析サービス

StgOrderDaily (order_type='FORECAST') を共通データソースとし、
顧客を問わず内示の変化推移・安全在庫分析を行う。
"""
import re
import statistics
from collections import Counter, defaultdict
from datetime import date, timedelta

from django.db.models import Sum

from masters.models import Calendar, Customer
from orders.core.models import Order, OrderLine, StgOrderDaily
from orders.utils.calendar_utils import WorkingDayCalculator


def _get_customer_calendar(customer):
    """顧客に紐づくカレンダーを取得（なければ daiso フォールバック）"""
    if customer and customer.calendar:
        return customer.calendar
    try:
        return Calendar.objects.get(calendar_code='daiso')
    except Calendar.DoesNotExist:
        return None


def _extract_firm_issue_date(order_no, customer_code):
    """注文番号から確定発行日を抽出（顧客別ロジック）

    Kubota (000196): FIRM-000196-{FACTORY}-{YYMMDD} → 6桁YYMMDD
    Rieden: FIRM-{code}-{YYYYMMDD} → 8桁YYYYMMDD
    Tiera/その他: FIRM-{code}-{delivery_no or timestamp} → 14桁timestamp
    """
    parts = re.split(r'[-_]', str(order_no or ''))
    if len(parts) < 3:
        return None

    if customer_code == '000196':
        for part in parts[2:]:
            s = part.strip()
            if len(s) == 6 and s.isdigit():
                try:
                    return date(2000 + int(s[:2]), int(s[2:4]), int(s[4:6]))
                except ValueError:
                    pass

    for part in parts[2:]:
        s = part.strip()
        if len(s) == 8 and s.isdigit():
            try:
                return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
            except ValueError:
                pass

    for part in parts[2:]:
        s = part.strip()
        if len(s) == 14 and s.isdigit():
            try:
                return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
            except ValueError:
                pass

    return None


def _count_working_days(wdc, d_from, d_to):
    if d_from == d_to:
        return 0
    step = 1 if d_to > d_from else -1
    count = 0
    cur = d_from + timedelta(days=step)
    while cur != d_to + timedelta(days=step):
        if wdc.is_working_day(cur):
            count += step
        cur += timedelta(days=step)
    return count


# ---------------------------------------------------------------------------
# 顧客一覧
# ---------------------------------------------------------------------------
def get_naiji_customers():
    """内示データがある顧客一覧を返す"""
    customer_ids = (
        StgOrderDaily.objects
        .filter(order_type='FORECAST')
        .values_list('customer_id', flat=True)
        .distinct()
    )
    customers = Customer.objects.filter(id__in=customer_ids, is_active=True).order_by('customer_code')
    return [
        {
            'id': c.id,
            'customer_code': c.customer_code,
            'customer_name': c.customer_name or '',
            'short_name': c.short_name or '',
        }
        for c in customers
    ]


# ---------------------------------------------------------------------------
# 製品一覧
# ---------------------------------------------------------------------------
def get_naiji_products(customer_id):
    """指定顧客の内示製品一覧（Order→OrderLineで高速取得）"""
    order_ids = list(
        Order.objects
        .filter(customer_id=customer_id, order_type='FORECAST')
        .values_list('id', flat=True)
    )
    if not order_ids:
        return []

    product_codes = set()
    ship_to_map = defaultdict(set)
    for row in (
        OrderLine.objects
        .filter(order_id__in=order_ids)
        .values('product_code', 'ship_to_code')
        .distinct()
    ):
        product_codes.add(row['product_code'])
        if row['ship_to_code']:
            ship_to_map[row['product_code']].add(row['ship_to_code'])

    product_names = {}
    from masters.models import Product
    for p in Product.objects.filter(
        product_code__in=list(product_codes)
    ).values('product_code', 'product_name'):
        product_names[p['product_code']] = p['product_name'] or ''

    return sorted([
        {
            'product_code': pc,
            'product_name': product_names.get(pc, ''),
            'snapshot_count': None,
            'latest_date': None,
            'ship_to_list': sorted(ship_to_map.get(pc, [])),
        }
        for pc in product_codes
    ], key=lambda x: x['product_code'])


# ---------------------------------------------------------------------------
# 共通データ構築
# ---------------------------------------------------------------------------
def _build_product_data(customer_id, product_code, ship_to='', start_date=None, end_date=None, snapshot_start_date=None):
    """スナップショット・確定データの構築（全分析関数の共通基盤）

    Returns:
        dict with keys:
            snapshots_map, snapshot_dates, ordered_files, all_due_dates,
            firm_quantities, firm_dates, wdc, customer_code, product_name
    """
    customer = Customer.objects.select_related('calendar').filter(id=customer_id).first()
    cal = _get_customer_calendar(customer)
    wdc = WorkingDayCalculator(cal)
    customer_code = customer.customer_code if customer else ''
    customer_name = customer.customer_name if customer else ''

    product_name = ''
    first = (
        StgOrderDaily.objects
        .filter(customer_id=customer_id, product_code=product_code, order_type='FORECAST')
        .values('product_name')
        .first()
    )
    if first:
        product_name = first['product_name'] or ''

    qs = (
        StgOrderDaily.objects
        .filter(customer_id=customer_id, product_code=product_code, order_type='FORECAST')
        .order_by('created_at', 'id')
    )
    if ship_to:
        qs = qs.filter(ship_to_code=ship_to)

    snapshots_map = {}
    snapshot_dates = {}
    for row in qs:
        sf = row.source_file
        if not sf:
            continue
        if sf not in snapshot_dates:
            snapshot_dates[sf] = row.created_at
        if snapshot_start_date and snapshot_dates[sf].date() < snapshot_start_date:
            continue
        ds = row.due_date.isoformat()
        if start_date and row.due_date < start_date:
            continue
        if end_date and row.due_date > end_date:
            continue
        if sf not in snapshots_map:
            snapshots_map[sf] = {}
        qty = float(row.quantity or 0)
        snapshots_map[sf][ds] = snapshots_map[sf].get(ds, 0.0) + qty

    all_due_dates = sorted({
        ds
        for qtys in snapshots_map.values()
        for ds in qtys.keys()
        if wdc.is_working_day(date.fromisoformat(ds))
    })
    ordered_files = sorted(snapshots_map.keys(), key=lambda f: snapshot_dates[f])

    firm_qs = OrderLine.objects.filter(
        order__order_type='FIRM', order__status='OPEN',
        order__customer_id=customer_id, product_code=product_code,
    )
    if ship_to:
        firm_qs = firm_qs.filter(ship_to_code=ship_to)
    if start_date:
        firm_qs = firm_qs.filter(due_date__gte=start_date)
    if end_date:
        firm_qs = firm_qs.filter(due_date__lte=end_date)

    firm_quantities = {}
    for row in firm_qs.values('due_date').annotate(total_qty=Sum('quantity')):
        firm_quantities[row['due_date'].isoformat()] = float(row['total_qty'])

    firm_dates = {}
    for line in firm_qs.select_related('order').only('due_date', 'order__order_no', 'order__order_date'):
        issue_date_obj = _extract_firm_issue_date(line.order.order_no, customer_code)
        if issue_date_obj is None:
            issue_date_obj = line.order.order_date
        if issue_date_obj is None:
            continue
        ds = line.due_date.isoformat()
        if ds not in firm_dates or issue_date_obj > date.fromisoformat(firm_dates[ds]):
            firm_dates[ds] = issue_date_obj.isoformat()

    return {
        'snapshots_map': snapshots_map,
        'snapshot_dates': snapshot_dates,
        'ordered_files': ordered_files,
        'all_due_dates': all_due_dates,
        'firm_quantities': firm_quantities,
        'firm_dates': firm_dates,
        'wdc': wdc,
        'customer_code': customer_code,
        'customer_name': customer_name,
        'product_name': product_name,
    }


# ---------------------------------------------------------------------------
# メイン分析
# ---------------------------------------------------------------------------
def compute_naiji_analysis(customer_id, product_code, start_date=None, end_date=None, ship_to=''):
    """内示変化推移分析データを計算して返す（汎用版）"""
    pd = _build_product_data(customer_id, product_code, ship_to, start_date, end_date)
    snapshots_map = pd['snapshots_map']
    snapshot_dates = pd['snapshot_dates']
    ordered_files = pd['ordered_files']
    all_due_dates = pd['all_due_dates']
    firm_quantities = pd['firm_quantities']
    firm_dates = pd['firm_dates']
    wdc = pd['wdc']

    snapshots = [
        {
            'source_file': sf,
            'snapshot_date': snapshot_dates[sf].date().isoformat(),
            'quantities': snapshots_map[sf],
        }
        for sf in ordered_files
    ]

    # --- 統計計算（納期ごと）---
    stat_results = {}
    for ds in all_due_dates:
        _raw = [snapshots_map[sf][ds] for sf in ordered_files if ds in snapshots_map[sf]]
        _first_pos = next((i for i, q in enumerate(_raw) if q > 0), None)
        qty_series = _raw[_first_pos:] if _first_pos is not None else []
        if not qty_series:
            continue

        mean_val = sum(qty_series) / len(qty_series)
        std_val = statistics.stdev(qty_series) if len(qty_series) >= 2 else 0.0
        min_val = min(qty_series)
        max_val = max(qty_series)
        first_qty = qty_series[0]
        last_qty = qty_series[-1]
        firm_qty = firm_quantities.get(ds)

        stat_results[ds] = {
            'count': len(qty_series),
            'mean': round(mean_val, 2),
            'std_dev': round(std_val, 2),
            'min': min_val,
            'max': max_val,
            'range': round(max_val - min_val, 2),
            'cv': round(std_val / mean_val * 100, 2) if mean_val else 0.0,
            'first_qty': first_qty,
            'last_qty': last_qty,
            'first_to_last_change': round(last_qty - first_qty, 2),
            'first_to_last_pct': round((last_qty - first_qty) / first_qty * 100, 1) if first_qty else None,
            'firm_qty': firm_qty,
            'last_vs_firm': round(last_qty - firm_qty, 2) if firm_qty is not None else None,
            'last_vs_firm_pct': round((last_qty - firm_qty) / firm_qty * 100, 1) if firm_qty else None,
        }

    # --- 期間サマリー ---
    period_summary = _compute_period_summary(
        all_due_dates, snapshots_map, ordered_files, snapshot_dates,
        firm_quantities, firm_dates, wdc,
    )

    return {
        'product_code': product_code,
        'due_dates': all_due_dates,
        'snapshots': snapshots,
        'firm_quantities': firm_quantities,
        'firm_dates': firm_dates,
        'converge_dates': period_summary.pop('converge_dates', {}),
        'statistics': stat_results,
        'period_summary': period_summary,
    }


def _compute_period_summary(all_due_dates, snapshots_map, ordered_files, snapshot_dates,
                            firm_quantities, firm_dates, wdc):
    """期間全体サマリー（安全在庫分析）を計算"""
    all_errors = []
    date_max_shortages = []
    n_dates_with_firm = 0
    n_dates_shortage = 0
    _max_diff_val = _max_diff_date = _min_diff_val = _min_diff_date = None

    for ds in all_due_dates:
        firm_qty = firm_quantities.get(ds)
        if firm_qty is None:
            continue
        n_dates_with_firm += 1
        _raw = [snapshots_map[sf][ds] for sf in ordered_files if ds in snapshots_map[sf]]
        qty_series = [q for q in _raw if q > 0]
        if not qty_series:
            continue
        has_shortage = False
        _date_worst = 0.0
        for q in qty_series:
            err = q - firm_qty
            all_errors.append(err)
            if _max_diff_val is None or err > _max_diff_val:
                _max_diff_val = err
                _max_diff_date = ds
            if _min_diff_val is None or err < _min_diff_val:
                _min_diff_val = err
                _min_diff_date = ds
            if q < firm_qty:
                has_shortage = True
                s = firm_qty - q
                if s > _date_worst:
                    _date_worst = s
        if _date_worst > 0:
            date_max_shortages.append((round(_date_worst, 1), ds))
        if has_shortage:
            n_dates_shortage += 1

    # --- 収束安定期間 ---
    stable_days_list = []
    converge_dates = {}
    pre_converge_shortage_count = 0
    pre_converge_shortage_dates = []
    n_converge_total = 0
    firm_due_lt5_count = 0
    firm_due_lt5_total = 0
    firm_converge_on_or_after_firm_count = 0
    firm_converge_on_or_after_firm_total = 0
    firm_converge_on_or_after_firm_dates_list = []

    firm_stable_days_list = []
    firm_delay_count = 0
    firm_delay_total = 0

    for ds in all_due_dates:
        firm_qty = firm_quantities.get(ds)
        if firm_qty is None:
            continue
        due_date_obj = date.fromisoformat(ds)
        current_streak_start = None
        prev_qty = None
        for sf in ordered_files:
            if ds not in snapshots_map[sf]:
                continue
            qty = snapshots_map[sf][ds]
            if qty <= 0:
                continue
            snap_date = snapshot_dates[sf].date()
            if abs(qty - firm_qty) < 0.5:
                if current_streak_start is None:
                    current_streak_start = snap_date
            else:
                current_streak_start = None
                prev_qty = qty
        if current_streak_start is not None:
            converge_dates[ds] = current_streak_start.isoformat()
            n_converge_total += 1
            if prev_qty is not None and prev_qty < firm_qty - 0.5:
                pre_converge_shortage_count += 1
                pre_converge_shortage_dates.append((round(firm_qty - prev_qty, 1), ds))
            days = _count_working_days(wdc, current_streak_start, due_date_obj)
            if days >= 0:
                stable_days_list.append((days, ds))
                firm_date_str = firm_dates.get(ds)
                if firm_date_str:
                    firm_date_obj = date.fromisoformat(firm_date_str)
                    firm_due_lt5_total += 1
                    if _count_working_days(wdc, firm_date_obj, due_date_obj) < 5:
                        firm_due_lt5_count += 1
                    firm_converge_on_or_after_firm_total += 1
                    if current_streak_start >= firm_date_obj:
                        firm_converge_on_or_after_firm_count += 1
                        firm_converge_on_or_after_firm_dates_list.append(ds)
                    fdays = _count_working_days(wdc, current_streak_start, firm_date_obj)
                    firm_stable_days_list.append((fdays, ds))
                    firm_delay_total += 1
                    if firm_date_obj >= due_date_obj:
                        firm_delay_count += 1

    # 収束日数統計
    if stable_days_list:
        days_vals = sorted([d for d, _ in stable_days_list])
        _n = len(days_vals)
        stable_days_mean = round(sum(days_vals) / _n, 1)
        stable_days_median = days_vals[_n // 2] if _n % 2 == 1 else round((days_vals[_n // 2 - 1] + days_vals[_n // 2]) / 2, 1)
        stable_days_std = round(statistics.stdev(days_vals), 1) if _n >= 2 else 0.0
        _min_e = min(stable_days_list, key=lambda x: x[0])
        _max_e = max(stable_days_list, key=lambda x: x[0])
        within_7_dates = sorted([ds for d, ds in stable_days_list if d <= 7])
        stable_days_dist = {
            'within_7': sum(1 for d in days_vals if d <= 7),
            'within_7_pct': round(sum(1 for d in days_vals if d <= 7) / _n * 100, 1),
            'within_7_dates': within_7_dates,
            'within_8_14': sum(1 for d in days_vals if 8 <= d <= 14),
            'within_8_14_pct': round(sum(1 for d in days_vals if 8 <= d <= 14) / _n * 100, 1),
            'within_15_21': sum(1 for d in days_vals if 15 <= d <= 21),
            'within_15_21_pct': round(sum(1 for d in days_vals if 15 <= d <= 21) / _n * 100, 1),
            'over_21': sum(1 for d in days_vals if d > 21),
            'over_21_pct': round(sum(1 for d in days_vals if d > 21) / _n * 100, 1),
        }
    else:
        stable_days_mean = stable_days_median = stable_days_std = None
        _min_e = _max_e = (None, None)
        stable_days_dist = None

    # 確定安定日数統計
    if firm_stable_days_list:
        fdays_vals = [d for d, _ in firm_stable_days_list]
        firm_stable_days_mean = round(sum(fdays_vals) / len(fdays_vals), 1)
        _fmin_e = min(firm_stable_days_list, key=lambda x: x[0])
        _fmax_e = max(firm_stable_days_list, key=lambda x: x[0])
    else:
        firm_stable_days_mean = None
        _fmin_e = _fmax_e = (None, None)
    firm_stable_days_negative_rate = round(firm_delay_count / firm_delay_total * 100, 1) if firm_delay_total > 0 else None

    # 誤差集計
    n = len(all_errors)
    if n > 0:
        abs_errors = [abs(e) for e in all_errors]
        mae = round(sum(abs_errors) / n, 2)
        max_diff = round(_max_diff_val, 2)
        min_diff = round(_min_diff_val, 2)
        mean_err = round(sum(all_errors) / n, 2)
        sigma = round(statistics.stdev(all_errors), 2) if n >= 2 else 0.0
        shortage_rate = round(n_dates_shortage / n_dates_with_firm * 100, 1) if n_dates_with_firm > 0 else 0.0

        if date_max_shortages:
            _qty_list = [qty for qty, _ in date_max_shortages]
            _counter = Counter(_qty_list)
            _sorted = sorted(_counter.items(), key=lambda x: x[0], reverse=True)
            max_shortage = _sorted[0][0]
            worst1_rate = round(_sorted[0][1] / n_dates_with_firm * 100, 1) if n_dates_with_firm > 0 else None
            worst1_dates = sorted([ds for qty, ds in date_max_shortages if qty == max_shortage])
            worst2_qty = _sorted[1][0] if len(_sorted) > 1 else None
            worst2_rate = round(_sorted[1][1] / n_dates_with_firm * 100, 1) if len(_sorted) > 1 and n_dates_with_firm > 0 else None
            worst2_dates = sorted([ds for qty, ds in date_max_shortages if qty == worst2_qty]) if worst2_qty is not None else []
        else:
            max_shortage = 0.0
            worst1_rate = worst2_qty = worst2_rate = None
            worst1_dates = worst2_dates = []

        bias = -mean_err if mean_err < 0 else 0.0
        ss_90 = round(1.28 * sigma + bias, 1)
        ss_95 = round(1.65 * sigma + bias, 1)
        ss_99 = round(2.33 * sigma + bias, 1)
    else:
        mae = max_diff = min_diff = mean_err = sigma = None
        _max_diff_date = _min_diff_date = None
        shortage_rate = max_shortage = worst1_rate = worst2_qty = worst2_rate = None
        worst1_dates = worst2_dates = []
        ss_90 = ss_95 = ss_99 = None
        n_dates_with_firm = 0

    firm_due_lt5_rate = round(firm_due_lt5_count / firm_due_lt5_total * 100, 1) if firm_due_lt5_total > 0 else None
    firm_converge_on_or_after_firm_rate = round(
        firm_converge_on_or_after_firm_count / firm_converge_on_or_after_firm_total * 100, 1
    ) if firm_converge_on_or_after_firm_total > 0 else None

    return {
        'analyzed_dates': len(all_due_dates),
        'dates_with_firm': n_dates_with_firm,
        'mae': mae,
        'max_diff': max_diff,
        'max_diff_date': _max_diff_date,
        'min_diff': min_diff,
        'min_diff_date': _min_diff_date,
        'mean_error': mean_err,
        'sigma': sigma,
        'shortage_rate': shortage_rate,
        'shortage_dates': n_dates_shortage,
        'max_shortage': max_shortage,
        'worst1_rate': worst1_rate,
        'worst1_dates': worst1_dates,
        'worst2_qty': worst2_qty,
        'worst2_rate': worst2_rate,
        'worst2_dates': worst2_dates,
        'safety_stock_90': ss_90,
        'safety_stock_95': ss_95,
        'safety_stock_99': ss_99,
        'stable_days_mean': stable_days_mean,
        'stable_days_median': stable_days_median,
        'stable_days_std': stable_days_std,
        'stable_days_dist': stable_days_dist,
        'stable_days_min': _min_e[0],
        'stable_days_min_date': _min_e[1],
        'stable_days_max': _max_e[0],
        'stable_days_max_date': _max_e[1],
        'stable_days_count': len(stable_days_list) if stable_days_list else None,
        'pre_converge_shortage_rate': round(pre_converge_shortage_count / n_converge_total * 100, 1) if n_converge_total > 0 else None,
        'pre_converge_shortage_count': pre_converge_shortage_count,
        'pre_converge_total': n_converge_total,
        'pre_converge_shortage_dates': sorted(pre_converge_shortage_dates, key=lambda x: -x[0]),
        'firm_due_lt5_count': firm_due_lt5_count,
        'firm_due_lt5_total': firm_due_lt5_total,
        'firm_due_lt5_rate': firm_due_lt5_rate,
        'firm_converge_on_or_after_firm_count': firm_converge_on_or_after_firm_count,
        'firm_converge_on_or_after_firm_total': firm_converge_on_or_after_firm_total,
        'firm_converge_on_or_after_firm_rate': firm_converge_on_or_after_firm_rate,
        'firm_converge_on_or_after_firm_dates': sorted(firm_converge_on_or_after_firm_dates_list),
        'converge_dates': converge_dates,
        'firm_stable_days_mean': firm_stable_days_mean,
        'firm_stable_days_min': _fmin_e[0],
        'firm_stable_days_min_date': _fmin_e[1],
        'firm_stable_days_max': _fmax_e[0],
        'firm_stable_days_max_date': _fmax_e[1],
        'firm_stable_days_count': len(firm_stable_days_list) if firm_stable_days_list else None,
        'firm_stable_days_negative_rate': firm_stable_days_negative_rate,
    }


# ---------------------------------------------------------------------------
# バッチサマリー（一括分析レポート用）
# ---------------------------------------------------------------------------
def compute_naiji_summary(customer_id, product_code, start_date=None, end_date=None, ship_to='', snapshot_start_date=None):
    """一括レポート用のサマリーデータを計算"""
    pd = _build_product_data(customer_id, product_code, ship_to, start_date, end_date, snapshot_start_date=snapshot_start_date)

    summary = _compute_period_summary(
        pd['all_due_dates'], pd['snapshots_map'], pd['ordered_files'],
        pd['snapshot_dates'], pd['firm_quantities'], pd['firm_dates'], pd['wdc'],
    )
    summary['product_code'] = product_code
    summary['product_name'] = pd['product_name']
    summary['snapshot_count'] = len(pd['ordered_files'])

    return summary


# ---------------------------------------------------------------------------
# PPTXレポート用データ計算
# ---------------------------------------------------------------------------
def _business_days_before(wdc, base_date, n):
    """base_date から n 営業日前の日付を返す"""
    cur = base_date
    count = 0
    while count < n:
        cur -= timedelta(days=1)
        if wdc.is_working_day(cur):
            count += 1
    return cur


def _compute_volatility(all_due_dates, snapshots_map, ordered_files, snapshot_dates):
    """納期ごとの内示変動回数（前回スナップショットからqtyが変わった回数）"""
    change_counts = {}
    for ds in all_due_dates:
        prev_qty = None
        count = 0
        for sf in ordered_files:
            if ds not in snapshots_map[sf]:
                continue
            qty = snapshots_map[sf][ds]
            if prev_qty is not None and qty != prev_qty:
                count += 1
            prev_qty = qty
        change_counts[ds] = count

    counts = list(change_counts.values())
    if not counts:
        return {'change_counts': {}, 'avg_change_count': 0.0, 'max_change_count': 0, 'example': None}

    avg_count = round(sum(counts) / len(counts), 1)
    max_count = max(counts)
    example_ds = max(change_counts, key=lambda d: change_counts[d])
    series = [
        {'snapshot_date': snapshot_dates[sf].date().isoformat(), 'qty': snapshots_map[sf][example_ds]}
        for sf in ordered_files if example_ds in snapshots_map[sf]
    ]
    return {
        'change_counts': change_counts,
        'avg_change_count': avg_count,
        'max_change_count': max_count,
        'example': {'due_date': example_ds, 'change_count': change_counts[example_ds], 'series': series},
    }


def _compute_last_minute_changes(all_due_dates, snapshots_map, ordered_files, snapshot_dates,
                                  firm_quantities, wdc):
    """納期5営業日前時点の内示と確定数量の乖離イベントを集計

    差(diff) = 確定数量 - 5営業日前内示。正なら確定が内示より多い（急増＝欠品リスク）、
    負なら確定が内示より少ない（急減＝過剰在庫リスク）。
    """
    total_events = 0
    large_events = 0
    divergences = []
    for ds in all_due_dates:
        firm_qty = firm_quantities.get(ds)
        if firm_qty is None:
            continue
        due_date_obj = date.fromisoformat(ds)
        target_date = _business_days_before(wdc, due_date_obj, 5)

        candidate = None
        for sf in ordered_files:
            if ds not in snapshots_map[sf]:
                continue
            snap_date = snapshot_dates[sf].date()
            if snap_date <= target_date:
                candidate = (snap_date, snapshots_map[sf][ds])
        if candidate is None:
            continue
        snap_date, qty = candidate
        if qty == firm_qty:
            continue

        total_events += 1
        diff = round(firm_qty - qty, 1)
        pct = round(diff / firm_qty * 100, 1) if firm_qty else None
        is_large = pct is not None and abs(pct) >= 20
        if is_large:
            large_events += 1
        divergences.append({
            'due_date': ds,
            'snapshot_date': snap_date.isoformat(),
            'snapshot_qty': qty,
            'firm_qty': firm_qty,
            'diff': diff,
            'pct': pct,
            'direction': 'shortage' if diff > 0 else 'overstock',
        })

    return {
        'total_events': total_events,
        'large_events': large_events,
        'large_rate': round(large_events / total_events * 100, 1) if total_events else None,
        'divergences': divergences,
    }


def _compute_firm_variability(all_due_dates, firm_quantities):
    """確定数量のばらつき統計（平均/σ/CV/レンジ）と連続納期間の日間差"""
    sorted_ds = sorted([ds for ds in all_due_dates if ds in firm_quantities])
    values = [firm_quantities[ds] for ds in sorted_ds]
    if not values:
        return None

    mean_val = round(sum(values) / len(values), 1)
    std_val = round(statistics.stdev(values), 1) if len(values) >= 2 else 0.0
    cv = round(std_val / mean_val * 100, 1) if mean_val else 0.0
    min_val = min(values)
    max_val = max(values)

    diffs = [abs(firm_quantities[cur] - firm_quantities[prev]) for prev, cur in zip(sorted_ds, sorted_ds[1:])]
    diff_mean = round(sum(diffs) / len(diffs), 1) if diffs else None
    diff_max = round(max(diffs), 1) if diffs else None

    return {
        'count': len(values),
        'mean': mean_val,
        'std_dev': std_val,
        'cv': cv,
        'min': min_val,
        'max': max_val,
        'range': round(max_val - min_val, 1),
        'diff_mean': diff_mean,
        'diff_max': diff_max,
        'series': [{'due_date': ds, 'qty': firm_quantities[ds]} for ds in sorted_ds],
    }


def _compute_monthly_forecast_deviation(snapshots_map, snapshot_dates, ordered_files, firm_quantities):
    """2か月前（前半月1〜15日）の内示（日当たり平均）と確定（日当たり平均）の月別乖離率を計算

    対象月Mに対して:
      1. Mの確定数量の日当たり平均 = 確定合計 ÷ 確定日数
      2. M-2か月の前半月（1〜15日）のスナップショットを探す
      3. 各スナップショットごとにMの内示日当たり平均を求める（内示合計 ÷ 内示日数）
      4. それらの日当たり平均の平均を求める
      5. 内示日当たり平均 vs 確定日当たり平均を比較
    """
    from collections import defaultdict

    if not firm_quantities or not ordered_files:
        return {'months': [], 'deviations': [], 'avg_pct': None}

    firm_by_month_total = defaultdict(float)
    firm_by_month_days = defaultdict(int)
    for ds, qty in firm_quantities.items():
        m = ds[:7]
        firm_by_month_total[m] += qty
        firm_by_month_days[m] += 1

    snaps_by_month = defaultdict(list)
    for sf in ordered_files:
        snap_date = snapshot_dates[sf].date()
        if snap_date.day > 15:
            continue
        snap_month = snap_date.strftime('%Y-%m')
        snaps_by_month[snap_month].append(sf)

    def _ref_month(target_month):
        year, mon = int(target_month[:4]), int(target_month[5:7])
        mon -= 2
        if mon <= 0:
            mon += 12
            year -= 1
        return f'{year:04d}-{mon:02d}'

    deviations = []
    for month in sorted(firm_by_month_total.keys()):
        ref = _ref_month(month)
        ref_snaps = snaps_by_month.get(ref, [])
        if not ref_snaps:
            continue

        snap_daily_avgs = []
        for sf in ref_snaps:
            month_entries = {ds: qty for ds, qty in snapshots_map[sf].items() if ds[:7] == month}
            if month_entries:
                daily_avg = sum(month_entries.values()) / len(month_entries)
                snap_daily_avgs.append(daily_avg)

        if not snap_daily_avgs:
            continue

        forecast_daily = round(sum(snap_daily_avgs) / len(snap_daily_avgs), 1)
        firm_days = firm_by_month_days[month]
        firm_daily = round(firm_by_month_total[month] / firm_days, 1) if firm_days > 0 else 0

        if firm_daily > 0:
            pct = round((forecast_daily - firm_daily) / firm_daily * 100, 1)
        else:
            pct = None

        deviations.append({
            'month': month,
            'forecast_daily': forecast_daily,
            'firm_daily': firm_daily,
            'firm_days': firm_days,
            'pct': pct,
            'snap_count': len(snap_daily_avgs),
            'ref_month': ref,
        })

    abs_pcts = [abs(d['pct']) for d in deviations if d['pct'] is not None]
    avg_pct = round(sum(abs_pcts) / len(abs_pcts), 1) if abs_pcts else None

    return {
        'months': sorted(firm_by_month_total.keys()),
        'deviations': deviations,
        'avg_pct': avg_pct,
    }


def _compute_short_lead_firm(customer_id, product_entries, start_date=None):
    """確定日後の追加（5稼働日未満）の事例を抽出

    発行日の翌日（弊社到着日）から納期までの稼働日が5未満のFIRMレコードを返す。
    """
    from django.db import connection
    from datetime import timedelta
    import json

    cal_start = start_date or date(2026, 1, 1)
    product_codes = [e['product_code'] for e in product_entries]
    if not product_codes:
        return []

    cursor = connection.cursor()
    cursor.execute(
        "SELECT target_date FROM m_calendar_day"
        " WHERE calendar_id = 1 AND is_working_day = 1"
        " AND target_date >= %s AND target_date <= %s",
        [cal_start - timedelta(days=90), date(2027, 12, 31)],
    )
    working_days = set(row[0] for row in cursor.fetchall())

    placeholders = ','.join(['%s'] * len(product_codes))
    cursor = connection.cursor()
    cursor.execute(f"""
        SELECT r.raw_payload, d.due_date, d.product_code, d.ship_to_code, d.quantity
        FROM stg_order_raw_kubota r
        JOIN stg_order_daily d ON d.raw_kubota_id = r.id
        WHERE d.customer_id = %s AND d.order_type = 'FIRM'
          AND d.due_date >= %s
          AND d.product_code IN ({placeholders})
    """, [customer_id, cal_start] + product_codes)

    def _parse_issue(s):
        if not s or len(s) != 6:
            return None
        try:
            return date(2000 + int(s[:2]), int(s[2:4]), int(s[4:6]))
        except Exception:
            return None

    def _count_wd(s, e):
        count = 0
        cur = s
        while cur < e:
            if cur in working_days:
                count += 1
            cur += timedelta(days=1)
        return count

    by_order = {}
    for raw_payload, due_date, pc, st, qty in cursor.fetchall():
        payload = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
        issue_d = _parse_issue(payload.get('issue_date', ''))
        if not issue_d:
            continue
        received = issue_d + timedelta(days=1)
        order_no = payload.get('order_no') or ''
        key = (pc, st or '', due_date, order_no)
        if key not in by_order or received < by_order[key][0]:
            by_order[key] = (received, issue_d, qty)

    results = []
    for (pc, st, due_date, _order_no), (received, issue_d, qty) in by_order.items():
        wd = _count_wd(received, due_date)
        if wd < 5:
            results.append({
                'product_code': pc,
                'ship_to': st,
                'due_date': due_date.isoformat(),
                'issue_date': issue_d.isoformat(),
                'received_date': received.isoformat(),
                'quantity': float(qty),
                'working_days': wd,
            })
    results.sort(key=lambda x: x['due_date'])
    return results


def _compute_batch_orders(customer_id, product_entries, start_date=None):
    """まとめ注文の事例を抽出

    ある日の確定数量が平均の1.5倍超え、かつ翌稼働日に確定がないケース。
    """
    from django.db import connection
    from datetime import timedelta

    cal_start = start_date or date(2026, 1, 1)
    product_codes = [e['product_code'] for e in product_entries]
    if not product_codes:
        return []

    cursor = connection.cursor()
    cursor.execute(
        "SELECT target_date FROM m_calendar_day"
        " WHERE calendar_id = 1 AND is_working_day = 1"
        " AND target_date >= %s AND target_date <= %s",
        [cal_start, date(2027, 12, 31)],
    )
    working_days = sorted(row[0] for row in cursor.fetchall())
    wd_set = set(working_days)

    placeholders = ','.join(['%s'] * len(product_codes))
    cursor.execute(f"""
        SELECT product_code, ship_to_code, due_date, SUM(quantity)
        FROM stg_order_daily
        WHERE customer_id = %s AND order_type = 'FIRM' AND due_date >= %s
          AND product_code IN ({placeholders})
        GROUP BY product_code, ship_to_code, due_date
        ORDER BY product_code, ship_to_code, due_date
    """, [customer_id, cal_start] + product_codes)

    from collections import defaultdict
    by_product = defaultdict(dict)
    for pc, st, dd, qty in cursor.fetchall():
        by_product[(pc, st or '')][dd] = float(qty)

    def _next_working_day(d):
        nxt = d + timedelta(days=1)
        while nxt not in wd_set and nxt < date(2027, 12, 31):
            nxt += timedelta(days=1)
        return nxt

    results = []
    for (pc, st), day_map in by_product.items():
        qtys = list(day_map.values())
        if len(qtys) < 3:
            continue
        avg = sum(qtys) / len(qtys)
        if avg == 0:
            continue
        for dd, q in day_map.items():
            if q > avg * 1.5:
                nwd = _next_working_day(dd)
                if nwd not in day_map:
                    results.append({
                        'product_code': pc,
                        'ship_to': st,
                        'due_date': dd.isoformat(),
                        'quantity': q,
                        'avg_quantity': round(avg, 1),
                        'ratio': round(q / avg, 1),
                        'next_working_day': nwd.isoformat(),
                    })
    results.sort(key=lambda x: (x['due_date'], x['product_code']))
    return results


def compute_naiji_report_data(customer_id, product_entries, start_date=None, end_date=None, snapshot_start_date=None):
    """PPTXレポート用データを計算

    product_entries: [{'product_code': str, 'ship_to': str}, ...]
    _build_product_data で共通データを構築し、収束/変動回数/確定直前乖離/
    確定数量ばらつきを製品ごとに計算して返す。
    """
    customer_name = ''
    products = []
    all_snapshot_dates = set()
    all_firm_due_dates = set()

    for entry in product_entries:
        pc = entry['product_code']
        st = (entry.get('ship_to') or '').strip()

        pd = _build_product_data(customer_id, pc, st, start_date, end_date, snapshot_start_date=snapshot_start_date)
        if not customer_name:
            customer_name = pd['customer_name']

        snapshots_map = pd['snapshots_map']
        snapshot_dates = pd['snapshot_dates']
        ordered_files = pd['ordered_files']
        all_due_dates = pd['all_due_dates']
        firm_quantities = pd['firm_quantities']
        firm_dates = pd['firm_dates']
        wdc = pd['wdc']

        for sf in ordered_files:
            all_snapshot_dates.add(snapshot_dates[sf].date())
        for ds in firm_quantities:
            all_firm_due_dates.add(date.fromisoformat(ds))

        summary = _compute_period_summary(
            all_due_dates, snapshots_map, ordered_files, snapshot_dates,
            firm_quantities, firm_dates, wdc,
        )
        volatility = _compute_volatility(all_due_dates, snapshots_map, ordered_files, snapshot_dates)
        last_minute = _compute_last_minute_changes(
            all_due_dates, snapshots_map, ordered_files, snapshot_dates, firm_quantities, wdc,
        )
        firm_variability = _compute_firm_variability(all_due_dates, firm_quantities)

        monthly_deviation = _compute_monthly_forecast_deviation(
            snapshots_map, snapshot_dates, ordered_files, firm_quantities,
        )

        products.append({
            'product_code': pc,
            'ship_to': st,
            'product_name': pd['product_name'],
            'snapshot_count': len(ordered_files),
            'summary': summary,
            'volatility': volatility,
            'last_minute': last_minute,
            'firm_variability': firm_variability,
            'monthly_deviation': monthly_deviation,
        })

    # --- 概要カード用の集計 ---
    within7_pcts = [
        p['summary']['stable_days_dist']['within_7_pct']
        for p in products if p['summary'].get('stable_days_dist')
    ]
    avg_change_counts = [p['volatility']['avg_change_count'] for p in products if p['volatility']['example']]
    max_diff_pcts = [
        abs(d['pct']) for p in products for d in p['last_minute']['divergences'] if d['pct'] is not None
    ]
    cvs = [p['firm_variability']['cv'] for p in products if p['firm_variability']]
    overstock_events = sum(1 for p in products for d in p['last_minute']['divergences'] if d['diff'] < 0)
    shortage_events = sum(1 for p in products for d in p['last_minute']['divergences'] if d['diff'] > 0)

    overview = {
        'within7_pct_min': round(min(within7_pcts), 1) if within7_pcts else None,
        'within7_pct_max': round(max(within7_pcts), 1) if within7_pcts else None,
        'avg_change_count_min': round(min(avg_change_counts), 1) if avg_change_counts else None,
        'avg_change_count_max': round(max(avg_change_counts), 1) if avg_change_counts else None,
        'max_divergence_pct': round(max(max_diff_pcts), 0) if max_diff_pcts else None,
        'cv_min': round(min(cvs), 1) if cvs else None,
        'cv_max': round(max(cvs), 1) if cvs else None,
        'overstock_events': overstock_events,
        'shortage_events': shortage_events,
    }

    firm_due_counts = [p['summary']['dates_with_firm'] for p in products if p['summary']['dates_with_firm']]

    short_lead_firm = _compute_short_lead_firm(customer_id, product_entries, start_date=date(2026, 7, 1))
    batch_orders = _compute_batch_orders(customer_id, product_entries, start_date=start_date)

    return {
        'customer_id': customer_id,
        'customer_name': customer_name,
        'products': products,
        'overview': overview,
        'short_lead_firm': short_lead_firm,
        'batch_orders': batch_orders,
        'snapshot_count': len(all_snapshot_dates),
        'first_snapshot_date': min(all_snapshot_dates).isoformat() if all_snapshot_dates else None,
        'last_snapshot_date': max(all_snapshot_dates).isoformat() if all_snapshot_dates else None,
        'firm_due_min': min(firm_due_counts) if firm_due_counts else None,
        'firm_due_max': max(firm_due_counts) if firm_due_counts else None,
        'first_firm_date': min(all_firm_due_dates).isoformat() if all_firm_due_dates else None,
        'last_firm_date': max(all_firm_due_dates).isoformat() if all_firm_due_dates else None,
    }


# ---------------------------------------------------------------------------
# Excelレポート生成
# ---------------------------------------------------------------------------
def generate_batch_report_excel(customer_id, entries, start_date=None, end_date=None, snapshot_start_date=None):
    """複数製品の内示分析サマリーをExcelワークブックで返す"""
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    customer = Customer.objects.filter(id=customer_id).first()
    customer_name = customer.customer_name if customer else ''

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '内示分析'

    header_fill = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True, size=10)
    center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin = Side(style='thin', color='CCCCCC')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    period_str = ''
    if start_date:
        period_str += f'納期: {start_date.isoformat()}'
    if end_date:
        period_str += f' ～ {end_date.isoformat()}'
    ws.append([f'{customer_name} 内示変化推移分析 一括レポート　{period_str}'])
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=25)
    title_cell = ws.cell(row=1, column=1)
    title_cell.font = Font(bold=True, size=12, color='1F4E79')
    title_cell.alignment = Alignment(horizontal='left', vertical='center')
    ws.row_dimensions[1].height = 22

    ws.append(['', '', '', '予測誤差（全スナップショット − 確定）', '', '', '', '', '', '', '欠品リスク', '', '', '', '', '推奨安全在庫量', '', '', '収束安定期間（日数）', '', '', '', '', '', '', '安定日数（確定登録まで）', '', '', '', ''])
    cat_row = 2
    cat_ranges = [(4, 10), (11, 15), (16, 18), (19, 25), (26, 31)]
    cat_labels = ['予測誤差（全スナップショット − 確定）', '欠品リスク（内示＜確定）', '推奨安全在庫量（Z×σ）', '収束安定期間（内示＝確定が続いた日数）', '安定日数（収束開始→確定登録日）']
    cat_fills = ['2E75B6', 'C00000', '375623', '7030A0', 'BF8F00']
    for (start_col, end_col), label, fill_color in zip(cat_ranges, cat_labels, cat_fills):
        ws.merge_cells(start_row=cat_row, start_column=start_col, end_row=cat_row, end_column=end_col)
        cell = ws.cell(row=cat_row, column=start_col)
        cell.value = label
        cell.font = Font(color='FFFFFF', bold=True, size=9)
        cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type='solid')
        cell.alignment = center
        cell.border = border
    for col in range(1, 4):
        cell = ws.cell(row=cat_row, column=col)
        cell.fill = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
        cell.border = border

    headers = [
        '品番', '品名', 'スナップ\nショット数',
        '最大差', '最大差日', '最小差', '最小差日', 'MAE', '平均差', 'σ',
        '内示過小率(%)', 'ワースト1\n過小量', 'ワースト1\n出現率(%)', 'ワースト2\n過小量', 'ワースト2\n出現率(%)',
        '安全在庫\n90%', '安全在庫\n95%', '安全在庫\n99%',
        '収束\n平均日', '収束\n中央値', '収束\n標準偏差', '収束\n≤7日', '収束\n8-14日', '収束\n15-21日', '収束\n≥22日', '収束\n最短日', '収束最短日', '収束\n最長日', '収束最長日', '収束\n対象件数', '分析\n納期数',
        '安定\n平均日', '安定\n最短日', '安定最短日', '安定\n最長日', '安定\n対象件数', '安定\nマイナス率%',
    ]
    ws.append(headers)
    header_row = 3
    header_col_fills = (
        ['1F4E79'] * 3 +
        ['2E75B6'] * 7 +
        ['C00000'] * 5 +
        ['375623'] * 3 +
        ['7030A0'] * 13 +
        ['BF8F00'] * 6
    )
    for col_idx, (hdr, fill_color) in enumerate(zip(headers, header_col_fills), start=1):
        cell = ws.cell(row=header_row, column=col_idx)
        cell.value = hdr
        cell.font = Font(color='FFFFFF', bold=True, size=9)
        cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type='solid')
        cell.alignment = center
        cell.border = border
    ws.row_dimensions[header_row].height = 30

    def _v(val):
        return val if val is not None else ''

    def _parse_entry(entry_str):
        if ':' in entry_str:
            pc, st = entry_str.split(':', 1)
            return pc.strip(), st.strip()
        return entry_str.strip(), ''

    for row_idx, entry in enumerate(entries, start=4):
        pc, st = _parse_entry(entry)
        summary = compute_naiji_summary(customer_id, pc, start_date, end_date, ship_to=st, snapshot_start_date=snapshot_start_date)
        display_code = f"{summary['product_code']} ({st})" if st else summary['product_code']
        row_data = [
            display_code,
            summary['product_name'],
            _v(summary['snapshot_count']),
            _v(summary['max_diff']),
            _v(summary['max_diff_date']),
            _v(summary['min_diff']),
            _v(summary['min_diff_date']),
            _v(summary['mae']),
            _v(summary['mean_error']),
            _v(summary['sigma']),
            _v(summary['shortage_rate']),
            _v(summary['max_shortage']),
            _v(summary['worst1_rate']),
            _v(summary['worst2_qty']),
            _v(summary['worst2_rate']),
            _v(summary['safety_stock_90']),
            _v(summary['safety_stock_95']),
            _v(summary['safety_stock_99']),
            _v(summary['stable_days_mean']),
            _v(summary.get('stable_days_median')),
            _v(summary.get('stable_days_std')),
            _v(summary.get('stable_days_dist', {}).get('within_7') if summary.get('stable_days_dist') else None),
            _v(summary.get('stable_days_dist', {}).get('within_8_14') if summary.get('stable_days_dist') else None),
            _v(summary.get('stable_days_dist', {}).get('within_15_21') if summary.get('stable_days_dist') else None),
            _v(summary.get('stable_days_dist', {}).get('over_21') if summary.get('stable_days_dist') else None),
            _v(summary['stable_days_min']),
            _v(summary['stable_days_min_date']),
            _v(summary['stable_days_max']),
            _v(summary['stable_days_max_date']),
            _v(summary['stable_days_count']),
            _v(summary['analyzed_dates']),
            _v(summary['firm_stable_days_mean']),
            _v(summary['firm_stable_days_min']),
            _v(summary['firm_stable_days_min_date']),
            _v(summary['firm_stable_days_max']),
            _v(summary['firm_stable_days_count']),
            _v(summary['firm_stable_days_negative_rate']),
        ]
        ws.append(row_data)
        row_fill = 'EBF3FB' if row_idx % 2 == 0 else 'FFFFFF'
        for col_idx in range(1, 38):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center')
            if col_idx in (1, 2):
                cell.alignment = Alignment(horizontal='left', vertical='center')
            cell.fill = PatternFill(start_color=row_fill, end_color=row_fill, fill_type='solid')

    col_widths = [18, 20, 8, 7, 12, 7, 12, 7, 7, 7, 10, 10, 9, 10, 9, 9, 9, 9, 8, 8, 8, 8, 8, 8, 8, 8, 12, 8, 12, 8, 8, 8, 8, 12, 8, 8, 10]
    for i, w in enumerate(col_widths, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    ws.freeze_panes = 'A4'

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf, customer_name
