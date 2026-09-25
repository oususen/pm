from rest_framework.routers import DefaultRouter

from .views import ConsumableStockMovementViewSet, ConsumableSupplierViewSet, ConsumableViewSet

router = DefaultRouter()
router.register(r'suppliers', ConsumableSupplierViewSet)
router.register(r'items', ConsumableViewSet)
router.register(r'movements', ConsumableStockMovementViewSet)

urlpatterns = router.urls
