from decimal import Decimal

from production.models_brake_line_record import BrakeLineRecord
from production.models_process_realtime import ProcessRealtimeRecord
from production.models_process_work_session import ProcessWorkSession
from production.models_process_work_session_equipment import ProcessWorkSessionEquipment
from production.serializers_process_realtime import (
    SESSION_ACTIONS,
    _sync_record_session_meta,
    apply_operator_action_session,
    build_worker_display_name,
)
from masters.models import Process, Product

BRAKE_SPOT_LOGIN_REQUIRED_MESSAGE = 'ブレーキ・スポットの記録にはログインが必要です。'
BRAKE_SPOT_REASON_CODE_REQUIRED_MESSAGE = '中断・強制終了には理由コードの選択が必要です。'


def resolve_brake_spot_operator(request):
    """
    ブレーキ・スポットの作業者を request.user から決める。
    未ログイン、または username が空なら None。
    それ以外は (名前, ログインID, ユーザー) の組を返す。
    """
    user = getattr(request, 'user', None)
    if user is None or not getattr(user, 'is_authenticated', False):
        return None
    username = str(getattr(user, 'username', '') or '').strip()
    if not username:
        return None
    return build_worker_display_name(user), user.username, user


def validate_interruption_reason_code(operator_action, reason_code):
    """
    PAUSE/TEMP_END のときだけ理由コードを検証する。
    有効なら True、無効なら False を返す（呼び出し側で400にする）。
    START/END/RESUME等では常に True（検証不要）。
    """
    if operator_action not in ('PAUSE', 'TEMP_END'):
        return True
    if not reason_code:
        return False
    from masters.models import InterruptionReason
    return InterruptionReason.objects.filter(
        code=reason_code,
        line_category='2',
        operation=operator_action,
        is_active=True,
    ).exists()


ACTIVE_BRAKE_SPOT_ACTIONS = {
    BrakeLineRecord.OPERATOR_ACTION_START,
    BrakeLineRecord.OPERATOR_ACTION_RESUME,
    BrakeLineRecord.OPERATOR_ACTION_PAUSE,
}


def find_equipment_active_product_conflict(*, equipment_id, product_id=None, product_code=''):
    """
    同一設備の最新状態が未終了（START/RESUME/PAUSE）なら該当レコードを返す。
    同じ製品でも別製品でもブロック対象。
    """
    if not equipment_id:
        return None

    latest_record = (
        BrakeLineRecord.objects
        .filter(equipment_id=equipment_id)
        .select_related('equipment', 'product')
        .order_by('-recorded_at', '-id')
        .first()
    )
    if not latest_record:
        return None

    latest_action = str(latest_record.operator_action or '').upper()
    if latest_action not in ACTIVE_BRAKE_SPOT_ACTIONS:
        return None

    return latest_record


def lock_and_reject_duplicate_operator_action(
    *,
    line_id,
    process_id,
    product_id=None,
    product_code='',
    equipment_id=None,
    operator_action,
):
    """同一の作業アクションを連続登録しないため、直前レコードを行ロックして確認する。"""
    queryset = BrakeLineRecord.objects.select_for_update().filter(
        line_id=line_id,
        process_id=process_id,
        equipment_id=equipment_id or None,
    )
    if product_id:
        queryset = queryset.filter(product_id=product_id)
    else:
        queryset = queryset.filter(product__isnull=True, product_code=product_code)

    latest_record = queryset.order_by('-recorded_at', '-id').first()
    if not latest_record:
        return None

    action = str(operator_action or '').upper()
    if latest_record.operator_action == action:
        return latest_record
    return None


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
