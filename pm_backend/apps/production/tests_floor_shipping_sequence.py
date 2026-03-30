from datetime import date

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory

from masters.models import BOM, BOMItem, Line, Process, Product, Routing, RoutingStep
from production.models_line_backlog import LineBacklog
from production.models_line_plan import LinePlan
from production.views import LineBacklogViewSet, LinePlanViewSet


class FloorShippingSequenceRuleTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_floor_delivery_save_rejects_more_than_two_lots_per_day_product(self):
        line = Line.objects.create(
            line_code='L-FLOOR-DELIVERY',
            line_name='フロア配送',
        )
        process = Process.objects.create(
            process_code='P-FLOOR-DELIVERY',
            process_name='フロア配送工程',
            line=line,
        )
        product = Product.objects.create(
            product_code='TEST-FLOOR-DELIVERY',
            product_name='フロア配送テスト品',
        )

        view = LinePlanViewSet.as_view({'post': 'save'})
        request = self.factory.post(
            '/api/line-plans/save/',
            {
                'line_id': line.id,
                'items': [
                    {'product_id': product.id, 'process_id': process.id, 'plan_date': '2026-04-01', 'plan_qty': 10, 'sequence_no': 1},
                    {'product_id': product.id, 'process_id': process.id, 'plan_date': '2026-04-01', 'plan_qty': 20, 'sequence_no': 2},
                    {'product_id': product.id, 'process_id': process.id, 'plan_date': '2026-04-01', 'plan_qty': 30, 'sequence_no': 3},
                ],
            },
            format='json',
        )
        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('2件まで', str(response.data.get('detail')))
        self.assertEqual(LinePlan.objects.count(), 0)

    def test_pickup_uses_floor_delivery_sequence_rank_for_lt(self):
        floor_line = Line.objects.create(
            line_code='L-FLOOR',
            line_name='フロアライン',
        )
        delivery_line = Line.objects.create(
            line_code='L-FLOOR-DELIVERY',
            line_name='フロア配送',
        )

        floor_process = Process.objects.create(
            process_code='P-FLOOR',
            process_name='フロア工程',
            line=floor_line,
        )
        delivery_process = Process.objects.create(
            process_code='P-FLOOR-DELIVERY',
            process_name='フロア配送工程',
            line=delivery_line,
        )

        floor_product = Product.objects.create(
            product_code='TEST-FLOOR-PRODUCT',
            product_name='フロア品',
        )
        delivery_product = Product.objects.create(
            product_code='TEST-DELIVERY-PRODUCT',
            product_name='配送品',
        )

        BOMItem.objects.create(
            bom=BOM.objects.create(
                parent_product=delivery_product,
                version='v1',
                valid_from=date(2026, 1, 1),
            ),
            child_product=floor_product,
            quantity=1,
        )

        RoutingStep.objects.create(
            routing=Routing.objects.create(
                product=floor_product,
                routing_code='FLOOR-ROUTE',
                is_default=True,
            ),
            step_no=1,
            process=floor_process,
            line=floor_line,
            output_product=floor_product,
            hierarchy_path='1',
            hierarchy_depth=1,
            time_unit='DAY',
            lead_time_days=1,
        )
        RoutingStep.objects.create(
            routing=Routing.objects.create(
                product=delivery_product,
                routing_code='DELIVERY-ROUTE',
                is_default=True,
            ),
            step_no=1,
            process=delivery_process,
            line=delivery_line,
            output_product=delivery_product,
            hierarchy_path='1',
            hierarchy_depth=1,
            time_unit='DAY',
            lead_time_days=1,
        )

        LineBacklog.objects.create(
            plan_date=date(2026, 4, 2),
            process=delivery_process,
            product=delivery_product,
            line=delivery_line,
            sequence_no=1,
            plan_qty=10,
            plan_id='LOT-AM',
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 4, 2),
            process=delivery_process,
            product=delivery_product,
            line=delivery_line,
            sequence_no=2,
            plan_qty=20,
            plan_id='LOT-PM',
        )

        view = LineBacklogViewSet.as_view({'post': 'pickup'})
        request = self.factory.post(
            '/api/line-backlogs/pickup/',
            {
                'line_id': floor_line.id,
                'start_date': '2026-04-01',
                'end_date': '2026-04-02',
            },
            format='json',
        )
        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        same_day = LineBacklog.objects.get(
            line=floor_line,
            process=floor_process,
            product=floor_product,
            plan_date=date(2026, 4, 2),
            sequence_no=0,
        )
        previous_day = LineBacklog.objects.get(
            line=floor_line,
            process=floor_process,
            product=floor_product,
            plan_date=date(2026, 4, 1),
            sequence_no=0,
        )

        self.assertEqual(same_day.order_qty, 10)
        self.assertEqual(previous_day.order_qty, 20)
