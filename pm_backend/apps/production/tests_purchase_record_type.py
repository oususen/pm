"""仕入実績（record_type='PURCHASE'）と生産実績の区別を検証する。"""
from datetime import date

from django.test import TestCase

from masters.models import Line, Process, Product
from production.models_line_backlog import LineBacklog
from production.models_process_realtime import ProcessRealtimeRecord
from production.production_actual_reconcile import collect_production_actual_reconcile_diffs
from production.serializers_process_realtime import ProcessRealtimeCreateSerializer
from purchase.purchase_actual_reconcile import collect_purchase_actual_reconcile_diffs


class PurchaseRecordTypeValidationTest(TestCase):
    def _errors(self, record_type, event_data):
        serializer = ProcessRealtimeCreateSerializer(data={
            'process_id': 1,
            'product_id': 1,
            'record_type': record_type,
            'qty': 5,
            'event_data': event_data,
        })
        self.assertFalse(serializer.is_valid())
        return serializer.errors

    def test_purchase_requires_purchase_source(self):
        errors = self._errors('PURCHASE', {'source': 'MANUAL', 'line_id': 1})
        self.assertIn('event_data', errors)

    def test_purchase_requires_line_id(self):
        errors = self._errors('PURCHASE', {'source': 'PURCHASE_ACTUAL_INPUT'})
        self.assertIn('event_data', errors)

    def test_production_rejects_purchase_source(self):
        errors = self._errors('PRODUCTION', {'source': 'PURCHASE_RECEIVING', 'line_id': 1})
        self.assertIn('record_type', errors)


class PurchaseRecordTypeReconcileTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(product_code='RT-PART', product_name='区別確認品')
        self.target_date = date(2026, 9, 30)

    def test_production_reconcile_excludes_purchase_records(self):
        line = Line.objects.create(line_code='RT-PROD', line_name='生産ライン', line_type='PROD')
        process = Process.objects.create(process_code='RT-P', process_name='生産工程', line=line)
        event = {'plan_date': self.target_date.isoformat()}
        ProcessRealtimeRecord.objects.create(
            process=process, product=self.product, record_type='PRODUCTION', qty=3, event_data=event,
        )
        ProcessRealtimeRecord.objects.create(
            process=process, product=self.product, record_type='PURCHASE', qty=7,
            event_data={**event, 'source': 'PURCHASE_RECEIVING', 'line_id': line.id},
        )
        LineBacklog.objects.create(
            line=line, process=process, product=self.product, plan_date=self.target_date,
            sequence_no=0, actual_qty=3,
        )

        result = collect_production_actual_reconcile_diffs()

        self.assertEqual(result['diff_rows'], [])

    def test_purchase_reconcile_counts_all_purchase_sources(self):
        line = Line.objects.create(line_code='RT-SUP', line_name='仕入先', line_type='PURCHASE')
        process = Process.objects.create(process_code='RT-G', process_name='外作', is_outsource=True)
        for source, qty in (('PURCHASE_ACTUAL_INPUT', 4), ('PURCHASE_RECEIVING', 5), ('PURCHASE_RECEIVING_MOBILE', 6)):
            ProcessRealtimeRecord.objects.create(
                process=process, product=self.product, record_type='PURCHASE', qty=qty,
                event_data={'source': source, 'line_id': line.id, 'arrival_date': self.target_date.isoformat()},
            )
        # 生産実績は同じ工程・品番でも納入実績の集計に含めない
        ProcessRealtimeRecord.objects.create(
            process=process, product=self.product, record_type='PRODUCTION', qty=100,
            event_data={'line_id': line.id, 'arrival_date': self.target_date.isoformat()},
        )
        LineBacklog.objects.create(
            line=line, process=process, product=self.product, plan_date=self.target_date,
            sequence_no=0, actual_qty=15,
        )

        result = collect_purchase_actual_reconcile_diffs()

        self.assertEqual(result['compared_count'], 1)
        self.assertEqual(result['diff_rows'], [])
