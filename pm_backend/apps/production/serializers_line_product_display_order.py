from rest_framework import serializers
from .models_line_product_display_order import LineProductDisplayOrder


class LineProductDisplayOrderSerializer(serializers.ModelSerializer):
    line_code = serializers.CharField(source='line.line_code', read_only=True)

    class Meta:
        model = LineProductDisplayOrder
        fields = ['id', 'line', 'line_code', 'product_code', 'display_order', 'context',
                  'bg_color', 'text_color', 'plan_bg_color', 'plan_text_color',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
