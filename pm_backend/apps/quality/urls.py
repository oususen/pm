from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    EquipmentInspectionConfirmationViewSet,
    EquipmentInspectionRecordViewSet,
    EquipmentInspectionTaskListView,
    EquipmentInspectionTemplateViewSet,
)
from .views_checksheet import (
    ProductChecksheetBatchViewSet,
    ProductChecksheetRecordViewSet,
    ProductChecksheetTaskListView,
    ProductChecksheetTemplateViewSet,
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
router.register(
    r"product-checksheet-templates",
    ProductChecksheetTemplateViewSet,
    basename="productchecksheets-template",
)
router.register(
    r"product-checksheet-batches",
    ProductChecksheetBatchViewSet,
    basename="productchecksheets-batch",
)
router.register(
    r"product-checksheet-records",
    ProductChecksheetRecordViewSet,
    basename="productchecksheets-record",
)

urlpatterns = [
    path("equipment-inspection-tasks/", EquipmentInspectionTaskListView.as_view(), name="equipmentinspectiontask-list"),
    path("product-checksheet-tasks/", ProductChecksheetTaskListView.as_view(), name="productchecksheet-task-list"),
    path("", include(router.urls)),
]
