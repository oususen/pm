from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet, CustomerViewSet, ProcessViewSet, LineViewSet, ProductionLineViewSet,
    SupplierViewSet, CalendarViewSet, CalendarDayViewSet, WorkPatternViewSet, BreakTimeViewSet,
    BOMViewSet, BOMItemViewSet, RoutingViewSet, RoutingStepViewSet,
    RoutingStepMaterialViewSet, ProductGroupViewSet, ContainerCapacityViewSet, ContactViewSet
)

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'product-groups', ProductGroupViewSet)
router.register(r'container-capacities', ContainerCapacityViewSet)
router.register(r'customers', CustomerViewSet)
router.register(r'processes', ProcessViewSet)
router.register(r'lines', LineViewSet)
router.register(r'production-lines', ProductionLineViewSet, basename='productionline')
router.register(r'suppliers', SupplierViewSet)
router.register(r'calendars', CalendarViewSet)
router.register(r'work-patterns', WorkPatternViewSet)
router.register(r'break-times', BreakTimeViewSet)
router.register(r'calendar-days', CalendarDayViewSet)
router.register(r'boms', BOMViewSet)
router.register(r'bom-items', BOMItemViewSet)
router.register(r'routings', RoutingViewSet)
router.register(r'routing-steps', RoutingStepViewSet)
router.register(r'routing-step-materials', RoutingStepMaterialViewSet)
router.register(r'contacts', ContactViewSet)

urlpatterns = router.urls
