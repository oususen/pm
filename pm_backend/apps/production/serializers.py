from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import F, Sum
from django.db.models.functions import Coalesce
from rest_framework import serializers
from masters.models import RoutingStep
from masters.services.routing_service import build_effective_routing_q

from .models import LineDemand
from .models_line_backlog import LineBacklog
from .models_line_plan import LinePlan
from .models_line_gantt_plan import LineGanttPlan
from .models_line_daily_schedule_setting import LineDailyScheduleSetting
from .models_line_default_schedule_setting import LineDefaultScheduleSetting
from .models_auto_plan_aggregate_setting import AutoPlanAggregateSetting
from .models_line_backlog_adjustment import LineBacklogAdjustment
from .models_plan_change_log import ProductionPlanChangeLog
from .models_plan_lock_setting import ProductionPlanLockSetting
from .models_record_inquiry_setting import ProductionRecordInquirySetting
from .models_schedule_config import ScheduleConfig, ScheduleRunLog
from .models_purchase_actual_reconcile import (
    PurchaseActualReconcileReport,
    PurchaseActualReconcileReportDetail,
)
from .models_production_actual_reconcile import (
    ProductionActualReconcileReport,
    ProductionActualReconcileReportDetail,
)
from .models_laser_pattern import LaserPattern, LaserPatternComponent, LaserPatternFinishedProduct
from .models_laser_actual import LaserActual, LaserActualDetail
from .models_laser_kadojiseki import LaserShiftRecord
from .models_process_realtime import ProcessRealtimeRecord
from .models_production import ProcessActual, ProductionOrder, StockAllocation
from .inventory.lead_time_utils import resolve_lead_days_for_step


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
    step_no = serializers.SerializerMethodField()

    class Meta:
        model = LineDemand
        fields = [
            'id', 'line', 'line_code', 'line_name', 'routing_step', 'process', 'process_code', 'process_name',
            'product', 'product_code', 'product_name', 'is_final_product',
            'plan_date', 'lead_time_days', 'is_shifted',
            'forecast_qty', 'firm_qty', 'plan_qty', 'actual_qty',
            'plan_progress', 'actual_progress', 'required_qty',
            'order_numbers', 'step_no', 'created_at', 'updated_at',
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

    def get_step_no(self, obj):
        if obj.routing_step_id and obj.routing_step:
            return obj.routing_step.step_no
        return None


class LineBacklogSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    is_virtual_set = serializers.BooleanField(source='product.is_virtual_set', read_only=True)
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
            'product', 'product_code', 'product_name', 'is_virtual_set', 'is_final_product', 'is_line_final_product',
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
        val = getattr(obj, 'step_no', None)
        if val is not None:
            return val
        src = getattr(obj, 'source_routing_step', None)
        if src:
            return src.step_no
        return None

    def get_cycle_time_min(self, obj):
        return getattr(obj, 'cycle_time_min', None)

    def get_routing_product_id(self, obj):
        return getattr(obj, 'routing_product_id', None)

    def get_work_minutes(self, obj):
        return getattr(obj, 'work_minutes', None)

    def _build_lt_cache(self):
        # 既知の制限: ルーティング有効判定を「現在時刻」基準で一括計算している。
        # 日付レンジをまたぐ応答では、ルーティング切替日前後の行に対し
        # 誤ったルーティングでLT/工程情報を返す余地がある。
        # 行ごとにplan_dateベースで解決するには構造変更が必要なため据え置き。
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

        step_qs = RoutingStep.objects.filter(
            output_product_id__in=product_ids
        ).filter(
            build_effective_routing_q(prefix='routing__')
        ).select_related('line')
        routing_ids = set(step_qs.values_list('routing_id', flat=True))
        if not routing_ids:
            return

        steps = list(RoutingStep.objects.filter(
            routing_id__in=routing_ids
        ).filter(
            build_effective_routing_q(prefix='routing__')
        ).select_related('line', 'output_product'))

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
            if final_step:
                base_days = resolve_lead_days_for_step(final_step)
                lt_by_step[final_step.id] = {
                    'total': base_days,
                    'self': base_days,
                }

            def compute(path, parent_days):
                step = step_map.get(path)
                if not step:
                    return
                self_days = resolve_lead_days_for_step(step)
                total_days = parent_days + self_days
                lt_by_step[step.id] = {
                    'total': total_days,
                    'self': self_days,
                }
                for child_path in sorted(children_map.get(path, []), key=path_key):
                    compute(child_path, total_days)

            for root_path in sorted(children_map.get(None, []), key=path_key):
                compute(root_path, base_days)

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


class LaserPatternComponentSerializer(serializers.ModelSerializer):
    component_product_code = serializers.CharField(source='component_product.product_code', read_only=True)
    component_product_name = serializers.CharField(source='component_product.product_name', read_only=True)

    class Meta:
        model = LaserPatternComponent
        fields = [
            'id',
            'component_product',
            'component_product_code',
            'component_product_name',
            'take_qty',
        ]


class LaserPatternFinishedProductSerializer(serializers.ModelSerializer):
    finished_product_code = serializers.CharField(source='finished_product.product_code', read_only=True)
    finished_product_name = serializers.CharField(source='finished_product.product_name', read_only=True)

    class Meta:
        model = LaserPatternFinishedProduct
        fields = [
            'id',
            'finished_product',
            'finished_product_code',
            'finished_product_name',
            'units_per_shot',
        ]


class LaserPatternSerializer(serializers.ModelSerializer):
    material_code = serializers.CharField(source='material.product_code', read_only=True)
    material_name = serializers.CharField(source='material.product_name', read_only=True)
    equipment_code = serializers.CharField(source='equipment.equipment_code', read_only=True)
    equipment_name = serializers.CharField(source='equipment.equipment_name', read_only=True)
    component_items = LaserPatternComponentSerializer(many=True)
    finished_items = LaserPatternFinishedProductSerializer(many=True)

    class Meta:
        model = LaserPattern
        fields = [
            'id',
            'pattern_no',
            'material',
            'material_code',
            'material_name',
            'equipment',
            'equipment_code',
            'equipment_name',
            'process_time_min',
            'is_budget_target',
            'is_active',
            'component_items',
            'finished_items',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_component_items(self, value):
        if not value:
            raise serializers.ValidationError('構成部品を1件以上入力してください。')
        seen = set()
        for item in value:
            pid = item.get('component_product')
            pid_key = pid.pk if hasattr(pid, 'pk') else pid
            if pid_key in seen:
                raise serializers.ValidationError('同じ構成部品が重複しています。')
            seen.add(pid_key)
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)

        # 新規/更新共通で、材料予算用フラグと完成品情報の整合性を強制する
        if 'is_budget_target' in attrs:
            is_budget_target = bool(attrs.get('is_budget_target'))
        else:
            is_budget_target = bool(getattr(self.instance, 'is_budget_target', False))

        if 'finished_items' in attrs:
            finished_items = attrs.get('finished_items') or []
        else:
            finished_items = []
            if self.instance is not None:
                finished_items = list(self.instance.finished_items.all())

        if is_budget_target and not finished_items:
            raise serializers.ValidationError({
                'finished_items': '材料予算用パターンは完成品情報を1件以上入力してください。'
            })
        if not is_budget_target and finished_items:
            raise serializers.ValidationError({
                'finished_items': '材料予算用にしないパターンは完成品情報を入力できません。'
            })

        return attrs

    def create(self, validated_data):
        component_items = validated_data.pop('component_items', [])
        finished_items = validated_data.pop('finished_items', [])
        pattern = LaserPattern.objects.create(**validated_data)
        self._replace_children(pattern, component_items, finished_items)
        return pattern

    def update(self, instance, validated_data):
        component_items = validated_data.pop('component_items', None)
        finished_items = validated_data.pop('finished_items', None)

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if component_items is not None and finished_items is not None:
            self._replace_children(instance, component_items, finished_items)
        return instance

    def _replace_children(self, pattern, component_items, finished_items):
        LaserPatternComponent.objects.filter(pattern=pattern).delete()
        LaserPatternFinishedProduct.objects.filter(pattern=pattern).delete()
        LaserPatternComponent.objects.bulk_create([
            LaserPatternComponent(
                pattern=pattern,
                component_product=item['component_product'],
                take_qty=item['take_qty'],
            )
            for item in component_items
        ])
        LaserPatternFinishedProduct.objects.bulk_create([
            LaserPatternFinishedProduct(
                pattern=pattern,
                finished_product=item['finished_product'],
                units_per_shot=item['units_per_shot'],
            )
            for item in finished_items
        ])


class LaserActualDetailSerializer(serializers.ModelSerializer):
    detail_type_display = serializers.CharField(source='get_detail_type_display', read_only=True)
    resolved_process_id = serializers.SerializerMethodField()
    resolved_process_code = serializers.SerializerMethodField()
    resolved_process_name = serializers.SerializerMethodField()
    resolved_line_id = serializers.SerializerMethodField()

    class Meta:
        model = LaserActualDetail
        fields = [
            'id',
            'detail_type',
            'detail_type_display',
            'product',
            'product_code',
            'product_name',
            'units_per_shot',
            'total_qty',
            'scrap_qty',
            'scrap_reason',
            'display_order',
            'resolved_process_id',
            'resolved_process_code',
            'resolved_process_name',
            'resolved_line_id',
        ]
        read_only_fields = fields

    def _resolve_process_line(self, obj):
        actual = getattr(obj, 'actual', None)
        equipment = getattr(actual, 'equipment', None)
        product = getattr(obj, 'product', None)
        cache_key = (
            getattr(equipment, 'id', None),
            getattr(product, 'id', None),
        )
        cache = self.context.setdefault('laser_detail_process_cache', {})
        if cache_key not in cache:
            cache[cache_key] = LaserActualSerializer._resolve_component_process_line(
                equipment,
                product,
            )
        return cache[cache_key]

    def get_resolved_process_id(self, obj):
        process, _line = self._resolve_process_line(obj)
        return getattr(process, 'id', None)

    def get_resolved_process_code(self, obj):
        process, _line = self._resolve_process_line(obj)
        return getattr(process, 'process_code', '')

    def get_resolved_process_name(self, obj):
        process, _line = self._resolve_process_line(obj)
        return getattr(process, 'process_name', '')

    def get_resolved_line_id(self, obj):
        _process, line = self._resolve_process_line(obj)
        return getattr(line, 'id', None)


class LaserActualSerializer(serializers.ModelSerializer):
    BACKLOG_COUNTABLE_ACTIONS = {
        LaserActual.OPERATOR_ACTION_END,
        LaserActual.OPERATOR_ACTION_PAUSE,
    }

    equipment_code = serializers.CharField(read_only=True)
    equipment_name = serializers.CharField(read_only=True)
    equipment_process_code = serializers.CharField(source='equipment.process.process_code', read_only=True, default='')
    equipment_process_id   = serializers.IntegerField(source='equipment.process.id', read_only=True, default=None)
    material_code = serializers.CharField(read_only=True)
    material_name = serializers.CharField(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    details = LaserActualDetailSerializer(many=True, read_only=True)
    component_scraps = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)

    class Meta:
        model = LaserActual
        fields = [
            'id',
            'work_date',
            'equipment',
            'equipment_code',
            'equipment_name',
            'equipment_process_code',
            'equipment_process_id',
            'pattern',
            'pattern_no',
            'material',
            'material_code',
            'material_name',
            'shot_count',
            'process_time_per_shot',
            'total_process_time',
            'operator_action',
            'operator_action_reason',
            'remarks',
            'component_scraps',
            'created_by',
            'created_by_name',
            'updated_by',
            'updated_by_name',
            'created_at',
            'updated_at',
            'details',
        ]
        read_only_fields = [
            'id',
            'pattern_no',
            'equipment_code',
            'equipment_name',
            'material',
            'material_code',
            'material_name',
            'process_time_per_shot',
            'total_process_time',
            'created_by',
            'created_by_name',
            'updated_by',
            'updated_by_name',
            'created_at',
            'updated_at',
            'details',
        ]

    @staticmethod
    def _q1(value):
        if not isinstance(value, Decimal):
            value = Decimal(str(value if value is not None else 0))
        return value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)

    @staticmethod
    def _q3(value):
        if not isinstance(value, Decimal):
            value = Decimal(str(value if value is not None else 0))
        return value.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)

    @staticmethod
    def _display_user_name(user):
        if not user:
            return ''
        full_name = (getattr(user, 'get_full_name', lambda: '')() or '').strip()
        if full_name:
            return full_name
        return getattr(user, 'username', '') or ''

    def get_created_by_name(self, obj):
        return self._display_user_name(getattr(obj, 'created_by', None))

    def get_updated_by_name(self, obj):
        return self._display_user_name(getattr(obj, 'updated_by', None))

    def validate_shot_count(self, value):
        if value is None or int(value) < 0:
            raise serializers.ValidationError('回数は0以上の整数で入力してください。')
        return int(value)

    def validate(self, attrs):
        pattern = attrs.get('pattern') or getattr(self.instance, 'pattern', None)
        if not pattern:
            raise serializers.ValidationError({'pattern': 'パターン番号を選択してください。'})
        if not pattern.component_items.exists():
            raise serializers.ValidationError({'pattern': '選択パターンに構成部品が登録されていません。'})
        if bool(getattr(pattern, 'is_budget_target', False)) and not pattern.finished_items.exists():
            raise serializers.ValidationError({'pattern': '材料予算用パターンには完成品情報が必要です。'})

        action = str(
            attrs.get('operator_action')
            or getattr(self.instance, 'operator_action', LaserActual.OPERATOR_ACTION_END)
            or LaserActual.OPERATOR_ACTION_END
        ).upper()
        allowed_actions = {
            LaserActual.OPERATOR_ACTION_START,
            LaserActual.OPERATOR_ACTION_END,
            LaserActual.OPERATOR_ACTION_PAUSE,
            LaserActual.OPERATOR_ACTION_TEMP_END,
            LaserActual.OPERATOR_ACTION_RESUME,
        }
        if action not in allowed_actions:
            raise serializers.ValidationError({'operator_action': '作業時刻が不正です。'})

        shot_count = attrs.get('shot_count')
        if shot_count is None:
            shot_count = getattr(self.instance, 'shot_count', 0)
        shot_count = int(shot_count or 0)
        if action == LaserActual.OPERATOR_ACTION_END and shot_count < 1:
            raise serializers.ValidationError({'shot_count': '終了時の回数は1以上で入力してください。'})
        if action == LaserActual.OPERATOR_ACTION_PAUSE and shot_count < 0:
            raise serializers.ValidationError({'shot_count': '中断時の回数は0以上で入力してください。'})

        reason_required_actions = {
            LaserActual.OPERATOR_ACTION_PAUSE,
            LaserActual.OPERATOR_ACTION_TEMP_END,
        }
        reason_text = str(
            attrs.get('operator_action_reason')
            if 'operator_action_reason' in attrs
            else getattr(self.instance, 'operator_action_reason', '')
        ).strip()
        if action in reason_required_actions and not reason_text:
            raise serializers.ValidationError({'operator_action_reason': '中断/一時終了時は理由を入力してください。'})
        if action not in reason_required_actions:
            attrs['operator_action_reason'] = ''

        component_scrap_map = self._normalize_component_scrap_map(
            pattern=pattern,
            shot_count=shot_count,
            component_scraps=attrs.get('component_scraps'),
        )
        attrs['_component_scrap_map'] = component_scrap_map
        return attrs

    def _normalize_component_scrap_map(self, pattern, shot_count, component_scraps):
        pattern_components = list(
            pattern.component_items.select_related('component_product').all()
        ) if pattern else []
        if not pattern_components:
            return {}

        gross_qty_by_product = {}
        shot_decimal = Decimal(str(int(shot_count or 0)))
        for item in pattern_components:
            if not item.component_product_id:
                continue
            units = self._q3(item.take_qty or Decimal('0'))
            gross_qty_by_product[item.component_product_id] = self._q3(units * shot_decimal)

        rows = component_scraps if isinstance(component_scraps, list) else []
        normalized = {}
        for row in rows:
            product_id_raw = (row or {}).get('product') or (row or {}).get('product_id')
            if product_id_raw in (None, ''):
                continue
            try:
                product_id = int(product_id_raw)
            except (TypeError, ValueError):
                raise serializers.ValidationError({'component_scraps': '仕損対象の品目が不正です。'})
            if product_id not in gross_qty_by_product:
                raise serializers.ValidationError({'component_scraps': '仕損対象にパターン外の品目が含まれています。'})

            try:
                scrap_qty = self._q3((row or {}).get('scrap_qty') or Decimal('0'))
            except Exception:
                raise serializers.ValidationError({'component_scraps': '仕損数量は数値で入力してください。'})
            if scrap_qty < 0:
                raise serializers.ValidationError({'component_scraps': '仕損数量は0以上で入力してください。'})

            gross_qty = gross_qty_by_product[product_id]
            if scrap_qty > gross_qty:
                raise serializers.ValidationError({'component_scraps': '仕損数量は実績数を超えられません。'})

            scrap_reason = str((row or {}).get('scrap_reason') or '').strip()
            if scrap_qty > 0 and not scrap_reason:
                raise serializers.ValidationError({'component_scraps': '仕損理由を入力してください。'})

            normalized[product_id] = {
                'scrap_qty': scrap_qty,
                'scrap_reason': scrap_reason,
            }
        return normalized

    def _apply_pattern_snapshot(self, instance, component_scrap_map=None):
        pattern = instance.pattern
        shot_count = int(instance.shot_count or 0)
        component_scrap_map = component_scrap_map or {}
        process_time_per_shot = self._q1(pattern.process_time_min or Decimal('0'))
        total_process_time = self._q1(process_time_per_shot * Decimal(shot_count))
        material = pattern.material
        equipment = instance.equipment

        instance.pattern_no = pattern.pattern_no
        instance.material = material
        instance.material_code = material.product_code if material else ''
        instance.material_name = material.product_name if material else ''
        instance.equipment_code = equipment.equipment_code if equipment else ''
        instance.equipment_name = equipment.equipment_name if equipment else ''
        instance.process_time_per_shot = process_time_per_shot
        instance.total_process_time = total_process_time
        instance.save(
            update_fields=[
                'pattern_no',
                'material',
                'material_code',
                'material_name',
                'equipment_code',
                'equipment_name',
                'process_time_per_shot',
                'total_process_time',
                'updated_at',
            ]
        )

        component_rows = []
        for index, item in enumerate(pattern.component_items.select_related('component_product').all(), start=1):
            units = self._q3(item.take_qty or Decimal('0'))
            product = item.component_product
            gross_qty = self._q3(units * Decimal(shot_count))
            scrap_entry = component_scrap_map.get(getattr(product, 'id', None), {})
            scrap_qty = self._q3(scrap_entry.get('scrap_qty') or Decimal('0'))
            if scrap_qty > gross_qty:
                scrap_qty = gross_qty
            total_qty = self._q3(gross_qty - scrap_qty)
            component_rows.append(
                LaserActualDetail(
                    actual=instance,
                    detail_type=LaserActualDetail.DETAIL_TYPE_COMPONENT,
                    product=product,
                    product_code=product.product_code if product else '',
                    product_name=product.product_name if product else '',
                    units_per_shot=units,
                    total_qty=total_qty,
                    scrap_qty=scrap_qty,
                    scrap_reason=str(scrap_entry.get('scrap_reason') or '').strip(),
                    display_order=index,
                )
            )

        finished_rows = []
        for index, item in enumerate(pattern.finished_items.select_related('finished_product').all(), start=1):
            units = self._q3(item.units_per_shot or Decimal('0'))
            total_qty = self._q3(units * Decimal(shot_count))
            product = item.finished_product
            finished_rows.append(
                LaserActualDetail(
                    actual=instance,
                    detail_type=LaserActualDetail.DETAIL_TYPE_FINISHED,
                    product=product,
                    product_code=product.product_code if product else '',
                    product_name=product.product_name if product else '',
                    units_per_shot=units,
                    total_qty=total_qty,
                    scrap_qty=Decimal('0'),
                    scrap_reason='',
                    display_order=index,
                )
            )

        LaserActualDetail.objects.filter(actual=instance).delete()
        LaserActualDetail.objects.bulk_create(component_rows + finished_rows)

    @classmethod
    def _is_countable_action(cls, action):
        return str(action or '').upper() in cls.BACKLOG_COUNTABLE_ACTIONS

    @staticmethod
    def _empty_backlog_defaults():
        return {
            'demand_qty_plan': 0,
            'order_qty': 0,
            'plan_qty': 0,
            'actual_qty': 0,
            'stock_qty': 0,
            'planned_stock_qty': 0,
            'adjust_qty': 0,
            'scrap_adjust_qty': 0,
            'scrap_qty': 0,
            'actual_shipment_qty': 0,
            'progress_qty': 0,
            'planned_progress_qty': 0,
        }

    @staticmethod
    def _to_backlog_qty(value):
        try:
            num = Decimal(str(value or 0))
        except Exception:
            return 0
        return int(num.quantize(Decimal('1'), rounding=ROUND_HALF_UP))

    @staticmethod
    def _resolve_component_process_line(equipment, product):
        preferred_process = getattr(equipment, 'process', None) if equipment else None
        preferred_line = getattr(equipment, 'line', None) if equipment else None
        if not preferred_line and preferred_process:
            preferred_line = getattr(preferred_process, 'line', None)

        step = None
        if product:
            base_qs = RoutingStep.objects.filter(
                output_product=product,
            ).filter(
                build_effective_routing_q(prefix='routing__')
            ).select_related('process', 'process__line', 'line').order_by(
                '-routing__is_default',
                '-routing__valid_from_datetime',
                'step_no',
                'id',
            )
            if preferred_line:
                step = base_qs.filter(line=preferred_line).first()
            if not step and preferred_process:
                step = base_qs.filter(process=preferred_process).first()
            if not step:
                step = base_qs.first()

        if step:
            process = step.process
            line = step.line or getattr(step.process, 'line', None)
            if process and line:
                return process, line

        process = preferred_process
        line = preferred_line
        if process and not line:
            line = getattr(process, 'line', None)
        return process, line

    @classmethod
    def build_backlog_delta_map(cls, instance):
        if not instance or not instance.work_date:
            return {}
        if not cls._is_countable_action(instance.operator_action):
            return {}

        details = list(
            instance.details.filter(
                detail_type=LaserActualDetail.DETAIL_TYPE_COMPONENT,
            ).select_related('product')
        )
        if not details:
            return {}

        delta_map = {}
        for detail in details:
            if not detail.product_id:
                continue
            qty = cls._to_backlog_qty(detail.total_qty)
            if qty == 0:
                continue
            process, line = cls._resolve_component_process_line(instance.equipment, detail.product)
            if not process or not line:
                continue
            key = (instance.work_date, line.id, process.id, detail.product_id)
            delta_map[key] = int(delta_map.get(key, 0)) + qty
        return delta_map

    @classmethod
    def apply_backlog_delta_map(cls, delta_map):
        if not delta_map:
            return

        for key, delta_qty in delta_map.items():
            qty = int(delta_qty or 0)
            if qty == 0:
                continue
            plan_date, line_id, process_id, product_id = key
            backlog, _created = LineBacklog.objects.get_or_create(
                plan_date=plan_date,
                line_id=line_id,
                process_id=process_id,
                product_id=product_id,
                sequence_no=0,
                defaults=cls._empty_backlog_defaults(),
            )
            LineBacklog.objects.filter(id=backlog.id).update(actual_qty=F('actual_qty') + qty)

    @classmethod
    def revert_backlog_for_instance(cls, instance):
        original_map = cls.build_backlog_delta_map(instance)
        if not original_map:
            return
        rollback_map = {key: -int(value or 0) for key, value in original_map.items()}
        cls.apply_backlog_delta_map(rollback_map)

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        component_scrap_map = validated_data.pop('_component_scrap_map', {})
        validated_data.pop('component_scraps', None)
        with transaction.atomic():
            instance = LaserActual.objects.create(
                created_by=user,
                updated_by=user,
                **validated_data,
            )
            self._apply_pattern_snapshot(instance, component_scrap_map)
            delta_map = self.build_backlog_delta_map(instance)
            self.apply_backlog_delta_map(delta_map)
        return instance

    def update(self, instance, validated_data):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        component_scrap_map = validated_data.pop('_component_scrap_map', {})
        validated_data.pop('component_scraps', None)
        before_map = self.build_backlog_delta_map(instance)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if user:
            instance.updated_by = user
        with transaction.atomic():
            instance.save()
            self._apply_pattern_snapshot(instance, component_scrap_map)
            after_map = self.build_backlog_delta_map(instance)

            delta_map = {}
            for key, value in after_map.items():
                delta_map[key] = int(delta_map.get(key, 0)) + int(value or 0)
            for key, value in before_map.items():
                delta_map[key] = int(delta_map.get(key, 0)) - int(value or 0)
            self.apply_backlog_delta_map(delta_map)
        return instance


class StockAllocationSerializer(serializers.ModelSerializer):
    """在庫引当シリアライザー"""
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    product_line_name = serializers.SerializerMethodField()
    product_supplier_name = serializers.SerializerMethodField()
    scrap_qty = serializers.SerializerMethodField()
    available_qty_net = serializers.SerializerMethodField()
    available_qty = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        read_only=True,
    )

    class Meta:
        model = StockAllocation
        fields = [
            'id', 'product', 'product_code', 'product_name', 'product_line_name', 'product_supplier_name', 'location',
            'current_stock', 'reserved_qty', 'scrap_qty', 'available_qty', 'available_qty_net', 'min_stock_qty',
            'is_bottleneck', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'scrap_qty', 'available_qty', 'available_qty_net', 'created_at', 'updated_at']

    def get_product_line_name(self, obj):
        for item in getattr(obj.product, 'prefetched_bom_items', []):
            if item.line:
                return item.line.line_name
        return ''

    def get_product_supplier_name(self, obj):
        for item in getattr(obj.product, 'prefetched_bom_items', []):
            if item.supplier:
                return item.supplier.supplier_name
        return ''

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
    actuals = ProcessActualSerializer(many=True, read_only=True)

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


class AutoPlanAggregateSettingSerializer(serializers.ModelSerializer):
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = AutoPlanAggregateSetting
        fields = [
            'id', 'line', 'line_code', 'line_name',
            'product', 'product_code', 'product_name',
            'aggregate_weekday', 'aggregate_days', 'is_active',
            'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']


class ProductionPlanLockSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionPlanLockSetting
        fields = ['id', 'lock_days', 'updated_at', 'updated_by']
        read_only_fields = ['id', 'updated_at', 'updated_by']


class ProductionRecordInquirySettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionRecordInquirySetting
        fields = ['id', 'tab_key', 'target_line_codes', 'product_mappings', 'updated_at', 'updated_by']
        read_only_fields = ['id', 'updated_at', 'updated_by']


class ScheduleConfigSerializer(serializers.ModelSerializer):
    task_name_display = serializers.CharField(
        source='get_task_name_display', read_only=True
    )
    last_run_status_display = serializers.SerializerMethodField()
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    line_type = serializers.CharField(source='line.line_type', read_only=True)
    process_code = serializers.CharField(source='process.process_code', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    notify_user_names = serializers.SerializerMethodField()
    notify_user_codes = serializers.SerializerMethodField()

    class Meta:
        model = ScheduleConfig
        fields = [
            'id', 'task_name', 'task_name_display', 'line', 'line_code', 'line_name', 'line_type',
            'process', 'process_code', 'process_name',
            'is_enabled',
            'scheduled_hour', 'scheduled_minute',
            'scheduled_dom',
            'average_days_window', 'safety_days',
            'execution_order',
            'auto_plan_sequence_locked',
            'range_base_day', 'range_days_after',
            'include_current_month', 'include_next_month', 'include_second_month', 'include_third_month',
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


class ScheduleRunLogSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = ScheduleRunLog
        fields = [
            'id', 'task_name', 'started_at', 'finished_at',
            'status', 'status_display', 'message', 'duration_seconds',
        ]

    def get_status_display(self, obj):
        mapping = {'SUCCESS': '成功', 'FAILED': '失敗', 'RUNNING': '実行中'}
        return mapping.get(obj.status, '')

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


class PurchaseActualReconcileReportDetailSerializer(serializers.ModelSerializer):
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    process_code = serializers.CharField(source='process.process_code', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = PurchaseActualReconcileReportDetail
        fields = [
            'id',
            'report',
            'line', 'line_code', 'line_name',
            'process', 'process_code', 'process_name',
            'product', 'product_code', 'product_name',
            'plan_date',
            'expected_qty', 'backlog_qty', 'diff_qty',
            'fixed',
            'created_at',
        ]
        read_only_fields = fields


class PurchaseActualReconcileReportSerializer(serializers.ModelSerializer):
    mode_display = serializers.CharField(source='get_mode_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseActualReconcileReport
        fields = [
            'id',
            'task_config',
            'mode', 'mode_display',
            'status', 'status_display',
            'compared_count',
            'diff_count',
            'fixed_count',
            'message',
            'created_by', 'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj):
        if not obj.created_by_id:
            return ''
        full_name = obj.created_by.get_full_name() or ''
        if full_name.strip():
            return full_name
        return obj.created_by.username or ''


class ProductionActualReconcileReportDetailSerializer(serializers.ModelSerializer):
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    line_name = serializers.CharField(source='line.line_name', read_only=True)
    process_code = serializers.CharField(source='process.process_code', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = ProductionActualReconcileReportDetail
        fields = [
            'id',
            'report',
            'line', 'line_code', 'line_name',
            'process', 'process_code', 'process_name',
            'product', 'product_code', 'product_name',
            'plan_date',
            'expected_qty', 'backlog_qty', 'diff_qty',
            'fixed',
            'created_at',
        ]
        read_only_fields = fields


class ProductionActualReconcileReportSerializer(serializers.ModelSerializer):
    mode_display = serializers.CharField(source='get_mode_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ProductionActualReconcileReport
        fields = [
            'id',
            'task_config',
            'mode', 'mode_display',
            'status', 'status_display',
            'compared_count',
            'diff_count',
            'fixed_count',
            'message',
            'created_by', 'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj):
        if not obj.created_by_id:
            return ''
        full_name = obj.created_by.get_full_name() or ''
        if full_name.strip():
            return full_name
        return obj.created_by.username or ''


class LineBacklogAdjustmentSerializer(serializers.ModelSerializer):
    line_code = serializers.CharField(source='line.line_code', read_only=True)
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    process_code = serializers.CharField(source='process.process_code', read_only=True)
    updated_by_name = serializers.SerializerMethodField()

    def get_updated_by_name(self, obj):
        user = obj.updated_by
        if not user:
            return None
        full_name = (user.get_full_name() or '').strip()
        return full_name if full_name else user.username

    class Meta:
        model = LineBacklogAdjustment
        fields = [
            'id',
            'line',
            'line_code',
            'product',
            'product_code',
            'process',
            'process_code',
            'plan_date',
            'adjust_type',
            'adjust_qty',
            'reason',
            'updated_at',
            'updated_by',
            'updated_by_name',
        ]
        read_only_fields = ['id', 'updated_at', 'updated_by']


class LaserShiftRecordSerializer(serializers.ModelSerializer):
    """レーザーシフト稼働記録シリアライザ（開始・終了2段階入力）"""

    equipment_code = serializers.CharField(source='equipment.equipment_code', read_only=True)
    equipment_name = serializers.CharField(source='equipment.equipment_name', read_only=True)
    shift_no_display = serializers.CharField(source='get_shift_no_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    process_hours = serializers.SerializerMethodField()
    operating_rate = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = LaserShiftRecord
        fields = [
            'id',
            'work_date',
            'equipment',
            'equipment_code',
            'equipment_name',
            'shift_no',
            'shift_no_display',
            'start_totalizer_hour',
            'start_totalizer_min',
            'end_totalizer_hour',
            'end_totalizer_min',
            'work_hours',
            'process_hours',
            'operating_rate',
            'is_completed',
            'created_by',
            'created_by_name',
            'updated_by',
            'updated_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None

    def get_updated_by_name(self, obj):
        if obj.updated_by:
            return obj.updated_by.get_full_name() or obj.updated_by.username
        return None

    def get_is_completed(self, obj):
        """開始・終了両方入力済みかどうか"""
        return (
            obj.end_totalizer_hour is not None
            and obj.end_totalizer_min is not None
            and obj.work_hours is not None
        )

    def get_process_hours(self, obj):
        """加工時間 = (終了積算 - 開始積算) ÷ 60"""
        if obj.end_totalizer_hour is None or obj.end_totalizer_min is None:
            return None
        end_min = obj.end_totalizer_hour * 60 + obj.end_totalizer_min
        start_min = obj.start_totalizer_hour * 60 + obj.start_totalizer_min
        diff_min = end_min - start_min
        if diff_min < 0:
            return None  # 積算リセット等
        return round(diff_min / 60, 1)

    def get_operating_rate(self, obj):
        """稼働率 = 加工時間 ÷ 仕事時間 × 100"""
        process_hours = self.get_process_hours(obj)
        if process_hours is None:
            return None
        work_hours = float(obj.work_hours or 0)
        if work_hours <= 0:
            return None
        return round(process_hours / work_hours * 100, 1)

    def validate_start_totalizer_min(self, value):
        if value > 59:
            raise serializers.ValidationError('分は0〜59で入力してください。')
        return value

    def validate_end_totalizer_min(self, value):
        if value is not None and value > 59:
            raise serializers.ValidationError('分は0〜59で入力してください。')
        return value

    def validate_work_hours(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError('仕事時間は0より大きい値を入力してください。')
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = request.user
            validated_data['updated_by'] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['updated_by'] = request.user
        return super().update(instance, validated_data)
