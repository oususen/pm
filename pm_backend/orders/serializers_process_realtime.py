"""
工程実時間記録用のSerializer
"""
from rest_framework import serializers
from masters.models import Process, Product
from .models_process_realtime import ProcessRealtimeRecord


class ProcessRealtimeRecordSerializer(serializers.ModelSerializer):
    """工程実時間記録Serializer"""

    process_code = serializers.CharField(source='process.process_code', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    record_type_display = serializers.CharField(source='get_record_type_display', read_only=True)
    equipment_state_display = serializers.CharField(source='get_equipment_state_display', read_only=True)
    product_code = serializers.CharField(read_only=True)
    product_name = serializers.CharField(read_only=True)

    class Meta:
        model = ProcessRealtimeRecord
        fields = [
            'id',
            'process',
            'process_code',
            'process_name',
            'product',
            'product_code',
            'product_name',
            'timestamp',
            'record_type',
            'record_type_display',
            'qty',
            'equipment_state',
            'equipment_state_display',
            'event_data',
            'batch_no',
            'operator_name',
            'remarks',
        ]
        read_only_fields = ['id', 'timestamp']


class ProcessRealtimeCreateSerializer(serializers.Serializer):
    """工程実時間記録作成用Serializer（簡易入力）"""

    process_id = serializers.IntegerField()
    product_id = serializers.IntegerField(required=False, allow_null=True)
    product_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    product_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    record_type = serializers.ChoiceField(choices=ProcessRealtimeRecord.RECORD_TYPE_CHOICES)
    qty = serializers.DecimalField(max_digits=10, decimal_places=3, default=0)
    equipment_state = serializers.ChoiceField(
        choices=ProcessRealtimeRecord.EQUIPMENT_STATE_CHOICES,
        required=False,
        allow_null=True
    )
    batch_no = serializers.CharField(max_length=100, required=False, allow_blank=True)
    operator_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    remarks = serializers.CharField(required=False, allow_blank=True)
    event_data = serializers.JSONField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs.get('record_type') == 'PRODUCTION':
            has_product_id = bool(attrs.get('product_id'))
            has_product_code = bool((attrs.get('product_code') or '').strip())
            if not has_product_id and not has_product_code:
                raise serializers.ValidationError({'product_id': '生産記録は製品（品番）の指定が必要です。'})
        return attrs

    def create(self, validated_data):
        process_id = validated_data.pop('process_id')
        try:
            process = Process.objects.get(id=process_id)
        except Process.DoesNotExist as exc:
            raise serializers.ValidationError({'process_id': '指定された工程が存在しません。'}) from exc

        product = None
        product_id = validated_data.pop('product_id', None)
        product_code = (validated_data.pop('product_code', None) or '').strip() or None
        product_name = (validated_data.pop('product_name', None) or '').strip() or None

        if product_id:
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist as exc:
                raise serializers.ValidationError({'product_id': '指定された製品が存在しません。'}) from exc
        elif product_code:
            product = Product.objects.filter(product_code=product_code).first()

        if product:
            product_code = product.product_code
            product_name = product.product_name

        return ProcessRealtimeRecord.objects.create(
            process=process,
            product=product,
            product_code=product_code,
            product_name=product_name,
            **validated_data
        )

