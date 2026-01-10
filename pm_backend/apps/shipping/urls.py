from django.urls import include, path
from rest_framework.routers import DefaultRouter

from shipping.views import ShipmentActualViewSet
from shipping.views_shipping_order import (
    generate_shipping_order_pdf_api,
    get_available_dates,
    get_shipping_order_data,
)

router = DefaultRouter()
router.register(r'shipment-actuals', ShipmentActualViewSet, basename='shipmentactual')

urlpatterns = [
    path('', include(router.urls)),
    # Shipping order APIs
    path('shipping/available-dates/', get_available_dates, name='shipping-available-dates'),
    path('shipping/order-data/<str:target_date_str>/', get_shipping_order_data, name='shipping-order-data'),
    path('shipping/generate-pdf/', generate_shipping_order_pdf_api, name='shipping-generate-pdf'),
]
