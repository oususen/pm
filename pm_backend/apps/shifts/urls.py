from rest_framework.routers import DefaultRouter
from .views import (
    ShiftLineViewSet, ShiftWorkerViewSet,
    ShiftLineProcessViewSet, ShiftAssignmentViewSet,
)

router = DefaultRouter()
router.register(r'shifts/lines', ShiftLineViewSet, basename='shift-line')
router.register(r'shifts/workers', ShiftWorkerViewSet, basename='shift-worker')
router.register(r'shifts/line-processes', ShiftLineProcessViewSet, basename='shift-line-process')
router.register(r'shifts/assignments', ShiftAssignmentViewSet, basename='shift-assignment')

urlpatterns = router.urls
