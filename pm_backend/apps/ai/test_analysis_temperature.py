"""分析の温度の設定(AI設定。BOSS承認 2026-10-07)を検証する。取得・範囲・外部AIへの渡し方・分析案の作成での扱い。DBは使わない(模擬)。"""
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db import DatabaseError
from django.test import SimpleTestCase, override_settings

from ai.config.models import AIProviderConfig
from ai.services import analysis_llm
from ai.services.analysis_plan_store import AnalysisError, AnalysisPlanStore
from ai.services.analysis_planning_service import create_plan
from ai.test_analysis_planning import FakeRedis


class GetTemperatureTests(SimpleTestCase):
    def config(self, value):
        return patch.object(AIProviderConfig.objects, 'get', return_value=SimpleNamespace(analysis_temperature=value))

    def test_the_value_of_each_provider_is_read_from_the_setting(self):
        for provider, value, expected in (('openrouter', Decimal('0.00'), 0.0), ('deepseek', Decimal('0.30'), 0.3), ('qwen', Decimal('1.00'), 1.0)):
            with self.subTest(provider=provider), patch.object(AIProviderConfig.objects, 'get', return_value=SimpleNamespace(analysis_temperature=value)) as get:
                self.assertEqual(analysis_llm.get_analysis_temperature(provider), expected)
                get.assert_called_once_with(provider=provider)

    def test_a_missing_row_or_a_database_error_stops_without_a_substitute_value(self):
        for error in (AIProviderConfig.DoesNotExist(), DatabaseError('x')):
            with self.subTest(error=type(error).__name__), patch.object(AIProviderConfig.objects, 'get', side_effect=error):
                with self.assertRaises(AnalysisError) as caught:
                    analysis_llm.get_analysis_temperature('openrouter')
                self.assertEqual(caught.exception.status_code, 503)

    def test_an_out_of_range_value_stops(self):
        for value in (Decimal('-0.01'), Decimal('1.01'), Decimal('5')):
            with self.subTest(value=value), self.config(value):
                with self.assertRaises(AnalysisError) as caught:
                    analysis_llm.get_analysis_temperature('openrouter')
                self.assertEqual(caught.exception.status_code, 503)


class ExternalRequestTests(SimpleTestCase):
    def sent_temperature(self, **kwargs):
        captured = {}

        def fake_urlopen(request, timeout):
            captured['body'] = json.loads(request.data.decode('utf-8'))
            raise TimeoutError()

        agent = {'label': 'OpenRouter', 'api_key': 'k', 'base_url': 'https://example.invalid'}
        with patch.object(analysis_llm, 'external_provider', return_value=agent), patch.object(analysis_llm, 'urlopen', fake_urlopen):
            with self.assertRaises(analysis_llm.chat_service.LocalAIError):
                analysis_llm.request_external_json('openrouter', 'm', [{'role': 'user', 'content': 'a'}], **kwargs)
        return captured['body']['temperature']

    def test_the_given_temperature_is_sent_and_the_default_is_the_old_value(self):
        self.assertEqual(self.sent_temperature(temperature=0.0), 0.0)
        self.assertEqual(self.sent_temperature(temperature=0.55), 0.55)
        self.assertEqual(self.sent_temperature(), 0.3)  # 相談など、設定を使わない呼出しは、従来のまま


@override_settings(AI_ANALYSIS_REDIS_URL='redis://test.invalid/0')
class PlanCreationTests(SimpleTestCase):
    def setUp(self):
        self.redis = FakeRedis()
        for target, kwargs in (('ai.services.analysis_plan_store.Redis.from_url', {'return_value': self.redis}),
                               ('ai.services.analysis_planning_service.get_analysis_execution_policy', {'return_value': SimpleNamespace(plan_cache_ttl_minutes=60, max_fetch_rows=100000)}),
                               ('ai.services.analysis_planning_service.planning_options', {'return_value': {'available': True}}),
                               ('ai.services.analysis_planning_service.get_qwen_analysis_timeout', {'return_value': 240})):
            patcher = patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.raw = json.dumps({'title': 't', 'steps': ['s'], 'outputs': ['o'], 'datasets': [{'view': 'v_ai_shipment', 'fields': ['shipment_date', 'quantity']}]})

    def test_the_local_plan_uses_the_configured_temperature(self):
        with patch.object(analysis_llm, 'get_analysis_temperature', return_value=0.0) as get, \
                patch('ai.services.analysis_planning_service.chat_service._chat', return_value=self.raw) as chat:
            create_plan(3, {'purpose': '出荷の傾向', 'date_from': '2026-09-01', 'date_to': '2026-09-30'})
        get.assert_called_once_with('qwen')
        self.assertEqual(chat.call_args.kwargs['temperature'], 0.0)

    def test_the_external_plan_uses_the_configured_temperature(self):
        from unittest.mock import ANY
        from ai.services import analysis_planning_service as planning
        data = {'purpose': '出荷の傾向', 'date_from': '2026-09-01', 'date_to': '2026-09-30', 'provider': 'openrouter', 'model': 'm', 'external_confirmation': 'ok'}
        with patch.object(planning, 'resolve_planning_provider', return_value=('openrouter', 'm')), patch.object(planning, '_external_purpose', side_effect=lambda text: text),                 patch.object(planning, '_confirmation', return_value='ok'), patch.object(analysis_llm, 'get_analysis_temperature', return_value=0.0) as get,                 patch.object(analysis_llm, 'request_external_json', return_value=self.raw) as external:
            create_plan(3, data)
        get.assert_called_once_with('openrouter')
        self.assertEqual(external.call_args.args, ('openrouter', 'm', ANY, 0.0))

    def test_an_unavailable_setting_stops_an_external_plan_before_sending(self):
        from ai.services import analysis_planning_service as planning
        data = {'purpose': '出荷の傾向', 'date_from': '2026-09-01', 'date_to': '2026-09-30', 'provider': 'openrouter', 'model': 'm', 'external_confirmation': 'ok'}
        with patch.object(planning, 'resolve_planning_provider', return_value=('openrouter', 'm')), patch.object(planning, '_external_purpose', side_effect=lambda text: text),                 patch.object(planning, '_confirmation', return_value='ok'), patch.object(analysis_llm, 'get_analysis_temperature', side_effect=AnalysisError('x', 503)),                 patch.object(analysis_llm, 'request_external_json') as external, self.assertRaises(AnalysisError):
            create_plan(3, data)
        external.assert_not_called()

    def test_an_unavailable_setting_stops_before_the_ai_call_and_saves_nothing(self):
        before = dict(self.redis.values)
        with patch.object(analysis_llm, 'get_analysis_temperature', side_effect=AnalysisError('温度を取得できません', 503)), \
                patch('ai.services.analysis_planning_service.chat_service._chat') as chat, self.assertRaises(AnalysisError) as caught:
            create_plan(3, {'purpose': '出荷の傾向', 'date_from': '2026-09-01', 'date_to': '2026-09-30'})
        self.assertEqual(caught.exception.status_code, 503)
        chat.assert_not_called()
        self.assertEqual(self.redis.values, before)


class LocalQwenTests(SimpleTestCase):
    def sent_options(self, **kwargs):
        from ai.services import chat_service
        captured = {}

        class Response:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return json.dumps({'message': {'content': '{}'}}).encode('utf-8')

        def fake_urlopen(request, timeout):
            captured['options'] = json.loads(request.data.decode('utf-8'))['options']
            return Response()

        with patch.object(chat_service, 'urlopen', fake_urlopen):
            try:
                chat_service._chat([{'role': 'user', 'content': 'a'}], 'qwen', json_mode=True, **kwargs)
            except Exception:
                pass
        return captured['options']['temperature']

    def test_the_local_model_uses_the_given_temperature_and_keeps_the_old_value_otherwise(self):
        self.assertEqual(self.sent_options(temperature=0.0), 0.0)
        self.assertEqual(self.sent_options(temperature=0.4), 0.4)
        self.assertEqual(self.sent_options(), 0.7)  # 指定しない呼出し(検索AIなど)は、従来のまま


class SerializerTests(SimpleTestCase):
    """AI設定APIの入力検証: 0〜1、小数第2位まで。"""

    def validate(self, value):
        from ai.config.serializers import AIProviderConfigSerializer
        serializer = AIProviderConfigSerializer(AIProviderConfig(provider='openrouter', default_model='google/gemma-4-26b-a4b-it'),
                                                data={'analysis_temperature': value}, partial=True)
        return serializer.is_valid(), serializer.errors

    def test_valid_values(self):
        for value in (0, 1, '0.30', 0.5, '0.05'):
            with self.subTest(value=value):
                self.assertTrue(self.validate(value)[0])

    def test_invalid_values(self):
        for value in (-0.01, 1.01, 5, 0.123, 'abc', '', None):
            with self.subTest(value=value):
                valid, errors = self.validate(value)
                self.assertFalse(valid)
                self.assertIn('analysis_temperature', errors)

    def test_the_default_keeps_the_old_behavior(self):
        self.assertEqual(AIProviderConfig._meta.get_field('analysis_temperature').default, Decimal('0.30'))
