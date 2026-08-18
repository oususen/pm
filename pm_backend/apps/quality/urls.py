from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    EquipmentInspectionConfirmationViewSet,
    EquipmentInspectionRecordViewSet,
    EquipmentInspectionTaskListView,
    EquipmentInspectionTemplateViewSet,
)
from .views_integrated_checksheet import (
    ChecksheetReworkAlertConfigViewSet,
    IntegratedChecksheetBatchViewSet,
    IntegratedChecksheetTaskListView,
    IntegratedChecksheetTemplateViewSet,
    IntegratedChecksheetUnitViewSet,
)
from .views_training import (
    TrainingAttemptViewSet,
    TrainingBookViewSet,
    TrainingExamSessionStartView,
    TrainingPracticeGradeView,
    TrainingPracticeStartView,
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
    r"checksheet-rework-alert-configs",
    ChecksheetReworkAlertConfigViewSet,
    basename="checksheet-rework-alert-config",
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
    path("integrated-checksheet-tasks/", IntegratedChecksheetTaskListView.as_view(), name="integratedchecksheet-task-list"),
    path("training-exam-sessions/start/", TrainingExamSessionStartView.as_view(), name="training-exam-session-start"),
    path("training-practice/start/", TrainingPracticeStartView.as_view(), name="training-practice-start"),
    path("training-practice/grade/", TrainingPracticeGradeView.as_view(), name="training-practice-grade"),
    path("training-progress/summary/", TrainingProgressSummaryView.as_view(), name="training-progress-summary"),
    path("", include(router.urls)),
]
