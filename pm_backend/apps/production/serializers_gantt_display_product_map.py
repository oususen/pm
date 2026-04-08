from rest_framework import serializers

from .models_gantt_display_product_map import GanttDisplayProductMap


class GanttDisplayProductMapSerializer(serializers.ModelSerializer):
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    final_product_code = serializers.CharField(source='final_product.product_code', read_only=True)
    final_product_name = serializers.CharField(source='final_product.product_name', read_only=True)
    process_code = serializers.CharField(source='process.process_code', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    display_product_code = serializers.CharField(source='display_product.product_code', read_only=True)
    display_product_name = serializers.CharField(source='display_product.product_name', read_only=True)

    class Meta:
        model = GanttDisplayProductMap
        fields = [
            'id',
            'line',
            'line_code',
            'line_name',
            'final_product',
            'final_product_code',
            'final_product_name',
            'process',
            'process_code',
            'process_name',
            'display_product',
            'display_product_code',
            'display_product_name',
            'created_at',
            'updated_at',
            'updated_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'updated_by']

    def validate(self, attrs):
        attrs = super().validate(attrs)
        line = attrs.get('line') or getattr(self.instance, 'line', None)
        process = attrs.get('process') or getattr(self.instance, 'process', None)
        final_product = attrs.get('final_product') or getattr(self.instance, 'final_product', None)

        if final_product and not bool(getattr(final_product, 'is_line_final_product', False)):
            raise serializers.ValidationError({'final_product': 'ライン最終品を選択してください。'})

        if line and process and process.line_id and process.line_id != line.id:
            raise serializers.ValidationError({'process': '選択した工程は指定ラインと一致しません。'})

        return attrs
