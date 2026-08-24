import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from production.models_purchase_actual_reconcile import (
    PurchaseActualReconcileReport,
    PurchaseActualReconcileReportDetail,
)
from production.models_production_actual_reconcile import (
    ProductionActualReconcileReport,
    ProductionActualReconcileReportDetail,
)
from production.models_schedule_config import ScheduleConfig, ScheduleRunLog
from production.serializers import (
    ScheduleRunLogSerializer,
    PurchaseActualReconcileReportSerializer,
    PurchaseActualReconcileReportDetailSerializer,
    ProductionActualReconcileReportSerializer,
    ProductionActualReconcileReportDetailSerializer,
)
from production.services import scheduled_task_config_service, scheduled_task_execution_service

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
        config_id = request.query_params.get('config_id')
        if not config_id:
            return Response({'detail': 'config_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        logs = ScheduleRunLog.objects.filter(config_id=config_id).order_by('-started_at')[:30]
        serializer = ScheduleRunLogSerializer(logs, many=True)
        return Response(serializer.data)


class ScheduleRunNowView(APIView):
    """定時タスクを手動実行（非同期）"""

    def post(self, request):
        return scheduled_task_execution_service.run_now(request=request, logger=logger)


class PurchaseActualReconcileReportView(APIView):
    """納入実績整合チェックのレポート取得API"""

    def get(self, request):
        limit = request.query_params.get('limit', 10)
        detail_limit = request.query_params.get('detail_limit', 200)
        report_id = request.query_params.get('report_id')

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 50))

        try:
            detail_limit = int(detail_limit)
        except (TypeError, ValueError):
            detail_limit = 200
        detail_limit = max(1, min(detail_limit, 1000))

        report_qs = (
            PurchaseActualReconcileReport.objects
            .select_related('task_config', 'created_by')
            .order_by('-id')
        )
        if report_id:
            report_qs = report_qs.filter(id=report_id)

        reports = list(report_qs[:limit])
        latest = reports[0] if reports else None
        detail_rows = []
        if latest:
            detail_rows = list(
                PurchaseActualReconcileReportDetail.objects
                .filter(report_id=latest.id)
                .select_related('line', 'process', 'product')
                .order_by('plan_date', 'line__line_code', 'product__product_code')[:detail_limit]
            )

        return Response({
            'reports': PurchaseActualReconcileReportSerializer(reports, many=True).data,
            'details': PurchaseActualReconcileReportDetailSerializer(detail_rows, many=True).data,
            'latest_report_id': latest.id if latest else None,
        })


class PurchaseActualReconcileFixView(APIView):
    """納入実績整合チェックの手動修正実行API"""

    def post(self, request):
        from .scheduler.tasks_purchase_actual_reconcile import run_purchase_actual_reconcile_check

        task_name = 'PURCHASE_ACTUAL_RECONCILE_CHECK'
        running = ScheduleConfig.objects.filter(task_name=task_name, last_run_status='RUNNING').exists()
        if running:
            return Response(
                {'detail': '現在整合チェックが実行中です。完了後に再実行してください。'},
                status=status.HTTP_409_CONFLICT,
            )

        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        try:
            result = run_purchase_actual_reconcile_check(apply_fix=True, created_by=user)
            return Response({
                'detail': '修正を実行しました。',
                **result,
            })
        except Exception as e:
            logger.exception('納入実績整合修正に失敗')
            return Response(
                {'detail': f'修正に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ProductionActualReconcileReportView(APIView):
    """生産実績整合チェックのレポート取得API"""

    def get(self, request):
        limit = request.query_params.get('limit', 10)
        detail_limit = request.query_params.get('detail_limit', 200)
        report_id = request.query_params.get('report_id')

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 50))

        try:
            detail_limit = int(detail_limit)
        except (TypeError, ValueError):
            detail_limit = 200
        detail_limit = max(1, min(detail_limit, 1000))

        report_qs = (
            ProductionActualReconcileReport.objects
            .select_related('task_config', 'created_by')
            .order_by('-id')
        )
        if report_id:
            report_qs = report_qs.filter(id=report_id)

        reports = list(report_qs[:limit])
        latest = reports[0] if reports else None
        detail_rows = []
        if latest:
            detail_rows = list(
                ProductionActualReconcileReportDetail.objects
                .filter(report_id=latest.id)
                .select_related('line', 'process', 'product')
                .order_by('plan_date', 'line__line_code', 'product__product_code')[:detail_limit]
            )

        return Response({
            'reports': ProductionActualReconcileReportSerializer(reports, many=True).data,
            'details': ProductionActualReconcileReportDetailSerializer(detail_rows, many=True).data,
            'latest_report_id': latest.id if latest else None,
        })


class ProductionActualReconcileFixView(APIView):
    """生産実績整合チェックの手動修正実行API"""

    def post(self, request):
        from .scheduler.tasks_production_actual_reconcile import run_production_actual_reconcile_check

        task_name = 'PRODUCTION_ACTUAL_RECONCILE_CHECK'
        running = ScheduleConfig.objects.filter(task_name=task_name, last_run_status='RUNNING').exists()
        if running:
            return Response(
                {'detail': '現在整合チェックが実行中です。完了後に再実行してください。'},
                status=status.HTTP_409_CONFLICT,
            )

        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        try:
            result = run_production_actual_reconcile_check(apply_fix=True, created_by=user)
            return Response({
                'detail': '修正を実行しました。',
                **result,
            })
        except Exception as e:
            logger.exception('生産実績整合修正に失敗')
            return Response(
                {'detail': f'修正に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ScheduleCancelView(APIView):
    """定時タスクのキャンセル要求API（実行中タスク向け）"""

    def post(self, request):
        from .scheduler.tasks import request_task_cancel

        task = (request.data.get('task_name') or 'INVENTORY_RECALC').upper()
        config_id = request.data.get('config_id') or request.data.get('id')
        supported_tasks = {'INVENTORY_RECALC', 'PICKUP_ONLY', 'INVENTORY_ONLY', 'PROGRESS_ONLY'}

        if task not in supported_tasks:
            return Response(
                {'detail': f'このタスクはキャンセル未対応です: {task}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if config_id:
            exists = ScheduleConfig.objects.filter(id=config_id, task_name=task).exists()
            if not exists:
                return Response({'detail': '対象設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)

        result = request_task_cancel(task)
        if not result.get('ok'):
            if result.get('reason') == 'not_found':
                return Response({'detail': '対象設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
            if result.get('reason') == 'not_running':
                return Response({'detail': '現在このタスクは実行中ではありません。'}, status=status.HTTP_409_CONFLICT)
            return Response({'detail': 'キャンセル要求に失敗しました。'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if result.get('already_requested'):
            return Response({'detail': '既にキャンセル要求済みです。停止完了までお待ちください。'})
        return Response({'detail': 'キャンセル要求を受け付けました。安全な区切りで停止します。'})
