from rest_framework import serializers

from .models_progress_monitor import ProgressMonitorTarget


class ProgressMonitorTargetSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    registered_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ProgressMonitorTarget
        fields = [
            'id', 'product', 'product_code', 'product_name',
            'line', 'line_code', 'line_name', 'display_order', 'memo',
            'is_active', 'registered_by', 'registered_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['registered_by', 'created_at', 'updated_at']

    def get_registered_by_name(self, obj):
        if not obj.registered_by_id:
            return ''
        return obj.registered_by.get_full_name() or obj.registered_by.username
