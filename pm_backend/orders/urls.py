from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LineDemandViewSet,
    LineBacklogViewSet,
    OrderViewSet,
    OrderLineViewSet,
    StgOrderRawViewSet,
    StgOrderDailyViewSet,
    StockAllocationViewSet,
    ProductionOrderViewSet,
    ProcessActualViewSet,
)
from .views_services import CRPViewSet, BOMServiceViewSet
from .views_line_realtime import LineRealtimeRecordViewSet, LineStatusViewSet

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'order-lines', OrderLineViewSet, basename='orderline')
router.register(r'stg-order-raw', StgOrderRawViewSet, basename='stgorderraw')
router.register(r'stg-order-daily', StgOrderDailyViewSet, basename='stgorderdaily')
router.register(r'line-demands', LineDemandViewSet, basename='linedemand')
router.register(r'line-backlogs', LineBacklogViewSet, basename='linebacklog')

# 製造実行系
router.register(r'stock-allocations', StockAllocationViewSet, basename='stockallocation')
router.register(r'production-orders', ProductionOrderViewSet, basename='productionorder')
router.register(r'process-actuals', ProcessActualViewSet, basename='processactual')

# サービス系API
router.register(r'crp', CRPViewSet, basename='crp')
router.register(r'bom-service', BOMServiceViewSet, basename='bom-service')

# ライン実時間記録
router.register(r'line-realtime-records', LineRealtimeRecordViewSet, basename='linerealtimerecord')
router.register(r'line-status', LineStatusViewSet, basename='linestatus')

urlpatterns = [
    path('', include(router.urls)),
]
