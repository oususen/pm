from rest_framework import viewsets, status
from decimal import Decimal
from datetime import timedelta
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
import django_filters

from .models import LineDemand, Order, OrderLine, StgOrderRaw, StgOrderDaily
from .models_line_backlog import LineBacklog
from .models_production import StockAllocation, ProductionOrder, ProcessActual
from .serializers import (
    LineDemandSerializer,
    OrderSerializer,
    OrderLineSerializer,
    StgOrderRawSerializer,
    StgOrderDailySerializer,
    LineBacklogSerializer,
    StockAllocationSerializer,
    ProductionOrderSerializer,
    ProductionOrderListSerializer,
    ProcessActualSerializer,
)
from .services.csv_import import CSVImportService
from .services.order_expansion import OrderExpansionService
from masters.models import Routing, RoutingStep


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
    queryset = OrderLine.objects.all().select_related('order', 'product')
    serializer_class = OrderLineSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['order', 'product', 'due_date']
    search_fields = ['product_code']
    ordering_fields = ['due_date', 'line_no']
    ordering = ['line_no']


class StgOrderRawViewSet(viewsets.ModelViewSet):
    """受注取込ステージング（生データ）ViewSet"""
    queryset = StgOrderRaw.objects.all()
    serializer_class = StgOrderRawSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['customer_code', 'order_type', 'parse_status', 'source_file']
    search_fields = ['customer_code', 'product_code', 'source_file']
    ordering_fields = ['created_at', 'due_date']
    ordering = ['-created_at']

    def _get_import_service(self, customer_code, order_type, filename):
        """Select appropriate import service based on customer code, order type, and filename"""
        # Import services here to avoid circular imports
        from .services.csv_import import CSVImportService

        # Extract location from filename
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
            # Detect location from filename
            if '堺' in filename or 'sakai' in filename_lower:
                if order_type == 'FORECAST':
                    # クボタ_堺_内示
                    from .services.kubota_sakai_naiji_import import KubotaSakaiNaijiImportService
                    return KubotaSakaiNaijiImportService()
                elif order_type == 'FIRM':
                    # クボタ_堺_確定
                    from .services.kubota_sakai_kakutei_import import KubotaSakaiKakuteiImportService
                    return KubotaSakaiKakuteiImportService()
            elif '枚方' in filename or 'hirakata' in filename_lower:
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

            # Check for duplicate file name
            from orders.models import StgOrderRaw
            if StgOrderRaw.objects.filter(source_file=file.name).exists():
                return Response(
                    {
                        'success': False,
                        'error': f'このファイル名は既にアップロード済みです: {file.name}',
                        'message': f'ファイル名 "{file.name}" は既にステージングに存在します。別のファイル名でアップロードしてください。'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Select appropriate import service based on customer code, order type, and filename
            import_service = self._get_import_service(customer_code, order_type, file.name)
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

    queryset = LineDemand.objects.all().select_related('line', 'product', 'routing_step')
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


class LineBacklogViewSet(viewsets.ModelViewSet):
    queryset = LineBacklog.objects.all().select_related('process', 'product', 'line')
    serializer_class = LineBacklogSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = LineBacklogFilter
    ordering_fields = ['plan_date', 'line', 'product']
    ordering = ['plan_date', 'line']

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
        from orders.models import LineDemand
        from masters.models import BOMItem, RoutingStep, Calendar, CalendarDay
        from collections import defaultdict

        line_id = request.data.get('line_id')
        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        # このラインの「ライン最終品」を特定（is_line_final_product フラグを使用）
        target_products = set()
        product_process_map = {}

        # このラインに属する全工程を取得し、is_line_final_product=True の製品のみを対象とする
        steps_on_line = RoutingStep.objects.filter(
            line_id=line_id
        ).select_related('output_product', 'routing__product', 'process')

        for step in steps_on_line:
            product = step.output_product or step.routing.product
            if product and product.is_line_final_product:
                target_products.add(product.id)
                product_process_map[product.id] = step.process_id

        if not target_products:
            # このラインが生産する製品（ライン最終品）がない
            return Response([])

        # 需要を計算：(product_id, plan_date) -> order_qty
        demand_map = defaultdict(Decimal)

        # 使用するカレンダ（tiera_muke）を取得
        calendar_id = Calendar.objects.filter(calendar_code='tiera_muke').values_list('id', flat=True).first()

        def shift_business_days(target_date, days):
            """
            稼働日で日付をシフトする。
            days > 0 なら過去方向へ、days < 0 なら未来方向へ。
            カレンダが無い場合は暦日でシフト。
            """
            if not days:
                return target_date
            if not calendar_id:
                return target_date + timedelta(days=-days)

            step = -1 if days > 0 else 1  # 正:過去へ、負:未来へ
            remaining = abs(int(days))
            current = target_date
            while remaining > 0:
                current = current + timedelta(days=step)
                cal = CalendarDay.objects.filter(calendar_id=calendar_id, target_date=current).first()
                is_work = cal.is_working_day if cal is not None else True
                if is_work:
                    remaining -= 1
            return current

        # 既存バックログを先に取得し、ゼロ需要でもレコードを返せるよう初期化
        backlog_qs = self.get_queryset().filter(line_id=line_id, product_id__in=target_products).select_related('product', 'process')
        if start_date:
            backlog_qs = backlog_qs.filter(plan_date__gte=start_date)
        if end_date:
            backlog_qs = backlog_qs.filter(plan_date__lte=end_date)
        for existing in backlog_qs:
            demand_map[(existing.product_id, existing.plan_date)] = Decimal('0')

        # 1. 後ライン（次工程）から需要を取得（RoutingStepベース）
        # ロジック：
        #   ステップ1: 現在ラインのoutput_product（例：中間品C）を特定
        #   ステップ2: 中間品Cを子部品として使う親製品（例：中間品B）をBOMから探す
        #   ステップ3: 親製品を出力するラインをRoutingStepから探す
        #   ステップ4: そのライン（例：溶接ライン）のLineBacklogから計画数を取得
        #   ステップ5: BOM個数を掛けて現在ラインの必要数を計算
        downstream_found = False
        for product_id in target_products:
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

                    # リードタイム（日）を考慮：RoutingStep > Line > BOM明細 の順で優先
                    lt_days = 0
                    if d_step.lead_time_days:
                        lt_days = d_step.lead_time_days
                    elif d_step.line and d_step.line.lead_time_days:
                        lt_days = d_step.line.lead_time_days
                    elif bom_item.lead_time_days:
                        lt_days = bom_item.lead_time_days

                    # ステップ4: 後工程ラインのLineBacklogから計画数を取得
                    # 親製品が中間品の場合、そのRoutingの最終品（ライン最終品）を基準にする
                    routing_final_product = None
                    if d_step.routing and d_step.routing.product:
                        # Routingの製品がライン最終品の場合、それを使用
                        if d_step.routing.product.is_line_final_product:
                            routing_final_product = d_step.routing.product

                    # LineBacklog取得：ライン最終品を優先、なければ親製品を使用
                    target_product_for_backlog = routing_final_product or parent_product
                    backlog_items = LineBacklog.objects.filter(
                        line_id=downstream_line_id,
                        product_id=target_product_for_backlog.id
                    )
                    if start_date:
                        backlog_items = backlog_items.filter(plan_date__gte=start_date)
                    if end_date:
                        backlog_items = backlog_items.filter(plan_date__lte=end_date)

                    # ステップ5: 後工程の計画数 × BOM個数 = 現在ラインの必要数
                    # routing_final_productを使った場合、BOMチェーン全体の個数を計算する必要がある
                    if routing_final_product and routing_final_product != parent_product:
                        # BOMチェーンをたどって総個数を計算
                        # current_output_product → ... → parent_product → ... → routing_final_product
                        # ここでは簡易的に、全経路の個数を掛け合わせる
                        # TODO: より正確な計算が必要な場合は再帰的にBOMをたどる
                        total_qty_per = qty_per  # とりあえず直接の個数を使用
                    else:
                        total_qty_per = qty_per

                    for backlog in backlog_items:
                        plan_date = backlog.plan_date
                        if lt_days:
                            plan_date = shift_business_days(plan_date, lt_days)
                        key = (current_output_product, plan_date)
                        demand_map[key] += backlog.plan_qty * total_qty_per
                        downstream_found = True

        # 2. RoutingStepベースの展開が失敗した場合、BOMベースの展開を試みる
        if not downstream_found:
            # BOMItemのline_idを使って需要展開
            for product_id in target_products:
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
                    lt_days = bom_item.lead_time_days or 0

                    for backlog in backlog_items:
                        plan_date = backlog.plan_date
                        if lt_days:
                            plan_date = shift_business_days(plan_date, lt_days)
                        key = (current_output_product, plan_date)
                        demand_map[key] += backlog.plan_qty * qty_per
                        downstream_found = True

        # 3. BOMベースの展開も失敗した場合は最終ラインとしてLineDemandを使用
        if not downstream_found:
            demand_qs = LineDemand.objects.filter(line_id=line_id, product_id__in=target_products)
            if start_date:
                demand_qs = demand_qs.filter(plan_date__gte=start_date)
            if end_date:
                demand_qs = demand_qs.filter(plan_date__lte=end_date)

            for demand in demand_qs:
                if demand.product_id:
                    key = (demand.product_id, demand.plan_date)
                    demand_map[key] = demand.plan_qty

        # 4. LineBacklogに保存（order_qtyのみ更新、他の数量は維持）
        upserted_items = []
        for (product_id, plan_date), order_qty in demand_map.items():
            process_id = product_process_map.get(product_id)
            if not process_id:
                continue

            obj, _ = LineBacklog.objects.update_or_create(
                plan_date=plan_date,
                process_id=process_id,
                product_id=product_id,
                line_id=line_id,
                defaults={'order_qty': order_qty}
            )
            upserted_items.append(obj)

        # 5. 最新状態を返す
        serializer = self.get_serializer(upserted_items or backlog_qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def save(self, request):
        """
        ユーザーが入力した計画データをLineBacklogに保存する
        期待payload: { line_id, items: [{product_id, process_id, plan_date, plan_qty?, actual_qty?, stock_qty?, planned_stock_qty?}] }
        """
        line_id = request.data.get('line_id')
        items = request.data.get('items', [])
        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(items, list) or not items:
            return Response({'detail': 'items is required'}, status=status.HTTP_400_BAD_REQUEST)

        created = 0
        updated = 0
        skipped = []

        for it in items:
            try:
                product_id = it.get('product_id')
                process_id = it.get('process_id')
                plan_date = it.get('plan_date')
                if not product_id or not process_id or not plan_date:
                    skipped.append({'item': it, 'reason': 'product_id/process_id/plan_date required'})
                    continue

                # 更新するフィールドを準備
                defaults = {}
                if 'plan_qty' in it:
                    defaults['plan_qty'] = Decimal(str(it['plan_qty']))
                if 'actual_qty' in it:
                    defaults['actual_qty'] = Decimal(str(it['actual_qty']))
                if 'stock_qty' in it:
                    defaults['stock_qty'] = Decimal(str(it['stock_qty']))
                if 'planned_stock_qty' in it:
                    defaults['planned_stock_qty'] = Decimal(str(it['planned_stock_qty']))

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

        return Response({'created': created, 'updated': updated, 'skipped': skipped})


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
