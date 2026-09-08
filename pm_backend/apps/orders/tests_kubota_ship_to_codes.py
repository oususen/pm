import csv
from datetime import date
from importlib import import_module
from io import StringIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from masters.models import Calendar, Customer, Product, Line, Process, Routing, RoutingStep
from orders.core.models import Order, OrderLine
from orders.core.services.ship_to_utils import normalize_kubota_ship_to_code
from orders.management.commands.normalize_kubota_ship_to_codes import Command, merge_settings
from production.models import LineDemand
from production.services.order_expansion import OrderExpansionService
from shipping.models import ShipToLeadTime, ShipToLeadTimeColorExclusion, ShippingProgress
from shipping.services.shipping_progress import recalculate_shipping_progress


class KubotaShipToParserTests(SimpleTestCase):
    def test_numeric_codes_and_non_numeric_codes(self):
        for original, expected in (
            ('971', '00971'), ('00971', '00971'), ('5476', '05476'),
            ('4', '00004'), ('0', '00000'), ('９７１', '00971'),
            ('34158', '34158'), ('123456', '123456'),
            ('ZGHC', 'ZGHC'), ('E213', 'E213'), ('ZS01', 'ZS01'),
            ('97-1', '97-1'), ('9 71', '9 71'), ('971.0', '971.0'),
            ('', ''), (None, ''),
        ):
            with self.subTest(original=original):
                self.assertEqual(normalize_kubota_ship_to_code(original), expected)

    def parse(self, service, rows, order_type, save_result=(1, 1, 1, 1)):
        stream = StringIO()
        csv.writer(stream).writerows(rows)
        upload = SimpleUploadedFile('test.csv', stream.getvalue().encode('cp932'))
        with patch.object(service, 'save_to_database', return_value=save_result) as save:
            result = service.import_csv(upload, '000196', order_type)
        self.assertTrue(result['success'], result)
        self.assertTrue(save.called)
        return save.call_args.args[0]

    def test_forecast_pairs_with_different_padding_are_paired(self):
        for suffix, name in (
            ('sakai', 'KubotaSakaiNaijiImportService'),
            ('hirakata', 'KubotaHirakataNaijiImportService'),
            ('hirakata_2027', 'KubotaHirakata2027NaijiImportService'),
        ):
            with self.subTest(format=suffix):
                service = getattr(import_module(f'orders.core.services.kubota_{suffix}_naiji_import'), name)()
                rows = []
                for kind, code, value in (('V2', '971', '60929'), ('V3', '00971', '18')):
                    row = [''] * 120
                    row[0] = '36'
                    row[service.COL_PRODUCT_CODE] = 'TEST-PRODUCT'
                    row[service.COL_RECORD_TYPE] = kind
                    row[service.COL_SHIP_TO] = code
                    row[service.COL_DATA_START] = value
                    row[service.COL_START_MONTH] = '2609'
                    rows.append(row)
                raw = self.parse(service, [[''] * 120] + rows, 'FORECAST')
                self.assertEqual(len(raw), 1)
                self.assertEqual(raw[0].raw_payload['ship_to'], '00971')
                self.assertEqual(raw[0].raw_payload['v2_row'][service.COL_SHIP_TO], '971')

    def test_kmt_forecast_is_normalized_before_storage(self):
        from orders.core.services.kubota_kmt_naiji_import import KubotaKmtNaijiImportService
        service = KubotaKmtNaijiImportService()
        row = [''] * 96
        row[0], row[7], row[11], row[46], row[71] = '4', 'TEST-PRODUCT', '971', '18', '20260929'
        self.assertEqual(self.parse(service, [row], 'FORECAST')[0].raw_payload['ship_to'], '00971')

    def test_confirmed_formats_normalize_codes(self):
        formats = (
            ('sakai', 'KubotaSakaiKakuteiImportService', ('47', '49')),
            ('hirakata_2027', 'KubotaHirakata2027KakuteiImportService', ('45', '47')),
            ('kmt', 'KubotaKmtKakuteiImportService', ('27', '49')),
        )
        for suffix, name, data_nos in formats:
            for data_no in data_nos:
                with self.subTest(format=suffix, data_no=data_no):
                    service = getattr(import_module(f'orders.core.services.kubota_{suffix}_kakutei_import'), name)()
                    row = [''] * 34
                    row[0], row[1], row[5], row[12] = data_no, '92' if suffix == 'kmt' else '01', 'TEST-PRODUCT', '971'
                    if suffix == 'kmt' and data_no == '27':
                        row[21], row[22], row[24] = '20260929', '18', '260908'
                    else:
                        row[23], row[24], row[26] = '0929', '18', '260908'
                    save_result = (1, 1, 1, 1) if suffix == 'kmt' else (1, 1, 1, 1, [])
                    raw = self.parse(service, [row], 'FIRM', save_result)
                    self.assertEqual(raw[0].raw_payload['ship_to'], '00971')

    def test_legacy_hirakata_confirmed_formats(self):
        from orders.core.services.kubota_hirakata_kakutei_import import KubotaHirakataKakuteiImportService
        for data_no in ('45', '47'):
            with self.subTest(data_no=data_no):
                service = KubotaHirakataKakuteiImportService()
                header = [''] * 34
                header[3] = '注番'
                row = [''] * 34
                row[0], row[3], row[5] = data_no, 'TEST-ORDER', 'TEST-PRODUCT'
                if data_no == '45':
                    row[13], row[18], row[19], row[21] = '971', '260929', '18', '260908'
                else:
                    row[12], row[23], row[24], row[26] = '971', '0929', '18', '260908'
                with patch('orders.core.services.kubota_hirakata_kakutei_import.StgOrderRawKubota.objects') as manager:
                    manager.filter.return_value.values_list.return_value = []
                    raw = self.parse(service, [header, row], 'FIRM')
                self.assertEqual(raw[0].raw_payload['ship_to'], '00971')


class KubotaShipToMigrationTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(customer_code='000196', customer_name='クボタ')
        self.calendar = Calendar.objects.create(calendar_code='test', calendar_name='テスト')

    def test_settings_keep_color_products_and_canonical_id(self):
        old = ShipToLeadTime.objects.create(customer=self.customer, ship_to_code='971', bg_color='#e78f2c', calendar=self.calendar)
        canonical = ShipToLeadTime.objects.create(customer=self.customer, ship_to_code='00971')
        ShipToLeadTimeColorExclusion.objects.create(ship_to_lead_time=old, product_code='TEST-PRODUCT')
        Command().update_settings(f'customer_id={self.customer.pk}', {'971': '00971'})
        canonical.refresh_from_db()
        self.assertEqual(canonical.bg_color, '#e78f2c')
        self.assertEqual(canonical.calendar_id, self.calendar.pk)
        self.assertFalse(ShipToLeadTime.objects.filter(pk=old.pk).exists())
        self.assertEqual(list(canonical.color_exclusions.values_list('product_code', flat=True)), ['TEST-PRODUCT'])

    def test_conflicting_settings_are_rejected(self):
        rows = [dict(ship_to_code=code, ship_to_name='', additional_days=days, bg_color='', text_color='', calendar_id=None, is_active=True)
                for code, days in (('971', 1), ('00971', 2))]
        with self.assertRaises(CommandError):
            merge_settings(rows)

    @patch('production.services.order_expansion.get_business_today', return_value=date(2026, 9, 8))
    def test_full_expansion_removes_old_code_and_excludes_matching_forecast(self, _today):
        line = Line.objects.create(line_code='TEST', line_name='テスト', calendar=self.calendar)
        process = Process.objects.create(process_code='TEST', process_name='テスト', line=line)
        product = Product.objects.create(product_code='TEST-PRODUCT', product_name='テスト', is_final_product=True)
        routing = Routing.objects.create(product=product, routing_code='TEST', is_default=True, is_active=True)
        step = RoutingStep.objects.create(routing=routing, step_no=1, process=process, line=line, output_product=product, hierarchy_path='final', time_unit='DAY', lead_time_days=0)
        for kind, code in (('FIRM', '00971'), ('FORECAST', '971')):
            order = Order.objects.create(customer=self.customer, order_no=kind, order_type=kind, status='OPEN')
            OrderLine.objects.create(order=order, line_no=1, product=product, product_code=product.product_code, quantity=18, due_date=date(2026, 9, 29), ship_to_code='00971', is_expanded=True)
            LineDemand.objects.create(line=line, routing_step=step, process=process, product=product, product_code=product.product_code, ship_to_code=code, plan_date=date(2026, 9, 29), firm_qty=18 if kind == 'FIRM' else 0, forecast_qty=18 if kind == 'FORECAST' else 0)
        result = OrderExpansionService().expand_open_orders(clear_existing=True)
        self.assertFalse(result['errors'])
        demand = LineDemand.objects.get(product_code=product.product_code)
        self.assertEqual((demand.ship_to_code, demand.firm_qty, demand.forecast_qty), ('00971', 18, 0))

    def test_shipping_rebuild_prefers_firm_and_keeps_adjustments(self):
        target = date(2026, 9, 29)
        product = Product.objects.create(product_code='TEST-PRODUCT', product_name='テスト', category='TEST', unit='個')
        for kind in ('FIRM', 'FORECAST'):
            order = Order.objects.create(customer=self.customer, order_no=kind, order_type=kind, status='OPEN')
            OrderLine.objects.create(order=order, line_no=1, product=product, product_code=product.product_code, quantity=18, due_date=target, ship_to_code='00971')
        for code, adjustment in (('971', 2), ('00971', 3)):
            ShippingProgress.objects.create(customer_code='000196', product_code=product.product_code, ship_to_code=code, plan_date=target, adjust_qty=adjustment)
        unrelated = ShippingProgress.objects.create(customer_code='000018', product_code=product.product_code, ship_to_code='000010', plan_date=target, progress_qty=77)
        alpha = ShippingProgress.objects.create(customer_code='000196', product_code=product.product_code, ship_to_code='ZGHC', plan_date=target, progress_qty=88)
        Command().rebuild_shipping_progress()
        row = ShippingProgress.objects.get(customer_code='000196', ship_to_code='00971')
        self.assertEqual((row.firm_qty, row.forecast_qty, row.adjust_qty, row.progress_qty), (18, 0, 5, -13))
        self.assertFalse(ShippingProgress.objects.filter(ship_to_code='971').exists())
        unrelated.refresh_from_db()
        alpha.refresh_from_db()
        self.assertEqual(unrelated.progress_qty, 77)
        self.assertEqual(alpha.progress_qty, 88)
        # 対象を空集合で指定した場合も、全件再計算にはならない。
        recalculate_shipping_progress(target, target, customer_code='000196', ship_to_codes=[])
        alpha.refresh_from_db()
        self.assertEqual(alpha.progress_qty, 88)
