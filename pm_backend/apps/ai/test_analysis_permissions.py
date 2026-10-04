"""分析APIの全入口を実ユーザー・実効権限で照合する(一時SQLiteのみ)。"""
import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import UserPermission
from ai import urls, views, analysis_execution_views as executions
from ai.analysis_permissions import CanUseAIAnalysis
from ai.services.analysis_plan_store import AnalysisError


# 仕様書の一覧と同じ。URL集合との一致で、新規APIの検証漏れも検出する。
ENDPOINTS = (
    ('ai-analysis-options', 'get', None),
    ('ai-analysis-plans', 'post', None),
    ('ai-analysis-external-preview', 'post', None),
    ('ai-analysis-plan', 'get', 'plan_id'),
    ('ai-analysis-approve', 'post', 'plan_id'),
    ('ai-analysis-preview', 'post', 'plan_id'),
    ('ai-analysis-codegen-preview', 'post', 'plan_id'),
    ('ai-analysis-codegen', 'post', 'plan_id'),
    ('ai-analysis-codegen-trial', 'post', 'plan_id'),
    ('ai-analysis-codegen-approve', 'post', 'plan_id'),
    ('ai-analysis-codegen-release', 'post', 'plan_id'),
    ('ai-analysis-codegen-refresh-wrapper', 'post', 'plan_id'),
    ('ai-analysis-execution-options', 'get', None),
    ('ai-analysis-execute', 'post', 'plan_id'),
    ('ai-analysis-job', 'get', 'job_id'),
    ('ai-analysis-job-cancel', 'post', 'job_id'),
    ('ai-analysis-runs', 'get', None),
    ('ai-analysis-templates', 'get', None),
    ('ai-analysis-templates', 'post', None),
    ('ai-analysis-template', 'get', 'template_id'),
    ('ai-analysis-template-plans', 'post', 'template_id'),
)
ROUTES = {route.name: route for route in urls.urlpatterns if str(route.pattern).startswith('ai/analysis/')}


@override_settings(ALLOWED_HOSTS=['testserver'])
class AnalysisPermissionsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='analysis-normal-user')
        self.factory = APIRequestFactory()

    def request(self, name, method, argument, user, query=None):
        request = (self.factory.get('/', query or {}) if method == 'get'
                   else self.factory.post('/', {}, format='json'))
        if user is not None:
            force_authenticate(request, user)
        kwargs = {argument: uuid4()} if argument else {}
        return ROUTES[name].callback(request, **kwargs)

    def grant(self, resource='ai.analysis', view=False, edit=False):
        return UserPermission.objects.create(user=self.user, resource=resource, can_view=view, can_edit=edit)

    def test_endpoint_set_and_permission_class_have_no_omissions(self):
        self.assertEqual(set(ROUTES), {row[0] for row in ENDPOINTS})
        self.assertEqual(len(ROUTES), len({row[0] for row in ENDPOINTS}))
        for route in ROUTES.values():
            self.assertIn(CanUseAIAnalysis, route.callback.view_class.permission_classes)

    def test_view_only_get_allowed_post_denied_and_edit_implies_view(self):
        permission = self.grant(view=True)
        for edit in (False, True):
            permission.can_view, permission.can_edit = not edit, edit
            permission.save()
            for name, method, argument in ENDPOINTS:
                with self.subTest(name=name, edit=edit):
                    cls = ROUTES[name].callback.view_class
                    with patch.object(cls, method, return_value=Response({'accepted': True})) as handler:
                        response = self.request(name, method, argument, self.user)
                    allowed = edit or method == 'get'
                    self.assertEqual(response.status_code, 200 if allowed else 403)
                    self.assertEqual(handler.called, allowed)

    def test_parent_chat_settings_and_staff_do_not_grant_analysis(self):
        self.user.is_staff = True
        self.user.save()
        for resource in ('ai', 'ai.chat', 'settings.ai'):
            permission = self.grant(resource, edit=True)
            for name, method, argument in ENDPOINTS:
                with self.subTest(resource=resource, name=name):
                    cls = ROUTES[name].callback.view_class
                    with patch.object(cls, method) as handler:
                        self.assertEqual(self.request(name, method, argument, self.user).status_code, 403)
                    handler.assert_not_called()
            permission.delete()

    def test_superuser_without_profile_is_allowed_at_each_entrance(self):
        self.user.is_superuser = True
        self.user.save()
        for name, method, argument in ENDPOINTS:
            with self.subTest(name=name):
                cls = ROUTES[name].callback.view_class
                with patch.object(cls, method, return_value=Response({'accepted': True})):
                    self.assertEqual(self.request(name, method, argument, self.user).status_code, 200)

    def test_revoked_permission_is_rechecked_for_execution_cancel_and_result(self):
        permission = self.grant(edit=True)
        cases = (('ai-analysis-execute', 'post', 'plan_id'),
                 ('ai-analysis-job-cancel', 'post', 'job_id'),
                 ('ai-analysis-job', 'get', 'job_id'))
        for name, method, argument in cases:
            cls = ROUTES[name].callback.view_class
            with patch.object(cls, method, return_value=Response({'accepted': True})):
                self.assertEqual(self.request(name, method, argument, self.user).status_code, 200)
        permission.delete()
        for name, method, argument in cases:
            cls = ROUTES[name].callback.view_class
            with patch.object(cls, method) as handler:
                self.assertEqual(self.request(name, method, argument, self.user).status_code, 403)
                handler.assert_not_called()

    def test_permission_lookup_failure_is_fixed_403_at_every_entrance(self):
        self.grant(edit=True)
        with patch('ai.analysis_permissions._has_resource_permission', side_effect=RuntimeError('SECRET-DB')):
            for name, method, argument in ENDPOINTS:
                cls = ROUTES[name].callback.view_class
                with self.subTest(name=name), patch.object(cls, method) as handler:
                    response = self.request(name, method, argument, self.user)
                    self.assertEqual(response.status_code, 403)
                    self.assertEqual(str(response.data['detail']), CanUseAIAnalysis.message)
                    self.assertNotIn('SECRET', str(response.data))
                    handler.assert_not_called()

    def test_all_history_requires_analysis_view_and_existing_settings_edit(self):
        permission = self.grant(view=True)
        with patch.object(executions, 'visible_runs', return_value=[]) as visible:
            own = self.request('ai-analysis-runs', 'get', None, self.user)
            self.assertEqual(own.status_code, 200)
            visible.assert_called_once_with(self.user, False)
            visible.reset_mock()
            response = self.request('ai-analysis-runs', 'get', None, self.user, {'include_all': 'true'})
            self.assertEqual(response.status_code, 403)
            visible.assert_not_called()
            self.grant('settings.ai', edit=True)
            self.assertEqual(self.request('ai-analysis-runs', 'get', None, self.user, {'include_all': 'true'}).status_code, 200)
            visible.assert_called_once_with(self.user, True)
            permission.delete()
            visible.reset_mock()
            self.assertEqual(self.request('ai-analysis-runs', 'get', None, self.user, {'include_all': 'true'}).status_code, 403)
            visible.assert_not_called()

    def test_owner_404_is_preserved_after_permission_success(self):
        self.grant(edit=True)
        with patch.object(executions, 'JobStore') as store:
            for name, method, operation in (
                ('ai-analysis-job', 'get', 'get'), ('ai-analysis-job-cancel', 'post', 'cancel'),
            ):
                getattr(store.return_value, operation).side_effect = AnalysisError('実行が見つかりません。', 404)
                self.assertEqual(self.request(name, method, 'job_id', self.user).status_code, 404)
                self.assertEqual(getattr(store.return_value, operation).call_args.args[1], self.user.pk)
        with patch.object(views, 'AnalysisPlanStore') as store:
            store.return_value.get.side_effect = AnalysisError('分析案が見つかりません。', 404)
            self.assertEqual(self.request('ai-analysis-plan', 'get', 'plan_id', self.user).status_code, 404)
            self.assertEqual(store.return_value.get.call_args.args[1], self.user.pk)

    @override_settings(AI_ANALYSIS_REDIS_URL='redis://localhost/0')
    def test_view_only_user_reaches_real_plan_owner_check_and_cannot_post(self):
        self.grant(view=True)
        other = get_user_model().objects.create_user(username='analysis-other-owner')
        plan_id = uuid4()
        plan = {'id': str(plan_id), 'owner_id': self.user.pk,
                'proposal': {'title': '所有者だけに見える分析案'}, 'revision': 1}
        client = MagicMock()
        # Redisの読み取りだけを模擬し、API・資源権限・Store.get/_decodeは実処理を通す。
        with patch('ai.services.analysis_plan_store.Redis.from_url', return_value=client):
            client.get.return_value = json.dumps(plan, ensure_ascii=False)
            request = self.factory.get('/')
            force_authenticate(request, self.user)
            response = ROUTES['ai-analysis-plan'].callback(request, plan_id=plan_id)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['proposal'], plan['proposal'])
            self.assertNotIn('owner_id', response.data)
            client.get.assert_called_once_with(f'pm:ai:analysis:plan:{plan_id}')

            client.get.reset_mock()
            plan['owner_id'] = other.pk
            client.get.return_value = json.dumps(plan, ensure_ascii=False)
            request = self.factory.get('/')
            force_authenticate(request, self.user)
            response = ROUTES['ai-analysis-plan'].callback(request, plan_id=plan_id)
            self.assertEqual(response.status_code, 404)
            self.assertNotIn(plan['proposal']['title'], str(response.data))
            client.get.assert_called_once_with(f'pm:ai:analysis:plan:{plan_id}')

            client.reset_mock()
            plan['owner_id'] = self.user.pk
            client.get.return_value = json.dumps(plan, ensure_ascii=False)
            for name, method, argument in ENDPOINTS:
                if method != 'post':
                    continue
                with self.subTest(name=name):
                    request = self.factory.post('/', {}, format='json')
                    force_authenticate(request, self.user)
                    kwargs = {argument: plan_id if argument == 'plan_id' else uuid4()} if argument else {}
                    response = ROUTES[name].callback(request, **kwargs)
                    self.assertEqual(response.status_code, 403)
                    self.assertEqual(str(response.data['detail']), CanUseAIAnalysis.message)
            # POSTは資源権限で拒否し、他人／自分の判定前にRedisへ触れない。
            self.assertEqual(client.mock_calls, [])


def endpoint_test(name, method, argument):
    def test(self):
        cls = ROUTES[name].callback.view_class
        # 権限・認証を実際に通し、許可時だけ入口の先へ進むことを確認する。
        with patch.object(cls, method, return_value=Response({'accepted': True})) as handler:
            response = self.request(name, method, argument, self.user)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(str(response.data['detail']), CanUseAIAnalysis.message)
            handler.assert_not_called()
            response = self.request(name, method, argument, None)
            self.assertIn(response.status_code, (401, 403))
            handler.assert_not_called()
            self.grant(edit=True)
            self.assertEqual(self.request(name, method, argument, self.user).status_code, 200)
            handler.assert_called_once()
    return test


for _name, _method, _argument in ENDPOINTS:
    setattr(AnalysisPermissionsTests, 'test_endpoint_' + _name.replace('-', '_'),
            endpoint_test(_name, _method, _argument))
