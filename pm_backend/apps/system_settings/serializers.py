from rest_framework import serializers
from .models import SystemSetting


class SystemSettingSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True)

    class Meta:
        model = SystemSetting
        fields = ['id', 'key', 'value', 'description', 'updated_at', 'updated_by_name']
        read_only_fields = ['id', 'key', 'description', 'updated_at', 'updated_by_name']
