from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Order, OrderLine, StgOrderRaw, StgOrderDaily
from .serializers import (
    OrderSerializer,
    OrderLineSerializer,
    StgOrderRawSerializer,
    StgOrderDailySerializer
)
from .services.csv_import import CSVImportService


class OrderViewSet(viewsets.ModelViewSet):
    """受注ヘッダViewSet"""
    queryset = Order.objects.all().select_related('customer').prefetch_related('lines')
    serializer_class = OrderSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['customer', 'order_type', 'status', 'order_date']
    search_fields = ['order_no', 'source_file']
    ordering_fields = ['order_date', 'created_at']
    ordering = ['-order_date', '-created_at']


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

            # Import CSV
            service = CSVImportService()
            result = service.import_csv(file, customer_code, order_type, source_system)

            if result['success']:
                return Response(result, status=status.HTTP_201_CREATED)
            else:
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


class StgOrderDailyViewSet(viewsets.ModelViewSet):
    """受注取込ステージング（日別）ViewSet"""
    queryset = StgOrderDaily.objects.all().select_related('customer', 'raw')
    serializer_class = StgOrderDailySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['customer', 'order_type', 'due_date']
    search_fields = ['product_code']
    ordering_fields = ['due_date', 'created_at']
    ordering = ['due_date']
