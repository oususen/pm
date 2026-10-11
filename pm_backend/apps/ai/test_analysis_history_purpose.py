"""実行目的の原文保存・既存NULL・履歴API。実データ取得やAI通信は行わない。"""
from importlib import import_module

from django.contrib.auth import get_user_model
from django.db import migrations
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import UserPermission
from ai.analysis_execution_views import AIAnalysisRunsView
from ai.models import AIAnalysisRun
from ai.services import analysis_run_service as runs
from ai.test_analysis_run import BUNDLE, POLICY, make_plan


@override_settings(ALLOWED_HOSTS=['testserver'])
class HistoryPurposeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='purpose-owner')
        UserPermission.objects.create(user=self.user, resource='ai.analysis', can_view=True, can_edit=True)
        self.plan = make_plan({})
        self.plan['proposal'].update(purpose='ACMEの親品を確認する\n<b>原文</b>', external_purpose='CUST-001の親品を確認する')

    def test_start_and_not_run_store_original_purpose_and_return_it_in_the_api(self):
        started = runs.start_run(self.user, self.plan, BUNDLE, POLICY)
        skipped = runs.record_not_run(self.user, self.plan, 'expired', 'plan_expired', POLICY)
        for run in (started, skipped):
            run.refresh_from_db()
            self.assertEqual(run.purpose, self.plan['proposal']['purpose'])
        # 分析案を変更しても、保存済みの履歴を上書きしない。
        self.plan['proposal']['purpose'] = '変更後'
        request = APIRequestFactory().get('/')
        force_authenticate(request, self.user)
        response = AIAnalysisRunsView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row['purpose'] for row in response.data['results']], [started.purpose, skipped.purpose])

    def test_existing_null_is_returned_without_inventing_a_purpose(self):
        run = runs.start_run(self.user, self.plan, BUNDLE, POLICY)
        AIAnalysisRun.objects.filter(pk=run.pk).update(purpose=None)
        run.refresh_from_db()
        self.assertIsNone(runs.serialize_run(run)['purpose'])

    def test_each_not_run_state_keeps_the_purpose(self):
        for status, reason in [('expired', 'plan_expired'), ('cancelled', 'user_cancelled'), ('failed', 'template_unavailable')]:
            with self.subTest(status=status):
                run = runs.record_not_run(self.user, self.plan, status, reason, POLICY)
                run.refresh_from_db()
                self.assertEqual(runs.serialize_run(run)['purpose'], self.plan['proposal']['purpose'])

    def test_migration_only_adds_nullable_text_without_default_or_backfill(self):
        migration = import_module('ai.migrations.0047_aianalysisrun_purpose').Migration
        self.assertEqual(migration.dependencies, [('ai', '0046_ai_department_view')])
        self.assertEqual(len(migration.operations), 1)
        operation = migration.operations[0]
        self.assertIsInstance(operation, migrations.AddField)
        self.assertEqual((operation.model_name, operation.name), ('aianalysisrun', 'purpose'))
        self.assertTrue(operation.field.null)
        self.assertFalse(operation.field.has_default())
