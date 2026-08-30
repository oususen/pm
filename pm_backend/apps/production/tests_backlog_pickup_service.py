from datetime import date
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from masters.models import Line, Process, Product, Routing, RoutingStep
from production.models import LineDemand
from production.models_line_backlog import LineBacklog
from production.services.backlog_pickup_service import pickup, seed_progress_backlogs_from_demand


class BacklogPickupServiceTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.deps = {
            'parse_optional_date': lambda value: date.fromisoformat(value) if value else None,
            'parse_product_ids': lambda value: value,
            'invalid_sequence_sort_value': 999999,
            'floor_shipping_pm_sequence_threshold': 900000,
            'is_floor_shipping_delivery_line': lambda *_args, **_kwargs: False,
            'is_kubota_delivery_line': lambda *_args, **_kwargs: False,
        }

    @patch('production.services.backlog_pickup_service._notify_backlog_process_resolution_failure')
    def test_raise_when_purchase_demand_process_is_missing(self, mock_notify):
        line = Line.objects.create(
            line_code='000030',
            line_name='購買ライン',
            line_type='PURCHASE',
        )
        product = Product.objects.create(
            product_code='TEST-PURCHASE',
            product_name='購買テスト品',
        )
        LineDemand.objects.create(
            line=line,
            product=product,
            product_code=product.product_code,
            plan_date=date(2026, 8, 24),
        )

        request = self.factory.post(
            '/production/linebacklogs/seed_progress_backlogs_from_demand/',
            {
                'start_date': '2026-08-24',
                'end_date': '2026-08-24',
            },
            format='json',
        )

        response = seed_progress_backlogs_from_demand(None, request, **self.deps)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'BACKLOG_PROCESS_MISSING')
        self.assertEqual(len(response.data['errors']), 1)
        self.assertEqual(response.data['errors'][0]['line_code'], '000030')
        self.assertEqual(LineBacklog.objects.count(), 0)
        mock_notify.assert_called_once()

    @patch('production.services.backlog_pickup_service._notify_backlog_process_resolution_failure')
    def test_create_backlog_when_demand_process_exists(self, mock_notify):
        line = Line.objects.create(
            line_code='LTEST-BACKLOG',
            line_name='進度空行補完ライン',
            line_type='PROD',
        )
        process = Process.objects.create(
            process_code='PTEST-BACKLOG',
            process_name='進度空行補完工程',
            line=line,
        )
        product = Product.objects.create(
            product_code='TEST-BACKLOG',
            product_name='進度空行補完品',
        )
        routing = Routing.objects.create(
            product=product,
            routing_code='RTEST-BACKLOG',
            is_default=True,
            is_active=True,
        )
        step = RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=process,
            line=line,
            output_product=product,
        )
        LineDemand.objects.create(
            line=line,
            routing_step=step,
            process=process,
            product=product,
            product_code=product.product_code,
            plan_date=date(2026, 8, 24),
        )

        request = self.factory.post(
            '/production/linebacklogs/seed_progress_backlogs_from_demand/',
            {
                'start_date': '2026-08-24',
                'end_date': '2026-08-24',
            },
            format='json',
        )

        response = seed_progress_backlogs_from_demand(None, request, **self.deps)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['created'], 1)
        self.assertEqual(LineBacklog.objects.count(), 1)
        backlog = LineBacklog.objects.get()
        self.assertEqual(backlog.line_id, line.id)
        self.assertEqual(backlog.process_id, process.id)
        self.assertEqual(backlog.product_id, product.id)
        mock_notify.assert_not_called()

    def test_pickup_final_product_resolves_demand_per_ship_to_then_sums(self):
        line = Line.objects.create(
            line_code='LTEST-PICKUP',
            line_name='需要取込ライン',
            line_type='PROD',
        )
        process = Process.objects.create(
            process_code='PTEST-PICKUP',
            process_name='需要取込工程',
            line=line,
        )
        product = Product.objects.create(
            product_code='TEST-FINAL',
            product_name='最終品テスト',
            is_final_product=True,
        )
        routing = Routing.objects.create(
            product=product,
            routing_code='RTEST-PICKUP',
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=process,
            line=line,
            output_product=product,
        )
        LineDemand.objects.create(
            line=line,
            process=process,
            product=product,
            product_code=product.product_code,
            ship_to_code='5476',
            plan_date=date(2026, 9, 4),
            forecast_qty=152,
            plan_qty=152,
        )
        LineDemand.objects.create(
            line=line,
            process=process,
            product=product,
            product_code=product.product_code,
            ship_to_code='833',
            plan_date=date(2026, 9, 4),
            firm_qty=40,
            plan_qty=40,
        )

        request = self.factory.post(
            '/production/linebacklogs/pickup/',
            {
                'line_id': line.id,
                'start_date': '2026-09-04',
                'end_date': '2026-09-04',
            },
            format='json',
        )

        response = pickup(None, request, **self.deps)

        self.assertEqual(response.status_code, 200)
        backlog = LineBacklog.objects.get(
            line_id=line.id,
            process_id=process.id,
            product_id=product.id,
            plan_date=date(2026, 9, 4),
            sequence_no=0,
        )
        self.assertEqual(backlog.order_qty, 192)
        self.assertEqual(backlog.order_qty_actual, 40)
        self.assertEqual(backlog.demand_qty_plan, 192)
