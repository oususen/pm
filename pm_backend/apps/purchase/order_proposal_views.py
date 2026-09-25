import math
import re
from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Max, Q
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Table, TableStyle
from reportlab.pdfgen import canvas
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.approval_views import _frontend_base_url
from accounts.models import ApprovalRouteConfig
from accounts.role_utils import build_chief_role_q, build_leader_role_q, build_supervisor_role_q
from masters.models import BOMItem, Calendar, Line, Process, Product, Supplier
from notifications.models import Notification
from orders.utils.calendar_utils import WorkingDayCalculator, get_business_today
from production.models_line_backlog import LineBacklog
from production.models_production import StockAllocation
from production.models_production_lock import ProductionLock
from shipping.services.email_service import EmailService

from .process_resolver import resolve_purchase_line, resolve_supplier_process
from .models import (
    PurchaseOrderProposal,
    PurchaseOrderProposalEmailConfig,
    PurchaseOrderProposalApproval,
    PurchaseOrderProposalLine,
    PurchaseOrderTask,
    SupplierOrderPattern,
    SupplierOrderSchedule,
)
from .serializers import (
    PurchaseOrderProposalDetailSerializer,
    PurchaseOrderProposalEmailConfigSerializer,
    PurchaseOrderProposalLineSerializer,
    PurchaseOrderProposalListSerializer,
    PurchaseOrderTaskSerializer,
    SupplierOrderPatternSerializer,
    SupplierOrderScheduleSerializer,
)


DEFAULT_APPROVAL_LEVELS = [
    (1, '業務員'),
    (2, '班長'),
    (3, '係長'),
    (4, '事業部長'),
]

TASK_TYPE_BY_APPROVAL_LEVEL = {
    1: PurchaseOrderTask.TASK_CREATE_PROPOSAL,
    2: PurchaseOrderTask.TASK_APPROVE_L2,
    3: PurchaseOrderTask.TASK_APPROVE_L3,
    4: PurchaseOrderTask.TASK_APPROVE_L4,
}

STATUS_TO_APPROVAL_LEVEL = {
    PurchaseOrderProposal.STATUS_DRAFT: 1,
    PurchaseOrderProposal.STATUS_SUBMITTED: 2,
    PurchaseOrderProposal.STATUS_APPROVED_L2: 3,
    PurchaseOrderProposal.STATUS_APPROVED_L3: 4,
    PurchaseOrderProposal.STATUS_APPROVED: 4,
}

APPROVAL_TRANSITION = {
    PurchaseOrderProposal.STATUS_SUBMITTED: {
        'level': 2,
        'next_status': PurchaseOrderProposal.STATUS_APPROVED_L2,
        'next_level': 3,
        'next_task_type': PurchaseOrderTask.TASK_APPROVE_L3,
    },
    PurchaseOrderProposal.STATUS_APPROVED_L2: {
        'level': 3,
        'next_status': PurchaseOrderProposal.STATUS_APPROVED_L3,
        'next_level': 4,
        'next_task_type': PurchaseOrderTask.TASK_APPROVE_L4,
    },
    PurchaseOrderProposal.STATUS_APPROVED_L3: {
        'level': 4,
        'next_status': PurchaseOrderProposal.STATUS_APPROVED,
        'next_level': None,
        'next_task_type': PurchaseOrderTask.TASK_CREATE_ORDER_PDF,
    },
}

AUTO_FILL_SOURCE_PROGRESS = 'PROGRESS'
AUTO_FILL_SOURCE_PLANNED_STOCK = 'PLANNED_STOCK'
AUTO_FILL_SOURCE_PLANNED_PROGRESS = 'PLANNED_PROGRESS'
AUTO_FILL_SOURCE_DEFAULT = AUTO_FILL_SOURCE_PLANNED_STOCK

PURCHASE_ORDER_PDF_FONT = 'HeiseiKakuGo-W5'
PURCHASE_ORDER_PROPOSAL_APPROVAL_ITEM_KEY = 'purchase_order_proposal'

APPROVAL_LEVEL_TO_ROUTE_STAGE = {
    1: 'creator',
    2: 'reviewer1',
    3: 'reviewer2',
    4: 'approver',
}

APPROVAL_STAGE_LABELS = {
    'creator': '業務員',
    'reviewer1': '班長',
    'reviewer2': '係長',
    'approver': '事業部長',
}


def _get_purchase_order_proposal_route() -> ApprovalRouteConfig:
    route = ApprovalRouteConfig.objects.filter(
        item_key=PURCHASE_ORDER_PROPOSAL_APPROVAL_ITEM_KEY,
        is_active=True,
    ).first()
    if not route:
        raise ValueError('承認設定に「外作・購入品注文」がありません。')
    return route


def _get_user_profile(user):
    if not user or not getattr(user, 'id', None):
        return None
    try:
        return user.profile
    except ObjectDoesNotExist:
        return None


_DEPT_LEVEL_TO_PROFILE_FIELD = {
    'division': 'profile__division',
    'group': 'profile__group',
    'team': 'profile__team',
    'unit': 'profile__department',
}


def _resolve_route_stage_users(route_config: ApprovalRouteConfig, stage: str, creator=None):
    authorized_users = list(route_config.creator_authorized_users.all()) if stage == 'creator' else []
    allowed_users = list(getattr(route_config, f'{stage}_allowed_users').all())
    if allowed_users:
        return list({user.id: user for user in allowed_users + authorized_users if getattr(user, 'id', None)}.values())

    role = getattr(route_config, f'{stage}_role', '')
    user_qs = get_user_model().objects.filter(is_active=True)

    dept = getattr(route_config, f'{stage}_department', None)
    if dept:
        field = _DEPT_LEVEL_TO_PROFILE_FIELD.get(dept.level)
        if field and role:
            users = list(user_qs.filter(**{field: dept, 'profile__role': role}).distinct())
            return list({user.id: user for user in users + authorized_users if getattr(user, 'id', None)}.values())
        if field:
            users = list(user_qs.filter(**{field: dept}).distinct())
            return list({user.id: user for user in users + authorized_users if getattr(user, 'id', None)}.values())

    profile = _get_user_profile(creator)

    if profile:
        if role == 'leader' and getattr(profile, 'unit_id', None):
            users = list(user_qs.filter(build_leader_role_q(profile.unit_id)).distinct())
            return list({user.id: user for user in users + authorized_users if getattr(user, 'id', None)}.values())
        if role == 'supervisor' and getattr(profile, 'team_id', None):
            users = list(user_qs.filter(build_supervisor_role_q(profile.team_id)).distinct())
            return list({user.id: user for user in users + authorized_users if getattr(user, 'id', None)}.values())
        if role == 'chief' and getattr(profile, 'group_id', None):
            users = list(user_qs.filter(build_chief_role_q(profile.group_id)).distinct())
            return list({user.id: user for user in users + authorized_users if getattr(user, 'id', None)}.values())
        if role == 'manager' and getattr(profile, 'division_id', None):
            users = list(user_qs.filter(profile__role='manager', profile__division_id=profile.division_id).distinct())
            return list({user.id: user for user in users + authorized_users if getattr(user, 'id', None)}.values())
        if role in ('office_staff', 'staff'):
            users = list(user_qs.filter(profile__role=role).distinct())
            return list({user.id: user for user in users + authorized_users if getattr(user, 'id', None)}.values())
        return authorized_users

    if role:
        users = list(user_qs.filter(profile__role=role).distinct())
        return list({user.id: user for user in users + authorized_users if getattr(user, 'id', None)}.values())
    return authorized_users


def _get_route_proxy_users(route_config: ApprovalRouteConfig, stage: str):
    return list(getattr(route_config, f'{stage}_proxy_users').all())


def _resolve_purchase_approval_users(route_config: ApprovalRouteConfig, level: int, proposal: PurchaseOrderProposal):
    stage = APPROVAL_LEVEL_TO_ROUTE_STAGE.get(int(level))
    if not stage:
        return []
    users = _resolve_route_stage_users(route_config, stage, creator=proposal.created_by)
    users.extend(_get_route_proxy_users(route_config, stage))
    return list({user.id: user for user in users if getattr(user, 'id', None)}.values())


def _route_stage_task_enabled(route_config: ApprovalRouteConfig, level: int):
    stage = APPROVAL_LEVEL_TO_ROUTE_STAGE.get(int(level))
    if not stage:
        return False
    if stage == 'reviewer2' and not route_config.reviewer2_enabled:
        return False
    return getattr(route_config, f'{stage}_task_enabled', True)


def _route_stage_app_notification_enabled(route_config: ApprovalRouteConfig, level: int):
    stage = APPROVAL_LEVEL_TO_ROUTE_STAGE.get(int(level))
    if not stage:
        return False
    if stage == 'reviewer2' and not route_config.reviewer2_enabled:
        return False
    return getattr(route_config, f'{stage}_app_notification_enabled', True)


def _route_stage_email_notification_enabled(route_config: ApprovalRouteConfig, level: int):
    stage = APPROVAL_LEVEL_TO_ROUTE_STAGE.get(int(level))
    if not stage:
        return False
    if stage == 'reviewer2' and not route_config.reviewer2_enabled:
        return False
    return getattr(route_config, f'{stage}_email_notification_enabled', False)


def _get_purchase_approval_result_users(route_config: ApprovalRouteConfig, proposal: PurchaseOrderProposal):
    users = []
    if proposal.created_by_id:
        users.append(proposal.created_by)
    for level in (2, 3, 4):
        if level == 3 and not route_config.reviewer2_enabled:
            continue
        users.extend(_resolve_purchase_approval_users(route_config, level, proposal))
    return list({user.id: user for user in users if getattr(user, 'id', None)}.values())


def _send_purchase_approval_stage_email(
    route_config: ApprovalRouteConfig,
    level: int,
    proposal: PurchaseOrderProposal,
    users,
    operator_user,
    request=None,
):
    if not users or not _route_stage_email_notification_enabled(route_config, level):
        return
    emails = sorted({user.email for user in users if getattr(user, 'email', '')})
    if not emails:
        return

    stage = APPROVAL_LEVEL_TO_ROUTE_STAGE.get(int(level))
    stage_label = APPROVAL_STAGE_LABELS.get(stage, '承認')
    operator_name = _display_user_name(operator_user)
    supplier_name = getattr(getattr(proposal, 'supplier', None), 'supplier_name', '') or ''
    base_url = _frontend_base_url(request)
    link = f'{base_url}/purchase/order-proposals/{proposal.pk}' if base_url else ''
    body_lines = [
        f'{operator_name}さんから外作・購入品注文書の{stage_label}依頼があります。',
        '',
        f'注文書番号: {proposal.proposal_no}',
        f'仕入先: {supplier_name}',
        f'発注日: {proposal.order_date}',
        f'希望納入日: {proposal.desired_delivery_date}',
    ]
    if link:
        body_lines.extend(['', '確認リンク:', link])
    EmailService().send_plain_email(
        to_emails=emails,
        subject=f'[外作・購入品注文] {stage_label}依頼: {proposal.proposal_no}',
        body='\n'.join(body_lines),
        user_id=getattr(operator_user, 'id', None),
    )


def _send_purchase_approval_result_email(
    route_config: ApprovalRouteConfig,
    proposal: PurchaseOrderProposal,
    users,
    operator_user,
    request=None,
):
    if not users or not route_config.approved_result_email_notification_enabled:
        return
    emails = sorted({user.email for user in users if getattr(user, 'email', '')})
    if not emails:
        return

    operator_name = _display_user_name(operator_user)
    supplier_name = getattr(getattr(proposal, 'supplier', None), 'supplier_name', '') or ''
    base_url = _frontend_base_url(request)
    link = f'{base_url}/purchase/order-proposals/{proposal.pk}' if base_url else ''
    body_lines = [
        f'{operator_name}さんが外作・購入品注文書を最終承認しました。',
        '注文書作成を行ってください。',
        '',
        f'注文書番号: {proposal.proposal_no}',
        f'仕入先: {supplier_name}',
        f'発注日: {proposal.order_date}',
        f'希望納入日: {proposal.desired_delivery_date}',
    ]
    if link:
        body_lines.extend(['', '確認リンク:', link])
    EmailService().send_plain_email(
        to_emails=emails,
        subject=f'[外作・購入品注文] 承認完了: {proposal.proposal_no}',
        body='\n'.join(body_lines),
        user_id=getattr(operator_user, 'id', None),
    )


def _send_purchase_rejection_email(
    route_config: ApprovalRouteConfig,
    proposal: PurchaseOrderProposal,
    users,
    operator_user,
    comment: str = '',
    request=None,
):
    if not users or not route_config.rejected_result_email_notification_enabled:
        return
    emails = sorted({user.email for user in users if getattr(user, 'email', '')})
    if not emails:
        return

    operator_name = _display_user_name(operator_user)
    supplier_name = getattr(getattr(proposal, 'supplier', None), 'supplier_name', '') or ''
    base_url = _frontend_base_url(request)
    link = f'{base_url}/purchase/order-proposals/{proposal.pk}' if base_url else ''
    body_lines = [
        f'{operator_name}さんが外作・購入品注文書を差戻しました。',
        '',
        f'注文書番号: {proposal.proposal_no}',
        f'仕入先: {supplier_name}',
        f'発注日: {proposal.order_date}',
        f'希望納入日: {proposal.desired_delivery_date}',
    ]
    if comment:
        body_lines.extend(['', f'差戻理由: {comment}'])
    if link:
        body_lines.extend(['', '確認リンク:', link])
    EmailService().send_plain_email(
        to_emails=emails,
        subject=f'[外作・購入品注文] 差戻: {proposal.proposal_no}',
        body='\n'.join(body_lines),
        user_id=getattr(operator_user, 'id', None),
    )


def _proposal_no_prefix(target_date: date) -> str:
    return f'POP{target_date.strftime("%Y%m%d")}'


def _generate_proposal_no(target_date: date) -> str:
    prefix = _proposal_no_prefix(target_date)
    last = (
        PurchaseOrderProposal.objects.select_for_update()
        .filter(proposal_no__startswith=prefix)
        .order_by('-proposal_no')
        .first()
    )
    seq = 1
    if last and isinstance(last.proposal_no, str):
        tail = last.proposal_no.split('-')[-1]
        if tail.isdigit():
            seq = int(tail) + 1
    return f'{prefix}-{seq:04d}'


def _coerce_date(value, field_name='date'):
    if isinstance(value, date):
        return value
    if not value:
        raise ValueError(f'{field_name} is required')
    try:
        return date.fromisoformat(str(value).replace('/', '-'))
    except ValueError as exc:
        raise ValueError(f'{field_name} must be YYYY-MM-DD') from exc


def _get_daiso_calendar():
    return (
        Calendar.objects.filter(Q(calendar_code__iexact='daiso') | Q(calendar_name__icontains='ダイソウ'))
        .order_by('id')
        .first()
    )


def _shift_to_previous_working_day(target_date: date, calculator: WorkingDayCalculator) -> date:
    shifted = target_date
    while not calculator.is_working_day(shifted):
        shifted = shifted - timedelta(days=1)
    return shifted


def _iter_month_starts(start_date: date, end_date: date):
    current = date(start_date.year, start_date.month, 1)
    while current <= end_date:
        yield current
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)


def _nth_weekday_of_month(year: int, month: int, weekday: int, nth_week: int):
    first_weekday, last_day = monthrange(year, month)
    day = 1 + ((weekday - first_weekday) % 7) + (nth_week - 1) * 7
    if day > last_day:
        return None
    return date(year, month, day)


def _parse_csv_ints(value):
    if not value:
        return []
    return [int(d.strip()) for d in str(value).split(',') if d.strip()]


def _generate_raw_pattern_dates(schedule: SupplierOrderSchedule, start_date: date, end_date: date, calculator: WorkingDayCalculator = None):
    pattern = schedule.pattern
    if not pattern:
        return
    recurrence = pattern.recurrence_type

    if recurrence == SupplierOrderPattern.RECURRENCE_MONTHLY_DATE:
        days_of_month = _parse_csv_ints(pattern.days_of_month)
        if not days_of_month:
            return
        for month_start in _iter_month_starts(start_date, end_date):
            last_day = monthrange(month_start.year, month_start.month)[1]
            for dom in sorted(days_of_month):
                day = min(dom, last_day)
                raw = date(month_start.year, month_start.month, day)
                if start_date <= raw <= end_date:
                    yield raw
        return

    if recurrence == SupplierOrderPattern.RECURRENCE_MONTHLY_NTH_DOW:
        nth_weeks = _parse_csv_ints(pattern.nth_weeks)
        days_of_week = _parse_csv_ints(pattern.days_of_week)
        if not nth_weeks or not days_of_week:
            return
        for month_start in _iter_month_starts(start_date, end_date):
            for nw in sorted(nth_weeks):
                for dow in sorted(days_of_week):
                    raw = _nth_weekday_of_month(month_start.year, month_start.month, dow, nw)
                    if raw and start_date <= raw <= end_date:
                        yield raw
        return

    if recurrence == SupplierOrderPattern.RECURRENCE_WEEKLY:
        days_of_week = set(_parse_csv_ints(pattern.days_of_week))
        if not days_of_week:
            return
        cursor = start_date
        while cursor <= end_date:
            if cursor.weekday() in days_of_week:
                yield cursor
            cursor = cursor + timedelta(days=1)
        return

    if recurrence == SupplierOrderPattern.RECURRENCE_EVERY_BUSINESS_DAY:
        cursor = start_date
        while cursor <= end_date:
            yield cursor
            cursor = cursor + timedelta(days=1)
        return

    if recurrence == SupplierOrderPattern.RECURRENCE_EVERY_N_BUSINESS_DAYS:
        interval = int(pattern.interval_days or 1)
        ref_date = schedule.start_date or pattern.start_date
        if not ref_date or interval < 1 or not calculator:
            return
        # 基準日から営業日をカウントし、interval営業日ごとの日を算出
        if ref_date < start_date:
            # 基準日→start_date間の営業日数を数えてオフセットを求める
            d = ref_date
            biz_count = 0
            while d < start_date:
                if calculator.is_working_day(d):
                    biz_count += 1
                d = d + timedelta(days=1)
            remainder = biz_count % interval
            skip = (interval - remainder) % interval
        else:
            # start_date <= ref_date: ref_dateから開始
            skip = 0
            start_date = ref_date

        cursor = start_date
        biz_count = 0
        while cursor <= end_date:
            if calculator.is_working_day(cursor):
                if biz_count >= skip and (biz_count - skip) % interval == 0:
                    yield cursor
                biz_count += 1
            cursor = cursor + timedelta(days=1)


def _is_order_timing_today(schedule: SupplierOrderSchedule, today: date, daiso_calculator: WorkingDayCalculator) -> bool:
    window_start = today - timedelta(days=62)
    window_end = today + timedelta(days=62)
    for raw_date in _generate_raw_pattern_dates(schedule, window_start, window_end, daiso_calculator):
        shifted = _shift_to_previous_working_day(raw_date, daiso_calculator)
        if shifted == today:
            return True
    return False


def _resolve_purchase_line_for_supplier(supplier: Supplier):
    line_name = f'仕入:{supplier.supplier_code} {supplier.supplier_name}'
    if len(line_name) > 50:
        line_name = line_name[:50]
    line_obj, created = Line.objects.get_or_create(
        line_code=supplier.supplier_code,
        defaults={
            'line_name': line_name,
            'line_type': 'PURCHASE',
            'is_active': True,
        },
    )
    if not created and line_obj.line_type != 'PURCHASE':
        line_obj.line_type = 'PURCHASE'
        line_obj.save(update_fields=['line_type'])
    return line_obj


def _create_notification(title: str, description: str, users, operator_name: str | None = None):
    user_ids = sorted({u.id for u in users if getattr(u, 'id', None)})
    if not user_ids:
        return
    today = get_business_today()
    operator = (operator_name or '').strip() or 'system'
    notification = Notification.objects.create(
        title=title[:200],
        category='購買',
        domain='PURCHASE_ORDER',
        valid_from=today,
        valid_to=today + timedelta(days=14),
        display_order=0,
        description=description or '',
        operator_name=operator,
    )
    notification.target_users.set(user_ids)


def _display_user_name(user):
    if not user or not getattr(user, 'id', None):
        return ''
    last_name = (getattr(user, 'last_name', '') or '').strip()
    first_name = (getattr(user, 'first_name', '') or '').strip()
    if last_name or first_name:
        return f'{last_name} {first_name}'.strip()
    full_name = (user.get_full_name() or '').strip()
    if full_name:
        return full_name
    return (getattr(user, 'username', '') or '').strip()


def _display_user_last_name(user):
    if not user or not getattr(user, 'id', None):
        return ''
    last_name = str(getattr(user, 'last_name', '') or '').strip()
    if last_name:
        return last_name
    full_name = str(user.get_full_name() or '').strip()
    if full_name:
        tokens = [token for token in re.split(r'[\s　]+', full_name) if token]
        if tokens:
            return tokens[0]
    return (getattr(user, 'username', '') or '').strip()


def _load_auto_plan_locks(line_ids, plan_date):
    ids = sorted({int(line_id) for line_id in line_ids if line_id})
    if not ids or not plan_date:
        return {}
    rows = ProductionLock.objects.filter(
        lock_type='auto_plan',
        line_id__in=ids,
        plan_date=plan_date,
    ).values('line_id', 'product_id', 'locked_qty')
    return {
        (row['line_id'], row['product_id']): int(row['locked_qty'] or 0)
        for row in rows
    }


def _apply_locked_qty_to_proposal_lines(lines, supplier, plan_date):
    canonical_line = resolve_purchase_line(supplier) if supplier else None
    line_ids = {line.get('line') for line in lines if isinstance(line, dict)}
    if canonical_line:
        line_ids.add(canonical_line.id)
    locks = _load_auto_plan_locks(line_ids, plan_date)
    if not locks:
        return lines

    result = []
    seen = set()
    for line_data in lines:
        item = dict(line_data)
        key = (int(item.get('line') or 0), int(item.get('product') or 0))
        if key in locks:
            item['order_qty'] = locks[key]
            seen.add(key)
        result.append(item)

    for (line_id, product_id), locked_qty in sorted(locks.items()):
        if (line_id, product_id) in seen:
            continue
        result.append({
            'product': product_id,
            'line': line_id,
            'shortage_date': plan_date,
            'shortage_qty': 0,
            'order_qty': locked_qty,
            'snapshot_stock': 0,
            'snapshot_min_stock': 0,
            'note': '自動計画ロック数量',
        })
    return result


def _restore_locked_plan_for_proposal_line(proposal, prop_line):
    lock = ProductionLock.objects.filter(
        lock_type='auto_plan',
        line_id=prop_line.line_id,
        product_id=prop_line.product_id,
        plan_date=proposal.desired_delivery_date,
    ).first()
    if not lock:
        return None

    supplier = getattr(proposal, 'supplier', None)
    target_line = prop_line.line or (resolve_purchase_line(supplier) if supplier else None)
    process = resolve_supplier_process(
        supplier=supplier,
        line=target_line,
        product=prop_line.product,
        create_purchase_process=True,
    )
    process_id = process.id if process else None
    if not process_id:
        raise ValueError(f'ロック済み注文書の工程を特定できません: product_id={prop_line.product_id}')

    order_qty = int(lock.locked_qty or 0)
    if int(prop_line.order_qty or 0) != order_qty:
        prop_line.order_qty = order_qty
        prop_line.save(update_fields=['order_qty'])

    LineBacklog.objects.update_or_create(
        line_id=prop_line.line_id,
        product_id=prop_line.product_id,
        plan_date=proposal.desired_delivery_date,
        sequence_no=1,
        defaults={
            'process_id': process_id,
            'plan_qty': order_qty,
            'order_qty': 0,
            'actual_qty': 0,
            'stock_qty': 0,
            'planned_stock_qty': 0,
            'adjust_qty': 0,
            'scrap_qty': 0,
            'actual_shipment_qty': 0,
        },
    )
    return order_qty


def _resolve_notification_operator_name(proposal: PurchaseOrderProposal, fallback_user=None):
    creator_name = _display_user_name(getattr(proposal, 'created_by', None))
    if creator_name:
        return creator_name
    fallback_name = _display_user_name(fallback_user)
    if fallback_name:
        return fallback_name
    return 'system'


def _write_plan_qty_on_final_approval(proposal: PurchaseOrderProposal):
    """最終承認時に各提案行の order_qty を LineBacklog.plan_qty として納入日に書き込む。
    購買計画は sequence_no=1 固定（仕様: LineBacklog_sequence_no仕様.md）。
    既存 seq=1 レコードは上書き。追加注文は別UIで対応する想定。"""
    delivery_date = proposal.desired_delivery_date
    if not delivery_date:
        return
    supplier = getattr(proposal, 'supplier', None)
    canonical_line = resolve_purchase_line(supplier) if supplier else None
    for prop_line in proposal.lines.all():
        locked_qty = _restore_locked_plan_for_proposal_line(proposal, prop_line)
        if locked_qty is not None:
            continue
        order_qty = int(prop_line.order_qty or 0)
        if order_qty <= 0:
            continue
        line_id = prop_line.line_id
        product_id = prop_line.product_id
        if not line_id or not product_id:
            continue
        target_line = prop_line.line or canonical_line
        process = resolve_supplier_process(
            supplier=supplier,
            line=target_line,
            product=prop_line.product,
            create_purchase_process=True,
        )
        process_id = process.id if process else None

        LineBacklog.objects.update_or_create(
            line_id=line_id,
            product_id=product_id,
            plan_date=delivery_date,
            sequence_no=1,
            defaults={
                'process_id': process_id,
                'plan_qty': order_qty,
                'order_qty': 0,
                'actual_qty': 0,
                'stock_qty': 0,
                'planned_stock_qty': 0,
                'adjust_qty': 0,
                'scrap_qty': 0,
                'actual_shipment_qty': 0,
            },
        )


def _delete_plan_qty_for_proposal(proposal: PurchaseOrderProposal):
    """提案差戻/キャンセル時に、最終承認時に書き込んだ LineBacklog.plan_qty(seq=1) を削除する。"""
    delivery_date = proposal.desired_delivery_date
    if not delivery_date:
        return
    for prop_line in proposal.lines.all():
        lock = ProductionLock.objects.filter(
            lock_type='auto_plan',
            line_id=prop_line.line_id,
            product_id=prop_line.product_id,
            plan_date=delivery_date,
        ).first()
        order_qty = int(prop_line.order_qty or 0)
        if order_qty <= 0 and not lock:
            continue
        LineBacklog.objects.filter(
            line_id=prop_line.line_id,
            product_id=prop_line.product_id,
            plan_date=delivery_date,
            sequence_no=1,
        ).delete()
        _restore_locked_plan_for_proposal_line(proposal, prop_line)


def _create_tasks_for_users(proposal: PurchaseOrderProposal, task_type: str, users, due_date: date | None = None):
    created_count = 0
    for user in users:
        if not getattr(user, 'id', None):
            continue
        exists = PurchaseOrderTask.objects.filter(
            proposal=proposal,
            task_type=task_type,
            assigned_to=user,
            status=PurchaseOrderTask.STATUS_PENDING,
        ).exists()
        if exists:
            continue
        PurchaseOrderTask.objects.create(
            proposal=proposal,
            task_type=task_type,
            assigned_to=user,
            status=PurchaseOrderTask.STATUS_PENDING,
            due_date=due_date,
        )
        created_count += 1
    return created_count


def _mark_tasks_done(proposal: PurchaseOrderProposal, task_type: str):
    now = timezone.now()
    PurchaseOrderTask.objects.filter(
        proposal=proposal,
        task_type=task_type,
        status=PurchaseOrderTask.STATUS_PENDING,
    ).update(status=PurchaseOrderTask.STATUS_DONE, done_at=now)


def _mark_all_pending_tasks_skipped(proposal: PurchaseOrderProposal):
    now = timezone.now()
    PurchaseOrderTask.objects.filter(
        proposal=proposal,
        status=PurchaseOrderTask.STATUS_PENDING,
    ).update(status=PurchaseOrderTask.STATUS_SKIPPED, done_at=now)


def _complete_order_pdf_task_for_user(proposal: PurchaseOrderProposal, user) -> bool:
    if not user or not getattr(user, 'id', None):
        return False

    now = timezone.now()
    updated = PurchaseOrderTask.objects.filter(
        proposal=proposal,
        task_type=PurchaseOrderTask.TASK_CREATE_ORDER_PDF,
        assigned_to=user,
        status=PurchaseOrderTask.STATUS_PENDING,
    ).update(status=PurchaseOrderTask.STATUS_DONE, done_at=now)

    # 旧データ互換: 既に SEND_TO_SUPPLIER タスクが直接作られていた提案に対して
    # 注文書作成実行時に完了履歴を補完する。
    if not updated and proposal.status == PurchaseOrderProposal.STATUS_APPROVED:
        has_pending_send = PurchaseOrderTask.objects.filter(
            proposal=proposal,
            task_type=PurchaseOrderTask.TASK_SEND_TO_SUPPLIER,
            assigned_to=user,
            status=PurchaseOrderTask.STATUS_PENDING,
        ).exists()
        has_create_task_row = PurchaseOrderTask.objects.filter(
            proposal=proposal,
            task_type=PurchaseOrderTask.TASK_CREATE_ORDER_PDF,
            assigned_to=user,
        ).exists()
        if has_pending_send and not has_create_task_row:
            PurchaseOrderTask.objects.create(
                proposal=proposal,
                task_type=PurchaseOrderTask.TASK_CREATE_ORDER_PDF,
                assigned_to=user,
                status=PurchaseOrderTask.STATUS_DONE,
                due_date=proposal.order_date,
                done_at=now,
            )
            updated = 1

    if updated:
        _create_tasks_for_users(
            proposal=proposal,
            task_type=PurchaseOrderTask.TASK_SEND_TO_SUPPLIER,
            users=[user],
            due_date=proposal.order_date,
        )
    return bool(updated)


def _delivery_date_with_supplier_calendar(order_date: date, lead_time_days: int, supplier: Supplier):
    calculator = WorkingDayCalculator(getattr(supplier, 'calendar', None))
    return calculator.add_working_days(order_date, max(int(lead_time_days or 0), 0))


def _collect_supplier_product_line_pairs(supplier: Supplier, order_date: date):
    canonical_line = _resolve_purchase_line_for_supplier(supplier)
    pairs = set()

    bom_items = (
        BOMItem.objects.filter(supplier_id=supplier.id, child_product_id__isnull=False)
        .select_related('line')
        .only('child_product_id', 'line_id', 'line__line_type')
    )
    for item in bom_items:
        line_id = canonical_line.id
        if item.line_id and item.line and item.line.line_type == 'PURCHASE':
            line_id = item.line_id
        pairs.add((line_id, item.child_product_id))

    product_ids_from_backlog = LineBacklog.objects.filter(
        line_id=canonical_line.id,
        plan_date__gte=order_date,
    ).values_list('product_id', flat=True).distinct()
    for product_id in product_ids_from_backlog:
        if product_id:
            pairs.add((canonical_line.id, product_id))

    if not pairs:
        return []

    line_ids = {line_id for line_id, _ in pairs}
    product_ids = {product_id for _, product_id in pairs}
    line_map = {line.id: line for line in Line.objects.filter(id__in=line_ids)}
    product_map = {
        row['id']: row
        for row in Product.objects.filter(id__in=product_ids).values(
            'id',
            'product_code',
            'product_name',
            'order_lot_min',
            'order_lot_multiple',
        )
    }

    results = []
    for line_id, product_id in pairs:
        line_obj = line_map.get(line_id)
        product_obj = product_map.get(product_id)
        if not line_obj or not product_obj:
            continue
        results.append((line_obj, product_obj))
    return results


def _normalize_auto_fill_source(value):
    raw = str(value or '').strip().upper()
    if raw in ('PROGRESS', '進度'):
        return AUTO_FILL_SOURCE_PROGRESS
    if raw in ('PLANNED_PROGRESS', '計画進度'):
        return AUTO_FILL_SOURCE_PLANNED_PROGRESS
    if raw in ('PLANNED_STOCK', 'STOCK', '計画在庫', '在庫'):
        return AUTO_FILL_SOURCE_PLANNED_STOCK
    return AUTO_FILL_SOURCE_DEFAULT


def _build_auto_fill_lines(proposal: PurchaseOrderProposal, next_delivery_date: date, source: str = AUTO_FILL_SOURCE_DEFAULT):
    from production.inventory.inventory_calculator import recalculate_inventory_for_line
    from production.services.recalc_start_date import resolve_inventory_effective_start_date

    order_date = proposal.order_date
    delivery_date = proposal.desired_delivery_date
    # 参照範囲: [delivery_date, next_delivery_date - 1]
    range_start = delivery_date
    range_end = next_delivery_date - timedelta(days=1)
    generated = []
    source = _normalize_auto_fill_source(source)

    pairs = _collect_supplier_product_line_pairs(proposal.supplier, order_date)

    # 参照範囲の値を正しくするため、先に次回納入日までの在庫・計画在庫・進度・計画進度を再計算
    today = get_business_today()
    recalc_end_date = range_end
    line_products_map = {}
    for line_obj, product in pairs:
        line_products_map.setdefault(line_obj.id, set()).add(product['id'])
    for line_id, product_ids in line_products_map.items():
        target_product_ids = sorted(product_ids)
        effective_start_dt = resolve_inventory_effective_start_date(
            line_id,
            today,
            recalc_end_date,
            product_ids=target_product_ids,
        )
        recalculate_inventory_for_line(
            line_id,
            effective_start_dt,
            recalc_end_date,
            include_progress=True,
            line_final_only=False,
            product_ids=target_product_ids,
        )

    for line_obj, product in pairs:
        min_stock_qty = (
            StockAllocation.objects.filter(product_id=product['id'])
            .aggregate(v=Max('min_stock_qty'))
            .get('v')
            or 0
        )
        rows = list(
            LineBacklog.objects.filter(
                line_id=line_obj.id,
                product_id=product['id'],
                plan_date__gte=range_start,
                plan_date__lte=range_end,
            )
            .order_by('plan_date')
            .values('plan_date', 'planned_stock_qty', 'progress_qty', 'planned_progress_qty')
        )
        if not rows:
            continue

        shortage_qty = 0
        snapshot_stock = None
        snapshot_min_stock = int(min_stock_qty) if source == AUTO_FILL_SOURCE_PLANNED_STOCK else 0
        first_reference = None
        for row in rows:
            if source == AUTO_FILL_SOURCE_PROGRESS:
                reference_value = int(row['progress_qty'] or 0)
                current_shortage = abs(reference_value) if reference_value < 0 else 0
            elif source == AUTO_FILL_SOURCE_PLANNED_PROGRESS:
                reference_value = int(row['planned_progress_qty'] or 0)
                current_shortage = abs(reference_value) if reference_value < 0 else 0
            else:
                reference_value = int(row['planned_stock_qty'] or 0)
                current_shortage = int(min_stock_qty) - reference_value
            if first_reference is None:
                first_reference = reference_value
            if current_shortage > 0:
                if snapshot_stock is None:
                    snapshot_stock = reference_value
                shortage_qty = max(shortage_qty, current_shortage)

        if shortage_qty <= 0:
            continue

        order_lot_multiple = int(product.get('order_lot_multiple') or 1)
        if order_lot_multiple <= 0:
            order_lot_multiple = 1
        order_lot_min = int(product.get('order_lot_min') or 0)

        order_qty = math.ceil(shortage_qty / order_lot_multiple) * order_lot_multiple
        order_qty = max(order_qty, order_lot_min)

        generated.append({
            'product': product['id'],
            'line': line_obj.id,
            'shortage_date': delivery_date,
            'shortage_qty': shortage_qty,
            'next_delivery_date': next_delivery_date,
            'order_qty': order_qty,
            'snapshot_stock': snapshot_stock if snapshot_stock is not None else first_reference,
            'snapshot_min_stock': snapshot_min_stock,
            'note': '',
        })

    return generated


def _proposal_detail_queryset():
    return (
        PurchaseOrderProposal.objects.select_related('supplier', 'created_by')
        .prefetch_related('lines__product', 'lines__line', 'approvals__approved_by', 'tasks__assigned_to')
    )


def _load_proposal_detail(pk: int):
    return _proposal_detail_queryset().filter(pk=pk).first()


def _ensure_purchase_order_pdf_font():
    registered = pdfmetrics.getRegisteredFontNames()
    if PURCHASE_ORDER_PDF_FONT in registered:
        return PURCHASE_ORDER_PDF_FONT
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(PURCHASE_ORDER_PDF_FONT))
        return PURCHASE_ORDER_PDF_FONT
    except Exception:
        return 'Helvetica'


def _short_text(value, limit: int):
    text = str(value or '').replace('\n', ' ').strip()
    if len(text) <= limit:
        return text
    return f'{text[: max(limit - 1, 0)]}…'


def _proposal_pdf_filename(proposal: PurchaseOrderProposal):
    return f'{_proposal_pdf_stem(proposal)}.pdf'


def _sanitize_filename_part(value, fallback: str = '-'):
    raw = str(value or '').strip()
    sanitized = re.sub(r'[\\/:*?"<>|]+', '_', raw)
    sanitized = re.sub(r'\s+', '', sanitized)
    return sanitized or fallback


def _proposal_daily_serial_no(proposal: PurchaseOrderProposal):
    proposal_no = str(proposal.proposal_no or '')
    matched = re.search(r'-(\d+)$', proposal_no)
    if matched:
        try:
            return str(int(matched.group(1)))
        except (TypeError, ValueError):
            pass
    return str(proposal.id or 1)


def _proposal_total_order_amount(proposal: PurchaseOrderProposal):
    total = 0
    for row in proposal.lines.all():
        try:
            qty = int(row.order_qty or 0)
        except (TypeError, ValueError):
            qty = 0
        if qty > 0:
            total += qty
    return total


def _proposal_pdf_stem(proposal: PurchaseOrderProposal):
    order_date = proposal.order_date.strftime('%Y%m%d') if proposal.order_date else '00000000'
    supplier_code = _sanitize_filename_part(getattr(proposal.supplier, 'supplier_code', ''), 'UNKNOWN')
    supplier_name = _sanitize_filename_part(getattr(proposal.supplier, 'supplier_name', ''), '')
    total_amount = _proposal_total_order_amount(proposal)
    daily_serial = _proposal_daily_serial_no(proposal)
    return f'{order_date}_{supplier_code}_{supplier_name}_{total_amount}_注文書_{daily_serial}'


def _build_saved_purchase_order_pdf_path(proposal: PurchaseOrderProposal):
    now = timezone.now()
    if timezone.is_aware(now):
        now = timezone.localtime(now)

    base_dir = Path(settings.MEDIA_ROOT)
    supplier_code = re.sub(r'[^0-9A-Za-z_-]+', '_', str(getattr(proposal.supplier, 'supplier_code', '') or 'UNKNOWN'))
    target_dir = base_dir / 'purchase_orders' / f'{now.year:04d}' / f'{now.month:02d}' / supplier_code
    target_dir.mkdir(parents=True, exist_ok=True)

    stem = _proposal_pdf_stem(proposal)
    target_path = target_dir / f'{stem}.pdf'
    suffix = 1
    while target_path.exists():
        target_path = target_dir / f'{stem}_{suffix:02d}.pdf'
        suffix += 1

    return target_path


def _save_purchase_order_pdf(proposal: PurchaseOrderProposal, pdf_bytes: bytes):
    target_path = _build_saved_purchase_order_pdf_path(proposal)
    target_path.write_bytes(pdf_bytes)
    relative_path = target_path.relative_to(Path(settings.MEDIA_ROOT))
    return str(relative_path).replace('\\', '/')


def _format_pdf_output_date():
    current = timezone.now()
    if timezone.is_aware(current):
        current = timezone.localtime(current)
    return current.date().isoformat()


def _format_pdf_output_datetime(value=None, fmt: str = '%Y-%m-%d %H:%M'):
    current = value or timezone.now()
    if timezone.is_aware(current):
        current = timezone.localtime(current)
    return current.strftime(fmt)


def _format_pdf_japanese_date(value=None):
    current = value or timezone.now()
    if timezone.is_aware(current):
        current = timezone.localtime(current)
    if isinstance(current, datetime):
        current = current.date()
    if not isinstance(current, date):
        return ''
    return f'{current.year}年{current.month}月{current.day}日'


def _format_pdf_month_day(value):
    if not value:
        return ''
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return f'{value.month}/{value.day}'
    raw = str(value).strip()
    if not raw:
        return ''
    try:
        parsed = date.fromisoformat(raw)
        return f'{parsed.month}/{parsed.day}'
    except ValueError:
        return raw


def _format_pdf_integer(value):
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        return ''
    return f'{number:,}'


def _format_pdf_decimal(value, digits: int = 2):
    if value is None:
        return ''
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return ''
    quantized = number.quantize(Decimal(f'1.{"0" * digits}'))
    text = f'{quantized:,}'
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text


def _resolve_supplier_contact_person(supplier: Supplier):
    if not supplier:
        return 'ご担当者'
    person = str(getattr(supplier, 'contact_person', '') or '').strip()
    return person or 'ご担当者'


def _resolve_line_unit_price(line):
    for target in (line, getattr(line, 'product', None)):
        if not target:
            continue
        for attr_name in ('unit_price', 'purchase_unit_price', 'price', 'cost'):
            if not hasattr(target, attr_name):
                continue
            raw = getattr(target, attr_name)
            if raw in (None, ''):
                continue
            try:
                value = Decimal(str(raw))
            except (InvalidOperation, TypeError, ValueError):
                continue
            if value >= 0:
                return value
    return None


PURCHASE_ORDER_PROPOSAL_EMAIL_DEFAULT_BODY = '''{supplier_name} 御中

お世話になっております。
発注書を送付いたします。

注文書番号: {proposal_no}
発注日: {order_date}
希望納入日: {desired_delivery_date}

添付のPDFをご確認のうえ、手配をお願いいたします。

------------------------------
ダイソウ工業株式会社
{created_by_name}

ご不明な点がございましたら下記までご連絡ください。
Email:{created_by_email}
'''


def _build_purchase_order_email_subject(proposal: PurchaseOrderProposal):
    return f'【発注書】{proposal.proposal_no} {proposal.supplier.supplier_name}'


def _append_purchase_order_reply_notice(body: str, cc_emails=None):
    text = (body or '').strip()
    if '送信専用' in text and ('返信' in text or 'ご返信' in text):
        return text
    cc_list = [email for email in (cc_emails or []) if email]
    reply_to = f'CC宛先（{", ".join(cc_list)}）' if cc_list else 'CC宛先'
    notice = f'※このメールは送信専用です。ご返信は{reply_to}へお願いします。'
    return f'{text}\n\n{notice}' if text else notice


def _render_purchase_order_proposal_email_body(template: str, proposal: PurchaseOrderProposal, cc_emails=None):
    creator_name = _display_user_name(proposal.created_by) if proposal.created_by_id else ''
    values = {
        'supplier_name': proposal.supplier.supplier_name,
        'proposal_no': proposal.proposal_no,
        'order_date': proposal.order_date,
        'desired_delivery_date': proposal.desired_delivery_date,
        'created_by_name': creator_name,
        'created_by_email': getattr(proposal.created_by, 'email', '') if proposal.created_by_id else '',
    }
    body = template or PURCHASE_ORDER_PROPOSAL_EMAIL_DEFAULT_BODY
    body = re.sub(
        r'\{(\w+)\}',
        lambda m: str(values.get(m.group(1), '') or '') if m.group(1) in values else m.group(0),
        body,
    )
    return _append_purchase_order_reply_notice(body, cc_emails)


def _get_purchase_order_proposal_email_config(proposal: PurchaseOrderProposal):
    if not proposal.supplier_id:
        return None
    return (
        PurchaseOrderProposalEmailConfig.objects
        .prefetch_related('cc_users')
        .filter(supplier_id=proposal.supplier_id)
        .first()
    )


def _build_purchase_order_email_body(proposal: PurchaseOrderProposal):
    creator_name = _display_user_name(getattr(proposal, 'created_by', None)) or '-'
    creator_email = str(getattr(getattr(proposal, 'created_by', None), 'email', '') or '').strip() or '-'
    return (
        f'{proposal.supplier.supplier_name} 御中\n\n'
        'お世話になっております。\n'
        '発注書を送付いたします。\n\n'
        f'注文書番号: {proposal.proposal_no}\n'
        f'発注日: {proposal.order_date}\n'
        f'希望納入日: {proposal.desired_delivery_date}\n\n'
        '添付のPDFをご確認のうえ、手配をお願いいたします。\n\n'
        '------------------------------\n'
        'ダイソウ工業株式会社\n'
        f'{creator_name}\n\n'
        'ご不明な点がございましたら下記までご連絡ください。\n'
        f'Email:{creator_email}\n'
    )


def _build_purchase_order_pdf(proposal: PurchaseOrderProposal):
    font_name = _ensure_purchase_order_pdf_font()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
    page_width, page_height = landscape(A4)
    left_margin = 8 * mm
    right_margin = 8 * mm

    proposal_lines = list(proposal.lines.select_related('product', 'line').order_by('product__product_code'))
    lines_first_page = 14
    lines_other_page = 18
    chunks = []
    remaining = proposal_lines[:]
    first = remaining[:lines_first_page]
    chunks.append(first)
    remaining = remaining[lines_first_page:]
    while remaining:
        chunks.append(remaining[:lines_other_page])
        remaining = remaining[lines_other_page:]
    total_pages = len(chunks)
    contact_person = _resolve_supplier_contact_person(proposal.supplier)
    line_amount_map = {}
    proposal_total_amount = Decimal('0')
    for line in proposal_lines:
        order_qty = int(line.order_qty or 0)
        unit_price = _resolve_line_unit_price(line)
        amount = (unit_price * Decimal(order_qty)) if unit_price is not None else Decimal(order_qty)
        line_amount_map[getattr(line, 'id', None)] = amount
        proposal_total_amount += amount

    approved_rows = [
        row
        for row in proposal.approvals.all()
        if row.action == PurchaseOrderProposalApproval.ACTION_APPROVED
    ]
    approval_by_level = {}
    for row in sorted(
        approved_rows,
        key=lambda item: (int(getattr(item, 'approval_level', 0) or 0), item.approved_at or timezone.now()),
        reverse=True,
    ):
        level = int(getattr(row, 'approval_level', 0) or 0)
        if level and level not in approval_by_level:
            approval_by_level[level] = row

    try:
        route_config = _get_purchase_order_proposal_route()
    except ValueError:
        route_config = None

    # level → stage マッピング: L2=reviewer1(班長), L3=reviewer2(係長), L4=approver(事業部長)
    proxy_user_ids_by_stage = {}
    if route_config:
        for stage in ('creator', 'reviewer1', 'reviewer2', 'approver'):
            proxy_field = getattr(route_config, f'{stage}_proxy_users', None)
            proxy_user_ids_by_stage[stage] = set(proxy_field.values_list('id', flat=True)) if proxy_field else set()

    def _stamp_label(user, acted_at=None, stage=''):
        name = _display_user_last_name(user)
        if not name:
            return ''
        if user and user.pk in proxy_user_ids_by_stage.get(stage, set()):
            name = f'{name}(代)'
        date_str = f'{acted_at.month}/{acted_at.day}' if acted_at else ''
        return f'{name}\n{date_str}' if date_str else name

    # 承認データをstageごとに構築
    # L1=creator(業務員サイン), L2=reviewer1(班長), L3=reviewer2(係長), L4=approver(事業部長)
    level_to_stage = {1: 'creator', 2: 'reviewer1', 3: 'reviewer2', 4: 'approver'}
    stamp_data = {}
    for level, row in approval_by_level.items():
        stage = level_to_stage.get(level)
        if stage and row.approved_by_id:
            stamp_data[stage] = _stamp_label(row.approved_by, row.approved_at, stage)
    if 'creator' not in stamp_data and proposal.created_by_id:
        stamp_data['creator'] = _stamp_label(proposal.created_by, proposal.generated_at, 'creator')

    # 承認枠の列構成（route_config参照）
    stamp_items = [('承認', 'approver')]
    if route_config and route_config.reviewer2_enabled:
        stamp_items.extend([('確認②', 'reviewer2'), ('確認①', 'reviewer1')])
    else:
        stamp_items.append(('確認', 'reviewer1'))
    stamp_items.append(('作成', 'creator'))

    table_col_widths = [38 * mm, 63 * mm, 22 * mm, 24 * mm, 18 * mm, 21 * mm, 28 * mm, 67 * mm]
    table_headers = ['部品番号', '部品名', '材質・材寸', '納期', '発注量', '単価', '金額', '備考']
    header_height = 10 * mm
    row_height = 8.2 * mm

    for page_index, line_chunk in enumerate(chunks, start=1):
        # ページ番号（全ページ共通）
        pdf.setFont(font_name, 8)
        pdf.drawRightString(page_width - right_margin, page_height - 17 * mm, f'PAGE ({page_index}/{total_pages})')

        if page_index == 1:
            # タイトル
            title_y = page_height - 14 * mm
            pdf.setFont(font_name, 16)
            pdf.drawCentredString(page_width / 2, title_y, '購　入　品　注　文　書')
            pdf.line(page_width / 2 - 42 * mm, title_y - 2 * mm, page_width / 2 + 42 * mm, title_y - 2 * mm)

            # 右上：日付・社名
            pdf.setFont(font_name, 11)
            pdf.drawRightString(page_width - right_margin, page_height - 22 * mm, _format_pdf_japanese_date())
            pdf.drawRightString(page_width - right_margin, page_height - 28 * mm, 'ダイソウ工業株式会社')

            # 左：仕入先・担当者
            supplier_name = _short_text(getattr(proposal.supplier, 'supplier_name', ''), 30)
            pdf.setFont(font_name, 14)
            pdf.drawString(left_margin + 8 * mm, page_height - 26 * mm, supplier_name)
            pdf.setDash(2, 2)
            pdf.line(left_margin, page_height - 29 * mm, left_margin + 62 * mm, page_height - 29 * mm)
            pdf.line(left_margin, page_height - 39 * mm, left_margin + 62 * mm, page_height - 39 * mm)
            pdf.setDash()
            pdf.setFont(font_name, 15)
            pdf.drawCentredString(left_margin + 43 * mm, page_height - 36 * mm, f'{contact_person} 様')

            # 中央：注意書き
            pdf.setFont(font_name, 9)
            info_x = left_margin + 68 * mm
            info_top = page_height - 24 * mm
            info_lines = [
                '下記内容にて、不都合な点がございましたら',
                '御連絡下さい。',
                '※納期に間に合わない場合は、',
                '早急に御連絡下さい。',
            ]
            for i, text in enumerate(info_lines):
                pdf.drawString(info_x, info_top - i * 4.5 * mm, text)

            # 右：承認枠（レーザ材料注文と同方式）
            stamp_col_w = 16 * mm
            stamp_header_h = 7 * mm
            stamp_body_h = 13 * mm
            stamp_x = page_width - right_margin - stamp_col_w * len(stamp_items)
            stamp_top = page_height - 36 * mm
            stamp_body_top = stamp_top - stamp_header_h
            for idx, (label, stage) in enumerate(stamp_items):
                x = stamp_x + idx * stamp_col_w
                # ヘッダーセル
                pdf.rect(x, stamp_top - stamp_header_h, stamp_col_w, stamp_header_h, stroke=1, fill=0)
                pdf.setFont(font_name, 9)
                pdf.drawCentredString(x + stamp_col_w / 2, stamp_top - stamp_header_h + 2 * mm, label)
                # ボディセル（名前+日付）
                pdf.rect(x, stamp_body_top - stamp_body_h, stamp_col_w, stamp_body_h, stroke=1, fill=0)
                cell_text = stamp_data.get(stage, '')
                if cell_text:
                    lines = cell_text.split('\n')
                    pdf.setFont(font_name, 8)
                    line_h = 8 * 1.15
                    start_y = (stamp_body_top - stamp_body_h / 2) + ((len(lines) - 1) * line_h / 2) - (8 * 0.35)
                    for li, line_text in enumerate(lines):
                        pdf.drawCentredString(x + stamp_col_w / 2, start_y - li * line_h, line_text)

        # 明細テーブル
        rows = []
        for line in line_chunk:
            order_qty = int(line.order_qty or 0)
            unit_price = _resolve_line_unit_price(line)
            line_amount = line_amount_map.get(getattr(line, 'id', None), Decimal(order_qty))

            rows.append([
                _short_text(getattr(line.product, 'product_code', ''), 24),
                _short_text(getattr(line.product, 'product_name', ''), 30),
                '',
                _format_pdf_month_day(line.shortage_date or proposal.desired_delivery_date),
                _format_pdf_integer(order_qty),
                _format_pdf_decimal(unit_price, 2),
                _format_pdf_decimal(line_amount, 0),
                _short_text(line.note or '', 40),
            ])

        max_lines = lines_first_page if page_index == 1 else lines_other_page
        while len(rows) < max_lines:
            rows.append(['', '', '', '', '', '', '', ''])

        table = Table(
            [table_headers, *rows],
            colWidths=table_col_widths,
            rowHeights=[header_height] + [row_height] * len(rows),
            repeatRows=1,
        )
        table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, 0), font_name, 12),
            ('FONT', (0, 1), (-1, -1), font_name, 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (2, -1), 'LEFT'),
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),
            ('ALIGN', (4, 1), (6, -1), 'RIGHT'),
            ('ALIGN', (7, 1), (7, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 0.8, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.black),
        ]))

        table_top_y = page_height - 58 * mm if page_index == 1 else page_height - 25 * mm
        table_height = header_height + row_height * len(rows)
        table.wrapOn(pdf, page_width - left_margin - right_margin, table_height)
        table.drawOn(pdf, left_margin, table_top_y - table_height)

        # フッタ
        footer_y = table_top_y - table_height - 10 * mm
        pdf.setFont(font_name, 18)
        pdf.drawCentredString(page_width / 2 - 6 * mm, footer_y, '※納期通りに納入宜しくお願い致します。')
        label_x = page_width - right_margin - 42 * mm
        total_box_x = page_width - right_margin - 22 * mm
        total_box_w = 22 * mm
        total_box_h = 10 * mm
        is_last_page = (page_index == total_pages)
        if is_last_page:
            amount_label = '合計金額'
            amount_value = proposal_total_amount
        else:
            amount_label = '小計'
            page_subtotal = sum(line_amount_map.get(getattr(l, 'id', None), Decimal(0)) for l in line_chunk)
            amount_value = page_subtotal
        pdf.setFont(font_name, 11)
        pdf.drawString(label_x, footer_y + 2 * mm, amount_label)
        pdf.rect(total_box_x, footer_y - 2.5 * mm, total_box_w, total_box_h, stroke=1, fill=0)
        pdf.setFont(font_name, 12)
        pdf.drawCentredString(total_box_x + total_box_w / 2, footer_y + 1 * mm, _format_pdf_decimal(amount_value, 0))

        # 識別情報
        pdf.setFont(font_name, 8)
        pdf.drawString(left_margin, 8 * mm, f'注文書番号: {proposal.proposal_no}')
        pdf.drawRightString(page_width - right_margin, 8 * mm, f'出力日時: {_format_pdf_output_datetime()}')

        if page_index < total_pages:
            pdf.showPage()

    pdf.save()
    buffer.seek(0)
    return buffer


def run_auto_purchase_order_check():
    from production.models_schedule_config import ScheduleConfig

    today = get_business_today()
    daiso_calculator = WorkingDayCalculator(_get_daiso_calendar())
    config = ScheduleConfig.objects.filter(task_name='AUTO_PURCHASE_ORDER_CHECK', line__isnull=True).first()
    try:
        route_config = _get_purchase_order_proposal_route()
    except ValueError as exc:
        if config:
            config.last_run_at = datetime.now()
            config.last_run_status = 'FAILED'
            config.last_run_message = str(exc)
            config.save(update_fields=['last_run_at', 'last_run_status', 'last_run_message'])
        return
    level1_users = _resolve_route_stage_users(route_config, 'creator')
    if config:
        config.last_run_at = datetime.now()
        config.last_run_status = 'RUNNING'
        config.last_run_message = '実行中...'
        config.save(update_fields=['last_run_at', 'last_run_status', 'last_run_message'])

    created_proposals = 0
    created_tasks = 0
    errors = []
    try:
        schedules = SupplierOrderSchedule.objects.filter(is_enabled=True).select_related('supplier', 'supplier__calendar', 'pattern')

        for schedule in schedules:
            try:
                if not _is_order_timing_today(schedule, today, daiso_calculator):
                    continue

                proposal = PurchaseOrderProposal.objects.filter(
                    supplier=schedule.supplier,
                    order_date=today,
                ).exclude(status=PurchaseOrderProposal.STATUS_CANCELED).first()

                with transaction.atomic():
                    if not proposal:
                        proposal = PurchaseOrderProposal.objects.create(
                            proposal_no=_generate_proposal_no(today),
                            supplier=schedule.supplier,
                            order_date=today,
                            desired_delivery_date=_delivery_date_with_supplier_calendar(
                                today,
                                int(schedule.lead_time_days or 0),
                                schedule.supplier,
                            ),
                            status=PurchaseOrderProposal.STATUS_DRAFT,
                            note=f'自動生成（スケジュールID:{schedule.id}）',
                            created_by=None,
                        )
                        created_proposals += 1

                    if level1_users and route_config.creator_task_enabled:
                        created_tasks += _create_tasks_for_users(
                            proposal=proposal,
                            task_type=PurchaseOrderTask.TASK_CREATE_PROPOSAL,
                            users=level1_users,
                            due_date=today,
                        )
            except Exception as exc:
                errors.append(f'schedule_id={schedule.id}: {exc}')

        if level1_users and route_config.creator_app_notification_enabled and (created_proposals or created_tasks):
            _create_notification(
                title='外作・購入品注文書作成タスクが生成されました',
                description=f'対象日: {today} / 生成提案書: {created_proposals}件 / タスク: {created_tasks}件',
                users=level1_users,
            )
        level1_emails = sorted({user.email for user in level1_users if getattr(user, 'email', '')})
        if level1_emails and route_config.creator_email_notification_enabled and (created_proposals or created_tasks):
            EmailService().send_plain_email(
                to_emails=level1_emails,
                subject='[外作・購入品注文] 注文書作成タスクが生成されました',
                body=f'対象日: {today}\n生成提案書: {created_proposals}件\nタスク: {created_tasks}件',
            )
    finally:
        if config:
            is_success = len(errors) == 0
            config.last_run_status = 'SUCCESS' if is_success else 'FAILED'
            config.last_run_message = (
                f'対象日: {today}, 生成提案書: {created_proposals}件, 生成タスク: {created_tasks}件'
                + (f' / エラー: {"; ".join(errors)}' if errors else '')
            )
            config.save(update_fields=['last_run_status', 'last_run_message'])

    return {
        'date': str(today),
        'created_proposals': created_proposals,
        'created_tasks': created_tasks,
        'errors': errors,
    }


class SupplierOrderPatternListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = SupplierOrderPattern.objects.all()
        is_active = request.query_params.get('is_active')
        if is_active in ('true', '1'):
            queryset = queryset.filter(is_active=True)
        serializer = SupplierOrderPatternSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = SupplierOrderPatternSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(SupplierOrderPatternSerializer(obj).data, status=status.HTTP_201_CREATED)


class SupplierOrderPatternDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk: int):
        obj = SupplierOrderPattern.objects.filter(pk=pk).first()
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = SupplierOrderPatternSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk: int):
        obj = SupplierOrderPattern.objects.filter(pk=pk).first()
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if obj.schedules.exists():
            return Response(
                {'detail': 'このパターンは発注スケジュールで使用中のため削除できません。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SupplierOrderScheduleListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = SupplierOrderSchedule.objects.select_related('supplier', 'pattern').order_by('supplier__supplier_code', 'id')

        supplier_id = request.query_params.get('supplier')
        is_enabled = request.query_params.get('is_enabled')

        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        if is_enabled in ('true', 'false', '1', '0'):
            queryset = queryset.filter(is_enabled=is_enabled.lower() in ('true', '1'))

        serializer = SupplierOrderScheduleSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = SupplierOrderScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(SupplierOrderScheduleSerializer(obj).data, status=status.HTTP_201_CREATED)


class SupplierOrderScheduleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk: int):
        obj = SupplierOrderSchedule.objects.filter(pk=pk).first()
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = SupplierOrderScheduleSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk: int):
        obj = SupplierOrderSchedule.objects.filter(pk=pk).first()
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PurchaseOrderProposalListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = PurchaseOrderProposal.objects.select_related('supplier', 'created_by').prefetch_related('tasks', 'lines').order_by('-order_date', '-id')

        supplier_id = request.query_params.get('supplier')
        status_code = request.query_params.get('status')
        date_from = request.query_params.get('order_date_from')
        date_to = request.query_params.get('order_date_to')
        only_my_tasks = request.query_params.get('only_my_tasks')

        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        if status_code:
            queryset = queryset.filter(status=status_code)
        if date_from:
            try:
                queryset = queryset.filter(order_date__gte=_coerce_date(date_from, 'order_date_from'))
            except ValueError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if date_to:
            try:
                queryset = queryset.filter(order_date__lte=_coerce_date(date_to, 'order_date_to'))
            except ValueError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if str(only_my_tasks).lower() in ('true', '1', 'yes'):
            queryset = queryset.filter(
                Q(tasks__assigned_to=request.user, tasks__status=PurchaseOrderTask.STATUS_PENDING)
                | Q(created_by=request.user, status__in=(PurchaseOrderProposal.STATUS_DRAFT, PurchaseOrderProposal.STATUS_REJECTED))
            ).distinct()

        serializer = PurchaseOrderProposalListSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        supplier_id = request.data.get('supplier')
        if not supplier_id:
            return Response({'detail': 'supplier is required'}, status=status.HTTP_400_BAD_REQUEST)

        supplier = Supplier.objects.filter(id=supplier_id).first()
        if not supplier:
            return Response({'detail': 'supplier not found'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order_date = _coerce_date(request.data.get('order_date') or get_business_today(), 'order_date')
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        desired_delivery_date_raw = request.data.get('desired_delivery_date')
        if desired_delivery_date_raw:
            try:
                desired_delivery_date = _coerce_date(desired_delivery_date_raw, 'desired_delivery_date')
            except ValueError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            schedule_id = request.data.get('schedule_id')
            lead_time_days = 0
            if schedule_id:
                schedule = SupplierOrderSchedule.objects.filter(id=schedule_id, supplier_id=supplier.id).first()
                if schedule:
                    lead_time_days = int(schedule.lead_time_days or 0)
            desired_delivery_date = _delivery_date_with_supplier_calendar(order_date, lead_time_days, supplier)

        lines = request.data.get('lines') or []
        if not isinstance(lines, list):
            return Response({'detail': 'lines must be list'}, status=status.HTTP_400_BAD_REQUEST)
        lines = _apply_locked_qty_to_proposal_lines(lines, supplier, desired_delivery_date)

        with transaction.atomic():
            proposal = PurchaseOrderProposal.objects.create(
                proposal_no=_generate_proposal_no(order_date),
                supplier=supplier,
                order_date=order_date,
                desired_delivery_date=desired_delivery_date,
                status=PurchaseOrderProposal.STATUS_DRAFT,
                created_by=request.user if request.user.is_authenticated else None,
                note=str(request.data.get('note') or ''),
            )

            for line_data in lines:
                line_serializer = PurchaseOrderProposalLineSerializer(data=line_data)
                line_serializer.is_valid(raise_exception=True)
                line_serializer.save(proposal=proposal)

        detail = PurchaseOrderProposalDetailSerializer(proposal)
        return Response(detail.data, status=status.HTTP_201_CREATED)


class PurchaseOrderProposalDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        proposal = (
            PurchaseOrderProposal.objects.select_related('supplier', 'created_by')
            .prefetch_related('lines__product', 'lines__line', 'approvals__approved_by', 'tasks__assigned_to')
            .filter(pk=pk)
            .first()
        )
        if not proposal:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(PurchaseOrderProposalDetailSerializer(proposal).data)

    def put(self, request, pk: int):
        proposal = PurchaseOrderProposal.objects.filter(pk=pk).first()
        if not proposal:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if proposal.status not in (PurchaseOrderProposal.STATUS_DRAFT, PurchaseOrderProposal.STATUS_REJECTED):
            return Response({'detail': 'DRAFT/差戻のみ編集できます'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            supplier_id = request.data.get('supplier')
            if supplier_id:
                supplier = Supplier.objects.filter(id=supplier_id).first()
                if not supplier:
                    return Response({'detail': 'supplier not found'}, status=status.HTTP_400_BAD_REQUEST)
                proposal.supplier = supplier

            if 'order_date' in request.data:
                try:
                    proposal.order_date = _coerce_date(request.data.get('order_date'), 'order_date')
                except ValueError as exc:
                    return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            if 'desired_delivery_date' in request.data:
                try:
                    proposal.desired_delivery_date = _coerce_date(request.data.get('desired_delivery_date'), 'desired_delivery_date')
                except ValueError as exc:
                    return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            if 'next_delivery_date' in request.data:
                raw_nd = request.data.get('next_delivery_date')
                if raw_nd in (None, ''):
                    proposal.next_delivery_date = None
                else:
                    try:
                        proposal.next_delivery_date = _coerce_date(raw_nd, 'next_delivery_date')
                    except ValueError as exc:
                        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            if 'note' in request.data:
                proposal.note = str(request.data.get('note') or '')
            proposal.save()

            if 'lines' in request.data:
                lines = request.data.get('lines') or []
                if not isinstance(lines, list):
                    return Response({'detail': 'lines must be list'}, status=status.HTTP_400_BAD_REQUEST)
                lines = _apply_locked_qty_to_proposal_lines(lines, proposal.supplier, proposal.desired_delivery_date)
                proposal.lines.all().delete()
                for line_data in lines:
                    line_serializer = PurchaseOrderProposalLineSerializer(data=line_data)
                    line_serializer.is_valid(raise_exception=True)
                    line_serializer.save(proposal=proposal)

        proposal = (
            PurchaseOrderProposal.objects.select_related('supplier', 'created_by')
            .prefetch_related('lines__product', 'lines__line', 'approvals__approved_by', 'tasks__assigned_to')
            .get(pk=pk)
        )
        return Response(PurchaseOrderProposalDetailSerializer(proposal).data)

    def delete(self, request, pk: int):
        proposal = PurchaseOrderProposal.objects.filter(pk=pk).first()
        if not proposal:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if proposal.status != PurchaseOrderProposal.STATUS_DRAFT:
            return Response({'detail': 'DRAFTのみ削除できます'}, status=status.HTTP_400_BAD_REQUEST)
        proposal.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PurchaseOrderProposalSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        proposal = PurchaseOrderProposal.objects.filter(pk=pk).first()
        if not proposal:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if proposal.status not in (PurchaseOrderProposal.STATUS_DRAFT, PurchaseOrderProposal.STATUS_REJECTED):
            return Response({'detail': 'DRAFT/差戻のみサインできます'}, status=status.HTTP_400_BAD_REQUEST)
        if not proposal.lines.exists():
            return Response({'detail': '明細がありません'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            route_config = _get_purchase_order_proposal_route()
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        level2_users = []

        with transaction.atomic():
            proposal.status = PurchaseOrderProposal.STATUS_SUBMITTED
            if not proposal.created_by_id and request.user.is_authenticated:
                proposal.created_by = request.user
            proposal.save(update_fields=['status', 'created_by', 'updated_at'])

            PurchaseOrderProposalApproval.objects.create(
                proposal=proposal,
                approval_level=1,
                action=PurchaseOrderProposalApproval.ACTION_APPROVED,
                approved_by=request.user if request.user.is_authenticated else None,
                comment=str(request.data.get('comment') or ''),
            )
            _mark_tasks_done(proposal, PurchaseOrderTask.TASK_CREATE_PROPOSAL)

            level2_users = _resolve_purchase_approval_users(route_config, 2, proposal)
            if _route_stage_task_enabled(route_config, 2):
                _create_tasks_for_users(
                    proposal=proposal,
                    task_type=PurchaseOrderTask.TASK_APPROVE_L2,
                    users=level2_users,
                    due_date=proposal.order_date,
                )

        if level2_users and _route_stage_app_notification_enabled(route_config, 2):
            _create_notification(
                title=f'外作・購入品注文書 承認依頼: {proposal.proposal_no}',
                description='班長承認待ちです。',
                users=level2_users,
                operator_name=_resolve_notification_operator_name(proposal, request.user),
            )
        _send_purchase_approval_stage_email(
            route_config=route_config,
            level=2,
            proposal=proposal,
            users=level2_users,
            operator_user=request.user,
            request=request,
        )

        proposal = (
            PurchaseOrderProposal.objects.select_related('supplier', 'created_by')
            .prefetch_related('lines__product', 'lines__line', 'approvals__approved_by', 'tasks__assigned_to')
            .get(pk=pk)
        )
        return Response(PurchaseOrderProposalDetailSerializer(proposal).data)


class PurchaseOrderProposalApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        proposal = PurchaseOrderProposal.objects.filter(pk=pk).first()
        if not proposal:
            return Response(status=status.HTTP_404_NOT_FOUND)

        transition = APPROVAL_TRANSITION.get(proposal.status)
        if not transition:
            return Response({'detail': 'この状態では承認できません'}, status=status.HTTP_400_BAD_REQUEST)

        current_level = transition['level']
        current_task_type = TASK_TYPE_BY_APPROVAL_LEVEL.get(current_level)
        next_status = transition['next_status']
        next_level = transition['next_level']
        next_task_type = transition['next_task_type']
        try:
            route_config = _get_purchase_order_proposal_route()
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        next_users = []
        notify_users = []
        if next_task_type in (PurchaseOrderTask.TASK_CREATE_ORDER_PDF, PurchaseOrderTask.TASK_SEND_TO_SUPPLIER):
            if proposal.created_by_id:
                next_users = [proposal.created_by]
            notify_users = next_users
        elif next_level:
            next_users = _resolve_purchase_approval_users(route_config, next_level, proposal)
            notify_users = next_users

        with transaction.atomic():
            PurchaseOrderProposalApproval.objects.create(
                proposal=proposal,
                approval_level=current_level,
                action=PurchaseOrderProposalApproval.ACTION_APPROVED,
                approved_by=request.user if request.user.is_authenticated else None,
                comment=str(request.data.get('comment') or ''),
            )
            proposal.status = next_status
            proposal.save(update_fields=['status', 'updated_at'])

            if current_task_type:
                _mark_tasks_done(proposal, current_task_type)

            # 最終承認時: 提案行の order_qty を LineBacklog.plan_qty として書込
            if next_status == PurchaseOrderProposal.STATUS_APPROVED:
                _write_plan_qty_on_final_approval(proposal)

            if (
                next_task_type
                and next_users
                and (next_level is None or _route_stage_task_enabled(route_config, next_level))
            ):
                _create_tasks_for_users(
                    proposal=proposal,
                    task_type=next_task_type,
                    users=next_users,
                    due_date=proposal.order_date,
                )

        if next_level:
            if notify_users and _route_stage_app_notification_enabled(route_config, next_level):
                _create_notification(
                    title=f'外作・購入品注文書 承認依頼: {proposal.proposal_no}',
                    description=f'ステータスが {next_status} になりました。',
                    users=notify_users,
                    operator_name=_resolve_notification_operator_name(proposal, request.user),
                )
            _send_purchase_approval_stage_email(
                route_config=route_config,
                level=next_level,
                proposal=proposal,
                users=notify_users,
                operator_user=request.user,
                request=request,
            )
        elif next_status == PurchaseOrderProposal.STATUS_APPROVED:
            result_users = _get_purchase_approval_result_users(route_config, proposal)
            if route_config.approved_result_app_notification_enabled:
                _create_notification(
                    title=f'外作・購入品注文書 承認完了: {proposal.proposal_no}',
                    description='最終承認済みです。注文書作成を行ってください。',
                    users=result_users,
                    operator_name=_resolve_notification_operator_name(proposal, request.user),
                )
            _send_purchase_approval_result_email(
                route_config=route_config,
                proposal=proposal,
                users=result_users,
                operator_user=request.user,
                request=request,
            )

        proposal = (
            PurchaseOrderProposal.objects.select_related('supplier', 'created_by')
            .prefetch_related('lines__product', 'lines__line', 'approvals__approved_by', 'tasks__assigned_to')
            .get(pk=pk)
        )
        return Response(PurchaseOrderProposalDetailSerializer(proposal).data)


class PurchaseOrderProposalRejectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        proposal = PurchaseOrderProposal.objects.filter(pk=pk).first()
        if not proposal:
            return Response(status=status.HTTP_404_NOT_FOUND)

        comment = str(request.data.get('comment') or '').strip()
        if not comment:
            return Response({'detail': 'comment is required'}, status=status.HTTP_400_BAD_REQUEST)

        current_level = STATUS_TO_APPROVAL_LEVEL.get(proposal.status)
        if (
            current_level is None
            or proposal.status in (
                PurchaseOrderProposal.STATUS_APPROVED,
                PurchaseOrderProposal.STATUS_SENT,
                PurchaseOrderProposal.STATUS_CANCELED,
            )
        ):
            return Response({'detail': 'この状態では差戻できません'}, status=status.HTTP_400_BAD_REQUEST)

        notify_users = []
        if proposal.created_by_id:
            notify_users.append(proposal.created_by)
        previous_level = max(current_level - 1, 1)
        prev_approvers = (
            proposal.approvals.filter(
                approval_level=previous_level,
                action=PurchaseOrderProposalApproval.ACTION_APPROVED,
                approved_by_id__isnull=False,
            )
            .select_related('approved_by')
        )
        notify_users.extend([row.approved_by for row in prev_approvers if row.approved_by_id])

        with transaction.atomic():
            PurchaseOrderProposalApproval.objects.create(
                proposal=proposal,
                approval_level=current_level,
                action=PurchaseOrderProposalApproval.ACTION_REJECTED,
                approved_by=request.user if request.user.is_authenticated else None,
                comment=comment,
            )
            proposal.status = PurchaseOrderProposal.STATUS_REJECTED
            proposal.save(update_fields=['status', 'updated_at'])

            _mark_all_pending_tasks_skipped(proposal)
            if proposal.created_by_id:
                _create_tasks_for_users(
                    proposal=proposal,
                    task_type=PurchaseOrderTask.TASK_CREATE_PROPOSAL,
                    users=[proposal.created_by],
                    due_date=proposal.order_date,
                )

        _create_notification(
            title=f'外作・購入品注文書 差戻: {proposal.proposal_no}',
            description=comment,
            users=notify_users,
            operator_name=_resolve_notification_operator_name(proposal, request.user),
        )

        try:
            route_config = _get_purchase_order_proposal_route()
        except ValueError:
            route_config = None
        if route_config:
            _send_purchase_rejection_email(
                route_config=route_config,
                proposal=proposal,
                users=notify_users,
                operator_user=request.user,
                comment=comment,
                request=request,
            )

        proposal = (
            PurchaseOrderProposal.objects.select_related('supplier', 'created_by')
            .prefetch_related('lines__product', 'lines__line', 'approvals__approved_by', 'tasks__assigned_to')
            .get(pk=pk)
        )
        return Response(PurchaseOrderProposalDetailSerializer(proposal).data)


class PurchaseOrderProposalAdminResetView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        if not request.user.is_superuser:
            return Response({'detail': '管理者権限が必要です'}, status=status.HTTP_403_FORBIDDEN)
        proposal = PurchaseOrderProposal.objects.filter(pk=pk).first()
        if not proposal:
            return Response(status=status.HTTP_404_NOT_FOUND)
        with transaction.atomic():
            proposal.approvals.all().delete()
            proposal.tasks.all().delete()
            proposal.status = PurchaseOrderProposal.STATUS_DRAFT
            proposal.save(update_fields=['status', 'updated_at'])
        return Response({'detail': 'リセットしました'})


class PurchaseOrderProposalCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        proposal = PurchaseOrderProposal.objects.filter(pk=pk).first()
        if not proposal:
            return Response(status=status.HTTP_404_NOT_FOUND)

        comment = str(request.data.get('comment') or '').strip()

        # キャンセル可能なのは最終承認済(APPROVED)のみ。送信済/既キャンセルは不可。
        if proposal.status != PurchaseOrderProposal.STATUS_APPROVED:
            return Response({'detail': 'この状態ではキャンセルできません'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            route_config = _get_purchase_order_proposal_route()
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # 権限チェック: 汎用承認設定の承認者または代理承認者のみキャンセル可
        authorized_ids = {
            user.id
            for user in _resolve_purchase_approval_users(route_config, 4, proposal)
            if getattr(user, 'id', None)
        }
        user_id = getattr(request.user, 'id', None)
        if not user_id or user_id not in authorized_ids:
            return Response(
                {'detail': 'キャンセル権限がありません（事業部長または代理承認者のみ実行可）'},
                status=status.HTTP_403_FORBIDDEN,
            )

        notify_users = []
        if proposal.created_by_id:
            notify_users.append(proposal.created_by)
        approvers = (
            proposal.approvals.filter(
                action=PurchaseOrderProposalApproval.ACTION_APPROVED,
                approved_by_id__isnull=False,
            )
            .select_related('approved_by')
        )
        notify_users.extend([row.approved_by for row in approvers if row.approved_by_id])

        with transaction.atomic():
            proposal.status = PurchaseOrderProposal.STATUS_CANCELED
            proposal.save(update_fields=['status', 'updated_at'])

            # 最終承認時に書き込んだ plan_qty(seq=1) を削除
            _delete_plan_qty_for_proposal(proposal)

            _mark_all_pending_tasks_skipped(proposal)

        _create_notification(
            title=f'外作・購入品注文書 キャンセル: {proposal.proposal_no}',
            description=comment,
            users=notify_users,
            operator_name=_resolve_notification_operator_name(proposal, request.user),
        )

        proposal = (
            PurchaseOrderProposal.objects.select_related('supplier', 'created_by')
            .prefetch_related('lines__product', 'lines__line', 'approvals__approved_by', 'tasks__assigned_to')
            .get(pk=pk)
        )
        return Response(PurchaseOrderProposalDetailSerializer(proposal).data)


class PurchaseOrderProposalEmailConfigListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = (
            PurchaseOrderProposalEmailConfig.objects
            .select_related('supplier')
            .prefetch_related('cc_users')
            .order_by('supplier__supplier_code')
        )
        serializer = PurchaseOrderProposalEmailConfigSerializer(queryset, many=True)
        return Response(serializer.data)


class PurchaseOrderProposalEmailConfigDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, supplier_id: int):
        supplier = Supplier.objects.filter(pk=supplier_id).first()
        if not supplier:
            return Response(status=status.HTTP_404_NOT_FOUND)
        config, _ = PurchaseOrderProposalEmailConfig.objects.get_or_create(
            supplier=supplier,
            defaults={'body': PURCHASE_ORDER_PROPOSAL_EMAIL_DEFAULT_BODY},
        )
        serializer = PurchaseOrderProposalEmailConfigSerializer(config)
        return Response(serializer.data)

    def put(self, request, supplier_id: int):
        supplier = Supplier.objects.filter(pk=supplier_id).first()
        if not supplier:
            return Response(status=status.HTTP_404_NOT_FOUND)
        config, _ = PurchaseOrderProposalEmailConfig.objects.get_or_create(
            supplier=supplier,
            defaults={'body': PURCHASE_ORDER_PROPOSAL_EMAIL_DEFAULT_BODY},
        )
        payload = {**request.data, 'supplier': supplier.id}
        serializer = PurchaseOrderProposalEmailConfigSerializer(config, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(supplier=supplier)
        return Response(serializer.data)


class PurchaseOrderProposalSendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        proposal = (
            PurchaseOrderProposal.objects.select_related('supplier', 'created_by')
            .prefetch_related('lines__product', 'lines__line', 'approvals__approved_by')
            .filter(pk=pk)
            .first()
        )
        if not proposal:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if proposal.status != PurchaseOrderProposal.STATUS_APPROVED:
            return Response({'detail': '最終承認済みのみ送信できます'}, status=status.HTTP_400_BAD_REQUEST)
        if not proposal.lines.exists():
            return Response({'detail': '明細がないため送信できません'}, status=status.HTTP_400_BAD_REQUEST)
        if PurchaseOrderTask.objects.filter(
            proposal=proposal,
            task_type=PurchaseOrderTask.TASK_CREATE_ORDER_PDF,
            status=PurchaseOrderTask.STATUS_PENDING,
        ).exists():
            return Response({'detail': '先に注文書作成を実行してください'}, status=status.HTTP_400_BAD_REQUEST)

        to_email = str(request.data.get('to_email') or proposal.supplier.order_email or '').strip()
        if not to_email:
            return Response({'detail': '仕入先マスタに送信メールアドレスが未設定です'}, status=status.HTTP_400_BAD_REQUEST)
        email_config = _get_purchase_order_proposal_email_config(proposal)
        cc_emails = sorted({user.email for user in email_config.cc_users.all() if getattr(user, 'email', '')}) if email_config else []
        subject = str(request.data.get('subject') or '').strip() or _build_purchase_order_email_subject(proposal)
        body_raw = request.data.get('body')
        if body_raw is None:
            body = _render_purchase_order_proposal_email_body(
                email_config.body if email_config else PURCHASE_ORDER_PROPOSAL_EMAIL_DEFAULT_BODY,
                proposal,
                cc_emails=cc_emails,
            )
        else:
            body = str(body_raw)
            if not body.strip():
                body = _render_purchase_order_proposal_email_body(
                    email_config.body if email_config else PURCHASE_ORDER_PROPOSAL_EMAIL_DEFAULT_BODY,
                    proposal,
                    cc_emails=cc_emails,
                )
            else:
                body = _append_purchase_order_reply_notice(body, cc_emails)

        pdf_buffer = _build_purchase_order_pdf(proposal)
        pdf_bytes = pdf_buffer.getvalue()
        saved_pdf_path = _save_purchase_order_pdf(proposal, pdf_bytes)
        email_service = EmailService()
        send_result = email_service.send_email_with_attachment(
            to_emails=[to_email],
            subject=subject,
            body=body,
            attachment_data=BytesIO(pdf_bytes),
            attachment_filename=_proposal_pdf_filename(proposal),
            cc_emails=cc_emails if cc_emails else None,
            user_id=request.user.id if request.user and request.user.is_authenticated else None,
        )
        if not send_result.get('success'):
            return Response(
                {'detail': send_result.get('message') or '購入先送信に失敗しました'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            proposal.status = PurchaseOrderProposal.STATUS_SENT
            proposal.sent_at = timezone.now()
            proposal.save(update_fields=['status', 'sent_at', 'updated_at'])
            _mark_tasks_done(proposal, PurchaseOrderTask.TASK_SEND_TO_SUPPLIER)

        proposal = _load_proposal_detail(pk)
        payload = PurchaseOrderProposalDetailSerializer(proposal).data
        payload['send_result'] = send_result.get('message') or ''
        payload['saved_pdf_path'] = saved_pdf_path
        return Response(payload)


class PurchaseOrderProposalPdfView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        proposal = (
            PurchaseOrderProposal.objects.select_related('supplier', 'created_by')
            .prefetch_related('lines__product', 'lines__line', 'approvals__approved_by', 'tasks')
            .filter(pk=pk)
            .first()
        )
        if not proposal:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if proposal.status == PurchaseOrderProposal.STATUS_APPROVED:
            with transaction.atomic():
                _complete_order_pdf_task_for_user(
                    proposal=proposal,
                    user=request.user if request.user.is_authenticated else None,
                )

        pdf_buffer = _build_purchase_order_pdf(proposal)
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        filename = _proposal_pdf_filename(proposal)
        quoted = quote(filename)
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{quoted}"
        return response


class PurchaseOrderProposalAutoFillView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        proposal = PurchaseOrderProposal.objects.filter(pk=pk).first()
        if not proposal:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if proposal.status not in (PurchaseOrderProposal.STATUS_DRAFT, PurchaseOrderProposal.STATUS_REJECTED):
            return Response({'detail': 'DRAFTまたはREJECTEDのみ自動提案できます'}, status=status.HTTP_400_BAD_REQUEST)

        raw_next = request.data.get('next_delivery_date')
        if not raw_next:
            return Response({'detail': '次回納入日を指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            next_delivery_date = datetime.strptime(str(raw_next), '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return Response({'detail': 'next_delivery_date はYYYY-MM-DD形式で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        if next_delivery_date <= proposal.desired_delivery_date:
            return Response({'detail': '次回納入日は納入日より後の日付を指定してください'}, status=status.HTTP_400_BAD_REQUEST)

        # ヘッダの次回納入日も保存
        if proposal.next_delivery_date != next_delivery_date:
            proposal.next_delivery_date = next_delivery_date
            proposal.save(update_fields=['next_delivery_date', 'updated_at'])

        source = _normalize_auto_fill_source(request.data.get('source'))
        clear_existing = str(request.data.get('clear_existing', 'true')).lower() in ('true', '1', 'yes')
        generated_lines = _build_auto_fill_lines(
            proposal,
            next_delivery_date=next_delivery_date,
            source=source,
        )
        generated_lines = _apply_locked_qty_to_proposal_lines(
            generated_lines,
            proposal.supplier,
            proposal.desired_delivery_date,
        )

        with transaction.atomic():
            if clear_existing:
                proposal.lines.all().delete()

            created = []
            for line_data in generated_lines:
                serializer = PurchaseOrderProposalLineSerializer(data=line_data)
                serializer.is_valid(raise_exception=True)
                created.append(serializer.save(proposal=proposal))

        proposal = (
            PurchaseOrderProposal.objects.select_related('supplier', 'created_by')
            .prefetch_related('lines__product', 'lines__line', 'approvals__approved_by', 'tasks__assigned_to')
            .get(pk=pk)
        )
        detail = PurchaseOrderProposalDetailSerializer(proposal)
        return Response({
            'generated_count': len(generated_lines),
            'source': source,
            'proposal': detail.data,
        })


class PurchaseOrderTaskListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = PurchaseOrderTask.objects.select_related('proposal', 'proposal__supplier', 'assigned_to').order_by('status', 'due_date', '-created_at')

        assigned_to_me = request.query_params.get('assigned_to_me', 'true')
        if str(assigned_to_me).lower() in ('true', '1', 'yes'):
            queryset = queryset.filter(assigned_to=request.user)

        task_type = request.query_params.get('task_type')
        status_code = request.query_params.get('status')
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        if status_code:
            queryset = queryset.filter(status=status_code)

        serializer = PurchaseOrderTaskSerializer(queryset, many=True)
        return Response(serializer.data)


class PurchaseOrderProposalDeliveryNotePdfView(APIView):
    """注文書詳細から外作納品書PDFを生成"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        from .tasks_auto_delivery_list import _generate_delivery_note_pdf

        proposal = (
            PurchaseOrderProposal.objects.select_related('supplier')
            .prefetch_related('lines__product')
            .filter(pk=pk)
            .first()
        )
        if not proposal:
            return Response(status=status.HTTP_404_NOT_FOUND)

        items = []
        for line in proposal.lines.select_related('product').all():
            product = line.product
            if not product:
                continue
            delivery_date = line.next_delivery_date or proposal.next_delivery_date or proposal.desired_delivery_date
            if not delivery_date:
                continue
            qty = int(line.order_qty or 0)
            if qty <= 0:
                continue
            items.append({
                'product_code': product.product_code or '',
                'product_name': product.product_name or '',
                'expected_qty': qty,
                'delivery_date': delivery_date,
            })

        if not items:
            return Response({'detail': '納品書に出力する明細がありません'}, status=status.HTTP_400_BAD_REQUEST)

        supplier = proposal.supplier
        representative_date = items[0]['delivery_date']
        pdf_buffer = _generate_delivery_note_pdf(items, representative_date, supplier)

        s_code = supplier.supplier_code or ''
        filename = f'外作納品書_{s_code}_{representative_date}.pdf'
        quoted = quote(filename)
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{quoted}"
        return response
