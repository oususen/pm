"""変数(品番・顧客コード・納入先コード)の値を、マスタ・公開ビューの正規の表記へ直す(2026-10-10、BOSS承認)を検証する。

背景: 目的文の小文字の品番 v053904703 が、そのままコードに入り、DuckDB(大文字小文字を区別)で0行になった。
MySQL(ci)は区別しないため、存在確認は通っていた。マスタの表記に直す(upper()は使わない。マスタに小文字の品番 giji が実在する)。
品番は v_ai_product、納入先コードは v_ai_shipment(分析用接続)、顧客コードは m_customer(顧客マスタのビューは未作成)で確認する。
"""
import json
from unittest.mock import patch

from django.test import TestCase

from ai.models import AIAnalysisTemplate
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


class LiteralCheckTests(TestCase):
    """直書き検査は、SQL・Pythonの文字列リテラルだけが対象(識別子・コメントは除外)。大文字小文字は区別しない(Codexレビュー指摘1)。"""
    SQL = ('SELECT shipment_date, SUM(quantity) AS {alias} FROM v_ai_shipment WHERE product_code = {{{{product_code}}}} '
           'AND shipment_date BETWEEN {{{{period_from}}}} AND {{{{period_to}}}} {tail}')

    def defs(self, default):
        return [{**PRODUCT_DEF, 'default': default}, {**DEFS[1]}, {**DEFS[2]}]

    def steps(self, alias='q', tail=''):
        return [{'name': 'w_a', 'query': self.SQL.format(alias=alias, tail=tail)}]

    def test_literal_check_ignores_identifiers_and_comments(self):
        defs = self.defs('giji')
        steps = self.steps(alias='GIJI', tail='-- giji\n/* GIJI */ GROUP BY shipment_date')
        params.check_source(steps, PYTHON_P, defs)
        params.check_source(self.steps(alias='"giji" ', tail='GROUP BY `GIJI`'), PYTHON_P, defs)   # 引用符つきの識別子
        params.check_source(STEPS_P, PYTHON_P + "\n# giji\ngiji_value = 1\n", defs)                   # Python: 識別子・コメント

    def test_literal_check_still_catches_lowercase_literal(self):
        defs = self.defs('V053904703')
        for tail in ("AND x = 'v053904703'", "AND x = 'ab''v053904703'", "AND x = 'a' || 'V053904703'"):
            with self.subTest(tail=tail), self.assertRaises(params.SourceCheckError) as caught:
                params.check_source(self.steps(tail=tail), PYTHON_P, defs)
            self.assertEqual(caught.exception.reasons, ['parameters_literal', 'parameters_literal_sql', 'parameters_literal_value'])
        # コメントの後ろの文字列リテラルも検出し、文字列の中の -- はコメントとみなさない
        with self.assertRaises(params.SourceCheckError):
            params.check_source(self.steps(tail="-- note\nAND x = 'v053904703 -- y'"), PYTHON_P, defs)

    def test_literal_check_python_literals(self):
        defs = self.defs('V053904703')
        for code in ("x = 'v053904703'", "x = f'{1} V053904703'", 'x = "a v053904703 b"', "x = '''v053904703'''"):
            with self.subTest(code=code), self.assertRaises(params.SourceCheckError) as caught:
                params.check_source(STEPS_P, PYTHON_P + '\n' + code, defs)
            self.assertEqual(caught.exception.reasons, ['parameters_literal', 'parameters_literal_python', 'parameters_literal_value'])
        params.check_source(STEPS_P, PYTHON_P + "\nv053904703 = 1  # V053904703", defs)

    def test_literal_check_python_literal_next_to_placeholder(self):
        # {{名前}} は文字列のダミーに置き換えて読むため、変数と並べた直書き(置換後は文字列の連結)も拒否する
        defs = self.defs('V053904703')
        for code in ('x = {{product_code}} "v053904703"', 'x = "v053904703" {{product_code}}'):
            with self.subTest(code=code), self.assertRaises(params.SourceCheckError) as caught:
                params.check_source(STEPS_P, PYTHON_P + '\n' + code, defs)
            self.assertEqual(caught.exception.reasons, ['parameters_literal', 'parameters_literal_python', 'parameters_literal_value'])

    def test_literal_check_short_default_does_not_match_placeholder_dummy(self):
        # 変数だけの式と、三重引用符の中の変数で、短い default(none/on/ne)がダミーに誤一致しない。
        # (ダミーの中身を守るテスト。ダミーを 'None' のような文字列に戻すと失敗する)
        # 注意: default が p・h・ph のような極端に短い値は、ダミー '?PH ?' に部分一致して拒否される(品番マスタに該当する値はない。仕様書 5.3-5c)
        for default in ('none', 'on', 'ne'):
            with self.subTest(default=default):
                params.check_source(STEPS_P, PYTHON_P + "\nz = {{product_code}}", self.defs(default))
                params.check_source(STEPS_P, PYTHON_P + "\nz = '''a {{product_code}} b'''", self.defs(default))
        # 抽出内容を固定する(抽出が空になって空振りしていないことの確認)
        self.assertEqual(params._python_string_literals("x = {{product_code}}"), [params.PLACEHOLDER_DUMMY])
        self.assertEqual(params._python_string_literals("x = '''a {{product_code}} b'''"), ["a '%s' b" % params.PLACEHOLDER_DUMMY])  # 実行時の置換と同じく、値は引用符つきで入る

    def test_literal_check_placeholder_inside_plain_string_is_left_to_later_check(self):
        # 引用符に隣接しない通常の文字列(f-stringを含む)の中の {{名前}} は、ダミー置換後に構文エラーとなり、ここでは何も抽出しない
        # (拒否は、続く validate_generated=置き換え後の実行する形の検査が行う。仕様書 5.3-5c)
        self.assertEqual(params._python_string_literals("x = 'abc {{product_code}} def'"), [])
        self.assertEqual(params._python_string_literals("y = f'{1} {{product_code}} g'"), [])

    def test_literal_check_syntax_error_python_does_not_raise_here(self):
        # 構文が読めないPythonは、ここでは何も返さず(例外にもしない)、続く validate_generated が拒否する
        params.check_source(STEPS_P, PYTHON_P + "\nx = (", self.defs('V053904703'))
        self.assertEqual(params._python_string_literals("x = ('"), [])


def _view_candidates(rows, view_type, value):
    with fake_reader([(row,) for row in rows]), patch.dict(params.TYPES[view_type], {'exists': {
            'product_code': params._exists_product, 'ship_to_code': params._exists_ship_to}[view_type]}):
        return params._check_value(view_type, value, 'v')


class FullwidthCandidateTests(TestCase):
    """全角半角の違いは対象外。ASCIIの大文字小文字の違いだけで候補を絞ってから、曖昧判定する(Codexレビュー指摘2)。"""
    TYPES = ('product_code', 'ship_to_code')   # v_ai_product / v_ai_shipment

    def test_ship_to_fullwidth_variant_is_not_ambiguous(self):
        for type_name in self.TYPES:
            with self.subTest(type_name=type_name):
                self.assertEqual(_view_candidates(['X1', 'Ｘ１'], type_name, 'x1'), 'X1')
                self.assertEqual(_view_candidates(['Ｘ１', 'X1'], type_name, 'X1'), 'X1')

    def test_ambiguous_ascii_case_variants_still_rejected(self):
        for type_name in self.TYPES:
            with self.subTest(type_name=type_name), self.assertRaises(params.DefinitionError) as caught:
                _view_candidates(['X1', 'x1', 'Ｘ１'], type_name, 'X1')
            self.assertEqual(caught.exception.reasons, ['parameters_def_ambiguous'])

    def test_fullwidth_only_candidates_are_unregistered(self):
        for type_name in self.TYPES:
            with self.subTest(type_name=type_name), self.assertRaises(params.DefinitionError) as caught:
                _view_candidates(['Ｘ１'], type_name, 'x1')
            self.assertEqual(caught.exception.reasons, ['parameters_def_unregistered'])

    def test_canonical_lookup_returns_none_when_nothing_matches(self):
        with fake_reader([('Ｘ１',)]):
            self.assertIsNone(params._canonical_in_view('v_ai_shipment', 'ship_to_code', 'x1', '納入先コード'))
        with fake_reader([(b'X1',)]):   # CAST(... AS BINARY) のbytesも扱う
            self.assertEqual(params._canonical_in_view('v_ai_shipment', 'ship_to_code', 'x1', '納入先コード'), 'X1')


class StaleDefaultTests(ParamBase):
    """小文字のdefaultで保存された旧テンプレートは、現在のマスタ表記では保存済みハッシュと一致しない(Codexレビュー指摘3)。"""
    NORMALIZED = '保存時の表記と現在のマスタ表記が異なります。新しい分析として作り直し、試行・承認してください。'

    def setUp(self):
        super().setUp()
        patcher = patch.dict(params.TYPES['product_code'], {'exists': master_of('P-001', 'P-002')})
        patcher.start()
        self.addCleanup(patcher.stop)

    def stale_row(self, status):
        lower = [{**DEFS[0], 'default': 'p-001'}, *DEFS[1:]]
        with patch.dict(params.TYPES['product_code'], {'exists': lambda value: value}):   # 正規化の導入前の保存を再現する(小文字のまま保存)
            return self.param_row(status=status, definitions=lower)

    def test_approve_rejects_template_with_stale_lowercase_default(self):
        row = self.stale_row('pending_admin')
        response = self.approve(self.admin, row)
        self.assertEqual(response.status_code, 409)
        self.assertIn(self.NORMALIZED, str(response.data))
        row.refresh_from_db()
        self.assertEqual((row.status, row.state_revision), ('pending_admin', 1))

    def test_reuse_stale_default_shows_normalization_message(self):
        row = self.stale_row('approved')
        for supplied in (None, {'product_code': 'P-001'}):   # 正しい値を再入力しても、入力の処理より前に拒否される
            with self.subTest(supplied=supplied):
                response = self.reuse_with(self.other, row, supplied)
                self.assertEqual(response.status_code, 409)
                self.assertIn(self.NORMALIZED, str(response.data))
        self.assert_no_plan()

    def test_reuse_hash_mismatch_other_cause_keeps_original_message(self):
        row = self.param_row()
        AIAnalysisTemplate.objects.filter(pk=row.pk).update(sql_sha256='0' * 64)   # 表記とは無関係なハッシュの不一致
        response = self.reuse_with(self.other, row)
        self.assertEqual(response.status_code, 409)
        self.assertIn('保存されたSQL・Pythonのハッシュが一致しないため再利用できません。', str(response.data))
        self.assertNotIn(self.NORMALIZED, str(response.data))

    def test_approve_hash_mismatch_other_cause_keeps_original_message(self):
        row = self.param_row(status='pending_admin')
        AIAnalysisTemplate.objects.filter(pk=row.pk).update(python_sha256='0' * 64)
        response = self.approve(self.admin, row)
        self.assertEqual(response.status_code, 409)
        self.assertIn('保存されたSQL・Pythonのハッシュが一致しないため承認できません。', str(response.data))
        self.assertNotIn(self.NORMALIZED, str(response.data))

    def test_approve_passes_for_uppercase_default_template(self):
        row = self.param_row(status='pending_admin')   # 開発DBの id=2 相当(大文字default)
        self.assertEqual(self.approve(self.admin, row).status_code, 200)
        row.refresh_from_db()
        self.assertEqual(row.status, 'approved')


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
