import io

import django_filters
from django.http import HttpResponse
from openpyxl import Workbook
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q

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
    queryset = (
        ShipmentActual.objects.all()
        .select_related('product', 'customer', 'shipping_trip_allocation__trip__departed_by')
        .prefetch_related('splits')
    )
    serializer_class = ShipmentActualSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ShipmentActualFilter
    search_fields = ['product_code', 'customer_code', 'ship_to_code']
    ordering_fields = ['shipment_date', 'product_code', 'customer_code', 'created_at']
    ordering = ['-shipment_date', 'product_code']

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        departure_date_gte = params.get('departure_date__gte')
        if departure_date_gte:
            qs = qs.filter(shipping_trip_allocation__trip__departure_date__gte=departure_date_gte)

        departure_date_lte = params.get('departure_date__lte')
        if departure_date_lte:
            qs = qs.filter(shipping_trip_allocation__trip__departure_date__lte=departure_date_lte)

        source_order_no = str(params.get('source_order_no') or '').strip()
        if source_order_no:
            qs = qs.filter(splits__source_order_no__icontains=source_order_no)

        trip_keyword = str(params.get('trip_keyword') or '').strip()
        if trip_keyword:
            qs = qs.filter(
                Q(shipping_trip_allocation__trip__trip_code__icontains=trip_keyword) |
                Q(shipping_trip_allocation__trip__trip_ref__icontains=trip_keyword)
            )

        business_type = str(params.get('business_type') or '').strip()
        if business_type:
            qs = qs.filter(shipping_trip_allocation__trip__business_type=business_type)

        return qs.distinct()

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
        self._create_history(before, 'UPDATE_BEFORE')
        instance = serializer.save()
        self._create_history(instance, 'UPDATE_AFTER')

    def perform_destroy(self, instance):
        self._create_history(instance, 'DELETE')
        instance.delete()

    @action(detail=False, methods=['get'], url_path='export-excel')
    def export_excel(self, request):
        queryset = self.filter_queryset(self.get_queryset())

        wb = Workbook()
        ws = wb.active
        ws.title = '出荷実績'
        ws.append(['出発日', '到着日', '品番', '数量', '生産日', '注番'])

        for actual in queryset:
            trip = getattr(getattr(actual, 'shipping_trip_allocation', None), 'trip', None)
            departure_date = getattr(trip, 'departure_date', None) or actual.shipment_date
            arrival_date = actual.shipment_date
            product_code = actual.product_code or ''
            splits = list(actual.splits.all())

            if splits:
                for split in splits:
                    ws.append([
                        departure_date.isoformat() if departure_date else '',
                        arrival_date.isoformat() if arrival_date else '',
                        product_code,
                        float(split.quantity or 0),
                        split.production_date.isoformat() if split.production_date else '',
                        split.source_order_no or '',
                    ])
                continue

            ws.append([
                departure_date.isoformat() if departure_date else '',
                arrival_date.isoformat() if arrival_date else '',
                product_code,
                float(actual.quantity or 0),
                '',
                '',
            ])

        for col, width in {'A': 14, 'B': 14, 'C': 18, 'D': 12, 'E': 14, 'F': 18}.items():
            ws.column_dimensions[col].width = width

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="出荷実績.xlsx"'
        return response

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        histories = ShipmentActualHistory.objects.filter(
            shipment_actual_id=pk
        ).order_by('-id')
        serializer = ShipmentActualHistorySerializer(histories, many=True)
        return Response(serializer.data)


class ShipToLeadTimeViewSet(viewsets.ModelViewSet):
    """納入地別出荷加算日数ViewSet"""
    queryset = ShipToLeadTime.objects.select_related('customer', 'calendar').prefetch_related('color_exclusions').all()
    serializer_class = ShipToLeadTimeSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['customer', 'is_active']
    ordering = ['customer__customer_code', 'ship_to_code']

    @action(detail=False, methods=['get'], url_path='ship-to-codes')
    def ship_to_codes(self, request):
        """顧客IDから受注データ上の納入先コード一覧を返す"""
        customer_id = request.query_params.get('customer_id')
        if not customer_id:
            return Response([])
        from orders.core.models import StgOrderDaily
        codes = (
            StgOrderDaily.objects
            .filter(customer_id=customer_id, ship_to_code__isnull=False)
            .exclude(ship_to_code='')
            .values_list('ship_to_code', flat=True)
            .distinct()
            .order_by('ship_to_code')
        )
        return Response(list(codes))
