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

    def test_a_template_superseded_while_waiting_for_the_ai_is_not_recommended(self):
        row = self.approved(name='応答待ちで置換される')
        keep = self.approved(name='残る', purpose='残る目的', category='quality')
        self.reply = ai_reply(template_ids=[row.pk, keep.pk])
        original = self.fake_chat

        def change_during_the_call(messages, provider, **kwargs):
            AIAnalysisTemplate.objects.filter(pk=row.pk).update(status='superseded')
            AIAnalysisTemplate.objects.filter(pk=keep.pk).update(name='応答中に変わった名称')
            return original(messages, provider, **kwargs)

        with patch.object(chat_service, '_chat', side_effect=change_during_the_call):
            data = self.ask().data
        self.assertEqual([(t['id'], t['name']) for t in data['templates']], [(keep.pk, '応答中に変わった名称')])

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


class FakeRedactor:
    """登録名称(ACME・山田)を、コードへ置換する。"""

    def redact_text(self, text):
        return text.replace('ACME', 'CUST-001').replace('山田', 'EMP-007')


class ConsultExternalTests(ConsultBase):
    """社外のAI(選択に従う)へ送るとき: 了承の確認・コード置換・使えないときは代替しない(BOSS承認 2026-10-06)。"""

    def setUp(self):
        super().setUp()
        self.external_calls = []
        self.external_reply = ai_reply(reply='社外AIの返事です。', draft_purpose='CUST-001の出荷を比較する')
        for target, name, value in (
            (consult, 'resolve_planning_provider', lambda data: (data.get('provider', 'qwen'), data.get('model') or chat_service.MODEL)),
            (consult, 'build_analysis_code_redactor', lambda: FakeRedactor()),
            (consult.analysis_llm, 'request_external_json', self.fake_external),
        ):
            patcher = patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def fake_external(self, provider, model, messages):
        self.external_calls.append((provider, model, messages))
        if isinstance(self.external_reply, Exception):
            raise self.external_reply
        return self.external_reply

    def ask_external(self, messages=ASK, **extra):
        body = {'provider': 'openrouter', 'model': 'm-ext', 'external_confirmed': True, **extra}
        return self.call('ai-analysis-consult', self.creator, data={'messages': messages, **body})

    def test_an_external_ai_needs_the_confirmation_and_nothing_is_sent_without_it(self):
        for value in (None, False, 'true', 1, 'yes'):
            with self.subTest(value=value):
                body = {'messages': ASK, 'provider': 'openrouter', 'model': 'm-ext'}
                if value is not None:
                    body['external_confirmed'] = value
                self.assertEqual(self.call('ai-analysis-consult', self.creator, data=body).status_code, 409)
        self.assertEqual((self.external_calls, self.chat_calls), ([], []))

    def test_the_selected_external_ai_is_called_with_code_replaced_text_and_the_local_ai_is_not(self):
        approved = self.approved(name='ACME向けの出荷', purpose='山田さんの担当の出荷を比べる', category='shipment')
        history = [{'role': 'user', 'content': 'ACMEの出荷を比べたい'}, {'role': 'assistant', 'content': 'ACMEは何月ですか？'}, {'role': 'user', 'content': '山田が8月です'}]
        response = self.ask_external(history)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.chat_calls, [])
        provider, model, messages = self.external_calls[0]
        self.assertEqual((provider, model), ('openrouter', 'm-ext'))
        self.assertEqual([m['role'] for m in messages], ['system', 'user', 'assistant', 'user'])
        self.assertEqual([m['content'] for m in messages[1:]], ['CUST-001の出荷を比べたい', 'CUST-001は何月ですか？', 'EMP-007が8月です'])
        everything = json.dumps(messages, ensure_ascii=False)
        self.assertNotIn('ACME', everything); self.assertNotIn('山田', everything)
        self.assertIn(f'ID {approved.pk}: CUST-001向けの出荷(カテゴリ: 出荷、目的: EMP-007さんの担当の出荷を比べる)', messages[0]['content'])
        data = response.data
        self.assertEqual((data['reply'], data['draft']['purpose'], data['external'], data['provider'], data['model']),
                         ('社外AIの返事です。', 'CUST-001の出荷を比較する', True, 'openrouter', 'm-ext'))
        self.assertEqual(data['sent_text'], 'EMP-007が8月です')

    def test_the_selection_is_passed_to_the_provider_check(self):
        with patch.object(consult, 'resolve_planning_provider', return_value=('deepseek', 'd-model')) as resolve:
            self.assertEqual(self.ask_external(provider='deepseek', model='d-model').status_code, 200)
        resolve.assert_called_once_with({'provider': 'deepseek', 'model': 'd-model'})
        self.assertEqual(self.external_calls[0][:2], ('deepseek', 'd-model'))

    def test_an_unavailable_external_ai_stops_without_falling_back_to_the_local_ai(self):
        with patch.object(consult, 'resolve_planning_provider', side_effect=consult.AnalysisError('外部AIへの送信が管理設定で許可されていません。', 403)):
            response = self.ask_external()
        self.assertEqual(response.status_code, 403)
        self.assertEqual((self.external_calls, self.chat_calls), ([], []))

    def test_a_replacement_failure_stops_before_sending(self):
        from django.db import DatabaseError
        with patch.object(consult, 'build_analysis_code_redactor', side_effect=DatabaseError('SECRET-DB')):
            response = self.ask_external()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('SECRET', json.dumps(response.data, ensure_ascii=False))

        class Broken:
            def redact_text(self, text):
                raise DatabaseError('SECRET-DB')

        with patch.object(consult, 'build_analysis_code_redactor', lambda: Broken()):
            response = self.ask_external()
        self.assertEqual(response.status_code, 503)
        self.assertEqual((self.external_calls, self.chat_calls), ([], []))

    def test_an_external_failure_is_a_fixed_503_without_the_provider_text(self):
        self.external_reply = chat_service.LocalAIError('SECRET-PROVIDER 残高不足')
        response = self.ask_external()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('SECRET', json.dumps(response.data, ensure_ascii=False))

    def test_an_unusable_external_output_is_a_502(self):
        self.external_reply = 'JSONではない SECRET'
        response = self.ask_external()
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('SECRET', json.dumps(response.data, ensure_ascii=False))

    def test_the_local_ai_path_is_unchanged_and_sends_the_original_text(self):
        self.approved(name='ACME向け', purpose='山田の目的')
        response = self.call('ai-analysis-consult', self.creator, data={'messages': [{'role': 'user', 'content': 'ACMEの件'}], 'provider': 'qwen'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.data['external'], response.data['sent_text']), (False, None))
        self.assertEqual(self.external_calls, [])
        self.assertEqual(self.chat_calls[0][0][1]['content'], 'ACMEの件')
        self.assertIn('ACME向け', self.chat_calls[0][0][0]['content'])

    def test_recommendations_still_come_from_the_db_for_an_external_ai(self):
        row = self.approved(name='ACME向け', purpose='山田の目的', category='quality')
        self.external_reply = ai_reply(template_ids=[row.pk, 999999])
        template = self.ask_external().data['templates'][0]
        self.assertEqual((template['id'], template['name'], template['purpose'], template['category_label']), (row.pk, 'ACME向け', '山田の目的', '品質'))


class ConsultRedactionFailureTests(ConsultExternalTests):
    def test_a_message_that_cannot_be_replaced_is_a_422_without_the_name_and_nothing_is_sent(self):
        class Ambiguous:
            def redact_text(self, text):
                raise consult.AnalysisError('名称「秘密の会社」が曖昧です', 400)

        with patch.object(consult, 'build_analysis_code_redactor', lambda: Ambiguous()):
            response = self.ask_external()
        self.assertEqual(response.status_code, 422)
        self.assertNotIn('秘密の会社', json.dumps(response.data, ensure_ascii=False))
        self.assertEqual((self.external_calls, self.chat_calls), ([], []))

    def test_a_template_that_cannot_be_replaced_blocks_the_send_with_a_424_instead_of_being_skipped(self):
        self.approved(name='置換できる', purpose='ふつうの目的')
        self.approved(name='秘密の会社向け', purpose='目的')

        class OnlyTemplatesFail:
            def redact_text(self, text):
                if '秘密の会社' in text:
                    raise consult.AnalysisError('名称「秘密の会社」が未登録です', 400)
                return text

        with patch.object(consult, 'build_analysis_code_redactor', lambda: OnlyTemplatesFail()):
            response = self.ask_external()
        self.assertEqual(response.status_code, 424)
        self.assertNotIn('秘密の会社', json.dumps(response.data, ensure_ascii=False))
        self.assertEqual((self.external_calls, self.chat_calls), ([], []))  # 除外して続けず、社外へは送らない


class ConsultRealExternalSelectionTests(ConsultBase):
    """consult経由で、実際の resolve_planning_provider(管理設定・外部送信の許可・APIキー)が働くことを確認する(置換器と社外の呼び出しだけ差し替える)。"""

    def setUp(self):
        super().setUp()
        patch.stopall()
        self.external_calls = []
        for target, name, value in (
            (chat_service, '_chat', self.fake_chat),
            (consult, 'build_analysis_code_redactor', lambda: FakeRedactor()),
            (consult.analysis_llm, 'request_external_json', lambda provider, model, messages: self.external_calls.append((provider, model)) or ai_reply()),
            (consult, 'get_qwen_analysis_timeout', lambda: 77),
        ):
            patcher = patch.object(target, name, value)
            patcher.start()
        self.addCleanup(patch.stopall)
        from ai.config.models import AIProviderConfig
        self.config = AIProviderConfig.objects.create(provider='openrouter', default_model='qwen/qwen3-30b-a3b-instruct-2507', is_enabled=True)

    def ask_real(self, **extra):
        body = {'provider': 'openrouter', 'model': 'google/gemma-4-26b-a4b-it', 'external_confirmed': True, **extra}
        return self.call('ai-analysis-consult', self.creator, data={'messages': ASK, **body})

    def allowed(self, key='KEY', transfer=True):
        patcher_a = patch('ai.services.analysis_planning_service.external_aggregate_transfer_allowed', lambda: transfer)
        patcher_b = patch.dict(chat_service.EXTERNAL_AGENT_PROVIDERS['openrouter'], {'api_key': key})
        patcher_a.start(); patcher_b.start()
        self.addCleanup(patcher_a.stop); self.addCleanup(patcher_b.stop)

    def test_all_settings_in_place_sends_to_the_selected_model(self):
        self.allowed()
        response = self.ask_real()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.external_calls, [('openrouter', 'google/gemma-4-26b-a4b-it')])
        self.assertEqual(self.chat_calls, [])

    def test_each_missing_setting_stops_the_send_without_falling_back(self):
        from ai.config.models import AIProviderConfig
        self.allowed(transfer=False)
        self.assertEqual(self.ask_real().status_code, 403)  # 外部送信が管理設定で許可されていない
        self.allowed(key='', transfer=False)
        self.assertEqual(self.ask_real().status_code, 403)  # 外部送信の許可が、APIキーより先に判定される
        self.allowed(key='', transfer=True)
        self.assertEqual(self.ask_real().status_code, 503)  # APIキー未設定
        self.allowed()
        self.assertEqual(self.ask_real(model='not/allowed-model').status_code, 400)  # 許可リストにないモデル
        AIProviderConfig.objects.filter(pk=self.config.pk).update(is_enabled=False)
        self.assertEqual(self.ask_real().status_code, 400)  # 管理設定で無効
        AIProviderConfig.objects.all().delete()
        self.assertEqual(self.ask_real().status_code, 400)  # 管理設定にプロバイダがない
        self.assertEqual((self.external_calls, self.chat_calls), ([], []))


class ConsultRealSelectionTests(ConsultBase):
    """provider の検証は、実際の関数(許可リスト・管理設定)に任せる。"""

    def setUp(self):
        super().setUp()
        patch.stopall()
        patcher = patch.object(chat_service, '_chat', side_effect=self.fake_chat)
        patcher.start()
        self.addCleanup(patch.stopall)

    def test_an_unknown_provider_or_a_bad_model_is_refused_before_any_call(self):
        for extra in ({'provider': 'foo'}, {'provider': 5}, {'provider': 'qwen', 'model': 'other-model'}, {'provider': ['qwen']}):
            with self.subTest(extra=extra):
                self.assertEqual(self.ask(**extra).status_code, 400)
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
        self.assertEqual(self.call('ai-analysis-consult', self.creator, data={'messages': ASK, 'temperature': 1}).status_code, 400)
        self.assertEqual(self.call('ai-analysis-consult', self.creator, data={}).status_code, 400)
        self.assertEqual(self.chat_calls, [])

    def test_keys_other_than_the_selection_and_the_confirmation_are_refused(self):
        for extra in ({'system': 'x'}, {'messages2': []}, {'num_predict': 9}):
            with self.subTest(extra=extra):
                self.assertEqual(self.ask(**extra).status_code, 400)
        self.assertEqual(self.chat_calls, [])

    def test_the_analysis_edit_permission_is_required(self):
        from accounts.models import UserPermission
        UserPermission.objects.filter(user=self.creator, resource='ai.analysis').update(can_edit=False)
        self.assertEqual(self.ask().status_code, 403)
        self.assertEqual(self.ask(user=self.other).status_code, 200)
        self.assertEqual(self.call('ai-analysis-consult', None, data={'messages': ASK}).status_code, 403)
        self.assertEqual(len(self.chat_calls), 1)
