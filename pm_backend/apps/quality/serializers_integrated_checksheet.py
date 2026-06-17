from rest_framework import serializers

from .models_integrated_checksheet import (
    IntegratedChecksheetBatch,
    IntegratedChecksheetCheck,
    IntegratedChecksheetItem,
    IntegratedChecksheetItemAttachment,
    IntegratedChecksheetProcessBlock,
    IntegratedChecksheetSketchField,
    IntegratedChecksheetSketchResponse,
    IntegratedChecksheetTemplate,
    IntegratedChecksheetUnit,
    IntegratedChecksheetWorkflowLog,
)

def _format_user_name(user):
    if not user:
        return ""
    last_name = (getattr(user, "last_name", "") or "").strip()
    first_name = (getattr(user, "first_name", "") or "").strip()
    return f"{last_name} {first_name}".strip() or user.get_full_name() or str(user)


class IntegratedChecksheetSketchFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegratedChecksheetSketchField
        fields = ["id", "key", "label", "field_type", "x", "y", "width", "height", "required", "sort_order"]


class IntegratedChecksheetItemAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegratedChecksheetItemAttachment
        fields = [
            "id", "display_order", "title", "description",
            "check_point", "ok_example", "ng_example", "image_url",
        ]


class IntegratedChecksheetItemSerializer(serializers.ModelSerializer):
    attachments = IntegratedChecksheetItemAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = IntegratedChecksheetItem
        fields = [
            "id", "sort_order", "item_name", "standard", "frequency",
            "method", "record_type", "unit", "criteria", "remarks", "is_required",
            "attachments",
        ]


class IntegratedChecksheetProcessBlockSerializer(serializers.ModelSerializer):
    items = IntegratedChecksheetItemSerializer(many=True, read_only=True)
    sketch_fields = IntegratedChecksheetSketchFieldSerializer(many=True, read_only=True)
    process_code = serializers.CharField(source="process.process_code", read_only=True)
    process_name = serializers.CharField(source="process.process_name", read_only=True)
    sketch_image_url = serializers.SerializerMethodField()
    source_pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = IntegratedChecksheetProcessBlock
        fields = [
            "id", "process", "process_code", "process_name",
            "sort_order", "sketch_image_url", "source_pdf_url",
            "items", "sketch_fields",
        ]

    def get_sketch_image_url(self, obj):
        if obj.sketch_image:
            try:
                return obj.sketch_image.url
            except Exception:
                pass
        return ""

    def get_source_pdf_url(self, obj):
        if obj.source_pdf:
            try:
                return obj.source_pdf.url
            except Exception:
                pass
        return ""


class IntegratedChecksheetTemplateListSerializer(serializers.ModelSerializer):
    """一覧用の軽量シリアライザ（process_blocks を含まない）"""
    product_code = serializers.CharField(source="product.product_code", read_only=True)
    product_name = serializers.CharField(source="product.product_name", read_only=True)

    class Meta:
        model = IntegratedChecksheetTemplate
        fields = [
            "id", "product", "product_code", "product_name",
            "name", "version", "status", "is_active",
            "updated_at",
        ]


class IntegratedChecksheetWorkflowLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = IntegratedChecksheetWorkflowLog
        fields = [
            "id", "action", "from_status", "to_status",
            "actor", "actor_name", "comment", "created_at",
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        return _format_user_name(obj.actor)


class IntegratedChecksheetTemplateSerializer(serializers.ModelSerializer):
    process_blocks = IntegratedChecksheetProcessBlockSerializer(many=True, read_only=True)
    workflow_logs = IntegratedChecksheetWorkflowLogSerializer(many=True, read_only=True)
    product_code = serializers.CharField(source="product.product_code", read_only=True)
    product_name = serializers.CharField(source="product.product_name", read_only=True)
    line_code = serializers.SerializerMethodField()
    line_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    reviewer_user_name = serializers.SerializerMethodField()
    chief_user_name = serializers.SerializerMethodField()
    approver_user_name = serializers.SerializerMethodField()

    class Meta:
        model = IntegratedChecksheetTemplate
        fields = [
            "id", "product", "product_code", "product_name",
            "line", "line_code", "line_name",
            "name", "document_title", "sheet_name",
            "revision_notes", "revision_date", "effective_from",
            "version", "status", "is_active",
            "reviewer_user", "reviewer_user_name",
            "chief_user", "chief_user_name",
            "approver_user", "approver_user_name",
            "rejection_comment",
            "submitted_items_snapshot",
            "created_by", "created_by_name",
            "reviewed_at", "chief_reviewed_at", "approved_at",
            "process_blocks", "workflow_logs", "created_at", "updated_at",
        ]
        read_only_fields = ["created_by"]

    def get_line_code(self, obj):
        return obj.line.line_code if obj.line else ""

    def get_line_name(self, obj):
        return obj.line.line_name if obj.line else ""

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or str(obj.created_by) if obj.created_by else ""

    def get_reviewer_user_name(self, obj):
        return _format_user_name(obj.reviewer_user)

    def get_chief_user_name(self, obj):
        return _format_user_name(obj.chief_user)

    def get_approver_user_name(self, obj):
        return _format_user_name(obj.approver_user)


class IntegratedChecksheetCheckSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.item_name", read_only=True)
    record_type = serializers.CharField(source="item.record_type", read_only=True)
    process_block_id = serializers.IntegerField(source="item.process_block_id", read_only=True)
    checked_by_name = serializers.SerializerMethodField()

    class Meta:
        model = IntegratedChecksheetCheck
        fields = [
            "id", "item", "item_name", "record_type", "process_block_id",
            "judgement", "numeric_value", "text_value", "photo_url",
            "checked_by", "checked_by_name", "checked_at",
        ]

    def get_checked_by_name(self, obj):
        return _format_user_name(obj.checked_by) if obj.checked_by_id else ""


class IntegratedChecksheetSketchResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegratedChecksheetSketchResponse
        fields = [
            "id", "process_block", "drawing_data", "field_responses",
            "created_at", "updated_at",
        ]


class IntegratedChecksheetUnitSerializer(serializers.ModelSerializer):
    checks = IntegratedChecksheetCheckSerializer(many=True, read_only=True)
    sketch_responses = IntegratedChecksheetSketchResponseSerializer(many=True, read_only=True)
    process_progress = serializers.SerializerMethodField()

    class Meta:
        model = IntegratedChecksheetUnit
        fields = [
            "id", "sequence_no", "sei_ban", "status",
            "completed_at", "approved_at", "approved_by",
            "checks", "sketch_responses", "process_progress",
        ]

    def get_process_progress(self, obj):
        blocks = getattr(obj, "_process_blocks", None)
        if not blocks:
            try:
                blocks = list(obj.batch.template.process_blocks.prefetch_related("items").order_by("sort_order"))
            except Exception:
                return []
        checks_by_item = {c.item_id: c for c in obj.checks.all()}
        result = []
        for block in blocks:
            items = list(block.items.all())
            total = len(items)
            done = sum(1 for it in items if it.id in checks_by_item and _is_checked(checks_by_item[it.id]))
            required_items = [it for it in items if it.is_required]
            required_total = len(required_items)
            required_done = sum(1 for it in required_items if it.id in checks_by_item and _is_checked(checks_by_item[it.id]))
            result.append({
                "process_block_id": block.id,
                "process_code": block.process.process_code,
                "sort_order": block.sort_order,
                "total": total,
                "done": done,
                "complete": required_total == 0 or required_done >= required_total,
            })
        return result


def _is_checked(check):
    if check.judgement:
        return True
    if check.numeric_value is not None:
        return True
    if check.text_value:
        return True
    return False


class IntegratedChecksheetBatchSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product.product_code", read_only=True)
    product_name = serializers.CharField(source="product.product_name", read_only=True)
    line_code = serializers.CharField(source="line.line_code", read_only=True)
    template_name = serializers.CharField(source="template.name", read_only=True, default="")
    unit_count = serializers.IntegerField(read_only=True, default=0)
    completed_count = serializers.IntegerField(read_only=True, default=0)
    process_progress = serializers.SerializerMethodField()

    leader_confirmed_by_name = serializers.SerializerMethodField()
    supervisor_confirmed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = IntegratedChecksheetBatch
        fields = [
            "id", "template", "template_name", "product", "product_code", "product_name",
            "line", "line_code", "plan_date", "quantity", "lot_no",
            "status", "unit_count", "completed_count", "process_progress",
            "leader_confirmed_by", "leader_confirmed_by_name", "leader_confirmed_at",
            "supervisor_confirmed_by", "supervisor_confirmed_by_name", "supervisor_confirmed_at",
            "created_at", "updated_at",
        ]

    def get_leader_confirmed_by_name(self, obj):
        return _format_user_name(obj.leader_confirmed_by) if obj.leader_confirmed_by_id else ""

    def get_supervisor_confirmed_by_name(self, obj):
        return _format_user_name(obj.supervisor_confirmed_by) if obj.supervisor_confirmed_by_id else ""

    def get_process_progress(self, obj):
        blocks = list(
            obj.template.process_blocks.select_related("process").prefetch_related("items").all()
        ) if obj.template_id else []
        units = list(obj.units.prefetch_related("checks__item__process_block").all())
        total_units = len(units)
        if total_units == 0:
            return [
                {
                    "process_block_id": block.id,
                    "process_code": block.process.process_code if block.process_id else "",
                    "process_name": block.process.process_name if block.process_id else "",
                    "done_units": 0,
                    "total_units": 0,
                }
                for block in blocks
            ]

        unit_checked_items = []
        for unit in units:
            checked_item_ids = set()
            for check in unit.checks.all():
                if _is_checked(check):
                    checked_item_ids.add(check.item_id)
            unit_checked_items.append(checked_item_ids)

        result = []
        for block in blocks:
            required_item_ids = {item.id for item in block.items.all() if item.is_required}
            if not required_item_ids:
                done_units = total_units
            else:
                done_units = sum(1 for checked_ids in unit_checked_items if required_item_ids.issubset(checked_ids))
            result.append({
                "process_block_id": block.id,
                "process_code": block.process.process_code if block.process_id else "",
                "process_name": block.process.process_name if block.process_id else "",
                "done_units": done_units,
                "total_units": total_units,
            })
        return result
