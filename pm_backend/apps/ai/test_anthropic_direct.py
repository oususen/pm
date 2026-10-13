"""Anthropic Claude直接接続(単位1: 基盤と分析案の作成)の検証。外部APIは呼ばない(urlopenを模擬)。APIキーはテスト専用のダミー値。"""
import importlib
import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import UserPermission
from ai.config.catalog import PROVIDER_CATALOG
from ai.config.models import AIProviderConfig
from ai.config.serializers import AIProviderConfigSerializer
from ai.services import analysis_llm, analysis_planning_service as planning, anthropic_client, chat_service
from ai.services.analysis_plan_store import AnalysisError
from ai.test_analysis_planning import FakeRedis

DUMMY_KEY = 'dummy-test-key-not-real'
SCHEMA = {'type': 'object', 'properties': {'a': {'type': 'string'}}, 'required': ['a'], 'additionalProperties': False}
PROPOSAL = {
    'title': '日別出荷', 'steps': ['日別に合計する'], 'outputs': ['日別の表'],
    'datasets': [{'view': 'v_ai_shipment', 'fields': ['id', 'shipment_date', 'quantity']}],
}
PAYLOAD = {'purpose': '出荷の傾向を見る', 'date_from': '2026-09-01', 'date_to': '2026-09-30'}


def claude_response(text='{"a": "x"}', stop_reason='end_turn', content=None):
    body = json.dumps({'content': content if content is not None else [{'type': 'text', 'text': text}], 'stop_reason': stop_reason}).encode('utf-8')
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = body
    return response


def openai_response(text):
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = json.dumps({'choices': [{'message': {'content': text}, 'finish_reason': 'stop'}]}).encode('utf-8')
    return response


def http_error(code, body=b'SECRET-BODY'):
    return HTTPError('https://example.invalid', code, 'error', {}, BytesIO(body))


class ClientTests(SimpleTestCase):
    messages = [{'role': 'system', 'content': 'SYS'}, {'role': 'user', 'content': 'U1'}, {'role': 'assistant', 'content': 'A1'}, {'role': 'user', 'content': 'U2'}]

    def call(self, messages=None, schema=SCHEMA, **urlopen_kwargs):
        urlopen_kwargs.setdefault('return_value', claude_response())
        with patch.dict(chat_service.EXTERNAL_AGENT_PROVIDERS['anthropic'], {'api_key': DUMMY_KEY}), \
                patch('ai.services.anthropic_client.urlopen', **urlopen_kwargs) as urlopen:
            result = analysis_llm.request_external_json('anthropic', 'claude-haiku-5-5', messages or self.messages, 0.3, json_schema=schema)
        return result, urlopen

    def error(self, **urlopen_kwargs):
        with self.assertRaises(chat_service.LocalAIError) as caught:
            self.call(**urlopen_kwargs)
        return caught.exception

    def test_body_headers_and_conversion(self):
        result, urlopen = self.call()
        self.assertEqual(result, '{"a": "x"}')
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.anthropic.com/v1/messages')
        self.assertEqual(urlopen.call_args.kwargs['timeout'], 90)
        headers = {key.lower(): value for key, value in request.header_items()}
        self.assertEqual(headers['x-api-key'], DUMMY_KEY)
        self.assertEqual(headers['anthropic-version'], '2023-06-01')
        self.assertNotIn('authorization', headers)
        body = json.loads(request.data.decode('utf-8'))
        self.assertEqual(body['system'], 'SYS')
        self.assertEqual(body['messages'], [{'role': 'user', 'content': 'U1'}, {'role': 'assistant', 'content': 'A1'}, {'role': 'user', 'content': 'U2'}])
        for key in ('temperature', 'top_p', 'top_k', 'stream'):
            self.assertNotIn(key, body)
        self.assertEqual(body['thinking'], {'type': 'disabled'})
        self.assertEqual(body['max_tokens'], chat_service.AGENT_MAX_TOKENS)
        self.assertEqual(body['model'], 'claude-haiku-5-5')
        self.assertEqual(body['output_config'], {'format': {'type': 'json_schema', 'schema': SCHEMA}})
        self.assertEqual(set(body), {'model', 'max_tokens', 'messages', 'thinking', 'output_config', 'system'})

    def test_a_different_temperature_argument_is_never_sent(self):
        with patch.dict(chat_service.EXTERNAL_AGENT_PROVIDERS['anthropic'], {'api_key': DUMMY_KEY}), \
                patch('ai.services.anthropic_client.urlopen', return_value=claude_response()) as urlopen:
            analysis_llm.request_external_json('anthropic', 'claude-haiku-5-5', self.messages, 0.9, json_schema=SCHEMA)
        self.assertNotIn(b'temperature', urlopen.call_args.args[0].data)

    def test_text_blocks_are_joined_and_other_blocks_are_ignored(self):
        content = [{'type': 'thinking', 'thinking': 'x'}, {'type': 'text', 'text': '{"a":'}, {'type': 'tool_use'}, {'type': 'text', 'text': ' "x"}'}]
        result, _ = self.call(return_value=claude_response(content=content))
        self.assertEqual(result, '{"a": "x"}')

    def test_no_schema_stops_without_any_http_request(self):
        with patch.dict(chat_service.EXTERNAL_AGENT_PROVIDERS['anthropic'], {'api_key': DUMMY_KEY}), \
                patch('ai.services.anthropic_client.urlopen') as urlopen, patch('ai.services.analysis_llm.urlopen') as other:
            with self.assertRaises(chat_service.LocalAIError):
                analysis_llm.request_external_json('anthropic', 'claude-haiku-5-5', self.messages, 0.3)
        urlopen.assert_not_called()
        other.assert_not_called()

    def test_a_trailing_assistant_message_or_a_missing_user_is_not_sent(self):
        for messages in ([{'role': 'user', 'content': 'a'}, {'role': 'assistant', 'content': 'b'}], [{'role': 'system', 'content': 's'}],
                         [{'role': 'tool', 'content': 'x'}]):
            with self.subTest(messages=messages), patch('ai.services.anthropic_client.urlopen') as urlopen:
                with patch.dict(chat_service.EXTERNAL_AGENT_PROVIDERS['anthropic'], {'api_key': DUMMY_KEY}), self.assertRaises(chat_service.LocalAIError):
                    analysis_llm.request_external_json('anthropic', 'm', messages, json_schema=SCHEMA)
                urlopen.assert_not_called()

    def test_missing_key_is_ai_auth_and_sends_nothing(self):
        with patch.dict(chat_service.EXTERNAL_AGENT_PROVIDERS['anthropic'], {'api_key': ''}), patch('ai.services.anthropic_client.urlopen') as urlopen:
            with self.assertRaises(chat_service.LocalAIError) as caught:
                analysis_llm.request_external_json('anthropic', 'm', self.messages, json_schema=SCHEMA)
        self.assertEqual(caught.exception.code, 'ai_auth')
        urlopen.assert_not_called()

    def test_http_status_classification_and_no_body_leak(self):
        expected = {401: ('ai_auth', 'APIキー'), 403: ('ai_auth', 'APIキー'), 402: ('ai_http', '請求エラー'), 429: ('ai_http', 'レート制限または月間上限'),
                    400: ('ai_http', '残高・上限・リクエスト内容を確認'), 500: ('ai_http', '呼び出しに失敗'), 529: ('ai_http', '呼び出しに失敗'), 404: ('ai_http', '呼び出しに失敗')}
        for status, (code, text) in expected.items():
            with self.subTest(status=status):
                error = self.error(side_effect=http_error(status))
                self.assertEqual(error.code, code)
                self.assertIn(text, str(error))
                for secret in ('SECRET-BODY', DUMMY_KEY):
                    self.assertNotIn(secret, str(error))
                    self.assertNotIn(secret, repr(error))

    def test_timeout_and_connection_errors(self):
        self.assertEqual(self.error(side_effect=TimeoutError()).code, 'ai_timeout')
        self.assertEqual(self.error(side_effect=URLError(TimeoutError())).code, 'ai_timeout')
        self.assertEqual(self.error(side_effect=URLError('refused')).code, 'ai_connect')
        self.assertEqual(self.error(side_effect=OSError('x')).code, 'ai_connect')

    def test_http_error_is_handled_before_url_error(self):
        # HTTPErrorはURLErrorの下位の型。順序が逆だと、401が接続失敗になる
        self.assertTrue(issubclass(HTTPError, URLError))
        self.assertEqual(self.error(side_effect=http_error(401)).code, 'ai_auth')
        self.assertEqual(self.error(side_effect=http_error(429)).code, 'ai_http')

    def test_incomplete_or_refused_responses_are_never_a_success(self):
        for reason in ('max_tokens', 'refusal', 'model_context_window_exceeded'):
            with self.subTest(reason=reason):
                error = self.error(return_value=claude_response('{"a": "x"}', stop_reason=reason))
                self.assertEqual(error.code, '')
                self.assertNotIn('"a"', str(error))
        self.assertIn('生成上限', str(self.error(return_value=claude_response('{"a"', stop_reason='max_tokens'))))

    def test_empty_text_is_ai_empty(self):
        for content in ([], [{'type': 'text', 'text': '  '}], [{'type': 'thinking', 'thinking': 'x'}]):
            with self.subTest(content=content):
                self.assertEqual(self.error(return_value=claude_response(content=content)).code, 'ai_empty')

    def test_invalid_json_response_is_not_leaked(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'SECRET-NOT-JSON'
        error = self.error(return_value=response)
        self.assertNotIn('SECRET', str(error))


class ExistingProvidersUnchangedTests(SimpleTestCase):
    """deepseek/openrouterの送信内容(URL・ヘッダ・body)が従来と同一であること(スナップショット)。json_schemaを渡しても影響しない。"""
    messages = [{'role': 'system', 'content': 'S'}, {'role': 'user', 'content': 'U'}]

    def sent(self, provider, model, **kwargs):
        with patch.dict(chat_service.EXTERNAL_AGENT_PROVIDERS[provider], {'api_key': DUMMY_KEY}), \
                patch('ai.services.analysis_llm.urlopen', return_value=openai_response('{}')) as urlopen:
            analysis_llm.request_external_json(provider, model, self.messages, 0.3, **kwargs)
        request = urlopen.call_args.args[0]
        return request.full_url, dict(request.header_items()), json.loads(request.data.decode('utf-8')), urlopen.call_args.kwargs

    def test_deepseek_snapshot(self):
        base = {'model': 'deepseek-v4-pro', 'stream': False, 'messages': self.messages, 'temperature': 0.3, 'max_tokens': 4096,
                'response_format': {'type': 'json_object'}, 'thinking': {'type': 'disabled'}}
        for kwargs in ({}, {'json_schema': SCHEMA}):
            url, headers, body, options = self.sent('deepseek', 'deepseek-v4-pro', **kwargs)
            self.assertEqual(url, 'https://api.deepseek.com/chat/completions')
            self.assertEqual(headers, {'Content-type': 'application/json', 'Authorization': f'Bearer {DUMMY_KEY}'})
            self.assertEqual(body, base)
            self.assertEqual(options, {'timeout': 90})

    def test_openrouter_snapshot(self):
        common = {'stream': False, 'messages': self.messages, 'temperature': 0.3, 'max_tokens': 4096,
                  'provider': {'allow_fallbacks': True}, 'reasoning': {'enabled': False}}
        for model, extra in (('qwen/qwen3-14b', {}), ('deepseek/deepseek-v4.1-flash', {'response_format': {'type': 'json_object'}})):
            for kwargs in ({}, {'json_schema': SCHEMA}):
                with self.subTest(model=model, kwargs=bool(kwargs)):
                    url, headers, body, _ = self.sent('openrouter', model, **kwargs)
                    self.assertEqual(url, 'https://openrouter.ai/api/v1/chat/completions')
                    self.assertEqual(headers, {'Content-type': 'application/json', 'Authorization': f'Bearer {DUMMY_KEY}'})
                    self.assertEqual(body, {'model': model, **common, **extra})

    def test_anthropic_client_is_not_used_for_other_providers(self):
        with patch('ai.services.anthropic_client.request_json') as client:
            self.sent('deepseek', 'deepseek-v4-pro')
            self.sent('openrouter', 'qwen/qwen3-14b')
        client.assert_not_called()


class ProviderRegistrationTests(SimpleTestCase):
    def test_catalog_chat_service_and_planning_providers_agree(self):
        self.assertEqual(dict(PROVIDER_CATALOG['anthropic']['models']), dict(chat_service.ANTHROPIC_MODELS))
        self.assertEqual(list(chat_service.ANTHROPIC_MODELS), ['claude-haiku-5-5'])
        self.assertEqual(chat_service.ANTHROPIC_MODELS['claude-haiku-5-5'], 'Claude Haiku 5.5（Anthropic・有料/要クレジット）')
        self.assertEqual(PROVIDER_CATALOG['anthropic']['label'], 'Anthropic Claude')
        agent = chat_service.EXTERNAL_AGENT_PROVIDERS['anthropic']
        self.assertEqual((agent['label'], agent['default_model'], agent['models']), ('Anthropic Claude', 'claude-haiku-5-5', chat_service.ANTHROPIC_MODELS))
        self.assertIn('anthropic', planning.PLANNING_PROVIDERS)
        self.assertEqual(set(PROVIDER_CATALOG), {'qwen', *chat_service.EXTERNAL_AGENT_PROVIDERS})
        self.assertEqual(set(PROVIDER_CATALOG), set(planning.PLANNING_PROVIDERS))
        self.assertEqual(chat_service.PROVIDER_REQUIRED_PERMISSION, {'anthropic': 'ai.analysis'})
        self.assertTrue(set(dict(AIProviderConfig._meta.get_field('provider').choices)) == set(PROVIDER_CATALOG))

    def test_base_url_has_no_trailing_slash_and_the_key_is_empty_by_default_in_the_code(self):
        self.assertFalse(chat_service.ANTHROPIC_BASE_URL.endswith('/'))

    def options(self, enabled=True, key=DUMMY_KEY, transfer=True):
        configs = [SimpleNamespace(provider='anthropic', is_enabled=enabled, default_model='claude-haiku-5-5')]
        with patch('ai.services.analysis_planning_service.AIProviderConfig.objects.all', return_value=configs), \
                patch.dict(chat_service.EXTERNAL_AGENT_PROVIDERS['anthropic'], {'api_key': key}), \
                patch('ai.services.analysis_planning_service.external_aggregate_transfer_allowed', return_value=transfer):
            return {item['provider']: item for item in planning.planning_options()['providers']}['anthropic']

    def test_planning_options_report_availability_and_reason(self):
        ready = self.options()
        self.assertTrue(ready['available'] and ready['external'])
        self.assertEqual((ready['label'], ready['default_model']), ('Anthropic Claude', 'claude-haiku-5-5'))
        self.assertEqual([item['id'] for item in ready['models']], ['claude-haiku-5-5'])
        for kwargs, text in (({'enabled': False}, '無効'), ({'key': ''}, 'APIキーが未設定'), ({'transfer': False}, '許可されていません')):
            with self.subTest(kwargs=kwargs):
                item = self.options(**kwargs)
                self.assertFalse(item['available'])
                self.assertIn(text, item['reason'])

    def test_unregistered_model_is_400_and_disabled_is_400(self):
        config = MagicMock(first=lambda: SimpleNamespace(is_enabled=True, default_model='claude-haiku-5-5'))
        with patch('ai.services.analysis_planning_service.AIProviderConfig.objects.filter', return_value=config), \
                patch('ai.services.analysis_planning_service.external_aggregate_transfer_allowed', return_value=True), \
                patch.dict(chat_service.EXTERNAL_AGENT_PROVIDERS['anthropic'], {'api_key': DUMMY_KEY}):
            self.assertEqual(planning.resolve_planning_provider({'provider': 'anthropic'}), ('anthropic', 'claude-haiku-5-5'))
            with self.assertRaises(AnalysisError) as caught:
                planning.resolve_planning_provider({'provider': 'anthropic', 'model': 'claude-unknown'})
            self.assertEqual(caught.exception.status_code, 400)
        disabled = MagicMock(first=lambda: SimpleNamespace(is_enabled=False, default_model='claude-haiku-5-5'))
        with patch('ai.services.analysis_planning_service.AIProviderConfig.objects.filter', return_value=disabled), \
                self.assertRaises(AnalysisError) as caught:
            planning.resolve_planning_provider({'provider': 'anthropic'})
        self.assertEqual(caught.exception.status_code, 400)

    def test_schema_is_the_plan_or_unsupported_by_anyof(self):
        schema = planning.ANTHROPIC_PLAN_SCHEMA
        plan, unsupported = schema['anyOf']
        self.assertEqual(set(plan['properties']), {'title', 'steps', 'outputs', 'datasets'})
        self.assertEqual(set(plan['required']), {'title', 'steps', 'outputs', 'datasets'})
        self.assertEqual(set(plan['properties']['datasets']['items']['properties']), {'view', 'fields'})
        self.assertEqual(set(unsupported['properties']), {'unsupported'})
        self.assertIs(plan['additionalProperties'], False)
        self.assertIs(unsupported['additionalProperties'], False)


class SerializerTests(SimpleTestCase):
    def validate(self, provider, data):
        serializer = AIProviderConfigSerializer(AIProviderConfig(provider=provider, default_model='claude-haiku-5-5'), data=data, partial=True)
        return serializer.is_valid(), serializer.errors

    def test_temperature_change_is_rejected_for_anthropic_only(self):
        valid, errors = self.validate('anthropic', {'analysis_temperature': 0.5})
        self.assertFalse(valid)
        self.assertIn('analysis_temperature', errors)
        self.assertTrue(self.validate('openrouter', {'analysis_temperature': 0.5})[0])
        self.assertTrue(self.validate('anthropic', {'is_enabled': True, 'default_model': 'claude-haiku-5-5'})[0])
        self.assertFalse(self.validate('anthropic', {'default_model': 'claude-other'})[0])


@override_settings(AI_ANALYSIS_REDIS_URL='redis://test.invalid/0')
class PlanCreationTests(SimpleTestCase):
    def setUp(self):
        self.redis = FakeRedis()
        config = MagicMock(first=lambda: SimpleNamespace(is_enabled=True, default_model='claude-haiku-5-5'))
        for target, kwargs in [
            ('ai.services.analysis_plan_store.Redis.from_url', {'return_value': self.redis}),
            ('ai.services.analysis_planning_service.get_analysis_execution_policy', {'return_value': SimpleNamespace(plan_cache_ttl_minutes=60, max_fetch_rows=100000)}),
            ('ai.services.analysis_planning_service.external_aggregate_transfer_allowed', {'return_value': True}),
            ('ai.services.analysis_planning_service.AIProviderConfig.objects.filter', {'return_value': config}),
            ('ai.services.analysis_planning_service._external_purpose', {'side_effect': lambda text: text}),
        ]:
            patcher = patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.dict(chat_service.EXTERNAL_AGENT_PROVIDERS['anthropic'], {'api_key': DUMMY_KEY})
        patcher.start()
        self.addCleanup(patcher.stop)

    def create(self):
        data = {**PAYLOAD, 'provider': 'anthropic', 'model': 'claude-haiku-5-5'}
        data['external_confirmation'] = planning.external_send_preview(3, data)['confirmation']
        return planning.create_plan(3, data)

    def test_plan_is_created_with_structured_output_and_without_temperature(self):
        with patch.object(analysis_llm, 'get_analysis_temperature', return_value=0.3) as temperature, \
                patch('ai.services.anthropic_client.urlopen', return_value=claude_response(json.dumps(PROPOSAL, ensure_ascii=False))) as urlopen, \
                patch('ai.services.analysis_llm.urlopen') as compatible:
            plan = self.create()
        temperature.assert_called_once_with('anthropic')  # 読むだけ。値は送らない
        compatible.assert_not_called()
        body = json.loads(urlopen.call_args.args[0].data.decode('utf-8'))
        for key in ('temperature', 'top_p', 'top_k', 'response_format', 'stream'):
            self.assertNotIn(key, body)
        self.assertEqual(body['output_config']['format'], {'type': 'json_schema', 'schema': planning.ANTHROPIC_PLAN_SCHEMA})
        self.assertEqual(body['thinking'], {'type': 'disabled'})
        self.assertEqual([m['role'] for m in body['messages']], ['user'])
        self.assertIn('分析案だけを作る', body['system'])
        self.assertEqual((plan['proposal']['provider'], plan['proposal']['model']), ('anthropic', 'claude-haiku-5-5'))
        self.assertEqual(plan['status'], 'awaiting_method')

    def test_unsupported_answer_is_not_a_plan(self):
        with patch.object(analysis_llm, 'get_analysis_temperature', return_value=0.3), \
                patch('ai.services.anthropic_client.urlopen', return_value=claude_response('{"unsupported": "未公開データが必要"}')):
            with self.assertRaises(AnalysisError) as caught:
                self.create()
        self.assertEqual(caught.exception.status_code, 502)
        self.assertEqual(self.redis.values, {})

    def test_failures_are_503_and_never_become_a_plan(self):
        for outcome in (http_error(402), http_error(429), TimeoutError(), claude_response('{"title"', stop_reason='max_tokens')):
            kwargs = {'side_effect': outcome} if isinstance(outcome, Exception) else {'return_value': outcome}
            with self.subTest(outcome=type(outcome).__name__), patch.object(analysis_llm, 'get_analysis_temperature', return_value=0.3), \
                    patch('ai.services.anthropic_client.urlopen', **kwargs):
                with self.assertRaises(AnalysisError) as caught:
                    self.create()
                self.assertEqual(caught.exception.status_code, 503)
                self.assertNotIn(DUMMY_KEY, str(caught.exception.detail))
        self.assertEqual(self.redis.values, {})

    def test_unconfirmed_request_never_sends(self):
        with patch('ai.services.anthropic_client.urlopen') as urlopen, self.assertRaises(AnalysisError) as caught:
            planning.create_plan(3, {**PAYLOAD, 'provider': 'anthropic', 'external_confirmation': 'fake'})
        self.assertEqual(caught.exception.status_code, 409)
        urlopen.assert_not_called()


class ConsultCodegenGuardTests(SimpleTestCase):
    def test_consult_rejects_anthropic_with_400_and_calls_no_ai(self):
        from ai.services import analysis_consult_service as consult
        with patch('ai.services.anthropic_client.urlopen') as claude, patch('ai.services.analysis_llm.urlopen') as other, \
                patch.object(analysis_llm, 'request_external_json') as external, patch.object(consult, 'resolve_planning_provider') as resolve:
            with self.assertRaises(AnalysisError) as caught:
                consult.consult({'messages': [{'role': 'user', 'content': '出荷を見たい'}], 'provider': 'anthropic', 'external_confirmed': True})
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(str(caught.exception.detail), 'Claude は、相談・コード生成ではまだ使えません。')
        for mock in (claude, other, external, resolve):
            mock.assert_not_called()

    def test_codegen_rejects_a_plan_made_with_anthropic_with_400_and_calls_no_ai(self):
        from ai.services import analysis_codegen_service as codegen
        plan = {'proposal': {'provider': 'anthropic', 'model': 'claude-haiku-5-5'}}
        with patch('ai.services.anthropic_client.urlopen') as claude, patch('ai.services.analysis_llm.urlopen') as other, \
                patch.object(codegen, 'resolve_planning_provider') as resolve:
            with self.assertRaises(AnalysisError) as caught:
                codegen._provider_for(plan)
        self.assertEqual(caught.exception.status_code, 400)
        self.assertIn('コード生成', str(caught.exception.detail))
        for mock in (claude, other, resolve):
            mock.assert_not_called()

    def test_other_providers_still_reach_the_existing_check_in_codegen(self):
        from ai.services import analysis_codegen_service as codegen
        with patch.object(codegen, 'resolve_planning_provider', return_value=('openrouter', 'm')) as resolve:
            self.assertEqual(codegen._provider_for({'proposal': {'provider': 'openrouter', 'model': 'm'}}), ('openrouter', 'm'))
        resolve.assert_called_once()


@override_settings(ALLOWED_HOSTS=['testserver'])
class PermissionAndChatGuardTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create_user(username='claude-user')
        for provider, order in (('qwen', 1), ('openrouter', 3), ('anthropic', 4)):
            AIProviderConfig.objects.create(provider=provider, default_model='claude-haiku-5-5' if provider == 'anthropic' else 'm', is_enabled=True, display_order=order)

    def grant(self, resource, view=False, edit=False):
        return UserPermission.objects.create(user=self.user, resource=resource, can_view=view or edit, can_edit=edit)

    def chat_post(self, provider='anthropic'):
        from ai.views import AIChatView
        request = self.factory.post('/', {'message': 'こんにちは', 'provider': provider}, format='json')
        force_authenticate(request, self.user)
        with patch('ai.services.anthropic_client.urlopen') as claude, patch('ai.services.analysis_llm.urlopen') as other, \
                patch.object(chat_service, '_deepseek_agent_chat') as agent:
            response = AIChatView.as_view()(request)
        for mock in (claude, other, agent):
            mock.assert_not_called()
        return response

    def test_chat_post_is_403_without_analysis_edit_even_with_chat(self):
        self.grant('ai.chat', edit=True)
        self.assertEqual(self.chat_post().status_code, 403)
        self.grant('ai.analysis', view=True)  # 閲覧だけでは足りない(分析案の作成=edit水準)
        self.assertEqual(self.chat_post().status_code, 403)

    def test_chat_post_is_400_fixed_message_with_analysis_edit(self):
        self.grant('ai.chat', edit=True)
        self.grant('ai.analysis', edit=True)
        response = self.chat_post()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'Claude は、社内AIチャットではまだ使えません。')

    def test_chat_post_without_chat_permission_is_403_before_everything(self):
        self.grant('ai.analysis', edit=True)
        self.assertEqual(self.chat_post().status_code, 403)

    def test_permission_lookup_failure_is_403_for_anthropic(self):
        self.grant('ai.chat', edit=True)
        real = chat_service._has_resource_permission

        def lookup(user, resource, level='view'):
            if resource == 'ai.analysis':
                raise RuntimeError('SECRET-DB')
            return real(user, resource, level)

        with patch.object(chat_service, '_has_resource_permission', side_effect=lookup):
            response = self.chat_post()
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('SECRET', str(response.data))

    def test_other_providers_are_not_affected_by_the_guard(self):
        self.grant('ai.chat', edit=True)
        self.assertEqual(self.chat_post('unknown').status_code, 400)
        self.assertEqual(self.chat_post('unknown').data['detail'], 'AIモデルの指定が不正です。')

    def test_chat_get_never_lists_anthropic(self):
        from ai.views import AIChatView
        self.grant('ai.chat', edit=True)
        self.grant('ai.analysis', edit=True)
        request = self.factory.get('/')
        force_authenticate(request, self.user)
        with patch.object(chat_service, 'urlopen', side_effect=URLError('x')):
            response = AIChatView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('anthropic', response.data['providers'])
        self.assertIn('openrouter', response.data['providers'])

    def test_analysis_api_rejects_a_chat_only_user_choosing_anthropic(self):
        from ai.views import AIAnalysisPlansView
        self.grant('ai.chat', edit=True)
        request = self.factory.post('/', {**PAYLOAD, 'provider': 'anthropic'}, format='json')
        force_authenticate(request, self.user)
        with patch('ai.services.anthropic_client.urlopen') as claude, patch.object(planning, 'create_plan') as create:
            response = AIAnalysisPlansView.as_view()(request)
        self.assertEqual(response.status_code, 403)
        claude.assert_not_called()
        create.assert_not_called()


class MigrationDataTests(TestCase):
    """データマイグレーション0053の正方向(無効で作成)と逆方向(行の削除)。"""

    def module(self):
        return importlib.import_module('ai.migrations.0053_add_anthropic_provider')

    def test_forward_creates_a_disabled_row_and_reverse_removes_it(self):
        migration = self.module()
        migration.add_anthropic_provider(django_apps, None)
        row = AIProviderConfig.objects.get(provider='anthropic')
        self.assertEqual((row.is_enabled, row.display_order, row.default_model), (False, 4, 'claude-haiku-5-5'))
        AIProviderConfig.objects.create(provider='qwen', default_model='q', is_enabled=True)
        migration.remove_anthropic_provider(django_apps, None)
        self.assertFalse(AIProviderConfig.objects.filter(provider='anthropic').exists())
        self.assertTrue(AIProviderConfig.objects.filter(provider='qwen').exists())  # 他の行は消さない

    def test_dependencies_follow_the_alter_field_migration(self):
        self.assertEqual(self.module().Migration.dependencies, [('ai', '0052_alter_aiproviderconfig_provider_anthropic')])
