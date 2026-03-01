import math
import re
from calendar import monthrange
from datetime import date, timedelta
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
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Table, TableStyle
from reportlab.pdfgen import canvas
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from masters.models import BOMItem, Calendar, Line, Product, Supplier
from notifications.models import Notification
from orders.utils.calendar_utils import WorkingDayCalculator, get_business_today
from production.models_line_backlog import LineBacklog
from production.models_production import StockAllocation
from shipping.services.email_service import EmailService

from .models import (
    PurchaseOrderApprovalConfig,
    PurchaseOrderProposal,
    PurchaseOrderProposalApproval,
    PurchaseOrderProposalLine,
    PurchaseOrderTask,
    SupplierOrderSchedule,
)
from .serializers import (
    PurchaseOrderApprovalConfigSerializer,
    PurchaseOrderProposalDetailSerializer,
    PurchaseOrderProposalLineSerializer,
    PurchaseOrderProposalListSerializer,
    PurchaseOrderTaskSerializer,
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


def _ensure_approval_config_defaults():
    for level, name in DEFAULT_APPROVAL_LEVELS:
        PurchaseOrderApprovalConfig.objects.get_or_create(
            approval_level=level,
            defaults={'level_name': name},
        )


def _get_approval_config(level: int) -> PurchaseOrderApprovalConfig:
    _ensure_approval_config_defaults()
    config, _ = PurchaseOrderApprovalConfig.objects.get_or_create(
        approval_level=level,
        defaults={'level_name': dict(DEFAULT_APPROVAL_LEVELS).get(level, f'Level {level}')},
    )
    return config


def _get_user_profile(user):
    if not user or not getattr(user, 'id', None):
        return None
    try:
        return user.profile
    except ObjectDoesNotExist:
        return None


def _resolve_level2_approvers_for_submit(proposal: PurchaseOrderProposal, configured_users):
    if not configured_users:
        return []

    creator = proposal.created_by
    profile = _get_user_profile(creator)
    if not profile:
        return configured_users

    team_id = getattr(profile, 'team_id', None)
    group_id = getattr(profile, 'group_id', None)
    if not team_id and not group_id:
        return configured_users

    configured_user_ids = [u.id for u in configured_users if getattr(u, 'id', None)]
    if not configured_user_ids:
        return []

    user_qs = get_user_model().objects.filter(
        id__in=configured_user_ids,
        is_active=True,
        profile__role='supervisor',
    ).exclude(id=getattr(creator, 'id', None))

    if team_id:
        user_qs = user_qs.filter(profile__team_id=team_id)
    elif group_id:
        user_qs = user_qs.filter(profile__group_id=group_id)

    matched = list(user_qs.distinct())
    if matched:
        return matched

    return configured_users


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


def _generate_raw_pattern_dates(schedule: SupplierOrderSchedule, start_date: date, end_date: date):
    pattern_type = schedule.pattern_type
    if pattern_type == SupplierOrderSchedule.PATTERN_MONTHLY_DATE:
        for month_start in _iter_month_starts(start_date, end_date):
            last_day = monthrange(month_start.year, month_start.month)[1]
            day = min(int(schedule.day_of_month or 1), last_day)
            raw = date(month_start.year, month_start.month, day)
            if start_date <= raw <= end_date:
                yield raw
        return

    if pattern_type == SupplierOrderSchedule.PATTERN_WEEKLY_NTH_DAY:
        nth_week = int(schedule.nth_week or 0)
        day_of_week = int(schedule.day_of_week or 0)
        if not (1 <= nth_week <= 5 and 0 <= day_of_week <= 6):
            return
        for month_start in _iter_month_starts(start_date, end_date):
            raw = _nth_weekday_of_month(month_start.year, month_start.month, day_of_week, nth_week)
            if raw and start_date <= raw <= end_date:
                yield raw
        return

    if pattern_type == SupplierOrderSchedule.PATTERN_EVERY_WEEK:
        day_of_week = int(schedule.day_of_week or 0)
        if not (0 <= day_of_week <= 6):
            return
        cursor = start_date
        while cursor <= end_date:
            if cursor.weekday() == day_of_week:
                yield cursor
            cursor = cursor + timedelta(days=1)


def _is_order_timing_today(schedule: SupplierOrderSchedule, today: date, daiso_calculator: WorkingDayCalculator) -> bool:
    window_start = today - timedelta(days=62)
    window_end = today + timedelta(days=62)
    for raw_date in _generate_raw_pattern_dates(schedule, window_start, window_end):
        shifted_date = _shift_to_previous_working_day(raw_date, daiso_calculator)
        if shifted_date == today:
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


def _resolve_notification_operator_name(proposal: PurchaseOrderProposal, fallback_user=None):
    creator_name = _display_user_name(getattr(proposal, 'created_by', None))
    if creator_name:
        return creator_name
    fallback_name = _display_user_name(fallback_user)
    if fallback_name:
        return fallback_name
    return 'system'


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


def _build_auto_fill_lines(proposal: PurchaseOrderProposal, horizon_days: int = 30, source: str = AUTO_FILL_SOURCE_DEFAULT):
    order_date = proposal.order_date
    end_date = order_date + timedelta(days=max(1, min(horizon_days, 365)))
    generated = []
    source = _normalize_auto_fill_source(source)

    for line_obj, product in _collect_supplier_product_line_pairs(proposal.supplier, order_date):
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
                plan_date__gte=order_date,
                plan_date__lte=end_date,
            )
            .order_by('plan_date')
            .values('plan_date', 'planned_stock_qty', 'progress_qty', 'planned_progress_qty')
        )
        if not rows:
            continue

        shortage_date = None
        shortage_qty = 0
        snapshot_stock = None
        snapshot_min_stock = int(min_stock_qty) if source == AUTO_FILL_SOURCE_PLANNED_STOCK else 0
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
            if current_shortage > 0:
                if shortage_date is None:
                    shortage_date = row['plan_date']
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
            'shortage_date': shortage_date,
            'shortage_qty': shortage_qty,
            'order_qty': order_qty,
            'snapshot_stock': snapshot_stock,
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
    total_amount = _proposal_total_order_amount(proposal)
    daily_serial = _proposal_daily_serial_no(proposal)
    return f'{order_date}_{supplier_code}_{total_amount}_注文書_{daily_serial}'


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


def _build_purchase_order_email_subject(proposal: PurchaseOrderProposal):
    return f'【発注書】{proposal.proposal_no} {proposal.supplier.supplier_name}'


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
    pdf = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4
    left_margin = 12 * mm

    proposal_lines = list(proposal.lines.select_related('product', 'line').order_by('id'))
    lines_per_page = 20
    chunks = [
        proposal_lines[idx: idx + lines_per_page]
        for idx in range(0, len(proposal_lines), lines_per_page)
    ] or [[]]

    approved_rows = [
        row
        for row in proposal.approvals.all()
        if row.action == PurchaseOrderProposalApproval.ACTION_APPROVED
    ]
    approval_map = {}
    for row in sorted(approved_rows, key=lambda item: (item.approval_level, item.approved_at or timezone.now()), reverse=True):
        approval_map.setdefault(int(row.approval_level), row)

    creator_name = ''
    if proposal.created_by_id:
        creator_name = _display_user_name(proposal.created_by)

    table_col_widths = [10 * mm, 28 * mm, 42 * mm, 42 * mm, 22 * mm, 16 * mm, 16 * mm, 32 * mm]
    table_headers = ['No', '品番', '品名', '購買ライン', '不足日', '不足数', '発注数', '備考']

    for page_index, line_chunk in enumerate(chunks):
        y = page_height - 15 * mm
        title = '発注書' if page_index == 0 else '発注書（続き）'
        pdf.setFont(font_name, 16)
        pdf.drawString(left_margin, y, title)

        pdf.setFont(font_name, 10)
        y -= 6 * mm
        pdf.drawString(left_margin, y, f'注文書番号: {proposal.proposal_no}')
        pdf.drawRightString(page_width - left_margin, y, f'出力日: {_format_pdf_output_date()}')
        y -= 5 * mm
        pdf.drawString(left_margin, y, f'仕入先: {proposal.supplier.supplier_code} {proposal.supplier.supplier_name}')
        y -= 5 * mm
        pdf.drawString(left_margin, y, f'発注日: {proposal.order_date}')
        pdf.drawString(left_margin + 70 * mm, y, f'希望納入日: {proposal.desired_delivery_date}')
        y -= 5 * mm
        pdf.drawString(left_margin, y, f'作成者: {creator_name or "-"}')
        if page_index == 0 and proposal.note:
            y -= 5 * mm
            pdf.drawString(left_margin, y, f'備考: {_short_text(proposal.note, 80)}')

        y -= 7 * mm
        table_rows = [table_headers]
        for offset, line in enumerate(line_chunk):
            row_no = page_index * lines_per_page + offset + 1
            table_rows.append([
                str(row_no),
                _short_text(getattr(line.product, 'product_code', ''), 14),
                _short_text(getattr(line.product, 'product_name', ''), 20),
                _short_text(f'{getattr(line.line, "line_code", "")} {getattr(line.line, "line_name", "")}', 20),
                str(line.shortage_date or ''),
                '' if line.shortage_qty is None else str(int(line.shortage_qty)),
                str(int(line.order_qty or 0)),
                _short_text(line.note or '', 15),
            ])
        if not line_chunk:
            table_rows.append(['', '', '明細なし', '', '', '', '', ''])

        table = Table(table_rows, colWidths=table_col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), font_name, 8.5),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (4, 1), (6, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 0.8, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.black),
        ]))
        _, table_height = table.wrap(page_width - left_margin * 2, page_height)
        table.drawOn(pdf, left_margin, y - table_height)
        y = y - table_height - 7 * mm

        if page_index == len(chunks) - 1:
            if y < 45 * mm:
                pdf.showPage()
                y = page_height - 20 * mm
            sign_rows = [
                ['業務員', '班長', '係長', '事業部長'],
                ['', '', '', ''],
                ['', '', '', ''],
            ]
            for level in (1, 2, 3, 4):
                row = approval_map.get(level)
                if not row:
                    continue
                user_name = ''
                if row.approved_by_id:
                    user_name = _display_user_name(row.approved_by)
                approved_at = ''
                if row.approved_at:
                    approved_at = _format_pdf_output_datetime(row.approved_at)
                sign_rows[1][level - 1] = _short_text(user_name, 14)
                sign_rows[2][level - 1] = approved_at

            sign_table = Table(sign_rows, colWidths=[(page_width - left_margin * 2) / 4] * 4, rowHeights=[8 * mm, 10 * mm, 8 * mm])
            sign_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), font_name, 9),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOX', (0, 0), (-1, -1), 0.8, colors.black),
                ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.black),
            ]))
            _, sign_height = sign_table.wrap(page_width - left_margin * 2, page_height)
            sign_table.drawOn(pdf, left_margin, y - sign_height)

        pdf.setFont(font_name, 8)
        pdf.drawRightString(page_width - left_margin, 8 * mm, f'出力日時: {_format_pdf_output_datetime()}')

        if page_index < len(chunks) - 1:
            pdf.showPage()

    pdf.save()
    buffer.seek(0)
    return buffer


def run_auto_purchase_order_check():
    from production.models_schedule_config import ScheduleConfig

    today = get_business_today()
    daiso_calculator = WorkingDayCalculator(_get_daiso_calendar())
    _ensure_approval_config_defaults()
    level1_config = _get_approval_config(1)
    level1_users = list(level1_config.approver_users.all())
    config = ScheduleConfig.objects.filter(task_name='AUTO_PURCHASE_ORDER_CHECK', line__isnull=True).first()
    if config:
        config.last_run_at = timezone.now()
        config.last_run_status = 'RUNNING'
        config.last_run_message = '実行中...'
        config.save(update_fields=['last_run_at', 'last_run_status', 'last_run_message'])

    created_proposals = 0
    created_tasks = 0
    errors = []
    try:
        schedules = SupplierOrderSchedule.objects.filter(is_enabled=True).select_related('supplier', 'supplier__calendar')

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

                    if level1_users:
                        created_tasks += _create_tasks_for_users(
                            proposal=proposal,
                            task_type=PurchaseOrderTask.TASK_CREATE_PROPOSAL,
                            users=level1_users,
                            due_date=today,
                        )
            except Exception as exc:
                errors.append(f'schedule_id={schedule.id}: {exc}')

        if level1_users and (created_proposals or created_tasks):
            _create_notification(
                title='発注提案書作成タスクが生成されました',
                description=f'対象日: {today} / 生成提案書: {created_proposals}件 / タスク: {created_tasks}件',
                users=level1_users,
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


class SupplierOrderScheduleListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = SupplierOrderSchedule.objects.select_related('supplier').order_by('supplier__supplier_code', 'id')

        supplier_id = request.query_params.get('supplier')
        pattern_type = request.query_params.get('pattern_type')
        is_enabled = request.query_params.get('is_enabled')

        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        if pattern_type:
            queryset = queryset.filter(pattern_type=pattern_type)
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
            queryset = queryset.filter(tasks__assigned_to=request.user, tasks__status=PurchaseOrderTask.STATUS_PENDING).distinct()

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
        if proposal.status != PurchaseOrderProposal.STATUS_DRAFT:
            return Response({'detail': 'DRAFTのみ編集できます'}, status=status.HTTP_400_BAD_REQUEST)

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
            if 'note' in request.data:
                proposal.note = str(request.data.get('note') or '')
            proposal.save()

            if 'lines' in request.data:
                lines = request.data.get('lines') or []
                if not isinstance(lines, list):
                    return Response({'detail': 'lines must be list'}, status=status.HTTP_400_BAD_REQUEST)
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
        if proposal.status != PurchaseOrderProposal.STATUS_DRAFT:
            return Response({'detail': 'DRAFTのみサインできます'}, status=status.HTTP_400_BAD_REQUEST)
        if not proposal.lines.exists():
            return Response({'detail': '明細がありません'}, status=status.HTTP_400_BAD_REQUEST)

        level2_config = _get_approval_config(2)
        configured_level2_users = list(level2_config.approver_users.all())
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

            level2_users = _resolve_level2_approvers_for_submit(
                proposal=proposal,
                configured_users=configured_level2_users,
            )
            _create_tasks_for_users(
                proposal=proposal,
                task_type=PurchaseOrderTask.TASK_APPROVE_L2,
                users=level2_users,
                due_date=proposal.order_date,
            )

        _create_notification(
            title=f'発注提案書 承認依頼: {proposal.proposal_no}',
            description='班長承認待ちです。',
            users=level2_users + list(level2_config.notify_users.all()),
            operator_name=_resolve_notification_operator_name(proposal, request.user),
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

        next_users = []
        notify_users = []
        if next_task_type in (PurchaseOrderTask.TASK_CREATE_ORDER_PDF, PurchaseOrderTask.TASK_SEND_TO_SUPPLIER):
            if proposal.created_by_id:
                next_users = [proposal.created_by]
            if not next_users:
                next_users = list(_get_approval_config(1).approver_users.all())
            notify_users = next_users
        elif next_level:
            next_config = _get_approval_config(next_level)
            next_users = list(next_config.approver_users.all())
            notify_users = next_users + list(next_config.notify_users.all())

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

            if next_task_type and next_users:
                _create_tasks_for_users(
                    proposal=proposal,
                    task_type=next_task_type,
                    users=next_users,
                    due_date=proposal.order_date,
                )

        if notify_users:
            notify_description = f'ステータスが {next_status} になりました。'
            if next_task_type == PurchaseOrderTask.TASK_CREATE_ORDER_PDF:
                notify_description = '最終承認済みです。注文書作成を行ってください。'
            _create_notification(
                title=f'発注提案書 承認依頼: {proposal.proposal_no}',
                description=notify_description,
                users=notify_users,
                operator_name=_resolve_notification_operator_name(proposal, request.user),
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
        if current_level is None or proposal.status in (PurchaseOrderProposal.STATUS_SENT, PurchaseOrderProposal.STATUS_CANCELED):
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
            title=f'発注提案書 差戻: {proposal.proposal_no}',
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
        subject = str(request.data.get('subject') or '').strip() or _build_purchase_order_email_subject(proposal)
        body_raw = request.data.get('body')
        if body_raw is None:
            body = _build_purchase_order_email_body(proposal)
        else:
            body = str(body_raw)
            if not body.strip():
                body = _build_purchase_order_email_body(proposal)

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

        try:
            horizon_days = int(request.data.get('horizon_days', 30))
        except (TypeError, ValueError):
            return Response({'detail': 'horizon_days must be integer'}, status=status.HTTP_400_BAD_REQUEST)
        horizon_days = max(1, min(horizon_days, 365))

        source = _normalize_auto_fill_source(request.data.get('source'))
        clear_existing = str(request.data.get('clear_existing', 'true')).lower() in ('true', '1', 'yes')
        generated_lines = _build_auto_fill_lines(
            proposal,
            horizon_days=horizon_days,
            source=source,
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


class PurchaseOrderApprovalConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _ensure_approval_config_defaults()
        queryset = PurchaseOrderApprovalConfig.objects.prefetch_related('approver_users', 'notify_users').order_by('approval_level')
        serializer = PurchaseOrderApprovalConfigSerializer(queryset, many=True)
        return Response(serializer.data)

    def put(self, request):
        _ensure_approval_config_defaults()
        payload_configs = request.data.get('configs')
        if payload_configs is None:
            payload_configs = [request.data]
        if not isinstance(payload_configs, list):
            return Response({'detail': 'configs must be list'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            for item in payload_configs:
                level = item.get('approval_level')
                if level is None:
                    return Response({'detail': 'approval_level is required'}, status=status.HTTP_400_BAD_REQUEST)
                try:
                    level = int(level)
                except (TypeError, ValueError):
                    return Response({'detail': 'approval_level must be integer'}, status=status.HTTP_400_BAD_REQUEST)
                config = _get_approval_config(level)

                if 'level_name' in item and item.get('level_name'):
                    config.level_name = str(item.get('level_name'))
                    config.save(update_fields=['level_name'])
                if 'approver_users' in item:
                    config.approver_users.set(item.get('approver_users') or [])
                if 'notify_users' in item:
                    config.notify_users.set(item.get('notify_users') or [])

        queryset = PurchaseOrderApprovalConfig.objects.prefetch_related('approver_users', 'notify_users').order_by('approval_level')
        serializer = PurchaseOrderApprovalConfigSerializer(queryset, many=True)
        return Response(serializer.data)
