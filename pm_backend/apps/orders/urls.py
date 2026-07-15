from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrderViewSet,
    OrderLineViewSet,
    StgOrderRawViewSet,
    StgOrderDailyViewSet,
)
from .core.views import (
    kubota_sakai_import_config_view,
    order_first_article_setting_view,
)

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'order-lines', OrderLineViewSet, basename='orderline')
router.register(r'stg-order-raw', StgOrderRawViewSet, basename='stgorderraw')
router.register(r'stg-order-daily', StgOrderDailyViewSet, basename='stgorderdaily')

urlpatterns = [
    path('', include(router.urls)),
    path('kubota-sakai-import-config/', kubota_sakai_import_config_view, name='kubota-sakai-import-config'),
    path('order-first-article-setting/', order_first_article_setting_view, name='order-first-article-setting'),
]
