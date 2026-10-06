"""テンプレートの再利用(第3段階3-D): 分析案の作成・状態ごとの可否・実行の受付時と開始前の確認・履歴のテンプレートIDを検証する。

実ユーザー・実効権限・一時SQLiteを使う。Redisの分析案の作成は模擬(作成する内容を記録して検証する)。AI・launcherは呼ばない。
"""
import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from accounts.models import UserPermission
from ai import urls
from ai.models import AIAnalysisRun, AIAnalysisTemplate
from ai.services import analysis_codegen_service as cg
from ai.services import analysis_run_service as runs
from ai.services import analysis_template_reuse_service as reuse
from ai.services import analysis_template_service as service
from ai.services.analysis_plan_store import AnalysisError
from ai.test_analysis_template_review import ReviewBase
from ai.test_analysis_templates import PYTHON, STEPS, VIEWS, make_plan

ROUTES = {route.name: route for route in urls.urlpatterns if getattr(route, 'name', None)}


class FakeStore:
    """分析案の作成だけを記録する(Redisへは書かない)。"""
    created = []

    def check_connection(self):
        pass

    def create(self, owner_id, proposal, ttl_minutes, extra=None):
        plan = {'id': str(uuid4()), 'owner_id': owner_id, 'revision': 1, 'status': 'awaiting_method', 'proposal': proposal,
                'created_at': datetime.now().isoformat(), 'expires_at': (datetime.now() + timedelta(minutes=ttl_minutes)).isoformat(),
                'method_approved_at': None, 'data_approved_at': None, 'preview': None, **(extra or {})}
        FakeStore.created.append((plan, ttl_minutes))
        return plan


class ReuseBase(ReviewBase):
    def setUp(self):
        super().setUp()
        FakeStore.created = []
        for target, value in (('AnalysisPlanStore', FakeStore), ('get_analysis_execution_policy', lambda: SimpleNamespace(plan_cache_ttl_minutes=45))):
            patcher = patch.object(reuse, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        ai = patch.object(cg, '_call_ai')
        self.ai = ai.start()
        self.addCleanup(ai.stop)

    def create_plan(self, user, template, **kwargs):
        return self.call('ai-analysis-template-plans', user, template_id=template.pk, **kwargs)

    def assert_no_plan(self):
        self.assertEqual(FakeStore.created, [])
        self.ai.assert_not_called()

    def row_with(self, **overrides):
        """内容を変えた行(ハッシュも同じ作り方で整える)。"""
        user = overrides.pop('user', self.creator)
        fields = service._fields_from_plan(make_plan(user.pk))
        fields.update({k: v for k, v in overrides.items() if k not in ('status',)})
        fields['content_sha256'] = service._content_sha256(fields)
        return self.row(user, status=overrides.get('status', 'pending_admin'), **fields)


class CreatePlanTests(ReuseBase):
    def test_creates_a_new_plan_owned_by_the_user_from_an_approved_template_without_calling_the_ai(self):
        template = self.row(status='approved')
        response = self.create_plan(self.other, template)
        self.assertEqual(response.status_code, 201)
        plan, ttl = FakeStore.created[0]
        bundle = cg.make_bundle(STEPS, PYTHON, VIEWS)
        self.assertEqual((plan['owner_id'], plan['status'], ttl), (self.other.pk, 'awaiting_method', 45))
        self.assertEqual((plan['method_approved_at'], plan['data_approved_at'], plan['preview']), (None, None, None))  # 過去の承認・件数は持ち込まない
        self.assertEqual(plan['proposal']['provider'], 'template')
        self.assertEqual((plan['proposal']['title'], plan['proposal']['date_from'], plan['proposal']['date_to']), (template.name, '2026-01-01', '2026-01-31'))
        self.assertEqual(plan['proposal']['materials'], [])
        self.assertEqual(plan['template'], {'id': template.pk, 'version': 1, 'family_id': str(template.family_id), 'name': template.name,
                                            'status': 'approved', 'content_sha256': template.content_sha256, 'values': {}})
        codegen = plan['codegen']
        self.assertEqual((codegen['status'], codegen['attempts'], codegen['trial'], codegen['inflight']), ('generated', 0, None, None))
        self.assertEqual((codegen['steps'], codegen['python'], codegen['executed_code_sha256'], codegen['wrapper_version']),
                         (STEPS, PYTHON, bundle.executed_code_sha256, bundle.wrapper_version))
        self.assertNotIn('owner_id', response.data)
        self.assertEqual((response.data['template']['id'], response.data['codegen_state']['status']), (template.pk, 'generated'))
        self.ai.assert_not_called()

    def test_reusable_range_by_status_and_user(self):
        approved, pending, rejected, superseded = (self.row(status=s) for s in ('approved', 'pending_admin', 'rejected', 'superseded'))
        expected = {
            # (ユーザー, テンプレート) → 応答
            ('creator', 'approved'): 201, ('other', 'approved'): 201, ('admin', 'approved'): 201,
            ('creator', 'pending'): 201, ('admin', 'pending'): 201, ('other', 'pending'): 403,
            ('creator', 'rejected'): 409, ('admin', 'rejected'): 409, ('other', 'rejected'): 404,
            ('creator', 'superseded'): 409, ('admin', 'superseded'): 409, ('other', 'superseded'): 404,
        }
        users = {'creator': self.creator, 'other': self.other, 'admin': self.admin}
        rows = {'approved': approved, 'pending': pending, 'rejected': rejected, 'superseded': superseded}
        for (who, which), status in expected.items():
            with self.subTest(who=who, which=which):
                self.assertEqual(self.create_plan(users[who], rows[which]).status_code, status)
        self.assertEqual(len(FakeStore.created), sum(1 for status in expected.values() if status == 201))

    def test_unknown_template_view_only_user_and_body_are_refused(self):
        template = self.row(status='approved')
        self.assertEqual(self.call('ai-analysis-template-plans', self.other, template_id=999999).status_code, 404)
        UserPermission.objects.filter(user=self.other, resource='ai.analysis').update(can_edit=False)
        self.assertEqual(self.create_plan(self.other, template).status_code, 403)
        self.assertEqual(self.create_plan(None, template).status_code, 403)
        self.assertEqual(self.create_plan(self.creator, template, data={'revision': 1}).status_code, 400)
        self.assert_no_plan()

    def test_old_wrapper_is_rebuilt_with_the_current_wrapper_and_needs_a_new_trial(self):
        template = self.row_with(wrapper_version='old-wrapper', status='approved')
        self.assertEqual(self.create_plan(self.other, template).status_code, 201)
        plan = FakeStore.created[0][0]
        self.assertEqual(plan['codegen']['wrapper_version'], cg.WRAPPER_VERSION)
        self.assertNotEqual(plan['codegen']['wrapper_version'], template.wrapper_version)
        self.assertIsNone(plan['codegen']['trial'])
        self.assertEqual(plan['codegen']['executed_code_sha256'], cg.make_bundle(STEPS, PYTHON, VIEWS).executed_code_sha256)

    def test_refuses_tampered_invalid_or_no_longer_public_templates_with_fixed_409(self):
        template = self.row(status='approved')
        AIAnalysisTemplate.objects.filter(pk=template.pk).update(python_code=PYTHON + '\n# 改変')
        self.assertEqual(self.create_plan(self.other, template).status_code, 409)  # ハッシュの不一致
        cond = self.row(status='approved')
        AIAnalysisTemplate.objects.filter(pk=cond.pk).update(conditions='承認後に書き換えた条件')
        self.assertEqual(self.create_plan(self.other, cond).status_code, 409)  # コード以外の項目の改変(content_sha256だけが検出する)
        good = self.row(status='approved')
        with patch.object(reuse, 'validate_generated', return_value=['python:forbidden_name']):
            response = self.create_plan(self.other, good)
        self.assertEqual(response.status_code, 409)
        self.assertNotIn('forbidden_name', json.dumps(response.data, ensure_ascii=False))
        with patch.object(reuse, 'validate_datasets', side_effect=AnalysisError('SECRET-DETAIL')):
            response = self.create_plan(self.other, good)
        self.assertEqual(response.status_code, 409)
        self.assertNotIn('SECRET', json.dumps(response.data, ensure_ascii=False))
        with patch.object(reuse, 'make_bundle', return_value=SimpleNamespace(sql_sha256='x', python_sha256='y')):
            self.assertEqual(self.create_plan(self.other, good).status_code, 409)  # SQL・Pythonのハッシュの不一致
        self.assert_no_plan()

    def test_approved_review_information_stays_with_the_creator_and_admins(self):
        approved = self.row(status='pending_admin')
        self.assertEqual(self.reject(self.admin, approved).status_code, 200)
        plan = make_plan(self.admin.pk, revision=2)
        correction = AIAnalysisTemplate.objects.get(pk=self.save_correction(self.admin, approved, plan=plan).data['id'])
        self.assertEqual(self.approve(self.admin2, correction).status_code, 200)
        # 訂正版の作成者は管理者(admin)。元の作成者(creator)も、この行の作成者ではないので、確認情報は出ない
        for user, review in ((self.other, False), (self.creator, False), (self.admin, True), (self.admin2, True)):
            with self.subTest(user=user.username):
                data = self.call('ai-analysis-template', user, 'get', template_id=correction.pk).data
                self.assertTrue(data['content_visible'])
                self.assertEqual(data['python_code'], PYTHON)  # 正式の全文は全員に表示
                for key in ('reviewed_by', 'reviewed_at', 'rejection_reason', 'state_revision', 'replaces', 'replacement_id'):
                    self.assertEqual(key in data, review, key)

    def test_approved_template_content_is_visible_to_all_analysis_users_but_pending_stays_restricted(self):
        approved, pending = self.row(status='approved'), self.row(status='pending_admin')
        data = self.call('ai-analysis-template', self.other, 'get', template_id=approved.pk).data
        self.assertEqual((data['content_visible'], data['python_code']), (True, PYTHON))
        self.assertTrue([i for i in self.call('ai-analysis-templates', self.other, 'get').data['results'] if i['id'] == approved.pk][0]['content_visible'])
        hidden = self.call('ai-analysis-template', self.other, 'get', template_id=pending.pk).data
        self.assertFalse(hidden['content_visible'])
        self.assertNotIn('python_code', hidden)


class CheckPlanTemplateTests(ReuseBase):
    def plan_for(self, template):
        self.assertEqual(self.create_plan(self.creator, template).status_code, 201)
        return FakeStore.created[-1][0]

    def test_plain_plans_are_unaffected_and_confirmation_without_template_is_refused(self):
        self.assertIsNone(reuse.check_plan_template({'id': 'x'}, self.creator, accepting=True))
        with self.assertRaises(AnalysisError) as raised:
            reuse.check_plan_template({'id': 'x'}, self.creator, 5, accepting=True)
        self.assertEqual(raised.exception.status_code, 400)

    def test_approved_template_needs_no_confirmation(self):
        template = self.row(status='approved')
        plan = self.plan_for(template)
        self.assertEqual(reuse.check_plan_template(plan, self.creator, accepting=True).pk, template.pk)
        self.assertEqual(reuse.check_plan_template(plan, self.creator, template.pk, accepting=True).pk, template.pk)
        for bad in (template.pk + 1, True, str(template.pk)):
            with self.subTest(bad=bad), self.assertRaises(AnalysisError) as raised:
                reuse.check_plan_template(plan, self.creator, bad, accepting=True)
            self.assertEqual(raised.exception.status_code, 400)

    def test_unapproved_template_needs_the_confirmation_bound_to_its_id(self):
        template, other_template = self.row(status='pending_admin'), self.row(status='pending_admin')
        plan = self.plan_for(template)
        for confirmed in (None, other_template.pk, True, str(template.pk), 0):
            with self.subTest(confirmed=confirmed), self.assertRaises(AnalysisError) as raised:
                reuse.check_plan_template(plan, self.creator, confirmed, accepting=True)
            self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(reuse.check_plan_template(plan, self.creator, template.pk, accepting=True).pk, template.pk)
        # ワーカーの開始前は、受付時に確認済みなので、状態・内容だけを見る
        self.assertEqual(reuse.check_plan_template(plan, self.creator, accepting=False).pk, template.pk)

    def test_template_that_became_unavailable_after_the_plan_was_created_is_refused(self):
        template = self.row(status='pending_admin')
        plan = self.plan_for(template)
        for status in ('rejected', 'superseded'):
            AIAnalysisTemplate.objects.filter(pk=template.pk).update(status=status)
            for accepting in (True, False):
                with self.subTest(status=status, accepting=accepting), self.assertRaises(reuse.TemplateUnavailable) as raised:
                    reuse.check_plan_template(plan, self.creator, template.pk, accepting=accepting)
                self.assertEqual((raised.exception.status_code, raised.exception.reason), (409, 'template_unavailable'))
        AIAnalysisTemplate.objects.filter(pk=template.pk).update(status='approved', content_sha256='0' * 64)
        with self.assertRaises(reuse.TemplateUnavailable):
            reuse.check_plan_template(plan, self.creator, accepting=False)
        AIAnalysisTemplate.objects.filter(pk=template.pk).delete()
        with self.assertRaises(reuse.TemplateUnavailable):
            reuse.check_plan_template(plan, self.creator, accepting=False)

    def test_approval_after_plan_creation_keeps_the_plan_valid_and_needs_no_confirmation(self):
        template = self.row(status='pending_admin')
        plan = self.plan_for(template)
        self.assertEqual(self.approve(self.admin, template).status_code, 200)
        self.assertEqual(reuse.check_plan_template(plan, self.creator, accepting=True).status, 'approved')

    def test_user_who_lost_access_to_an_unapproved_template_is_refused(self):
        template = self.row(status='pending_admin')
        plan = self.plan_for(template)
        with self.assertRaises(reuse.TemplateUnavailable):
            reuse.check_plan_template(plan, self.other, template.pk, accepting=True)


class RunHistoryAndExecuteTests(ReuseBase):
    def test_start_run_and_not_run_records_keep_the_template_id_and_version(self):
        policy = SimpleNamespace(max_memory_mb=512, max_cpu_cores=1, max_execution_seconds=60, max_fetch_rows=100000, plan_cache_ttl_minutes=60)
        bundle = cg.make_bundle(STEPS, PYTHON, VIEWS)
        plan = {**make_plan(self.creator.pk), 'template': {'id': 42, 'version': 3}}
        plan['preview'] = {'datasets': [{'view': 'v_ai_shipment', 'rows': 3}], 'total_rows': 3}
        run = runs.start_run(self.creator, plan, bundle, policy)
        self.assertEqual((run.template_id, run.template_version), (42, 3))
        skipped = runs.record_not_run(self.creator, plan, 'failed', 'template_unavailable', policy)
        self.assertEqual((skipped.template_id, skipped.template_version, skipped.reason), (42, 3, 'template_unavailable'))
        self.assertEqual(skipped.detail, 'テンプレートが再利用できない状態になったため、実行しませんでした。')
        plain = runs.start_run(self.creator, make_plan(self.creator.pk), bundle, policy)
        self.assertEqual((plain.template_id, plain.template_version), (None, None))
        self.assertEqual(AIAnalysisRun.objects.count(), 3)

    def test_execute_view_accepts_only_the_known_bodies_and_passes_the_confirmation(self):
        from ai import analysis_execution_views as views
        body = {'revision': 2, 'executed_code_sha256': 'a' * 64}
        cases = ((body, None), ({**body, 'template_confirmed': 7}, 7))
        for data, confirmed in cases:
            with self.subTest(data=data), patch.object(views.JobStore, 'submit', return_value={'id': 'job'}) as submit, \
                    patch.object(views, 'execution_enabled', create=True):
                response = self.call('ai-analysis-execute', self.creator, data=data, plan_id=uuid4())
                self.assertEqual(response.status_code, 202)
                self.assertEqual(submit.call_args.args[-1], confirmed)
        for bad in ({'revision': 2}, {**body, 'extra': 1}, {**body, 'template_confirmed': 1, 'extra': 1}):
            with self.subTest(bad=bad), patch.object(views.JobStore, 'submit') as submit:
                self.assertEqual(self.call('ai-analysis-execute', self.creator, data=bad, plan_id=uuid4()).status_code, 400)
                submit.assert_not_called()


class NoSaveFromTemplatePlanTests(ReuseBase):
    def test_template_derived_plan_cannot_be_saved_as_a_template_and_creates_no_duplicate(self):
        template = self.row(status='approved')
        self.assertEqual(self.create_plan(self.other, template).status_code, 201)
        plan = {**FakeStore.created[0][0], 'status': 'data_approved', 'owner_id': self.other.pk}
        plan['codegen'] = {**plan['codegen'], 'status': 'code_approved'}
        plan['method_approved_at'] = plan['data_approved_at'] = datetime.now().isoformat()
        plan['codegen']['code_approved_at'] = datetime.now().isoformat()
        before = AIAnalysisTemplate.objects.count()
        with patch.object(service.AnalysisPlanStore, 'get', lambda _s, pid, owner: json.loads(json.dumps(plan))):
            response = self.call('ai-analysis-templates', self.other, 'post', {'plan_id': plan['id'], 'category': 'shipment', 'revision': plan['revision']})
            # 管理者の訂正版としての保存も同じ(内容が同じで意味がない)
            rejected = self.row(status='rejected')
            correction = self.call('ai-analysis-templates', self.admin, 'post', {'plan_id': plan['id'], 'category': 'shipment', 'revision': plan['revision'], 'replaces': rejected.pk})
        self.assertEqual((response.status_code, correction.status_code), (409, 409))
        self.assertNotIn('Traceback', json.dumps(response.data, ensure_ascii=False))
        self.assertEqual(AIAnalysisTemplate.objects.count(), before + 1)  # rejected行を作った1件だけ。保存は増えていない

    def test_plain_plan_is_still_saved(self):
        plan = make_plan(self.creator.pk)
        with patch.object(service.AnalysisPlanStore, 'get', lambda _s, pid, owner: json.loads(json.dumps(plan))):
            response = self.call('ai-analysis-templates', self.creator, 'post', {'plan_id': plan['id'], 'category': 'shipment', 'revision': plan['revision']})
        self.assertEqual(response.status_code, 201)


class NoRegenerationTests(ReuseBase):
    def test_code_generation_and_its_preview_are_refused_for_template_plans_without_calling_the_ai(self):
        plan = {**make_plan(self.creator.pk), 'template': {'id': 1, 'version': 1}, 'status': 'data_approved'}
        store = SimpleNamespace(get=lambda plan_id, owner_id: plan, check_connection=lambda: None)
        with patch.object(cg, 'AnalysisPlanStore', return_value=store):
            for call in (lambda: cg.generate(self.creator.pk, plan['id'], plan['revision'], 'x'), lambda: cg.preview(self.creator.pk, plan['id'], plan['revision'])):
                with self.assertRaises(AnalysisError) as raised:
                    call()
                self.assertEqual(raised.exception.status_code, 409)
        self.ai.assert_not_called()
