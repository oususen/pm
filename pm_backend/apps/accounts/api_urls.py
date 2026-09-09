from rest_framework.routers import DefaultRouter

from .api_views import (
    DepartmentViewSet,
    UserViewSet,
    DepartmentPermissionViewSet,
    PositionPermissionViewSet,
    PositionListView,
    DepartmentPositionPermissionViewSet,
    DepartmentPositionListView,
    DivisionListView,
    GroupListView,
    TeamListView,
    UnitListView,
    UserSmtpConfigViewSet,
    UnitLineMappingViewSet,
    UserFavoriteViewSet,
    ApprovalRouteConfigViewSet,
)

router = DefaultRouter()
router.register(r'departments', DepartmentViewSet)
router.register(r'users', UserViewSet)
router.register(r'department-permissions', DepartmentPermissionViewSet)
router.register(r'position-permissions', PositionPermissionViewSet)
router.register(r'positions', PositionListView, basename='position-list')
router.register(r'department-position-permissions', DepartmentPositionPermissionViewSet)
router.register(r'department-positions', DepartmentPositionListView, basename='department-position-list')
router.register(r'divisions', DivisionListView, basename='division-list')
router.register(r'groups', GroupListView, basename='group-list')
router.register(r'teams', TeamListView, basename='team-list')
router.register(r'units', UnitListView, basename='unit-list')
router.register(r'smtp-configs', UserSmtpConfigViewSet)
router.register(r'unit-line-mappings', UnitLineMappingViewSet)
router.register(r'favorites', UserFavoriteViewSet)
router.register(r'approval-routes', ApprovalRouteConfigViewSet)

urlpatterns = router.urls
