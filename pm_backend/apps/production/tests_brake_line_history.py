from datetime import date, datetime

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory

from masters.models import Line, Process, Product
from production.models_brake_line_record import BrakeLineRecord
from production.models_line_backlog import LineBacklog
from production.models_process_work_session_change_history import ProcessWorkSessionChangeHistory
from production.views_brake_line import BrakeLineSessionDetailView


class BrakeLineHistoryTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.line = Line.objects.create(
            line_code='L-BRAKE-HIS',
            line_name='ブレーキ履歴試験ライン',
        )
        self.process = Process.objects.create(
            process_code='4013',
            process_name='ナットスポット',
            line=self.line,
        )
        self.product = Product.objects.create(
            product_code='BRAKE-HIS-01',
            product_name='ブレーキ履歴試験品',
        )

    def test_delete_creates_history(self):
        start_record = BrakeLineRecord.objects.create(
            plan_date=date(2026, 8, 21),
            line=self.line,
            process=self.process,
            product=self.product,
            product_code=self.product.product_code,
            operator='テスト 作業者',
            operator_action=BrakeLineRecord.OPERATOR_ACTION_START,
            recorded_at=datetime(2026, 8, 21, 19, 57),
        )
        end_record = BrakeLineRecord.objects.create(
            plan_date=date(2026, 8, 21),
            line=self.line,
            process=self.process,
            product=self.product,
            product_code=self.product.product_code,
            operator='テスト 作業者',
            operator_action=BrakeLineRecord.OPERATOR_ACTION_END,
            qty=90,
            recorded_at=datetime(2026, 8, 21, 20, 46),
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 8, 21),
            line=self.line,
            process=self.process,
            product=self.product,
            sequence_no=0,
            actual_qty=90,
        )

        view = BrakeLineSessionDetailView.as_view()
        request = self.factory.delete(
            f'/api/production/brake-line-sessions/{end_record.id}/',
            {
                'start_record_id': start_record.id,
                'end_record_id': end_record.id,
                'change_reason': '重複終了削除',
            },
            format='json',
        )
        response = view(request, session_id=end_record.id)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(BrakeLineRecord.objects.filter(id=start_record.id).exists())
        self.assertFalse(BrakeLineRecord.objects.filter(id=end_record.id).exists())
        backlog = LineBacklog.objects.get(
            plan_date=date(2026, 8, 21),
            line=self.line,
            process=self.process,
            product=self.product,
            sequence_no=0,
        )
        self.assertEqual(backlog.actual_qty, 0)
        history = ProcessWorkSessionChangeHistory.objects.get(
            session_record_id=end_record.id,
            operation_type='DELETE',
        )
        self.assertEqual(history.reason, '重複終了削除')
        self.assertEqual(history.product_code, self.product.product_code)
