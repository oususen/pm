"""クボタ堺配送進捗の再計算

進捗 = 前日進捗 - 需要 + 便振分 + 調整

需要: KubotaSakaiDueAdjustment.delivery_qty を品番×納入地×日付で合算
便振分: KubotaSakaiTripAssignment.qty を品番×納入地×日付で合算
"""
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum

from orders.core.models import KubotaSakaiDueAdjustment, KubotaSakaiTripAssignment
from shipping.models import KubotaSakaiDeliveryProgress


def _to_int(value):
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return int(value.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return int(value)


def recalculate_delivery_progress(start_date, end_date):
    """指定期間のクボタ堺配送進捗を再計算する。

    start_date より前日の進捗値を起点として、start_date 〜 end_date の
    各日の進捗を累計計算する。
    """
    if start_date > end_date:
        return

    # 需要: DueAdjustment.delivery_qty を品番×納入地×日付で集計
    demand_qs = (
        KubotaSakaiDueAdjustment.objects
        .filter(due_date__range=(start_date, end_date), delivery_qty__gt=0)
        .values('product_code', 'ship_to_code', 'due_date')
        .annotate(total=Sum('delivery_qty'))
    )
    demand_map = {}
    all_keys = set()
    for row in demand_qs:
        key = (row['product_code'], row['ship_to_code'] or '')
        demand_map[(key, row['due_date'])] = _to_int(row['total'])
        all_keys.add(key)

    # 便振分: TripAssignment.qty を品番×納入地×出発日で集計
    assigned_qs = (
        KubotaSakaiTripAssignment.objects
        .filter(departure_date__range=(start_date, end_date))
        .select_related('due_adjustment')
        .values(
            'due_adjustment__product_code',
            'due_adjustment__ship_to_code',
            'departure_date',
        )
        .annotate(total=Sum('qty'))
    )
    assigned_map = {}
    for row in assigned_qs:
        key = (row['due_adjustment__product_code'], row['due_adjustment__ship_to_code'] or '')
        assigned_map[(key, row['departure_date'])] = _to_int(row['total'])
        all_keys.add(key)

    # 既存の進捗行から対象キーを追加（需要・振分がなくても調整値が入っている場合）
    existing_keys = (
        KubotaSakaiDeliveryProgress.objects
        .filter(plan_date__range=(start_date, end_date))
        .values('product_code', 'ship_to_code')
        .distinct()
    )
    for row in existing_keys:
        all_keys.add((row['product_code'], row['ship_to_code'] or ''))

    if not all_keys:
        return

    # 前日進捗を取得（start_date - 1 の progress_qty）
    prev_date = start_date - timedelta(days=1)
    prev_progress_qs = KubotaSakaiDeliveryProgress.objects.filter(
        plan_date=prev_date,
    )
    prev_progress = {}
    for row in prev_progress_qs:
        key = (row.product_code, row.ship_to_code or '')
        prev_progress[key] = row.progress_qty

    # 既存の調整値を保持するため、対象期間の既存行を取得
    existing_rows = {}
    for row in KubotaSakaiDeliveryProgress.objects.filter(
        plan_date__range=(start_date, end_date),
    ):
        existing_rows[(row.product_code, row.ship_to_code or '', row.plan_date)] = row

    to_create = []
    to_update = []

    days = (end_date - start_date).days + 1
    for product_code, ship_to_code in sorted(all_keys):
        key = (product_code, ship_to_code)
        last_progress = prev_progress.get(key, 0)

        for day_offset in range(days):
            plan_date = start_date + timedelta(days=day_offset)
            demand = demand_map.get((key, plan_date), 0)
            assigned = assigned_map.get((key, plan_date), 0)

            row_key = (product_code, ship_to_code, plan_date)
            existing = existing_rows.get(row_key)
            adjust = existing.adjust_qty if existing else 0

            progress = last_progress - demand + assigned + adjust

            if existing:
                changed = (
                    existing.demand_qty != demand
                    or existing.assigned_qty != assigned
                    or existing.progress_qty != progress
                )
                if changed:
                    existing.demand_qty = demand
                    existing.assigned_qty = assigned
                    existing.progress_qty = progress
                    to_update.append(existing)
            else:
                if demand != 0 or assigned != 0 or progress != 0:
                    to_create.append(KubotaSakaiDeliveryProgress(
                        plan_date=plan_date,
                        product_code=product_code,
                        ship_to_code=ship_to_code,
                        demand_qty=demand,
                        assigned_qty=assigned,
                        adjust_qty=0,
                        progress_qty=progress,
                    ))

            last_progress = progress

    if to_create:
        KubotaSakaiDeliveryProgress.objects.bulk_create(to_create)
    if to_update:
        KubotaSakaiDeliveryProgress.objects.bulk_update(
            to_update, ['demand_qty', 'assigned_qty', 'progress_qty']
        )
