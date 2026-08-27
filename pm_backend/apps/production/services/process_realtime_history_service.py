from django.utils import timezone

from production.models_process_work_session_change_history import ProcessWorkSessionChangeHistory


def _to_local_naive(dt):
    if not dt:
        return None
    if timezone.is_aware(dt):
        return timezone.localtime(dt).replace(tzinfo=None)
    return dt


def _format_history_datetime(dt):
    if not dt:
        return ''
    local_dt = _to_local_naive(dt)
    return local_dt.strftime('%Y/%m/%d %H:%M') if local_dt else ''


def serialize_session_snapshot(session_obj):
    if not session_obj:
        return {}
    return {
        'product_code': session_obj.product_code or '',
        'product_name': session_obj.product_name or '',
        'started_at': _format_history_datetime(session_obj.started_at),
        'ended_at': _format_history_datetime(session_obj.ended_at),
        'production_qty': int(session_obj.production_qty or 0),
        'defect_qty': int(session_obj.defect_qty or 0),
        'operator_name': session_obj.operator_name or '',
        'plan_date': str(session_obj.plan_date) if session_obj.plan_date else '',
    }


def _history_display_value(value):
    text = str(value or '').strip()
    return text or '—'


def build_history_summary(operation_type, before_data, after_data):
    normalized_type = str(operation_type or '').upper()

    if normalized_type == 'ADD':
        parts = []
        if after_data.get('product_code'):
            parts.append(f"品番: {after_data['product_code']}")
        if after_data.get('product_name'):
            parts.append(f"品名: {after_data['product_name']}")
        if after_data.get('plan_date'):
            parts.append(f"作業日: {after_data['plan_date']}")
        if after_data.get('operator_name'):
            parts.append(f"作業者: {after_data['operator_name']}")
        if after_data.get('started_at'):
            parts.append(f"開始時刻: {after_data['started_at']}")
        if after_data.get('ended_at'):
            parts.append(f"終了時刻: {after_data['ended_at']}")
        parts.append(f"実績数量: {after_data.get('production_qty', 0)}")
        if int(after_data.get('defect_qty', 0) or 0):
            parts.append(f"仕損: {after_data.get('defect_qty', 0)}")
        return ' / '.join(parts)

    if normalized_type == 'DELETE':
        parts = []
        if before_data.get('product_code'):
            parts.append(f"品番: {before_data['product_code']}")
        if before_data.get('product_name'):
            parts.append(f"品名: {before_data['product_name']}")
        if before_data.get('plan_date'):
            parts.append(f"作業日: {before_data['plan_date']}")
        if before_data.get('operator_name'):
            parts.append(f"作業者: {before_data['operator_name']}")
        if before_data.get('started_at'):
            parts.append(f"開始時刻: {before_data['started_at']}")
        if before_data.get('ended_at'):
            parts.append(f"終了時刻: {before_data['ended_at']}")
        parts.append(f"実績数量: {before_data.get('production_qty', 0)}")
        if int(before_data.get('defect_qty', 0) or 0):
            parts.append(f"仕損: {before_data.get('defect_qty', 0)}")
        return '削除: ' + ' / '.join(parts)

    labels = {
        'product_code': '品番',
        'product_name': '品名',
        'plan_date': '作業日',
        'started_at': '開始時刻',
        'ended_at': '終了時刻',
        'production_qty': '実績数量',
        'defect_qty': '仕損',
        'operator_name': '作業者',
    }
    parts = []
    for key, label in labels.items():
        before_value = before_data.get(key)
        after_value = after_data.get(key)
        if str(before_value or '') == str(after_value or ''):
            continue
        parts.append(f'{label}: {_history_display_value(before_value)} → {_history_display_value(after_value)}')
    return ' / '.join(parts) or '変更なし'


def create_session_change_history(*, session_obj, operation_type, reason, changed_by, before_data=None, after_data=None):
    if not session_obj:
        return None
    before_payload = before_data or {}
    after_payload = after_data or {}
    return ProcessWorkSessionChangeHistory.objects.create(
        session=session_obj,
        session_record_id=session_obj.id,
        operation_type=str(operation_type or '').upper(),
        process=session_obj.process,
        product=session_obj.product,
        product_code=session_obj.product_code or '',
        product_name=session_obj.product_name or '',
        plan_date=session_obj.plan_date,
        reason=str(reason or '').strip(),
        change_summary=build_history_summary(operation_type, before_payload, after_payload),
        before_data=before_payload,
        after_data=after_payload,
        changed_by=changed_by,
    )


def create_record_change_history(
    *,
    session_record_id,
    operation_type,
    reason,
    changed_by,
    process=None,
    product=None,
    product_code='',
    product_name='',
    plan_date=None,
    before_data=None,
    after_data=None,
):
    before_payload = before_data or {}
    after_payload = after_data or {}
    return ProcessWorkSessionChangeHistory.objects.create(
        session=None,
        session_record_id=session_record_id,
        operation_type=str(operation_type or '').upper(),
        process=process,
        product=product,
        product_code=str(product_code or '').strip(),
        product_name=str(product_name or '').strip(),
        plan_date=plan_date,
        reason=str(reason or '').strip(),
        change_summary=build_history_summary(operation_type, before_payload, after_payload),
        before_data=before_payload,
        after_data=after_payload,
        changed_by=changed_by,
    )
