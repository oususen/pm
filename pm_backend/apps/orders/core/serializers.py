from rest_framework import serializers

from .models import Order, OrderLine, StgOrderDaily, StgOrderRaw


class OrderLineSerializer(serializers.ModelSerializer):
    """Order line serializer"""
    product_name = serializers.SerializerMethodField()
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    effective_order_type = serializers.SerializerMethodField()
    customer_code = serializers.CharField(source='order.customer.customer_code', read_only=True)
    customer_name = serializers.CharField(source='order.customer.customer_name', read_only=True)
    customer_calendar_id = serializers.IntegerField(source='order.customer.calendar_id', read_only=True)
    order_no = serializers.CharField(source='order.order_no', read_only=True)

    class Meta:
        model = OrderLine
        fields = [
            'id', 'order', 'line_no', 'product', 'product_code', 'product_name',
            'order_type', 'order_type_display', 'effective_order_type',
            'customer_order_no', 'quantity', 'actual_shipment_qty', 'due_date', 'plant_code', 'ship_to_code', 'remark',
            'customer_code', 'customer_name', 'customer_calendar_id', 'order_no',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_product_name(self, obj):
        if obj.product:
            return obj.product.product_name
        return None

    def get_effective_order_type(self, obj):
        if obj.order_type:
            return obj.order_type
        if obj.order and obj.order.order_type:
            return obj.order.order_type
        return None


class OrderSerializer(serializers.ModelSerializer):
    """Order header serializer"""
    customer_name = serializers.SerializerMethodField()
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    lines = OrderLineSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'customer_name', 'order_no', 'order_type', 'order_type_display',
            'version_no', 'source_system', 'source_file', 'order_date', 'freeze_from',
            'status', 'status_display', 'lines', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_customer_name(self, obj):
        return obj.customer.customer_name


class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for order list (ヘッダのみ)"""
    customer_name = serializers.SerializerMethodField()
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'customer_name', 'order_no', 'order_type', 'order_type_display',
            'version_no', 'source_system', 'source_file', 'order_date', 'freeze_from',
            'status', 'status_display', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_customer_name(self, obj):
        return obj.customer.customer_name


class StgOrderRawSerializer(serializers.ModelSerializer):
    """Staging order raw data serializer"""
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    parse_status_display = serializers.CharField(source='get_parse_status_display', read_only=True)

    class Meta:
        model = StgOrderRaw
        fields = [
            'id', 'customer_code', 'order_type', 'order_type_display', 'source_system',
            'source_file', 'source_row_no', 'record_token', 'start_month', 'due_date',
            'product_code', 'quantity', 'raw_payload', 'parse_status', 'parse_status_display',
            'error_message', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StgOrderDailySerializer(serializers.ModelSerializer):
    """Staging order daily serializer"""
    customer_name = serializers.SerializerMethodField()
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)

    class Meta:
        model = StgOrderDaily
        fields = [
            'id', 'raw', 'customer', 'customer_name', 'order_type', 'order_type_display',
            'version_no', 'product_code', 'due_date', 'quantity', 'plant_code',
            'ship_to_code', 'source_system', 'source_file', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_customer_name(self, obj):
        if obj.customer:
            return obj.customer.customer_name
        return None
