"""コード生成の失敗の理由を、原因ごとに区別する(2026-10-07、BOSS承認)。

変数の定義の不備(parameters_invalid + 原因の固定コード + 該当する変数の名前)と、Pythonの構文の誤り(python:syntax_error + 置き換え前後・種類の固定コード)。
AIの自由な文章は、保存・表示しない。
"""
import json

from unittest.mock import patch

from django.test import SimpleTestCase

from ai.services import analysis_codegen_service as cg
from ai.services import analysis_template_params as params
from ai.test_analysis_codegen import CodegenBase, GOOD_PYTHON, GOOD_STEPS, PARAM_DEFS, param_response
from ai.test_analysis_multi_period import HALVES, date_def, period_response


def altered(index, **changes):
    items = [dict(item) for item in HALVES]
    items[index].update(changes)
    return items


class DiagnosticBase(CodegenBase):
    def setUp(self):
        super().setUp()
        patcher = patch.dict(params.TYPES['customer_code'], {'exists': lambda value: value == 'C-001'})
        patcher.start()
        self.addCleanup(patcher.stop)


class DefinitionReasonTests(DiagnosticBase):
    def assert_reason(self, response, code, names=None):
        plan = self.new_plan()
        self.generate(plan, response)
        state = self.current(plan)['codegen']
        self.assertEqual((state['status'], state['reasons']), ('failed', ['parameters_invalid', code]))
        if names is None:
            self.assertNotIn('reason_names', state)
        else:
            self.assertEqual(state['reason_names'], {code: names})
            self.assertEqual(state['history'][-1]['names'], {code: names})

    def test_each_definition_problem_has_its_own_fixed_code_and_names_the_variables(self):
        cases = [
            ('変数の名前が文字列でない', period_response(parameters=[{'name': [], 'type': 'date', 'label': 'x', 'default': '2026-01-01'}]), 'parameters_def_name', None),
            ('名前の形が不正(大文字)', period_response(parameters=altered(0, name='First_from')), 'parameters_def_name', None),
            ('日付の変数の名前が、_from・_toでない', period_response(parameters=altered(0, name='first_start')), 'parameters_def_name', ['first_start']),
            ('種類が不正', period_response(parameters=altered(0, type='supplier')), 'parameters_def_type', ['first_from']),
            ('ラベルがない', period_response(parameters=altered(0, label='')), 'parameters_def_label', ['first_from']),
            ('初期値がない', period_response(parameters=[{k: v for k, v in item.items() if k != 'default'} if i == 0 else item for i, item in enumerate(HALVES)]), 'parameters_def_default', ['first_from']),
            ('組が欠けている', period_response(parameters=HALVES[:3]), 'parameters_def_pair', ['second_from']),
            ('日付の形が不正', period_response(parameters=altered(0, default='2026-1-1')), 'parameters_def_date', ['first_from']),
            ('開始日が終了日より後', period_response(parameters=altered(0, default='2026-01-20')), 'parameters_def_order', ['first_from', 'first_to']),
            ('全体の期間の外', period_response(parameters=altered(0, default='2025-12-01')), 'parameters_def_outside', ['first_from', 'first_to']),
            ('登録されていない顧客コード', param_response(parameters=[{**PARAM_DEFS[0], 'default': 'C-999'}, *PARAM_DEFS[1:]]), 'parameters_def_unregistered', ['customer_code']),
            ('コードの値の形が不正', param_response(parameters=[{**PARAM_DEFS[0], 'default': 'C 001'}, *PARAM_DEFS[1:]]), 'parameters_def_value', ['customer_code']),
            ('項目の形が不正', period_response(parameters=['x']), 'parameters_def_format', None),
        ]
        for label, response, code, names in cases:
            with self.subTest(label):
                self.assert_reason(response, code, names)

    def test_a_successful_generation_has_no_reason_names(self):
        plan = self.new_plan()
        self.generate(plan, period_response())
        state = self.current(plan)['codegen']
        self.assertEqual(state['status'], 'generated')
        self.assertNotIn('reason_names', state)


class SyntaxReasonTests(DiagnosticBase):
    def reasons(self, response):
        plan = self.new_plan()
        self.generate(plan, response)
        state = self.current(plan)['codegen']
        self.assertEqual(state['status'], 'failed')
        return state['reasons']

    def test_a_syntax_error_in_code_without_variables_reports_only_its_kind(self):
        reasons = self.reasons(json.dumps({'steps': GOOD_STEPS, 'python': GOOD_PYTHON + "\nx = ("}, ensure_ascii=False))
        self.assertIn('python:syntax_error', reasons)
        self.assertIn('python_syntax_bracket', reasons)
        self.assertNotIn('python_syntax_after_substitution', reasons); self.assertNotIn('python_syntax_in_source', reasons)

    def test_replacing_a_variable_inside_a_python_string_is_reported_as_broken_by_the_replacement(self):
        # Pythonの文字列(シングルクォート)の中の{{…}}が、引用符つきの値に置き換わると、構文が壊れる(Gemmaの失敗の仮説)
        reasons = self.reasons(param_response(python=GOOD_PYTHON + "\nsql = 'SELECT {{customer_code}} FROM v_ai_shipment'\nemit_report(sql + {{period_from}})"))
        self.assertIn('python:syntax_error', reasons)
        self.assertIn('python_syntax_after_substitution', reasons)
        self.assertNotIn('python_syntax_in_source', reasons)

    def test_a_syntax_error_that_exists_before_the_replacement_is_reported_as_such(self):
        reasons = self.reasons(param_response(python=GOOD_PYTHON + "\nemit_report({{customer_code}} + {{period_from}})\nx = ("))
        self.assertIn('python_syntax_in_source', reasons)
        self.assertNotIn('python_syntax_after_substitution', reasons)

    def test_the_kind_is_a_fixed_code_for_each_group_of_python_messages(self):
        cases = [('x = "abc', 'python_syntax_string'), ('x = )', 'python_syntax_bracket'), ('x = (1,\n', 'python_syntax_bracket'),
                 ('if True:\nx = 1', 'python_syntax_indent'), ('x = 1 ，2', 'python_syntax_character'), ('x = = 1', 'python_syntax_other')]
        for python, expected in cases:
            with self.subTest(python=python):
                self.assertEqual(cg._syntax_details(python, None), [expected])

    def test_an_extreme_python_never_raises_out_of_the_diagnosis(self):
        # 置き換え後は1行目で構文の誤り、置き換え前は深い入れ子でMemoryError(Python 3.13)。例外で止まると「生成中」が残る(evaluatorの指摘)
        source = {'python': "a = 'abc {{x}} def'\nb = " + '-' * 20000 + '1'}
        concrete = "a = 'abc 'X' def'\nb = 1"
        codes = cg._syntax_details(concrete, source)
        self.assertIn('python_syntax_in_source', codes)
        self.assertTrue(all(code.startswith('python_syntax') for code in codes))

    def test_no_message_or_code_of_the_ai_is_in_the_reasons(self):
        reasons = self.reasons(param_response(python=GOOD_PYTHON + "\nsecret_marker = 'SECRET-AI-TEXT {{customer_code}}'"))
        self.assertNotIn('SECRET', json.dumps(reasons, ensure_ascii=False))
        self.assertTrue(all(code.startswith(('python', 'parameters')) for code in reasons))


class PromptRuleTests(SimpleTestCase):
    def test_python_must_not_contain_placeholders_and_the_example_follows_it(self):
        self.assertIn('Pythonの中には、{{名前}} を書かない', cg.PARAMETER_RULE)
        self.assertIn('引用符がぶつかって、構文が壊れる', cg.PARAMETER_RULE)
        self.assertNotIn('{{', cg.PERIOD_EXAMPLE['python'])  # 見本のPythonは、変数を書かない


def setUpModule():
    global _temperature_patch
    from unittest import mock
    _temperature_patch = mock.patch('ai.services.analysis_llm.get_analysis_temperature', return_value=0.3)
    _temperature_patch.start()


def tearDownModule():
    _temperature_patch.stop()


class ExcludedPeriodRuleTests(SimpleTestCase):
    def test_the_rule_tells_the_ai_to_make_an_excluded_period_a_variable(self):
        # 2026-10-08: 追加の指示の「除く期間」の日付が、SQLへ直接書かれて失敗した(BOSS承認 案2)
        rule = cg.PARAMETER_RULE
        self.assertIn('期間の一部を除く指示', rule)
        self.assertIn('NOT BETWEEN {{exclude_from}} AND {{exclude_to}}', rule)
        self.assertIn('除く期間は、全体の期間の中に入れる', rule)
        # 片側だけの指定は、AIに補わせない(推測の補完をしない)。利用者へ書き直しを促す警告で扱う
        self.assertNotIn('片側だけが書かれているとき', rule)
