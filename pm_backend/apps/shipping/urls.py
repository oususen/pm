from django.urls import include, path
from rest_framework.routers import DefaultRouter

from shipping.views import ShipmentActualViewSet
from shipping.views_shipping_order import (
    generate_shipping_order_pdf_api,
    get_available_dates,
    get_shipping_order_data,
)
from shipping.views_hirakata_pickup import (
    generate_hirakata_pickup_pdf,
    generate_hirakata_pickup_excel,
    get_hirakata_pickup_date_range,
    get_hirakata_daily_products,
    get_hirakata_pickup_contacts,
    send_hirakata_pickup_email,
)

router = DefaultRouter()
router.register(r'shipment-actuals', ShipmentActualViewSet, basename='shipmentactual')

urlpatterns = [
    path('', include(router.urls)),
    # Shipping order APIs
    path('shipping/available-dates/', get_available_dates, name='shipping-available-dates'),
    path('shipping/order-data/<str:target_date_str>/', get_shipping_order_data, name='shipping-order-data'),
    path('shipping/generate-pdf/', generate_shipping_order_pdf_api, name='shipping-generate-pdf'),
    # Hirakata pickup APIs
    path('hirakata-pickup/generate-pdf/', generate_hirakata_pickup_pdf, name='hirakata-pickup-generate-pdf'),
    path('hirakata-pickup/generate-excel/', generate_hirakata_pickup_excel, name='hirakata-pickup-generate-excel'),
    path('hirakata-pickup/date-range/', get_hirakata_pickup_date_range, name='hirakata-pickup-date-range'),
    path('hirakata-pickup/daily-products/', get_hirakata_daily_products, name='hirakata-daily-products'),
    path('hirakata-pickup/contacts/', get_hirakata_pickup_contacts, name='hirakata-pickup-contacts'),
    path('hirakata-pickup/send-email/', send_hirakata_pickup_email, name='hirakata-pickup-send-email'),
]
