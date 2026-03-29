from django.urls import path
from .views import SystemSettingViewSet

setting_list = SystemSettingViewSet.as_view({'get': 'list'})
setting_detail = SystemSettingViewSet.as_view({'get': 'list_detail', 'post': 'create'})
setting_update = SystemSettingViewSet.as_view({'patch': 'update_by_key'})

urlpatterns = [
    path('system-settings/', setting_list),
    path('system-settings/detail/', setting_detail),
    path('system-settings/update-by-key/', setting_update),
]
