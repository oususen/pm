"""結果の改良(レベル1。BOSS承認 2026-10-06): 追加の指示を、元の目的に足した新しい分析案と、実行履歴への保存を、一時SQLiteで検証する。

AI(ローカルQwen・社外)と置換器だけを差し替える。追加の指示は、目的文に足してAIへ送り(社外はコード置換後)、実行履歴に原文で残す。
"""
import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from ai.models import AIAnalysisRun
from ai.services import analysis_planning_service as planning
from ai.services import analysis_run_service as runs
from ai.services.analysis_plan_store import AnalysisError, AnalysisPlanStore
from ai.test_analysis_planning import FakeRedis
from ai.test_analysis_run import BUNDLE, POLICY, make_plan
from ai.test_analysis_execution import approved_counts

PROPOSAL = {
    'title': '製品別出荷', 'steps': ['製品別に出荷数量を合計する'], 'outputs': ['製品別の表'],
    'datasets': [{'view': 'v_ai_shipment', 'fields': ['id', 'shipment_date', 'product_code', 'product_name', 'quantity']}],
}
PAYLOAD = {'purpose': '9月の製品別出荷量を比べる', 'date_from': '2026-09-01', 'date_to': '2026-09-30'}


class FakeRedactor:
    def redact_text(self, text):
        return text.replace('ACME', 'CUST-001')


def make_run(user, **overrides):
    values = {
        'plan_id': 'p', 'user': user, 'views': PROPOSAL['datasets'], 'date_from': '2026-09-01', 'date_to': '2026-09-30',
        'worker_id': 'w', 'heartbeat_at': datetime.now(), 'started_at': datetime.now(),
    }
    values.update(overrides)
    return AIAnalysisRun.objects.create(**values)


@override_settings(AI_ANALYSIS_REDIS_URL='redis://test.invalid/0')
class RefinementBase(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.user = users.create_user(username='rf-user')
        self.other = users.create_user(username='rf-other')
        self.source = make_run(self.user, status='success')
        self.redis = FakeRedis()
        self.chat_calls = []
        self.external_calls = []
        patchers = [
            patch('ai.services.analysis_plan_store.Redis.from_url', return_value=self.redis),
            patch.object(planning, 'get_analysis_execution_policy', return_value=SimpleNamespace(plan_cache_ttl_minutes=60, max_fetch_rows=100000)),
            patch.object(planning, 'get_qwen_analysis_timeout', return_value=100),
            patch.object(planning, 'planning_options', return_value={'available': True}),
            patch.object(planning.chat_service, '_chat', side_effect=self.fake_chat),
            patch.object(planning, 'build_analysis_code_redactor', return_value=FakeRedactor()),
            patch.object(planning.analysis_llm, 'request_external_json', side_effect=self.fake_external),
            patch.object(planning, 'resolve_planning_provider', side_effect=self.fake_resolve),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def fake_resolve(self, data):
        provider = data.get('provider', 'qwen')
        return (provider, 'm-ext' if provider != 'qwen' else 'qwen-model')

    def fake_chat(self, messages, provider, **kwargs):
        self.chat_calls.append(messages)
        return json.dumps(PROPOSAL, ensure_ascii=False)

    def fake_external(self, provider, model, messages, temperature=0.3):
        self.external_calls.append((provider, model, messages))
        return json.dumps(PROPOSAL, ensure_ascii=False)

    def refinement(self, instruction='品番も付けて', from_run_id=None):
        return {'instruction': instruction, 'from_run_id': self.source.pk if from_run_id is None else from_run_id}

    def create(self, **extra):
        return planning.create_plan(self.user.pk, {**PAYLOAD, **extra})


class RefinementPlanTests(RefinementBase):
    def test_the_instruction_is_added_to_the_purpose_sent_to_the_ai_and_kept_in_the_plan(self):
        plan = self.create(refinement=self.refinement())
        expected = '9月の製品別出荷量を比べる' + chr(10) + '追加の指示: 品番も付けて'
        sent = json.loads(self.chat_calls[0][1]['content'])
        self.assertEqual(sent['purpose'], expected)
        self.assertEqual(plan['proposal']['purpose'], expected)
        self.assertEqual(plan['refinement'], {'instruction': '品番も付けて', 'from_run_id': self.source.pk})
        self.assertEqual(plan['status'], 'awaiting_method')

    def test_without_a_refinement_the_plan_is_unchanged(self):
        plan = self.create()
        self.assertNotIn('refinement', plan)
        self.assertEqual(plan['proposal']['purpose'], PAYLOAD['purpose'])
        self.assertEqual(json.loads(self.chat_calls[0][1]['content'])['purpose'], PAYLOAD['purpose'])

    def test_the_instruction_is_trimmed_and_has_no_length_limit(self):
        long_text = '品番も付けて。' * 2000
        plan = self.create(refinement=self.refinement('  ' + long_text + '  '))
        self.assertEqual(plan['refinement']['instruction'], long_text)

    def test_the_source_run_is_optional_but_must_be_the_users_own(self):
        self.assertEqual(self.create(refinement={'instruction': '品番も付けて', 'from_run_id': None})['refinement']['from_run_id'], None)
        stranger = make_run(self.other)
        for run_id, status in ((stranger.pk, 404), (999999, 404)):
            with self.subTest(run_id=run_id), self.assertRaises(AnalysisError) as caught:
                self.create(refinement={'instruction': '品番も付けて', 'from_run_id': run_id})
            self.assertEqual(caught.exception.status_code, status)

    def test_invalid_refinements_are_refused_before_calling_the_ai(self):
        bad = ['品番も付けて', ['x'], {}, {'instruction': 'x'}, {'from_run_id': 1}, {'instruction': 'x', 'from_run_id': 1, 'extra': 1},
               {'instruction': '', 'from_run_id': None}, {'instruction': '   ', 'from_run_id': None}, {'instruction': 5, 'from_run_id': None},
               {'instruction': None, 'from_run_id': None}, {'instruction': 'x', 'from_run_id': True}, {'instruction': 'x', 'from_run_id': '1'},
               {'instruction': 'x', 'from_run_id': 0}, {'instruction': 'x', 'from_run_id': -3}, {'instruction': 'x', 'from_run_id': 1.0}]
        for refinement in bad:
            with self.subTest(refinement=refinement), self.assertRaises(AnalysisError):
                self.create(refinement=refinement)
        self.assertEqual((self.chat_calls, self.external_calls), ([], []))

    def test_a_chain_of_refinements_keeps_the_earlier_instructions_in_the_purpose(self):
        first = self.create(refinement=self.refinement('品番も付けて'))
        second = planning.create_plan(self.user.pk, {**PAYLOAD, 'purpose': first['proposal']['purpose'], 'refinement': self.refinement('上位3件だけ')})
        text = second['proposal']['purpose']
        self.assertEqual(text.count('追加の指示:'), 2)
        self.assertIn('品番も付けて', text); self.assertIn('上位3件だけ', text)


class RefinementExternalTests(RefinementBase):
    def external(self, **extra):
        return {**PAYLOAD, 'provider': 'openrouter', 'model': 'm-ext', **extra}

    def test_the_preview_and_the_sent_text_include_the_replaced_instruction(self):
        data = self.external(purpose='ACMEの出荷を比べる', refinement=self.refinement('ACME向けに品番も付けて'))
        preview = planning.external_send_preview(self.user.pk, data)
        self.assertEqual(preview['purpose'], 'CUST-001の出荷を比べる' + chr(10) + '追加の指示: CUST-001向けに品番も付けて')
        plan = planning.create_plan(self.user.pk, {**data, 'external_confirmation': preview['confirmation']})
        sent = json.loads(self.external_calls[0][2][1]['content'])
        self.assertNotIn('ACME', json.dumps(sent, ensure_ascii=False))
        self.assertEqual(plan['proposal']['external_purpose'], preview['purpose'])
        self.assertEqual(plan['refinement']['instruction'], 'ACME向けに品番も付けて')  # 履歴に残すのは原文
        self.assertEqual(self.chat_calls, [])

    def test_the_confirmation_is_bound_to_the_instruction(self):
        data = self.external(refinement=self.refinement('品番も付けて'))
        token = planning.external_send_preview(self.user.pk, data)['confirmation']
        plain = planning.external_send_preview(self.user.pk, self.external())['confirmation']
        other = planning.external_send_preview(self.user.pk, self.external(refinement=self.refinement('上位3件だけ')))['confirmation']
        self.assertEqual(len({token, plain, other}), 3)
        for changed in (self.external(refinement=self.refinement('上位3件だけ')), self.external()):
            with self.subTest(changed=changed.get('refinement')), self.assertRaises(AnalysisError) as caught:
                planning.create_plan(self.user.pk, {**changed, 'external_confirmation': token})
            self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(self.external_calls, [])  # 確認が合わなければ、送らない

    def test_an_instruction_that_cannot_be_replaced_is_never_sent(self):
        class Ambiguous:
            def redact_text(self, text):
                raise AnalysisError('名称が曖昧です', 400)

        with patch.object(planning, 'build_analysis_code_redactor', return_value=Ambiguous()), self.assertRaises(AnalysisError):
            planning.external_send_preview(self.user.pk, self.external(refinement=self.refinement()))
        self.assertEqual(self.external_calls, [])


class RefinementRunHistoryTests(RefinementBase):
    def start(self, plan_extra=None):
        plan = {**make_plan(approved_counts()), **(plan_extra or {})}
        return runs.start_run(self.user, plan, BUNDLE, POLICY)

    def test_a_refined_runs_history_keeps_the_instruction_and_the_source_run(self):
        run = self.start({'refinement': {'instruction': 'ACME向けに品番も付けて', 'from_run_id': self.source.pk}})
        run.refresh_from_db()
        self.assertEqual((run.refinement_instruction, run.refined_from_run_id), ('ACME向けに品番も付けて', self.source.pk))
        data = runs.serialize_run(run)
        self.assertEqual((data['refinement_instruction'], data['refined_from_run_id']), ('ACME向けに品番も付けて', self.source.pk))

    def test_a_normal_run_has_no_instruction_and_no_source(self):
        run = self.start()
        run.refresh_from_db()
        data = runs.serialize_run(run)
        self.assertEqual((data['refinement_instruction'], data['refined_from_run_id']), (None, None))

    def test_the_source_link_becomes_null_when_the_source_run_is_deleted_and_the_instruction_stays(self):
        run = self.start({'refinement': {'instruction': '品番も付けて', 'from_run_id': self.source.pk}})
        AIAnalysisRun.objects.filter(pk=self.source.pk).delete()
        run.refresh_from_db()
        self.assertEqual((run.refined_from_run_id, run.refinement_instruction), (None, '品番も付けて'))

    def test_the_history_is_visible_only_to_the_owner_and_admins_like_other_run_data(self):
        run = self.start({'refinement': {'instruction': '品番も付けて', 'from_run_id': None}})
        self.assertEqual(list(runs.visible_runs(self.user, False).values_list('pk', flat=True)).count(run.pk), 1)
        self.assertEqual(list(runs.visible_runs(self.other, False).filter(pk=run.pk)), [])
        self.assertEqual(runs.visible_runs(self.other, True).filter(pk=run.pk).count(), 1)  # 管理者の全履歴の表示


# 分析の温度は、AI設定(DB)から取得する。このモジュールの試験は、DBを使わないため、従来の値(0.3)を返す。温度の取得そのものは、test_analysis_temperature.pyで確認する
def setUpModule():
    global _temperature_patch
    from unittest import mock
    _temperature_patch = mock.patch('ai.services.analysis_llm.get_analysis_temperature', return_value=0.3)
    _temperature_patch.start()


def tearDownModule():
    _temperature_patch.stop()
