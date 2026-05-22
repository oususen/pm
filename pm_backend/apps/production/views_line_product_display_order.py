import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from .models_line_product_display_order import LineProductDisplayOrder
from .serializers_line_product_display_order import LineProductDisplayOrderSerializer


class LineProductDisplayOrderFilter(django_filters.FilterSet):
    line = django_filters.NumberFilter(field_name='line_id')
    context = django_filters.CharFilter(field_name='context')

    class Meta:
        model = LineProductDisplayOrder
        fields = []


class LineProductDisplayOrderViewSet(viewsets.ModelViewSet):
    queryset = LineProductDisplayOrder.objects.all().select_related('line')
    serializer_class = LineProductDisplayOrderSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = LineProductDisplayOrderFilter
    ordering_fields = ['display_order', 'product_code']
    ordering = ['display_order']

    @action(detail=False, methods=['post'], url_path='bulk-save')
    def bulk_save(self, request):
        line_id = request.data.get('line_id')
        context_key = request.data.get('context', 'default')
        items = request.data.get('items', [])
        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        LineProductDisplayOrder.objects.filter(line_id=line_id, context=context_key).delete()
        objs = [
            LineProductDisplayOrder(
                line_id=line_id,
                product_code=item['product_code'],
                display_order=item['display_order'],
                context=context_key,
                bg_color=item.get('bg_color', ''),
                text_color=item.get('text_color', ''),
                plan_bg_color=item.get('plan_bg_color', ''),
                plan_text_color=item.get('plan_text_color', ''),
            )
            for item in items
        ]
        LineProductDisplayOrder.objects.bulk_create(objs)
        return Response({'detail': 'ok', 'count': len(objs)})
