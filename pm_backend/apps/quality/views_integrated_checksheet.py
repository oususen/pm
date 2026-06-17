from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models_integrated_checksheet import (
    IntegratedChecksheetBatch,
    IntegratedChecksheetCheck,
    IntegratedChecksheetItem,
    IntegratedChecksheetItemAttachment,
    IntegratedChecksheetProcessBlock,
    IntegratedChecksheetSketchField,
    IntegratedChecksheetSketchResponse,
    IntegratedChecksheetTask,
    IntegratedChecksheetTemplate,
    IntegratedChecksheetUnit,
    IntegratedChecksheetWorkflowLog,
)
from .serializers_integrated_checksheet import (
    IntegratedChecksheetBatchSerializer,
    IntegratedChecksheetItemSerializer,
    IntegratedChecksheetProcessBlockSerializer,
    IntegratedChecksheetTemplateListSerializer,
    IntegratedChecksheetTemplateSerializer,
    IntegratedChecksheetUnitSerializer,
)

def _generate_sei_ban(batch):
    """バッチ内の全ユニットの刻印番号を生成する。
    台目順に連番を振る（保留状態に関わらず維持）。
    フォーマット: YYYY MM DD NN 識別記号（スペース区切り）
    """
    plan_date = batch.plan_date
    if not plan_date:
        return
    if isinstance(plan_date, str):
        plan_date = datetime.strptime(plan_date, "%Y-%m-%d").date()
    yyyy = f"{plan_date.year:04d}"
    mm = f"{plan_date.month:02d}"
    dd = f"{plan_date.day:02d}"

    identification_code = getattr(batch.product, 'identification_code', '') or ''

    units = list(batch.units.order_by('sequence_no'))

    to_update = []
    for unit in units:
        nn = f"{unit.sequence_no:02d}"
        parts = [yyyy, mm, dd, nn]
        if identification_code:
            parts.append(identification_code)
        new_sei_ban = ' '.join(parts)
        if unit.sei_ban != new_sei_ban:
            unit.sei_ban = new_sei_ban
            to_update.append(unit)

    if to_update:
        IntegratedChecksheetUnit.objects.bulk_update(to_update, ['sei_ban'])


def _display_name(user):
    if not user:
        return ""
    last = (getattr(user, "last_name", "") or "").strip()
    first = (getattr(user, "first_name", "") or "").strip()
    return f"{last} {first}".strip() or user.get_full_name() or str(user)


def _log_ics_workflow(template, action, actor=None, from_status="", to_status="", comment=""):
    return IntegratedChecksheetWorkflowLog.objects.create(
        template=template,
        action=action,
        actor=actor if actor and getattr(actor, "id", None) else None,
        from_status=from_status or "",
        to_status=to_status or "",
        comment=comment or "",
    )


def _ics_task_due_date():
    return (datetime.now() + timedelta(days=3)).date()


def _create_ics_task(template, task_type, user):
    if not user or not getattr(user, "id", None):
        return
    exists = IntegratedChecksheetTask.objects.filter(
        template=template, task_type=task_type,
        assigned_to=user, status=IntegratedChecksheetTask.STATUS_PENDING,
    ).exists()
    if exists:
        return
    IntegratedChecksheetTask.objects.create(
        template=template, task_type=task_type,
        assigned_to=user, status=IntegratedChecksheetTask.STATUS_PENDING,
        due_date=_ics_task_due_date(),
    )


def _mark_ics_tasks_done(template, task_type):
    IntegratedChecksheetTask.objects.filter(
        template=template, task_type=task_type,
        status=IntegratedChecksheetTask.STATUS_PENDING,
    ).update(status=IntegratedChecksheetTask.STATUS_DONE, done_at=datetime.now())


def _skip_all_ics_pending_tasks(template):
    IntegratedChecksheetTask.objects.filter(
        template=template, status=IntegratedChecksheetTask.STATUS_PENDING,
    ).update(status=IntegratedChecksheetTask.STATUS_SKIPPED, done_at=datetime.now())


def _build_ics_items_snapshot(template):
    """差戻し後の再提出比較で使う、工程付きチェック項目スナップショットを作る。"""
    snapshot = []
    blocks = (
        template.process_blocks
        .select_related("process")
        .prefetch_related("items")
        .order_by("sort_order", "id")
    )
    for block in blocks:
        for item in block.items.all().order_by("sort_order", "id"):
            snapshot.append({
                "id": item.id,
                "process_block_id": block.id,
                "process_id": block.process_id,
                "process_sort_order": block.sort_order,
                "sort_order": item.sort_order,
                "item_name": item.item_name or "",
                "standard": item.standard or "",
                "frequency": item.frequency or "",
                "method": item.method or "",
                "record_type": item.record_type or IntegratedChecksheetItem.RECORD_CHECK,
                "unit": item.unit or "",
                "criteria": item.criteria or "",
                "is_required": bool(item.is_required),
            })
    return snapshot


def _role_rank(role):
    return {"worker": 1, "supervisor": 2, "chief": 3, "manager": 4, "admin": 5}.get(str(role or "").lower(), 0)


def _reviewer_sort_key(user):
    return getattr(user, "id", 0)


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


def _ensure_workflow_users(template, creator=None, persist=False):
    creator_user = creator or template.created_by
    reviewer_user, chief_user, approver_user = _auto_assign_workflow_users(creator_user)
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


class IntegratedChecksheetTemplateViewSet(viewsets.ModelViewSet):
    queryset = IntegratedChecksheetTemplate.objects.all()
    serializer_class = IntegratedChecksheetTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            qs = qs.select_related("product")
        else:
            qs = qs.select_related(
                "product", "line", "created_by",
                "reviewer_user", "chief_user", "approver_user",
            ).prefetch_related(
                "process_blocks__process",
                "process_blocks__items",
                "process_blocks__sketch_fields",
                "workflow_logs__actor",
            )
        product_id = self.request.query_params.get("product")
        line_id = self.request.query_params.get("line")
        status_val = self.request.query_params.get("status")
        is_active = self.request.query_params.get("is_active")
        if product_id:
            qs = qs.filter(product_id=product_id)
        if line_id:
            qs = qs.filter(line_id=line_id)
        if status_val:
            qs = qs.filter(status=status_val)
        if is_active is not None:
            qs = qs.filter(is_active=is_active in ("true", "1", "True"))
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return IntegratedChecksheetTemplateListSerializer
        return IntegratedChecksheetTemplateSerializer

    def perform_create(self, serializer):
        template = serializer.save(created_by=self.request.user)
        _ensure_workflow_users(template, creator=self.request.user, persist=True)
        WL = IntegratedChecksheetWorkflowLog
        _log_ics_workflow(template, WL.ACTION_CREATED, self.request.user,
                          to_status=template.status)

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        template = serializer.save()
        _ensure_workflow_users(template, creator=template.created_by or self.request.user, persist=True)
        WL = IntegratedChecksheetWorkflowLog
        _log_ics_workflow(template, WL.ACTION_UPDATED, self.request.user,
                          from_status=old_status, to_status=template.status,
                          comment="テンプレート更新")

    def perform_destroy(self, instance):
        if instance.status not in (
            IntegratedChecksheetTemplate.STATUS_DRAFT,
            IntegratedChecksheetTemplate.STATUS_REJECTED,
        ):
            from rest_framework.exceptions import ValidationError
            raise ValidationError("下書き・差戻しのテンプレートのみ削除できます。")
        _skip_all_ics_pending_tasks(instance)
        instance.delete()

    @action(detail=True, methods=["post"])
    def submit_for_review(self, request, pk=None):
        template = self.get_object()
        if template.status not in (
            IntegratedChecksheetTemplate.STATUS_DRAFT,
            IntegratedChecksheetTemplate.STATUS_REJECTED,
        ):
            return Response(
                {"detail": "下書き/差戻しのテンプレートのみ確認依頼できます。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        _ensure_workflow_users(template, creator=template.created_by or request.user, persist=True)

        if not template.reviewer_user_id:
            return Response(
                {"detail": "班長担当が設定されていません。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        _skip_all_ics_pending_tasks(template)
        old_status = template.status
        # 初回提出時のみスナップショット未設定なら保存（差戻し再提出時は reject 時点基準を維持）
        if not template.submitted_items_snapshot:
            template.submitted_items_snapshot = _build_ics_items_snapshot(template)
        template.status = IntegratedChecksheetTemplate.STATUS_SUPERVISOR_PENDING
        template.rejection_comment = ""
        template.reviewed_at = None
        template.chief_reviewed_at = None
        template.approved_at = None
        template.save(update_fields=[
            "status", "rejection_comment", "reviewed_at", "chief_reviewed_at",
            "approved_at", "submitted_items_snapshot", "updated_at",
        ])
        _create_ics_task(template, IntegratedChecksheetTask.TASK_SUPERVISOR_REVIEW, template.reviewer_user)
        parts = []
        if template.reviewer_user:
            parts.append(f"班長: {_display_name(template.reviewer_user)}")
        if template.chief_user:
            parts.append(f"係長: {_display_name(template.chief_user)}")
        if template.approver_user:
            parts.append(f"部長: {_display_name(template.approver_user)}")
        comment = " / ".join(parts)
        if request.data.get("comment"):
            comment += f" {request.data['comment']}"
        WL = IntegratedChecksheetWorkflowLog
        _log_ics_workflow(template, WL.ACTION_SUBMITTED, request.user,
                          from_status=old_status, to_status=template.status,
                          comment=comment)
        return Response(IntegratedChecksheetTemplateSerializer(
            self.get_queryset().get(pk=template.pk)
        ).data)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        template = self.get_object()
        T = IntegratedChecksheetTemplate
        TK = IntegratedChecksheetTask
        WL = IntegratedChecksheetWorkflowLog
        old_status = template.status
        if template.status == T.STATUS_SUPERVISOR_PENDING:
            if template.reviewer_user_id and template.reviewer_user_id != request.user.id:
                return Response(
                    {"detail": "班長担当者のみ確認できます。"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            _mark_ics_tasks_done(template, TK.TASK_SUPERVISOR_REVIEW)
            template.reviewed_at = datetime.now()
            if template.chief_user_id:
                template.status = T.STATUS_CHIEF_PENDING
                _create_ics_task(template, TK.TASK_CHIEF_REVIEW, template.chief_user)
            elif template.approver_user_id:
                template.status = T.STATUS_MANAGER_PENDING
                _create_ics_task(template, TK.TASK_MANAGER_APPROVE, template.approver_user)
            else:
                template.status = T.STATUS_APPROVED
                template.is_active = True
            template.save(update_fields=["status", "is_active", "reviewed_at", "updated_at"])
            _log_ics_workflow(template, WL.ACTION_SUPERVISOR_REVIEWED, request.user,
                              from_status=old_status, to_status=template.status,
                              comment="班長確認完了")
        elif template.status == T.STATUS_CHIEF_PENDING:
            if template.chief_user_id and template.chief_user_id != request.user.id:
                return Response(
                    {"detail": "係長担当者のみ確認できます。"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            _mark_ics_tasks_done(template, TK.TASK_CHIEF_REVIEW)
            template.chief_reviewed_at = datetime.now()
            if template.approver_user_id:
                template.status = T.STATUS_MANAGER_PENDING
                _create_ics_task(template, TK.TASK_MANAGER_APPROVE, template.approver_user)
            else:
                template.status = T.STATUS_APPROVED
                template.is_active = True
            template.save(update_fields=["status", "is_active", "chief_reviewed_at", "updated_at"])
            _log_ics_workflow(template, WL.ACTION_CHIEF_REVIEWED, request.user,
                              from_status=old_status, to_status=template.status,
                              comment="係長承認完了")
        else:
            return Response(
                {"detail": "班長確認待ち/係長確認待ちのテンプレートのみ確認完了できます。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(IntegratedChecksheetTemplateSerializer(
            self.get_queryset().get(pk=template.pk)
        ).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        template = self.get_object()
        if template.status != IntegratedChecksheetTemplate.STATUS_MANAGER_PENDING:
            return Response(
                {"detail": "部長承認待ちのテンプレートのみ承認できます。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if template.approver_user_id and template.approver_user_id != request.user.id:
            return Response(
                {"detail": "部長担当者のみ承認できます。"},
                status=status.HTTP_403_FORBIDDEN,
            )
        old_status = template.status
        with transaction.atomic():
            IntegratedChecksheetTemplate.objects.filter(
                product=template.product,
                line=template.line,
                is_active=True,
            ).exclude(id=template.id).update(is_active=False)
            template.status = IntegratedChecksheetTemplate.STATUS_APPROVED
            template.is_active = True
            template.approved_at = datetime.now()
            template.save(update_fields=["status", "is_active", "approved_at", "updated_at"])
            _mark_ics_tasks_done(template, IntegratedChecksheetTask.TASK_MANAGER_APPROVE)
            WL = IntegratedChecksheetWorkflowLog
            _log_ics_workflow(template, WL.ACTION_APPROVED, request.user,
                              from_status=old_status, to_status=template.status,
                              comment="部長承認完了")
        return Response(IntegratedChecksheetTemplateSerializer(
            self.get_queryset().get(pk=template.pk)
        ).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        template = self.get_object()
        T = IntegratedChecksheetTemplate
        if template.status not in (
            T.STATUS_SUPERVISOR_PENDING,
            T.STATUS_CHIEF_PENDING,
            T.STATUS_MANAGER_PENDING,
        ):
            return Response(
                {"detail": "確認/承認待ちのテンプレートのみ差戻しできます。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        expected_user_id = {
            T.STATUS_SUPERVISOR_PENDING: template.reviewer_user_id,
            T.STATUS_CHIEF_PENDING: template.chief_user_id,
            T.STATUS_MANAGER_PENDING: template.approver_user_id,
        }.get(template.status)
        if expected_user_id and expected_user_id != request.user.id:
            return Response(
                {"detail": "担当者のみ差戻しできます。"},
                status=status.HTTP_403_FORBIDDEN,
            )
        comment = str(request.data.get("comment") or "").strip()
        old_status = template.status
        _skip_all_ics_pending_tasks(template)
        # 差戻し時点の項目を次回再提出の比較基準として保存する
        template.submitted_items_snapshot = _build_ics_items_snapshot(template)
        template.status = IntegratedChecksheetTemplate.STATUS_REJECTED
        template.rejection_comment = comment
        template.save(update_fields=["status", "rejection_comment", "submitted_items_snapshot", "updated_at"])
        if template.created_by_id:
            _create_ics_task(template, IntegratedChecksheetTask.TASK_CREATOR_FIX, template.created_by)
        WL = IntegratedChecksheetWorkflowLog
        _log_ics_workflow(template, WL.ACTION_REJECTED, request.user,
                          from_status=old_status, to_status=template.status,
                          comment=comment or "-")
        return Response(IntegratedChecksheetTemplateSerializer(
            self.get_queryset().get(pk=template.pk)
        ).data)

    @action(detail=True, methods=["post"])
    def revise(self, request, pk=None):
        template = self.get_object()
        if template.status != IntegratedChecksheetTemplate.STATUS_APPROVED:
            return Response(
                {"detail": "承認済みのテンプレートのみ改訂できます。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        new_version = (
            IntegratedChecksheetTemplate.objects
            .filter(product=template.product, line=template.line)
            .order_by("-version")
            .values_list("version", flat=True)
            .first() or 0
        ) + 1
        template.pk = None
        template.version = new_version
        template.status = IntegratedChecksheetTemplate.STATUS_DRAFT
        template.is_active = False
        template.rejection_comment = ""
        template.created_by = request.user
        template.save()
        return Response(IntegratedChecksheetTemplateSerializer(
            self.get_queryset().get(pk=template.pk)
        ).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def preview_pdf(self, request, pk=None):
        from .services_integrated_checksheet import generate_integrated_template_pdf

        template = self.get_object()
        pdf_buffer = generate_integrated_template_pdf(template)
        if not pdf_buffer:
            return Response(
                {"detail": "PDFを生成できませんでした。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        template_name = template.name or template.document_title or "template"
        filename = f"{template_name}.pdf"
        return FileResponse(pdf_buffer, as_attachment=True, filename=filename, content_type="application/pdf")

    @action(
        detail=False, methods=["post"], url_path="upload-attachment-image",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_attachment_image(self, request):
        import os
        import uuid

        from django.core.files.storage import default_storage

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "ファイルがありません。"}, status=status.HTTP_400_BAD_REQUEST)
        ext = os.path.splitext(file_obj.name)[1] or ""
        filename = f"integrated_checksheet_attachments/{uuid.uuid4().hex}{ext}"
        saved_path = default_storage.save(filename, file_obj)
        base_url = request.build_absolute_uri("/")[:-1]
        image_url = f"{base_url}{default_storage.url(saved_path)}"
        return Response({"image_url": image_url}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def save_structure(self, request, pk=None):
        """工程ブロック・項目・台紙フィールドを一括保存"""
        import os

        from django.core.files.base import ContentFile

        template = self.get_object()
        blocks_data = request.data.get("process_blocks", [])
        with transaction.atomic():
            existing_block_ids = set(template.process_blocks.values_list("id", flat=True))
            incoming_block_ids = set()
            for b_data in blocks_data:
                block_id = b_data.get("id")
                copy_source_block_id = b_data.get("copy_source_block_id")
                block_defaults = {
                    "process_id": b_data["process"],
                    "sort_order": b_data.get("sort_order", 1),
                }
                if block_id:
                    block = IntegratedChecksheetProcessBlock.objects.filter(
                        id=block_id, template=template
                    ).first()
                    if block:
                        for k, v in block_defaults.items():
                            setattr(block, k, v)
                        block.save()
                        incoming_block_ids.add(block.id)
                    else:
                        block = IntegratedChecksheetProcessBlock.objects.create(
                            template=template, **block_defaults
                        )
                        incoming_block_ids.add(block.id)
                else:
                    block = IntegratedChecksheetProcessBlock.objects.create(
                        template=template, **block_defaults
                    )
                    incoming_block_ids.add(block.id)

                if copy_source_block_id and not block_id:
                    src_block = IntegratedChecksheetProcessBlock.objects.filter(id=copy_source_block_id).first()
                    if src_block:
                        if src_block.source_pdf and src_block.source_pdf.storage.exists(src_block.source_pdf.name):
                            ext = os.path.splitext(src_block.source_pdf.name)[1]
                            block.source_pdf.save(
                                f"copy_{template.pk}_{block.id}{ext}",
                                ContentFile(src_block.source_pdf.read()),
                                save=False,
                            )
                        if src_block.sketch_image and src_block.sketch_image.storage.exists(src_block.sketch_image.name):
                            ext = os.path.splitext(src_block.sketch_image.name)[1]
                            block.sketch_image.save(
                                f"copy_{template.pk}_{block.id}{ext}",
                                ContentFile(src_block.sketch_image.read()),
                                save=False,
                            )
                        if block.source_pdf or block.sketch_image:
                            block.save()

                items_data = b_data.get("items", [])
                block.items.all().delete()
                for idx, item_data in enumerate(items_data):
                    item_obj = IntegratedChecksheetItem.objects.create(
                        process_block=block,
                        sort_order=item_data.get("sort_order", idx + 1),
                        item_name=item_data.get("item_name", ""),
                        standard=item_data.get("standard", ""),
                        frequency=item_data.get("frequency", ""),
                        method=item_data.get("method", ""),
                        record_type=item_data.get("record_type", IntegratedChecksheetItem.RECORD_CHECK),
                        unit=item_data.get("unit", ""),
                        criteria=item_data.get("criteria", ""),
                        remarks=item_data.get("remarks", ""),
                        is_required=item_data.get("is_required", True),
                    )
                    for att_idx, att_data in enumerate(item_data.get("attachments", [])):
                        IntegratedChecksheetItemAttachment.objects.create(
                            item=item_obj,
                            display_order=att_data.get("display_order", att_idx + 1),
                            title=att_data.get("title", ""),
                            description=att_data.get("description", ""),
                            check_point=att_data.get("check_point", ""),
                            ok_example=att_data.get("ok_example", ""),
                            ng_example=att_data.get("ng_example", ""),
                            image_url=att_data.get("image_url", ""),
                        )

                sketch_fields_data = b_data.get("sketch_fields", [])
                block.sketch_fields.all().delete()
                for idx, sf_data in enumerate(sketch_fields_data):
                    IntegratedChecksheetSketchField.objects.create(
                        process_block=block,
                        key=sf_data.get("key", f"field_{idx + 1}"),
                        label=sf_data.get("label", ""),
                        field_type=sf_data.get("field_type", IntegratedChecksheetSketchField.FIELD_TEXT),
                        x=sf_data.get("x", 0),
                        y=sf_data.get("y", 0),
                        width=sf_data.get("width", 160),
                        height=sf_data.get("height", 36),
                        required=sf_data.get("required", False),
                        sort_order=sf_data.get("sort_order", idx),
                    )

            removed = existing_block_ids - incoming_block_ids
            if removed:
                IntegratedChecksheetProcessBlock.objects.filter(id__in=removed).delete()

        template.refresh_from_db()
        _ensure_workflow_users(template, creator=template.created_by or request.user, persist=True)
        template.refresh_from_db()
        return Response(IntegratedChecksheetTemplateSerializer(
            self.get_queryset().get(pk=template.pk)
        ).data)

    @action(detail=True, methods=["post"], url_path="upload_sketch/(?P<block_id>[0-9]+)", parser_classes=[MultiPartParser, FormParser])
    def upload_sketch(self, request, pk=None, block_id=None):
        """工程ブロックの台紙をアップロード（PDF or 画像）"""
        from .services_checksheet import create_background_assets

        template = self.get_object()
        block = IntegratedChecksheetProcessBlock.objects.filter(
            id=block_id, template=template
        ).first()
        if not block:
            return Response({"detail": "工程ブロックが見つかりません。"}, status=status.HTTP_404_NOT_FOUND)

        uploaded_pdf = request.FILES.get("source_pdf")
        uploaded_image = request.FILES.get("source_image")
        if not uploaded_pdf and not uploaded_image:
            return Response({"detail": "台紙PDFまたは台紙画像が必要です。"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            assets = create_background_assets(uploaded_pdf=uploaded_pdf, uploaded_image=uploaded_image)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if assets.get("source_pdf"):
            block.source_pdf = assets["source_pdf"]
        if assets.get("background_image"):
            block.sketch_image = assets["background_image"]
        block.save()

        return Response(IntegratedChecksheetProcessBlockSerializer(block).data)


class IntegratedChecksheetBatchViewSet(
    mixins.DestroyModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = (
        IntegratedChecksheetBatch.objects
        .select_related("template", "product", "line", "leader_confirmed_by", "supervisor_confirmed_by")
        .prefetch_related(
            "template__process_blocks__process",
            "template__process_blocks__items",
            "units__checks__item__process_block",
        )
        .all()
    )
    serializer_class = IntegratedChecksheetBatchSerializer
    permission_classes = [IsAuthenticated]

    def perform_destroy(self, instance):
        if instance.status in (
            IntegratedChecksheetBatch.STATUS_LEADER_CONFIRMED,
            IntegratedChecksheetBatch.STATUS_SUPERVISOR_CONFIRMED,
        ):
            from rest_framework.exceptions import ValidationError
            raise ValidationError("確認済みのバッチは削除できません。")
        instance.delete()

    @action(detail=True, methods=["post"])
    def edit_batch(self, request, pk=None):
        batch = self.get_object()
        if batch.status in (
            IntegratedChecksheetBatch.STATUS_LEADER_CONFIRMED,
            IntegratedChecksheetBatch.STATUS_SUPERVISOR_CONFIRMED,
        ):
            return Response(
                {"detail": "確認済みのバッチは編集できません。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        plan_date = request.data.get("plan_date")
        new_quantity = request.data.get("quantity")
        update_fields = ["updated_at"]

        if plan_date is not None:
            batch.plan_date = plan_date or None
            update_fields.append("plan_date")

        if new_quantity is not None:
            new_quantity = int(new_quantity)
            if new_quantity < 1:
                return Response({"detail": "台数は1以上にしてください。"}, status=status.HTTP_400_BAD_REQUEST)
            old_quantity = batch.quantity
            with transaction.atomic():
                if new_quantity > old_quantity:
                    IntegratedChecksheetUnit.objects.bulk_create([
                        IntegratedChecksheetUnit(batch=batch, sequence_no=seq)
                        for seq in range(old_quantity + 1, new_quantity + 1)
                    ])
                elif new_quantity < old_quantity:
                    remove_units = batch.units.filter(sequence_no__gt=new_quantity)
                    has_data = remove_units.filter(
                        Q(checks__isnull=False) | Q(sketch_responses__isnull=False)
                    ).distinct().exists()
                    if has_data:
                        return Response(
                            {"detail": f"台目{new_quantity + 1}以降にチェックデータがあるため削減できません。"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    remove_units.delete()
                batch.quantity = new_quantity
                update_fields.append("quantity")
                batch.save(update_fields=update_fields)
                self._update_batch_status_helper(batch)
        else:
            batch.save(update_fields=update_fields)

        _generate_sei_ban(batch)
        batch = self.get_queryset().get(pk=batch.pk)
        return Response(IntegratedChecksheetBatchSerializer(batch).data)

    def _update_batch_status_helper(self, batch):
        total = batch.units.count()
        if total == 0:
            next_status = IntegratedChecksheetBatch.STATUS_OPEN
        else:
            completed = batch.units.filter(
                status__in=[IntegratedChecksheetUnit.STATUS_COMPLETED, IntegratedChecksheetUnit.STATUS_APPROVED]
            ).count()
            next_status = IntegratedChecksheetBatch.STATUS_COMPLETED if completed >= total else IntegratedChecksheetBatch.STATUS_OPEN
        if batch.status != next_status:
            batch.status = next_status
            batch.save(update_fields=["status", "updated_at"])

    def get_queryset(self):
        qs = super().get_queryset().annotate(
            unit_count=Count("units"),
            completed_count=Count("units", filter=Q(units__status__in=[
                IntegratedChecksheetUnit.STATUS_COMPLETED,
                IntegratedChecksheetUnit.STATUS_APPROVED,
            ])),
        )
        product_id = self.request.query_params.get("product")
        line_id = self.request.query_params.get("line")
        status_val = self.request.query_params.get("status")
        if product_id:
            qs = qs.filter(product_id=product_id)
        if line_id:
            qs = qs.filter(line_id=line_id)
        if status_val:
            qs = qs.filter(status=status_val)
        sei_ban = self.request.query_params.get("sei_ban")
        if sei_ban:
            qs = qs.filter(units__sei_ban__icontains=sei_ban).distinct()
        return qs

    @action(detail=True, methods=["get"])
    def units(self, request, pk=None):
        batch = self.get_object()
        units = (
            batch.units
            .prefetch_related("checks__item__process_block", "sketch_responses")
            .order_by("sequence_no")
        )
        blocks = list(
            batch.template.process_blocks
            .select_related("process")
            .prefetch_related("items")
            .order_by("sort_order")
        )
        for unit in units:
            unit._process_blocks = blocks
        return Response(IntegratedChecksheetUnitSerializer(units, many=True).data)

    @action(detail=False, methods=["post"])
    def prepare(self, request):
        """バッチ作成（台目レコードも一括生成）"""
        product_id = request.data.get("product")
        line_id = request.data.get("line")
        quantity = int(request.data.get("quantity", 0))
        plan_date = request.data.get("plan_date")
        lot_no = request.data.get("lot_no", "")

        if not product_id or not line_id or quantity <= 0 or not plan_date:
            return Response({"detail": "product, line, quantity, plan_date は必須です。"}, status=status.HTTP_400_BAD_REQUEST)

        template = (
            IntegratedChecksheetTemplate.objects
            .filter(
                product_id=product_id,
                line_id=line_id,
                status=IntegratedChecksheetTemplate.STATUS_APPROVED,
                is_active=True,
            )
            .order_by("-version")
            .first()
        )
        if not template:
            template = (
                IntegratedChecksheetTemplate.objects
                .filter(
                    product_id=product_id,
                    line__isnull=True,
                    status=IntegratedChecksheetTemplate.STATUS_APPROVED,
                    is_active=True,
                )
                .order_by("-version")
                .first()
            )
        if not template:
            return Response({"detail": "承認済みテンプレートがありません。"}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            batch = IntegratedChecksheetBatch.objects.create(
                template=template,
                product_id=product_id,
                line_id=line_id,
                plan_date=plan_date,
                quantity=quantity,
                lot_no=lot_no,
                created_by=request.user,
            )
            IntegratedChecksheetUnit.objects.bulk_create([
                IntegratedChecksheetUnit(batch=batch, sequence_no=seq)
                for seq in range(1, quantity + 1)
            ])
            batch.refresh_from_db()
            _generate_sei_ban(batch)

        batch = self.get_queryset().get(pk=batch.pk)
        return Response(IntegratedChecksheetBatchSerializer(batch).data, status=status.HTTP_201_CREATED)

    def _all_units_completed(self, batch):
        """全台目の必須項目が完了しているか"""
        blocks = list(
            batch.template.process_blocks.prefetch_related("items").all()
        )
        required_item_ids = set()
        for block in blocks:
            for item in block.items.all():
                if item.is_required:
                    required_item_ids.add(item.id)
        if not required_item_ids:
            return True
        for unit in batch.units.prefetch_related("checks").all():
            checked_ids = set()
            for check in unit.checks.all():
                if check.judgement or check.numeric_value is not None or check.text_value or check.photo_url:
                    checked_ids.add(check.item_id)
            if not required_item_ids.issubset(checked_ids):
                return False
        return True

    @action(detail=True, methods=["post"])
    def leader_confirm(self, request, pk=None):
        batch = self.get_object()
        if batch.status not in (
            IntegratedChecksheetBatch.STATUS_OPEN,
            IntegratedChecksheetBatch.STATUS_COMPLETED,
        ):
            return Response(
                {"detail": f"現在のステータス「{batch.get_status_display()}」ではリーダ確認できません。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not self._all_units_completed(batch):
            return Response(
                {"detail": "全台目の必須項目が完了していません。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        batch.status = IntegratedChecksheetBatch.STATUS_LEADER_CONFIRMED
        batch.leader_confirmed_by = request.user
        batch.leader_confirmed_at = datetime.now()
        batch.save(update_fields=["status", "leader_confirmed_by", "leader_confirmed_at", "updated_at"])
        batch = self.get_queryset().get(pk=batch.pk)
        return Response(IntegratedChecksheetBatchSerializer(batch).data)

    @action(detail=True, methods=["post"])
    def supervisor_confirm(self, request, pk=None):
        batch = self.get_object()
        if batch.status != IntegratedChecksheetBatch.STATUS_LEADER_CONFIRMED:
            return Response(
                {"detail": "リーダ確認済みのバッチのみ班長確認できます。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        batch.status = IntegratedChecksheetBatch.STATUS_SUPERVISOR_CONFIRMED
        batch.supervisor_confirmed_by = request.user
        batch.supervisor_confirmed_at = datetime.now()
        batch.save(update_fields=["status", "supervisor_confirmed_by", "supervisor_confirmed_at", "updated_at"])
        batch = self.get_queryset().get(pk=batch.pk)
        return Response(IntegratedChecksheetBatchSerializer(batch).data)


class IntegratedChecksheetUnitViewSet(viewsets.GenericViewSet):
    queryset = IntegratedChecksheetUnit.objects.all()
    serializer_class = IntegratedChecksheetUnitSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def save_checks(self, request, pk=None):
        """台目の項目チェック結果を一括保存。工程順序を検証する。"""
        unit = self.get_object()
        batch = unit.batch
        template = batch.template
        checks_data = request.data.get("checks", [])
        target_block_id = request.data.get("process_block_id")

        blocks = list(template.process_blocks.prefetch_related("items").order_by("sort_order"))

        if target_block_id:
            target_block_id = int(target_block_id)
            for block in blocks:
                if block.id == target_block_id:
                    break
                items = list(block.items.all())
                if not items:
                    continue
                existing = set(
                    IntegratedChecksheetCheck.objects
                    .filter(unit=unit, item__process_block=block)
                    .exclude(judgement="", numeric_value__isnull=True, text_value="", photo_url="")
                    .values_list("item_id", flat=True)
                )
                required_items = [it for it in items if it.is_required]
                if required_items and not all(it.id in existing for it in required_items):
                    return Response(
                        {"detail": f"工程「{block.process.process_name}」の必須項目が未完了です。先にチェックしてください。"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        now = datetime.now()
        with transaction.atomic():
            for check_data in checks_data:
                item_id = check_data.get("item")
                if not item_id:
                    continue
                defaults = {
                    "checked_by": request.user,
                    "checked_at": now,
                }
                if "judgement" in check_data:
                    defaults["judgement"] = check_data["judgement"]
                if "numeric_value" in check_data:
                    defaults["numeric_value"] = check_data["numeric_value"]
                if "text_value" in check_data:
                    defaults["text_value"] = check_data["text_value"]
                if "photo_url" in check_data:
                    defaults["photo_url"] = check_data["photo_url"]

                IntegratedChecksheetCheck.objects.update_or_create(
                    unit=unit, item_id=item_id, defaults=defaults,
                )

            self._update_unit_status(unit, blocks)

        unit.refresh_from_db()
        return Response(IntegratedChecksheetUnitSerializer(unit).data)

    @action(detail=True, methods=["post"])
    def save_sketch(self, request, pk=None):
        """台目×工程ブロックの台紙データ（手書き＋フィールド回答）を保存"""
        unit = self.get_object()
        process_block_id = request.data.get("process_block_id")
        drawing_data = request.data.get("drawing_data", {})
        field_responses = request.data.get("field_responses", {})

        if not process_block_id:
            return Response({"detail": "process_block_id は必須です。"}, status=status.HTTP_400_BAD_REQUEST)

        IntegratedChecksheetSketchResponse.objects.update_or_create(
            unit=unit, process_block_id=process_block_id,
            defaults={"drawing_data": drawing_data, "field_responses": field_responses},
        )

        return Response({"ok": True})

    @action(detail=True, methods=["post"])
    def release_hold(self, request, pk=None):
        """工程ブロックの保留を解除する（リーダー以上のみ）"""
        user = request.user
        role = getattr(getattr(user, 'profile', None), 'role', '')
        if not user.is_superuser and role not in ('leader', 'supervisor', 'chief', 'manager'):
            return Response({"detail": "保留解除はリーダー以上の権限が必要です。"}, status=status.HTTP_403_FORBIDDEN)

        unit = self.get_object()
        process_block_id = request.data.get("process_block_id")
        if not process_block_id:
            return Response({"detail": "process_block_id は必須です。"}, status=status.HTTP_400_BAD_REQUEST)

        resp = IntegratedChecksheetSketchResponse.objects.filter(
            unit=unit, process_block_id=process_block_id,
        ).first()
        if not resp:
            return Response({"detail": "対象の台紙データがありません。"}, status=status.HTTP_404_NOT_FOUND)

        release_reason = str(request.data.get("release_reason", "")).strip()
        if not release_reason:
            return Response({"detail": "解除理由は必須です。"}, status=status.HTTP_400_BAD_REQUEST)

        fr = resp.field_responses if isinstance(resp.field_responses, dict) else {}
        fr.pop('_hold', None)
        fr['_hold_released'] = True
        fr['_hold_reason_original'] = fr.pop('_hold_reason', '')
        fr['_release_reason'] = release_reason
        fr['_released_by'] = user.get_full_name() or str(user)
        fr['_released_at'] = datetime.now().isoformat()
        resp.field_responses = fr
        resp.save(update_fields=['field_responses', 'updated_at'])

        unit.refresh_from_db()
        return Response(IntegratedChecksheetUnitSerializer(unit).data)

    @action(detail=False, methods=["get"])
    def search_history(self, request):
        """刻印番号でユニットを検索し、全工程のチェック履歴を返す"""
        sei_ban = request.query_params.get("sei_ban", "").strip()
        if not sei_ban:
            return Response({"detail": "sei_ban は必須です。"}, status=status.HTTP_400_BAD_REQUEST)

        units = (
            IntegratedChecksheetUnit.objects
            .filter(sei_ban__icontains=sei_ban)
            .select_related(
                "batch__template", "batch__product", "batch__line",
                "batch__leader_confirmed_by", "batch__supervisor_confirmed_by",
            )
            .prefetch_related(
                "checks__item__process_block__process",
                "checks__checked_by",
                "sketch_responses__process_block__process",
            )
            .order_by("-batch__plan_date", "sequence_no")
        )

        results = []
        for unit in units:
            batch = unit.batch
            template = batch.template
            blocks = list(
                template.process_blocks
                .select_related("process")
                .order_by("sort_order")
            )
            checks_by_block = {}
            for check in unit.checks.all():
                bid = check.item.process_block_id
                if bid not in checks_by_block:
                    checks_by_block[bid] = []
                checks_by_block[bid].append({
                    "item_name": check.item.item_name,
                    "record_type": check.item.record_type,
                    "judgement": check.judgement,
                    "numeric_value": str(check.numeric_value) if check.numeric_value is not None else None,
                    "text_value": check.text_value,
                    "photo_url": check.photo_url,
                    "checked_by": check.checked_by.get_full_name() or str(check.checked_by) if check.checked_by else "",
                    "checked_at": check.checked_at.isoformat() if check.checked_at else None,
                })

            sketch_map = {}
            for sr in unit.sketch_responses.all():
                fr = sr.field_responses if isinstance(sr.field_responses, dict) else {}
                hold_info = None
                if fr.get("_hold"):
                    hold_info = {"status": "held", "reason": fr.get("_hold_reason", "")}
                elif fr.get("_hold_released"):
                    hold_info = {
                        "status": "released",
                        "hold_reason": fr.get("_hold_reason_original", ""),
                        "release_reason": fr.get("_release_reason", ""),
                        "released_by": fr.get("_released_by", ""),
                        "released_at": fr.get("_released_at", ""),
                    }
                sketch_map[sr.process_block_id] = hold_info

            process_results = []
            for block in blocks:
                process_results.append({
                    "process_code": block.process.process_code,
                    "process_name": block.process.process_name,
                    "block_id": block.id,
                    "checks": checks_by_block.get(block.id, []),
                    "hold": sketch_map.get(block.id),
                })

            results.append({
                "unit_id": unit.id,
                "sei_ban": unit.sei_ban,
                "sequence_no": unit.sequence_no,
                "status": unit.status,
                "completed_at": unit.completed_at.isoformat() if unit.completed_at else None,
                "batch_id": batch.id,
                "plan_date": str(batch.plan_date) if batch.plan_date else "",
                "lot_no": batch.lot_no,
                "product_code": batch.product.product_code,
                "product_name": batch.product.product_name,
                "line_code": batch.line.line_code if batch.line else "",
                "line_name": batch.line.line_name if batch.line else "",
                "batch_status": batch.status,
                "processes": process_results,
            })

        return Response(results)

    def _update_unit_status(self, unit, blocks):
        all_required_items = []
        for block in blocks:
            all_required_items.extend([it for it in block.items.all() if it.is_required])

        if not all_required_items:
            self._update_batch_status(unit.batch)
            return

        checked_ids = set(
            IntegratedChecksheetCheck.objects
            .filter(unit=unit)
            .exclude(judgement="", numeric_value__isnull=True, text_value="", photo_url="")
            .values_list("item_id", flat=True)
        )
        all_done = all(it.id in checked_ids for it in all_required_items)

        if all_done and unit.status != IntegratedChecksheetUnit.STATUS_COMPLETED:
            unit.status = IntegratedChecksheetUnit.STATUS_COMPLETED
            unit.completed_at = datetime.now()
            unit.save(update_fields=["status", "completed_at"])
        elif not all_done and unit.status == IntegratedChecksheetUnit.STATUS_PENDING:
            unit.status = IntegratedChecksheetUnit.STATUS_IN_PROGRESS
            unit.save(update_fields=["status"])

        self._update_batch_status(unit.batch)

    def _update_batch_status(self, batch):
        total = batch.units.count()
        if total == 0:
            next_status = IntegratedChecksheetBatch.STATUS_OPEN
        else:
            completed = batch.units.filter(
                status__in=[
                    IntegratedChecksheetUnit.STATUS_COMPLETED,
                    IntegratedChecksheetUnit.STATUS_APPROVED,
                ]
            ).count()
            next_status = (
                IntegratedChecksheetBatch.STATUS_COMPLETED
                if completed >= total
                else IntegratedChecksheetBatch.STATUS_OPEN
            )

        if batch.status != next_status:
            batch.status = next_status
            batch.save(update_fields=["status", "updated_at"])


class IntegratedChecksheetTaskListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = IntegratedChecksheetTask.objects.select_related(
            "template__product", "assigned_to",
        ).order_by("status", "due_date", "-created_at")

        if str(request.query_params.get("assigned_to_me", "true")).lower() in ("true", "1", "yes"):
            qs = qs.filter(assigned_to=request.user)

        task_type = request.query_params.get("task_type")
        status_val = request.query_params.get("status")
        if task_type:
            qs = qs.filter(task_type=task_type)
        if status_val:
            qs = qs.filter(status=status_val)

        data = []
        for t in qs[:200]:
            data.append({
                "id": t.id,
                "template_id": t.template_id,
                "template_name": t.template.name if t.template else "",
                "product_code": t.template.product.product_code if t.template and t.template.product else "",
                "task_type": t.task_type,
                "task_type_display": t.get_task_type_display(),
                "assigned_to": t.assigned_to_id,
                "assigned_to_name": _display_name(t.assigned_to),
                "status": t.status,
                "due_date": str(t.due_date) if t.due_date else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "done_at": t.done_at.isoformat() if t.done_at else None,
            })
        return Response(data)
