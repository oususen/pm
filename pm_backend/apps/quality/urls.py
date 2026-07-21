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
from .views_integrated_checksheet import (
    IntegratedChecksheetBatchViewSet,
    IntegratedChecksheetTaskListView,
    IntegratedChecksheetTemplateViewSet,
    IntegratedChecksheetUnitViewSet,
)
from .views_training import (
    TrainingAttemptViewSet,
    TrainingBookViewSet,
    TrainingExamSessionStartView,
    TrainingProgressSummaryView,
    TrainingStepRecordViewSet,
    TrainingTrackViewSet,
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
router.register(
    r"integrated-checksheet-templates",
    IntegratedChecksheetTemplateViewSet,
    basename="integratedchecksheet-template",
)
router.register(
    r"integrated-checksheet-batches",
    IntegratedChecksheetBatchViewSet,
    basename="integratedchecksheet-batch",
)
router.register(
    r"integrated-checksheet-units",
    IntegratedChecksheetUnitViewSet,
    basename="integratedchecksheet-unit",
)
router.register(
    r"training-books",
    TrainingBookViewSet,
    basename="training-book",
)
router.register(
    r"training-tracks",
    TrainingTrackViewSet,
    basename="training-track",
)
router.register(
    r"training-attempts",
    TrainingAttemptViewSet,
    basename="training-attempt",
)
router.register(
    r"training-step-records",
    TrainingStepRecordViewSet,
    basename="training-step-record",
)

urlpatterns = [
    path("equipment-inspection-tasks/", EquipmentInspectionTaskListView.as_view(), name="equipmentinspectiontask-list"),
    path("product-checksheet-tasks/", ProductChecksheetTaskListView.as_view(), name="productchecksheet-task-list"),
    path("integrated-checksheet-tasks/", IntegratedChecksheetTaskListView.as_view(), name="integratedchecksheet-task-list"),
    path("training-exam-sessions/start/", TrainingExamSessionStartView.as_view(), name="training-exam-session-start"),
    path("training-progress/summary/", TrainingProgressSummaryView.as_view(), name="training-progress-summary"),
    path("", include(router.urls)),
]
