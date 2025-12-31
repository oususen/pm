from rest_framework import viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Exists, OuterRef, Q
from django.core.files.storage import default_storage
import django_filters
import os
import uuid
from datetime import date
from .models import (
    Product, Customer, Process, Line, Supplier, Calendar, CalendarDay, WorkPattern, BreakTime,
    BOM, BOMItem, Routing, RoutingStep, RoutingStepMaterial
)
from .serializers import (
    ProductSerializer, CustomerSerializer, ProcessSerializer, LineSerializer,
    SupplierSerializer, CalendarSerializer, CalendarDaySerializer, WorkPatternSerializer, BreakTimeSerializer,
    BOMSerializer, BOMItemSerializer, RoutingSerializer, RoutingStepSerializer,
    RoutingStepMaterialSerializer
)


class ProductFilter(django_filters.FilterSet):
    created_from = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_to = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    is_final_product = django_filters.BooleanFilter(field_name='is_final_product')
    is_line_final_product = django_filters.BooleanFilter(field_name='is_line_final_product')
    has_bom = django_filters.BooleanFilter(method='filter_has_bom')

    class Meta:
        model = Product
        fields = [
            'category',
            'is_active',
            'is_final_product',
            'is_line_final_product',
            'has_bom',
            'created_from',
            'created_to',
        ]

    def filter_has_bom(self, queryset, name, value):
        if value is None:
            return queryset
        bom_exists = BOM.objects.filter(parent_product_id=OuterRef('pk'))
        queryset = queryset.annotate(_has_bom=Exists(bom_exists))
        if value:
            return queryset.filter(_has_bom=True)
        return queryset.filter(_has_bom=False)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['product_code', 'product_name']
    ordering_fields = ['product_code', 'created_at']
    ordering = ['product_code']

    @action(detail=True, methods=['post'], url_path='upload_image', parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def upload_image(self, request, pk=None):
        product = self.get_object()
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'detail': 'ファイルがありません'}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(file_obj.name)[1] or ''
        filename = f"products/{product.product_code}_{uuid.uuid4().hex}{ext}"
        saved_path = default_storage.save(filename, file_obj)
        url = default_storage.url(saved_path)
        product.image_url = url
        product.save(update_fields=['image_url', 'updated_at'])
        return Response({'image_url': url}, status=status.HTTP_200_OK)


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    filterset_fields = ['is_active']
    search_fields = ['customer_code', 'customer_name']
    ordering_fields = ['customer_code', 'created_at']
    ordering = ['customer_code']


class ProcessViewSet(viewsets.ModelViewSet):
    queryset = Process.objects.all()
    serializer_class = ProcessSerializer
    filterset_fields = ['is_active', 'is_outsource']
    search_fields = ['process_code', 'process_name']
    ordering_fields = ['process_code', 'created_at']
    ordering = ['process_code']

    @action(detail=True, methods=['get'], url_path='related-products')
    def related_products(self, request, pk=None):
        """
        工程に関連する製品を取得:
        - 連産品（仮想セット品番）: BOM.is_coproduct=true の親製品
        - 連産品の子品番: 連産品のBOM配下にある実際の製品
        - 使用する社内生産品: RoutingStepMaterial から取得した中間品
        - 使用する購入品: RoutingStepMaterial から取得した購入部品
        - BOM明細で工程が一致する子品番（中間品/連産品の子品番を補完）
        """
        process = self.get_object()
        products_map = {}  # key: product_id, value: {product, relation_type}

        # 1. この工程を含むルーティングステップを取得
        routing_steps = RoutingStep.objects.filter(process=process).select_related('routing')

        for step in routing_steps:
            routing = step.routing
            if not routing or not routing.product:
                continue

            # 1-0. この工程の出力品目（中間品）を追加
            output_product = step.output_product
            if output_product and output_product.id not in products_map:
                products_map[output_product.id] = {
                    'product': output_product,
                    'relation_type': 'output_product'
                }

            # 2. ルーティングの親製品を取得
            parent_product = routing.product

            # 2-1. 親製品が連産品かチェック
            try:
                bom = BOM.objects.get(parent_product=parent_product, is_coproduct=True)
                # 連産品の場合、親製品を追加
                if parent_product.id not in products_map:
                    products_map[parent_product.id] = {
                        'product': parent_product,
                        'relation_type': 'coproduct_parent'
                    }

                # 連産品の子品番を追加
                for child in bom.bom_items.all():
                    if child.child_product and child.child_product.id not in products_map:
                        products_map[child.child_product.id] = {
                            'product': child.child_product,
                            'relation_type': 'coproduct_child'
                        }
            except BOM.DoesNotExist:
                pass

            # 3. このルーティングステップで使用する材料を取得
            materials = RoutingStepMaterial.objects.filter(
                routing_step=step
            ).select_related('component')

            for material in materials:
                component = material.component
                if not component or component.id in products_map:
                    continue

                # カテゴリで社内生産品か購入品かを判定
                if component.category in ('ASSEMBLY', 'SINGLE'):
                    relation_type = 'intermediate'
                elif component.category in ('PURCHASED', 'MATERIAL'):
                    relation_type = 'purchased'
                else:
                    relation_type = 'other'

                products_map[component.id] = {
                    'product': component,
                    'relation_type': relation_type
                }

        # 4. BOM明細で工程が一致する子品番を追加（中間品/連産品の子品番補完）
        bom_items = BOMItem.objects.filter(process=process).select_related(
            'child_product',
            'bom__parent_product'
        )
        for item in bom_items:
            child = item.child_product
            if not child:
                continue
            if child.id not in products_map:
                relation_type = 'coproduct_child' if item.bom and item.bom.is_coproduct else 'bom_process_item'
                products_map[child.id] = {
                    'product': child,
                    'relation_type': relation_type
                }

            # 連産品BOMの場合は親（仮想セット）も追加
            if item.bom and item.bom.is_coproduct and item.bom.parent_product:
                parent = item.bom.parent_product
                if parent.id not in products_map:
                    products_map[parent.id] = {
                        'product': parent,
                        'relation_type': 'coproduct_parent'
                    }

        # 結果をシリアライズ
        result = []
        for item in products_map.values():
            product = item['product']
            result.append({
                'id': product.id,
                'product_code': product.product_code,
                'product_name': product.product_name,
                'category': product.category,
                'relation_type': item['relation_type']
            })

        return Response(result)


class LineViewSet(viewsets.ModelViewSet):
    queryset = Line.objects.all()
    serializer_class = LineSerializer
    filterset_fields = ['is_active']
    search_fields = ['line_code', 'line_name']
    ordering_fields = ['line_code', 'created_at']
    ordering = ['line_code']


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    search_fields = ['supplier_code', 'supplier_name']
    ordering_fields = ['supplier_code']
    ordering = ['supplier_code']


class CalendarViewSet(viewsets.ModelViewSet):
    queryset = Calendar.objects.all()
    serializer_class = CalendarSerializer
    search_fields = ['calendar_code', 'calendar_name']
    ordering_fields = ['calendar_code', 'created_at']
    ordering = ['calendar_code']


class WorkPatternViewSet(viewsets.ModelViewSet):
    queryset = WorkPattern.objects.all()
    serializer_class = WorkPatternSerializer
    search_fields = ['pattern_code', 'pattern_name']
    ordering_fields = ['pattern_code', 'created_at']
    ordering = ['pattern_code']


class BreakTimeViewSet(viewsets.ModelViewSet):
    queryset = BreakTime.objects.all()
    serializer_class = BreakTimeSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['work_pattern']
    ordering_fields = ['order']
    ordering = ['work_pattern', 'order']


class CalendarDayViewSet(viewsets.ModelViewSet):
    queryset = CalendarDay.objects.all()
    serializer_class = CalendarDaySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['calendar', 'is_working_day']
    ordering_fields = ['target_date']
    ordering = ['target_date']
    pagination_class = None  # all days are returned to support range updates

    def create(self, request, *args, **kwargs):
        """
        Upsert by (calendar, target_date) so bulk range registration does not
        fail with unique constraint errors when records already exist.
        """
        calendar_id = request.data.get('calendar')
        target_date = request.data.get('target_date')
        existing = None
        if calendar_id and target_date:
            existing = CalendarDay.objects.filter(
                calendar_id=calendar_id,
                target_date=target_date
            ).first()

        serializer = self.get_serializer(instance=existing, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        headers = {} if existing else self.get_success_headers(serializer.data)
        status_code = status.HTTP_200_OK if existing else status.HTTP_201_CREATED
        return Response(serializer.data, status=status_code, headers=headers)


class BOMViewSet(viewsets.ModelViewSet):
    queryset = BOM.objects.all()
    serializer_class = BOMSerializer
    filterset_fields = ['parent_product', 'is_active']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()

        # デバッグログ
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"BOM Filter Params: {dict(self.request.query_params)}")

        # 親製品（品番/品名）検索
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(parent_product__product_code__icontains=search) |
                Q(parent_product__product_name__icontains=search)
            )

        # 最終品フィルタ（親製品のis_final_productフィールドで絞り込み）
        is_final = self.request.query_params.get('parent_is_final', None)
        if is_final is not None and is_final != '':
            is_final_bool = is_final.lower() == 'true'
            queryset = queryset.filter(parent_product__is_final_product=is_final_bool)

        # ライン最終品フィルタ（親製品のis_line_final_productフィールドで絞り込み）
        is_line_final = self.request.query_params.get('parent_is_line_final', None)
        if is_line_final is not None and is_line_final != '':
            is_line_final_bool = is_line_final.lower() == 'true'
            queryset = queryset.filter(parent_product__is_line_final_product=is_line_final_bool)

        # 連産品フィルタ
        is_coproduct = self.request.query_params.get('is_coproduct', None)
        if is_coproduct is not None and is_coproduct != '':
            is_coproduct_bool = is_coproduct.lower() == 'true'
            queryset = queryset.filter(is_coproduct=is_coproduct_bool)

        # 版フィルタ
        version = self.request.query_params.get('version', None)
        if version:
            queryset = queryset.filter(version__icontains=version)

        # 作成日フィルタ（From）
        created_from = self.request.query_params.get('created_from', None)
        if created_from:
            logger.info(f"Filtering by created_from: {created_from}")
            from datetime import datetime
            created_from_dt = datetime.strptime(created_from, '%Y-%m-%d')
            queryset = queryset.filter(created_at__gte=created_from_dt)

        # 作成日フィルタ（To）
        created_to = self.request.query_params.get('created_to', None)
        if created_to:
            logger.info(f"Filtering by created_to: {created_to}")
            from datetime import datetime, timedelta
            created_to_dt = datetime.strptime(created_to, '%Y-%m-%d')
            # その日の23:59:59まで含めるため、翌日の00:00:00未満とする
            created_to_dt = created_to_dt + timedelta(days=1)
            queryset = queryset.filter(created_at__lt=created_to_dt)

        logger.info(f"Final queryset count: {queryset.count()}")
        return queryset

    def _serialize_product(self, product: Product):
        return {
            'id': product.id,
            'code': product.product_code,
            'name': product.product_name,
            'is_phantom': product.is_phantom,
        }

    def _pick_child_bom(self, product: Product):
        """Active BOM for child product (latest by valid_from)."""
        today = date.today()
        qs = BOM.objects.filter(
            parent_product=product,
            is_active=True,
            valid_from__lte=today,
        ).order_by('-valid_from', '-id')
        child = qs.first()
        if child:
            return child
        # fallback: any active BOM
        return BOM.objects.filter(
            parent_product=product,
            is_active=True,
        ).order_by('-valid_from', '-id').first()

    def _build_item_node(self, item: BOMItem, visited_bom_ids: set):
        child_bom = self._pick_child_bom(item.child_product)
        # prevent infinite loops
        if child_bom and child_bom.id in visited_bom_ids:
            child_tree = None
        elif child_bom:
            child_tree = self._build_bom_tree(child_bom, visited_bom_ids)
        else:
            child_tree = None

        return {
            'id': item.id,
            'bom': item.bom_id,
            'child_product': self._serialize_product(item.child_product),
            'quantity': str(item.quantity),
            'loss_rate': str(item.loss_rate) if item.loss_rate is not None else None,
            'sourcing_type': item.sourcing_type,
            'supplier': {
                'id': item.supplier_id,
                'name': item.supplier.supplier_name if item.supplier else None,
            } if item.supplier_id else None,
            'process': item.process_id,
            'process_name': item.process.process_name if item.process else None,
            'line': item.line_id,
            'line_name': item.line.line_name if item.line else None,
            'time_unit': item.time_unit,
            'lead_time_days': item.lead_time_days,
            'duration_min': item.duration_min,
            'remark': item.remark,
            'child_bom': child_tree,
        }

    def _build_bom_tree(self, bom: BOM, visited_bom_ids: set):
        visited_bom_ids.add(bom.id)
        items_qs = BOMItem.objects.filter(bom=bom).select_related('child_product', 'supplier')
        items = [self._build_item_node(item, visited_bom_ids) for item in items_qs]
        return {
            'id': bom.id,
            'parent_product': self._serialize_product(bom.parent_product),
            'version': bom.version,
            'valid_from': bom.valid_from,
            'valid_to': bom.valid_to,
            'is_active': bom.is_active,
            'items': items,
        }

    @action(detail=True, methods=['get'])
    def tree(self, request, pk=None):
        bom = self.get_object()
        tree = self._build_bom_tree(bom, visited_bom_ids=set())
        return Response(tree)

    def _collect_routing_items_recursive(self, bom: BOM, visited_bom_ids: set, collector: list, depth: int = 0, path_prefix: tuple = ()):
        """
        Depth-first collect routing items (MAKE/SUBCON) from bom and its descendants.

        - Child BOMs are traversed before appending the parent item (post-order) so
          downstream工程が先に生成される（前後関係を表す工程順に近づける）。
        - collector に (depth, path, item) を詰める。path は階層内の通し。
        """
        if bom.id in visited_bom_ids:
            return
        visited_bom_ids.add(bom.id)

        items_qs = BOMItem.objects.filter(bom=bom).select_related('child_product', 'process', 'line').order_by('id')
        for idx, item in enumerate(items_qs, start=1):
            child_bom = self._pick_child_bom(item.child_product)
            if child_bom:
                self._collect_routing_items_recursive(
                    child_bom,
                    visited_bom_ids,
                    collector,
                    depth=depth + 1,
                    path_prefix=path_prefix + (idx,)
                )
            if item.sourcing_type in ['MAKE', 'SUBCON']:
                collector.append((depth, path_prefix + (idx,), item))

    @action(detail=True, methods=['post'])
    def generate_routing(self, request, pk=None):
        """Generate or replace routing steps from BOM MAKE/SUBCON items (recursive)."""
        bom = self.get_object()
        routing_items_info = []
        self._collect_routing_items_recursive(bom, visited_bom_ids=set(), collector=routing_items_info)

        if not routing_items_info:
            return Response({'detail': 'No MAKE/SUBCON items found in this BOM tree. Nothing to generate.'}, status=status.HTTP_400_BAD_REQUEST)

        # Optional final step (manual input)
        final_process_id = request.data.get('final_process_id')
        final_line_id = request.data.get('final_line_id')
        final_time_unit = request.data.get('final_time_unit', 'MINUTE')
        final_lead_time_days = request.data.get('final_lead_time_days')
        final_duration_min = request.data.get('final_duration_min')

        final_process = None
        final_line = None

        if final_process_id:
            try:
                final_process = Process.objects.get(id=final_process_id)
            except Process.DoesNotExist:
                return Response({'detail': f'Final process not found: id={final_process_id}'}, status=status.HTTP_400_BAD_REQUEST)

            if final_line_id:
                try:
                    final_line = Line.objects.get(id=final_line_id)
                except Line.DoesNotExist:
                    return Response({'detail': f'Final line not found: id={final_line_id}'}, status=status.HTTP_400_BAD_REQUEST)

            if final_time_unit not in ['MINUTE', 'DAY']:
                return Response({'detail': 'final_time_unit must be MINUTE or DAY'}, status=status.HTTP_400_BAD_REQUEST)

            if final_time_unit == 'MINUTE':
                if not final_duration_min or int(final_duration_min) <= 0:
                    return Response({'detail': 'final_duration_min must be >0 when final_time_unit=MINUTE'}, status=status.HTTP_400_BAD_REQUEST)
                final_lead_time_days = 0
            else:
                if not final_lead_time_days or int(final_lead_time_days) <= 0:
                    return Response({'detail': 'final_lead_time_days must be >0 when final_time_unit=DAY'}, status=status.HTTP_400_BAD_REQUEST)
                final_duration_min = None

        # Validate each item has process/time info
        for _, _, it in routing_items_info:
            if not it.process_id:
                return Response({'detail': f'Process is required on BOM item {it.child_product.product_code} ({it.sourcing_type})'}, status=status.HTTP_400_BAD_REQUEST)
            if it.time_unit not in ['MINUTE', 'DAY']:
                return Response({'detail': f'Invalid time_unit on BOM item {it.child_product.product_code}'}, status=status.HTTP_400_BAD_REQUEST)
            if it.time_unit == 'MINUTE':
                if it.duration_min is None or it.duration_min <= 0:
                    return Response({'detail': f'duration_min must be >0 (MINUTE) on BOM item {it.child_product.product_code}'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                if it.lead_time_days <= 0:
                    return Response({'detail': f'lead_time_days must be >0 (DAY) on BOM item {it.child_product.product_code}'}, status=status.HTTP_400_BAD_REQUEST)

        routing_code = request.data.get('routing_code') or f"AUTO-{bom.parent_product.product_code}-{bom.version}"
        description = request.data.get('description') or f"Auto-generated from BOM {bom.id}"
        set_default = request.data.get('is_default', True)

        routing, created = Routing.objects.get_or_create(
            product=bom.parent_product,
            routing_code=routing_code,
            defaults={
                'description': description,
                'is_default': set_default,
                'is_active': True,
            }
        )

        routing.description = description
        routing.is_active = True
        if set_default:
            Routing.objects.filter(product=bom.parent_product).exclude(id=routing.id).update(is_default=False)
            routing.is_default = True
        routing.save()

        routing.steps.all().delete()
        created_steps = []
        for idx, (depth, path, item) in enumerate(routing_items_info, start=1):
            path_str = ".".join(str(p) for p in path) if path else "1"
            step = RoutingStep.objects.create(
                routing=routing,
                step_no=idx,
                process=item.process,
                line=item.line,
                output_product=item.child_product,
                hierarchy_depth=depth,
                hierarchy_path=path_str,
                time_unit=item.time_unit,
                lead_time_days=item.lead_time_days if item.time_unit == 'DAY' else 0,
                duration_min=item.duration_min if item.time_unit == 'MINUTE' else None,
                remark=f"Auto from BOM item {item.child_product.product_code} (path {path_str}, depth {depth})"
            )
            created_steps.append((item, step))

        # Append final step if provided
        if final_process:
            RoutingStep.objects.create(
                routing=routing,
                step_no=len(created_steps) + 1,
                process=final_process,
                line=final_line,
                output_product=bom.parent_product,
                hierarchy_depth=0,
                hierarchy_path="final",
                time_unit=final_time_unit,
                lead_time_days=int(final_lead_time_days) if final_time_unit == 'DAY' else 0,
                duration_min=int(final_duration_min) if final_time_unit == 'MINUTE' else None,
                remark='Final step (manual input)'
            )

        # 自動で工程別部品を付与（対象ステップの商品に紐づく子BOMの明細を消費部品とする）
        for item, step in created_steps:
            child_bom = self._pick_child_bom(item.child_product)
            if not child_bom:
                continue
            child_items = BOMItem.objects.filter(bom=child_bom).select_related('child_product')
            for child_item in child_items:
                RoutingStepMaterial.objects.create(
                    routing_step=step,
                    component=child_item.child_product,
                    quantity=child_item.quantity,
                    consume_timing='START',
                    remark=f"Auto from child BOM {child_bom.id}"
                )

        serialized = RoutingSerializer(routing)
        return Response(
            {
                'message': 'Routing generated from BOM (recursive)',
                'routing': serialized.data,
                'generated_steps': len(routing_items_info),
                'replaced_existing': not created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class BOMItemViewSet(viewsets.ModelViewSet):
    queryset = BOMItem.objects.all()
    serializer_class = BOMItemSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['bom', 'sourcing_type', 'process', 'line', 'time_unit', 'supplier']
    ordering_fields = ['created_at']
    ordering = ['id']


class RoutingViewSet(viewsets.ModelViewSet):
    queryset = Routing.objects.all()
    serializer_class = RoutingSerializer
    filterset_fields = ['product', 'is_active', 'is_default']
    ordering_fields = ['created_at']
    ordering = ['-created_at']


class RoutingStepViewSet(viewsets.ModelViewSet):
    queryset = RoutingStep.objects.all()
    serializer_class = RoutingStepSerializer
    filterset_fields = ['routing', 'process', 'line', 'time_unit']
    ordering_fields = ['step_no']
    ordering = ['routing', 'step_no']


class RoutingStepMaterialViewSet(viewsets.ModelViewSet):
    queryset = RoutingStepMaterial.objects.all().select_related('routing_step', 'component')
    serializer_class = RoutingStepMaterialSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['routing_step', 'component', 'consume_timing']
    search_fields = ['component__product_code', 'component__product_name']
    ordering_fields = ['routing_step', 'component']
    ordering = ['routing_step', 'component']
