"""分析案の入力・二段階承認・Redisの期限／競合・固定COUNTを検証する。"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db import DatabaseError
from django.test import SimpleTestCase, override_settings
from redis.exceptions import ConnectionError, WatchError
from rest_framework.test import APIRequestFactory, force_authenticate

from ai.services.analysis_data_service import count_target_rows, validate_datasets, validate_period
from ai.services.analysis_plan_store import AnalysisError, AnalysisPlanStore, public_plan
from ai.services.analysis_planning_service import approve_plan, create_plan, preview_plan, validate_proposal
from ai.views import AIAnalysisApproveView, AIAnalysisPlansView, AIAnalysisPreviewView


class FakeRedis:
    """テスト専用。実装側でのRedis代替先としては使用しない。"""
    def __init__(self):
        self.values = {}
        self.ttls = {}
        self.expire_on_execute = False
        self.pending = None

    def ping(self):
        return True

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, ex=None, nx=False, xx=False, keepttl=False):
        if (nx and key in self.values) or (xx and key not in self.values):
            return False
        self.values[key] = value
        if not keepttl:
            self.ttls[key] = ex
        return True

    def pipeline(self):
        pipe = MagicMock()
        pipe.__enter__.return_value = pipe
        pipe.get.side_effect = self.get
        pipe.set.side_effect = lambda *args, **kwargs: setattr(self, 'pending', (args, kwargs))

        def execute():
            if self.expire_on_execute:
                self.values.clear()
                raise WatchError()
            args, kwargs = self.pending
            return [self.set(*args, **kwargs)]

        pipe.execute.side_effect = execute
        return pipe


@override_settings(AI_ANALYSIS_REDIS_URL='redis://test.invalid/0')
class AnalysisPlanningTest(SimpleTestCase):
    def setUp(self):
        self.redis = FakeRedis()
        patcher = patch('ai.services.analysis_plan_store.Redis.from_url', return_value=self.redis)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.store = AnalysisPlanStore()
        self.proposal = {
            'title': '日別出荷', 'steps': ['日別に全行の出荷数量を合計する'], 'outputs': ['日別の表'],
            'datasets': [{'view': 'v_ai_shipment', 'fields': ['id', 'shipment_date', 'quantity']}],
            'purpose': '出荷傾向を見る', 'date_from': '2026-09-01', 'date_to': '2026-09-30',
            'materials': [], 'conditions': '指定期間の全登録行（追加の絞り条件なし）',
        }
        self.plan = self.store.create(3, self.proposal, 60)
        self.policy = SimpleNamespace(plan_cache_ttl_minutes=60, max_fetch_rows=100000)
        patcher = patch('ai.services.analysis_planning_service.get_analysis_execution_policy', return_value=self.policy)
        patcher.start()
        self.addCleanup(patcher.stop)

    def assert_error(self, status, operation):
        with self.assertRaises(AnalysisError) as caught:
            operation()
        self.assertEqual(caught.exception.status_code, status)

    def test_period_requires_strict_dates_and_order(self):
        for start, end in [(None, '2026-09-30'), ('20260901', '2026-09-30'), ('2026-02-30', '2026-03-01'), ('2026-10-01', '2026-09-30')]:
            self.assert_error(400, lambda: validate_period(start, end))
        self.assertEqual(validate_period('2026-09-01', '2026-09-30'), ('2026-09-01', '2026-09-30'))

    def test_unknown_or_duplicate_views_and_fields_are_rejected(self):
        for datasets in [[], [{'view': 't_shipment_actual', 'fields': ['id']}],
                         [{'view': 'v_ai_shipment', 'fields': ['shipment_date', 'password']}],
                         [{'view': 'v_ai_shipment', 'fields': ['id']}],
                         [{'view': 'v_ai_shipment', 'fields': ['shipment_date', 'shipment_date']}],
                         self.proposal['datasets'] * 2,
                         [{'view': 'v_ai_shipment', 'fields': ['shipment_date'], 'sql': 'DROP TABLE x'}]]:
            self.assert_error(400, lambda: validate_datasets(datasets, '2026-09-01', '2026-09-30'))

    def test_invalid_model_output_is_not_a_usable_plan(self):
        for raw in ['not json', '{}', '{"unsupported":"残業"}', json.dumps({**self.proposal, 'sql': 'SELECT 1'})]:
            self.assert_error(502, lambda: validate_proposal(raw, '目的', '2026-09-01', '2026-09-30'))

    def test_method_count_and_data_approval_order(self):
        self.assert_error(409, lambda: approve_plan(self.store, self.plan['id'], 3, 1, 'data'))
        with patch('ai.services.analysis_planning_service.count_target_rows') as count:
            self.assert_error(409, lambda: preview_plan(self.store, self.plan['id'], 3, 1))
            count.assert_not_called()
        plan = approve_plan(self.store, self.plan['id'], 3, 1, 'method')
        self.assert_error(409, lambda: approve_plan(self.store, plan['id'], 3, 2, 'data'))
        with patch('ai.services.analysis_planning_service.count_target_rows', return_value={
            'datasets': [{'view': 'v_ai_shipment', 'rows': 1200}], 'total_rows': 1200, 'counted_at': '2026-10-03T10:00:00',
        }):
            plan = preview_plan(self.store, plan['id'], 3, 2)
        plan = approve_plan(self.store, plan['id'], 3, 3, 'data')
        self.assertEqual(plan['status'], 'data_approved')
        self.assertEqual(plan['revision'], 4)
        self.assertIsNotNone(plan['method_approved_at'])
        self.assertIsNotNone(plan['data_approved_at'])
        self.assert_error(409, lambda: approve_plan(self.store, plan['id'], 3, 4, 'method'))

    def test_over_limit_and_changed_limit_block_approval(self):
        plan = approve_plan(self.store, self.plan['id'], 3, 1, 'method')
        with patch('ai.services.analysis_planning_service.count_target_rows', return_value={
            'datasets': [{'view': 'v_ai_shipment', 'rows': 100001}], 'total_rows': 100001, 'counted_at': '2026-10-03T10:00:00',
        }):
            plan = preview_plan(self.store, plan['id'], 3, 2)
        self.assertTrue(plan['preview']['over_limit'])
        self.assert_error(400, lambda: approve_plan(self.store, plan['id'], 3, 3, 'data'))
        with patch('ai.services.analysis_planning_service.count_target_rows', return_value={
            'datasets': [{'view': 'v_ai_shipment', 'rows': 1500}], 'total_rows': 1500, 'counted_at': '2026-10-03T10:00:00',
        }):
            plan = preview_plan(self.store, plan['id'], 3, 3)
        self.policy.max_fetch_rows = 1000
        self.assert_error(400, lambda: approve_plan(self.store, plan['id'], 3, 4, 'data'))

    def test_owner_revision_expiry_and_preserved_ttl(self):
        self.assert_error(404, lambda: self.store.get(self.plan['id'], 4))
        self.assert_error(409, lambda: approve_plan(self.store, self.plan['id'], 3, 9, 'method'))
        self.assert_error(400, lambda: approve_plan(self.store, self.plan['id'], 3, True, 'method'))
        approve_plan(self.store, self.plan['id'], 3, 1, 'method')
        self.assertEqual(self.redis.ttls[self.store._key(self.plan['id'])], 3600)
        self.assertNotIn('owner_id', public_plan(self.plan))
        self.redis.values.clear()
        self.assert_error(410, lambda: self.store.get(self.plan['id'], 3))

    def test_expiry_during_approval_does_not_recreate_plan(self):
        self.redis.expire_on_execute = True
        self.assert_error(409, lambda: approve_plan(self.store, self.plan['id'], 3, 1, 'method'))
        self.assertEqual(self.redis.values, {})

    def test_revision_change_during_count_does_not_apply_old_count(self):
        plan = approve_plan(self.store, self.plan['id'], 3, 1, 'method')

        def count(_):
            self.store.update(plan['id'], 3, 2, lambda current: None)
            return {'datasets': [], 'total_rows': 1, 'counted_at': '2026-10-03T10:00:00'}

        with patch('ai.services.analysis_planning_service.count_target_rows', side_effect=count):
            self.assert_error(409, lambda: preview_plan(self.store, plan['id'], 3, 2))
        self.assertIsNone(self.store.get(plan['id'], 3)['preview'])

    def test_creation_uses_only_local_purpose_and_public_schema(self):
        raw = json.dumps({key: self.proposal[key] for key in ('title', 'steps', 'outputs', 'datasets')})
        with patch('ai.services.analysis_planning_service.planning_options', return_value={'available': True}), patch(
            'ai.services.analysis_planning_service.chat_service._chat', return_value=raw,
        ) as chat, patch('ai.services.analysis_planning_service.get_qwen_analysis_timeout', return_value=240):
            plan = create_plan(3, {'purpose': '出荷傾向を見る', 'date_from': '2026-09-01', 'date_to': '2026-09-30'})
        messages, provider = chat.call_args.args
        self.assertEqual(provider, 'qwen')
        self.assertEqual(chat.call_args.kwargs['timeout'], 240)
        self.assertEqual([message['role'] for message in messages], ['system', 'user'])
        self.assertNotIn('t_shipment_actual', messages[0]['content'])
        self.assertNotIn('000196', messages[0]['content'])
        # 製品別の集計では、fieldsに品番と製品名の両方を含める(BOSS承認 2026-10-06)
        self.assertIn('fieldsにproduct_codeとproduct_nameの両方を含める', messages[0]['content'])
        self.assertEqual(plan['status'], 'awaiting_method')

    def test_invalid_qwen_timeout_stops_before_ai_and_plan_save(self):
        with patch('ai.services.analysis_planning_service.planning_options', return_value={'available': True}), patch(
            'ai.services.analysis_planning_service.get_qwen_analysis_timeout', side_effect=AnalysisError('設定不正', 503),
        ), patch('ai.services.analysis_planning_service.chat_service._chat') as chat:
            before = dict(self.redis.values)
            self.assert_error(503, lambda: create_plan(3, {'purpose': '目的', 'date_from': '2026-09-01', 'date_to': '2026-09-30'}))
            chat.assert_not_called()
            self.assertEqual(self.redis.values, before)

    def test_cache_failure_stops_before_ai_call(self):
        with patch('ai.services.analysis_planning_service.planning_options', return_value={'available': True}), patch.object(
            self.redis, 'ping', side_effect=ConnectionError(),
        ), patch('ai.services.analysis_planning_service.chat_service._chat') as chat:
            self.assert_error(503, lambda: create_plan(3, {'purpose': '目的', 'date_from': '2026-09-01', 'date_to': '2026-09-30'}))
            chat.assert_not_called()
        with override_settings(AI_ANALYSIS_REDIS_URL=''):
            self.assert_error(503, AnalysisPlanStore)

    def test_count_uses_only_fixed_view_sql_bound_period_and_reader(self):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.side_effect = [(75000,), (75001,)]
        datasets = [*self.proposal['datasets'], {'view': 'v_ai_purchase_receipt', 'fields': ['id', 'arrival_date', 'qty']}]
        connection = MagicMock()
        connection.cursor.return_value = cursor
        with patch('ai.services.analysis_data_service.settings', SimpleNamespace(DATABASES={'ai_reader': {'USER': 'pm_ai_reader'}})), patch(
            'ai.services.analysis_data_service.connections', {'ai_reader': connection},
        ):
            preview = count_target_rows({**self.proposal, 'datasets': datasets})
        self.assertEqual(preview['total_rows'], 150001)
        self.assertEqual(cursor.execute.call_count, 2)
        for call in cursor.execute.call_args_list:
            sql, params = call.args
            self.assertIn('SELECT COUNT(*) FROM `v_ai_', sql)
            self.assertNotIn('LIMIT', sql)
            self.assertEqual(params, ['2026-09-01', '2026-09-30'])

    def test_reader_failure_does_not_adopt_partial_counts(self):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (1,)
        cursor.execute.side_effect = [None, DatabaseError('接続または権限エラー')]
        connection = MagicMock()
        connection.cursor.return_value = cursor
        datasets = [*self.proposal['datasets'], {'view': 'v_ai_purchase_receipt', 'fields': ['arrival_date', 'qty']}]
        with patch('ai.services.analysis_data_service.settings', SimpleNamespace(DATABASES={'ai_reader': {'USER': 'pm_ai_reader'}})), patch(
            'ai.services.analysis_data_service.connections', {'ai_reader': connection},
        ):
            self.assert_error(503, lambda: count_target_rows({**self.proposal, 'datasets': datasets}))

    def test_api_rejects_overrides_and_requires_authentication(self):
        factory = APIRequestFactory()
        user = SimpleNamespace(pk=3, is_authenticated=True)
        for view, payload in [(AIAnalysisApproveView, {'revision': 1, 'stage': 'method', 'datasets': []}),
                              (AIAnalysisPreviewView, {'revision': 1, 'sql': 'SELECT 1'}),
                              (AIAnalysisApproveView, [{'revision': 1, 'stage': 'method'}]),
                              (AIAnalysisPreviewView, [])]:
            request = factory.post('/', payload, format='json')
            force_authenticate(request, user=user)
            with patch('ai.analysis_permissions._has_resource_permission', return_value=True):
                response = view.as_view()(request, plan_id=self.plan['id'])
            self.assertEqual(response.status_code, 400)
        with patch('ai.views.create_plan') as create:
            response = AIAnalysisPlansView.as_view()(factory.post('/', {}, format='json'))
            self.assertIn(response.status_code, (401, 403))
            create.assert_not_called()


class ManagementColumnPlanningTest(SimpleTestCase):
    def test_server_adds_id_after_validation_without_asking_the_ai(self):
        from ai.services.analysis_data_service import with_management_columns
        datasets = [{'view': 'v_ai_shipment', 'fields': ['shipment_date', 'quantity']},
                    {'view': 'v_ai_purchase_receipt', 'fields': ['arrival_date', 'id', 'qty']}]
        self.assertEqual(with_management_columns(datasets), [
            {'view': 'v_ai_shipment', 'fields': ['id', 'shipment_date', 'quantity']},
            {'view': 'v_ai_purchase_receipt', 'fields': ['id', 'arrival_date', 'qty']},
        ])
        self.assertEqual(datasets[0]['fields'], ['shipment_date', 'quantity'])  # 元の内容は変えない

    def test_validated_proposal_contains_id_and_the_prompt_does_not_ask_for_it(self):
        raw = json.dumps({'title': 't', 'steps': ['s'], 'outputs': ['o'],
                          'datasets': [{'view': 'v_ai_shipment', 'fields': ['shipment_date', 'quantity']}]})
        proposal = validate_proposal(raw, '目的', '2026-01-01', '2026-01-31')
        self.assertEqual(proposal['datasets'][0]['fields'][0], 'id')
