"""親品と実在する直上工程の整合性を、API・管理画面で共通に検証する。"""
from django.core.exceptions import ValidationError


def validate_routing_parent(parent_id, output_id, routing_id, path, step_id=None):
    # 親未指定、自己親の中間工程、最上位・finalは既存仕様を維持する。
    if not parent_id or not output_id or parent_id == output_id or not routing_id or '.' not in (path or ''):
        return
    from masters.models import RoutingStep
    parents = RoutingStep.objects.filter(routing_id=routing_id, hierarchy_path=path.rsplit('.', 1)[0])
    if step_id:
        parents = parents.exclude(pk=step_id)
    # 既存の親工程欠落を推定補完しない。
    if parents.exists() and not parents.filter(output_product_id=parent_id).exists():
        raise ValidationError({'parent_product': '親製品が直上工程の加工後品と一致しません。工程構成を確認してください。'})
