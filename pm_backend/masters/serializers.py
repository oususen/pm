from rest_framework import serializers
from .models import (
    Product, Customer, Process, Line, Supplier, Calendar, CalendarDay,
    BOM, BOMItem, Routing, RoutingStep
)


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'


class ProcessSerializer(serializers.ModelSerializer):
    line_name = serializers.CharField(source='line.line_name', read_only=True)

    class Meta:
        model = Process
        fields = '__all__'


class LineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Line
        fields = '__all__'


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'


class CalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calendar
        fields = '__all__'


class CalendarDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarDay
        fields = '__all__'


class BOMItemSerializer(serializers.ModelSerializer):
    child_product_name = serializers.CharField(source='child_product.product_name', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)

    class Meta:
        model = BOMItem
        fields = '__all__'

    def validate(self, attrs):
        sourcing_type = attrs.get('sourcing_type', getattr(self.instance, 'sourcing_type', None))
        time_unit = attrs.get('time_unit', getattr(self.instance, 'time_unit', 'MINUTE'))
        process = attrs.get('process', getattr(self.instance, 'process', None))

        if sourcing_type == 'MAKE' and process is None:
            raise serializers.ValidationError('自社製造の場合、工程は必須です。')

        if time_unit not in ['MINUTE', 'DAY']:
            raise serializers.ValidationError('時間単位は MINUTE か DAY を指定してください。')

        if time_unit == 'MINUTE':
            duration_min = attrs.get('duration_min', getattr(self.instance, 'duration_min', None))
            if duration_min is None or duration_min <= 0:
                raise serializers.ValidationError('時間単位=MINUTEのとき、所要時間(分)は1以上で入力してください。')
        else:
            lead_time_days = attrs.get('lead_time_days', getattr(self.instance, 'lead_time_days', 0))
            if lead_time_days is None or lead_time_days <= 0:
                raise serializers.ValidationError('時間単位=DAYのとき、リードタイム(日)は1以上で入力してください。')

        return attrs


class BOMSerializer(serializers.ModelSerializer):
    items = BOMItemSerializer(many=True, read_only=True)
    parent_product_name = serializers.CharField(source='parent_product.product_name', read_only=True)

    class Meta:
        model = BOM
        fields = '__all__'


class RoutingStepSerializer(serializers.ModelSerializer):
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)

    class Meta:
        model = RoutingStep
        fields = '__all__'


class RoutingSerializer(serializers.ModelSerializer):
    steps = RoutingStepSerializer(many=True, read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = Routing
        fields = '__all__'
