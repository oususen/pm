from django.urls import path
from .views import SystemSettingViewSet

setting_list = SystemSettingViewSet.as_view({'get': 'list'})
setting_detail = SystemSettingViewSet.as_view({'get': 'list_detail', 'post': 'create'})
setting_update = SystemSettingViewSet.as_view({'patch': 'update_by_key'})
set_plan_qty_pw = SystemSettingViewSet.as_view({'post': 'set_plan_qty_password'})
verify_plan_qty_pw = SystemSettingViewSet.as_view({'post': 'verify_plan_qty_password'})

urlpatterns = [
    path('system-settings/', setting_list),
    path('system-settings/detail/', setting_detail),
    path('system-settings/update-by-key/', setting_update),
    path('system-settings/set-plan-qty-password/', set_plan_qty_pw),
    path('system-settings/verify-plan-qty-password/', verify_plan_qty_pw),
]
