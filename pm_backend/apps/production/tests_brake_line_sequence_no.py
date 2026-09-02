from datetime import date

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory

from masters.models import Calendar, Equipment, Line, Process, Product
from production.models_brake_line_record import BrakeLineRecord
from production.models_line_backlog import LineBacklog
from production.models_process_realtime import ProcessRealtimeRecord
from production.models_process_work_session import ProcessWorkSession
from production.models_process_work_session_equipment import ProcessWorkSessionEquipment
from production.models_record_inquiry_setting import ProductionRecordInquirySetting
from production.views_brake_line import (
    BrakeLinePlanView,
    BrakeLineRecordView,
    BrakeLineSessionDetailView,
)
from production.views_spot_line import SpotLineRecordView


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


class BrakeSpotDualWriteTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.plan_date = date(2026, 3, 26)

        self.calendar = Calendar.objects.create(
            calendar_code='daiso',
            calendar_name='ダイソー',
        )
        self.brake_line = Line.objects.create(
            line_code='L-BRAKE-DUAL',
            line_name='ブレーキ二重書込ライン',
            calendar=self.calendar,
        )
        self.spot_line = Line.objects.create(
            line_code='L-SPOT-DUAL',
            line_name='スポット二重書込ライン',
            calendar=self.calendar,
        )
        self.brake_process = Process.objects.create(
            process_code='P-BRAKE-DUAL',
            process_name='ブレーキ工程',
            line=self.brake_line,
        )
        self.spot_process = Process.objects.create(
            process_code='P-SPOT-DUAL',
            process_name='スポット工程',
            line=self.spot_line,
        )
        self.product = Product.objects.create(
            product_code='TEST-DUAL',
            product_name='二重書込テスト品',
        )
        self.other_product = Product.objects.create(
            product_code='TEST-DUAL-2',
            product_name='二重書込テスト品2',
        )
        self.brake_equipment = Equipment.objects.create(
            equipment_code='EQ-BRAKE-DUAL',
            equipment_name='ブレーキ設備',
            line=self.brake_line,
            process=self.brake_process,
        )
        self.spot_equipment_1 = Equipment.objects.create(
            equipment_code='EQ-SPOT-DUAL-1',
            equipment_name='スポット設備1',
            line=self.spot_line,
            process=self.spot_process,
        )
        self.spot_equipment_2 = Equipment.objects.create(
            equipment_code='EQ-SPOT-DUAL-2',
            equipment_name='スポット設備2',
            line=self.spot_line,
            process=self.spot_process,
        )

        ProductionRecordInquirySetting.objects.create(
            tab_key=ProductionRecordInquirySetting.TAB_SPOT,
            target_line_codes=[self.spot_line.line_code],
        )

    def test_brake_record_post_also_writes_process_tables(self):
        view = BrakeLineRecordView.as_view()
        request = self.factory.post(
            '/api/production/brake-line-record/',
            {
                'line_id': self.brake_line.id,
                'process_id': self.brake_process.id,
                'product_id': self.product.id,
                'product_code': self.product.product_code,
                'plan_date': self.plan_date.isoformat(),
                'operator': 'tester',
                'operator_action': BrakeLineRecord.OPERATOR_ACTION_START,
                'qty': 0,
                'equipment_id': self.brake_equipment.id,
            },
            format='json',
        )
        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            ProcessRealtimeRecord.objects.filter(
                process=self.brake_process,
                product=self.product,
                record_type='OPERATOR_ACTION',
                event_data__source='BRAKE_LINE_RECORD',
                event_data__action='START',
            ).count(),
            1,
        )
        self.assertEqual(
            ProcessWorkSession.objects.filter(
                process=self.brake_process,
                product=self.product,
                plan_date=self.plan_date,
                status='OPEN',
                session_type='WORK',
            ).count(),
            1,
        )
        session = ProcessWorkSession.objects.get(
            process=self.brake_process,
            product=self.product,
            plan_date=self.plan_date,
            status='OPEN',
            session_type='WORK',
        )
        self.assertEqual(
            ProcessWorkSessionEquipment.objects.filter(
                session=session,
                role=ProcessWorkSessionEquipment.ROLE_PRIMARY,
            ).count(),
            1,
        )

    def test_brake_record_rejects_start_when_same_equipment_has_other_open_product(self):
        BrakeLineRecord.objects.create(
            plan_date=self.plan_date,
            line=self.brake_line,
            process=self.brake_process,
            product=self.product,
            product_code=self.product.product_code,
            equipment=self.brake_equipment,
            operator='tester',
            operator_action=BrakeLineRecord.OPERATOR_ACTION_START,
            qty=0,
        )

        request = self.factory.post(
            '/api/production/brake-line-record/',
            {
                'line_id': self.brake_line.id,
                'process_id': self.brake_process.id,
                'product_id': self.other_product.id,
                'product_code': self.other_product.product_code,
                'plan_date': self.plan_date.isoformat(),
                'operator': 'tester',
                'operator_action': BrakeLineRecord.OPERATOR_ACTION_START,
                'qty': 0,
                'equipment_id': self.brake_equipment.id,
            },
            format='json',
        )
        response = BrakeLineRecordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('未終了', response.data['detail'])
        self.assertEqual(
            BrakeLineRecord.objects.filter(
                equipment=self.brake_equipment,
                operator_action=BrakeLineRecord.OPERATOR_ACTION_START,
            ).count(),
            1,
        )

    def test_spot_record_skip_qty_update_secondary_equipment_does_not_create_duplicate_session(self):
        # 1台目（セッション同期あり）
        first_request = self.factory.post(
            '/api/production/spot-line-record/',
            {
                'line_id': self.spot_line.id,
                'process_id': self.spot_process.id,
                'product_id': self.product.id,
                'product_code': self.product.product_code,
                'plan_date': self.plan_date.isoformat(),
                'operator': 'tester',
                'operator_action': BrakeLineRecord.OPERATOR_ACTION_START,
                'qty': 0,
                'skip_qty_update': False,
                'equipment_id': self.spot_equipment_1.id,
            },
            format='json',
        )
        first_response = SpotLineRecordView.as_view()(first_request)
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        # 2台目（セッション同期なし、生ログは保存）
        second_request = self.factory.post(
            '/api/production/spot-line-record/',
            {
                'line_id': self.spot_line.id,
                'process_id': self.spot_process.id,
                'product_id': self.product.id,
                'product_code': self.product.product_code,
                'plan_date': self.plan_date.isoformat(),
                'operator': 'tester',
                'operator_action': BrakeLineRecord.OPERATOR_ACTION_START,
                'qty': 0,
                'skip_qty_update': True,
                'equipment_id': self.spot_equipment_2.id,
            },
            format='json',
        )
        second_response = SpotLineRecordView.as_view()(second_request)
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(
            ProcessRealtimeRecord.objects.filter(
                process=self.spot_process,
                product=self.product,
                record_type='OPERATOR_ACTION',
                event_data__source='SPOT_LINE_RECORD',
                event_data__action='START',
            ).count(),
            2,
        )
        # セッションは1件のみ（2台目は skip_qty_update=true で同期対象外）
        self.assertEqual(
            ProcessWorkSession.objects.filter(
                process=self.spot_process,
                product=self.product,
                plan_date=self.plan_date,
                session_type='WORK',
            ).count(),
            1,
        )
        session = ProcessWorkSession.objects.get(
            process=self.spot_process,
            product=self.product,
            plan_date=self.plan_date,
            session_type='WORK',
        )
        self.assertEqual(
            ProcessWorkSessionEquipment.objects.filter(
                session=session,
                role=ProcessWorkSessionEquipment.ROLE_PRIMARY,
            ).count(),
            1,
        )
        self.assertEqual(
            ProcessWorkSessionEquipment.objects.filter(
                session=session,
                role=ProcessWorkSessionEquipment.ROLE_SUB,
            ).count(),
            1,
        )

    def test_spot_record_rejects_start_when_same_equipment_has_other_open_product(self):
        BrakeLineRecord.objects.create(
            plan_date=self.plan_date,
            line=self.spot_line,
            process=self.spot_process,
            product=self.product,
            product_code=self.product.product_code,
            equipment=self.spot_equipment_1,
            operator='tester',
            operator_action=BrakeLineRecord.OPERATOR_ACTION_PAUSE,
            qty=0,
        )

        request = self.factory.post(
            '/api/production/spot-line-record/',
            {
                'line_id': self.spot_line.id,
                'process_id': self.spot_process.id,
                'product_id': self.other_product.id,
                'product_code': self.other_product.product_code,
                'plan_date': self.plan_date.isoformat(),
                'operator': 'tester',
                'operator_action': BrakeLineRecord.OPERATOR_ACTION_START,
                'qty': 0,
                'skip_qty_update': False,
                'equipment_id': self.spot_equipment_1.id,
            },
            format='json',
        )
        response = SpotLineRecordView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('未終了', response.data['detail'])
        self.assertEqual(
            BrakeLineRecord.objects.filter(
                equipment=self.spot_equipment_1,
                operator_action=BrakeLineRecord.OPERATOR_ACTION_START,
            ).count(),
            0,
        )

    def test_brake_record_rejects_repeated_end_without_double_counting(self):
        payload = {
            'line_id': self.brake_line.id,
            'process_id': self.brake_process.id,
            'product_id': self.product.id,
            'product_code': self.product.product_code,
            'plan_date': self.plan_date.isoformat(),
            'operator': 'tester',
            'operator_action': BrakeLineRecord.OPERATOR_ACTION_END,
            'qty': 4,
            'equipment_id': self.brake_equipment.id,
        }
        view = BrakeLineRecordView.as_view()

        first_response = view(self.factory.post('/api/production/brake-line-record/', payload, format='json'))
        second_response = view(self.factory.post('/api/production/brake-line-record/', payload, format='json'))

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(BrakeLineRecord.objects.filter(
            line=self.brake_line,
            process=self.brake_process,
            product=self.product,
            operator_action=BrakeLineRecord.OPERATOR_ACTION_END,
        ).count(), 1)
        backlog = LineBacklog.objects.get(
            plan_date=self.plan_date,
            line=self.brake_line,
            process=self.brake_process,
            product=self.product,
            sequence_no=0,
        )
        self.assertEqual(backlog.actual_qty, 4)

    def test_spot_record_rejects_repeated_end_without_double_counting(self):
        payload = {
            'line_id': self.spot_line.id,
            'process_id': self.spot_process.id,
            'product_id': self.product.id,
            'product_code': self.product.product_code,
            'plan_date': self.plan_date.isoformat(),
            'operator': 'tester',
            'operator_action': BrakeLineRecord.OPERATOR_ACTION_END,
            'qty': 6,
            'equipment_id': self.spot_equipment_1.id,
            'skip_qty_update': False,
        }
        view = SpotLineRecordView.as_view()

        first_response = view(self.factory.post('/api/production/spot-line-record/', payload, format='json'))
        second_response = view(self.factory.post('/api/production/spot-line-record/', payload, format='json'))

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(BrakeLineRecord.objects.filter(
            line=self.spot_line,
            process=self.spot_process,
            product=self.product,
            operator_action=BrakeLineRecord.OPERATOR_ACTION_END,
        ).count(), 1)
        backlog = LineBacklog.objects.get(
            plan_date=self.plan_date,
            line=self.spot_line,
            process=self.spot_process,
            product=self.product,
            sequence_no=0,
        )
        self.assertEqual(backlog.actual_qty, 6)
