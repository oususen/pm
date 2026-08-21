import django_filters
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from masters.models import Process
from .models_gantt_display_product_map import GanttDisplayProductMap
from .models_gantt_process_display_order import GanttProcessDisplayOrder
from .serializers_gantt_display_product_map import GanttDisplayProductMapSerializer
from .serializers_gantt_process_display_order import GanttProcessDisplayOrderSerializer


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
            Q(line__line_code__iexact=value) |
            Q(line__line_name__icontains=value)
        )

    def filter_process_search(self, queryset, _name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(process__process_code__iexact=value) |
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

    @action(detail=False, methods=['get', 'post'], url_path='process-display-orders')
    def process_display_orders(self, request):
        if request.method.lower() == 'get':
            line_id = request.query_params.get('line')
            if not line_id:
                return Response([], status=status.HTTP_200_OK)

            process_ids = set(
                Process.objects.filter(line_id=line_id).values_list('id', flat=True)
            )
            process_ids.update(
                GanttDisplayProductMap.objects.filter(line_id=line_id).values_list('process_id', flat=True)
            )

            processes = list(
                Process.objects.filter(id__in=process_ids).order_by('process_code', 'id')
            )
            saved_rows = {
                row.process_id: row
                for row in GanttProcessDisplayOrder.objects.filter(line_id=line_id).select_related('line', 'process')
            }

            rows = []
            for idx, process in enumerate(processes):
                saved = saved_rows.get(process.id)
                rows.append({
                    'id': saved.id if saved else None,
                    'line': int(line_id),
                    'line_code': process.line.line_code if process.line_id else '',
                    'line_name': process.line.line_name if process.line_id else '',
                    'process': process.id,
                    'process_code': process.process_code or '',
                    'process_name': process.process_name or '',
                    'display_order': saved.display_order if saved else idx,
                    'updated_at': saved.updated_at if saved else None,
                    'updated_by': saved.updated_by_id if saved else None,
                    'is_saved': bool(saved),
                })

            rows.sort(key=lambda row: (row['display_order'], row['process_code'], row['process']))
            return Response(rows)

        line_id = request.data.get('line_id')
        items = request.data.get('items', [])
        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        process_ids = [item.get('process') for item in items if item.get('process')]
        valid_processes = {
            proc.id: proc
            for proc in Process.objects.filter(id__in=process_ids)
        }
        missing_ids = [pid for pid in process_ids if pid not in valid_processes]
        if missing_ids:
            return Response({'detail': '存在しない工程が含まれています。'}, status=status.HTTP_400_BAD_REQUEST)

        invalid_ids = [proc.id for proc in valid_processes.values() if proc.line_id and str(proc.line_id) != str(line_id)]
        if invalid_ids:
            return Response({'detail': '指定ラインに属さない工程が含まれています。'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user if request.user.is_authenticated else None
        GanttProcessDisplayOrder.objects.filter(line_id=line_id).delete()
        objs = [
            GanttProcessDisplayOrder(
                line_id=line_id,
                process_id=item['process'],
                display_order=item.get('display_order', idx),
                updated_by=user,
            )
            for idx, item in enumerate(items)
            if item.get('process')
        ]
        GanttProcessDisplayOrder.objects.bulk_create(objs)
        saved = GanttProcessDisplayOrder.objects.filter(line_id=line_id).select_related('line', 'process')
        return Response(GanttProcessDisplayOrderSerializer(saved, many=True).data)
