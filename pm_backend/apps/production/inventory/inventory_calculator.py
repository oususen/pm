"""
在庫計算ロジック
LineBacklogの在庫・計画在庫を再計算するためのユーティリティ
"""
from datetime import datetime, timedelta
from decimal import Decimal
import json
from django.db.models import F
from orders.utils.calendar_utils import get_business_today
from system_settings.models import SystemSetting
from ..models_line_backlog import LineBacklog
from ..models_line_backlog_adjustment import LineBacklogAdjustment
from ..serializers_process_realtime import _resolve_product_process_line
from .lead_time_utils import resolve_lead_days_for_step
from quality.models_scrap import ScrapRecord, ScrapRecordDetail

PLANNED_STOCK_CALC_RULES_KEY = 'production.planned_stock_calc_rules'


def _load_planned_stock_calc_rule_map():
    """
    計算特例設定を読み込み、(line_code, process_code, calc_target) -> setting の辞書で返す。
    """
    row = SystemSetting.objects.filter(key=PLANNED_STOCK_CALC_RULES_KEY).first()
    if not row or not row.value:
        return {}
    try:
        raw = json.loads(row.value)
    except Exception:
        return {}
    if not isinstance(raw, list):
        return {}
    result = {}
    for item in raw:
        line_code = str((item or {}).get('lineCode') or '').strip().upper()
        process_code = str((item or {}).get('processCode') or '').strip().upper()
        calc_target = str((item or {}).get('calcTarget') or '').strip().upper()
        setting = str((item or {}).get('setting') or '').strip().upper()
        # 旧形式互換
        old_item = str((item or {}).get('item') or '').strip().upper()
        old_mode = str((item or {}).get('mode') or '').strip().upper()
        if old_item == 'PARENT_SHIPMENT_SOURCE' and old_mode == 'PLAN':
            calc_target = calc_target or 'PLANNED_STOCK'
            setting = 'ORDER_QTY'
        if setting == 'PARENT_PLAN':
            setting = 'ORDER_QTY'
        if not line_code or not process_code:
            continue
        if calc_target not in {'STOCK', 'PLANNED_STOCK'}:
            continue
        if setting not in {'ORDER_QTY', 'ACTUAL_OR_PLAN'}:
            continue
        result[(line_code, process_code, calc_target)] = setting
    return result


def aggregate_scrap_to_backlog(line_id=None, start_date=None, end_date=None, product_ids=None):
    """
    ScrapRecordとScrapRecordDetailから仕損数を集計し、LineBacklogに反映

    新しい仕様:
    - 自工程仕損（ScrapRecord）: scrap_qty に保存（全ての仕損）
    - 後工程仕損の展開分（ScrapRecordDetail）: adjust_qty に保存（負の値として）

    Args:
        line_id: 対象ラインID（Noneの場合は全ライン）
        start_date: 開始日
        end_date: 終了日
        product_ids: 対象製品ID配列（指定時はその製品のみ集計）
    """
    target_product_ids = {int(pid) for pid in (product_ids or []) if pid is not None}

    # まず対象期間・対象ラインを決めるために ScrapRecord を取得し、影響する line_id を集計する
    scrap_filter = {
        'disposition_status__in': ['PENDING', 'PARTIAL', 'REJECTED', 'APPROVED'],
        'event_type__in': ['SCRAP', 'RETURN'],
        'plan_date__isnull': False,
    }
    if start_date and end_date:
        scrap_filter['plan_date__range'] = [start_date, end_date]
    if target_product_ids:
        scrap_filter['product_id__in'] = list(target_product_ids)

    # 発生ラインで絞り込むと、前工程品が別ラインに計上されるケースを取りこぼすため、
    # line_id 指定時もフィルタしないで取得し、後段で actual_line で判定する。
    scrap_records = ScrapRecord.objects.filter(**scrap_filter).select_related('product', 'line', 'process')

    # 影響するラインID（集計先の actual_line_id と、明細に含まれる line_id）を集める
    # line_id 指定時はそのラインのみリセット対象にする。未指定の場合は影響ラインを集計する。
    if line_id:
        affected_line_ids = {line_id}
    else:
        affected_line_ids = set()
        for scrap in scrap_records:
            actual_process, actual_line = _resolve_product_process_line(scrap.product, scrap.process)
            if not actual_line:
                actual_line = getattr(actual_process, 'line', None)
            if actual_line:
                affected_line_ids.add(actual_line.id if hasattr(actual_line, 'id') else actual_line)

    # 明細（子部品）の line_id も影響ラインに含める
    detail_filter = {
        'scrap_record__disposition_status__in': ['PENDING', 'PARTIAL', 'REJECTED', 'APPROVED'],
        'scrap_record__event_type__in': ['SCRAP', 'RETURN'],
        'scrap_record__plan_date__isnull': False,
        'is_backlog_processed': False,  # 未処理のみ
    }
    if start_date and end_date:
        detail_filter['scrap_record__plan_date__range'] = [start_date, end_date]
    if target_product_ids:
        detail_filter['product_id__in'] = list(target_product_ids)

    details = ScrapRecordDetail.objects.filter(**detail_filter).select_related('scrap_record', 'product')
    if not line_id:
        for detail in details:
            if detail.line_id:
                affected_line_ids.add(detail.line_id)

    # リセット対象を限定（影響ライン × 対象期間）
    reset_filter = {}
    if affected_line_ids:
        reset_filter['line_id__in'] = list(affected_line_ids)
    elif line_id:
        reset_filter['line_id'] = line_id
    if start_date and end_date:
        reset_filter['plan_date__range'] = [start_date, end_date]
    if target_product_ids:
        reset_filter['product_id__in'] = list(target_product_ids)

    LineBacklog.objects.filter(**reset_filter).update(scrap_qty=0, scrap_adjust_qty=0)
    # 仕損由来の adjust_qty もリセット（他の調整との区別が難しいため注意）
    # ※ 現状は adjust_qty を使っている他の機能がないためリセット可能
    # LineBacklog.objects.filter(**reset_filter).update(adjust_qty=0)

    # 自工程仕損の集計（全ての仕損を scrap_qty に保存）
    # ※ scrap_records は前段で取得済み

    for scrap in scrap_records:
        if not scrap.product or not scrap.line or not scrap.process:
            continue

        # 製品のRoutingStepから正しい工程/ラインを取得（発生工程と異なる場合に対応）
        actual_process, actual_line = _resolve_product_process_line(scrap.product, scrap.process)
        if not actual_line:
            actual_line = getattr(actual_process, 'line', None)
        if not actual_line:
            continue

        if line_id and getattr(actual_line, 'id', actual_line) != line_id:
            # 指定ラインの再計算時は、そのラインに計上されるものだけ処理
            continue
        if target_product_ids and scrap.product_id not in target_product_ids:
            continue

        LineBacklog.objects.get_or_create(
            plan_date=scrap.plan_date,
            product=scrap.product,
            line=actual_line,
            process=actual_process,
            sequence_no=0,
        )
        # 自工程生産品か判定（製品の工程=発生工程）→ scrap_qty、異なれば scrap_adjust_qty にマイナス
        is_self = actual_process.id == scrap.process_id
        if is_self:
            LineBacklog.objects.filter(
                plan_date=scrap.plan_date,
                product=scrap.product,
                line=actual_line,
                process=actual_process,
                sequence_no=0,
            ).update(scrap_qty=F('scrap_qty') + int(scrap.qty))
        else:
            LineBacklog.objects.filter(
                plan_date=scrap.plan_date,
                product=scrap.product,
                line=actual_line,
                process=actual_process,
                sequence_no=0,
            ).update(scrap_adjust_qty=F('scrap_adjust_qty') - int(scrap.qty))

    # 後工程仕損の展開分（子部品）は adjust_qty に保存（負の値として）
    # 未処理のレコードのみ対象（is_backlog_processed=False）
    processed_detail_ids = []

    for detail in details:
        if not detail.product or not detail.line_id or not detail.process_id:
            continue
        if line_id and detail.line_id != line_id:
            # 対象ライン以外の子部品はスキップ（line_id 未指定時は全件）
            continue
        if target_product_ids and detail.product_id not in target_product_ids:
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


def _build_demand_map(line_id, start_date, end_date):
    """
    最終品（is_final_product=True）の需要を (product_id, plan_date) で集計。
    LineDemandから取得（plan_dateはLTシフト済み）。確定優先。
    """
    from collections import defaultdict
    from production.models import LineDemand

    demands = LineDemand.objects.filter(
        line_id=line_id,
        product__is_final_product=True,
        plan_date__gte=start_date,
        plan_date__lte=end_date,
    )

    firm_by_key = defaultdict(Decimal)
    forecast_by_key = defaultdict(Decimal)
    shifted_keys = set()
    for ld in demands:
        key = (ld.product_id, ld.plan_date)
        firm_qty = Decimal(str(ld.firm_qty or 0))
        forecast_qty = Decimal(str(ld.forecast_qty or 0))
        if firm_qty > 0:
            firm_by_key[key] += firm_qty
        if forecast_qty > 0:
            forecast_by_key[key] += forecast_qty
        if ld.is_shifted or ld.firm_is_shifted or ld.forecast_is_shifted:
            shifted_keys.add(key)

    demand_map = {}
    for key in set(firm_by_key) | set(forecast_by_key):
        firm = firm_by_key.get(key, Decimal('0'))
        forecast = forecast_by_key.get(key, Decimal('0'))
        if key in shifted_keys and firm > 0 and forecast > 0:
            demand_map[key] = firm + forecast
        else:
            demand_map[key] = firm if firm > 0 else forecast

    return demand_map


def _get_direct_parent_bom_lead_time(product_id):
    """
    直親BOMの最大lead_time_daysを返す（在庫・計画在庫用）。
    累積LTではなく、直接の親BOMアイテムのLTのみを参照する。
    """
    from masters.models import BOMItem
    if not product_id:
        return 0
    max_lt = BOMItem.objects.filter(
        child_product_id=product_id,
        bom__is_active=True,
    ).values_list('lead_time_days', flat=True)
    return int(max(max_lt, default=0) or 0)


def _get_max_parent_bom_lead_time(product_id):
    """
    製品の完成品向け累積LT（自分LTを含む）を取得する。

    優先ロジック:
    1. RoutingStep（output_product=対象製品）から、完成品までの階層累積LTの最大値を使用
       - final工程のLTを起点に、hierarchy_path で子階層へ伝播した total LT を採用
       - 対象製品の候補工程が複数ある場合は最大値
    2. 1が取得できない場合は、従来互換として直親BOMの最大 lead_time_days を使用

    Args:
        product_id: 製品ID

    Returns:
        int: 最大リードタイム（日）
    """
    from masters.models import BOMItem, RoutingStep
    from masters.services.routing_service import build_effective_routing_q

    if not product_id:
        return 0

    def fallback_direct_parent_lt():
        max_lt = BOMItem.objects.filter(
            child_product_id=product_id,
            bom__is_active=True,
        ).values_list('lead_time_days', flat=True)
        return int(max(max_lt, default=0) or 0)

    step_qs = RoutingStep.objects.filter(
        output_product_id=product_id,
    ).filter(
        build_effective_routing_q(prefix='routing__')
    ).select_related('line', 'output_product')

    candidate_steps = list(step_qs)
    if not candidate_steps:
        return fallback_direct_parent_lt()

    routing_ids = {s.routing_id for s in candidate_steps if s.routing_id}
    if not routing_ids:
        return fallback_direct_parent_lt()

    steps = list(
        RoutingStep.objects.filter(routing_id__in=routing_ids)
        .filter(build_effective_routing_q(prefix='routing__'))
        .select_related('line', 'output_product')
    )

    def path_key(path):
        try:
            return tuple(int(p) for p in str(path).split('.'))
        except Exception:
            return (str(path),)

    lt_by_step = {}
    for routing_id in routing_ids:
        routing_steps = [s for s in steps if s.routing_id == routing_id]
        if not routing_steps:
            continue

        step_map = {
            s.hierarchy_path: s
            for s in routing_steps
            if s.hierarchy_path and s.hierarchy_path != 'final'
        }
        children_map = {}
        for path in step_map.keys():
            parent_path = path.rsplit('.', 1)[0] if '.' in path else None
            children_map.setdefault(parent_path, []).append(path)

        final_step = next((s for s in routing_steps if s.hierarchy_path == 'final'), None)
        base_days = 0
        if final_step:
            base_days = resolve_lead_days_for_step(final_step)
            lt_by_step[final_step.id] = {'total': base_days, 'self': base_days}

        def compute(path, parent_days):
            step = step_map.get(path)
            if not step:
                return
            self_days = resolve_lead_days_for_step(step)
            total_days = parent_days + self_days
            lt_by_step[step.id] = {'total': total_days, 'self': self_days}
            for child_path in sorted(children_map.get(path, []), key=path_key):
                compute(child_path, total_days)

        for root_path in sorted(children_map.get(None, []), key=path_key):
            compute(root_path, base_days)

        # hierarchy_path が無いデータでも最低限 self LT を返せるようにする
        for step in routing_steps:
            if step.id in lt_by_step:
                continue
            self_days = resolve_lead_days_for_step(step)
            lt_by_step[step.id] = {'total': self_days, 'self': self_days}

    cumulative_lt = 0
    for step in candidate_steps:
        val = (lt_by_step.get(step.id) or {}).get('total')
        if val is not None and int(val) > cumulative_lt:
            cumulative_lt = int(val)

    return max(cumulative_lt, fallback_direct_parent_lt())


def _get_final_product_delivery_lt(line_id, product_id):
    """
    ライン最終品/最終品のデリバリLT（RoutingStep / Line.lead_time_days）を取得する。
    計画在庫初期値のLT調整に使用するデリバリLT。
    demand_map（LineDemand由来）のplan_dateは同じLTでシフト済み。
    """
    from masters.models import RoutingStep
    from django.db.models import Q
    step = (
        RoutingStep.objects.filter(
            Q(line_id=line_id) | Q(line__isnull=True, process__line_id=line_id)
        )
        .filter(
            Q(output_product_id=product_id)
            | Q(output_product_id__isnull=True, routing__product_id=product_id)
        )
        .select_related('line', 'process__line')
        .first()
    )
    if step:
        if step.lead_time_days:
            return int(step.lead_time_days)
        step_line = step.line or getattr(step.process, 'line', None)
        if step_line and step_line.lead_time_days:
            return int(step_line.lead_time_days)
    return 0


def _resolve_line_calendar_id(line_id):
    """ラインに紐づくカレンダーIDを取得する。未設定時は daiso カレンダーを使用。"""
    from masters.models import Calendar, Line

    if not line_id:
        return None
    line_obj = Line.objects.filter(id=line_id).only('calendar_id').first()
    return getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(
        calendar_code='daiso'
    ).values_list('id', flat=True).first()


def _build_adjustment_maps(line_id, start_date, end_date, product_ids=None):
    """調整を一括取得して辞書化（計算ループ中はDB参照しない）"""
    target_product_ids = sorted({int(pid) for pid in (product_ids or []) if pid is not None})
    qs = LineBacklogAdjustment.objects.filter(
        line_id=line_id,
        plan_date__range=[start_date, end_date],
    )
    if target_product_ids:
        qs = qs.filter(product_id__in=target_product_ids)
    rows = qs.values('adjust_type', 'product_id', 'process_id', 'plan_date', 'adjust_qty')

    maps = {
        'STOCK': {},
        'PLANNED_STOCK': {},
        'PROGRESS': {},
        'PLANNED_PROGRESS': {},
    }
    for row in rows:
        ad_type = row['adjust_type']
        if ad_type not in maps:
            continue
        key = (row['product_id'], row['plan_date'], row['process_id'])
        maps[ad_type][key] = maps[ad_type].get(key, 0) + int(row['adjust_qty'] or 0)
    return maps


def _resolve_day_adjustment(rows, ad_map):
    """行（日付×製品）に対する調整値を解決（工程一致を優先）"""
    if not rows or not ad_map:
        return 0
    product_id = rows[0].product_id
    plan_date = rows[0].plan_date
    process_ids = {r.process_id for r in rows if r.process_id}
    total = ad_map.get((product_id, plan_date, None), 0)
    for pid in process_ids:
        total += ad_map.get((product_id, plan_date, pid), 0)
    return int(total)


_ROUTING_PARENT_STEP_CACHE = {}


def _filter_parent_bom_items_by_routing(backlog, parent_bom_items):
    from masters.models import RoutingStep

    items = list(parent_bom_items)
    if not items:
        return items

    current_steps = list(
        RoutingStep.objects.filter(
            line_id=backlog.line_id,
            output_product_id=backlog.product_id,
            process_id=backlog.process_id,
        ).select_related('routing')
    )
    if not current_steps:
        return items

    filtered = []
    routing_product_ids = {
        step.routing.product_id
        for step in current_steps
        if getattr(step, 'routing_id', None) and getattr(step.routing, 'product_id', None)
    }
    if not routing_product_ids:
        return items

    child_step_nos = [int(step.step_no or 0) for step in current_steps]
    parent_ids = {
        getattr(getattr(item, 'bom', None), 'parent_product_id', None)
        for item in items
    }
    parent_ids.discard(None)
    if not parent_ids:
        return items

    cache_key = (tuple(sorted(routing_product_ids)), tuple(sorted(parent_ids)))
    parent_steps_map = _ROUTING_PARENT_STEP_CACHE.get(cache_key)
    if parent_steps_map is None:
        parent_steps_map = {}
        qs = (
            RoutingStep.objects.filter(
                routing__product_id__in=routing_product_ids,
                output_product_id__in=parent_ids,
            )
            .select_related('routing')
            .order_by('output_product_id', 'step_no', 'id')
        )
        for step in qs:
            key = (step.routing.product_id, step.output_product_id)
            parent_steps_map.setdefault(key, []).append(step)
        _ROUTING_PARENT_STEP_CACHE[cache_key] = parent_steps_map

    for item in items:
        parent_product_id = getattr(getattr(item, 'bom', None), 'parent_product_id', None)
        if not parent_product_id:
            continue
        matched = False
        for current_step in current_steps:
            routing_product_id = getattr(getattr(current_step, 'routing', None), 'product_id', None)
            if not routing_product_id:
                continue
            parent_steps = parent_steps_map.get((routing_product_id, parent_product_id), [])
            if not parent_steps:
                continue
            current_step_no = int(current_step.step_no or 0)
            if any(int(parent_step.step_no or 0) > current_step_no for parent_step in parent_steps):
                matched = True
                break
        if matched:
            filtered.append(item)

    return filtered or items


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
    for bom_item in _filter_parent_bom_items_by_routing(backlog, parent_bom_items):
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


FLOOR_SHIPPING_DELIVERY_LABEL = 'フロア配送'
FLOOR_SHIPPING_PM_THRESHOLD = 50


def _is_floor_shipping_delivery_line(line_obj):
    if not line_obj:
        return False
    line_code = str(getattr(line_obj, 'line_code', '') or '').strip()
    line_name = str(getattr(line_obj, 'line_name', '') or '').strip()
    return FLOOR_SHIPPING_DELIVERY_LABEL in f'{line_code} {line_name}'


def _check_floor_shipping_parent(parent_product_id, cache):
    if parent_product_id in cache:
        return cache[parent_product_id]
    from masters.models import RoutingStep
    step = RoutingStep.objects.filter(
        output_product_id=parent_product_id
    ).select_related('line').first()
    result = bool(step and step.line and _is_floor_shipping_delivery_line(step.line))
    cache[parent_product_id] = result
    return result


def _floor_shipping_plan_shipment(backlog, shift_fn, parent_product, qty_per):
    """フロア配送ラインの出庫をsequence_noベースのLTで計算（pickup側と同一ロジック）

    pickup (views.py) の便判定:
      sorted by sequence_no → lot_index で判定
      - sequence_no > 50: 強制2便 (LT=1)
      - lot_index == 0 かつ sequence_no ≤ 50: 1便 (LT=2)
      - lot_index > 0 かつ sequence_no ≤ 50: 2便 (LT=1)
    """
    total = Decimal('0')
    date_lt1 = shift_fn(backlog.plan_date, 1) if shift_fn else backlog.plan_date
    date_lt2 = shift_fn(backlog.plan_date, 2) if shift_fn else backlog.plan_date

    checked_dates = set()
    for parent_date in [date_lt2, date_lt1]:
        if parent_date in checked_dates:
            continue
        checked_dates.add(parent_date)

        plan_rows = list(LineBacklog.objects.filter(
            product=parent_product,
            plan_date=parent_date,
            sequence_no__gt=0,
        ).values_list('sequence_no', 'plan_qty'))
        if not plan_rows:
            continue

        def _sort_key(item):
            seq = int(item[0] or 0)
            return seq if seq > 0 else 10 ** 9
        plan_rows.sort(key=_sort_key)

        for lot_index, (seq_no, plan_qty) in enumerate(plan_rows):
            seq = int(seq_no or 0)
            force_pm = seq > FLOOR_SHIPPING_PM_THRESHOLD
            effective_lt = 1 if force_pm else (2 if lot_index == 0 else 1)
            expected_parent = shift_fn(backlog.plan_date, effective_lt) if shift_fn else backlog.plan_date
            if expected_parent != parent_date:
                continue
            plan = int(plan_qty or 0)
            if plan:
                total += Decimal(str(plan)) * qty_per

    return total


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

    from django.db.models import Sum

    total_shipment = Decimal('0')
    for bom_item in _filter_parent_bom_items_by_routing(backlog, parent_bom_items):
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
        # sequence_no違いの同一工程行を集約し、仕損の重複加算を防ぐ
        downstream_groups = LineBacklog.objects.filter(
            product=parent_product,
            plan_date=parent_date,
        ).values('product_id', 'line_id', 'process_id', 'plan_date').annotate(
            actual_total=Sum('actual_qty'),
        )
        for downstream in downstream_groups:
            actual = int(downstream.get('actual_total') or 0)
            # 全ての仕損を出庫に含める（line+process単位で1回のみ）
            scrap = _get_shipment_scrap_qty(
                downstream['product_id'],
                downstream['line_id'],
                downstream['process_id'],
                downstream['plan_date']
            )
            use_qty = Decimal(str(actual)) + scrap
            if use_qty:
                total_shipment += Decimal(str(use_qty)) * Decimal(str(qty_per))

    return total_shipment


def _compute_planned_stock_lt_adjustment(
    product_id,
    initial_date,
    max_lt,
    shift_fn,
    demand_map=None,
    final_delivery_lt=None,
    line_id=None,
):
    """
    計画在庫初期値のLT調整量を計算する。

    実在庫はLTシフトなしで計算されるが、計画在庫はLTシフトあり。
    そのため、initial_dateの実在庫を計画在庫の初期値として使う際は、
    「initial_date+1 ～ initial_date+LT」の出庫分（LTシフト）を差し引く必要がある。

    社内品: 親製品の実績（BOM LT 分）を差し引く
    最終品/ライン最終品: デリバリLT分の需要を差し引く

    ※ initial_date+LT ≤ today-1 の条件下では全て実績確定しているため値が安定する。
    """
    from masters.models import BOMItem
    from django.db.models import Sum

    total_adjustment = Decimal('0')

    # 最終品/ライン最終品：calc_start_date（initial_date）から後ろ向きに
    # デリバリLT日分の需要を差し引く。
    #
    # 最終品は demand_map（LineDemand由来）を優先し、
    # ライン最終品など demand_map を持たないケースでは同日の order_qty を使用する。
    # LT 分だけ在庫の初期値から差し引いて計画在庫の初期値とする：
    #   LT=1: demand[initial_date]
    #   LT=2: demand[initial_date] + demand[initial_date - 1営業日]
    #   LT=N: demand[initial_date] + ... + demand[initial_date - (N-1)営業日]
    #
    # これにより初期値の段階で LT 分だけ計画在庫 < 実在庫 となり、
    # 以降は普通の計算式（LT シフトなし）で継続する。
    if final_delivery_lt is not None:
        delivery_lt = int(final_delivery_lt or 0)
    else:
        # 呼び出し元未指定時は0日として扱う（後方互換のself_lt_days参照は廃止）
        delivery_lt = 0

    if delivery_lt >= 0:
        for offset in range(delivery_lt):  # 0, 1, ..., delivery_lt-1
            adj_date = shift_fn(initial_date, -offset)  # initial_date から後ろ向きにシフト
            qty = demand_map.get((product_id, adj_date), Decimal('0')) if demand_map else Decimal('0')
            if not qty and line_id:
                backlog_rows = LineBacklog.objects.filter(
                    line_id=line_id,
                    product_id=product_id,
                    plan_date=adj_date,
                )
                qty = Decimal(str(sum(int(row.order_qty or 0) for row in backlog_rows)))
            total_adjustment += Decimal(str(qty))
        return int(total_adjustment)

    # 社内品：親の BOM 経由でLTシフト分の実績出庫を差し引く
    parent_bom_items = BOMItem.objects.filter(
        child_product_id=product_id,
        bom__is_active=True,
        bom__is_coproduct=False,
    ).select_related('bom__parent_product')

    if not parent_bom_items.exists():
        return 0

    total_adjustment = Decimal('0')
    for bom_item in parent_bom_items:
        parent_product = bom_item.bom.parent_product
        if not parent_product:
            continue
        qty_per = bom_item.quantity or Decimal('0')
        if qty_per == 0:
            continue
        lead_days = bom_item.lead_time_days or 0
        if lead_days == 0:
            continue

        for offset in range(1, lead_days + 1):
            adj_date = shift_fn(initial_date, offset)
            downstream_groups = LineBacklog.objects.filter(
                product=parent_product,
                plan_date=adj_date,
            ).values('product_id', 'line_id', 'process_id', 'plan_date').annotate(
                actual_total=Sum('actual_qty'),
            )
            for downstream in downstream_groups:
                actual = int(downstream.get('actual_total') or 0)
                scrap = _get_shipment_scrap_qty(
                    downstream['product_id'],
                    downstream['line_id'],
                    downstream['process_id'],
                    downstream['plan_date'],
                )
                use_qty = Decimal(str(actual)) + scrap
                if use_qty:
                    total_adjustment += use_qty * Decimal(str(qty_per))

    return int(total_adjustment)


def _calculate_parent_actual_or_plan_shipment(backlog, shift_fn=None, floor_shipping_cache=None):
    """
    計画在庫用の出庫計算（実績優先、なければ計画を使用）+ 仕損

    LTシフト後の親製品の日付で：
    - 実績がある場合 → 実績 + 仕損（全て）を使用
    - 実績がない場合 → 計画数を使用
    - どちらもない場合 → 0
    - 親参照自体がない場合 → None

    Args:
        backlog: LineBacklogインスタンス
        shift_fn: LTシフト関数（営業日ベースで日付をシフト）
        floor_shipping_cache: フロア配送ライン判定キャッシュ
    """
    from masters.models import BOMItem

    parent_bom_items = BOMItem.objects.filter(
        child_product=backlog.product,
        bom__is_active=True,
        bom__is_coproduct=False
    ).select_related('bom__parent_product')

    if not parent_bom_items.exists():
        return None

    from django.db.models import Sum

    fs_cache = floor_shipping_cache if floor_shipping_cache is not None else {}
    total_shipment = Decimal('0')
    effective_parent_items = list(_filter_parent_bom_items_by_routing(backlog, parent_bom_items))
    if not effective_parent_items:
        return None

    for bom_item in effective_parent_items:
        parent_product = bom_item.bom.parent_product
        if not parent_product:
            continue
        qty_per = bom_item.quantity or Decimal('0')
        if qty_per == 0:
            continue

        if _check_floor_shipping_parent(parent_product.id, fs_cache):
            total_shipment += _floor_shipping_plan_shipment(
                backlog, shift_fn, parent_product, qty_per,
            )
            continue

        lead_days = bom_item.lead_time_days or 0
        parent_date = backlog.plan_date
        if shift_fn:
            parent_date = shift_fn(backlog.plan_date, lead_days)
        # sequence_no違いの同一工程行を集約し、仕損の重複加算を防ぐ
        downstream_groups = LineBacklog.objects.filter(
            product=parent_product,
            plan_date=parent_date,
        ).values('product_id', 'line_id', 'process_id', 'plan_date').annotate(
            actual_total=Sum('actual_qty'),
            plan_total=Sum('plan_qty'),
        )
        for downstream in downstream_groups:
            actual = int(downstream.get('actual_total') or 0)
            plan = int(downstream.get('plan_total') or 0)
            # 全ての仕損を出庫に含める（line+process単位で1回のみ）
            scrap = _get_shipment_scrap_qty(
                downstream['product_id'],
                downstream['line_id'],
                downstream['process_id'],
                downstream['plan_date']
            )
            if actual > 0 or scrap > 0:
                use_qty = Decimal(str(actual)) + scrap
            else:
                use_qty = Decimal(str(plan))
            if use_qty:
                total_shipment += Decimal(str(use_qty)) * Decimal(str(qty_per))

    return total_shipment


def _calculate_parent_planned_shipment(backlog, today, shift_fn, floor_shipping_cache=None):
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

    from django.db.models import Sum

    fs_cache = floor_shipping_cache if floor_shipping_cache is not None else {}
    total_shipment = Decimal('0')
    for bom_item in _filter_parent_bom_items_by_routing(backlog, parent_bom_items):
        parent_product = bom_item.bom.parent_product
        if not parent_product:
            continue
        qty_per = bom_item.quantity or Decimal('0')
        if qty_per == 0:
            continue

        if _check_floor_shipping_parent(parent_product.id, fs_cache):
            total_shipment += _floor_shipping_plan_shipment(
                backlog, shift_fn, parent_product, qty_per,
            )
            continue

        lead_days = bom_item.lead_time_days or 0
        parent_date = backlog.plan_date
        if shift_fn:
            parent_date = shift_fn(backlog.plan_date, lead_days)
        # sequence_no違いの同一工程行を集約し、仕損の重複加算を防ぐ
        downstream_groups = LineBacklog.objects.filter(
            product=parent_product,
            plan_date=parent_date,
        ).values('product_id', 'line_id', 'process_id', 'plan_date').annotate(
            plan_total=Sum('plan_qty'),
        )
        for downstream in downstream_groups:
            plan = int(downstream.get('plan_total') or 0)
            # 全ての仕損を出庫に含める（line+process単位で1回のみ）
            scrap = _get_shipment_scrap_qty(
                downstream['product_id'],
                downstream['line_id'],
                downstream['process_id'],
                downstream['plan_date']
            )
            use_qty = Decimal(str(plan)) + scrap
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

    for bom_item in _filter_parent_bom_items_by_routing(backlog, parent_bom_items):
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

    for bom_item in _filter_parent_bom_items_by_routing(backlog, parent_bom_items):
        downstream_backlogs = LineBacklog.objects.filter(
            product=bom_item.bom.parent_product,
            plan_date=backlog.plan_date,
            actual_qty__gt=0
        )
        if downstream_backlogs.exists():
            return True

    return False


def recalculate_stock_qty(
    line_id,
    product_id,
    start_date,
    end_date,
    demand_map=None,
    stock_adjust_map=None,
    reference_today=None,
    max_parent_lt=None,
    calendar_id=None,
    shared_workday_cache=None,
):
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

    # 基礎行（sequence_no=0）が無い日付には新規作成してから計算する
    to_create = []
    for plan_date, rows in by_date.items():
        has_base = any((r.sequence_no or 0) == 0 for r in rows)
        if not has_base:
            sample = rows[0]
            to_create.append(LineBacklog(
                plan_date=plan_date,
                process_id=sample.process_id,
                product_id=sample.product_id,
                line_id=sample.line_id,
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
    created_any = False
    if to_create:
        created = LineBacklog.objects.bulk_create(to_create)
        # MySQL などでは bulk_create 直後の PK が埋まらないことがあるため、再取得して差し替える
        created_any = True
        for obj in created:
            by_date.setdefault(obj.plan_date, []).append(obj)

    if created_any:
        # PK が欠落している可能性があるため、対象期間を再取得して by_date を作り直す
        backlogs = list(LineBacklog.objects.filter(
            line_id=line_id,
            product_id=product_id,
            plan_date__range=[start_date, end_date]
        ).select_related('product').order_by('plan_date', 'sequence_no', 'id'))
        by_date = {}
        for backlog in backlogs:
            by_date.setdefault(backlog.plan_date, []).append(backlog)

    workday_cache = shared_workday_cache if shared_workday_cache is not None else {}
    if calendar_id is None and line_id:
        calendar_id = _resolve_line_calendar_id(line_id)

    def is_working_day(target_date):
        if not calendar_id:
            return target_date.weekday() < 5
        if target_date in workday_cache:
            return workday_cache[target_date]
        from masters.models import CalendarDay
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
        return min(base_rows, key=lambda r: r.id)

    # 計算起点日（calc_today）と実績反映判定日（business_today）を分離する。
    # 休日に再計算した場合でも、当日の実績は出庫計算に反映する。
    business_today = reference_today or get_business_today()
    calc_today = business_today
    if reference_today is None and not is_working_day(calc_today):
        calc_today = get_prev_working_day(calc_today)
    inventory_lock_date = SystemSetting.get_lock_date('inventory')
    stock_by_date = {}
    demand_map = demand_map or {}
    calc_rule_map = _load_planned_stock_calc_rule_map()
    line_code_cache = {}
    process_code_cache = {}

    def _resolve_line_code(line_id_value):
        lid = int(line_id_value or 0)
        if lid <= 0:
            return ''
        if lid in line_code_cache:
            return line_code_cache[lid]
        from masters.models import Line
        line = Line.objects.filter(id=lid).only('line_code').first()
        code = str(getattr(line, 'line_code', '') or '').strip().upper()
        line_code_cache[lid] = code
        return code

    def _resolve_process_code(process_id_value):
        pid = int(process_id_value or 0)
        if pid <= 0:
            return ''
        if pid in process_code_cache:
            return process_code_cache[pid]
        from masters.models import Process
        proc = Process.objects.filter(id=pid).only('process_code').first()
        code = str(getattr(proc, 'process_code', '') or '').strip().upper()
        process_code_cache[pid] = code
        return code

    # 計画在庫は calc_start_date の stock_qty を初期値として参照するため、
    # 在庫の再計算範囲を calc_start_date まで広げて stock_qty を常に最新に保つ。
    # effective_start = min(start_date, calc_start_date)
    if max_parent_lt is None:
        max_parent_lt = _get_direct_parent_bom_lead_time(product_id)
    max_lt = int(max_parent_lt or 0)
    calc_start_date = shift_working_days(calc_today, -(max_lt + 1))
    effective_start = min(start_date, calc_start_date)

    # effective_start が start_date より古い場合、バックログを再取得して by_date を再構築
    if effective_start < start_date:
        backlogs = list(LineBacklog.objects.filter(
            line_id=line_id,
            product_id=product_id,
            plan_date__range=[effective_start, end_date]
        ).select_related('product').order_by('plan_date', 'sequence_no', 'id'))
        by_date = {}
        for backlog in backlogs:
            by_date.setdefault(backlog.plan_date, []).append(backlog)

    # effective_start より前の最新在庫を初期値として取得
    initial_backlog = LineBacklog.objects.filter(
        line_id=line_id,
        product_id=product_id,
        plan_date__lt=effective_start,
        stock_qty__isnull=False
    ).order_by('-plan_date', 'sequence_no', 'id').first()

    if initial_backlog:
        last_stock = initial_backlog.stock_qty or 0
        stock_by_date[initial_backlog.plan_date] = last_stock
    else:
        last_stock = 0

    # 更新対象のbacklogを追跡（effective_start以前は更新しない）
    backlogs_to_update = []

    for plan_date in sorted(by_date.keys()):
        rows = by_date[plan_date]
        sample = rows[0]
        is_final = bool(getattr(sample.product, 'is_final_product', False))

        # 棚卸確定フラグがある場合、その値を正として採用し、計算はスキップ
        if any(getattr(r, 'is_stocktake_fix', False) for r in rows):
            # 代表行の在庫を採用
            stock_qty = sample.stock_qty or 0
            stock_by_date[plan_date] = stock_qty
            last_stock = stock_qty
            continue

        # 締め日以前は既存値を維持し再計算しない
        if inventory_lock_date and plan_date <= inventory_lock_date:
            existing_stock = 0
            for row in rows:
                if row.stock_qty:
                    existing_stock = row.stock_qty
                    break
            stock_by_date[plan_date] = existing_stock
            last_stock = existing_stock
            continue

        # effective_start より前は既存の在庫値を使用し、更新しない（安全ガード）
        if plan_date < effective_start:
            existing_stock = 0
            for row in rows:
                if row.stock_qty:
                    existing_stock = row.stock_qty
                    break
            stock_by_date[plan_date] = existing_stock
            last_stock = existing_stock
            continue

        actual_total = sum(r.actual_qty or 0 for r in rows)
        order_total = sum(r.order_qty or 0 for r in rows)
        scrap_adjust_total = sum(r.scrap_adjust_qty or 0 for r in rows)
        # adjust_qty は在庫計算に使わない（既存仕様）

        if plan_date <= business_today:
            if is_final:
                actual_shipment = demand_map.get((sample.product_id, plan_date), Decimal('0'))
            else:
                line_code = _resolve_line_code(getattr(sample, 'line_id', None))
                process_code = _resolve_process_code(getattr(sample, 'process_id', None))
                setting = calc_rule_map.get((line_code, process_code, 'STOCK'), '')
                if setting == 'ORDER_QTY':
                    # 特例: pickup 済みの前工程需要(order_qty)をそのまま出庫として使用
                    actual_shipment = Decimal(str(order_total))
                else:
                    # 標準: 親の actual_qty + scrap_qty を出庫として計算（休日実績も反映）
                    actual_shipment = _calculate_parent_actual_shipment(sample)
        else:
            actual_shipment = Decimal('0')
        actual_shipment = int(actual_shipment or 0)

        # 在庫も進度と同様、休日を含めて「前日（暦日）」を基準に引き継ぐ。
        prev_day = plan_date - timedelta(days=1)
        prev_stock = stock_by_date.get(prev_day, last_stock)

        stock_adjust = _resolve_day_adjustment(rows, stock_adjust_map)
        # 在庫 = 前日在庫 + 実績 - 出庫 + scrap_adjust_qty(非自工程仕損は負値で蓄積) + 手動調整
        stock_qty = (
            prev_stock
            + actual_total
            - actual_shipment
            + scrap_adjust_total
            + stock_adjust
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


def recalculate_planned_stock_qty(
    line_id,
    product_id,
    start_date,
    end_date,
    demand_map=None,
    planned_stock_adjust_map=None,
    reference_today=None,
    max_parent_lt=None,
    calendar_id=None,
    shared_workday_cache=None,
    force_from_start=False,
):
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

    workday_cache = shared_workday_cache if shared_workday_cache is not None else {}
    if calendar_id is None and line_id:
        calendar_id = _resolve_line_calendar_id(line_id)

    def is_working_day(target_date):
        if not calendar_id:
            return target_date.weekday() < 5
        if target_date in workday_cache:
            return workday_cache[target_date]
        from masters.models import CalendarDay
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
        return min(base_rows, key=lambda r: r.id)

    # 計算起点日（calc_today）と実績反映判定日（business_today）を分離する。
    # 休日に再計算した場合でも、当日の実績は計画在庫計算に反映する。
    business_today = reference_today or get_business_today()
    calc_today = business_today
    if reference_today is None and not is_working_day(calc_today):
        calc_today = get_prev_working_day(calc_today)
    # 直親BOMのLTを使用し、LT+1日前から再計算
    if max_parent_lt is None:
        max_parent_lt = _get_direct_parent_bom_lead_time(product_id)
    max_lt = int(max_parent_lt or 0)
    # 最終品/ライン最終品はデリバリLT分だけ初期値を調整するため、計算窓を広げる。
    # self_lt_days（製造LT）ではなく、出庫基準と同じデリバリLT（RoutingStep/Line）を使う。
    sample_product = backlogs[0].product if backlogs else None
    is_final_product = bool(sample_product and getattr(sample_product, 'is_final_product', False))
    is_line_final_product = bool(sample_product and getattr(sample_product, 'is_line_final_product', False))
    final_delivery_lt = 0
    use_delivery_lt_initialization = is_final_product or is_line_final_product
    if use_delivery_lt_initialization:
        final_delivery_lt = _get_final_product_delivery_lt(line_id, product_id)
        max_lt = max(max_lt, final_delivery_lt)
    calc_start_date = shift_working_days(calc_today, -(max_lt + 1))
    # 過去から再計算（force_from_start=True）の場合のみ、start_date から再計算する
    if force_from_start and start_date < calc_start_date:
        calc_start_date = start_date

    # calc_start_date が start_date より古い場合、バックログを再取得
    if calc_start_date < start_date:
        backlogs = list(LineBacklog.objects.filter(
            line_id=line_id,
            product_id=product_id,
            plan_date__range=[calc_start_date, end_date]
        ).select_related('product').order_by('plan_date', 'sequence_no', 'id'))
        if not backlogs:
            return
        by_date = {}
        for backlog in backlogs:
            by_date.setdefault(backlog.plan_date, []).append(backlog)
        sample_product = backlogs[0].product if backlogs else None
        is_final_product = bool(sample_product and getattr(sample_product, 'is_final_product', False))
        is_line_final_product = bool(sample_product and getattr(sample_product, 'is_line_final_product', False))
        use_delivery_lt_initialization = is_final_product or is_line_final_product

    inventory_lock_date = SystemSetting.get_lock_date('inventory')
    planned_by_date = {}
    demand_map = demand_map or {}
    floor_shipping_cache = {}
    calc_rule_map = _load_planned_stock_calc_rule_map()
    line_code_cache = {}
    process_code_cache = {}

    def _resolve_line_code(line_id_value):
        lid = int(line_id_value or 0)
        if lid <= 0:
            return ''
        if lid in line_code_cache:
            return line_code_cache[lid]
        from masters.models import Line
        line = Line.objects.filter(id=lid).only('line_code').first()
        code = str(getattr(line, 'line_code', '') or '').strip().upper()
        line_code_cache[lid] = code
        return code

    def _resolve_process_code(process_id_value):
        pid = int(process_id_value or 0)
        if pid <= 0:
            return ''
        if pid in process_code_cache:
            return process_code_cache[pid]
        from masters.models import Process
        proc = Process.objects.filter(id=pid).only('process_code').first()
        code = str(getattr(proc, 'process_code', '') or '').strip().upper()
        process_code_cache[pid] = code
        return code

    # 計画在庫の初期値は、まず「計算開始日より前の既存 planned_stock_qty」を優先する。
    # これがあれば、在庫(stock_qty)を直接起点にせずに計庫の連鎖を継続できる。
    planned_anchor = LineBacklog.objects.filter(
        line_id=line_id,
        product_id=product_id,
        plan_date__lt=calc_start_date,
        planned_stock_qty__isnull=False,
    ).order_by('-plan_date', 'sequence_no', 'id').first()

    if planned_anchor:
        last_planned = planned_anchor.planned_stock_qty or 0
        planned_by_date[planned_anchor.plan_date] = last_planned
        initial_backlog = planned_anchor
    else:
        # 既存計庫が無い初回だけ、実在庫を基準に LT 分の需要を差し引いて初期化する。
        # 最終品/ライン最終品: calc_start_date 当日（__lte）の在庫を使う
        # 社内品: calc_start_date の前日（__lt）の在庫を使う
        _ib_date_lookup = 'plan_date__lte' if use_delivery_lt_initialization else 'plan_date__lt'
        initial_backlog = LineBacklog.objects.filter(
            line_id=line_id,
            product_id=product_id,
            **{_ib_date_lookup: calc_start_date},
            stock_qty__isnull=False
        ).order_by('-plan_date', 'sequence_no', 'id').first()

    if initial_backlog and not planned_anchor:
        # 実在庫はLTシフトなし、計画在庫はLTシフトありで計算するため、
        # initial_date+1 ～ initial_date+LT の出庫分（LTシフト）を差し引く。
        # 社内品：親の実績を BOM LT 分差し引く
        # 最終品/ライン最終品：デリバリLT分の需要を差し引く
        lt_adjustment = _compute_planned_stock_lt_adjustment(
            product_id, initial_backlog.plan_date, max_lt, shift_working_days,
            demand_map=demand_map,
            final_delivery_lt=final_delivery_lt if use_delivery_lt_initialization else None,
            line_id=line_id,
        )
        last_planned = (initial_backlog.stock_qty or 0) - lt_adjustment
        planned_by_date[initial_backlog.plan_date] = last_planned
    elif not initial_backlog:
        # calc_start_date以前にデータがない場合（初回投入時など）、
        # 対象範囲の最古のstock_qtyを初期値としてフォールバック
        fallback = backlogs[0] if backlogs else None
        last_planned = (fallback.stock_qty or 0) if fallback else 0

    # 更新対象のbacklogを追跡（計算開始日以前は更新しない）
    backlogs_to_update = []

    for plan_date in sorted(by_date.keys()):
        rows = by_date[plan_date]
        sample = rows[0]

        # 棚卸確定フラグがある場合、その値を正として採用
        if any(getattr(r, 'is_stocktake_fix', False) for r in rows):
            planned_stock = sample.planned_stock_qty or 0
            planned_by_date[plan_date] = planned_stock
            last_planned = planned_stock
            continue

        # 締め日以前は既存値を維持し再計算しない
        if inventory_lock_date and plan_date <= inventory_lock_date:
            existing_planned = 0
            for row in rows:
                if row.planned_stock_qty:
                    existing_planned = row.planned_stock_qty
                    break
            planned_by_date[plan_date] = existing_planned
            last_planned = existing_planned
            continue

        # 計算開始日以前は通常計算をスキップ。
        # 最終品/ライン最終品: calc_start_date 当日の計庫を初期値とするため、
        #   当日もスキップ。ただし LT 調整済みの初期値を DB に書き戻す必要があるため bulk_update 対象に含める。
        # 社内品: calc_start_date から通常計算を開始する（従来どおり）。
        if plan_date < calc_start_date:
            planned_by_date[plan_date] = last_planned
            continue
        if use_delivery_lt_initialization and not planned_anchor and plan_date == calc_start_date:
            planned_by_date[plan_date] = last_planned
            rep = pick_representative(rows)
            for row in rows:
                row.planned_stock_qty = 0
            rep.planned_stock_qty = last_planned
            backlogs_to_update.extend(rows)
            continue

        plan_total = sum(r.plan_qty or 0 for r in rows)
        actual_total = sum(r.actual_qty or 0 for r in rows)
        # 計画在庫計算でも adjust_qty を使用しない
        # 仕損による子部品の消費は、出庫計算（親の実績/計画+仕損）で反映される
        order_total = sum(r.order_qty or 0 for r in rows)

        # 非稼働日は入庫・出庫とも発生しないため前日からそのまま繰越す。
        # shift_working_daysが休日→営業日にマッピングするため、営業日と同じ親データを
        # 二重カウントしてしまう問題を防ぐ。
        if not is_working_day(plan_date):
            prev_day = plan_date - timedelta(days=1)
            prev_planned = planned_by_date.get(prev_day, last_planned)
            planned_stock_adjust = _resolve_day_adjustment(rows, planned_stock_adjust_map)
            planned_stock = prev_planned + planned_stock_adjust
            rep = pick_representative(rows)
            for row in rows:
                row.planned_stock_qty = 0
            rep.planned_stock_qty = planned_stock
            planned_by_date[plan_date] = planned_stock
            last_planned = planned_stock
            backlogs_to_update.extend(rows)
            continue

        is_final = bool(getattr(sample.product, 'is_final_product', False))
        is_line_final = bool(getattr(sample.product, 'is_line_final_product', False))
        line_code = _resolve_line_code(getattr(sample, 'line_id', None))
        process_code = _resolve_process_code(getattr(sample, 'process_id', None))
        forced_parent_shipment_mode = calc_rule_map.get(
            (line_code, process_code, 'PLANNED_STOCK'),
            ''
        )
        if is_final:
            planned_shipment = demand_map.get((sample.product_id, plan_date), Decimal('0'))
        elif is_line_final:
            if forced_parent_shipment_mode == 'ORDER_QTY':
                planned_shipment = Decimal(str(order_total))
            elif plan_date < business_today:
                # ライン最終品でも過去日は親の実績優先で整合を取る。
                planned_shipment = _calculate_parent_actual_or_plan_shipment(sample, shift_working_days, floor_shipping_cache)
            else:
                planned_shipment = Decimal(str(order_total))
        else:
            if forced_parent_shipment_mode == 'ORDER_QTY':
                planned_shipment = Decimal(str(order_total))
            elif plan_date < business_today:
                planned_shipment = _calculate_parent_actual_or_plan_shipment(sample, shift_working_days, floor_shipping_cache)
            else:
                planned_shipment = _calculate_parent_planned_shipment(sample, business_today, shift_working_days, floor_shipping_cache)
        planned_shipment = int(planned_shipment or 0)

        # 在庫も進度と同様、休日を含めて「前日（暦日）」を基準に引き継ぐ。
        prev_day = plan_date - timedelta(days=1)
        prev_planned = planned_by_date.get(prev_day, last_planned)
        planned_stock_adjust = _resolve_day_adjustment(rows, planned_stock_adjust_map)

        # 計画在庫 = 前日計画在庫 + 実績/計画 - 出庫
        # 仕損による子部品消費は出庫計算で反映済み（adjust_qty は使用しない）
        if plan_date < business_today:
            planned_stock = (
                prev_planned
                + actual_total
                - planned_shipment
                + planned_stock_adjust
            )
        else:
            planned_stock = (
                prev_planned
                + plan_total
                - planned_shipment
                + planned_stock_adjust
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


def recalculate_inventory_for_line(
    line_id,
    start_date,
    end_date,
    include_progress=True,
    line_final_only=False,
    product_ids=None,
    progress_only=False,
    progress_calc_start_date=None,
    force_from_start=False,
):
    """
    指定ラインの在庫を再計算

    Args:
        line_id: ラインID
        start_date: 開始日
        end_date: 終了日
        include_progress: 進度も再計算するか（デフォルト: True）
        line_final_only: ライン最終品のみ計算するか（デフォルト: False）
        product_ids: 対象製品ID配列（指定時はその製品のみ計算）
        progress_only: Trueの場合は進度のみ再計算し、在庫・計画在庫をスキップ
    """
    import logging
    import time
    logger = logging.getLogger(__name__)
    target_product_ids = sorted({int(pid) for pid in (product_ids or []) if pid is not None})

    # progress_only=True のとき進度は必ず計算する
    if progress_only:
        include_progress = True

    overall_start = time.perf_counter()
    logger.info(
        "在庫再計算開始: line_id=%s, %s ~ %s, line_final_only=%s, progress_only=%s, product_count=%s",
        line_id,
        start_date,
        end_date,
        line_final_only,
        progress_only,
        len(target_product_ids) if target_product_ids else "ALL",
    )

    if not progress_only:
        # まず仕損数を集計
        scrap_start = time.perf_counter()
        aggregate_scrap_to_backlog(
            line_id,
            start_date,
            end_date,
            product_ids=target_product_ids or None,
        )
        logger.info("仕損集計時間: %.3fs", time.perf_counter() - scrap_start)

        demand_start = time.perf_counter()
        demand_map = _build_demand_map(line_id, start_date, end_date)
        logger.info("需要マップ作成時間: %.3fs", time.perf_counter() - demand_start)
    else:
        demand_map = {}

    adj_start = start_date
    if progress_calc_start_date and progress_calc_start_date < start_date:
        adj_start = progress_calc_start_date
    adjustment_maps = _build_adjustment_maps(
        line_id,
        adj_start,
        end_date,
        product_ids=target_product_ids or None,
    )
    shared_calendar_id = _resolve_line_calendar_id(line_id) if line_id else None
    shared_workday_cache = {}
    max_parent_lt_cache = {}
    recalculate_progress_qty = None
    if include_progress:
        from .progress_calculator import recalculate_progress_qty as _recalculate_progress_qty
        recalculate_progress_qty = _recalculate_progress_qty

    # 製品ごとに在庫計算
    product_qs = LineBacklog.objects.filter(
        line_id=line_id,
        plan_date__range=[start_date, end_date]
    )
    if target_product_ids:
        product_qs = product_qs.filter(product_id__in=target_product_ids)
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

    direct_lt_cache = {}

    for product_id in product_ids:
        logger.info(f"製品ID {product_id} の在庫計算中...")
        # 在庫・計画在庫は直親LT、進度は累積LTを使用
        direct_lt = direct_lt_cache.get(product_id)
        if direct_lt is None:
            direct_lt = _get_direct_parent_bom_lead_time(product_id)
            direct_lt_cache[product_id] = direct_lt

        max_parent_lt = max_parent_lt_cache.get(product_id)
        if max_parent_lt is None:
            max_parent_lt = _get_max_parent_bom_lead_time(product_id)
            max_parent_lt_cache[product_id] = max_parent_lt

        if not progress_only:
            # 実在庫を計算
            t0 = time.perf_counter()
            recalculate_stock_qty(
                line_id,
                product_id,
                start_date,
                end_date,
                demand_map=demand_map,
                stock_adjust_map=adjustment_maps.get('STOCK'),
                max_parent_lt=direct_lt,
                calendar_id=shared_calendar_id,
                shared_workday_cache=shared_workday_cache,
            )
            stock_elapsed = time.perf_counter() - t0
            stock_total += stock_elapsed
            if stock_elapsed > stock_max[0]:
                stock_max = (stock_elapsed, product_id)

            # 計画在庫を計算
            t1 = time.perf_counter()
            recalculate_planned_stock_qty(
                line_id,
                product_id,
                start_date,
                end_date,
                demand_map=demand_map,
                planned_stock_adjust_map=adjustment_maps.get('PLANNED_STOCK'),
                max_parent_lt=direct_lt,
                calendar_id=shared_calendar_id,
                shared_workday_cache=shared_workday_cache,
                force_from_start=force_from_start,
            )
            planned_elapsed = time.perf_counter() - t1
            planned_total += planned_elapsed
            if planned_elapsed > planned_max[0]:
                planned_max = (planned_elapsed, product_id)

        if include_progress:
            # 進度を計算
            t2 = time.perf_counter()
            recalculate_progress_qty(
                line_id,
                product_id,
                start_date,
                end_date,
                progress_adjust_map=adjustment_maps.get('PROGRESS'),
                planned_progress_adjust_map=adjustment_maps.get('PLANNED_PROGRESS'),
                override_calc_start_date=progress_calc_start_date,
                max_parent_lt=max_parent_lt,
                calendar_id=shared_calendar_id,
                shared_workday_cache=shared_workday_cache,
            )
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

    return {
        'line_id': line_id,
        'product_count': len(product_ids),
        'progress_product_count': len(product_ids) if include_progress else 0,
    }
