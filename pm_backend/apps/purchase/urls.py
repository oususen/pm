from django.urls import path

from .order_proposal_views import (
    PurchaseOrderApprovalConfigView,
    PurchaseOrderProposalApproveView,
    PurchaseOrderProposalAutoFillView,
    PurchaseOrderProposalDetailView,
    PurchaseOrderProposalListCreateView,
    PurchaseOrderProposalPdfView,
    PurchaseOrderProposalRejectView,
    PurchaseOrderProposalSendView,
    PurchaseOrderProposalSubmitView,
    PurchaseOrderTaskListView,
    SupplierOrderScheduleDetailView,
    SupplierOrderScheduleListCreateView,
)
from .views import (
    EngineeringChangeCaseRecalculateView,
    EngineeringChangePartDetailView,
    EngineeringChangeView,
    PurchaseActualCandidatesView,
    PurchaseActualInquiryView,
    PurchaseActualProgressView,
    PurchaseActualRegisterView,
    PurchasePlanLockSettingView,
)

urlpatterns = [
    path('purchase-plan-lock-setting/', PurchasePlanLockSettingView.as_view(), name='purchase-plan-lock-setting'),
    path('engineering-changes/', EngineeringChangeView.as_view(), name='engineering-changes'),
    path('engineering-changes/parts/<int:pk>/', EngineeringChangePartDetailView.as_view(), name='engineering-change-part-detail'),
    path('engineering-changes/cases/<int:case_id>/recalculate/', EngineeringChangeCaseRecalculateView.as_view(), name='engineering-change-case-recalculate'),
    path('purchase-actual/candidates/', PurchaseActualCandidatesView.as_view(), name='purchase-actual-candidates'),
    path('purchase-actual/inquiry/', PurchaseActualInquiryView.as_view(), name='purchase-actual-inquiry'),
    path('purchase-actual/progress/', PurchaseActualProgressView.as_view(), name='purchase-actual-progress'),
    path('purchase-actual/register/', PurchaseActualRegisterView.as_view(), name='purchase-actual-register'),
    path('supplier-order-schedules/', SupplierOrderScheduleListCreateView.as_view(), name='supplier-order-schedules'),
    path('supplier-order-schedules/<int:pk>/', SupplierOrderScheduleDetailView.as_view(), name='supplier-order-schedule-detail'),
    path('purchase-order-proposals/', PurchaseOrderProposalListCreateView.as_view(), name='purchase-order-proposals'),
    path('purchase-order-proposals/<int:pk>/', PurchaseOrderProposalDetailView.as_view(), name='purchase-order-proposal-detail'),
    path('purchase-order-proposals/<int:pk>/submit/', PurchaseOrderProposalSubmitView.as_view(), name='purchase-order-proposal-submit'),
    path('purchase-order-proposals/<int:pk>/approve/', PurchaseOrderProposalApproveView.as_view(), name='purchase-order-proposal-approve'),
    path('purchase-order-proposals/<int:pk>/reject/', PurchaseOrderProposalRejectView.as_view(), name='purchase-order-proposal-reject'),
    path('purchase-order-proposals/<int:pk>/send/', PurchaseOrderProposalSendView.as_view(), name='purchase-order-proposal-send'),
    path('purchase-order-proposals/<int:pk>/pdf/', PurchaseOrderProposalPdfView.as_view(), name='purchase-order-proposal-pdf'),
    path('purchase-order-proposals/<int:pk>/auto_fill/', PurchaseOrderProposalAutoFillView.as_view(), name='purchase-order-proposal-auto-fill'),
    path('purchase-order-tasks/', PurchaseOrderTaskListView.as_view(), name='purchase-order-tasks'),
    path('purchase-order-approval-config/', PurchaseOrderApprovalConfigView.as_view(), name='purchase-order-approval-config'),
]
