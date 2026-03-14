from rest_framework.routers import DefaultRouter
from .views import OvertimeApplicationViewSet

router = DefaultRouter()
router.register(r'overtime/applications', OvertimeApplicationViewSet, basename='overtime-application')

urlpatterns = router.urls
