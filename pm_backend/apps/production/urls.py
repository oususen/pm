from django.urls import include, path
from rest_framework.routers import DefaultRouter

from production.views_orphan_backlog import (
    OrphanLineBacklogReportView,
    OrphanLineBacklogFixView,
)
from production.views_line_demand import LineDemandViewSet
from production.views_ai_demo import ProductionAIDemoView
from production.views_ai_config import AISearchConfigViewSet, AISearchConfigModelsView
from production.views_plan_line_setting import ProductionPlanLineSettingView
from production.views import (
    LineBacklogViewSet,
    LinePlanViewSet,
    ProductionPlanChangeLogViewSet,
    LineGanttPlanViewSet,
    LineBacklogAdjustmentView,
    ProcessActualViewSet,
    ProductionOrderViewSet,
    StockAllocationViewSet,
    StockMigrationDetectView,
    StockMigrationExecuteView,
)
from production.views_schedule_settings import (
    AutoPlanAggregateSettingViewSet,
    LineDailyScheduleSettingViewSet,
    LineDefaultScheduleSettingViewSet,
)
from production.views_settings import (
    ProductionPlanLockSettingView,
    ProductionRecordInquirySettingView,
)
from production.views_production_lock import ProductionLockView
from production.views_pdf_floor_shipping import (
    FloorShippingLapPDFView,
    FloorShippingNewPDFView,
    FloorShippingPDFView,
)
from production.views_pdf_hokushin_delivery import (
    HokushinDeliveryAllPDFView,
    HokushinDeliveryPDFView,
)
from production.views_pdf_hokushin_list import (
    HokushinDeliveryListLapPDFView,
    HokushinDeliveryListNewPDFView,
    HokushinDeliveryListPDFView,
)
from production.views_schedule import (
    ScheduleConfigView,
    ScheduleRunLogView,
    ScheduleRunNowView,
    PurchaseActualReconcileReportView,
    PurchaseActualReconcileFixView,
    ProductionActualReconcileReportView,
    ProductionActualReconcileFixView,
    ScheduleCancelView,
    ScheduleResetView,
)
from production.views_laser import (
    LaserActualDetailUpdateView,
    LaserActualViewSet,
    LaserPatternViewSet,
    LaserProcessingFreqPatternViewSet,
    LaserShiftRecordViewSet,
)
from production.views_laser_weekly_plan import (
    LaserMaterialOrderEmailConfigViewSet,
    LaserWeeklyMaterialGroupViewSet,
    LaserWeeklyPlanTargetViewSet,
    LaserWeeklyPlanViewSet,
)
from production.views_line_realtime import LineRealtimeRecordViewSet, LineStatusViewSet
from production.views_process_realtime import ProcessRealtimeRecordViewSet
from production.views_services import BOMServiceViewSet, CRPViewSet, LineLoadViewSet
from production.views_brake_line import BrakeLinePlanView, BrakeLineProductsView, BrakeLineEquipmentsView, BrakeLineActualAddView, BrakeLineLabelPrintProxyView, BrakeLineRecordView, BrakeLineSessionView, BrakeLineSessionDetailView
from production.views_spot_line import SpotLinePlanView, SpotLineEquipmentsView, SpotLineProductsView, SpotLineRecordView
from production.views_gantt_display_product_map import GanttDisplayProductMapViewSet
from production.views_line_product_display_order import LineProductDisplayOrderViewSet
from production.views_plan_deviation_report import PlanDeviationReportView, PlanDeviationLineConfigView
from production.views_progress_compare import ProgressPdfCompareView, ProgressPdfAdjustView
from production.views_record_confirmation import ProductionRecordConfirmationView
from production.views_stocktake import StocktakeRecordView, StocktakeHistoryView, StocktakeRecorderView, StocktakeCounterView, StocktakeLayoutConfigView, StocktakeAreaView, StocktakeSlipPDFView, StocktakeResultView, StocktakeResultExportView, StocktakeLatestSystemView
from production.views_morning_meeting import MorningMeetingViewSet
from production.views_daily_process_target import DailyProcessTargetViewSet
from production.views_camera_actual import (
    CameraAutoDetectView,
    CameraEventCreateView,
    CameraResultDailyView,
    CameraShapeTrainingStartView,
    CameraShapeTrainingStatusView,
    CameraShapeTrainingPhotoUploadView,
    CameraShapeTrainingUploadView,
)
from production.views_actual_cycle_time import (
    ActualCycleTimeCalcView,
    ActualCycleTimeSaveView,
    ActualCycleTimeListView,
    ActualCycleTimeDeleteByPeriodView,
    FinishedProductCycleTimeConsolidatedView,
    FinishedProductCycleTimeSaveView,
    FinishedProductCycleTimeListView,
    FinishedProductCycleTimeLatestForLineView,
)

router = DefaultRouter()
router.register(r'line-demands', LineDemandViewSet, basename='linedemand')
router.register(r'line-plans', LinePlanViewSet, basename='lineplan')
router.register(r'production-plan-change-logs', ProductionPlanChangeLogViewSet, basename='productionplanchangelog')
router.register(r'line-backlogs', LineBacklogViewSet, basename='linebacklog')
router.register(r'line-gantt-plans', LineGanttPlanViewSet, basename='lineganttplan')
router.register(r'line-daily-schedule-settings', LineDailyScheduleSettingViewSet, basename='linedailyschedulesetting')
router.register(r'line-default-schedule-settings', LineDefaultScheduleSettingViewSet, basename='linedefaultschedulesetting')
router.register(r'auto-plan-aggregate-settings', AutoPlanAggregateSettingViewSet, basename='autoplanaggregatesetting')
router.register(r'laser-processing-freq-patterns', LaserProcessingFreqPatternViewSet, basename='laserprocessingfreqpattern')
router.register(r'laser-patterns', LaserPatternViewSet, basename='laserpattern')
router.register(r'laser-actuals', LaserActualViewSet, basename='laseractual')
router.register(r'laser-shift-records', LaserShiftRecordViewSet, basename='lasershiftrecord')
router.register(r'laser-weekly-plan-targets', LaserWeeklyPlanTargetViewSet, basename='laserweeklyplantarget')
router.register(r'laser-weekly-material-groups', LaserWeeklyMaterialGroupViewSet, basename='laserweeklymaterialgroup')
router.register(r'laser-material-order-email-configs', LaserMaterialOrderEmailConfigViewSet, basename='lasermaterialorderemailconfig')
router.register(r'laser-weekly-plans', LaserWeeklyPlanViewSet, basename='laserweeklyplan')
router.register(r'gantt-display-product-maps', GanttDisplayProductMapViewSet, basename='ganttdisplayproductmap')
router.register(r'line-product-display-orders', LineProductDisplayOrderViewSet, basename='lineproductdisplayorder')
router.register(r'morning-meetings', MorningMeetingViewSet, basename='morningmeeting')
router.register(r'daily-process-targets', DailyProcessTargetViewSet, basename='daily-process-target')
router.register(r'ai-search-configs', AISearchConfigViewSet, basename='aisearchconfig')

# Execution endpoints
router.register(r'stock-allocations', StockAllocationViewSet, basename='stockallocation')
router.register(r'production-orders', ProductionOrderViewSet, basename='productionorder')
router.register(r'process-actuals', ProcessActualViewSet, basename='processactual')

# Service endpoints
router.register(r'crp', CRPViewSet, basename='crp')
router.register(r'line-load', LineLoadViewSet, basename='line-load')
router.register(r'bom-service', BOMServiceViewSet, basename='bom-service')

# Line realtime records
router.register(r'line-realtime-records', LineRealtimeRecordViewSet, basename='linerealtimerecord')
router.register(r'line-status', LineStatusViewSet, basename='linestatus')

# Process realtime records
router.register(r'process-realtime-records', ProcessRealtimeRecordViewSet, basename='processrealtimerecord')

urlpatterns = [
    path('', include(router.urls)),
    path('production-ai-demo/', ProductionAIDemoView.as_view(), name='production-ai-demo'),
    path('ai-search-config-models/', AISearchConfigModelsView.as_view(), name='ai-search-config-models'),
    path('production-plan-line-settings/', ProductionPlanLineSettingView.as_view(), name='production-plan-line-settings'),
    path('production-plan-lock-setting/', ProductionPlanLockSettingView.as_view(), name='production-plan-lock-setting'),
    path('production-record-settings/', ProductionRecordInquirySettingView.as_view(), name='production-record-settings'),
    path('schedule-config/', ScheduleConfigView.as_view(), name='schedule-config'),
    path('schedule-config/run-now/', ScheduleRunNowView.as_view(), name='schedule-run-now'),
    path('schedule-config/run-logs/', ScheduleRunLogView.as_view(), name='schedule-run-logs'),
    path('schedule-config/purchase-actual-reconcile/reports/', PurchaseActualReconcileReportView.as_view(), name='schedule-purchase-actual-reconcile-reports'),
    path('schedule-config/purchase-actual-reconcile/fix/', PurchaseActualReconcileFixView.as_view(), name='schedule-purchase-actual-reconcile-fix'),
    path('schedule-config/production-actual-reconcile/reports/', ProductionActualReconcileReportView.as_view(), name='schedule-production-actual-reconcile-reports'),
    path('schedule-config/production-actual-reconcile/fix/', ProductionActualReconcileFixView.as_view(), name='schedule-production-actual-reconcile-fix'),
    path('orphan-backlog/report/', OrphanLineBacklogReportView.as_view(), name='orphan-backlog-report'),
    path('orphan-backlog/fix/', OrphanLineBacklogFixView.as_view(), name='orphan-backlog-fix'),
    path('schedule-config/cancel/', ScheduleCancelView.as_view(), name='schedule-cancel'),
    path('schedule-config/reset/', ScheduleResetView.as_view(), name='schedule-reset'),
    path('line-backlog-adjustments/', LineBacklogAdjustmentView.as_view(), name='line-backlog-adjustments'),
    path('stock-migration/detect/', StockMigrationDetectView.as_view(), name='stock-migration-detect'),
    path('stock-migration/execute/', StockMigrationExecuteView.as_view(), name='stock-migration-execute'),
    path('brake-line-plan/', BrakeLinePlanView.as_view(), name='brake-line-plan'),
    path('brake-line-products/', BrakeLineProductsView.as_view(), name='brake-line-products'),
    path('brake-line-equipments/', BrakeLineEquipmentsView.as_view(), name='brake-line-equipments'),
    path('brake-line-actual/add/', BrakeLineActualAddView.as_view(), name='brake-line-actual-add'),
    path('brake-line-label-print/', BrakeLineLabelPrintProxyView.as_view(), name='brake-line-label-print'),
    path('brake-line-record/', BrakeLineRecordView.as_view(), name='brake-line-record'),
    path('brake-line-sessions/', BrakeLineSessionView.as_view(), name='brake-line-sessions'),
    path('brake-line-sessions/<int:session_id>/', BrakeLineSessionDetailView.as_view(), name='brake-line-session-detail'),
    path('laser-actual-details/<int:detail_id>/', LaserActualDetailUpdateView.as_view(), name='laser-actual-detail-update'),
    path('spot-line-plan/', SpotLinePlanView.as_view(), name='spot-line-plan'),
    path('spot-line-products/', SpotLineProductsView.as_view(), name='spot-line-products'),
    path('spot-line-equipments/', SpotLineEquipmentsView.as_view(), name='spot-line-equipments'),
    path('spot-line-record/', SpotLineRecordView.as_view(), name='spot-line-record'),
    path('floor-shipping-pdf/', FloorShippingPDFView.as_view(), name='floor-shipping-pdf'),
    path('floor-shipping-new-pdf/', FloorShippingNewPDFView.as_view(), name='floor-shipping-new-pdf'),
    path('floor-shipping-lap-pdf/', FloorShippingLapPDFView.as_view(), name='floor-shipping-lap-pdf'),
    path('hokushin-delivery-list-pdf/', HokushinDeliveryListPDFView.as_view(), name='hokushin-delivery-list-pdf'),
    path('hokushin-delivery-list-new-pdf/', HokushinDeliveryListNewPDFView.as_view(), name='hokushin-delivery-list-new-pdf'),
    path('hokushin-delivery-list-lap-pdf/', HokushinDeliveryListLapPDFView.as_view(), name='hokushin-delivery-list-lap-pdf'),
    path('hokushin-delivery-pdf/', HokushinDeliveryPDFView.as_view(), name='hokushin-delivery-pdf'),
    path('hokushin-delivery-all-pdf/', HokushinDeliveryAllPDFView.as_view(), name='hokushin-delivery-all-pdf'),
    path('plan-deviation-report/', PlanDeviationReportView.as_view(), name='plan-deviation-report'),
    path('plan-deviation-line-config/', PlanDeviationLineConfigView.as_view(), name='plan-deviation-line-config'),
    path('record-confirmations/', ProductionRecordConfirmationView.as_view(), name='record-confirmations'),
    path('stocktake-records/', StocktakeRecordView.as_view(), name='stocktake-records'),
    path('stocktake-records/<int:product_id>/history/', StocktakeHistoryView.as_view(), name='stocktake-history'),
    path('stocktake-recorders/', StocktakeRecorderView.as_view(), name='stocktake-recorders'),
    path('stocktake-counters/', StocktakeCounterView.as_view(), name='stocktake-counters'),
    path('stocktake-layout-config/', StocktakeLayoutConfigView.as_view(), name='stocktake-layout-config'),
    path('stocktake-areas/', StocktakeAreaView.as_view(), name='stocktake-areas'),
    path('stocktake-results/', StocktakeResultView.as_view(), name='stocktake-results'),
    path('stocktake-results/export/', StocktakeResultExportView.as_view(), name='stocktake-results-export'),
    path('stocktake-results/latest-system/', StocktakeLatestSystemView.as_view(), name='stocktake-latest-system'),
    path('stocktake-slip-pdf/', StocktakeSlipPDFView.as_view(), name='stocktake-slip-pdf'),
    path('camera-events/', CameraEventCreateView.as_view(), name='camera-events'),
    path('camera-results-daily/', CameraResultDailyView.as_view(), name='camera-results-daily'),
    path('camera-auto-detect/', CameraAutoDetectView.as_view(), name='camera-auto-detect'),
    path('camera-shape-training/upload-dataset/', CameraShapeTrainingUploadView.as_view(), name='camera-shape-training-upload'),
    path('camera-shape-training/upload-photos/', CameraShapeTrainingPhotoUploadView.as_view(), name='camera-shape-training-upload-photos'),
    path('camera-shape-training/start/', CameraShapeTrainingStartView.as_view(), name='camera-shape-training-start'),
    path('camera-shape-training/status/', CameraShapeTrainingStatusView.as_view(), name='camera-shape-training-status'),
    path('actual-cycle-time/calc/', ActualCycleTimeCalcView.as_view(), name='actual-cycle-time-calc'),
    path('actual-cycle-time/save/', ActualCycleTimeSaveView.as_view(), name='actual-cycle-time-save'),
    path('finished-product-cycle-time/calc/', FinishedProductCycleTimeConsolidatedView.as_view(), name='finished-product-cycle-time-calc'),
    path('finished-product-cycle-time/save/', FinishedProductCycleTimeSaveView.as_view(), name='finished-product-cycle-time-save'),
    path('actual-cycle-time/list/', ActualCycleTimeListView.as_view(), name='actual-cycle-time-list'),
    path('finished-product-cycle-time/list/', FinishedProductCycleTimeListView.as_view(), name='finished-product-cycle-time-list'),
    path('finished-product-cycle-time/latest-for-line/', FinishedProductCycleTimeLatestForLineView.as_view(), name='finished-product-cycle-time-latest-for-line'),
    path('actual-cycle-time/delete-by-period/', ActualCycleTimeDeleteByPeriodView.as_view(), name='actual-cycle-time-delete-by-period'),
    path('progress-pdf-compare/', ProgressPdfCompareView.as_view(), name='progress-pdf-compare'),
    path('progress-pdf-adjust/', ProgressPdfAdjustView.as_view(), name='progress-pdf-adjust'),
    path('production-locks/', ProductionLockView.as_view(), name='production-locks'),
]
