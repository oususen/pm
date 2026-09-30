"""社内AIの生産数集計（_production_facts）の定義を検証する。"""
from datetime import date
from unittest.mock import patch

from django.test import TestCase

from ai.services.chat_service import _production_facts
from masters.models import Line, Process, Product
from production.models_brake_line_record import BrakeLineRecord
from production.models_process_realtime import ProcessRealtimeRecord


class ProductionFactsBrakeTest(TestCase):
    def setUp(self):
        # テスト用SQLiteではAI専用接続(ai_reader)を別接続にできないため、同じ接続で集計する
        patcher = patch('ai.services.chat_service.AI_DB_ALIAS', 'default')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.line = Line.objects.create(line_code='AI-BRK', line_name='ブレーキ', line_type='PROD')
        self.process = Process.objects.create(process_code='AI-BP', process_name='ブレーキ工程', line=self.line)
        self.product = Product.objects.create(product_code='AI-BRAKE-01', product_name='ブレーキ品')
        self.day = date(2026, 9, 16)

    def _record(self, action, qty):
        BrakeLineRecord.objects.create(
            plan_date=self.day, line=self.line, process=self.process, product=self.product,
            product_code=self.product.product_code, operator='作業者', operator_action=action, qty=qty,
        )

    def test_brake_quantity_sums_end_and_pause(self):
        # 開始→中断(40)→再開→終了(60)→開始→強制終了 の作業区間
        for action, qty in (('START', 0), ('PAUSE', 40), ('RESUME', 0), ('END', 60), ('START', 0), ('TEMP_END', 0)):
            self._record(action, qty)

        facts = _production_facts(self.day, self.day, product_code=self.product.product_code)

        self.assertEqual(facts['brake_total'], 100)
        self.assertEqual(facts['brake_records'], 2)
        self.assertEqual(facts['total'], 100)
        self.assertEqual(facts['source'], 'ブレーキ実績（終了・中断時の加工数）')

    def test_purchase_records_are_not_production(self):
        ProcessRealtimeRecord.objects.create(
            process=self.process, product=self.product, product_code=self.product.product_code,
            record_type='PRODUCTION', qty=7, event_data={'source': 'OPERATOR_ACTION_END'},
        )
        ProcessRealtimeRecord.objects.create(
            process=self.process, product=self.product, product_code=self.product.product_code,
            record_type='PURCHASE', qty=50,
            event_data={'source': 'PURCHASE_ACTUAL_INPUT', 'line_id': self.line.id},
        )
        today = ProcessRealtimeRecord.objects.first().timestamp.date()

        facts = _production_facts(today, today, product_code=self.product.product_code)

        self.assertEqual(facts['source'], '工程実績')
        self.assertEqual(facts['total'], 7)
