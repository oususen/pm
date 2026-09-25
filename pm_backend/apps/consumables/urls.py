from rest_framework.routers import DefaultRouter

from .views import ConsumableStockMovementViewSet, ConsumableSupplierViewSet, ConsumableViewSet
from .views_dispatch import ConsumableDispatchOrderViewSet, ConsumableRequestViewSet

router = DefaultRouter()
router.register(r'suppliers', ConsumableSupplierViewSet)
router.register(r'items', ConsumableViewSet)
router.register(r'movements', ConsumableStockMovementViewSet)
router.register(r'requests', ConsumableRequestViewSet)
router.register(r'dispatch-orders', ConsumableDispatchOrderViewSet)

urlpatterns = router.urls
