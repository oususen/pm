from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    target_department_names = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id',
            'title',
            'category',
            'domain',
            'target_departments',
            'target_department_names',
            'target_positions',
            'valid_from',
            'valid_to',
            'display_order',
            'description',
            'operator_name',
            'created_at',
            'updated_at',
        ]

    def get_target_department_names(self, obj):
        return [dept.name for dept in obj.target_departments.all()]
