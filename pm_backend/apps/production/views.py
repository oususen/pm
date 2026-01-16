from rest_framework import viewsets, status
from rest_framework.views import APIView
from decimal import Decimal
from datetime import timedelta, datetime
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
import django_filters
from django.db.models import Q, Max
import logging

from .models import LineDemand
from orders.models import OrderLine
from .models_line_backlog import LineBacklog
from .models_line_plan import LinePlan
from .models_production import StockAllocation, ProductionOrder, ProcessActual
from .models_line_gantt_plan import LineGanttPlan
from .models_line_daily_schedule_setting import LineDailyScheduleSetting
from .models_plan_change_log import ProductionPlanChangeLog
from .models_plan_lock_setting import ProductionPlanLockSetting
from .serializers import (
    LineDemandSerializer,
    LineBacklogSerializer,
    LinePlanSerializer,
    LineGanttPlanSerializer,
    LineDailyScheduleSettingSerializer,
    ProductionPlanLockSettingSerializer,
    StockAllocationSerializer,
    ProductionOrderSerializer,
    ProductionOrderListSerializer,
    ProcessActualSerializer,
)
from .services.order_expansion import OrderExpansionService
from .services.gantt_planning import generate_line_gantt_plans
from masters.models import Routing, RoutingStep, ProcessCycleTime, Line, Supplier, Process, Calendar, CalendarDay, BOM, BOMItem

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
            # 1. 該当ライン・日付・製品のLinePlanを削除
            if affected_dates and affected_products:
                deleted_plan_result = LinePlan.objects.filter(
                    line_id=line_id,
                    plan_date__in=affected_dates,
                    product_id__in=affected_products
                ).delete()
                deleted_plan = deleted_plan_result[0] if deleted_plan_result else 0

                # 2. 該当ライン・日付・製品のLineGanttPlanを削除
                deleted_gantt_result = LineGanttPlan.objects.filter(
                    line_id=line_id,
                    plan_date__in=affected_dates,
                    product_id__in=affected_products
                ).delete()
                deleted_gantt = deleted_gantt_result[0] if deleted_gantt_result else 0

                # 3. 該当ライン・日付・製品のLineBacklogを削除（計画レコードのみ）
                # ルール: sequence_no > 0 のレコードは計画レコードとして削除
                #        sequence_no = 0 は在庫・需要・仕損などの基礎データとして保持
                #        sequence_no = NULL は実績レコードとして保持
                deleted_backlog_result = LineBacklog.objects.filter(
                    line_id=line_id,
                    plan_date__in=affected_dates,
                    product_id__in=affected_products,
                    sequence_no__gt=0  # sequence_no > 0 のみ削除（計画レコード）
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

        if not items:
            return

        line_ids = {item.line_id for item in items if item.line_id}
        if not line_ids:
            return

        line_map = {line.id: line for line in Line.objects.filter(id__in=line_ids)}
        default_calendar_id = Calendar.objects.filter(calendar_code='tiera_muke').values_list('id', flat=True).first()

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
                    lead_days = step.lead_time_days or 0
                    if not lead_days and step.line_id and step.line.lead_time_days:
                        lead_days = step.line.lead_time_days
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
                    return True
                if target_date in workday_cache:
                    return workday_cache[target_date]
                cal = CalendarDay.objects.filter(
                    calendar_id=calendar_id,
                    target_date=target_date
                ).first()
                is_work = cal.is_working_day if cal is not None else True
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
                step = product_step_map.get(product_id)
                if step and step.lead_time_days:
                    return step.lead_time_days
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
        from masters.models import BOMItem, RoutingStep
        from collections import defaultdict

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
        steps_on_line = RoutingStep.objects.filter(
            line_id=line_id
        ).select_related('output_product', 'routing__product', 'process')

        for step in steps_on_line:
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

        if not target_products:
            return Response([])

        # 需要を計算：(product_id, plan_date) -> order_qty
        demand_map = defaultdict(Decimal)

        # 使用するカレンダ（ライン紐付があれば優先、無ければtiera_muke）
        line_obj = Line.objects.filter(id=line_id).first()
        calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(calendar_code='tiera_muke').values_list('id', flat=True).first()

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
            カレンダが無い場合は暦日でシフト。
            """
            def is_working_day(check_date):
                if not calendar_id:
                    return True
                # キャッシュから取得（キャッシュにない場合はTrue扱い）
                return calendar_day_cache.get(check_date, True)

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

            step = -1 if days > 0 else 1  # 正:過去へ、負:未来へ
            remaining = abs(int(days))
            current = target_date
            while remaining > 0:
                current = current + timedelta(days=step)
                if is_working_day(current):
                    remaining -= 1
            return current

        gantt_usage_cache = {}

        def build_line_start_map(line_id, product_ids):
            key = (
                line_id,
                tuple(sorted(product_ids)),
                start_date,
                end_date,
            )
            if key in gantt_usage_cache:
                return gantt_usage_cache[key]

            qs = LineGanttPlan.objects.filter(
                line_id=line_id,
                product_id__in=product_ids,
            )

            usage_map = {}
            for plan in qs:
                start_dt_value = plan.start_datetime
                if not start_dt_value:
                    continue
                try:
                    plan_day = start_dt_value.date()
                except Exception:
                    try:
                        ts = str(start_dt_value).replace('Z', '+00:00')
                        plan_day = datetime.fromisoformat(ts).date()
                    except Exception:
                        continue
                if start_dt and plan_day < start_dt:
                    continue
                if end_dt and plan_day > end_dt:
                    continue
                try:
                    qty = Decimal(str(plan.plan_qty or 0))
                except Exception:
                    qty = Decimal('0')
                if qty == 0:
                    continue
                usage_map[plan_day] = usage_map.get(plan_day, Decimal('0')) + qty

            gantt_usage_cache[key] = usage_map
            return usage_map

        def resolve_lead_time_days(current_product_id, bom_item=None):
            """現ラインのLTを優先して解決する。"""
            step = product_step_map.get(current_product_id)
            if step and step.lead_time_days:
                return step.lead_time_days
            if step and step.line and step.line.lead_time_days:
                return step.line.lead_time_days
            if bom_item and bom_item.lead_time_days:
                return bom_item.lead_time_days
            return 0

        # 既存バックログを先に取得し、ゼロ需要でもレコードを返せるよう初期化
        backlog_qs = self.get_queryset().filter(line_id=line_id, product_id__in=target_products).select_related('product', 'process')
        if start_date:
            backlog_qs = backlog_qs.filter(plan_date__gte=start_date)
        if end_date:
            backlog_qs = backlog_qs.filter(plan_date__lte=end_date)
        for existing in backlog_qs:
            demand_map[(existing.product_id, existing.plan_date)] = Decimal('0')

        # 最終品はOrderLineから、中間品は後工程から需要を取得

        # A. 最終品（is_final_product=True）はOrderLineから取得
        if final_products:
            order_lines = OrderLine.objects.filter(
                order__status='OPEN',
                product_id__in=final_products
            ).select_related('order', 'product')

            if start_date:
                order_lines = order_lines.filter(due_date__gte=start_date)
            if end_date:
                order_lines = order_lines.filter(due_date__lte=end_date)

            firm_map = defaultdict(Decimal)
            forecast_map = defaultdict(Decimal)

            for ol in order_lines:
                if not ol.product_id:
                    continue
                step = product_step_map.get(ol.product_id)
                if not step:
                    continue

                lead_days = resolve_lead_time_days(ol.product_id)
                plan_date = shift_business_days(ol.due_date, lead_days)
                key = (ol.product_id, plan_date)

                qty = Decimal(str(ol.quantity or 0))
                order_type = (ol.order.order_type or '').upper()
                if order_type == 'FIRM':
                    firm_map[key] += qty
                else:
                    forecast_map[key] += qty

            for key in set(firm_map) | set(forecast_map):
                firm_qty = firm_map.get(key, Decimal('0'))
                forecast_qty = forecast_map.get(key, Decimal('0'))
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
            all_bom_items = BOMItem.objects.filter(
                child_product_id__in=intermediate_products
            ).select_related('bom', 'bom__parent_product')
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
            all_downstream_steps = RoutingStep.objects.filter(
                output_product_id__in=parent_product_ids
            ).select_related('routing', 'routing__product', 'line')
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

                for d_step in downstream_steps:
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
                    line_start_map = build_line_start_map(downstream_line_id, target_ids)
                    backlog_items = LineBacklog.objects.filter(
                        line_id=downstream_line_id,
                        product_id__in=target_ids
                    )
                    if start_date:
                        backlog_items = backlog_items.filter(plan_date__gte=start_date)
                    if end_date:
                        backlog_items = backlog_items.filter(plan_date__lte=end_date)

                    # ステップ5: 後工程の計画数 × BOM個数 = 現在ラインの必要数
                    if routing_final_product and routing_final_product != parent_product:
                        total_qty_per = qty_per
                    else:
                        total_qty_per = qty_per

                    fallback_map = {}
                    if len(target_ids) > 1:
                        parent_map = {}
                        final_map = {}
                        for backlog in backlog_items:
                            plan_date = backlog.plan_date
                            qty = Decimal(str(backlog.plan_qty or 0))
                            if qty == 0:
                                continue
                            if backlog.product_id == parent_product.id:
                                parent_map[plan_date] = parent_map.get(plan_date, Decimal('0')) + qty
                            else:
                                final_map[plan_date] = final_map.get(plan_date, Decimal('0')) + qty
                        for plan_date in set(parent_map) | set(final_map):
                            qty = parent_map.get(plan_date)
                            if qty is None or qty <= 0:
                                qty = final_map.get(plan_date, Decimal('0'))
                            if qty:
                                fallback_map[plan_date] = qty
                    else:
                        for backlog in backlog_items:
                            plan_date = backlog.plan_date
                            qty = Decimal(str(backlog.plan_qty or 0))
                            if qty == 0:
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
                backlog_qs_parent = LineBacklog.objects.filter(product_id__in=parent_ids_for_backlog)
                if start_date:
                    backlog_qs_parent = backlog_qs_parent.filter(plan_date__gte=start_date)
                if end_date:
                    backlog_qs_parent = backlog_qs_parent.filter(plan_date__lte=end_date)
                for backlog in backlog_qs_parent:
                    prod_id = backlog.product_id
                    if prod_id not in backlog_by_product:
                        backlog_by_product[prod_id] = []
                    backlog_by_product[prod_id].append(backlog)

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

                    for backlog in backlog_items:
                        plan_date = backlog.plan_date
                        if lt_days:
                            plan_date = shift_business_days(plan_date, lt_days)
                        key = (current_output_product, plan_date)
                        demand_map[key] += backlog.plan_qty * qty_per
                        downstream_found = True

        # 4. LineBacklogに保存（order_qtyのみ更新、他の数量は維持）
        upserted_items = []
        for (product_id, plan_date), order_qty in demand_map.items():
            process_id = product_process_map.get(product_id)
            if not process_id:
                continue

            obj, created = LineBacklog.objects.update_or_create(
                plan_date=plan_date,
                process_id=process_id,
                product_id=product_id,
                line_id=line_id,
                sequence_no=0,
                defaults={
                    'order_qty': order_qty,
                    'demand_qty_plan': order_qty,
                    'plan_qty': 0,
                    'sequence_no': 0,
                }
            )
            upserted_items.append(obj)

        # 5. 最新状態を返す
        items_to_serialize = upserted_items
        if not items_to_serialize:
            existing_items = list(backlog_qs)
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

        line_code = f"SUP{supplier.id}"
        line_name = f"仕入:{supplier.supplier_code} {supplier.supplier_name}"
        if len(line_name) > 50:
            line_name = line_name[:50]
        line_obj, created = Line.objects.get_or_create(
            line_code=line_code,
            defaults={
                'line_name': line_name,
                'line_type': 'PURCHASE',
                'is_active': False,
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

        if not bom_items.exists():
            return Response({'created': 0, 'updated': 0, 'items': 0, 'line_id': line_id, 'process_id': process_id})

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

        if not parent_ids or not child_ids:
            return Response({'created': 0, 'updated': 0, 'items': 0})

        parent_qs = LineBacklog.objects.filter(product_id__in=parent_ids)
        if start_dt:
            parent_qs = parent_qs.filter(plan_date__gte=start_dt)
        if end_dt:
            parent_qs = parent_qs.filter(plan_date__lte=end_dt)

        # 親製品の計画数量(plan_qty)を取得（order_qtyではなくplan_qtyを使用）
        parent_orders = parent_qs.values('product_id', 'line_id', 'plan_date', 'plan_qty').filter(
            plan_qty__gt=0  # 計画数量が0より大きいもののみ
        )

        calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(
            calendar_code='tiera_muke'
        ).values_list('id', flat=True).first()

        def shift_business_days(target_date, days):
            if not days:
                if not calendar_id:
                    return target_date
                cal = CalendarDay.objects.filter(calendar_id=calendar_id, target_date=target_date).first()
                is_work = cal.is_working_day if cal is not None else True
                if is_work:
                    return target_date
                current = target_date
                while True:
                    current = current - timedelta(days=1)
                    cal = CalendarDay.objects.filter(calendar_id=calendar_id, target_date=current).first()
                    is_work = cal.is_working_day if cal is not None else True
                    if is_work:
                        return current
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

        demand_map = defaultdict(Decimal)
        for row in parent_orders:
            parent_id = row['product_id']
            plan_date = row['plan_date']
            plan_qty = Decimal(str(row['plan_qty'] or 0))

            # 計画数量(plan_qty)を使用（後ラインの計画から需要を取得）
            if plan_qty == 0:
                continue
            for child_id, qty, lead_time_days in parent_to_children.get(parent_id, []):
                target_date = shift_business_days(plan_date, lead_time_days)
                demand_map[(child_id, target_date)] += plan_qty * qty

        existing_qs = LineBacklog.objects.filter(
            line_id=line_id,
            process_id=process_id,
            product_id__in=child_ids,
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
                    'plan_qty': 0,
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
        copro_boms = BOM.objects.filter(is_coproduct=True, is_active=True).order_by('-valid_from', '-id').prefetch_related('items')
        for bom in copro_boms:
            for item in bom.items.all():
                try:
                    qty_decimal = Decimal(item.quantity)
                except Exception:
                    continue
                if qty_decimal == 0:
                    continue
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

        # ラインに紐づくカレンダがあれば使用、無ければtiera_mukeを使用
        line_obj = Line.objects.filter(id=line_id).first()
        calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(calendar_code='tiera_muke').values_list('id', flat=True).first()
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
        processed_combinations = set()  # (親製品ID, 工程ID, 日付)の重複を防ぐ

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

            steps = steps_map.get(product_id, [])
            if not steps:
                skipped.append({'product_id': product_id, 'plan_date': plan_date, 'reason': 'RoutingStep not found on line'})
                continue

            for step in sorted(steps, key=lambda s: s.step_no or 0):
                target_date = shift_business_days(plan_date, step.lead_time_days or 0)
                target_product_id = step.output_product_id or product_id

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

                # 既に処理済みの(製品, 工程, 日付)の組み合わせはスキップ
                combination_key = (target_product_id, step.process_id, target_date, seq_key)
                child_key = None
                if child_target_product_id and child_target_product_id != target_product_id:
                    child_key = (child_target_product_id, step.process_id, target_date, seq_key)
                skip_parent = False
                if combination_key in processed_combinations:
                    if not (child_key and child_key not in processed_combinations):
                        continue
                    skip_parent = True
                else:
                    processed_combinations.add(combination_key)

                # 連産品（コプロダクト）の場合、セット数ベースで工数を計算
                time_qty = plan_qty
                is_copro_driver = True

                if copro_info_target:
                    copro_key = (copro_info_target['parent_id'], plan_date)
                    set_qty = copro_set_qty.get(copro_key)
                    if set_qty is not None:
                        time_qty = set_qty
                        plan_qty = set_qty
                    driver_id = copro_driver.get(copro_key)
                    # 代表child以外は工数0として扱い、重複計上を防ぐ
                    is_copro_driver = driver_id in (None, original_target_product_id, product_id)

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

                def upsert_backlog(target_id, qty_value, time_value):
                    nonlocal created, updated
                    if read_only:
                        obj = LineBacklog.objects.filter(
                            plan_date=target_date,
                            process_id=step.process_id,
                            product_id=target_id,
                            line_id=line_id,
                            sequence_no=seq_key,
                        ).first()

                        if not obj:
                            obj = LineBacklog(
                                plan_date=target_date,
                                process_id=step.process_id,
                                product_id=target_id,
                                line_id=line_id,
                                plan_qty=int(qty_value),
                                order_qty=int(order_qty),
                                demand_qty_plan=int(demand_qty_plan),
                                source_line_id=line_id,
                                source_routing_step_id=step.id,
                                sequence_no=seq_key,
                            )
                    else:
                        defaults_dict = {
                            'order_qty': int(order_qty),
                            'demand_qty_plan': int(demand_qty_plan),
                            'source_line_id': line_id,
                            'source_routing_step_id': step.id,
                        }
                        defaults_dict['plan_qty'] = int(qty_value)

                        defaults_dict['sequence_no'] = seq_key

                        if parent_plan_id:
                            defaults_dict['plan_id'] = parent_plan_id

                        obj, is_created = LineBacklog.objects.update_or_create(
                            plan_date=target_date,
                            process_id=step.process_id,
                            product_id=target_id,
                            line_id=line_id,
                            sequence_no=seq_key,
                            defaults=defaults_dict
                        )
                        created += 1 if is_created else 0
                        updated += 0 if is_created else 1

                    obj.computed_time_min = time_value
                    obj.work_minutes = calendar_work_map.get(target_date)
                    obj.step_no = step.step_no
                    obj.cycle_time_min = float(ct.cycle_time_min) if ct and ct.cycle_time_min else None
                    obj.routing_product_id = step.routing.product_id if step.routing_id and step.routing else None
                    upserted.append(obj)

                if not skip_parent:
                    upsert_backlog(target_product_id, plan_qty, computed_time_min)

                if child_key and child_key not in processed_combinations:
                    processed_combinations.add(child_key)
                    upsert_backlog(child_target_product_id, child_plan_qty, 0)

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
                        # 既存レコードを取得
                        existing = LineBacklog.objects.filter(
                            plan_date=plan_date,
                            process_id=process_id,
                            product_id=product_id,
                            line_id=line_id,
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

                # sequence_noを取得（デフォルトは1）
                sequence_no = it.get('sequence_no', 1)
                if sequence_no is None:
                    sequence_no = 1

                # 既存レコードを取得
                existing = LineBacklog.objects.filter(
                    plan_date=plan_date,
                    process_id=process_id,
                    product_id=product_id,
                    line_id=line_id,
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
                    from datetime import datetime
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

                # LineBacklogに保存
                obj, is_created = LineBacklog.objects.update_or_create(
                    plan_date=plan_date,
                    process_id=process_id,
                    product_id=product_id,
                    line_id=line_id,
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

    @action(detail=False, methods=['post'])
    def recalculate_inventory(self, request):
        """
        在庫・計画在庫を再計算するAPI

        期待payload: {
            line_id: int (required),
            start_date: str (YYYY-MM-DD, required),
            end_date: str (YYYY-MM-DD, required)
        }
        """
        from .inventory.inventory_calculator import recalculate_inventory_for_line

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
            recalculate_inventory_for_line(line_id, start_dt, end_dt)
            return Response({'detail': 'Inventory recalculated successfully'})
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
        期待payload: [{ plan_id, process_id, start_time, end_time }, ...]
        """
        updates = request.data
        if not isinstance(updates, list) or not updates:
            return Response({'detail': 'updates must be a non-empty list'}, status=status.HTTP_400_BAD_REQUEST)

        updated_count = 0
        for update in updates:
            plan_id = update.get('plan_id')
            process_id = update.get('process_id')
            if not plan_id or not process_id:
                continue

            plan = LineGanttPlan.objects.filter(plan_id=plan_id).first()
            if not plan or not plan.processes_plan:
                continue

            processes_plan = list(plan.processes_plan)
            changed = False
            for proc in processes_plan:
                if str(proc.get('process_id')) == str(process_id):
                    proc['start_time'] = update.get('start_time')
                    proc['end_time'] = update.get('end_time')
                    changed = True
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

        return Response({'updated': updated_count})


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
