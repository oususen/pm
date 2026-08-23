import django_filters
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.views import APIView

from .models_laser_actual import LaserActual, LaserActualDetail
from .models_laser_kadojiseki import LaserShiftRecord
from .models_laser_pattern import LaserPattern
from .services.laser_service import (
    build_laser_monthly_material_summary,
    delete_laser_actual,
    list_current_processing_laser_actuals,
    update_laser_actual_detail_quantity,
)
from .serializers import (
    LaserActualSerializer,
    LaserPatternSerializer,
    LaserShiftRecordSerializer,
)


class LaserPatternViewSet(viewsets.ModelViewSet):
    """レーザパターンマスタ編集用ViewSet"""

    queryset = LaserPattern.objects.all().select_related('material', 'equipment').prefetch_related(
        'component_items__component_product',
        'finished_items__finished_product',
    )
    serializer_class = LaserPatternSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['pattern_no', 'material__product_code', 'material__product_name']
    ordering_fields = ['pattern_no', 'updated_at', 'created_at']
    ordering = ['pattern_no']

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('show_inactive') != 'true':
            qs = qs.filter(is_active=True)
        return qs

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        actual_count = instance.laser_actuals.count()
        if actual_count > 0:
            return Response(
                {'detail': f'このパターンには実績が {actual_count} 件あるため削除できません。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='monthly-material-summary')
    def monthly_material_summary(self, request):
        data, status_code = build_laser_monthly_material_summary(
            request.query_params,
            self.get_queryset(),
        )
        return Response(data, status=status_code)

    @action(detail=True, methods=['post'])
    def copy(self, request, pk=None):
        """既存パターンを複製（コピー先パターン番号は手入力）"""
        source = self.get_object()
        new_pattern_no = str(request.data.get('pattern_no') or '').strip()
        if not new_pattern_no:
            return Response({'detail': 'pattern_no is required'}, status=status.HTTP_400_BAD_REQUEST)
        if LaserPattern.objects.filter(pattern_no=new_pattern_no).exists():
            return Response({'detail': 'pattern_no already exists'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            copied = LaserPattern.objects.create(
                pattern_no=new_pattern_no,
                material=source.material,
                equipment=source.equipment,
                process_time_min=source.process_time_min,
                is_budget_target=source.is_budget_target,
            )
            copied.component_items.bulk_create([
                item.__class__(
                    pattern=copied,
                    component_product=item.component_product,
                    take_qty=item.take_qty,
                )
                for item in source.component_items.all()
            ])
            copied.finished_items.bulk_create([
                item.__class__(
                    pattern=copied,
                    finished_product=item.finished_product,
                    units_per_shot=item.units_per_shot,
                )
                for item in source.finished_items.all()
            ])

        serializer = self.get_serializer(copied)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LaserActualFilter(django_filters.FilterSet):
    session_id = django_filters.NumberFilter(field_name='id')
    work_date__gte = django_filters.DateFilter(field_name='work_date', lookup_expr='gte')
    work_date__lte = django_filters.DateFilter(field_name='work_date', lookup_expr='lte')
    equipment = django_filters.NumberFilter(field_name='equipment_id')
    pattern = django_filters.NumberFilter(field_name='pattern_id')
    pattern_no = django_filters.CharFilter(method='filter_pattern_no')
    operator_action = django_filters.CharFilter(field_name='operator_action')

    class Meta:
        model = LaserActual
        fields = []

    def filter_pattern_no(self, queryset, name, value):
        keyword = str(value or '').strip()
        if not keyword:
            return queryset
        return queryset.filter(pattern_no__icontains=keyword)


class LaserActualViewSet(viewsets.ModelViewSet):
    """レーザー実績（ヘッダ+明細）"""

    queryset = (
        LaserActual.objects.all()
        .select_related('equipment', 'equipment__process', 'pattern', 'material', 'created_by', 'updated_by')
        .prefetch_related('details')
    )
    serializer_class = LaserActualSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = LaserActualFilter
    search_fields = ['pattern_no', 'equipment_code', 'equipment_name', 'material_code', 'material_name']
    ordering_fields = ['work_date', 'created_at', 'pattern_no', 'shot_count', 'total_process_time']
    ordering = ['-work_date', '-created_at', '-id']

    @action(detail=False, methods=['get'], url_path='current-processing')
    def current_processing(self, request):
        return Response(
            list_current_processing_laser_actuals(
                request.query_params.get('scan_limit', 2000)
            )
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            delete_laser_actual(instance)
        except Exception as exc:
            return Response(
                {'detail': f'レーザー実績の削除に失敗しました: {str(exc)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class LaserActualDetailUpdateView(APIView):
    """レーザー実績明細（品番別）の数量個別更新"""

    @transaction.atomic
    def patch(self, request, detail_id):
        data, status_code = update_laser_actual_detail_quantity(
            detail_id,
            request.data.get('total_qty'),
        )
        return Response(data, status=status_code)


class LaserShiftRecordFilter(django_filters.FilterSet):
    work_date__gte = django_filters.DateFilter(field_name='work_date', lookup_expr='gte')
    work_date__lte = django_filters.DateFilter(field_name='work_date', lookup_expr='lte')
    equipment = django_filters.NumberFilter(field_name='equipment_id')
    shift_no = django_filters.NumberFilter(field_name='shift_no')

    class Meta:
        model = LaserShiftRecord
        fields = []


class LaserShiftRecordViewSet(viewsets.ModelViewSet):
    """レーザーシフト稼働記録（開始・終了の2段階入力）"""

    queryset = LaserShiftRecord.objects.all().select_related('equipment', 'created_by', 'updated_by')
    serializer_class = LaserShiftRecordSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = LaserShiftRecordFilter
    ordering_fields = ['work_date', 'equipment', 'shift_no', 'created_at']
    ordering = ['-work_date', 'equipment', 'shift_no']
