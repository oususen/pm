from django.urls import include, path
from rest_framework.routers import DefaultRouter

from shipping.views import ShipmentActualViewSet
from shipping.views_kubota_sakai_due_adjustment import KubotaSakaiDueAdjustmentViewSet
from shipping.views_kubota_sakai_trip_assignment import KubotaSakaiTripAssignmentViewSet
from shipping.views_shipping_order import (
    generate_shipping_order_pdf_api,
    get_available_dates,
    get_shipping_order_data,
)
from shipping.views_fujishoji_document import (
    get_fujishoji_available_dates,
    get_fujishoji_document_data,
    generate_fujishoji_pdf_api,
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
router.register(r'kubota-sakai-due-adjustments', KubotaSakaiDueAdjustmentViewSet, basename='kubotasakaidueadjustment')
router.register(r'kubota-sakai-trip-assignments', KubotaSakaiTripAssignmentViewSet, basename='kubotasakaitripassignment')

urlpatterns = [
    path('', include(router.urls)),
    # Shipping order APIs
    path('shipping/available-dates/', get_available_dates, name='shipping-available-dates'),
    path('shipping/order-data/<str:target_date_str>/', get_shipping_order_data, name='shipping-order-data'),
    path('shipping/generate-pdf/', generate_shipping_order_pdf_api, name='shipping-generate-pdf'),
    # 富士商事出荷指示書API
    path('shipping/fujishoji-document/available-dates/', get_fujishoji_available_dates, name='fujishoji-available-dates'),
    path('shipping/fujishoji-document/generate-pdf/', generate_fujishoji_pdf_api, name='fujishoji-document-pdf'),
    path('shipping/fujishoji-document/<str:target_date_str>/', get_fujishoji_document_data, name='fujishoji-document-data'),
    # Hirakata pickup APIs
    path('hirakata-pickup/generate-pdf/', generate_hirakata_pickup_pdf, name='hirakata-pickup-generate-pdf'),
    path('hirakata-pickup/generate-excel/', generate_hirakata_pickup_excel, name='hirakata-pickup-generate-excel'),
    path('hirakata-pickup/date-range/', get_hirakata_pickup_date_range, name='hirakata-pickup-date-range'),
    path('hirakata-pickup/daily-products/', get_hirakata_daily_products, name='hirakata-daily-products'),
    path('hirakata-pickup/contacts/', get_hirakata_pickup_contacts, name='hirakata-pickup-contacts'),
    path('hirakata-pickup/send-email/', send_hirakata_pickup_email, name='hirakata-pickup-send-email'),
]
