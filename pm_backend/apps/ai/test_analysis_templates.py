"""テンプレートの保存・一覧・詳細(第3段階3-A)を、実ユーザー・実効権限・一時SQLiteで検証する。

Redisの分析案は、AnalysisPlanStoreの読み取りだけを差し替える(保存・権限・共有範囲・ハッシュは実処理)。
AI・launcherは呼ばないことも確認する。
"""
import json
from datetime import date, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.db import IntegrityError, transaction
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import UserPermission
from ai import urls
from ai.models import AIAnalysisTemplate
from ai.services import analysis_codegen_service as cg
from ai.services import analysis_template_service as service
from ai.services.analysis_plan_store import AnalysisError, AnalysisPlanStore

DATASETS = [{'view': 'v_ai_shipment', 'fields': ['id', 'shipment_date', 'quantity']}]
VIEWS = [d['view'] for d in DATASETS]
STEPS = [{'name': 'w_daily', 'query': 'SELECT shipment_date, SUM(quantity) AS q FROM v_ai_shipment GROUP BY shipment_date'}]
PYTHON = "rows = con.sql('SELECT shipment_date, q FROM w_daily ORDER BY shipment_date').fetchall()\nemit_table('日別', ['日', '数量'], [[str(a), str(b)] for a, b in rows])"
ROUTES = {route.name: route for route in urls.urlpatterns if str(route.pattern).startswith('ai/analysis/')}
SECRET = '秘密の条件ＸＹＺ'


def make_plan(owner_id, revision=3, **overrides):
    bundle = cg.make_bundle(STEPS, PYTHON, VIEWS)
    now = datetime.now()
    plan = {
        'id': str(uuid4()), 'owner_id': owner_id, 'revision': revision, 'status': 'data_approved',
        'proposal': {
            'title': '日別出荷の分析', 'steps': ['出荷を日別に集計', '表にする'], 'outputs': ['日別の表'], 'datasets': DATASETS,
            'purpose': '日別の出荷数量を確認する', 'date_from': '2026-01-01', 'date_to': '2026-01-31', 'materials': [],
            'conditions': SECRET,
        },
        'expires_at': (now + timedelta(minutes=30)).isoformat(),
        'method_approved_at': (now - timedelta(minutes=5)).isoformat(), 'data_approved_at': (now - timedelta(minutes=4)).isoformat(),
        'codegen': {
            'status': 'code_approved', 'steps': STEPS, 'python': PYTHON, 'executed_code_sha256': bundle.executed_code_sha256,
            'wrapper_version': bundle.wrapper_version, 'code_approved_at': (now - timedelta(minutes=3)).isoformat(),
        },
    }
    plan.update(overrides)
    return plan


@override_settings(ALLOWED_HOSTS=['testserver'])
class TemplateTestBase(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.owner = users.create_user(username='tpl-owner')
        self.other = users.create_user(username='tpl-other')
        self.admin = users.create_user(username='tpl-admin')
        for user in (self.owner, self.other, self.admin):
            UserPermission.objects.create(user=user, resource='ai.analysis', can_view=True, can_edit=True)
        UserPermission.objects.create(user=self.admin, resource='settings.ai', can_view=True, can_edit=True)
        self.factory = APIRequestFactory()

    def call(self, name, user, method='get', data=None, **kwargs):
        request = (self.factory.get('/', data or {}) if method == 'get' else self.factory.post('/', data or {}, format='json'))
        if user is not None:
            force_authenticate(request, user)
        return ROUTES[name].callback(request, **kwargs)

    def use_plan(self, plan):
        """分析案の読み取りだけを差し替える。所有者の照合は実処理(_decode)を通す。"""
        return patch.object(service.AnalysisPlanStore, 'get', lambda _self, plan_id, owner_id: AnalysisPlanStore._decode(json.dumps(plan), owner_id))

    def save(self, user, plan, revision=None):
        with self.use_plan(plan), patch.object(cg, '_call_ai') as ai:
            response = self.call('ai-analysis-templates', user, 'post', {'plan_id': plan['id'], 'revision': plan['revision'] if revision is None else revision})
        ai.assert_not_called()
        return response

    def make_row(self, user, status='pending_admin', **overrides):
        plan = make_plan(user.pk if user else 0)
        fields = service._fields_from_plan(plan)
        values = {'family_id': uuid4(), 'version': 1, 'source_plan_id': str(uuid4()), 'source_plan_revision': 1,
                  'approved_by': user, 'status': status, **fields}
        values.update(overrides)
        return AIAnalysisTemplate.objects.create(**values)


class SaveTests(TemplateTestBase):
    def test_saves_approved_plan_with_recalculated_hashes_and_pending_status(self):
        plan = make_plan(self.owner.pk)
        response = self.save(self.owner, plan)
        self.assertEqual(response.status_code, 201)
        row = AIAnalysisTemplate.objects.get()
        bundle = cg.make_bundle(STEPS, PYTHON, VIEWS)
        self.assertEqual((row.status, row.version, row.state_revision), ('pending_admin', 1, 1))
        self.assertEqual((row.name, row.approved_by_id, row.source_plan_id, row.source_plan_revision), ('日別出荷の分析', self.owner.pk, plan['id'], 3))
        self.assertEqual((row.sql_steps, row.python_code, row.datasets), (STEPS, PYTHON, DATASETS))
        self.assertEqual((row.executed_code_sha256, row.python_sha256, row.sql_sha256, row.wrapper_version),
                         (bundle.executed_code_sha256, bundle.python_sha256, bundle.sql_sha256, bundle.wrapper_version))
        self.assertEqual((row.date_from.isoformat(), row.date_to.isoformat()), ('2026-01-01', '2026-01-31'))
        self.assertEqual(len(row.content_sha256), 64)
        self.assertEqual(response.data['id'], row.pk)
        self.assertTrue(response.data['created'])
        self.assertNotIn('owner_id', response.data)

    def test_same_request_and_same_content_do_not_create_duplicates(self):
        plan = make_plan(self.owner.pk)
        first = self.save(self.owner, plan)
        again = self.save(self.owner, plan)
        self.assertEqual((first.status_code, again.status_code), (201, 200))
        self.assertFalse(again.data['created'])
        self.assertEqual(AIAnalysisTemplate.objects.count(), 1)
        # 版だけが進んだ同じ内容(同じ分析案)も、別の行にしない
        newer = {**plan, 'revision': 9}
        self.assertEqual(self.save(self.owner, newer).status_code, 200)
        self.assertEqual(AIAnalysisTemplate.objects.count(), 1)

    def test_changed_content_from_same_plan_is_a_separate_revision_row(self):
        plan = make_plan(self.owner.pk)
        self.save(self.owner, plan)
        changed = make_plan(self.owner.pk, revision=4, id=plan['id'])
        changed['proposal'] = {**changed['proposal'], 'title': '別の名称'}
        self.assertEqual(self.save(self.owner, changed).status_code, 201)
        rows = AIAnalysisTemplate.objects.order_by('id')
        self.assertEqual(rows.count(), 2)
        self.assertNotEqual(rows[0].content_sha256, rows[1].content_sha256)
        self.assertNotEqual(rows[0].family_id, rows[1].family_id)

    def test_rejects_unapproved_or_inconsistent_plans_with_fixed_messages(self):
        cases = {
            'code_not_approved': ({'codegen': {**make_plan(self.owner.pk)['codegen'], 'status': 'generated'}}, 409),
            'method_not_approved': ({'method_approved_at': None}, 409),
            'data_not_approved': ({'status': 'awaiting_data'}, 409),
            'expired': ({'expires_at': (datetime.now() - timedelta(seconds=1)).isoformat()}, 410),
        }
        for label, (overrides, status) in cases.items():
            with self.subTest(label):
                response = self.save(self.owner, make_plan(self.owner.pk, **overrides))
                self.assertEqual(response.status_code, status)
        self.assertEqual(AIAnalysisTemplate.objects.count(), 0)

    def test_rejects_when_approved_code_hash_no_longer_matches(self):
        plan = make_plan(self.owner.pk)
        plan['codegen'] = {**plan['codegen'], 'python': PYTHON + '\n# 承認後に変更'}
        self.assertEqual(self.save(self.owner, plan).status_code, 409)
        self.assertEqual(AIAnalysisTemplate.objects.count(), 0)

    def test_rejects_when_current_validation_fails_or_wrapper_is_old(self):
        plan = make_plan(self.owner.pk)
        with patch.object(service, 'validate_generated', return_value=['python:import']):
            self.assertEqual(self.save(self.owner, plan).status_code, 409)
        old = make_plan(self.owner.pk)
        old['codegen'] = {**old['codegen'], 'wrapper_version': 'old-wrapper'}
        self.assertEqual(self.save(self.owner, old).status_code, 409)
        self.assertEqual(AIAnalysisTemplate.objects.count(), 0)

    def test_revision_mismatch_other_owner_and_missing_plan(self):
        plan = make_plan(self.owner.pk)
        self.assertEqual(self.save(self.owner, plan, revision=2).status_code, 409)
        self.assertEqual(self.save(self.other, plan).status_code, 404)
        with patch.object(service.AnalysisPlanStore, 'get', lambda _self, pid, owner: AnalysisPlanStore._decode(None, owner)):
            response = self.call('ai-analysis-templates', self.owner, 'post', {'plan_id': plan['id'], 'revision': 3})
        self.assertEqual(response.status_code, 410)
        self.assertEqual(AIAnalysisTemplate.objects.count(), 0)

    def test_name_longer_than_column_is_refused_not_truncated(self):
        plan = make_plan(self.owner.pk)
        plan['proposal'] = {**plan['proposal'], 'title': 'あ' * 301}
        self.assertEqual(self.save(self.owner, plan).status_code, 409)
        plan['proposal'] = {**plan['proposal'], 'title': 'あ' * 300}
        self.assertEqual(self.save(self.owner, plan).status_code, 201)

    def test_request_body_is_strict(self):
        plan = make_plan(self.owner.pk)
        bad_bodies = [
            {'plan_id': plan['id']}, {'plan_id': plan['id'], 'revision': 3, 'python': 'x'}, {'plan_id': 'not-a-uuid', 'revision': 3},
            {'plan_id': plan['id'], 'revision': True}, {'plan_id': plan['id'], 'revision': '3'}, {'plan_id': plan['id'], 'revision': 0},
            {'plan_id': 123, 'revision': 3},
        ]
        for body in bad_bodies:
            with self.subTest(body=body), self.use_plan(plan):
                self.assertEqual(self.call('ai-analysis-templates', self.owner, 'post', body).status_code, 400)
        self.assertEqual(AIAnalysisTemplate.objects.count(), 0)

    def test_view_only_user_cannot_save_and_nothing_is_read_from_redis(self):
        UserPermission.objects.filter(user=self.owner, resource='ai.analysis').update(can_edit=False)
        with patch.object(service.AnalysisPlanStore, 'get') as get:
            response = self.call('ai-analysis-templates', self.owner, 'post', {'plan_id': str(uuid4()), 'revision': 1})
        self.assertEqual(response.status_code, 403)
        get.assert_not_called()

    def test_concurrent_save_returns_the_row_that_won_and_creates_no_extra_row(self):
        """同時要求に負けた側(最初の確認をすり抜け、作成で一意制約に当たる)は、先に成立した行を返す。"""
        plan = make_plan(self.owner.pk)
        winner = self.make_row(self.owner, source_plan_id=plan['id'], source_plan_revision=plan['revision'])
        real = service._find_existing
        calls = []

        def racing(*args):
            calls.append(args)
            return None if len(calls) == 1 else real(*args)

        with patch.object(service, '_find_existing', side_effect=racing):
            response = self.save(self.owner, plan)
        self.assertEqual((response.status_code, response.data['id'], response.data['created']), (200, winner.pk, False))
        self.assertEqual((len(calls), AIAnalysisTemplate.objects.count()), (2, 1))

    def test_concurrent_save_of_same_content_with_another_revision_is_not_duplicated(self):
        """版違いで同じ内容を同時に保存しても、同じ分析案・同じ内容の行は1つ(source_plan_id, content_sha256の一意制約)。"""
        plan = make_plan(self.owner.pk, revision=3)
        content = service._fields_from_plan(plan)['content_sha256']
        winner = self.make_row(self.owner, source_plan_id=plan['id'], source_plan_revision=9, content_sha256=content)
        real = service._find_existing
        calls = []

        def racing(*args):
            calls.append(args)
            return None if len(calls) == 1 else real(*args)

        with patch.object(service, '_find_existing', side_effect=racing):
            response = self.save(self.owner, plan)
        self.assertEqual((response.status_code, response.data['id']), (200, winner.pk))
        self.assertEqual(AIAnalysisTemplate.objects.count(), 1)

    def test_lost_race_without_a_visible_winner_is_a_fixed_409_and_creates_nothing(self):
        plan = make_plan(self.owner.pk)
        with patch.object(service, '_find_existing', return_value=None), \
                patch.object(AIAnalysisTemplate.objects, 'create', side_effect=IntegrityError('SECRET-DB')):
            response = self.save(self.owner, plan)
        self.assertEqual(response.status_code, 409)
        self.assertNotIn('SECRET', json.dumps(response.data, ensure_ascii=False))
        self.assertEqual(AIAnalysisTemplate.objects.count(), 0)

    def test_resend_after_rejection_returns_the_existing_row_with_its_status(self):
        """却下・置換済みの後の再提出の扱いは3-Bで決める。それまで、同じ内容の再送は既存の行(状態つき)を返す。"""
        plan = make_plan(self.owner.pk)
        self.save(self.owner, plan)
        AIAnalysisTemplate.objects.update(status='rejected')
        response = self.save(self.owner, plan)
        self.assertEqual((response.status_code, response.data['created'], response.data['status']), (200, False, 'rejected'))
        self.assertEqual(AIAnalysisTemplate.objects.count(), 1)

    def test_incomplete_or_wrongly_typed_plans_are_fixed_409_not_server_errors(self):
        def broken(mutate):
            plan = make_plan(self.owner.pk)
            mutate(plan)
            return plan
        cases = {
            'title_missing': lambda p: p['proposal'].pop('title'),
            'purpose_missing': lambda p: p['proposal'].pop('purpose'),
            'purpose_none': lambda p: p['proposal'].update(purpose=None),
            'conditions_none': lambda p: p['proposal'].update(conditions=None),
            'steps_not_list': lambda p: p['proposal'].update(steps='手順'),
            'outputs_empty': lambda p: p['proposal'].update(outputs=[]),
            'datasets_missing': lambda p: p['proposal'].pop('datasets'),
            'dates_missing': lambda p: p['proposal'].pop('date_from'),
            'proposal_missing': lambda p: p.pop('proposal'),
            'codegen_steps_missing': lambda p: p['codegen'].pop('steps'),
            'expires_with_timezone': lambda p: p.update(expires_at='2099-01-01T00:00:00+09:00'),
            'method_time_broken': lambda p: p.update(method_approved_at='not-a-time'),
        }
        for label, mutate in cases.items():
            with self.subTest(label):
                response = self.save(self.owner, broken(mutate))
                self.assertEqual(response.status_code, 409)
                self.assertNotIn('Traceback', json.dumps(response.data, ensure_ascii=False))
        self.assertEqual(AIAnalysisTemplate.objects.count(), 0)


class VisibilityTests(TemplateTestBase):
    def test_creator_and_admin_see_full_content_others_see_summary_only(self):
        row = self.make_row(self.owner)
        for user, full in ((self.owner, True), (self.admin, True), (self.other, False)):
            with self.subTest(user=user.username):
                detail = self.call('ai-analysis-template', user, template_id=row.pk)
                listing = self.call('ai-analysis-templates', user).data['results'][0]
                self.assertEqual(detail.status_code, 200)
                for data in (detail.data, listing):
                    self.assertEqual(data['content_visible'], full)
                    self.assertEqual((data['name'], data['status_label'], data['created_by']), ('日別出荷の分析', '管理者承認待ち', 'tpl-owner'))
                if full:
                    self.assertEqual((detail.data['python_code'], detail.data['sql_steps'], detail.data['conditions']), (PYTHON, STEPS, SECRET))
                    self.assertNotIn('python_code', listing)
                else:
                    text = json.dumps(detail.data, ensure_ascii=False) + json.dumps(listing, ensure_ascii=False)
                    for hidden in ('python_code', 'sql_steps', 'conditions', 'datasets', 'procedure', 'output_spec', SECRET, 'emit_table',
                                   'date_from', 'content_sha256', 'executed_code_sha256'):
                        self.assertNotIn(hidden, text)

    def test_rejected_and_superseded_are_hidden_from_others_but_not_creator_or_admin(self):
        pending = self.make_row(self.owner)
        rejected = self.make_row(self.owner, status='rejected')
        superseded = self.make_row(self.owner, status='superseded')
        approved = self.make_row(self.owner, status='approved')
        other_ids = {row['id'] for row in self.call('ai-analysis-templates', self.other).data['results']}
        self.assertEqual(other_ids, {pending.pk, approved.pk})
        for row in (rejected, superseded):
            self.assertEqual(self.call('ai-analysis-template', self.other, template_id=row.pk).status_code, 404)
        for user in (self.owner, self.admin):
            ids = {item['id'] for item in self.call('ai-analysis-templates', user).data['results']}
            self.assertEqual(ids, {pending.pk, rejected.pk, superseded.pk, approved.pk})
            self.assertEqual(self.call('ai-analysis-template', user, template_id=rejected.pk).status_code, 200)

    def test_unknown_template_is_404(self):
        self.assertEqual(self.call('ai-analysis-template', self.owner, template_id=999999).status_code, 404)

    def test_deleted_creator_is_shown_as_deleted_user_and_content_hidden_from_non_admin(self):
        row = self.make_row(self.owner)
        # ユーザー削除はDjango標準のSET_NULL(外部の未管理テーブルが一時DBにないため、削除後の行の状態を直接作る)
        self.assertEqual(AIAnalysisTemplate._meta.get_field('approved_by').remote_field.on_delete.__name__, 'SET_NULL')
        AIAnalysisTemplate.objects.filter(pk=row.pk).update(approved_by=None)
        row.refresh_from_db()
        self.assertIsNone(row.approved_by_id)
        data = self.call('ai-analysis-template', self.other, template_id=row.pk).data
        self.assertEqual((data['created_by'], data['content_visible']), ('削除済みユーザー', False))
        self.assertTrue(self.call('ai-analysis-template', self.admin, template_id=row.pk).data['content_visible'])

    def test_admin_lookup_failure_does_not_grant_content(self):
        row = self.make_row(self.owner)
        with patch.object(service, '_has_resource_permission', side_effect=RuntimeError('SECRET-DB')):
            data = self.call('ai-analysis-template', self.other, template_id=row.pk)
        self.assertEqual(data.status_code, 200)
        self.assertFalse(data.data['content_visible'])
        self.assertNotIn('SECRET', json.dumps(data.data))


class ListTests(TemplateTestBase):
    def test_newest_first_with_id_tiebreak_and_fixed_page_size_30(self):
        now = datetime.now()
        rows = [self.make_row(self.owner, source_plan_id=str(uuid4())) for _ in range(31)]
        AIAnalysisTemplate.objects.update(created_at=now)
        AIAnalysisTemplate.objects.filter(pk=rows[0].pk).update(created_at=now - timedelta(days=1))
        page1 = self.call('ai-analysis-templates', self.owner).data
        self.assertEqual((page1['count'], len(page1['results'])), (31, 30))
        self.assertIsNotNone(page1['next'])
        ids = [item['id'] for item in page1['results']]
        self.assertEqual(ids, sorted(ids, reverse=True))
        page2 = self.call('ai-analysis-templates', self.owner, data={'page': 2}).data
        self.assertEqual([item['id'] for item in page2['results']], [rows[0].pk])
        # 利用者がページサイズを変えられない
        self.assertEqual(len(self.call('ai-analysis-templates', self.owner, data={'page_size': 100}).data['results']), 30)


class ModelTests(TemplateTestBase):
    def test_unique_constraints_and_content_is_not_changed_by_status_update(self):
        row = self.make_row(self.owner)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_row(self.owner, family_id=row.family_id, version=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_row(self.owner, source_plan_id=row.source_plan_id, source_plan_revision=row.source_plan_revision)
        before = row.content_sha256
        AIAnalysisTemplate.objects.filter(pk=row.pk).update(status='approved', state_revision=2)
        row.refresh_from_db()
        self.assertEqual((row.status, row.content_sha256), ('approved', before))

    def test_content_hash_ignores_dates_and_status_but_changes_with_code(self):
        plan = make_plan(self.owner.pk)
        first = service._fields_from_plan(plan)['content_sha256']
        self.assertEqual(first, service._fields_from_plan(make_plan(self.owner.pk))['content_sha256'])
        changed = make_plan(self.owner.pk)
        changed['proposal'] = {**changed['proposal'], 'date_to': '2026-02-28'}
        self.assertNotEqual(first, service._fields_from_plan(changed)['content_sha256'])

    def test_content_hash_matches_a_fixed_value_and_can_be_recalculated_from_the_stored_row(self):
        fixed = {
            'name': '日別出荷の分析', 'purpose': '日別の出荷数量を確認する', 'procedure': ['出荷を日別に集計', '表にする'],
            'output_spec': ['日別の表'], 'conditions': '条件', 'datasets': [{'view': 'v_ai_shipment', 'fields': ['id', 'shipment_date', 'quantity']}],
            'date_from': date(2026, 1, 1), 'date_to': date(2026, 1, 31), 'sql_steps': [{'name': 'w_daily', 'query': 'SELECT 1'}],
            'python_code': "emit_table('日別', ['日'], [['1']])", 'wrapper_version': 'w1', 'executed_code_sha256': 'a' * 64,
        }
        # 計算方法(キー・並び・区切り・日付表記)を変えると、保存済みの行のハッシュと照合できなくなる。意図した変更だけが値を変える
        self.assertEqual(service._content_sha256(fixed), '393611427254d56581f3e5b5cec0fbe41826fa21153a678c4d34f4ea3bf4e926')
        # 辞書のキーの並びが違っても同じ値(DBのJSON表現の順序に依存しない)
        reordered = {key: fixed[key] for key in reversed(list(fixed))}
        reordered['datasets'] = [{'fields': ['id', 'shipment_date', 'quantity'], 'view': 'v_ai_shipment'}]
        self.assertEqual(service._content_sha256(reordered), service._content_sha256(fixed))
        # 保存した行を読み戻した値から再計算した結果が、保存したcontent_sha256と一致する
        self.save(self.owner, make_plan(self.owner.pk))
        row = AIAnalysisTemplate.objects.get()
        recalculated = service._content_sha256({
            'name': row.name, 'purpose': row.purpose, 'procedure': row.procedure, 'output_spec': row.output_spec,
            'conditions': row.conditions, 'datasets': row.datasets, 'date_from': row.date_from, 'date_to': row.date_to,
            'sql_steps': row.sql_steps, 'python_code': row.python_code, 'wrapper_version': row.wrapper_version,
            'executed_code_sha256': row.executed_code_sha256,
        })
        self.assertEqual(recalculated, row.content_sha256)

    def test_same_plan_and_content_is_unique_in_the_database(self):
        row = self.make_row(self.owner)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_row(self.owner, source_plan_id=row.source_plan_id, source_plan_revision=row.source_plan_revision + 1,
                          content_sha256=row.content_sha256)

    def test_service_errors_are_analysis_errors_not_internal_text(self):
        plan = make_plan(self.owner.pk, status='awaiting_method')
        with self.assertRaises(AnalysisError):
            service._fields_from_plan(plan)
