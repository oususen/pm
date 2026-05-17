from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'outsource/subcontractors', views.SubcontractorViewSet)
router.register(r'outsource/items', views.OutsourceItemViewSet)
router.register(r'outsource/bom', views.OutsourceBOMViewSet)
router.register(r'outsource/orders', views.OutsourceOrderViewSet)
router.register(r'outsource/splits', views.OutsourceSplitViewSet)
router.register(r'outsource/materials', views.MaterialRequirementViewSet)
router.register(r'outsource/deliveries', views.SubcontractorDeliveryViewSet)
router.register(r'outsource/shipments', views.CustomerShipmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
