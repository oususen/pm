"""
ルーティングの入力ミスや後からのライン/工程変更により、現行の有効ルーティングには
もう存在しない(製品×ライン×工程)の組み合わせでLineBacklog/LineDemandが残ってしまう
ケースを検出・削除するサービス。

現行ルーティングの判定は以下の2経路の合算で行う:
  1. m_routing_step (routing.product = 対象製品, routing.is_active=True) の line/process
  2. m_routing_step.output_product = 対象製品 (親製品のルーティング内でこの製品を
     produce する工程) の line/process

検出した孤立グループのうち、需要/計画/実績/調整/進度など全ての数値項目がゼロの
「ゴースト行」は安全に削除できる。数値が残っているグループ(過去にそのライン/工程で
実際に需要や進度が発生していた形跡があるもの)は `force=True` を明示しない限り
削除しない。

管理コマンド(find_orphan_line_backlog)とメンテナンス画面API(views_orphan_backlog.py)の
両方からこのサービスを利用する。
"""
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Max, Min, Sum

from masters.models import Product
from masters.models import RoutingStep
from production.models import LineDemand
from production.models_line_backlog import LineBacklog

BACKLOG_QTY_FIELDS = [
    'demand_qty_plan', 'order_qty', 'order_qty_actual', 'plan_qty', 'actual_qty', 'stock_qty',
    'planned_stock_qty', 'adjust_qty', 'scrap_adjust_qty', 'scrap_qty',
    'actual_shipment_qty', 'progress_qty', 'planned_progress_qty',
]

DEMAND_QTY_FIELDS = [
    'forecast_qty', 'firm_qty', 'plan_qty', 'actual_qty', 'plan_progress', 'actual_progress',
]


def _exclude_st_coproduct_groups(qs):
    excluded_product_ids = Product.objects.filter(
        is_virtual_set=True,
        product_code__istartswith='ST',
    ).values_list('id', flat=True)
    return qs.exclude(product_id__in=excluded_product_ids)


def _to_jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


def build_valid_line_process_maps():
    """製品ID -> 現行有効な{(line_id, process_id)}集合、および{line_id}集合を返す

    外作品のルーティングstepはprocess_id=Noneの場合がある。
    その場合もline_idは有効として扱う。
    """
    valid_line_process = defaultdict(set)
    valid_line_only = defaultdict(set)
    valid_line_any_process = defaultdict(set)

    steps = RoutingStep.objects.filter(
        routing__is_active=True,
        line_id__isnull=False,
    ).values('routing__product_id', 'output_product_id', 'line_id', 'process_id')
    for s in steps:
        line_id = s['line_id']
        process_id = s['process_id']
        # output_productのline_idで有効ラインを判定する
        target_id = s['output_product_id'] or s['routing__product_id']

        if process_id is not None:
            valid_line_process[target_id].add((line_id, process_id))
        else:
            valid_line_any_process[target_id].add(line_id)
        valid_line_only[target_id].add(line_id)

    return valid_line_process, valid_line_only, valid_line_any_process


def find_backlog_groups(product_code=None, include_st_coproduct=False):
    """LineBacklogの孤立グループ(ghosts, residuals)を検出する"""
    valid_line_process, _, valid_line_any_process = build_valid_line_process_maps()

    qs = LineBacklog.objects.all()
    if product_code:
        qs = qs.filter(product__product_code=product_code)
    if not include_st_coproduct:
        qs = _exclude_st_coproduct_groups(qs)

    groups = qs.values(
        'product_id', 'product__product_code', 'product__product_name',
        'line_id', 'line__line_code', 'line__line_name',
        'process_id', 'process__process_code', 'process__process_name',
    ).annotate(
        cnt=Count('id'),
        min_date=Min('plan_date'), max_date=Max('plan_date'),
        **{f'sum_{f}': Sum(f) for f in BACKLOG_QTY_FIELDS},
    )

    ghosts, residuals = [], []
    for g in groups:
        pid = g['product_id']
        lid = g['line_id']
        if (lid, g['process_id']) in valid_line_process.get(pid, set()):
            continue
        if lid in valid_line_any_process.get(pid, set()):
            continue
        is_all_zero = all((g[f'sum_{f}'] or 0) == 0 for f in BACKLOG_QTY_FIELDS)
        entry = {
            'product_id': g['product_id'],
            'product_code': g['product__product_code'],
            'product_name': g['product__product_name'],
            'line_id': g['line_id'],
            'line_code': g['line__line_code'],
            'line_name': g['line__line_name'],
            'process_id': g['process_id'],
            'process_code': g['process__process_code'],
            'process_name': g['process__process_name'],
            'count': g['cnt'],
            'min_date': _to_jsonable(g['min_date']),
            'max_date': _to_jsonable(g['max_date']),
            'sums': {f: _to_jsonable(g[f'sum_{f}'] or 0) for f in BACKLOG_QTY_FIELDS},
        }
        (ghosts if is_all_zero else residuals).append(entry)
    return ghosts, residuals


def find_demand_groups(product_code=None, include_st_coproduct=False):
    """LineDemandの孤立グループ(ghosts, residuals)を検出する"""
    _, valid_line_only, _ = build_valid_line_process_maps()

    qs = LineDemand.objects.exclude(product_id__isnull=True)
    if product_code:
        qs = qs.filter(product_code=product_code)
    if not include_st_coproduct:
        qs = _exclude_st_coproduct_groups(qs)

    groups = qs.values(
        'product_id', 'product_code', 'product__product_name',
        'line_id', 'line__line_code', 'line__line_name',
    ).annotate(
        cnt=Count('id'),
        min_date=Min('plan_date'), max_date=Max('plan_date'),
        **{f'sum_{f}': Sum(f) for f in DEMAND_QTY_FIELDS},
    )

    ghosts, residuals = [], []
    for g in groups:
        if g['line_id'] in valid_line_only.get(g['product_id'], set()):
            continue
        is_all_zero = all((g[f'sum_{f}'] or 0) == 0 for f in DEMAND_QTY_FIELDS)
        entry = {
            'product_id': g['product_id'],
            'product_code': g['product_code'],
            'product_name': g['product__product_name'],
            'line_id': g['line_id'],
            'line_code': g['line__line_code'],
            'line_name': g['line__line_name'],
            'count': g['cnt'],
            'min_date': _to_jsonable(g['min_date']),
            'max_date': _to_jsonable(g['max_date']),
            'sums': {f: _to_jsonable(g[f'sum_{f}'] or 0) for f in DEMAND_QTY_FIELDS},
        }
        (ghosts if is_all_zero else residuals).append(entry)
    return ghosts, residuals


def build_report(product_code=None, include_st_coproduct=False):
    backlog_ghosts, backlog_residuals = find_backlog_groups(
        product_code,
        include_st_coproduct=include_st_coproduct,
    )
    demand_ghosts, demand_residuals = find_demand_groups(
        product_code,
        include_st_coproduct=include_st_coproduct,
    )
    return {
        'backlog_ghosts': backlog_ghosts,
        'backlog_residuals': backlog_residuals,
        'demand_ghosts': demand_ghosts,
        'demand_residuals': demand_residuals,
    }


def apply_fix(backlog_targets=None, demand_targets=None):
    """
    指定されたグループを削除する。安全のため、削除直前に再度「現行ルーティングに
    合致しない孤立グループ」であることを確認してから削除する(force指定時も、
    現行ルーティングに合致するグループは絶対に削除しない)。

    backlog_targets: [{"product_id", "line_id", "process_id", "force": bool}, ...]
    demand_targets:  [{"product_id", "line_id", "force": bool}, ...]

    戻り値: {"deleted_backlog": int, "deleted_demand": int, "skipped": [str, ...]}
    """
    backlog_targets = backlog_targets or []
    demand_targets = demand_targets or []
    valid_line_process, valid_line_only, valid_line_any_process = build_valid_line_process_maps()

    skipped = []
    deleted_backlog = 0
    deleted_demand = 0

    with transaction.atomic():
        for t in backlog_targets:
            product_id, line_id, process_id = t['product_id'], t['line_id'], t['process_id']
            force = bool(t.get('force'))
            if (line_id, process_id) in valid_line_process.get(product_id, set()) or line_id in valid_line_any_process.get(product_id, set()):
                skipped.append(f'LineBacklog product_id={product_id} line_id={line_id} process_id={process_id}: 現行ルーティングに合致するためスキップ')
                continue
            if not force:
                qs = LineBacklog.objects.filter(product_id=product_id, line_id=line_id, process_id=process_id)
                sums = qs.aggregate(**{f'sum_{f}': Sum(f) for f in BACKLOG_QTY_FIELDS})
                is_all_zero = all((sums[f'sum_{f}'] or 0) == 0 for f in BACKLOG_QTY_FIELDS)
                if not is_all_zero:
                    skipped.append(f'LineBacklog product_id={product_id} line_id={line_id} process_id={process_id}: 数値が残っているためforce指定が必要')
                    continue
            deleted, _ = LineBacklog.objects.filter(
                product_id=product_id, line_id=line_id, process_id=process_id,
            ).delete()
            deleted_backlog += deleted

        for t in demand_targets:
            product_id, line_id = t['product_id'], t['line_id']
            force = bool(t.get('force'))
            if line_id in valid_line_only.get(product_id, set()):
                skipped.append(f'LineDemand product_id={product_id} line_id={line_id}: 現行ルーティングに合致するためスキップ')
                continue
            if not force:
                qs = LineDemand.objects.filter(product_id=product_id, line_id=line_id)
                sums = qs.aggregate(**{f'sum_{f}': Sum(f) for f in DEMAND_QTY_FIELDS})
                is_all_zero = all((sums[f'sum_{f}'] or 0) == 0 for f in DEMAND_QTY_FIELDS)
                if not is_all_zero:
                    skipped.append(f'LineDemand product_id={product_id} line_id={line_id}: 数値が残っているためforce指定が必要')
                    continue
            deleted, _ = LineDemand.objects.filter(product_id=product_id, line_id=line_id).delete()
            deleted_demand += deleted

    return {'deleted_backlog': deleted_backlog, 'deleted_demand': deleted_demand, 'skipped': skipped}
