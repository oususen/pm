from collections import defaultdict
from datetime import date, datetime, timedelta
import logging

from django.db import transaction

from masters.models import Line, Process, Product
from notifications.models import Notification
from production.models_line_backlog import LineBacklog
from production.models_process_realtime import ProcessRealtimeRecord
from production.models_process_work_session import ProcessWorkSession
from production.models_production_actual_reconcile import (
    ProductionActualReconcileReport,
    ProductionActualReconcileReportDetail,
)
from production.serializers_process_realtime import resolve_workday_date_for_process
from production.views_process_realtime import _is_countable_session_for_actual

logger = logging.getLogger(__name__)

TARGET_LINE_TYPES = {'PROD', 'OUTSOURCE'}


def _to_int_or_none(value):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_date_or_none(value):
    text = str(value or '').strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text.replace('/', '-'))
    except ValueError:
        return None


def _to_naive_datetime(dt):
    if not dt:
        return None
    if isinstance(dt, datetime) and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _resolve_production_record_plan_date(record):
    event = record.event_data or {}
    session_meta = event.get('session') if isinstance(event.get('session'), dict) else {}
    plan_date = (
        _parse_date_or_none(session_meta.get('plan_date'))
        or _parse_date_or_none(event.get('plan_date'))
    )
    if plan_date:
        return plan_date
    ts = _to_naive_datetime(record.timestamp)
    if not ts:
        return datetime.now().date()
    return resolve_workday_date_for_process(record.process, ts)


def collect_production_actual_reconcile_diffs():
    expected_by_key = defaultdict(int)
    session_map = {}

    session_qs = (
        ProcessWorkSession.objects.filter(
            process__line__line_type__in=TARGET_LINE_TYPES,
        )
        .select_related('process', 'process__line')
        .only(
            'id',
            'process_id',
            'product_id',
            'plan_date',
            'production_qty',
            'session_type',
            'end_action',
            'process__line_id',
        )
    )
    for session in session_qs.iterator():
        line_id = _to_int_or_none(getattr(session.process, 'line_id', None))
        session_map[int(session.id)] = {
            'line_id': line_id,
            'process_id': _to_int_or_none(session.process_id),
            'product_id': _to_int_or_none(session.product_id),
            'plan_date': session.plan_date,
            'countable': _is_countable_session_for_actual(session.session_type, session.end_action),
        }

        if not session_map[int(session.id)]['countable']:
            continue
        if not line_id or not session.process_id or not session.product_id or not session.plan_date:
            continue
        key = (line_id, int(session.process_id), int(session.product_id), session.plan_date)
        expected_by_key[key] += int(session.production_qty or 0)

    rec_qs = (
        ProcessRealtimeRecord.objects.filter(record_type='PRODUCTION')
        .exclude(event_data__source='PURCHASE_ACTUAL_INPUT')
        .select_related('process', 'process__line', 'product')
        .only('id', 'process_id', 'product_id', 'qty', 'timestamp', 'event_data', 'process__line_id', 'process__line__line_type')
    )
    for rec in rec_qs.iterator():
        if not rec.process_id or not rec.product_id:
            continue
        line_obj = getattr(rec.process, 'line', None)
        line_id = _to_int_or_none(getattr(line_obj, 'id', None))
        line_type = str(getattr(line_obj, 'line_type', '') or '').upper()
        if not line_id or line_type not in TARGET_LINE_TYPES:
            continue

        plan_date = _resolve_production_record_plan_date(rec)
        event = rec.event_data or {}
        work_session_id = _to_int_or_none(event.get('work_session_id'))
        if work_session_id:
            session_meta = session_map.get(work_session_id)
            if session_meta and session_meta.get('countable'):
                same_parent = (
                    _to_int_or_none(session_meta.get('line_id')) == line_id
                    and _to_int_or_none(session_meta.get('process_id')) == _to_int_or_none(rec.process_id)
                    and _to_int_or_none(session_meta.get('product_id')) == _to_int_or_none(rec.product_id)
                    and session_meta.get('plan_date') == plan_date
                )
                if same_parent:
                    # 親セッション由来の生産実績レコードは、ProcessWorkSession側で計上済みのため除外
                    continue

        key = (line_id, int(rec.process_id), int(rec.product_id), plan_date)
        expected_by_key[key] += int(rec.qty or 0)

    backlog_by_key = {}
    backlog_qs = (
        LineBacklog.objects.filter(
            sequence_no=0,
            line__line_type__in=TARGET_LINE_TYPES,
        )
        .exclude(actual_qty=0)
        .select_related('line', 'process', 'product')
        .only(
            'id',
            'line_id',
            'process_id',
            'product_id',
            'plan_date',
            'actual_qty',
            'line__line_code',
            'line__line_name',
            'process__process_code',
            'process__process_name',
            'product__product_code',
            'product__product_name',
        )
    )
    for row in backlog_qs.iterator():
        if not row.line_id or not row.process_id or not row.product_id or not row.plan_date:
            continue
        key = (int(row.line_id), int(row.process_id), int(row.product_id), row.plan_date)
        backlog_by_key[key] = int(row.actual_qty or 0)

    all_keys = set(expected_by_key.keys()) | set(backlog_by_key.keys())
    line_ids = {line_id for line_id, _, _, _ in all_keys}
    process_ids = {process_id for _, process_id, _, _ in all_keys}
    product_ids = {product_id for _, _, product_id, _ in all_keys}

    line_map = Line.objects.in_bulk(line_ids)
    process_map = Process.objects.in_bulk(process_ids)
    product_map = Product.objects.in_bulk(product_ids)

    diff_rows = []

    for line_id, process_id, product_id, plan_date in sorted(
        all_keys,
        key=lambda x: (x[3], x[0], x[2], x[1]),
    ):
        expected_qty = int(expected_by_key.get((line_id, process_id, product_id, plan_date), 0))
        backlog_qty = int(backlog_by_key.get((line_id, process_id, product_id, plan_date), 0))
        if expected_qty == backlog_qty:
            continue

        line = line_map.get(line_id)
        process = process_map.get(process_id)
        product = product_map.get(product_id)
        diff_rows.append({
            'line_id': line_id,
            'line_code': getattr(line, 'line_code', ''),
            'line_name': getattr(line, 'line_name', ''),
            'process_id': process_id,
            'process_code': getattr(process, 'process_code', ''),
            'process_name': getattr(process, 'process_name', ''),
            'product_id': product_id,
            'product_code': getattr(product, 'product_code', ''),
            'product_name': getattr(product, 'product_name', ''),
            'plan_date': plan_date,
            'expected_qty': expected_qty,
            'backlog_qty': backlog_qty,
            'diff_qty': expected_qty - backlog_qty,
        })

    return {
        'compared_count': len(all_keys),
        'diff_rows': diff_rows,
    }


def _apply_reconcile_fix(diff_rows):
    fixed_count = 0

    with transaction.atomic():
        for row in diff_rows:
            line_id = row['line_id']
            process_id = row['process_id']
            product_id = row['product_id']
            plan_date = row['plan_date']
            expected_qty = int(row['expected_qty'] or 0)

            backlog = LineBacklog.objects.filter(
                line_id=line_id,
                process_id=process_id,
                product_id=product_id,
                plan_date=plan_date,
                sequence_no=0,
            ).first()

            if backlog:
                current_qty = int(backlog.actual_qty or 0)
                if current_qty != expected_qty:
                    backlog.actual_qty = expected_qty
                    backlog.save(update_fields=['actual_qty'])
                    fixed_count += 1
                continue

            if expected_qty == 0:
                continue

            LineBacklog.objects.create(
                line_id=line_id,
                process_id=process_id,
                product_id=product_id,
                plan_date=plan_date,
                sequence_no=0,
                order_qty=0,
                plan_qty=0,
                actual_qty=expected_qty,
                stock_qty=0,
                planned_stock_qty=0,
                adjust_qty=0,
                scrap_qty=0,
                actual_shipment_qty=0,
            )
            fixed_count += 1

    return fixed_count


def _create_report_details(report, diff_rows, fixed=False):
    if not diff_rows:
        return
    details = [
        ProductionActualReconcileReportDetail(
            report=report,
            line_id=row['line_id'],
            process_id=row['process_id'],
            product_id=row['product_id'],
            plan_date=row['plan_date'],
            expected_qty=row['expected_qty'],
            backlog_qty=row['backlog_qty'],
            diff_qty=row['diff_qty'],
            fixed=fixed,
        )
        for row in diff_rows
    ]
    ProductionActualReconcileReportDetail.objects.bulk_create(details, batch_size=500)


def _notify_diff_if_needed(task_config, report):
    if not task_config or report.diff_count <= 0:
        return
    if not task_config.notify_users.exists():
        return

    notification = Notification.objects.create(
        title='[差分検知] 生産実績整合チェック',
        category='システム',
        domain='生産',
        description=(
            f'差分を検知しました。\n'
            f'レポートID: {report.id}\n'
            f'比較件数: {report.compared_count}件\n'
            f'差分件数: {report.diff_count}件\n'
            f'修正件数: {report.fixed_count}件\n'
            f'{report.message or ""}'
        ).strip(),
        valid_from=None,
        valid_to=datetime.now().date() + timedelta(days=7),
        operator_name='system',
    )
    notification.target_users.set(task_config.notify_users.all())


def run_production_actual_reconcile(task_config=None, apply_fix=False, created_by=None):
    mode = 'FIX' if apply_fix else 'CHECK'
    fixed_count = 0
    run_status = 'SUCCESS'
    message = ''

    try:
        result = collect_production_actual_reconcile_diffs()
        compared_count = int(result.get('compared_count', 0))
        diff_rows = list(result.get('diff_rows') or [])

        if apply_fix and diff_rows:
            fixed_count = _apply_reconcile_fix(diff_rows)

        if apply_fix:
            message = f'比較:{compared_count}件 差分:{len(diff_rows)}件 修正:{fixed_count}件'
        else:
            message = f'比較:{compared_count}件 差分:{len(diff_rows)}件'
    except Exception as exc:
        logger.exception('生産実績整合チェックに失敗')
        compared_count = 0
        diff_rows = []
        fixed_count = 0
        run_status = 'FAILED'
        message = f'実行中にエラーが発生しました: {exc}'

    report = ProductionActualReconcileReport.objects.create(
        task_config=task_config,
        mode=mode,
        status=run_status,
        compared_count=compared_count,
        diff_count=len(diff_rows),
        fixed_count=fixed_count,
        message=message,
        created_by=created_by if getattr(created_by, 'id', None) else None,
    )
    _create_report_details(report, diff_rows, fixed=(apply_fix and run_status == 'SUCCESS'))

    if run_status == 'SUCCESS' and not apply_fix:
        _notify_diff_if_needed(task_config, report)

    return {
        'report_id': report.id,
        'mode': mode,
        'status': run_status,
        'compared_count': report.compared_count,
        'diff_count': report.diff_count,
        'fixed_count': report.fixed_count,
        'message': report.message,
    }
