"""工程実績入力時のルーティング検証。"""

from django.db.models import Q

from masters.models import BOM, RoutingStep
from masters.services.routing_service import build_effective_routing_q


def get_valid_output_routing_steps(process, product, plan_date):
    """指定日に製品を出力する、対象ライン上の有効工程を返す。"""
    if not process or not product or not plan_date or not process.line_id:
        return []

    line_id = process.line_id
    return list(
        RoutingStep.objects.filter(
            output_product_id=product.id,
            process_id__isnull=False,
        ).filter(
            build_effective_routing_q(plan_date, prefix='routing__')
        ).filter(
            Q(line_id=line_id)
            | Q(line__isnull=True, process__line_id=line_id)
        ).select_related('process', 'process__line', 'line')
    )


def is_valid_output_process(process, product, plan_date):
    """工程が指定製品の有効な出力工程かを判定する。連産品は除外する。"""
    if is_coproduct_product(product, plan_date):
        return True

    return any(
        step.process_id == process.id
        for step in get_valid_output_routing_steps(process, product, plan_date)
    )


def is_coproduct_product(product, plan_date):
    """製品が当日時点で有効な連産BOMの親または子品番かを判定する。"""
    if not product or not plan_date:
        return False

    return BOM.objects.filter(
        is_active=True,
        is_coproduct=True,
        valid_from__lte=plan_date,
    ).filter(
        Q(valid_to__isnull=True) | Q(valid_to__gte=plan_date)
    ).filter(
        Q(parent_product_id=product.id)
        | Q(items__child_product_id=product.id)
    ).exists()


def build_invalid_product_process_message(process, product):
    """ルーティング外の工程への入力拒否メッセージを返す。"""
    return (
        f'{product.product_code} は {process.process_code} '
        f'{process.process_name}工程の加工品ではないため、入力できません。'
    )
