from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import call, patch

from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory

from masters.models import Line, Process, Product, BOM, BOMItem, Routing, RoutingStep, InterruptionReason
from production.models_line_backlog import LineBacklog
from production.models_process_realtime import ProcessRealtimeRecord
from production.models_process_work_session_change_history import ProcessWorkSessionChangeHistory
from production.models_process_work_session import ProcessWorkSession
from production.services.process_realtime_backlog_service import (
    apply_delta_to_inventory_and_progress,
    recalculate_inventory_after_session_change,
)
from production.services.process_realtime_routing_service import (
    get_input_eligible_product_ids,
    is_valid_output_process,
)
from production.views_process_realtime import ProcessRealtimeRecordViewSet
from django.contrib.auth import get_user_model
from rest_framework.test import force_authenticate
from quality.models_scrap import ScrapRecord
from production.services.process_realtime_scrap_service import process_scrap_disposition


class GeneralProcessInterruptionReasonTest(TestCase):
    """一般工程の中断理由コードの検証・保存・正規化を確認する。"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create_user(username='reason-user')
        self.line = Line.objects.create(line_code='REASON-L', line_name='中断理由検証ライン')
        self.process = Process.objects.create(
            process_code='REASON-P', process_name='中断理由検証工程', line=self.line,
        )
        self.product = Product.objects.create(product_code='REASON-01', product_name='中断理由検証品')
        routing = Routing.objects.create(
            product=self.product, routing_code='R-REASON', is_default=True, is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing, step_no=10, process=self.process, line=self.line,
            output_product=self.product,
        )
        InterruptionReason.objects.update_or_create(
            code='3997',
            defaults={
                'line_category': '3', 'category': '9', 'display_name': 'その他',
                'operation': 'PAUSE', 'display_order': 9997, 'is_active': True,
            },
        )
        InterruptionReason.objects.update_or_create(
            code='3998',
            defaults={
                'line_category': '3', 'category': '9', 'display_name': 'その他',
                'operation': 'TEMP_END', 'display_order': 9998, 'is_active': True,
            },
        )

    def payload(self, action, **overrides):
        data = {
            'process_id': self.process.id,
            'product_id': self.product.id,
            'record_type': 'OPERATOR_ACTION',
            'qty': 0,
            'event_data': {'action': action},
        }
        data.update(overrides)
        return data

    def serializer(self, action, **overrides):
        from production.serializers_process_realtime import ProcessRealtimeCreateSerializer
        return ProcessRealtimeCreateSerializer(
            data=self.payload(action, **overrides),
            context={'request': SimpleNamespace(user=self.user)},
        )

    def post(self, action, **overrides):
        request = self.factory.post(
            '/api/process-realtime-records/', self.payload(action, **overrides), format='json',
        )
        force_authenticate(request, user=self.user)
        with patch(
            'production.serializers_process_realtime.resolve_workday_date_for_process',
            return_value=date(2026, 10, 17),
        ):
            return ProcessRealtimeRecordViewSet.as_view({'post': 'create'})(request)

    def test_pause_and_temp_end_require_matching_active_general_reason(self):
        cases = [
            ('PAUSE', {}),
            ('PAUSE', {'interruption_reason_code': None}),
            ('PAUSE', {'interruption_reason_code': '3998'}),
            ('TEMP_END', {'interruption_reason_code': '3997'}),
            ('TEMP_END', {'interruption_reason_code': '9999'}),
        ]
        for action, overrides in cases:
            with self.subTest(action=action, overrides=overrides):
                before = (ProcessRealtimeRecord.objects.count(), LineBacklog.objects.count())
                response = self.post(action, **overrides)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('interruption_reason_code', response.data)
                self.assertEqual(
                    (ProcessRealtimeRecord.objects.count(), LineBacklog.objects.count()), before,
                )

    def test_valid_pause_code_is_saved_only_on_operator_action_parent(self):
        self.assertEqual(self.post('START').status_code, status.HTTP_201_CREATED)
        response = self.post('PAUSE', interruption_reason_code='3997')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        parent = ProcessRealtimeRecord.objects.get(pk=response.data['id'])
        child = ProcessRealtimeRecord.objects.get(
            record_type='PRODUCTION', event_data__operator_action_record_id=parent.id,
        )
        self.assertEqual(response.data['interruption_reason_code'], '3997')
        self.assertEqual(parent.interruption_reason_code, '3997')
        self.assertEqual(child.interruption_reason_code, '')

    def test_non_target_actions_and_record_types_normalize_reason_to_blank(self):
        for action in ('START', 'RESUME', 'END', 'CANCEL'):
            with self.subTest(action=action):
                overrides = {'interruption_reason_code': '3997'}
                if action == 'END':
                    overrides['production_qty'] = 1
                serializer = self.serializer(action, **overrides)
                self.assertTrue(serializer.is_valid(), serializer.errors)
                self.assertEqual(serializer.validated_data['interruption_reason_code'], '')

        from production.serializers_process_realtime import ProcessRealtimeCreateSerializer
        serializer = ProcessRealtimeCreateSerializer(
            data={
                'process_id': self.process.id,
                'product_id': self.product.id,
                'record_type': 'PRODUCTION',
                'qty': 1,
                'interruption_reason_code': None,
            },
            context={'request': SimpleNamespace(user=self.user)},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['interruption_reason_code'], '')


class ScrapLoginIdTest(TestCase):
    """仕損の担当者列と既存イベント情報の分離を検証する。"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create_user(username='000175', last_name='記入', first_name='太郎')
        self.reporter = get_user_model().objects.create_user(username='000176')
        self.cause = get_user_model().objects.create_user(username='000177')
        self.process = Process.objects.create(process_code='LOGIN-SCRAP', process_name='仕損列検証')
        self.product = Product.objects.create(product_code='LOGIN-SCRAP', product_name='仕損列検証品')

    def post_scrap(self, **overrides):
        payload = {
            'process_id': self.process.id, 'product_id': self.product.id,
            'record_type': 'SCRAP', 'qty': 1, 'operator_name': '記入 太郎',
            'reporter_login_id': self.reporter.username, 'cause_login_id': None,
            'operator_login_id': '偽装',
            'event_data': {'reason': 'RUST', 'operator': {'login_id': '偽装'},
                           'cause_person': None, 'reporter': {'login_id': '偽装'},
                           'is_production_recorded': False},
        }
        payload.update(overrides)
        request = self.factory.post('/api/process-realtime-records/', payload, format='json')
        force_authenticate(request, user=self.user)
        with patch('production.serializers_process_realtime.build_scrap_multiplier_details', return_value=[]), \
             patch('production.serializers_process_realtime.build_scrap_multiplier_map', return_value={}), \
             patch('production.serializers_process_realtime.update_scrap_to_backlog'):
            return ProcessRealtimeRecordViewSet.as_view({'post': 'create'})(request)

    def test_general_scrap_columns_and_response(self):
        response = self.post_scrap(cause_login_id=self.cause.username)
        self.assertEqual(response.status_code, 201)
        scrap = ScrapRecord.objects.get(process_record_id=response.data['id'])
        self.assertEqual(scrap.operator_login_id, self.user.username)
        self.assertEqual(scrap.cause_login_id, self.cause.username)
        self.assertEqual(scrap.reporter_login_id, self.reporter.username)
        self.assertEqual(response.data['scrap_operator_login_id'], self.user.username)
        self.assertEqual(response.data['scrap_cause_login_id'], self.cause.username)
        self.assertEqual(response.data['scrap_reporter_login_id'], self.reporter.username)
        self.assertEqual(response.data['event_data'], {'reason': 'RUST', 'is_production_recorded': False})

    def test_empty_cause_is_null(self):
        for cause in (None, ''):
            with self.subTest(cause=cause):
                response = self.post_scrap(cause_login_id=cause)
                self.assertEqual(response.status_code, 201)
                self.assertIsNone(response.data['scrap_cause_login_id'])

    def test_column_save_keeps_scrap_backlog_and_stock_effects(self):
        from production.models_production import StockAllocation
        from production.serializers_process_realtime import ProcessRealtimeCreateSerializer
        line = Line.objects.create(line_code='LOGIN-SCRAP', line_name='列保存在庫検証')
        self.process.line = line
        self.process.save(update_fields=['line'])
        stock = StockAllocation.objects.create(product=self.product, location='DEFAULT', current_stock=10, min_stock_qty=0)
        serializer = ProcessRealtimeCreateSerializer(data={
            'process_id': self.process.id, 'product_id': self.product.id,
            'record_type': 'SCRAP', 'qty': 2,
            'reporter_login_id': self.reporter.username,
            'event_data': {'reason': 'RUST', 'relation_type': 'OUTPUT_PRODUCT', 'is_production_recorded': False},
        }, context={'request': SimpleNamespace(user=self.user)})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        record = serializer.save()
        stock.refresh_from_db()
        self.assertEqual(stock.current_stock, Decimal('8'))
        backlog = LineBacklog.objects.get(line=line, process=self.process, product=self.product, sequence_no=0)
        self.assertEqual(backlog.scrap_qty, 2)
        self.assertEqual(backlog.actual_qty, 0)
        self.assertEqual(backlog.scrap_adjust_qty, 0)
        self.assertEqual(record.scrap_detail.operator_login_id, self.user.username)

    def test_invalid_users_or_missing_reporter_are_rejected_before_save(self):
        for overrides in ({'reporter_login_id': None}, {'reporter_login_id': ''},
                          {'reporter_login_id': 'unknown'}, {'cause_login_id': 'unknown'},
                          {'scrap_input_source': 'OTHER'}):
            with self.subTest(overrides=overrides):
                response = self.post_scrap(**overrides)
                self.assertEqual(response.status_code, 400)
                self.assertFalse(ScrapRecord.objects.exists())
        # 未指定も400。Noneと区別してserializer入力から削除する。
        from production.serializers_process_realtime import ProcessRealtimeCreateSerializer
        serializer = ProcessRealtimeCreateSerializer(data={
            'process_id': self.process.id, 'product_id': self.product.id, 'record_type': 'SCRAP',
        }, context={'request': SimpleNamespace(user=self.user)})
        self.assertFalse(serializer.is_valid())
        self.assertIn('reporter_login_id', serializer.errors)

    def test_brake_and_spot_ignore_client_people(self):
        for source in ('BRAKE', 'SPOT'):
            with self.subTest(source=source):
                response = self.post_scrap(scrap_input_source=source, cause_login_id={'invalid': True}, reporter_login_id='unknown')
                self.assertEqual(response.status_code, 201)
                for key in ('scrap_operator_login_id', 'scrap_cause_login_id', 'scrap_reporter_login_id'):
                    self.assertEqual(response.data[key], self.user.username)

    def test_return_records_actor_only(self):
        response = self.post_scrap()
        record = ProcessRealtimeRecord.objects.get(pk=response.data['id'])
        with patch('production.services.process_realtime_scrap_service._build_return_details'), \
             patch('production.services.process_realtime_scrap_service._restore_parent_backlog'), \
             patch('production.services.process_realtime_scrap_service._restore_child_adjustments'):
            process_scrap_disposition(record, 'RETURN', qty_input=1, decided_by=self.user.username)
        returned = ScrapRecord.objects.get(event_type='RETURN')
        self.assertEqual(returned.operator_login_id, self.user.username)
        self.assertIsNone(returned.cause_login_id)
        self.assertIsNone(returned.reporter_login_id)

    def test_anonymous_scrap_and_return_are_rejected(self):
        from django.contrib.auth.models import AnonymousUser
        from production.serializers_process_realtime import ProcessRealtimeCreateSerializer
        from production.services.process_realtime_scrap_service import ScrapServiceError
        serializer = ProcessRealtimeCreateSerializer(data={
            'process_id': self.process.id, 'product_id': self.product.id,
            'record_type': 'SCRAP', 'reporter_login_id': self.reporter.username,
        }, context={'request': SimpleNamespace(user=AnonymousUser())})
        self.assertFalse(serializer.is_valid())
        self.assertIn('operator_login_id', serializer.errors)
        response = self.post_scrap()
        record = ProcessRealtimeRecord.objects.get(pk=response.data['id'])
        with self.assertRaises(ScrapServiceError) as error:
            process_scrap_disposition(record, 'RETURN', qty_input=1)
        self.assertEqual(error.exception.status_code, 400)
        self.assertFalse(ScrapRecord.objects.filter(event_type='RETURN').exists())



class ProcessRealtimeOperatorLoginIdTest(TestCase):
    """一般の工程実績の作業者ログインID列（operator_login_id）を検証する。"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create_user(username='000175', last_name='記入', first_name='太郎')
        self.line = Line.objects.create(line_code='LID-L', line_name='ログインID検証ライン')
        self.process = Process.objects.create(process_code='LID-P', process_name='ログインID検証工程', line=self.line)
        self.product = Product.objects.create(product_code='LID-PROD', product_name='ログインID検証品')
        routing = Routing.objects.create(product=self.product, routing_code='R-LID', is_default=True, is_active=True)
        RoutingStep.objects.create(
            routing=routing, step_no=10, process=self.process, line=self.line, output_product=self.product,
        )
        self.reason_pause = InterruptionReason.objects.create(
            code='9101', line_category='3', category='1', display_name='テスト用設備トラブル',
            operation='PAUSE', display_order=10, is_active=True,
        )
        # 連産親（子へ展開される）
        self.parent = Product.objects.create(product_code='LID-SET', product_name='連産親', is_virtual_set=True)
        self.child = Product.objects.create(product_code='LID-CHILD', product_name='連産子')
        bom = BOM.objects.create(
            parent_product=self.parent, version='v1', valid_from=date(2026, 1, 1),
            is_active=True, is_coproduct=True,
        )
        BOMItem.objects.create(bom=bom, child_product=self.child, quantity=Decimal('1'))

    def post(self, payload, user='default'):
        request = self.factory.post('/api/process-realtime-records/', payload, format='json')
        if user == 'default':
            user = self.user
        if user is not None:
            force_authenticate(request, user=user)
        with patch(
            'production.serializers_process_realtime.resolve_workday_date_for_process',
            return_value=date(2026, 3, 5),
        ):
            return ProcessRealtimeRecordViewSet.as_view({'post': 'create'})(request)

    def base(self, record_type, **extra):
        payload = {
            'process_id': self.process.id, 'product_id': self.product.id,
            'record_type': record_type, 'qty': 3, 'operator_name': '記入 太郎',
        }
        payload.update(extra)
        return payload

    def test_parent_rows_store_login_user_and_ignore_client_values(self):
        cases = [
            self.base('PRODUCTION'),
            self.base('OPERATOR_ACTION', qty=0, event_data={'action': 'START'}),
            {'process_id': self.process.id, 'record_type': 'EQUIPMENT_STATE', 'equipment_state': 'RUNNING',
             'qty': 0, 'operator_name': '記入 太郎'},
        ]
        for payload in cases:
            with self.subTest(record_type=payload['record_type']):
                payload = dict(payload)
                payload['operator_login_id'] = '偽装'
                payload['event_data'] = dict(payload.get('event_data') or {},
                                             operator_login_id='偽装', operator_user_id='偽装')
                response = self.post(payload)
                self.assertEqual(response.status_code, 201, response.data)
                self.assertEqual(response.data['operator_login_id'], '000175')
                record = ProcessRealtimeRecord.objects.get(pk=response.data['id'])
                self.assertEqual(record.operator_login_id, '000175')
                self.assertEqual(record.operator_name, '記入 太郎')

    def test_equipment_state_without_operator_name_still_uses_login_user(self):
        response = self.post({'process_id': self.process.id, 'record_type': 'EQUIPMENT_STATE',
                              'equipment_state': 'RUNNING', 'qty': 0})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['operator_login_id'], '000175')

    def test_pause_and_end_production_rows_and_coproduct_children_share_login_id(self):
        for action in ('PAUSE', 'END'):
            with self.subTest(action=action):
                ProcessRealtimeRecord.objects.all().delete()
                ProcessWorkSession.objects.all().delete()
                start = self.post(self.base('OPERATOR_ACTION', product_id=self.parent.id, qty=0,
                                            event_data={'action': 'START'}))
                self.assertEqual(start.status_code, 201, start.data)
                payload = self.base('OPERATOR_ACTION', product_id=self.parent.id, qty=4,
                                    event_data={'action': action})
                if action == 'PAUSE':
                    payload['interruption_reason_code'] = self.reason_pause.code
                if action == 'END':
                    payload['production_qty'] = 4
                response = self.post(payload)
                self.assertEqual(response.status_code, 201, response.data)
                production = ProcessRealtimeRecord.objects.filter(record_type='PRODUCTION')
                self.assertEqual(production.count(), 2)  # 親 + 連産子
                self.assertEqual({r.product_code for r in production}, {'LID-SET', 'LID-CHILD'})
                self.assertEqual({r.operator_login_id for r in production}, {'000175'})

    def test_production_coproduct_child_shares_login_id(self):
        response = self.post(self.base('PRODUCTION', product_id=self.parent.id))
        self.assertEqual(response.status_code, 201, response.data)
        rows = ProcessRealtimeRecord.objects.filter(record_type='PRODUCTION')
        self.assertEqual(rows.count(), 2)
        self.assertEqual({r.operator_login_id for r in rows}, {'000175'})

    # ---- 2人1設備（B治具）: 印 + operator_user_id(auth_user.id) から username を引く約束 ----
    def two_person(self, worker, **kw):
        data = {'two_person_same_equipment': True, 'operator_user_id': str(worker.id)}
        data.update(kw)
        return data

    def make_worker(self, username='000999', **extra):
        return get_user_model().objects.create_user(username=username, **extra)

    def test_two_person_b_jig_uses_worker_username_and_a_jig_uses_login_user(self):
        admin = get_user_model().objects.create_user(username='admin', is_staff=True)
        worker = self.make_worker('000175x', last_name='王')
        for jig, target, expected in (('A', admin, 'admin'), ('B', worker, '000175x')):
            with self.subTest(jig=jig):
                response = self.post(self.base('PRODUCTION', event_data=self.two_person(target)), user=admin)
                self.assertEqual(response.status_code, 201, response.data)
                self.assertEqual(response.data['operator_login_id'], expected)
                record = ProcessRealtimeRecord.objects.get(pk=response.data['id'])
                self.assertEqual(record.operator_login_id, expected)
                # event_data の operator_user_id は消さずに保存
                self.assertEqual(record.event_data['operator_user_id'], str(target.id))

    def test_two_person_all_parent_record_types_and_int_id(self):
        worker = self.make_worker()
        cases = [
            self.base('PRODUCTION', event_data=self.two_person(worker)),
            self.base('OPERATOR_ACTION', qty=0, event_data=self.two_person(worker, action='START')),
            {'process_id': self.process.id, 'record_type': 'EQUIPMENT_STATE', 'equipment_state': 'RUNNING',
             'qty': 0, 'event_data': self.two_person(worker)},
            self.base('PRODUCTION', event_data={'two_person_same_equipment': True, 'operator_user_id': worker.id}),
        ]
        for payload in cases:
            with self.subTest(record_type=payload['record_type']):
                response = self.post(payload)
                self.assertEqual(response.status_code, 201, response.data)
                self.assertEqual(response.data['operator_login_id'], '000999')

    def test_two_person_b_jig_pause_end_and_coproduct_rows_share_worker(self):
        worker = self.make_worker()
        for action in ('PAUSE', 'END'):
            with self.subTest(action=action):
                ProcessRealtimeRecord.objects.all().delete()
                ProcessWorkSession.objects.all().delete()
                start = self.post(self.base('OPERATOR_ACTION', product_id=self.parent.id, qty=0,
                                            event_data=self.two_person(worker, action='START')))
                self.assertEqual(start.status_code, 201, start.data)
                payload = self.base('OPERATOR_ACTION', product_id=self.parent.id, qty=4,
                                    event_data=self.two_person(worker, action=action))
                if action == 'PAUSE':
                    payload['interruption_reason_code'] = self.reason_pause.code
                if action == 'END':
                    payload['production_qty'] = 4
                response = self.post(payload)
                self.assertEqual(response.status_code, 201, response.data)
                self.assertEqual(response.data['operator_login_id'], '000999')
                production = ProcessRealtimeRecord.objects.filter(record_type='PRODUCTION')
                self.assertEqual(production.count(), 2)  # 親 + 連産子
                self.assertEqual({r.operator_login_id for r in production}, {'000999'})

    def test_two_person_coproduct_child_shares_worker_on_production(self):
        worker = self.make_worker()
        response = self.post(self.base('PRODUCTION', product_id=self.parent.id, event_data=self.two_person(worker)))
        self.assertEqual(response.status_code, 201, response.data)
        rows = ProcessRealtimeRecord.objects.filter(record_type='PRODUCTION')
        self.assertEqual(rows.count(), 2)
        self.assertEqual({r.operator_login_id for r in rows}, {'000999'})

    def test_two_person_invalid_user_id_is_400_and_creates_nothing(self):
        inactive = self.make_worker('000888', is_active=False)
        bad_values = {
            'missing': {'two_person_same_equipment': True},
            'empty': {'two_person_same_equipment': True, 'operator_user_id': ''},
            'not_number': {'two_person_same_equipment': True, 'operator_user_id': 'abc'},
            'not_exist': {'two_person_same_equipment': True, 'operator_user_id': '99999999'},
            'inactive': {'two_person_same_equipment': True, 'operator_user_id': str(inactive.id)},
        }
        backlog_before = LineBacklog.objects.count()
        for name, event_data in bad_values.items():
            for payload in (
                self.base('PRODUCTION', product_id=self.parent.id, event_data=event_data),
                self.base('OPERATOR_ACTION', qty=0, event_data=dict(event_data, action='START')),
                {'process_id': self.process.id, 'record_type': 'EQUIPMENT_STATE', 'equipment_state': 'RUNNING',
                 'qty': 0, 'event_data': event_data},
            ):
                with self.subTest(case=name, record_type=payload['record_type']):
                    response = self.post(payload)
                    self.assertEqual(response.status_code, 400, getattr(response, 'data', None))
                    self.assertIn('event_data', response.data)
        self.assertEqual(ProcessRealtimeRecord.objects.count(), 0)
        self.assertEqual(ProcessWorkSession.objects.count(), 0)
        self.assertEqual(LineBacklog.objects.count(), backlog_before)

    def test_without_flag_operator_user_id_is_ignored(self):
        other = self.make_worker()
        for flag in (None, False):
            with self.subTest(flag=flag):
                event_data = {'operator_user_id': str(other.id)}
                if flag is not None:
                    event_data['two_person_same_equipment'] = flag
                response = self.post(self.base('PRODUCTION', event_data=event_data))
                self.assertEqual(response.status_code, 201, response.data)
                self.assertEqual(response.data['operator_login_id'], '000175')

    def test_scrap_ignores_two_person_flag_and_stays_null(self):
        other = self.make_worker()
        with patch('production.serializers_process_realtime.build_scrap_multiplier_details', return_value=[]), \
             patch('production.serializers_process_realtime.build_scrap_multiplier_map', return_value={}), \
             patch('production.serializers_process_realtime.update_scrap_to_backlog'):
            response = self.post(self.base('SCRAP', reporter_login_id=self.user.username,
                                           event_data=dict(self.two_person(other), reason='RUST',
                                                           is_production_recorded=False)))
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(response.data['operator_login_id'])

    def test_scrap_row_is_null(self):
        with patch('production.serializers_process_realtime.build_scrap_multiplier_details', return_value=[]), \
             patch('production.serializers_process_realtime.build_scrap_multiplier_map', return_value={}), \
             patch('production.serializers_process_realtime.update_scrap_to_backlog'):
            response = self.post(self.base('SCRAP', reporter_login_id=self.user.username,
                                           event_data={'reason': 'RUST', 'is_production_recorded': False}))
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(response.data['operator_login_id'])
        self.assertEqual(ScrapRecord.objects.get(process_record_id=response.data['id']).operator_login_id, '000175')

    def test_purchase_works_without_request_context_and_is_null(self):
        from production.serializers_process_realtime import ProcessRealtimeCreateSerializer
        from production.models_process_realtime import PURCHASE_ACTUAL_SOURCES
        purchase_process = Process.objects.create(process_code='LID-PUR', process_name='仕入検証工程', line=self.line)
        serializer = ProcessRealtimeCreateSerializer(data={
            'process_id': purchase_process.id, 'product_id': self.product.id, 'record_type': 'PURCHASE',
            'qty': 2, 'work_date': date(2026, 3, 5),
            'event_data': {'source': PURCHASE_ACTUAL_SOURCES[0], 'line_id': self.line.id},
        })
        with patch('production.serializers_process_realtime.is_valid_output_process', return_value=True):
            self.assertTrue(serializer.is_valid(), serializer.errors)
            record = serializer.save()
        self.assertEqual(record.record_type, 'PURCHASE')
        self.assertIsNone(record.operator_login_id)

    def test_anonymous_requests_are_rejected_for_login_id_record_types(self):
        for payload in (self.base('PRODUCTION'),
                        self.base('OPERATOR_ACTION', qty=0, event_data={'action': 'START'}),
                        {'process_id': self.process.id, 'record_type': 'EQUIPMENT_STATE',
                         'equipment_state': 'RUNNING', 'qty': 0}):
            with self.subTest(record_type=payload['record_type']):
                response = self.post(payload, user=None)
                self.assertEqual(response.status_code, 400)
                self.assertIn('operator_login_id', response.data)
        self.assertFalse(ProcessRealtimeRecord.objects.exists())

    def test_patch_cannot_rewrite_operator_login_id(self):
        response = self.post(self.base('PRODUCTION'))
        record_id = response.data['id']
        request = self.factory.patch(f'/api/process-realtime-records/{record_id}/',
                                     {'operator_login_id': '偽装', 'remarks': '更新'}, format='json')
        force_authenticate(request, user=self.user)
        ProcessRealtimeRecordViewSet.as_view({'patch': 'partial_update'})(request, pk=record_id)
        record = ProcessRealtimeRecord.objects.get(pk=record_id)
        self.assertEqual(record.operator_login_id, '000175')

    def test_backlog_effect_is_unchanged_by_login_id_column(self):
        response = self.post(self.base('PRODUCTION', qty=5))
        self.assertEqual(response.status_code, 201, response.data)
        backlog = LineBacklog.objects.get(line=self.line, process=self.process, product=self.product,
                                          sequence_no=0)
        self.assertEqual(backlog.actual_qty, 5)
        self.assertEqual(backlog.scrap_qty, 0)


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
        # 手動追加・作業者変更で指定する作業者（auth_user）
        self.worker = get_user_model().objects.create_user(
            username='000555', last_name='訂正', first_name='花子',
        )

    def make_dt(self, year, month, day, hour, minute=0):
        value = datetime(year, month, day, hour, minute)
        if settings.USE_TZ:
            return timezone.make_aware(value)
        return value

    def create_output_routing(self, process=None, product=None, routing_code='R-TEST-RT'):
        process = process or self.process
        product = product or self.product
        routing = Routing.objects.create(
            product=product,
            routing_code=routing_code,
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=process,
            line=process.line,
            output_product=product,
        )

    @patch('production.inventory.inventory_calculator.recalculate_inventory_for_line')
    def test_recalculate_helper_uses_plan_date_range(self, mock_recalculate):
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

        session = SimpleNamespace(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product_id=self.product.id,
        )

        recalculate_inventory_after_session_change(session)

        mock_recalculate.assert_called_once_with(
            line_id=self.line.id,
            start_date=date(2026, 3, 5),
            end_date=date(2026, 3, 7),
            include_progress=True,
            line_final_only=False,
            product_ids=[self.product.id],
        )

    @patch('production.inventory.inventory_calculator.recalculate_inventory_for_line')
    def test_recalculate_helper_expands_to_parent_line_with_lt(self, mock_recalculate):
        parent_line = Line.objects.create(
            line_code='LPARENT-RT',
            line_name='親ライン',
        )
        parent_process = Process.objects.create(
            process_code='PPARENT-RT',
            process_name='親工程',
            line=parent_line,
        )
        parent_product = Product.objects.create(
            product_code='PARENT-RT',
            product_name='親品番',
        )
        BOM.objects.create(
            parent_product=parent_product,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
        )
        bom = BOM.objects.get(parent_product=parent_product)
        BOMItem.objects.create(
            bom=bom,
            child_product=self.product,
            quantity=Decimal('1'),
            process=parent_process,
            line=parent_line,
            lead_time_days=2,
        )
        routing = Routing.objects.create(
            product=parent_product,
            routing_code='R-PARENT-RT',
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=parent_process,
            line=parent_line,
            output_product=self.product,
            lead_time_days=2,
        )

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
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 3),
            process=parent_process,
            product=parent_product,
            line=parent_line,
            sequence_no=0,
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 8),
            process=parent_process,
            product=parent_product,
            line=parent_line,
            sequence_no=0,
        )

        session = SimpleNamespace(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product_id=self.product.id,
        )

        recalculate_inventory_after_session_change(session)

        self.assertEqual(mock_recalculate.call_count, 2)
        mock_recalculate.assert_has_calls(
            [
                call(
                    line_id=self.line.id,
                    start_date=date(2026, 3, 5),
                    end_date=date(2026, 3, 7),
                    include_progress=True,
                    line_final_only=False,
                    product_ids=[self.product.id],
                ),
                call(
                    line_id=parent_line.id,
                    start_date=date(2026, 3, 3),
                    end_date=date(2026, 3, 8),
                    include_progress=True,
                    line_final_only=False,
                    product_ids=[parent_product.id],
                ),
            ],
            any_order=True,
        )

    @patch('production.inventory.inventory_calculator.recalculate_inventory_for_line')
    def test_recalculate_helper_uses_bom_item_process_to_select_lt(self, mock_recalculate):
        shared_line = Line.objects.create(
            line_code='LSHARED-RT',
            line_name='共通ライン',
        )
        process_a = Process.objects.create(
            process_code='PSHARED-A',
            process_name='共通工程A',
            line=shared_line,
        )
        process_b = Process.objects.create(
            process_code='PSHARED-B',
            process_name='共通工程B',
            line=shared_line,
        )
        parent_product = Product.objects.create(
            product_code='PARENT-PROC',
            product_name='親品番工程選択',
        )
        bom = BOM.objects.create(
            parent_product=parent_product,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=self.product,
            quantity=Decimal('1'),
            process=process_a,
            line=shared_line,
            lead_time_days=1,
        )
        routing = Routing.objects.create(
            product=parent_product,
            routing_code='R-PARENT-PROC',
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=process_b,
            line=shared_line,
            output_product=self.product,
            lead_time_days=4,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=20,
            process=process_a,
            line=shared_line,
            output_product=self.product,
            lead_time_days=1,
        )

        LineBacklog.objects.create(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product=self.product,
            line=self.line,
            sequence_no=0,
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 4),
            process=process_a,
            product=parent_product,
            line=shared_line,
            sequence_no=0,
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 8),
            process=process_a,
            product=parent_product,
            line=shared_line,
            sequence_no=0,
        )

        session = SimpleNamespace(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product_id=self.product.id,
        )

        recalculate_inventory_after_session_change(session)

        self.assertEqual(mock_recalculate.call_count, 2)
        mock_recalculate.assert_has_calls(
            [
                call(
                    line_id=shared_line.id,
                    start_date=date(2026, 3, 4),
                    end_date=date(2026, 3, 8),
                    include_progress=True,
                    line_final_only=False,
                    product_ids=[parent_product.id],
                ),
            ],
            any_order=True,
        )

    @patch('production.inventory.inventory_calculator.recalculate_inventory_for_line')
    def test_recalculate_helper_uses_coproduct_children_as_recalc_targets(self, mock_recalculate):
        child = Product.objects.create(
            product_code='CHILD-RECALC',
            product_name='連産子再計算',
        )
        parent = Product.objects.create(
            product_code='STYD-RECALC',
            product_name='連産親再計算',
            is_virtual_set=True,
        )
        bom = BOM.objects.create(
            parent_product=parent,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
            is_coproduct=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=child,
            quantity=Decimal('1'),
            process=self.process,
            line=self.line,
        )
        routing = Routing.objects.create(
            product=child,
            routing_code='R-CHILD-RECALC',
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=self.process,
            line=self.line,
            output_product=child,
            lead_time_days=1,
        )

        LineBacklog.objects.create(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product=child,
            line=self.line,
            sequence_no=0,
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 7),
            process=self.process,
            product=child,
            line=self.line,
            sequence_no=0,
        )

        session = SimpleNamespace(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product_id=parent.id,
        )

        recalculate_inventory_after_session_change(session)

        mock_recalculate.assert_called_once_with(
            line_id=self.line.id,
            start_date=date(2026, 3, 5),
            end_date=date(2026, 3, 7),
            include_progress=True,
            line_final_only=False,
            product_ids=[child.id],
        )

    @patch('production.services.process_realtime_backlog_service.recalculate_child_stock_after_record_edit')
    def test_apply_delta_uses_coproduct_child_as_bom_parent(self, mock_recalculate_child_stock):
        parent = Product.objects.create(
            product_code='STYD-DELTA',
            product_name='連産親差分',
            is_virtual_set=True,
        )
        coproduct_child = Product.objects.create(
            product_code='CHILD-DELTA',
            product_name='連産子差分',
        )
        component = Product.objects.create(
            product_code='COMP-DELTA',
            product_name='子部品差分',
        )
        coproduct_bom = BOM.objects.create(
            parent_product=parent,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
            is_coproduct=True,
        )
        BOMItem.objects.create(
            bom=coproduct_bom,
            child_product=coproduct_child,
            quantity=Decimal('2'),
            process=self.process,
            line=self.line,
        )
        child_bom = BOM.objects.create(
            parent_product=coproduct_child,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
            is_coproduct=False,
        )
        BOMItem.objects.create(
            bom=child_bom,
            child_product=component,
            quantity=Decimal('3'),
            process=self.process,
            line=self.line,
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product=coproduct_child,
            line=self.line,
            sequence_no=0,
            stock_qty=0,
            planned_stock_qty=0,
            progress_qty=0,
            planned_progress_qty=0,
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product=component,
            line=self.line,
            sequence_no=0,
            stock_qty=100,
            planned_stock_qty=100,
            actual_shipment_qty=0,
        )

        session = SimpleNamespace(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product_id=parent.id,
        )

        with patch('production.services.process_realtime_backlog_service.get_business_today', return_value=date(2026, 3, 5)):
            apply_delta_to_inventory_and_progress(session, 4)

        coproduct_child_backlog = LineBacklog.objects.get(
            line=self.line,
            process=self.process,
            product=coproduct_child,
            plan_date=date(2026, 3, 5),
            sequence_no=0,
        )
        component_backlog = LineBacklog.objects.get(
            line=self.line,
            process=self.process,
            product=component,
            plan_date=date(2026, 3, 5),
            sequence_no=0,
        )
        self.assertEqual(coproduct_child_backlog.stock_qty, 8)
        self.assertEqual(coproduct_child_backlog.planned_stock_qty, 8)
        self.assertEqual(coproduct_child_backlog.progress_qty, 8)
        self.assertEqual(coproduct_child_backlog.planned_progress_qty, 8)
        self.assertEqual(component_backlog.stock_qty, 76)
        self.assertEqual(component_backlog.planned_stock_qty, 76)
        self.assertEqual(component_backlog.actual_shipment_qty, 24)
        mock_recalculate_child_stock.assert_called_once_with(
            parent_plan_date=date(2026, 3, 5),
            today=date(2026, 3, 5),
            child_product_ids={component.id},
        )

    @patch('production.views_process_realtime.recalculate_inventory_after_session_change')
    @patch('production.views_process_realtime.resolve_workday_date_for_process', return_value=date(2026, 3, 5))
    def test_create_manual_session_triggers_recalculation(self, _mock_plan_date, mock_recalculate):
        self.create_output_routing()
        view = ProcessRealtimeRecordViewSet.as_view({'post': 'sessions'})
        request = self.factory.post(
            '/api/process-realtime/sessions/',
            {
                'process_id': self.process.id,
                'product_code': self.product.product_code,
                'started_at': '2026-03-05T09:00:00',
                'ended_at': '2026-03-05T10:00:00',
                'production_qty': 5,
                'operator_user_id': self.worker.id,
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

    @patch('production.views_process_realtime.recalculate_inventory_after_session_change')
    @patch('production.views_process_realtime.resolve_workday_date_for_process', return_value=date(2026, 3, 5))
    def test_create_manual_session_creates_coproduct_child_records(self, _mock_plan_date, mock_recalculate):
        parent = Product.objects.create(
            product_code='STYD-SET',
            product_name='連産親',
            is_virtual_set=True,
        )
        child = Product.objects.create(
            product_code='CHILD-01',
            product_name='連産子',
        )
        bom = BOM.objects.create(
            parent_product=parent,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
            is_coproduct=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=child,
            quantity=Decimal('2'),
            process=self.process,
            line=self.line,
        )
        self.create_output_routing(product=parent, routing_code='R-COPRODUCT-RT')

        view = ProcessRealtimeRecordViewSet.as_view({'post': 'sessions'})
        request = self.factory.post(
            '/api/process-realtime/sessions/',
            {
                'process_id': self.process.id,
                'product_code': parent.product_code,
                'started_at': '2026-03-05T09:00:00',
                'ended_at': '2026-03-05T10:00:00',
                'production_qty': 5,
                'operator_user_id': self.worker.id,
                'change_reason': '連産補完',
            },
            format='json',
        )

        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = ProcessWorkSession.objects.get(product=parent)
        records = ProcessRealtimeRecord.objects.filter(
            record_type='PRODUCTION',
            event_data__work_session_id=session.id,
        ).order_by('product_code')
        self.assertEqual(records.count(), 2)
        parent_record = records.get(product=parent)
        child_record = records.get(product=child)
        self.assertEqual(parent_record.qty, Decimal('5'))
        self.assertEqual(child_record.qty, Decimal('10'))
        self.assertEqual(child_record.event_data.get('coproduct_parent_record_id'), parent_record.id)
        child_backlog = LineBacklog.objects.get(
            line=self.line,
            process=self.process,
            product=child,
            plan_date=date(2026, 3, 5),
            sequence_no=0,
        )
        self.assertEqual(child_backlog.actual_qty, 10)
        mock_recalculate.assert_called_once()

    def test_coproduct_parent_and_child_are_excluded_from_routing_validation(self):
        parent = Product.objects.create(
            product_code='STYD-ROUTING-SET',
            product_name='連産親',
            is_virtual_set=True,
        )
        child = Product.objects.create(
            product_code='CHILD-ROUTING-EXEMPT',
            product_name='連産子',
        )
        bom = BOM.objects.create(
            parent_product=parent,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
            is_coproduct=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=child,
            quantity=Decimal('1'),
        )

        self.assertTrue(is_valid_output_process(
            self.process,
            child,
            date(2026, 3, 5),
        ))
        self.assertTrue(is_valid_output_process(
            self.process,
            parent,
            date(2026, 3, 5),
        ))
        self.assertEqual(
            get_input_eligible_product_ids(
                self.process,
                [self.product.id, parent.id, child.id],
                date(2026, 3, 5),
            ),
            {parent.id, child.id},
        )

        self.create_output_routing(routing_code='R-ROUTING-ELIGIBLE')
        self.assertEqual(
            get_input_eligible_product_ids(
                self.process,
                [self.product.id, parent.id, child.id],
                date(2026, 3, 5),
            ),
            {self.product.id, parent.id, child.id},
        )

    @patch('production.views_process_realtime.recalculate_inventory_after_session_change')
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

    @patch('production.views_process_realtime.recalculate_inventory_after_session_change')
    def test_session_detail_update_syncs_coproduct_child_record_qty(self, mock_recalculate):
        parent = Product.objects.create(
            product_code='STYD-UPD',
            product_name='連産親更新',
            is_virtual_set=True,
        )
        child = Product.objects.create(
            product_code='CHILD-UPD',
            product_name='連産子更新',
        )
        bom = BOM.objects.create(
            parent_product=parent,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
            is_coproduct=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=child,
            quantity=Decimal('3'),
            process=self.process,
            line=self.line,
        )
        session = ProcessWorkSession.objects.create(
            process=self.process,
            product=parent,
            product_code=parent.product_code,
            product_name=parent.product_name,
            plan_date=date(2026, 3, 5),
            session_no=1,
            session_type='WORK',
            start_action='MANUAL',
            end_action='END',
            started_at=self.make_dt(2026, 3, 5, 9),
            ended_at=self.make_dt(2026, 3, 5, 10),
            status='CLOSED',
            duration_seconds=3600,
            production_qty=2,
        )
        ProcessRealtimeRecord.objects.create(
            process=self.process,
            product=parent,
            product_code=parent.product_code,
            product_name=parent.product_name,
            record_type='PRODUCTION',
            qty=Decimal('2'),
            event_data={'work_session_id': session.id},
        )
        ProcessRealtimeRecord.objects.create(
            process=self.process,
            product=child,
            product_code=child.product_code,
            product_name=child.product_name,
            record_type='PRODUCTION',
            qty=Decimal('6'),
            event_data={'work_session_id': session.id, 'coproduct_parent_record_id': 99999},
        )

        view = ProcessRealtimeRecordViewSet.as_view({'patch': 'session_detail'})
        request = self.factory.patch(
            f'/api/process-realtime/sessions/{session.id}/',
            {
                'production_qty': 4,
                'change_reason': '連産数量訂正',
            },
            format='json',
        )
        response = view(request, session_id=session.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        records = ProcessRealtimeRecord.objects.filter(
            record_type='PRODUCTION',
            event_data__work_session_id=session.id,
        )
        self.assertEqual(records.count(), 2)
        self.assertEqual(records.get(product=parent).qty, Decimal('4'))
        self.assertEqual(records.get(product=child).qty, Decimal('12'))
        mock_recalculate.assert_called_once()

    @patch('production.views_process_realtime.recalculate_inventory_after_session_change')
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
        routing = Routing.objects.create(
            product=self.product,
            routing_code='R-DELETE-VALID',
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=self.process,
            line=self.line,
            output_product=self.product,
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

    @patch('production.views_process_realtime.recalculate_inventory_for_product_impact')
    def test_session_detail_delete_removes_invalid_process_backlogs_and_recalculates_valid_route(self, mock_recalculate):
        valid_process = Process.objects.create(
            process_code='PVALID-DELETE',
            process_name='正規工程',
            line=self.line,
        )
        invalid_process = Process.objects.create(
            process_code='PINVALID-DELETE',
            process_name='誤工程',
            line=self.line,
        )
        routing = Routing.objects.create(
            product=self.product,
            routing_code='R-INVALID-DELETE',
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=valid_process,
            line=self.line,
            output_product=self.product,
        )
        session = ProcessWorkSession.objects.create(
            process=invalid_process,
            product=self.product,
            product_code=self.product.product_code,
            product_name=self.product.product_name,
            plan_date=date(2026, 3, 5),
            session_no=1,
            session_type='WORK',
            start_action='MANUAL',
            end_action='END',
            started_at=self.make_dt(2026, 3, 5, 9),
            ended_at=self.make_dt(2026, 3, 5, 10),
            status='CLOSED',
            duration_seconds=3600,
            production_qty=5,
        )
        LineBacklog.objects.create(
            plan_date=session.plan_date,
            process=invalid_process,
            product=self.product,
            line=self.line,
            sequence_no=0,
            actual_qty=5,
        )
        LineBacklog.objects.create(
            plan_date=session.plan_date,
            process=invalid_process,
            product=self.product,
            line=self.line,
            sequence_no=1,
            plan_qty=5,
        )
        ProcessRealtimeRecord.objects.create(
            process=invalid_process,
            product=self.product,
            product_code=self.product.product_code,
            product_name=self.product.product_name,
            record_type='PRODUCTION',
            qty=Decimal('5'),
            event_data={'work_session_id': session.id},
        )

        view = ProcessRealtimeRecordViewSet.as_view({'delete': 'session_detail'})
        request = self.factory.delete(
            f'/api/process-realtime/sessions/{session.id}/',
            {'change_reason': '誤工程のため削除'},
            format='json',
        )
        response = view(request, session_id=session.id)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(LineBacklog.objects.filter(
            line=self.line,
            process=invalid_process,
            product=self.product,
            plan_date=session.plan_date,
        ).exists())
        self.assertFalse(ProcessRealtimeRecord.objects.filter(
            event_data__work_session_id=session.id,
        ).exists())
        self.assertFalse(ProcessWorkSession.objects.filter(id=session.id).exists())
        mock_recalculate.assert_called_once_with(
            line_id=self.line.id,
            product_id=self.product.id,
            plan_date=date(2026, 3, 5),
        )

    @patch('production.views_process_realtime.resolve_workday_date_for_process', return_value=date(2026, 3, 5))
    def test_operator_action_end_without_start_is_rejected(self, _mock_plan_date):
        self.create_output_routing()
        view = ProcessRealtimeRecordViewSet.as_view({'post': 'create'})
        request = self.factory.post(
            '/api/process-realtime/',
            {
                'process_id': self.process.id,
                'record_type': 'OPERATOR_ACTION',
                'product_id': self.product.id,
                'operator_name': 'テスト作業者',
                'production_qty': 5,
                'event_data': {
                    'action': 'END',
                },
                'remarks': '終了誤操作確認',
            },
            format='json',
        )
        force_authenticate(request, user=get_user_model().objects.create_user(username='000901'))

        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('開始されていないため終了できません', str(response.data))
        self.assertEqual(ProcessRealtimeRecord.objects.count(), 0)
        self.assertEqual(ProcessWorkSession.objects.count(), 0)


class ProcessRealtimeSessionWorkerTest(TestCase):
    """単位3a: セッションの作業者（operator_login_id）と実績変更API（手動POST／PATCH）を検証する。"""

    def setUp(self):
        self.factory = APIRequestFactory()
        User = get_user_model()
        self.user_a = User.objects.create_user(username='000175', last_name='記入', first_name='太郎')
        self.user_b = User.objects.create_user(username='000999', last_name='終了', first_name='次郎')
        self.user_c = User.objects.create_user(username='000555', last_name='訂正', first_name='花子')
        self.line = Line.objects.create(line_code='SW-L', line_name='作業者検証ライン')
        self.process = Process.objects.create(process_code='SW-P', process_name='作業者検証工程', line=self.line)
        self.product = Product.objects.create(product_code='SW-PROD', product_name='作業者検証品')
        self.parent = Product.objects.create(product_code='SW-SET', product_name='連産親', is_virtual_set=True)
        self.child = Product.objects.create(product_code='SW-CHILD', product_name='連産子')
        bom = BOM.objects.create(
            parent_product=self.parent, version='v1', valid_from=date(2026, 1, 1),
            is_active=True, is_coproduct=True,
        )
        BOMItem.objects.create(bom=bom, child_product=self.child, quantity=Decimal('2'),
                               process=self.process, line=self.line)
        for product, code in ((self.product, 'R-SW1'), (self.parent, 'R-SW2')):
            routing = Routing.objects.create(product=product, routing_code=code, is_default=True, is_active=True)
            RoutingStep.objects.create(
                routing=routing, step_no=10, process=self.process, line=self.line, output_product=product,
            )
        self.reason_pause = InterruptionReason.objects.create(
            code='9101', line_category='3', category='1', display_name='テスト用設備トラブル',
            operation='PAUSE', display_order=10, is_active=True,
        )
        # 在庫・進度の再計算は別テストで検証済みのため呼び出しだけ止める（LineBacklog.actual_qty の反映は実行する）
        patcher = patch('production.views_process_realtime.recalculate_inventory_after_session_change')
        patcher.start()
        self.addCleanup(patcher.stop)
        plan_patcher = patch('production.views_process_realtime.resolve_workday_date_for_process',
                             return_value=date(2026, 3, 5))
        plan_patcher.start()
        self.addCleanup(plan_patcher.stop)

    # ---- 呼び出し補助 ----
    def act(self, user, action, product=None, qty=0, operator_name=None, event_extra=None, reason_code=None):
        product = product or self.product
        event_data = {'action': action}
        event_data.update(event_extra or {})
        if operator_name is None:
            operator_name = f'{user.last_name} {user.first_name}'
        payload = {
            'process_id': self.process.id, 'product_id': product.id, 'record_type': 'OPERATOR_ACTION',
            'qty': qty, 'operator_name': operator_name, 'event_data': event_data,
        }
        if reason_code is not None:
            payload['interruption_reason_code'] = reason_code
        if action == 'END':
            payload['production_qty'] = qty
        request = self.factory.post('/api/process-realtime-records/', payload, format='json')
        force_authenticate(request, user=user)
        with patch('production.serializers_process_realtime.resolve_workday_date_for_process',
                   return_value=date(2026, 3, 5)):
            response = ProcessRealtimeRecordViewSet.as_view({'post': 'create'})(request)
        self.assertEqual(response.status_code, 201, getattr(response, 'data', None))
        return response

    def manual_post(self, **extra):
        payload = {
            'process_id': self.process.id, 'product_code': self.product.product_code,
            'started_at': '2026-03-05T09:00:00', 'ended_at': '2026-03-05T10:00:00',
            'production_qty': 5, 'change_reason': '登録漏れ補完',
        }
        payload.update(extra)
        request = self.factory.post('/api/process-realtime/sessions/', payload, format='json')
        return ProcessRealtimeRecordViewSet.as_view({'post': 'sessions'})(request)

    def patch(self, session, **payload):
        payload.setdefault('change_reason', '作業者訂正')
        request = self.factory.patch(f'/api/process-realtime/sessions/{session.id}/', payload, format='json')
        return ProcessRealtimeRecordViewSet.as_view({'patch': 'session_detail'})(request, session_id=session.id)

    def list_rows(self, **params):
        request = self.factory.get('/api/process-realtime/sessions/', params)
        response = ProcessRealtimeRecordViewSet.as_view({'get': 'sessions'})(request)
        self.assertEqual(response.status_code, 200)
        return response.data

    def production_rows(self, session):
        return ProcessRealtimeRecord.objects.filter(
            record_type='PRODUCTION', event_data__work_session_id=session.id,
        )

    def db_counts(self):
        return (
            ProcessWorkSession.objects.count(),
            ProcessRealtimeRecord.objects.count(),
            LineBacklog.objects.count(),
            ProcessWorkSessionChangeHistory.objects.count(),
        )

    def actual_qty(self, product):
        backlog = LineBacklog.objects.filter(
            line=self.line, process=self.process, product=product, plan_date=date(2026, 3, 5), sequence_no=0,
        ).first()
        return backlog.actual_qty if backlog else None

    def make_normal_closed_session(self, product=None, qty=5):
        self.act(self.user_a, 'START', product=product)
        self.act(self.user_a, 'END', product=product, qty=qty)
        return ProcessWorkSession.objects.latest('id')

    # ---- 1〜3: 通常入力のセッション作成 ----
    def test_normal_start_stores_login_user_on_session_and_keeps_name_empty(self):
        self.act(self.user_a, 'START')
        session = ProcessWorkSession.objects.get()
        self.assertEqual(session.operator_login_id, '000175')
        self.assertEqual(session.operator_name, '')

    def test_two_person_start_uses_worker_username(self):
        self.act(self.user_a, 'START', operator_name='B Worker',
                 event_extra={'two_person_same_equipment': True, 'operator_user_id': str(self.user_b.id)})
        session = ProcessWorkSession.objects.get()
        self.assertEqual(session.operator_login_id, '000999')
        self.assertEqual(session.operator_name, 'b worker')

    def test_start_by_a_and_end_by_b_keeps_start_login_and_lists_end_pair(self):
        self.act(self.user_a, 'START')
        self.act(self.user_b, 'END', qty=4)
        session = ProcessWorkSession.objects.get()
        self.assertEqual(session.operator_login_id, '000175')
        end_production = self.production_rows(session).get()
        self.assertEqual(end_production.operator_login_id, '000999')
        row = self.list_rows()[0]
        self.assertEqual(row['operator_name'], '終了 次郎')
        self.assertEqual(row['operator_login_id'], '000999')

    def test_pair_is_not_mixed_when_end_login_id_is_null(self):
        self.act(self.user_a, 'START')
        self.act(self.user_b, 'END', qty=4)
        session = ProcessWorkSession.objects.get()
        ProcessRealtimeRecord.objects.filter(id=session.end_record_id).update(operator_login_id=None)
        row = self.list_rows()[0]
        self.assertEqual(row['operator_name'], '終了 次郎')
        self.assertIsNone(row['operator_login_id'])  # START の login_id で埋めない

    def test_pause_resume_sessions_take_login_of_their_action_record(self):
        self.act(self.user_a, 'START')
        self.act(self.user_b, 'PAUSE', qty=2, reason_code=self.reason_pause.code)
        self.act(self.user_c, 'RESUME')
        by_type = {(s.session_type, s.start_action): s for s in ProcessWorkSession.objects.all()}
        self.assertEqual(by_type[('WORK', 'START')].operator_login_id, '000175')
        self.assertEqual(by_type[('PAUSE', 'PAUSE')].operator_login_id, '000999')
        self.assertEqual(by_type[('WORK', 'RESUME')].operator_login_id, '000555')

    # ---- 4・5: 手動 POST ----
    def test_manual_post_with_operator_user_id_sets_pair_everywhere(self):
        response = self.manual_post(product_code=self.parent.product_code, operator_user_id=self.user_c.id,
                                    operator_name='無視される名前')
        self.assertEqual(response.status_code, 201, response.data)
        session = ProcessWorkSession.objects.get()
        self.assertEqual(session.operator_login_id, '000555')
        self.assertEqual(session.operator_name, '訂正 花子')
        rows = self.production_rows(session)
        self.assertEqual(rows.count(), 2)  # 親 + 連産子
        self.assertEqual({(r.operator_name, r.operator_login_id) for r in rows}, {('訂正 花子', '000555')})
        self.assertEqual(response.data['operator_name'], '訂正 花子')
        self.assertEqual(response.data['operator_login_id'], '000555')
        history = ProcessWorkSessionChangeHistory.objects.get(session_record_id=session.id)
        self.assertEqual(history.after_data['operator_login_id'], '000555')

    def test_manual_post_name_uses_username_when_full_name_is_empty(self):
        nameless = get_user_model().objects.create_user(username='000777')
        response = self.manual_post(operator_user_id=str(nameless.id))
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(ProcessWorkSession.objects.get().operator_name, '000777')

    def test_manual_post_invalid_worker_is_400_and_creates_nothing(self):
        inactive = get_user_model().objects.create_user(username='000888', is_active=False)
        cases = {
            'missing': ({}, '作業者が指定されていません'),
            'name_only': ({'operator_name': '記入 太郎'}, '作業者が指定されていません'),
            'not_exist': ({'operator_user_id': 99999999}, '存在しないか、無効'),
            'inactive': ({'operator_user_id': inactive.id}, '存在しないか、無効'),
            'not_number': ({'operator_user_id': 'abc'}, '形式が不正'),
            'empty': ({'operator_user_id': ''}, '形式が不正'),
            'bool': ({'operator_user_id': True}, '形式が不正'),
        }
        before = self.db_counts()
        for name, (extra, message) in cases.items():
            with self.subTest(case=name):
                response = self.manual_post(**extra)
                self.assertEqual(response.status_code, 400, getattr(response, 'data', None))
                self.assertIn(message, response.data['detail'])
                self.assertEqual(self.db_counts(), before)

    # ---- 6: 数量だけの PATCH ----
    def test_quantity_only_patch_keeps_session_worker_and_names_rebuilt_rows(self):
        session = self.make_normal_closed_session(product=self.parent, qty=5)
        self.assertEqual(session.operator_name, '')
        session_before = (session.operator_name, session.operator_login_id)
        response = self.patch(session, production_qty=7)
        self.assertEqual(response.status_code, 200, response.data)
        session.refresh_from_db()
        self.assertEqual((session.operator_name, session.operator_login_id), session_before)
        rows = self.production_rows(session)
        self.assertEqual(rows.count(), 2)
        self.assertEqual({(r.operator_name, r.operator_login_id) for r in rows}, {('記入 太郎', '000175')})
        row = [r for r in self.list_rows(coproduct_mode='parent_only') if r['id'] == session.id][0]
        self.assertEqual((row['operator_name'], row['operator_login_id']), ('記入 太郎', '000175'))
        self.assertEqual(response.data['operator_name'], '記入 太郎')

    # ---- 7: 作業者変更 ----
    def test_patch_operator_user_id_updates_all_four_places(self):
        session = self.make_normal_closed_session(product=self.parent, qty=5)
        response = self.patch(session, operator_user_id=self.user_c.id)
        self.assertEqual(response.status_code, 200, response.data)
        session.refresh_from_db()
        self.assertEqual((session.operator_name, session.operator_login_id), ('訂正 花子', '000555'))
        for record_id in (session.start_record_id, session.end_record_id):
            record = ProcessRealtimeRecord.objects.get(id=record_id)
            self.assertEqual((record.operator_name, record.operator_login_id), ('訂正 花子', '000555'))
        rows = self.production_rows(session)
        self.assertEqual(rows.count(), 2)
        self.assertEqual({(r.operator_name, r.operator_login_id) for r in rows}, {('訂正 花子', '000555')})
        self.assertEqual(response.data['operator_login_id'], '000555')
        self.assertEqual(response.data['operator_name'], '訂正 花子')

    def test_patch_operator_user_id_on_open_session(self):
        self.act(self.user_a, 'START')
        session = ProcessWorkSession.objects.get()
        self.assertEqual(session.status, 'OPEN')
        response = self.patch(session, operator_user_id=str(self.user_b.id))
        self.assertEqual(response.status_code, 200, response.data)
        session.refresh_from_db()
        self.assertEqual(session.status, 'OPEN')
        self.assertEqual((session.operator_name, session.operator_login_id), ('終了 次郎', '000999'))
        start = ProcessRealtimeRecord.objects.get(id=session.start_record_id)
        self.assertEqual((start.operator_name, start.operator_login_id), ('終了 次郎', '000999'))

    # ---- 8: 400 のとき DB 不変 ----
    def snapshot_state(self, session):
        session.refresh_from_db()
        records = list(ProcessRealtimeRecord.objects.order_by('id').values_list(
            'id', 'operator_name', 'operator_login_id', 'qty'))
        return (session.operator_name, session.operator_login_id, session.production_qty, records, self.db_counts())

    def test_patch_invalid_worker_is_400_and_db_unchanged(self):
        inactive = get_user_model().objects.create_user(username='000888', is_active=False)
        session = self.make_normal_closed_session()
        state = self.snapshot_state(session)
        cases = {
            'name_only': {'operator_name': '記入 太郎'},
            'name_empty': {'operator_name': ''},
            'id_empty': {'operator_user_id': ''},
            'id_null': {'operator_user_id': None},
            'id_not_number': {'operator_user_id': 'abc'},
            'id_not_exist': {'operator_user_id': 99999999},
            'id_inactive': {'operator_user_id': inactive.id},
            'id_with_qty': {'operator_user_id': 'abc', 'production_qty': 99},
        }
        for name, extra in cases.items():
            with self.subTest(case=name):
                response = self.patch(session, **extra)
                self.assertEqual(response.status_code, 400, getattr(response, 'data', None))
                self.assertEqual(self.snapshot_state(session), state)
        self.assertIn('画面が古い', self.patch(session, operator_name='x').data['detail'])

    def test_operator_name_is_ignored_when_operator_user_id_is_given(self):
        session = self.make_normal_closed_session()
        response = self.patch(session, operator_user_id=self.user_c.id, operator_name='別の名前')
        self.assertEqual(response.status_code, 200, response.data)
        session.refresh_from_db()
        self.assertEqual(session.operator_name, '訂正 花子')

    def test_old_screen_quantity_only_patch_is_200(self):
        # 旧画面は作業者を変えたときだけ operator_name を送る。数量だけなら送らないので従来どおり通る
        session = self.make_normal_closed_session()
        response = self.patch(session, production_qty=6, defect_qty=0)
        self.assertEqual(response.status_code, 200, response.data)

    # ---- 9: 数量不変 ----
    def test_worker_change_does_not_touch_backlog_but_quantity_change_does(self):
        response = self.manual_post(operator_user_id=self.user_a.id)
        self.assertEqual(response.status_code, 201, response.data)
        session = ProcessWorkSession.objects.get()
        self.assertEqual(self.actual_qty(self.product), 5)
        response = self.patch(session, operator_user_id=self.user_c.id)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.actual_qty(self.product), 5)
        response = self.patch(session, production_qty=8)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.actual_qty(self.product), 8)
        response = self.patch(session, production_qty=8, operator_user_id=self.user_b.id)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.actual_qty(self.product), 8)

    # ---- 10: read_only ----
    def test_operator_login_id_in_payload_is_ignored(self):
        session = self.make_normal_closed_session()
        response = self.patch(session, operator_login_id='偽装', production_qty=6)
        self.assertEqual(response.status_code, 200, response.data)
        session.refresh_from_db()
        self.assertEqual(session.operator_login_id, '000175')
        self.assertIn('operator_login_id', self.list_rows()[0])

    # ---- 11: 変更履歴 ----
    def test_history_records_login_id_only_change_and_before_name(self):
        same_name = get_user_model().objects.create_user(username='000176', last_name='記入', first_name='太郎')
        session = self.make_normal_closed_session()
        response = self.patch(session, operator_user_id=same_name.id)
        self.assertEqual(response.status_code, 200, response.data)
        history = ProcessWorkSessionChangeHistory.objects.get(session_record_id=session.id, operation_type='UPDATE')
        self.assertEqual(history.before_data['operator_name'], '記入 太郎')  # セッション自体の名前は空でも解決値
        self.assertEqual(history.before_data['operator_login_id'], '000175')
        self.assertEqual(history.after_data['operator_login_id'], '000176')
        self.assertIn('ログインID: 000175 → 000176', history.change_summary)
        self.assertNotIn('作業者:', history.change_summary)  # 名前は同じなので login_id だけの変更

    def test_history_not_created_when_nothing_changed(self):
        session = self.make_normal_closed_session()
        response = self.patch(session, production_qty=session.production_qty)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(ProcessWorkSessionChangeHistory.objects.filter(session_record_id=session.id).exists())
