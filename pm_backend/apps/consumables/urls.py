from rest_framework.routers import DefaultRouter

from .views import ConsumableSupplierViewSet, ConsumableViewSet

router = DefaultRouter()
router.register(r'suppliers', ConsumableSupplierViewSet)
router.register(r'items', ConsumableViewSet)

urlpatterns = router.urls
