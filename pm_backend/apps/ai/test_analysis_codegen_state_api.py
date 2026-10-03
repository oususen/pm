"""2-C前半: 状態の再取得に、サーバーが判定した生成状態を含める。DB・AIは呼ばない。"""
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ai.services.analysis_plan_store import AnalysisError
from ai.services import analysis_codegen_service as cg
from ai.views import AIAnalysisPlanView, AIAnalysisPlansView, AIAnalysisApproveView, AIAnalysisPreviewView


class CodegenStateAPITests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(pk=987002, is_authenticated=True)
        self.plan = {'id': 'test-plan', 'owner_id': self.user.pk, 'revision': 3, 'status': 'data_approved',
                     'proposal': {'provider': 'deepseek'}}
        self.factory = APIRequestFactory()

    def request(self, view, data=None, plan_id=True):
        request = self.factory.get('/') if data is None else self.factory.post('/', data, format='json')
        force_authenticate(request, self.user)
        return view.as_view()(request, **({'plan_id': self.plan['id']} if plan_id else {}))

    def test_get_state_has_no_owner_and_uses_server_attempt_limit(self):
        with patch('ai.views.AnalysisPlanStore') as store:
            store.return_value.get.return_value = self.plan
            response = self.request(AIAnalysisPlanView)
            store.return_value.get.assert_called_once_with('test-plan', self.user.pk)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('owner_id', response.data)
        self.assertEqual(response.data['codegen_state']['status'], 'none')
        self.assertEqual(response.data['codegen_state']['max_attempts'], cg.MAX_GENERATIONS)

    def test_get_distinguishes_running_from_unknown_without_releasing(self):
        now = datetime(2026, 10, 4, 12, 0, 0)
        with patch.object(cg, 'datetime') as clock, patch.object(cg, 'get_qwen_analysis_timeout', return_value=240):
            clock.now.return_value = now
            clock.fromisoformat.side_effect = datetime.fromisoformat
            for provider in ('deepseek', 'qwen'):
                self.plan['proposal']['provider'] = provider
                limit = cg.inflight_limit_seconds(provider)
                for seconds, expected in [(limit - 1, 'running'), (limit, 'running'), (limit + 1, 'unknown')]:
                    with self.subTest(provider=provider, seconds=seconds):
                        self.plan['codegen'] = {'status': 'generating', 'attempts': 2,
                                                'inflight': {'started_at': (now - timedelta(seconds=seconds)).isoformat()}}
                        with patch('ai.views.AnalysisPlanStore') as store:
                            store.return_value.get.return_value = self.plan
                            response = self.request(AIAnalysisPlanView)
                            store.return_value.update.assert_not_called()
                        self.assertEqual(response.data['codegen_state']['inflight_state'], expected)
                        self.assertEqual(response.data['codegen_state']['attempts'], 2)

    def test_expired_plan_is_not_recreated(self):
        with patch('ai.views.AnalysisPlanStore') as store:
            store.return_value.get.side_effect = AnalysisError('期限切れ', 410)
            response = self.request(AIAnalysisPlanView)
            store.return_value.update.assert_not_called()
        self.assertEqual(response.status_code, 410)

    def test_other_owner_is_not_given_state(self):
        with patch('ai.views.AnalysisPlanStore') as store:
            store.return_value.get.side_effect = AnalysisError('見つかりません', 404)
            response = self.request(AIAnalysisPlanView)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('codegen_state', response.data)

    def test_planning_responses_also_include_initial_codegen_state(self):
        cases = [(AIAnalysisPlansView, 'create_plan', {'purpose': '分析'}, False, 201),
                 (AIAnalysisApproveView, 'approve_plan', {'revision': 3, 'stage': 'data'}, True, 200),
                 (AIAnalysisPreviewView, 'preview_plan', {'revision': 3}, True, 200)]
        for view, operation, data, plan_id, status in cases:
            with patch(f'ai.views.{operation}', return_value=self.plan), patch('ai.views.AnalysisPlanStore'):
                response = self.request(view, data, plan_id)
            self.assertEqual(response.status_code, status)
            self.assertEqual(response.data['codegen_state']['attempts'], 0)
            self.assertNotIn('owner_id', response.data)
