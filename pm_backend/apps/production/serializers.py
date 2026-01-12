from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce
from rest_framework import serializers

from .models import LineDemand
from .models_line_backlog import LineBacklog
from .models_line_plan import LinePlan
from .models_line_gantt_plan import LineGanttPlan
from .models_process_realtime import ProcessRealtimeRecord
from .models_production import ProcessActual, ProductionOrder, StockAllocation


class LineDemandSerializer(serializers.ModelSerializer):
    """ライン別需要展開のシリアライザ"""

    line_name = serializers.SerializerMethodField()
    line_code = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    is_final_product = serializers.BooleanField(source='product.is_final_product', read_only=True)
    required_qty = serializers.SerializerMethodField()
    process = serializers.SerializerMethodField()
    process_code = serializers.SerializerMethodField()
    process_name = serializers.SerializerMethodField()

    class Meta:
        model = LineDemand
        fields = [
            'id', 'line', 'line_code', 'line_name', 'routing_step', 'process', 'process_code', 'process_name',
            'product', 'product_code', 'product_name', 'is_final_product',
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

    def get_process_code(self, obj):
        if obj.routing_step_id and obj.routing_step and obj.routing_step.process_id:
            return obj.routing_step.process.process_code
        return None

    def get_process_name(self, obj):
        if obj.routing_step_id and obj.routing_step and obj.routing_step.process_id:
            return obj.routing_step.process.process_name
        return None


class LineBacklogSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    process_code = serializers.CharField(source='process.process_code', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    is_final_product = serializers.BooleanField(source='product.is_final_product', read_only=True)
    is_line_final_product = serializers.BooleanField(source='product.is_line_final_product', read_only=True)
    firm_order_qty = serializers.IntegerField(read_only=True)
    forecast_order_qty = serializers.IntegerField(read_only=True)
    computed_time_min = serializers.SerializerMethodField()
    work_minutes = serializers.SerializerMethodField()
    step_no = serializers.SerializerMethodField()
    cycle_time_min = serializers.SerializerMethodField()
    routing_product_id = serializers.SerializerMethodField()

    class Meta:
        model = LineBacklog
        fields = [
            'id', 'plan_date', 'process', 'process_code', 'process_name',
            'product', 'product_code', 'product_name', 'is_final_product', 'is_line_final_product',
            'line', 'line_code', 'line_name',
            'demand_qty_plan', 'order_qty', 'firm_order_qty', 'forecast_order_qty',
            'plan_qty', 'actual_qty', 'stock_qty', 'planned_stock_qty',
            'adjust_qty', 'scrap_qty', 'actual_shipment_qty',
            'sequence_no', 'plan_id',
            'source_line', 'source_routing_step', 'updated_at',
            'computed_time_min', 'work_minutes', 'step_no', 'cycle_time_min', 'routing_product_id',
        ]
        read_only_fields = ['id', 'updated_at']

    def get_computed_time_min(self, obj):
        return getattr(obj, 'computed_time_min', None)

    def get_step_no(self, obj):
        return getattr(obj, 'step_no', None)

    def get_cycle_time_min(self, obj):
        return getattr(obj, 'cycle_time_min', None)

    def get_routing_product_id(self, obj):
        return getattr(obj, 'routing_product_id', None)

    def get_work_minutes(self, obj):
        return getattr(obj, 'work_minutes', None)


class LinePlanSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    process_code = serializers.CharField(source='process.process_code', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    is_final_product = serializers.BooleanField(source='product.is_final_product', read_only=True)
    is_line_final_product = serializers.BooleanField(source='product.is_line_final_product', read_only=True)

    class Meta:
        model = LinePlan
        fields = [
            'id', 'plan_date', 'process', 'process_code', 'process_name',
            'product', 'product_code', 'product_name', 'is_final_product', 'is_line_final_product',
            'line', 'line_code', 'line_name',
            'plan_qty', 'sequence_no', 'plan_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LineGanttPlanSerializer(serializers.ModelSerializer):
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = LineGanttPlan
        fields = [
            'plan_id',
            'line',
            'line_code',
            'line_name',
            'product',
            'product_code',
            'product_name',
            'plan_date',
            'plan_qty',
            'sequence_no',
            'start_datetime',
            'end_datetime',
            'processes_plan',
        ]


class StockAllocationSerializer(serializers.ModelSerializer):
    """在庫引当シリアライザー"""
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    scrap_qty = serializers.SerializerMethodField()
    available_qty_net = serializers.SerializerMethodField()
    available_qty = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        read_only=True,
        source='available_qty'
    )

    class Meta:
        model = StockAllocation
        fields = [
            'id', 'product', 'product_code', 'product_name', 'location',
            'current_stock', 'reserved_qty', 'scrap_qty', 'available_qty', 'available_qty_net', 'min_stock_qty',
            'is_bottleneck', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'scrap_qty', 'available_qty', 'available_qty_net', 'created_at', 'updated_at']

    def get_scrap_qty(self, obj):
        agg = ProcessRealtimeRecord.objects.filter(
            record_type='SCRAP',
            product_id=obj.product_id,
        ).aggregate(total=Coalesce(Sum('qty'), Decimal('0')))
        return agg['total'] or Decimal('0')

    def get_available_qty_net(self, obj):
        scrap = self.get_scrap_qty(obj)
        return obj.current_stock - obj.reserved_qty - scrap


class ProcessActualSerializer(serializers.ModelSerializer):
    """工程実績シリアライザー"""
    process_code = serializers.CharField(source='process.process_code', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)

    class Meta:
        model = ProcessActual
        fields = [
            'id', 'production_order', 'routing_step', 'process', 'process_code', 'process_name',
            'line', 'line_code', 'line_name', 'completed_qty', 'actual_duration_min',
            'completed_at', 'operator', 'remark', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductionOrderSerializer(serializers.ModelSerializer):
    """製造指示シリアライザー（詳細）"""
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    routing_code = serializers.CharField(source='routing.routing_code', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    actuals = ProcessActualSerializer(many=True, read_only=True, source='actuals')

    class Meta:
        model = ProductionOrder
        fields = [
            'id', 'order_no', 'product', 'product_code', 'product_name',
            'routing', 'routing_code', 'line', 'line_code', 'line_name',
            'order_qty', 'status', 'status_display',
            'scheduled_start_date', 'scheduled_end_date',
            'actual_start_date', 'actual_end_date',
            'priority', 'allocation', 'remark', 'actuals',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductionOrderListSerializer(serializers.ModelSerializer):
    """製造指示シリアライザー（一覧用・軽量版）"""
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ProductionOrder
        fields = [
            'id', 'order_no', 'product', 'product_code', 'product_name',
            'line', 'line_code', 'line_name', 'order_qty', 'status', 'status_display',
            'scheduled_start_date', 'scheduled_end_date', 'priority',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
