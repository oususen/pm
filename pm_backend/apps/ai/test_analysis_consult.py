"""分析の前のAIとの目的の相談と、承認済みテンプレートの推薦(段階1)を、実ユーザー・実効権限・一時SQLiteで検証する。

AIの呼び出し(ローカルQwen)だけを差し替える。社外AIが呼ばれないこと、保存しないこと、AIの出力の確認(日付・ID)を確認する。
"""
import json
from datetime import datetime
from unittest.mock import patch

from django.test import override_settings

from ai.models import AIAnalysisTemplate
from ai.services import analysis_consult_service as consult
from ai.services import chat_service
from ai.test_analysis_template_review import ReviewBase

ASK = [{'role': 'user', 'content': '8月と9月の出荷を比べたい'}]


def ai_reply(**overrides):
    body = {'reply': '製品は絞りますか？', 'draft_purpose': None, 'date_from': None, 'date_to': None, 'template_ids': []}
    body.update(overrides)
    return json.dumps(body, ensure_ascii=False)


@override_settings(ALLOWED_HOSTS=['testserver'])
class ConsultBase(ReviewBase):
    def setUp(self):
        super().setUp()
        self.chat_calls = []
        self.reply = ai_reply()
        for target, value in (
            (consult, {'resolve_planning_provider': lambda data: ('qwen', chat_service.MODEL), 'get_qwen_analysis_timeout': lambda: 77}),
        ):
            for name, replacement in value.items():
                patcher = patch.object(target, name, replacement)
                patcher.start()
                self.addCleanup(patcher.stop)
        patcher = patch.object(chat_service, '_chat', side_effect=self.fake_chat)
        patcher.start()
        self.addCleanup(patcher.stop)

    def fake_chat(self, messages, provider, **kwargs):
        self.chat_calls.append((messages, provider, kwargs))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply

    def ask(self, messages=ASK, user=None, **extra):
        return self.call('ai-analysis-consult', user or self.creator, data={'messages': messages, **extra})

    def approved(self, **overrides):
        return self.row(status='approved', **overrides)


class ConsultFlowTests(ConsultBase):
    def test_returns_reply_draft_and_recommendations_from_the_db(self):
        a = self.approved(name='月別出荷の比較', purpose='月ごとの出荷量を比べる', category='shipment')
        self.reply = ai_reply(reply='期間は8月から9月ですね。', draft_purpose='8月と9月の出荷量を比較する', date_from='2026-08-01', date_to='2026-09-30',
                              template_ids=[a.pk])
        response = self.ask()
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data['reply'], '期間は8月から9月ですね。')
        self.assertEqual(data['draft'], {'purpose': '8月と9月の出荷量を比較する', 'date_from': '2026-08-01', 'date_to': '2026-09-30'})
        self.assertEqual([(t['id'], t['name'], t['purpose'], t['category'], t['category_label']) for t in data['templates']],
                         [(a.pk, '月別出荷の比較', '月ごとの出荷量を比べる', 'shipment', '出荷')])
        self.assertEqual((data['provider'], data['model']), ('qwen', chat_service.MODEL))

    def test_only_the_local_qwen_is_called_with_json_mode_the_saved_timeout_and_never_an_external_ai(self):
        with patch('ai.services.analysis_llm.request_external_json', side_effect=AssertionError('社外AIは呼ばない')) as external:
            self.assertEqual(self.ask().status_code, 200)
        external.assert_not_called()
        messages, provider, kwargs = self.chat_calls[0]
        self.assertEqual((provider, kwargs['json_mode'], kwargs['timeout']), ('qwen', True, 77))
        self.assertEqual([m['role'] for m in messages], ['system', 'user'])
        self.assertEqual(messages[1]['content'], '8月と9月の出荷を比べたい')

    def test_system_prompt_has_approved_templates_today_and_views_but_not_unapproved_ones_or_data(self):
        approved = self.approved(name='承認済みの名称', purpose='承認済みの目的')
        hidden = {s: self.row(status=s, name=f'非承認{s}') for s in ('pending_admin', 'rejected', 'superseded')}
        self.assertEqual(self.ask().status_code, 200)
        system = self.chat_calls[0][0][0]['content']
        self.assertIn(f'ID {approved.pk}: 承認済みの名称(カテゴリ: その他、目的: 承認済みの目的)', system)
        for name in ('非承認pending_admin', '非承認rejected', '非承認superseded'):
            self.assertNotIn(name, system)
        self.assertIn('v_ai_shipment', system)
        self.assertIn(consult._today().isoformat(), system)

    def test_the_business_day_changes_at_8(self):
        with patch.object(consult, 'datetime') as clock:
            clock.now.return_value = datetime(2026, 1, 19, 7, 59)
            self.assertEqual(consult._today().isoformat(), '2026-01-18')
            clock.now.return_value = datetime(2026, 1, 19, 8, 0)
            self.assertEqual(consult._today().isoformat(), '2026-01-19')

    def test_nothing_is_stored(self):
        before = AIAnalysisTemplate.objects.count()
        self.assertEqual(self.ask().status_code, 200)
        self.assertEqual(AIAnalysisTemplate.objects.count(), before)

    def test_the_whole_conversation_is_passed_in_order_without_a_count_limit(self):
        history = []
        for index in range(30):
            history += [{'role': 'user', 'content': f'質問{index}'}, {'role': 'assistant', 'content': f'答え{index}'}]
        history.append({'role': 'user', 'content': '最後'})
        self.assertEqual(self.ask(history).status_code, 200)
        sent = self.chat_calls[0][0][1:]
        self.assertEqual([(m['role'], m['content']) for m in sent], [(m['role'], m['content']) for m in history])


class ConsultVerificationTests(ConsultBase):
    def test_template_ids_keep_only_real_approved_ones_without_duplicates_up_to_ten_in_the_ai_order(self):
        rows = [self.approved(name=f'承認{i}') for i in range(12)]
        pending = self.row(status='pending_admin')
        rejected = self.row(status='rejected')
        ids = [rows[3].pk, pending.pk, rows[3].pk, 999999, True, '5', None, 2.0, rejected.pk] + [r.pk for r in rows if r.pk != rows[3].pk]
        self.reply = ai_reply(template_ids=ids)
        data = self.ask().data
        expected = [rows[3].pk] + [r.pk for r in rows if r.pk != rows[3].pk][:9]
        self.assertEqual([t['id'] for t in data['templates']], expected)
        self.assertEqual(len(data['templates']), 10)

    def test_template_ids_that_are_not_a_list_are_ignored(self):
        self.approved()
        for value in ('abc', 5, {'a': 1}, None):
            with self.subTest(value=value):
                self.reply = ai_reply(template_ids=value)
                self.assertEqual(self.ask().data['templates'], [])

    def test_displayed_template_values_come_from_the_db_not_from_the_ai_text(self):
        row = self.approved(name='DBの名称', purpose='DBの目的')
        self.reply = ai_reply(template_ids=[row.pk], name='AIが作った名称', templates=[{'id': row.pk, 'name': 'AIの名称'}])
        template = self.ask().data['templates'][0]
        self.assertEqual((template['name'], template['purpose'], template['version']), ('DBの名称', 'DBの目的', 1))
        self.assertEqual((template['date_from'], template['date_to']), (row.date_from.isoformat(), row.date_to.isoformat()))

    def test_invalid_dates_are_dropped_not_replaced(self):
        for start, end in (('2026-09-30', '2026-08-01'), ('2026/08/01', '2026-09-30'), ('2026-08-01', None), (None, '2026-09-30'),
                           ('あいう', '2026-09-30'), (20260801, 20260930), ('2026-02-30', '2026-03-01')):
            with self.subTest(start=start, end=end):
                self.reply = ai_reply(draft_purpose='目的の文案', date_from=start, date_to=end)
                draft = self.ask().data['draft']
                self.assertEqual((draft['purpose'], draft['date_from'], draft['date_to']), ('目的の文案', None, None))

    def test_a_blank_or_non_text_purpose_draft_is_none(self):
        for value in ('', '  ', None, 5, ['x']):
            with self.subTest(value=value):
                self.reply = ai_reply(draft_purpose=value)
                self.assertIsNone(self.ask().data['draft']['purpose'])

    def test_an_unusable_ai_output_is_a_fixed_502_without_the_raw_text(self):
        for raw in ('これはJSONではない SECRET-AI', '[1, 2]', json.dumps({'draft_purpose': 'x'}), json.dumps({'reply': ''}), json.dumps({'reply': 5})):
            with self.subTest(raw=raw[:20]):
                self.reply = raw
                response = self.ask()
                self.assertEqual(response.status_code, 502)
                self.assertNotIn('SECRET', json.dumps(response.data, ensure_ascii=False))

    def test_a_local_ai_failure_is_a_fixed_503_without_the_exception_text(self):
        self.reply = chat_service.LocalAIError('SECRET-OLLAMA')
        response = self.ask()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('SECRET', json.dumps(response.data, ensure_ascii=False))

    def test_an_unavailable_local_ai_stops_before_calling_it(self):
        with patch.object(consult, 'resolve_planning_provider', side_effect=consult.AnalysisError('ローカルQwenが無効です。', 503)):
            response = self.ask()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.chat_calls, [])


class ConsultRealProviderCheckTests(ConsultBase):
    """resolve_planning_provider の差し替えを外し、実関数がローカルQwenだけを確認することを検証する(planning_optionsだけ差し替える)。"""

    def setUp(self):
        super().setUp()
        patch.stopall()  # 親の差し替えを外す(次で必要な分だけ入れ直す)
        patcher = patch.object(chat_service, '_chat', side_effect=self.fake_chat)
        patcher.start()
        self.addCleanup(patch.stopall)
        patcher = patch.object(consult, 'get_qwen_analysis_timeout', lambda: 77)
        patcher.start()

    def test_the_real_check_asks_for_qwen_only_and_passes_when_it_is_enabled(self):
        with patch('ai.services.analysis_planning_service.planning_options', return_value={'available': True}):
            self.assertEqual(self.ask().status_code, 200)
        self.assertEqual(self.chat_calls[0][1], 'qwen')

    def test_a_disabled_qwen_stops_with_503_before_calling_the_ai(self):
        with patch('ai.services.analysis_planning_service.planning_options', return_value={'available': False}):
            response = self.ask()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.chat_calls, [])


class ConsultInputTests(ConsultBase):
    def test_bad_messages_are_refused_before_calling_the_ai(self):
        user = lambda text: {'role': 'user', 'content': text}
        bot = lambda text: {'role': 'assistant', 'content': text}
        cases = {
            'not a list': 'abc', 'empty': [], 'not dicts': ['a'], 'bad role': [{'role': 'system', 'content': 'x'}],
            'extra key': [{'role': 'user', 'content': 'x', 'name': 'y'}], 'content not text': [{'role': 'user', 'content': 5}],
            'blank content': [user('  ')], 'starts with assistant': [bot('a'), user('b')], 'ends with assistant': [user('a'), bot('b')],
            'not alternating': [user('a'), user('b')],
        }
        for label, messages in cases.items():
            with self.subTest(label=label):
                self.assertEqual(self.ask(messages).status_code, 400)
        self.assertEqual(self.call('ai-analysis-consult', self.creator, data={'messages': ASK, 'provider': 'openrouter'}).status_code, 400)
        self.assertEqual(self.call('ai-analysis-consult', self.creator, data={}).status_code, 400)
        self.assertEqual(self.chat_calls, [])

    def test_an_attempt_to_choose_another_ai_is_refused(self):
        response = self.ask(model='x')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.chat_calls, [])

    def test_the_analysis_edit_permission_is_required(self):
        from accounts.models import UserPermission
        UserPermission.objects.filter(user=self.creator, resource='ai.analysis').update(can_edit=False)
        self.assertEqual(self.ask().status_code, 403)
        self.assertEqual(self.ask(user=self.other).status_code, 200)
        self.assertEqual(self.call('ai-analysis-consult', None, data={'messages': ASK}).status_code, 403)
        self.assertEqual(len(self.chat_calls), 1)
