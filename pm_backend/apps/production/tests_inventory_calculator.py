from datetime import date
from unittest.mock import patch

from django.test import TestCase

from masters.models import Line, Process, Product
from production.inventory.inventory_calculator import recalculate_planned_stock_qty
from production.models_line_backlog import LineBacklog


class PlannedStockCalculatorTest(TestCase):
    @patch('production.inventory.inventory_calculator.get_business_today', return_value=date(2026, 3, 6))
    def test_calc_start_date_uses_stock_qty_for_display_and_next_day_anchor(self, _mock_today):
        line = Line.objects.create(
            line_code='LTEST-PS',
            line_name='計画在庫テストライン',
        )
        process = Process.objects.create(
            process_code='PTEST-PS',
            process_name='計画在庫テスト工程',
            line=line,
        )
        product = Product.objects.create(
            product_code='TEST-PLANNED-STOCK',
            product_name='計画在庫テスト品',
        )

        start_day = LineBacklog.objects.create(
            plan_date=date(2026, 3, 5),
            process=process,
            product=product,
            line=line,
            sequence_no=0,
            stock_qty=-5,
            planned_stock_qty=3,
        )
        extra_lot = LineBacklog.objects.create(
            plan_date=date(2026, 3, 5),
            process=process,
            product=product,
            line=line,
            sequence_no=1,
            plan_qty=2,
            planned_stock_qty=4,
        )
        next_day = LineBacklog.objects.create(
            plan_date=date(2026, 3, 6),
            process=process,
            product=product,
            line=line,
            sequence_no=0,
            stock_qty=-5,
            planned_stock_qty=0,
        )

        recalculate_planned_stock_qty(
            line.id,
            product.id,
            date(2026, 3, 5),
            date(2026, 3, 6),
        )

        start_day.refresh_from_db()
        extra_lot.refresh_from_db()
        next_day.refresh_from_db()

        self.assertEqual(start_day.planned_stock_qty, -5)
        self.assertEqual(extra_lot.planned_stock_qty, 0)
        self.assertEqual(next_day.planned_stock_qty, -5)
