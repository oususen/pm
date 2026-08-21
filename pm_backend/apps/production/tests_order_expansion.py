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

    def _create_order_line(self, order_no, order_type, quantity, due_date, is_expanded=False):
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
        )

    def test_incremental_expand_replaces_forecast_and_increments_new_firm(self):
        due_date = '2026-04-10'
        existing_firm = self._create_order_line('FIRM-OLD', 'FIRM', '5', due_date, is_expanded=True)
        new_firm = self._create_order_line('FIRM-NEW', 'FIRM', '2', due_date, is_expanded=False)
        forecast = self._create_order_line('FC-NEW', 'FORECAST', '7', due_date, is_expanded=False)

        LineDemand.objects.create(
            line=self.line,
            routing_step=self.step,
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
            actual_qty=Decimal('0'),
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
        self.assertEqual(demand.forecast_order_numbers, 'FC-NEW')
        self.assertEqual(demand.firm_order_numbers, 'FIRM-NEW,FIRM-OLD')
        self.assertTrue(new_firm.is_expanded)
        self.assertTrue(existing_firm.is_expanded)
        self.assertFalse(forecast.is_expanded)

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
