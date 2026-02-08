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
from ..serializers_process_realtime import _resolve_product_process_line
from quality.models_scrap import ScrapRecord, ScrapRecordDetail


def aggregate_scrap_to_backlog(line_id=None, start_date=None, end_date=None):
    """
    ScrapRecordとScrapRecordDetailから仕損数を集計し、LineBacklogに反映

    新しい仕様:
    - 自工程仕損（ScrapRecord）: scrap_qty に保存（全ての仕損）
    - 後工程仕損の展開分（ScrapRecordDetail）: adjust_qty に保存（負の値として）

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
    # 仕損由来の adjust_qty もリセット（他の調整との区別が難しいため注意）
    # ※ 現状は adjust_qty を使っている他の機能がないためリセット可能
    # LineBacklog.objects.filter(**reset_filter).update(adjust_qty=0)

    # 自工程仕損の集計（全ての仕損を scrap_qty に保存）
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

        # 製品のRoutingStepから正しい工程/ラインを取得（発生工程と異なる場合に対応）
        actual_process, actual_line = _resolve_product_process_line(scrap.product, scrap.process)
        if not actual_line:
            actual_line = getattr(actual_process, 'line', None)
        if not actual_line:
            continue

        LineBacklog.objects.get_or_create(
            plan_date=scrap.plan_date,
            product=scrap.product,
            line=actual_line,
            process=actual_process,
            sequence_no=0,
        )
        LineBacklog.objects.filter(
            plan_date=scrap.plan_date,
            product=scrap.product,
            line=actual_line,
            process=actual_process,
            sequence_no=0,
        ).update(scrap_qty=F('scrap_qty') + int(scrap.qty))

    # 後工程仕損の展開分（子部品）は adjust_qty に保存（負の値として）
    # 未処理のレコードのみ対象（is_backlog_processed=False）
    detail_filter = {
        'scrap_record__disposition_status__in': ['PENDING', 'PARTIAL', 'REJECTED', 'APPROVED'],
        'scrap_record__event_type__in': ['SCRAP', 'RETURN'],
        'scrap_record__plan_date__isnull': False,
        'is_backlog_processed': False,  # 未処理のみ
    }
    if line_id:
        detail_filter['line_id'] = line_id
    if start_date and end_date:
        detail_filter['scrap_record__plan_date__range'] = [start_date, end_date]

    details = ScrapRecordDetail.objects.filter(**detail_filter).select_related('scrap_record', 'product')
    processed_detail_ids = []

    for detail in details:
        if not detail.product or not detail.line_id or not detail.process_id:
            continue
        # 自製品（親と同じ製品）はスキップ（scrap_qty で既に処理済み）
        if (detail.product_id == detail.scrap_record.product_id
            and detail.line_id == detail.scrap_record.line_id
            and detail.process_id == detail.scrap_record.process_id):
            # 自製品でも処理済みフラグは立てる
            processed_detail_ids.append(detail.id)
            continue

        LineBacklog.objects.get_or_create(
            plan_date=detail.scrap_record.plan_date,
            product=detail.product,
            line_id=detail.line_id,
            process_id=detail.process_id,
            sequence_no=0,
        )
        # 子部品は adjust_qty に負の値として保存（在庫減算のため）
        LineBacklog.objects.filter(
            plan_date=detail.scrap_record.plan_date,
            product=detail.product,
            line_id=detail.line_id,
            process_id=detail.process_id,
            sequence_no=0,
        ).update(adjust_qty=F('adjust_qty') - int(detail.deduct_qty))
        processed_detail_ids.append(detail.id)

    # 処理済みフラグを更新
    if processed_detail_ids:
        ScrapRecordDetail.objects.filter(id__in=processed_detail_ids).update(is_backlog_processed=True)


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
        calendar_code='daiso'
    ).values_list('id', flat=True).first()
    workday_cache = {}

    def is_working_day(target_date):
        # カレンダー未設定時は土日を非稼働日として扱う
        if not calendar_id:
            return target_date.weekday() < 5
        if target_date in workday_cache:
            return workday_cache[target_date]
        cal = CalendarDay.objects.filter(
            calendar_id=calendar_id,
            target_date=target_date
        ).first()
        # カレンダ未登録日は週末を非稼働日扱い
        is_work = cal.is_working_day if cal is not None else target_date.weekday() < 5
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


def _get_max_parent_bom_lead_time(product_id):
    """
    製品を子製品として持つBOMの最大リードタイムを取得

    Args:
        product_id: 製品ID

    Returns:
        int: 最大リードタイム（日）。BOMがない場合は0
    """
    from masters.models import BOMItem
    max_lt = BOMItem.objects.filter(
        child_product_id=product_id,
        bom__is_active=True
    ).values_list('lead_time_days', flat=True)
    return max(max_lt, default=0) or 0


def _sum_parent_shipments(backlog, pick_qty, shift_fn=None):
    from masters.models import BOMItem

    # 連産品（is_coproduct=True）のBOMは除外
    # 連産品の実績は通常の親製品とは別扱いのため、出庫計算に含めない
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


def _get_shipment_scrap_qty(product_id, line_id, process_id, plan_date):
    """
    出庫計算用の仕損数量を取得（全ての仕損）

    仕損が発生した場合、子部品も消費されているため、出庫として計上する。
    is_production_recorded に関係なく全ての仕損を含める。
    """
    from django.db.models import Sum
    result = ScrapRecord.objects.filter(
        product_id=product_id,
        line_id=line_id,
        process_id=process_id,
        plan_date=plan_date,
        disposition_status__in=['PENDING', 'PARTIAL', 'REJECTED', 'APPROVED'],
        event_type__in=['SCRAP', 'RETURN'],
    ).aggregate(total=Sum('qty'))
    return result['total'] or Decimal('0')


def _calculate_parent_actual_shipment(backlog, shift_fn=None):
    """
    実在庫・計画在庫用の実績出庫計算（後工程の実績 + 仕損を使用）

    親製品の仕損も出庫として計上する。
    仕損が発生した場合、子部品も消費されているため、全ての仕損を出庫に含める。

    Args:
        backlog: LineBacklogインスタンス
        shift_fn: LTシフト関数（営業日ベースで日付をシフト）
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
        lead_days = bom_item.lead_time_days or 0
        parent_date = backlog.plan_date
        if shift_fn:
            parent_date = shift_fn(backlog.plan_date, lead_days)
        downstream_backlogs = LineBacklog.objects.filter(
            product=parent_product,
            plan_date=parent_date,
        )
        for downstream in downstream_backlogs:
            actual = downstream.actual_qty or 0
            # 全ての仕損を出庫に含める
            scrap = _get_shipment_scrap_qty(
                downstream.product_id,
                downstream.line_id,
                downstream.process_id,
                downstream.plan_date
            )
            use_qty = actual + scrap
            if use_qty:
                total_shipment += Decimal(str(use_qty)) * Decimal(str(qty_per))

    return total_shipment


def _calculate_parent_actual_or_plan_shipment(backlog, shift_fn=None):
    """
    計画在庫用の出庫計算（実績優先、なければ計画を使用）+ 仕損

    LTシフト後の親製品の日付で：
    - 実績がある場合 → 実績 + 仕損（全て）を使用
    - 実績がない場合 → 計画数を使用
    - どちらもない場合 → 0

    Args:
        backlog: LineBacklogインスタンス
        shift_fn: LTシフト関数（営業日ベースで日付をシフト）
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
        lead_days = bom_item.lead_time_days or 0
        parent_date = backlog.plan_date
        if shift_fn:
            parent_date = shift_fn(backlog.plan_date, lead_days)
        downstream_backlogs = LineBacklog.objects.filter(
            product=parent_product,
            plan_date=parent_date,
        )
        for downstream in downstream_backlogs:
            actual = downstream.actual_qty or 0
            # 全ての仕損を出庫に含める
            scrap = _get_shipment_scrap_qty(
                downstream.product_id,
                downstream.line_id,
                downstream.process_id,
                downstream.plan_date
            )
            if actual > 0 or scrap > 0:
                use_qty = actual + scrap
            else:
                use_qty = downstream.plan_qty or 0
            if use_qty:
                total_shipment += Decimal(str(use_qty)) * Decimal(str(qty_per))

    return total_shipment


def _calculate_parent_planned_shipment(backlog, today, shift_fn):
    """
    計画在庫用の出庫計算（後工程の計画値＝内示を使用）+ 仕損

    計画在庫は「計画ベース」の値なので、出庫も計画値（内示）を使用する。
    これは実在庫（後工程の実績を使用）とは異なる点。
    ただし、仕損は実績なので計画値に加算する。

    - 今日以降: 後工程の計画値 + 仕損（全て）で計算

    ※ 実在庫の出庫は _calculate_parent_actual_shipment で actual_qty + scrap_qty を使用
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
        lead_days = bom_item.lead_time_days or 0
        parent_date = backlog.plan_date
        if shift_fn:
            parent_date = shift_fn(backlog.plan_date, lead_days)
        downstream_backlogs = LineBacklog.objects.filter(
            product=parent_product,
            plan_date=parent_date,
        )
        for downstream in downstream_backlogs:
            plan = downstream.plan_qty or 0
            # 全ての仕損を出庫に含める
            scrap = _get_shipment_scrap_qty(
                downstream.product_id,
                downstream.line_id,
                downstream.process_id,
                downstream.plan_date
            )
            use_qty = plan + scrap
            if use_qty:
                total_shipment += Decimal(str(use_qty)) * Decimal(str(qty_per))

    return total_shipment


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
    day_before_yesterday = get_prev_working_day(get_prev_working_day(today))  # 前々営業日
    stock_by_date = {}
    firm_map = firm_map or {}

    # システム日付（8時区切り）の前々営業日の実在庫を初期値として取得
    # 前日ではなく前々営業日を使う理由：
    # - 7:59に実績入力（昨日の実績）→ 8:01に在庫計算の場合
    # - 前日の在庫はまだ7:59の実績が反映されていない可能性がある
    # - 前々営業日の在庫は確定しているので、そこから昨日・今日を再計算すれば正しい値になる
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

    # 更新対象のbacklogを追跡（前々営業日以前は更新しない）
    yesterday = today - timedelta(days=1)
    backlogs_to_update = []

    for plan_date in sorted(by_date.keys()):
        rows = by_date[plan_date]
        sample = rows[0]
        is_final = bool(getattr(sample.product, 'is_final_product', False))

        # 前々営業日以前は既存の在庫値を使用し、更新しない
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
        # 在庫計算では adjust_qty を使用しない
        # 仕損による子部品の消費は、出庫計算（親の実績+仕損）で反映される

        if plan_date <= today:
            if is_final:
                actual_shipment = firm_map.get((sample.product_id, plan_date), Decimal('0'))
            else:
                # 親の actual_qty + scrap_qty を出庫として計算
                actual_shipment = _calculate_parent_actual_shipment(sample)
        else:
            actual_shipment = Decimal('0')
        actual_shipment = int(actual_shipment or 0)

        prev_day = get_prev_working_day(plan_date)
        prev_stock = stock_by_date.get(prev_day, last_stock)

        # 在庫 = 前日在庫 + 実績 - 出庫(親の実績+仕損)
        # 仕損による子部品消費は出庫計算で反映済み（adjust_qty は使用しない）
        stock_qty = (
            prev_stock
            + actual_total
            - actual_shipment
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
    # 製品のBOMの最大LTを取得し、LT+1日前から再計算
    # これにより、親製品の実績変更が子製品の過去の出庫に正しく反映される
    max_lt = _get_max_parent_bom_lead_time(product_id)
    calc_start_date = shift_working_days(today, -(max_lt + 1))
    planned_by_date = {}
    firm_map = firm_map or {}

    # 計算開始日以前の実在庫を初期値として取得
    initial_backlog = LineBacklog.objects.filter(
        line_id=line_id,
        product_id=product_id,
        plan_date__lte=calc_start_date,
        stock_qty__isnull=False
    ).order_by('-plan_date', 'sequence_no', 'id').first()

    if initial_backlog:
        last_planned = initial_backlog.stock_qty or 0
        planned_by_date[initial_backlog.plan_date] = last_planned
    else:
        last_planned = 0

    # 更新対象のbacklogを追跡（計算開始日以前は更新しない）
    backlogs_to_update = []

    for plan_date in sorted(by_date.keys()):
        rows = by_date[plan_date]
        sample = rows[0]

        # 計算開始日以前は実在庫の値を使用し、更新しない
        if plan_date <= calc_start_date:
            # 既存の実在庫値を取得してplanned_by_dateに保持（後続の計算用）
            existing_stock = 0
            for row in rows:
                if row.stock_qty:
                    existing_stock = row.stock_qty
                    break
            planned_by_date[plan_date] = existing_stock
            last_planned = existing_stock
            continue

        plan_total = sum(r.plan_qty or 0 for r in rows)
        actual_total = sum(r.actual_qty or 0 for r in rows)
        # 計画在庫計算でも adjust_qty を使用しない
        # 仕損による子部品の消費は、出庫計算（親の実績/計画+仕損）で反映される
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

        # 計画在庫 = 前日計画在庫 + 実績/計画 - 出庫
        # 仕損による子部品消費は出庫計算で反映済み（adjust_qty は使用しない）
        if plan_date < today:
            planned_stock = (
                prev_planned
                + actual_total
                - planned_shipment
            )
        else:
            planned_stock = (
                prev_planned
                + plan_total
                - planned_shipment
            )

        rep = pick_representative(rows)
        for row in rows:
            row.planned_stock_qty = 0
        rep.planned_stock_qty = planned_stock
        planned_by_date[plan_date] = planned_stock
        last_planned = planned_stock

        # 更新対象に追加
        backlogs_to_update.extend(rows)

    if backlogs_to_update:
        LineBacklog.objects.bulk_update(backlogs_to_update, ['planned_stock_qty'])


def recalculate_inventory_for_line(line_id, start_date, end_date, include_progress=True, line_final_only=False):
    """
    指定ラインの全製品について在庫を再計算

    Args:
        line_id: ラインID
        start_date: 開始日
        end_date: 終了日
        include_progress: 進度も再計算するか（デフォルト: True）
        line_final_only: ライン最終品のみ計算するか（デフォルト: False）
    """
    import logging
    import time
    logger = logging.getLogger(__name__)

    overall_start = time.perf_counter()
    logger.info(f"在庫再計算開始: line_id={line_id}, {start_date} ~ {end_date}, line_final_only={line_final_only}")

    # まず仕損数を集計
    scrap_start = time.perf_counter()
    aggregate_scrap_to_backlog(line_id, start_date, end_date)
    logger.info("仕損集計時間: %.3fs", time.perf_counter() - scrap_start)

    firm_start = time.perf_counter()
    firm_map = _build_firm_order_map(line_id, start_date, end_date)
    logger.info("確定受注マップ作成時間: %.3fs", time.perf_counter() - firm_start)

    # 製品ごとに在庫計算
    product_qs = LineBacklog.objects.filter(
        line_id=line_id,
        plan_date__range=[start_date, end_date]
    )
    if line_final_only:
        product_qs = product_qs.filter(product__is_line_final_product=True)
    product_ids = list(product_qs.values_list('product_id', flat=True).distinct())

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

        if include_progress:
            from .progress_calculator import recalculate_progress_qty

            # 進度を計算
            t2 = time.perf_counter()
            recalculate_progress_qty(line_id, product_id, start_date, end_date)
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
        progress_total / product_count if include_progress else 0.0,
        progress_max[0],
        progress_max[1],
    )
    logger.info("在庫再計算完了: total_time=%.3fs", time.perf_counter() - overall_start)
