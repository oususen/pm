"""
在庫計算ロジック
LineBacklogの在庫・計画在庫を再計算するためのユーティリティ
"""
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import F
from orders.models import OrderLine
from orders.utils.calendar_utils import get_business_today
from ..models_line_backlog import LineBacklog
from quality.models_scrap import ScrapRecord, ScrapRecordDetail


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
        'disposition_status__in': ['PENDING', 'PARTIAL', 'REJECTED', 'APPROVED'],
        'event_type__in': ['SCRAP', 'RETURN'],
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
        'scrap_record__disposition_status__in': ['PENDING', 'PARTIAL', 'REJECTED', 'APPROVED'],
        'scrap_record__event_type__in': ['SCRAP', 'RETURN'],
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


def _sum_parent_shipments(backlog, pick_qty, shift_fn=None):
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
        lead_days = bom_item.lead_time_days or 0
        parent_date = backlog.plan_date
        if shift_fn:
            parent_date = shift_fn(backlog.plan_date, lead_days)
        downstream_backlogs = LineBacklog.objects.filter(
            product=parent_product,
            plan_date=parent_date,
        )
        for downstream in downstream_backlogs:
            use_qty = pick_qty(downstream)
            if use_qty:
                total_shipment += Decimal(str(use_qty)) * Decimal(str(qty_per))

    return total_shipment


def _calculate_parent_actual_shipment(backlog):
    return _sum_parent_shipments(backlog, lambda d: d.actual_qty or 0)


def _calculate_parent_actual_shipment_with_lt(backlog, shift_fn):
    """
    後工程実績をLT遡りで計算（進度用）
    後工程で実績が入った日からLT分遡った日に出庫として計上
    """
    return _sum_parent_shipments(backlog, lambda d: d.actual_qty or 0, shift_fn)


def _calculate_parent_planned_shipment(backlog, today, shift_fn):
    if backlog.plan_date < today:
        return _sum_parent_shipments(backlog, lambda d: d.actual_qty or 0, shift_fn)
    if backlog.plan_date == today:
        def pick(d):
            plan_qty = d.plan_qty or 0
            actual_qty = d.actual_qty or 0
            return actual_qty if actual_qty > plan_qty else plan_qty
        return _sum_parent_shipments(backlog, pick, shift_fn)
    return _sum_parent_shipments(backlog, lambda d: d.plan_qty or 0, shift_fn)


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
    backlogs = list(LineBacklog.objects.filter(
        line_id=line_id,
        product_id=product_id,
        plan_date__range=[start_date, end_date]
    ).select_related('product').order_by('plan_date', 'sequence_no', 'id'))

    if not backlogs:
        return

    by_date = {}
    for backlog in backlogs:
        by_date.setdefault(backlog.plan_date, []).append(backlog)

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

    def pick_representative(rows):
        base_rows = [r for r in rows if r.sequence_no == 0]
        if base_rows:
            return min(base_rows, key=lambda r: r.id)
        plan_rows = [r for r in rows if (r.plan_qty or 0) > 0]
        candidates = plan_rows if plan_rows else rows
        return min(candidates, key=lambda r: (r.sequence_no if r.sequence_no is not None else 0, r.id))

    today = get_business_today()
    day_before_yesterday = today - timedelta(days=2)  # 前々日
    stock_by_date = {}
    firm_map = firm_map or {}

    # システム日付（8時区切り）の前々日の実在庫を初期値として取得
    # 前日ではなく前々日を使う理由：
    # - 7:59に実績入力（昨日の実績）→ 8:01に在庫計算の場合
    # - 前日の在庫はまだ7:59の実績が反映されていない可能性がある
    # - 前々日の在庫は確定しているので、そこから昨日・今日を再計算すれば正しい値になる
    initial_backlog = LineBacklog.objects.filter(
        line_id=line_id,
        product_id=product_id,
        plan_date__lte=day_before_yesterday,
        stock_qty__isnull=False
    ).order_by('-plan_date', 'sequence_no', 'id').first()

    if initial_backlog:
        last_stock = initial_backlog.stock_qty or 0
        stock_by_date[initial_backlog.plan_date] = last_stock
    else:
        last_stock = 0

    # 更新対象のbacklogを追跡（前々日以前は更新しない）
    yesterday = today - timedelta(days=1)
    backlogs_to_update = []

    for plan_date in sorted(by_date.keys()):
        rows = by_date[plan_date]
        sample = rows[0]
        is_final = bool(getattr(sample.product, 'is_final_product', False))

        # 前々日以前は既存の在庫値を使用し、更新しない
        if plan_date <= day_before_yesterday:
            # 既存の在庫値を取得してstock_by_dateに保持（後続の計算用）
            existing_stock = 0
            for row in rows:
                if row.stock_qty:
                    existing_stock = row.stock_qty
                    break
            stock_by_date[plan_date] = existing_stock
            last_stock = existing_stock
            continue

        actual_total = sum(r.actual_qty or 0 for r in rows)
        adjust_total = sum(r.adjust_qty or 0 for r in rows)
        scrap_total = sum(r.scrap_qty or 0 for r in rows)

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
            + adjust_total
            - scrap_total
        )

        rep = pick_representative(rows)
        for row in rows:
            row.actual_shipment_qty = 0
            row.stock_qty = 0
        rep.actual_shipment_qty = actual_shipment
        rep.stock_qty = stock_qty
        stock_by_date[plan_date] = stock_qty
        last_stock = stock_qty

        # 更新対象に追加
        backlogs_to_update.extend(rows)

    if backlogs_to_update:
        LineBacklog.objects.bulk_update(backlogs_to_update, ['stock_qty', 'actual_shipment_qty'])


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
    backlogs = list(LineBacklog.objects.filter(
        line_id=line_id,
        product_id=product_id,
        plan_date__range=[start_date, end_date]
    ).select_related('product').order_by('plan_date', 'sequence_no', 'id'))

    if not backlogs:
        return

    by_date = {}
    for backlog in backlogs:
        by_date.setdefault(backlog.plan_date, []).append(backlog)

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

    def pick_representative(rows):
        base_rows = [r for r in rows if r.sequence_no == 0]
        if base_rows:
            return min(base_rows, key=lambda r: r.id)
        plan_rows = [r for r in rows if (r.plan_qty or 0) > 0]
        candidates = plan_rows if plan_rows else rows
        return min(candidates, key=lambda r: (r.sequence_no if r.sequence_no is not None else 0, r.id))

    today = get_business_today()
    planned_by_date = {}
    last_planned = 0
    firm_map = firm_map or {}

    for plan_date in sorted(by_date.keys()):
        rows = by_date[plan_date]
        sample = rows[0]

        plan_total = sum(r.plan_qty or 0 for r in rows)
        actual_total = sum(r.actual_qty or 0 for r in rows)
        adjust_total = sum(r.adjust_qty or 0 for r in rows)
        scrap_total = sum(r.scrap_qty or 0 for r in rows)
        order_total = sum(r.order_qty or 0 for r in rows)

        is_final = bool(getattr(sample.product, 'is_final_product', False))
        if is_final:
            firm_qty = firm_map.get((sample.product_id, plan_date), Decimal('0'))
            if plan_date <= today:
                planned_shipment = firm_qty
            else:
                planned_shipment = firm_qty if firm_qty > 0 else Decimal(str(order_total))
        else:
            planned_shipment = _calculate_parent_planned_shipment(sample, today, shift_working_days)
        planned_shipment = int(planned_shipment or 0)

        prev_day = get_prev_working_day(plan_date)
        prev_planned = planned_by_date.get(prev_day, last_planned)

        if plan_date < today:
            planned_stock = (
                prev_planned
                + actual_total
                - planned_shipment
                + adjust_total
                - scrap_total
            )
        else:
            planned_stock = (
                prev_planned
                + plan_total
                - planned_shipment
                + adjust_total
                - scrap_total
            )

        rep = pick_representative(rows)
        for row in rows:
            row.planned_stock_qty = 0
        rep.planned_stock_qty = planned_stock
        planned_by_date[plan_date] = planned_stock
        last_planned = planned_stock

    LineBacklog.objects.bulk_update(backlogs, ['planned_stock_qty'])


def recalculate_progress_qty(line_id, product_id, start_date, end_date, firm_map=None):
    """
    進度を日次で再計算

    進度と在庫の違い：
    - 在庫: 後工程実績発生日に出庫計上（物理的な在庫を反映）
    - 進度: 後工程実績をLT遡りで計算（計画に対する進み/遅れを反映）

    計算式:
    進度 = 前日進度 + 実績 - 出庫（LT遡り） + 調整 - 仕損

    Args:
        line_id: ラインID
        product_id: 製品ID
        start_date: 開始日
        end_date: 終了日
        firm_map: 最終品の確定数量マップ
    """
    backlogs = list(LineBacklog.objects.filter(
        line_id=line_id,
        product_id=product_id,
        plan_date__range=[start_date, end_date]
    ).select_related('product').order_by('plan_date', 'sequence_no', 'id'))

    if not backlogs:
        return

    by_date = {}
    for backlog in backlogs:
        by_date.setdefault(backlog.plan_date, []).append(backlog)

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

    def shift_working_days(target_date, days):
        """
        稼働日でシフト。days > 0 なら未来へ、days < 0 なら過去へ。
        進度計算では後工程実績日からLT分「未来へ」シフトして
        前工程の出庫日を求める（= 前工程の日付からLT分「過去へ」遡った日に
        後工程実績があるか確認）
        """
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

    def pick_representative(rows):
        base_rows = [r for r in rows if r.sequence_no == 0]
        if base_rows:
            return min(base_rows, key=lambda r: r.id)
        plan_rows = [r for r in rows if (r.plan_qty or 0) > 0]
        candidates = plan_rows if plan_rows else rows
        return min(candidates, key=lambda r: (r.sequence_no if r.sequence_no is not None else 0, r.id))

    today = get_business_today()
    progress_by_date = {}
    last_progress = 0
    firm_map = firm_map or {}

    for plan_date in sorted(by_date.keys()):
        rows = by_date[plan_date]
        sample = rows[0]

        actual_total = sum(r.actual_qty or 0 for r in rows)
        adjust_total = sum(r.adjust_qty or 0 for r in rows)
        scrap_total = sum(r.scrap_qty or 0 for r in rows)

        is_final = bool(getattr(sample.product, 'is_final_product', False))

        if plan_date <= today:
            if is_final:
                # 最終品の進度出庫もLT遡りで確定を参照
                progress_shipment = firm_map.get((sample.product_id, plan_date), Decimal('0'))
            else:
                # 中間品: 後工程実績をLT遡りで計算
                progress_shipment = _calculate_parent_actual_shipment_with_lt(sample, shift_working_days)
        else:
            progress_shipment = Decimal('0')
        progress_shipment = int(progress_shipment or 0)

        prev_day = get_prev_working_day(plan_date)
        prev_progress = progress_by_date.get(prev_day, last_progress)

        progress_qty = (
            prev_progress
            + actual_total
            - progress_shipment
            + adjust_total
            - scrap_total
        )

        rep = pick_representative(rows)
        for row in rows:
            row.progress_qty = 0
        rep.progress_qty = progress_qty
        progress_by_date[plan_date] = progress_qty
        last_progress = progress_qty

    LineBacklog.objects.bulk_update(backlogs, ['progress_qty'])


def recalculate_inventory_for_line(line_id, start_date, end_date):
    """
    指定ラインの全製品について在庫を再計算

    Args:
        line_id: ラインID
        start_date: 開始日
        end_date: 終了日
    """
    import logging
    import time
    logger = logging.getLogger(__name__)

    overall_start = time.perf_counter()
    logger.info(f"在庫再計算開始: line_id={line_id}, {start_date} ~ {end_date}")

    # まず仕損数を集計
    scrap_start = time.perf_counter()
    aggregate_scrap_to_backlog(line_id, start_date, end_date)
    logger.info("仕損集計時間: %.3fs", time.perf_counter() - scrap_start)

    firm_start = time.perf_counter()
    firm_map = _build_firm_order_map(line_id, start_date, end_date)
    logger.info("確定受注マップ作成時間: %.3fs", time.perf_counter() - firm_start)

    # 製品ごとに在庫計算
    product_ids = list(LineBacklog.objects.filter(
        line_id=line_id,
        plan_date__range=[start_date, end_date]
    ).values_list('product_id', flat=True).distinct())

    logger.info(f"対象製品数: {len(product_ids)}")

    stock_total = 0.0
    planned_total = 0.0
    progress_total = 0.0
    stock_max = (0.0, None)
    planned_max = (0.0, None)
    progress_max = (0.0, None)

    for product_id in product_ids:
        logger.info(f"製品ID {product_id} の在庫計算中...")

        # 実在庫を計算
        t0 = time.perf_counter()
        recalculate_stock_qty(line_id, product_id, start_date, end_date, firm_map=firm_map)
        stock_elapsed = time.perf_counter() - t0
        stock_total += stock_elapsed
        if stock_elapsed > stock_max[0]:
            stock_max = (stock_elapsed, product_id)

        # 計画在庫を計算
        t1 = time.perf_counter()
        recalculate_planned_stock_qty(line_id, product_id, start_date, end_date, firm_map=firm_map)
        planned_elapsed = time.perf_counter() - t1
        planned_total += planned_elapsed
        if planned_elapsed > planned_max[0]:
            planned_max = (planned_elapsed, product_id)

        # 進度を計算
        t2 = time.perf_counter()
        recalculate_progress_qty(line_id, product_id, start_date, end_date, firm_map=firm_map)
        progress_elapsed = time.perf_counter() - t2
        progress_total += progress_elapsed
        if progress_elapsed > progress_max[0]:
            progress_max = (progress_elapsed, product_id)

    product_count = max(len(product_ids), 1)
    logger.info(
        "在庫再計算合計: stock=%.3fs (avg=%.3fs, max=%.3fs id=%s) planned=%.3fs (avg=%.3fs, max=%.3fs id=%s) progress=%.3fs (avg=%.3fs, max=%.3fs id=%s)",
        stock_total,
        stock_total / product_count,
        stock_max[0],
        stock_max[1],
        planned_total,
        planned_total / product_count,
        planned_max[0],
        planned_max[1],
        progress_total,
        progress_total / product_count,
        progress_max[0],
        progress_max[1],
    )
    logger.info("在庫再計算完了: total_time=%.3fs", time.perf_counter() - overall_start)
