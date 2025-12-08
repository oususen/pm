from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from datetime import date
from .models import (
    Product, Customer, Process, Line, Supplier, Calendar, CalendarDay,
    BOM, BOMItem, Routing, RoutingStep
)
from .serializers import (
    ProductSerializer, CustomerSerializer, ProcessSerializer, LineSerializer,
    SupplierSerializer, CalendarSerializer, CalendarDaySerializer,
    BOMSerializer, BOMItemSerializer, RoutingSerializer, RoutingStepSerializer
)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['product_code', 'product_name']
    ordering_fields = ['product_code', 'created_at']
    ordering = ['product_code']


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


class CalendarDayViewSet(viewsets.ModelViewSet):
    queryset = CalendarDay.objects.all()
    serializer_class = CalendarDaySerializer
    filterset_fields = ['calendar', 'is_working_day']
    ordering_fields = ['target_date']
    ordering = ['target_date']


class BOMViewSet(viewsets.ModelViewSet):
    queryset = BOM.objects.all()
    serializer_class = BOMSerializer
    filterset_fields = ['parent_product', 'is_active']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

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

    @action(detail=True, methods=['post'])
    def generate_routing(self, request, pk=None):
        """Generate or replace routing steps from BOM MAKE items."""
        bom = self.get_object()
        make_items = list(BOMItem.objects.filter(bom=bom, sourcing_type='MAKE').select_related('child_product', 'process', 'line'))
        if not make_items:
            return Response({'detail': 'No MAKE items found in this BOM. Nothing to generate.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate each item has process/time info
        for it in make_items:
            if not it.process_id:
                return Response({'detail': f'Process is required on BOM item {it.child_product.product_code}'}, status=status.HTTP_400_BAD_REQUEST)
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
        for idx, item in enumerate(make_items, start=1):
            RoutingStep.objects.create(
                routing=routing,
                step_no=idx,
                process=item.process,
                line=item.line,
                time_unit=item.time_unit,
                lead_time_days=item.lead_time_days if item.time_unit == 'DAY' else 0,
                duration_min=item.duration_min if item.time_unit == 'MINUTE' else None,
                remark=f"Auto from BOM item {item.child_product.product_code}"
            )

        serialized = RoutingSerializer(routing)
        return Response(
            {
                'message': 'Routing generated from BOM',
                'routing': serialized.data,
                'generated_steps': len(make_items),
                'replaced_existing': not created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class BOMItemViewSet(viewsets.ModelViewSet):
    queryset = BOMItem.objects.all()
    serializer_class = BOMItemSerializer
    filterset_fields = ['bom', 'sourcing_type', 'process', 'line', 'time_unit']
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
