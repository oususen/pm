from rest_framework import viewsets, status
from decimal import Decimal
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import LineDemand, Order, OrderLine, StgOrderRaw, StgOrderDaily
from .models_line_backlog import LineBacklog
from .serializers import (
    LineDemandSerializer,
    OrderSerializer,
    OrderLineSerializer,
    StgOrderRawSerializer,
    StgOrderDailySerializer,
    LineBacklogSerializer,
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


class LineBacklogViewSet(viewsets.ModelViewSet):
    queryset = LineBacklog.objects.all().select_related('process', 'product', 'line')
    serializer_class = LineBacklogSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['line', 'process', 'product', 'plan_date']
    ordering_fields = ['plan_date', 'line', 'product']
    ordering = ['plan_date', 'line']

    @action(detail=False, methods=['post'])
    def expand(self, request):
        """
        後工程ラインの計画数量を前工程への発注としてバックログに書き込む。
        期待payload: { line_id, items: [{product_id, process_id, plan_date, quantity, source_routing_step_id?}] }
        line_id は「後工程（画面で選択中のライン=source_line）」として扱い、前工程ラインはルーティングから自動判定する。
        """
        source_line_id = request.data.get('line_id')
        items = request.data.get('items', [])
        if not source_line_id:
            return Response({'detail': 'line_id is required (後工程ライン)'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(items, list) or not items:
            return Response({'detail': 'items is required'}, status=status.HTTP_400_BAD_REQUEST)
        created = 0
        updated = 0
        skipped = []

        def find_final_product(product_id):
            """
            中間品から最終製品を逆引きする。
            product_idがRoutingのoutput_productとして使われている場合、そのRoutingのproduct（最終製品）を返す。
            見つからなければproduct_id自体が最終製品とみなす。
            """
            step = RoutingStep.objects.filter(output_product_id=product_id).select_related('routing').first()
            if step and step.routing:
                return step.routing.product_id
            return product_id

        def resolve_prev_step(product_id, process_id, src_line_id):
            """
            後工程のステップに対して、直前の前工程ステップ(1つ)を特定する。
            一つのラインずつ展開するための関数。
            """
            # まず最終製品を特定
            final_product_id = find_final_product(product_id)

            # 最終製品のルーティングを取得
            routing = Routing.objects.filter(product_id=final_product_id, is_default=True).prefetch_related('steps').first()
            if not routing:
                raise ValueError(f'default routing not found for final_product_id={final_product_id}')
            steps = list(routing.steps.order_by('step_no').select_related('output_product', 'process', 'line'))

            # 現在のラインに一致するステップを探す（複数マッチング戦略）
            current = None

            # 戦略1: product_idとprocess_idとline_idが全て一致
            current = next((st for st in steps if st.line_id == src_line_id and st.process_id == process_id and
                           (st.output_product_id == product_id or st.routing.product_id == product_id)), None)

            # 戦略2: line_idとprocess_idが一致
            if not current:
                current = next((st for st in steps if st.line_id == src_line_id and st.process_id == process_id), None)

            # 戦略3: line_idのみ一致（最後のステップ）
            if not current:
                matching_steps = [st for st in steps if st.line_id == src_line_id]
                if matching_steps:
                    current = matching_steps[-1]

            if not current:
                raise ValueError(f'no step found for line_id={src_line_id} in routing for product_id={final_product_id}')

            # 直前の前工程ステップを取得（step_noがcurrentより小さく、line_idが異なる最大のstep_no）
            prev = (
                RoutingStep.objects.filter(
                    routing_id=routing.id,
                    step_no__lt=current.step_no,
                    line__isnull=False
                )
                .exclude(line_id=src_line_id)
                .select_related('output_product', 'process', 'line')
                .order_by('-step_no')
                .first()
            )

            if not prev:
                raise ValueError(f'no previous step found for current step_no={current.step_no} in routing')

            # 前工程のステップのoutput_productを使用（なければ最終製品を使用）
            target_product_id = prev.output_product_id if prev.output_product_id else final_product_id

            return {
                'line_id': prev.line_id,
                'process_id': prev.process_id,
                'product_id': target_product_id,
            }

        for it in items:
            try:
                product_id = it.get('product_id')
                process_id = it.get('process_id')
                plan_date = it.get('plan_date')
                qty = Decimal(str(it.get('quantity', 0)))
                if not product_id or not process_id or not plan_date:
                    skipped.append({'item': it, 'reason': 'product_id/process_id/plan_date required'})
                    continue
                try:
                    prev_step = resolve_prev_step(product_id, process_id, source_line_id)
                except Exception as e:
                    skipped.append({'item': it, 'reason': str(e)})
                    continue

                # 前工程のステップ情報を使ってLineBacklogに登録
                obj, is_created = LineBacklog.objects.update_or_create(
                    plan_date=plan_date,
                    process_id=prev_step['process_id'],  # 前工程のprocess_id
                    product_id=prev_step['product_id'],  # 前工程のoutput_product_id
                    line_id=prev_step['line_id'],        # 前工程のline_id
                    defaults={
                        'demand_qty_plan': qty,
                        'source_line_id': source_line_id,
                        'source_routing_step_id': it.get('source_routing_step_id'),
                    }
                )
                if is_created:
                    created += 1
                else:
                    updated += 1
            except Exception as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'created': created, 'updated': updated, 'skipped': skipped})

    @action(detail=False, methods=['post'])
    def pickup(self, request):
        """
        ラインの需要を取得する。
        - LineBacklogにデータがあればLineBacklogから取得（中間工程）
        - なければLineDemandから取得（最終工程）
        - みなし組立品(is_phantom=True)は除外
        期待payload: { line_id, start_date?, end_date? }
        """
        from orders.models import LineDemand

        line_id = request.data.get('line_id')
        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        # まずLineBacklogにデータがあるかチェック
        backlog_qs = self.get_queryset().filter(line_id=line_id).select_related('product')
        if start_date:
            backlog_qs = backlog_qs.filter(plan_date__gte=start_date)
        if end_date:
            backlog_qs = backlog_qs.filter(plan_date__lte=end_date)

        # みなし組立品を除外
        backlog_qs = backlog_qs.filter(product__is_phantom=False)

        if backlog_qs.exists():
            # 中間工程：LineBacklogから取得
            serializer = self.get_serializer(backlog_qs, many=True)
            return Response(serializer.data)
        else:
            # 最終工程：LineDemandから取得（みなし組立品を除外）
            demand_qs = LineDemand.objects.filter(line_id=line_id).select_related('product', 'routing_step__process')
            if start_date:
                demand_qs = demand_qs.filter(plan_date__gte=start_date)
            if end_date:
                demand_qs = demand_qs.filter(plan_date__lte=end_date)

            # みなし組立品を除外
            demand_qs = demand_qs.filter(product__is_phantom=False)

            result = []
            for demand in demand_qs:
                result.append({
                    'plan_date': demand.plan_date,
                    'product': demand.product.id if demand.product else None,
                    'product_code': demand.product_code,
                    'product_name': demand.product.product_name if demand.product else '',
                    'process': demand.routing_step.process.id if demand.routing_step and demand.routing_step.process else None,
                    'line': line_id,
                    'demand_qty_plan': demand.plan_qty,
                    'source_line': None,
                })

            return Response(result)
