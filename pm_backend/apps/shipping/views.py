import django_filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import ShipmentActual, ShipmentActualHistory, ShipToLeadTime
from .serializers import ShipmentActualHistorySerializer, ShipmentActualSerializer, ShipToLeadTimeSerializer


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


class ShipToLeadTimeViewSet(viewsets.ModelViewSet):
    """納入地別出荷加算日数ViewSet"""
    queryset = ShipToLeadTime.objects.select_related('customer').all()
    serializer_class = ShipToLeadTimeSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['customer', 'is_active']
    ordering = ['customer__customer_code', 'ship_to_code']
