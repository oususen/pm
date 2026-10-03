"""分析案の作成で、AI・モデルの選択と外部AI送信の安全境界（伏字化・送信範囲・許可・失敗時の停止）を検証する。"""
import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.db import DatabaseError
from django.test import SimpleTestCase, override_settings

from ai.services import analysis_llm, analysis_planning_service as planning, chat_service
from ai.services.analysis_plan_store import AnalysisError, AnalysisPlanStore
from ai.test_analysis_planning import FakeRedis

PROPOSAL = {
    'title': '作業者1向けの日別出荷',
    'steps': ['日別に全行の出荷数量を合計する'],
    'outputs': ['作業者1が確認する日別の表'],
    'datasets': [{'view': 'v_ai_shipment', 'fields': ['id', 'shipment_date', 'quantity']}],
}
PAYLOAD = {'purpose': '山田太郎さんの出荷傾向を見る', 'date_from': '2026-09-01', 'date_to': '2026-09-30'}


def fake_response(content, finish_reason='stop'):
    body = json.dumps({'choices': [{'message': {'content': content}, 'finish_reason': finish_reason}]}).encode('utf-8')
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = body
    return response


def make_redactor():
    redactor = chat_service.ExternalDataRedactor()
    redactor.add('山田太郎', '作業者1')
    return redactor


@override_settings(AI_ANALYSIS_REDIS_URL='redis://test.invalid/0')
class ExternalPlanningTest(SimpleTestCase):
    def setUp(self):
        self.redis = FakeRedis()
        for target, kwargs in [
            ('ai.services.analysis_plan_store.Redis.from_url', {'return_value': self.redis}),
            ('ai.services.analysis_planning_service.get_analysis_execution_policy',
             {'return_value': SimpleNamespace(plan_cache_ttl_minutes=60, max_fetch_rows=100000)}),
            ('ai.services.analysis_planning_service.external_aggregate_transfer_allowed', {'return_value': True}),
            ('ai.services.analysis_planning_service.AIProviderConfig.objects.filter', {
                'return_value': MagicMock(first=lambda: SimpleNamespace(is_enabled=True, default_model='deepseek-v4-pro')),
            }),
            ('ai.services.analysis_planning_service.chat_service._build_external_data_redactor', {'side_effect': make_redactor}),
        ]:
            patcher = patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)
        for provider in ('deepseek', 'openrouter'):
            patcher = patch.dict(chat_service.EXTERNAL_AGENT_PROVIDERS[provider], {'api_key': 'test-key'})
            patcher.start()
            self.addCleanup(patcher.stop)

    def assert_error(self, status, operation):
        with self.assertRaises(AnalysisError) as caught:
            operation()
        self.assertEqual(caught.exception.status_code, status)
        return caught.exception

    def create(self, **extra):
        return planning.create_plan(3, {**PAYLOAD, **extra})

    def test_external_request_is_redacted_and_sends_no_rows(self):
        with patch('ai.services.analysis_llm.urlopen', return_value=fake_response(json.dumps(PROPOSAL, ensure_ascii=False))) as urlopen:
            plan = self.create(provider='deepseek', model='deepseek-v4-pro')
        request = urlopen.call_args.args[0]
        self.assertEqual(urlopen.call_args.kwargs['timeout'], 90)
        self.assertEqual(request.get_header('Authorization'), 'Bearer test-key')
        body = json.loads(request.data.decode('utf-8'))
        sent = json.dumps(body['messages'], ensure_ascii=False)
        self.assertNotIn('山田太郎', sent)
        self.assertIn('作業者1', sent)
        self.assertNotIn('t_shipment_actual', sent)
        self.assertEqual([message['role'] for message in body['messages']], ['system', 'user'])
        self.assertEqual(json.loads(body['messages'][1]['content']).keys(), {'purpose', 'date_from', 'date_to'})
        self.assertEqual(body['thinking'], {'type': 'disabled'})
        self.assertEqual(body['response_format'], {'type': 'json_object'})
        # 画面に出す分析案は元の名称へ戻し、使ったAIを記録する。保存する目的文は元の文のまま。
        self.assertIn('山田太郎', plan['proposal']['title'])
        self.assertIn('山田太郎', plan['proposal']['outputs'][0])
        self.assertEqual(plan['proposal']['purpose'], PAYLOAD['purpose'])
        self.assertEqual((plan['proposal']['provider'], plan['proposal']['model']), ('deepseek', 'deepseek-v4-pro'))

    def test_openrouter_uses_same_path_with_provider_specific_parameters(self):
        with patch('ai.services.analysis_llm.urlopen', return_value=fake_response(json.dumps(PROPOSAL, ensure_ascii=False))) as urlopen:
            plan = self.create(provider='openrouter', model='qwen/qwen3.8-27b:free')
        body = json.loads(urlopen.call_args.args[0].data.decode('utf-8'))
        self.assertIn('/chat/completions', urlopen.call_args.args[0].full_url)
        self.assertNotIn('response_format', body)
        self.assertNotIn('thinking', body)
        self.assertEqual(body['reasoning'], {'enabled': False})
        self.assertEqual(plan['proposal']['provider'], 'openrouter')

    def test_json_wrapped_in_a_code_block_is_accepted_but_still_validated(self):
        wrapped = '```json\n' + json.dumps(PROPOSAL, ensure_ascii=False) + '\n```'
        with patch('ai.services.analysis_llm.urlopen', return_value=fake_response(wrapped)):
            self.assertEqual(self.create(provider='deepseek')['status'], 'awaiting_method')
        invalid = '```json\n' + json.dumps({**PROPOSAL, 'sql': 'SELECT 1'}, ensure_ascii=False) + '\n```'
        with patch('ai.services.analysis_llm.urlopen', return_value=fake_response(invalid)):
            self.assert_error(502, lambda: self.create(provider='deepseek'))

    def test_selection_is_limited_to_allowed_providers_models_and_settings(self):
        for extra, status in [
            ({'provider': 'unknown'}, 400),
            ({'provider': 'deepseek', 'model': 'not-registered'}, 400),
            ({'provider': 'openrouter', 'model': 'deepseek-v4-pro'}, 400),
            ({'provider': 'qwen', 'model': 'other'}, 400),
            ({'provider': 123}, 400),
            ({'extra': 'x'}, 400),
        ]:
            with self.subTest(extra=extra), patch('ai.services.analysis_llm.urlopen') as urlopen:
                self.assert_error(status, lambda: self.create(**extra))
                urlopen.assert_not_called()

    def test_disabled_provider_policy_off_and_missing_key_stop_before_sending(self):
        cases = [
            (400, patch('ai.services.analysis_planning_service.AIProviderConfig.objects.filter', return_value=MagicMock(
                first=lambda: SimpleNamespace(is_enabled=False, default_model='deepseek-v4-pro')))),
            (403, patch('ai.services.analysis_planning_service.external_aggregate_transfer_allowed', return_value=False)),
            (503, patch.dict(chat_service.EXTERNAL_AGENT_PROVIDERS['deepseek'], {'api_key': ''})),
        ]
        for status, patcher in cases:
            with self.subTest(status=status), patcher, patch('ai.services.analysis_llm.urlopen') as urlopen:
                self.assert_error(status, lambda: self.create(provider='deepseek'))
                urlopen.assert_not_called()

    def test_redaction_failure_or_cache_failure_stops_before_sending(self):
        with patch('ai.services.analysis_planning_service.chat_service._build_external_data_redactor', side_effect=DatabaseError()), \
                patch('ai.services.analysis_llm.urlopen') as urlopen:
            error = self.assert_error(503, lambda: self.create(provider='deepseek'))
            self.assertIn('送信していません', str(error.detail))
            urlopen.assert_not_called()
        with patch.object(AnalysisPlanStore, 'check_connection', side_effect=AnalysisError('接続不可', 503)), \
                patch('ai.services.analysis_llm.urlopen') as urlopen:
            self.assert_error(503, lambda: self.create(provider='deepseek'))
            urlopen.assert_not_called()

    def test_external_failures_are_explicit_and_never_become_a_plan(self):
        def http_error(code):
            return HTTPError('https://example.invalid', code, 'error', {}, BytesIO(b''))

        for outcome, text in [
            (http_error(401), 'APIキー'), (http_error(500), '呼び出しに失敗'), (TimeoutError(), '制限時間内'),
            (fake_response('', 'stop'), '空の応答'), (fake_response('{"title": "x"', 'length'), '生成上限'),
        ]:
            kwargs = {'side_effect': outcome} if isinstance(outcome, Exception) else {'return_value': outcome}
            with self.subTest(text=text), patch('ai.services.analysis_llm.urlopen', **kwargs):
                error = self.assert_error(503, lambda: self.create(provider='deepseek'))
                self.assertIn(text, str(error.detail))
        self.assertEqual(self.redis.values, {})

    def test_local_qwen_path_is_unchanged_and_never_calls_external_api(self):
        raw = json.dumps(PROPOSAL, ensure_ascii=False)
        with patch('ai.services.analysis_planning_service.planning_options', return_value={'available': True}), \
                patch('ai.services.analysis_planning_service.chat_service._chat', return_value=raw) as chat, \
                patch('ai.services.analysis_llm.urlopen') as urlopen:
            plan = self.create()
        urlopen.assert_not_called()
        self.assertEqual(chat.call_args.args[1], 'qwen')
        self.assertEqual((plan['proposal']['provider'], plan['proposal']['model']), ('qwen', chat_service.MODEL))
        self.assertEqual(plan['proposal']['title'], PROPOSAL['title'])

    def test_options_list_providers_with_reasons_and_search_matching_default(self):
        configs = [SimpleNamespace(provider='qwen', is_enabled=True, default_model=chat_service.MODEL),
                   SimpleNamespace(provider='deepseek', is_enabled=False, default_model='deepseek-v4-pro'),
                   SimpleNamespace(provider='openrouter', is_enabled=True, default_model='qwen/qwen3.8-27b:free')]
        with patch('ai.services.analysis_planning_service.AIProviderConfig.objects.all', return_value=configs):
            options = planning.planning_options()
        self.assertEqual(options['default_provider'], 'openrouter')
        by_key = {item['provider']: item for item in options['providers']}
        self.assertTrue(by_key['qwen']['available'] and not by_key['qwen']['external'])
        self.assertFalse(by_key['deepseek']['available'])
        self.assertIn('無効', by_key['deepseek']['reason'])
        self.assertTrue(by_key['openrouter']['available'])
        self.assertEqual(
            [item['id'] for item in by_key['openrouter']['models']], list(chat_service.OPENROUTER_MODELS),
        )
        with patch('ai.services.analysis_planning_service.AIProviderConfig.objects.all', return_value=configs), \
                patch('ai.services.analysis_planning_service.external_aggregate_transfer_allowed', return_value=False):
            blocked = {item['provider']: item for item in planning.planning_options()['providers']}
        self.assertIn('許可されていません', blocked['openrouter']['reason'])
        self.assertFalse(blocked['openrouter']['available'])
        self.assertTrue(analysis_llm.REQUEST_TIMEOUT_SECONDS == 90)
