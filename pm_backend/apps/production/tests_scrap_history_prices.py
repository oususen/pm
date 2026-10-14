"""未保存の合成データだけで仕損履歴の金額仕様を確認する。DBアクセスは禁止。"""
from decimal import Decimal

from django.test import SimpleTestCase
from rest_framework.renderers import JSONRenderer

from masters.models import Process, Product
from quality.models_scrap import ScrapRecord
from production.models_process_realtime import ProcessRealtimeRecord
from production.serializers_process_realtime import ProcessRealtimeRecordSerializer


class ScrapHistoryPricesTest(SimpleTestCase):
    def make_record(self, price='12.34', qty='2.000', returned='0.000', record_type='SCRAP'):
        product = Product(id=1, product_code='合成品番', unit_price=Decimal(price) if price is not None else None)
        record = ProcessRealtimeRecord(
            id=1, process=Process(id=1), product=product, record_type=record_type, qty=Decimal(qty),
        )
        record.scrap_detail = ScrapRecord(id=1, return_qty=Decimal(returned))
        return record

    def prices(self, record):
        data = ProcessRealtimeRecordSerializer(record).data
        # JSONにも小数文字列のまま渡り、浮動小数へ変換されないことを確認する。
        JSONRenderer().render(data)
        return data['scrap_unit_price'], data['scrap_amount']

    def test_current_master_price_is_used_after_change(self):
        record = self.make_record()
        self.assertEqual(self.prices(record), ('12.34', '24.68'))
        record.product.unit_price = Decimal('20.00')
        self.assertEqual(self.prices(record), ('20.00', '40.00'))

    def test_missing_price_or_product_is_null(self):
        self.assertEqual(self.prices(self.make_record(price=None)), (None, None))
        record = self.make_record()
        record.product = None
        record.product_code = '合成品番'
        self.assertEqual(self.prices(record), (None, None))

    def test_zero_price_is_preserved(self):
        self.assertEqual(self.prices(self.make_record(price='0.00')), ('0.00', '0.00'))

    def test_decimal_quantity_rounds_half_up(self):
        self.assertEqual(self.prices(self.make_record(price='0.10', qty='0.150')), ('0.10', '0.02'))
        self.assertEqual(self.prices(self.make_record(price='0.10', qty='0.149')), ('0.10', '0.01'))

    def test_return_quantity_is_not_deducted(self):
        self.assertEqual(self.prices(self.make_record(returned='2.000')), ('12.34', '24.68'))

    def test_non_scrap_record_is_null(self):
        self.assertEqual(self.prices(self.make_record(record_type='PRODUCTION')), (None, None))

    def test_prices_are_read_only(self):
        fields = ProcessRealtimeRecordSerializer().fields
        self.assertTrue(fields['scrap_unit_price'].read_only)
        self.assertTrue(fields['scrap_amount'].read_only)

    def test_largest_model_values_keep_decimal_precision(self):
        self.assertEqual(
            self.prices(self.make_record(price='9999999999.99', qty='9999999.999')),
            ('9999999999.99', '99999999989900000.00'),
        )
