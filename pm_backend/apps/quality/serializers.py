import re
from decimal import Decimal, InvalidOperation

from django.utils import timezone
from rest_framework import serializers

from .models import (
    EquipmentInspectionConfirmation,
    EquipmentInspectionItem,
    EquipmentInspectionItemAttachment,
    EquipmentInspectionRecord,
    EquipmentInspectionResult,
    EquipmentInspectionTask,
    EquipmentInspectionTemplate,
    EquipmentInspectionWorkflowLog,
)


def _user_display_name(user):
    if not user:
        return ""
    last_name = str(getattr(user, "last_name", "") or "").strip()
    first_name = str(getattr(user, "first_name", "") or "").strip()
    full_name = f"{last_name} {first_name}".strip()
    if full_name:
        return full_name
    username = str(getattr(user, "username", "") or "").strip()
    if username:
        return username
    return str(getattr(user, "email", "") or "").strip()


def _build_media_url(raw_url):
    if not raw_url:
        return raw_url
    path = str(raw_url)
    if path.startswith(("http://", "https://")):
        return path
    if path.startswith("/"):
        return path
    return f"/media/{path.lstrip('/')}"


def _normalize_judgement(value):
    return str(value or "").strip().upper()


def _normalize_numeric_text(value):
    text = str(value or "").strip()
    if not text:
        return ""
    return text.translate(
        str.maketrans(
            "０１２３４５６７８９．，－＋",
            "0123456789.,-+",
        )
    )


def _to_decimal(value):
    if value in ("", None):
        return None
    if isinstance(value, Decimal):
        return value
    raw = _normalize_numeric_text(value).replace(",", "")
    if not raw:
        return None
    try:
        return Decimal(raw)
    except (InvalidOperation, TypeError, ValueError):
        return None


def _normalize_rule_text(value):
    text = _normalize_numeric_text(value)
    if not text:
        return ""
    text = text.replace("\r", "\n").replace(" ", "").replace("\n", "")
    return text


def _parse_numeric_rule_text(value):
    text = _normalize_rule_text(value)
    if not text:
        return None

    range_match = re.search(r"([-+]?\d+(?:\.\d+)?)±([-+]?\d+(?:\.\d+)?)", text)
    if range_match:
        center = _to_decimal(range_match.group(1))
        tolerance = _to_decimal(range_match.group(2))
        if center is not None and tolerance is not None:
            tolerance = abs(tolerance)
            return {
                "type": "range",
                "min": center - tolerance,
                "max": center + tolerance,
            }

    min_match = re.search(r"([-+]?\d+(?:\.\d+)?)以上", text)
    if min_match:
        minimum = _to_decimal(min_match.group(1))
        if minimum is not None:
            return {"type": "min", "value": minimum}

    max_match = re.search(r"([-+]?\d+(?:\.\d+)?)以下", text)
    if max_match:
        maximum = _to_decimal(max_match.group(1))
        if maximum is not None:
            return {"type": "max", "value": maximum}

    return None


def _parse_numeric_rule(result_data):
    if str(result_data.get("record_type") or "").strip().upper() != EquipmentInspectionItem.RECORD_NUMERIC:
        return None

    for candidate in (result_data.get("criteria"), result_data.get("standard")):
        rule = _parse_numeric_rule_text(candidate)
        if rule:
            return rule
    return None


def _numeric_value_within_rule(result_data):
    numeric_value = _to_decimal(result_data.get("numeric_value"))
    if numeric_value is None:
        return None

    rule = _parse_numeric_rule(result_data)
    if not rule:
        return None

    if rule["type"] == "min":
        return numeric_value >= rule["value"]
    if rule["type"] == "max":
        return numeric_value <= rule["value"]
    if rule["type"] == "range":
        return rule["min"] <= numeric_value <= rule["max"]
    return None


def _has_result_value(result_data):
    record_type = str(result_data.get("record_type") or EquipmentInspectionItem.RECORD_CHECK).strip().upper()
    if record_type == EquipmentInspectionItem.RECORD_NUMERIC:
        return result_data.get("numeric_value") is not None
    if record_type == EquipmentInspectionItem.RECORD_TEXT:
        return bool(str(result_data.get("text_value") or "").strip())
    return _normalize_judgement(result_data.get("judgement")) in {
        EquipmentInspectionResult.JUDGEMENT_OK,
        EquipmentInspectionResult.JUDGEMENT_NG,
    }


def _required_result_errors(results_data):
    errors = []
    for index, result_data in enumerate(results_data, start=1):
        name = str(result_data.get("item_name") or "").strip() or f"{index}行目"
        has_value = _has_result_value(result_data)
        judgement = _normalize_judgement(result_data.get("judgement"))
        is_required = bool(result_data.get("is_required"))

        if is_required and not has_value:
            errors.append(f"{name}: 必須項目が未入力です。")
            continue

        if has_value and judgement not in {
            EquipmentInspectionResult.JUDGEMENT_OK,
            EquipmentInspectionResult.JUDGEMENT_NG,
        }:
            errors.append(f"{name}: 判定を入力してください。")
            continue

        if judgement == EquipmentInspectionResult.JUDGEMENT_OK and _numeric_value_within_rule(result_data) is False:
            errors.append(f"{name}: 測定値が判定基準を満たしていないためOKにできません。")
    return errors


def _calculate_overall_result(results_data):
    judgements = [_normalize_judgement(item.get("judgement")) for item in results_data]
    if EquipmentInspectionResult.JUDGEMENT_NG in judgements:
        return EquipmentInspectionRecord.RESULT_NG
    if EquipmentInspectionResult.JUDGEMENT_OK in judgements:
        return EquipmentInspectionRecord.RESULT_OK
    return ""


class EquipmentInspectionItemAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentInspectionItemAttachment
        fields = [
            "id",
            "display_order",
            "title",
            "description",
            "check_point",
            "ok_example",
            "ng_example",
            "image_url",
        ]
        read_only_fields = ["id"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["image_url"] = _build_media_url(data.get("image_url"))
        return data


class EquipmentInspectionItemSerializer(serializers.ModelSerializer):
    attachments = EquipmentInspectionItemAttachmentSerializer(many=True, required=False)

    class Meta:
        model = EquipmentInspectionItem
        fields = [
            "id",
            "section_type",
            "display_order",
            "inspection_no",
            "item_name",
            "standard",
            "frequency",
            "method",
            "record_type",
            "unit",
            "criteria",
            "is_required",
            "is_active",
            "attachments",
        ]
        read_only_fields = ["id"]


class EquipmentInspectionWorkflowLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = EquipmentInspectionWorkflowLog
        fields = [
            "id",
            "action",
            "from_status",
            "to_status",
            "actor",
            "actor_name",
            "comment",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        return _user_display_name(obj.actor)


class EquipmentInspectionTemplateSerializer(serializers.ModelSerializer):
    items = EquipmentInspectionItemSerializer(many=True)
    workflow_logs = EquipmentInspectionWorkflowLogSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    reviewer_user_name = serializers.SerializerMethodField()
    chief_user_name = serializers.SerializerMethodField()
    approver_user_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    chief_reviewed_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    process_ids = serializers.PrimaryKeyRelatedField(
        source="processes", many=True, read_only=True
    )
    line_ids = serializers.PrimaryKeyRelatedField(
        source="lines", many=True, read_only=True
    )

    class Meta:
        model = EquipmentInspectionTemplate
        fields = [
            "id",
            "sheet_code",
            "sheet_name",
            "title",
            "source_sheet_name",
            "revision_date",
            "revision_notes",
            "effective_from",
            "version",
            "status",
            "is_active",
            "processes",
            "process_ids",
            "lines",
            "line_ids",
            "created_by",
            "created_by_name",
            "reviewer_user",
            "reviewer_user_name",
            "chief_user",
            "chief_user_name",
            "approver_user",
            "approver_user_name",
            "reviewed_by",
            "reviewed_by_name",
            "chief_reviewed_by",
            "chief_reviewed_by_name",
            "approved_by",
            "approved_by_name",
            "reviewed_at",
            "chief_reviewed_at",
            "approved_at",
            "rejection_comment",
            "created_at",
            "updated_at",
            "items",
            "workflow_logs",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "status",
            "created_by",
            "reviewer_user",
            "chief_user",
            "approver_user",
            "reviewed_by",
            "chief_reviewed_by",
            "approved_by",
            "reviewed_at",
            "chief_reviewed_at",
            "approved_at",
        ]

    def get_created_by_name(self, obj):
        return _user_display_name(obj.created_by)

    def get_reviewer_user_name(self, obj):
        return _user_display_name(obj.reviewer_user)

    def get_chief_user_name(self, obj):
        return _user_display_name(obj.chief_user)

    def get_approver_user_name(self, obj):
        return _user_display_name(obj.approver_user)

    def get_reviewed_by_name(self, obj):
        return _user_display_name(obj.reviewed_by)

    def get_chief_reviewed_by_name(self, obj):
        return _user_display_name(obj.chief_reviewed_by)

    def get_approved_by_name(self, obj):
        return _user_display_name(obj.approved_by)

    def _save_items(self, template, items_data):
        template.items.all().delete()
        if not items_data:
            return

        created_items = []
        attachment_groups = []
        for index, item_data in enumerate(items_data, start=1):
            item_payload = dict(item_data)
            attachments_data = item_payload.pop("attachments", [])
            if not item_payload.get("display_order"):
                item_payload["display_order"] = index
            created_items.append(EquipmentInspectionItem(template=template, **item_payload))
            attachment_groups.append(attachments_data)

        created_items = EquipmentInspectionItem.objects.bulk_create(created_items)

        attachment_records = []
        for item, attachments_data in zip(created_items, attachment_groups):
            for attachment_index, attachment_data in enumerate(attachments_data, start=1):
                attachment_payload = dict(attachment_data)
                attachment_payload["display_order"] = (
                    int(attachment_payload.get("display_order") or attachment_index)
                )
                attachment_payload["image_url"] = str(attachment_payload.get("image_url") or "").strip()
                attachment_records.append(
                    EquipmentInspectionItemAttachment(item=item, **attachment_payload)
                )

        if attachment_records:
            EquipmentInspectionItemAttachment.objects.bulk_create(attachment_records)

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        processes_data = validated_data.pop("processes", None)
        lines_data = validated_data.pop("lines", None)
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        template = EquipmentInspectionTemplate.objects.create(**validated_data)
        if processes_data is not None:
            template.processes.set(processes_data)
        if lines_data is not None:
            template.lines.set(lines_data)
        self._save_items(template, items_data)
        return template

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        processes_data = validated_data.pop("processes", None)
        lines_data = validated_data.pop("lines", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if processes_data is not None:
            instance.processes.set(processes_data)
        if lines_data is not None:
            instance.lines.set(lines_data)
        if items_data is not None:
            self._save_items(instance, items_data)
        return instance


class EquipmentInspectionResultSerializer(serializers.ModelSerializer):
    reference_attachments = serializers.SerializerMethodField()

    class Meta:
        model = EquipmentInspectionResult
        fields = [
            "id",
            "item",
            "display_order",
            "inspection_no",
            "item_name",
            "standard",
            "frequency",
            "method",
            "record_type",
            "unit",
            "criteria",
            "is_required",
            "numeric_value",
            "text_value",
            "judgement",
            "comment",
            "measured_at",
            "reference_attachments",
        ]
        read_only_fields = ["id", "reference_attachments"]

    def get_reference_attachments(self, obj):
        item = getattr(obj, "item", None)
        if not item:
            return []
        serializer = EquipmentInspectionItemAttachmentSerializer(
            item.attachments.all(),
            many=True,
            context=self.context,
        )
        return serializer.data


class EquipmentInspectionRecordSerializer(serializers.ModelSerializer):
    results = EquipmentInspectionResultSerializer(many=True)
    operator_name = serializers.SerializerMethodField()
    result_count = serializers.SerializerMethodField()
    ng_count = serializers.SerializerMethodField()
    missing_required_count = serializers.SerializerMethodField()

    class Meta:
        model = EquipmentInspectionRecord
        fields = [
            "id",
            "template",
            "sheet_code",
            "sheet_name",
            "template_title",
            "template_version",
            "operation_date",
            "section_type",
            "operator",
            "operator_name",
            "status",
            "overall_result",
            "memo",
            "completed_at",
            "created_at",
            "updated_at",
            "result_count",
            "ng_count",
            "missing_required_count",
            "results",
        ]
        read_only_fields = [
            "id",
            "operator",
            "operator_name",
            "overall_result",
            "completed_at",
            "created_at",
            "updated_at",
            "result_count",
            "ng_count",
            "missing_required_count",
        ]

    def get_operator_name(self, obj):
        return _user_display_name(obj.operator)

    def get_result_count(self, obj):
        return len(obj.results.all())

    def get_ng_count(self, obj):
        return sum(
            1
            for result in obj.results.all()
            if _normalize_judgement(result.judgement) == EquipmentInspectionResult.JUDGEMENT_NG
        )

    def get_missing_required_count(self, obj):
        count = 0
        for result in obj.results.all():
            if not result.is_required:
                continue
            if not _has_result_value(
                {
                    "record_type": result.record_type,
                    "numeric_value": result.numeric_value,
                    "text_value": result.text_value,
                    "judgement": result.judgement,
                }
            ):
                count += 1
        return count

    def validate(self, attrs):
        results_data = attrs.get("results")
        status_value = str(attrs.get("status") or "").strip().upper()
        if results_data is None and self.instance is not None:
            results_data = list(self.instance.results.values())

        if status_value == EquipmentInspectionRecord.STATUS_COMPLETED:
            errors = _required_result_errors(results_data or [])
            if errors:
                raise serializers.ValidationError({"results": errors})
        return attrs

    def _save_results(self, record, results_data):
        record.results.all().delete()
        if not results_data:
            return

        result_records = []
        now = timezone.now()
        for index, result_data in enumerate(results_data, start=1):
            result_payload = dict(result_data)
            result_payload["judgement"] = _normalize_judgement(result_payload.get("judgement"))
            if not result_payload.get("display_order"):
                result_payload["display_order"] = index
            if result_payload.get("numeric_value") in ("", None):
                result_payload["numeric_value"] = None
            result_payload["text_value"] = str(result_payload.get("text_value") or "")
            if _has_result_value(result_payload):
                result_payload["measured_at"] = result_payload.get("measured_at") or now
            else:
                result_payload["measured_at"] = None
            result_records.append(EquipmentInspectionResult(record=record, **result_payload))

        EquipmentInspectionResult.objects.bulk_create(result_records)

    def _apply_record_state(self, instance, results_data):
        instance.overall_result = _calculate_overall_result(results_data)
        if instance.status == EquipmentInspectionRecord.STATUS_COMPLETED:
            instance.completed_at = timezone.now()
        else:
            instance.completed_at = None

    def create(self, validated_data):
        results_data = validated_data.pop("results", [])
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["operator"] = request.user
        instance = EquipmentInspectionRecord(**validated_data)
        self._apply_record_state(instance, results_data)
        instance.save()
        self._save_results(instance, results_data)
        return instance

    def update(self, instance, validated_data):
        results_data = validated_data.pop("results", None)
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            instance.operator = request.user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        current_results = results_data if results_data is not None else [
            {
                "record_type": result.record_type,
                "numeric_value": result.numeric_value,
                "text_value": result.text_value,
                "judgement": result.judgement,
                "is_required": result.is_required,
            }
            for result in instance.results.all()
        ]
        self._apply_record_state(instance, current_results)
        instance.save()
        if results_data is not None:
            self._save_results(instance, results_data)
        return instance


class EquipmentInspectionConfirmationSerializer(serializers.ModelSerializer):
    confirmed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = EquipmentInspectionConfirmation
        fields = [
            "id",
            "sheet_code",
            "sheet_name",
            "target_month",
            "confirm_type",
            "week_index",
            "confirmed_by",
            "confirmed_by_name",
            "comment",
            "confirmed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "confirmed_by",
            "confirmed_by_name",
            "confirmed_at",
            "created_at",
            "updated_at",
        ]

    def get_confirmed_by_name(self, obj):
        return _user_display_name(obj.confirmed_by)


class EquipmentInspectionTaskSerializer(serializers.ModelSerializer):
    assigned_to_username = serializers.CharField(source="assigned_to.username", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    sheet_code = serializers.CharField(source="template.sheet_code", read_only=True)
    sheet_name = serializers.CharField(source="template.sheet_name", read_only=True)
    template_title = serializers.CharField(source="template.title", read_only=True)
    template_version = serializers.IntegerField(source="template.version", read_only=True)
    template_status = serializers.CharField(source="template.status", read_only=True)
    module_code = serializers.SerializerMethodField()
    module_label = serializers.SerializerMethodField()
    task_category = serializers.SerializerMethodField()
    task_category_label = serializers.SerializerMethodField()

    class Meta:
        model = EquipmentInspectionTask
        fields = [
            "id",
            "template",
            "sheet_code",
            "sheet_name",
            "template_title",
            "template_version",
            "template_status",
            "task_type",
            "assigned_to",
            "assigned_to_username",
            "assigned_to_name",
            "status",
            "due_date",
            "created_at",
            "done_at",
            "module_code",
            "module_label",
            "task_category",
            "task_category_label",
        ]
        read_only_fields = ["id", "created_at", "done_at"]

    def get_assigned_to_name(self, obj):
        return _user_display_name(obj.assigned_to)

    def get_module_code(self, obj):
        return "QUALITY"

    def get_module_label(self, obj):
        return "品質"

    def get_task_category(self, obj):
        return "EQUIPMENT_INSPECTION"

    def get_task_category_label(self, obj):
        return "設備点検表"
