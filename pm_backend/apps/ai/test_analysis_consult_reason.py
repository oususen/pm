"""相談の返答の検証(理由コードと、前後の余分な文字の読み捨て)の試験。DBを使わない。返答の中身は、エラーへ含めない。"""
import json

from django.test import SimpleTestCase

from ai.services.analysis_consult_service import PARSE_FAILURE_TEXT, _parse
from ai.services.analysis_plan_store import AnalysisError

# json_text_after は、後ろの余分な文字を読み捨てるため廃止(出なくなった)
REASONS = {'empty', 'code_fence', 'json_no_object', 'json_prefix_brace', 'json_prefix_truncated', 'json_truncated', 'json_syntax', 'json_not_object', 'reply_missing'}
GOOD = {'reply': '製品は絞りますか？', 'draft_purpose': None, 'template_ids': []}
GOOD_TEXT = json.dumps(GOOD, ensure_ascii=False)


class ConsultParseReasonTests(SimpleTestCase):
    def reason_of(self, raw):
        with self.assertRaises(AnalysisError) as caught:
            _parse(raw)
        error = caught.exception
        self.assertEqual(error.status_code, 502)
        self.assertEqual(dict(error.detail), {'detail': PARSE_FAILURE_TEXT, 'reason': error.reason})
        self.assertEqual(PARSE_FAILURE_TEXT, 'AIの返答を検証できませんでした。もう一度送ってください。')
        self.assertIn(error.reason, REASONS)
        return error

    def test_accepts_extra_text_around_the_first_object(self):
        cases = [
            GOOD_TEXT,
            '  ' + GOOD_TEXT + '\n',
            '前置きです。' + GOOD_TEXT,
            '<think>考え</think>' + GOOD_TEXT,
            '考え中です。\n\nでは返します。\n' + GOOD_TEXT,
            GOOD_TEXT + '\n\n以上です。',
            '前置き ' + GOOD_TEXT + ' 後ろの文章',
            GOOD_TEXT + '{"reply": "別のオブジェクト"}',  # 最初のオブジェクトだけを使う
            'Here is the JSON: ' + GOOD_TEXT + ' [1]',
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                self.assertEqual(_parse(raw), GOOD)

    def test_each_reason(self):
        cases = {
            'empty': ['', '   \n\t', None],
            'code_fence': ['```json\n{"reply": "x"}\n```', '  \n```\nabc', '```json\n{broken\n```'],
            # 前置きに { を含む(最初の { が前置き側で、オブジェクトとして読めない)、{ がない
            # { がなく、先頭が [ でもない(JSONで返していない)
            'json_no_object': ['これはJSONではありません', 'nul', 'Here: x', '<think>考え中です</think>', '<think>考え中</think>\n結論は、絞ることです。'],
            # 前置きに { があり、最初の { から読めない(入力の終わりではない): 前置きの中の { 、または文法の誤り
            'json_prefix_brace': ['メモ{a}です ' + GOOD_TEXT, '<think>{a}</think>' + GOOD_TEXT, '説明 {reply: 1}', '説明 {"reply": "x",}', '前置き { ' + GOOD_TEXT],
            # 前置きのあとで、JSONが途中で終わっている(入力の終わりで読めない、または閉じない文字列)
            'json_prefix_truncated': ['説明 {"reply": "abc', '説明 {"reply": ', '説明 {', '説明 {"reply": "a", "template_ids": [1,', '前置き {"reply": "x", "draft_purpose": "ab'],
            'json_truncated': ['{"reply": "abc', '{"reply": ', '{"reply": "a"', '{"reply": "a", "template_ids": [1,', '{', '  {"reply": "abc\n'],
            'json_syntax': ['{reply: 1}', '{"reply": "x",}', "{'reply': 'x'}", '{"reply" "x"}', '[1,, 2]', '[1 2]', '{"a": 1 "b": 2}', '[1, 2'],
            'json_not_object': ['[1, 2]', '"text"', '123', 'null', '[{"reply": "x"}]'],
            'reply_missing': ['{}', '{"reply": 5}', '{"reply": null}', '{"reply": ""}', '{"reply": "  "}', '{"draft_purpose": "x"}',
                              '前置き {"draft_purpose": "x"}', '前置き {"reply": ""} 後ろ', '{"draft_purpose": "x"} {"reply": "後のオブジェクト"}'],
        }
        for reason, raws in cases.items():
            for raw in raws:
                with self.subTest(reason=reason, raw=raw):
                    self.assertEqual(self.reason_of(raw).reason, reason)

    def test_retired_codes_are_never_returned(self):
        self.assertNotIn('json_invalid', REASONS)
        self.assertNotIn('json_text_after', REASONS)
        self.assertNotIn('json_text_before', REASONS)  # 案Gで3コードに分けて廃止
        for raw in ['x', '{', '{reply: 1}', GOOD_TEXT.replace('"reply"', 'reply') + ' y', '[1,, 2]', '{"reply": "x"} y {', '{} 5']:
            with self.subTest(raw=raw):
                try:
                    _parse(raw)
                except AnalysisError as error:
                    self.assertNotIn(error.reason, {'json_invalid', 'json_text_after', 'json_text_before'})

    def test_priority(self):
        # コードブロックで囲まれた返答は、中身が正常でも拒否(案Bは採用していない)
        self.assertEqual(self.reason_of('```json\n' + GOOD_TEXT + '\n```').reason, 'code_fence')
        self.assertEqual(self.reason_of('```\n[1]\n```').reason, 'code_fence')
        # 空白だけは code_fence でなく empty
        self.assertEqual(self.reason_of(' \n ').reason, 'empty')
        # 最初の { 以外の { からは再試行しない(前置きの { が読めなければ、後ろに正常なオブジェクトがあっても拒否)
        self.assertEqual(self.reason_of('{ ' + GOOD_TEXT).reason, 'json_syntax')
        self.assertEqual(self.reason_of('前置き { ' + GOOD_TEXT).reason, 'json_prefix_brace')
        # 前置きの { から読めない場合と、前置きのあとで途中で切れた場合の区別
        self.assertEqual(self.reason_of('説明 {reply: 1}').reason, 'json_prefix_brace')
        self.assertEqual(self.reason_of('説明 {"reply": "abc').reason, 'json_prefix_truncated')
        # { がなければ、前置きの有無によらず json_no_object(JSONとして読める配列・数値などは json_not_object)
        self.assertEqual(self.reason_of('<think>考え</think>').reason, 'json_no_object')
        self.assertEqual(self.reason_of('123').reason, 'json_not_object')
        # 読めた最初のオブジェクトに reply がなければ、後ろに正常なオブジェクトがあっても reply_missing
        self.assertEqual(self.reason_of('{"x": 1}' + GOOD_TEXT).reason, 'reply_missing')
        # 先頭が [ のときは、後ろに正常なオブジェクトがあっても取り出さない
        self.assertEqual(self.reason_of('[1] ' + GOOD_TEXT).reason, 'json_syntax')
        self.assertEqual(self.reason_of('[' + GOOD_TEXT + ']').reason, 'json_not_object')
        # 先頭が { で途中で切れていれば json_truncated(前置きがあるときは json_prefix_truncated)
        self.assertEqual(self.reason_of('{"reply": "x", "draft_purpose": "ab').reason, 'json_truncated')
        self.assertEqual(self.reason_of('前置き {"reply": "x", "draft_purpose": "ab').reason, 'json_prefix_truncated')

    def test_error_and_result_have_no_discarded_content(self):
        secret = 'SECRETマーカー'
        rejected = [secret, '```' + secret, '[' + secret + ']', json.dumps([secret]), json.dumps({'reply': 5, 'x': secret}), '{"reply": "' + secret,
                    '{' + secret + '}', '<think>' + secret + '</think>{}', '{"reply": "' + secret + '", "n": ',
                    secret + ' {"draft_purpose": "x"}', secret + ' {a} ' + GOOD_TEXT, '{"reply": ""} ' + secret, '{"x": 1} ' + secret + ' ' + GOOD_TEXT]
        for raw in rejected:
            with self.subTest(raw=raw):
                error = self.reason_of(raw)
                text = ' '.join([str(error), str(error.detail), repr(error.detail), repr(error.reason), repr(error.args[0])])
                self.assertNotIn('SECRET', text)
                self.assertNotIn('マーカー', text)
                # 返答の長さ・エラー位置の数値が出ない(固定文と固定コードだけで、数字を含まない)
                self.assertFalse(any(ch.isdigit() for ch in text), text)
                self.assertIsNone(error.__cause__)  # 例外の連鎖から、返答の一部が出ない
                self.assertTrue(error.__suppress_context__ or error.__context__ is None)
        # 受け入れた場合も、読み捨てた部分は返り値に出ない(返り値は読めたオブジェクトそのもの)
        for raw in [secret + ' ' + GOOD_TEXT, GOOD_TEXT + ' ' + secret, secret + GOOD_TEXT + secret]:
            with self.subTest(raw=raw):
                data = _parse(raw)
                self.assertEqual(data, GOOD)
                self.assertNotIn('SECRET', json.dumps(data, ensure_ascii=False))

    def test_other_errors_unchanged(self):
        error = AnalysisError('x')
        self.assertEqual((error.status_code, error.detail, getattr(error, 'reason', None)), (400, 'x', None))
        error = AnalysisError('y', 503)
        self.assertEqual((error.status_code, str(error.detail)), (503, 'y'))
