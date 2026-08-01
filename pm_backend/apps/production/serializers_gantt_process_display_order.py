from rest_framework import serializers

from .models_gantt_process_display_order import GanttProcessDisplayOrder


class GanttProcessDisplayOrderSerializer(serializers.ModelSerializer):
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    process_code = serializers.CharField(source='process.process_code', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)

    class Meta:
        model = GanttProcessDisplayOrder
        fields = [
            'id',
            'line',
            'line_code',
            'line_name',
            'process',
            'process_code',
            'process_name',
            'display_order',
            'updated_at',
            'updated_by',
        ]
        read_only_fields = ['id', 'updated_at', 'updated_by']
