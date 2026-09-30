"""計画からの分納登録・再送・訂正を実データで検証する。"""
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from rest_framework.test import APIRequestFactory

from masters.models import Line, Process, Product, Routing, RoutingStep, Supplier
from production.models_line_backlog import LineBacklog
from production.models_process_realtime import ProcessRealtimeRecord
from purchase.services.actual_plan import lock_supplier, plan_key, plan_state
from purchase.views import PurchaseActualBulkItemsView, PurchaseActualBulkRegisterView, PurchaseActualDetailView


class PurchaseActualPlanFixture:
    def setUp(self):
        self.factory = APIRequestFactory()
        self.effects = patch('purchase.views._recalculate_purchase_actual_effects').start()
        self.addCleanup(patch.stopall)
        self.supplier = Supplier.objects.create(supplier_code='PLAN-SUP', supplier_name='計画仕入先')
        self.line = Line.objects.create(line_code='PLAN-SUP', line_name='計画仕入先', line_type='PURCHASE')
        self.process = Process.objects.create(process_code='G', process_name='外作', is_outsource=True)
        self.product = Product.objects.create(product_code='PLAN-PART', product_name='分納品')
        routing = Routing.objects.create(product=self.product, routing_code='PLAN-ROUTE', is_default=True, is_active=True)
        RoutingStep.objects.create(routing=routing, step_no=10, process=self.process,
                                   line=self.line, supplier=self.supplier, output_product=self.product)
        self.plan = LineBacklog.objects.create(line=self.line, product=self.product, process=self.process,
                                               plan_date=date(2026, 9, 4), sequence_no=1, plan_qty=10)
        self.key = plan_key(self.supplier.id, self.product.id, '2026-09-04')

    def state(self):
        return plan_state(self.key)

    def register(self, qty, token=None, plan=True, arrival='2026-09-06'):
        item = {'product_code': self.product.product_code, 'qty': qty}
        if plan:
            item.update(plan_date='2026-09-04', plan_token=token if token is not None else self.state()['plan_token'])
        request = self.factory.post('/', {'supplier_id': self.supplier.id, 'arrival_date': arrival,
                                         'items': [item]}, format='json')
        return PurchaseActualBulkRegisterView.as_view()(request).data['results'][0]

    def edit(self, record_id, **data):
        return PurchaseActualDetailView.as_view()(self.factory.put('/', data, format='json'), record_id=record_id)

    def delete(self, record_id):
        return PurchaseActualDetailView.as_view()(self.factory.delete('/'), record_id=record_id)


class PurchaseActualPlanTest(PurchaseActualPlanFixture, TestCase):
    def test_partial_delivery_replay_and_completion(self):
        old_token = self.state()['plan_token']
        first = self.register(4, old_token)
        self.assertEqual(first['status'], 'ok')
        record = ProcessRealtimeRecord.objects.get(pk=first['id'])
        self.assertEqual(record.record_type, 'PURCHASE')
        self.assertEqual(record.event_data['purchase_plan'], self.key)
        self.assertEqual(record.event_data['arrival_date'], '2026-09-06')
        self.assertEqual(self.state()['remaining_qty'], 6)
        # 完納前でも同じ送信や別画面の古い送信は拒否する。
        self.assertEqual(self.register(4, old_token)['status'], 'error')
        self.assertEqual(self.register(7)['status'], 'error')
        self.assertEqual(self.register(6, arrival='2026-09-07')['status'], 'ok')
        self.assertEqual(self.register(1)['status'], 'error')
        self.assertEqual(ProcessRealtimeRecord.objects.filter(event_data__purchase_plan=self.key).count(), 2)

    def test_edit_delete_and_stale_request_after_delete(self):
        initial_token = self.state()['plan_token']
        first = self.register(4)
        second = self.register(3)
        token_before_edit = self.state()['plan_token']
        self.assertEqual(self.edit(first['id'], qty=8).status_code, 400)
        self.assertEqual(self.edit(first['id'], qty=2, arrival_date='2026-09-08').status_code, 200)
        self.assertEqual(self.state()['remaining_qty'], 5)
        self.assertEqual(self.register(1, token_before_edit)['status'], 'error')
        self.assertEqual(self.delete(first['id']).status_code, 204)
        self.assertEqual(self.delete(second['id']).status_code, 204)
        self.assertEqual(self.state()['remaining_qty'], 10)
        self.assertEqual(self.register(4, initial_token)['status'], 'error')

    def test_unlinked_records_and_other_plan_dates_are_excluded(self):
        self.assertEqual(self.register(5, plan=False)['status'], 'ok')
        ProcessRealtimeRecord.objects.create(process=self.process, product=self.product, record_type='PURCHASE', qty=7,
            event_data={'purchase_plan': plan_key(self.supplier.id, self.product.id, '2026-09-03')})
        self.assertEqual(self.state()['registered_qty'], 0)
        self.assertEqual(self.register(10)['status'], 'ok')

    def test_changed_or_deleted_plan_rejects_old_screen(self):
        old_token = self.state()['plan_token']
        self.plan.plan_qty = 12
        self.plan.save()
        self.assertEqual(self.register(4, old_token)['status'], 'error')
        self.assertEqual(self.register(4)['status'], 'ok')
        self.plan.delete()
        self.assertEqual(self.register(1)['status'], 'error')

    def test_bulk_items_returns_plan_balance(self):
        self.register(4)
        response = PurchaseActualBulkItemsView.as_view()(self.factory.get('/', {
            'supplier_id': self.supplier.id, 'plan_date': '2026/09/04',
        }))
        item = response.data['items'][0]
        self.assertEqual(item['registered_qty'], 4)
        self.assertEqual(item['remaining_qty'], 6)
        self.assertEqual(item['plan_token'], self.state()['plan_token'])

    def test_failed_registration_does_not_consume_balance(self):
        RoutingStep.objects.all().delete()
        self.assertEqual(self.register(4)['status'], 'error')
        self.assertEqual(self.state()['remaining_qty'], 10)

    def test_supplier_change_is_rejected_without_losing_link(self):
        first = self.register(4)
        other = Supplier.objects.create(supplier_code='OTHER', supplier_name='別仕入先')
        self.assertEqual(self.edit(first['id'], supplier_id=other.id).status_code, 400)
        self.assertEqual(self.state()['registered_qty'], 4)


class PurchaseActualPlanConcurrencyTest(PurchaseActualPlanFixture, TransactionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    def test_two_screens_cannot_register_same_snapshot_even_with_balance(self):
        token = self.state()['plan_token']
        barrier = Barrier(2)

        def synchronized_lock(supplier_id):
            barrier.wait(timeout=10)
            return lock_supplier(supplier_id)

        def register_from_another_connection():
            close_old_connections()
            try:
                return self.register(4, token)['status']
            finally:
                close_old_connections()

        with patch('purchase.views.lock_supplier', side_effect=synchronized_lock):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: register_from_another_connection(), range(2)))
        self.assertCountEqual(results, ['ok', 'error'])
        self.assertEqual(self.state()['registered_qty'], 4)
