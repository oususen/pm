import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import generics, parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from masters.models import Line, Process, Product
from production.models import ProductionOrder

from .models_checksheet import (
    ProductChecksheetBatch,
    ProductChecksheetField,
    ProductChecksheetPhoto,
    ProductChecksheetRecord,
    ProductChecksheetTask,
    ProductChecksheetTemplate,
    ProductChecksheetWorkflowLog,
)
from .serializers_checksheet import (
    ProductChecksheetBatchSerializer,
    ProductChecksheetPrepareSerializer,
    ProductChecksheetRecordSerializer,
    ProductChecksheetTemplateSerializer,
)
from .services_checksheet import (
    active_template_for,
    create_background_assets,
    generate_record_pdf,
    generate_template_preview_pdf,
    normalize_responses,
    now_naive,
    parse_responses_json,
    prepare_batch,
    recalc_shipment_sequence,
    save_template_fields,
    update_batch_status,
    validate_record_required_fields,
)


# ---------------------------------------------------------------------------
# ワークフローヘルパー（設備点検表と同パターン）
# ---------------------------------------------------------------------------

def _display_name(user):
    if not user:
        return ""
    full = f"{getattr(user, 'last_name', '') or ''} {getattr(user, 'first_name', '') or ''}".strip()
    return full or getattr(user, "username", "") or ""


def _role_rank(role):
    return {"worker": 1, "supervisor": 2, "chief": 3, "manager": 4, "admin": 5}.get(str(role or "").lower(), 0)


def _reviewer_sort_key(user):
    return getattr(user, "id", 0)


def _log_workflow(template, action, actor, from_status, to_status, comment=""):
    ProductChecksheetWorkflowLog.objects.create(
        template=template,
        action=action,
        from_status=from_status,
        to_status=to_status,
        actor=actor if actor and getattr(actor, "is_authenticated", False) else None,
        comment=comment,
    )


def _task_due_date(template):
    return (now_naive() + timedelta(days=7)).date()


def _create_tasks_for_users(template, task_type, users, due_date=None):
    created_count = 0
    for user in users:
        if not user:
            continue
        ProductChecksheetTask.objects.create(
            template=template,
            task_type=task_type,
            assigned_to=user,
            due_date=due_date,
        )
        created_count += 1
    return created_count


def _mark_tasks_done(template, task_type):
    now = now_naive()
    ProductChecksheetTask.objects.filter(
        template=template,
        task_type=task_type,
        status=ProductChecksheetTask.STATUS_PENDING,
    ).update(status=ProductChecksheetTask.STATUS_DONE, done_at=now)


def _mark_all_pending_tasks_skipped(template):
    now = now_naive()
    ProductChecksheetTask.objects.filter(
        template=template,
        status=ProductChecksheetTask.STATUS_PENDING,
    ).update(status=ProductChecksheetTask.STATUS_SKIPPED, done_at=now)


def _create_notification(title, description, users, operator_name=""):
    try:
        from notifications.models import Notification
        for user in users:
            if not user:
                continue
            Notification.objects.create(
                title=title,
                description=description,
                target_user=user,
                operator_name=operator_name,
            )
    except Exception:
        pass


def _auto_assign_workflow_users(creator):
    if not creator or not getattr(creator, "id", None):
        return None, None, None

    profile = getattr(creator, "profile", None)
    department_id = getattr(profile, "department_id", None) if profile else None
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
        user for user in candidates
        if getattr(getattr(user, "profile", None), "role", "") == "supervisor"
        and _role_rank(getattr(getattr(user, "profile", None), "role", "")) > creator_rank
    ]
    same_team_supervisors = [
        user for user in supervisor_candidates
        if creator_team_id
        and getattr(user, "profile", None)
        and any(team.id == creator_team_id for team in user.profile.supervisor_teams.all())
    ]
    same_team_supervisors.sort(key=_reviewer_sort_key)
    supervisor_candidates.sort(key=_reviewer_sort_key)
    reviewer_user = (
        same_team_supervisors[0] if same_team_supervisors
        else (supervisor_candidates[0] if supervisor_candidates else None)
    )

    chief_candidates = [
        user for user in candidates
        if getattr(getattr(user, "profile", None), "role", "") == "chief"
        and _role_rank(getattr(getattr(user, "profile", None), "role", "")) > creator_rank
    ]
    same_group_chiefs = [
        user for user in chief_candidates
        if creator_group_id and getattr(getattr(user, "profile", None), "group_id", None) == creator_group_id
    ]
    same_group_chiefs.sort(key=_reviewer_sort_key)
    chief_candidates.sort(key=_reviewer_sort_key)
    chief_user = same_group_chiefs[0] if same_group_chiefs else (chief_candidates[0] if chief_candidates else None)

    manager_candidates = [
        user for user in candidates
        if getattr(getattr(user, "profile", None), "role", "") == "manager"
        and _role_rank(getattr(getattr(user, "profile", None), "role", "")) > creator_rank
    ]
    manager_candidates.sort(key=_reviewer_sort_key)
    approver_user = manager_candidates[0] if manager_candidates else None

    return reviewer_user, chief_user, approver_user


def _workflow_stage_sequence(template):
    stages = []
    if template.reviewer_user_id:
        stages.append((
            ProductChecksheetTemplate.STATUS_SUPERVISOR_PENDING,
            ProductChecksheetTask.TASK_SUPERVISOR_REVIEW,
            template.reviewer_user,
            "班長確認",
        ))
    if template.chief_user_id:
        stages.append((
            ProductChecksheetTemplate.STATUS_CHIEF_PENDING,
            ProductChecksheetTask.TASK_CHIEF_REVIEW,
            template.chief_user,
            "係長承認",
        ))
    if template.approver_user_id:
        stages.append((
            ProductChecksheetTemplate.STATUS_MANAGER_PENDING,
            ProductChecksheetTask.TASK_MANAGER_APPROVE,
            template.approver_user,
            "部長承認",
        ))
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


def _ensure_workflow_users(template, persist=False):
    if not template or not template.created_by_id:
        return template
    if template.status == ProductChecksheetTemplate.STATUS_DRAFT:
        return template

    reviewer_user, chief_user, approver_user = _auto_assign_workflow_users(template.created_by)
    update_fields = []
    if not template.reviewer_user_id and reviewer_user:
        template.reviewer_user = reviewer_user
        update_fields.append("reviewer_user")
    if not template.chief_user_id and chief_user:
        template.chief_user = chief_user
        update_fields.append("chief_user")
    if not template.approver_user_id and approver_user:
        template.approver_user = approver_user
        update_fields.append("approver_user")

    if persist and update_fields:
        template.save(update_fields=update_fields + ["updated_at"])
    return template


# ---------------------------------------------------------------------------
# ViewSets
# ---------------------------------------------------------------------------

class ProductChecksheetTemplateViewSet(viewsets.ModelViewSet):
    queryset = (
        ProductChecksheetTemplate.objects
        .select_related(
            "line", "process", "product", "created_by",
            "reviewer_user", "chief_user", "approver_user",
            "reviewed_by", "chief_reviewed_by", "approved_by",
        )
        .prefetch_related("fields", "workflow_logs__actor")
        .all()
    )
    serializer_class = ProductChecksheetTemplateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]

    def get_queryset(self):
        queryset = super().get_queryset()
        line_id = self.request.query_params.get("line")
        process_id = self.request.query_params.get("process")
        product_id = self.request.query_params.get("product")
        active = self.request.query_params.get("is_active")
        status_value = self.request.query_params.get("status")
        query = str(self.request.query_params.get("q") or "").strip()
        if line_id:
            queryset = queryset.filter(line_id=line_id)
        if process_id:
            queryset = queryset.filter(process_id=process_id)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        if active is not None:
            queryset = queryset.filter(is_active=str(active).lower() in ("1", "true", "yes"))
        if status_value:
            queryset = queryset.filter(status=status_value)
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(product__product_code__icontains=query)
                | Q(product__product_name__icontains=query)
                | Q(process__process_code__icontains=query)
                | Q(line__line_code__icontains=query)
            )
        return queryset

    def get_object(self):
        instance = super().get_object()
        return _ensure_workflow_users(instance, persist=True)

    def create(self, request, *args, **kwargs):
        line = get_object_or_404(Line, pk=request.data.get("line"))
        process = get_object_or_404(Process, pk=request.data.get("process"))
        product = get_object_or_404(Product, pk=request.data.get("product"))
        name = str(request.data.get("name") or "").strip() or f"{product.product_code} チェックシート"

        uploaded_pdf = request.FILES.get("source_pdf")
        uploaded_image = request.FILES.get("source_image")
        try:
            assets = create_background_assets(uploaded_pdf=uploaded_pdf, uploaded_image=uploaded_image)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            template = ProductChecksheetTemplate.objects.create(
                name=name,
                line=line,
                process=process,
                product=product,
                version=1,
                status=ProductChecksheetTemplate.STATUS_DRAFT,
                is_active=True,
                document_title=str(request.data.get("document_title") or name),
                sheet_name=str(request.data.get("sheet_name") or product.product_code),
                revision_date=parse_date(str(request.data.get("revision_date") or "")),
                revision_notes=str(request.data.get("revision_notes") or ""),
                effective_from=parse_date(str(request.data.get("effective_from") or "")),
                source_type=assets["source_type"],
                background_image=assets["background_image"],
                background_width=assets["background_width"],
                background_height=assets["background_height"],
                editor_notes=str(request.data.get("editor_notes") or ""),
                created_by=request.user if request.user.is_authenticated else None,
            )
            if assets.get("source_pdf"):
                template.source_pdf = assets["source_pdf"]
            if assets.get("source_image"):
                template.source_image = assets["source_image"]
            template.save()

            _log_workflow(
                template=template,
                action=ProductChecksheetWorkflowLog.ACTION_CREATED,
                actor=request.user,
                from_status="",
                to_status=template.status,
                comment="テンプレート作成",
            )

        serializer = self.get_serializer(template)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status in (
            ProductChecksheetTemplate.STATUS_SUPERVISOR_PENDING,
            ProductChecksheetTemplate.STATUS_CHIEF_PENDING,
            ProductChecksheetTemplate.STATUS_MANAGER_PENDING,
            ProductChecksheetTemplate.STATUS_APPROVED,
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
            action=ProductChecksheetWorkflowLog.ACTION_UPDATED,
            actor=request.user,
            from_status=prev_status,
            to_status=instance.status,
            comment="テンプレート更新",
        )
        return response

    @action(detail=True, methods=["post"])
    def save_fields(self, request, pk=None):
        template = self.get_object()
        if template.status not in (
            ProductChecksheetTemplate.STATUS_DRAFT,
            ProductChecksheetTemplate.STATUS_REJECTED,
        ):
            return Response({"detail": "下書き/差戻しのテンプレートのみ編集できます。"}, status=status.HTTP_400_BAD_REQUEST)

        raw_fields = request.data.get("fields")
        if raw_fields is None:
            raw_fields = request.data.get("fields_json", [])
        if isinstance(raw_fields, str):
            try:
                fields_payload = json.loads(raw_fields)
            except json.JSONDecodeError:
                return Response({"detail": "配置データのJSON形式が正しくありません。"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            fields_payload = raw_fields
        if not isinstance(fields_payload, list):
            return Response({"detail": "配置データは配列で送信してください。"}, status=status.HTTP_400_BAD_REQUEST)

        header_payload = request.data.get("header") or {}
        if isinstance(header_payload, str):
            try:
                header_payload = json.loads(header_payload)
            except json.JSONDecodeError:
                header_payload = {}

        with transaction.atomic():
            if header_payload:
                if "document_title" in header_payload:
                    template.document_title = str(header_payload.get("document_title") or "")
                if "sheet_name" in header_payload:
                    template.sheet_name = str(header_payload.get("sheet_name") or "")
                if "revision_date" in header_payload:
                    template.revision_date = parse_date(str(header_payload.get("revision_date") or ""))
                if "revision_notes" in header_payload:
                    template.revision_notes = str(header_payload.get("revision_notes") or "")
                if "effective_from" in header_payload:
                    template.effective_from = parse_date(str(header_payload.get("effective_from") or ""))
                if "editor_notes" in header_payload:
                    template.editor_notes = str(header_payload.get("editor_notes") or "")
                template.save()

            save_template_fields(template, fields_payload)

            _log_workflow(
                template=template,
                action=ProductChecksheetWorkflowLog.ACTION_UPDATED,
                actor=request.user,
                from_status=template.status,
                to_status=template.status,
                comment="配置データ保存",
            )

        template.refresh_from_db()
        serializer = self.get_serializer(template)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def active_for_target(self, request):
        template = active_template_for(
            request.query_params.get("line"),
            request.query_params.get("process"),
            request.query_params.get("product"),
        )
        if not template:
            return Response({"required": False})
        return Response({"required": True, "template": ProductChecksheetTemplateSerializer(template).data})

    @action(detail=True, methods=["get"])
    def preview_pdf(self, request, pk=None):
        template = self.get_object()
        pdf_buffer = generate_template_preview_pdf(template)
        if not pdf_buffer:
            return Response(
                {"detail": "台紙画像が設定されていないためPDFを生成できません。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        product_code = template.product.product_code if template.product else "template"
        filename = f"{product_code}_v{template.version}_preview.pdf"
        return FileResponse(pdf_buffer, as_attachment=True, filename=filename, content_type="application/pdf")

    # --- ワークフローアクション ---

    @action(detail=True, methods=["post"])
    def submit_for_review(self, request, pk=None):
        template = self.get_object()
        if template.status not in (
            ProductChecksheetTemplate.STATUS_DRAFT,
            ProductChecksheetTemplate.STATUS_REJECTED,
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

            if prev_status != ProductChecksheetTemplate.STATUS_REJECTED or not template.submitted_fields_snapshot:
                snapshot = list(
                    template.fields.order_by("sort_order").values(
                        "key", "label", "field_type", "x", "y",
                        "width", "height", "required", "sort_order",
                    )
                )
                template.submitted_fields_snapshot = snapshot

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
                action=ProductChecksheetWorkflowLog.ACTION_SUBMITTED,
                actor=request.user,
                from_status=prev_status,
                to_status=template.status,
                comment=comment,
            )
            notification_desc = f"{first_stage[3]}待ちです。"
            if user_comment:
                notification_desc += f"\nコメント: {user_comment}"
            _create_notification(
                title=f"製品チェックシート 確認依頼: {template.product.product_code} v{template.version}",
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
            ProductChecksheetTemplate.STATUS_SUPERVISOR_PENDING,
            ProductChecksheetTemplate.STATUS_CHIEF_PENDING,
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

            now = now_naive()
            action_name = ProductChecksheetWorkflowLog.ACTION_SUPERVISOR_REVIEWED
            comment = "班長確認完了"
            if prev_status == ProductChecksheetTemplate.STATUS_SUPERVISOR_PENDING:
                template.reviewed_by = request.user
                template.reviewed_at = now
            else:
                template.chief_reviewed_by = request.user
                template.chief_reviewed_at = now
                action_name = ProductChecksheetWorkflowLog.ACTION_CHIEF_REVIEWED
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
                title=f"製品チェックシート 承認依頼: {template.product.product_code} v{template.version}",
                description=f"{comment}。{next_stage[3]}待ちです。",
                users=[next_stage[2]],
                operator_name=_display_name(request.user),
            )

        serializer = self.get_serializer(template)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        template = self.get_object()
        if template.status != ProductChecksheetTemplate.STATUS_MANAGER_PENDING:
            return Response(
                {"detail": "部長承認待ちのテンプレートのみ承認できます。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            prev_status = template.status
            ProductChecksheetTemplate.objects.filter(
                line=template.line,
                process=template.process,
                product=template.product,
                is_active=True,
            ).exclude(id=template.id).update(is_active=False)

            template.status = ProductChecksheetTemplate.STATUS_APPROVED
            template.approved_by = request.user
            template.approved_at = now_naive()
            template.is_active = True
            template.save()
            _mark_tasks_done(template, ProductChecksheetTask.TASK_MANAGER_APPROVE)
            _log_workflow(
                template=template,
                action=ProductChecksheetWorkflowLog.ACTION_APPROVED,
                actor=request.user,
                from_status=prev_status,
                to_status=template.status,
                comment="部長承認完了",
            )
            if template.created_by_id:
                _create_notification(
                    title=f"製品チェックシート 承認完了: {template.product.product_code} v{template.version}",
                    description="製品チェックシートが承認されました。",
                    users=[template.created_by],
                    operator_name=_display_name(request.user),
                )

        serializer = self.get_serializer(template)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        template = self.get_object()
        if template.status not in (
            ProductChecksheetTemplate.STATUS_SUPERVISOR_PENDING,
            ProductChecksheetTemplate.STATUS_CHIEF_PENDING,
            ProductChecksheetTemplate.STATUS_MANAGER_PENDING,
        ):
            return Response(
                {"detail": "確認/承認待ちのテンプレートのみ差戻しできます。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comment = str(request.data.get("comment") or "").strip()
        with transaction.atomic():
            prev_status = template.status
            template.status = ProductChecksheetTemplate.STATUS_REJECTED
            template.rejection_comment = comment
            template.save()
            _mark_all_pending_tasks_skipped(template)
            _log_workflow(
                template=template,
                action=ProductChecksheetWorkflowLog.ACTION_REJECTED,
                actor=request.user,
                from_status=prev_status,
                to_status=template.status,
                comment=comment,
            )
            if template.created_by_id:
                _create_notification(
                    title=f"製品チェックシート 差戻し: {template.product.product_code} v{template.version}",
                    description=comment or "製品チェックシートが差戻しされました。",
                    users=[template.created_by],
                    operator_name=_display_name(request.user),
                )
                _create_tasks_for_users(
                    template=template,
                    task_type=ProductChecksheetTask.TASK_CREATOR_FIX,
                    users=[template.created_by],
                    due_date=_task_due_date(template),
                )

        serializer = self.get_serializer(template)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def revise(self, request, pk=None):
        template = self.get_object()
        if template.status != ProductChecksheetTemplate.STATUS_APPROVED:
            return Response(
                {"detail": "承認済みのテンプレートのみ改訂できます。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_version = (
            ProductChecksheetTemplate.objects.filter(
                line=template.line, process=template.process, product=template.product,
            )
            .order_by("-version")
            .values_list("version", flat=True)
            .first() or template.version
        ) + 1

        with transaction.atomic():
            new_template = ProductChecksheetTemplate.objects.create(
                name=template.name,
                line=template.line,
                process=template.process,
                product=template.product,
                version=new_version,
                status=ProductChecksheetTemplate.STATUS_DRAFT,
                is_active=template.is_active,
                document_title=template.document_title,
                sheet_name=template.sheet_name,
                revision_date=None,
                revision_notes="",
                effective_from=None,
                source_type=template.source_type,
                source_pdf=template.source_pdf.name if template.source_pdf else "",
                source_image=template.source_image.name if template.source_image else "",
                background_image=template.background_image.name if template.background_image else "",
                background_width=template.background_width,
                background_height=template.background_height,
                editor_notes=template.editor_notes,
                created_by=request.user,
                reviewer_user=template.reviewer_user,
                chief_user=template.chief_user,
                approver_user=template.approver_user,
            )

            for field in template.fields.all():
                field.pk = None
                field.id = None
                field.template = new_template
                field.save()

            _log_workflow(
                template=new_template,
                action=ProductChecksheetWorkflowLog.ACTION_CREATED,
                actor=request.user,
                from_status="",
                to_status=new_template.status,
                comment=f"v{template.version} からの改訂",
            )

        serializer = self.get_serializer(new_template)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProductChecksheetTaskListView(generics.ListAPIView):
    """製品チェックシート承認タスク一覧"""

    from .serializers_checksheet import ProductChecksheetTemplateSerializer

    class TaskSerializer(__import__("rest_framework").serializers.ModelSerializer):
        template_data = ProductChecksheetTemplateSerializer(source="template", read_only=True)

        class Meta:
            model = ProductChecksheetTask
            fields = ["id", "template", "template_data", "task_type", "assigned_to", "status", "due_date", "created_at", "done_at"]

    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ProductChecksheetTask.objects.select_related(
            "template", "template__line", "template__process", "template__product",
            "template__created_by", "assigned_to",
        ).all()
        assigned_to_me = str(self.request.query_params.get("assigned_to_me", "")).lower()
        if assigned_to_me in ("1", "true", "yes"):
            queryset = queryset.filter(assigned_to=self.request.user)
        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset


class ProductChecksheetBatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        ProductChecksheetBatch.objects.select_related(
            "template",
            "template__line",
            "template__process",
            "template__product",
            "line",
            "process",
            "product",
            "production_order",
        )
        .prefetch_related("template__fields")
        .all()
    )
    serializer_class = ProductChecksheetBatchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        production_order_id = self.request.query_params.get("production_order")
        product_id = self.request.query_params.get("product")
        line_id = self.request.query_params.get("line")
        process_id = self.request.query_params.get("process")
        status_value = self.request.query_params.get("status")
        if production_order_id:
            queryset = queryset.filter(production_order_id=production_order_id)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        if line_id:
            queryset = queryset.filter(line_id=line_id)
        if process_id:
            queryset = queryset.filter(process_id=process_id)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset.annotate(
            completed_count_value=Count("records", filter=Q(records__status__in=[
                ProductChecksheetRecord.STATUS_COMPLETED,
                ProductChecksheetRecord.STATUS_APPROVED,
            ])),
            approved_count_value=Count("records", filter=Q(records__status=ProductChecksheetRecord.STATUS_APPROVED)),
        )

    @action(detail=False, methods=["post"])
    def prepare(self, request):
        serializer = ProductChecksheetPrepareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        template = active_template_for(data["line"], data["process"], data["product"])
        if not template:
            return Response({"required": False, "is_complete": True})

        line = get_object_or_404(Line, pk=data["line"])
        process = get_object_or_404(Process, pk=data["process"])
        product = get_object_or_404(Product, pk=data["product"])
        production_order = None
        if data.get("production_order"):
            production_order = get_object_or_404(ProductionOrder, pk=data["production_order"])
        batch = prepare_batch(
            template=template,
            production_order=production_order,
            line=line,
            process=process,
            product=product,
            quantity=data["quantity"],
            lot_no=data.get("lot_no") or "",
            operator_name=data.get("operator_name") or "",
            source_context=data.get("source_context") or {},
            user=request.user,
        )
        update_batch_status(batch)
        batch = self.get_queryset().get(pk=batch.pk)
        response = ProductChecksheetBatchSerializer(batch).data
        response["required"] = True
        return Response(response)

    @action(detail=True, methods=["get"])
    def records(self, request, pk=None):
        batch = self.get_object()
        records = batch.records.select_related("batch", "template").prefetch_related("photos").order_by("sequence_no")
        return Response(ProductChecksheetRecordSerializer(records, many=True).data)


class ProductChecksheetRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        ProductChecksheetRecord.objects.select_related(
            "batch",
            "batch__template",
            "batch__line",
            "batch__process",
            "batch__product",
            "template",
        )
        .prefetch_related("photos", "template__fields")
        .all()
    )
    serializer_class = ProductChecksheetRecordSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]

    def get_queryset(self):
        queryset = super().get_queryset()
        batch_id = self.request.query_params.get("batch")
        product_id = self.request.query_params.get("product")
        status_value = self.request.query_params.get("status")
        planned_ship_date = self.request.query_params.get("planned_ship_date")
        shipment_unit_no = self.request.query_params.get("shipment_unit_no")
        query = str(self.request.query_params.get("q") or "").strip()
        if batch_id:
            queryset = queryset.filter(batch_id=batch_id)
        if product_id:
            queryset = queryset.filter(batch__product_id=product_id)
        if status_value:
            queryset = queryset.filter(status=status_value)
        if planned_ship_date:
            parsed = parse_date(planned_ship_date)
            if parsed:
                queryset = queryset.filter(planned_ship_date=parsed)
        if shipment_unit_no:
            queryset = queryset.filter(shipment_unit_no=shipment_unit_no)
        if query:
            queryset = queryset.filter(
                Q(batch__lot_no__icontains=query)
                | Q(batch__product__product_code__icontains=query)
                | Q(batch__product__product_name__icontains=query)
                | Q(supervisor_name__icontains=query)
                | Q(completed_by_name__icontains=query)
            )
        return queryset.order_by("-updated_at", "-id")

    @action(detail=True, methods=["post"])
    def save_input(self, request, pk=None):
        record = self.get_object()
        template = record.template
        raw_responses = request.data.get("responses_json") or request.data.get("responses") or {}
        payload = parse_responses_json(raw_responses)
        missing = validate_record_required_fields(template, payload, request.FILES)
        if missing:
            return Response({"detail": f"未入力があります: {', '.join(missing)}"}, status=status.HTTP_400_BAD_REQUEST)

        planned_ship_date = parse_date(str(request.data.get("planned_ship_date") or ""))
        shipment_unit_no = request.data.get("shipment_unit_no")
        shipment_unit_no = int(shipment_unit_no) if str(shipment_unit_no or "").isdigit() else None

        with transaction.atomic():
            record.responses_json = normalize_responses(template, payload)
            record.planned_ship_date = planned_ship_date
            record.shipment_unit_no = shipment_unit_no
            record.completed_by_name = str(request.data.get("completed_by_name") or request.data.get("operator_name") or "").strip()
            record.status = ProductChecksheetRecord.STATUS_COMPLETED
            record.completed_at = now_naive()
            record.save()
            for key, uploaded in request.FILES.items():
                ProductChecksheetPhoto.objects.filter(record=record, field_key=key).delete()
                ProductChecksheetPhoto.objects.create(record=record, field_key=key, image=uploaded)
            recalc_shipment_sequence(record.batch_id, record.planned_ship_date, record.shipment_unit_no)
            update_batch_status(record.batch)
        return Response(ProductChecksheetRecordSerializer(record).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        record = self.get_object()
        if record.status not in (ProductChecksheetRecord.STATUS_COMPLETED, ProductChecksheetRecord.STATUS_APPROVED):
            return Response({"detail": "入力完了済みのチェックシートのみ承認できます。"}, status=status.HTTP_400_BAD_REQUEST)
        supervisor_name = str(request.data.get("supervisor_name") or "").strip()
        if not supervisor_name:
            return Response({"detail": "確認者名を入力してください。"}, status=status.HTTP_400_BAD_REQUEST)
        record.supervisor_name = supervisor_name
        record.approved_at = now_naive()
        record.status = ProductChecksheetRecord.STATUS_APPROVED
        record.save(update_fields=["supervisor_name", "approved_at", "status", "updated_at"])
        try:
            generate_record_pdf(record)
        except Exception as exc:
            record.status = ProductChecksheetRecord.STATUS_COMPLETED
            record.approved_at = None
            record.save(update_fields=["status", "approved_at", "updated_at"])
            return Response({"detail": f"PDF生成に失敗しました: {exc}"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ProductChecksheetRecordSerializer(record).data)
