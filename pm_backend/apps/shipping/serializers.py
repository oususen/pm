from rest_framework import serializers

from masters.models import Customer, Product
from orders.core.models import KubotaSakaiDueAdjustment, KubotaSakaiTripAssignment
from .models import ShipmentActual, ShipmentActualHistory, ShipToLeadTime


class ShipmentActualSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = ShipmentActual
        fields = [
            'id', 'shipment_date',
            'product', 'product_code', 'product_name',
            'customer', 'customer_code', 'customer_name',
            'ship_to_code', 'quantity', 'remark',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'product_name', 'customer_name']

    def get_product_name(self, obj):
        if obj.product_id and obj.product:
            return obj.product.product_name
        code = str(getattr(obj, 'product_code', '') or '').strip()
        if not code:
            return None
        cache = self.context.setdefault('_product_name_by_code', {})
        if code not in cache:
            cache[code] = Product.objects.filter(product_code=code).values_list('product_name', flat=True).first()
        return cache.get(code)

    def get_customer_name(self, obj):
        if obj.customer_id and obj.customer:
            return obj.customer.customer_name
        return None

    def validate(self, attrs):
        # 製品コード/得意先コードからマスタを補完
        product = attrs.get('product') or getattr(self.instance, 'product', None)
        product_code = attrs.get('product_code')
        if product_code:
            product_match = Product.objects.filter(product_code=product_code).first()
            if product_match:
                attrs['product'] = product_match
        elif product:
            attrs['product_code'] = product.product_code

        customer = attrs.get('customer') or getattr(self.instance, 'customer', None)
        customer_code = attrs.get('customer_code')
        if customer_code is not None:
            raw_code = str(customer_code).strip()
            customer_code = raw_code
            if customer_code.isdigit() and len(customer_code) < 6:
                customer_code = customer_code.zfill(6)
            attrs['customer_code'] = customer_code

            customer_match = Customer.objects.filter(customer_code=customer_code).first()
            if not customer_match and raw_code.isdigit():
                customer_match = Customer.objects.filter(id=int(raw_code)).first()
            if customer_match:
                attrs['customer'] = customer_match
                attrs['customer_code'] = customer_match.customer_code
        elif customer:
            attrs['customer_code'] = customer.customer_code

        return attrs


class ShipmentActualHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentActualHistory
        fields = [
            'id', 'shipment_actual', 'action',
            'shipment_date', 'product_code', 'customer_code', 'ship_to_code',
            'quantity', 'remark', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ShipToLeadTimeSerializer(serializers.ModelSerializer):
    customer_code = serializers.CharField(source='customer.customer_code', read_only=True)
    customer_name = serializers.CharField(source='customer.customer_name', read_only=True)
    calendar_name = serializers.CharField(source='calendar.calendar_name', read_only=True, default=None)

    class Meta:
        model = ShipToLeadTime
        fields = [
            'id', 'customer', 'customer_code', 'customer_name',
            'ship_to_code', 'ship_to_name', 'additional_days',
            'calendar', 'calendar_name',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'customer_code', 'customer_name', 'calendar_name', 'created_at', 'updated_at']


class KubotaSakaiDueAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KubotaSakaiDueAdjustment
        fields = [
            'id',
            'product_code',
            'ship_to_code',
            'source_order_no',
            'order_type',
            'due_date',
            'demand_qty',
            'delivery_qty',
            'remaining_qty',
            'order_line',
            'updated_by',
            'updated_at',
            'created_at',
        ]
        read_only_fields = ['id', 'remaining_qty', 'created_at']


class KubotaSakaiTripAssignmentSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source='due_adjustment.product_code', read_only=True)
    due_date = serializers.DateField(source='due_adjustment.due_date', read_only=True)
    truck_name = serializers.CharField(source='truck.name', read_only=True)

    class Meta:
        model = KubotaSakaiTripAssignment
        fields = [
            'id',
            'due_adjustment',
            'truck',
            'departure_date',
            'qty',
            'created_by',
            'created_at',
            'updated_at',
            'product_code',
            'due_date',
            'truck_name',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at', 'product_code', 'due_date', 'truck_name']
