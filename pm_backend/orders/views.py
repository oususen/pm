from rest_framework import viewsets, status
from decimal import Decimal
from datetime import timedelta, datetime
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
import django_filters
from django.db.models import Q, Max
import logging

from .models import (
    LineDemand,
    Order,
    OrderLine,
    ShipmentActual,
    ShipmentActualHistory,
    StgOrderRaw,
    StgOrderDaily,
)
from .models_line_backlog import LineBacklog
from .models_production import StockAllocation, ProductionOrder, ProcessActual
from .models_line_gantt_plan import LineGanttPlan
from .serializers import (
    LineDemandSerializer,
    OrderSerializer,
    OrderLineSerializer,
    StgOrderRawSerializer,
    StgOrderDailySerializer,
    LineBacklogSerializer,
    LineGanttPlanSerializer,
    ShipmentActualHistorySerializer,
    ShipmentActualSerializer,
    StockAllocationSerializer,
    ProductionOrderSerializer,
    ProductionOrderListSerializer,
    ProcessActualSerializer,
)
from .services.csv_import import CSVImportService
from .services.order_expansion import OrderExpansionService
from .services.gantt_planning import generate_line_gantt_plans
from masters.models import Routing, RoutingStep, ProcessCycleTime, Line, Supplier, Process, Calendar, CalendarDay, BOM, BOMItem

logger = logging.getLogger(__name__)

class OrderViewSet(viewsets.ModelViewSet):
    """受注ヘッダViewSet"""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['customer', 'order_type', 'status', 'order_date']
    search_fields = ['order_no', 'source_file']
    ordering_fields = ['order_date', 'created_at', 'id']
    ordering = ['-order_date', '-id']

    def get_queryset(self):
        qs = Order.objects.select_related('customer')
        # 詳細取得時のみ明細をプリフェッチしてレスポンスサイズを抑える
        if self.action != 'list':
            qs = qs.prefetch_related('lines')
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            from .serializers import OrderListSerializer
            return OrderListSerializer
        return super().get_serializer_class()


class OrderLineViewSet(viewsets.ModelViewSet):
    """受注明細ViewSet"""
    queryset = OrderLine.objects.filter(order__status='OPEN').select_related('order', 'order__customer', 'product')
    serializer_class = OrderLineSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['order', 'product', 'due_date']
    search_fields = ['product_code']
    ordering_fields = ['due_date', 'line_no']
    ordering = ['line_no']


class ShipmentActualFilter(django_filters.FilterSet):
    """出荷実績のカスタムフィルタ"""
    shipment_date = django_filters.DateFilter(field_name='shipment_date')
    shipment_date__gte = django_filters.DateFilter(field_name='shipment_date', lookup_expr='gte')
    shipment_date__lte = django_filters.DateFilter(field_name='shipment_date', lookup_expr='lte')
    product_code = django_filters.CharFilter(field_name='product_code', lookup_expr='icontains')
    customer_code = django_filters.CharFilter(field_name='customer_code', lookup_expr='icontains')
    ship_to_code = django_filters.CharFilter(field_name='ship_to_code', lookup_expr='icontains')

    class Meta:
        model = ShipmentActual
        fields = []


class ShipmentActualViewSet(viewsets.ModelViewSet):
    """出荷実績ViewSet"""
    queryset = ShipmentActual.objects.all().select_related('product', 'customer')
    serializer_class = ShipmentActualSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ShipmentActualFilter
    search_fields = ['product_code', 'customer_code', 'ship_to_code']
    ordering_fields = ['shipment_date', 'product_code', 'customer_code', 'created_at']
    ordering = ['-shipment_date', 'product_code']

    def _create_history(self, instance, action):
        ShipmentActualHistory.objects.create(
            shipment_actual=instance,
            action=action,
            shipment_date=instance.shipment_date,
            product_code=instance.product_code,
            customer_code=instance.customer_code,
            ship_to_code=instance.ship_to_code,
            quantity=instance.quantity,
            remark=instance.remark,
        )

    def perform_create(self, serializer):
        instance = serializer.save()
        self._create_history(instance, 'CREATE')

    def perform_update(self, serializer):
        before = ShipmentActual.objects.get(pk=serializer.instance.pk)
        instance = serializer.save()
        self._create_history(before, 'UPDATE')

    def perform_destroy(self, instance):
        self._create_history(instance, 'DELETE')
        instance.delete()

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        histories = ShipmentActualHistory.objects.filter(
            shipment_actual_id=pk
        ).order_by('-id')
        serializer = ShipmentActualHistorySerializer(histories, many=True)
        return Response(serializer.data)


class StgOrderRawViewSet(viewsets.ModelViewSet):
    """受注取込ステージング（生データ）ViewSet"""
    queryset = StgOrderRaw.objects.all()
    serializer_class = StgOrderRawSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['customer_code', 'order_type', 'parse_status', 'source_file']
    search_fields = ['customer_code', 'product_code', 'source_file']
    ordering_fields = ['created_at', 'due_date']
    ordering = ['-created_at']

    def _get_import_service(self, customer_code, order_type, filename, factory=None):
        """Select appropriate import service based on customer code, order type, and factory

        Args:
            customer_code: Customer code
            order_type: 'FIRM' or 'FORECAST'
            filename: CSV filename (for fallback detection)
            factory: Explicit factory code (e.g., 'SAKAI', 'HIRAKATA')
        """
        # Import services here to avoid circular imports
        from .services.csv_import import CSVImportService

        # Extract location from filename (fallback)
        filename_lower = filename.lower()

        # Customer: 000001 (ティエラ)
        if customer_code == '000001':
            if order_type == 'FORECAST':
                # ティエラ_内示
                from .services.tiera_naiji_import import TieraNaijiImportService
                return TieraNaijiImportService()
            elif order_type == 'FIRM':
                # ティエラ_確定
                from .services.tiera_kakutei_import import TieraKakuteiImportService
                return TieraKakuteiImportService()

        # Customer: 000196 (クボタ)
        elif customer_code == '000196':
            # Determine factory: explicit parameter > filename detection
            detected_factory = factory
            if not detected_factory:
                if '堺' in filename or 'sakai' in filename_lower:
                    detected_factory = 'SAKAI'
                elif '枚方' in filename or 'hirakata' in filename_lower:
                    detected_factory = 'HIRAKATA'

            if detected_factory == 'SAKAI':
                if order_type == 'FORECAST':
                    # クボタ_堺_内示
                    from .services.kubota_sakai_naiji_import import KubotaSakaiNaijiImportService
                    return KubotaSakaiNaijiImportService()
                elif order_type == 'FIRM':
                    # クボタ_堺_確定
                    from .services.kubota_sakai_kakutei_import import KubotaSakaiKakuteiImportService
                    return KubotaSakaiKakuteiImportService()
            elif detected_factory == 'HIRAKATA':
                if order_type == 'FORECAST':
                    # クボタ_枚方_内示
                    from .services.kubota_hirakata_naiji_import import KubotaHirakataNaijiImportService
                    return KubotaHirakataNaijiImportService()
                elif order_type == 'FIRM':
                    # クボタ_枚方_確定
                    from .services.kubota_hirakata_kakutei_import import KubotaHirakataKakuteiImportService
                    return KubotaHirakataKakuteiImportService()

        # Customer: 000018 (リーデン)
        elif customer_code == '000018':
            if order_type == 'FIRM':
                # リーデン_確定
                from .services.rieden_kakutei_import import RiedenKakuteiImportService
                return RiedenKakuteiImportService()

        # Default service
        return CSVImportService()

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_csv(self, request):
        """Upload CSV file and import to staging"""
        try:
            file = request.FILES.get('file')
            customer_code = request.data.get('customer_code')
            order_type = request.data.get('order_type', 'FIRM')
            source_system = request.data.get('source_system', 'CSV')
            factory = request.data.get('factory')  # Optional: for multi-factory customers like Kubota

            if not file:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not customer_code:
                return Response(
                    {'error': 'Customer code is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check for duplicate file name across all raw tables
            from orders.models import StgOrderRaw, StgOrderRawKubota, StgOrderRawTiera, StgOrderRawRieden
            if (StgOrderRaw.objects.filter(source_file=file.name).exists() or
                StgOrderRawKubota.objects.filter(source_file=file.name).exists() or
                StgOrderRawTiera.objects.filter(source_file=file.name).exists() or
                StgOrderRawRieden.objects.filter(source_file=file.name).exists()):
                return Response(
                    {
                        'success': False,
                        'error': f'このファイル名は既にアップロード済みです: {file.name}',
                        'message': f'ファイル名 "{file.name}" は既にステージングに存在します。別のファイル名でアップロードしてください。'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Select appropriate import service based on customer code, order type, and factory
            import_service = self._get_import_service(customer_code, order_type, file.name, factory)
            result = import_service.import_csv(file, customer_code, order_type, source_system)

            if result['success']:
                # Automatically create orders from staging after successful upload
                # Always use CSVImportService for order creation (common logic)
                try:
                    order_service = CSVImportService()
                    # Use raw ID range to filter only records from this import
                    raw_id_range = (result.get('min_raw_id'), result.get('max_raw_id'))
                    order_result = order_service.create_orders_from_staging(
                        source_file=file.name,
                        raw_id_range=raw_id_range
                    )
                    # Merge results
                    result['orders_created'] = order_result.get('orders', 0)
                    result['lines_created'] = order_result.get('lines', 0)
                    result['superseded_forecast_orders'] = order_result.get('deleted_forecast_orders', 0)
                except Exception as e:
                    # If order creation fails, still return the staging import success
                    # but include the error
                    result['order_creation_error'] = str(e)
                    result['message'] = f"CSV imported to staging successfully, but order creation failed: {str(e)}"

                return Response(result, status=status.HTTP_201_CREATED)
            else:
                # Log error details
                print(f"CSV Import Error: {result}")
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def create_orders(self, request):
        """Create orders from staging data"""
        try:
            service = CSVImportService()
            result = service.create_orders_from_staging()
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def check_filename(self, request):
        """Check if filename already exists in staging"""
        filename = request.query_params.get('filename')
        if not filename:
            return Response(
                {'error': 'Filename parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from orders.models import StgOrderRaw
        exists = StgOrderRaw.objects.filter(source_file=filename).exists()

        return Response({
            'exists': exists,
            'filename': filename,
            'message': f'ファイル名 "{filename}" は既にアップロード済みです。' if exists else 'このファイル名は使用できます。'
        })


class StgOrderDailyViewSet(viewsets.ModelViewSet):
    """受注取込ステージング（日別）ViewSet"""
    queryset = StgOrderDaily.objects.all().select_related('customer', 'raw')
    serializer_class = StgOrderDailySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['customer', 'order_type', 'due_date']
    search_fields = ['product_code']
    ordering_fields = ['due_date', 'created_at']
    ordering = ['due_date']


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
        print(f"\n[DEBUG] ========== pickup API開始 ==========")
        print(f"[DEBUG] line_id={line_id}, start_date={start_date}, end_date={end_date}")
        target_products = set()
        final_products = set()  # ライン最終品
        intermediate_products = set()  # 中間品
        product_process_map = {}
        product_step_map = {}

        # このラインに属する全工程を取得し、全ての製品を対象とする
        steps_on_line = RoutingStep.objects.filter(
            line_id=line_id
        ).select_related('output_product', 'routing__product', 'process')

        print(f"[DEBUG] steps_on_line件数: {steps_on_line.count()}")

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
                    print(f"[DEBUG] 最終品: product_code={product.product_code}, product_id={product.id}, is_final={product.is_final_product}, process_id={step.process_id}")
                else:
                    intermediate_products.add(product.id)
                    print(f"[DEBUG] 中間品: product_code={product.product_code}, product_id={product.id}, is_final={product.is_final_product}, process_id={step.process_id}")

        print(f"[DEBUG] target_products件数: {len(target_products)}")
        print(f"[DEBUG] final_products件数: {len(final_products)}")
        print(f"[DEBUG] intermediate_products件数: {len(intermediate_products)}")

        if not target_products:
            # このラインが生産する製品がない
            print(f"[DEBUG] target_productsが空のため、空リストを返します")
            return Response([])

        # 需要を計算：(product_id, plan_date) -> order_qty
        demand_map = defaultdict(Decimal)

        # 使用するカレンダ（ライン紐付があれば優先、無ければtiera_muke）
        line_obj = Line.objects.filter(id=line_id).first()
        calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(calendar_code='tiera_muke').values_list('id', flat=True).first()

        def shift_business_days(target_date, days):
            """
            稼働日で日付をシフトする。
            days > 0 なら過去方向へ、days < 0 なら未来方向へ。
            カレンダが無い場合は暦日でシフト。
            """
            def is_working_day(check_date):
                if not calendar_id:
                    return True
                cal = CalendarDay.objects.filter(calendar_id=calendar_id, target_date=check_date).first()
                return cal.is_working_day if cal is not None else True

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
        print(f"\n[DEBUG] ========== 需要取得開始 ==========")

        # A. 最終品（is_final_product=True）はOrderLineから取得
        if final_products:
            print(f"\n[DEBUG] 最終品の需要取得開始（OrderLine使用）")
            print(f"[DEBUG] final_products={final_products}")

            order_lines = OrderLine.objects.filter(
                order__status='OPEN',
                product_id__in=final_products
            ).select_related('order', 'product')

            if start_date:
                order_lines = order_lines.filter(due_date__gte=start_date)
            if end_date:
                order_lines = order_lines.filter(due_date__lte=end_date)

            print(f"[DEBUG] OrderLine検索結果: {order_lines.count()}件")

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

                if plan_date != ol.due_date:
                    print(f"[DEBUG] OrderLine date shift: {ol.due_date} -> {plan_date}")

            for key in set(firm_map) | set(forecast_map):
                firm_qty = firm_map.get(key, Decimal('0'))
                forecast_qty = forecast_map.get(key, Decimal('0'))
                demand_qty = firm_qty if firm_qty > 0 else forecast_qty
                demand_map[key] = demand_qty
                print(f"[DEBUG] demand_map[{key}] = {demand_qty} (firm={firm_qty}, forecast={forecast_qty})")

        # B. 中間品は後工程から需要を取得
        if not intermediate_products:
            print(f"\n[DEBUG] 中間品がないため後工程展開をスキップ")

        # 1. 後ライン（次工程）から需要を取得（RoutingStepベース）
        # ロジック：
        #   ステップ1: 現在ラインのoutput_product（例：中間品C）を特定
        #   ステップ2: 中間品Cを子部品として使う親製品（例：中間品B）をBOMから探す
        #   ステップ3: 親製品を出力するラインをRoutingStepから探す
        #   ステップ4: そのライン（例：溶接ライン）のLineBacklogから計画数を取得
        #   ステップ5: BOM個数を掛けて現在ラインの必要数を計算
        downstream_found = False
        for product_id in intermediate_products:
            # 現在ラインのoutput_product（例：ブレーキラインなら中間品C）
            current_output_product = product_id

            # ステップ2: この製品を子部品として使うBOMを取得
            # （parent ← current_output_product の関係）
            bom_items = BOMItem.objects.filter(
                child_product_id=current_output_product
            ).select_related('bom__parent_product')

            for bom_item in bom_items:
                parent_product = bom_item.bom.parent_product
                if not parent_product:
                    continue

                qty_per = bom_item.quantity or Decimal('0')
                if qty_per == 0:
                    continue

                # ステップ3: 親製品を出力するライン（後工程）をRoutingStepから特定
                downstream_steps = RoutingStep.objects.filter(
                    output_product_id=parent_product.id
                ).select_related('routing', 'routing__product', 'line')

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
            print(f"\n[DEBUG] BOMベースの展開開始（中間品のみ）")
            # BOMItemのline_idを使って需要展開
            for product_id in intermediate_products:
                current_output_product = product_id

                # この製品を子部品として使うBOMItem（line_idが現在ラインと一致するもの）を取得
                bom_items = BOMItem.objects.filter(
                    child_product_id=current_output_product,
                    line_id=line_id
                ).select_related('bom__parent_product')

                for bom_item in bom_items:
                    parent_product = bom_item.bom.parent_product
                    if not parent_product:
                        continue

                    qty_per = bom_item.quantity or Decimal('0')
                    if qty_per == 0:
                        continue

                    # 親製品のLineBacklogから計画数を取得
                    backlog_items = LineBacklog.objects.filter(
                        product_id=parent_product.id
                    )
                    if start_date:
                        backlog_items = backlog_items.filter(plan_date__gte=start_date)
                    if end_date:
                        backlog_items = backlog_items.filter(plan_date__lte=end_date)

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
        print(f"\n[DEBUG] LineBacklogへの保存開始")
        print(f"[DEBUG] demand_map件数: {len(demand_map)}")
        upserted_items = []
        for (product_id, plan_date), order_qty in demand_map.items():
            process_id = product_process_map.get(product_id)
            print(f"[DEBUG] product_id={product_id}, plan_date={plan_date}, order_qty={order_qty}, process_id={process_id}")
            if not process_id:
                print(f"[DEBUG] process_id not found for product_id={product_id}, skipping")
                continue

            obj, created = LineBacklog.objects.update_or_create(
                plan_date=plan_date,
                process_id=process_id,
                product_id=product_id,
                line_id=line_id,
                defaults={'order_qty': order_qty}
            )
            print(f"[DEBUG] LineBacklog {'created' if created else 'updated'}: id={obj.id}, product_code={obj.product.product_code}, order_qty={obj.order_qty}")
            upserted_items.append(obj)

        print(f"[DEBUG] upserted_items件数: {len(upserted_items)}")

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
                        order_qty=0,
                        demand_qty_plan=0,
                        plan_qty=0,
                        actual_qty=0,
                        stock_qty=0,
                        planned_stock_qty=0,
                    ))
                items_to_serialize = placeholders
        serializer = self.get_serializer(items_to_serialize, many=True)
        print(f"[DEBUG] serializer.data件数: {len(serializer.data)}")
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
                defaults={
                    'order_qty': qty_val,
                    'demand_qty_plan': qty_val,
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
            qs = self.get_queryset().filter(line_id=line_id)
            qs = qs.filter(plan_date__gte=start_date, plan_date__lte=end_date)
            # 全製品（中間品、単品完成品、ライン最終品、工程最終品）で plan_qty > 0 のレコードを対象とする
            qs = qs.filter(plan_qty__gt=0)
            for obj in qs:
                base_plans.append({
                    'product_id': obj.product_id,
                    'plan_date': obj.plan_date,
                    'plan_qty': Decimal(str(obj.plan_qty or 0)),
                    'order_qty': Decimal(str(obj.order_qty or 0)),
                    'demand_qty_plan': Decimal(str(obj.demand_qty_plan or 0)),
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
                combination_key = (target_product_id, step.process_id, target_date)
                child_key = None
                if child_target_product_id and child_target_product_id != target_product_id:
                    child_key = (child_target_product_id, step.process_id, target_date)
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
                                sequence_no=sequence_no if sequence_no is not None else None,
                            )
                    else:
                        defaults_dict = {
                            'order_qty': int(order_qty),
                            'demand_qty_plan': int(demand_qty_plan),
                            'source_line_id': line_id,
                            'source_routing_step_id': step.id,
                        }
                        defaults_dict['plan_qty'] = int(qty_value)

                        if sequence_no is not None:
                            defaults_dict['sequence_no'] = sequence_no

                        if parent_plan_id:
                            defaults_dict['plan_id'] = parent_plan_id

                        obj, is_created = LineBacklog.objects.update_or_create(
                            plan_date=target_date,
                            process_id=step.process_id,
                            product_id=target_id,
                            line_id=line_id,
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

        # まず、製品コードを取得するために製品IDから製品情報を取得
        from masters.models import Product
        product_cache = {}

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
                            # plan_idに紐づく全てのLineBacklogレコードを削除
                            deleted_count = LineBacklog.objects.filter(plan_id=existing.plan_id).delete()[0]
                            deleted += deleted_count
                            continue
                        elif existing:
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

                new_plan_id = None
                if plan_qty_provided:
                    # plan_idを生成: 製品コード_YYYYMMDD_数量_順番
                    # gantt_planning.pyと同じフォーマットを使用
                    from datetime import datetime
                    if isinstance(plan_date, str):
                        plan_date_obj = datetime.strptime(plan_date, '%Y-%m-%d').date()
                    else:
                        plan_date_obj = plan_date

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
        from .inventory_calculator import recalculate_inventory_for_line

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
        期待payload: { line_id, start_date, end_date, clear_existing?: bool }
        """
        line_id = request.data.get('line_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        clear_existing = bool(request.data.get('clear_existing'))

        logger.info(
            'line_gantt_plans.generate: line_id=%s start=%s end=%s clear=%s',
            line_id, start_date, end_date, clear_existing
        )

        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not start_date or not end_date:
            return Response({'detail': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            line_id = int(line_id)
        except (TypeError, ValueError):
            return Response({'detail': 'line_id must be numeric'}, status=status.HTTP_400_BAD_REQUEST)

        plans = generate_line_gantt_plans(line_id, start_date, end_date, clear_existing=clear_existing)
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
