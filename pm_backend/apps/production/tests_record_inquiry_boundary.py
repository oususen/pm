from datetime import date, datetime, timedelta

from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory

from masters.models import Line, Process, Product
from production.models_process_work_session import ProcessWorkSession
from production.views_process_realtime import ProcessRealtimeRecordViewSet


class ProcessRealtimeSessionsBoundaryTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.line = Line.objects.create(
            line_code='LTEST-FILTER',
            line_name='実績照会フィルタライン',
        )
        self.process = Process.objects.create(
            process_code='PTEST-FILTER',
            process_name='実績照会フィルタ工程',
            line=self.line,
        )
        self.product = Product.objects.create(
            product_code='TEST-FILTER',
            product_name='実績照会フィルタ品',
        )

    def make_dt(self, year, month, day, hour, minute=0):
        value = datetime(year, month, day, hour, minute)
        if settings.USE_TZ:
            return timezone.make_aware(value)
        return value

    def create_session(self, started_at):
        ended_at = started_at + timedelta(hours=1)
        return ProcessWorkSession.objects.create(
            process=self.process,
            product=self.product,
            product_code=self.product.product_code,
            product_name=self.product.product_name,
            plan_date=date(2026, 3, 10),
            session_no=1,
            session_type='WORK',
            start_action='START',
            end_action='END',
            started_at=started_at,
            ended_at=ended_at,
            status='CLOSED',
            duration_seconds=3600,
            production_qty=1,
        )

    def test_sessions_filter_uses_8am_business_day_boundary(self):
        before_boundary = self.create_session(self.make_dt(2026, 3, 10, 7, 59))
        start_of_day = self.create_session(self.make_dt(2026, 3, 10, 8, 0))
        end_of_day = self.create_session(self.make_dt(2026, 3, 11, 7, 59))
        next_day = self.create_session(self.make_dt(2026, 3, 11, 8, 0))

        view = ProcessRealtimeRecordViewSet.as_view({'get': 'sessions'})
        request = self.factory.get(
            '/api/process-realtime/sessions/',
            {'start_date': '2026-03-10', 'end_date': '2026-03-10'},
        )

        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = [row['id'] for row in response.data]
        self.assertIn(start_of_day.id, returned_ids)
        self.assertIn(end_of_day.id, returned_ids)
        self.assertNotIn(before_boundary.id, returned_ids)
        self.assertNotIn(next_day.id, returned_ids)
