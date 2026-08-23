from datetime import date

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from masters.models import Customer, Equipment, Line, Process, Product
from orders.core.models import Order, OrderLine
from production.models_laser_pattern import LaserPattern, LaserPatternFinishedProduct
from production.views_laser import LaserPatternViewSet


class LaserMonthlyMaterialSummaryTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.customer = Customer.objects.create(
            customer_code='CUST-LASER',
            customer_name='レーザ得意先',
        )
        self.line = Line.objects.create(
            line_code='L-LASER-B',
            line_name='レーザ予算ライン',
        )
        self.process = Process.objects.create(
            process_code='P-LASER-B',
            process_name='レーザ予算工程',
            line=self.line,
        )
        self.equipment = Equipment.objects.create(
            equipment_code='EQ-LASER-B',
            equipment_name='レーザ予算設備',
            line=self.line,
            process=self.process,
        )
        self.material = Product.objects.create(
            product_code='MAT-LASER-B',
            product_name='レーザ材料予算',
            category='MATERIAL',
            unit='枚',
        )
        self.finished_a = Product.objects.create(
            product_code='FIN-LASER-A',
            product_name='レーザ完成品A',
            is_final_product=True,
        )
        self.finished_b = Product.objects.create(
            product_code='FIN-LASER-B',
            product_name='レーザ完成品B',
            is_final_product=True,
        )

        self.pattern = LaserPattern.objects.create(
            pattern_no='PT-LASER-B1',
            material=self.material,
            equipment=self.equipment,
            process_time_min=1.5,
            is_budget_target=True,
        )
        LaserPatternFinishedProduct.objects.create(
            pattern=self.pattern,
            finished_product=self.finished_a,
            units_per_shot=2,
        )
        LaserPatternFinishedProduct.objects.create(
            pattern=self.pattern,
            finished_product=self.finished_b,
            units_per_shot=1,
        )

    def _create_order_line(self, product, due_date, quantity, order_type, line_no):
        order = Order.objects.create(
            customer=self.customer,
            order_no=f'{order_type}-{line_no}',
            order_type=order_type,
            status='OPEN',
        )
        return OrderLine.objects.create(
            order=order,
            line_no=line_no,
            product=product,
            product_code=product.product_code,
            order_type=order_type,
            quantity=quantity,
            due_date=due_date,
        )

    def test_monthly_summary_uses_firm_priority_and_sums_required_material_qty(self):
        self._create_order_line(self.finished_a, date(2026, 3, 10), 10, 'FORECAST', 1)
        self._create_order_line(self.finished_a, date(2026, 3, 10), 6, 'FIRM', 2)
        self._create_order_line(self.finished_a, date(2026, 3, 20), 4, 'FORECAST', 3)
        self._create_order_line(self.finished_b, date(2026, 3, 12), 7, 'FORECAST', 4)

        view = LaserPatternViewSet.as_view({'get': 'monthly_material_summary'})
        request = self.factory.get('/api/laser-patterns/monthly-material-summary/', {'month': '2026-03'})
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['month'], '2026-03')
        self.assertEqual(response.data['totals']['material_type_count'], 1)
        self.assertEqual(response.data['totals']['pattern_count'], 1)
        self.assertAlmostEqual(response.data['totals']['required_shots'], 12.0)
        self.assertAlmostEqual(response.data['totals']['required_material_qty'], 12.0)
        self.assertAlmostEqual(response.data['totals']['total_process_time_min'], 18.0)

        material_row = response.data['material_totals'][0]
        self.assertEqual(material_row['material_code'], 'MAT-LASER-B')
        self.assertAlmostEqual(material_row['required_shots'], 12.0)
        self.assertAlmostEqual(material_row['required_material_qty'], 12.0)

        equipment_row = response.data['equipment_totals'][0]
        self.assertEqual(equipment_row['equipment_code'], 'EQ-LASER-B')
        self.assertEqual(equipment_row['equipment_name'], 'レーザ予算設備')
        self.assertEqual(equipment_row['pattern_count'], 1)
        self.assertAlmostEqual(equipment_row['total_process_time_min'], 18.0)

        pattern_row = response.data['pattern_rows'][0]
        self.assertEqual(pattern_row['pattern_no'], 'PT-LASER-B1')
        self.assertAlmostEqual(pattern_row['required_shots'], 12.0)
        self.assertAlmostEqual(pattern_row['required_material_qty'], 12.0)
        self.assertAlmostEqual(pattern_row['total_process_time_min'], 18.0)

        finished_map = {
            item['finished_product_code']: item
            for item in pattern_row['finished_items']
        }
        self.assertAlmostEqual(finished_map['FIN-LASER-A']['material_per_unit'], 0.5)
        self.assertAlmostEqual(finished_map['FIN-LASER-A']['firm_qty'], 6.0)
        self.assertAlmostEqual(finished_map['FIN-LASER-A']['forecast_qty'], 14.0)
        self.assertAlmostEqual(finished_map['FIN-LASER-A']['selected_qty'], 10.0)
        self.assertEqual(finished_map['FIN-LASER-A']['selected_basis'], 'MIXED')
        self.assertAlmostEqual(finished_map['FIN-LASER-A']['required_material_qty'], 5.0)
        self.assertNotIn('required_shots', finished_map['FIN-LASER-A'])
        self.assertNotIn('produced_qty', finished_map['FIN-LASER-A'])
        self.assertNotIn('surplus_qty', finished_map['FIN-LASER-A'])
        self.assertAlmostEqual(finished_map['FIN-LASER-B']['material_per_unit'], 1.0)
        self.assertAlmostEqual(finished_map['FIN-LASER-B']['firm_qty'], 0.0)
        self.assertAlmostEqual(finished_map['FIN-LASER-B']['forecast_qty'], 7.0)
        self.assertAlmostEqual(finished_map['FIN-LASER-B']['selected_qty'], 7.0)
        self.assertEqual(finished_map['FIN-LASER-B']['selected_basis'], 'FORECAST')
        self.assertAlmostEqual(finished_map['FIN-LASER-B']['required_material_qty'], 7.0)

    def test_monthly_summary_returns_warning_for_duplicate_finished_product_mapping(self):
        second_pattern = LaserPattern.objects.create(
            pattern_no='PT-LASER-B2',
            material=self.material,
            equipment=self.equipment,
            process_time_min=1,
            is_budget_target=True,
        )
        LaserPatternFinishedProduct.objects.create(
            pattern=second_pattern,
            finished_product=self.finished_a,
            units_per_shot=1,
        )
        self._create_order_line(self.finished_a, date(2026, 3, 5), 3, 'FORECAST', 10)

        view = LaserPatternViewSet.as_view({'get': 'monthly_material_summary'})
        request = self.factory.get('/api/laser-patterns/monthly-material-summary/', {'month': '2026-03'})
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['warnings'])
        self.assertIn('FIN-LASER-A', response.data['warnings'][0])
