from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import EquipmentInspectionTemplate, EquipmentInspectionWorkflowLog
from .serializers import (
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


def _role_rank(role_value):
    return ROLE_RANK.get(str(role_value or "").strip(), 0)


def _display_name(user):
    if not user:
        return ""
    full_name = f"{(user.last_name or '').strip()} {(user.first_name or '').strip()}".strip()
    if full_name:
        return full_name
    return (user.username or user.email or "").strip()


def _log_workflow(template, action, actor=None, from_status="", to_status="", comment=""):
    return EquipmentInspectionWorkflowLog.objects.create(
        template=template,
        action=action,
        actor=actor if actor and getattr(actor, "id", None) else None,
        from_status=from_status or "",
        to_status=to_status or "",
        comment=comment or "",
    )


def _auto_assign_review_and_approver(creator):
    """
    自動判定ルール（暫定）:
    - 確認者: 作成者と同部署で、作成者より上位役割の最小ランク
    - 承認者: 作成者と同部署で、chief/manager の最大ランク（部課長想定）
    """
    if not creator or not getattr(creator, "id", None):
        return None, None

    profile = getattr(creator, "profile", None)
    department_id = getattr(profile, "department_id", None) if profile else None
    if not department_id:
        return None, None

    creator_rank = _role_rank(getattr(profile, "role", ""))
    user_model = get_user_model()
    candidates = list(
        user_model.objects.filter(
            is_active=True,
            profile__department_id=department_id,
        )
        .exclude(id=creator.id)
        .select_related("profile")
    )

    if not candidates:
        return None, None

    reviewer_candidates = [
        u
        for u in candidates
        if _role_rank(getattr(getattr(u, "profile", None), "role", "")) > creator_rank
        and getattr(getattr(u, "profile", None), "role", "") in ("supervisor", "chief", "manager")
    ]
    reviewer_candidates.sort(
        key=lambda u: (
            _role_rank(getattr(getattr(u, "profile", None), "role", "")),
            u.id,
        )
    )
    reviewer_user = reviewer_candidates[0] if reviewer_candidates else None

    approver_candidates = [
        u
        for u in candidates
        if getattr(getattr(u, "profile", None), "role", "") in ("chief", "manager")
    ]
    approver_candidates.sort(
        key=lambda u: (
            -_role_rank(getattr(getattr(u, "profile", None), "role", "")),
            u.id,
        )
    )
    approver_user = approver_candidates[0] if approver_candidates else None

    if reviewer_user and approver_user and reviewer_user.id == approver_user.id:
        alt = [u for u in approver_candidates if u.id != reviewer_user.id]
        if alt:
            approver_user = alt[0]

    if approver_user is None and reviewer_user is not None:
        approver_user = reviewer_user

    return reviewer_user, approver_user


class EquipmentInspectionTemplateViewSet(viewsets.ModelViewSet):
    queryset = (
        EquipmentInspectionTemplate.objects.all()
        .select_related(
            "created_by",
            "reviewer_user",
            "approver_user",
            "reviewed_by",
            "approved_by",
        )
        .prefetch_related("items", "workflow_logs__actor")
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
        if for_operation in ("1", "true", "yes"):
            queryset = queryset.filter(
                status=EquipmentInspectionTemplate.STATUS_APPROVED,
                is_active=True,
            )
        return queryset

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
            EquipmentInspectionTemplate.STATUS_REVIEW_PENDING,
            EquipmentInspectionTemplate.STATUS_APPROVAL_PENDING,
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

        with transaction.atomic():
            prev_status = template.status
            if not template.created_by_id:
                template.created_by = request.user

            reviewer_user, approver_user = _auto_assign_review_and_approver(template.created_by or request.user)
            template.reviewer_user = reviewer_user
            template.approver_user = approver_user
            template.status = EquipmentInspectionTemplate.STATUS_REVIEW_PENDING
            template.rejection_comment = ""
            template.reviewed_by = None
            template.reviewed_at = None
            template.approved_by = None
            template.approved_at = None
            template.save()

            comment = (
                f"確認担当: {_display_name(reviewer_user) or '未判定'} / "
                f"承認担当: {_display_name(approver_user) or '未判定'}"
            )
            _log_workflow(
                template=template,
                action=EquipmentInspectionWorkflowLog.ACTION_SUBMITTED,
                actor=request.user,
                from_status=prev_status,
                to_status=template.status,
                comment=comment,
            )

        serializer = self.get_serializer(template)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        template = self.get_object()
        if template.status != EquipmentInspectionTemplate.STATUS_REVIEW_PENDING:
            return Response(
                {"detail": "確認待ちのテンプレートのみ確認完了できます。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            prev_status = template.status
            template.status = EquipmentInspectionTemplate.STATUS_APPROVAL_PENDING
            template.reviewed_by = request.user
            template.reviewed_at = timezone.now()
            if not template.approver_user_id:
                _, approver_user = _auto_assign_review_and_approver(template.created_by or request.user)
                template.approver_user = approver_user
            template.save()
            _log_workflow(
                template=template,
                action=EquipmentInspectionWorkflowLog.ACTION_REVIEWED,
                actor=request.user,
                from_status=prev_status,
                to_status=template.status,
                comment="確認完了",
            )

        serializer = self.get_serializer(template)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        template = self.get_object()
        if template.status != EquipmentInspectionTemplate.STATUS_APPROVAL_PENDING:
            return Response(
                {"detail": "承認待ちのテンプレートのみ承認できます。"},
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
            _log_workflow(
                template=template,
                action=EquipmentInspectionWorkflowLog.ACTION_APPROVED,
                actor=request.user,
                from_status=prev_status,
                to_status=template.status,
                comment="承認完了",
            )

        serializer = self.get_serializer(template)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        template = self.get_object()
        if template.status not in (
            EquipmentInspectionTemplate.STATUS_REVIEW_PENDING,
            EquipmentInspectionTemplate.STATUS_APPROVAL_PENDING,
        ):
            return Response(
                {"detail": "確認待ち/承認待ちのテンプレートのみ差戻しできます。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comment = str(request.data.get("comment") or "").strip()
        with transaction.atomic():
            prev_status = template.status
            template.status = EquipmentInspectionTemplate.STATUS_REJECTED
            template.rejection_comment = comment
            template.save()
            _log_workflow(
                template=template,
                action=EquipmentInspectionWorkflowLog.ACTION_REJECTED,
                actor=request.user,
                from_status=prev_status,
                to_status=template.status,
                comment=comment,
            )

        serializer = self.get_serializer(template)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def workflow_logs(self, request, pk=None):
        template = self.get_object()
        logs = template.workflow_logs.select_related("actor").all()
        serializer = EquipmentInspectionWorkflowLogSerializer(logs, many=True)
        return Response(serializer.data)
