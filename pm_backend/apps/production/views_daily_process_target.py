from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models_daily_process_target import DailyProcessTarget
from .serializers import DailyProcessTargetSerializer


class DailyProcessTargetViewSet(viewsets.ModelViewSet):
    """日別工程目標のCRUD。"""

    serializer_class = DailyProcessTargetSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = DailyProcessTarget.objects.select_related('line', 'process', 'created_by', 'updated_by')

        line_id = self.request.query_params.get('line')
        process_id = self.request.query_params.get('process')
        plan_date = self.request.query_params.get('plan_date')
        plan_date_gte = self.request.query_params.get('plan_date__gte') or self.request.query_params.get('plan_date_from')
        plan_date_lte = self.request.query_params.get('plan_date__lte') or self.request.query_params.get('plan_date_to')

        if line_id:
            qs = qs.filter(line_id=line_id)
        if process_id:
            qs = qs.filter(process_id=process_id)
        if plan_date:
            qs = qs.filter(plan_date=plan_date)
        if plan_date_gte:
            qs = qs.filter(plan_date__gte=plan_date_gte)
        if plan_date_lte:
            qs = qs.filter(plan_date__lte=plan_date_lte)
        return qs.order_by('plan_date', 'target_time', 'id')
