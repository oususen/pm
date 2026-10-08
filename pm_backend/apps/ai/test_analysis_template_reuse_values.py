"""再利用で、変数の値を指定するときの応答(2-C、2026-10-08、BOSS承認・Codex意見)を検証する。

値の不備(400)は、固定の理由コードと変数名(識別子だけ)を返す。値・AIの文章は返さない。全体の期間は、元のテンプレートの期間の外へも変えられる。
"""
from ai.test_analysis_template_params import HALF_DEFS, HALF_STEPS, PYTHON, ParamBase

# 全体の期間(period_from・period_to)と、除く期間(ex_from・ex_to。既定値は全体の期間の中)を持つテンプレート
EX_DEFS = [
    {'name': 'period_from', 'type': 'date', 'label': '開始日', 'default': '2026-01-01'},
    {'name': 'period_to', 'type': 'date', 'label': '終了日', 'default': '2026-01-31'},
    {'name': 'ex_from', 'type': 'date', 'label': '除く開始日', 'default': '2026-01-20'},
    {'name': 'ex_to', 'type': 'date', 'label': '除く終了日', 'default': '2026-01-25'},
]
EX_STEPS = [{'name': 'w_daily', 'query': (
    'SELECT shipment_date, SUM(quantity) AS q FROM v_ai_shipment WHERE shipment_date BETWEEN {{period_from}} AND {{period_to}} '
    'AND shipment_date NOT BETWEEN {{ex_from}} AND {{ex_to}} GROUP BY shipment_date')}]
from ai.test_analysis_template_reuse import FakeStore

SECRET_VALUE = 'SECRET-VALUE-XYZ'


class ReasonResponseTests(ParamBase):
    def row(self):
        return self.param_row()  # 品番・全体の期間(2026-01-01〜2026-01-31)

    def test_each_definition_error_returns_a_fixed_reason_and_the_variable_names_only(self):
        cases = (
            ({'period_from': '2026-1-1'}, 'parameters_def_date', ['period_from']),
            ({'product_code': 'P 001'}, 'parameters_def_value', ['product_code']),
            ({'product_code': 'P-999'}, 'parameters_def_unregistered', ['product_code']),
            ({'period_from': '2026-01-20', 'period_to': '2026-01-10'}, 'parameters_def_order', ['period_from', 'period_to']),
        )
        for body, reason, names in cases:
            with self.subTest(reason=reason):
                FakeStore.created.clear()
                response = self.reuse_with(self.other, self.row(), body)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data['reasons'], [reason])
                self.assertEqual(response.data['names'], {reason: names})
                self.assertEqual(FakeStore.created, [])

    def test_the_response_never_contains_the_entered_value(self):
        for body in ({'product_code': SECRET_VALUE}, {'period_from': SECRET_VALUE}, {'product_code': SECRET_VALUE + ' x'}):
            with self.subTest(body=body):
                text = str(self.reuse_with(self.other, self.row(), body).data)
                self.assertNotIn(SECRET_VALUE, text)

    def test_an_empty_value_is_rejected_and_is_not_replaced_by_the_stored_value(self):
        # Codex: 変更して空にした値は、省略せず、空のまま送る。サーバーは拒否し、保存済みの値へ戻さない
        for body, reason in (({'product_code': ''}, 'parameters_def_value'), ({'period_from': ''}, 'parameters_def_date'), ({'period_to': ''}, 'parameters_def_date')):
            with self.subTest(body=body):
                FakeStore.created.clear()
                response = self.reuse_with(self.other, self.row(), body)
                self.assertEqual((response.status_code, response.data['reasons']), (400, [reason]))
                self.assertEqual(FakeStore.created, [])

    def test_errors_without_a_reason_code_have_no_reasons_key(self):
        for body in ({'unknown_name': 'x'},):  # 定義にない変数名
            with self.subTest(body=body):
                response = self.reuse_with(self.other, self.row(), body)
                self.assertEqual(response.status_code, 400)
                self.assertNotIn('reasons', response.data)
        for body in ('x', 0, [], None):
            with self.subTest(parameters=body):
                self.assertEqual(self.call('ai-analysis-template-plans', self.other, data={'parameters': body}, template_id=self.row().pk).status_code, 400)


class PeriodChangeTests(ParamBase):
    def ex_row(self):
        return self.param_row(steps=EX_STEPS, python=PYTHON, definitions=EX_DEFS)

    def test_narrowing_only_the_overall_period_makes_the_default_excluded_period_stick_out_and_is_rejected(self):
        # 全体の期間を狭めても、除く期間は自動では動かない。既定の除く期間(1/20〜1/25)がはみ出すと、400(parameters_def_outside)
        response = self.reuse_with(self.other, self.ex_row(), {'period_to': '2026-01-15'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['reasons'], ['parameters_def_outside'])
        self.assertEqual(response.data['names'], {'parameters_def_outside': ['ex_from', 'ex_to']})
        self.assertEqual(FakeStore.created, [])

    def test_moving_the_overall_and_the_excluded_period_together_is_accepted(self):
        body = {'period_from': '2026-02-01', 'period_to': '2026-02-28', 'ex_from': '2026-02-10', 'ex_to': '2026-02-12'}
        response = self.reuse_with(self.other, self.ex_row(), body)
        self.assertEqual(response.status_code, 201)
        plan, _ = FakeStore.created[0]
        self.assertEqual((plan['proposal']['date_from'], plan['proposal']['date_to']), ('2026-02-01', '2026-02-28'))
        self.assertIn("NOT BETWEEN '2026-02-10' AND '2026-02-12'", plan['codegen']['steps'][0]['query'])
        self.assertEqual(plan['template']['values'], body)

    def test_widening_the_overall_period_keeps_the_default_excluded_period_inside(self):
        response = self.reuse_with(self.other, self.ex_row(), {'period_from': '2025-12-01', 'period_to': '2026-03-31'})
        self.assertEqual(response.status_code, 201)

    def test_the_overall_period_can_be_widened_beyond_the_template_period_and_is_used_as_the_plan_period(self):
        # 元は2026-01。全体の期間を、元の期間の外(2〜3月)へ変える。承認・件数確認・試行は、新しい分析案で取り直す
        row = self.param_row()
        response = self.reuse_with(self.other, row, {'period_from': '2025-12-01', 'period_to': '2026-03-31'})
        self.assertEqual(response.status_code, 201)
        plan, _ = FakeStore.created[0]
        self.assertEqual((plan['proposal']['date_from'], plan['proposal']['date_to']), ('2025-12-01', '2026-03-31'))
        self.assertEqual(plan['template']['values']['period_from'], '2025-12-01')
        self.assertIn("BETWEEN '2025-12-01' AND '2026-03-31'", plan['codegen']['steps'][0]['query'])
        self.assertNotIn('{{', str(plan['codegen']['steps']) + plan['codegen']['python'])
        self.assertEqual(plan['status'], 'awaiting_method')                      # 手順の承認から取り直す
        self.assertIsNone(plan['codegen']['trial'])                                # 試行・コード承認は引き継がない
        self.assertEqual(plan['codegen']['status'], 'generated')

    def test_narrowing_the_overall_period_does_not_move_the_compared_periods_and_is_rejected_with_names(self):
        row = self.param_row(steps=HALF_STEPS, python=PYTHON, definitions=HALF_DEFS)
        response = self.reuse_with(self.other, row, {})
        self.assertEqual(response.status_code, 201)   # 既定値は、元の期間の中
        FakeStore.created.clear()
        # HALF_DEFS に全体の期間の変数がない場合は、全体の期間は変えられない。比べる期間を、元の期間の外へ出すと、拒否される
        response = self.reuse_with(self.other, row, {'second_to': '2026-02-01'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['reasons'], ['parameters_def_outside'])
        self.assertEqual(response.data['names'], {'parameters_def_outside': ['second_from', 'second_to']})
        self.assertEqual(FakeStore.created, [])

    def test_the_stored_template_row_is_not_changed_by_a_reuse_with_values(self):
        row = self.param_row()
        before = {field: getattr(row, field) for field in ('content_sha256', 'name', 'date_from', 'date_to', 'state_revision', 'status')}
        self.assertEqual(self.reuse_with(self.other, row, {'product_code': 'P-002', 'period_from': '2026-01-05'}).status_code, 201)
        row.refresh_from_db()
        self.assertEqual({field: getattr(row, field) for field in before}, before)
