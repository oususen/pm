import logging

from rest_framework.views import APIView

from production.services import (
    schedule_reconcile_service,
    scheduled_task_config_service,
    scheduled_task_execution_service,
    scheduled_task_query_service,
)

logger = logging.getLogger(__name__)


class ScheduleConfigView(APIView):
    """定時タスクスケジュール設定API"""

    def get(self, request):
        return scheduled_task_config_service.get_configs(request=request, logger=logger)

    def post(self, request):
        return scheduled_task_config_service.save_config(request=request, logger=logger)


class ScheduleRunLogView(APIView):
    """定時タスク実行履歴（直近分）"""

    def get(self, request):
        return scheduled_task_query_service.get_run_logs(request=request, logger=logger)


class ScheduleRunNowView(APIView):
    """定時タスクを手動実行（非同期）"""

    def post(self, request):
        return scheduled_task_execution_service.run_now(request=request, logger=logger)


class PurchaseActualReconcileReportView(APIView):
    """納入実績整合チェックのレポート取得API"""

    def get(self, request):
        return schedule_reconcile_service.get_purchase_actual_reconcile_report(request=request, logger=logger)


class PurchaseActualReconcileFixView(APIView):
    """納入実績整合チェックの手動修正実行API"""

    def post(self, request):
        return schedule_reconcile_service.run_purchase_actual_reconcile_fix(request=request, logger=logger)


class ProductionActualReconcileReportView(APIView):
    """生産実績整合チェックのレポート取得API"""

    def get(self, request):
        return schedule_reconcile_service.get_production_actual_reconcile_report(request=request, logger=logger)


class ProductionActualReconcileFixView(APIView):
    """生産実績整合チェックの手動修正実行API"""

    def post(self, request):
        return schedule_reconcile_service.run_production_actual_reconcile_fix(request=request, logger=logger)


class ScheduleCancelView(APIView):
    """定時タスクのキャンセル要求API（実行中タスク向け）"""

    def post(self, request):
        return scheduled_task_execution_service.request_cancel(request=request, logger=logger)
