from rest_framework import serializers

from masters.models import Customer, Product
from orders.core.models import KubotaSakaiDueAdjustment, KubotaSakaiTripAssignment
from .models import ShipmentActual, ShipmentActualHistory, ShipmentActualSplit, ShipToLeadTime


class ShipmentActualSplitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentActualSplit
        fields = ['id', 'line_no', 'production_date', 'quantity', 'source_order_no']
        read_only_fields = ['id']


class ShipmentActualSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    production_splits = ShipmentActualSplitSerializer(source='splits', many=True, read_only=True)
    trip_id = serializers.SerializerMethodField()
    trip_code = serializers.SerializerMethodField()
    trip_ref = serializers.SerializerMethodField()
    business_type = serializers.SerializerMethodField()
    departure_date = serializers.SerializerMethodField()
    departure_time_plan = serializers.SerializerMethodField()
    departure_time_actual = serializers.SerializerMethodField()
    departed_by_name = serializers.SerializerMethodField()
    source_order_nos = serializers.SerializerMethodField()

    class Meta:
        model = ShipmentActual
        fields = [
            'id', 'shipment_date',
            'shipping_trip_allocation',
            'product', 'product_code', 'product_name',
            'customer', 'customer_code', 'customer_name',
            'ship_to_code', 'quantity', 'remark', 'production_splits',
            'trip_id', 'trip_code', 'trip_ref', 'business_type',
            'departure_date', 'departure_time_plan', 'departure_time_actual',
            'departed_by_name',
            'source_order_nos',
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

    def _trip(self, obj):
        allocation = getattr(obj, 'shipping_trip_allocation', None)
        return getattr(allocation, 'trip', None) if allocation else None

    def get_trip_id(self, obj):
        trip = self._trip(obj)
        return trip.id if trip else None

    def get_trip_code(self, obj):
        trip = self._trip(obj)
        if not trip:
            return None
        return (trip.trip_code or '').strip() or (trip.trip_ref or '').strip() or None

    def get_trip_ref(self, obj):
        trip = self._trip(obj)
        return getattr(trip, 'trip_ref', None) if trip else None

    def get_business_type(self, obj):
        trip = self._trip(obj)
        return getattr(trip, 'business_type', None) if trip else None

    def get_departure_date(self, obj):
        trip = self._trip(obj)
        if not trip or not trip.departure_date:
            return None
        return trip.departure_date.isoformat()

    def get_departure_time_plan(self, obj):
        trip = self._trip(obj)
        if not trip or not trip.departure_time_plan:
            return None
        return trip.departure_time_plan.strftime('%H:%M')

    def get_departure_time_actual(self, obj):
        trip = self._trip(obj)
        if not trip or not trip.departure_time_actual:
            return None
        return trip.departure_time_actual.strftime('%Y-%m-%d %H:%M')

    def get_departed_by_name(self, obj):
        trip = self._trip(obj)
        user = getattr(trip, 'departed_by', None) if trip else None
        if not user:
            return None
        last = str(getattr(user, 'last_name', '') or '').strip()
        first = str(getattr(user, 'first_name', '') or '').strip()
        if last and first:
            return f'{last} {first}'
        return last or first or str(getattr(user, 'username', '') or '')

    def get_source_order_nos(self, obj):
        values = []
        seen = set()
        for split in getattr(obj, 'splits', []).all() if hasattr(getattr(obj, 'splits', None), 'all') else []:
            order_no = str(split.source_order_no or '').strip()
            if order_no and order_no not in seen:
                seen.add(order_no)
                values.append(order_no)
        return values

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
            'ship_to_code', 'ship_to_name', 'additional_days', 'bg_color', 'text_color',
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
