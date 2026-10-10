"""テンプレートの変数(段階2-A)を、実ユーザー・実効権限・一時SQLiteで検証する。

変数の置き換え・検査(直書きの禁止)・保存(変数の形で保存、既定値で承認済みのコードと一致)・承認・再利用(値の指定、期間の変更)・表示範囲。
品番・顧客コードの実在の確認はマスタ(ORM)、納入先コードは分析用DB接続のため、納入先だけ差し替える(SQLiteにビューがないため)。
"""
import hashlib
import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from ai.models import AIAnalysisTemplate
from ai.services import analysis_codegen_service as cg
from ai.services import analysis_template_params as params
from ai.services import analysis_template_service as service
from ai.services.analysis_plan_store import AnalysisError
from ai.test_analysis_template_reuse import FakeStore, ReuseBase
from ai.test_analysis_templates import PYTHON, VIEWS, make_plan

STEPS_P = [{'name': 'w_daily', 'query': (
    'SELECT shipment_date, SUM(quantity) AS q FROM v_ai_shipment WHERE product_code = {{product_code}} '
    'AND shipment_date BETWEEN {{period_from}} AND {{period_to}} GROUP BY shipment_date')}]
PYTHON_P = PYTHON + "\nemit_report('品番 ' + {{product_code}} + ' ' + {{period_from}})"
DEFS = [
    {'name': 'product_code', 'type': 'product_code', 'label': '品番', 'default': 'P-001'},
    {'name': 'period_from', 'type': 'date', 'label': '開始日', 'default': '2026-01-01'},
    {'name': 'period_to', 'type': 'date', 'label': '終了日', 'default': '2026-01-31'},
]
PRODUCTS = {'P-001', 'P-002'}

@contextmanager
def fake_reader(rows):
    """分析用接続(ai_reader)を差し替える。cursor.fetchall() は rows を返し、実行したSQLと引数を executed に残す。"""
    class Cursor:
        executed = []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql, args):
            Cursor.executed.append((sql, args))

        def fetchall(self):
            return rows

    class Connections:
        def __getitem__(self, name):
            assert name == 'ai_reader'
            return type('C', (), {'cursor': staticmethod(lambda: Cursor())})()

    with patch.object(params, 'connections', Connections()), patch.dict(params.settings.DATABASES, {'ai_reader': {'USER': 'pm_ai_reader'}}):
        yield Cursor



def param_plan(owner_id, steps=STEPS_P, python=PYTHON_P, definitions=DEFS, source=True):
    """変数の形のコード(template_source)を持つ、コード承認済みの分析案。コードは、既定値で置き換えた形で承認済み。"""
    values = {item['name']: item['default'] for item in definitions}
    concrete_steps, concrete_python = params.concrete_code(steps, python, values)
    plan = make_plan(owner_id)
    bundle = cg.make_bundle(concrete_steps, concrete_python, VIEWS)
    plan['codegen'] = {
        'status': 'code_approved', 'steps': concrete_steps, 'python': concrete_python, 'executed_code_sha256': bundle.executed_code_sha256,
        'wrapper_version': bundle.wrapper_version, 'code_approved_at': (datetime.now() - timedelta(minutes=3)).isoformat(),
    }
    if source:
        plan['codegen']['template_source'] = {'steps': steps, 'python': python, 'parameters': definitions}
    return plan


class ParamBase(ReuseBase):
    def setUp(self):
        super().setUp()
        patcher = patch.dict(params.TYPES['product_code'], {'exists': lambda value: value if value in PRODUCTS else None})
        patcher.start()
        self.addCleanup(patcher.stop)

    def param_row(self, user=None, status='approved', **plan_kwargs):
        user = user or self.creator
        fields = service._fields_from_plan(param_plan(user.pk, **plan_kwargs))
        return AIAnalysisTemplate.objects.create(
            family_id=uuid4(), version=1, source_plan_id=str(uuid4()), source_plan_revision=1, approved_by=user, status=status, **fields)

    def reuse_with(self, user, template, parameters=None):
        data = None if parameters is None else {'parameters': parameters}
        return self.call('ai-analysis-template-plans', user, data=data, template_id=template.pk)


class SourceCheckTests(ParamBase):
    def test_placeholders_become_quoted_literals_and_the_source_is_not_changed(self):
        steps, python = params.concrete_code(STEPS_P, PYTHON_P, {'product_code': 'P-002', 'period_from': '2026-02-01', 'period_to': '2026-02-28'})
        self.assertIn("product_code = 'P-002' AND shipment_date BETWEEN '2026-02-01' AND '2026-02-28'", steps[0]['query'])
        self.assertIn("'品番 ' + 'P-002' + ' ' + '2026-02-01'", python)
        self.assertNotIn('{{', json.dumps(steps) + python)
        self.assertIn('{{product_code}}', STEPS_P[0]['query'])

    def test_a_valid_source_passes_and_every_defect_is_refused(self):
        params.check_source(STEPS_P, PYTHON_P, DEFS)
        s = lambda query: [{'name': 'w_a', 'query': query}]
        bad = {
            'undefined placeholder': (s('SELECT {{other}}'), PYTHON_P, DEFS),
            'unused definition': (s(STEPS_P[0]['query'].replace('product_code = {{product_code}} AND ', '')), PYTHON, DEFS),
            'default left in the code': (s(STEPS_P[0]['query'] + " AND note = 'P-001'"), PYTHON_P, DEFS),   # 直書き検査は文字列リテラルだけ(コメント・識別子は対象外)
            'default left in python': (STEPS_P, PYTHON_P + "\nx = 'P-001'", DEFS),
            'date literal in sql': (s(STEPS_P[0]['query'].replace('{{period_to}}', "'2026-01-31'")), PYTHON_P, DEFS[:2]),
            'date literal in python': (STEPS_P, PYTHON_P + "\nd = '2026-03-01'", DEFS),
            'placeholder in the step name': ([{'name': 'w_{{product_code}}', 'query': STEPS_P[0]['query']}], PYTHON_P, DEFS),
        }
        for label, (steps, python, definitions) in bad.items():
            with self.subTest(label=label), self.assertRaises(AnalysisError):
                params.check_source(steps, python, definitions)

    def test_malformed_placeholders_are_refused_instead_of_slipping_through(self):
        for text in ('{{Unknown}}', '{{unknown-name}}', '{{ product_code }}', '{{product_code}', '{product_code}}', '{{}}', '{{1abc}}', '}}x{{'):
            with self.subTest(text=text):
                with self.assertRaises(AnalysisError):
                    params.check_source(STEPS_P, PYTHON_P + "\nx = '" + text + "'", DEFS)
                with self.assertRaises(AnalysisError):
                    params.check_source([{'name': 'w_daily', 'query': STEPS_P[0]['query'] + ' -- ' + text}], PYTHON_P, DEFS)
        with self.assertRaises(AnalysisError):  # 置き換えの後に、波括弧の表記が残ることも許さない
            params.concrete_code([{'name': 'w_a', 'query': 'SELECT {{Bad}}'}], 'x = 1', {})

    def test_definitions_are_validated(self):
        ok = params.validate_definitions(DEFS)
        self.assertEqual([item['name'] for item in ok], ['product_code', 'period_from', 'period_to'])
        cases = {
            'not a list': 'x', 'extra key': [{**DEFS[0], 'x': 1}], 'missing key': [{'name': 'a'}], 'bad name': [{**DEFS[0], 'name': 'Product'}],
            'name with a trailing newline': [{**DEFS[0], 'name': 'product_code' + chr(10)}],
            'duplicate': [DEFS[0], DEFS[0]], 'unknown type': [{**DEFS[0], 'type': 'supplier'}], 'blank label': [{**DEFS[0], 'label': ' '}],
            'date for a non period name': [{**DEFS[0], 'type': 'date', 'default': '2026-01-01'}],
            'period name that is not a date': [{**DEFS[1], 'type': 'product_code', 'default': 'P-001'}],
            'only period_from': DEFS[:2], 'reversed period': [DEFS[0], {**DEFS[1], 'default': '2026-02-01'}, DEFS[2]],
            'default not registered': [{**DEFS[0], 'default': 'P-999'}], 'default with a quote': [{**DEFS[0], 'default': "P'-1"}],
            'bad date': [DEFS[0], {**DEFS[1], 'default': '2026-02-30'}, DEFS[2]],
        }
        for label, definitions in cases.items():
            with self.subTest(label=label), self.assertRaises(AnalysisError):
                params.validate_definitions(definitions)

    def test_values_are_checked_for_format_existence_unknown_names_and_period_order(self):
        self.assertEqual(params.resolve_values(DEFS, {'product_code': 'P-002'})['product_code'], 'P-002')
        self.assertEqual(params.resolve_values(DEFS, {})['period_from'], '2026-01-01')
        bad = [{'product_code': 'P-999'}, {'product_code': "P-001'; DROP TABLE x; --"}, {'product_code': 'P 001'}, {'product_code': 5},
               {'product_code': ''}, {'product_code': 'あ'}, {'other': 'x'}, {'period_from': '2026-03-01'}, {'period_to': '2025-12-31'},
               {'period_from': '2026/01/01'}, {'period_from': 20260101}]
        for supplied in bad:
            with self.subTest(supplied=supplied), self.assertRaises(AnalysisError):
                params.resolve_values(DEFS, supplied)
        with self.assertRaises(AnalysisError):
            params.resolve_values(DEFS, ['x'])

    def test_the_format_check_works_even_when_the_existence_check_accepts_anything(self):
        # 実在の確認が通る値でも、形式が不正なら(SQL・Pythonの文字列を壊し得る文字は)拒否する
        with patch.dict(params.TYPES['product_code'], {'exists': lambda value: value}):
            for value in ("P-001'; DROP TABLE x; --", 'P 001', 'P"001', 'P\\001', 'P-001\n', 'あ', 'x' * 41, '', '{{product_code}}'):
                with self.subTest(value=value), self.assertRaises(AnalysisError):
                    params.resolve_values(DEFS, {'product_code': value})
            self.assertEqual(params.resolve_values(DEFS, {'product_code': 'A_b-9' + 'x' * 35})['product_code'], 'A_b-9' + 'x' * 35)

    def test_ship_to_codes_are_checked_against_the_analysis_connection(self):
        definition = [{'name': 'ship_to', 'type': 'ship_to_code', 'label': '納入先', 'default': 'ZGHC'}]
        with patch.dict(params.TYPES['ship_to_code'], {'exists': lambda value: value if value == 'ZGHC' else None}):
            self.assertEqual(params.resolve_values(definition, {})['ship_to'], 'ZGHC')
            with self.assertRaises(AnalysisError):
                params.resolve_values(definition, {'ship_to': 'XXXX'})

    def test_the_real_checkers_use_the_masters(self):
        from masters.models import Customer
        Customer.objects.create(customer_code='REAL-C1', customer_name='実在の得意先')
        self.assertEqual(params._exists_customer('REAL-C1'), 'REAL-C1')
        self.assertIsNone(params._exists_customer('NOPE-2'))
        self.assertIsNone(params._exists_customer('REAL-P1'))
        # 品番は公開ビュー(v_ai_product)、納入先コードは v_ai_shipment を、分析用接続で確認する(SQLiteにビューがないため、接続を差し替える)
        with fake_reader([('REAL-P1',)]) as cursor:
            self.assertEqual(params._exists_product('real-p1'), 'REAL-P1')
            self.assertIn('`v_ai_product`', cursor.executed[-1][0]); self.assertEqual(cursor.executed[-1][1], ['real-p1'])
        definitions = [{'name': 'p', 'type': 'product_code', 'label': '品番', 'default': 'real-p1'}]
        with fake_reader([('REAL-P1',)]), patch.dict(params.TYPES['product_code'], {'exists': params._exists_product}):
            self.assertEqual(params.resolve_values(definitions, {})['p'], 'REAL-P1')
        with fake_reader([]), patch.dict(params.TYPES['product_code'], {'exists': params._exists_product}):
            with self.assertRaises(AnalysisError):
                params.resolve_values(definitions, {'p': 'NOPE-1'})

    def test_a_master_failure_is_a_fixed_503_for_products_and_customers(self):
        from django.db import DatabaseError
        with patch('django.db.models.query.QuerySet.first', side_effect=DatabaseError('SECRET-DB')):
            with self.assertRaises(AnalysisError) as caught:
                params._exists_customer('X-1')
            self.assertEqual(caught.exception.status_code, 503)
            self.assertIn('顧客コード', str(caught.exception.detail)); self.assertNotIn('SECRET', str(caught.exception.detail))
        for name, label in (('_exists_product', '品番'), ('_exists_ship_to', '納入先コード')):
            class Broken:
                def __getitem__(self, key):
                    raise DatabaseError('SECRET-DB')
            with self.subTest(name=name), patch.object(params, 'connections', Broken()), patch.dict(params.settings.DATABASES, {'ai_reader': {'USER': 'pm_ai_reader'}}):
                with self.assertRaises(AnalysisError) as caught:
                    getattr(params, name)('X-1')
                self.assertEqual(caught.exception.status_code, 503)
                self.assertIn(label, str(caught.exception.detail)); self.assertNotIn('SECRET', str(caught.exception.detail))

    def test_the_ship_to_check_uses_a_bound_query_on_the_reader_connection_only(self):
        from django.db import DatabaseError
        from django.db.utils import ConnectionDoesNotExist

        with fake_reader([("ZG'HC",)]) as cursor:
            self.assertEqual(params._exists_ship_to("ZG'HC"), "ZG'HC")
            self.assertEqual(cursor.executed[-1], ('SELECT DISTINCT CAST(`ship_to_code` AS BINARY) FROM `v_ai_shipment` WHERE `ship_to_code` = %s', ["ZG'HC"]))  # 値は、束縛パラメータ
        with fake_reader([]):
            self.assertIsNone(params._exists_ship_to('NONE'))
        with patch.dict(params.settings.DATABASES, {'ai_reader': {'USER': 'someone_else'}}), self.assertRaises(AnalysisError) as caught:
            params._exists_ship_to('ZGHC')
        self.assertEqual(caught.exception.status_code, 503)
        for error in (DatabaseError('SECRET-DB'), ConnectionDoesNotExist('SECRET')):
            class Broken:
                def __getitem__(self, name):
                    raise error
            with self.subTest(error=type(error).__name__), patch.object(params, 'connections', Broken()),                     patch.dict(params.settings.DATABASES, {'ai_reader': {'USER': 'pm_ai_reader'}}), self.assertRaises(AnalysisError) as caught:
                params._exists_ship_to('ZGHC')
            self.assertEqual(caught.exception.status_code, 503); self.assertNotIn('SECRET', str(caught.exception.detail))

    def test_the_type_registry_is_the_single_place_to_add_types(self):
        self.assertEqual(set(params.TYPES), {'date', 'product_code', 'customer_code', 'ship_to_code'})


class SaveTests(ParamBase):
    def test_a_parameterized_plan_is_saved_in_source_form_with_the_approved_concrete_hashes(self):
        plan = param_plan(self.creator.pk)
        fields = service._fields_from_plan(plan)
        self.assertEqual((fields['sql_steps'], fields['python_code'], fields['parameters']), (STEPS_P, PYTHON_P, DEFS))
        bundle = cg.make_bundle(plan['codegen']['steps'], plan['codegen']['python'], VIEWS)
        self.assertEqual((fields['sql_sha256'], fields['python_sha256'], fields['executed_code_sha256']),
                         (bundle.sql_sha256, bundle.python_sha256, bundle.executed_code_sha256))
        self.assertEqual(fields['content_sha256'], service._content_sha256(fields))
        self.assertNotEqual(fields['content_sha256'], service._content_sha256({**fields, 'parameters': []}))

    def test_a_template_without_variables_keeps_the_legacy_hash_and_an_empty_definition(self):
        fields = service._fields_from_plan(make_plan(self.creator.pk))
        self.assertEqual(fields['parameters'], [])
        material = {
            'name': fields['name'], 'purpose': fields['purpose'], 'procedure': fields['procedure'], 'output_spec': fields['output_spec'],
            'conditions': fields['conditions'], 'datasets': fields['datasets'], 'date_from': fields['date_from'].isoformat(),
            'date_to': fields['date_to'].isoformat(), 'sql_steps': fields['sql_steps'], 'python_code': fields['python_code'],
            'wrapper_version': fields['wrapper_version'], 'executed_code_sha256': fields['executed_code_sha256'],
        }
        legacy = hashlib.sha256(json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
        self.assertEqual(fields['content_sha256'], legacy)

    def test_a_source_that_does_not_reproduce_the_approved_code_is_refused(self):
        plan = param_plan(self.creator.pk)
        plan['codegen']['python'] = plan['codegen']['python'] + "\nemit_report('別')"
        bundle = cg.make_bundle(plan['codegen']['steps'], plan['codegen']['python'], VIEWS)
        plan['codegen']['executed_code_sha256'] = bundle.executed_code_sha256
        with self.assertRaises(AnalysisError) as caught:
            service._fields_from_plan(plan)
        self.assertEqual(caught.exception.status_code, 409)

    def test_literals_left_in_the_source_and_broken_definitions_are_refused_at_save(self):
        for label, kwargs in {
            'default left': dict(python=PYTHON_P + "\nx = 'P-001'"),
            'date literal': dict(python=PYTHON_P + "\nd = '2026-05-05'"),
            'unused variable': dict(steps=[{'name': 'w_daily', 'query': STEPS_P[0]['query'].replace('product_code = {{product_code}} AND ', '')}], python=PYTHON),
            'broken definition': dict(definitions=[{**DEFS[0], 'default': 'P-999'}, *DEFS[1:]]),
        }.items():
            with self.subTest(label=label), self.assertRaises(AnalysisError):
                service._fields_from_plan(param_plan(self.creator.pk, **kwargs))

    def test_period_defaults_must_match_the_approved_analysis_period(self):
        feb = [DEFS[0], {**DEFS[1], 'default': '2026-02-01'}, {**DEFS[2], 'default': '2026-02-28'}]
        plan = param_plan(self.creator.pk, definitions=feb)  # 分析案の期間は 2026-01-01～01-31 のまま
        with self.assertRaises(AnalysisError) as caught:
            service._fields_from_plan(plan)
        self.assertEqual(caught.exception.status_code, 409)
        plan['proposal']['date_from'], plan['proposal']['date_to'] = '2026-02-01', '2026-02-28'
        self.assertEqual(service._fields_from_plan(plan)['date_from'].isoformat(), '2026-02-01')

    def test_an_unreadable_source_is_a_fixed_409(self):
        plan = param_plan(self.creator.pk)
        plan['codegen']['template_source'] = {'steps': STEPS_P}
        with self.assertRaises(AnalysisError) as caught:
            service._fields_from_plan(plan)
        self.assertEqual(caught.exception.status_code, 409)

    def test_the_definition_is_shown_only_with_the_content(self):
        row = self.param_row(status='pending_admin')
        creator = self.call('ai-analysis-template', self.creator, 'get', template_id=row.pk).data
        other = self.call('ai-analysis-template', self.other, 'get', template_id=row.pk).data
        self.assertEqual(creator['parameters'], DEFS)
        self.assertNotIn('parameters', other)
        approved = self.param_row(status='approved')
        self.assertEqual(self.call('ai-analysis-template', self.other, 'get', template_id=approved.pk).data['parameters'], DEFS)
        listed = self.call('ai-analysis-templates', self.other, 'get').data['results']
        self.assertEqual([r.get('parameters') for r in listed if r['id'] == approved.pk], [DEFS])


class ApproveTests(ParamBase):
    def test_an_admin_can_approve_a_parameterized_template_and_the_hash_still_matches(self):
        row = self.param_row(status='pending_admin')
        self.assertEqual(self.approve(self.admin, row).status_code, 200)
        row.refresh_from_db()
        self.assertEqual(row.status, 'approved')

    def test_a_default_that_is_no_longer_registered_stops_the_approval_without_changing_the_state(self):
        row = self.param_row(status='pending_admin')
        with patch.dict(params.TYPES['product_code'], {'exists': lambda value: None}):
            response = self.approve(self.admin, row)
        self.assertEqual(response.status_code, 400)
        row.refresh_from_db()
        self.assertEqual((row.status, row.state_revision), ('pending_admin', 1))

    def test_a_tampered_definition_fails_the_hash_check(self):
        row = self.param_row(status='pending_admin')
        AIAnalysisTemplate.objects.filter(pk=row.pk).update(parameters=[{**DEFS[0], 'default': 'P-002'}, *DEFS[1:]])
        self.assertEqual(self.approve(self.admin, row).status_code, 409)


class ReuseTests(ParamBase):
    def test_reuse_without_values_uses_the_defaults_and_the_approved_code(self):
        row = self.param_row()
        response = self.reuse_with(self.other, row)
        self.assertEqual(response.status_code, 201)
        plan, _ = FakeStore.created[0]
        self.assertEqual((plan['proposal']['date_from'], plan['proposal']['date_to']), ('2026-01-01', '2026-01-31'))
        self.assertEqual(plan['template']['values'], {'product_code': 'P-001', 'period_from': '2026-01-01', 'period_to': '2026-01-31'})
        self.assertEqual(plan['codegen']['executed_code_sha256'], row.executed_code_sha256)
        self.assertNotIn('{{', json.dumps(plan['codegen']['steps']) + plan['codegen']['python'])

    def test_reuse_with_new_values_builds_new_code_and_a_new_period_that_needs_the_approvals_again(self):
        row = self.param_row()
        body = {'product_code': 'P-002', 'period_from': '2026-02-01', 'period_to': '2026-02-28'}
        response = self.reuse_with(self.other, row, body)
        self.assertEqual(response.status_code, 201)
        plan, _ = FakeStore.created[0]
        self.assertEqual((plan['proposal']['date_from'], plan['proposal']['date_to']), ('2026-02-01', '2026-02-28'))
        self.assertEqual(plan['template']['values'], body)
        query = plan['codegen']['steps'][0]['query']
        self.assertIn("product_code = 'P-002'", query); self.assertIn("'2026-02-01' AND '2026-02-28'", query)
        self.assertNotEqual(plan['codegen']['executed_code_sha256'], row.executed_code_sha256)
        self.assertEqual((plan['status'], plan['method_approved_at'], plan['data_approved_at'], plan['codegen']['status']),
                         ('awaiting_method', None, None, 'generated'))
        bundle = cg.make_bundle(plan['codegen']['steps'], plan['codegen']['python'], VIEWS)
        self.assertEqual(plan['codegen']['executed_code_sha256'], bundle.executed_code_sha256)

    def test_only_one_value_can_be_changed_and_the_others_keep_their_defaults(self):
        row = self.param_row()
        self.assertEqual(self.reuse_with(self.other, row, {'product_code': 'P-002'}).status_code, 201)
        plan, _ = FakeStore.created[0]
        self.assertEqual((plan['proposal']['date_from'], plan['template']['values']['product_code']), ('2026-01-01', 'P-002'))

    def test_invalid_values_create_no_plan(self):
        row = self.param_row()
        for body in ({'product_code': 'P-999'}, {'product_code': "x'; --"}, {'nope': 'x'}, {'period_from': '2026-03-01'}, {'period_to': '2025-01-01'},
                     {'period_from': 'あ'}, 'abc', ['x']):
            with self.subTest(body=body):
                self.assertEqual(self.reuse_with(self.other, row, body).status_code, 400)
        self.assertEqual(self.call('ai-analysis-template-plans', self.other, data={'parameters': {}, 'other': 1}, template_id=row.pk).status_code, 400)
        self.assert_no_plan()

    def test_a_template_without_variables_refuses_values_and_a_period_change(self):
        row = self.row(status='approved')
        for body in ({'period_from': '2026-02-01'}, {'product_code': 'P-001'}):
            with self.subTest(body=body):
                self.assertEqual(self.reuse_with(self.other, row, body).status_code, 400)
        self.assert_no_plan()
        self.assertEqual(self.reuse_with(self.other, row, {}).status_code, 201)
        self.assertEqual(self.reuse_with(self.other, row).status_code, 201)

    def test_a_template_without_period_variables_keeps_its_period(self):
        definitions = [DEFS[0]]
        steps = [{'name': 'w_daily', 'query': 'SELECT shipment_date, SUM(quantity) AS q FROM v_ai_shipment WHERE product_code = {{product_code}} GROUP BY shipment_date'}]
        row = self.param_row(steps=steps, python=PYTHON + "\nemit_report('品番 ' + {{product_code}})", definitions=definitions)
        self.assertEqual(self.reuse_with(self.other, row, {'period_from': '2026-02-01'}).status_code, 400)
        self.assertEqual(self.reuse_with(self.other, row, {'product_code': 'P-002'}).status_code, 201)
        plan, _ = FakeStore.created[0]
        self.assertEqual((plan['proposal']['date_from'], plan['proposal']['date_to']), ('2026-01-01', '2026-01-31'))

    def test_empty_or_non_object_values_are_refused_not_treated_as_no_values(self):
        row = self.param_row()
        for body in (0, '', [], None, False):
            with self.subTest(body=body):
                response = self.call('ai-analysis-template-plans', self.other, data={'parameters': body}, template_id=row.pk)
                self.assertEqual(response.status_code, 400)
        self.assert_no_plan()
        self.assertEqual(self.call('ai-analysis-template-plans', self.other, data={'parameters': {}}, template_id=row.pk).status_code, 201)

    def test_the_integrity_check_uses_the_stored_defaults_and_rejects_a_broken_row(self):
        row = self.param_row()
        AIAnalysisTemplate.objects.filter(pk=row.pk).update(python_code=row.python_code + "\n# 改ざん")
        self.assertEqual(self.reuse_with(self.other, row, {'product_code': 'P-002'}).status_code, 409)
        self.assert_no_plan()

    def test_values_that_make_code_failing_the_current_check_are_refused(self):
        row = self.param_row()
        with patch.object(cg, 'validate_generated', side_effect=[[], ['python:import_not_allowed']]) as check:
            with patch('ai.services.analysis_template_reuse_service.validate_generated', check):
                response = self.reuse_with(self.other, row, {'product_code': 'P-002'})
        self.assertEqual(response.status_code, 409)
        self.assert_no_plan()

    def test_the_reuse_permission_rules_still_apply_to_a_parameterized_template(self):
        pending = self.param_row(status='pending_admin')
        self.assertEqual(self.reuse_with(self.other, pending, {'product_code': 'P-002'}).status_code, 403)
        self.assertEqual(self.reuse_with(self.creator, pending, {'product_code': 'P-002'}).status_code, 201)
        self.assertEqual(self.reuse_with(self.other, self.param_row(status='rejected'), {}).status_code, 404)

    def test_a_missing_value_source_is_a_fixed_error_not_a_fallback(self):
        row = self.param_row()
        with patch.dict(params.TYPES['product_code'], {'exists': lambda value: (_ for _ in ()).throw(AnalysisError('品番を確認できません。', 503))}):
            response = self.reuse_with(self.other, row, {'product_code': 'P-002'})
        self.assertEqual(response.status_code, 503)
        self.assert_no_plan()


HALF_STEPS = [
    {'name': 'w_first', 'query': 'SELECT 1 FROM v_ai_shipment WHERE shipment_date BETWEEN {{first_from}} AND {{first_to}}'},
    {'name': 'w_second', 'query': 'SELECT 2 FROM v_ai_shipment WHERE shipment_date BETWEEN {{second_from}} AND {{second_to}}'},
]
HALF_DEFS = [
    {'name': 'first_from', 'type': 'date', 'label': '前半の開始日', 'default': '2026-01-01'},
    {'name': 'first_to', 'type': 'date', 'label': '前半の終了日', 'default': '2026-01-15'},
    {'name': 'second_from', 'type': 'date', 'label': '後半の開始日', 'default': '2026-01-16'},
    {'name': 'second_to', 'type': 'date', 'label': '後半の終了日', 'default': '2026-01-31'},
]


class MultiPeriodReuseTests(ParamBase):
    """複数の期間の変数(2026-10-07、BOSS承認)の再利用API: 比べる期間を指定でき、テンプレートの期間(1月)の外・逆順は400。"""

    def row(self):
        return self.param_row(steps=HALF_STEPS, python=PYTHON, definitions=HALF_DEFS)

    def test_compared_periods_can_be_changed_inside_the_template_period(self):
        row = self.row()
        body = {'first_from': '2026-01-02', 'first_to': '2026-01-10', 'second_from': '2026-01-11', 'second_to': '2026-01-20'}
        response = self.reuse_with(self.other, row, body)
        self.assertEqual(response.status_code, 201)
        plan, _ = FakeStore.created[0]
        queries = [step['query'] for step in plan['codegen']['steps']]
        self.assertIn("BETWEEN '2026-01-02' AND '2026-01-10'", queries[0])
        self.assertIn("BETWEEN '2026-01-11' AND '2026-01-20'", queries[1])
        self.assertEqual((plan['proposal']['date_from'], plan['proposal']['date_to']), ('2026-01-01', '2026-01-31'))  # 全体の期間は、テンプレートのまま
        self.assertEqual(plan['template']['values'], body)
        self.assertNotIn('{{', json.dumps(plan['codegen']['steps']) + plan['codegen']['python'])

    def test_a_period_outside_the_template_period_or_reversed_is_a_400_and_creates_nothing(self):
        row = self.row()
        for body in ({'first_from': '2025-12-31'}, {'second_to': '2026-02-01'}, {'first_from': '2026-01-20'}, {'second_from': '2026-02-01', 'second_to': '2026-02-10'}):
            with self.subTest(body=body):
                FakeStore.created.clear()
                response = self.reuse_with(self.other, row, body)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(FakeStore.created, [])

    def test_the_period_pairs_are_defaults_when_not_given(self):
        response = self.reuse_with(self.other, self.row())
        self.assertEqual(response.status_code, 201)
        plan, _ = FakeStore.created[0]
        self.assertEqual(plan['template']['values'], {item['name']: item['default'] for item in HALF_DEFS})


class NormalizeAndQuoteTests(ParamBase):
    def test_a_quote_next_to_a_placeholder_is_refused_because_the_replacement_adds_quotes(self):
        for text in ("x = '{{product_code}}'", 'x = "{{product_code}}"', "x = '{{product_code}}", "x = {{product_code}}'", 'x = "{{product_code}}'):
            with self.subTest(text=text), self.assertRaises(AnalysisError):
                params.check_source(STEPS_P, PYTHON_P + chr(10) + text, DEFS)
        params.check_source(STEPS_P, PYTHON_P + chr(10) + "x = f({{product_code}}, 'a')", DEFS)  # 離れていれば、よい

    def test_normalize_takes_the_period_from_the_plan_and_requires_a_default_for_codes(self):
        raw = [{'name': 'product_code', 'type': 'product_code', 'label': '品番', 'default': 'P-001'},
               {'name': 'period_from', 'type': 'date', 'label': '開始日', 'default': '1999-01-01'},
               {'name': 'period_to', 'type': 'date', 'label': '終了日'}]
        out = params.normalize_definitions(raw, '2026-02-01', '2026-02-28')
        self.assertEqual({item['name']: item['default'] for item in out}, {'product_code': 'P-001', 'period_from': '2026-02-01', 'period_to': '2026-02-28'})
        bad = [[], 'x', [{'name': 'a'}], [{'name': 'product_code', 'type': 'product_code', 'label': 'x'}],
               [{'name': 'product_code', 'type': 'product_code', 'label': 'x', 'default': 'P-001', 'extra': 1}],
               [{'name': 'product_code', 'type': 'product_code', 'label': 'x', 'default': 'P-999'}], raw[:2]]
        for value in bad:
            with self.subTest(value=str(value)[:50]), self.assertRaises(AnalysisError):
                params.normalize_definitions(value, '2026-02-01', '2026-02-28')

    def test_has_date_literal_finds_dates_in_sql_and_python_only_in_the_form_given(self):
        self.assertTrue(params.has_date_literal([{'name': 'w_a', 'query': "SELECT 1 WHERE d >= '2026-01-01'"}], 'x = 1'))
        self.assertTrue(params.has_date_literal([{'name': 'w_a', 'query': 'SELECT 1'}], "d = '2026-01-01'"))
        self.assertFalse(params.has_date_literal([{'name': 'w_a', 'query': 'SELECT 1'}], 'x = 1'))
        self.assertFalse(params.has_date_literal(STEPS_P, PYTHON_P))  # 変数の形のコードには、日付がない
