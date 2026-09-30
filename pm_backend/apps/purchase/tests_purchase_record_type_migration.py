"""既存の仕入実績（旧: record_type='PRODUCTION'）を PURCHASE へ移行した後の動作を検証する。"""
from datetime import date, datetime

from django.db import IntegrityError, transaction
from django.test import TestCase

from masters.models import BOM, BOMItem, Line, Process, Product
from production.models_line_backlog import LineBacklog
from production.models_process_realtime import PURCHASE_ACTUAL_SOURCES, ProcessRealtimeRecord
from purchase.services.actual_plan import plan_key, plan_state
from purchase.tests_actual_plan import PurchaseActualPlanFixture
from purchase.views import PurchaseActualInquiryView, _reconcile_purchase_actual_backlog_for_key

# 本番の移行SQL（仕様書/仕入実績record_type分離仕様書.md 5章）と同じ条件
MIGRATION_FILTER = {'record_type': 'PRODUCTION', 'event_data__source__in': list(PURCHASE_ACTUAL_SOURCES)}


class PurchaseRecordTypeMigrationTest(PurchaseActualPlanFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.arrival = date(2026, 9, 6)
        component_line = Line.objects.create(line_code='MIG-COMP', line_name='子部品ライン', line_type='PROD')
        self.component_process = Process.objects.create(
            process_code='MIG-COMP-P', process_name='子部品工程', line=component_line,
        )
        self.component = Product.objects.create(product_code='MIG-COMP-01', product_name='支給子部品')
        bom = BOM.objects.create(
            parent_product=self.product, version='v-mig', valid_from=date(2026, 1, 1), is_active=True,
        )
        BOMItem.objects.create(
            bom=bom, child_product=self.component, quantity=2,
            process=self.component_process, line=component_line,
        )
        self.child_backlog = LineBacklog.objects.create(
            line=component_line, process=self.component_process, product=self.component,
            plan_date=self.arrival, sequence_no=0, actual_shipment_qty=18,
        )
        # 旧形式の仕入実績（移行前の本番データと同じ形）
        self.linked = self._legacy_record(4, {
            'line_id': self.line.id,
            'purchase_plan': self.key,
        })
        # event_data.line_id を持たない既存データ（本番に41件存在）
        self.no_line = self._legacy_record(5, {})
        # 移行前の本番と同じく、仕入先ラインの actual_qty は旧形式レコードの合計で作成済み
        LineBacklog.objects.create(
            line=self.line, process=self.process, product=self.product,
            plan_date=self.arrival, sequence_no=0, actual_qty=9,
        )

        migrated = ProcessRealtimeRecord.objects.filter(**MIGRATION_FILTER).update(record_type='PURCHASE')
        self.assertEqual(migrated, 2)

    def _legacy_record(self, qty, extra_event):
        record = ProcessRealtimeRecord.objects.create(
            process=self.process, product=self.product,
            product_code=self.product.product_code, product_name=self.product.product_name,
            record_type='PRODUCTION', qty=qty,
            event_data={
                'source': 'PURCHASE_ACTUAL_INPUT',
                'arrival_date': self.arrival.isoformat(),
                'supplier_id': self.supplier.id,
                **extra_event,
            },
        )
        ProcessRealtimeRecord.objects.filter(pk=record.pk).update(timestamp=datetime(2026, 9, 6, 9, 0))
        return record

    def _supplier_actual(self):
        return LineBacklog.objects.get(
            line=self.line, process=self.process, product=self.product,
            plan_date=self.arrival, sequence_no=0,
        ).actual_qty

    def test_migrated_records_are_listed_and_reconcile_keeps_actual(self):
        response = PurchaseActualInquiryView.as_view()(self.factory.get('/', {
            'start_date': '2026-09-01', 'end_date': '2026-09-30',
        }))
        self.assertEqual(sorted(row['id'] for row in response.data), sorted([self.linked.id, self.no_line.id]))

        _reconcile_purchase_actual_backlog_for_key(self.process.id, self.product.id, self.line.id)
        self.assertEqual(self._supplier_actual(), 9)

    def test_migrated_plan_record_counts_toward_plan(self):
        state = plan_state(self.key)
        self.assertEqual(state['registered_qty'], 4)
        self.assertEqual(state['remaining_qty'], 6)
        other_key = plan_key(self.supplier.id, self.product.id, '2026-09-05')
        self.assertEqual(plan_state(other_key)['registered_qty'], 0)

    def test_migrated_record_without_line_id_can_be_edited_and_deleted(self):
        self.assertEqual(self.edit(self.no_line.id, qty=3).status_code, 200)
        self.assertEqual(self._supplier_actual(), 7)
        self.child_backlog.refresh_from_db()
        self.assertEqual(self.child_backlog.actual_shipment_qty, 14)

        self.assertEqual(self.delete(self.no_line.id).status_code, 204)
        self.assertEqual(self._supplier_actual(), 4)
        self.child_backlog.refresh_from_db()
        self.assertEqual(self.child_backlog.actual_shipment_qty, 8)
        self.assertFalse(ProcessRealtimeRecord.objects.filter(pk=self.no_line.pk).exists())


class PurchaseRecordTypeConstraintTest(TestCase):
    def setUp(self):
        self.process = Process.objects.create(process_code='CK-G', process_name='外作', is_outsource=True)
        self.product = Product.objects.create(product_code='CK-PART', product_name='制約確認品')

    def _create(self, record_type, event_data):
        return ProcessRealtimeRecord.objects.create(
            process=self.process, product=self.product, record_type=record_type, qty=1, event_data=event_data,
        )

    def test_purchase_without_purchase_source_is_rejected(self):
        for event_data in (None, {}, {'line_id': 1}, {'source': None}, {'source': 'MANUAL_RECORD_EDIT'}):
            with self.subTest(event_data=event_data):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        self._create('PURCHASE', event_data)

    def test_purchase_with_purchase_source_and_other_types_are_allowed(self):
        for source in PURCHASE_ACTUAL_SOURCES:
            self._create('PURCHASE', {'source': source})
        self._create('PRODUCTION', None)
        self._create('PRODUCTION', {'source': 'OPERATOR_ACTION_END'})
        self._create('SCRAP', {})
        self.assertEqual(ProcessRealtimeRecord.objects.count(), 6)
