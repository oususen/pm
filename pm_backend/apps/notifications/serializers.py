from rest_framework import serializers
from .models import Notification, NotificationRead


class NotificationSerializer(serializers.ModelSerializer):
    target_department_names = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()

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
            'is_read',
        ]

    def get_target_department_names(self, obj):
        return [dept.name for dept in obj.target_departments.all()]

    def get_is_read(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return NotificationRead.objects.filter(
            notification=obj,
            user=request.user
        ).exists()
