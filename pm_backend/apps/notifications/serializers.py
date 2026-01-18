from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    target_department_name = serializers.CharField(source='target_department.name', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'title',
            'category',
            'domain',
            'target_department',
            'target_department_name',
            'target_position',
            'valid_from',
            'valid_to',
            'display_order',
            'description',
            'operator_name',
            'created_at',
            'updated_at',
        ]
