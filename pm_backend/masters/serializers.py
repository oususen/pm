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

    class Meta:
        model = BOMItem
        fields = '__all__'


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
