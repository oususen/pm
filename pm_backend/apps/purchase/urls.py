from django.urls import path

from .views import EngineeringChangePartDetailView, EngineeringChangeView, PurchasePlanLockSettingView

urlpatterns = [
    path('purchase-plan-lock-setting/', PurchasePlanLockSettingView.as_view(), name='purchase-plan-lock-setting'),
    path('engineering-changes/', EngineeringChangeView.as_view(), name='engineering-changes'),
    path('engineering-changes/parts/<int:pk>/', EngineeringChangePartDetailView.as_view(), name='engineering-change-part-detail'),
]
