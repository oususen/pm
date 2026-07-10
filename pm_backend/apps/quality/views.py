import os
import uuid
import logging
from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.role_utils import build_leader_role_q, can_act_as_chief, can_act_as_manager, can_act_as_supervisor
from masters.models import Calendar, CalendarDay, Equipment
from notifications.models import Notification
from orders.utils.calendar_utils import WorkingDayCalculator

from .models import (
    EquipmentInspectionConfirmation,
    EquipmentInspectionItem,
    EquipmentInspectionRecord,
    EquipmentInspectionTask,
    EquipmentInspectionTemplate,
    EquipmentInspectionWorkflowLog,
)
from .serializers import (
    EquipmentInspectionConfirmationSerializer,
    EquipmentInspectionItemAttachmentSerializer,
    EquipmentInspectionRecordSerializer,
    EquipmentInspectionTaskSerializer,
    EquipmentInspectionTemplateSerializer,
    EquipmentInspectionWorkflowLogSerializer,
)

ROLE_RANK = {
    "staff": 1,
    "leader": 2,
    "supervisor": 3,
    "chief": 4,
    "manager": 5,
}

logger = logging.getLogger(__name__)


def _role_rank(role_value):
    return ROLE_RANK.get(str(role_value or "").strip(), 0)


def _reviewer_sort_key(user):
    return (
        _role_rank(getattr(getattr(user, "profile", None), "role", "")),
        user.id,
    )


def _display_name(user):
    if not user:
        return ""
    full_name = f"{(user.last_name or '').strip()} {(user.first_name or '').strip()}".strip()
    if full_name:
        return full_name
    return (user.username or user.email or "").strip()


def _section_type_label(value):
    if value == EquipmentInspectionItem.SECTION_QUARTERLY:
        return "定期実測"
    return "日次点検"


def _build_media_url(raw_url):
    if not raw_url:
        return raw_url
    path = str(raw_url)
    if path.startswith(("http://", "https://")):
        return path
    if path.startswith("/"):
        return path
    return f"/media/{path.lstrip('/')}"


def _template_summary(template):
    if not template:
        return None
    return {
        "id": template.id,
        "sheet_code": template.sheet_code,
        "sheet_name": template.sheet_name,
        "title": template.title,
        "version": template.version,
        "status": template.status,
        "effective_from": template.effective_from.isoformat() if template.effective_from else None,
    }


def _month_start(target_value):
    return date(target_value.year, target_value.month, 1)


def _month_end(target_value):
    month_first = _month_start(target_value)
    if month_first.month == 12:
        next_month = date(month_first.year + 1, 1, 1)
    else:
        next_month = date(month_first.year, month_first.month + 1, 1)
    return next_month - timedelta(days=1)


def _parse_date(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _parse_month(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    if len(raw) == 7:
        raw = f"{raw}-01"
    return _parse_date(raw)


def _build_month_weeks(target_month):
    month_first = _month_start(target_month)
    month_last = _month_end(target_month)
    cursor = month_first - timedelta(days=month_first.weekday())
    weeks = []
    index = 1
    while cursor <= month_last:
        week_start = cursor
        week_end = cursor + timedelta(days=6)
        display_start = max(week_start, month_first)
        display_end = min(week_end, month_last)
        weeks.append(
            {
                "week_index": index,
                "start_date": display_start.isoformat(),
                "end_date": display_end.isoformat(),
                "label": f"{display_start.month}/{display_start.day} - {display_end.month}/{display_end.day}",
            }
        )
        cursor += timedelta(days=7)
        index += 1
    return weeks


def _monthly_confirmation_exists(sheet_code, target_month):
    return EquipmentInspectionConfirmation.objects.filter(
        sheet_code=sheet_code,
        target_month=_month_start(target_month),
        confirm_type=EquipmentInspectionConfirmation.TYPE_MONTHLY_CHIEF,
        week_index=0,
    ).exists()


def _active_operation_template(sheet_code):
    return (
        EquipmentInspectionTemplate.objects.filter(
            sheet_code=sheet_code,
            status=EquipmentInspectionTemplate.STATUS_APPROVED,
            is_active=True,
        )
        .prefetch_related("items__attachments")
        .order_by("-version", "-id")
        .first()
    )


def _record_missing_required_count(record):
    count = 0
    for result in record.results.all():
        if not result.is_required:
            continue
        if result.record_type in (EquipmentInspectionItem.RECORD_NUMERIC, EquipmentInspectionItem.RECORD_PHOTO_NUMERIC):
            if result.numeric_value is None:
                count += 1
                continue
            if result.record_type == EquipmentInspectionItem.RECORD_PHOTO_NUMERIC and not str(result.photo_url or "").strip():
                count += 1
                continue
        elif result.record_type == EquipmentInspectionItem.RECORD_PHOTO:
            if not str(result.photo_url or "").strip():
                count += 1
                continue
        elif result.record_type == EquipmentInspectionItem.RECORD_TEXT:
            if not str(result.text_value or "").strip():
                count += 1
                continue
        elif not str(result.judgement or "").strip():
            count += 1
            continue

        if not str(result.judgement or "").strip():
            count += 1
    return count


def _get_calendar_for_equipment(sheet_code):
    """設備のライン→カレンダー、なければdaisoカレンダーを返す"""
    equipment = Equipment.objects.filter(equipment_code=sheet_code).select_related("line__calendar").first()
    if equipment and equipment.line and equipment.line.calendar:
        return equipment.line.calendar
    return Calendar.objects.filter(calendar_code="daiso").first()


def _equipment_context(sheet_code):
    equipment = (
        Equipment.objects.filter(equipment_code=sheet_code)
        .select_related("line", "process")
        .first()
    )
    if not equipment:
        return {}
    return {
        "line_id": equipment.line_id,
        "line_code": equipment.line.line_code if equipment.line else "",
        "line_name": equipment.line.line_name if equipment.line else "",
        "process_id": equipment.process_id,
        "process_code": equipment.process.process_code if equipment.process else "",
        "process_name": equipment.process.process_name if equipment.process else "",
    }


def _is_frequency_required(frequency, operation_date, calendar):
    """頻度に応じて、operation_dateが該当日かを判定する"""
    if not frequency:
        return True

    freq = frequency.strip()
    PRESET_FREQUENCIES = {"始業時", "週初め", "週末", "月初め", "月末"}
    WEEKDAY_FREQUENCIES = {
        "月曜日": 0,
        "火曜日": 1,
        "水曜日": 2,
        "木曜日": 3,
        "金曜日": 4,
        "土曜日": 5,
        "日曜日": 6,
    }
    if freq in WEEKDAY_FREQUENCIES:
        return operation_date.weekday() == WEEKDAY_FREQUENCIES[freq]

    if freq not in PRESET_FREQUENCIES:
        return True

    calculator = WorkingDayCalculator(calendar)

    if freq == "始業時":
        return calculator.is_working_day(operation_date)

    if freq in ("週初め", "週末"):
        week_start = operation_date - timedelta(days=operation_date.weekday())
        week_end = week_start + timedelta(days=6)
        week_working_days = []
        cursor = week_start
        while cursor <= week_end:
            if calculator.is_working_day(cursor):
                week_working_days.append(cursor)
            cursor += timedelta(days=1)
        if not week_working_days:
            return False
        if freq == "週初め":
            return operation_date == week_working_days[0]
        else:
            return operation_date == week_working_days[-1]

    if freq in ("月初め", "月末"):
        month_start = operation_date.replace(day=1)
        next_month = (month_start + timedelta(days=32)).replace(day=1)
        month_end = next_month - timedelta(days=1)
        month_working_days = []
        cursor = month_start
        while cursor <= month_end:
            if calculator.is_working_day(cursor):
                month_working_days.append(cursor)
            cursor += timedelta(days=1)
        if not month_working_days:
            return False
        if freq == "月初め":
            return operation_date == month_working_days[0]
        else:
            return operation_date == month_working_days[-1]

    return True


def _build_default_record_payload(template, operation_date, section_type, user, request):
    calendar = _get_calendar_for_equipment(template.sheet_code)
    items = (
        template.items.filter(section_type=section_type, is_active=True)
        .prefetch_related("attachments")
        .order_by("display_order", "id")
    )
    results = []
    for index, item in enumerate(items, start=1):
        attachment_serializer = EquipmentInspectionItemAttachmentSerializer(
            item.attachments.all(),
            many=True,
            context={"request": request},
        )
        is_frequency_applicable = _is_frequency_required(item.frequency, operation_date, calendar)
        required = item.is_required and is_frequency_applicable
        results.append(
            {
                "id": None,
                "item": item.id,
                "display_order": item.display_order or index,
                "inspection_no": item.inspection_no,
                "item_name": item.item_name,
                "standard": item.standard,
                "frequency": item.frequency,
                "method": item.method,
                "confirmation_method": item.confirmation_method,
                "record_type": item.record_type,
                "unit": item.unit,
                "criteria": item.criteria,
                "is_required": required,
                "is_frequency_applicable": is_frequency_applicable,
                "numeric_value": None,
                "text_value": "",
                "judgement": "",
                "comment": "",
                "measured_at": None,
                "reference_attachments": attachment_serializer.data,
            }
        )

    return {
        "id": None,
        "template": template.id,
        "sheet_code": template.sheet_code,
        "sheet_name": template.sheet_name,
        "template_title": template.title,
        "template_version": template.version,
        "operation_date": operation_date.isoformat(),
        "section_type": section_type,
        "operator": getattr(user, "id", None),
        "operator_name": _display_name(user),
        "status": EquipmentInspectionRecord.STATUS_DRAFT,
        "overall_result": "",
        "memo": "",
        "completed_at": None,
        "created_at": None,
        "updated_at": None,
        "result_count": len(results),
        "ng_count": 0,
        "missing_required_count": sum(1 for item in results if item["is_required"]),
        "results": results,
    }


def _log_workflow(template, action, actor=None, from_status="", to_status="", comment=""):
    return EquipmentInspectionWorkflowLog.objects.create(
        template=template,
        action=action,
        actor=actor if actor and getattr(actor, "id", None) else None,
        from_status=from_status or "",
        to_status=to_status or "",
        comment=comment or "",
    )


def _current_local_date():
    now = timezone.now()
    if timezone.is_naive(now):
        return now.date()
    return timezone.localtime(now).date()


def _task_due_date(template):
    return template.effective_from or _current_local_date()


def _create_notification(title, description, users, operator_name=""):
    user_ids = sorted({user.id for user in users if getattr(user, "id", None)})
    if not user_ids:
        return

    today = _current_local_date()
    notification = Notification.objects.create(
        title=str(title or "")[:200],
        category="品質",
        domain="QUALITY_EQUIPMENT_INSPECTION",
        valid_from=today,
        valid_to=today + timedelta(days=14),
        display_order=0,
        description=str(description or ""),
        operator_name=str(operator_name or "").strip() or "system",
    )
    notification.target_users.set(user_ids)


def _find_record_leaders(user):
    if not user or not getattr(user, "id", None):
        return []

    profile = getattr(user, "profile", None)
    unit_id = getattr(profile, "unit_id", None) if profile else None
    if not unit_id:
        return []

    user_model = get_user_model()
    return list(
        user_model.objects.filter(is_active=True)
        .filter(build_leader_role_q(unit_id))
        .exclude(id=user.id)
        .select_related("profile")
        .distinct()
        .order_by("id")
    )


def _create_tasks_for_users(template, task_type, users, due_date=None):
    created_count = 0
    for user in users:
        if not getattr(user, "id", None):
            continue
        exists = EquipmentInspectionTask.objects.filter(
            template=template,
            task_type=task_type,
            assigned_to=user,
            status=EquipmentInspectionTask.STATUS_PENDING,
        ).exists()
        if exists:
            continue
        EquipmentInspectionTask.objects.create(
            template=template,
            task_type=task_type,
            assigned_to=user,
            status=EquipmentInspectionTask.STATUS_PENDING,
            due_date=due_date,
        )
        created_count += 1
    return created_count


def _mark_tasks_done(template, task_type):
    now = timezone.now()
    EquipmentInspectionTask.objects.filter(
        template=template,
        task_type=task_type,
        status=EquipmentInspectionTask.STATUS_PENDING,
    ).update(status=EquipmentInspectionTask.STATUS_DONE, done_at=now)


def _mark_all_pending_tasks_skipped(template):
    now = timezone.now()
    EquipmentInspectionTask.objects.filter(
        template=template,
        status=EquipmentInspectionTask.STATUS_PENDING,
    ).update(status=EquipmentInspectionTask.STATUS_SKIPPED, done_at=now)


def _auto_assign_workflow_users(creator):
    """
    自動判定ルール:
    - 班長: 作成者の所属班を担当している班長を優先し、いなければ同事業部の班長
    - 係長: 作成者と同じ係の係長を優先し、いなければ同事業部の係長
    - 部長: 同事業部の部長
    """
    if not creator or not getattr(creator, "id", None):
        return None, None, None

    profile = getattr(creator, "profile", None)
    department_id = getattr(profile, "department_id", None) if profile else None
    creator_division_id = getattr(profile, "division_id", None) if profile else None
    if not department_id:
        return None, None, None

    creator_rank = _role_rank(getattr(profile, "role", ""))
    creator_team_id = getattr(profile, "team_id", None) if profile else None
    creator_group_id = getattr(profile, "group_id", None) if profile else None

    user_model = get_user_model()
    candidates = list(
        user_model.objects.filter(
            is_active=True,
            profile__department_id=department_id,
        )
        .exclude(id=creator.id)
        .select_related("profile")
        .prefetch_related("profile__supervisor_teams")
    )

    if not candidates:
        return None, None, None

    supervisor_candidates = [
        user
        for user in candidates
        if can_act_as_supervisor(getattr(user, "profile", None), creator_team_id)
        and _role_rank(getattr(getattr(user, "profile", None), "role", "")) > creator_rank
    ]
    same_team_supervisors = [
        user
        for user in supervisor_candidates
        if creator_team_id
        and getattr(user, "profile", None)
        and can_act_as_supervisor(user.profile, creator_team_id)
    ]
    same_team_supervisors.sort(key=_reviewer_sort_key)
    supervisor_candidates.sort(key=_reviewer_sort_key)
    reviewer_user = (
        same_team_supervisors[0]
        if same_team_supervisors
        else (supervisor_candidates[0] if supervisor_candidates else None)
    )

    chief_candidates = [
        user
        for user in candidates
        if can_act_as_chief(getattr(user, "profile", None), creator_group_id)
        and _role_rank(getattr(getattr(user, "profile", None), "role", "")) > creator_rank
    ]
    same_group_chiefs = [
        user
        for user in chief_candidates
        if creator_group_id and can_act_as_chief(getattr(user, "profile", None), creator_group_id)
    ]
    same_group_chiefs.sort(key=_reviewer_sort_key)
    chief_candidates.sort(key=_reviewer_sort_key)
    chief_user = same_group_chiefs[0] if same_group_chiefs else (chief_candidates[0] if chief_candidates else None)

    manager_candidates = [
        user
        for user in candidates
        if can_act_as_manager(getattr(user, "profile", None), creator_division_id)
        and _role_rank(getattr(getattr(user, "profile", None), "role", "")) > creator_rank
    ]
    manager_candidates.sort(key=_reviewer_sort_key)
    approver_user = manager_candidates[0] if manager_candidates else None

    return reviewer_user, chief_user, approver_user


def _workflow_stage_sequence(template):
    stages = []
    if template.reviewer_user_id:
        stages.append(
            (
                EquipmentInspectionTemplate.STATUS_SUPERVISOR_PENDING,
                EquipmentInspectionTask.TASK_SUPERVISOR_REVIEW,
                template.reviewer_user,
                "班長確認",
            )
        )
    if template.chief_user_id:
        stages.append(
            (
                EquipmentInspectionTemplate.STATUS_CHIEF_PENDING,
                EquipmentInspectionTask.TASK_CHIEF_REVIEW,
                template.chief_user,
                "係長承認",
            )
        )
    if template.approver_user_id:
        stages.append(
            (
                EquipmentInspectionTemplate.STATUS_MANAGER_PENDING,
                EquipmentInspectionTask.TASK_MANAGER_APPROVE,
                template.approver_user,
                "部長承認",
            )
        )
    return stages


def _find_stage(template, current_status=""):
    for stage in _workflow_stage_sequence(template):
        if stage[0] == current_status:
            return stage
    return None


def _next_stage(template, current_status=None):
    stages = _workflow_stage_sequence(template)
    if not stages:
        return None
    if not current_status:
        return stages[0]
    for index, stage in enumerate(stages):
        if stage[0] == current_status:
            if index + 1 < len(stages):
                return stages[index + 1]
            return None
    return None


def _ensure_workflow_users(template, persist=False, force=False):
    if not template or not template.created_by_id:
        return template
    if template.status == EquipmentInspectionTemplate.STATUS_DRAFT:
        return template

    reviewer_user, chief_user, approver_user = _auto_assign_workflow_users(template.created_by)
    update_fields = []
    if force and template.reviewer_user_id != getattr(reviewer_user, "id", None):
        template.reviewer_user = reviewer_user
        update_fields.append("reviewer_user")
    elif not template.reviewer_user_id and reviewer_user:
        template.reviewer_user = reviewer_user
        update_fields.append("reviewer_user")
    if force and template.chief_user_id != getattr(chief_user, "id", None):
        template.chief_user = chief_user
        update_fields.append("chief_user")
    elif not template.chief_user_id and chief_user:
        template.chief_user = chief_user
        update_fields.append("chief_user")
    if force and template.approver_user_id != getattr(approver_user, "id", None):
        template.approver_user = approver_user
        update_fields.append("approver_user")
    elif not template.approver_user_id and approver_user:
        template.approver_user = approver_user
        update_fields.append("approver_user")

    if persist and update_fields:
        template.save(update_fields=update_fields + ["updated_at"])
    return template


class EquipmentInspectionTemplateViewSet(viewsets.ModelViewSet):
    queryset = (
        EquipmentInspectionTemplate.objects.all()
        .select_related(
            "created_by",
            "reviewer_user",
            "chief_user",
            "approver_user",
            "reviewed_by",
            "chief_reviewed_by",
            "approved_by",
        )
        .prefetch_related("items__attachments", "workflow_logs__actor")
    )
    serializer_class = EquipmentInspectionTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        status_value = self.request.query_params.get("status")
        sheet_code = self.request.query_params.get("sheet_code")
        for_operation = str(self.request.query_params.get("for_operation", "")).lower()

        if status_value:
            queryset = queryset.filter(status=status_value)
        if sheet_code:
            queryset = queryset.filter(sheet_code=sheet_code)
        version_value = self.request.query_params.get("version")
        if version_value:
            queryset = queryset.filter(version=version_value)
        if for_operation in ("1", "true", "yes"):
            queryset = queryset.filter(
                status=EquipmentInspectionTemplate.STATUS_APPROVED,
                is_active=True,
            )
        process_id = self.request.query_params.get("process_id")
        line_id = self.request.query_params.get("line_id")
        if process_id:
            queryset = queryset.filter(processes__id=process_id)
        elif line_id:
            queryset = queryset.filter(lines__id=line_id)
        return queryset.distinct()

    def get_object(self):
        instance = super().get_object()
        return _ensure_workflow_users(instance, persist=True)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        template_id = response.data.get("id")
        if template_id:
            template = EquipmentInspectionTemplate.objects.filter(id=template_id).first()
            if template:
                _log_workflow(
                    template=template,
                    action=EquipmentInspectionWorkflowLog.ACTION_CREATED,
                    actor=request.user,
                    from_status="",
                    to_status=template.status,
                    comment="テンプレート作成",
                )
        return response

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status in (
            EquipmentInspectionTemplate.STATUS_SUPERVISOR_PENDING,
            EquipmentInspectionTemplate.STATUS_CHIEF_PENDING,
            EquipmentInspectionTemplate.STATUS_MANAGER_PENDING,
            EquipmentInspectionTemplate.STATUS_APPROVED,
        ):
            return Response(
                {"detail": "確認/承認中または承認済みのため更新できません。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        prev_status = instance.status
        response = super().update(request, *args, **kwargs)
        instance.refresh_from_db()
        _log_workflow(
            template=instance,
            action=EquipmentInspectionWorkflowLog.ACTION_UPDATED,
            actor=request.user,
            from_status=prev_status,
            to_status=instance.status,
            comment="テンプレート更新",
        )
        return response

    @action(
        detail=False,
        methods=["post"],
        parser_classes=[parsers.MultiPartParser, parsers.FormParser],
    )
    def upload_attachment_image(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "ファイルがありません。"}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(file_obj.name)[1] or ""
        filename = f"equipment_inspection_attachments/{uuid.uuid4().hex}{ext}"
        saved_path = default_storage.save(filename, file_obj)
        image_url = _build_media_url(default_storage.url(saved_path))
        return Response({"image_url": image_url}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def submit_for_review(self, request, pk=None):
        template = self.get_object()
        if template.status not in (
            EquipmentInspectionTemplate.STATUS_DRAFT,
            EquipmentInspectionTemplate.STATUS_REJECTED,
        ):
            return Response(
                {"detail": "下書き/差戻しのテンプレートのみ確認依頼できます。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        creator_user = template.created_by or request.user
        reviewer_user, chief_user, approver_user = _auto_assign_workflow_users(creator_user)
        if not approver_user:
            return Response(
                {"detail": "部長担当が見つかりません。組織設定を確認してください。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_comment = str(request.data.get("comment") or "").strip()

        with transaction.atomic():
            prev_status = template.status
            if not template.created_by_id:
                template.created_by = request.user

            # 初回提出時のみスナップショット未設定なら保存（差し戻し再提出時は reject 時点の基準を維持）
            if not template.submitted_items_snapshot:
                snapshot = list(
                    template.items.order_by("section_type", "display_order").values(
                        "section_type", "display_order", "inspection_no",
                        "item_name", "standard", "frequency", "method",
                        "record_type", "unit", "criteria", "is_required", "is_active",
                    )
                )
                template.submitted_items_snapshot = snapshot

            template.reviewer_user = reviewer_user
            template.chief_user = chief_user
            template.approver_user = approver_user
            first_stage = _next_stage(template)
            if not first_stage:
                return Response(
                    {"detail": "承認経路が見つかりません。組織設定を確認してください。"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            template.status = first_stage[0]
            template.rejection_comment = ""
            template.reviewed_by = None
            template.chief_reviewed_by = None
            template.reviewed_at = None
            template.chief_reviewed_at = None
            template.approved_by = None
            template.approved_at = None
            template.save()
            _mark_all_pending_tasks_skipped(template)
            _create_tasks_for_users(
                template=template,
                task_type=first_stage[1],
                users=[first_stage[2]],
                due_date=_task_due_date(template),
            )

            assignee_info = (
                f"班長: {_display_name(reviewer_user) or '未判定'} / "
                f"係長: {_display_name(chief_user) or '未判定'} / "
                f"部長: {_display_name(approver_user) or '未判定'}"
            )
            comment = f"{assignee_info}\n{user_comment}" if user_comment else assignee_info
            _log_workflow(
                template=template,
                action=EquipmentInspectionWorkflowLog.ACTION_SUBMITTED,
                actor=request.user,
                from_status=prev_status,
                to_status=template.status,
                comment=comment,
            )
            notification_desc = f"{first_stage[3]}待ちです。"
            if user_comment:
                notification_desc += f"\nコメント: {user_comment}"
            _create_notification(
                title=f"設備点検表 確認依頼: {template.sheet_code} v{template.version}",
                description=notification_desc,
                users=[first_stage[2]],
                operator_name=_display_name(request.user),
            )

        serializer = self.get_serializer(template)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        template = self.get_object()
        if template.status not in (
            EquipmentInspectionTemplate.STATUS_SUPERVISOR_PENDING,
            EquipmentInspectionTemplate.STATUS_CHIEF_PENDING,
        ):
            return Response(
                {"detail": "班長確認待ち/係長承認待ちのテンプレートのみ確認完了できます。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            prev_status = template.status
            current_stage = _find_stage(template, prev_status)
            if not current_stage:
                return Response(
                    {"detail": "現在の確認段階に対応するタスクが見つかりません。"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            now = timezone.now()
            action_name = EquipmentInspectionWorkflowLog.ACTION_SUPERVISOR_REVIEWED
            comment = "班長確認完了"
            if prev_status == EquipmentInspectionTemplate.STATUS_SUPERVISOR_PENDING:
                template.reviewed_by = request.user
                template.reviewed_at = now
            else:
                template.chief_reviewed_by = request.user
                template.chief_reviewed_at = now
                action_name = EquipmentInspectionWorkflowLog.ACTION_CHIEF_REVIEWED
                comment = "係長承認完了"

            next_stage = _next_stage(template, prev_status)
            if not next_stage:
                _, chief_user, approver_user = _auto_assign_workflow_users(template.created_by or request.user)
                if not template.chief_user_id and chief_user:
                    template.chief_user = chief_user
                if not template.approver_user_id and approver_user:
                    template.approver_user = approver_user
                next_stage = _next_stage(template, prev_status)
            if not next_stage:
                return Response(
                    {"detail": "次の承認経路が見つかりません。組織設定を確認してください。"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            template.status = next_stage[0]
            template.save()
            _mark_tasks_done(template, current_stage[1])
            _create_tasks_for_users(
                template=template,
                task_type=next_stage[1],
                users=[next_stage[2]],
                due_date=_task_due_date(template),
            )
            _log_workflow(
                template=template,
                action=action_name,
                actor=request.user,
                from_status=prev_status,
                to_status=template.status,
                comment=comment,
            )
            _create_notification(
                title=f"設備点検表 承認依頼: {template.sheet_code} v{template.version}",
                description=f"{comment}。{next_stage[3]}待ちです。",
                users=[next_stage[2]],
                operator_name=_display_name(request.user),
            )

        serializer = self.get_serializer(template)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        template = self.get_object()
        if template.status != EquipmentInspectionTemplate.STATUS_MANAGER_PENDING:
            return Response(
                {"detail": "部長承認待ちのテンプレートのみ承認できます。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            prev_status = template.status
            EquipmentInspectionTemplate.objects.filter(
                sheet_code=template.sheet_code,
                is_active=True,
            ).exclude(id=template.id).update(is_active=False)

            template.status = EquipmentInspectionTemplate.STATUS_APPROVED
            template.approved_by = request.user
            template.approved_at = timezone.now()
            template.is_active = True
            template.save()
            _mark_tasks_done(template, EquipmentInspectionTask.TASK_MANAGER_APPROVE)
            _log_workflow(
                template=template,
                action=EquipmentInspectionWorkflowLog.ACTION_APPROVED,
                actor=request.user,
                from_status=prev_status,
                to_status=template.status,
                comment="部長承認完了",
            )
            if template.created_by_id:
                _create_notification(
                    title=f"設備点検表 承認完了: {template.sheet_code} v{template.version}",
                    description="設備点検表が承認されました。",
                    users=[template.created_by],
                    operator_name=_display_name(request.user),
                )

        serializer = self.get_serializer(template)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        template = self.get_object()
        if template.status not in (
            EquipmentInspectionTemplate.STATUS_SUPERVISOR_PENDING,
            EquipmentInspectionTemplate.STATUS_CHIEF_PENDING,
            EquipmentInspectionTemplate.STATUS_MANAGER_PENDING,
        ):
            return Response(
                {"detail": "班長確認待ち/係長承認待ち/部長承認待ちのテンプレートのみ差戻しできます。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comment = str(request.data.get("comment") or "").strip()
        with transaction.atomic():
            prev_status = template.status
            # 差し戻し時点の項目を次回再提出の比較基準として保存する
            template.submitted_items_snapshot = list(
                template.items.order_by("section_type", "display_order").values(
                    "section_type", "display_order", "inspection_no",
                    "item_name", "standard", "frequency", "method",
                    "record_type", "unit", "criteria", "is_required", "is_active",
                )
            )
            template.status = EquipmentInspectionTemplate.STATUS_REJECTED
            template.rejection_comment = comment
            template.save()
            _mark_all_pending_tasks_skipped(template)
            _log_workflow(
                template=template,
                action=EquipmentInspectionWorkflowLog.ACTION_REJECTED,
                actor=request.user,
                from_status=prev_status,
                to_status=template.status,
                comment=comment,
            )
            if template.created_by_id:
                _create_notification(
                    title=f"設備点検表 差戻し: {template.sheet_code} v{template.version}",
                    description=comment or "設備点検表が差戻しされました。",
                    users=[template.created_by],
                    operator_name=_display_name(request.user),
                )
                _create_tasks_for_users(
                    template=template,
                    task_type=EquipmentInspectionTask.TASK_CREATOR_FIX,
                    users=[template.created_by],
                    due_date=_task_due_date(template),
                )

        serializer = self.get_serializer(template)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def revise(self, request, pk=None):
        """承認済みテンプレートを改訂（新版作成）する。"""
        template = self.get_object()
        if template.status != EquipmentInspectionTemplate.STATUS_APPROVED:
            return Response(
                {"detail": "承認済みのテンプレートのみ改訂できます。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_version = (
            EquipmentInspectionTemplate.objects.filter(sheet_code=template.sheet_code)
            .order_by("-version")
            .values_list("version", flat=True)
            .first()
            or template.version
        ) + 1

        with transaction.atomic():
            reviewer_user, chief_user, approver_user = _auto_assign_workflow_users(request.user)
            new_template = EquipmentInspectionTemplate.objects.create(
                sheet_code=template.sheet_code,
                sheet_name=template.sheet_name,
                title=template.title,
                source_sheet_name=template.source_sheet_name,
                revision_date=None,
                revision_notes="",
                effective_from=None,
                version=new_version,
                status=EquipmentInspectionTemplate.STATUS_DRAFT,
                is_active=template.is_active,
                created_by=request.user,
                reviewer_user=reviewer_user,
                chief_user=chief_user,
                approver_user=approver_user,
                measurement_months=template.measurement_months,
                measurement_schedule_type=template.measurement_schedule_type,
                measurement_weekdays=template.measurement_weekdays,
            )
            # 工程・ライン引き継ぎ
            new_template.processes.set(template.processes.all())
            new_template.lines.set(template.lines.all())

            # 点検項目と付表を複製
            for item in template.items.all():
                attachments = list(item.attachments.all())
                item.pk = None
                item.id = None
                item.template = new_template
                item.save()
                for att in attachments:
                    att.pk = None
                    att.id = None
                    att.item = item
                    att.save()

            _log_workflow(
                template=new_template,
                action=EquipmentInspectionWorkflowLog.ACTION_CREATED,
                actor=request.user,
                from_status="",
                to_status=new_template.status,
                comment=f"v{template.version} からの改訂",
            )

        serializer = self.get_serializer(new_template)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def workflow_logs(self, request, pk=None):
        template = self.get_object()
        logs = template.workflow_logs.select_related("actor").all()
        serializer = EquipmentInspectionWorkflowLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def prepare_test(self, request, pk=None):
        template = self.get_object()
        section_type = str(
            request.query_params.get("section_type") or EquipmentInspectionItem.SECTION_DAILY
        ).strip().upper()
        from datetime import date as _date
        operation_date = _date.today()
        payload = _build_default_record_payload(
            template, operation_date, section_type, request.user, request,
        )
        return Response({"record": payload})


class EquipmentInspectionTaskListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = EquipmentInspectionTask.objects.select_related("template", "assigned_to").order_by(
            "status",
            "due_date",
            "-created_at",
        )

        assigned_to_me = request.query_params.get("assigned_to_me", "true")
        if str(assigned_to_me).lower() in ("true", "1", "yes"):
            queryset = queryset.filter(assigned_to=request.user)

        task_type = request.query_params.get("task_type")
        status_code = request.query_params.get("status")
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        if status_code:
            queryset = queryset.filter(status=status_code)

        data = []
        for task in queryset[:200]:
            try:
                template = getattr(task, "template", None)
                data.append({
                    "id": task.id,
                    "template": task.template_id,
                    "sheet_code": getattr(template, "sheet_code", "") or "",
                    "sheet_name": getattr(template, "sheet_name", "") or "",
                    "template_title": getattr(template, "title", "") or "",
                    "template_version": getattr(template, "version", None),
                    "template_status": getattr(template, "status", "") or "",
                    "task_type": task.task_type,
                    "assigned_to": task.assigned_to_id,
                    "assigned_to_username": getattr(task.assigned_to, "username", "") or "",
                    "assigned_to_name": _display_name(task.assigned_to),
                    "status": task.status,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "done_at": task.done_at.isoformat() if task.done_at else None,
                    "module_code": "QUALITY",
                    "module_label": "品質",
                    "task_category": "EQUIPMENT_INSPECTION",
                    "task_category_label": "設備点検表",
                })
            except Exception:
                logger.exception("設備点検タスク整形に失敗しました: task_id=%s", getattr(task, "id", None))
        return Response(data)


class EquipmentInspectionRecordViewSet(viewsets.ModelViewSet):
    queryset = (
        EquipmentInspectionRecord.objects.all()
        .select_related("template", "operator")
        .prefetch_related("results__item__attachments")
    )
    serializer_class = EquipmentInspectionRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        sheet_code = self.request.query_params.get("sheet_code")
        operation_date = _parse_date(self.request.query_params.get("operation_date"))
        month_value = _parse_month(self.request.query_params.get("month"))
        section_type = str(self.request.query_params.get("section_type") or "").strip().upper()
        status_value = str(self.request.query_params.get("status") or "").strip().upper()

        if sheet_code:
            queryset = queryset.filter(sheet_code=sheet_code)
        if operation_date:
            queryset = queryset.filter(operation_date=operation_date)
        if month_value:
            queryset = queryset.filter(
                operation_date__gte=_month_start(month_value),
                operation_date__lte=_month_end(month_value),
            )
        if section_type:
            queryset = queryset.filter(section_type=section_type)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset

    def _ng_result_items_from_record(self, record):
        items = []
        for result in record.results.all():
            if str(result.judgement or "").strip().upper() != "NG":
                continue
            key = f"{result.display_order}:{str(result.item_name or '').strip()}"
            items.append((key, str(result.item_name or "").strip() or f"{result.display_order}行目"))
        return items

    def _reload_record(self, record):
        return (
            EquipmentInspectionRecord.objects.select_related("template", "operator")
            .prefetch_related("results__item__attachments")
            .get(pk=record.pk)
        )

    def _notify_leader_if_needed(self, record, previous_status="", previous_ng_keys=None):
        if record.status != EquipmentInspectionRecord.STATUS_COMPLETED:
            return

        current_ng_items = self._ng_result_items_from_record(record)
        if not current_ng_items:
            return

        previous_ng_keys = set(previous_ng_keys or [])
        if previous_status == EquipmentInspectionRecord.STATUS_COMPLETED:
            notify_items = [name for key, name in current_ng_items if key not in previous_ng_keys]
            if not notify_items:
                return
        else:
            notify_items = [name for _, name in current_ng_items]

        leaders = _find_record_leaders(record.operator)
        if not leaders:
            return

        item_names = " / ".join(notify_items[:5])
        if len(notify_items) > 5:
            item_names = f"{item_names} ほか{len(notify_items) - 5}件"

        _create_notification(
            title=f"設備点検 NG通知: {record.sheet_code} {record.operation_date:%Y-%m-%d}",
            description=(
                f"{_section_type_label(record.section_type)}でNGが登録されました。"
                f"設備: {record.sheet_code} {record.sheet_name} / "
                f"実施者: {_display_name(record.operator) or '-'} / "
                f"対象: {item_names}"
            ),
            users=leaders,
            operator_name=_display_name(record.operator),
        )

    def create(self, request, *args, **kwargs):
        sheet_code = str(request.data.get("sheet_code") or "").strip()
        operation_date = _parse_date(request.data.get("operation_date"))
        if not sheet_code or not operation_date:
            return Response(
                {"detail": "設備コードと点検日が必要です。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if _monthly_confirmation_exists(sheet_code, operation_date):
            return Response(
                {"detail": "月間班長確認済みのため更新できません。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        record = self._reload_record(record)
        self._notify_leader_if_needed(record, previous_status="", previous_ng_keys=set())
        headers = self.get_success_headers(serializer.data)
        response_serializer = self.get_serializer(record)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if _monthly_confirmation_exists(instance.sheet_code, instance.operation_date):
            return Response(
                {"detail": "月間班長確認済みのため更新できません。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        previous_status = instance.status
        previous_ng_keys = {key for key, _ in self._ng_result_items_from_record(instance)}
        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        record = self._reload_record(record)
        self._notify_leader_if_needed(record, previous_status=previous_status, previous_ng_keys=previous_ng_keys)
        response_serializer = self.get_serializer(record)
        return Response(response_serializer.data)

    @action(detail=False, methods=["get"])
    def prepare(self, request):
        sheet_code = str(request.query_params.get("sheet_code") or "").strip()
        operation_date = _parse_date(request.query_params.get("operation_date"))
        section_type = str(
            request.query_params.get("section_type") or EquipmentInspectionItem.SECTION_DAILY
        ).strip().upper()

        if not sheet_code or not operation_date:
            return Response(
                {"detail": "設備コードと点検日を指定してください。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record = (
            EquipmentInspectionRecord.objects.filter(
                sheet_code=sheet_code,
                operation_date=operation_date,
                section_type=section_type,
            )
            .select_related("template", "operator")
            .prefetch_related("results__item__attachments")
            .first()
        )
        current_template = _active_operation_template(sheet_code)
        locked = _monthly_confirmation_exists(sheet_code, operation_date)

        if record:
            serializer = self.get_serializer(record)
            return Response(
                {
                    "is_locked": locked,
                    "current_template": _template_summary(current_template or record.template),
                    "equipment_context": _equipment_context(sheet_code),
                    "record": serializer.data,
                }
            )

        if not current_template:
            return Response(
                {"detail": "承認済みテンプレートが見つかりません。"},
                status=status.HTTP_404_NOT_FOUND,
            )

        payload = _build_default_record_payload(
            current_template,
            operation_date,
            section_type,
            request.user,
            request,
        )
        return Response(
            {
                "is_locked": locked,
                "current_template": _template_summary(current_template),
                "equipment_context": _equipment_context(sheet_code),
                "record": payload,
            }
        )

    @action(detail=False, methods=["get"])
    def monthly_overview(self, request):
        sheet_code = str(request.query_params.get("sheet_code") or "").strip()
        month_value = _parse_month(request.query_params.get("month"))
        if not sheet_code or not month_value:
            return Response(
                {"detail": "設備コードと対象月を指定してください。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        month_first = _month_start(month_value)
        month_last = _month_end(month_value)
        records = list(
            EquipmentInspectionRecord.objects.filter(
                sheet_code=sheet_code,
                operation_date__gte=month_first,
                operation_date__lte=month_last,
            )
            .select_related("template", "operator")
            .prefetch_related("results__item__attachments")
            .order_by("operation_date", "section_type", "id")
        )
        confirmations = list(
            EquipmentInspectionConfirmation.objects.filter(
                sheet_code=sheet_code,
                target_month=month_first,
            )
            .select_related("confirmed_by")
            .order_by("confirm_type", "week_index", "id")
        )
        current_template = _active_operation_template(sheet_code)
        record_serializer = self.get_serializer(records, many=True)
        confirmation_serializer = EquipmentInspectionConfirmationSerializer(confirmations, many=True)
        sheet_name = (
            (current_template.sheet_name if current_template else "")
            or (records[0].sheet_name if records else "")
            or str(request.query_params.get("sheet_name") or "")
        )

        daily_records = [item for item in record_serializer.data if item["section_type"] == EquipmentInspectionItem.SECTION_DAILY]
        quarterly_records = [
            item for item in record_serializer.data if item["section_type"] == EquipmentInspectionItem.SECTION_QUARTERLY
        ]
        return Response(
            {
                "sheet_code": sheet_code,
                "sheet_name": sheet_name,
                "month": month_first.strftime("%Y-%m"),
                "is_locked": _monthly_confirmation_exists(sheet_code, month_first),
                "current_template": _template_summary(current_template),
                "weeks": _build_month_weeks(month_first),
                "daily_records": daily_records,
                "quarterly_records": quarterly_records,
                "confirmations": confirmation_serializer.data,
            }
        )


class EquipmentInspectionConfirmationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EquipmentInspectionConfirmation.objects.all().select_related("confirmed_by")
    serializer_class = EquipmentInspectionConfirmationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        sheet_code = self.request.query_params.get("sheet_code")
        month_value = _parse_month(self.request.query_params.get("month"))
        confirm_type = str(self.request.query_params.get("confirm_type") or "").strip().upper()

        if sheet_code:
            queryset = queryset.filter(sheet_code=sheet_code)
        if month_value:
            queryset = queryset.filter(target_month=_month_start(month_value))
        if confirm_type:
            queryset = queryset.filter(confirm_type=confirm_type)
        return queryset

    @action(detail=False, methods=["post"])
    def upsert(self, request):
        sheet_code = str(request.data.get("sheet_code") or "").strip()
        sheet_name = str(request.data.get("sheet_name") or "").strip()
        target_month = _parse_month(request.data.get("target_month"))
        confirm_type = str(request.data.get("confirm_type") or "").strip().upper()
        week_index = int(request.data.get("week_index") or 0)
        comment = str(request.data.get("comment") or "").strip()

        if not sheet_code or not target_month or confirm_type not in {
            EquipmentInspectionConfirmation.TYPE_WEEKLY_LEADER,
            EquipmentInspectionConfirmation.TYPE_MONTHLY_CHIEF,
        }:
            return Response(
                {"detail": "設備コード・対象月・確認種別は必須です。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_month = _month_start(target_month)
        if confirm_type == EquipmentInspectionConfirmation.TYPE_MONTHLY_CHIEF:
            week_index = 0
        elif week_index <= 0:
            return Response(
                {"detail": "週間リーダ確認は週番号が必要です。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_locked = _monthly_confirmation_exists(sheet_code, target_month)
        if is_locked and confirm_type != EquipmentInspectionConfirmation.TYPE_MONTHLY_CHIEF:
            return Response(
                {"detail": "月間班長確認済みのため週間リーダ確認は更新できません。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        defaults = {
            "sheet_name": sheet_name,
            "comment": comment,
            "confirmed_by": request.user,
            "confirmed_at": timezone.now(),
        }
        confirmation, _ = EquipmentInspectionConfirmation.objects.get_or_create(
            sheet_code=sheet_code,
            target_month=target_month,
            confirm_type=confirm_type,
            week_index=week_index,
            defaults=defaults,
        )
        confirmation.sheet_name = sheet_name or confirmation.sheet_name
        confirmation.comment = comment
        confirmation.confirmed_by = request.user
        confirmation.confirmed_at = timezone.now()
        confirmation.save()

        serializer = self.get_serializer(confirmation)
        return Response(serializer.data)
