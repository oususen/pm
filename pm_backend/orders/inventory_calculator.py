"""
在庫計算ロジック
LineBacklogの在庫・計画在庫を再計算するためのユーティリティ
"""
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import F
from .models_line_backlog import LineBacklog
from .models_scrap import ScrapRecord, ScrapRecordDetail
from .models import OrderLine


def aggregate_scrap_to_backlog(line_id=None, start_date=None, end_date=None):
    """
    ScrapRecordとScrapRecordDetailから仕損数を集計し、
    LineBacklog.scrap_qtyに反映

    Args:
        line_id: 対象ラインID（Noneの場合は全ライン）
        start_date: 開始日
        end_date: 終了日
    """
    # まず既存のscrap_qtyをゼロリセット
    reset_filter = {}
    if line_id:
        reset_filter['line_id'] = line_id
    if start_date and end_date:
        reset_filter['plan_date__range'] = [start_date, end_date]

    LineBacklog.objects.filter(**reset_filter).update(scrap_qty=0)

    # 自工程仕損の集計
    scrap_filter = {
        'disposition_status': 'REJECTED',  # 仕損確定のみ
        'plan_date__isnull': False,
    }
    if line_id:
        scrap_filter['line_id'] = line_id
    if start_date and end_date:
        scrap_filter['plan_date__range'] = [start_date, end_date]

    scrap_records = ScrapRecord.objects.filter(**scrap_filter).select_related('product', 'line', 'process')

    for scrap in scrap_records:
        if not scrap.product or not scrap.line or not scrap.process:
            continue

        LineBacklog.objects.filter(
            plan_date=scrap.plan_date,
            product=scrap.product,
            line=scrap.line,
            process=scrap.process,
        ).update(scrap_qty=F('scrap_qty') + int(scrap.qty))

    # 後工程仕損の展開分
    detail_filter = {
        'scrap_record__disposition_status': 'REJECTED',
        'scrap_record__plan_date__isnull': False,
    }
    if line_id:
        detail_filter['line_id'] = line_id
    if start_date and end_date:
        detail_filter['scrap_record__plan_date__range'] = [start_date, end_date]

    details = ScrapRecordDetail.objects.filter(**detail_filter).select_related('scrap_record', 'product')

    for detail in details:
        if not detail.product or not detail.line_id or not detail.process_id:
            continue

        LineBacklog.objects.filter(
            plan_date=detail.scrap_record.plan_date,
            product=detail.product,
            line_id=detail.line_id,
            process_id=detail.process_id,
        ).update(scrap_qty=F('scrap_qty') + int(detail.deduct_qty))


def _build_firm_order_map(line_id, start_date, end_date):
    """
    最終品（is_final_product=True）の確定数量を (product_id, plan_date) で集計。
    plan_date はリードタイムと稼働日を考慮して決定する。
    """
    from collections import defaultdict
    from masters.models import RoutingStep, Line, Calendar, CalendarDay

    steps_on_line = RoutingStep.objects.filter(
        line_id=line_id
    ).select_related('output_product', 'routing__product', 'line')

    product_step_map = {}
    final_products = set()
    max_lead_days = 0

    for step in steps_on_line:
        product = step.output_product or (step.routing.product if step.routing_id else None)
        if not product:
            continue
        if product.id not in product_step_map:
            product_step_map[product.id] = step
        if product.is_final_product:
            final_products.add(product.id)
            lead_days = step.lead_time_days or (step.line.lead_time_days if step.line else 0) or 0
            if lead_days > max_lead_days:
                max_lead_days = lead_days

    if not final_products:
        return {}

    line_obj = Line.objects.filter(id=line_id).first()
    calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(
        calendar_code='tiera_muke'
    ).values_list('id', flat=True).first()
    workday_cache = {}

    def is_working_day(target_date):
        if not calendar_id:
            return True
        if target_date in workday_cache:
            return workday_cache[target_date]
        cal = CalendarDay.objects.filter(
            calendar_id=calendar_id,
            target_date=target_date
        ).first()
        is_work = cal.is_working_day if cal is not None else True
        workday_cache[target_date] = is_work
        return is_work

    def shift_business_days(target_date, days):
        if not days:
            if not calendar_id:
                return target_date
            if is_working_day(target_date):
                return target_date
            current = target_date
            while True:
                current = current - timedelta(days=1)
                if is_working_day(current):
                    return current
        if not calendar_id:
            return target_date + timedelta(days=-days)

        step = -1 if days > 0 else 1
        remaining = abs(int(days))
        current = target_date
        while remaining > 0:
            current = current + timedelta(days=step)
            if is_working_day(current):
                remaining -= 1
        return current

    def resolve_lead_time_days(product_id):
        step = product_step_map.get(product_id)
        if step and step.lead_time_days:
            return step.lead_time_days
        if step and step.line and step.line.lead_time_days:
            return step.line.lead_time_days
        return 0

    due_end = end_date + timedelta(days=max_lead_days + 7)
    order_lines = OrderLine.objects.filter(
        order__status='OPEN',
        product_id__in=final_products,
        due_date__gte=start_date,
        due_date__lte=due_end,
    ).select_related('order')

    firm_map = defaultdict(Decimal)
    for ol in order_lines:
        if not ol.product_id or not ol.due_date:
            continue
        if (ol.order.order_type or '').upper() != 'FIRM':
            continue
        lead_days = resolve_lead_time_days(ol.product_id)
        plan_date = shift_business_days(ol.due_date, lead_days)
        if plan_date < start_date or plan_date > end_date:
            continue
        firm_map[(ol.product_id, plan_date)] += Decimal(str(ol.quantity or 0))

    return firm_map


def _sum_parent_shipments(backlog, pick_qty):
    from masters.models import BOMItem

    parent_bom_items = BOMItem.objects.filter(
        child_product=backlog.product,
        bom__is_active=True
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
        downstream_backlogs = LineBacklog.objects.filter(
            product=parent_product,
            plan_date=backlog.plan_date,
        )
        for downstream in downstream_backlogs:
            use_qty = pick_qty(downstream)
            if use_qty:
                total_shipment += Decimal(str(use_qty)) * Decimal(str(qty_per))

    return total_shipment


def _calculate_parent_actual_shipment(backlog):
    return _sum_parent_shipments(backlog, lambda d: d.actual_qty or 0)


def _calculate_parent_planned_shipment(backlog, today):
    if backlog.plan_date < today:
        return _calculate_parent_actual_shipment(backlog)
    if backlog.plan_date == today:
        def pick(d):
            plan_qty = d.plan_qty or 0
            actual_qty = d.actual_qty or 0
            return actual_qty if actual_qty > plan_qty else plan_qty
        return _sum_parent_shipments(backlog, pick)
    return _sum_parent_shipments(backlog, lambda d: d.plan_qty or 0)


def calculate_actual_shipment(backlog):
    """
    実績出庫数を後工程の実績から計算

    Args:
        backlog: LineBacklogインスタンス

    Returns:
        int: 実績出庫数（計算できない場合はNone）
    """
    from masters.models import BOMItem

    # この製品を子製品として使用しているBOMItemを検索
    parent_bom_items = BOMItem.objects.filter(
        child_product=backlog.product,
        bom__is_active=True
    ).select_related('bom__parent_product')

    if not parent_bom_items.exists():
        return None

    total_shipment = 0
    found_actual = False

    for bom_item in parent_bom_items:
        # 後工程の実績を取得
        # ※ リードタイムを考慮する場合は plan_date を調整
        downstream_backlogs = LineBacklog.objects.filter(
            product=bom_item.bom.parent_product,
            plan_date=backlog.plan_date,  # 同日（またはLT調整）
        )

        for downstream in downstream_backlogs:
            if downstream.actual_qty and downstream.actual_qty > 0:
                # 実績 × BOM数量 = 出庫数
                quantity = bom_item.quantity or Decimal('1')
                shipment = int(downstream.actual_qty * quantity)
                total_shipment += shipment
                found_actual = True

    return total_shipment if found_actual else None


def has_downstream_actual(backlog):
    """
    後工程に実績が入力されているかチェック

    Args:
        backlog: LineBacklogインスタンス

    Returns:
        bool: 後工程に実績があればTrue
    """
    from masters.models import BOMItem

    parent_bom_items = BOMItem.objects.filter(
        child_product=backlog.product,
        bom__is_active=True
    )

    for bom_item in parent_bom_items:
        downstream_backlogs = LineBacklog.objects.filter(
            product=bom_item.bom.parent_product,
            plan_date=backlog.plan_date,
            actual_qty__gt=0
        )
        if downstream_backlogs.exists():
            return True

    return False


def recalculate_stock_qty(line_id, product_id, start_date, end_date, firm_map=None):
    """
    実在庫を日次で再計算

    Args:
        line_id: ラインID
        product_id: 製品ID
        start_date: 開始日
        end_date: 終了日
    """
    backlogs = LineBacklog.objects.filter(
        line_id=line_id,
        product_id=product_id,
        plan_date__range=[start_date, end_date]
    ).select_related('product').order_by('plan_date')

    calendar_id = None
    workday_cache = {}
    if line_id:
        from masters.models import Line, Calendar, CalendarDay
        line_obj = Line.objects.filter(id=line_id).first()
        calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(
            calendar_code='tiera_muke'
        ).values_list('id', flat=True).first()

    def is_working_day(target_date):
        if not calendar_id:
            return True
        if target_date in workday_cache:
            return workday_cache[target_date]
        cal = CalendarDay.objects.filter(
            calendar_id=calendar_id,
            target_date=target_date
        ).first()
        is_work = cal.is_working_day if cal is not None else True
        workday_cache[target_date] = is_work
        return is_work

    def get_prev_working_day(target_date):
        prev_date = target_date - timedelta(days=1)
        if not calendar_id:
            return prev_date
        while not is_working_day(prev_date):
            prev_date = prev_date - timedelta(days=1)
        return prev_date

    today = datetime.now().date()
    prev_stock = 0
    firm_map = firm_map or {}

    for backlog in backlogs:
        # 前日在庫を取得
        if backlog.plan_date > start_date:
            prev_day = get_prev_working_day(backlog.plan_date)
            prev = LineBacklog.objects.filter(
                line_id=line_id,
                product_id=product_id,
                plan_date=prev_day
            ).first()
            if prev:
                prev_stock = prev.stock_qty

        # 実在庫計算
        actual_production = backlog.actual_qty or 0

        # 実績出庫数を計算（最終品は確定、最終品以外は親実績）
        is_final = bool(getattr(backlog.product, 'is_final_product', False))
        if backlog.plan_date <= today:
            if is_final:
                actual_shipment = firm_map.get((backlog.product_id, backlog.plan_date), Decimal('0'))
            else:
                actual_shipment = _calculate_parent_actual_shipment(backlog)
        else:
            actual_shipment = Decimal('0')
        actual_shipment = int(actual_shipment or 0)
        backlog.actual_shipment_qty = actual_shipment

        backlog.stock_qty = (
            prev_stock
            + actual_production
            - actual_shipment
            + (backlog.adjust_qty or 0)
            - (backlog.scrap_qty or 0)
        )
        backlog.save(update_fields=['stock_qty', 'actual_shipment_qty'])

        prev_stock = backlog.stock_qty


def recalculate_planned_stock_qty(line_id, product_id, start_date, end_date, firm_map=None):
    """
    計画在庫を日次で再計算（時制考慮版）
    - 過去（plan_date < today）:
        - 実績あり → 実績ベース計算
        - 実績なし → 生産・出庫ゼロとして計算
    - 今日以降（plan_date >= today）: 計画ベース計算

    Args:
        line_id: ラインID
        product_id: 製品ID
        start_date: 開始日
        end_date: 終了日
    """
    backlogs = LineBacklog.objects.filter(
        line_id=line_id,
        product_id=product_id,
        plan_date__range=[start_date, end_date]
    ).select_related('product').order_by('plan_date')

    calendar_id = None
    workday_cache = {}
    if line_id:
        from masters.models import Line, Calendar, CalendarDay
        line_obj = Line.objects.filter(id=line_id).first()
        calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(
            calendar_code='tiera_muke'
        ).values_list('id', flat=True).first()

    def is_working_day(target_date):
        if not calendar_id:
            return True
        if target_date in workday_cache:
            return workday_cache[target_date]
        cal = CalendarDay.objects.filter(
            calendar_id=calendar_id,
            target_date=target_date
        ).first()
        is_work = cal.is_working_day if cal is not None else True
        workday_cache[target_date] = is_work
        return is_work

    def get_prev_working_day(target_date):
        prev_date = target_date - timedelta(days=1)
        if not calendar_id:
            return prev_date
        while not is_working_day(prev_date):
            prev_date = prev_date - timedelta(days=1)
        return prev_date

    today = datetime.now().date()
    prev_planned = 0
    firm_map = firm_map or {}

    for backlog in backlogs:
        # 前日の計画在庫を取得
        if backlog.plan_date > start_date:
            prev_day = get_prev_working_day(backlog.plan_date)
            prev = LineBacklog.objects.filter(
                line_id=line_id,
                product_id=product_id,
                plan_date=prev_day
            ).first()
            if prev:
                prev_planned = prev.planned_stock_qty

        is_final = bool(getattr(backlog.product, 'is_final_product', False))
        if is_final:
            planned_shipment = firm_map.get((backlog.product_id, backlog.plan_date), Decimal('0'))
        else:
            planned_shipment = _calculate_parent_planned_shipment(backlog, today)
        planned_shipment = int(planned_shipment or 0)

        # 時制による計算分岐
        if backlog.plan_date < today:
            # ===== 過去：実績ベース =====
            backlog.planned_stock_qty = (
                prev_planned
                + (backlog.actual_qty or 0)
                - planned_shipment
                + (backlog.adjust_qty or 0)
                - (backlog.scrap_qty or 0)
            )
        elif backlog.plan_date == today:
            # ===== 今日：計画ベース =====
            backlog.planned_stock_qty = (
                prev_planned
                + (backlog.plan_qty or 0)
                - planned_shipment
                + (backlog.adjust_qty or 0)
            )
        else:
            # ===== 明日以降：計画ベース =====
            backlog.planned_stock_qty = (
                prev_planned
                + (backlog.plan_qty or 0)
                - planned_shipment
                + (backlog.adjust_qty or 0)
            )

        backlog.save(update_fields=['planned_stock_qty'])
        prev_planned = backlog.planned_stock_qty


def recalculate_inventory_for_line(line_id, start_date, end_date):
    """
    指定ラインの全製品について在庫を再計算

    Args:
        line_id: ラインID
        start_date: 開始日
        end_date: 終了日
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"在庫再計算開始: line_id={line_id}, {start_date} ~ {end_date}")

    # まず仕損数を集計
    aggregate_scrap_to_backlog(line_id, start_date, end_date)

    firm_map = _build_firm_order_map(line_id, start_date, end_date)

    # 製品ごとに在庫計算
    product_ids = LineBacklog.objects.filter(
        line_id=line_id,
        plan_date__range=[start_date, end_date]
    ).values_list('product_id', flat=True).distinct()

    logger.info(f"対象製品数: {len(product_ids)}")

    for product_id in product_ids:
        logger.info(f"製品ID {product_id} の在庫計算中...")

        # 実在庫を計算
        recalculate_stock_qty(line_id, product_id, start_date, end_date, firm_map=firm_map)

        # 計画在庫を計算
        recalculate_planned_stock_qty(line_id, product_id, start_date, end_date, firm_map=firm_map)

    logger.info("在庫再計算完了")
