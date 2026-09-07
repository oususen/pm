from datetime import date

from django.test import TestCase

from masters.models import Line, Process, Product
from production.models_line_backlog import LineBacklog
from purchase.services_auto_order_send import _load_first_cycle_progress_basis


class AutoOrderSendProgressBasisTest(TestCase):
    def setUp(self):
        self.line = Line.objects.create(line_code='TEST-PURCHASE', line_name='テスト購買', line_type='PURCHASE')
        self.process = Process.objects.create(process_code='PURCHASE', process_name='購入', line=self.line)
        self.product = Product.objects.create(product_code='TEST-PART', product_name='テスト部品')

    def add_day(self, plan_date, planned_progress, actual_qty, plan_qty):
        LineBacklog.objects.create(
            line=self.line, process=self.process, product=self.product, plan_date=plan_date,
            sequence_no=0, planned_progress_qty=planned_progress, actual_qty=actual_qty,
        )
        LineBacklog.objects.create(
            line=self.line, process=self.process, product=self.product, plan_date=plan_date,
            sequence_no=1, plan_qty=plan_qty,
        )

    def test_past_business_day_is_not_corrected_again(self):
        self.add_day(date(2026, 9, 6), planned_progress=100, actual_qty=4, plan_qty=10)

        result = _load_first_cycle_progress_basis(
            self.line, [self.product.id], delivery_date=date(2026, 9, 7), send_date=date(2026, 9, 7),
        )

        self.assertEqual(result[self.product.id], 100)

    def test_send_date_is_required(self):
        with self.assertRaises(TypeError):
            _load_first_cycle_progress_basis(
                self.line, [self.product.id], delivery_date=date(2026, 9, 7),
            )

    def test_business_day_is_corrected_from_plan_to_actual(self):
        self.add_day(date(2026, 9, 7), planned_progress=100, actual_qty=4, plan_qty=10)

        result = _load_first_cycle_progress_basis(
            self.line, [self.product.id], delivery_date=date(2026, 9, 8), send_date=date(2026, 9, 7),
        )

        self.assertEqual(result[self.product.id], 94)

    def test_business_day_correction_is_added_when_basis_is_another_day(self):
        self.add_day(date(2026, 9, 8), planned_progress=100, actual_qty=0, plan_qty=10)
        self.add_day(date(2026, 9, 7), planned_progress=0, actual_qty=2, plan_qty=3)

        result = _load_first_cycle_progress_basis(
            self.line, [self.product.id], delivery_date=date(2026, 9, 9), send_date=date(2026, 9, 7),
        )

        self.assertEqual(result[self.product.id], 99)
