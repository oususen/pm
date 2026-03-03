from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EquipmentInspectionTemplateViewSet

router = DefaultRouter()
router.register(
    r"equipment-inspection-templates",
    EquipmentInspectionTemplateViewSet,
    basename="equipmentinspectiontemplate",
)

urlpatterns = [
    path("", include(router.urls)),
]
