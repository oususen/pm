"""
進度計算ロジック
LineBacklogの進度を再計算するためのユーティリティ
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Q

from masters.models import Calendar, CalendarDay, Line, RoutingStep
from orders.utils.calendar_utils import get_business_today
from ..models import LineDemand
from ..models_line_backlog import LineBacklog
from .inventory_calculator import _get_max_parent_bom_lead_time


def recalculate_progress_qty(line_id, product_id, start_date, end_date):
    """
    進度を日次で再計算

    進度は「顧客需要に対する実績の遅れ/先行」を表す。
    ラインの計画とは関係なく、顧客の需要（内示/確定）に対して、
    リードタイムを加味した現在の実績の遅れ・先行を計算する。

    計算式:
    進度 = 前日進度 + 実績 - 需要（LineDemandから取得） + 調整 - 仕損

    需要の取得:
    - LineDemandから取得（受注をRoutingでLT遡りして展開済み）
    - 確定（firm_qty）があれば確定を使用
    - 確定がなければ内示（forecast_qty）を使用
    - どちらもなければ 0

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

    # 行が存在しない日も進度を保持するため、ダミー行（sequence_no=0）を補完する
    if backlogs:
        sample_process_id = next((r.process_id for r in backlogs if r.process_id), None)
        if start_date and end_date and sample_process_id:
            existing_dates = {b.plan_date for b in backlogs}
            to_create = []
            current = start_date
            while current <= end_date:
                if current not in existing_dates:
                    to_create.append(LineBacklog(
                        plan_date=current,
                        process_id=sample_process_id,
                        product_id=product_id,
                        line_id=line_id,
                        sequence_no=0,
                        order_qty=0,
                        demand_qty_plan=0,
                        plan_qty=0,
                        actual_qty=0,
                        stock_qty=0,
                        planned_stock_qty=0,
                        adjust_qty=0,
                        scrap_adjust_qty=0,
                        scrap_qty=0,
                        actual_shipment_qty=0,
                    ))
                    existing_dates.add(current)
                current += timedelta(days=1)
            if to_create:
                LineBacklog.objects.bulk_create(to_create)
                # PK が無いオブジェクトを bulk_update に渡さないため、再取得して置き換える
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
        line_obj = Line.objects.filter(id=line_id).first()
        calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(
            calendar_code='daiso'
        ).values_list('id', flat=True).first()

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
        # カレンダに定義が無い日も週末は非稼働とする
        is_work = cal.is_working_day if cal is not None else target_date.weekday() < 5
        workday_cache[target_date] = is_work
        return is_work

    def get_prev_working_day(target_date):
        prev_date = target_date - timedelta(days=1)
        while not is_working_day(prev_date):
            prev_date = prev_date - timedelta(days=1)
        return prev_date

    def shift_working_days(target_date, days):
        """営業日ベースで日付をシフト"""
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
    # これにより、親製品の実績変更が子製品の過去の需要（LineDemand）に正しく反映される
    max_lt = _get_max_parent_bom_lead_time(product_id)
    calc_start_date = shift_working_days(today, -(max_lt + 1))
    progress_by_date = {}
    last_progress = 0
    planned_progress_by_date = {}
    last_planned_progress = 0

    # 計算開始日以前の進度を初期値として取得
    initial_backlog = LineBacklog.objects.filter(
        line_id=line_id,
        product_id=product_id,
        plan_date__lte=calc_start_date,
        progress_qty__isnull=False
    ).order_by('-plan_date', 'sequence_no', 'id').first()

    if initial_backlog:
        last_progress = initial_backlog.progress_qty or 0
        progress_by_date[initial_backlog.plan_date] = last_progress
        last_planned_progress = initial_backlog.planned_progress_qty or 0
        planned_progress_by_date[initial_backlog.plan_date] = last_planned_progress

    process_ids = {r.process_id for r in backlogs if r.process_id}
    step_map = {}
    if process_ids:
        steps = RoutingStep.objects.filter(
            line_id=line_id,
            process_id__in=process_ids,
        ).filter(
            Q(output_product_id=product_id) | Q(routing__product_id=product_id)
        ).select_related('routing', 'output_product')
        for step in steps:
            step_product_id = step.output_product_id or (step.routing.product_id if step.routing_id else None)
            if not step_product_id:
                continue
            step_key = (step.process_id, step_product_id)
            if step_key not in step_map:
                step_map[step_key] = step.id

    demand_by_step = {}
    demand_by_product = {}
    if start_date and end_date:
        demand_qs = LineDemand.objects.filter(
            line_id=line_id,
            plan_date__range=[start_date, end_date],
        )
        step_ids = set(step_map.values())
        if step_ids:
            demand_qs = demand_qs.filter(Q(routing_step_id__in=step_ids) | Q(product_id=product_id))
        else:
            demand_qs = demand_qs.filter(product_id=product_id)

        for demand in demand_qs:
            qty = Decimal('0')
            if demand.firm_qty and demand.firm_qty > 0:
                qty = demand.firm_qty
            elif demand.forecast_qty and demand.forecast_qty > 0:
                qty = demand.forecast_qty
            if demand.routing_step_id:
                key = (demand.plan_date, demand.routing_step_id)
                demand_by_step[key] = demand_by_step.get(key, Decimal('0')) + qty
            if demand.product_id:
                key = (demand.plan_date, demand.product_id)
                demand_by_product[key] = demand_by_product.get(key, Decimal('0')) + qty

    # 更新対象のbacklogを追跡（計算開始日以前は更新しない）
    backlogs_to_update = []

    for plan_date in sorted(by_date.keys()):
        rows = by_date[plan_date]
        working_day = is_working_day(plan_date)

        # 計算開始日以前は既存の進度値を使用し、更新しない
        if plan_date <= calc_start_date:
            existing_progress = 0
            existing_planned_progress = 0
            for row in rows:
                if row.progress_qty or row.planned_progress_qty:
                    existing_progress = row.progress_qty or 0
                    existing_planned_progress = row.planned_progress_qty or 0
                    break
            progress_by_date[plan_date] = existing_progress
            planned_progress_by_date[plan_date] = existing_planned_progress
            last_progress = existing_progress
            last_planned_progress = existing_planned_progress
            continue

        actual_total = sum(r.actual_qty or 0 for r in rows)
        plan_total = sum(r.plan_qty or 0 for r in rows)
        adjust_total = sum(r.adjust_qty or 0 for r in rows)
        scrap_adjust_total = sum(r.scrap_adjust_qty or 0 for r in rows)
        # 進度計算では scrap_qty を引かない（自製品の仕損は actual_qty 減算で対応済み）

        # LineDemandから需要を取得（LT遡り済み）
        # 確定優先、なければ内示、どちらもなければ0
        demand_qty = Decimal('0')
        process_id = rows[0].process_id if rows else None
        step_id = step_map.get((process_id, product_id)) if process_id else None
        if step_id:
            demand_qty = demand_by_step.get((plan_date, step_id), Decimal('0'))
        if demand_qty == 0:
            demand_qty = demand_by_product.get((plan_date, product_id), Decimal('0'))

        progress_shipment = int(demand_qty or 0)

        prev_day = get_prev_working_day(plan_date)
        prev_progress = progress_by_date.get(prev_day, last_progress)
        prev_planned_progress = planned_progress_by_date.get(prev_day, last_planned_progress)

        # 非稼働日は前営業日の進度をそのまま保持する
        if not working_day:
            progress_qty = prev_progress
            planned_progress_qty = prev_planned_progress
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
            backlogs_to_update.extend(rows)
            continue

        # 進度 = 前日進度 + 実績 - 需要 + 調整 + 非自工程仕損調整
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
        backlogs_to_update.extend(rows)

    if backlogs_to_update:
        LineBacklog.objects.bulk_update(backlogs_to_update, ['progress_qty', 'planned_progress_qty'])
