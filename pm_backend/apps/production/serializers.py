from decimal import Decimal
import math

from django.db.models import Sum
from django.db.models.functions import Coalesce
from rest_framework import serializers

from .models import LineDemand
from .models_line_backlog import LineBacklog
from .models_line_plan import LinePlan
from .models_line_gantt_plan import LineGanttPlan
from .models_line_daily_schedule_setting import LineDailyScheduleSetting
from .models_line_default_schedule_setting import LineDefaultScheduleSetting
from .models_plan_change_log import ProductionPlanChangeLog
from .models_plan_lock_setting import ProductionPlanLockSetting
from .models_schedule_config import ScheduleConfig
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
    total_lt_days = serializers.SerializerMethodField()
    self_lt_days = serializers.SerializerMethodField()

    class Meta:
        model = LineBacklog
        fields = [
            'id', 'plan_date', 'process', 'process_code', 'process_name',
            'product', 'product_code', 'product_name', 'is_final_product', 'is_line_final_product',
            'line', 'line_code', 'line_name',
            'demand_qty_plan', 'order_qty', 'firm_order_qty', 'forecast_order_qty',
            'plan_qty', 'actual_qty', 'stock_qty', 'planned_stock_qty', 'progress_qty',
            'planned_progress_qty',
            'adjust_qty', 'scrap_qty', 'actual_shipment_qty',
            'sequence_no', 'plan_id',
            'source_line', 'source_routing_step', 'updated_at',
            'computed_time_min', 'work_minutes', 'step_no', 'cycle_time_min', 'routing_product_id',
            'total_lt_days', 'self_lt_days',
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

    def _build_lt_cache(self):
        if hasattr(self, '_lt_cache'):
            return
        self._lt_cache = {'step_lookup': {}, 'lt_by_step': {}}

        items = []
        if isinstance(self.instance, (list, tuple)):
            items = [obj for obj in self.instance if obj is not None]
        elif self.instance is not None:
            items = [self.instance]

        product_ids = {it.product_id for it in items if getattr(it, 'product_id', None)}
        if not product_ids:
            return

        from masters.models import RoutingStep

        step_qs = RoutingStep.objects.filter(output_product_id__in=product_ids).select_related('line')
        routing_ids = set(step_qs.values_list('routing_id', flat=True))
        if not routing_ids:
            return

        steps = list(RoutingStep.objects.filter(
            routing_id__in=routing_ids
        ).select_related('line', 'output_product'))

        minutes_per_day = 480

        def resolve_lead_time_days(step):
            if step.lead_time_days and step.lead_time_days > 0:
                return step.lead_time_days
            if step.line and step.line.lead_time_days:
                return max(step.line.lead_time_days, 0)
            return 0

        def calc_shift_days(prev_minutes, add_minutes):
            prev_days = math.ceil(prev_minutes / minutes_per_day) if prev_minutes > 0 else 0
            total_minutes = prev_minutes + add_minutes
            total_days = math.ceil(total_minutes / minutes_per_day) if total_minutes > 0 else 0
            return total_days - prev_days, total_minutes

        def path_key(path):
            try:
                return tuple(int(p) for p in str(path).split('.'))
            except Exception:
                return (str(path),)

        lt_by_step = {}
        for routing_id in routing_ids:
            routing_steps = [s for s in steps if s.routing_id == routing_id]
            if not routing_steps:
                continue
            step_map = {
                s.hierarchy_path: s
                for s in routing_steps
                if s.hierarchy_path and s.hierarchy_path != 'final'
            }
            children_map = {}
            for path in step_map.keys():
                parent_path = path.rsplit('.', 1)[0] if '.' in path else None
                children_map.setdefault(parent_path, []).append(path)

            final_step = next((s for s in routing_steps if s.hierarchy_path == 'final'), None)
            base_days = 0
            base_minutes = 0
            if final_step:
                lead_days = resolve_lead_time_days(final_step) if final_step.time_unit == 'DAY' else 0
                step_minutes = final_step.duration_min or 0 if final_step.time_unit == 'MINUTE' else 0
                minute_shift, base_minutes = calc_shift_days(0, step_minutes)
                base_days = lead_days + minute_shift
                lt_by_step[final_step.id] = {
                    'total': base_days,
                    'self': base_days,
                }

            def compute(path, parent_days, parent_minutes):
                step = step_map.get(path)
                if not step:
                    return
                lead_days = resolve_lead_time_days(step) if step.time_unit == 'DAY' else 0
                step_minutes = step.duration_min or 0 if step.time_unit == 'MINUTE' else 0
                minute_shift, total_minutes = calc_shift_days(parent_minutes, step_minutes)
                self_days = lead_days + minute_shift
                total_days = parent_days + self_days
                lt_by_step[step.id] = {
                    'total': total_days,
                    'self': self_days,
                }
                for child_path in sorted(children_map.get(path, []), key=path_key):
                    compute(child_path, total_days, total_minutes)

            for root_path in sorted(children_map.get(None, []), key=path_key):
                compute(root_path, base_days, base_minutes)

        step_lookup = {}
        for step in steps:
            key = (step.output_product_id, step.line_id, step.process_id)
            if key not in step_lookup:
                step_lookup[key] = step.id
            if step.output_product_id not in step_lookup:
                step_lookup[step.output_product_id] = step.id

        self._lt_cache = {'step_lookup': step_lookup, 'lt_by_step': lt_by_step}

    def _get_lt_for_obj(self, obj):
        self._build_lt_cache()
        cache = getattr(self, '_lt_cache', None) or {}
        step_lookup = cache.get('step_lookup', {})
        lt_by_step = cache.get('lt_by_step', {})
        step_id = step_lookup.get((obj.product_id, obj.line_id, obj.process_id))
        if not step_id:
            step_id = step_lookup.get(obj.product_id)
        if not step_id:
            return {'total': None, 'self': None}
        return lt_by_step.get(step_id, {'total': None, 'self': None})

    def get_total_lt_days(self, obj):
        return self._get_lt_for_obj(obj).get('total')

    def get_self_lt_days(self, obj):
        return self._get_lt_for_obj(obj).get('self')


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


class ProductionPlanChangeLogSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    process_code = serializers.CharField(source='process.process_code', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    changed_by_username = serializers.CharField(source='changed_by.username', read_only=True)

    class Meta:
        model = ProductionPlanChangeLog
        fields = [
            'id', 'changed_at', 'plan_date',
            'product', 'product_code', 'product_name',
            'process', 'process_code', 'process_name',
            'line', 'line_code', 'line_name',
            'sequence_no', 'plan_id',
            'before_qty', 'after_qty',
            'reason',
            'changed_by', 'changed_by_username',
        ]
        read_only_fields = fields


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


class LineDailyScheduleSettingSerializer(serializers.ModelSerializer):
    """ライン別日次スケジュール設定のシリアライザー"""
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)

    class Meta:
        model = LineDailyScheduleSetting
        fields = [
            'id', 'line', 'line_code', 'line_name', 'plan_date',
            'final_process_start_time', 'adjust_to_break_end',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LineDefaultScheduleSettingSerializer(serializers.ModelSerializer):
    """ライン別デフォルトスケジュール設定のシリアライザー"""
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)

    class Meta:
        model = LineDefaultScheduleSetting
        fields = [
            'id', 'line', 'line_code', 'line_name',
            'final_process_start_time', 'adjust_to_break_end',
            'created_at', 'updated_at', 'updated_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'updated_by']


class ProductionPlanLockSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionPlanLockSetting
        fields = ['id', 'lock_days', 'updated_at', 'updated_by']
        read_only_fields = ['id', 'updated_at', 'updated_by']


class ScheduleConfigSerializer(serializers.ModelSerializer):
    task_name_display = serializers.CharField(
        source='get_task_name_display', read_only=True
    )
    last_run_status_display = serializers.SerializerMethodField()
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    notify_user_names = serializers.SerializerMethodField()
    notify_user_codes = serializers.SerializerMethodField()

    class Meta:
        model = ScheduleConfig
        fields = [
            'id', 'task_name', 'task_name_display', 'line', 'line_code', 'line_name',
            'is_enabled',
            'scheduled_hour', 'scheduled_minute',
            'scheduled_dom',
            'include_next_month', 'include_second_month', 'include_third_month',
            'notify_users', 'notify_user_names', 'notify_user_codes',
            'last_run_at', 'last_run_status', 'last_run_status_display',
            'last_run_message', 'last_run_duration_seconds',
            'updated_at', 'updated_by',
        ]
        read_only_fields = [
            'id', 'last_run_at', 'last_run_status',
            'last_run_message', 'last_run_duration_seconds',
            'updated_at', 'updated_by',
        ]
        extra_kwargs = {
            'notify_user_codes': {'required': False},
            'notify_users': {'required': False},
        }

    def get_last_run_status_display(self, obj):
        mapping = {'SUCCESS': '成功', 'FAILED': '失敗', 'RUNNING': '実行中'}
        return mapping.get(obj.last_run_status, '')

    def get_notify_user_names(self, obj):
        if not obj.pk:
            return []
        names = []
        for user in obj.notify_users.all():
            full_name = user.get_full_name() or ''
            if full_name.strip():
                names.append(full_name)
            elif user.username:
                names.append(user.username)
            elif user.email:
                names.append(user.email)
        return names

    def get_notify_user_codes(self, obj):
        if not obj.pk:
            return []
        codes = []
        for user in obj.notify_users.select_related('profile'):
            code = getattr(getattr(user, 'profile', None), 'employee_code', None)
            if code:
                codes.append(code)
            elif user.username:
                codes.append(user.username)
            elif user.email:
                codes.append(user.email)
        return codes
