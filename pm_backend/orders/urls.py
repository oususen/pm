from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LineDemandViewSet,
    LineBacklogViewSet,
    LineGanttPlanViewSet,
    OrderViewSet,
    OrderLineViewSet,
    ShipmentActualViewSet,
    StgOrderRawViewSet,
    StgOrderDailyViewSet,
    StockAllocationViewSet,
    ProductionOrderViewSet,
    ProcessActualViewSet,
)
from .views_services import CRPViewSet, BOMServiceViewSet
from .views_line_realtime import LineRealtimeRecordViewSet, LineStatusViewSet
from .views_process_realtime import ProcessRealtimeRecordViewSet
from .views_shipping_order import (
    get_available_dates,
    get_shipping_order_data,
    generate_shipping_order_pdf_api,
)

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'order-lines', OrderLineViewSet, basename='orderline')
router.register(r'shipment-actuals', ShipmentActualViewSet, basename='shipmentactual')
router.register(r'stg-order-raw', StgOrderRawViewSet, basename='stgorderraw')
router.register(r'stg-order-daily', StgOrderDailyViewSet, basename='stgorderdaily')
router.register(r'line-demands', LineDemandViewSet, basename='linedemand')
router.register(r'line-backlogs', LineBacklogViewSet, basename='linebacklog')
router.register(r'line-gantt-plans', LineGanttPlanViewSet, basename='lineganttplan')

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

# 工程実時間記録
router.register(r'process-realtime-records', ProcessRealtimeRecordViewSet, basename='processrealtimerecord')

urlpatterns = [
    path('', include(router.urls)),
    # 出荷指示書API
    path('shipping/available-dates/', get_available_dates, name='shipping-available-dates'),
    path('shipping/order-data/<str:target_date_str>/', get_shipping_order_data, name='shipping-order-data'),
    path('shipping/generate-pdf/', generate_shipping_order_pdf_api, name='shipping-generate-pdf'),
]
