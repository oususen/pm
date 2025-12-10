# -*- coding: utf-8 -*-
from decimal import Decimal

from rest_framework import serializers
from .models import LineDemand, Order, OrderLine, StgOrderRaw, StgOrderDaily
from .models_line_backlog import LineBacklog
from masters.models import Customer, Product


class OrderLineSerializer(serializers.ModelSerializer):
    """Order line serializer"""
    product_name = serializers.SerializerMethodField()

    class Meta:
        model = OrderLine
        fields = [
            'id', 'order', 'line_no', 'product', 'product_code', 'product_name',
            'quantity', 'due_date', 'plant_code', 'ship_to_code', 'remark',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_product_name(self, obj):
        if obj.product:
            return obj.product.product_name
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


class LineDemandSerializer(serializers.ModelSerializer):
    """ライン別需要展開のシリアライザ"""

    line_name = serializers.SerializerMethodField()
    line_code = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    required_qty = serializers.SerializerMethodField()
    process = serializers.SerializerMethodField()

    class Meta:
        model = LineDemand
        fields = [
            'id', 'line', 'line_code', 'line_name', 'routing_step', 'process', 'product', 'product_code', 'product_name',
            'plan_date', 'lead_time_days',
            'forecast_qty', 'firm_qty', 'plan_qty', 'actual_qty',
            'plan_progress', 'actual_progress', 'required_qty',
            'order_numbers', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'plan_progress', 'actual_progress', 'required_qty']

    def get_line_name(self, obj):
        return obj.line.line_name if obj.line_id else None

    def get_line_code(self, obj):
        return obj.line.line_code if obj.line_id else None

    def get_product_name(self, obj):
        return obj.product.product_name if obj.product_id else None

    def get_required_qty(self, obj):
        return (obj.firm_qty or Decimal('0')) + (obj.forecast_qty or Decimal('0'))

    def get_process(self, obj):
        if obj.routing_step_id and obj.routing_step and obj.routing_step.process_id:
            return obj.routing_step.process_id
        return None


class LineBacklogSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    process_code = serializers.CharField(source='process.process_code', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)

    class Meta:
        model = LineBacklog
        fields = [
            'id', 'plan_date', 'process', 'process_code', 'process_name',
            'product', 'product_code', 'product_name',
            'line', 'line_code', 'line_name',
            'demand_qty_plan', 'plan_qty', 'actual_qty', 'stock_qty', 'planned_stock_qty',
            'source_line', 'source_routing_step', 'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']
