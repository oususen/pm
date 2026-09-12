"""
工程実時間記録用のSerializer
"""
from decimal import Decimal
from datetime import timedelta, time

from rest_framework import serializers
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from masters.models import Process, Product, BOM, Supplier, Routing, RoutingStep
from masters.services.routing_service import build_effective_routing_q, resolve_effective_routing
from .services.process_realtime_routing_service import (
    build_invalid_product_process_message,
    is_valid_output_process,
)
from orders.utils.calendar_utils import DAY_BOUNDARY_HOUR
from purchase.process_resolver import resolve_purchase_line, resolve_supplier_process
from .models_process_realtime import ProcessRealtimeRecord
from .models_process_work_session import ProcessWorkSession
from .models_process_work_session_change_history import ProcessWorkSessionChangeHistory
from .models_line_backlog import LineBacklog
from .models_production import StockAllocation
from quality.models_scrap import ScrapRecord, ScrapRecordDetail


def _resolve_product_process_line(product, fallback_process):
    """製品のRoutingStepから正しい工程/ラインを取得する。見つからない場合はフォールバックを返す。"""
    if not product:
        return fallback_process, getattr(fallback_process, 'line', None)

    # output_productから直接検索
    step = RoutingStep.objects.filter(
        output_product=product,
    ).filter(
        build_effective_routing_q(prefix='routing__')
    ).select_related('process', 'process__line', 'line').first()

    if not step:
        # Routingのproductとしてのルーティングの最終工程を検索
        routing = resolve_effective_routing(product.id if product else None)
        if routing:
            step = routing.steps.select_related(
                'process', 'process__line', 'line',
            ).order_by('-step_no').first()

    if step:
        return step.process, step.line or getattr(step.process, 'line', None)

    return fallback_process, getattr(fallback_process, 'line', None)


def build_scrap_multiplier_map(root_product_id: int, root_qty: Decimal) -> dict:
    """
    BOMを最下層まで展開し、各製品に必要な仕損数量を集計する。
    歩留まり・副産物は考慮しない（現仕様）。
    """
    if not root_product_id or root_qty is None:
        return {}

    multipliers = {}
    stack = [(root_product_id, Decimal(root_qty), None)]

    while stack:
        pid, qty, sourcing_type = stack.pop()
        if qty == 0:
            continue
        multipliers[pid] = multipliers.get(pid, Decimal('0')) + qty

        st = (sourcing_type or '').upper()
        if st == 'BUY':
            continue

        bom = BOM.objects.filter(parent_product_id=pid, is_active=True).order_by('-valid_from', '-id').first()
        if not bom:
            continue
        for item in bom.items.all():
            if item.quantity is None:
                continue
            child_qty = qty * Decimal(item.quantity)
            stack.append((item.child_product_id, child_qty, item.sourcing_type))

    return multipliers


def build_scrap_multiplier_details(root_product_id: int, root_qty: Decimal):
    """
    BOMを最下層まで展開し、各製品ごとの仕損数量と加工先工程/ライン情報を返す。
    （process_id/line_id は BOM 明細に設定されていれば一緒に返す）
    同じ製品でも異なる工程/サプライヤからの調達は別明細として扱う。
    """
    if not root_product_id or root_qty is None:
        return []

    stack = [(root_product_id, Decimal(root_qty), None, None, None, None)]
    detail_map = {}
    supplier_cache = {}
    product_cache = {}

    def resolve_purchase_line_id(supplier_id):
        supplier = supplier_cache.get(supplier_id)
        if supplier_id and supplier is None:
            supplier = Supplier.objects.filter(id=supplier_id).first()
            supplier_cache[supplier_id] = supplier
        line_obj = resolve_purchase_line(supplier) if supplier else None
        return line_obj.id if line_obj else None

    while stack:
        pid, qty, proc_id, line_id, supplier_id, sourcing_type = stack.pop()
        if qty == 0:
            continue

        st = (sourcing_type or '').upper()
        if st in ('BUY', 'SUBCON'):
            supplier = supplier_cache.get(supplier_id)
            if supplier_id and supplier is None:
                supplier = Supplier.objects.filter(id=supplier_id).first()
                supplier_cache[supplier_id] = supplier
            product = product_cache.get(pid)
            if pid and product is None:
                product = Product.objects.filter(id=pid).first()
                product_cache[pid] = product
            resolved_process = resolve_supplier_process(
                supplier=supplier,
                line=resolve_purchase_line(supplier) if supplier else None,
                product=product,
                preferred_process_id=proc_id,
                sourcing_type=st,
                create_purchase_process=(st == 'BUY'),
            )
            if resolved_process:
                proc_id = resolved_process.id
                line_id = resolve_purchase_line_id(supplier_id) or getattr(resolved_process, 'line_id', None)

        # 同じ製品でも工程/サプライヤが異なれば別明細とする
        key = (pid, proc_id, supplier_id)
        if key not in detail_map:
            detail_map[key] = {
                'qty': Decimal('0'),
                'process_id': proc_id,
                'line_id': line_id,
                'supplier_id': supplier_id,
                'sourcing_type': sourcing_type,
            }
        detail_map[key]['qty'] += qty
        if detail_map[key]['line_id'] is None and line_id is not None:
            detail_map[key]['line_id'] = line_id
        if detail_map[key]['sourcing_type'] is None and sourcing_type is not None:
            detail_map[key]['sourcing_type'] = sourcing_type

        if st == 'BUY':
            continue

        bom = BOM.objects.filter(parent_product_id=pid, is_active=True).order_by('-valid_from', '-id').first()
        if not bom:
            continue
        for item in bom.items.all():
            if item.quantity is None:
                continue
            child_qty = qty * Decimal(item.quantity)
            stack.append((
                item.child_product_id,
                child_qty,
                item.process_id or proc_id,
                item.line_id or line_id,
                item.supplier_id or supplier_id,
                item.sourcing_type or sourcing_type,
            ))

    result = []
    for (pid, proc_id, supplier_id), info in detail_map.items():
        result.append({
            'product_id': pid,
            'qty': info['qty'],
            'process_id': info['process_id'],
            'line_id': info['line_id'],
            'supplier_id': info['supplier_id'],
            'sourcing_type': info['sourcing_type'],
        })
    return result


def apply_scrap_to_stock(multipliers: dict):
    """
    仕損数量を在庫に転嫁する。既存の在庫引当テーブルを使用。
    location が複数ある場合は最初のレコードを使用し、無ければ DEFAULT ロケーションで作成。
    """
    for pid, qty in multipliers.items():
        if qty == 0:
            continue
        allocation = StockAllocation.objects.filter(product_id=pid).order_by('id').first()
        if allocation:
            allocation.current_stock = (allocation.current_stock or Decimal('0')) - qty
            allocation.save()
        else:
            StockAllocation.objects.create(
                product_id=pid,
                location='DEFAULT',
                current_stock=-qty,
                reserved_qty=Decimal('0'),
                min_stock_qty=0,
                is_bottleneck=False,
            )


def apply_scrap_return_to_stock(multipliers: dict):
    """
    仕損の戻し数量を在庫に反映する。location が複数ある場合は最初のレコードを使用。
    """
    for pid, qty in multipliers.items():
        if qty == 0:
            continue
        allocation = StockAllocation.objects.filter(product_id=pid).order_by('id').first()
        if allocation:
            allocation.current_stock = (allocation.current_stock or Decimal('0')) + qty
            allocation.save()
        else:
            StockAllocation.objects.create(
                product_id=pid,
                location='DEFAULT',
                current_stock=qty,
                reserved_qty=Decimal('0'),
                min_stock_qty=0,
                is_bottleneck=False,
            )


def update_line_backlog_production(process, product, qty, plan_date):
    """
    生産実績をLineBacklogのactual_qtyに反映する

    Args:
        process: Process オブジェクト
        product: Product オブジェクト (Noneの場合はスキップ)
        qty: 生産数量 (Decimal)
        plan_date: 計画日 (date)
    """
    if not product or not qty or qty <= 0:
        return

    line = getattr(process, 'line', None)
    if not line:
        return

    # 該当するLineBacklogレコードを取得または作成
    # 実績は sequence_no=0 の基礎データレコードに保存
    backlog, created = LineBacklog.objects.get_or_create(
        line=line,
        process=process,
        product=product,
        plan_date=plan_date,
        sequence_no=0,  # 実績は sequence_no=0 に保存
        defaults={
            'actual_qty': int(qty),
        }
    )

    if not created:
        # 既存レコードに実績を加算
        backlog.actual_qty = (backlog.actual_qty or 0) + int(qty)
        backlog.save(update_fields=['actual_qty'])


def check_plan_overrun(process, product, plan_date):
    """
    実績数量がガントチャート計画数量を超過しているかチェックする。
    ガントチャート計画（LineGanttPlan.processes_plan）を基準に比較する。

    Returns:
        dict or None: 超過している場合は警告情報を返す。超過なしならNone。
    """
    from .models_line_gantt_plan import LineGanttPlan

    line = getattr(process, 'line', None)
    if not line or not product:
        return None

    # 実績数（sequence_no=0）
    try:
        actual_row = LineBacklog.objects.get(
            line=line,
            process=process,
            product=product,
            plan_date=plan_date,
            sequence_no=0,
        )
        actual_qty = actual_row.actual_qty or 0
    except LineBacklog.DoesNotExist:
        return None

    # ガントチャート計画から該当工程・製品の計画数を集計
    gantt_plans = LineGanttPlan.objects.filter(
        line=line,
        plan_date=plan_date,
    )
    total_plan = 0
    process_id = process.id
    product_id = product.id
    for gp in gantt_plans:
        for pp in (gp.processes_plan or []):
            pp_process_id = pp.get('process_id')
            pp_product_id = pp.get('output_product_id') or gp.product_id
            if pp_process_id == process_id and pp_product_id == product_id:
                total_plan += int(pp.get('quantity', 0))

    if total_plan <= 0:
        return None

    if actual_qty > total_plan:
        return {
            'actual_qty': actual_qty,
            'plan_qty': total_plan,
            'over_qty': actual_qty - total_plan,
            'product_code': getattr(product, 'product_code', ''),
            'product_name': getattr(product, 'product_name', ''),
            'process_name': getattr(process, 'process_name', ''),
        }

    return None


def adjust_production_for_scrap(process, product, scrap_qty, plan_date):
    """
    仕損登録時に生産実績を減算する（実績入力済みの場合のみ使用）

    Args:
        process: Process オブジェクト
        product: Product オブジェクト
        scrap_qty: 仕損数量 (Decimal)
        plan_date: 計画日 (date)
    """
    if not product or not scrap_qty or scrap_qty <= 0:
        return

    # 製品のRoutingStepから正しい工程/ラインを取得
    actual_process, actual_line = _resolve_product_process_line(product, process)
    if not actual_line:
        actual_line = getattr(actual_process, 'line', None)
    if not actual_line:
        return

    # 該当するLineBacklogレコードを取得（無ければ基礎行を作成）
    backlog, _created = LineBacklog.objects.get_or_create(
        line=actual_line,
        process=actual_process,
        product=product,
        plan_date=plan_date,
        sequence_no=0,
        defaults={
          'order_qty': 0,
          'plan_qty': 0,
          'actual_qty': 0,
          'stock_qty': 0,
          'planned_stock_qty': 0,
          'adjust_qty': 0,
          'scrap_qty': 0,
          'actual_shipment_qty': 0,
        },
    )

    # 実績から仕損数量を減算（実績超過の仕損もそのままマイナスで保持する）
    new_actual = (backlog.actual_qty or 0) - int(scrap_qty)
    backlog.actual_qty = new_actual
    backlog.save(update_fields=['actual_qty'])


def apply_nonself_scrap_adjust(process, product, scrap_qty, plan_date):
    """
    自工程生産品以外の仕損を調整カラムに積む（実績は減算しない）。
    scrap_adjust_qty をマイナスして在庫・進度に反映させる。
    """
    if not product or not scrap_qty or scrap_qty <= 0:
        return

    actual_process, actual_line = _resolve_product_process_line(product, process)
    if not actual_line:
        actual_line = getattr(actual_process, 'line', None)
    if not actual_line:
        return

    backlog, _ = LineBacklog.objects.get_or_create(
        line=actual_line,
        process=actual_process,
        product=product,
        plan_date=plan_date,
        sequence_no=0,
        defaults={
            'order_qty': 0,
            'plan_qty': 0,
            'actual_qty': 0,
            'stock_qty': 0,
            'planned_stock_qty': 0,
            'adjust_qty': 0,
            'scrap_qty': 0,
            'actual_shipment_qty': 0,
            'scrap_adjust_qty': 0,
        }
    )

    backlog.scrap_adjust_qty = (backlog.scrap_adjust_qty or 0) - int(scrap_qty)
    backlog.save(update_fields=['scrap_adjust_qty'])


def update_scrap_to_backlog(process, product, scrap_qty, plan_date, details=None, relation_type=None):
    """
    仕損登録時にLineBacklogに即時反映する

    Args:
        process: Process オブジェクト
        product: Product オブジェクト（自製品）
        scrap_qty: 仕損数量 (Decimal)
        plan_date: 計画日 (date)
        details: ScrapRecordDetailのリスト（子部品の情報）
        relation_type: related-products 起点の区分（OUTPUT_PRODUCT 等）
    """
    if not scrap_qty or scrap_qty <= 0:
        return

    # 製品のRoutingStepから正しい工程/ラインを取得（登録工程と異なる場合に対応）
    actual_process, actual_line = _resolve_product_process_line(product, process)
    if not actual_line:
        actual_line = getattr(actual_process, 'line', None)
    if not actual_line:
        return

    rel = (relation_type or '').strip().upper()
    is_self_relation = rel in ('OUTPUT_PRODUCT', 'COPRODUCT_PARENT')
    if not is_self_relation and product:
        is_self_relation = actual_process and actual_process.id == getattr(process, 'id', None)

    # 自工程生産品 → scrap_qty / それ以外 → scrap_adjust_qty(負値)
    if product:
        backlog, _ = LineBacklog.objects.get_or_create(
            line=actual_line,
            process=actual_process,
            product=product,
            plan_date=plan_date,
            sequence_no=0,
            defaults={
                'order_qty': 0,
                'plan_qty': 0,
                'actual_qty': 0,
                'stock_qty': 0,
                'planned_stock_qty': 0,
                'adjust_qty': 0,
                'scrap_qty': 0,
                'actual_shipment_qty': 0,
                'scrap_adjust_qty': 0,
            }
        )
        if is_self_relation:
            LineBacklog.objects.filter(id=backlog.id).update(
                scrap_qty=F('scrap_qty') + int(scrap_qty)
            )
        else:
            LineBacklog.objects.filter(id=backlog.id).update(
                scrap_adjust_qty=F('scrap_adjust_qty') - int(scrap_qty)
            )

    # 子部品（BOM展開明細）は adjust_qty に保存
    if details:
        for detail in details:
            detail_line_id = detail.get('line_id')
            detail_process_id = detail.get('process_id')
            detail_product_id = detail.get('product_id')
            detail_qty = detail.get('qty') or Decimal('0')

            if not detail_line_id or not detail_process_id or not detail_product_id:
                continue
            if detail_qty <= 0:
                continue
            # 自製品はスキップ（既に上で処理済み）
            if product and detail_product_id == product.id:
                continue

            child_backlog, _ = LineBacklog.objects.get_or_create(
                line_id=detail_line_id,
                process_id=detail_process_id,
                product_id=detail_product_id,
                plan_date=plan_date,
                sequence_no=0,
                defaults={
                    'order_qty': 0,
                    'plan_qty': 0,
                    'actual_qty': 0,
                    'stock_qty': 0,
                    'planned_stock_qty': 0,
                    'adjust_qty': 0,
                    'scrap_qty': 0,
                    'actual_shipment_qty': 0,
                }
            )
            # 子部品は adjust_qty に負の値として保存（在庫減算のため）
            LineBacklog.objects.filter(id=child_backlog.id).update(
                adjust_qty=F('adjust_qty') - int(detail_qty)
            )


def update_line_backlog_actual_shipment(process, product, qty, plan_date):
    """
    後工程の実績を前工程の実績出庫（actual_shipment_qty）に即時反映する。
    """
    if not product or not qty:
        return

    bom = BOM.objects.filter(parent_product=product, is_active=True).order_by('-valid_from', '-id').first()
    if not bom:
        return
    # 連産品（仮想セット）親は子の実需（actual_shipment_qty）を即時加算しない。
    # 在庫再計算ロジックでは連産BOMを出庫計算対象外としているため、ここも合わせる。
    if bom.is_coproduct:
        return

    qty_decimal = Decimal(qty)
    for item in bom.items.select_related('child_product').all():
        if item.quantity is None:
            continue
        shipment_qty = qty_decimal * Decimal(item.quantity)
        shipment_int = int(shipment_qty or 0)
        if shipment_int == 0:
            continue

        target_qs = LineBacklog.objects.filter(
            product_id=item.child_product_id,
            plan_date=plan_date,
        )
        if item.line_id:
            target_qs = target_qs.filter(line_id=item.line_id)
        if item.process_id:
            target_qs = target_qs.filter(process_id=item.process_id)

        targets = list(target_qs.values('line_id', 'process_id').distinct())
        if not targets:
            if item.line_id and item.process_id:
                targets = [{'line_id': item.line_id, 'process_id': item.process_id}]
            else:
                continue

        for target in targets:
            backlog_qs = LineBacklog.objects.filter(
                line_id=target['line_id'],
                process_id=target['process_id'],
                product_id=item.child_product_id,
                plan_date=plan_date,
                sequence_no=0,
            )
            backlog = backlog_qs.first()
            if not backlog:
                if shipment_int < 0:
                    continue
                backlog = LineBacklog.objects.create(
                    line_id=target['line_id'],
                    process_id=target['process_id'],
                    product_id=item.child_product_id,
                    plan_date=plan_date,
                    sequence_no=0,
                    order_qty=0,
                    plan_qty=0,
                    actual_qty=0,
                    stock_qty=0,
                    planned_stock_qty=0,
                    adjust_qty=0,
                    scrap_qty=0,
                    actual_shipment_qty=0,
                )
            LineBacklog.objects.filter(id=backlog.id).update(
                actual_shipment_qty=F('actual_shipment_qty') + shipment_int
            )


def expand_coproduct_children_production(
    process,
    product,
    parent_qty,
    plan_date,
    batch_no='',
    operator_name='',
    remarks='',
    parent_record_id=None,
    base_event_data=None,
    session=None,
    session_issues=None,
    skip_backlog=False,
):
    """
    連産品（仮想セット品番）の親実績から子製品実績を展開する。
    """
    if not product or not getattr(product, 'is_virtual_set', False):
        return

    bom = BOM.objects.filter(parent_product=product, is_active=True).order_by('-valid_from').first()
    if not bom or not bom.is_coproduct:
        return

    qty_decimal = parent_qty or Decimal('0')
    for item in bom.items.select_related('child_product').all():
        child_product = item.child_product
        if not child_product:
            continue
        child_qty = qty_decimal * (item.quantity or Decimal('0'))
        if child_qty == 0:
            continue

        child_event_data = dict(base_event_data or {})
        child_event_data['coproduct_parent_product_code'] = product.product_code
        if parent_record_id:
            child_event_data['coproduct_parent_record_id'] = parent_record_id

        child_record = ProcessRealtimeRecord.objects.create(
            process=process,
            product=child_product,
            product_code=child_product.product_code,
            product_name=child_product.product_name,
            record_type='PRODUCTION',
            qty=child_qty,
            equipment_state=None,
            event_data=child_event_data,
            batch_no=batch_no,
            operator_name=operator_name,
            remarks=remarks,
        )
        if session:
            _sync_record_session_meta(child_record, session, session_issues)

        if not skip_backlog:
            update_line_backlog_production(process, child_product, child_qty, plan_date)


def resolve_workday_date_for_process(process, dt):
    """
    勤務カレンダに基づいて計画日を決定する。
    夜勤で日付を跨ぐ場合は前日扱いにする。
    日替わり時刻（8時）より前は前日扱いにする。
    """
    if dt.time() < time(DAY_BOUNDARY_HOUR, 0):
        return (dt - timedelta(days=1)).date()
    if not process:
        return dt.date()
    line = getattr(process, 'line', None)
    if not line:
        return dt.date()
    try:
        from .services.gantt_planning import LineWorkCalendar
        calendar = LineWorkCalendar(line)
        segments = calendar.get_segments(dt.date())
        if not segments or dt < segments[0][0]:
            prev_date = dt.date() - timedelta(days=1)
            prev_segments = calendar.get_segments(prev_date)
            if prev_segments and prev_segments[-1][1] >= dt:
                return prev_date
        return dt.date()
    except Exception:
        return dt.date()


SESSION_ACTIONS = {'START', 'PAUSE', 'RESUME', 'END', 'TEMP_END', 'CANCEL'}
SESSION_ACTIVE_STATUSES = ['OPEN']
SESSION_TYPE_WORK = 'WORK'
SESSION_TYPE_PAUSE = 'PAUSE'


def _extract_operator_action(event_data):
    payload = event_data or {}
    action = (
        payload.get('action')
        or payload.get('operator_action')
        or payload.get('action_type')
        or ''
    )
    return str(action).upper()


def _append_issue_flag(flags, issue_code):
    items = list(flags or [])
    code = str(issue_code or '').strip().upper()
    if code and code not in items:
        items.append(code)
    return items


def _add_session_issues(session, issue_codes):
    if not session:
        return
    merged = list(session.issue_flags or [])
    changed = False
    for code in issue_codes or []:
        next_flags = _append_issue_flag(merged, code)
        if len(next_flags) != len(merged):
            merged = next_flags
            changed = True
    if changed:
        session.issue_flags = merged
        session.issue_count = len(merged)
        session.save(update_fields=['issue_flags', 'issue_count', 'updated_at'])


def _next_session_no(process, product, plan_date):
    latest = ProcessWorkSession.objects.filter(
        process=process,
        product=product,
        plan_date=plan_date,
    ).order_by('-session_no').first()
    return (latest.session_no if latest else 0) + 1


def _create_session(
    process,
    product,
    plan_date,
    started_at,
    start_record,
    session_type=SESSION_TYPE_WORK,
    start_action='',
    operator_name='',
):
    product_code = product.product_code if product else ''
    product_name = product.product_name if product else ''
    return ProcessWorkSession.objects.create(
        process=process,
        product=product,
        product_code=product_code or '',
        product_name=product_name or '',
        plan_date=plan_date,
        session_no=_next_session_no(process, product, plan_date),
        started_at=started_at,
        status='OPEN',
        session_type=session_type,
        start_action=str(start_action or '').upper(),
        start_record=start_record,
        operator_name=operator_name or '',
    )


def _close_session(session, end_record, ended_at, end_action, production_qty=Decimal('0')):
    duration_seconds = 0
    if session.started_at and ended_at:
        duration_seconds = int((ended_at - session.started_at).total_seconds())
    session.ended_at = ended_at
    session.end_record = end_record
    session.end_action = str(end_action or '').upper()
    session.status = 'CLOSED'
    session.duration_seconds = max(duration_seconds, 0)
    session.production_qty = production_qty or Decimal('0')
    session.save(
        update_fields=[
            'ended_at',
            'end_record',
            'end_action',
            'status',
            'duration_seconds',
            'production_qty',
            'updated_at',
        ]
    )


def _build_session_meta(session):
    if not session:
        return None
    return {
        'id': session.id,
        'session_no': session.session_no,
        'session_type': session.session_type,
        'status': session.status,
        'plan_date': session.plan_date.isoformat() if session.plan_date else None,
        'start_action': session.start_action,
        'end_action': session.end_action,
        'started_at': session.started_at.isoformat() if session.started_at else None,
        'ended_at': session.ended_at.isoformat() if session.ended_at else None,
        'duration_seconds': int(session.duration_seconds or 0),
        'production_qty': float(session.production_qty or 0),
        'issue_count': int(session.issue_count or 0),
        'issue_flags': list(session.issue_flags or []),
    }


def _sync_record_session_meta(record, session, issue_codes=None):
    event_data = dict(record.event_data or {})
    meta = _build_session_meta(session)
    if meta:
        event_data['session'] = meta
    issues = list(event_data.get('session_issues') or [])
    for code in issue_codes or []:
        issues = _append_issue_flag(issues, code)
    if issues:
        event_data['session_issues'] = issues
    record.event_data = event_data
    record.save(update_fields=['event_data'])


def apply_operator_action_session(process, product, action, action_record, plan_date, production_qty=Decimal('0')):
    """
    作業者アクションからセッション状態を更新し、不整合を検知する。
    """
    action_key = str(action or '').upper()
    if action_key not in SESSION_ACTIONS:
        return None, []
    if not product:
        return None, ['MISSING_PRODUCT']

    issues = []
    action_time = action_record.timestamp
    action_event_data = dict(getattr(action_record, 'event_data', None) or {})
    two_person_same_equipment = bool(action_event_data.get('two_person_same_equipment'))
    current_operator_name = str(getattr(action_record, 'operator_name', '') or '').strip().lower()

    # 2人1設備モード時は作業者名でセッションを絞り込む（既存の空セッションにもフォールバック）
    base_session_qs = ProcessWorkSession.objects.filter(
        process=process,
        product=product,
        status__in=SESSION_ACTIVE_STATUSES,
    )
    if two_person_same_equipment and current_operator_name:
        session = base_session_qs.filter(operator_name=current_operator_name).order_by('-started_at', '-id').first()
    else:
        session = base_session_qs.order_by('-started_at', '-id').first()

    other_open_session = ProcessWorkSession.objects.filter(
        process=process,
        session_type=SESSION_TYPE_WORK,
        status__in=SESSION_ACTIVE_STATUSES,
    ).exclude(product=product).order_by('-started_at', '-id').first()

    def should_mark_overlap(other_session):
        if not other_session:
            return False
        if not two_person_same_equipment:
            return True
        other_start_record = getattr(other_session, 'start_record', None)
        other_operator_name = str(getattr(other_start_record, 'operator_name', '') or '').strip().lower()
        if current_operator_name and other_operator_name and current_operator_name != other_operator_name:
            return False
        return True

    session_operator_name = current_operator_name if two_person_same_equipment else ''

    def create_work(start_action):
        return _create_session(
            process=process,
            product=product,
            plan_date=plan_date,
            started_at=action_time,
            start_record=action_record,
            session_type=SESSION_TYPE_WORK,
            start_action=start_action,
            operator_name=session_operator_name,
        )

    def create_pause(start_action):
        return _create_session(
            process=process,
            product=product,
            plan_date=plan_date,
            started_at=action_time,
            start_record=action_record,
            session_type=SESSION_TYPE_PAUSE,
            start_action=start_action,
            operator_name=session_operator_name,
        )

    if action_key == 'START':
        if session:
            issues.append('DUPLICATE_START')
        else:
            session = create_work('START')
        if should_mark_overlap(other_open_session):
            issues.append('OVERLAP_OTHER_PRODUCT')
            issues.append(f"OVERLAP_SESSION_ID_{other_open_session.id}")

    elif action_key == 'PAUSE':
        qty = production_qty or Decimal('0')
        if not session:
            issues.append('PAUSE_WITHOUT_START')
            session = create_pause('PAUSE')
        elif session.session_type == SESSION_TYPE_PAUSE:
            issues.append('DUPLICATE_PAUSE')
        else:
            _close_session(
                session=session,
                end_record=action_record,
                ended_at=action_time,
                end_action='PAUSE',
                production_qty=qty,
            )
            session = create_pause('PAUSE')

    elif action_key == 'RESUME':
        if not session:
            issues.append('RESUME_WITHOUT_PAUSE')
            session = create_work('RESUME')
        elif session.session_type == SESSION_TYPE_PAUSE:
            _close_session(
                session=session,
                end_record=action_record,
                ended_at=action_time,
                end_action='RESUME',
                production_qty=Decimal('0'),
            )
            session = create_work('RESUME')
        else:
            issues.append('RESUME_WHILE_WORK')
        if should_mark_overlap(other_open_session):
            issues.append('OVERLAP_OTHER_PRODUCT')
            issues.append(f"OVERLAP_SESSION_ID_{other_open_session.id}")

    elif action_key == 'CANCEL':
        qty = Decimal('0')
        if session:
            _close_session(
                session=session,
                end_record=action_record,
                ended_at=action_time,
                end_action='CANCEL',
                production_qty=qty,
            )
        else:
            cancel_last_qs = ProcessWorkSession.objects.filter(
                process=process,
                product=product,
            )
            if two_person_same_equipment and current_operator_name:
                last_session = cancel_last_qs.filter(operator_name=current_operator_name).order_by('-started_at', '-id').first()
            else:
                last_session = cancel_last_qs.order_by('-started_at', '-id').first()
            last_end_action = str(getattr(last_session, 'end_action', '') or '').upper()
            if last_session and last_end_action == 'TEMP_END':
                start_time = last_session.ended_at or action_time
                start_record = last_session.end_record or action_record
                session = _create_session(
                    process=process,
                    product=product,
                    plan_date=last_session.plan_date or plan_date,
                    started_at=start_time,
                    start_record=start_record,
                    session_type=SESSION_TYPE_WORK,
                    start_action='TEMP_END',
                    operator_name=session_operator_name,
                )
                _close_session(
                    session=session,
                    end_record=action_record,
                    ended_at=action_time,
                    end_action='CANCEL',
                    production_qty=qty,
                )
            else:
                issues.append('CANCEL_WITHOUT_START')
                session = create_work('CANCEL')
                _close_session(
                    session=session,
                    end_record=action_record,
                    ended_at=action_time,
                    end_action='CANCEL',
                    production_qty=qty,
                )

    elif action_key in ('END', 'TEMP_END'):
        qty = production_qty or Decimal('0')
        if not session:
            if action_key == 'END':
                end_last_qs = ProcessWorkSession.objects.filter(
                    process=process,
                    product=product,
                )
                if two_person_same_equipment and current_operator_name:
                    last_session = end_last_qs.filter(operator_name=current_operator_name).order_by('-started_at', '-id').first()
                else:
                    last_session = end_last_qs.order_by('-started_at', '-id').first()
                last_end_action = str(getattr(last_session, 'end_action', '') or '').upper()
                if last_session and last_end_action == 'TEMP_END':
                    session = create_work('RESUME')
                    _close_session(
                        session=session,
                        end_record=action_record,
                        ended_at=action_time,
                        end_action='END',
                        production_qty=qty,
                    )
                else:
                    issues.append('END_WITHOUT_START')
                    session = create_work('END')
                    _close_session(
                        session=session,
                        end_record=action_record,
                        ended_at=action_time,
                        end_action='END',
                        production_qty=qty,
                    )
            else:
                issues.append('TEMP_END_WITHOUT_START')
                session = create_work('TEMP_END')
                _close_session(
                    session=session,
                    end_record=action_record,
                    ended_at=action_time,
                    end_action='TEMP_END',
                    production_qty=Decimal('0'),
                )
        else:
            if session.session_type == SESSION_TYPE_PAUSE:
                issues.append(f'{action_key}_WHILE_PAUSED')
                _close_session(
                    session=session,
                    end_record=action_record,
                    ended_at=action_time,
                    end_action=action_key,
                    production_qty=Decimal('0'),
                )
                if action_key == 'END':
                    issues.append('IMPLICIT_RESUME_BEFORE_END')
                    session = create_work('RESUME')
                    _close_session(
                        session=session,
                        end_record=action_record,
                        ended_at=action_time,
                        end_action='END',
                        production_qty=qty,
                    )
            else:
                _close_session(
                    session=session,
                    end_record=action_record,
                    ended_at=action_time,
                    end_action=action_key,
                    production_qty=qty if action_key == 'END' else Decimal('0'),
                )

    _add_session_issues(session, issues)
    return session, issues


class ProcessRealtimeRecordSerializer(serializers.ModelSerializer):
    """工程実時間記録Serializer"""

    process_code = serializers.CharField(source='process.process_code', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    record_type_display = serializers.CharField(source='get_record_type_display', read_only=True)
    equipment_state_display = serializers.CharField(source='get_equipment_state_display', read_only=True)
    product_code = serializers.CharField(read_only=True)
    product_name = serializers.CharField(read_only=True)
    scrap_record_id = serializers.SerializerMethodField()
    scrap_is_replenished = serializers.SerializerMethodField()
    scrap_replenished_at = serializers.SerializerMethodField()
    scrap_disposition_status = serializers.SerializerMethodField()
    scrap_disposition_display = serializers.SerializerMethodField()
    scrap_return_qty = serializers.SerializerMethodField()
    scrap_is_production_recorded = serializers.SerializerMethodField()
    scrap_decided_at = serializers.SerializerMethodField()
    scrap_decided_by = serializers.SerializerMethodField()

    class Meta:
        model = ProcessRealtimeRecord
        fields = [
            'id',
            'process',
            'process_code',
            'process_name',
            'product',
            'product_code',
            'product_name',
            'timestamp',
            'record_type',
            'record_type_display',
            'qty',
            'equipment_state',
            'equipment_state_display',
            'event_data',
            'batch_no',
            'operator_name',
            'remarks',
            'scrap_record_id',
            'scrap_is_replenished',
            'scrap_replenished_at',
            'scrap_disposition_status',
            'scrap_disposition_display',
            'scrap_return_qty',
            'scrap_is_production_recorded',
            'scrap_decided_at',
            'scrap_decided_by',
        ]
        read_only_fields = ['id', 'timestamp']

    def get_scrap_record_id(self, obj):
        return getattr(getattr(obj, 'scrap_detail', None), 'id', None)

    def get_scrap_is_replenished(self, obj):
        sd = getattr(obj, 'scrap_detail', None)
        return sd.is_replenished if sd else None

    def get_scrap_replenished_at(self, obj):
        sd = getattr(obj, 'scrap_detail', None)
        return sd.replenished_at if sd else None

    def get_scrap_disposition_status(self, obj):
        sd = getattr(obj, 'scrap_detail', None)
        return sd.disposition_status if sd else None

    def get_scrap_disposition_display(self, obj):
        sd = getattr(obj, 'scrap_detail', None)
        return sd.get_disposition_status_display() if sd else None

    def get_scrap_return_qty(self, obj):
        sd = getattr(obj, 'scrap_detail', None)
        return sd.return_qty if sd else None

    def get_scrap_is_production_recorded(self, obj):
        sd = getattr(obj, 'scrap_detail', None)
        return sd.is_production_recorded if sd else None

    def get_scrap_decided_at(self, obj):
        sd = getattr(obj, 'scrap_detail', None)
        return sd.decided_at if sd else None

    def get_scrap_decided_by(self, obj):
        sd = getattr(obj, 'scrap_detail', None)
        return sd.decided_by if sd else None


class ProcessWorkSessionSerializer(serializers.ModelSerializer):
    """工程作業セッションSerializer"""

    process_code = serializers.CharField(source='process.process_code', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    operator_name = serializers.SerializerMethodField()
    pause_reason = serializers.SerializerMethodField()
    equipments = serializers.SerializerMethodField()

    @staticmethod
    def _extract_pause_reason_from_record(record):
        if not record:
            return ''
        event_data = getattr(record, 'event_data', None)
        if not isinstance(event_data, dict):
            return ''
        for key in ('pause_reason', 'operator_action_reason'):
            value = event_data.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return ''

    def get_operator_name(self, obj):
        end_record = getattr(obj, 'end_record', None)
        end_name = (getattr(end_record, 'operator_name', '') or '').strip() if end_record else ''
        if end_name:
            return end_name
        start_record = getattr(obj, 'start_record', None)
        start_name = (getattr(start_record, 'operator_name', '') or '').strip() if start_record else ''
        if start_name:
            return start_name
        # 手動後入力セッション（start_record/end_record なし）はモデルフィールドから返す
        return (getattr(obj, 'operator_name', '') or '').strip()

    def get_pause_reason(self, obj):
        session_type = str(getattr(obj, 'session_type', '') or '').upper()
        end_action = str(getattr(obj, 'end_action', '') or '').upper()

        if session_type == 'PAUSE':
            candidate_records = [getattr(obj, 'start_record', None), getattr(obj, 'end_record', None)]
        elif session_type == 'WORK' and end_action == 'PAUSE':
            candidate_records = [getattr(obj, 'end_record', None), getattr(obj, 'start_record', None)]
        else:
            candidate_records = [getattr(obj, 'start_record', None), getattr(obj, 'end_record', None)]

        for record in candidate_records:
            reason = self._extract_pause_reason_from_record(record)
            if reason:
                return reason
        return ''

    def get_equipments(self, obj):
        manager = getattr(obj, 'session_equipments', None)
        if manager is None:
            return []
        rows = []
        for rel in manager.all():
            equipment = getattr(rel, 'equipment', None)
            rows.append({
                'equipment_id': rel.equipment_id,
                'equipment_code': getattr(equipment, 'equipment_code', '') if equipment else '',
                'equipment_name': getattr(equipment, 'equipment_name', '') if equipment else '',
                'role': rel.role,
            })
        return rows

    class Meta:
        model = ProcessWorkSession
        fields = [
            'id',
            'process',
            'process_code',
            'process_name',
            'product',
            'product_code',
            'product_name',
            'operator_name',
            'plan_date',
            'session_no',
            'session_type',
            'start_action',
            'end_action',
            'pause_reason',
            'equipments',
            'started_at',
            'ended_at',
            'status',
            'duration_seconds',
            'production_qty',
            'defect_qty',
            'issue_count',
            'issue_flags',
            'start_record',
            'end_record',
            'created_at',
            'updated_at',
        ]


class ProcessWorkSessionChangeHistorySerializer(serializers.ModelSerializer):
    process_code = serializers.CharField(source='process.process_code', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    changed_by_name = serializers.SerializerMethodField()

    def get_changed_by_name(self, obj):
        user = getattr(obj, 'changed_by', None)
        if not user:
            return ''
        full_name = (getattr(user, 'get_full_name', lambda: '')() or '').strip()
        if full_name:
            return full_name
        return getattr(user, 'username', '') or ''

    class Meta:
        model = ProcessWorkSessionChangeHistory
        fields = [
            'id',
            'session',
            'session_record_id',
            'operation_type',
            'process',
            'process_code',
            'process_name',
            'product',
            'product_code',
            'product_name',
            'plan_date',
            'reason',
            'change_summary',
            'before_data',
            'after_data',
            'changed_by',
            'changed_by_name',
            'changed_at',
        ]


class ProcessRealtimeCreateSerializer(serializers.Serializer):
    """工程実時間記録作成用Serializer（簡易入力）"""

    process_id = serializers.IntegerField()
    product_id = serializers.IntegerField(required=False, allow_null=True)
    product_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    product_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    record_type = serializers.ChoiceField(choices=ProcessRealtimeRecord.RECORD_TYPE_CHOICES)
    qty = serializers.DecimalField(max_digits=10, decimal_places=3, default=0)
    production_qty = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        required=False,
        allow_null=True,
    )
    equipment_state = serializers.ChoiceField(
        choices=ProcessRealtimeRecord.EQUIPMENT_STATE_CHOICES,
        required=False,
        allow_null=True
    )
    batch_no = serializers.CharField(max_length=100, required=False, allow_blank=True)
    operator_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    remarks = serializers.CharField(required=False, allow_blank=True)
    event_data = serializers.JSONField(required=False, allow_null=True)
    work_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs.get('record_type') in ['PRODUCTION', 'SCRAP']:
            has_product_id = bool(attrs.get('product_id'))
            has_product_code = bool((attrs.get('product_code') or '').strip())
            if not has_product_id and not has_product_code:
                raise serializers.ValidationError({'product_id': '生産記録は製品（品番）の指定が必要です。'})
        if attrs.get('record_type') == 'OPERATOR_ACTION':
            event_data = attrs.get('event_data') or {}
            action = _extract_operator_action(event_data)
            if action in SESSION_ACTIONS and not attrs.get('product_id'):
                raise serializers.ValidationError({'product_id': '作業時刻記録は製品の指定が必要です。'})
            if action == 'PAUSE':
                pause_qty = attrs.get('qty')
                if pause_qty is None or pause_qty < 0:
                    raise serializers.ValidationError({'qty': '中断時は数量の入力が必要です。'})
            if action == 'END':
                production_qty = attrs.get('production_qty')
                remarks_text = (attrs.get('remarks') or '').strip()
                if production_qty is None:
                    raise serializers.ValidationError({'production_qty': '終了時は数量の入力が必要です。'})
                if production_qty < 0:
                    raise serializers.ValidationError({'production_qty': '終了時の数量は0以上で入力してください。'})
                if production_qty == 0 and not remarks_text:
                    raise serializers.ValidationError({'production_qty': '終了時に数量0を入力する場合は備考の入力が必要です。'})
        return attrs

    def create(self, validated_data):
        process_id = validated_data.pop('process_id')
        try:
            process = Process.objects.get(id=process_id)
        except Process.DoesNotExist as exc:
            raise serializers.ValidationError({'process_id': '指定された工程が存在しません。'}) from exc

        override_work_date = validated_data.pop('work_date', None)
        now = timezone.now()
        if timezone.is_aware(now):
            now = timezone.localtime(now).replace(tzinfo=None)
        if override_work_date:
            plan_date = override_work_date
        else:
            plan_date = resolve_workday_date_for_process(process, now)

        product = None
        product_id = validated_data.pop('product_id', None)
        product_code = (validated_data.pop('product_code', None) or '').strip() or None
        product_name = (validated_data.pop('product_name', None) or '').strip() or None
        production_qty = validated_data.pop('production_qty', None)
        scrap_event = (validated_data.get('event_data') or {}) if validated_data else {}
        operator_event = (validated_data.get('event_data') or {}) if validated_data else {}

        if product_id:
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist as exc:
                raise serializers.ValidationError({'product_id': '指定された製品が存在しません。'}) from exc
        elif product_code:
            product = Product.objects.filter(product_code=product_code).first()

        if product:
            product_code = product.product_code
            product_name = product.product_name

        operator_action = _extract_operator_action(operator_event)
        requires_routing_validation = (
            validated_data.get('record_type') == 'PRODUCTION'
            or (
                validated_data.get('record_type') == 'OPERATOR_ACTION'
                and operator_action in SESSION_ACTIONS
            )
        )
        if requires_routing_validation:
            if not product:
                raise serializers.ValidationError({'product_id': '指定された製品が存在しません。'})
            routing_line_id = None
            event_source = str(operator_event.get('source') or '').strip().upper()
            if event_source in {'PURCHASE_ACTUAL_INPUT', 'PURCHASE_RECEIVING'}:
                try:
                    routing_line_id = int(operator_event.get('line_id'))
                except (TypeError, ValueError):
                    routing_line_id = None
            if not is_valid_output_process(
                process,
                product,
                plan_date,
                line_id=routing_line_id,
            ):
                raise serializers.ValidationError({
                    'product_id': build_invalid_product_process_message(process, product),
                })

        if validated_data.get('record_type') == 'OPERATOR_ACTION':
            if operator_action in SESSION_ACTIONS and not product:
                raise serializers.ValidationError({'product_id': '作業時刻記録は製品の指定が必要です。'})
        if validated_data.get('record_type') == 'OPERATOR_ACTION' and operator_action == 'END':
            end_session_qs = ProcessWorkSession.objects.filter(
                process=process,
                product=product,
                status__in=SESSION_ACTIVE_STATUSES,
            )
            end_two_person = bool(operator_event.get('two_person_same_equipment'))
            end_operator_name = str(validated_data.get('operator_name') or '').strip().lower()
            if end_two_person and end_operator_name:
                open_session = end_session_qs.filter(operator_name=end_operator_name).order_by('-started_at', '-id').first()
            else:
                open_session = end_session_qs.order_by('-started_at', '-id').first()
            if not open_session:
                raise serializers.ValidationError({'non_field_errors': ['開始されていないため終了できません。画面を更新して状態を確認してください。']})
            qty_decimal = production_qty or Decimal('0')
            remarks_text = (validated_data.get('remarks') or '').strip()
            if qty_decimal < 0:
                raise serializers.ValidationError({'production_qty': '終了時の数量は0以上で入力してください。'})
            if qty_decimal == 0 and not remarks_text:
                raise serializers.ValidationError({'production_qty': '終了時に数量0を入力する場合は備考の入力が必要です。'})
            if not product:
                raise serializers.ValidationError({'product_id': '終了実績の保存には製品の指定が必要です。'})

        validated_data.pop('work_date', None)

        with transaction.atomic():
            parent_record = ProcessRealtimeRecord.objects.create(
                process=process,
                product=product,
                product_code=product_code,
                product_name=product_name,
                **validated_data
            )

            session = None
            session_issues = []
            if validated_data.get('record_type') == 'OPERATOR_ACTION' and operator_action in SESSION_ACTIONS:
                session_production_qty = Decimal('0')
                if operator_action == 'END':
                    session_production_qty = production_qty or Decimal('0')
                elif operator_action == 'PAUSE':
                    session_production_qty = validated_data.get('qty', Decimal('0')) or Decimal('0')
                session, session_issues = apply_operator_action_session(
                    process=process,
                    product=product,
                    action=operator_action,
                    action_record=parent_record,
                    plan_date=plan_date,
                    production_qty=session_production_qty,
                )
                _sync_record_session_meta(parent_record, session, session_issues)

            # 作業者アクション PAUSE / END では、生産実績を別レコードとして保存しLineBacklogに反映
            if (
                validated_data.get('record_type') == 'OPERATOR_ACTION'
                and operator_action in ('PAUSE', 'END')
            ):
                production_session = session
                if operator_action == 'PAUSE' and parent_record and process and product:
                    # PAUSE時の数量は「直前で閉じた作業セッション」に紐付ける
                    # （中断セッションへ紐付くと、実績照会で START/RESUME→PAUSE 行に数量が出ないため）
                    closed_work_session = ProcessWorkSession.objects.filter(
                        process=process,
                        product=product,
                        end_record=parent_record,
                        session_type=SESSION_TYPE_WORK,
                    ).order_by('-id').first()
                    if closed_work_session:
                        production_session = closed_work_session

                qty_decimal = (
                    production_qty if operator_action == 'END'
                    else validated_data.get('qty', Decimal('0'))
                ) or Decimal('0')
                source = 'OPERATOR_ACTION_END' if operator_action == 'END' else 'OPERATOR_ACTION_PAUSE'
                production_event_data = {
                    'source': source,
                    'operator_action_record_id': parent_record.id,
                    'operator_action': operator_action,
                }
                if production_session:
                    production_event_data['work_session_id'] = production_session.id
                    production_event_data['session'] = _build_session_meta(production_session)
                plan_target = operator_event.get('plan_target')
                if isinstance(plan_target, dict):
                    production_event_data['plan_target'] = plan_target
                production_record = ProcessRealtimeRecord.objects.create(
                    process=process,
                    product=product,
                    product_code=product_code,
                    product_name=product_name,
                    record_type='PRODUCTION',
                    qty=qty_decimal,
                    equipment_state=None,
                    event_data=production_event_data,
                    batch_no=validated_data.get('batch_no', ''),
                    operator_name=validated_data.get('operator_name', ''),
                    remarks=validated_data.get('remarks', ''),
                )
                if production_session:
                    _sync_record_session_meta(production_record, production_session, session_issues)
                update_line_backlog_production(process, product, qty_decimal, plan_date)
                update_line_backlog_actual_shipment(process, product, qty_decimal, plan_date)
                expand_coproduct_children_production(
                    process=process,
                    product=product,
                    parent_qty=qty_decimal,
                    plan_date=plan_date,
                    batch_no=validated_data.get('batch_no', ''),
                    operator_name=validated_data.get('operator_name', ''),
                    remarks=validated_data.get('remarks', ''),
                    parent_record_id=production_record.id,
                    base_event_data=production_event_data,
                    session=production_session,
                    session_issues=session_issues,
                )

            # 生産実績の場合、LineBacklogに反映
            if validated_data.get('record_type') == 'PRODUCTION':
                qty_decimal = validated_data.get('qty', Decimal('0')) or Decimal('0')
                update_line_backlog_production(process, product, qty_decimal, plan_date)
                update_line_backlog_actual_shipment(process, product, qty_decimal, plan_date)

            # 連産品（仮想セット品番）の場合、子製品にも実績を保存する
            if validated_data.get('record_type') == 'PRODUCTION':
                qty_decimal = validated_data.get('qty', Decimal('0')) or Decimal('0')
                expand_coproduct_children_production(
                    process=process,
                    product=product,
                    parent_qty=qty_decimal,
                    plan_date=plan_date,
                    batch_no=validated_data.get('batch_no', ''),
                    operator_name=validated_data.get('operator_name', ''),
                    remarks=validated_data.get('remarks', ''),
                    parent_record_id=parent_record.id,
                )

            # 仕損は別テーブルにも保存
            if validated_data.get('record_type') == 'SCRAP':
                qty_decimal = validated_data.get('qty', Decimal('0')) or Decimal('0')
                status_raw = (scrap_event.get('disposition_status') or '').strip().upper()
                valid_statuses = {s for s, _ in ScrapRecord.DISPOSITION_STATUS_CHOICES}
                disposition_status = status_raw if status_raw in valid_statuses else 'REJECTED'
                decided_at = timezone.now() if disposition_status != 'PENDING' else None
                decided_by = validated_data.get('operator_name') if decided_at else None
                # 実績入力済みフラグ（True: 生産実績入力済み、False: 実績未入力）
                is_production_recorded = scrap_event.get('is_production_recorded', False)
                if isinstance(is_production_recorded, str):
                    is_production_recorded = is_production_recorded.lower() in ('true', '1', 'yes')
                relation_type = (scrap_event.get('relation_type') or '').strip().upper()

                try:
                    sr = ScrapRecord.objects.create(
                        process=process,
                        occurrence_process=process,  # 発生工程（実際に仕損を登録した工程）
                        line=getattr(process, 'line', None),
                        product=product,
                        product_code=product_code,
                        product_name=product_name,
                        event_type='SCRAP',
                        qty=qty_decimal,
                        plan_date=plan_date,  # 勤務カレンダに合わせた計画日
                        reason=scrap_event.get('reason') or '',
                        reason_detail=scrap_event.get('reason_detail') or '',
                        batch_no=validated_data.get('batch_no', ''),
                        operator_name=validated_data.get('operator_name', ''),
                        remarks=validated_data.get('remarks', ''),
                        process_record=parent_record,
                        disposition_status=disposition_status,
                        decided_at=decided_at,
                        decided_by=decided_by,
                        is_production_recorded=is_production_recorded,
                    )
                except Exception as exc:
                    from django.db import IntegrityError
                    if isinstance(exc, IntegrityError):
                        raise serializers.ValidationError(
                            {'detail': '同一実績に対する仕損が既に登録されています。画面を更新して最新の記録を確認してください。'}
                        ) from exc
                    raise

                # 明細を保存（BOM展開結果）
                details = build_scrap_multiplier_details(product.id if product else None, qty_decimal)
                if details:
                    products = {
                        p.id: p for p in Product.objects.filter(
                            id__in=[d['product_id'] for d in details if d.get('product_id')]
                        )
                    }
                    objs = []
                    for d in details:
                        pid = d.get('product_id')
                        prod = products.get(pid) if pid else None
                        objs.append(ScrapRecordDetail(
                            scrap_record=sr,
                            product=prod,
                            product_code=prod.product_code if prod else None,
                            product_name=prod.product_name if prod else None,
                            process_id=d.get('process_id'),
                            line_id=d.get('line_id'),
                            supplier_id=d.get('supplier_id'),
                            sourcing_type=d.get('sourcing_type'),
                            deduct_qty=d.get('qty') or Decimal('0'),
                            is_backlog_processed=True,  # 登録時にLineBacklogに反映済み
                        ))
                    ScrapRecordDetail.objects.bulk_create(objs)

                # LineBacklogへの即時反映（自製品 or 前工程/購買品 → scrap_qty / scrap_adjust_qty、子部品 → adjust_qty）
                update_scrap_to_backlog(
                    process,
                    product,
                    qty_decimal,
                    plan_date,
                    details,
                    relation_type=relation_type,
                )

                # 在庫・実績への転嫁
                if is_production_recorded:
                    # 実績入力済みの場合：自工程生産品のみ actual 減算、その他は scrap_adjust_qty に積む
                    self_relation = relation_type in ('OUTPUT_PRODUCT', 'COPRODUCT_PARENT')
                    if not self_relation and product:
                        resolved_process, _resolved_line = _resolve_product_process_line(product, process)
                        self_relation = resolved_process and resolved_process.id == process.id
                    if self_relation:
                        adjust_production_for_scrap(process, product, qty_decimal, plan_date)
                    else:
                        apply_nonself_scrap_adjust(process, product, qty_decimal, plan_date)
                else:
                    # 実績未入力の場合：BOMを最下層まで展開し、在庫引当テーブルに反映
                    # （即時在庫への反映用。LineBacklogのadjust_qtyは上で反映済み）
                    multipliers = build_scrap_multiplier_map(product.id if product else None, qty_decimal)
                    if multipliers:
                        apply_scrap_to_stock(multipliers)

            return parent_record
