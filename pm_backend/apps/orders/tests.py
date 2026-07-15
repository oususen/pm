from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from masters.models import Customer, Product
from orders.core.models import KubotaSakaiDueAdjustment, Order, OrderLine
from shipping.views_kubota_sakai_due_adjustment import KubotaSakaiDueAdjustmentViewSet


class KubotaSakaiDueAdjustmentImportTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.customer = Customer.objects.create(
            customer_code='000196',
            customer_name='クボタ',
        )
        self.product = Product.objects.create(
            product_code='V053103705',
            product_name='テスト品',
            category='TEST',
            unit='個',
            is_active=True,
            is_final_product=True,
        )

    def test_import_orders_removes_planned_forecast_when_firm_arrives(self):
        target_date = date(2026, 7, 17)

        forecast_order = Order.objects.create(
            customer=self.customer,
            order_no='FC-001',
            order_type='FORECAST',
            status='OPEN',
        )
        OrderLine.objects.create(
            order=forecast_order,
            line_no=1,
            product=self.product,
            product_code=self.product.product_code,
            quantity=Decimal('9'),
            due_date=target_date,
            ship_to_code='ZGHC',
        )

        forecast_row = KubotaSakaiDueAdjustment.objects.create(
            product_code=self.product.product_code,
            ship_to_code='ZGHC',
            source_order_no=None,
            order_type='FORECAST',
            due_date=target_date,
            demand_qty=Decimal('0'),
            delivery_qty=Decimal('9'),
            remaining_qty=Decimal('0'),
        )

        firm_order = Order.objects.create(
            customer=self.customer,
            order_no='FM-001',
            order_type='FIRM',
            status='OPEN',
        )
        OrderLine.objects.create(
            order=firm_order,
            line_no=1,
            product=self.product,
            product_code=self.product.product_code,
            customer_order_no='4510447094',
            quantity=Decimal('9'),
            due_date=target_date,
            ship_to_code='ZGHC',
        )

        request = self.factory.post(
            '/api/shipping/kubota-sakai-due-adjustments/import_orders/',
            {
                'start_date': target_date.isoformat(),
                'horizon_days': 1,
            },
            format='json',
        )
        response = KubotaSakaiDueAdjustmentViewSet.as_view({'post': 'import_orders'})(request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(KubotaSakaiDueAdjustment.objects.filter(id=forecast_row.id).exists())

        firm_row = KubotaSakaiDueAdjustment.objects.get(
            product_code=self.product.product_code,
            ship_to_code='ZGHC',
            source_order_no='4510447094',
            due_date=target_date,
        )
        self.assertEqual(firm_row.order_type, 'FIRM')
        self.assertEqual(firm_row.demand_qty, Decimal('9'))
        self.assertEqual(firm_row.delivery_qty, Decimal('9'))
        self.assertEqual(response.data['deleted_forecast'], 1)
