"""定時タスク整合チェック系サービス"""
from rest_framework import status
from rest_framework.response import Response

from production.models_production_actual_reconcile import (
    ProductionActualReconcileReport,
    ProductionActualReconcileReportDetail,
)
from production.models_purchase_actual_reconcile import (
    PurchaseActualReconcileReport,
    PurchaseActualReconcileReportDetail,
)
from production.models_schedule_config import ScheduleConfig
from production.serializers import (
    ProductionActualReconcileReportDetailSerializer,
    ProductionActualReconcileReportSerializer,
    PurchaseActualReconcileReportDetailSerializer,
    PurchaseActualReconcileReportSerializer,
)


def get_purchase_actual_reconcile_report(request, logger=None):
    limit, detail_limit, report_id = _normalize_report_query_params(request)
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


def run_purchase_actual_reconcile_fix(request, logger=None):
    from production.scheduler.tasks_purchase_actual_reconcile import run_purchase_actual_reconcile_check

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
        return Response({'detail': '修正を実行しました。', **result})
    except Exception as exc:
        if logger:
            logger.exception('納入実績整合修正に失敗')
        return Response(
            {'detail': f'修正に失敗しました: {str(exc)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def get_production_actual_reconcile_report(request, logger=None):
    limit, detail_limit, report_id = _normalize_report_query_params(request)
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


def run_production_actual_reconcile_fix(request, logger=None):
    from production.scheduler.tasks_production_actual_reconcile import run_production_actual_reconcile_check

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
        return Response({'detail': '修正を実行しました。', **result})
    except Exception as exc:
        if logger:
            logger.exception('生産実績整合修正に失敗')
        return Response(
            {'detail': f'修正に失敗しました: {str(exc)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _normalize_report_query_params(request):
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
    return limit, detail_limit, report_id
