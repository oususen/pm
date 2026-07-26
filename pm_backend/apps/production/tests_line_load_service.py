from decimal import Decimal

from django.test import TestCase

from masters.models import Calendar, Customer, Line, LineCycleTime, Process, Product, Routing, RoutingStep
from orders.core.models import Order, OrderLine
from production.models import LineDemand
from production.services.line_load_service import LineLoadService
from system_settings.models import SystemSetting


class LineLoadServiceTest(TestCase):
    def setUp(self):
        self.calendar = Calendar.objects.create(
            calendar_code='daiso',
            calendar_name='ダイソー',
        )
        self.line = Line.objects.create(
            line_code='L-BRAKE',
            line_name='ブレーキライン',
            calendar=self.calendar,
            line_type='PROD',
        )
        self.customer = Customer.objects.create(
            customer_code='C001',
            customer_name='得意先1',
        )
        self.process = Process.objects.create(
            process_code='4010',
            process_name='ブレーキティエラ',
            line=self.line,
            equipment_count=1,
        )
        self.product = Product.objects.create(
            product_code='YD40004397',
            product_name='プレート・フロア',
            is_final_product=True,
        )
        self.routing = Routing.objects.create(
            product=self.product,
            routing_code='R-YD40004397',
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
        LineCycleTime.objects.create(
            product=self.product,
            line=self.line,
            process=self.process,
            cycle_time_sec=Decimal('60'),
            is_active=True,
        )

    def _create_order_line(self, *, order_no, order_type, due_date, quantity):
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
        )

    def test_calculate_uses_linedemand_when_switch_setting_is_not_defined(self):
        LineDemand.objects.create(
            line=self.line,
            routing_step=self.step,
            product=self.product,
            product_code=self.product.product_code,
            plan_date='2026-07-10',
            lead_time_days=0,
            forecast_qty=Decimal('0'),
            firm_qty=Decimal('10'),
            plan_qty=Decimal('10'),
            actual_qty=Decimal('0'),
            plan_progress=Decimal('1.000'),
            actual_progress=Decimal('0.000'),
        )

        result = LineLoadService().calculate([self.line.id], '2026-07-01', '2026-07-31', 'monthly')

        self.assertEqual(result['demand_source_config']['orderline_until_date'], None)
        self.assertEqual(result['lines'][0]['data'][0]['line_load_sec'], 600.0)

    def test_calculate_switches_to_orderline_before_configured_date(self):
        SystemSetting.objects.create(
            key=LineLoadService.DEMAND_SOURCE_CONFIG_KEY,
            value='{"orderline_until_date":"2026-06-30"}',
            description='長期負荷チャートの需要ソース切替設定',
        )
        self._create_order_line(order_no='ORD-001', order_type='FIRM', due_date='2026-06-15', quantity='5')
        LineDemand.objects.create(
            line=self.line,
            routing_step=self.step,
            product=self.product,
            product_code=self.product.product_code,
            plan_date='2026-07-10',
            lead_time_days=0,
            forecast_qty=Decimal('0'),
            firm_qty=Decimal('10'),
            plan_qty=Decimal('10'),
            actual_qty=Decimal('0'),
            plan_progress=Decimal('1.000'),
            actual_progress=Decimal('0.000'),
        )

        result = LineLoadService().calculate([self.line.id], '2026-06-01', '2026-07-31', 'monthly')

        self.assertEqual(result['demand_source_config']['orderline_until_date_text'], '2026-06-30')
        self.assertEqual(len(result['lines'][0]['data']), 2)
        self.assertEqual(result['lines'][0]['data'][0]['date'], '2026-06-01')
        self.assertEqual(result['lines'][0]['data'][0]['line_load_sec'], 300.0)
        self.assertEqual(result['lines'][0]['data'][1]['date'], '2026-07-01')
        self.assertEqual(result['lines'][0]['data'][1]['line_load_sec'], 600.0)

    def test_orderline_forecast_is_ignored_when_same_source_key_has_firm(self):
        SystemSetting.objects.create(
            key=LineLoadService.DEMAND_SOURCE_CONFIG_KEY,
            value='{"orderline_until_date":"2026-06-30"}',
            description='長期負荷チャートの需要ソース切替設定',
        )
        order_firm = Order.objects.create(
            customer=self.customer,
            order_no='ORD-FIRM',
            order_type='FIRM',
            status='OPEN',
            version_no='v1',
        )
        order_forecast = Order.objects.create(
            customer=self.customer,
            order_no='ORD-FORECAST',
            order_type='FORECAST',
            status='OPEN',
            version_no='v1',
        )
        OrderLine.objects.create(
            order=order_firm,
            line_no=1,
            product=self.product,
            product_code=self.product.product_code,
            order_type='FIRM',
            quantity=Decimal('5'),
            due_date='2026-06-20',
            ship_to_code='A01',
        )
        OrderLine.objects.create(
            order=order_forecast,
            line_no=1,
            product=self.product,
            product_code=self.product.product_code,
            order_type='FORECAST',
            quantity=Decimal('3'),
            due_date='2026-06-20',
            ship_to_code='A01',
        )

        result = LineLoadService().calculate([self.line.id], '2026-06-01', '2026-06-30', 'monthly')

        self.assertEqual(result['lines'][0]['data'][0]['line_load_sec'], 300.0)
