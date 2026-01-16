from django.urls import path

from .views import PurchasePlanLockSettingView

urlpatterns = [
    path('purchase-plan-lock-setting/', PurchasePlanLockSettingView.as_view(), name='purchase-plan-lock-setting'),
]
