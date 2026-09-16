from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from masters.models import Calendar, CalendarDay, Customer, Line, Process, Product, Routing, RoutingStep
from orders.core.models import Order, OrderLine
from production.models import LineDemand
from production.services.order_expansion import OrderExpansionService


class OrderExpansionServiceTest(TestCase):
    def setUp(self):
        self.calendar = Calendar.objects.create(
            calendar_code='daiso',
            calendar_name='ダイソー',
        )
        self.line = Line.objects.create(
            line_code='L1',
            line_name='ライン1',
            calendar=self.calendar,
            lead_time_days=0,
        )
        self.process = Process.objects.create(
            process_code='P1',
            process_name='工程1',
            line=self.line,
        )
        self.customer = Customer.objects.create(
            customer_code='C001',
            customer_name='得意先1',
        )
        self.product = Product.objects.create(
            product_code='FG-A',
            product_name='完成品A',
            is_final_product=True,
        )
        self.routing = Routing.objects.create(
            product=self.product,
            routing_code='R1',
            is_default=True,
            is_active=True,
        )
        self.step = RoutingStep.objects.create(
            routing=self.routing,
            step_no=1,
            process=self.process,
            line=self.line,
            output_product=self.product,
            hierarchy_path='final',
            time_unit='DAY',
            lead_time_days=0,
        )

    def _create_order_line(self, order_no, order_type, quantity, due_date, is_expanded=False, ship_to_code=''):
        order = Order.objects.create(
            customer=self.customer,
            order_no=order_no,
            order_type=order_type,
            status='OPEN',
            version_no='v1',
        )
        return OrderLine.objects.create(
            order=order,
            line_no=1,
            product=self.product,
            product_code=self.product.product_code,
            order_type=order_type,
            quantity=Decimal(str(quantity)),
            due_date=due_date,
            is_expanded=is_expanded,
            ship_to_code=ship_to_code,
        )

    @patch('production.services.order_expansion.get_business_today', return_value=date(2026, 8, 1))
    def test_period_rebuild_preserves_earlier_demand_and_rebuilds_firm_only(self, _today):
        old = self._create_order_line('OLD', 'FIRM', 7, '2026-08-31')
        target = self._create_order_line('TARGET', 'FIRM', 5, '2026-09-01')
        OrderExpansionService().expand_firm_order_lines([old.id, target.id])
        old_demand = LineDemand.objects.get(plan_date='2026-08-31')
        old_snapshot = LineDemand.objects.filter(pk=old_demand.pk).values().get()
        LineDemand.objects.filter(plan_date='2026-09-01').update(actual_qty=2)
        unexpanded_old = self._create_order_line('OLD-UNEXPANDED', 'FIRM', 3, '2026-08-30')
        new = self._create_order_line('NEW', 'FIRM', 4, '2026-09-01')
        self._create_order_line('FORECAST', 'FORECAST', 9, '2026-09-02')
        LineDemand.objects.create(
            line=self.line,
            routing_step=self.step,
            process=self.process,
            product=self.product,
            product_code=self.product.product_code,
            plan_date='2026-09-02',
            forecast_qty=Decimal('9'),
            firm_qty=Decimal('0'),
            plan_qty=Decimal('9'),
        )

        for _ in range(2):
            result = OrderExpansionService().rebuild_from_due_date(date(2026, 9, 1))
            self.assertFalse(result['errors'])
            self.assertEqual(LineDemand.objects.filter(pk=old_demand.pk).values().get(), old_snapshot)
            target_demand = LineDemand.objects.get(plan_date='2026-09-01')
            self.assertEqual(target_demand.firm_qty, Decimal('9'))
            self.assertEqual(target_demand.actual_qty, Decimal('0'))
            self.assertFalse(LineDemand.objects.filter(plan_date='2026-09-02').exists())
        unexpanded_old.refresh_from_db()
        new.refresh_from_db()
        self.assertFalse(unexpanded_old.is_expanded)
        self.assertTrue(new.is_expanded)

    def test_period_rebuild_skips_demand_before_start_date(self):
        self.step.lead_time_days = 3
        self.step.save(update_fields=['lead_time_days'])
        for day in range(25, 32):
            CalendarDay.objects.create(calendar=self.calendar, target_date=date(2026, 8, day), is_working_day=True)
        CalendarDay.objects.create(calendar=self.calendar, target_date=date(2026, 9, 1), is_working_day=True)
        self._create_order_line('SHIFTED', 'FIRM', 5, '2026-09-01')
        result = OrderExpansionService().rebuild_from_due_date(date(2026, 9, 1))
        self.assertFalse(result['errors'])
        self.assertFalse(LineDemand.objects.exists())

    def test_period_rebuild_rolls_back_when_expansion_fails(self):
        target = self._create_order_line('ROLLBACK', 'FIRM', 5, '2026-09-01')
        OrderExpansionService().expand_firm_order_lines([target.id])
        snapshot = list(LineDemand.objects.values())
        service = OrderExpansionService()

        with patch.object(service, '_apply_incremental_firm_demands', side_effect=RuntimeError('テスト用エラー')):
            with self.assertRaises(RuntimeError):
                service.rebuild_from_due_date(date(2026, 9, 1))
        target.refresh_from_db()
        self.assertTrue(target.is_expanded)
        self.assertEqual(list(LineDemand.objects.values()), snapshot)

    def test_period_rebuild_rejects_invalid_start_date(self):
        from rest_framework.test import APIRequestFactory, force_authenticate
        from types import SimpleNamespace
        from production.views_line_demand import LineDemandViewSet

        view = LineDemandViewSet.as_view({'post': 'rebuild_from_date'})
        for payload in ({}, {'due_date_from': ''}, {'due_date_from': '2026-02-30'}):
            request = APIRequestFactory().post('/line-demands/rebuild-from-date/', payload, format='json')
            force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
            with patch('production.views_line_demand.OrderExpansionService') as service:
                response = view(request)
            self.assertEqual(response.status_code, 400)
            service.assert_not_called()

    def test_incremental_expand_replaces_forecast_and_increments_new_firm(self):
        due_date = '2026-04-10'
        existing_firm = self._create_order_line('FIRM-OLD', 'FIRM', '5', due_date, is_expanded=True)
        new_firm = self._create_order_line('FIRM-NEW', 'FIRM', '2', due_date, is_expanded=False)
        forecast = self._create_order_line('FC-NEW', 'FORECAST', '7', due_date, is_expanded=False)

        existing_demand = LineDemand.objects.create(
            line=self.line,
            routing_step=self.step,
            process=self.process,
            product=self.product,
            product_code=self.product.product_code,
            plan_date=due_date,
            lead_time_days=0,
            is_shifted=False,
            firm_is_shifted=False,
            forecast_is_shifted=False,
            forecast_qty=Decimal('3'),
            firm_qty=Decimal('5'),
            plan_qty=Decimal('8'),
            actual_qty=Decimal('2'),
            plan_progress=Decimal('1.000'),
            actual_progress=Decimal('0.000'),
            order_numbers='FC-OLD,FIRM-OLD',
            firm_order_numbers='FIRM-OLD',
            forecast_order_numbers='FC-OLD',
        )

        result = OrderExpansionService().expand_open_orders(clear_existing=False)

        demand = LineDemand.objects.get(
            line=self.line,
            product_code=self.product.product_code,
            plan_date=due_date,
        )
        new_firm.refresh_from_db()
        existing_firm.refresh_from_db()
        forecast.refresh_from_db()

        self.assertFalse(result['forced_full_rebuild'])
        self.assertEqual(demand.forecast_qty, Decimal('7'))
        self.assertEqual(demand.firm_qty, Decimal('7'))
        self.assertEqual(demand.plan_qty, Decimal('14'))
        self.assertEqual(demand.actual_qty, Decimal('2'))
        self.assertEqual(demand.forecast_order_numbers, 'FC-NEW')
        self.assertEqual(demand.firm_order_numbers, 'FIRM-NEW,FIRM-OLD')
        self.assertNotEqual(demand.id, existing_demand.id)
        self.assertEqual(result['deleted'], 1)
        self.assertTrue(new_firm.is_expanded)
        self.assertTrue(existing_firm.is_expanded)
        self.assertFalse(forecast.is_expanded)

    def test_incremental_expand_keeps_unchanged_forecast_demand(self):
        due_date = '2026-04-10'
        self._create_order_line('FC-UNCHANGED', 'FORECAST', '7', due_date)

        first_result = OrderExpansionService().expand_open_orders(clear_existing=False)
        demand = LineDemand.objects.get(
            line=self.line,
            product_code=self.product.product_code,
            plan_date=due_date,
        )
        demand_id = demand.id

        second_result = OrderExpansionService().expand_open_orders(clear_existing=False)
        demand.refresh_from_db()

        self.assertEqual(first_result['created'], 1)
        self.assertEqual(second_result['created'], 0)
        self.assertEqual(second_result['deleted'], 0)
        self.assertEqual(second_result['updated'], 0)
        self.assertEqual(demand.id, demand_id)

    def test_first_incremental_run_forces_full_rebuild_when_all_open_firm_are_unexpanded(self):
        due_date = '2026-04-11'
        line1 = self._create_order_line('FIRM-A', 'FIRM', '5', due_date, is_expanded=False)
        line2 = self._create_order_line('FIRM-B', 'FIRM', '2', due_date, is_expanded=False)

        LineDemand.objects.create(
            line=self.line,
            routing_step=self.step,
            product=self.product,
            product_code=self.product.product_code,
            plan_date=due_date,
            lead_time_days=0,
            forecast_qty=Decimal('0'),
            firm_qty=Decimal('99'),
            plan_qty=Decimal('99'),
            actual_qty=Decimal('0'),
            plan_progress=Decimal('1.000'),
            actual_progress=Decimal('0.000'),
            order_numbers='STALE',
            firm_order_numbers='STALE',
            forecast_order_numbers='',
        )

        result = OrderExpansionService().expand_open_orders(clear_existing=False)

        demand = LineDemand.objects.get(
            line=self.line,
            product_code=self.product.product_code,
            plan_date=due_date,
        )
        line1.refresh_from_db()
        line2.refresh_from_db()

        self.assertTrue(result['forced_full_rebuild'])
        self.assertEqual(demand.firm_qty, Decimal('7'))
        self.assertEqual(demand.forecast_qty, Decimal('0'))
        self.assertEqual(demand.firm_order_numbers, 'FIRM-A,FIRM-B')
        self.assertTrue(line1.is_expanded)
        self.assertTrue(line2.is_expanded)

    def test_customer_and_line_calendar_both_must_be_working_for_required_date(self):
        customer_calendar = Calendar.objects.create(
            calendar_code='tiera',
            calendar_name='ティエラ',
        )
        self.customer.calendar = customer_calendar
        self.customer.save(update_fields=['calendar'])
        CalendarDay.objects.create(
            calendar=customer_calendar,
            target_date='2026-07-20',
            is_working_day=False,
        )
        CalendarDay.objects.create(
            calendar=self.calendar,
            target_date='2026-07-18',
            is_working_day=False,
        )

        self._create_order_line('FIRM-CAL', 'FIRM', '1', '2026-07-20', is_expanded=False)

        result = OrderExpansionService().expand_open_orders(clear_existing=False)

        demand = LineDemand.objects.get(
            line=self.line,
            product_code=self.product.product_code,
            plan_date='2026-07-16',
        )

        self.assertFalse(result['forced_full_rebuild'])
        self.assertEqual(demand.firm_qty, Decimal('1'))

    @patch('production.services.order_expansion.get_business_today', return_value=date(2026, 8, 21))
    def test_forecast_due_today_or_past_is_not_expanded(self, _mock_today):
        self._create_order_line('FC-PAST', 'FORECAST', '4', '2026-08-20', is_expanded=False)
        self._create_order_line('FC-TODAY', 'FORECAST', '5', '2026-08-21', is_expanded=False)
        self._create_order_line('FC-FUTURE', 'FORECAST', '6', '2026-08-22', is_expanded=False)
        self._create_order_line('FIRM-TODAY', 'FIRM', '7', '2026-08-21', is_expanded=False)

        result = OrderExpansionService().expand_open_orders(clear_existing=False)

        demands = {
            demand.plan_date: demand
            for demand in LineDemand.objects.filter(
                line=self.line,
                product_code=self.product.product_code,
            )
        }

        self.assertFalse(result['forced_full_rebuild'])
        self.assertNotIn('2026-08-20', {str(key) for key in demands.keys()})
        self.assertIn('2026-08-21', {str(key) for key in demands.keys()})
        self.assertIn('2026-08-22', {str(key) for key in demands.keys()})
        self.assertEqual(demands['2026-08-21'].firm_qty, Decimal('7'))
        self.assertEqual(demands['2026-08-21'].forecast_qty, Decimal('0'))
        self.assertEqual(demands['2026-08-22'].forecast_qty, Decimal('6'))

    def test_revert_firm_order_lines_subtracts_demand_and_marks_unexpanded(self):
        due_date = '2026-08-20'
        order_line = self._create_order_line('FIRM-ROLLBACK', 'FIRM', '5', due_date, is_expanded=True)

        LineDemand.objects.create(
            line=self.line,
            routing_step=self.step,
            process=self.process,
            product=self.product,
            product_code=self.product.product_code,
            plan_date=due_date,
            lead_time_days=0,
            forecast_qty=Decimal('0'),
            firm_qty=Decimal('5'),
            plan_qty=Decimal('5'),
            actual_qty=Decimal('0'),
            plan_progress=Decimal('1.000'),
            actual_progress=Decimal('0.000'),
            order_numbers='FIRM-ROLLBACK',
            firm_order_numbers='FIRM-ROLLBACK',
            forecast_order_numbers='',
        )

        result = OrderExpansionService().revert_firm_order_lines([order_line.id])

        order_line.refresh_from_db()

        self.assertEqual(result['reverted_order_lines'], 1)
        self.assertEqual(result['deleted_demands'], 1)
        self.assertFalse(result['errors'])
        self.assertFalse(order_line.is_expanded)
        self.assertIsNone(order_line.expanded_at)
        self.assertFalse(LineDemand.objects.filter(
            line=self.line,
            product_code=self.product.product_code,
            plan_date=due_date,
        ).exists())

    def test_revert_accepts_recreated_routing_step_id(self):
        due_date = '2026-08-20'
        order_line = self._create_order_line('FIRM-OLD-STEP', 'FIRM', '5', due_date, is_expanded=True)
        old_routing = Routing.objects.create(
            product=self.product,
            routing_code='R-OLD',
            is_default=False,
            is_active=False,
        )
        old_step = RoutingStep.objects.create(
            routing=old_routing,
            step_no=self.step.step_no,
            process=self.process,
            line=self.line,
            output_product=self.product,
            hierarchy_path='final',
            time_unit='DAY',
            lead_time_days=0,
        )
        LineDemand.objects.create(
            line=self.line,
            routing_step=old_step,
            process=self.process,
            product=self.product,
            product_code=self.product.product_code,
            plan_date=due_date,
            lead_time_days=0,
            forecast_qty=Decimal('0'),
            firm_qty=Decimal('5'),
            plan_qty=Decimal('5'),
            actual_qty=Decimal('0'),
            order_numbers='FIRM-OLD-STEP',
            firm_order_numbers='FIRM-OLD-STEP',
        )

        result = OrderExpansionService().revert_firm_order_lines([order_line.id])

        self.assertFalse(result['errors'])
        self.assertEqual(result['reverted_order_lines'], 1)
        self.assertFalse(LineDemand.objects.filter(routing_step=old_step).exists())

    def test_expand_firm_order_lines_recreates_demand_for_target_only(self):
        due_date = '2026-08-21'
        order_line = self._create_order_line('FIRM-REBUILD', 'FIRM', '4', due_date, is_expanded=False)

        result = OrderExpansionService().expand_firm_order_lines([order_line.id])

        order_line.refresh_from_db()
        demand = LineDemand.objects.get(
            line=self.line,
            product_code=self.product.product_code,
            plan_date=due_date,
        )

        self.assertEqual(result['expanded_order_lines'], 1)
        self.assertFalse(result['errors'])
        self.assertTrue(order_line.is_expanded)
        self.assertIsNotNone(order_line.expanded_at)
        self.assertEqual(demand.firm_qty, Decimal('4'))
        self.assertEqual(demand.firm_order_numbers, 'FIRM-REBUILD')

    def test_ship_to_code_creates_separate_demands(self):
        due_date = '2026-04-12'
        self._create_order_line('FIRM-A', 'FIRM', '3', due_date, ship_to_code='000010')
        self._create_order_line('FIRM-B', 'FIRM', '5', due_date, ship_to_code='000030')

        OrderExpansionService().expand_open_orders(clear_existing=True)

        demands = LineDemand.objects.filter(
            line=self.line,
            product_code=self.product.product_code,
            plan_date=due_date,
        ).order_by('ship_to_code')
        self.assertEqual(demands.count(), 2)
        d1 = demands.get(ship_to_code='000010')
        d2 = demands.get(ship_to_code='000030')
        self.assertEqual(d1.firm_qty, Decimal('3'))
        self.assertEqual(d2.firm_qty, Decimal('5'))

    def test_revert_with_ship_to_code_affects_only_matching_row(self):
        due_date = '2026-04-13'
        ol_a = self._create_order_line('FIRM-C', 'FIRM', '4', due_date, is_expanded=True, ship_to_code='000010')
        ol_b = self._create_order_line('FIRM-D', 'FIRM', '6', due_date, is_expanded=True, ship_to_code='000030')

        LineDemand.objects.create(
            line=self.line, routing_step=self.step, process=self.process,
            product=self.product, product_code=self.product.product_code,
            ship_to_code='000010', plan_date=due_date, lead_time_days=0,
            forecast_qty=0, firm_qty=Decimal('4'), plan_qty=Decimal('4'),
            actual_qty=0, order_numbers='FIRM-C', firm_order_numbers='FIRM-C',
        )
        LineDemand.objects.create(
            line=self.line, routing_step=self.step, process=self.process,
            product=self.product, product_code=self.product.product_code,
            ship_to_code='000030', plan_date=due_date, lead_time_days=0,
            forecast_qty=0, firm_qty=Decimal('6'), plan_qty=Decimal('6'),
            actual_qty=0, order_numbers='FIRM-D', firm_order_numbers='FIRM-D',
        )

        result = OrderExpansionService().revert_firm_order_lines([ol_a.id])

        self.assertEqual(result['reverted_order_lines'], 1)
        self.assertFalse(result['errors'])
        remaining = LineDemand.objects.filter(
            line=self.line, product_code=self.product.product_code, plan_date=due_date,
        )
        self.assertEqual(remaining.count(), 1)
        self.assertEqual(remaining.first().ship_to_code, '000030')
        self.assertEqual(remaining.first().firm_qty, Decimal('6'))
