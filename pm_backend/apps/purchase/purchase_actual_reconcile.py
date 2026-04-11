from collections import defaultdict
from datetime import date, datetime, timedelta
import logging

from django.db import transaction

from masters.models import Line, Process, Product, Supplier
from notifications.models import Notification
from production.models_line_backlog import LineBacklog
from production.models_process_realtime import ProcessRealtimeRecord
from production.models_purchase_actual_reconcile import (
    PurchaseActualReconcileReport,
    PurchaseActualReconcileReportDetail,
)

logger = logging.getLogger(__name__)


def _to_int_or_none(value):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_purchase_actual_date(date_text, fallback_date):
    text = str(date_text or '').strip()
    if not text:
        return fallback_date
    try:
        return date.fromisoformat(text.replace('/', '-'))
    except ValueError:
        return fallback_date


def _resolve_purchase_line_id_from_supplier(supplier_id):
    sid = _to_int_or_none(supplier_id)
    if not sid:
        return None
    supplier = Supplier.objects.filter(id=sid).first()
    if not supplier:
        return None
    line = (
        Line.objects.filter(line_code=supplier.supplier_code).first()
        or Line.objects.filter(line_name__icontains=str(supplier.supplier_name or '').strip()).first()
    )
    return line.id if line else None


def _resolve_purchase_record_line_id(record):
    event = record.event_data or {}
    line_id = _to_int_or_none(event.get('line_id'))
    if line_id:
        return line_id
    supplier_line_id = _resolve_purchase_line_id_from_supplier(event.get('supplier_id'))
    if supplier_line_id:
        return supplier_line_id
    return getattr(record.process, 'line_id', None)


def _resolve_purchase_record_target_date(record):
    event = record.event_data or {}
    arrival_text = (event.get('arrival_date') or '').strip()
    return _parse_purchase_actual_date(arrival_text, record.timestamp.date())


def collect_purchase_actual_reconcile_diffs():
    expected_by_key = defaultdict(int)
    rec_qs = (
        ProcessRealtimeRecord.objects.filter(
            record_type='PRODUCTION',
            event_data__source='PURCHASE_ACTUAL_INPUT',
        )
        .select_related('process')
        .only('id', 'process_id', 'product_id', 'qty', 'timestamp', 'event_data', 'process__line_id')
    )
    for rec in rec_qs.iterator():
        if not rec.process_id or not rec.product_id:
            continue
        line_id = _to_int_or_none(_resolve_purchase_record_line_id(rec))
        if not line_id:
            continue
        target_date = _resolve_purchase_record_target_date(rec)
        key = (line_id, int(rec.process_id), int(rec.product_id), target_date)
        expected_by_key[key] += int(rec.qty or 0)

    backlog_by_key = {}
    backlog_qs = (
        LineBacklog.objects.filter(
            sequence_no=0,
            line__line_type='PURCHASE',
        )
        .exclude(actual_qty=0)
        .only('id', 'line_id', 'process_id', 'product_id', 'plan_date', 'actual_qty')
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
    affected_dates_by_product = defaultdict(set)

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
                    affected_dates_by_product[product_id].add(plan_date)
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
            affected_dates_by_product[product_id].add(plan_date)

    if affected_dates_by_product:
        try:
            from purchase.views import _recalculate_purchase_child_stock

            for product_id, dates in affected_dates_by_product.items():
                _recalculate_purchase_child_stock(product_id, sorted(dates))
        except Exception as exc:
            logger.warning('納入実績整合修正後の子部品在庫再計算に失敗: %s', exc)

    return fixed_count


def _create_report_details(report, diff_rows, fixed=False):
    if not diff_rows:
        return
    details = [
        PurchaseActualReconcileReportDetail(
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
    PurchaseActualReconcileReportDetail.objects.bulk_create(details, batch_size=500)


def _notify_diff_if_needed(task_config, report):
    if not task_config or report.diff_count <= 0:
        return
    if not task_config.notify_users.exists():
        return

    title = '[差分検知] 納入実績整合チェック'
    description = (
        f'差分を検知しました。\n'
        f'レポートID: {report.id}\n'
        f'比較件数: {report.compared_count}件\n'
        f'差分件数: {report.diff_count}件\n'
        f'修正件数: {report.fixed_count}件\n'
        f'{report.message or ""}'
    )
    notification = Notification.objects.create(
        title=title,
        category='システム',
        domain='購買',
        description=description.strip(),
        valid_from=None,
        valid_to=datetime.now().date() + timedelta(days=7),
        operator_name='system',
    )
    notification.target_users.set(task_config.notify_users.all())


def run_purchase_actual_reconcile(task_config=None, apply_fix=False, created_by=None):
    mode = 'FIX' if apply_fix else 'CHECK'
    fixed_count = 0
    status = 'SUCCESS'
    message = ''

    try:
        result = collect_purchase_actual_reconcile_diffs()
        compared_count = int(result.get('compared_count', 0))
        diff_rows = list(result.get('diff_rows') or [])

        if apply_fix and diff_rows:
            fixed_count = _apply_reconcile_fix(diff_rows)

        if apply_fix:
            message = (
                f'比較:{compared_count}件 差分:{len(diff_rows)}件 '
                f'修正:{fixed_count}件'
            )
        else:
            message = f'比較:{compared_count}件 差分:{len(diff_rows)}件'

    except Exception as exc:
        logger.exception('納入実績整合チェックに失敗')
        compared_count = 0
        diff_rows = []
        fixed_count = 0
        status = 'FAILED'
        message = f'実行中にエラーが発生しました: {exc}'

    report = PurchaseActualReconcileReport.objects.create(
        task_config=task_config,
        mode=mode,
        status=status,
        compared_count=compared_count,
        diff_count=len(diff_rows),
        fixed_count=fixed_count,
        message=message,
        created_by=created_by if getattr(created_by, 'id', None) else None,
    )
    _create_report_details(report, diff_rows, fixed=(apply_fix and status == 'SUCCESS'))

    if status == 'SUCCESS' and not apply_fix:
        _notify_diff_if_needed(task_config, report)

    return {
        'report_id': report.id,
        'mode': mode,
        'status': status,
        'compared_count': report.compared_count,
        'diff_count': report.diff_count,
        'fixed_count': report.fixed_count,
        'message': report.message,
    }
