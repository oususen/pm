from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory

from masters.models import Line, Process, Product
from production.models_line_backlog import LineBacklog
from production.models_process_work_session_change_history import ProcessWorkSessionChangeHistory
from production.models_process_work_session import ProcessWorkSession
from production.views_process_realtime import (
    ProcessRealtimeRecordViewSet,
    _recalculate_inventory_after_session_change,
)


class ProcessRealtimeSessionRecalcTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.line = Line.objects.create(
            line_code='LTEST-RT',
            line_name='実績再計算ライン',
        )
        self.process = Process.objects.create(
            process_code='PTEST-RT',
            process_name='実績再計算工程',
            line=self.line,
        )
        self.product = Product.objects.create(
            product_code='TEST-RT',
            product_name='実績再計算品',
        )

    def make_dt(self, year, month, day, hour, minute=0):
        value = datetime(year, month, day, hour, minute)
        if settings.USE_TZ:
            return timezone.make_aware(value)
        return value

    @patch('production.inventory.inventory_calculator.recalculate_inventory_for_line')
    def test_recalculate_helper_uses_plan_date_cutoff(self, mock_recalculate):
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product=self.product,
            line=self.line,
            sequence_no=0,
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 7),
            process=self.process,
            product=self.product,
            line=self.line,
            sequence_no=0,
        )

        session = SimpleNamespace(plan_date=date(2026, 3, 5), process=self.process)

        _recalculate_inventory_after_session_change(session)

        mock_recalculate.assert_called_once_with(
            line_id=self.line.id,
            start_date=date(2026, 3, 5),
            end_date=date(2026, 3, 7),
            include_progress=True,
            line_final_only=False,
            guard_cutoff=date(2026, 3, 4),
        )

    @patch('production.views_process_realtime._recalculate_inventory_after_session_change')
    @patch('production.views_process_realtime.resolve_workday_date_for_process', return_value=date(2026, 3, 5))
    def test_create_manual_session_triggers_recalculation(self, _mock_plan_date, mock_recalculate):
        view = ProcessRealtimeRecordViewSet.as_view({'post': 'sessions'})
        request = self.factory.post(
            '/api/process-realtime/sessions/',
            {
                'process_id': self.process.id,
                'product_code': self.product.product_code,
                'started_at': '2026-03-05T09:00:00',
                'ended_at': '2026-03-05T10:00:00',
                'production_qty': 5,
                'change_reason': '登録漏れ補完',
            },
            format='json',
        )

        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = ProcessWorkSession.objects.get()
        backlog = LineBacklog.objects.get(
            line=self.line,
            process=self.process,
            product=self.product,
            plan_date=date(2026, 3, 5),
            sequence_no=0,
        )
        self.assertEqual(backlog.actual_qty, 5)
        history = ProcessWorkSessionChangeHistory.objects.get(session_record_id=session.id)
        self.assertEqual(history.operation_type, 'ADD')
        self.assertEqual(history.reason, '登録漏れ補完')
        mock_recalculate.assert_called_once()
        self.assertEqual(mock_recalculate.call_args[0][0].id, session.id)

    @patch('production.views_process_realtime._recalculate_inventory_after_session_change')
    def test_session_detail_update_creates_history(self, mock_recalculate):
        started_at = self.make_dt(2026, 3, 5, 9)
        ended_at = self.make_dt(2026, 3, 5, 10)
        session = ProcessWorkSession.objects.create(
            process=self.process,
            product=self.product,
            product_code=self.product.product_code,
            product_name=self.product.product_name,
            plan_date=date(2026, 3, 5),
            session_no=1,
            session_type='WORK',
            start_action='MANUAL',
            end_action='END',
            started_at=started_at,
            ended_at=ended_at,
            status='CLOSED',
            duration_seconds=3600,
            production_qty=5,
        )

        view = ProcessRealtimeRecordViewSet.as_view({'patch': 'session_detail'})
        request = self.factory.patch(
            f'/api/process-realtime/sessions/{session.id}/',
            {
                'production_qty': 7,
                'change_reason': '数量訂正',
            },
            format='json',
        )
        response = view(request, session_id=session.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        history = ProcessWorkSessionChangeHistory.objects.get(session_record_id=session.id)
        self.assertEqual(history.operation_type, 'UPDATE')
        self.assertEqual(history.reason, '数量訂正')
        self.assertIn('実績数量', history.change_summary)
        self.assertEqual(int(history.before_data['production_qty']), 5)
        self.assertEqual(int(history.after_data['production_qty']), 7)
        mock_recalculate.assert_called_once()

    @patch('production.views_process_realtime._recalculate_inventory_after_session_change')
    def test_session_detail_delete_triggers_recalculation(self, mock_recalculate):
        started_at = self.make_dt(2026, 3, 5, 9)
        ended_at = self.make_dt(2026, 3, 5, 10)
        session = ProcessWorkSession.objects.create(
            process=self.process,
            product=self.product,
            product_code=self.product.product_code,
            product_name=self.product.product_name,
            plan_date=date(2026, 3, 5),
            session_no=1,
            session_type='WORK',
            start_action='MANUAL',
            end_action='END',
            started_at=started_at,
            ended_at=ended_at,
            status='CLOSED',
            duration_seconds=3600,
            production_qty=5,
        )
        backlog = LineBacklog.objects.create(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product=self.product,
            line=self.line,
            sequence_no=0,
            actual_qty=5,
        )

        view = ProcessRealtimeRecordViewSet.as_view({'delete': 'session_detail'})
        request = self.factory.delete(
            f'/api/process-realtime/sessions/{session.id}/',
            {
                'change_reason': '誤登録のため削除',
            },
            format='json',
        )
        response = view(request, session_id=session.id)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        backlog.refresh_from_db()
        self.assertEqual(backlog.actual_qty, 0)
        self.assertFalse(ProcessWorkSession.objects.filter(id=session.id).exists())
        history = ProcessWorkSessionChangeHistory.objects.get(session_record_id=session.id)
        self.assertEqual(history.operation_type, 'DELETE')
        self.assertEqual(history.reason, '誤登録のため削除')
        self.assertIn('削除:', history.change_summary)
        self.assertEqual(int(history.before_data['production_qty']), 5)
        self.assertEqual(history.after_data, {})
        mock_recalculate.assert_called_once()
