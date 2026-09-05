"""工程実績入力時のルーティング検証。"""

from django.db.models import Q

from masters.models import BOM, RoutingStep
from masters.services.routing_service import build_effective_routing_q


def get_valid_output_routing_steps(process, product, plan_date, line_id=None):
    """指定日に製品を出力する、対象ライン上の有効工程を返す。"""
    effective_line_id = line_id or getattr(process, 'line_id', None)
    if not process or not product or not plan_date or not effective_line_id:
        return []

    return list(
        RoutingStep.objects.filter(
            output_product_id=product.id,
            process_id__isnull=False,
        ).filter(
            build_effective_routing_q(plan_date, prefix='routing__')
        ).filter(
            Q(line_id=effective_line_id)
            | Q(line__isnull=True, process__line_id=effective_line_id)
        ).select_related('process', 'process__line', 'line')
    )


def is_valid_output_process(process, product, plan_date, line_id=None):
    """工程が指定製品の有効な出力工程かを判定する。連産品は除外する。"""
    if not product:
        return False
    if product.id in get_normal_output_product_ids(process, [product.id], plan_date, line_id=line_id):
        return True
    return product.id in get_coproduct_product_ids([product.id], plan_date)


def get_input_eligible_product_ids(process, product_ids, plan_date):
    """工程実績入力を許可する製品IDを一括で返す。"""
    candidate_ids = {int(product_id) for product_id in product_ids if product_id}
    if not process or not process.line_id or not plan_date or not candidate_ids:
        return set()

    normal_product_ids = get_normal_output_product_ids(process, candidate_ids, plan_date)
    return normal_product_ids | get_coproduct_product_ids(candidate_ids, plan_date)


def get_normal_output_product_ids(process, product_ids, plan_date, line_id=None):
    """工程・ライン・有効期間が一致する通常出力品番IDを返す。"""
    candidate_ids = {int(product_id) for product_id in product_ids if product_id}
    effective_line_id = line_id or getattr(process, 'line_id', None)
    if not process or not effective_line_id or not plan_date or not candidate_ids:
        return set()

    return set(
        RoutingStep.objects.filter(
            process_id=process.id,
            output_product_id__in=candidate_ids,
        ).filter(
            build_effective_routing_q(plan_date, prefix='routing__')
        ).filter(
            Q(line_id=effective_line_id)
            | Q(line__isnull=True, process__line_id=effective_line_id)
        ).values_list('output_product_id', flat=True).distinct()
    )


def get_coproduct_product_ids(product_ids, plan_date):
    """候補内で有効な連産BOMの親・子品番IDを返す。"""
    candidate_ids = {int(product_id) for product_id in product_ids if product_id}
    if not plan_date or not candidate_ids:
        return set()

    coproduct_product_ids = set()
    rows = BOM.objects.filter(
        is_active=True,
        is_coproduct=True,
        valid_from__lte=plan_date,
    ).filter(
        Q(valid_to__isnull=True) | Q(valid_to__gte=plan_date)
    ).filter(
        Q(parent_product_id__in=candidate_ids)
        | Q(items__child_product_id__in=candidate_ids)
    ).values_list('parent_product_id', 'items__child_product_id')
    for parent_product_id, child_product_id in rows:
        coproduct_product_ids.add(parent_product_id)
        if child_product_id:
            coproduct_product_ids.add(child_product_id)
    return coproduct_product_ids & candidate_ids


def is_coproduct_product(product, plan_date):
    """製品が当日時点で有効な連産BOMの親または子品番かを判定する。"""
    if not product or not plan_date:
        return False

    return product.id in get_coproduct_product_ids([product.id], plan_date)


def build_invalid_product_process_message(process, product):
    """ルーティング外の工程への入力拒否メッセージを返す。"""
    return (
        f'{product.product_code} は {process.process_code} '
        f'{process.process_name}工程の加工品ではないため、入力できません。'
    )
