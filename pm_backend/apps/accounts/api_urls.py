from rest_framework.routers import DefaultRouter

from .api_views import DepartmentViewSet, UserViewSet

router = DefaultRouter()
router.register(r'departments', DepartmentViewSet)
router.register(r'users', UserViewSet)

urlpatterns = router.urls
