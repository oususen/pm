from decimal import Decimal

from production.models_process_realtime import ProcessRealtimeRecord
from production.models_process_work_session import ProcessWorkSession
from production.models_process_work_session_equipment import ProcessWorkSessionEquipment
from production.serializers_process_realtime import (
    SESSION_ACTIONS,
    _sync_record_session_meta,
    apply_operator_action_session,
)
from masters.models import Process, Product


def _resolve_target_session_for_equipment(*, explicit_session, process, product, plan_date):
    if explicit_session:
        return explicit_session
    if not process or not product or not plan_date:
        return None

    open_session = ProcessWorkSession.objects.filter(
        process=process,
        product=product,
        plan_date=plan_date,
        status='OPEN',
    ).order_by('-started_at', '-id').first()
    if open_session:
        return open_session

    return ProcessWorkSession.objects.filter(
        process=process,
        product=product,
        plan_date=plan_date,
    ).order_by('-started_at', '-id').first()


def _attach_equipment_to_session(*, session, equipment_id, sync_session):
    if not session or not equipment_id:
        return
    role = ProcessWorkSessionEquipment.ROLE_PRIMARY if sync_session else ProcessWorkSessionEquipment.ROLE_SUB
    obj, created = ProcessWorkSessionEquipment.objects.get_or_create(
        session=session,
        equipment_id=equipment_id,
        defaults={'role': role},
    )
    if not created and role == ProcessWorkSessionEquipment.ROLE_PRIMARY and obj.role != role:
        obj.role = role
        obj.save(update_fields=['role', 'updated_at'])


def sync_brake_spot_action_to_process_session(
    *,
    process_id,
    product_id,
    product_code,
    product_name,
    operator_action,
    operator_action_reason,
    qty,
    operator_name,
    plan_date,
    line_id=None,
    equipment_id=None,
    source='',
    source_record_id=None,
    sync_session=True,
):
    """
    ブレーキ/スポットの作業アクションを ProcessRealtimeRecord と
    ProcessWorkSession へ同期する。
    """
    action = str(operator_action or '').upper()
    qty_decimal = Decimal(str(qty or 0))
    process = Process.objects.filter(id=process_id).first()
    if not process:
        return None, None

    product = Product.objects.filter(id=product_id).first() if product_id else None
    resolved_product_code = (product.product_code if product else (product_code or '')).strip()
    resolved_product_name = (product.product_name if product else (product_name or '')).strip()

    event_data = {
        'action': action,
        'operator_action_reason': str(operator_action_reason or ''),
        'source': str(source or ''),
        'line_id': line_id,
        'equipment_id': equipment_id,
        'source_record_id': source_record_id,
    }

    action_record = ProcessRealtimeRecord.objects.create(
        process=process,
        product=product,
        product_code=resolved_product_code or None,
        product_name=resolved_product_name or None,
        record_type='OPERATOR_ACTION',
        qty=qty_decimal,
        operator_name=str(operator_name or ''),
        event_data=event_data,
    )

    session = None
    if sync_session and product and action in SESSION_ACTIONS:
        production_qty = qty_decimal if action in ('END', 'PAUSE') else Decimal('0')
        session, issues = apply_operator_action_session(
            process=process,
            product=product,
            action=action,
            action_record=action_record,
            plan_date=plan_date,
            production_qty=production_qty,
        )
        _sync_record_session_meta(action_record, session, issues)

    target_session = _resolve_target_session_for_equipment(
        explicit_session=session,
        process=process,
        product=product,
        plan_date=plan_date,
    )
    _attach_equipment_to_session(
        session=target_session,
        equipment_id=equipment_id,
        sync_session=sync_session,
    )
    return action_record, session
