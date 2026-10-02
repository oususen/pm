"""分析実行設定の入力境界と、不正な要求による設定変更を防ぐ検証。"""
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from ai.config.models import AIAnalysisExecutionPolicy
from ai.config.serializers import AIAnalysisExecutionPolicySerializer
from ai.config.views import AIAnalysisExecutionPolicyView


class AnalysisExecutionPolicyTest(SimpleTestCase):
    defaults = {
        'plan_cache_ttl_minutes': 60,
        'max_execution_seconds': 300,
        'max_memory_mb': 2048,
        'max_cpu_cores': '1.0',
        'max_fetch_rows': 100000,
    }

    def test_default_and_boundary_values_are_valid(self):
        for payload in (
            self.defaults,
            dict(zip(self.defaults, (5, 30, 512, '0.5', 1000))),
            dict(zip(self.defaults, (480, 600, 4096, '2.0', 100000))),
        ):
            with self.subTest(payload=payload):
                serializer = AIAnalysisExecutionPolicySerializer(data=payload)
                self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_ranges_steps_and_empty_values_are_rejected(self):
        invalid_values = {
            'plan_cache_ttl_minutes': (4, 481, 60.5),
            'max_execution_seconds': (29, 601, 300.5),
            'max_memory_mb': (511, 4097, 513),
            'max_cpu_cores': ('0.4', '2.5', '1.1', '1.05', 'NaN', 'Infinity'),
            'max_fetch_rows': (999, 100001, 1001),
        }
        for field, values in invalid_values.items():
            for value in (*values, 0, '', None, True):
                with self.subTest(field=field, value=value):
                    serializer = AIAnalysisExecutionPolicySerializer(data={**self.defaults, field: value})
                    self.assertFalse(serializer.is_valid())
                    self.assertIn(field, serializer.errors)
            with self.subTest(field=field, missing=True):
                serializer = AIAnalysisExecutionPolicySerializer(data={key: value for key, value in self.defaults.items() if key != field})
                self.assertFalse(serializer.is_valid())
                self.assertIn(field, serializer.errors)

    def test_get_and_put_return_the_same_settings_row(self):
        policy = AIAnalysisExecutionPolicy(id=1, **self.defaults)
        factory = APIRequestFactory()
        with patch('ai.config.views.get_analysis_execution_policy', return_value=policy), patch.object(policy, 'save') as save:
            get_response = AIAnalysisExecutionPolicyView.as_view()(factory.get('/'))
            self.assertEqual(get_response.status_code, 200)
            self.assertEqual(get_response.data['max_fetch_rows'], 100000)
            response = AIAnalysisExecutionPolicyView.as_view()(factory.put(
                '/', {**self.defaults, 'max_fetch_rows': 20000, 'max_cpu_cores': '1.5', 'id': 99}, format='json',
            ))
            self.assertEqual(response.status_code, 200)
            save.assert_called_once()
            self.assertEqual(policy.pk, 1)
            self.assertEqual(policy.max_fetch_rows, 20000)
            self.assertEqual(policy.max_cpu_cores, Decimal('1.5'))

    def test_invalid_put_does_not_save_or_change_other_fields(self):
        policy = AIAnalysisExecutionPolicy(id=1, **self.defaults)
        with patch('ai.config.views.get_analysis_execution_policy', return_value=policy), patch.object(policy, 'save') as save:
            response = AIAnalysisExecutionPolicyView.as_view()(APIRequestFactory().put(
                '/', {**self.defaults, 'max_execution_seconds': 400, 'max_memory_mb': 513}, format='json',
            ))
            self.assertEqual(response.status_code, 400)
            self.assertIn('max_memory_mb', response.data)
            save.assert_not_called()
            self.assertEqual(policy.max_execution_seconds, 300)
            self.assertEqual(policy.max_memory_mb, 2048)
