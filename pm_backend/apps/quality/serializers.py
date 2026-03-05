from rest_framework import serializers

from .models import (
    EquipmentInspectionItem,
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


class EquipmentInspectionItemSerializer(serializers.ModelSerializer):
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
    approver_user_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

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
            "created_by",
            "created_by_name",
            "reviewer_user",
            "reviewer_user_name",
            "approver_user",
            "approver_user_name",
            "reviewed_by",
            "reviewed_by_name",
            "approved_by",
            "approved_by_name",
            "reviewed_at",
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
            "approver_user",
            "reviewed_by",
            "approved_by",
            "reviewed_at",
            "approved_at",
        ]

    def get_created_by_name(self, obj):
        return _user_display_name(obj.created_by)

    def get_reviewer_user_name(self, obj):
        return _user_display_name(obj.reviewer_user)

    def get_approver_user_name(self, obj):
        return _user_display_name(obj.approver_user)

    def get_reviewed_by_name(self, obj):
        return _user_display_name(obj.reviewed_by)

    def get_approved_by_name(self, obj):
        return _user_display_name(obj.approved_by)

    def _save_items(self, template, items_data):
        template.items.all().delete()
        if not items_data:
            return
        EquipmentInspectionItem.objects.bulk_create(
            [EquipmentInspectionItem(template=template, **item) for item in items_data]
        )

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        template = EquipmentInspectionTemplate.objects.create(**validated_data)
        self._save_items(template, items_data)
        return template

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            self._save_items(instance, items_data)
        return instance
