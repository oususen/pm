from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, CallSessionViewSet, PushSubscriptionViewSet, NativePushTokenViewSet

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet)
router.register(r'call-sessions', CallSessionViewSet, basename='call-session')
router.register(r'push-subscriptions', PushSubscriptionViewSet, basename='push-subscription')
router.register(r'native-push-tokens', NativePushTokenViewSet, basename='native-push-token')

urlpatterns = router.urls
