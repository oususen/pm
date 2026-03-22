from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    EquipmentInspectionConfirmationViewSet,
    EquipmentInspectionRecordViewSet,
    EquipmentInspectionTaskListView,
    EquipmentInspectionTemplateViewSet,
)

router = DefaultRouter()
router.register(
    r"equipment-inspection-templates",
    EquipmentInspectionTemplateViewSet,
    basename="equipmentinspectiontemplate",
)
router.register(
    r"equipment-inspection-records",
    EquipmentInspectionRecordViewSet,
    basename="equipmentinspectionrecord",
)
router.register(
    r"equipment-inspection-confirmations",
    EquipmentInspectionConfirmationViewSet,
    basename="equipmentinspectionconfirmation",
)

urlpatterns = [
    path("equipment-inspection-tasks/", EquipmentInspectionTaskListView.as_view(), name="equipmentinspectiontask-list"),
    path("", include(router.urls)),
]
