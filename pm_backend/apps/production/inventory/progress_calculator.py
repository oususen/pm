"""
進度計算ロジック
LineBacklogの進度を再計算するためのユーティリティ
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Q

from masters.models import Calendar, CalendarDay, Line, RoutingStep
from ..models import LineDemand
from ..models_line_backlog import LineBacklog


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

    def pick_representative(rows):
        base_rows = [r for r in rows if r.sequence_no == 0]
        if base_rows:
            return min(base_rows, key=lambda r: r.id)
        plan_rows = [r for r in rows if (r.plan_qty or 0) > 0]
        candidates = plan_rows if plan_rows else rows
        return min(candidates, key=lambda r: (r.sequence_no if r.sequence_no is not None else 0, r.id))

    progress_by_date = {}
    last_progress = 0

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

    for plan_date in sorted(by_date.keys()):
        rows = by_date[plan_date]

        actual_total = sum(r.actual_qty or 0 for r in rows)
        adjust_total = sum(r.adjust_qty or 0 for r in rows)
        scrap_total = sum(r.scrap_qty or 0 for r in rows)

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
