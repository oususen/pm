"""目的・手順に書かれた値(品番など)が、変数にされず、コードに直接書かれたときの警告(2026-10-08、BOSS承認)を検証する。

実機で、Qwen3 14Bが、2つの品番をSQL・Pythonに直接書き、再利用で品番を変えられないコードを作った(DeepSeekは、品番ごとの変数を自分で作った)。
機械的な文字列の確認で、画面に警告する(止めない)。指示文にも、品番が複数のときの書き方を足した。
"""
import json

from django.test import SimpleTestCase

from ai.services import analysis_codegen_service as cg
from ai.services.analysis_template_params import copied_literals
from ai.test_analysis_codegen import GOOD_PYTHON, OWNER, CodegenBase

TEXTS = ['品番V053504641とV053143615の日別出荷数量比較', '品番 V053504641 を抽出', '日付ごとの合計']


class CopiedLiteralsTests(SimpleTestCase):
    def test_codes_written_directly_in_sql_and_python_are_found(self):
        steps = [{'name': 'w_a', 'query': "SELECT shipment_date FROM v_ai_shipment WHERE product_code IN ('V053504641', 'V053143615')"}]
        python = "if code == 'V053504641':\n    pass\nemit_report('x')"
        self.assertEqual(copied_literals(TEXTS, steps, python), ['V053143615', 'V053504641'])

    def test_variables_leave_no_literal(self):
        steps = [{'name': 'w_a', 'query': 'SELECT shipment_date FROM v_ai_shipment WHERE product_code IN ({{product_code_1}}, {{product_code_2}})'}]
        self.assertEqual(copied_literals(TEXTS, steps, "emit_report('x')"), [])

    def test_a_code_inside_a_longer_string_such_as_a_title_is_found(self):
        self.assertEqual(copied_literals(TEXTS, [], "emit_chart('line', '品番V053504641の推移', [], [])"), ['V053504641'])

    def test_only_values_from_the_plan_texts_that_look_like_codes_are_checked(self):
        steps = [{'name': 'w_a', 'query': "SELECT 'daily' AS kind, 'V999999999' AS other FROM v_ai_shipment"}]
        # 'daily'は数字を含まない、V999999999は目的・手順に書かれていない値 → 対象外
        self.assertEqual(copied_literals(TEXTS, steps, "emit_report('x')"), [])

    def test_dates_are_not_reported_here_because_they_have_their_own_check(self):
        steps = [{'name': 'w_a', 'query': "SELECT 1 FROM v_ai_shipment WHERE shipment_date BETWEEN '2026-08-01' AND '2026-09-30'"}]
        self.assertEqual(copied_literals(['2026-08-01から2026-09-30の出荷'], steps, "emit_report('x')"), [])

    def test_numeric_codes_such_as_customer_codes_are_found(self):
        steps = [{'name': 'w_a', 'query': "SELECT 1 FROM v_ai_shipment WHERE customer_code = '000196'"}]
        self.assertEqual(copied_literals(['顧客000196の出荷'], steps, "emit_report('x')"), ['000196'])

    def test_unrelated_text_and_empty_inputs_are_safe(self):
        self.assertEqual(copied_literals([], [], "emit_report('x')"), [])
        self.assertEqual(copied_literals(['abc'], [], ''), [])


class PromptTests(SimpleTestCase):
    def test_the_instruction_covers_several_codes_and_the_period_variable_names(self):
        rule = cg.PARAMETER_RULE
        self.assertIn('複数書かれているときは、値ごとに別の変数を作る', rule)
        self.assertIn('IN ({{product_code_1}}, {{product_code_2}})', rule)
        self.assertIn('Pythonの中には、品番・顧客コードの文字列を直接書かない', rule)
        self.assertIn('全体の期間の変数名は、必ず period_from・period_to にする', rule)


class MultiCodeExampleTests(SimpleTestCase):
    """複数の品番の見本(2026-10-08、BOSS承認)。実際のDuckDBと外枠での動作は、作成時に確認済み。ここでは、変数の検査と、直書きの警告に当たらないことを確認する。"""

    DEFS = [
        {'name': 'product_code_1', 'type': 'product_code', 'label': '品番1', 'default': 'P-001'},
        {'name': 'product_code_2', 'type': 'product_code', 'label': '品番2', 'default': 'P-002'},
        {'name': 'period_from', 'type': 'date', 'label': '開始日', 'default': '2026-08-01'},
        {'name': 'period_to', 'type': 'date', 'label': '終了日', 'default': '2026-09-30'},
    ]

    def test_the_prompt_contains_the_example_and_it_passes_the_variable_checks(self):
        from unittest.mock import patch
        from ai.services import analysis_template_params as params
        self.assertIn('複数の品番(顧客コード)を比べる分析の、返すJSONの例', cg.SYSTEM_PROMPT)
        self.assertIn('品番の文字列は、Pythonに直接書かない', cg.SYSTEM_PROMPT)
        example = cg.MULTI_CODE_EXAMPLE
        self.assertEqual([item['name'] for item in example['parameters']], ['product_code_1', 'product_code_2', 'period_from', 'period_to'])
        with patch.dict(params.TYPES['product_code'], {'exists': lambda value: value}):
            definitions = params.validate_definitions(self.DEFS)
            params.check_source(example['steps'], example['python'], definitions)  # 宣言と使用が一致し、固定の値の直書きがない
        self.assertEqual(copied_literals(['品番P-001とP-002の比較', '2026-08-01から2026-09-30'], example['steps'], example['python']), [])

    def test_the_example_python_does_not_put_a_code_string_or_brace_pairs(self):
        python = cg.MULTI_CODE_EXAMPLE['python']
        self.assertNotIn('}}', python.replace('{{', '').replace(' }}', ''))   # 閉じ括弧を連続させない(変数の表記と区別できないため)
        self.assertNotIn('{{', python)                                         # Pythonの中に、変数を書かない
        self.assertIn('amounts.get((d, code), 0.0)', python)                  # ない日は 0.0(系列の個数を、日付に合わせる)


class GenerationWarningTests(CodegenBase):
    """生成の結果に、コードに直接書かれた値(literal_values)が残る(警告用。生成は成功のまま)。"""

    def plan_with_purpose(self, purpose):
        plan = self.new_plan()
        return self.store.update(plan['id'], OWNER, plan['revision'], lambda current: current['proposal'].update(purpose=purpose))

    def response(self, query):
        return json.dumps({'steps': [{'name': 'w_daily', 'query': query}], 'python': GOOD_PYTHON})

    def test_a_directly_written_code_is_generated_with_a_warning_value(self):
        plan = self.plan_with_purpose('品番V053504641の出荷')
        result, _ = self.generate(plan, self.response("SELECT shipment_date, SUM(quantity) AS q FROM v_ai_shipment WHERE product_code = 'V053504641' GROUP BY shipment_date"))
        self.assertEqual(result['codegen']['status'], 'generated')          # 警告だけで、生成は止めない
        self.assertEqual(result['codegen']['literal_values'], ['V053504641'])

    def test_no_literal_values_key_when_nothing_is_copied(self):
        plan = self.plan_with_purpose('品番V053504641の出荷')
        result, _ = self.generate(plan, self.response('SELECT shipment_date, SUM(quantity) AS q FROM v_ai_shipment GROUP BY shipment_date'))
        self.assertEqual(result['codegen']['status'], 'generated')
        self.assertNotIn('literal_values', result['codegen'])


# 分析の温度は、AI設定(DB)から取得する。このモジュールの試験は、DBを使わないため、従来の値(0.3)を返す(test_analysis_codegen.pyと同じ)
def setUpModule():
    global _temperature_patch
    from unittest import mock
    _temperature_patch = mock.patch('ai.services.analysis_llm.get_analysis_temperature', return_value=0.3)
    _temperature_patch.start()


def tearDownModule():
    _temperature_patch.stop()
