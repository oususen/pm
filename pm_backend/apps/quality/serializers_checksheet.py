from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from .models_checksheet import (
    ProductChecksheetBatch,
    ProductChecksheetField,
    ProductChecksheetPhoto,
    ProductChecksheetRecord,
    ProductChecksheetTemplate,
    ProductChecksheetWorkflowLog,
)


def _display_user_name(user):
    if not user:
        return ""
    full_name = f"{getattr(user, 'last_name', '') or ''} {getattr(user, 'first_name', '') or ''}".strip()
    return full_name or getattr(user, "username", "") or getattr(user, "email", "") or ""


def _media_url(field):
    if not field:
        return ""
    try:
        return field.url
    except Exception:
        return ""


class ProductChecksheetFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductChecksheetField
        fields = [
            "id",
            "key",
            "label",
            "field_type",
            "description",
            "x",
            "y",
            "width",
            "height",
            "required",
            "placeholder",
            "sort_order",
            "show_label",
            "text_direction",
            "counter_step",
        ]
        read_only_fields = ["id"]


class ProductChecksheetWorkflowLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = ProductChecksheetWorkflowLog
        fields = ["id", "action", "from_status", "to_status", "actor", "actor_name", "comment", "created_at"]
        read_only_fields = fields

    def get_actor_name(self, obj):
        return _display_user_name(obj.actor)


class ProductChecksheetTemplateSerializer(serializers.ModelSerializer):
    line_code = serializers.CharField(source="line.line_code", read_only=True)
    line_name = serializers.CharField(source="line.line_name", read_only=True)
    process_code = serializers.CharField(source="process.process_code", read_only=True)
    process_name = serializers.CharField(source="process.process_name", read_only=True)
    product_code = serializers.CharField(source="product.product_code", read_only=True)
    product_name = serializers.CharField(source="product.product_name", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    reviewer_user_name = serializers.SerializerMethodField()
    chief_user_name = serializers.SerializerMethodField()
    approver_user_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    chief_reviewed_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    background_image_url = serializers.SerializerMethodField()
    source_pdf_url = serializers.SerializerMethodField()
    source_image_url = serializers.SerializerMethodField()
    fields_data = ProductChecksheetFieldSerializer(source="fields", many=True, read_only=True)
    workflow_logs = ProductChecksheetWorkflowLogSerializer(many=True, read_only=True)

    class Meta:
        model = ProductChecksheetTemplate
        fields = [
            "id",
            "name",
            "line", "line_code", "line_name",
            "process", "process_code", "process_name",
            "product", "product_code", "product_name",
            "version",
            "status",
            "is_active",
            "document_title",
            "sheet_name",
            "revision_date",
            "revision_notes",
            "effective_from",
            "source_type",
            "source_pdf", "source_pdf_url",
            "source_image", "source_image_url",
            "background_image", "background_image_url",
            "background_width",
            "background_height",
            "editor_notes",
            "created_by", "created_by_name",
            "reviewer_user", "reviewer_user_name",
            "chief_user", "chief_user_name",
            "approver_user", "approver_user_name",
            "reviewed_by", "reviewed_by_name",
            "chief_reviewed_by", "chief_reviewed_by_name",
            "approved_by", "approved_by_name",
            "reviewed_at",
            "chief_reviewed_at",
            "approved_at",
            "rejection_comment",
            "submitted_fields_snapshot",
            "created_at",
            "updated_at",
            "fields_data",
            "workflow_logs",
        ]
        read_only_fields = [
            "id", "created_by", "created_by_name",
            "reviewer_user", "reviewer_user_name",
            "chief_user", "chief_user_name",
            "approver_user", "approver_user_name",
            "reviewed_by", "reviewed_by_name",
            "chief_reviewed_by", "chief_reviewed_by_name",
            "approved_by", "approved_by_name",
            "reviewed_at", "chief_reviewed_at", "approved_at",
            "submitted_fields_snapshot",
            "created_at", "updated_at",
            "fields_data", "workflow_logs",
            "background_image_url", "source_pdf_url", "source_image_url",
        ]

    def get_created_by_name(self, obj):
        return _display_user_name(obj.created_by)

    def get_reviewer_user_name(self, obj):
        return _display_user_name(obj.reviewer_user)

    def get_chief_user_name(self, obj):
        return _display_user_name(obj.chief_user)

    def get_approver_user_name(self, obj):
        return _display_user_name(obj.approver_user)

    def get_reviewed_by_name(self, obj):
        return _display_user_name(obj.reviewed_by)

    def get_chief_reviewed_by_name(self, obj):
        return _display_user_name(obj.chief_reviewed_by)

    def get_approved_by_name(self, obj):
        return _display_user_name(obj.approved_by)

    def get_background_image_url(self, obj):
        return _media_url(obj.background_image)

    def get_source_pdf_url(self, obj):
        return _media_url(obj.source_pdf)

    def get_source_image_url(self, obj):
        return _media_url(obj.source_image)


class ProductChecksheetPhotoSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductChecksheetPhoto
        fields = ["id", "field_key", "image", "image_url", "created_at"]
        read_only_fields = ["id", "image_url", "created_at"]

    def get_image_url(self, obj):
        return _media_url(obj.image)


class ProductChecksheetRecordSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="batch.product.product_code", read_only=True)
    product_name = serializers.CharField(source="batch.product.product_name", read_only=True)
    line_code = serializers.CharField(source="batch.line.line_code", read_only=True)
    process_code = serializers.CharField(source="batch.process.process_code", read_only=True)
    lot_no = serializers.CharField(source="batch.lot_no", read_only=True)
    quantity = serializers.IntegerField(source="batch.quantity", read_only=True)
    generated_pdf_url = serializers.SerializerMethodField()
    photos = ProductChecksheetPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = ProductChecksheetRecord
        fields = [
            "id",
            "batch",
            "template",
            "sequence_no",
            "status",
            "responses_json",
            "planned_ship_date",
            "shipment_unit_no",
            "shipment_sequence_no",
            "completed_by_name",
            "completed_at",
            "supervisor_name",
            "approved_at",
            "generated_pdf",
            "generated_pdf_url",
            "created_at",
            "updated_at",
            "product_code",
            "product_name",
            "line_code",
            "process_code",
            "lot_no",
            "quantity",
            "photos",
        ]
        read_only_fields = [
            "id", "batch", "template", "sequence_no",
            "status", "completed_at", "approved_at",
            "generated_pdf", "generated_pdf_url",
            "created_at", "updated_at",
            "product_code", "product_name",
            "line_code", "process_code",
            "lot_no", "quantity", "photos",
        ]

    def get_generated_pdf_url(self, obj):
        return _media_url(obj.generated_pdf)


class ProductChecksheetBatchSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)
    version_no = serializers.IntegerField(source="template.version", read_only=True)
    line_code = serializers.CharField(source="line.line_code", read_only=True)
    line_name = serializers.CharField(source="line.line_name", read_only=True)
    process_code = serializers.CharField(source="process.process_code", read_only=True)
    process_name = serializers.CharField(source="process.process_name", read_only=True)
    product_code = serializers.CharField(source="product.product_code", read_only=True)
    product_name = serializers.CharField(source="product.product_name", read_only=True)
    completed_count = serializers.SerializerMethodField()
    approved_count = serializers.SerializerMethodField()
    is_complete = serializers.SerializerMethodField()
    template_detail = ProductChecksheetTemplateSerializer(source="template", read_only=True)

    class Meta:
        model = ProductChecksheetBatch
        fields = [
            "id",
            "template",
            "template_name",
            "template_detail",
            "version_no",
            "production_order",
            "line", "line_code", "line_name",
            "process", "process_code", "process_name",
            "product", "product_code", "product_name",
            "plan_date",
            "lot_no",
            "quantity",
            "operator_name",
            "source_context",
            "status",
            "completed_count",
            "approved_count",
            "is_complete",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_completed_count(self, obj):
        if hasattr(obj, "completed_count_value"):
            return obj.completed_count_value
        return obj.records.filter(status__in=[ProductChecksheetRecord.STATUS_COMPLETED, ProductChecksheetRecord.STATUS_APPROVED]).count()

    def get_approved_count(self, obj):
        if hasattr(obj, "approved_count_value"):
            return obj.approved_count_value
        return obj.records.filter(status=ProductChecksheetRecord.STATUS_APPROVED).count()

    def get_is_complete(self, obj):
        return self.get_completed_count(obj) >= obj.quantity


class ProductChecksheetPrepareSerializer(serializers.Serializer):
    production_order = serializers.IntegerField(required=False, allow_null=True)
    line = serializers.IntegerField()
    process = serializers.IntegerField()
    product = serializers.IntegerField()
    quantity = serializers.CharField()
    lot_no = serializers.CharField(required=False, allow_blank=True, default="")
    operator_name = serializers.CharField(required=False, allow_blank=True, default="")
    source_context = serializers.JSONField(required=False)

    def validate_quantity(self, value):
        try:
            dec = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise serializers.ValidationError("数量は数値で入力してください。") from exc
        if dec <= 0:
            raise serializers.ValidationError("数量は1以上で入力してください。")
        if dec != dec.to_integral_value():
            raise serializers.ValidationError("製品チェックシート対象数量は整数で入力してください。")
        return int(dec)
