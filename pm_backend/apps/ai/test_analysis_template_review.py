"""テンプレートの管理者による承認・却下・訂正版(第3段階3-B)を、実ユーザー・実効権限・一時SQLiteで検証する。

通知(3-C)・再利用(3-D)は対象外。Redisの分析案は、読み取りだけを差し替える(保存・権限・状態遷移は実処理)。
"""
import json
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import UserPermission
from ai import urls
from ai.models import AIAnalysisTemplate
from ai.services import analysis_template_review_service as review
from ai.services import analysis_template_service as service
from ai.services.analysis_plan_store import AnalysisPlanStore
from ai.test_analysis_templates import make_plan

ROUTES = {route.name: route for route in urls.urlpatterns if getattr(route, 'name', None)}
SECRET_REASON = '却下理由の内容ＡＢＣ'


@override_settings(ALLOWED_HOSTS=['testserver'])
class ReviewBase(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.creator = users.create_user(username='rv-creator')
        self.other = users.create_user(username='rv-other')
        self.admin = users.create_user(username='rv-admin')
        self.admin2 = users.create_user(username='rv-admin2')
        for user in (self.creator, self.other, self.admin, self.admin2):
            UserPermission.objects.create(user=user, resource='ai.analysis', can_view=True, can_edit=True)
        for user in (self.admin, self.admin2):
            UserPermission.objects.create(user=user, resource='settings.ai', can_view=True, can_edit=True)
        self.factory = APIRequestFactory()

    def call(self, name, user, method='post', data=None, **kwargs):
        request = self.factory.get('/', data or {}) if method == 'get' else self.factory.post('/', data or {}, format='json')
        if user is not None:
            force_authenticate(request, user)
        return ROUTES[name].callback(request, **kwargs)

    def row(self, user=None, **overrides):
        user = user or self.creator
        fields = service._fields_from_plan(make_plan(user.pk))
        values = {'family_id': uuid4(), 'version': 1, 'source_plan_id': str(uuid4()), 'source_plan_revision': 1,
                  'approved_by': user, **fields}
        values.update(overrides)
        return AIAnalysisTemplate.objects.create(**values)

    def approve(self, user, row, revision=None):
        return self.call('ai-analysis-template-approve', user, data={'state_revision': row.state_revision if revision is None else revision}, template_id=row.pk)

    def reject(self, user, row, reason=SECRET_REASON, revision=None):
        return self.call('ai-analysis-template-reject', user, data={'state_revision': row.state_revision if revision is None else revision, 'reason': reason}, template_id=row.pk)

    def save_correction(self, user, old, plan=None, **overrides):
        plan = plan or make_plan(user.pk, revision=2)
        plan['proposal'] = {**plan['proposal'], 'title': '訂正した分析', **overrides}
        with patch.object(service.AnalysisPlanStore, 'get', lambda _s, pid, owner: AnalysisPlanStore._decode(json.dumps(plan), owner)):
            return self.call('ai-analysis-templates', user, data={'plan_id': plan['id'], 'revision': plan['revision'], 'replaces': old.pk})


class PermissionTests(ReviewBase):
    def test_only_settings_ai_edit_can_approve_or_reject(self):
        row = self.row()
        for label, user in (('creator', self.creator), ('other', self.other), ('anonymous', None)):
            for action in (self.approve, self.reject):
                with self.subTest(label=label, action=action.__name__):
                    response = action(user, row)
                    self.assertEqual(response.status_code, 403 if user else 403)
        row.refresh_from_db()
        self.assertEqual((row.status, row.state_revision), ('pending_admin', 1))

    def test_view_only_settings_ai_and_lookup_failure_are_denied_with_fixed_text(self):
        row = self.row()
        UserPermission.objects.filter(user=self.admin2, resource='settings.ai').update(can_edit=False)
        self.assertEqual(self.approve(self.admin2, row).status_code, 403)
        with patch('ai.analysis_permissions._has_resource_permission', side_effect=RuntimeError('SECRET-DB')):
            response = self.approve(self.admin, row)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('SECRET', json.dumps(response.data, ensure_ascii=False))
        row.refresh_from_db()
        self.assertEqual(row.status, 'pending_admin')

    def test_ai_analysis_edit_alone_does_not_grant_review_even_for_own_template(self):
        row = self.row(self.creator)
        self.assertEqual(self.approve(self.creator, row).status_code, 403)
        self.assertEqual(self.reject(self.creator, row).status_code, 403)

    def test_review_routes_are_exactly_the_two_admin_endpoints(self):
        names = {name for name in ROUTES if name in ('ai-analysis-template-approve', 'ai-analysis-template-reject')}
        self.assertEqual(names, {'ai-analysis-template-approve', 'ai-analysis-template-reject'})
        for name in names:
            from ai.analysis_permissions import CanReviewAITemplates
            self.assertIn(CanReviewAITemplates, ROUTES[name].callback.view_class.permission_classes)


class ApproveRejectTests(ReviewBase):
    def test_approve_sets_status_reviewer_and_revision(self):
        row = self.row()
        response = self.approve(self.admin, row)
        self.assertEqual(response.status_code, 200)
        row.refresh_from_db()
        self.assertEqual((row.status, row.state_revision, row.reviewed_by_id), ('approved', 2, self.admin.pk))
        self.assertIsNotNone(row.reviewed_at)
        self.assertEqual((response.data['status'], response.data['reviewed_by']), ('approved', 'rv-admin'))

    def test_admin_may_approve_a_template_created_by_the_same_admin_and_it_is_recorded(self):
        row = self.row(self.admin)
        self.assertEqual(self.approve(self.admin, row).status_code, 200)
        row.refresh_from_db()
        self.assertEqual((row.approved_by_id, row.reviewed_by_id), (self.admin.pk, self.admin.pk))

    def test_reject_requires_a_reason_within_the_limit_and_stores_it(self):
        row = self.row()
        for bad in ('', '   ', None, 123, 'あ' * (review.REJECTION_REASON_MAX + 1)):
            with self.subTest(bad=bad):
                self.assertEqual(self.reject(self.admin, row, reason=bad).status_code, 400)
        row.refresh_from_db()
        self.assertEqual((row.status, row.rejection_reason), ('pending_admin', ''))
        response = self.reject(self.admin, row, reason='あ' * review.REJECTION_REASON_MAX)
        self.assertEqual(response.status_code, 200)
        row.refresh_from_db()
        self.assertEqual((row.status, row.state_revision, row.reviewed_by_id), ('rejected', 2, self.admin.pk))
        self.assertEqual(len(row.rejection_reason), review.REJECTION_REASON_MAX)

    def test_stale_revision_wrong_status_and_unknown_template_are_rejected_without_changes(self):
        row = self.row()
        self.assertEqual(self.approve(self.admin, row, revision=5).status_code, 409)
        self.assertEqual(self.reject(self.admin, row, revision=0).status_code, 400)
        self.assertEqual(self.approve(self.admin, row, revision=True).status_code, 400)
        self.assertEqual(self.call('ai-analysis-template-approve', self.admin, data={'state_revision': 1}, template_id=999999).status_code, 404)
        self.assertEqual(self.approve(self.admin, row).status_code, 200)
        # 正式になった後は、承認も却下もできない(取り消しは3-Bの対象外)
        row.refresh_from_db()
        self.assertEqual(self.approve(self.admin2, row).status_code, 409)
        self.assertEqual(self.reject(self.admin2, row).status_code, 409)
        row.refresh_from_db()
        self.assertEqual((row.status, row.state_revision, row.reviewed_by_id, row.rejection_reason), ('approved', 2, self.admin.pk, ''))

    def test_request_bodies_are_strict(self):
        row = self.row()
        for body in ({}, {'state_revision': 1, 'extra': 1}, {'revision': 1}):
            self.assertEqual(self.call('ai-analysis-template-approve', self.admin, data=body, template_id=row.pk).status_code, 400)
        for body in ({'state_revision': 1}, {'state_revision': 1, 'reason': 'x', 'extra': 1}):
            self.assertEqual(self.call('ai-analysis-template-reject', self.admin, data=body, template_id=row.pk).status_code, 400)

    def test_approval_and_rejection_race_only_one_succeeds(self):
        """同じ版を見た2人の操作のうち、先に成立した方だけが有効。後の操作は何も変えない。"""
        row = self.row()
        stale = review._target(row.pk, row.state_revision)
        self.assertEqual(self.reject(self.admin, row).status_code, 200)
        # 先の確認で状態を読んだ後に、他の操作が成立したときの条件付き更新(_target通過後の競合)を再現する
        with patch.object(review, '_target', return_value=stale):
            response = self.approve(self.admin2, row)
        self.assertEqual(response.status_code, 409)
        row.refresh_from_db()
        self.assertEqual((row.status, row.reviewed_by_id), ('rejected', self.admin.pk))

    def test_hash_mismatch_blocks_approval(self):
        row = self.row()
        AIAnalysisTemplate.objects.filter(pk=row.pk).update(python_code=row.python_code + '\n# 改変')
        response = self.approve(self.admin, row)
        self.assertEqual(response.status_code, 409)
        row.refresh_from_db()
        self.assertEqual(row.status, 'pending_admin')

    def test_rejection_reason_is_visible_only_to_creator_and_admins(self):
        row = self.row()
        self.assertEqual(self.reject(self.admin, row).status_code, 200)
        for user, visible in ((self.creator, True), (self.admin2, True), (self.admin, True)):
            detail = self.call('ai-analysis-template', user, 'get', template_id=row.pk)
            self.assertEqual((detail.status_code, detail.data['rejection_reason'], detail.data['reviewed_by']), (200, SECRET_REASON, 'rv-admin'))
            listing = [item for item in self.call('ai-analysis-templates', user, 'get').data['results'] if item['id'] == row.pk][0]
            self.assertNotIn('rejection_reason', listing)
        # 却下された版は、他の利用者には存在しない
        self.assertEqual(self.call('ai-analysis-template', self.other, 'get', template_id=row.pk).status_code, 404)
        self.assertNotIn(SECRET_REASON, json.dumps(self.call('ai-analysis-templates', self.other, 'get').data, ensure_ascii=False))

    def test_pending_row_does_not_expose_review_fields_to_others(self):
        row = self.row()
        data = self.call('ai-analysis-template', self.other, 'get', template_id=row.pk).data
        for key in ('rejection_reason', 'reviewed_by', 'reviewed_at', 'state_revision', 'replaces', 'python_code'):
            self.assertNotIn(key, data)

    def test_status_filter_for_the_admin_review_list(self):
        pending, rejected, approved = self.row(), self.row(status='rejected'), self.row(status='approved')
        ids = lambda user, status: {item['id'] for item in self.call('ai-analysis-templates', user, 'get', {'status': status}).data['results']}
        self.assertEqual(ids(self.admin, 'pending_admin'), {pending.pk})
        self.assertEqual(ids(self.admin, 'rejected'), {rejected.pk})
        self.assertEqual(ids(self.other, 'rejected'), set())
        self.assertEqual(self.call('ai-analysis-templates', self.admin, 'get', {'status': 'bogus'}).status_code, 400)


class CorrectionTests(ReviewBase):
    def rejected(self):
        row = self.row()
        self.assertEqual(self.reject(self.admin, row).status_code, 200)
        row.refresh_from_db()
        return row

    def test_admin_saves_a_correction_as_the_next_version_of_the_same_family(self):
        old = self.rejected()
        response = self.save_correction(self.admin, old)
        self.assertEqual(response.status_code, 201)
        new = AIAnalysisTemplate.objects.get(pk=response.data['id'])
        self.assertEqual((new.family_id, new.version, new.replaces_id, new.status, new.approved_by_id), (old.family_id, 2, old.pk, 'pending_admin', self.admin.pk))
        old.refresh_from_db()
        self.assertEqual((old.status, old.version, old.state_revision), ('rejected', 1, 2))  # 元の行は変わらない
        self.assertNotEqual(new.content_sha256, old.content_sha256)

    def test_correction_requires_admin_a_rejected_original_and_different_content(self):
        old = self.rejected()
        self.assertEqual(self.save_correction(self.creator, old).status_code, 403)
        pending = self.row()
        self.assertEqual(self.save_correction(self.admin, pending).status_code, 409)
        # 内容が同じ(名称も変えない)なら訂正版にならない
        plan = make_plan(self.admin.pk, revision=2)
        with patch.object(service.AnalysisPlanStore, 'get', lambda _s, pid, owner: AnalysisPlanStore._decode(json.dumps(plan), owner)):
            same = self.call('ai-analysis-templates', self.admin, data={'plan_id': plan['id'], 'revision': 2, 'replaces': old.pk})
        self.assertEqual(same.status_code, 409)
        for bad in (True, 0, '1'):
            with patch.object(service.AnalysisPlanStore, 'get', lambda _s, pid, owner: AnalysisPlanStore._decode(json.dumps(plan), owner)):
                response = self.call('ai-analysis-templates', self.admin, data={'plan_id': plan['id'], 'revision': 2, 'replaces': bad})
            self.assertEqual(response.status_code, 400, bad)
        self.assertEqual(self.save_correction(self.admin, old, plan=make_plan(self.admin.pk, revision=2)).status_code, 201)
        self.assertEqual(AIAnalysisTemplate.objects.filter(replaces__isnull=False).count(), 1)

    def test_unknown_original_is_404(self):
        plan = make_plan(self.admin.pk, revision=2)
        with patch.object(service.AnalysisPlanStore, 'get', lambda _s, pid, owner: AnalysisPlanStore._decode(json.dumps(plan), owner)):
            response = self.call('ai-analysis-templates', self.admin, data={'plan_id': plan['id'], 'revision': 2, 'replaces': 999999})
        self.assertEqual(response.status_code, 404)

    def test_resending_the_same_correction_returns_the_same_row(self):
        old = self.rejected()
        plan = make_plan(self.admin.pk, revision=2)
        first = self.save_correction(self.admin, old, plan=plan)
        again = self.save_correction(self.admin, old, plan=plan)
        self.assertEqual((first.status_code, again.status_code, again.data['id'], again.data['created']), (201, 200, first.data['id'], False))
        self.assertEqual(AIAnalysisTemplate.objects.count(), 2)

    def test_resending_the_same_correction_after_approval_still_returns_the_existing_row(self):
        old = self.rejected()
        plan = make_plan(self.admin.pk, revision=2)
        first = self.save_correction(self.admin, old, plan=plan)
        new = AIAnalysisTemplate.objects.get(pk=first.data['id'])
        self.assertEqual(self.approve(self.admin2, new).status_code, 200)  # 元は置換済みになる
        again = self.save_correction(self.admin, old, plan=plan)
        self.assertEqual((again.status_code, again.data['id'], again.data['created']), (200, new.pk, False))
        self.assertEqual(AIAnalysisTemplate.objects.count(), 2)
        # 管理者でない利用者の再送は、既存の行があっても権限で拒否する
        with patch.object(service.AnalysisPlanStore, 'get', lambda _s, pid, owner: AnalysisPlanStore._decode(json.dumps(plan), owner)):
            denied = self.call('ai-analysis-templates', self.creator, data={'plan_id': plan['id'], 'revision': 2, 'replaces': old.pk})
        self.assertIn(denied.status_code, (403, 404))

    def test_correction_request_for_a_plan_already_saved_as_a_plain_template_is_refused(self):
        old = self.rejected()
        plan = make_plan(self.admin.pk, revision=2)
        plan['proposal'] = {**plan['proposal'], 'title': '訂正した分析'}
        with patch.object(service.AnalysisPlanStore, 'get', lambda _s, pid, owner: AnalysisPlanStore._decode(json.dumps(plan), owner)):
            plain = self.call('ai-analysis-templates', self.admin, data={'plan_id': plan['id'], 'revision': 2})
            self.assertEqual(plain.status_code, 201)
            response = self.call('ai-analysis-templates', self.admin, data={'plan_id': plan['id'], 'revision': 2, 'replaces': old.pk})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(AIAnalysisTemplate.objects.filter(replaces__isnull=False).count(), 0)

    def test_approving_the_correction_supersedes_the_original_in_one_transaction(self):
        old = self.rejected()
        new = AIAnalysisTemplate.objects.get(pk=self.save_correction(self.admin, old).data['id'])
        self.assertEqual(self.approve(self.admin2, new).status_code, 200)
        old.refresh_from_db(); new.refresh_from_db()
        self.assertEqual((new.status, old.status), ('approved', 'superseded'))
        self.assertEqual(old.state_revision, 3)
        detail = self.call('ai-analysis-template', self.creator, 'get', template_id=old.pk).data
        self.assertEqual((detail['status'], detail['replacement_id']), ('superseded', new.pk))
        # 置換済みの元の版は、他の利用者には存在しない
        self.assertEqual(self.call('ai-analysis-template', self.other, 'get', template_id=old.pk).status_code, 404)

    def test_if_replacing_the_original_fails_the_approval_is_rolled_back(self):
        old = self.rejected()
        new = AIAnalysisTemplate.objects.get(pk=self.save_correction(self.admin, old).data['id'])
        AIAnalysisTemplate.objects.filter(pk=old.pk).update(status='superseded')  # 先に別の経路で状態が変わった
        response = self.approve(self.admin2, new)
        self.assertEqual(response.status_code, 409)
        new.refresh_from_db()
        self.assertEqual((new.status, new.state_revision, new.reviewed_by_id), ('pending_admin', 1, None))

    def test_rejecting_the_correction_leaves_the_original_rejected_and_allows_another_correction(self):
        old = self.rejected()
        first = AIAnalysisTemplate.objects.get(pk=self.save_correction(self.admin, old).data['id'])
        self.assertEqual(self.reject(self.admin2, first).status_code, 200)
        old.refresh_from_db()
        self.assertEqual(old.status, 'rejected')
        second = self.save_correction(self.admin, old, plan=make_plan(self.admin.pk, revision=3), title='さらに訂正')
        self.assertEqual(second.status_code, 201)
        self.assertEqual(AIAnalysisTemplate.objects.get(pk=second.data['id']).version, 3)

    def test_only_one_pending_correction_per_rejected_original(self):
        old = self.rejected()
        first = self.save_correction(self.admin, old)
        self.assertEqual(first.status_code, 201)
        second = self.save_correction(self.admin, old, plan=make_plan(self.admin.pk, revision=3), title='別の訂正')
        self.assertEqual(second.status_code, 409)
        self.assertEqual(AIAnalysisTemplate.objects.filter(replaces=old).count(), 1)
        # 先の訂正版を却下すれば、次の訂正版を保存できる。承認して元が置換済みになった後は保存できない
        self.assertEqual(self.reject(self.admin2, AIAnalysisTemplate.objects.get(pk=first.data['id'])).status_code, 200)
        third = self.save_correction(self.admin, old, plan=make_plan(self.admin.pk, revision=4), title='三つ目の訂正')
        self.assertEqual(third.status_code, 201)
        self.assertEqual(self.approve(self.admin2, AIAnalysisTemplate.objects.get(pk=third.data['id'])).status_code, 200)
        fourth = self.save_correction(self.admin, old, plan=make_plan(self.admin.pk, revision=5), title='四つ目の訂正')
        self.assertEqual(fourth.status_code, 409)
        self.assertEqual(AIAnalysisTemplate.objects.filter(replaces=old).count(), 2)

    def test_pending_correction_check_runs_under_a_lock_on_the_original(self):
        """同時の訂正版保存で、両方が事前の確認をすり抜けても、ロック内の確認で片方だけが成立する(ロックを取ることと、ロック内で確認することを検証)。"""
        old = self.rejected()
        self.assertEqual(self.save_correction(self.admin, old).status_code, 201)
        real = AIAnalysisTemplate.objects.select_for_update
        with patch.object(service, '_replaced_template', return_value=old), \
                patch.object(service.AIAnalysisTemplate.objects, 'select_for_update', wraps=real) as lock:
            response = self.save_correction(self.admin, old, plan=make_plan(self.admin.pk, revision=3), title='同時の訂正')
        self.assertEqual(response.status_code, 409)
        lock.assert_called_once()
        self.assertEqual(AIAnalysisTemplate.objects.filter(replaces=old).count(), 1)

    def test_pending_check_happens_inside_the_transaction_after_the_lock_query(self):
        """承認待ちの訂正版の確認が、トランザクション(SAVEPOINT)の内側で、元の行を取得するロックの問い合わせより後に実行されること。
        SQLiteでは排他は効かないため、実際のロックの効果は実DBで確認する(未確認)。"""
        old = self.rejected()
        self.assertEqual(self.save_correction(self.admin, old).status_code, 201)
        with CaptureQueriesContext(connection) as queries, \
                patch.object(service, '_replaced_template', return_value=old):
            response = self.save_correction(self.admin, old, plan=make_plan(self.admin.pk, revision=3), title='同時の訂正')
        self.assertEqual(response.status_code, 409)
        sqls = [q['sql'] for q in queries.captured_queries]

        savepoint = next(i for i, sql in enumerate(sqls) if sql.startswith('SAVEPOINT'))
        lock = next(i for i, sql in enumerate(sqls) if i > savepoint and '"ai_analysis_template"."id" =' in sql)
        pending = next(i for i, sql in enumerate(sqls) if '"replaces_id" =' in sql and "'pending_admin'" in sql)
        self.assertLess(savepoint, lock)
        self.assertLess(lock, pending)

    def test_approval_reruns_the_current_code_checks_and_does_not_reject_an_old_wrapper(self):
        row = self.row()
        with patch.object(review, 'validate_generated', return_value=['python:forbidden_name']) as checked:
            response = self.approve(self.admin, row)
        self.assertEqual(response.status_code, 409)
        self.assertNotIn('forbidden_name', json.dumps(response.data, ensure_ascii=False))
        checked.assert_called_once()
        row.refresh_from_db()
        self.assertEqual((row.status, row.state_revision, row.reviewed_by_id), ('pending_admin', 1, None))
        # 検査に合格すれば承認できる。外枠の版が現行と違っても、承認時には拒否しない
        fields = service._fields_from_plan(make_plan(self.creator.pk))
        fields['wrapper_version'] = 'old-wrapper'
        fields['content_sha256'] = service._content_sha256(fields)
        old_wrapper = self.row(**fields)
        self.assertEqual(self.approve(self.admin, old_wrapper).status_code, 200)
        self.assertEqual(self.approve(self.admin, row).status_code, 200)

    def test_malformed_stored_rows_are_a_fixed_409_not_a_server_error(self):
        for label, overrides in (('datasets_without_view', {'datasets': [{'fields': ['id']}]}), ('steps_not_a_list', {'sql_steps': 5}),
                                 ('python_not_text', {'python_code': 123})):
            with self.subTest(label):
                fields = service._fields_from_plan(make_plan(self.creator.pk))
                fields.update(overrides)
                fields['content_sha256'] = '0' * 64
                row = self.row(**fields)
                # 保存された値から計算したハッシュに揃え、ハッシュ照合は通る形でも、検査が例外にならず拒否されること
                with patch.object(review, '_stored_hash', return_value=row.content_sha256):
                    response = self.approve(self.admin, row)
                self.assertEqual(response.status_code, 409)
                row.refresh_from_db()
                self.assertEqual(row.status, 'pending_admin')

    def test_approved_and_superseded_rows_cannot_be_changed_again(self):
        old = self.rejected()
        new = AIAnalysisTemplate.objects.get(pk=self.save_correction(self.admin, old).data['id'])
        self.assertEqual(self.approve(self.admin, new).status_code, 200)
        old.refresh_from_db(); new.refresh_from_db()
        for row in (old, new):
            self.assertEqual(self.approve(self.admin, row).status_code, 409)
            self.assertEqual(self.reject(self.admin, row).status_code, 409)
        self.assertEqual(self.save_correction(self.admin, old, plan=make_plan(self.admin.pk, revision=4), title='別の訂正').status_code, 409)

    def test_no_notification_or_external_call_happens(self):
        old = self.rejected()
        with patch('ai.services.analysis_codegen_service._call_ai') as ai, \
                patch('shipping.services.email_service.EmailService.send_plain_email') as mail:
            self.save_correction(self.admin, old)
        ai.assert_not_called()
        mail.assert_not_called()
