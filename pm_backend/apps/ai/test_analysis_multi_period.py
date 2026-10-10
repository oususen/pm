"""複数の期間の変数(2026-10-07、BOSS承認)を検証する。

比べる期間(月ごと・前半と後半など)は、「名前_from」と「名前_to」の組を何組でも。全体の期間(period_from・period_to)は、分析案の期間に固定。
比べる期間の初期値はAIが目的・手順から読み取り、サーバーが、形式・開始日<=終了日・全体の期間の中、を確認する。
"""
import json

from django.test import SimpleTestCase

from ai.services import analysis_codegen_service as cg
from ai.services import analysis_template_params as params
from ai.services.analysis_plan_store import AnalysisError
from ai.test_analysis_codegen import CodegenBase, GOOD_PYTHON, OWNER

OUTER = ('2026-01-01', '2026-01-31')


def date_def(name, default=None, label=None):
    item = {'name': name, 'type': 'date', 'label': label or name}
    if default is not None:
        item['default'] = default
    return item


HALVES = [date_def('first_from', '2026-01-01'), date_def('first_to', '2026-01-15'), date_def('second_from', '2026-01-16'), date_def('second_to', '2026-01-31')]


class DefinitionTests(SimpleTestCase):
    def test_any_number_of_period_pairs_with_the_overall_period(self):
        three = HALVES + [date_def('third_from', '2026-01-10'), date_def('third_to', '2026-01-12')]
        overall = [date_def('period_from', '2026-01-01'), date_def('period_to', '2026-01-31')]
        for definitions in (HALVES, three, overall + HALVES, overall + three):
            with self.subTest(count=len(definitions)):
                self.assertEqual(len(params.validate_definitions(definitions)), len(definitions))

    def test_a_date_variable_needs_a_from_to_name_and_a_partner(self):
        bad = [
            [date_def('month', '2026-01-01')],                                             # 名前が、_from・_toで終わらない
            [date_def('first_from', '2026-01-01')],                                        # 相手(_to)がない
            [date_def('first_to', '2026-01-15')],                                          # 相手(_from)がない
            [date_def('first_from', '2026-01-01'), date_def('second_to', '2026-01-15')],  # 組になっていない
            [{'name': 'first_to', 'type': 'product_code', 'label': 'x', 'default': 'P-001'}, date_def('first_from', '2026-01-01')],  # 相手が日付でない
            [{'name': 'period_from', 'type': 'product_code', 'label': 'x', 'default': 'P-001'}, date_def('period_to', '2026-01-31')],  # period_*は日付
            [date_def('first_from', '2026-1-1'), date_def('first_to', '2026-01-15')],     # 日付の形
            [date_def('first_from', '2026-01-02'), date_def('first_to', '2026-01-01')],   # 開始日>終了日
        ]
        for definitions in bad:
            with self.subTest(definitions=str(definitions)[:70]), self.assertRaises(AnalysisError):
                params.validate_definitions(definitions)

    def test_a_date_variable_with_a_malformed_name_is_refused_even_next_to_a_valid_pair(self):
        # 組(a_from・a_to)の隣に、名前の形が崩れた日付の変数(ato)があっても、通さない
        pair = [date_def('ab_from', '2026-01-01'), date_def('ab_to', '2026-01-05')]
        for extra in ('abxyz', 'ab_fromx', 'abfrom', 'AB_to', 'abc'):  # 'abxyz'・'abc'は、末尾3文字を除くと、組の名前(ab)に見えるため、組の確認だけでは通ってしまう
            with self.subTest(extra=extra), self.assertRaises(AnalysisError):
                params.validate_definitions(pair + [date_def(extra, '2026-01-02')])

    def test_a_non_date_variable_may_end_with_to_or_from(self):
        # 名前が_toで終わる、日付でない変数(ship_toなど)は、そのまま使える
        defs = [{'name': 'ship_to', 'type': 'product_code', 'label': 'x', 'default': 'P-001'}]
        from unittest.mock import patch
        with patch.dict(params.TYPES['product_code'], {'exists': lambda value: value}):
            self.assertEqual(len(params.validate_definitions(defs)), 1)


class ContainmentTests(SimpleTestCase):
    def test_periods_inside_the_outer_period_pass(self):
        values = params.resolve_values(params.validate_definitions(HALVES), {}, outer=OUTER)
        self.assertEqual((values['first_from'], values['second_to']), ('2026-01-01', '2026-01-31'))

    def test_a_period_outside_the_outer_period_is_refused(self):
        for override in ({'first_from': '2025-12-31'}, {'second_to': '2026-02-01'}):
            with self.subTest(override=override), self.assertRaises(AnalysisError):
                params.resolve_values(params.validate_definitions(HALVES), override, outer=OUTER)

    def test_a_reversed_period_is_refused_at_reuse_too(self):
        with self.assertRaises(AnalysisError):
            params.resolve_values(params.validate_definitions(HALVES), {'first_from': '2026-01-20'}, outer=OUTER)  # first: 20日〜15日

    def test_the_overall_variables_define_the_outer_period_when_present(self):
        defs = params.validate_definitions([date_def('period_from', '2026-01-01'), date_def('period_to', '2026-01-31')] + HALVES)
        with self.assertRaises(AnalysisError):
            params.resolve_values(defs, {'period_to': '2026-01-20'}, outer=('2000-01-01', '2100-01-01'))  # 全体を20日までにすると、後半(〜31日)がはみ出す
        params.resolve_values(defs, {'period_to': '2026-01-31'}, outer=('2000-01-01', '2100-01-01'))

    def test_without_an_outer_period_only_the_order_is_checked(self):
        # 全体の期間がないとき(呼出し側が確認する)。開始<=終了は、確認する
        params.resolve_values(params.validate_definitions(HALVES), {})
        with self.assertRaises(AnalysisError):
            params.resolve_values(params.validate_definitions(HALVES), {'second_from': '2026-02-01'})


class ReuseTests(SimpleTestCase):
    """保存済みテンプレートの再利用(concrete_for)でも、比べる期間は、テンプレートの期間の中でなければならない。"""

    def template(self):
        from datetime import date
        from types import SimpleNamespace
        return SimpleNamespace(parameters=params.validate_definitions(HALVES), sql_steps=SourceTests.STEPS, python_code="emit_report('x')",
                               date_from=date(2026, 1, 1), date_to=date(2026, 1, 31))

    def test_values_inside_the_template_period_are_used_and_outside_values_are_refused(self):
        from ai.services.analysis_template_service import concrete_for
        steps, _python, values = concrete_for(self.template(), {'first_from': '2026-01-02', 'first_to': '2026-01-10'})
        self.assertIn("BETWEEN '2026-01-02' AND '2026-01-10'", steps[0]['query'])
        self.assertIn("BETWEEN '2026-01-16' AND '2026-01-31'", steps[1]['query'])  # 指定しない期間は、初期値
        for override in ({'first_from': '2025-12-31'}, {'second_to': '2026-02-01'}, {'first_from': '2026-01-20'}):
            with self.subTest(override=override), self.assertRaises(AnalysisError):
                concrete_for(self.template(), override)


class NormalizeTests(SimpleTestCase):
    def test_the_ai_gives_the_initial_dates_and_the_server_keeps_the_overall_period(self):
        raw = [date_def('period_from', '1999-01-01'), date_def('period_to', '1999-12-31')] + HALVES
        out = params.normalize_definitions(raw, *OUTER)
        defaults = {item['name']: item['default'] for item in out}
        self.assertEqual((defaults['period_from'], defaults['period_to']), OUTER)  # 全体の期間は、AIの値を使わない
        self.assertEqual((defaults['first_to'], defaults['second_from']), ('2026-01-15', '2026-01-16'))  # 比べる期間は、AIの値

    def test_a_compared_period_needs_an_initial_date_inside_the_plan_period(self):
        for raw in ([date_def('first_from'), date_def('first_to', '2026-01-15')],                                  # defaultがない
                    [date_def('first_from', '2025-12-01'), date_def('first_to', '2026-01-15')],                    # 全体の外
                    [date_def('first_from', '2026-01-01'), date_def('first_to', '2026-03-01')],                    # 全体の外
                    [date_def('first_from', '2026-01-20'), date_def('first_to', '2026-01-15')]):                   # 逆順
            with self.subTest(raw=str(raw)[:60]), self.assertRaises(AnalysisError):
                params.normalize_definitions(raw, *OUTER)


class SourceTests(SimpleTestCase):
    STEPS = [{'name': 'w_first', 'query': 'SELECT 1 FROM v_ai_shipment WHERE shipment_date BETWEEN {{first_from}} AND {{first_to}}'},
             {'name': 'w_second', 'query': 'SELECT 2 FROM v_ai_shipment WHERE shipment_date BETWEEN {{second_from}} AND {{second_to}}'}]

    def test_each_period_is_replaced_by_its_own_dates(self):
        defs = params.validate_definitions(HALVES)
        params.check_source(self.STEPS, "emit_report('x')", defs)
        steps, _python = params.concrete_code(self.STEPS, "emit_report('x')", params.resolve_values(defs, {}, outer=OUTER))
        self.assertIn("BETWEEN '2026-01-01' AND '2026-01-15'", steps[0]['query'])
        self.assertIn("BETWEEN '2026-01-16' AND '2026-01-31'", steps[1]['query'])

    def test_a_literal_date_and_unused_or_undeclared_periods_are_still_refused(self):
        defs = params.validate_definitions(HALVES)
        with self.assertRaises(params.SourceCheckError) as caught:  # 日付の直書き
            params.check_source(self.STEPS, "d = '2026-01-05'", defs)
        self.assertIn('parameters_literal_date', caught.exception.reasons)
        with self.assertRaises(params.SourceCheckError) as caught:  # 使われない期間
            params.check_source(self.STEPS[:1], "emit_report('x')", defs)
        self.assertEqual(caught.exception.reason, 'parameters_unused')
        self.assertEqual(caught.exception.names['parameters_unused'], ['second_from', 'second_to'])


def period_response(parameters=None, steps=None, python=None):
    steps = steps or SourceTests.STEPS
    body = {'steps': steps, 'python': python or GOOD_PYTHON, 'parameters': HALVES if parameters is None else parameters}
    return json.dumps(body, ensure_ascii=False)


class GenerationTests(CodegenBase):
    """コード生成: 複数の期間の変数を、サーバーが確認し、実行する形(各期間の日付を別々に入れた形)にする。"""

    def test_two_periods_become_separate_concrete_ranges_and_the_source_form_is_kept(self):
        plan = self.new_plan()
        self.generate(plan, period_response())
        state = self.current(plan)['codegen']
        self.assertEqual(state['status'], 'generated')
        queries = [step['query'] for step in state['steps']]
        self.assertIn("BETWEEN '2026-01-01' AND '2026-01-15'", queries[0])
        self.assertIn("BETWEEN '2026-01-16' AND '2026-01-31'", queries[1])  # 全体の期間を2回使った形(同じ条件)にならない
        names = [item['name'] for item in state['template_source']['parameters']]
        self.assertEqual(names, ['first_from', 'first_to', 'second_from', 'second_to'])
        self.assertIn('{{first_from}}', state['template_source']['steps'][0]['query'])

    def test_invalid_periods_from_the_ai_fail_with_a_fixed_reason(self):
        bad = [
            [date_def('first_from', '2025-12-01'), date_def('first_to', '2026-01-15'), date_def('second_from', '2026-01-16'), date_def('second_to', '2026-01-31')],  # 全体の外
            [date_def('first_from', '2026-01-20'), date_def('first_to', '2026-01-15'), date_def('second_from', '2026-01-16'), date_def('second_to', '2026-01-31')],  # 逆順
            [date_def('first_from', '2026-01-01'), date_def('first_to', '2026-01-15'), date_def('second_from', '2026-01-16')],                                       # 組でない
            [date_def('first_from'), date_def('first_to'), date_def('second_from', '2026-01-16'), date_def('second_to', '2026-01-31')],                              # defaultがない
        ]
        for parameters in bad:
            with self.subTest(parameters=str(parameters)[:60]):
                plan = self.new_plan()
                self.generate(plan, period_response(parameters))
                state = self.current(plan)['codegen']
                self.assertEqual((state['status'], state['reasons'][0], len(state['reasons'])), ('failed', 'parameters_invalid', 2))
                self.assertNotIn('template_source', state)

    def test_the_instruction_explains_the_compared_periods(self):
        rule = cg.PARAMETER_RULE
        for part in ('期間を分けて比べる分析', '「名前_from」と「名前_to」の2つの日付の変数', 'aug_from・aug_to と sep_from・sep_to',
                     '比べる2つの期間の両方に、そのまま使わない', '比べる期間・除く期間の default は必要', '全体の期間の中に入れ'):
            self.assertIn(part, rule)


class ExampleTests(CodegenBase):
    """指示に入れた、期間を分けて比べる分析の見本(DeepSeekの案の形。BOSS承認 2026-10-07)。見本そのものが、実際の生成と同じ検査に通ること。"""

    def example_response(self, dates=None):
        example = json.loads(json.dumps(cg.PERIOD_EXAMPLE))
        dates = dates or {'a_from': '2026-01-01', 'a_to': '2026-01-15', 'b_from': '2026-01-16', 'b_to': '2026-01-31'}  # テストの分析案の期間(1月)の中に収める
        for item in example['parameters']:
            item['default'] = dates[item['name']]
        return json.dumps(example, ensure_ascii=False)

    def test_the_example_passes_the_same_checks_as_a_real_generation(self):
        plan = self.new_plan()
        self.generate(plan, self.example_response())
        state = self.current(plan)['codegen']
        self.assertEqual((state['status'], state.get('reasons')), ('generated', None))
        queries = [step['query'] for step in state['steps']]
        self.assertIn("BETWEEN '2026-01-01' AND '2026-01-15'", queries[0])
        self.assertIn("BETWEEN '2026-01-16' AND '2026-01-31'", queries[0])  # 1つの手順で、2つの期間を、別々の範囲として使う
        self.assertEqual([item['name'] for item in state['template_source']['parameters']], ['a_from', 'a_to', 'b_from', 'b_to'])

    def test_every_declared_variable_is_used_and_no_date_is_written_in_the_code(self):
        example = cg.PERIOD_EXAMPLE
        code = ' '.join(step['query'] for step in example['steps']) + example['python']
        for item in example['parameters']:
            self.assertIn('{{%s}}' % item['name'], code)
        self.assertFalse(params.DATE_LITERAL_PATTERN.search(code))  # 日付は、parametersのdefaultにだけある

    def test_the_example_is_inside_the_instruction_with_the_two_rules(self):
        import json as _json
        rule = cg.PARAMETER_RULE
        self.assertIn(_json.dumps(cg.PERIOD_EXAMPLE, ensure_ascii=False), rule)
        for part in ('CASE WHEN により期間にラベルを付けて集計', 'SUM(CASE WHEN ...) により期間を横に並べる', 'JOIN で結合する形は、条件を取り違えやすい',
                     '宣言した変数は、すべて、最初の集計の条件で使う', 'default の日付は、この例の値で、実際は、目的・手順から読み取る'):
            self.assertIn(part, rule)
        self.assertIn('中間テーブルと同じ名前のWITHで、問い合わせ全体を包まない', cg.SYSTEM_PROMPT)


def setUpModule():
    global _temperature_patch
    from unittest import mock
    _temperature_patch = mock.patch('ai.services.analysis_llm.get_analysis_temperature', return_value=0.3)
    _temperature_patch.start()


def tearDownModule():
    _temperature_patch.stop()
