from datetime import date
from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.db import connection, transaction
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from masters.models import Customer
from orders.core.models import KubotaSakaiDueAdjustment, KubotaSakaiDueSharedNote, Order, OrderLine
from shipping.views_kubota_sakai_due_adjustment import (
    KubotaSakaiDueAdjustmentViewSet,
    sync_kubota_sakai_due_adjustments_from_orders,
)
from shipping.views_kubota_sakai_trip_assignment import KubotaSakaiTripPlanViewNew


class DueSharedNoteTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.key = dict(product_code='V053504641', ship_to_code='ZGHC', due_date=date(2026, 9, 17))
        self.note = '検査行き　3台含む'

    def row(self, **values):
        return KubotaSakaiDueAdjustment.objects.create(**(self.key | values))

    def save_note(self, row, **values):
        request = self.factory.post('/', {'due_adjustment_id': row.id, **values}, format='json')
        return KubotaSakaiDueAdjustmentViewSet.as_view({'post': 'save_coordination_note'})(request)

    def migrate_notes(self):
        migration = import_module('orders.migrations.0069_move_forecast_coordination_notes')
        migration.move_forecast_notes(apps, SimpleNamespace(connection=connection))

    def test_migration_moves_forecast_only_and_is_repeatable(self):
        forecast = self.row(coordination_note=self.note)
        firm = self.row(order_type='FIRM', source_order_no='4511750833', coordination_note='注番固有の連絡')
        self.migrate_notes()
        self.migrate_notes()
        forecast.refresh_from_db()
        firm.refresh_from_db()
        self.assertEqual(forecast.coordination_note, '')
        self.assertEqual(firm.coordination_note, '注番固有の連絡')
        self.assertEqual(KubotaSakaiDueSharedNote.objects.get(**self.key).coordination_note, self.note)

    def test_forecast_note_survives_split_into_firm_orders_and_reimport(self):
        forecast = self.row(coordination_note=self.note)
        self.migrate_notes()
        customer = Customer.objects.create(customer_code='000196', customer_name='クボタ')
        order = Order.objects.create(customer=customer, order_no='確定テスト', order_type='FIRM')
        for index, source in enumerate(['4511750833', '4511751023'], 1):
            OrderLine.objects.create(order=order, line_no=index, customer_order_no=source, quantity=10, **self.key)
        for _ in range(2):
            sync_kubota_sakai_due_adjustments_from_orders(self.key['due_date'], self.key['due_date'])
        self.assertFalse(KubotaSakaiDueAdjustment.objects.filter(pk=forecast.pk).exists())
        self.assertEqual(KubotaSakaiDueAdjustment.objects.filter(**self.key).count(), 2)
        request = self.factory.get('/', {'start_date': '2026-09-17', 'horizon_days': 1})
        response = KubotaSakaiDueAdjustmentViewSet.as_view({'get': 'grid'})(request)
        self.assertEqual(response.status_code, 200)
        for line in response.data['rows'][0]['lines']:
            self.assertEqual(line['shared_coordination_note_by_date']['2026-09-17'], self.note)
            self.assertEqual(line['coordination_note_by_date']['2026-09-17'], '')

    def test_common_and_order_notes_can_be_saved_and_deleted_independently(self):
        firm = self.row(order_type='FIRM', source_order_no='4511750833')
        response = self.save_note(firm, coordination_note='個別', shared_coordination_note=self.note)
        self.assertEqual(response.status_code, 200)
        response = self.save_note(firm, coordination_note='', shared_coordination_note=self.note)
        self.assertTrue(response.data['has_coordination_note'])
        response = self.save_note(firm, coordination_note='個別', shared_coordination_note='')
        self.assertEqual(response.data['coordination_note'], '個別')
        self.assertEqual(KubotaSakaiDueSharedNote.objects.get(**self.key).coordination_note, '')

    def test_legacy_forecast_save_uses_common_note_and_normalizes_empty_ship_to(self):
        forecast = self.row(ship_to_code=None)
        response = self.save_note(forecast, coordination_note=self.note)
        self.assertEqual(response.status_code, 200)
        forecast.refresh_from_db()
        self.assertEqual(forecast.coordination_note, '')
        self.assertEqual(KubotaSakaiDueSharedNote.objects.get(ship_to_code='').coordination_note, self.note)

    def test_oversized_common_note_does_not_update_order_note(self):
        firm = self.row(order_type='FIRM', source_order_no='4511750833', coordination_note='元の連絡')
        response = self.save_note(firm, coordination_note='変更', shared_coordination_note='あ' * 201)
        self.assertEqual(response.status_code, 400)
        firm.refresh_from_db()
        self.assertEqual(firm.coordination_note, '元の連絡')

    def test_migration_does_not_truncate_conflicting_notes(self):
        self.row(coordination_note='あ' * 200)
        self.row(coordination_note='別の連絡')
        with self.assertRaises(ValueError), transaction.atomic():
            self.migrate_notes()
        self.assertEqual(KubotaSakaiDueSharedNote.objects.count(), 0)
        self.assertEqual(KubotaSakaiDueAdjustment.objects.exclude(coordination_note='').count(), 2)

    def test_trip_plan_shows_common_and_order_note_without_leaking_to_other_group(self):
        self.row(order_type='FIRM', source_order_no='4511750833', delivery_qty=1, coordination_note='個別')
        self.row(order_type='FIRM', source_order_no='4511751023', delivery_qty=1)
        self.row(order_type='FIRM', source_order_no='別納入先', ship_to_code='OTHER', delivery_qty=1)
        self.row(order_type='FIRM', source_order_no='別品番', product_code='OTHER', delivery_qty=1)
        KubotaSakaiDueSharedNote.objects.create(**self.key, coordination_note=self.note)
        response = KubotaSakaiTripPlanViewNew.as_view()(self.factory.get('/', {'target_date': '2026-09-17'}))
        self.assertEqual(response.status_code, 200)
        rows = {row['source_order_no']: row for row in response.data['rows']}
        for source in ['4511750833', '4511751023']:
            self.assertEqual(rows[source]['shared_coordination_note'], self.note)
            self.assertIn('共通連絡', rows[source]['coordination_note'])
        self.assertIn('個別', rows['4511750833']['coordination_note'])
        for source in ['別納入先', '別品番']:
            self.assertEqual(rows[source]['coordination_note'], '')
