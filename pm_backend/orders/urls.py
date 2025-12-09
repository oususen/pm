from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LineDemandViewSet,
    LineBacklogViewSet,
    OrderViewSet,
    OrderLineViewSet,
    StgOrderRawViewSet,
    StgOrderDailyViewSet
)

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'order-lines', OrderLineViewSet, basename='orderline')
router.register(r'stg-order-raw', StgOrderRawViewSet, basename='stgorderraw')
router.register(r'stg-order-daily', StgOrderDailyViewSet, basename='stgorderdaily')
router.register(r'line-demands', LineDemandViewSet, basename='linedemand')
router.register(r'line-backlogs', LineBacklogViewSet, basename='linebacklog')

urlpatterns = [
    path('', include(router.urls)),
]
