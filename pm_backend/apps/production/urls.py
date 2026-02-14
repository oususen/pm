from django.urls import include, path
from rest_framework.routers import DefaultRouter

from production.views import (
    LineBacklogViewSet,
    LineDemandViewSet,
    LinePlanViewSet,
    ProductionPlanChangeLogViewSet,
    LineGanttPlanViewSet,
    LineDailyScheduleSettingViewSet,
    LineDefaultScheduleSettingViewSet,
    ProductionPlanLockSettingView,
    ScheduleConfigView,
    ScheduleRunNowView,
    ProcessActualViewSet,
    ProductionOrderViewSet,
    StockAllocationViewSet,
)
from production.views_line_realtime import LineRealtimeRecordViewSet, LineStatusViewSet
from production.views_process_realtime import ProcessRealtimeRecordViewSet
from production.views_services import BOMServiceViewSet, CRPViewSet

router = DefaultRouter()
router.register(r'line-demands', LineDemandViewSet, basename='linedemand')
router.register(r'line-plans', LinePlanViewSet, basename='lineplan')
router.register(r'production-plan-change-logs', ProductionPlanChangeLogViewSet, basename='productionplanchangelog')
router.register(r'line-backlogs', LineBacklogViewSet, basename='linebacklog')
router.register(r'line-gantt-plans', LineGanttPlanViewSet, basename='lineganttplan')
router.register(r'line-daily-schedule-settings', LineDailyScheduleSettingViewSet, basename='linedailyschedulesetting')
router.register(r'line-default-schedule-settings', LineDefaultScheduleSettingViewSet, basename='linedefaultschedulesetting')

# Execution endpoints
router.register(r'stock-allocations', StockAllocationViewSet, basename='stockallocation')
router.register(r'production-orders', ProductionOrderViewSet, basename='productionorder')
router.register(r'process-actuals', ProcessActualViewSet, basename='processactual')

# Service endpoints
router.register(r'crp', CRPViewSet, basename='crp')
router.register(r'bom-service', BOMServiceViewSet, basename='bom-service')

# Line realtime records
router.register(r'line-realtime-records', LineRealtimeRecordViewSet, basename='linerealtimerecord')
router.register(r'line-status', LineStatusViewSet, basename='linestatus')

# Process realtime records
router.register(r'process-realtime-records', ProcessRealtimeRecordViewSet, basename='processrealtimerecord')

urlpatterns = [
    path('', include(router.urls)),
    path('production-plan-lock-setting/', ProductionPlanLockSettingView.as_view(), name='production-plan-lock-setting'),
    path('schedule-config/', ScheduleConfigView.as_view(), name='schedule-config'),
    path('schedule-config/run-now/', ScheduleRunNowView.as_view(), name='schedule-run-now'),
]
