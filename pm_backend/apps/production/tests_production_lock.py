from contextlib import nullcontext
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from production.management.commands import generate_production_plan as command
from production import views_production_lock as views


class LockedQuantityTests(SimpleTestCase):
    """実DBを変更せず、数量の採用時点と保存先を検証する。"""

    def test_lock_replaces_duplicate_demands_and_includes_zero_and_no_demand(self):
        day = date(2026, 9, 14)
        locks = [SimpleNamespace(plan_date=day, product_id=p, locked_qty=Decimal(q))
                 for p, q in [(1, '30'), (2, '0'), (3, '40')]]
        demands = [dict(plan_date=day, product_id=p, process_id=8, demand_qty_plan=100)
                   for p in [1, 1, 2, 4]]
        for line_type in ['PROD', 'PURCHASE']:
            with self.subTest(line_type=line_type), \
                 patch.object(command.ProductionLock, 'objects') as lock_manager, \
                 patch.object(command.LinePlan, 'objects') as plans, \
                 patch.object(command.LineBacklog, 'objects') as backlogs:
                lock_manager.filter.return_value = locks
                source = backlogs.filter.return_value if line_type == 'PURCHASE' else plans.all.return_value
                source.filter.return_value.values.return_value = [
                    dict(plan_date=day, product_id=3, process_id=9),
                ]
                result = command.apply_locked_quantities(SimpleNamespace(id=1, line_type=line_type), day, day, demands)
                self.assertEqual({r['product_id']: r['demand_qty_plan'] for r in result},
                                 {1: Decimal(30), 2: Decimal(0), 3: Decimal(40), 4: 100})
                self.assertEqual(len(result), 4)
                self.assertEqual(next(r for r in result if r['product_id'] == 3)['process_id'], 9)
                if line_type == 'PURCHASE':
                    backlogs.filter.assert_called_once_with(sequence_no=1)
                    plans.all.assert_not_called()

    def test_missing_process_stops_before_deleting_plans(self):
        day = date(2026, 9, 14)
        with patch.object(command.ProductionLock, 'objects') as locks, patch.object(command.LinePlan, 'objects') as plans:
            locks.filter.return_value = [SimpleNamespace(plan_date=day, product_id=1, locked_qty=Decimal(10))]
            plans.all.return_value.filter.return_value.values.return_value = []
            with self.assertRaises(command.CommandError):
                command.apply_locked_quantities(SimpleNamespace(id=1, line_type='PROD'), day, day, [])

    def test_command_generates_once_using_locked_quantity_even_without_demand(self):
        day = date(2026, 9, 14)
        row = dict(plan_date=day, product_id=1, process_id=8, demand_qty_plan=30)
        for line_type in ['PROD', 'PURCHASE']:
            line = SimpleNamespace(id=1, line_code='L1', line_type=line_type, use_direct_process=False)
            with self.subTest(line_type=line_type), \
                 patch.object(command, 'iter_lines', return_value=[line]), \
                 patch.object(command, 'run_pickup'), \
                 patch.object(command, 'fetch_final_demands', return_value=[]), \
                 patch.object(command, 'apply_locked_quantities', return_value=[row]), \
                 patch.object(command, 'delete_existing') as delete, \
                 patch.object(command, 'generate_line_plans', return_value=(1, [])) as generate, \
                 patch.object(command, 'apply_purchase_plan_to_backlog', return_value=(1, 0)) as purchase, \
                 patch.object(command, 'expand_processes_for_auto_plan') as expand, \
                 patch.object(command, 'generate_gantt') as gantt, \
                 patch.object(command.transaction, 'atomic', side_effect=lambda: nullcontext()):
                cmd = command.Command(stdout=MagicMock())
                cmd.handle(lines=[1], start=str(day), end=str(day), run_date=str(day))
                delete.assert_called_once()
                if line_type == 'PURCHASE':
                    purchase.assert_called_once_with(1, day, day, [row])
                    generate.assert_not_called()
                    expand.assert_not_called()
                    gantt.assert_not_called()
                else:
                    generate.assert_called_once_with(1, [row])
                    expand.assert_called_once()
                    gantt.assert_called_once()

    def test_lock_api_uses_saved_quantity_and_rejects_unsaved_or_relocked_changes(self):
        for line_type in ['PROD', 'PURCHASE']:
            with self.subTest(line_type=line_type), \
                 patch.object(views.Line, 'objects') as lines, \
                 patch.object(views.LinePlan, 'objects') as plans, \
                 patch.object(views.LineBacklog, 'objects') as backlogs, \
                 patch.object(views.ProductionLock, 'objects') as locks, \
                 patch.object(views.transaction, 'atomic', side_effect=lambda: nullcontext()):
                lines.filter.return_value.first.return_value = SimpleNamespace(id=1, line_type=line_type)
                source = backlogs.filter.return_value if line_type == 'PURCHASE' else plans.all.return_value
                source.filter.return_value.aggregate.return_value = {'qty': Decimal(30)}
                request = SimpleNamespace(user=None, data=dict(lock_type='auto_plan', line_id=1,
                    product_id=2, plan_date='2026-09-14', locked_qty=40))
                self.assertEqual(views.ProductionLockView().post(request).status_code, 409)
                locks.get_or_create.assert_not_called()
                request.data['locked_qty'] = 30
                locks.get_or_create.return_value = (SimpleNamespace(id=1, locked_qty=Decimal(30)), True)
                self.assertEqual(views.ProductionLockView().post(request).status_code, 201)
                locks.get_or_create.return_value = (SimpleNamespace(id=1, locked_qty=Decimal(20)), False)
                self.assertEqual(views.ProductionLockView().post(request).status_code, 409)

    def test_lock_requires_product_and_quantity(self):
        serializer = views.LockCreateSerializer(data=dict(lock_type='auto_plan', line_id=1, plan_date='2026-09-14'))
        self.assertFalse(serializer.is_valid())
        self.assertIn('product_id', serializer.errors)
        self.assertIn('locked_qty', serializer.errors)
