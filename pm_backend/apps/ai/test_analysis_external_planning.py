"""分析案の作成で、AI・モデルの選択と外部AI送信の安全境界（伏字化・送信範囲・許可・失敗時の停止）を検証する。"""
import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.db import DatabaseError
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from ai.services import analysis_llm, analysis_planning_service as planning, chat_service
from ai.services.analysis_plan_store import AnalysisError, AnalysisPlanStore
from ai.test_analysis_planning import FakeRedis
from ai.services.analysis_redaction import AnalysisCodeRedactor, build_analysis_code_redactor
from ai.views import AIAnalysisExternalPreviewView, AIAnalysisPlansView

PROPOSAL = {
    'title': '000175向けの日別出荷',
    'steps': ['日別に全行の出荷数量を合計する'],
    'outputs': ['000175が確認する日別の表'],
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
    redactor = AnalysisCodeRedactor()
    redactor.add('山田太郎', '000175')
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
            ('ai.services.analysis_planning_service.build_analysis_code_redactor', {'side_effect': make_redactor}),
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
        data = {**PAYLOAD, **extra}
        if data.get('provider', 'qwen') != 'qwen':
            data['external_confirmation'] = planning.external_send_preview(3, data)['confirmation']
        return planning.create_plan(3, data)

    def test_external_request_is_redacted_and_sends_no_rows(self):
        with patch('ai.services.analysis_llm.urlopen', return_value=fake_response(json.dumps(PROPOSAL, ensure_ascii=False))) as urlopen:
            plan = self.create(provider='deepseek', model='deepseek-v4-pro')
        request = urlopen.call_args.args[0]
        self.assertEqual(urlopen.call_args.kwargs['timeout'], 90)
        self.assertEqual(request.get_header('Authorization'), 'Bearer test-key')
        body = json.loads(request.data.decode('utf-8'))
        sent = json.dumps(body['messages'], ensure_ascii=False)
        self.assertNotIn('山田太郎', sent)
        self.assertIn('000175', sent)
        self.assertNotIn('t_shipment_actual', sent)
        self.assertEqual([message['role'] for message in body['messages']], ['system', 'user'])
        self.assertEqual(json.loads(body['messages'][1]['content']).keys(), {'purpose', 'date_from', 'date_to'})
        self.assertEqual(body['thinking'], {'type': 'disabled'})
        self.assertEqual(body['response_format'], {'type': 'json_object'})
        # 実コードは自動復元しない。元の目的文と確認済み送信文はRedis上だけに保存する。
        self.assertIn('000175', plan['proposal']['title'])
        self.assertIn('000175', plan['proposal']['outputs'][0])
        self.assertNotIn('山田太郎', plan['proposal']['title'])
        self.assertEqual(plan['proposal']['external_purpose'], '000175さんの出荷傾向を見る')
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
        with patch('ai.services.analysis_planning_service.build_analysis_code_redactor', side_effect=DatabaseError()), \
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

    def test_local_qwen_uses_its_timeout_and_never_calls_external_api(self):
        raw = json.dumps(PROPOSAL, ensure_ascii=False)
        with patch('ai.services.analysis_planning_service.planning_options', return_value={'available': True}), \
                patch('ai.services.analysis_planning_service.chat_service._chat', return_value=raw) as chat, \
                patch('ai.services.analysis_planning_service.get_qwen_analysis_timeout', return_value=180), \
                patch('ai.services.analysis_llm.urlopen') as urlopen:
            plan = self.create()
        urlopen.assert_not_called()
        self.assertEqual(chat.call_args.args[1], 'qwen')
        self.assertEqual(chat.call_args.kwargs['timeout'], 180)
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

    def test_preview_never_calls_ai_or_saves_a_plan(self):
        with patch('ai.services.analysis_llm.urlopen') as urlopen:
            preview = planning.external_send_preview(3, {**PAYLOAD, 'provider': 'deepseek'})
        self.assertEqual(preview['purpose'], '000175さんの出荷傾向を見る')
        urlopen.assert_not_called()
        self.assertEqual(self.redis.values, {})

    def test_http_preview_and_unconfirmed_create(self):
        factory = APIRequestFactory()
        data = {**PAYLOAD, 'provider': 'deepseek'}
        with patch('ai.analysis_permissions._has_resource_permission', return_value=True), patch('ai.services.analysis_llm.urlopen') as urlopen:
            request = factory.post('/api/ai/analysis/external-preview/', data, format='json')
            force_authenticate(request, user=SimpleNamespace(pk=3, is_authenticated=True))
            response = AIAnalysisExternalPreviewView.as_view()(request)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['purpose'], '000175さんの出荷傾向を見る')
            request = factory.post('/api/ai/analysis/plans/', data, format='json')
            force_authenticate(request, user=SimpleNamespace(pk=3, is_authenticated=True))
            self.assertEqual(AIAnalysisPlansView.as_view()(request).status_code, 409)
            urlopen.assert_not_called()

    def test_unconfirmed_or_changed_requests_never_send(self):
        data = {**PAYLOAD, 'provider': 'deepseek'}
        token = planning.external_send_preview(3, data)['confirmation']
        changes = [
            {}, {'external_confirmation': True}, {'external_confirmation': 'fake'},
            {'external_confirmation': token, 'purpose': '別の目的'},
            {'external_confirmation': token, 'date_to': '2026-10-01'},
            {'external_confirmation': token, 'model': 'deepseek-v4-flash'},
        ]
        for change in changes:
            with self.subTest(change=change), patch('ai.services.analysis_llm.urlopen') as urlopen:
                # 未許可モデルは400、確認内容の不一致は409。
                self.assert_error(400 if change.get('model') and change['model'] not in chat_service.DEEPSEEK_MODELS else 409,
                                  lambda: planning.create_plan(3, {**data, **change}))
                urlopen.assert_not_called()
        with patch('ai.services.analysis_llm.urlopen') as urlopen:
            self.assert_error(409, lambda: planning.create_plan(4, {**data, 'external_confirmation': token}))
            changed = AnalysisCodeRedactor()
            changed.add('山田太郎', '000999')
            with patch('ai.services.analysis_planning_service.build_analysis_code_redactor', return_value=changed):
                self.assert_error(409, lambda: planning.create_plan(3, {**data, 'external_confirmation': token}))
            urlopen.assert_not_called()

    def test_missing_or_ambiguous_code_stops_preview_and_send(self):
        for codes in ((None,), ('000175', '000999')):
            redactor = AnalysisCodeRedactor()
            for code in codes:
                redactor.add('山田太郎', code)
            with patch('ai.services.analysis_planning_service.build_analysis_code_redactor', return_value=redactor), \
                    patch('ai.services.analysis_llm.urlopen') as urlopen:
                self.assert_error(400, lambda: planning.external_send_preview(3, {**PAYLOAD, 'provider': 'deepseek'}))
                self.assert_error(400, lambda: planning.create_plan(3, {**PAYLOAD, 'provider': 'deepseek', 'external_confirmation': 'fake'}))
                urlopen.assert_not_called()


class AnalysisCodeRedactorTest(SimpleTestCase):
    def test_codes_keep_zeroes_no_cascade_and_email_removed(self):
        redactor = AnalysisCodeRedactor()
        redactor.add('王崇栓', '000175')
        redactor.add('クボタ', '000196')
        redactor.add('000175', '000999')
        self.assertEqual(redactor.redact_text('王崇栓 クボタ test@example.com'), '000175 000196 [メールアドレス]')

    def test_builder_includes_inactive_and_uncoded_registered_names(self):
        users = MagicMock()
        users.values.return_value = [
            {'username': 'former', 'last_name': '王', 'first_name': '崇栓', 'profile__employee_code': '000175'},
            {'username': 'no-code', 'last_name': 'コード', 'first_name': '未登録', 'profile__employee_code': None},
        ]
        customers = MagicMock()
        customers.values.return_value = [{'customer_name': 'クボタ', 'short_name': '旧顧客', 'customer_code': '000196'}]
        suppliers = MagicMock()
        suppliers.values.return_value = [{'supplier_name': '旧仕入先', 'supplier_code': '000007'}]
        operators = MagicMock()
        operators.exclude.return_value.exclude.return_value.values_list.return_value.distinct.return_value = ['王  崇栓', '未解決作業者']
        with patch('ai.services.analysis_redaction.get_user_model') as user_model, \
                patch('ai.services.analysis_redaction.Customer.objects.using', return_value=customers), \
                patch('ai.services.analysis_redaction.Supplier.objects.using', return_value=suppliers), \
                patch('ai.services.analysis_redaction.ProcessRealtimeRecord.objects.using', return_value=operators):
            user_model.return_value.objects.using.return_value = users
            redactor = build_analysis_code_redactor()
        self.assertEqual(redactor.redact_text('王崇栓 former 王　崇栓 王  崇栓 クボタ 旧顧客 旧仕入先'),
                         '000175 000175 000175 000175 000196 000196 000007')
        users.filter.assert_not_called()
        customers.filter.assert_not_called()
        for text in ('コード未登録', '未解決作業者'):
            with self.assertRaises(AnalysisError):
                redactor.redact_text(text)


# 分析の温度は、AI設定(DB)から取得する。このモジュールの試験は、DBを使わないため、従来の値(0.3)を返す。温度の取得そのものは、test_analysis_temperature.pyで確認する
def setUpModule():
    global _temperature_patch
    from unittest import mock
    _temperature_patch = mock.patch('ai.services.analysis_llm.get_analysis_temperature', return_value=0.3)
    _temperature_patch.start()


def tearDownModule():
    _temperature_patch.stop()
