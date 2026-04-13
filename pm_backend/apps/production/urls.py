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
    ProductionRecordInquirySettingView,
    ScheduleConfigView,
    ScheduleRunNowView,
    PurchaseActualReconcileReportView,
    PurchaseActualReconcileFixView,
    ProductionActualReconcileReportView,
    ProductionActualReconcileFixView,
    ScheduleCancelView,
    LineBacklogAdjustmentView,
    FloorShippingPDFView,
    HokushinDeliveryPDFView,
    LaserPatternViewSet,
    LaserActualViewSet,
    LaserActualDetailUpdateView,
    LaserShiftRecordViewSet,
    ProcessActualViewSet,
    ProductionOrderViewSet,
    StockAllocationViewSet,
    StockMigrationDetectView,
    StockMigrationExecuteView,
)
from production.views_line_realtime import LineRealtimeRecordViewSet, LineStatusViewSet
from production.views_process_realtime import ProcessRealtimeRecordViewSet
from production.views_services import BOMServiceViewSet, CRPViewSet
from production.views_brake_line import BrakeLinePlanView, BrakeLineProductsView, BrakeLineEquipmentsView, BrakeLineActualAddView, BrakeLineRecordView, BrakeLineSessionView, BrakeLineSessionDetailView
from production.views_spot_line import SpotLinePlanView, SpotLineEquipmentsView, SpotLineProductsView, SpotLineRecordView
from production.views_gantt_display_product_map import GanttDisplayProductMapViewSet
from production.views_plan_deviation_report import PlanDeviationReportView

router = DefaultRouter()
router.register(r'line-demands', LineDemandViewSet, basename='linedemand')
router.register(r'line-plans', LinePlanViewSet, basename='lineplan')
router.register(r'production-plan-change-logs', ProductionPlanChangeLogViewSet, basename='productionplanchangelog')
router.register(r'line-backlogs', LineBacklogViewSet, basename='linebacklog')
router.register(r'line-gantt-plans', LineGanttPlanViewSet, basename='lineganttplan')
router.register(r'line-daily-schedule-settings', LineDailyScheduleSettingViewSet, basename='linedailyschedulesetting')
router.register(r'line-default-schedule-settings', LineDefaultScheduleSettingViewSet, basename='linedefaultschedulesetting')
router.register(r'laser-patterns', LaserPatternViewSet, basename='laserpattern')
router.register(r'laser-actuals', LaserActualViewSet, basename='laseractual')
router.register(r'laser-shift-records', LaserShiftRecordViewSet, basename='lasershiftrecord')
router.register(r'gantt-display-product-maps', GanttDisplayProductMapViewSet, basename='ganttdisplayproductmap')

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
    path('production-record-settings/', ProductionRecordInquirySettingView.as_view(), name='production-record-settings'),
    path('schedule-config/', ScheduleConfigView.as_view(), name='schedule-config'),
    path('schedule-config/run-now/', ScheduleRunNowView.as_view(), name='schedule-run-now'),
    path('schedule-config/purchase-actual-reconcile/reports/', PurchaseActualReconcileReportView.as_view(), name='schedule-purchase-actual-reconcile-reports'),
    path('schedule-config/purchase-actual-reconcile/fix/', PurchaseActualReconcileFixView.as_view(), name='schedule-purchase-actual-reconcile-fix'),
    path('schedule-config/production-actual-reconcile/reports/', ProductionActualReconcileReportView.as_view(), name='schedule-production-actual-reconcile-reports'),
    path('schedule-config/production-actual-reconcile/fix/', ProductionActualReconcileFixView.as_view(), name='schedule-production-actual-reconcile-fix'),
    path('schedule-config/cancel/', ScheduleCancelView.as_view(), name='schedule-cancel'),
    path('line-backlog-adjustments/', LineBacklogAdjustmentView.as_view(), name='line-backlog-adjustments'),
    path('stock-migration/detect/', StockMigrationDetectView.as_view(), name='stock-migration-detect'),
    path('stock-migration/execute/', StockMigrationExecuteView.as_view(), name='stock-migration-execute'),
    path('brake-line-plan/', BrakeLinePlanView.as_view(), name='brake-line-plan'),
    path('brake-line-products/', BrakeLineProductsView.as_view(), name='brake-line-products'),
    path('brake-line-equipments/', BrakeLineEquipmentsView.as_view(), name='brake-line-equipments'),
    path('brake-line-actual/add/', BrakeLineActualAddView.as_view(), name='brake-line-actual-add'),
    path('brake-line-record/', BrakeLineRecordView.as_view(), name='brake-line-record'),
    path('brake-line-sessions/', BrakeLineSessionView.as_view(), name='brake-line-sessions'),
    path('brake-line-sessions/<int:session_id>/', BrakeLineSessionDetailView.as_view(), name='brake-line-session-detail'),
    path('laser-actual-details/<int:detail_id>/', LaserActualDetailUpdateView.as_view(), name='laser-actual-detail-update'),
    path('spot-line-plan/', SpotLinePlanView.as_view(), name='spot-line-plan'),
    path('spot-line-products/', SpotLineProductsView.as_view(), name='spot-line-products'),
    path('spot-line-equipments/', SpotLineEquipmentsView.as_view(), name='spot-line-equipments'),
    path('spot-line-record/', SpotLineRecordView.as_view(), name='spot-line-record'),
    path('floor-shipping-pdf/', FloorShippingPDFView.as_view(), name='floor-shipping-pdf'),
    path('hokushin-delivery-pdf/', HokushinDeliveryPDFView.as_view(), name='hokushin-delivery-pdf'),
    path('plan-deviation-report/', PlanDeviationReportView.as_view(), name='plan-deviation-report'),
]
