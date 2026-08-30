import django_filters
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from .models import LineDemand
from .serializers import LineDemandSerializer
from .services.order_expansion import OrderExpansionService


class LineDemandFilter(django_filters.FilterSet):
    """LineDemandのカスタムフィルタ"""

    plan_date__gte = django_filters.DateFilter(field_name='plan_date', lookup_expr='gte')
    plan_date__lte = django_filters.DateFilter(field_name='plan_date', lookup_expr='lte')
    product__in = django_filters.CharFilter(method='filter_product_in')
    line_search = django_filters.CharFilter(method='filter_line_search')
    process_search = django_filters.CharFilter(method='filter_process_search')
    product_search = django_filters.CharFilter(method='filter_product_search')

    class Meta:
        model = LineDemand
        fields = ['line', 'routing_step', 'product', 'plan_date', 'ship_to_code']

    def filter_line_search(self, queryset, name, value):
        if value:
            return queryset.filter(
                Q(line__line_code__iexact=value) | Q(line__line_name__icontains=value)
            )
        return queryset

    def filter_process_search(self, queryset, name, value):
        if value:
            return queryset.filter(
                Q(process__process_code__iexact=value)
                | Q(process__process_name__icontains=value)
            )
        return queryset

    def filter_product_search(self, queryset, name, value):
        if value:
            return queryset.filter(
                Q(product__product_code__icontains=value)
                | Q(product__product_name__icontains=value)
                | Q(product_code__icontains=value)
            )
        return queryset

    def filter_product_in(self, queryset, name, value):
        """カンマ区切りの製品IDリストでフィルタ"""
        if value:
            try:
                product_ids = [int(x.strip()) for x in value.split(',') if x.strip()]
                return queryset.filter(product_id__in=product_ids)
            except (ValueError, TypeError):
                return queryset.none()
        return queryset


class LineDemandViewSet(viewsets.ModelViewSet):
    """ライン需要展開ViewSet"""

    queryset = LineDemand.objects.all().select_related(
        'line',
        'product',
        'process',
        'routing_step',
    )
    serializer_class = LineDemandSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = LineDemandFilter
    search_fields = ['product_code', 'order_numbers']
    ordering_fields = ['plan_date', 'line', 'product_code', 'created_at']
    ordering = ['plan_date', 'line']

    @action(detail=False, methods=['post'])
    def expand(self, request):
        """OPEN受注をライン別に展開してt_line_demandを再生成"""
        clear_param = request.data.get('clear_existing', False)
        if isinstance(clear_param, str):
            clear_existing = clear_param.lower() not in ['false', '0', 'no']
        else:
            clear_existing = bool(clear_param)

        service = OrderExpansionService()
        result = service.expand_open_orders(clear_existing=clear_existing)

        status_code = (
            status.HTTP_201_CREATED
            if not result.get('errors')
            else status.HTTP_400_BAD_REQUEST
        )
        return Response(result, status=status_code)
