"""Qwen専用の分析案作成時間の入力・保存・取得・呼出しを検証する。"""
import json
from unittest.mock import MagicMock, patch

from django.db import DatabaseError
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from ai.config.models import AIProviderConfig
from ai.config.serializers import AIProviderConfigSerializer
from ai.config.views import AIProviderConfigViewSet
from ai.services import chat_service
from ai.services.analysis_plan_store import AnalysisError
from ai.services.analysis_planning_service import get_qwen_analysis_timeout


class QwenAnalysisTimeoutTest(SimpleTestCase):
    def setUp(self):
        self.config = AIProviderConfig(id=2, provider='qwen', default_model=chat_service.MODEL)

    def test_default_and_boundaries(self):
        self.assertEqual(self.config.analysis_plan_timeout_seconds, 180)
        for value in (30, 180, 600):
            serializer = AIProviderConfigSerializer(self.config, data={'analysis_plan_timeout_seconds': value}, partial=True)
            self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_and_external_values_are_rejected(self):
        for value in (0, 29, 601, '', None, True, 180.5, 'NaN'):
            with self.subTest(value=value):
                serializer = AIProviderConfigSerializer(self.config, data={'analysis_plan_timeout_seconds': value}, partial=True)
                self.assertFalse(serializer.is_valid())
                self.assertIn('analysis_plan_timeout_seconds', serializer.errors)
        for provider in ('deepseek', 'openrouter'):
            serializer = AIProviderConfigSerializer(AIProviderConfig(provider=provider),
                data={'analysis_plan_timeout_seconds': 240}, partial=True)
            self.assertFalse(serializer.is_valid())

    def test_api_save_get_and_invalid_atomic_update(self):
        factory = APIRequestFactory()
        view = AIProviderConfigViewSet.as_view({'patch': 'partial_update', 'get': 'retrieve'})
        with patch.object(AIProviderConfigViewSet, 'get_object', return_value=self.config), patch.object(self.config, 'save') as save:
            response = view(factory.patch('/', {'analysis_plan_timeout_seconds': 240}, format='json'), pk=2)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['analysis_plan_timeout_seconds'], 240)
            save.assert_called_once()
            self.assertTrue(self.config.is_enabled)
            self.assertEqual(self.config.default_model, chat_service.MODEL)
            response = view(factory.get('/'), pk=2)
            self.assertEqual(response.data['analysis_plan_timeout_seconds'], 240)
            save.reset_mock()
            response = view(factory.patch('/', {'is_enabled': False, 'analysis_plan_timeout_seconds': 601}, format='json'), pk=2)
            self.assertEqual(response.status_code, 400)
            save.assert_not_called()
            self.assertTrue(self.config.is_enabled)
            self.assertEqual(self.config.analysis_plan_timeout_seconds, 240)

    def test_existing_model_and_enable_update_does_not_reset_timeout(self):
        self.config.analysis_plan_timeout_seconds = 240
        serializer = AIProviderConfigSerializer(self.config, data={'is_enabled': False, 'default_model': chat_service.MODEL}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with patch.object(self.config, 'save'):
            serializer.save()
        self.assertEqual(self.config.analysis_plan_timeout_seconds, 240)

    def test_saved_value_is_read_for_each_new_request(self):
        with patch('ai.services.analysis_planning_service.AIProviderConfig.objects.get', return_value=self.config) as get:
            self.assertEqual(get_qwen_analysis_timeout(), 180)
            self.config.analysis_plan_timeout_seconds = 240
            self.assertEqual(get_qwen_analysis_timeout(), 240)
            self.assertEqual(get.call_count, 2)
            get.assert_called_with(provider='qwen')

    def test_missing_invalid_or_failed_setting_has_no_fallback(self):
        for value in (None, True, 0, 29, 601, 180.5, '180'):
            self.config.analysis_plan_timeout_seconds = value
            with patch('ai.services.analysis_planning_service.AIProviderConfig.objects.get', return_value=self.config):
                with self.assertRaises(AnalysisError) as caught:
                    get_qwen_analysis_timeout()
                self.assertEqual(caught.exception.status_code, 503)
        for error in (DatabaseError(), AIProviderConfig.DoesNotExist()):
            with patch('ai.services.analysis_planning_service.AIProviderConfig.objects.get', side_effect=error):
                with self.assertRaises(AnalysisError) as caught:
                    get_qwen_analysis_timeout()
                self.assertEqual(caught.exception.status_code, 503)

    def test_transport_receives_analysis_timeout_search_default_unchanged(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps({'message': {'content': '回答'}}).encode()
        with patch('ai.services.chat_service.urlopen', return_value=response) as urlopen:
            chat_service._chat([], 'qwen', timeout=240)
            self.assertEqual(urlopen.call_args.kwargs['timeout'], 240)
            chat_service._chat([], 'qwen')
            self.assertEqual(urlopen.call_args.kwargs['timeout'], 90)
