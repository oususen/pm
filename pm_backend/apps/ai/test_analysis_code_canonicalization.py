"""変数(品番・顧客コード・納入先コード)の値を、マスタ・公開ビューの正規の表記へ直す(2026-10-10、BOSS承認)を検証する。

背景: 目的文の小文字の品番 v053904703 が、そのままコードに入り、DuckDB(大文字小文字を区別)で0行になった。
MySQL(ci)は区別しないため、存在確認は通っていた。マスタの表記に直す(upper()は使わない。マスタに小文字の品番 giji が実在する)。
品番は v_ai_product、納入先コードは v_ai_shipment(分析用接続)、顧客コードは m_customer(顧客マスタのビューは未作成)で確認する。
"""
import json
from unittest.mock import patch

from django.test import TestCase

from ai.services import analysis_template_params as params
from ai.services import analysis_template_service as service
from ai.services.analysis_plan_store import AnalysisError
from ai.test_analysis_codegen import PARAM_DEFS, CodegenBase, param_response
from ai.test_analysis_template_params import DEFS, PYTHON_P, STEPS_P, ParamBase, fake_reader, param_plan
from ai.test_analysis_template_reuse import FakeStore

PRODUCT_DEF = {'name': 'product_code', 'type': 'product_code', 'label': '品番', 'default': 'v053904703'}


def master_of(*codes):
    """マスタ(ビュー)に保存されている表記の一覧から、大文字小文字を区別せず一致するものを返す確認関数(MySQL ci の代わり)。"""
    return lambda value: next((code for code in codes if code.lower() == value.lower()), None)


class CanonicalizeTests(TestCase):
    def test_lowercase_product_code_is_canonicalized_to_master(self):
        definitions = [PRODUCT_DEF, {**DEFS[1]}, {**DEFS[2]}]
        with fake_reader([('V053904703',)]) as cursor, patch.dict(params.TYPES['product_code'], {'exists': params._exists_product}):
            cleaned = params.validate_definitions(definitions)
            self.assertIn('`v_ai_product`', cursor.executed[0][0])
            self.assertEqual(cursor.executed[0][1], ['v053904703'])
            self.assertEqual(cleaned[0]['default'], 'V053904703')          # 保存される定義の default も、正規の表記
            values = params.resolve_values(cleaned, {})
        self.assertEqual(values['product_code'], 'V053904703')
        steps, python = params.concrete_code(STEPS_P, PYTHON_P, values)
        self.assertIn("product_code = 'V053904703'", steps[0]['query'])
        self.assertNotIn('v053904703', json.dumps(steps) + python)
        self.assertEqual(definitions[0]['default'], 'v053904703')             # 入力の定義は書き換えない

    def test_unregistered_product_code_still_rejected(self):
        with fake_reader([]), patch.dict(params.TYPES['product_code'], {'exists': params._exists_product}):
            with self.assertRaises(params.DefinitionError) as caught:
                params.validate_definitions([{**PRODUCT_DEF, 'default': 'nope-1'}, DEFS[1], DEFS[2]])
        self.assertEqual(caught.exception.reasons, ['parameters_def_unregistered'])
        self.assertEqual(caught.exception.names, {'parameters_def_unregistered': ['product_code']})

    def test_customer_code_and_ship_to_code_canonicalized(self):
        from masters.models import Customer
        Customer.objects.create(customer_code='Cust-A', customer_name='得意先')
        self.assertEqual(params._check_value('customer_code', 'Cust-A', 'c'), 'Cust-A')
        # 大文字小文字を区別しない一致(MySQL ci)はSQLiteでは再現できないため、DBから返った保存の表記が使われることを確認する
        with patch('django.db.models.query.QuerySet.first', return_value='Cust-A'):
            self.assertEqual(params._check_value('customer_code', 'cust-a', 'c'), 'Cust-A')
        with fake_reader([('ZGHC',)]), patch.dict(params.TYPES['ship_to_code'], {'exists': params._exists_ship_to}):
            self.assertEqual(params._check_value('ship_to_code', 'zghc', 's'), 'ZGHC')
        with self.assertRaises(params.DefinitionError) as caught:
            params._check_value('customer_code', 'nope', 'c')
        self.assertEqual(caught.exception.reasons, ['parameters_def_unregistered'])

    def test_giji_lowercase_master_is_preserved(self):
        # マスタに小文字の品番 giji が実在する。upper() ではなく、マスタの表記にする
        with fake_reader([('giji',)]), patch.dict(params.TYPES['product_code'], {'exists': params._exists_product}):
            self.assertEqual(params._check_value('product_code', 'GIJI', 'p'), 'giji')
            self.assertEqual(params._check_value('product_code', 'giji', 'p'), 'giji')

    def test_ship_to_ambiguous_case_variants_rejected(self):
        with fake_reader([('ZGHC',), ('zghc',)]) as cursor, patch.dict(params.TYPES['ship_to_code'], {'exists': params._exists_ship_to}):
            with self.assertRaises(params.DefinitionError) as caught:
                params._check_value('ship_to_code', 'Zghc', 'ship_to')
            self.assertIn('CAST(`ship_to_code` AS BINARY)', cursor.executed[0][0])   # ciのDISTINCTで潰れない取得
        self.assertEqual(caught.exception.reasons, ['parameters_def_ambiguous'])
        self.assertEqual(caught.exception.names, {'parameters_def_ambiguous': ['ship_to']})

    def test_a_non_string_or_unsafe_canonical_value_is_not_used(self):
        for stored in ('A B', 'あ', 'x' * 41, 5):
            with self.subTest(stored=stored), patch.dict(params.TYPES['product_code'], {'exists': lambda value, s=stored: s}):
                with self.assertRaises(params.DefinitionError) as caught:
                    params._check_value('product_code', 'p-1', 'p')
                self.assertEqual(caught.exception.reasons, ['parameters_def_value'])

    def test_literal_check_uses_canonical_default(self):
        defs = [{**PRODUCT_DEF, 'default': 'V053904703'}, {**DEFS[1]}, {**DEFS[2]}]
        steps = [{'name': 'w_a', 'query': STEPS_P[0]['query']}]
        params.check_source(steps, PYTHON_P, defs)
        for literal in ('V053904703', 'v053904703'):   # 正規の表記が、大文字小文字を変えて直書きされても、検出する
            with self.subTest(literal=literal), self.assertRaises(params.SourceCheckError) as caught:
                params.check_source(steps, PYTHON_P + f"\nx = '{literal}'", defs)
            self.assertEqual(caught.exception.reason, 'parameters_literal')
            self.assertIn('parameters_literal_value', caught.exception.reasons)


class ReuseAndSaveTests(ParamBase):
    def setUp(self):
        super().setUp()
        patcher = patch.dict(params.TYPES['product_code'], {'exists': master_of('P-001', 'P-002')})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_reuse_supplied_lowercase_value_is_canonicalized(self):
        row = self.param_row()
        response = self.reuse_with(self.other, row, {'product_code': 'p-002'})
        self.assertEqual(response.status_code, 201)
        plan, _ = FakeStore.created[0]
        self.assertEqual(plan['template']['values']['product_code'], 'P-002')
        self.assertIn("product_code = 'P-002'", plan['codegen']['steps'][0]['query'])
        self.assertNotIn('p-002', json.dumps(plan['codegen']['steps']) + plan['codegen']['python'])

    def test_existing_uppercase_template_hashes_unchanged(self):
        row = self.param_row()
        fields = service._fields_from_plan(param_plan(self.creator.pk))
        stored = {name: getattr(row, name) for name in ('content_sha256', 'sql_sha256', 'python_sha256', 'executed_code_sha256')}
        self.assertEqual({name: fields[name] for name in stored}, stored)
        self.assertEqual(row.parameters, DEFS)
        self.assertEqual(self.reuse_with(self.other, row).status_code, 201)       # 既定値での再利用は、承認済みのコードのまま
        plan, _ = FakeStore.created[0]
        self.assertEqual(plan['codegen']['executed_code_sha256'], row.executed_code_sha256)
        self.assertEqual(plan['template']['values']['product_code'], 'P-001')

    def test_template_save_matches_approved_code_after_normalization(self):
        # コード生成の確認時に正規化された定義(default=P-001)で承認したコードは、そのまま保存できる(保存時は、正規化を足さない)
        definitions = params.validate_definitions([{**DEFS[0], 'default': 'p-001'}, *DEFS[1:]])
        self.assertEqual(definitions[0]['default'], 'P-001')
        fields = service._fields_from_plan(param_plan(self.creator.pk, definitions=definitions))
        self.assertEqual(fields['parameters'][0]['default'], 'P-001')
        # 正規化の前(小文字の default)で承認されたコードは、保存時に書き換えず、一致しないものとして拒否する(409)
        lower = [{**DEFS[0], 'default': 'p-001'}, *DEFS[1:]]
        with self.assertRaises(AnalysisError) as caught:
            service._fields_from_plan(param_plan(self.creator.pk, definitions=lower))
        self.assertEqual(caught.exception.status_code, 409)


class NormalizedValuesTests(CodegenBase):
    def setUp(self):
        super().setUp()
        patcher = patch.dict(params.TYPES['customer_code'], {'exists': master_of('C-001')})
        patcher.start()
        self.addCleanup(patcher.stop)

    def state_of(self, response):
        plan = self.new_plan()
        self.generate(plan, response)
        return self.current(plan)['codegen']

    def test_normalized_values_in_codegen_state(self):
        defs = [{**PARAM_DEFS[0], 'default': 'c-001'}, *PARAM_DEFS[1:]]
        state = self.state_of(param_response(parameters=defs))
        self.assertEqual(state['status'], 'generated')
        self.assertEqual(state['normalized_values'], [{'name': 'customer_code', 'from': 'c-001', 'to': 'C-001'}])
        self.assertEqual(state['template_source']['parameters'][0]['default'], 'C-001')
        self.assertIn("customer_code = 'C-001'", state['steps'][0]['query'])

    def test_no_normalized_values_when_nothing_changed_and_periods_are_not_reported(self):
        defs = [PARAM_DEFS[0], {**PARAM_DEFS[1], 'default': '2020-05-05'}, PARAM_DEFS[2]]   # 期間の default は、分析案の期間に置き換わる(コード系ではない)
        state = self.state_of(param_response(parameters=defs))
        self.assertEqual(state['status'], 'generated')
        self.assertNotIn('normalized_values', state)

    def test_normalized_values_only_hold_fixed_shape_strings(self):
        self.assertEqual(params.normalized_values('x', [{**PRODUCT_DEF, 'default': 'V1'}]), [])
        raw = [{'name': 'product_code', 'default': '<img src=x>'}, {'name': 'b', 'default': 5}, 'x', None, {'name': 'c_code', 'default': 'a-1'}]
        defs = [{'name': 'product_code', 'type': 'product_code', 'default': 'V1'}, {'name': 'b', 'type': 'product_code', 'default': 'V2'},
                {'name': 'c_code', 'type': 'customer_code', 'default': 'A-1'}, {'name': 'period_from', 'type': 'date', 'default': '2026-01-01'}]
        self.assertEqual(params.normalized_values(raw, defs), [{'name': 'c_code', 'from': 'a-1', 'to': 'A-1'}])


# 分析の温度は、AI設定(DB)から取得する。このモジュールの生成試験は、DBを使わないため、従来の値(0.3)を返す(test_analysis_copied_literals.pyと同じ)
def setUpModule():
    global _temperature_patch
    _temperature_patch = patch('ai.services.analysis_llm.get_analysis_temperature', return_value=0.3)
    _temperature_patch.start()


def tearDownModule():
    _temperature_patch.stop()
