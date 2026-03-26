from datetime import date

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory

from masters.models import Calendar, Line, Process, Product
from production.models_brake_line_record import BrakeLineRecord
from production.models_line_backlog import LineBacklog
from production.models_record_inquiry_setting import ProductionRecordInquirySetting
from production.views_brake_line import (
    BrakeLinePlanView,
    BrakeLineRecordView,
    BrakeLineSessionDetailView,
)


class BrakeLineSequenceNoRuleTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.plan_date = date(2026, 3, 26)
        self.laser_date = date(2026, 3, 25)

        self.calendar = Calendar.objects.create(
            calendar_code='daiso',
            calendar_name='ダイソー',
        )
        self.laser_line = Line.objects.create(
            line_code='L-LASER-SEQ',
            line_name='レーザ試験ライン',
            calendar=self.calendar,
        )
        self.brake_line = Line.objects.create(
            line_code='L-BRAKE-SEQ',
            line_name='ブレーキ試験ライン',
            calendar=self.calendar,
        )
        self.laser_process = Process.objects.create(
            process_code='P-LASER-SEQ',
            process_name='レーザ工程',
            line=self.laser_line,
        )
        self.brake_process = Process.objects.create(
            process_code='P-BRAKE-SEQ',
            process_name='ブレーキ工程',
            line=self.brake_line,
        )
        self.laser_product = Product.objects.create(
            product_code='TEST-SEQ',
            product_name='レーザ品',
        )
        self.brake_product = Product.objects.create(
            product_code='TEST-SEQB',
            product_name='ブレーキ品',
        )

        ProductionRecordInquirySetting.objects.create(
            tab_key=ProductionRecordInquirySetting.TAB_LASER,
            target_line_codes=[self.laser_line.line_code],
        )
        ProductionRecordInquirySetting.objects.create(
            tab_key=ProductionRecordInquirySetting.TAB_BRAKE,
            target_line_codes=[self.brake_line.line_code],
        )

    def test_plan_view_reads_actual_qty_from_seq0(self):
        LineBacklog.objects.create(
            plan_date=self.laser_date,
            process=self.laser_process,
            product=self.laser_product,
            line=self.laser_line,
            sequence_no=0,
            actual_qty=12,
        )
        seq1_backlog = LineBacklog.objects.create(
            plan_date=self.plan_date,
            process=self.brake_process,
            product=self.brake_product,
            line=self.brake_line,
            sequence_no=1,
            plan_qty=8,
            actual_qty=99,
        )
        LineBacklog.objects.create(
            plan_date=self.plan_date,
            process=self.brake_process,
            product=self.brake_product,
            line=self.brake_line,
            sequence_no=0,
            actual_qty=5,
        )

        view = BrakeLinePlanView.as_view()
        request = self.factory.get('/api/production/brake-line-plan/', {'date': self.plan_date.isoformat()})
        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = next(i for i in response.data['items'] if i['product_code'] == self.brake_product.product_code)
        self.assertEqual(item['plan_qty'], 8)
        self.assertEqual(item['actual_qty'], 5)
        self.assertEqual(item['backlog_id'], seq1_backlog.id)
        self.assertEqual(item['sequence_no'], 1)

    def test_record_save_adds_actual_qty_to_seq0(self):
        seq1_backlog = LineBacklog.objects.create(
            plan_date=self.plan_date,
            process=self.brake_process,
            product=self.brake_product,
            line=self.brake_line,
            sequence_no=1,
            plan_qty=10,
            actual_qty=0,
        )

        view = BrakeLineRecordView.as_view()
        request = self.factory.post(
            '/api/production/brake-line-record/',
            {
                'line_id': self.brake_line.id,
                'process_id': self.brake_process.id,
                'product_id': self.brake_product.id,
                'product_code': self.brake_product.product_code,
                'plan_date': self.plan_date.isoformat(),
                'operator': 'tester',
                'operator_action': BrakeLineRecord.OPERATOR_ACTION_END,
                'qty': 4,
                'sequence_no': 1,
            },
            format='json',
        )
        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        record = BrakeLineRecord.objects.get(id=response.data['id'])
        seq0_backlog = LineBacklog.objects.get(
            plan_date=self.plan_date,
            process=self.brake_process,
            product=self.brake_product,
            line=self.brake_line,
            sequence_no=0,
        )
        seq1_backlog.refresh_from_db()

        self.assertEqual(record.sequence_no, 1)
        self.assertEqual(seq0_backlog.actual_qty, 4)
        self.assertEqual(seq1_backlog.actual_qty, 0)
        self.assertEqual(response.data['backlog']['backlog_id'], seq0_backlog.id)
        self.assertEqual(response.data['backlog']['actual_qty'], 4)

    def test_session_patch_updates_seq0_actual_qty(self):
        seq0_backlog = LineBacklog.objects.create(
            plan_date=self.plan_date,
            process=self.brake_process,
            product=self.brake_product,
            line=self.brake_line,
            sequence_no=0,
            actual_qty=10,
        )
        seq1_backlog = LineBacklog.objects.create(
            plan_date=self.plan_date,
            process=self.brake_process,
            product=self.brake_product,
            line=self.brake_line,
            sequence_no=1,
            plan_qty=10,
            actual_qty=0,
        )
        end_record = BrakeLineRecord.objects.create(
            plan_date=self.plan_date,
            line=self.brake_line,
            process=self.brake_process,
            product=self.brake_product,
            product_code=self.brake_product.product_code,
            operator='tester',
            operator_action=BrakeLineRecord.OPERATOR_ACTION_END,
            qty=10,
            sequence_no=1,
        )

        view = BrakeLineSessionDetailView.as_view()
        request = self.factory.patch(
            f'/api/production/brake-line-sessions/{end_record.id}/',
            {
                'end_record_id': end_record.id,
                'production_qty': 7,
            },
            format='json',
        )
        response = view(request, session_id=end_record.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        end_record.refresh_from_db()
        seq0_backlog.refresh_from_db()
        seq1_backlog.refresh_from_db()

        self.assertEqual(end_record.qty, 7)
        self.assertEqual(seq0_backlog.actual_qty, 7)
        self.assertEqual(seq1_backlog.actual_qty, 0)
