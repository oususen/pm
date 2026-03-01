from rest_framework import viewsets, status
from rest_framework.views import APIView
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import timedelta, datetime
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
import django_filters
from django.db.models import Q, Max
from django.db import transaction
import logging
import csv
import io
from django.http import HttpResponse

from .models import LineDemand
from orders.models import OrderLine
from .models_line_backlog import LineBacklog
from .models_line_backlog_adjustment import LineBacklogAdjustment
from .models_line_plan import LinePlan
from .models_production import StockAllocation, ProductionOrder, ProcessActual
from .models_line_gantt_plan import LineGanttPlan
from .models_line_daily_schedule_setting import LineDailyScheduleSetting
from .models_line_default_schedule_setting import LineDefaultScheduleSetting
from .models_plan_change_log import ProductionPlanChangeLog
from .models_plan_lock_setting import ProductionPlanLockSetting
from .models_schedule_config import ScheduleConfig
from .serializers import (
    LineDemandSerializer,
    LineBacklogSerializer,
    LinePlanSerializer,
    ProductionPlanChangeLogSerializer,
    LineGanttPlanSerializer,
    LineDailyScheduleSettingSerializer,
    LineDefaultScheduleSettingSerializer,
    ProductionPlanLockSettingSerializer,
    ScheduleConfigSerializer,
    StockAllocationSerializer,
    ProductionOrderSerializer,
    ProductionOrderListSerializer,
    ProcessActualSerializer,
    LineBacklogAdjustmentSerializer,
)
from .services.order_expansion import OrderExpansionService
from .services.gantt_planning import generate_line_gantt_plans
from masters.models import Routing, RoutingStep, ProcessCycleTime, Line, Supplier, Process, Calendar, CalendarDay, BOM, BOMItem, Product
from django.contrib.auth import get_user_model
from django.db.models import Q

logger = logging.getLogger(__name__)


class LineDemandViewSet(viewsets.ModelViewSet):
    """ライン需要展開ViewSet"""

    queryset = LineDemand.objects.all().select_related('line', 'product', 'routing_step', 'routing_step__process')
    serializer_class = LineDemandSerializer
    pagination_class = None  # 小規模データ想定のためページングなしで返却
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['line', 'routing_step', 'product', 'plan_date']
    search_fields = ['product_code', 'order_numbers']
    ordering_fields = ['plan_date', 'line', 'product_code', 'created_at']
    ordering = ['plan_date', 'line']

    @action(detail=False, methods=['post'])
    def expand(self, request):
        """OPEN受注をライン別に展開してt_line_demandを再生成"""
        clear_param = request.data.get('clear_existing', True)
        if isinstance(clear_param, str):
            clear_existing = clear_param.lower() not in ['false', '0', 'no']
        else:
            clear_existing = bool(clear_param)

        service = OrderExpansionService()
        result = service.expand_open_orders(clear_existing=clear_existing)

        status_code = status.HTTP_201_CREATED if not result.get('errors') else status.HTTP_400_BAD_REQUEST
        return Response(result, status=status_code)


class LineBacklogFilter(django_filters.FilterSet):
    """LineBacklogのカスタムフィルタ"""
    line = django_filters.NumberFilter(field_name='line_id')
    process = django_filters.NumberFilter(field_name='process_id')
    product = django_filters.NumberFilter(field_name='product_id')
    product__in = django_filters.CharFilter(method='filter_product_in')
    plan_date = django_filters.DateFilter(field_name='plan_date')
    plan_date__gte = django_filters.DateFilter(field_name='plan_date', lookup_expr='gte')
    plan_date__lte = django_filters.DateFilter(field_name='plan_date', lookup_expr='lte')

    class Meta:
        model = LineBacklog
        fields = []

    def filter_product_in(self, queryset, name, value):
        """カンマ区切りの製品IDリストでフィルタ"""
        if value:
            try:
                product_ids = [int(x.strip()) for x in value.split(',') if x.strip()]
                return queryset.filter(product_id__in=product_ids)
            except (ValueError, TypeError):
                return queryset.none()
        return queryset


class LinePlanFilter(django_filters.FilterSet):
    """LinePlanのカスタムフィルタ"""
    line = django_filters.NumberFilter(field_name='line_id')
    process = django_filters.NumberFilter(field_name='process_id')
    product = django_filters.NumberFilter(field_name='product_id')
    plan_date = django_filters.DateFilter(field_name='plan_date')
    plan_date__gte = django_filters.DateFilter(field_name='plan_date', lookup_expr='gte')
    plan_date__lte = django_filters.DateFilter(field_name='plan_date', lookup_expr='lte')

    class Meta:
        model = LinePlan
        fields = []


class ProductionPlanChangeLogFilter(django_filters.FilterSet):
    """ProductionPlanChangeLogのカスタムフィルタ"""
    line = django_filters.NumberFilter(field_name='line_id')
    process = django_filters.NumberFilter(field_name='process_id')
    product = django_filters.NumberFilter(field_name='product_id')
    changed_by = django_filters.NumberFilter(field_name='changed_by_id')
    plan_date = django_filters.DateFilter(field_name='plan_date')
    plan_date__gte = django_filters.DateFilter(field_name='plan_date', lookup_expr='gte')
    plan_date__lte = django_filters.DateFilter(field_name='plan_date', lookup_expr='lte')
    changed_at__gte = django_filters.DateTimeFilter(field_name='changed_at', lookup_expr='gte')
    changed_at__lte = django_filters.DateTimeFilter(field_name='changed_at', lookup_expr='lte')

    class Meta:
        model = ProductionPlanChangeLog
        fields = []


class LineGanttPlanFilter(django_filters.FilterSet):
    """LineGanttPlanのカスタムフィルタ"""
    line = django_filters.NumberFilter(field_name='line_id')
    product = django_filters.NumberFilter(field_name='product_id')
    plan_date = django_filters.DateFilter(field_name='plan_date')
    plan_date__gte = django_filters.DateFilter(field_name='plan_date', lookup_expr='gte')
    plan_date__lte = django_filters.DateFilter(field_name='plan_date', lookup_expr='lte')

    class Meta:
        model = LineGanttPlan
        fields = []


class ProductionPlanChangeLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductionPlanChangeLog.objects.all().select_related('line', 'process', 'product', 'changed_by')
    serializer_class = ProductionPlanChangeLogSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductionPlanChangeLogFilter
    search_fields = [
        'product__product_code',
        'product__product_name',
        'process__process_code',
        'process__process_name',
        'line__line_code',
        'line__line_name',
        'reason',
        'changed_by__username',
        'changed_by__first_name',
        'changed_by__last_name',
    ]
    ordering_fields = ['changed_at', 'plan_date', 'line', 'process', 'product', 'before_qty', 'after_qty']
    ordering = ['-changed_at', '-id']


class LinePlanViewSet(viewsets.ModelViewSet):
    queryset = LinePlan.objects.all().select_related('process', 'product', 'line')
    serializer_class = LinePlanSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = LinePlanFilter
    ordering_fields = ['plan_date', 'line', 'product']
    ordering = ['plan_date', 'line']

    @action(detail=False, methods=['post'])
    def save(self, request):
        """
        ユーザーが入力した計画データをLinePlanに保存する
        期待payload: { line_id, items: [{product_id, process_id, plan_date, plan_qty?, sequence_no?}] }

        保存前に、該当ライン・日付・製品のすべてのLinePlanとLineGanttPlanを削除してから新規作成する
        """
        line_id = request.data.get('line_id')
        items = request.data.get('items', [])
        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(items, list) or not items:
            return Response({'detail': 'items is required'}, status=status.HTTP_400_BAD_REQUEST)
        raw_reason = request.data.get('change_reason')
        change_reason = None
        if raw_reason is not None:
            change_reason = str(raw_reason).strip()
            if not change_reason:
                return Response({'detail': 'change_reason is required'}, status=status.HTTP_400_BAD_REQUEST)

        from masters.models import Product
        from django.db import transaction

        def parse_plan_date(raw_date):
            if isinstance(raw_date, str):
                return datetime.strptime(raw_date, '%Y-%m-%d').date()
            return raw_date

        # 対象となる日付と製品を抽出
        affected_dates = set()
        affected_products = set()
        for it in items:
            plan_date = it.get('plan_date')
            product_id = it.get('product_id')
            if plan_date and product_id:
                affected_dates.add(parse_plan_date(plan_date))
                affected_products.add(product_id)

        created = 0
        deleted_plan = 0
        deleted_gantt = 0
        deleted_backlog = 0
        skipped = []
        product_cache = {}
        next_seq_cache = {}
        existing_plan_map = {}
        change_user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

        def get_next_sequence(plan_date_obj):
            """自動採番: 日付ごとに連番を生成"""
            cache_key = (line_id, plan_date_obj)
            if cache_key not in next_seq_cache:
                next_seq_cache[cache_key] = 1
            next_seq = next_seq_cache[cache_key]
            next_seq_cache[cache_key] = next_seq + 1
            return next_seq

        def record_change(before_qty, after_qty, plan_date_obj, product_id, process_id, line_id_val, sequence_no_val, plan_id_val):
            if not change_reason:
                return
            if before_qty == after_qty:
                return
            ProductionPlanChangeLog.objects.create(
                plan_date=plan_date_obj,
                product_id=product_id,
                process_id=process_id,
                line_id=line_id_val,
                sequence_no=sequence_no_val,
                plan_id=plan_id_val,
                before_qty=before_qty,
                after_qty=after_qty,
                reason=change_reason,
                changed_by=change_user,
            )

        # トランザクション内で削除→作成を実行
        with transaction.atomic():
            if change_reason and affected_dates and affected_products:
                existing_plans = LinePlan.objects.filter(
                    line_id=line_id,
                    plan_date__in=affected_dates,
                    product_id__in=affected_products
                )
                for plan in existing_plans:
                    key = (plan.product_id, plan.process_id, plan.plan_date, plan.sequence_no)
                    existing_plan_map[key] = plan
            # 1. 該当LinePlanのplan_idを先に取得
            if affected_dates and affected_products:
                existing_plan_ids = list(LinePlan.objects.filter(
                    line_id=line_id,
                    plan_date__in=affected_dates,
                    product_id__in=affected_products
                ).values_list('plan_id', flat=True))

                # 2. 該当ライン・日付・製品のLinePlanを削除
                deleted_plan_result = LinePlan.objects.filter(
                    line_id=line_id,
                    plan_date__in=affected_dates,
                    product_id__in=affected_products
                ).delete()
                deleted_plan = deleted_plan_result[0] if deleted_plan_result else 0

                # 3. 該当ライン・日付・製品のLineGanttPlanを削除
                deleted_gantt_result = LineGanttPlan.objects.filter(
                    line_id=line_id,
                    plan_date__in=affected_dates,
                    product_id__in=affected_products
                ).delete()
                deleted_gantt = deleted_gantt_result[0] if deleted_gantt_result else 0

                # 4. 該当LinePlanのplan_idに紐づくLineBacklogを削除（計画レコードのみ）
                # ルール: sequence_no > 0 のレコードは計画レコードとして削除
                #        sequence_no = 0 は在庫・需要・仕損などの基礎データとして保持
                #        sequence_no = NULL は実績レコードとして保持
                deleted_backlog = 0
                if existing_plan_ids:
                    deleted_backlog_result = LineBacklog.objects.filter(
                        plan_id__in=existing_plan_ids,
                        sequence_no__gt=0
                    ).delete()
                    deleted_backlog = deleted_backlog_result[0] if deleted_backlog_result else 0

            # 4. 新規作成
            for it in items:
                try:
                    product_id = it.get('product_id')
                    process_id = it.get('process_id')
                    plan_date = it.get('plan_date')
                    if not product_id or not process_id or not plan_date:
                        skipped.append({'item': it, 'reason': 'product_id/process_id/plan_date required'})
                        continue

                    plan_qty_value = Decimal(str(it.get('plan_qty') or 0))
                    plan_date_obj = parse_plan_date(plan_date)

                    seq_in = it.get('sequence_no')
                    if seq_in in (None, '', 0):
                        # sequence_noが指定されていない場合は自動採番
                        if plan_qty_value > 0:
                            sequence_no = get_next_sequence(plan_date_obj)
                        else:
                            skipped.append({'item': it, 'reason': 'sequence_no required for zero quantity'})
                            continue
                    else:
                        try:
                            sequence_no = int(seq_in)
                        except (TypeError, ValueError):
                            skipped.append({'item': it, 'reason': 'invalid sequence_no'})
                            continue

                    existing_key = (product_id, process_id, plan_date_obj, sequence_no)
                    existing_plan = existing_plan_map.pop(existing_key, None)
                    before_qty = int(existing_plan.plan_qty or 0) if existing_plan else 0
                    before_plan_id = existing_plan.plan_id if existing_plan else None

                    # plan_qty <= 0 の場合はスキップ（既に削除済み）
                    if plan_qty_value <= 0:
                        record_change(
                            before_qty,
                            0,
                            plan_date_obj,
                            product_id,
                            process_id,
                            line_id,
                            sequence_no,
                            before_plan_id,
                        )
                        continue

                    if product_id not in product_cache:
                        try:
                            product = Product.objects.get(id=product_id)
                            product_cache[product_id] = product
                        except Product.DoesNotExist:
                            skipped.append({'item': it, 'reason': 'product not found'})
                            continue
                    product = product_cache[product_id]
                    product_code = product.product_code

                    qty_label = str(plan_qty_value).rstrip('0').rstrip('.')
                    if '.' in qty_label:
                        qty_label = qty_label.replace('.', 'p')

                    plan_id = f"{product_code}_{plan_date_obj.strftime('%Y%m%d')}_{qty_label}_{sequence_no}"

                    # 新規作成
                    LinePlan.objects.create(
                        plan_date=plan_date_obj,
                        process_id=process_id,
                        product_id=product_id,
                        line_id=line_id,
                        plan_qty=int(plan_qty_value),
                        plan_id=plan_id,
                        sequence_no=sequence_no,
                    )
                    created += 1
                    record_change(
                        before_qty,
                        int(plan_qty_value),
                        plan_date_obj,
                        product_id,
                        process_id,
                        line_id,
                        sequence_no,
                        plan_id,
                    )

                except Exception as e:
                    return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

            if change_reason:
                for plan in existing_plan_map.values():
                    record_change(
                        int(plan.plan_qty or 0),
                        0,
                        plan.plan_date,
                        plan.product_id,
                        plan.process_id,
                        line_id,
                        plan.sequence_no,
                        plan.plan_id,
                    )

        return Response({
            'created': created,
            'deleted_plan': deleted_plan,
            'deleted_gantt': deleted_gantt,
            'deleted_backlog': deleted_backlog,
            'skipped': skipped
        })


class LineBacklogViewSet(viewsets.ModelViewSet):
    queryset = LineBacklog.objects.all().select_related('process', 'product', 'line')
    serializer_class = LineBacklogSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = LineBacklogFilter
    ordering_fields = ['plan_date', 'line', 'product']
    ordering = ['plan_date', 'line']

    def list(self, request, *args, **kwargs):
        include_split = request.query_params.get('include_order_split')
        include_split = str(include_split).lower() in ['true', '1', 'yes']

        if not include_split:
            return super().list(request, *args, **kwargs)

        queryset = self.filter_queryset(self.get_queryset())
        items = list(queryset)
        self._attach_order_split(items)
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)

    def _attach_order_split(self, items):
        from collections import defaultdict
        from django.db.models import Q

        if not items:
            return

        line_ids = {item.line_id for item in items if item.line_id}
        if not line_ids:
            return

        line_map = {line.id: line for line in Line.objects.filter(id__in=line_ids)}
        default_calendar_id = Calendar.objects.filter(calendar_code='daiso').values_list('id', flat=True).first()

        items_by_line = defaultdict(list)
        for item in items:
            items_by_line[item.line_id].append(item)

        for line_id, line_items in items_by_line.items():
            dates = [it.plan_date for it in line_items if it.plan_date]
            if not dates:
                continue

            min_date = min(dates)
            max_date = max(dates)

            line_obj = line_map.get(line_id)
            calendar_id = getattr(line_obj, 'calendar_id', None) or default_calendar_id

            steps_on_line = RoutingStep.objects.filter(
                line_id=line_id
            ).select_related('output_product', 'routing__product', 'line')

            product_step_map = {}
            final_products = set()
            max_lead_days = 0

            for step in steps_on_line:
                product = step.output_product or (step.routing.product if step.routing_id else None)
                if not product:
                    continue
                if product.id not in product_step_map:
                    product_step_map[product.id] = step
                if product.is_final_product:
                    final_products.add(product.id)
                    # 最終品はラインLTを使用
                    lead_days = (step.line.lead_time_days or 0) if step.line_id and step.line else 0
                    if lead_days > max_lead_days:
                        max_lead_days = lead_days

            if not final_products:
                continue

            due_end = max_date + timedelta(days=max_lead_days + 7)
            order_lines = OrderLine.objects.filter(
                order__status='OPEN',
                product_id__in=final_products,
                due_date__gte=min_date,
                due_date__lte=due_end,
            ).select_related('order')

            firm_map = defaultdict(int)
            forecast_map = defaultdict(int)
            workday_cache = {}

            def is_working_day(target_date):
                if not calendar_id:
                    # カレンダー未設定時は週末を非稼働日扱い（pickupと同一ルール）
                    return target_date.weekday() < 5
                if target_date in workday_cache:
                    return workday_cache[target_date]
                cal = CalendarDay.objects.filter(
                    calendar_id=calendar_id,
                    target_date=target_date
                ).first()
                # カレンダ未登録日も週末は非稼働日扱い（pickupと同一ルール）
                is_work = cal.is_working_day if cal is not None else target_date.weekday() < 5
                workday_cache[target_date] = is_work
                return is_work

            def shift_business_days(target_date, days):
                if not days:
                    if not calendar_id:
                        return target_date
                    if is_working_day(target_date):
                        return target_date
                    current = target_date
                    while True:
                        current = current - timedelta(days=1)
                        if is_working_day(current):
                            return current
                if not calendar_id:
                    return target_date + timedelta(days=-days)

                step = -1 if days > 0 else 1
                remaining = abs(int(days))
                current = target_date
                while remaining > 0:
                    current = current + timedelta(days=step)
                    if is_working_day(current):
                        remaining -= 1
                return current

            def resolve_lead_time_days(product_id):
                # 最終品はラインLTを使用
                step = product_step_map.get(product_id)
                if step and step.line and step.line.lead_time_days:
                    return step.line.lead_time_days
                return 0

            for ol in order_lines:
                if not ol.product_id or not ol.due_date:
                    continue
                lead_days = resolve_lead_time_days(ol.product_id)
                plan_date = shift_business_days(ol.due_date, lead_days)
                if plan_date < min_date or plan_date > max_date:
                    continue
                qty = ol.quantity or 0
                key = (ol.product_id, plan_date)
                order_type = (ol.order.order_type or '').upper()
                if order_type == 'FIRM':
                    firm_map[key] += int(qty)
                else:
                    forecast_map[key] += int(qty)

            for item in line_items:
                if item.product_id not in final_products:
                    continue
                key = (item.product_id, item.plan_date)
                item.firm_order_qty = firm_map.get(key, 0)
                item.forecast_order_qty = forecast_map.get(key, 0)

    @action(detail=False, methods=['post'], url_path='resolve_upstream_lines')
    def resolve_upstream_lines(self, request):
        """
        BOM/ルーティングから前ライン候補を抽出する。

        期待payload: { line_id?, product_ids: [int] }
        """
        line_id = request.data.get('line_id')
        product_ids = request.data.get('product_ids', [])

        if isinstance(product_ids, str):
            product_ids = [p for p in product_ids.split(',') if p.strip()]
        if not isinstance(product_ids, (list, tuple)) or not product_ids:
            return Response({'line_ids': []})

        try:
            parent_ids = {int(p) for p in product_ids}
        except (TypeError, ValueError):
            return Response({'detail': 'product_ids must be numeric'}, status=status.HTTP_400_BAD_REQUEST)

        bom_items = BOMItem.objects.filter(
            bom__is_active=True,
            bom__parent_product_id__in=parent_ids,
        )
        child_ids = set(bom_items.values_list('child_product_id', flat=True))
        if not child_ids:
            return Response({'line_ids': []})

        routing_steps = RoutingStep.objects.filter(
            Q(output_product_id__in=child_ids) | Q(routing__product_id__in=child_ids),
            line_id__isnull=False,
            routing__is_active=True,
        )
        line_ids = sorted(set(routing_steps.values_list('line_id', flat=True)))

        if line_id:
            try:
                line_id = int(line_id)
                line_ids = [lid for lid in line_ids if lid != line_id]
            except (TypeError, ValueError):
                pass

        return Response({
            'line_ids': line_ids,
            'child_product_ids': sorted(child_ids),
        })

    @action(detail=False, methods=['post'])
    def pickup(self, request):
        """
        ラインの需要を取得・計算する。

        処理フロー：
        1. LineBacklogにデータがあればそのまま返す
        2. なければ需要を計算：
           - 後ラインからplan_qtyを集計 × BOM個数 → order_qty
           - 後ラインがなければLineDemandから → order_qty（最終ライン）
        3. 計算結果をLineBacklogに保存して返す

        期待payload: { line_id, start_date?, end_date? }
        """
        import logging
        import time
        from masters.models import BOMItem, RoutingStep
        from collections import defaultdict

        logger = logging.getLogger(__name__)
        pickup_start = time.perf_counter()

        line_id = request.data.get('line_id')
        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        def parse_date(val):
            if val is None:
                return None
            if hasattr(val, 'year'):
                return val
            try:
                return datetime.strptime(str(val), '%Y-%m-%d').date()
            except Exception:
                return None

        start_dt = parse_date(start_date)
        end_dt = parse_date(end_date)

        # このラインで生産される全製品を特定（中間品、単品完成品、ライン最終品、工程最終品を含む）
        target_products = set()
        final_products = set()  # ライン最終品
        intermediate_products = set()  # 中間品
        product_process_map = {}
        product_step_map = {}

        # このラインに属する全工程を取得し、全ての製品を対象とする
        from django.db.models import Q  # 安全側でローカルインポート（UnboundLocalError対策）
        steps_on_line = RoutingStep.objects.filter(
            Q(line_id=line_id) | Q(line__isnull=True, process__line_id=line_id)
        ).select_related('output_product', 'routing__product', 'process')

        steps_on_line_count = 0
        max_source_lt_days = 0
        for step in steps_on_line:
            steps_on_line_count += 1
            product = step.output_product or step.routing.product
            if product:
                target_products.add(product.id)
                product_process_map[product.id] = step.process_id
                if product.id not in product_step_map:
                    product_step_map[product.id] = step

                # ライン最終品と中間品を分類
                # is_final_product がTrueなら最終品扱い
                if product.is_final_product:
                    final_products.add(product.id)
                else:
                    intermediate_products.add(product.id)

            # 需要元データの取得上限をLT分だけ先まで広げるための最大LT
            try:
                if step.time_unit == 'MINUTE':
                    step_lt = int(getattr(getattr(step, 'line', None), 'lead_time_days', 0) or 0)
                else:
                    step_lt = int(step.lead_time_days or 0)
                if step_lt > max_source_lt_days:
                    max_source_lt_days = step_lt
            except Exception:
                pass

        logger.info(
            "pickup: line_id=%s steps_on_line=%s target_products=%s final_products=%s intermediate_products=%s",
            line_id,
            steps_on_line_count,
            len(target_products),
            len(final_products),
            len(intermediate_products),
        )

        if not target_products:
            return Response([])
        source_end_dt = (end_dt + timedelta(days=max_source_lt_days + 7)) if end_dt else None

        # 需要を計算：(product_id, plan_date) -> order_qty
        demand_map = defaultdict(Decimal)

        # 使用するカレンダ（ライン紐付があれば優先、無ければdaiso）
        line_obj = Line.objects.filter(id=line_id).first()
        calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(calendar_code='daiso').values_list('id', flat=True).first()

        # CalendarDayを一括取得してキャッシュ化（N+1問題を解消）
        calendar_day_cache = {}
        if calendar_id:
            # 期間を広めに取得（リードタイム分を考慮して前後60日）
            cache_start = (start_dt - timedelta(days=60)) if start_dt else None
            cache_end = (end_dt + timedelta(days=60)) if end_dt else None
            cal_qs = CalendarDay.objects.filter(calendar_id=calendar_id)
            if cache_start:
                cal_qs = cal_qs.filter(target_date__gte=cache_start)
            if cache_end:
                cal_qs = cal_qs.filter(target_date__lte=cache_end)
            for cal in cal_qs:
                calendar_day_cache[cal.target_date] = cal.is_working_day

        def shift_business_days(target_date, days):
            """
            稼働日で日付をシフトする。
            days > 0 なら過去方向へ、days < 0 なら未来方向へ。
            カレンダが無い場合は週末判定（土日非稼働）、さらに無ければ暦日でシフト。
            """
            def is_working_day(check_date):
                # カレンダ未設定 → 週末判定（月〜金を稼働日）
                if not calendar_id:
                    return check_date.weekday() < 5
                if check_date in calendar_day_cache:
                    return calendar_day_cache[check_date]
                cal = CalendarDay.objects.filter(calendar_id=calendar_id, target_date=check_date).first()
                is_work = cal.is_working_day if cal is not None else check_date.weekday() < 5
                calendar_day_cache[check_date] = is_work
                return is_work

            if not days:
                if not calendar_id:
                    return target_date
                if is_working_day(target_date):
                    return target_date
                current = target_date
                while True:
                    current = current - timedelta(days=1)
                    if is_working_day(current):
                        return current
            step = -1 if days > 0 else 1  # 正:過去へ、負:未来へ
            remaining = abs(int(days))
            current = target_date
            while remaining > 0:
                current = current + timedelta(days=step)
                if is_working_day(current):
                    remaining -= 1
            return current

        gantt_usage_cache = {}
        downstream_backlog_cache = {}

        def build_line_start_map(line_id, product_ids):
            key = (
                line_id,
                tuple(sorted(product_ids)),
                start_date,
                end_date,
                source_end_dt,
            )
            if key in gantt_usage_cache:
                return gantt_usage_cache[key]

            gantt_start = time.perf_counter()
            qs = LineGanttPlan.objects.filter(
                line_id=line_id,
                product_id__in=product_ids,
            ).only('plan_id', 'start_datetime', 'plan_qty')

            usage_map = {}
            plan_id_set = set()
            gantt_rows = 0
            for plan in qs:
                gantt_rows += 1
                start_dt_value = plan.start_datetime
                if not start_dt_value:
                    continue
                # 日替わり8時ルール: 8時より前は前日扱い
                def apply_day_boundary(dt_val):
                    """日替わり時刻（8時）を考慮した日付を取得"""
                    if hasattr(dt_val, 'hour') and dt_val.hour < 8:
                        return (dt_val - timedelta(days=1)).date()
                    return dt_val.date() if hasattr(dt_val, 'date') else dt_val

                try:
                    plan_day = apply_day_boundary(start_dt_value)
                except Exception:
                    try:
                        ts = str(start_dt_value).replace('Z', '+00:00')
                        parsed_dt = datetime.fromisoformat(ts)
                        plan_day = apply_day_boundary(parsed_dt)
                    except Exception:
                        continue
                if start_dt and plan_day < start_dt:
                    continue
                if source_end_dt and plan_day > source_end_dt:
                    continue
                try:
                    qty = Decimal(str(plan.plan_qty or 0))
                except Exception:
                    qty = Decimal('0')
                if qty == 0:
                    continue
                if plan.plan_id:
                    plan_id_set.add(plan.plan_id)
                usage_map[plan_day] = usage_map.get(plan_day, Decimal('0')) + qty

            gantt_usage_cache[key] = (usage_map, plan_id_set)
            logger.info(
                "pickup: gantt_plans line_id=%s products=%s rows=%s time=%.3fs",
                line_id,
                len(product_ids),
                gantt_rows,
                time.perf_counter() - gantt_start,
            )
            return usage_map, plan_id_set

        def get_downstream_backlog_rows(target_line_id, target_ids):
            cache_key = (
                target_line_id,
                tuple(sorted(target_ids)),
                start_dt,
                source_end_dt or end_dt,
            )
            if cache_key in downstream_backlog_cache:
                return downstream_backlog_cache[cache_key]

            qs = LineBacklog.objects.filter(
                line_id=target_line_id,
                product_id__in=target_ids,
            )
            if start_dt:
                qs = qs.filter(plan_date__gte=start_dt)
            if source_end_dt or end_dt:
                qs = qs.filter(plan_date__lte=source_end_dt or end_dt)
            rows = list(qs.values_list('product_id', 'plan_date', 'plan_qty', 'plan_id'))
            downstream_backlog_cache[cache_key] = rows
            return rows

        def resolve_lead_time_days(current_product_id, bom_item=None):
            """現ラインのLTを優先して解決する。"""
            step = product_step_map.get(current_product_id)
            if step is not None:
                try:
                    # time_unit基準でLT解決:
                    # - MINUTE: line.lead_time_days を使用
                    # - DAY: routing_step.lead_time_days を使用
                    if step.time_unit == 'MINUTE':
                        step_line = getattr(step, 'line', None)
                        return max(int(getattr(step_line, 'lead_time_days', 0) or 0), 0)

                    return max(int(step.lead_time_days or 0), 0)
                except Exception:
                    return 0
            if bom_item and bom_item.lead_time_days:
                return bom_item.lead_time_days
            return 0

        # 既存バックログを先に取得し、ゼロ需要でもレコードを返せるよう初期化
        backlog_qs = self.get_queryset().filter(line_id=line_id, product_id__in=target_products).select_related('product', 'process')
        if start_date:
            backlog_qs = backlog_qs.filter(plan_date__gte=start_date)
        if end_date:
            backlog_qs = backlog_qs.filter(plan_date__lte=end_date)
        existing_backlogs = list(backlog_qs)
        for existing in existing_backlogs:
            demand_map[(existing.product_id, existing.plan_date)] = Decimal('0')
        logger.info("pickup: existing_backlogs=%s", len(existing_backlogs))

        # 最終品はOrderLineから、中間品は後工程から需要を取得

        # A. 最終品（is_final_product=True）はOrderLineから取得
        if final_products:
            order_lines_qs = OrderLine.objects.filter(
                order__status='OPEN',
                product_id__in=final_products
            ).select_related('order', 'product')

            if start_date:
                order_lines_qs = order_lines_qs.filter(due_date__gte=start_date)
            if source_end_dt or end_date:
                order_lines_qs = order_lines_qs.filter(due_date__lte=source_end_dt or end_date)

            order_lines = list(order_lines_qs)

            logger.info("pickup: order_lines=%s", len(order_lines))

            firm_map = defaultdict(Decimal)
            forecast_map = defaultdict(Decimal)
            shifted_keys = set()

            for ol in order_lines:
                if not ol.product_id:
                    continue
                step = product_step_map.get(ol.product_id)
                if not step:
                    continue

                lead_days = resolve_lead_time_days(ol.product_id)
                plan_date = shift_business_days(ol.due_date, lead_days)
                key = (ol.product_id, plan_date)
                if plan_date != ol.due_date:
                    shifted_keys.add(key)

                qty = Decimal(str(ol.quantity or 0))
                order_type = (ol.order.order_type or '').upper()
                if order_type == 'FIRM':
                    firm_map[key] += qty
                else:
                    forecast_map[key] += qty

            for key in set(firm_map) | set(forecast_map):
                firm_qty = firm_map.get(key, Decimal('0'))
                forecast_qty = forecast_map.get(key, Decimal('0'))
                # 前倒しで同日に重なった需要のみ、確定＋内示を合算する。
                # 前倒しが無い場合は従来どおり「確定優先」。
                if key in shifted_keys and firm_qty > 0 and forecast_qty > 0:
                    demand_qty = firm_qty + forecast_qty
                else:
                    demand_qty = firm_qty if firm_qty > 0 else forecast_qty
                demand_map[key] = demand_qty

        # B. 中間品は後工程から需要を取得

        # 1. 後ライン（次工程）から需要を取得（RoutingStepベース）
        # ロジック：
        #   ステップ1: 現在ラインのoutput_product（例：中間品C）を特定
        #   ステップ2: 中間品Cを子部品として使う親製品（例：中間品B）をBOMから探す
        #   ステップ3: 親製品を出力するラインをRoutingStepから探す
        #   ステップ4: そのライン（例：溶接ライン）のLineBacklogから計画数を取得
        #   ステップ5: BOM個数を掛けて現在ラインの必要数を計算
        downstream_found = False

        # 中間品がある場合、関連データを一括取得（N+1問題を解消）
        bom_items_by_child = {}
        parent_product_ids = set()
        if intermediate_products:
            all_bom_items = list(BOMItem.objects.filter(
                child_product_id__in=intermediate_products
            ).select_related('bom', 'bom__parent_product'))
            logger.info("pickup: bom_items_for_intermediate=%s", len(all_bom_items))
            for bom_item in all_bom_items:
                child_id = bom_item.child_product_id
                if child_id not in bom_items_by_child:
                    bom_items_by_child[child_id] = []
                bom_items_by_child[child_id].append(bom_item)
                if bom_item.bom and bom_item.bom.parent_product_id:
                    parent_product_ids.add(bom_item.bom.parent_product_id)

        # 親製品を出力するRoutingStepを一括取得
        downstream_steps_by_product = {}
        if parent_product_ids:
            all_downstream_steps = list(RoutingStep.objects.filter(
                output_product_id__in=parent_product_ids
            ).select_related('routing', 'routing__product', 'line'))
            logger.info("pickup: downstream_steps=%s", len(all_downstream_steps))
            for d_step in all_downstream_steps:
                prod_id = d_step.output_product_id
                if prod_id not in downstream_steps_by_product:
                    downstream_steps_by_product[prod_id] = []
                downstream_steps_by_product[prod_id].append(d_step)

        for product_id in intermediate_products:
            # 現在ラインのoutput_product（例：ブレーキラインなら中間品C）
            current_output_product = product_id

            # ステップ2: この製品を子部品として使うBOMを取得（キャッシュから）
            bom_items = bom_items_by_child.get(current_output_product, [])

            for bom_item in bom_items:
                parent_product = bom_item.bom.parent_product
                if not parent_product:
                    continue

                qty_per = bom_item.quantity or Decimal('0')
                if qty_per == 0:
                    continue

                # ステップ3: 親製品を出力するライン（後工程）をRoutingStepから特定（キャッシュから）
                downstream_steps = downstream_steps_by_product.get(parent_product.id, [])
                # 連産などで1つの親に複数のライン最終品が紐づく場合は、
                # 別最終品由来の親計画をfallbackで混在させないようにする
                final_targets_for_parent = {
                    s.routing.product_id
                    for s in downstream_steps
                    if s.routing
                    and s.routing.product
                    and s.routing.product.is_line_final_product
                    and s.routing.product_id
                    and s.routing.product_id != parent_product.id
                }
                has_multiple_final_targets = len(final_targets_for_parent) > 1

                # 同一(line, process, output_product, routing)が完全に重複している場合だけスキップ
                seen_steps = set()
                for d_step in downstream_steps:
                    step_key = (d_step.line_id, d_step.process_id, d_step.output_product_id, d_step.routing_id)
                    if step_key in seen_steps:
                        continue
                    seen_steps.add(step_key)
                    downstream_line_id = d_step.line_id
                    if not downstream_line_id:
                        continue

                    # リードタイム（日）を考慮：現ラインのRoutingStep > Line > BOM明細 の順で優先
                    lt_days = resolve_lead_time_days(current_output_product, bom_item)

                    # ステップ4: 後工程ラインのLineBacklogから計画数を取得
                    # 親製品が中間品の場合、そのRoutingの最終品（ライン最終品）を基準にする
                    routing_final_product = None
                    if d_step.routing and d_step.routing.product:
                        # Routingの製品がライン最終品の場合、それを使用
                        if d_step.routing.product.is_line_final_product:
                            routing_final_product = d_step.routing.product

                    target_ids = [parent_product.id]
                    if routing_final_product and routing_final_product != parent_product:
                        target_ids.append(routing_final_product.id)

                    # LineBacklog取得：ガントのstart_datetimeを優先し、無ければ親製品/ライン最終品の計画を使用
                    line_start_map, gantt_plan_ids = build_line_start_map(downstream_line_id, target_ids)
                    backlog_rows = get_downstream_backlog_rows(downstream_line_id, target_ids)

                    # ステップ5: 後工程の計画数 × BOM個数 = 現在ラインの必要数
                    if routing_final_product and routing_final_product != parent_product:
                        total_qty_per = qty_per
                    else:
                        total_qty_per = qty_per

                    fallback_map = {}
                    if len(target_ids) > 1:
                        parent_map = {}
                        final_map = {}
                        for backlog_product_id, plan_date, plan_qty, backlog_plan_id in backlog_rows:
                            qty = Decimal(str(plan_qty or 0))
                            if qty == 0:
                                continue
                            if backlog_plan_id and backlog_plan_id in gantt_plan_ids:
                                continue
                            if backlog_product_id == parent_product.id:
                                parent_map[plan_date] = parent_map.get(plan_date, Decimal('0')) + qty
                            else:
                                final_map[plan_date] = final_map.get(plan_date, Decimal('0')) + qty
                        for plan_date in set(parent_map) | set(final_map):
                            if has_multiple_final_targets:
                                # 複数最終品を持つ親では、当該最終品の数量のみを採用する
                                qty = final_map.get(plan_date, Decimal('0'))
                            else:
                                qty = parent_map.get(plan_date)
                                if qty is None or qty <= 0:
                                    qty = final_map.get(plan_date, Decimal('0'))
                            if qty:
                                fallback_map[plan_date] = qty
                    else:
                        for _, plan_date, plan_qty, backlog_plan_id in backlog_rows:
                            qty = Decimal(str(plan_qty or 0))
                            if qty == 0:
                                continue
                            if backlog_plan_id and backlog_plan_id in gantt_plan_ids:
                                continue
                            fallback_map[plan_date] = fallback_map.get(plan_date, Decimal('0')) + qty

                    for plan_date in set(line_start_map) | set(fallback_map):
                        qty = line_start_map.get(plan_date)
                        if qty is None or qty <= 0:
                            qty = fallback_map.get(plan_date, Decimal('0'))
                        if qty == 0:
                            continue
                        shifted_date = shift_business_days(plan_date, lt_days) if lt_days else plan_date
                        key = (current_output_product, shifted_date)
                        demand_map[key] += qty * total_qty_per
                        downstream_found = True

        # 2. RoutingStepベースの展開が失敗した場合、BOMベースの展開を試みる（中間品のみ）
        if not downstream_found and intermediate_products:
            # BOMItemを一括取得（line_idが現在ラインと一致するもの）
            bom_items_for_line = BOMItem.objects.filter(
                child_product_id__in=intermediate_products,
                line_id=line_id
            ).select_related('bom', 'bom__parent_product')

            # 親製品IDを収集
            parent_ids_for_backlog = set()
            bom_items_by_child_line = {}
            for bom_item in bom_items_for_line:
                child_id = bom_item.child_product_id
                if child_id not in bom_items_by_child_line:
                    bom_items_by_child_line[child_id] = []
                bom_items_by_child_line[child_id].append(bom_item)
                if bom_item.bom and bom_item.bom.parent_product_id:
                    parent_ids_for_backlog.add(bom_item.bom.parent_product_id)

            # 親製品のLineBacklogを一括取得
            backlog_by_product = {}
            if parent_ids_for_backlog:
                backlog_qs_parent = LineBacklog.objects.filter(
                    product_id__in=parent_ids_for_backlog,
                    plan_qty__gt=0,
                )
                if start_date:
                    backlog_qs_parent = backlog_qs_parent.filter(plan_date__gte=start_date)
                if source_end_dt or end_date:
                    backlog_qs_parent = backlog_qs_parent.filter(plan_date__lte=source_end_dt or end_date)
                for prod_id, plan_date, plan_qty in backlog_qs_parent.values_list('product_id', 'plan_date', 'plan_qty'):
                    if prod_id not in backlog_by_product:
                        backlog_by_product[prod_id] = []
                    backlog_by_product[prod_id].append((plan_date, plan_qty))

            for product_id in intermediate_products:
                current_output_product = product_id
                bom_items = bom_items_by_child_line.get(current_output_product, [])

                for bom_item in bom_items:
                    parent_product = bom_item.bom.parent_product
                    if not parent_product:
                        continue

                    qty_per = bom_item.quantity or Decimal('0')
                    if qty_per == 0:
                        continue

                    # 親製品のLineBacklogを取得（キャッシュから）
                    backlog_items = backlog_by_product.get(parent_product.id, [])

                    # リードタイムを考慮
                    lt_days = resolve_lead_time_days(current_output_product, bom_item)

                    for plan_date, plan_qty in backlog_items:
                        if lt_days:
                            plan_date = shift_business_days(plan_date, lt_days)
                        key = (current_output_product, plan_date)
                        demand_map[key] += Decimal(str(plan_qty or 0)) * qty_per
                        downstream_found = True

        # 4. LineBacklogに保存（order_qtyのみ更新、他の数量は維持）- bulk操作で高速化
        upserted_items = []
        upsert_start = time.perf_counter()

        # 対象キーを収集
        target_keys = []
        target_key_set = set()
        for (product_id, plan_date), order_qty in demand_map.items():
            if start_dt and plan_date < start_dt:
                continue
            if end_dt and plan_date > end_dt:
                continue
            process_id = product_process_map.get(product_id)
            if not process_id:
                continue
            key = (product_id, plan_date, process_id)
            target_keys.append((product_id, plan_date, process_id, order_qty))
            target_key_set.add(key)

        # 期間内の全日付に対して、存在しない場合はsequence_no=0の行を用意する
        if start_dt and end_dt:
            # sequence_no=0(需要行)の存在だけを判定する。
            # 計画行(sequence_no>0)が存在していても、需要行が無ければ新規作成する。
            existing_any = set(
                LineBacklog.objects.filter(
                    line_id=line_id,
                    product_id__in=target_products,
                    plan_date__range=[start_dt, end_dt],
                    sequence_no=0,
                ).values_list('product_id', 'plan_date', 'process_id')
            )
            total_days = (end_dt - start_dt).days + 1
            for product_id in target_products:
                process_id = product_process_map.get(product_id)
                if not process_id:
                    continue
                for offset in range(total_days):
                    plan_date = start_dt + timedelta(days=offset)
                    key = (product_id, plan_date, process_id)
                    if key in existing_any or key in target_key_set:
                        continue
                    target_keys.append((product_id, plan_date, process_id, Decimal('0')))
                    target_key_set.add(key)

        if target_keys:
            # 既存レコードを一括取得（巨大ORを避ける）
            target_product_ids = sorted({product_id for product_id, _, _, _ in target_keys})
            target_process_ids = sorted({process_id for _, _, process_id, _ in target_keys})
            target_plan_dates = [plan_date for _, plan_date, _, _ in target_keys]
            existing_qs = LineBacklog.objects.filter(
                line_id=line_id,
                sequence_no=0,
                product_id__in=target_product_ids,
                process_id__in=target_process_ids,
            )
            if target_plan_dates:
                min_plan_date = min(target_plan_dates)
                max_plan_date = max(target_plan_dates)
                existing_qs = existing_qs.filter(plan_date__gte=min_plan_date, plan_date__lte=max_plan_date)
            existing_records = {
                (r.product_id, r.plan_date, r.process_id): r
                for r in existing_qs
            }

            to_create = []
            to_update = []
            for product_id, plan_date, process_id, order_qty in target_keys:
                key = (product_id, plan_date, process_id)
                if key in existing_records:
                    obj = existing_records[key]
                    obj.order_qty = order_qty
                    obj.demand_qty_plan = order_qty
                    # sequence_no=0 は需要行なので、計画数は常に0を維持する
                    obj.plan_qty = 0
                    to_update.append(obj)
                else:
                    to_create.append(LineBacklog(
                        plan_date=plan_date,
                        process_id=process_id,
                        product_id=product_id,
                        line_id=line_id,
                        sequence_no=0,
                        order_qty=order_qty,
                        demand_qty_plan=order_qty,
                        plan_qty=0,
                    ))

            # bulk_create と bulk_update を実行
            if to_create:
                LineBacklog.objects.bulk_create(to_create)
            if to_update:
                LineBacklog.objects.bulk_update(to_update, ['order_qty', 'demand_qty_plan', 'plan_qty'])

            upserted_items = to_create + to_update

        logger.info(
            "pickup: upserted_items=%s (create=%s, update=%s) time=%.3fs",
            len(upserted_items),
            len(to_create) if target_keys else 0,
            len(to_update) if target_keys else 0,
            time.perf_counter() - upsert_start,
        )

        # 5. 最新状態を返す
        items_to_serialize = upserted_items
        if not items_to_serialize:
            existing_items = existing_backlogs
            if existing_items:
                items_to_serialize = existing_items
            else:
                placeholder_date = start_dt or end_dt or datetime.today().date()
                placeholders = []
                for product_id in target_products:
                    process_id = product_process_map.get(product_id)
                    if not process_id:
                        continue
                    placeholders.append(LineBacklog(
                        plan_date=placeholder_date,
                        process_id=process_id,
                        product_id=product_id,
                        line_id=line_id,
                        sequence_no=0,
                        order_qty=0,
                        demand_qty_plan=0,
                        plan_qty=0,
                        actual_qty=0,
                        stock_qty=0,
                        planned_stock_qty=0,
                    ))
                items_to_serialize = placeholders
        serializer = self.get_serializer(items_to_serialize, many=True)
        logger.info("pickup: total_time=%.3fs", time.perf_counter() - pickup_start)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='pickup_purchase')
    def pickup_purchase(self, request):
        """
        購買/外注部品の需要を集計してLineBacklogに反映する。

        期待payload: { supplier_id or line_id, start_date?, end_date? }
        """
        from collections import defaultdict

        supplier_id = request.data.get('supplier_id') or request.data.get('line_id')
        if not supplier_id:
            return Response({'detail': 'supplier_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            supplier_id = int(supplier_id)
        except (TypeError, ValueError):
            return Response({'detail': 'supplier_id must be numeric'}, status=status.HTTP_400_BAD_REQUEST)

        supplier = Supplier.objects.filter(id=supplier_id).first()
        if not supplier:
            return Response({'detail': 'supplier not found'}, status=status.HTTP_400_BAD_REQUEST)

        line_code = supplier.supplier_code
        line_name = f"仕入:{supplier.supplier_code} {supplier.supplier_name}"
        if len(line_name) > 50:
            line_name = line_name[:50]
        line_obj, created = Line.objects.get_or_create(
            line_code=line_code,
            defaults={
                'line_name': line_name,
                'line_type': 'PURCHASE',
                'is_active': True,
            }
        )
        if not created and line_obj.line_type != 'PURCHASE':
            line_obj.line_type = 'PURCHASE'
            line_obj.save(update_fields=['line_type'])
        line_id = line_obj.id
        process_code = 'PURCHASE'
        process_name = '購買'
        process_obj, _ = Process.objects.get_or_create(
            process_code=process_code,
            defaults={
                'process_name': process_name,
                'line': line_obj,
                'management_unit': 'DAY',
                'is_active': False,
            }
        )
        process_id = process_obj.id

        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        def parse_date(val):
            if val is None:
                return None
            if hasattr(val, 'year'):
                return val
            try:
                return datetime.strptime(str(val), '%Y-%m-%d').date()
            except Exception:
                return None

        start_dt = parse_date(start_date)
        end_dt = parse_date(end_date)

        bom_items = BOMItem.objects.filter(
            sourcing_type__in=['BUY', 'SUBCON'],
            supplier_id=supplier_id,
            bom__is_active=True,
        ).select_related('bom', 'bom__parent_product')

        parent_to_children = defaultdict(list)
        parent_ids = set()
        child_ids = set()
        for item in bom_items:
            parent_id = item.bom.parent_product_id if item.bom_id else None
            if not parent_id:
                continue
            qty = Decimal(str(item.quantity or 0))
            if qty == 0:
                continue
            lead_time_days = item.lead_time_days or 0
            parent_ids.add(parent_id)
            child_ids.add(item.child_product_id)
            parent_to_children[parent_id].append((item.child_product_id, qty, lead_time_days))

        calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(
            calendar_code='daiso'
        ).values_list('id', flat=True).first()

        # カレンダ日をキャッシュし、無い場合は週末判定にフォールバックする
        calendar_day_cache = {}
        if calendar_id:
            cache_start = (start_dt - timedelta(days=60)) if start_dt else None
            cache_end = (end_dt + timedelta(days=60)) if end_dt else None
            cal_qs = CalendarDay.objects.filter(calendar_id=calendar_id)
            if cache_start:
                cal_qs = cal_qs.filter(target_date__gte=cache_start)
            if cache_end:
                cal_qs = cal_qs.filter(target_date__lte=cache_end)
            for cal in cal_qs:
                calendar_day_cache[cal.target_date] = cal.is_working_day

        def is_working_day(check_date):
            if calendar_id:
                if check_date in calendar_day_cache:
                    return calendar_day_cache[check_date]
                cal = CalendarDay.objects.filter(calendar_id=calendar_id, target_date=check_date).first()
                # 仕入先カレンダ運用:
                # カレンダが設定されている場合、未登録日は「休み」とみなす。
                is_work = cal.is_working_day if cal is not None else False
                calendar_day_cache[check_date] = is_work
                return is_work
            # カレンダ未設定時は週末判定（月〜金を稼働日）を使う
            return check_date.weekday() < 5

        # 親計画の検索範囲を end_dt の「翌出勤日」まで延長する。
        # 表示期間（30日/60日）の末日直後の出勤日の親計画も需要計算に含めることで、
        # 表示期間によって需要値が変わらないようにする。
        parent_orders = []
        if parent_ids:
            parent_qs = LineBacklog.objects.filter(product_id__in=parent_ids).select_related('line')
            if start_dt:
                parent_qs = parent_qs.filter(plan_date__gte=start_dt)
            if end_dt:
                # end_dt の翌日から最初の出勤日を探す（最大14日先まで）
                next_work = end_dt + timedelta(days=1)
                for _ in range(14):
                    if is_working_day(next_work):
                        break
                    next_work += timedelta(days=1)
                parent_qs = parent_qs.filter(plan_date__lte=next_work)

            # 親製品の数量を取得:
            # - 通常ライン: plan_qty > 0
            # - 外作ライン(OUTSOURCE): 計画を持たないため order_qty > 0 も対象にする
            parent_orders = list(
                parent_qs.values('product_id', 'line_id', 'line__line_type', 'plan_date', 'plan_qty', 'order_qty', 'plan_id').filter(
                    Q(plan_qty__gt=0) | Q(order_qty__gt=0, line__line_type='OUTSOURCE')
                )
            )

        # 日替わり8時ルール: 8時より前は前日扱い
        def apply_day_boundary(dt_val):
            """日替わり時刻（8時）を考慮した日付を取得"""
            if hasattr(dt_val, 'hour') and dt_val.hour < 8:
                return (dt_val - timedelta(days=1)).date()
            return dt_val.date() if hasattr(dt_val, 'date') else dt_val

        # 親製品（中間品）から最終品を特定するマップを構築
        # parent_id -> [(line_id, final_product_id)]
        from masters.models import RoutingStep
        parent_to_final = {}
        if parent_ids:
            steps_qs = RoutingStep.objects.filter(
                output_product_id__in=parent_ids
            ).select_related('routing', 'routing__product')
            for step in steps_qs:
                if step.routing and step.routing.product:
                    if step.routing.product.is_line_final_product:
                        parent_id = step.output_product_id
                        final_id = step.routing.product_id
                        line_id_step = step.line_id
                        if parent_id not in parent_to_final:
                            parent_to_final[parent_id] = []
                        parent_to_final[parent_id].append((line_id_step, final_id))

        # ガント検索用の製品ID（親製品＋最終品）
        gantt_product_ids = set(parent_ids)
        for finals in parent_to_final.values():
            for _, final_id in finals:
                gantt_product_ids.add(final_id)

        def shift_business_days(target_date, days):
            """
            稼働日ベースで日付をシフトする（カレンダが無い場合は週末判定）。
            days > 0 なら過去方向、days < 0 なら未来方向。
            """
            if not days:
                if is_working_day(target_date):
                    return target_date
                current = target_date
                while True:
                    current = current - timedelta(days=1)
                    if is_working_day(current):
                        return current

            step = -1 if days > 0 else 1
            remaining = abs(int(days))
            current = target_date
            while remaining > 0:
                current = current + timedelta(days=step)
                if is_working_day(current):
                    remaining -= 1
            return current

        demand_map = defaultdict(Decimal)
        for row in parent_orders:
            parent_id = row['product_id']
            line_id_parent = row.get('line_id')
            plan_date = row['plan_date']

            # 外作ライン(OUTSOURCE)は計画を持たないため order_qty（需要）を使用する
            if row.get('line__line_type') == 'OUTSOURCE':
                plan_qty = Decimal(str(row.get('order_qty') or 0))
            else:
                plan_qty = Decimal(str(row['plan_qty'] or 0))

            # 購買需要では、計画日(plan_date)を基準にLTをシフトする
            effective_date = plan_date

            if plan_qty == 0:
                continue

            # 需要 = 親数量 × 子BOM数量（LTを考慮して日付をシフト）
            for child_id, qty, lead_time_days in parent_to_children.get(parent_id, []):
                target_date = shift_business_days(effective_date, lead_time_days)
                demand_map[(child_id, target_date)] += plan_qty * qty

        # フォールバック: 購買ラインのLineDemand（内示/確定集計）を需要として取り込む
        # BOM展開で同一キーがある場合はBOM計算値を優先する。
        direct_qs = LineDemand.objects.filter(line_id=line_id)
        if start_dt:
            direct_qs = direct_qs.filter(plan_date__gte=start_dt)
        if end_dt:
            direct_qs = direct_qs.filter(plan_date__lte=end_dt)

        direct_demand_product_ids = set()
        for row in direct_qs.values('product_id', 'plan_date', 'plan_qty'):
            product_id = row.get('product_id')
            plan_date = row.get('plan_date')
            qty = Decimal(str(row.get('plan_qty') or 0))
            if not product_id or not plan_date or qty == 0:
                continue
            direct_demand_product_ids.add(product_id)
            # BOM展開対象品は、需要ソースを親計画由来（BOM）に統一する
            if product_id in child_ids:
                continue
            key = (product_id, plan_date)
            if key not in demand_map:
                demand_map[key] = qty

        target_product_ids = set(child_ids) | direct_demand_product_ids
        existing_qs = LineBacklog.objects.filter(
            line_id=line_id,
            process_id=process_id,
            product_id__in=target_product_ids,
        )
        if start_dt:
            existing_qs = existing_qs.filter(plan_date__gte=start_dt)
        if end_dt:
            existing_qs = existing_qs.filter(plan_date__lte=end_dt)

        existing_map = {(obj.product_id, obj.plan_date): obj for obj in existing_qs}

        created = 0
        updated = 0

        for (child_id, plan_date), demand in demand_map.items():
            qty_val = int(demand)
            obj, is_created = LineBacklog.objects.update_or_create(
                plan_date=plan_date,
                process_id=process_id,
                product_id=child_id,
                line_id=line_id,
                sequence_no=0,
                defaults={
                    'order_qty': qty_val,
                    'demand_qty_plan': qty_val,
                    'sequence_no': 0,
                }
            )
            if is_created:
                created += 1
            else:
                updated += 1
            existing_map.pop((child_id, plan_date), None)

        for obj in existing_map.values():
            if (obj.order_qty or 0) != 0 or (obj.demand_qty_plan or 0) != 0:
                obj.order_qty = 0
                obj.demand_qty_plan = 0
                obj.save(update_fields=['order_qty', 'demand_qty_plan', 'updated_at'])
                updated += 1

        return Response({'created': created, 'updated': updated, 'items': len(demand_map), 'line_id': line_id, 'process_id': process_id})

    @action(detail=False, methods=['post'])
    def expand_processes(self, request):
        """
        指定ラインの計画数量を工程レベルに展開する。
        期待payload: { line_id, start_date, end_date, items?: [{product_id, plan_date, plan_qty?, order_qty?, demand_qty_plan?}], read_only?: bool }
        read_only=True の場合、LineBacklogに保存せず計算結果のみを返す
        read_only=False の場合、計算結果をLineBacklogに保存（plan_qtyを計算値で更新）
        """
        from collections import defaultdict
        from masters.models import RoutingStep, Calendar, CalendarDay

        line_id = request.data.get('line_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        items = request.data.get('items', [])
        read_only = request.data.get('read_only', False)  # デフォルトはFalse（保存する）
        auto_plan_mode = request.data.get('auto_plan_mode', False)
        if isinstance(auto_plan_mode, str):
            auto_plan_mode = auto_plan_mode.lower() in ['true', '1', 'yes']
        else:
            auto_plan_mode = bool(auto_plan_mode)
        include_coproduct_children = request.data.get('include_coproduct_children', False)
        if isinstance(include_coproduct_children, str):
            include_coproduct_children = include_coproduct_children.lower() in ['true', '1', 'yes']
        else:
            include_coproduct_children = bool(include_coproduct_children)

        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not start_date or not end_date:
            return Response({'detail': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            line_id = int(line_id)
        except (TypeError, ValueError):
            return Response({'detail': 'line_id must be numeric'}, status=status.HTTP_400_BAD_REQUEST)

        def parse_date(val):
            if val is None:
                return None
            if hasattr(val, 'year'):
                return val
            try:
                return datetime.strptime(str(val), '%Y-%m-%d').date()
            except Exception:
                return None

        # 先に対象期間内のベース計画を集める（フロントからのitems優先、無ければDBから取得）
        base_plans = []
        if isinstance(items, list) and items:
            for it in items:
                plan_date = parse_date(it.get('plan_date'))
                if not plan_date:
                    continue
                product_id = it.get('product_id')
                if not product_id:
                    continue
                plan_qty_raw = it.get('plan_qty', 0)
                order_qty_raw = it.get('order_qty', 0)
                demand_qty_raw = it.get('demand_qty_plan', order_qty_raw)
                try:
                    plan_qty = Decimal(str(plan_qty_raw or 0))
                    order_qty = Decimal(str(order_qty_raw or 0))
                    demand_qty_plan = Decimal(str(demand_qty_raw or 0))
                except Exception:
                    continue
                # 期間外は除外
                if str(plan_date) < str(start_date) or str(plan_date) > str(end_date):
                    continue
                base_plans.append({
                    'product_id': product_id,
                    'plan_date': plan_date,
                    'plan_qty': plan_qty,
                    'order_qty': order_qty,
                    'demand_qty_plan': demand_qty_plan,
                    'sequence_no': it.get('sequence_no'),
                })
        else:
            qs = LinePlan.objects.filter(line_id=line_id)
            qs = qs.filter(plan_date__gte=start_date, plan_date__lte=end_date)
            qs = qs.filter(plan_qty__gt=0)
            for obj in qs:
                base_plans.append({
                    'product_id': obj.product_id,
                    'plan_date': obj.plan_date,
                    'plan_qty': Decimal(str(obj.plan_qty or 0)),
                    'order_qty': Decimal('0'),
                    'demand_qty_plan': Decimal('0'),
                    'sequence_no': obj.sequence_no,
                    'plan_id': obj.plan_id,
                })

        if not base_plans:
            return Response([])

        # 連産品（コプロダクト）用の補助マップ
        # child_to_parent: 子製品 -> (親セットID, qty_per)
        # parent_children: 親セット -> [(child_id, qty_per)]
        # copro_set_qty: (親セット, 日付) -> 必要セット数（子計画から逆算した最大値）
        # copro_driver: (親セット, 日付) -> 工数を計上する代表子ID（最優先:計画>0かつIDが小さいもの）
        copro_child_map = {}
        parent_children = {}
        copro_set_qty = {}
        copro_driver = {}
        plan_qty_map = {}

        # plan_qty_mapを先に作成（Decimal化）
        for plan in base_plans:
            try:
                plan_qty_map[(plan['product_id'], plan['plan_date'])] = Decimal(str(plan['plan_qty'] or 0))
            except Exception:
                plan_qty_map[(plan['product_id'], plan['plan_date'])] = Decimal('0')

        # is_coproduct=True のBOMから子→親の対応を構築（最新valid_from優先）
        # is_coproduct_driver=True の子製品のみを copro_child_map に登録（共用部品問題を回避）
        copro_boms = BOM.objects.filter(is_coproduct=True, is_active=True).order_by('-valid_from', '-id').prefetch_related('items')
        for bom in copro_boms:
            for item in bom.items.all():
                try:
                    qty_decimal = Decimal(item.quantity)
                except Exception:
                    continue
                if qty_decimal == 0:
                    continue
                # is_coproduct_driver=True の子製品のみを連産品展開の対象とする
                if item.is_coproduct_driver:
                    if item.child_product_id not in copro_child_map:
                        copro_child_map[item.child_product_id] = {
                            'parent_id': bom.parent_product_id,
                            'qty_per': qty_decimal,
                        }
                parent_children.setdefault(bom.parent_product_id, []).append((item.child_product_id, qty_decimal))

        # 親セットごとに日付別セット数と代表子を決定
        for parent_id, children in parent_children.items():
            # その親に紐づく日付一覧を抽出
            dates = set()
            for child_id, _ in children:
                for (pid, d), qty in plan_qty_map.items():
                    if pid == child_id and qty is not None:
                        dates.add(d)
            for plan_date in dates:
                max_set = None
                driver_id = None
                for child_id, qty_per in children:
                    if qty_per == 0:
                        continue
                    qty = plan_qty_map.get((child_id, plan_date))
                    if qty is None:
                        continue
                    try:
                        set_qty = qty / qty_per
                    except Exception:
                        continue
                    if max_set is None or set_qty > max_set:
                        max_set = set_qty
                    if qty > 0:
                        if driver_id is None or child_id < driver_id:
                            driver_id = child_id
                if max_set is not None:
                    copro_set_qty[(parent_id, plan_date)] = max_set
                if driver_id is None and children:
                    # 需要が0でも最小IDを代表として扱う
                    driver_id = min(c[0] for c in children)
                if driver_id is not None:
                    copro_driver[(parent_id, plan_date)] = driver_id

        # 標準BOMの数量マップ（親→子の使用数量／有効期間）を構築
        # 全BOM（非連産品）から数量マップを構築（多段BOMに対応）
        bom_qty_map = defaultdict(list)
        normal_boms = BOM.objects.filter(
            is_active=True,
            is_coproduct=False,
        ).order_by('-valid_from', '-id').prefetch_related('items')
        for bom in normal_boms:
            for item in bom.items.all():
                try:
                    qty_decimal = Decimal(item.quantity)
                except Exception:
                    continue
                if qty_decimal == 0:
                    continue
                bom_qty_map[bom.parent_product_id].append({
                    'child_id': item.child_product_id,
                    'qty': qty_decimal,
                    'valid_from': bom.valid_from,
                    'valid_to': bom.valid_to,
                })

        def find_bom_multiplier(parent_id, target_id, plan_date, visited=None):
            """
            多段BOMを辿って parent_id -> ... -> target_id の数量倍率を返す。
            見つからない場合はNone。
            """
            if parent_id == target_id:
                return Decimal('1')
            if visited is None:
                visited = set()
            key = (parent_id, target_id)
            if key in visited:
                return None
            visited.add(key)
            for ent in bom_qty_map.get(parent_id, []):
                if plan_date < ent['valid_from']:
                    continue
                if ent['valid_to'] and plan_date > ent['valid_to']:
                    continue
                if ent['child_id'] == target_id:
                    return ent['qty']
                sub = find_bom_multiplier(ent['child_id'], target_id, plan_date, visited)
                if sub is not None:
                    try:
                        return ent['qty'] * sub
                    except Exception:
                        return None
            return None

        # ラインに紐づくカレンダがあれば使用、無ければdaisoを使用
        line_obj = Line.objects.filter(id=line_id).first()
        calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(calendar_code='daiso').values_list('id', flat=True).first()
        calendar_work_map = {}
        if calendar_id:
            cal_qs = CalendarDay.objects.filter(
                calendar_id=calendar_id,
                target_date__gte=start_date,
                target_date__lte=end_date
            )
            for c in cal_qs:
                calendar_work_map[c.target_date] = c.work_minutes

        def shift_business_days(target_date, days):
            if not days:
                return target_date
            if not calendar_id:
                return target_date + timedelta(days=-days)
            step = -1 if days > 0 else 1
            remaining = abs(int(days))
            current = target_date
            while remaining > 0:
                current = current + timedelta(days=step)
                cal = CalendarDay.objects.filter(calendar_id=calendar_id, target_date=current).first()
                is_work = cal.is_working_day if cal is not None else True
                if is_work:
                    remaining -= 1
            return current

        # 対象ラインのRoutingStepを製品別にグルーピング
        steps_map = defaultdict(list)
        steps_qs = RoutingStep.objects.filter(line_id=line_id).select_related('routing', 'output_product', 'process')
        process_ids = set()
        cycle_product_ids = set(p['product_id'] for p in base_plans)
        for step in steps_qs:
            product_keys = []
            if step.output_product_id:
                product_keys.append(step.output_product_id)
            if step.routing_id and step.routing.product_id:
                product_keys.append(step.routing.product_id)
            process_ids.add(step.process_id)
            if step.output_product_id:
                cycle_product_ids.add(step.output_product_id)
            if step.routing_id and step.routing.product_id:
                cycle_product_ids.add(step.routing.product_id)
            for pid in set(product_keys):
                steps_map[pid].append(step)

        # サイクルタイムをまとめて取得（ライン特定優先、なければライン指定なしを使用）
        cycle_time_map = defaultdict(list)
        if process_ids and cycle_product_ids:
            ct_qs = ProcessCycleTime.objects.filter(
                process_id__in=process_ids,
                product_id__in=cycle_product_ids,
                is_active=True,
            ).filter(Q(line_id=line_id) | Q(line__isnull=True))
            for ct in ct_qs:
                cycle_time_map[(ct.product_id, ct.process_id)].append(ct)

        def pick_cycle_time(product_id, process_id, plan_date):
            candidates = cycle_time_map.get((product_id, process_id), [])
            best = None
            for ct in candidates:
                if ct.valid_from and plan_date < ct.valid_from:
                    continue
                if ct.valid_to and plan_date > ct.valid_to:
                    continue
                if best is None:
                    best = ct
                    continue
                # ライン指定がある方を優先
                if best.line_id is None and ct.line_id == line_id:
                    best = ct
            return best

        created = 0
        updated = 0
        skipped = []
        upserted = []

        # 影響範囲（変更された計画に対応するライン内工程）を削除してから再作成する
        if isinstance(items, list) and items and not read_only:
            affected_keys = set()
            for plan in base_plans:
                product_id = plan['product_id']
                plan_date = plan['plan_date']
                sequence_no = plan.get('sequence_no')
                seq_key = sequence_no if sequence_no is not None else 1
                steps = steps_map.get(product_id, [])
                if not steps:
                    continue
                for step in sorted(steps, key=lambda s: s.step_no or 0):
                    target_date = shift_business_days(plan_date, step.lead_time_days or 0)
                    target_product_id = step.output_product_id or product_id

                    copro_info_target = copro_child_map.get(target_product_id)
                    child_target_product_id = None
                    if copro_info_target:
                        if include_coproduct_children:
                            child_target_product_id = target_product_id
                        target_product_id = copro_info_target['parent_id']

                    affected_keys.add((target_product_id, step.process_id, target_date, seq_key))
                    if child_target_product_id and child_target_product_id != target_product_id:
                        affected_keys.add((child_target_product_id, step.process_id, target_date, seq_key))

            if affected_keys:
                q_filter = Q()
                for product_id, process_id, plan_date, seq_key in affected_keys:
                    q_filter |= Q(
                        plan_date=plan_date,
                        process_id=process_id,
                        product_id=product_id,
                        line_id=line_id,
                        sequence_no=seq_key,
                    )
                LineBacklog.objects.filter(q_filter).delete()

        # 集計結果を保持（共用部品の加算に対応）
        aggregated = {}

        for plan in base_plans:
            product_id = plan['product_id']
            plan_date = plan['plan_date']
            raw_plan_qty = plan['plan_qty']
            plan_qty = raw_plan_qty
            order_qty = plan['order_qty']
            demand_qty_plan = plan['demand_qty_plan']
            sequence_no = plan.get('sequence_no')
            parent_plan_id = plan.get('plan_id')  # 親（ライン最終品）のplan_id
            seq_key = sequence_no if sequence_no is not None else 1
            seen_target_keys = set() if auto_plan_mode else None

            steps = steps_map.get(product_id, [])
            if not steps:
                skipped.append({'product_id': product_id, 'plan_date': plan_date, 'reason': 'RoutingStep not found on line'})
                continue

            for step in sorted(steps, key=lambda s: s.step_no or 0):
                # ライン最終品の場合はLTシフトしない（計画日＝完成日）
                lt_days = step.lead_time_days or 0
                if step.output_product and step.output_product.is_line_final_product:
                    lt_days = 0
                target_date = shift_business_days(plan_date, lt_days)
                target_product_id = step.output_product_id or product_id
                plan_qty_step = plan_qty
                order_qty_step = order_qty
                demand_qty_step = demand_qty_plan

                # 連産品の子製品の場合、親製品に置き換える
                original_target_product_id = target_product_id
                copro_info_target = copro_child_map.get(target_product_id)
                child_target_product_id = None
                child_plan_qty = raw_plan_qty
                if copro_info_target:
                    if include_coproduct_children:
                        child_target_product_id = original_target_product_id
                    # 子製品を親製品に置き換え
                    target_product_id = copro_info_target['parent_id']

                # 連産品（コプロダクト）の場合、セット数ベースで工数を計算
                time_qty = plan_qty_step
                is_copro_driver = True

                if copro_info_target:
                    copro_key = (copro_info_target['parent_id'], plan_date)
                    set_qty = copro_set_qty.get(copro_key)
                    if set_qty is not None:
                        time_qty = set_qty
                        plan_qty_step = set_qty
                    driver_id = copro_driver.get(copro_key)
                    # 代表child以外は工数0として扱い、重複計上を防ぐ
                    is_copro_driver = driver_id in (None, original_target_product_id, product_id)

                # 標準BOMの数量を掛けて「二個使い」などを反映
                # 連産品置き換え時（copro）は別ロジックで処理するため除外
                qty_multiplier = Decimal('1')
                if not copro_info_target and target_product_id != product_id:
                    # 多段BOMを遡って数量を算出（親=ライン最終品）
                    multiplier = find_bom_multiplier(product_id, target_product_id, plan_date)
                    if multiplier is not None:
                        qty_multiplier = multiplier
                plan_qty_step = plan_qty_step * qty_multiplier
                time_qty = time_qty * qty_multiplier
                order_qty_step = order_qty_step * qty_multiplier
                demand_qty_step = demand_qty_step * qty_multiplier
                child_plan_qty = child_plan_qty * qty_multiplier

                computed_time_min = None
                # サイクルタイム取得は元の製品IDで行う
                ct = pick_cycle_time(original_target_product_id, step.process_id, target_date)
                if not ct and step.routing_id and step.routing.product_id and step.routing.product_id != original_target_product_id:
                    ct = pick_cycle_time(step.routing.product_id, step.process_id, target_date)
                if not ct and product_id != original_target_product_id:
                    ct = pick_cycle_time(product_id, step.process_id, target_date)

                if step.process and step.process.management_unit == 'MINUTE':
                    if ct:
                        try:
                            total_min = (Decimal(time_qty) * Decimal(ct.cycle_time_min or 0)) + Decimal(ct.setup_time_min or 0)
                            computed_time_min = float(total_min)
                        except Exception:
                            computed_time_min = None
                    elif step.time_unit == 'MINUTE' and step.duration_min is not None:
                        # サイクルタイム未設定時はRoutingStepのduration_minを1個当たり時間として使用
                        try:
                            total_min = Decimal(time_qty) * Decimal(step.duration_min or 0)
                            computed_time_min = float(total_min)
                        except Exception:
                            computed_time_min = None

                if not is_copro_driver:
                    computed_time_min = 0

                def add_aggregate(target_id, qty_value, time_value, ord_qty_value, dem_qty_value):
                    key = (target_id, step.process_id, target_date, seq_key)
                    entry = aggregated.get(key)
                    if not entry:
                        entry = {
                            'plan_qty': Decimal('0'),
                            'order_qty': Decimal('0'),
                            'demand_qty_plan': Decimal('0'),
                            'time_min': Decimal('0'),
                            'plan_ids': set(),
                            'step': step,
                            'cycle_time': ct,
                            'routing_product_id': step.routing.product_id if step.routing_id and step.routing else None,
                        }
                        aggregated[key] = entry
                    entry['plan_qty'] += Decimal(qty_value or 0)
                    entry['order_qty'] += Decimal(ord_qty_value or 0)
                    entry['demand_qty_plan'] += Decimal(dem_qty_value or 0)
                    if time_value is not None:
                        entry['time_min'] += Decimal(str(time_value))
                    if parent_plan_id:
                        entry['plan_ids'].add(parent_plan_id)

                main_key = (target_product_id, step.process_id, target_date, seq_key)
                if auto_plan_mode:
                    if main_key in seen_target_keys:
                        continue
                    seen_target_keys.add(main_key)
                add_aggregate(target_product_id, plan_qty_step, computed_time_min, order_qty_step, demand_qty_step)

                if child_target_product_id and child_target_product_id != target_product_id:
                    child_key = (child_target_product_id, step.process_id, target_date, seq_key)
                    if auto_plan_mode:
                        if child_key in seen_target_keys:
                            continue
                        seen_target_keys.add(child_key)
                    add_aggregate(child_target_product_id, child_plan_qty, 0, order_qty_step, demand_qty_step)

        for (target_id, process_id, target_date, seq_key), entry in aggregated.items():
            plan_qty_value = int(entry['plan_qty'])
            order_qty_value = int(entry['order_qty'])
            demand_qty_value = int(entry['demand_qty_plan'])
            plan_ids = entry['plan_ids']
            plan_id_value = None
            if len(plan_ids) == 1:
                plan_id_value = next(iter(plan_ids))

            if read_only:
                obj = LineBacklog.objects.filter(
                    plan_date=target_date,
                    process_id=process_id,
                    product_id=target_id,
                    line_id=line_id,
                    sequence_no=seq_key,
                ).first()

                if not obj:
                    obj = LineBacklog(
                        plan_date=target_date,
                        process_id=process_id,
                        product_id=target_id,
                        line_id=line_id,
                        plan_qty=plan_qty_value,
                        order_qty=order_qty_value,
                        demand_qty_plan=demand_qty_value,
                        source_line_id=line_id,
                        source_routing_step_id=entry['step'].id,
                        sequence_no=seq_key,
                    )
            else:
                defaults_dict = {
                    'order_qty': order_qty_value,
                    'demand_qty_plan': demand_qty_value,
                    'source_line_id': line_id,
                    'source_routing_step_id': entry['step'].id,
                    'plan_qty': plan_qty_value,
                    'sequence_no': seq_key,
                }
                if plan_id_value:
                    defaults_dict['plan_id'] = plan_id_value
                else:
                    defaults_dict['plan_id'] = None

                obj, is_created = LineBacklog.objects.update_or_create(
                    plan_date=target_date,
                    process_id=process_id,
                    product_id=target_id,
                    line_id=line_id,
                    sequence_no=seq_key,
                    defaults=defaults_dict
                )
                created += 1 if is_created else 0
                updated += 0 if is_created else 1

            obj.computed_time_min = float(entry['time_min']) if entry['time_min'] is not None else None
            obj.work_minutes = calendar_work_map.get(target_date)
            obj.step_no = entry['step'].step_no
            obj.cycle_time_min = float(entry['cycle_time'].cycle_time_min) if entry['cycle_time'] and entry['cycle_time'].cycle_time_min else None
            obj.routing_product_id = entry['routing_product_id']
            upserted.append(obj)

        serializer = self.get_serializer(upserted, many=True)
        return Response({
            'items': serializer.data,
            'created': created,
            'updated': updated,
            'skipped': skipped,
        })

    @action(detail=False, methods=['post'])
    def save(self, request):
        """
        ユーザーが入力した計画データをLineBacklogに保存する
        期待payload: { line_id, items: [{product_id, process_id, plan_date, plan_qty?, actual_qty?, stock_qty?, planned_stock_qty?, adjust_qty?, sequence_no?}] }

        plan_id ロジック:
        - plan_id = 製品コード_日付_数量_順番
        - 数量が変更されるとplan_idが変わるため、古いplan_idのレコードを削除
        - plan_qty=0の場合もplan_idに紐づくレコードを削除
        """
        line_id = request.data.get('line_id')
        items = request.data.get('items', [])
        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(items, list) or not items:
            return Response({'detail': 'items is required'}, status=status.HTTP_400_BAD_REQUEST)

        created = 0
        updated = 0
        deleted = 0
        skipped = []
        change_reason = request.data.get('change_reason')
        if isinstance(change_reason, str):
            change_reason = change_reason.strip()
        if not change_reason:
            change_reason = None

        # まず、製品コードを取得するために製品IDから製品情報を取得
        from masters.models import Product
        product_cache = {}
        plan_date_cache = {}
        change_user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

        def parse_plan_date(raw_date):
            if raw_date in plan_date_cache:
                return plan_date_cache[raw_date]
            if isinstance(raw_date, str):
                parsed = datetime.strptime(raw_date, '%Y-%m-%d').date()
            else:
                parsed = raw_date
            plan_date_cache[raw_date] = parsed
            return parsed

        def record_change(plan_date_value, product_id, process_id, line_id, before_qty, after_qty, plan_id_value, sequence_no_value):
            if not change_reason:
                return
            if before_qty == after_qty:
                return
            from purchase.models import PurchasePlanChangeLog
            PurchasePlanChangeLog.objects.create(
                plan_date=plan_date_value,
                product_id=product_id,
                process_id=process_id,
                line_id=line_id,
                sequence_no=sequence_no_value,
                plan_id=plan_id_value,
                before_qty=before_qty,
                after_qty=after_qty,
                reason=change_reason,
                changed_by=change_user,
            )

        for it in items:
            try:
                product_id = it.get('product_id')
                process_id = it.get('process_id')
                plan_date = it.get('plan_date')
                if not product_id or not process_id or not plan_date:
                    skipped.append({'item': it, 'reason': 'product_id/process_id/plan_date required'})
                    continue

                # 製品情報を取得（キャッシュを使用）
                if product_id not in product_cache:
                    try:
                        product = Product.objects.get(id=product_id)
                        product_cache[product_id] = product
                    except Product.DoesNotExist:
                        skipped.append({'item': it, 'reason': 'product not found'})
                        continue
                product = product_cache[product_id]
                product_code = product.product_code

                # plan_qty=0 の場合、plan_idに紐づくレコードを削除
                plan_qty_provided = 'plan_qty' in it
                plan_qty_value = None
                existing_plan_qty = 0
                existing_plan_id = None
                existing_sequence_no = None
                if plan_qty_provided:
                    plan_qty_value = Decimal(str(it['plan_qty'] or 0))
                    if plan_qty_value == 0:
                        # 既存レコードを取得（sequence_noで絞り込み）
                        _seq_for_zero = it.get('sequence_no') if it.get('sequence_no') is not None else 0
                        existing = LineBacklog.objects.filter(
                            plan_date=plan_date,
                            process_id=process_id,
                            product_id=product_id,
                            line_id=line_id,
                            sequence_no=_seq_for_zero,
                        ).first()

                        if existing and existing.plan_id:
                            existing_plan_qty = int(existing.plan_qty or 0)
                            existing_plan_id = existing.plan_id
                            existing_sequence_no = existing.sequence_no
                            ProductionOrder.objects.filter(order_no=existing.plan_id).delete()
                            # plan_idに紐づく全てのLineBacklogレコードを削除
                            deleted_count = LineBacklog.objects.filter(plan_id=existing.plan_id).delete()[0]
                            deleted += deleted_count
                            record_change(
                                parse_plan_date(plan_date),
                                product_id,
                                process_id,
                                line_id,
                                existing_plan_qty,
                                0,
                                existing_plan_id,
                                existing_sequence_no,
                            )
                            continue
                        elif existing:
                            existing_plan_qty = int(existing.plan_qty or 0)
                            existing_plan_id = existing.plan_id
                            existing_sequence_no = existing.sequence_no
                            # plan_idが無い場合は従来のロジック
                            def resolve_qty(field_name):
                                if field_name in it:
                                    return Decimal(str(it[field_name] or 0))
                                return Decimal(str(getattr(existing, field_name, 0) or 0))

                            actual_qty = resolve_qty('actual_qty')
                            stock_qty = resolve_qty('stock_qty')
                            planned_stock_qty = resolve_qty('planned_stock_qty')
                            adjust_qty = resolve_qty('adjust_qty')
                            order_qty = Decimal(str(existing.order_qty or 0))
                            demand_qty_plan = Decimal(str(existing.demand_qty_plan or 0))
                            seq_in = it.get('sequence_no', existing.sequence_no)
                            seq_val = 0 if seq_in is None else seq_in

                            if (
                                actual_qty == 0
                                and stock_qty == 0
                                and planned_stock_qty == 0
                                and adjust_qty == 0
                                and order_qty == 0
                                and demand_qty_plan == 0
                                and seq_val in (0, None, '')
                            ):
                                existing.delete()
                                deleted += 1
                                record_change(
                                    parse_plan_date(plan_date),
                                    product_id,
                                    process_id,
                                    line_id,
                                    existing_plan_qty,
                                    0,
                                    existing_plan_id,
                                    existing_sequence_no,
                                )
                                continue

                # sequence_noを取得（デフォルトは0）
                sequence_no = it.get('sequence_no')
                if sequence_no is None:
                    sequence_no = 0

                # 既存レコードを取得（sequence_noで絞り込み）
                existing = LineBacklog.objects.filter(
                    plan_date=plan_date,
                    process_id=process_id,
                    product_id=product_id,
                    line_id=line_id,
                    sequence_no=sequence_no,
                ).first()
                if existing:
                    existing_plan_qty = int(existing.plan_qty or 0)
                    existing_plan_id = existing.plan_id
                    existing_sequence_no = existing.sequence_no

                new_plan_id = None
                plan_date_obj = None
                if plan_qty_provided:
                    # plan_idを生成: 製品コード_YYYYMMDD_数量_順番
                    # gantt_planning.pyと同じフォーマットを使用
                    plan_date_obj = parse_plan_date(plan_date)

                    # 数量ラベルを生成（小数点以下の0を除去、小数点を'p'に変換）
                    qty_label = str(plan_qty_value).rstrip('0').rstrip('.')
                    if '.' in qty_label:
                        qty_label = qty_label.replace('.', 'p')

                    new_plan_id = f"{product_code}_{plan_date_obj.strftime('%Y%m%d')}_{qty_label}_{sequence_no}"

                    # 既存レコードがあり、plan_idが変更された場合、古いplan_idのレコードを削除
                    if existing and existing.plan_id and existing.plan_id != new_plan_id:
                        # 古いplan_idに紐づく全てのLineBacklogレコードを削除
                        old_plan_id = existing.plan_id
                        LineBacklog.objects.filter(plan_id=old_plan_id).delete()
                        ProductionOrder.objects.filter(order_no=old_plan_id).delete()
                        # existingは削除されたので、新規作成扱いになる
                        existing = None

                # 更新するフィールドを準備
                defaults = {}
                if plan_qty_provided:
                    defaults['plan_id'] = new_plan_id
                    defaults['plan_qty'] = plan_qty_value
                if 'actual_qty' in it:
                    defaults['actual_qty'] = Decimal(str(it['actual_qty']))
                if 'stock_qty' in it:
                    defaults['stock_qty'] = Decimal(str(it['stock_qty']))
                if 'planned_stock_qty' in it:
                    defaults['planned_stock_qty'] = Decimal(str(it['planned_stock_qty']))
                if 'adjust_qty' in it:
                    defaults['adjust_qty'] = Decimal(str(it['adjust_qty']))
                if 'sequence_no' in it:
                    defaults['sequence_no'] = sequence_no

                # LineBacklogに保存（sequence_noを検索条件に含める）
                defaults.pop('sequence_no', None)
                obj, is_created = LineBacklog.objects.update_or_create(
                    plan_date=plan_date,
                    process_id=process_id,
                    product_id=product_id,
                    line_id=line_id,
                    sequence_no=sequence_no,
                    defaults=defaults
                )
                if is_created:
                    created += 1
                else:
                    updated += 1

                if plan_qty_provided and plan_qty_value is not None:
                    after_qty = int(plan_qty_value)
                    record_change(
                        plan_date_obj or parse_plan_date(plan_date),
                        product_id,
                        process_id,
                        line_id,
                        existing_plan_qty,
                        after_qty,
                        new_plan_id or existing_plan_id,
                        sequence_no if 'sequence_no' in it or sequence_no is not None else existing_sequence_no,
                    )

                if plan_qty_provided and plan_qty_value is not None and plan_qty_value > 0 and new_plan_id:
                    routing = Routing.objects.filter(product_id=product_id, is_active=True).order_by('-is_default', 'id').first()
                    ProductionOrder.objects.update_or_create(
                        order_no=new_plan_id,
                        defaults={
                            'product_id': product_id,
                            'routing_id': routing.id if routing else None,
                            'line_id': line_id,
                            'order_qty': plan_qty_value,
                            'scheduled_start_date': plan_date_obj,
                            'scheduled_end_date': plan_date_obj,
                            'priority': sequence_no or 0,
                        }
                    )
            except Exception as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'created': created, 'updated': updated, 'deleted': deleted, 'skipped': skipped})

    def _parse_stocktake_file(self, upload_file):
        """
        棚卸ファイル（xlsx/csv）を読み込み、品番ごとの数量に集約する。
        期待列: 製品番号, 製品名(任意), 数量
        """
        filename = (upload_file.name or '').lower()
        aggregated = {}
        row_count = 0

        def parse_qty(raw_value, row_no):
            text = '' if raw_value is None else str(raw_value).strip()
            if text == '':
                raise ValueError(f'数量が未入力です (行={row_no})')
            text = text.replace(',', '')
            try:
                qty = Decimal(text)
            except InvalidOperation:
                raise ValueError(f'数量が不正です: "{raw_value}" (行={row_no})')
            if qty < 0:
                raise ValueError(f'数量は0以上にしてください (行={row_no})')
            return qty

        def add_row(product_code, qty, row_no):
            if product_code is None:
                raise ValueError(f'製品番号が未入力です (行={row_no})')
            # Excelが数値型で読み込んだ場合の対応（26.0 → "26"）
            if isinstance(product_code, float) and product_code == int(product_code):
                code = str(int(product_code))
            else:
                code = str(product_code).strip()
            if not code:
                raise ValueError(f'製品番号が未入力です (行={row_no})')
            aggregated[code] = aggregated.get(code, Decimal('0')) + qty

        if filename.endswith('.xlsx'):
            from openpyxl import load_workbook

            wb = load_workbook(upload_file, data_only=True, read_only=True)
            ws = wb.active
            header = [str(v).strip() if v is not None else '' for v in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
            try:
                product_col = header.index('製品番号')
                qty_col = header.index('数量')
            except ValueError:
                raise ValueError('ヘッダーに「製品番号」「数量」列が必要です')

            for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                product_val = row[product_col] if product_col < len(row) else None
                qty_val = row[qty_col] if qty_col < len(row) else None
                if product_val in [None, ''] and qty_val in [None, '']:
                    continue
                qty = parse_qty(qty_val, idx)
                add_row(product_val, qty, idx)
                row_count += 1

        elif filename.endswith('.csv'):
            raw = upload_file.read()
            try:
                text = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = raw.decode('cp932')
            reader = csv.DictReader(io.StringIO(text))
            if not reader.fieldnames:
                raise ValueError('CSVヘッダーがありません')
            names = {name.strip() for name in reader.fieldnames if name}
            if '製品番号' not in names or '数量' not in names:
                raise ValueError('CSVヘッダーに「製品番号」「数量」列が必要です')

            for idx, row in enumerate(reader, start=2):
                product_val = row.get('製品番号')
                qty_val = row.get('数量')
                if (product_val is None or str(product_val).strip() == '') and (qty_val is None or str(qty_val).strip() == ''):
                    continue
                qty = parse_qty(qty_val, idx)
                add_row(product_val, qty, idx)
                row_count += 1
        else:
            raise ValueError('.xlsx または .csv ファイルを指定してください')

        if not aggregated:
            raise ValueError('棚卸データが見つかりません')

        return {
            'row_count': row_count,
            'rows': aggregated,
        }

    @action(detail=False, methods=['get'])
    def download_stocktake_template(self, request):
        """
        棚卸取込用テンプレートExcelを返す。
        """
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = 'stocktake'
        ws.append(['製品番号', '製品名', '数量'])
        ws.append(['ABC-001', 'サンプル製品A', 1500])
        ws.append(['ABC-002', 'サンプル製品B', 800.5])
        ws.append(['DEF-003', 'サンプル製品C', 0])

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="stocktake_template.xlsx"'
        return response

    @action(
        detail=False,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_stocktake_excel(self, request):
        """
        棚卸Excel/CSVを取り込み、在庫初期値を反映する。

        期待payload:
        - file: xlsx/csv
        - stocktake_date: YYYY-MM-DD
        """
        from .inventory.stocktake_initializer import (
            get_progress_upper_bound_date,
            _collect_stocktake_mapping_keys,
        )

        upload_file = request.FILES.get('file')
        stocktake_date_raw = request.data.get('stocktake_date')
        location = (request.data.get('location') or 'MAIN').strip() or 'MAIN'

        if not upload_file:
            return Response({'detail': 'file is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not stocktake_date_raw:
            return Response({'detail': 'stocktake_date is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            stocktake_date = datetime.strptime(str(stocktake_date_raw), '%Y-%m-%d').date()
        except ValueError as e:
            return Response({'detail': f'Invalid stocktake_date format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            parsed = self._parse_stocktake_file(upload_file)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        product_codes = list(parsed['rows'].keys())
        products = Product.objects.filter(product_code__in=product_codes).values('id', 'product_code')
        product_id_by_code = {p['product_code']: p['id'] for p in products}
        product_code_by_id = {pid: code for code, pid in product_id_by_code.items()}
        missing_codes = sorted([c for c in product_codes if c not in product_id_by_code])
        if missing_codes:
            return Response(
                {'detail': 'unknown product_code found', 'missing_product_codes': missing_codes},
                status=status.HTTP_400_BAD_REQUEST,
            )

        upper_bound_date = get_progress_upper_bound_date()
        baseline_date = stocktake_date

        allocation_created = 0
        allocation_updated = 0
        backlog_created = 0
        backlog_updated = 0

        try:
            with transaction.atomic():
                # 1) t_stock_allocation へ反映（MAIN固定）
                for code, qty in parsed['rows'].items():
                    product_id = product_id_by_code[code]
                    obj, created = StockAllocation.objects.get_or_create(
                        product_id=product_id,
                        location=location,
                        defaults={
                            'current_stock': qty,
                            'reserved_qty': Decimal('0'),
                            'min_stock_qty': 0,
                            'is_bottleneck': False,
                        }
                    )
                    if created:
                        allocation_created += 1
                    else:
                        obj.current_stock = qty
                        obj.reserved_qty = Decimal('0')
                        obj.save(update_fields=['current_stock', 'reserved_qty', 'updated_at'])
                        allocation_updated += 1

                # 2) line_backlog (sequence_no=0) へ棚卸在庫を反映
                target_product_ids = list(product_id_by_code.values())
                unique_keys, mapped_product_ids = _collect_stocktake_mapping_keys(
                    baseline_date,
                    target_product_ids,
                )

                for process_id, product_id, line_id in unique_keys:
                    # line_backlog はint管理のため、小数は切り捨てで保持
                    product_code = product_code_by_id.get(product_id)
                    stock_int = int(parsed['rows'][product_code]) if product_code else 0
                    obj, created = LineBacklog.objects.get_or_create(
                        plan_date=baseline_date,
                        process_id=process_id,
                        product_id=product_id,
                        line_id=line_id,
                        sequence_no=0,
                        defaults={
                            'demand_qty_plan': 0,
                            'order_qty': 0,
                            'plan_qty': 0,
                            'actual_qty': 0,
                            'stock_qty': stock_int,
                            'planned_stock_qty': 0,
                            'adjust_qty': 0,
                            'scrap_adjust_qty': 0,
                            'scrap_qty': 0,
                            'actual_shipment_qty': 0,
                            'progress_qty': 0,
                            'planned_progress_qty': 0,
                            'is_stocktake_fix': True,  # 棚卸確定フラグON
                        },
                    )
                    if created:
                        backlog_created += 1
                    else:
                        obj.stock_qty = stock_int
                        # planned_stock_qty は Step2(initialize_stocktake) で計算する。
                        # Step1(取込)では値を確定させないため0を保持する。
                        obj.planned_stock_qty = 0
                        obj.progress_qty = 0
                        obj.planned_progress_qty = 0
                        obj.is_stocktake_fix = True
                        obj.save(update_fields=['stock_qty', 'planned_stock_qty', 'progress_qty', 'planned_progress_qty', 'is_stocktake_fix', 'updated_at'])
                        backlog_updated += 1
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        unmapped_product_codes = sorted([
            code for code, pid in product_id_by_code.items() if pid not in mapped_product_ids
        ])

        return Response({
            'detail': 'Stocktake file imported successfully',
            'stocktake_date': stocktake_date.isoformat(),
            'baseline_date': baseline_date.isoformat(),
            'upper_bound_date': upper_bound_date.isoformat(),
            'location': location,
            'loaded_rows': parsed['row_count'],
            'product_count': len(product_codes),
            'allocation_created': allocation_created,
            'allocation_updated': allocation_updated,
            'backlog_created': backlog_created,
            'backlog_updated': backlog_updated,
            'unmapped_product_codes': unmapped_product_codes,
        })

    @action(detail=False, methods=['post'])
    def initialize_stocktake(self, request):
        """
        棚卸初期化（在庫/計画在庫/進度）を一括実行する。

        期待payload:
        - stocktake_date: YYYY-MM-DD
        - end_date: YYYY-MM-DD
        """
        from .inventory.stocktake_initializer import (
            initialize_progress_from_stocktake,
            initialize_planned_stock,
            ensure_stocktake_backlogs,
            get_progress_upper_bound_date,
            recalculate_progress_from_stocktake,
            recalculate_inventory_from_stocktake,
        )

        stocktake_date_raw = request.data.get('stocktake_date')
        end_date_raw = request.data.get('end_date')
        if not stocktake_date_raw:
            return Response({'detail': 'stocktake_date is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not end_date_raw:
            return Response({'detail': 'end_date is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            stocktake_dt = datetime.strptime(str(stocktake_date_raw), '%Y-%m-%d').date()
            end_dt = datetime.strptime(str(end_date_raw), '%Y-%m-%d').date()
        except ValueError as e:
            return Response({'detail': f'Invalid date format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        baseline_dt = stocktake_dt
        upper_bound = get_progress_upper_bound_date()

        if end_dt < baseline_dt:
            return Response(
                {'detail': 'end_date must be on or after resolved baseline_date'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            baseline_result = ensure_stocktake_backlogs(baseline_dt)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        line_ids = list(LineBacklog.objects.filter(
            plan_date__gte=baseline_dt,
            plan_date__lte=end_dt,
        ).values_list('line_id', flat=True).distinct())

        if not line_ids:
            return Response(
                {'detail': 'line_backlog rows not found in calculation range'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # 1. 計画在庫の初期値を正しく計算してセットする（専用ロジック）
            # stock_qty - パイプライン需要
            initialize_planned_stock(line_ids, baseline_dt)

            # 2. 棚卸専用の再計算（基準日以降）
            # 通常計算の「前々営業日以前スキップ」を使わず、棚卸日を起点に連鎖計算する。
            for line_id in line_ids:
                # 進度は棚卸初期化ロジックで別計算するため、ここでは在庫・計画在庫のみ再計算
                recalculate_inventory_from_stocktake(line_id, baseline_dt, end_dt)
            
            # 3. 進度の初期化（専用ロジック）
            progress_result = initialize_progress_from_stocktake(baseline_dt)
            progress_recalc_results = []
            for line_id in line_ids:
                progress_recalc_results.append(
                    recalculate_progress_from_stocktake(line_id, baseline_dt, end_dt)
                )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'detail': 'Stocktake initialization completed',
            'stocktake_date': stocktake_dt.isoformat(),
            'baseline_date': baseline_dt.isoformat(),
            'upper_bound_date': upper_bound.isoformat(),
            'end_date': end_dt.isoformat(),
            'line_count': len(line_ids),
            'baseline_backlog_created': baseline_result.get('backlog_created', 0),
            'baseline_backlog_updated': baseline_result.get('backlog_updated', 0),
            'baseline_unmapped_product_codes': baseline_result.get('unmapped_product_codes', []),
            'progress_recalc_line_count': len(progress_recalc_results),
            'progress_recalc_product_count': sum(r.get('product_count', 0) for r in progress_recalc_results),
            **progress_result,
        })

    @action(detail=False, methods=['post'])
    def recalculate_inventory(self, request):
        """
        在庫・計画在庫を再計算するAPI

        期待payload: {
            line_id: int (required),
            start_date: str (YYYY-MM-DD, required),
            end_date: str (YYYY-MM-DD, required),
            include_progress: bool (optional, default: True),
            line_final_only: bool (optional, default: False) - Trueの場合はライン最終品のみ計算
            final_only: bool (deprecated, line_final_only を使用) - 後方互換のため残存
        }
        """
        from .inventory.inventory_calculator import recalculate_inventory_for_line

        line_id = request.data.get('line_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        include_progress_raw = request.data.get('include_progress', True)
        if isinstance(include_progress_raw, str):
            include_progress = include_progress_raw.lower() not in ['false', '0', 'no']
        else:
            include_progress = bool(include_progress_raw)

        # line_final_only を優先、未指定なら final_only（後方互換）を参照
        line_final_only_raw = request.data.get('line_final_only')
        if line_final_only_raw is None:
            line_final_only_raw = request.data.get('final_only', False)
        if isinstance(line_final_only_raw, str):
            line_final_only = line_final_only_raw.lower() in ['true', '1', 'yes']
        else:
            line_final_only = bool(line_final_only_raw)

        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not start_date or not end_date:
            return Response({'detail': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from datetime import datetime
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError as e:
            return Response({'detail': f'Invalid date format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            recalculate_inventory_for_line(line_id, start_dt, end_dt, include_progress=include_progress, line_final_only=line_final_only)
            return Response({'detail': 'Inventory recalculated successfully'})
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def initialize_progress(self, request):
        """
        棚卸在庫を起点に進度(progress_qty / planned_progress_qty)を初期化するAPI

        期待payload: {
            stocktake_date: str (YYYY-MM-DD, required)
            baseline_date: str (YYYY-MM-DD, optional)  # 明示指定時のみ使用
        }
        """
        from .inventory.stocktake_initializer import (
            initialize_progress_from_stocktake,
            resolve_progress_baseline_date,
        )

        stocktake_date_raw = request.data.get('stocktake_date')
        baseline_date_raw = request.data.get('baseline_date')
        if not stocktake_date_raw and not baseline_date_raw:
            return Response(
                {'detail': 'stocktake_date is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        stocktake_dt = None
        if stocktake_date_raw:
            try:
                stocktake_dt = datetime.strptime(str(stocktake_date_raw), '%Y-%m-%d').date()
            except ValueError as e:
                return Response({'detail': f'Invalid stocktake_date format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        if baseline_date_raw:
            try:
                baseline_dt = datetime.strptime(str(baseline_date_raw), '%Y-%m-%d').date()
            except ValueError as e:
                return Response({'detail': f'Invalid baseline_date format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
            upper_bound = None
        else:
            try:
                baseline_dt, upper_bound = resolve_progress_baseline_date(stocktake_dt)
            except ValueError as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = initialize_progress_from_stocktake(baseline_dt)
            response_payload = {
                'detail': 'Progress initialized successfully',
                'baseline_date': baseline_dt.isoformat(),
                **result,
            }
            if stocktake_dt:
                response_payload['stocktake_date'] = stocktake_dt.isoformat()
            if upper_bound:
                response_payload['upper_bound_date'] = upper_bound.isoformat()
            return Response(response_payload)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def recalculate_scrap(self, request):
        """
        仕損数（scrap_qty）を再集計するAPI

        期待payload: {
            line_id: int (required),
            start_date: str (YYYY-MM-DD, required),
            end_date: str (YYYY-MM-DD, required)
        }
        """
        from .inventory.inventory_calculator import aggregate_scrap_to_backlog

        line_id = request.data.get('line_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not start_date or not end_date:
            return Response({'detail': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from datetime import datetime
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError as e:
            return Response({'detail': f'Invalid date format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            aggregate_scrap_to_backlog(line_id, start_dt, end_dt)
            return Response({'detail': 'Scrap recalculated successfully'})
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LineGanttPlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LineGanttPlan.objects.all().select_related('line', 'product')
    serializer_class = LineGanttPlanSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = LineGanttPlanFilter
    ordering_fields = ['plan_date', 'line', 'product']
    ordering = ['plan_date', 'line']

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        ガント用ライン計画を生成して保存する。
        期待payload: { line_id, start_date, end_date, clear_existing?: bool, final_process_start_time?: str, adjust_to_break_end?: bool }
        """
        line_id = request.data.get('line_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        clear_existing = bool(request.data.get('clear_existing'))
        final_process_start_time = request.data.get('final_process_start_time')
        adjust_to_break_end = request.data.get('adjust_to_break_end', False)

        logger.info(
            'line_gantt_plans.generate: line_id=%s start=%s end=%s clear=%s final_time=%s adjust=%s',
            line_id, start_date, end_date, clear_existing, final_process_start_time, adjust_to_break_end
        )

        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not start_date or not end_date:
            return Response({'detail': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            line_id = int(line_id)
        except (TypeError, ValueError):
            return Response({'detail': 'line_id must be numeric'}, status=status.HTTP_400_BAD_REQUEST)

        plans = generate_line_gantt_plans(
            line_id,
            start_date,
            end_date,
            clear_existing=clear_existing,
            final_process_start_time=final_process_start_time,
            adjust_to_break_end=adjust_to_break_end
        )
        logger.info('line_gantt_plans.generate: plans=%s', len(plans))

        upserted = []
        for plan in plans:
            obj, _ = LineGanttPlan.objects.update_or_create(
                plan_id=plan['plan_id'],
                defaults={
                    'line_id': plan['line_id'],
                    'product_id': plan['product_id'],
                    'plan_date': plan['plan_date'],
                    'plan_qty': plan['plan_qty'],
                    'sequence_no': plan['sequence_no'],
                    'start_datetime': plan['start_datetime'],
                    'end_datetime': plan['end_datetime'],
                    'processes_plan': plan['processes_plan'],
                }
            )
            upserted.append(obj)

        if clear_existing:
            def parse_date(val):
                try:
                    return datetime.strptime(str(val), '%Y-%m-%d').date()
                except Exception:
                    return None

            start_dt = parse_date(start_date)
            end_dt = parse_date(end_date)
            qs = LineGanttPlan.objects.filter(line_id=line_id)
            if start_dt:
                qs = qs.filter(plan_date__gte=start_dt)
            if end_dt:
                qs = qs.filter(plan_date__lte=end_dt)
            plan_ids = [p['plan_id'] for p in plans]
            if plan_ids:
                qs = qs.exclude(plan_id__in=plan_ids)
            deleted_count, _ = qs.delete()
            logger.info('line_gantt_plans.generate: cleared=%s', deleted_count)

        serializer = self.get_serializer(upserted, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['put'], url_path='bulk-update')
    def bulk_update(self, request):
        """
        ガントのドラッグ調整結果を一括保存する。
        期待payload: [{ plan_id, process_id, output_product_id?, start_time?, end_time?, quantity? }, ...]
        """
        updates = request.data
        if not isinstance(updates, list) or not updates:
            return Response({'detail': 'updates must be a non-empty list'}, status=status.HTTP_400_BAD_REQUEST)

        updated_count = 0
        change_log_count = 0
        change_user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        change_reason = '工程ガント数量編集'
        for update in updates:
            plan_id = update.get('plan_id')
            process_id = update.get('process_id')
            if not plan_id or not process_id:
                continue
            try:
                process_id = int(process_id)
            except Exception:
                continue
            output_product_id = update.get('output_product_id')
            if output_product_id in [None, '']:
                output_product_id = None
            else:
                try:
                    output_product_id = int(output_product_id)
                except Exception:
                    output_product_id = None
            start_time = update.get('start_time')
            end_time = update.get('end_time')
            has_quantity = 'quantity' in update
            quantity_value = None
            quantity_int_value = None
            if has_quantity:
                try:
                    quantity_value = Decimal(str(update.get('quantity')))
                    if quantity_value <= 0:
                        has_quantity = False
                    else:
                        quantity_int_value = int(quantity_value.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
                except Exception:
                    has_quantity = False

            plan = LineGanttPlan.objects.filter(plan_id=plan_id).first()
            if not plan or not plan.processes_plan:
                continue

            processes_plan = list(plan.processes_plan)
            changed = False
            matched_output_product_id = None
            quantity_changed = False
            before_quantity_value = None
            for proc in processes_plan:
                if str(proc.get('process_id')) == str(process_id):
                    proc_output_product_id = proc.get('output_product_id')
                    if output_product_id is not None and str(proc_output_product_id) != str(output_product_id):
                        continue
                    matched_output_product_id = proc_output_product_id
                    if start_time:
                        proc['start_time'] = start_time
                        changed = True
                    if end_time:
                        proc['end_time'] = end_time
                        changed = True
                    if has_quantity and quantity_int_value is not None:
                        try:
                            before_qty = int(Decimal(str(proc.get('quantity') or 0)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
                        except Exception:
                            before_qty = 0
                        if before_qty != quantity_int_value:
                            proc['quantity'] = quantity_int_value
                            changed = True
                            quantity_changed = True
                            before_quantity_value = before_qty
                    if changed:
                        updated_count += 1
                    break

            if changed:
                starts = []
                ends = []
                for proc in processes_plan:
                    try:
                        starts.append(datetime.fromisoformat(proc['start_time']))
                        ends.append(datetime.fromisoformat(proc['end_time']))
                    except Exception:
                        continue
                if starts:
                    plan.start_datetime = min(starts)
                if ends:
                    plan.end_datetime = max(ends)
                plan.processes_plan = processes_plan
                plan.save()
                if quantity_changed and quantity_int_value is not None and matched_output_product_id:
                    try:
                        matched_output_product_id = int(matched_output_product_id)
                    except Exception:
                        matched_output_product_id = None
                if quantity_changed and quantity_int_value is not None and matched_output_product_id:
                    backlog_qs = LineBacklog.objects.filter(
                        line_id=plan.line_id,
                        process_id=process_id,
                        product_id=matched_output_product_id,
                        plan_id=plan_id,
                    )
                    backlog_rows = list(backlog_qs)
                    if backlog_rows:
                        backlog_qs.update(plan_qty=quantity_int_value)
                        for row in backlog_rows:
                            before_qty = int(row.plan_qty or 0)
                            if before_qty == quantity_int_value:
                                continue
                            ProductionPlanChangeLog.objects.create(
                                plan_date=row.plan_date,
                                product_id=row.product_id,
                                process_id=row.process_id,
                                line_id=row.line_id,
                                sequence_no=row.sequence_no,
                                plan_id=row.plan_id,
                                before_qty=before_qty,
                                after_qty=quantity_int_value,
                                reason=change_reason,
                                changed_by=change_user,
                            )
                            change_log_count += 1
                    elif before_quantity_value is not None:
                        ProductionPlanChangeLog.objects.create(
                            plan_date=plan.plan_date,
                            product_id=matched_output_product_id,
                            process_id=process_id,
                            line_id=plan.line_id,
                            sequence_no=plan.sequence_no,
                            plan_id=plan_id,
                            before_qty=before_quantity_value,
                            after_qty=quantity_int_value,
                            reason=change_reason,
                            changed_by=change_user,
                        )
                        change_log_count += 1

        return Response({'updated': updated_count, 'change_logs': change_log_count})


# ========================================
# 製造実行系ViewSet
# ========================================

class StockAllocationFilter(django_filters.FilterSet):
    """在庫引当フィルタ"""
    product_code = django_filters.CharFilter(field_name='product__product_code', lookup_expr='icontains')
    is_bottleneck = django_filters.BooleanFilter()
    location = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = StockAllocation
        fields = ['product', 'product_code', 'location', 'is_bottleneck']


class StockAllocationViewSet(viewsets.ModelViewSet):
    """在庫引当ViewSet"""
    queryset = StockAllocation.objects.all().select_related('product')
    serializer_class = StockAllocationSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = StockAllocationFilter
    search_fields = ['product__product_code', 'product__product_name', 'location']
    ordering_fields = ['current_stock', 'reserved_qty', 'min_stock_qty', 'updated_at']
    ordering = ['-updated_at']

    @action(detail=True, methods=['post'])
    def reserve(self, request, pk=None):
        """
        在庫引当
        payload: { quantity: Decimal }
        """
        allocation = self.get_object()
        qty = request.data.get('quantity')

        if not qty:
            return Response({'detail': 'quantity is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            qty = Decimal(str(qty))
            if qty <= 0:
                return Response({'detail': 'quantity must be positive'}, status=status.HTTP_400_BAD_REQUEST)

            if allocation.available_qty < qty:
                return Response({
                    'detail': f'Insufficient stock. Available: {allocation.available_qty}, Requested: {qty}'
                }, status=status.HTTP_400_BAD_REQUEST)

            allocation.reserved_qty += qty
            allocation.save()

            serializer = self.get_serializer(allocation)
            return Response(serializer.data)

        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """
        引当解除
        payload: { quantity: Decimal }
        """
        allocation = self.get_object()
        qty = request.data.get('quantity')

        if not qty:
            return Response({'detail': 'quantity is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            qty = Decimal(str(qty))
            if qty <= 0:
                return Response({'detail': 'quantity must be positive'}, status=status.HTTP_400_BAD_REQUEST)

            if allocation.reserved_qty < qty:
                return Response({
                    'detail': f'Cannot release more than reserved. Reserved: {allocation.reserved_qty}, Requested: {qty}'
                }, status=status.HTTP_400_BAD_REQUEST)

            allocation.reserved_qty -= qty
            allocation.save()

            serializer = self.get_serializer(allocation)
            return Response(serializer.data)

        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProductionOrderFilter(django_filters.FilterSet):
    """製造指示フィルタ"""
    product_code = django_filters.CharFilter(field_name='product__product_code', lookup_expr='icontains')
    status = django_filters.MultipleChoiceFilter(choices=ProductionOrder._meta.get_field('status').choices)
    scheduled_start_date_from = django_filters.DateFilter(field_name='scheduled_start_date', lookup_expr='gte')
    scheduled_start_date_to = django_filters.DateFilter(field_name='scheduled_start_date', lookup_expr='lte')

    class Meta:
        model = ProductionOrder
        fields = ['product', 'product_code', 'line', 'status', 'scheduled_start_date']


class ProductionOrderViewSet(viewsets.ModelViewSet):
    """製造指示ViewSet"""
    queryset = ProductionOrder.objects.all().select_related(
        'product', 'routing', 'line', 'allocation'
    )
    serializer_class = ProductionOrderSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductionOrderFilter
    search_fields = ['order_no', 'product__product_code', 'product__product_name']
    ordering_fields = ['scheduled_start_date', 'scheduled_end_date', 'priority', 'created_at']
    ordering = ['-scheduled_start_date', 'priority']

    def get_queryset(self):
        qs = ProductionOrder.objects.select_related('product', 'routing', 'line', 'allocation')
        # 詳細取得時のみ工程実績をプリフェッチ
        if self.action != 'list':
            qs = qs.prefetch_related('actuals__process', 'actuals__line')
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductionOrderListSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=['post'], url_path='sync-from-plan')
    def sync_from_plan(self, request):
        """
        LineBacklog の plan_id を製造指示番号として同期する。
        payload: { line_id?, start_date?, end_date? }
        """
        line_id = request.data.get('line_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        backlog_qs = LineBacklog.objects.exclude(plan_id__isnull=True).exclude(plan_id='').filter(plan_qty__gt=0)
        if line_id:
            backlog_qs = backlog_qs.filter(line_id=line_id)
        if start_date:
            backlog_qs = backlog_qs.filter(plan_date__gte=start_date)
        if end_date:
            backlog_qs = backlog_qs.filter(plan_date__lte=end_date)

        from masters.models import Product
        product_cache = {}
        routing_cache = {}
        created = 0
        updated = 0
        skipped = 0
        seen = set()

        for backlog in backlog_qs.select_related('product'):
            plan_id = backlog.plan_id
            if not plan_id or plan_id in seen:
                continue
            seen.add(plan_id)

            plan_product_code = plan_id.split('_', 1)[0]
            product = product_cache.get(plan_product_code)
            if product is None:
                product = Product.objects.filter(product_code=plan_product_code).first()
                product_cache[plan_product_code] = product
            if not product:
                product = backlog.product
            if not product or not backlog.plan_date:
                skipped += 1
                continue

            routing = routing_cache.get(product.id)
            if routing is None:
                routing = Routing.objects.filter(product_id=product.id, is_active=True).order_by('-is_default', 'id').first()
                routing_cache[product.id] = routing

            defaults = {
                'product_id': product.id,
                'routing_id': routing.id if routing else None,
                'line_id': backlog.line_id,
                'order_qty': backlog.plan_qty,
                'scheduled_start_date': backlog.plan_date,
                'scheduled_end_date': backlog.plan_date,
                'priority': backlog.sequence_no or 0,
            }

            order, is_created = ProductionOrder.objects.get_or_create(
                order_no=plan_id,
                defaults=defaults
            )
            if is_created:
                created += 1
                continue
            if order.status != 'PLANNED':
                continue

            changed = False
            for key, value in defaults.items():
                if getattr(order, key) != value:
                    setattr(order, key, value)
                    changed = True
            if changed:
                order.save()
                updated += 1

        return Response({
            'created': created,
            'updated': updated,
            'skipped': skipped,
        })

    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """
        製造指示発行（計画済→指示済）
        """
        order = self.get_object()

        if order.status != 'PLANNED':
            return Response({
                'detail': f'Cannot release order with status: {order.get_status_display()}'
            }, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'RELEASED'
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        製造開始（指示済→進行中）
        """
        order = self.get_object()

        if order.status != 'RELEASED':
            return Response({
                'detail': f'Cannot start order with status: {order.get_status_display()}'
            }, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone
        order.status = 'IN_PROGRESS'
        order.actual_start_date = timezone.now()
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        製造完了（進行中→完了）
        """
        order = self.get_object()

        if order.status != 'IN_PROGRESS':
            return Response({
                'detail': f'Cannot complete order with status: {order.get_status_display()}'
            }, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone
        order.status = 'COMPLETED'
        order.actual_end_date = timezone.now()
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        製造中止
        """
        order = self.get_object()

        if order.status == 'COMPLETED':
            return Response({
                'detail': 'Cannot cancel completed order'
            }, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'CANCELED'
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)


class ProcessActualFilter(django_filters.FilterSet):
    """工程実績フィルタ"""
    production_order_no = django_filters.CharFilter(field_name='production_order__order_no', lookup_expr='icontains')
    completed_at_from = django_filters.DateTimeFilter(field_name='completed_at', lookup_expr='gte')
    completed_at_to = django_filters.DateTimeFilter(field_name='completed_at', lookup_expr='lte')

    class Meta:
        model = ProcessActual
        fields = ['production_order', 'process', 'line', 'operator']


class ProcessActualViewSet(viewsets.ModelViewSet):
    """工程実績ViewSet"""
    queryset = ProcessActual.objects.all().select_related(
        'production_order', 'production_order__product', 'routing_step', 'process', 'line'
    )
    serializer_class = ProcessActualSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProcessActualFilter
    search_fields = ['production_order__order_no', 'process__process_code', 'operator']
    ordering_fields = ['completed_at', 'actual_duration_min', 'created_at']
    ordering = ['-completed_at']


class LineDailyScheduleSettingViewSet(viewsets.ModelViewSet):
    """ライン別日次スケジュール設定ViewSet"""
    queryset = LineDailyScheduleSetting.objects.all().select_related('line')
    serializer_class = LineDailyScheduleSettingSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['line', 'plan_date']
    ordering_fields = ['plan_date', 'line']
    ordering = ['plan_date', 'line']

    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        """複数日の設定を一括保存"""
        settings_data = request.data.get('settings', [])
        if not settings_data:
            return Response({'error': 'settings is required'}, status=status.HTTP_400_BAD_REQUEST)

        created_count = 0
        updated_count = 0
        errors = []

        for setting_data in settings_data:
            line_id = setting_data.get('line')
            plan_date = setting_data.get('plan_date')

            if not line_id or not plan_date:
                errors.append({'error': 'line and plan_date are required', 'data': setting_data})
                continue

            try:
                obj, created = LineDailyScheduleSetting.objects.update_or_create(
                    line_id=line_id,
                    plan_date=plan_date,
                    defaults={
                        'final_process_start_time': setting_data.get('final_process_start_time'),
                        'adjust_to_break_end': setting_data.get('adjust_to_break_end', True),
                    }
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            except Exception as e:
                errors.append({'error': str(e), 'data': setting_data})

        return Response({
            'created': created_count,
            'updated': updated_count,
            'errors': errors
        }, status=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS)


class LineDefaultScheduleSettingViewSet(viewsets.ModelViewSet):
    """ライン別デフォルトスケジュール設定ViewSet"""

    queryset = LineDefaultScheduleSetting.objects.all().select_related('line')
    serializer_class = LineDefaultScheduleSettingSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['line']
    ordering_fields = ['line']
    ordering = ['line']

    def create(self, request, *args, **kwargs):
        """ライン単位でupsert（既存があれば更新）"""
        line_id = request.data.get('line')
        if not line_id:
            return Response({'detail': 'line is required'}, status=status.HTTP_400_BAD_REQUEST)

        final_process_start_time = request.data.get('final_process_start_time')
        adjust_to_break_end = request.data.get('adjust_to_break_end', True)
        if isinstance(adjust_to_break_end, str):
            adjust_to_break_end = adjust_to_break_end.lower() in ('true', '1', 'yes')

        obj, created = LineDefaultScheduleSetting.objects.update_or_create(
            line_id=line_id,
            defaults={
                'final_process_start_time': final_process_start_time or None,
                'adjust_to_break_end': adjust_to_break_end,
                'updated_by': request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
            }
        )
        serializer = self.get_serializer(obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        """複数ラインのデフォルト設定を一括保存"""
        settings_data = request.data.get('settings', [])
        if not settings_data:
            return Response({'error': 'settings is required'}, status=status.HTTP_400_BAD_REQUEST)

        created_count = 0
        updated_count = 0
        errors = []
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

        changed_line_ids = []
        for setting_data in settings_data:
            line_id = setting_data.get('line')
            if not line_id:
                errors.append({'error': 'line is required', 'data': setting_data})
                continue
            final_time = setting_data.get('final_process_start_time') or None
            adjust = setting_data.get('adjust_to_break_end', True)
            if isinstance(adjust, str):
                adjust = adjust.lower() in ('true', '1', 'yes')
            try:
                obj, created = LineDefaultScheduleSetting.objects.update_or_create(
                    line_id=line_id,
                    defaults={
                        'final_process_start_time': final_time,
                        'adjust_to_break_end': adjust,
                        'updated_by': user,
                    }
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                changed_line_ids.append(line_id)
            except Exception as e:
                errors.append({'error': str(e), 'data': setting_data})

        # デフォルト変更時は日別設定をリセット（次回ロード時に新デフォルトが適用される）
        if changed_line_ids:
            LineDailyScheduleSetting.objects.filter(line_id__in=changed_line_ids).delete()

        return Response(
            {
                'created': created_count,
                'updated': updated_count,
                'errors': errors,
            },
            status=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS,
        )


class ProductionPlanLockSettingView(APIView):
    def get(self, request):
        setting = ProductionPlanLockSetting.objects.first()
        if not setting:
            user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
            setting = ProductionPlanLockSetting.objects.create(lock_days=0, updated_by=user)
        serializer = ProductionPlanLockSettingSerializer(setting)
        return Response(serializer.data)

    def post(self, request):
        raw_days = request.data.get('lock_days')
        try:
            lock_days = int(raw_days)
        except (TypeError, ValueError):
            return Response({'detail': 'lock_days must be integer'}, status=status.HTTP_400_BAD_REQUEST)
        if lock_days < 0:
            return Response({'detail': 'lock_days must be >= 0'}, status=status.HTTP_400_BAD_REQUEST)

        setting = ProductionPlanLockSetting.objects.first()
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        if not setting:
            setting = ProductionPlanLockSetting.objects.create(lock_days=lock_days, updated_by=user)
        else:
            setting.lock_days = lock_days
            setting.updated_by = user
            setting.save(update_fields=['lock_days', 'updated_at', 'updated_by'])

        serializer = ProductionPlanLockSettingSerializer(setting)
        return Response(serializer.data)


class LineBacklogAdjustmentView(APIView):
    """LineBacklog調整の保存/取得API"""

    def get(self, request):
        qs = LineBacklogAdjustment.objects.select_related('line', 'product', 'process').all().order_by('-plan_date', '-id')

        line_code = (request.query_params.get('line_code') or '').strip()
        product_code = (request.query_params.get('product_code') or '').strip()
        process_code = (request.query_params.get('process_code') or '').strip()
        adjust_type = (request.query_params.get('adjust_type') or '').strip().upper()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if line_code:
            qs = qs.filter(line__line_code=line_code)
        if product_code:
            qs = qs.filter(product__product_code=product_code)
        if process_code:
            qs = qs.filter(process__process_code=process_code)
        if adjust_type:
            qs = qs.filter(adjust_type=adjust_type)
        if start_date:
            qs = qs.filter(plan_date__gte=start_date)
        if end_date:
            qs = qs.filter(plan_date__lte=end_date)

        serializer = LineBacklogAdjustmentSerializer(qs[:500], many=True)
        return Response(serializer.data)

    def post(self, request):
        line_code = (request.data.get('line_code') or '').strip()
        product_code = (request.data.get('product_code') or '').strip()
        process_code = (request.data.get('process_code') or '').strip()
        plan_date_raw = request.data.get('plan_date')
        adjust_type = str(request.data.get('adjust_type') or '').upper().strip()
        reason = str(request.data.get('reason') or '').strip()

        if not line_code or not product_code or not plan_date_raw or not adjust_type:
            return Response({'detail': 'line_code, product_code, plan_date, adjust_type は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            plan_date = datetime.strptime(str(plan_date_raw), '%Y-%m-%d').date()
        except ValueError as e:
            return Response({'detail': f'plan_date形式が不正です: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            adjust_qty = int(request.data.get('adjust_qty', 0))
        except (TypeError, ValueError):
            return Response({'detail': 'adjust_qty は整数で指定してください'}, status=status.HTTP_400_BAD_REQUEST)

        valid_types = {'STOCK', 'PLANNED_STOCK', 'PROGRESS', 'PLANNED_PROGRESS'}
        if adjust_type not in valid_types:
            return Response({'detail': 'adjust_type が不正です'}, status=status.HTTP_400_BAD_REQUEST)

        line = Line.objects.filter(line_code=line_code, is_active=True).first()
        if not line:
            return Response({'detail': f'ラインが見つかりません: {line_code}'}, status=status.HTTP_400_BAD_REQUEST)

        product = Product.objects.filter(product_code=product_code).first()
        if not product:
            return Response({'detail': f'品番が見つかりません: {product_code}'}, status=status.HTTP_400_BAD_REQUEST)

        process = None
        if process_code:
            process = Process.objects.filter(process_code=process_code).first()
            if not process:
                return Response({'detail': f'工程が見つかりません: {process_code}'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        obj, _ = LineBacklogAdjustment.objects.update_or_create(
            line=line,
            product=product,
            process=process,
            plan_date=plan_date,
            adjust_type=adjust_type,
            defaults={
                'adjust_qty': adjust_qty,
                'reason': reason,
                'updated_by': user,
            },
        )
        serializer = LineBacklogAdjustmentSerializer(obj)
        return Response(serializer.data)


class ScheduleConfigView(APIView):
    """定時タスクスケジュール設定API"""

    def _ensure_defaults(self):
        """既定設定を補完（自動計画は社内/外作/購買ライン分を作成）"""
        inventory_defaults = [
            ('INVENTORY_RECALC', 7, 0, True),
            ('PICKUP_ONLY', 7, 30, False),
            ('INVENTORY_ONLY', 8, 0, False),
            ('PROGRESS_ONLY', 8, 30, False),
        ]
        for task_name, hour, minute, is_enabled in inventory_defaults:
            ScheduleConfig.objects.get_or_create(
                task_name=task_name,
                line=None,
                defaults={
                    'scheduled_hour': hour,
                    'scheduled_minute': minute,
                    'is_enabled': is_enabled,
                    'range_base_day': 'TODAY',
                    'range_days_after': 45,
                },
            )
        ScheduleConfig.objects.get_or_create(
            task_name='ORDER_EXPANSION',
            line=None,
            defaults={
                'scheduled_hour': 6,
                'scheduled_minute': 0,
                'is_enabled': False,
                'range_base_day': 'TODAY',
                'range_days_after': 45,
            },
        )
        safety_defaults = [
            ('AUTO_SAFETY_STOCK_INTERNAL', 1, 3, 0, 60, 1, False),
            ('AUTO_SAFETY_STOCK_PURCHASE', 1, 3, 30, 60, 1, False),
        ]
        for task_name, dom, hour, minute, average_days_window, safety_days, is_enabled in safety_defaults:
            ScheduleConfig.objects.get_or_create(
                task_name=task_name,
                line=None,
                defaults={
                    'scheduled_dom': dom,
                    'scheduled_hour': hour,
                    'scheduled_minute': minute,
                    'is_enabled': is_enabled,
                    'range_base_day': 'TODAY',
                    'range_days_after': 45,
                    'average_days_window': average_days_window,
                    'safety_days': safety_days,
                },
            )
        base_plan = ScheduleConfig.objects.filter(task_name='AUTO_PLAN', line__isnull=False).first()
        if not base_plan:
            base_plan = ScheduleConfig.objects.filter(task_name='AUTO_PLAN', line__isnull=True).first()
        template = {
            'scheduled_hour': getattr(base_plan, 'scheduled_hour', 3) or 3,
            'scheduled_minute': getattr(base_plan, 'scheduled_minute', 0) or 0,
            'scheduled_dom': getattr(base_plan, 'scheduled_dom', 1),
            'is_enabled': getattr(base_plan, 'is_enabled', True),
            'include_next_month': getattr(base_plan, 'include_next_month', True),
            'include_second_month': getattr(base_plan, 'include_second_month', False),
            'include_third_month': getattr(base_plan, 'include_third_month', False),
        }
        target_types = ['PROD', 'OUTSOURCE', 'PURCHASE']
        for idx, line in enumerate(
            Line.objects.filter(is_active=True, line_type__in=target_types).order_by('line_type', 'line_code', 'id'),
            start=1
        ):
            ScheduleConfig.objects.get_or_create(
                task_name='AUTO_PLAN',
                line=line,
                defaults={**template, 'execution_order': idx},
            )

    def get(self, request):
        self._ensure_defaults()
        configs = ScheduleConfig.objects.select_related('line').order_by('task_name', 'execution_order', 'line__line_code')
        serializer = ScheduleConfigSerializer(configs, many=True)
        return Response(serializer.data)

    def post(self, request):
        config_id = request.data.get('id') or request.data.get('config_id')
        task_name = str(request.data.get('task_name', 'INVENTORY_RECALC')).upper()
        line_id = request.data.get('line')

        def to_bool(val, default=False):
            if val in (None, ''):
                return default
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in ('true', '1', 'yes', 'on')
            return bool(val)

        scheduled_hour = request.data.get('scheduled_hour')
        scheduled_minute = request.data.get('scheduled_minute', 0)
        scheduled_dom = request.data.get('scheduled_dom')
        execution_order = request.data.get('execution_order')
        range_base_day = (request.data.get('range_base_day') or 'TODAY').upper()
        range_days_after = request.data.get('range_days_after', 45)
        average_days_window = request.data.get('average_days_window', 60)
        safety_days = request.data.get('safety_days', 1)
        is_enabled = request.data.get('is_enabled', True)
        include_current_month = to_bool(request.data.get('include_current_month', False), False)
        include_next_month = to_bool(request.data.get('include_next_month', True), True)
        include_second_month = to_bool(request.data.get('include_second_month', False), False)
        include_third_month = to_bool(request.data.get('include_third_month', False), False)
        from_sequence_ui = to_bool(request.data.get('from_sequence_ui', False), False)

        try:
            scheduled_hour = int(scheduled_hour)
            scheduled_minute = int(scheduled_minute)
        except (TypeError, ValueError):
            return Response(
                {'detail': '時刻は整数で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (0 <= scheduled_hour <= 23) or not (0 <= scheduled_minute <= 59):
            return Response(
                {'detail': '時刻の範囲が不正です'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if scheduled_dom not in (None, '',):
            try:
                scheduled_dom = int(scheduled_dom)
            except (TypeError, ValueError):
                return Response({'detail': '実行日は1-31の整数で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
            if not (1 <= scheduled_dom <= 31):
                return Response({'detail': '実行日は1-31の範囲で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            scheduled_dom = None
        if execution_order in (None, ''):
            execution_order = None
        else:
            try:
                execution_order = int(execution_order)
            except (TypeError, ValueError):
                return Response({'detail': '実行順は整数で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
            if execution_order < 1:
                return Response({'detail': '実行順は1以上で指定してください'}, status=status.HTTP_400_BAD_REQUEST)

        if isinstance(is_enabled, str):
            is_enabled = is_enabled.lower() in ('true', '1', 'yes')

        allowed_base_days = {'TODAY', 'YESTERDAY', 'TWO_DAYS_AGO'}
        if range_base_day not in allowed_base_days:
            return Response(
                {'detail': '開始基準日は 今日 / 昨日 / 一昨日 から選択してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            range_days_after = int(range_days_after)
        except (TypeError, ValueError):
            return Response(
                {'detail': '何日後は整数で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (0 <= range_days_after <= 365):
            return Response(
                {'detail': '何日後は0〜365で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            average_days_window = int(average_days_window)
        except (TypeError, ValueError):
            return Response(
                {'detail': '実行日からの平均日数は整数で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (1 <= average_days_window <= 365):
            return Response(
                {'detail': '実行日からの平均日数は1〜365で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            safety_days = int(safety_days)
        except (TypeError, ValueError):
            return Response(
                {'detail': '安全在庫日数は整数で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (1 <= safety_days <= 365):
            return Response(
                {'detail': '安全在庫日数は1〜365で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        line_obj = None
        safety_task_names = {'AUTO_SAFETY_STOCK_INTERNAL', 'AUTO_SAFETY_STOCK_PURCHASE'}
        if task_name == 'AUTO_PLAN':
            if not line_id:
                return Response({'detail': 'ラインを指定してください'}, status=status.HTTP_400_BAD_REQUEST)
            line_obj = Line.objects.filter(id=line_id, line_type__in=['PROD', 'OUTSOURCE', 'PURCHASE']).first()
            if not line_obj:
                return Response({'detail': '指定されたラインが見つかりません（社内/外作/購買ラインのみ設定可能）'}, status=status.HTTP_400_BAD_REQUEST)
            if not (include_current_month or include_next_month or include_second_month or include_third_month):
                return Response({'detail': '実行期間を1つ以上選択してください'}, status=status.HTTP_400_BAD_REQUEST)
        if task_name in safety_task_names and scheduled_dom is None:
            return Response({'detail': '安全在庫タスクは実行日（1-31）を指定してください'}, status=status.HTTP_400_BAD_REQUEST)

        if config_id:
            config = ScheduleConfig.objects.filter(id=config_id).first()
            if not config:
                return Response({'detail': '設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        else:
            config, _ = ScheduleConfig.objects.get_or_create(
                task_name=task_name,
                line=line_obj,
                defaults={
                    'scheduled_hour': scheduled_hour,
                    'scheduled_minute': scheduled_minute,
                    'scheduled_dom': scheduled_dom,
                    'range_base_day': range_base_day,
                    'range_days_after': range_days_after,
                    'average_days_window': average_days_window,
                    'safety_days': safety_days,
                    'is_enabled': is_enabled,
                    'include_current_month': include_current_month,
                    'include_next_month': include_next_month,
                    'include_second_month': include_second_month,
                    'include_third_month': include_third_month,
                },
            )

        if task_name == 'AUTO_PLAN' and getattr(config, 'auto_plan_sequence_locked', False) and not from_sequence_ui:
            return Response(
                {'detail': '自動計画は順序運用モードです。順序設定画面から編集してください。'},
                status=status.HTTP_409_CONFLICT,
            )

        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        config.scheduled_hour = scheduled_hour
        config.scheduled_minute = scheduled_minute
        config.scheduled_dom = scheduled_dom
        config.range_base_day = range_base_day
        config.range_days_after = range_days_after
        config.average_days_window = average_days_window
        config.safety_days = safety_days
        config.is_enabled = is_enabled
        config.include_current_month = include_current_month
        config.include_next_month = include_next_month
        config.include_second_month = include_second_month
        config.include_third_month = include_third_month
        if execution_order is not None:
            config.execution_order = execution_order
        if task_name == 'AUTO_PLAN':
            config.auto_plan_sequence_locked = from_sequence_ui
        if line_obj:
            config.line = line_obj
        config.updated_by = user
        update_fields = [
            'scheduled_hour', 'scheduled_minute', 'scheduled_dom',
            'range_base_day', 'range_days_after', 'average_days_window', 'safety_days',
            'is_enabled', 'include_current_month', 'include_next_month', 'include_second_month', 'include_third_month',
            'line', 'updated_at', 'updated_by',
        ]
        if execution_order is not None:
            update_fields.append('execution_order')
        if task_name == 'AUTO_PLAN':
            update_fields.append('auto_plan_sequence_locked')
        config.save(update_fields=update_fields)

        notify_user_ids = request.data.get('notify_users', None)
        notify_user_codes = request.data.get('notify_user_codes', None)

        if notify_user_ids is not None:
            config.notify_users.set(notify_user_ids)
        elif notify_user_codes is not None:
            codes = notify_user_codes
            if isinstance(codes, str):
                import re
                codes = [c for c in re.split(r'[,\s]+', codes) if c]
            try:
                iter(codes)
            except TypeError:
                codes = []
            User = get_user_model()
            users = User.objects.filter(
                Q(profile__employee_code__in=codes) | Q(username__in=codes) | Q(email__in=codes)
            ).distinct()
            config.notify_users.set(users)

        serializer = ScheduleConfigSerializer(config)
        return Response(serializer.data)


class ScheduleRunNowView(APIView):
    """定時タスクを手動実行（非同期）"""

    def post(self, request):
        import threading
        from .scheduler.tasks import run_inventory_recalculation
        from .scheduler.tasks_safety_stock import run_auto_safety_stock
        from .scheduler.tasks_auto_plan import run_auto_plan
        from .scheduler.tasks_order_expansion import run_order_expansion
        task = (request.data.get('task_name') or 'INVENTORY_RECALC').upper()
        task_labels = {
            'INVENTORY_RECALC': '取り込み＋在庫再計算',
            'PICKUP_ONLY': '取り込みのみ',
            'INVENTORY_ONLY': '在庫計算のみ',
            'PROGRESS_ONLY': '進度計算のみ',
            'AUTO_SAFETY_STOCK_INTERNAL': '自動安全在庫（社内）',
            'AUTO_SAFETY_STOCK_PURCHASE': '自動安全在庫（購入品）',
        }
        config_id = request.data.get('config_id') or request.data.get('id')
        line_id = request.data.get('line')
        try:
            if task == 'AUTO_PLAN':
                # config_id/line指定が無い場合は、設定済みAUTO_PLANを実行順で順次実行する
                if config_id:
                    config = ScheduleConfig.objects.filter(id=config_id).first()
                    if not config:
                        return Response({'detail': '対象設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
                    result = run_auto_plan(force=True, config_id=config.id)
                elif line_id:
                    config = ScheduleConfig.objects.filter(task_name='AUTO_PLAN', line_id=line_id).first()
                    if not config:
                        return Response({'detail': '対象設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
                    result = run_auto_plan(force=True, config_id=config.id)
                else:
                    result = run_auto_plan(force=True)
                return Response({'detail': '生産計画自動生成を実行しました', **(result or {})})
            elif task == 'ORDER_EXPANSION':
                result = run_order_expansion()
                return Response({'detail': '自動受注展開を実行しました', **(result or {})})
            elif task in task_labels:
                from django.utils import timezone
                # 二重実行防止: 同一タスクのRUNNING状態チェック（10分超はスタック扱いでリセット）
                stale_cfg = ScheduleConfig.objects.filter(
                    task_name=task,
                    last_run_status='RUNNING',
                ).first()
                if stale_cfg:
                    elapsed = (timezone.now() - stale_cfg.last_run_at).total_seconds() if stale_cfg.last_run_at else 9999
                    if elapsed < 600:
                        return Response(
                            {'detail': '既に実行中です。完了までお待ちください。'},
                            status=status.HTTP_409_CONFLICT,
                        )
                    stale_cfg.last_run_status = 'FAILED'
                    stale_cfg.last_run_message = f'タイムアウト（{int(elapsed)}秒経過）により強制リセット'
                    stale_cfg.save(update_fields=['last_run_status', 'last_run_message'])
                    logger.warning(f'[スケジューラ] {task} RUNNING状態が{int(elapsed)}秒スタック → FAILEDにリセット')

                # バックグラウンドスレッドで実行
                def _run():
                    import django
                    django.db.connections.close_all()
                    try:
                        if task in {'AUTO_SAFETY_STOCK_INTERNAL', 'AUTO_SAFETY_STOCK_PURCHASE'}:
                            run_auto_safety_stock(task_name=task)
                        else:
                            run_inventory_recalculation(task_name=task)
                    except Exception:
                        logger.exception('バックグラウンドタスク実行に失敗')
                        ScheduleConfig.objects.filter(
                            task_name=task,
                            last_run_status='RUNNING',
                        ).update(last_run_status='FAILED', last_run_message='実行中にエラーが発生しました')

                thread = threading.Thread(target=_run, daemon=True)
                thread.start()
                return Response({
                    'detail': f'{task_labels[task]}をバックグラウンドで開始しました。',
                    'async': True,
                })
            else:
                return Response(
                    {'detail': f'未対応のタスクです: {task}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            logger.exception('手動実行に失敗')
            return Response(
                {'detail': f'実行に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
