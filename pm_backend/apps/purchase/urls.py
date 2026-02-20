from django.urls import path

from .views import EngineeringChangeCaseRecalculateView, EngineeringChangePartDetailView, EngineeringChangeView, PurchasePlanLockSettingView

urlpatterns = [
    path('purchase-plan-lock-setting/', PurchasePlanLockSettingView.as_view(), name='purchase-plan-lock-setting'),
    path('engineering-changes/', EngineeringChangeView.as_view(), name='engineering-changes'),
    path('engineering-changes/parts/<int:pk>/', EngineeringChangePartDetailView.as_view(), name='engineering-change-part-detail'),
    path('engineering-changes/cases/<int:case_id>/recalculate/', EngineeringChangeCaseRecalculateView.as_view(), name='engineering-change-case-recalculate'),
]
