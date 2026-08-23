from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from masters.models import Process, Product, Supplier
from production.models_line_backlog import LineBacklog
from production.models_process_realtime import ProcessRealtimeRecord
from production.serializers_process_realtime import (
    _resolve_product_process_line,
    build_scrap_multiplier_details,
    resolve_workday_date_for_process,
)
from quality.models_scrap import ScrapRecord, ScrapRecordDetail


class ScrapServiceError(Exception):
    def __init__(self, detail, status_code=400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _require_scrap_record(record):
    if record.record_type != 'SCRAP':
        raise ScrapServiceError('SCRAP以外は対象外です。', status_code=400)
    sd = getattr(record, 'scrap_detail', None)
    if not sd:
        raise ScrapServiceError('対応する仕損記録がありません。', status_code=400)
    return sd


def get_scrap_breakdown(record):
    if record.record_type != 'SCRAP' or not record.product_id:
        return []

    details_qs = ScrapRecordDetail.objects.filter(scrap_record__process_record=record)
    if not details_qs.exists() and getattr(record, 'scrap_detail', None):
        qty = record.qty or 0
        gen_details = build_scrap_multiplier_details(record.product_id, qty)
        if gen_details:
            products = {
                p.id: p for p in Product.objects.filter(
                    id__in=[d['product_id'] for d in gen_details if d.get('product_id')]
                )
            }
            objs = []
            for d in gen_details:
                pid = d.get('product_id')
                prod = products.get(pid) if pid else None
                objs.append(ScrapRecordDetail(
                    scrap_record=record.scrap_detail,
                    product=prod,
                    product_code=prod.product_code if prod else None,
                    product_name=prod.product_name if prod else None,
                    process_id=d.get('process_id'),
                    line_id=d.get('line_id'),
                    supplier_id=d.get('supplier_id'),
                    sourcing_type=d.get('sourcing_type'),
                    deduct_qty=d.get('qty') or 0,
                ))
            ScrapRecordDetail.objects.bulk_create(objs)
            details_qs = ScrapRecordDetail.objects.filter(scrap_record__process_record=record)

    qty = record.qty or 0
    allowed_ids = {
        d.get('product_id')
        for d in build_scrap_multiplier_details(record.product_id, qty)
        if d.get('product_id')
    }
    if allowed_ids:
        details_qs = details_qs.filter(product_id__in=allowed_ids)

    aggregated = defaultdict(lambda: {
        'deduct_qty': Decimal('0'),
        'detail_ids': [],
        'is_replenished_list': [],
    })

    products = {p.id: p for p in Product.objects.filter(id__in=details_qs.values_list('product_id', flat=True))}
    processes = {p.id: p for p in Process.objects.filter(id__in=details_qs.values_list('process_id', flat=True))}
    suppliers = {s.id: s for s in Supplier.objects.filter(id__in=details_qs.values_list('supplier_id', flat=True))}

    for d in details_qs:
        key = (d.product_id, d.process_id, d.supplier_id)
        p = products.get(d.product_id)
        proc = processes.get(d.process_id) if d.process_id else None
        supplier = suppliers.get(d.supplier_id) if d.supplier_id else None

        if key not in aggregated:
            aggregated[key] = {
                'product_id': d.product_id,
                'product_code': d.product_code or (p.product_code if p else None),
                'product_name': d.product_name or (p.product_name if p else None),
                'process_id': d.process_id,
                'process_code': proc.process_code if proc else None,
                'process_name': proc.process_name if proc else None,
                'supplier_id': d.supplier_id,
                'supplier_code': supplier.supplier_code if supplier else None,
                'supplier_name': supplier.supplier_name if supplier else None,
                'sourcing_type': d.sourcing_type,
                'deduct_qty': Decimal('0'),
                'detail_ids': [],
                'is_replenished_list': [],
                'replenished_at': d.replenished_at,
                'replenished_by': d.replenished_by,
            }

        aggregated[key]['deduct_qty'] += (d.deduct_qty or Decimal('0'))
        aggregated[key]['detail_ids'].append(d.id)
        aggregated[key]['is_replenished_list'].append(d.is_replenished)

    details = []
    for item in aggregated.values():
        all_replenished = all(item['is_replenished_list']) if item['is_replenished_list'] else False
        details.append({
            'detail_id': item['detail_ids'][0],
            'product_id': item['product_id'],
            'product_code': item['product_code'],
            'product_name': item['product_name'],
            'deduct_qty': float(item['deduct_qty']),
            'process_id': item['process_id'],
            'process_code': item['process_code'],
            'process_name': item['process_name'],
            'supplier_id': item['supplier_id'],
            'supplier_code': item['supplier_code'],
            'supplier_name': item['supplier_name'],
            'sourcing_type': item['sourcing_type'],
            'is_replenished': all_replenished,
            'replenished_at': item['replenished_at'],
            'replenished_by': item['replenished_by'],
        })

    details.sort(key=lambda x: (x['product_code'] or '', x['product_id'] or 0))
    return details


def mark_scrap_replenished(record, user=None):
    sd = _require_scrap_record(record)

    sd.is_replenished = True
    sd.replenished_at = timezone.now()
    if user and getattr(user, 'is_authenticated', False):
        sd.replenished_by = getattr(user, 'username', None) or sd.replenished_by
    sd.save()
    ScrapRecordDetail.objects.filter(scrap_record=sd).update(
        is_replenished=True,
        replenished_at=sd.replenished_at,
        replenished_by=sd.replenished_by,
    )
    record.event_data = record.event_data or {}
    record.event_data['is_replenished'] = True
    record.save(update_fields=['event_data'])
    return {
        'scrap_record_id': sd.id,
        'is_replenished': sd.is_replenished,
        'replenished_at': sd.replenished_at,
        'replenished_by': sd.replenished_by,
    }


def mark_scrap_detail_replenished(record, detail_id, user=None):
    _require_scrap_record(record)
    if not detail_id:
        raise ScrapServiceError('detail_id is required', status_code=400)
    try:
        detail = ScrapRecordDetail.objects.get(id=detail_id, scrap_record__process_record=record)
    except ScrapRecordDetail.DoesNotExist as exc:
        raise ScrapServiceError('明細が見つかりません', status_code=404) from exc

    detail.is_replenished = True
    detail.replenished_at = timezone.now()
    if user and getattr(user, 'is_authenticated', False):
        detail.replenished_by = getattr(user, 'username', None) or detail.replenished_by
    detail.save()

    sd = getattr(record, 'scrap_detail', None)
    if sd:
        all_done = not ScrapRecordDetail.objects.filter(scrap_record=sd, is_replenished=False).exists()
        if all_done:
            sd.is_replenished = True
            sd.replenished_at = detail.replenished_at
            sd.replenished_by = detail.replenished_by
            sd.save()
            record.event_data = record.event_data or {}
            record.event_data['is_replenished'] = True
            record.save(update_fields=['event_data'])

    return {
        'detail_id': detail.id,
        'is_replenished': detail.is_replenished,
        'replenished_at': detail.replenished_at,
        'replenished_by': detail.replenished_by,
    }


def _build_return_details(return_record, product_id, qty):
    details = build_scrap_multiplier_details(product_id, -qty)
    if not details:
        return
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
            scrap_record=return_record,
            product=prod,
            product_code=prod.product_code if prod else None,
            product_name=prod.product_name if prod else None,
            process_id=d.get('process_id'),
            line_id=d.get('line_id'),
            supplier_id=d.get('supplier_id'),
            sourcing_type=d.get('sourcing_type'),
            deduct_qty=d.get('qty') or Decimal('0'),
            is_backlog_processed=True,
        ))
    ScrapRecordDetail.objects.bulk_create(objs)


def _restore_parent_backlog(sd, product_obj, return_date, qty_int):
    if not qty_int or not sd.line_id or not sd.process_id or not sd.product_id:
        return

    actual_process, actual_line = _resolve_product_process_line(product_obj, sd.process)
    is_self = actual_process and actual_process.id == (sd.process_id if sd.process_id else None)
    target_line_id = getattr(actual_line, 'id', sd.line_id)
    target_process_id = getattr(actual_process, 'id', sd.process_id)

    LineBacklog.objects.get_or_create(
        line_id=target_line_id,
        process_id=target_process_id,
        product_id=sd.product_id,
        plan_date=return_date,
        sequence_no=0,
        defaults={
            'order_qty': 0,
            'plan_qty': 0,
            'actual_qty': 0,
            'stock_qty': 0,
            'planned_stock_qty': 0,
            'adjust_qty': 0,
            'scrap_qty': 0,
            'scrap_adjust_qty': 0,
            'actual_shipment_qty': 0,
        },
    )

    backlog_filter = dict(
        line_id=target_line_id,
        process_id=target_process_id,
        product_id=sd.product_id,
        plan_date=return_date,
    )
    if is_self:
        LineBacklog.objects.filter(**backlog_filter).update(scrap_qty=F('scrap_qty') - qty_int)
        LineBacklog.objects.filter(**backlog_filter).update(actual_qty=F('actual_qty') + qty_int)
    else:
        LineBacklog.objects.filter(**backlog_filter).update(scrap_adjust_qty=F('scrap_adjust_qty') + qty_int)


def _restore_child_adjustments(product_id, qty, return_date):
    details_for_adjust = build_scrap_multiplier_details(product_id, qty)
    if not details_for_adjust:
        return

    for d in details_for_adjust:
        detail_line_id = d.get('line_id')
        detail_process_id = d.get('process_id')
        detail_product_id = d.get('product_id')
        detail_qty = d.get('qty') or Decimal('0')
        if not detail_line_id or not detail_process_id or not detail_product_id:
            continue
        if product_id and detail_product_id == product_id:
            continue
        qty_child = int(detail_qty or 0)
        if qty_child == 0:
            continue
        LineBacklog.objects.get_or_create(
            line_id=detail_line_id,
            process_id=detail_process_id,
            product_id=detail_product_id,
            plan_date=return_date,
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
        LineBacklog.objects.filter(
            line_id=detail_line_id,
            process_id=detail_process_id,
            product_id=detail_product_id,
            plan_date=return_date,
        ).update(
            adjust_qty=F('adjust_qty') + qty_child
        )


def _process_scrap_return(record, sd, qty_input, decided_by):
    try:
        qty = Decimal(str(qty_input))
    except (InvalidOperation, TypeError) as exc:
        raise ScrapServiceError('qty must be a valid number.', status_code=400) from exc
    if qty <= 0:
        raise ScrapServiceError('qty must be greater than 0.', status_code=400)

    product_id = record.product_id
    if not product_id and record.product_code:
        prod = Product.objects.filter(product_code=record.product_code).first()
        product_id = prod.id if prod else None
    product_obj = sd.product
    if not product_obj and product_id:
        product_obj = Product.objects.filter(id=product_id).first()
    if not product_id:
        raise ScrapServiceError('製品が未設定のため在庫戻しができません。', status_code=400)

    current_return = sd.return_qty or Decimal('0')
    scrap_qty = sd.qty or Decimal('0')
    new_return = current_return + qty
    if new_return > scrap_qty:
        raise ScrapServiceError('戻し数量が仕損数量を超えています。', status_code=400)

    now = timezone.now()
    if timezone.is_aware(now):
        now = timezone.localtime(now).replace(tzinfo=None)
    ref_process = sd.process or sd.occurrence_process
    return_date = resolve_workday_date_for_process(ref_process, now)
    return_record = ScrapRecord.objects.create(
        process=sd.process,
        occurrence_process=sd.occurrence_process or sd.process,
        line=sd.line,
        product=product_obj,
        product_code=sd.product_code,
        product_name=sd.product_name,
        event_type='RETURN',
        qty=-qty,
        plan_date=return_date,
        reason=sd.reason or '',
        reason_detail=sd.reason_detail or '',
        batch_no=sd.batch_no or '',
        operator_name=sd.operator_name or '',
        remarks=sd.remarks or '',
        return_for=sd,
        disposition_status='APPROVED',
        decided_at=timezone.now(),
        decided_by=decided_by,
    )

    _build_return_details(return_record, product_id, qty)

    sd.return_qty = new_return
    sd.disposition_status = 'APPROVED' if new_return == scrap_qty else 'PARTIAL'
    sd.decided_at = timezone.now()
    if decided_by:
        sd.decided_by = decided_by
    sd.save()

    qty_int = int(qty)
    _restore_parent_backlog(sd, product_obj, return_date, qty_int)
    _restore_child_adjustments(product_id, qty, return_date)


def _confirm_scrap(sd, decided_by):
    if (sd.return_qty or Decimal('0')) > 0:
        sd.disposition_status = 'PARTIAL'
    else:
        sd.disposition_status = 'REJECTED'
    sd.decided_at = timezone.now()
    if decided_by:
        sd.decided_by = decided_by
    sd.save()


def process_scrap_disposition(record, action, qty_input=None, decided_by=None):
    sd = _require_scrap_record(record)
    normalized_action = str(action or '').strip().upper()
    if normalized_action not in ('RETURN', 'CONFIRM_SCRAP'):
        raise ScrapServiceError('action is required (RETURN or CONFIRM_SCRAP)', status_code=400)

    with transaction.atomic():
        if normalized_action == 'RETURN':
            _process_scrap_return(record, sd, qty_input, decided_by)
        else:
            _confirm_scrap(sd, decided_by)

    return {
        'scrap_record_id': sd.id,
        'disposition_status': sd.disposition_status,
        'return_qty': sd.return_qty,
        'decided_at': sd.decided_at,
        'decided_by': sd.decided_by,
    }
