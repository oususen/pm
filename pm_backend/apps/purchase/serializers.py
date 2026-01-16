from rest_framework import serializers

from .models import PurchasePlanLockSetting


class PurchasePlanLockSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchasePlanLockSetting
        fields = ['id', 'lock_days', 'updated_at', 'updated_by']
        read_only_fields = ['id', 'updated_at', 'updated_by']
