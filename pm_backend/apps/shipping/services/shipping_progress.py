"""出荷進度の再計算

進度 = 前日進度 - 需要(確定優先、なければ内示) + 実績 + 調整

需要: OrderLine の quantity を品番×得意先×納入先×納期(LT調整後)で合算
  - 同一キーに FIRM と FORECAST が両方ある場合、FORECAST は除外
実績: ShipmentActual の quantity を品番×得意先×納入先×出荷日で合算
"""
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum

from masters.models import Calendar
from orders.core.models import Order, OrderLine
from orders.utils.calendar_utils import WorkingDayCalculator
from shipping.models import ShipmentActual, ShipToLeadTime, ShippingProgress

DEFAULT_PROGRESS_HORIZON_DAYS = 30


def get_progress_horizon_days():
    """出荷進度の再計算日数を取得する。SystemSetting から読み込み、未設定なら30日。"""
    try:
        from system_settings.models import SystemSetting
        setting = SystemSetting.objects.filter(key='shipping.progress_horizon_days').first()
        if setting and setting.value:
            return max(int(setting.value), 1)
    except Exception:
        pass
    return DEFAULT_PROGRESS_HORIZON_DAYS


def _to_int(value):
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return int(value.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return int(value)


def _build_lead_time_map():
    """納入先リードタイム(営業日)のマップを構築。key=(customer_code, ship_to_code)"""
    lt_map = {}
    for row in ShipToLeadTime.objects.filter(is_active=True).select_related('customer'):
        key = (row.customer.customer_code, (row.ship_to_code or '').strip())
        lt_map[key] = row.additional_days or 0
    return lt_map


def recalculate_shipping_progress(start_date, end_date):
    """指定期間の出荷進度を再計算する。

    start_date ~ end_date の各日について、品番×得意先×納入先ごとに
    需要(内示/確定)・実績を集計し、累積進度を計算してDBに保存する。
    """
    if start_date > end_date:
        return

    calendar = Calendar.objects.first()
    calc = WorkingDayCalculator(calendar)
    lt_map = _build_lead_time_map()

    # --- 需要集計: OrderLine (OPEN受注のみ) ---
    order_lines = (
        OrderLine.objects
        .filter(order__status='OPEN')
        .select_related('order__customer')
        .only(
            'product_code', 'order_type', 'quantity', 'due_date', 'ship_to_code',
            'order__order_type', 'order__customer__customer_code',
        )
    )

    # 品番×得意先×納入先×日付 ごとに内示/確定を集計
    forecast_map = defaultdict(int)  # (product, customer, ship_to, date) -> qty
    firm_map = defaultdict(int)
    all_keys = set()  # (product_code, customer_code, ship_to_code)

    for ol in order_lines:
        if not ol.due_date or not ol.product_code:
            continue
        customer_code = ol.order.customer.customer_code if ol.order and ol.order.customer else ''
        ship_to_code = (ol.ship_to_code or '').strip()

        # LT調整: 納期を出荷加算日数分だけ前倒し
        due_date = ol.due_date
        lt_days = lt_map.get((customer_code, ship_to_code), 0)
        if lt_days > 0:
            due_date = calc.subtract_working_days(due_date, lt_days)

        order_type = (ol.order_type or ol.order.order_type or '').upper() if ol.order else (ol.order_type or '').upper()
        qty = _to_int(ol.quantity)
        group_key = (ol.product_code, customer_code, ship_to_code)
        date_key = (ol.product_code, customer_code, ship_to_code, due_date)
        all_keys.add(group_key)

        if order_type == 'FIRM':
            firm_map[date_key] += qty
        else:
            forecast_map[date_key] += qty

    # 確定優先: 同一キー(品番×得意先×納入先×日付)にFIRMがあるFORECASTを除外
    for date_key in list(forecast_map.keys()):
        if date_key in firm_map:
            del forecast_map[date_key]

    # --- 実績集計: ShipmentActual ---
    actual_qs = (
        ShipmentActual.objects
        .filter(shipment_date__range=(start_date, end_date))
        .values('product_code', 'customer_code', 'ship_to_code', 'shipment_date')
        .annotate(total=Sum('quantity'))
    )
    actual_map = {}
    for row in actual_qs:
        product_code = row['product_code'] or ''
        customer_code = row['customer_code'] or ''
        ship_to_code = (row['ship_to_code'] or '').strip()
        date_key = (product_code, customer_code, ship_to_code, row['shipment_date'])
        actual_map[date_key] = _to_int(row['total'])
        all_keys.add((product_code, customer_code, ship_to_code))

    # 既存の進捗行から対象キーを追加
    existing_keys = (
        ShippingProgress.objects
        .filter(plan_date__range=(start_date, end_date))
        .values('product_code', 'customer_code', 'ship_to_code')
        .distinct()
    )
    for row in existing_keys:
        all_keys.add((row['product_code'], row['customer_code'] or '', (row['ship_to_code'] or '').strip()))

    if not all_keys:
        return

    # --- 前日進度を取得 ---
    prev_date = start_date - timedelta(days=1)
    prev_progress = {}
    for row in ShippingProgress.objects.filter(plan_date=prev_date):
        key = (row.product_code, row.customer_code or '', (row.ship_to_code or '').strip())
        prev_progress[key] = row.progress_qty

    # --- 既存行を取得(調整値の保持用) ---
    existing_rows = {}
    for row in ShippingProgress.objects.filter(plan_date__range=(start_date, end_date)):
        existing_rows[(row.product_code, row.customer_code or '', (row.ship_to_code or '').strip(), row.plan_date)] = row

    # --- 日毎に累積進度を計算 ---
    to_create = []
    to_update = []
    days = (end_date - start_date).days + 1

    for product_code, customer_code, ship_to_code in sorted(all_keys):
        group_key = (product_code, customer_code, ship_to_code)
        last_progress = prev_progress.get(group_key, 0)

        for day_offset in range(days):
            plan_date = start_date + timedelta(days=day_offset)
            date_key = (product_code, customer_code, ship_to_code, plan_date)

            forecast = forecast_map.get(date_key, 0)
            firm = firm_map.get(date_key, 0)
            actual = actual_map.get(date_key, 0)

            row_key = (product_code, customer_code, ship_to_code, plan_date)
            existing = existing_rows.get(row_key)
            adjust = existing.adjust_qty if existing else 0

            # 需要 = 確定があれば確定、なければ内示
            demand = firm if firm > 0 else forecast
            progress = last_progress - demand + actual + adjust

            if existing:
                changed = (
                    existing.forecast_qty != forecast
                    or existing.firm_qty != firm
                    or existing.actual_qty != actual
                    or existing.progress_qty != progress
                )
                if changed:
                    existing.forecast_qty = forecast
                    existing.firm_qty = firm
                    existing.actual_qty = actual
                    existing.progress_qty = progress
                    to_update.append(existing)
            else:
                if forecast != 0 or firm != 0 or actual != 0 or progress != 0:
                    to_create.append(ShippingProgress(
                        plan_date=plan_date,
                        product_code=product_code,
                        customer_code=customer_code,
                        ship_to_code=ship_to_code,
                        forecast_qty=forecast,
                        firm_qty=firm,
                        actual_qty=actual,
                        adjust_qty=0,
                        progress_qty=progress,
                    ))

            last_progress = progress

    if to_create:
        ShippingProgress.objects.bulk_create(to_create)
    if to_update:
        ShippingProgress.objects.bulk_update(
            to_update, ['forecast_qty', 'firm_qty', 'actual_qty', 'progress_qty']
        )
