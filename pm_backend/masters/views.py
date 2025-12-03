from rest_framework import viewsets
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


class BOMItemViewSet(viewsets.ModelViewSet):
    queryset = BOMItem.objects.all()
    serializer_class = BOMItemSerializer
    filterset_fields = ['bom', 'sourcing_type']
    ordering_fields = ['created_at']


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
