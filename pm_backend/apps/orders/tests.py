from datetime import date
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from masters.models import Customer, Product
from orders.core.models import KubotaSakaiDueAdjustment, Order, OrderLine, StgOrderDaily
from orders.core.services.kubota_sakai_kakutei_import import KubotaSakaiKakuteiImportService
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


class KubotaSakaiKakuteiImportServiceTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            customer_code='000196',
            customer_name='クボタ',
        )

    def test_import_csv_omits_zero_diff_rows_after_aggregating_latest_forecast_snapshot(self):
        due_date = date(2026, 7, 30)
        product_code = '6E46336181'
        ship_to_code = 'WEI0E'

        StgOrderDaily.objects.create(
            customer=self.customer,
            order_type='FORECAST',
            version_no='v1',
            product_code=product_code,
            due_date=due_date,
            quantity=Decimal('99'),
            ship_to_code=ship_to_code,
            source_system='CSV',
            source_file='20260722_RCV_JVAN_36_old.csv',
        )
        StgOrderDaily.objects.create(
            customer=self.customer,
            order_type='FORECAST',
            version_no='v1',
            product_code=product_code,
            due_date=due_date,
            quantity=Decimal('20'),
            ship_to_code=ship_to_code,
            source_system='CSV',
            source_file='20260723_RCV_JVAN_36_new.csv',
        )
        StgOrderDaily.objects.create(
            customer=self.customer,
            order_type='FORECAST',
            version_no='v1',
            product_code=product_code,
            due_date=due_date,
            quantity=Decimal('16'),
            ship_to_code=ship_to_code,
            source_system='CSV',
            source_file='20260723_RCV_JVAN_36_new.csv',
        )

        row = [''] * 34
        row[0] = '47'
        row[1] = '21'
        row[5] = product_code
        row[10] = 'テスト品'
        row[12] = ship_to_code
        row[13] = 'テスト納入地'
        row[14] = 'N'
        row[23] = '0730'
        row[24] = '36'
        row[26] = '260723'
        row[33] = '4500000001'
        content = (','.join(row) + '\r\n').encode('cp932')
        upload = SimpleUploadedFile(
            '20260723取込済_RCV_JVAN - 47sa.csv',
            content,
            content_type='text/csv',
        )

        result = KubotaSakaiKakuteiImportService().import_csv(upload, '000196', 'FIRM')

        self.assertTrue(result['success'])
        self.assertEqual(result['forecast_diffs'], [])
