from django.urls import include, path
from rest_framework.routers import DefaultRouter

from production.views import (
    LineBacklogViewSet,
    LineDemandViewSet,
    LinePlanViewSet,
    LineGanttPlanViewSet,
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
router.register(r'line-backlogs', LineBacklogViewSet, basename='linebacklog')
router.register(r'line-gantt-plans', LineGanttPlanViewSet, basename='lineganttplan')

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
]
