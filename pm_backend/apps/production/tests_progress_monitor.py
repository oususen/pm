from datetime import date

from accounts.models import Department, UnitLineMapping, UserProfile
from django.contrib.auth import get_user_model
from django.urls import reverse
from masters.models import Line, Process, Product
from rest_framework import status
from rest_framework.test import APITestCase

from .models import LineDemand
from .models_line_backlog import LineBacklog
from .models_progress_monitor import ProgressMonitorTarget


class ProgressMonitorApiTest(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='monitor', password='test')
        self.unit = Department.objects.create(name='板金', level='unit', display_id=1)
        self.other_unit = Department.objects.create(name='組立', level='unit', display_id=2)
        UserProfile.objects.create(user=self.user, unit=self.unit)
        self.line = Line.objects.create(line_code='LTEST1', line_name='テストライン')
        self.other_line = Line.objects.create(line_code='LTEST2', line_name='対象外ライン')
        UnitLineMapping.objects.create(unit=self.unit, line=self.line)
        UnitLineMapping.objects.create(unit=self.other_unit, line=self.other_line)
        self.product = Product.objects.create(product_code='P-MONITOR', product_name='監視製品')
        self.process1 = Process.objects.create(process_code='PROC1', process_name='工程1', line=self.line)
        self.process2 = Process.objects.create(process_code='PROC2', process_name='工程2', line=self.line)
        self.client.force_authenticate(self.user)

    def snapshot(self, **params):
        query = {'unit_id': self.unit.id, 'start_date': '2026-10-01', 'horizon': 30}
        query.update(params)
        return self.client.get(reverse('progress-monitor-target-snapshot'), query)

    def create_target(self, **kwargs):
        values = {'product': self.product, 'line': self.line, 'registered_by': self.user}
        values.update(kwargs)
        return ProgressMonitorTarget.objects.create(**values)

    def create_backlog(self, process, sequence_no, **kwargs):
        values = {
            'plan_date': date(2026, 10, 16), 'process': process, 'product': self.product,
            'line': self.line, 'sequence_no': sequence_no,
        }
        values.update(kwargs)
        return LineBacklog.objects.create(**values)

    def create_demand(self, process, ship_to_code, **kwargs):
        values = {
            'plan_date': date(2026, 10, 16), 'process': process, 'product': self.product,
            'product_code': self.product.product_code, 'line': self.line, 'ship_to_code': ship_to_code,
        }
        values.update(kwargs)
        return LineDemand.objects.create(**values)

    def test_options_returns_only_profile_and_leader_units(self):
        response = self.client.get(reverse('progress-monitor-target-options'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in response.data['units']], [self.unit.id])
        self.assertEqual(response.data['lines_by_unit'][str(self.unit.id)][0]['id'], self.line.id)

    def test_options_returns_union_of_profile_unit_and_leader_units(self):
        leader_unit = Department.objects.create(name='兼任グループ', level='unit', display_id=3)
        leader_line = Line.objects.create(line_code='LTEST3', line_name='兼任ライン')
        UnitLineMapping.objects.create(unit=leader_unit, line=leader_line)
        self.user.profile.leader_units.add(leader_unit)

        response = self.client.get(reverse('progress-monitor-target-options'))

        self.assertEqual(
            {item['id'] for item in response.data['units']},
            {self.unit.id, leader_unit.id},
        )
        self.assertNotIn(self.other_unit.id, {item['id'] for item in response.data['units']})

    def test_create_rejects_line_outside_allowed_units(self):
        response = self.client.post(reverse('progress-monitor-target-list'), {
            'product': self.product.id, 'line': self.other_line.id,
            'display_order': 0, 'memo': '', 'is_active': True,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_snapshot_separates_sequence_roles(self):
        self.create_target()
        self.create_backlog(
            self.process1, 0, plan_qty=999, actual_qty=5, adjust_qty=-2,
            progress_qty=-3, planned_progress_qty=-1,
        )
        self.create_backlog(
            self.process1, 1, plan_qty=11, actual_qty=888, adjust_qty=777,
            progress_qty=666, planned_progress_qty=555,
        )

        response = self.snapshot()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cell = response.data['rows'][0]['cells']['2026-10-16']
        self.assertEqual(cell['plan'], 11)
        self.assertEqual(cell['actual'], 5)
        self.assertEqual(cell['adjust'], -2)
        self.assertEqual(cell['progress'], -3)
        self.assertEqual(cell['planned_progress'], -1)

    def test_snapshot_sums_matching_process_demands_and_prefers_them(self):
        self.create_target()
        self.create_backlog(self.process1, 0)
        self.create_demand(self.process1, 'A', forecast_qty=5, firm_qty=2)
        self.create_demand(self.process1, 'B', forecast_qty=7, firm_qty=3)
        self.create_demand(None, 'COMMON', forecast_qty=99, firm_qty=88)

        response = self.snapshot()

        cell = response.data['rows'][0]['cells']['2026-10-16']
        self.assertEqual(cell['forecast'], 12)
        self.assertEqual(cell['firm'], 5)

    def test_snapshot_uses_processless_demand_when_exact_process_is_missing(self):
        self.create_target()
        self.create_backlog(self.process2, 0)
        self.create_demand(None, 'COMMON', forecast_qty=9, firm_qty=4)

        response = self.snapshot()

        cell = response.data['rows'][0]['cells']['2026-10-16']
        self.assertEqual(response.data['rows'][0]['process_code'], 'PROC2')
        self.assertEqual(cell['forecast'], 9)
        self.assertEqual(cell['firm'], 4)

    def test_snapshot_splits_same_target_by_process(self):
        target = self.create_target()
        self.create_backlog(self.process1, 0, progress_qty=-3)
        self.create_backlog(self.process2, 0, progress_qty=7)

        response = self.snapshot()

        self.assertEqual(len(response.data['rows']), 2)
        self.assertEqual({row['process_code'] for row in response.data['rows']}, {'PROC1', 'PROC2'})
        self.assertTrue(all(row['target_id'] == target.id for row in response.data['rows']))

    def test_snapshot_returns_empty_card_when_period_data_is_missing(self):
        target = self.create_target(memo='確認対象')

        response = self.snapshot()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['rows']), 1)
        self.assertEqual(response.data['rows'][0]['target_id'], target.id)
        self.assertIsNone(response.data['rows'][0]['process_id'])
        self.assertEqual(response.data['rows'][0]['cells'], {})
        self.assertEqual(len(response.data['dates']), 30)
        self.assertEqual(response.data['end_date'], date(2026, 10, 30))

    def test_snapshot_excludes_inactive_and_other_unit_targets(self):
        inactive = self.create_target(is_active=False)
        other_product = Product.objects.create(product_code='P-OTHER', product_name='対象外製品')
        ProgressMonitorTarget.objects.create(
            product=other_product, line=self.other_line, registered_by=self.user,
        )

        response = self.snapshot()

        self.assertEqual(response.data['rows'], [])
        self.assertEqual([item['target_id'] for item in response.data['targets']], [inactive.id])

    def test_create_defaults_monitor_type_to_progress(self):
        response = self.client.post(reverse('progress-monitor-target-list'), {
            'product': self.product.id, 'line': self.line.id,
            'display_order': 0, 'memo': '', 'is_active': True,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['monitor_type'], 'progress')

    def test_snapshot_includes_monitor_type_and_inventory_fields(self):
        target = self.create_target(monitor_type=ProgressMonitorTarget.MONITOR_TYPE_INVENTORY)
        self.create_backlog(
            self.process1, 0, scrap_qty=4, stock_qty=-6, planned_stock_qty=8,
            order_qty=15, order_qty_actual=9,
        )
        # LineDemandがあっても在庫監視の計需・実需には使わないことを確認する
        self.create_demand(self.process1, 'A', forecast_qty=999, firm_qty=888)

        response = self.snapshot()

        row = response.data['rows'][0]
        self.assertEqual(row['target_id'], target.id)
        self.assertEqual(row['monitor_type'], 'inventory')
        cell = row['cells']['2026-10-16']
        self.assertEqual(cell['scrap'], 4)
        self.assertEqual(cell['stock'], -6)
        self.assertEqual(cell['planned_stock'], 8)
        self.assertEqual(cell['forecast'], 15)
        self.assertEqual(cell['firm'], 9)
        target_entry = next(item for item in response.data['targets'] if item['target_id'] == target.id)
        self.assertEqual(target_entry['monitor_type'], 'inventory')

    def test_snapshot_progress_mode_still_uses_line_demand_for_forecast_firm(self):
        self.create_target()
        self.create_backlog(self.process1, 0, order_qty=777, order_qty_actual=666)
        self.create_demand(self.process1, 'A', forecast_qty=5, firm_qty=2)

        response = self.snapshot()

        cell = response.data['rows'][0]['cells']['2026-10-16']
        self.assertEqual(cell['forecast'], 5)
        self.assertEqual(cell['firm'], 2)

    def test_snapshot_rejects_unassigned_unit_and_invalid_horizon(self):
        outside = self.client.get(reverse('progress-monitor-target-snapshot'), {
            'unit_id': self.other_unit.id, 'start_date': '2026-10-01', 'horizon': 30,
        })
        invalid_horizon = self.snapshot(horizon=31)

        self.assertEqual(outside.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_horizon.status_code, status.HTTP_400_BAD_REQUEST)
