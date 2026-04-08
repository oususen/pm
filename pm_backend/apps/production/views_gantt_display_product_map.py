import django_filters
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from .models_gantt_display_product_map import GanttDisplayProductMap
from .serializers_gantt_display_product_map import GanttDisplayProductMapSerializer


class GanttDisplayProductMapFilter(django_filters.FilterSet):
    line = django_filters.NumberFilter(field_name='line_id')
    final_product = django_filters.NumberFilter(field_name='final_product_id')
    process = django_filters.NumberFilter(field_name='process_id')
    display_product = django_filters.NumberFilter(field_name='display_product_id')
    line_search = django_filters.CharFilter(method='filter_line_search')
    process_search = django_filters.CharFilter(method='filter_process_search')
    product_search = django_filters.CharFilter(method='filter_product_search')

    class Meta:
        model = GanttDisplayProductMap
        fields = []

    def filter_line_search(self, queryset, _name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(line__line_code__icontains=value) |
            Q(line__line_name__icontains=value)
        )

    def filter_process_search(self, queryset, _name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(process__process_code__icontains=value) |
            Q(process__process_name__icontains=value)
        )

    def filter_product_search(self, queryset, _name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(final_product__product_code__icontains=value) |
            Q(final_product__product_name__icontains=value) |
            Q(display_product__product_code__icontains=value) |
            Q(display_product__product_name__icontains=value)
        )


class GanttDisplayProductMapViewSet(viewsets.ModelViewSet):
    queryset = GanttDisplayProductMap.objects.all().select_related(
        'line',
        'final_product',
        'process',
        'display_product',
    )
    serializer_class = GanttDisplayProductMapSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = GanttDisplayProductMapFilter
    search_fields = [
        'line__line_code',
        'line__line_name',
        'final_product__product_code',
        'final_product__product_name',
        'process__process_code',
        'process__process_name',
        'display_product__product_code',
        'display_product__product_name',
    ]
    ordering_fields = [
        'id',
        'line__line_code',
        'final_product__product_code',
        'process__process_code',
        'display_product__product_code',
        'updated_at',
    ]
    ordering = ['line__line_code', 'final_product__product_code', 'process__process_code', 'display_product__product_code', 'id']

    def perform_create(self, serializer):
        user = self.request.user if self.request and self.request.user.is_authenticated else None
        serializer.save(updated_by=user)

    def perform_update(self, serializer):
        user = self.request.user if self.request and self.request.user.is_authenticated else None
        serializer.save(updated_by=user)
