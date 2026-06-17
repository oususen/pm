from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, CallSessionViewSet

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet)
router.register(r'call-sessions', CallSessionViewSet, basename='call-session')

urlpatterns = router.urls
