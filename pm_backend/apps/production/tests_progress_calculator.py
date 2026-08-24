from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from masters.models import Line, Process, Product, Routing, RoutingStep
from production.inventory.progress_calculator import ProgressDemandResolutionError, recalculate_progress_qty
from production.models import LineDemand
from production.models_line_backlog import LineBacklog


class ProgressCalculatorTest(TestCase):
    @patch('production.inventory.progress_calculator.get_business_today', return_value=date(2026, 8, 24))
    def test_raise_when_product_demand_exists_but_step_demand_is_unresolved(self, _mock_today):
        line = Line.objects.create(
            line_code='LTEST-PROG',
            line_name='進度テストライン',
        )
        process = Process.objects.create(
            process_code='PTEST-PROG',
            process_name='進度テスト工程',
            line=line,
        )
        product = Product.objects.create(
            product_code='TEST-PROGRESS',
            product_name='進度テスト品',
        )

        LineBacklog.objects.create(
            plan_date=date(2026, 8, 24),
            process=process,
            product=product,
            line=line,
            sequence_no=0,
            plan_qty=0,
            actual_qty=0,
            progress_qty=0,
            planned_progress_qty=0,
        )
        LineDemand.objects.create(
            line=line,
            product=product,
            product_code=product.product_code,
            plan_date=date(2026, 8, 24),
            forecast_qty=Decimal('10'),
            firm_qty=Decimal('0'),
            plan_qty=Decimal('10'),
            actual_qty=Decimal('0'),
            plan_progress=Decimal('0'),
            actual_progress=Decimal('0'),
        )

        with self.assertRaises(ProgressDemandResolutionError) as ctx:
            recalculate_progress_qty(
                line.id,
                product.id,
                date(2026, 8, 24),
                date(2026, 8, 24),
                override_calc_start_date=date(2026, 8, 24),
            )

        self.assertEqual(len(ctx.exception.details), 1)
        self.assertEqual(ctx.exception.details[0]['reason'], 'routing_step需要未解決')

    @patch('production.inventory.progress_calculator.get_business_today', return_value=date(2026, 8, 24))
    def test_use_linedemand_process_demand_even_if_multiple_routing_steps_exist(self, _mock_today):
        line = Line.objects.create(
            line_code='000030',
            line_name='購買ライン',
        )
        process = Process.objects.create(
            process_code='PURCHASE',
            process_name='購買',
            line=line,
        )
        product = Product.objects.create(
            product_code='Z449558',
            product_name='テスト品',
        )
        routing1 = Routing.objects.create(
            product=product,
            routing_code='R1',
            is_default=True,
            is_active=True,
        )
        routing2 = Routing.objects.create(
            product=product,
            routing_code='R2',
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing1,
            step_no=5000,
            process=process,
            line=line,
            output_product=product,
        )
        demand_step = RoutingStep.objects.create(
            routing=routing2,
            step_no=5000,
            process=process,
            line=line,
            output_product=product,
        )

        backlog = LineBacklog.objects.create(
            plan_date=date(2026, 8, 19),
            process=process,
            product=product,
            line=line,
            sequence_no=0,
            plan_qty=0,
            actual_qty=0,
            progress_qty=0,
            planned_progress_qty=0,
        )
        LineDemand.objects.create(
            line=line,
            routing_step=demand_step,
            product=product,
            product_code=product.product_code,
            plan_date=date(2026, 8, 19),
            forecast_qty=Decimal('0'),
            firm_qty=Decimal('74'),
            plan_qty=Decimal('74'),
            actual_qty=Decimal('0'),
            plan_progress=Decimal('0'),
            actual_progress=Decimal('0'),
        )

        recalculate_progress_qty(
            line.id,
            product.id,
            date(2026, 8, 19),
            date(2026, 8, 19),
            override_calc_start_date=date(2026, 8, 19),
        )

        backlog.refresh_from_db()
        self.assertEqual(backlog.progress_qty, -74)
