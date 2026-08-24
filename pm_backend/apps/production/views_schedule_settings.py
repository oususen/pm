from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from production.models_auto_plan_aggregate_setting import AutoPlanAggregateSetting
from production.models_line_daily_schedule_setting import LineDailyScheduleSetting
from production.models_line_default_schedule_setting import LineDefaultScheduleSetting
from production.serializers import (
    AutoPlanAggregateSettingSerializer,
    LineDailyScheduleSettingSerializer,
    LineDefaultScheduleSettingSerializer,
)


class LineDailyScheduleSettingViewSet(viewsets.ModelViewSet):
    """ライン別日次スケジュール設定ViewSet"""

    queryset = LineDailyScheduleSetting.objects.all().select_related('line')
    serializer_class = LineDailyScheduleSettingSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['line', 'plan_date']
    ordering_fields = ['plan_date', 'line']
    ordering = ['plan_date', 'line']

    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        settings_data = request.data.get('settings', [])
        if not settings_data:
            return Response({'error': 'settings is required'}, status=status.HTTP_400_BAD_REQUEST)

        created_count = 0
        updated_count = 0
        errors = []

        for setting_data in settings_data:
            line_id = setting_data.get('line')
            plan_date = setting_data.get('plan_date')

            if not line_id or not plan_date:
                errors.append({'error': 'line and plan_date are required', 'data': setting_data})
                continue

            try:
                obj, created = LineDailyScheduleSetting.objects.update_or_create(
                    line_id=line_id,
                    plan_date=plan_date,
                    defaults={
                        'final_process_start_time': setting_data.get('final_process_start_time'),
                        'adjust_to_break_end': setting_data.get('adjust_to_break_end', True),
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            except Exception as e:
                errors.append({'error': str(e), 'data': setting_data})

        return Response(
            {'created': created_count, 'updated': updated_count, 'errors': errors},
            status=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS,
        )


class LineDefaultScheduleSettingViewSet(viewsets.ModelViewSet):
    """ライン別デフォルトスケジュール設定ViewSet"""

    queryset = LineDefaultScheduleSetting.objects.all().select_related('line')
    serializer_class = LineDefaultScheduleSettingSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['line']
    ordering_fields = ['line']
    ordering = ['line']

    def create(self, request, *args, **kwargs):
        line_id = request.data.get('line')
        if not line_id:
            return Response({'detail': 'line is required'}, status=status.HTTP_400_BAD_REQUEST)

        final_process_start_time = request.data.get('final_process_start_time')
        adjust_to_break_end = request.data.get('adjust_to_break_end', True)
        if isinstance(adjust_to_break_end, str):
            adjust_to_break_end = adjust_to_break_end.lower() in ('true', '1', 'yes')

        obj, created = LineDefaultScheduleSetting.objects.update_or_create(
            line_id=line_id,
            defaults={
                'final_process_start_time': final_process_start_time or None,
                'adjust_to_break_end': adjust_to_break_end,
                'updated_by': request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
            },
        )
        serializer = self.get_serializer(obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        settings_data = request.data.get('settings', [])
        if not settings_data:
            return Response({'error': 'settings is required'}, status=status.HTTP_400_BAD_REQUEST)

        created_count = 0
        updated_count = 0
        errors = []
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

        changed_line_ids = []
        for setting_data in settings_data:
            line_id = setting_data.get('line')
            if not line_id:
                errors.append({'error': 'line is required', 'data': setting_data})
                continue
            final_time = setting_data.get('final_process_start_time') or None
            adjust = setting_data.get('adjust_to_break_end', True)
            if isinstance(adjust, str):
                adjust = adjust.lower() in ('true', '1', 'yes')
            try:
                obj, created = LineDefaultScheduleSetting.objects.update_or_create(
                    line_id=line_id,
                    defaults={
                        'final_process_start_time': final_time,
                        'adjust_to_break_end': adjust,
                        'updated_by': user,
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                changed_line_ids.append(line_id)
            except Exception as e:
                errors.append({'error': str(e), 'data': setting_data})

        if changed_line_ids:
            LineDailyScheduleSetting.objects.filter(line_id__in=changed_line_ids).delete()

        return Response(
            {'created': created_count, 'updated': updated_count, 'errors': errors},
            status=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS,
        )


class AutoPlanAggregateSettingViewSet(viewsets.ModelViewSet):
    """自動計画まとめ生産設定ViewSet"""

    queryset = AutoPlanAggregateSetting.objects.all().select_related('line', 'product')
    serializer_class = AutoPlanAggregateSettingSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['line', 'product', 'is_active']
    search_fields = ['line__line_code', 'line__line_name', 'product__product_code', 'product__product_name']
    ordering_fields = ['line__line_code', 'product__product_code', 'aggregate_weekday', 'aggregate_days', 'updated_at']
    ordering = ['line__line_code', 'product__product_code']

    def perform_create(self, serializer):
        user = self.request.user if getattr(self.request, 'user', None) and self.request.user.is_authenticated else None
        serializer.save(updated_by=user)

    def perform_update(self, serializer):
        user = self.request.user if getattr(self.request, 'user', None) and self.request.user.is_authenticated else None
        serializer.save(updated_by=user)
