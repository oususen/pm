from django.utils.dateparse import parse_date

from production.models_line_gantt_plan import LineGanttPlan


def get_gantt_plan_qty(line_id, process_id, dates_str):
    if not line_id or not process_id or not dates_str:
        return {}

    try:
        process_id_int = int(process_id)
    except (ValueError, TypeError):
        return {}

    date_list = []
    for date_text in str(dates_str).split(','):
        date_text = date_text.strip()
        if not date_text:
            continue
        parsed = parse_date(date_text)
        if parsed:
            date_list.append(parsed)
    if not date_list:
        return {}

    plans = LineGanttPlan.objects.filter(
        line_id=line_id,
        plan_date__in=date_list,
    )

    result = {}
    for plan in plans:
        if not plan.processes_plan:
            continue
        for process_plan in plan.processes_plan:
            if process_plan.get('process_id') != process_id_int:
                continue
            product_code = process_plan.get('output_product_code', '')
            qty = process_plan.get('quantity', 0)
            if not product_code or not qty:
                continue
            plan_date_str = str(plan.plan_date)
            if product_code not in result:
                result[product_code] = {}
            result[product_code][plan_date_str] = result[product_code].get(plan_date_str, 0) + qty

    return result
