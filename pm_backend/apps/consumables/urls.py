from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import ConsumableStockMovementViewSet, ConsumableSupplierViewSet, ConsumableViewSet
from .views_dispatch import (
    ConsumableDispatchOrderViewSet,
    ConsumableOrderEmailConfigDetailView,
    ConsumableOrderEmailConfigListView,
    ConsumableRequestViewSet,
)

router = DefaultRouter()
router.register(r'suppliers', ConsumableSupplierViewSet)
router.register(r'items', ConsumableViewSet)
router.register(r'movements', ConsumableStockMovementViewSet)
router.register(r'requests', ConsumableRequestViewSet)
router.register(r'dispatch-orders', ConsumableDispatchOrderViewSet)

urlpatterns = [
    path('order-email-configs/', ConsumableOrderEmailConfigListView.as_view()),
    path('order-email-configs/<int:supplier_id>/', ConsumableOrderEmailConfigDetailView.as_view()),
] + router.urls
