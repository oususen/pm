"""分析用SQL・Pythonの生成(2-B): 送信内容・送信確認・生成回数・状態不明・検査・試行実行・コード承認を検証する。

Redisは、開発のMemurai(AI_ANALYSIS_REDIS_URL)を使う。AIの呼出しは模擬する(外部AIへは接続しない)。
実launcher(Docker)を使う確認は、AI_ANALYSIS_LAUNCHER_URL_FOR_TEST が設定されている場合だけ実行する。
"""
import ast
import json
import os
import threading
import time
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from ai.services import analysis_codegen_service as cg
from ai.services import analysis_guard_runtime as guard
from ai.services.analysis_plan_store import AnalysisError, AnalysisPlanStore
from ai.test_analysis_execution import FakeLauncher

POLICY = SimpleNamespace(max_memory_mb=512, max_cpu_cores=Decimal('1.0'), max_execution_seconds=60, max_fetch_rows=100_000,
                         plan_cache_ttl_minutes=60)
OWNER = 987001
DATASETS = [
    {'view': 'v_ai_shipment', 'fields': ['id', 'shipment_date', 'quantity', 'customer_code']},
    {'view': 'v_ai_purchase_receipt', 'fields': ['id', 'arrival_date', 'qty']},
]
VIEWS = [d['view'] for d in DATASETS]
GOOD_STEPS = [{'name': 'w_daily', 'query': 'SELECT shipment_date, SUM(quantity) AS q FROM v_ai_shipment GROUP BY shipment_date'}]
GOOD_PYTHON = "rows = con.sql('SELECT shipment_date, q FROM w_daily ORDER BY shipment_date').fetchall()\nemit_table('日別', ['日', '数量'], [[str(a), str(b)] for a, b in rows])"
GOOD_RESPONSE = json.dumps({'steps': GOOD_STEPS, 'python': GOOD_PYTHON}, ensure_ascii=False)
SENTINELS = ('ＳＥＣＲＥＴ目的', 'ＳＥＣＲＥＴ題名', 'ＳＥＣＲＥＴ手順', 'ＳＥＣＲＥＴ出力')


class FakeRedactor:
    """登録名称(ＳＥＣＲＥＴ…)をコードへ置換する。実際の置換規則の検証は、既存の分析案作成のテストで行う。"""

    def redact_text(self, text):
        return text.replace('ＳＥＣＲＥＴ', 'CODE-')


class Crash(BaseException):
    """AI呼出しの途中でプロセスが止まった状況を作る(通常の例外処理を通らない)。"""


def make_plan(provider='deepseek', model='m1'):
    store = AnalysisPlanStore()
    proposal = {
        'title': 'ＳＥＣＲＥＴ題名', 'steps': ['ＳＥＣＲＥＴ手順1', '手順2'], 'outputs': ['ＳＥＣＲＥＴ出力'], 'datasets': DATASETS,
        'purpose': 'ＳＥＣＲＥＴ目的', 'external_purpose': 'CODE-目的', 'date_from': '2026-01-01', 'date_to': '2026-01-31',
        'materials': [], 'conditions': '指定期間の全登録行（追加の絞り条件なし）', 'provider': provider, 'model': model,
    }
    plan = store.create(OWNER, proposal, 30)

    def approved(current):
        current['status'] = 'data_approved'
        current['preview'] = {'datasets': [{'view': 'v_ai_shipment', 'rows': 2724}, {'view': 'v_ai_purchase_receipt', 'rows': 498}], 'total_rows': 3222}
        current['method_approved_at'] = current['data_approved_at'] = datetime.now().isoformat()

    return store.update(plan['id'], OWNER, plan['revision'], approved)


class CodegenBase(SimpleTestCase):
    def setUp(self):
        self.store = AnalysisPlanStore()
        self.keys = []
        patches = [
            patch.object(cg, 'build_analysis_code_redactor', lambda: FakeRedactor()),
            patch.object(cg, 'get_qwen_analysis_timeout', lambda: 90),
            patch.object(cg, 'get_analysis_execution_policy', lambda: POLICY),
            patch.object(cg, 'resolve_planning_provider', lambda data: (data['provider'], data['model'])),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        self.addCleanup(self.cleanup_keys)

    def new_plan(self, **kwargs):
        plan = make_plan(**kwargs)
        self.keys.append(self.store._key(plan['id']))
        return plan

    def cleanup_keys(self):
        for key in self.keys:
            self.store.client.delete(key)

    def confirmation_for(self, plan):
        return cg.preview(OWNER, plan['id'], plan['revision'])['confirmation']

    def generate(self, plan, response=GOOD_RESPONSE):
        with patch.object(cg, '_call_ai', return_value=response) as call:
            result = cg.generate(OWNER, plan['id'], plan['revision'], self.confirmation_for(plan))
        return result, call

    def current(self, plan):
        return self.store.get(plan['id'], OWNER)


class StaticChecksTest(SimpleTestCase):
    def test_python_allowed_and_rejected_constructs(self):
        self.assertEqual(guard.validate_python(GOOD_PYTHON), [])
        cases = {
            'import os\nemit_report("x")': 'import_not_allowed',
            'from subprocess import run\nemit_report("x")': 'import_not_allowed',
            'import json, socket\nemit_report("x")': 'import_not_allowed',
            'open("f")\nemit_report("x")': 'forbidden_name',
            'eval("1")\nemit_report("x")': 'forbidden_name',
            'getattr(con, "x")\nemit_report("x")': 'forbidden_name',
            'x = ().__class__\nemit_report("x")': 'private_attribute',
            'x = con._raw\nemit_report("x")': 'private_attribute',
            'con.close()\nemit_report("x")': 'con_method_not_allowed',
            'x = 1': 'no_output',
            'def f(:\n': 'syntax_error',
            'global x\nemit_report("x")': 'construct_not_allowed',
            'g = (i for i in [1])\nx = g.gi_frame\nemit_report("x")': 'private_attribute',  # 生成器のフレームから、外枠の変数へ届く
            'g = (i for i in [1])\nx = g.gi_frame.f_back.f_locals\nemit_report("x")': 'private_attribute',
            'try:\n    1/0\nexcept Exception as e:\n    x = e.tb_frame\nemit_report("x")': 'private_attribute',
            'def f():\n    pass\nx = f.co_consts\nemit_report("x")': 'private_attribute',
        }
        for source, expected in cases.items():
            self.assertIn(expected, guard.validate_python(source), source)
        self.assertEqual(guard.validate_python('import json, math, datetime, decimal, statistics, collections, itertools, re\nemit_report("x")'), [])

    def test_steps_rules(self):
        ok = [{'name': 'w_a', 'query': 'SELECT 1'}]
        guard.validate_steps(ok, VIEWS)
        bad_cases = [
            [{'name': 'a', 'query': 'SELECT 1'}],  # w_で始まらない
            [{'name': 'w_A', 'query': 'SELECT 1'}],  # 大文字
            [{'name': 'v_ai_shipment', 'query': 'SELECT 1'}],  # 承認ビューと同名
            [{'name': 'w_a', 'query': 'SELECT 1'}, {'name': 'w_a', 'query': 'SELECT 2'}],  # 重複
            [{'name': 'w_a', 'query': ''}],
            [{'name': 'w_a', 'query': 'SELECT 1', 'extra': 1}],
            [{'name': 'w_' + 'x' * 41, 'query': 'SELECT 1'}],  # 長すぎる
            'SELECT 1',
        ]
        for steps in bad_cases:
            with self.assertRaises(guard.GuardError, msg=str(steps)[:40]):
                guard.validate_steps(steps, VIEWS)

    def test_size_and_count_limits_are_counted_separately_and_for_the_whole_code(self):
        many = [{'name': f'w_{i}', 'query': 'SELECT 1'} for i in range(cg.MAX_STEPS + 1)]
        self.assertIn('too_many_steps', cg.validate_generated(many, GOOD_PYTHON, VIEWS))
        big_sql = [{'name': 'w_a', 'query': 'SELECT ' + '1,' * (cg.MAX_SQL_BYTES // 2) + '1'}]
        self.assertIn('sql_too_large', cg.validate_generated(big_sql, GOOD_PYTHON, VIEWS))
        big_python = GOOD_PYTHON + '\n# ' + 'x' * cg.MAX_PYTHON_BYTES
        self.assertIn('python_too_large', cg.validate_generated(GOOD_STEPS, big_python, VIEWS))
        # SQL・Pythonがそれぞれ上限内でも、固定外枠を加えたコード全体が64KBを超えれば拒否する
        python_pad = cg.MAX_PYTHON_BYTES - len(GOOD_PYTHON.encode('utf-8')) - 8
        python_near = GOOD_PYTHON + '\n# ' + 'y' * python_pad
        sql_near = [{'name': 'w_a', 'query': 'SELECT 1 -- '}]
        sql_near[0]['query'] += 'x' * (cg.MAX_SQL_BYTES - len(cg.steps_text(sql_near).encode('utf-8')) - 8)
        self.assertLessEqual(len(python_near.encode('utf-8')), cg.MAX_PYTHON_BYTES)
        self.assertLessEqual(len(cg.steps_text(sql_near).encode('utf-8')), cg.MAX_SQL_BYTES)
        total = len(cg.compose_code(sql_near, python_near, VIEWS).encode('utf-8'))
        problems = cg.validate_generated(sql_near, python_near, VIEWS)
        # SQL・Pythonがそれぞれ上限内でも、固定外枠を加えたコード全体が64KBを超えれば、コード全体の上限で拒否する
        self.assertEqual('code_too_large' in problems, total > cg.MAX_CODE_BYTES, (total, problems))
        self.assertNotIn('sql_too_large', problems)
        self.assertNotIn('python_too_large', problems)
        # 組み立て後の全体が上限を超える場合を、必ず作って確認する(外枠の大きさを、見えるようにする)
        with patch.object(cg, 'MAX_CODE_BYTES', len(cg.compose_code(GOOD_STEPS, GOOD_PYTHON, VIEWS).encode('utf-8')) - 1):
            self.assertIn('code_too_large', cg.validate_generated(GOOD_STEPS, GOOD_PYTHON, VIEWS))
        self.assertGreater(len(cg.GUARD_SOURCE.encode('utf-8')), 3000)  # 外枠は、64KBの一部を使う

    def test_response_parsing_is_strict(self):
        self.assertEqual(cg.parse_response(GOOD_RESPONSE)[0], 'generated')
        self.assertEqual(cg.parse_response('{"unsupported": "理由"}')[:2], ('unsupported', '理由'))
        for raw in ('not json', '[]', '{"steps": []}', '{"steps": [], "python": "x", "extra": 1}', '{"unsupported": "x", "steps": []}', None):
            self.assertEqual(cg.parse_response(raw)[0], 'invalid', raw)

    def test_composed_code_roundtrips_any_text_and_hashes_are_stable(self):
        tricky = "s = '''三重\"\"\"クォート\\n''' + \"\\\\ \" + 'あ😀'\nemit_report(s)"
        steps = [{'name': 'w_a', 'query': "SELECT '\\' AS \"q\"\n-- コメント"}]
        code = cg.compose_code(steps, tricky, VIEWS)
        namespace = {}
        exec(compile('\n'.join(code.split('\n', 2)[:2]), 'prefix', 'exec'), namespace)
        self.assertEqual(namespace['_PYTHON_SOURCE'], tricky)
        self.assertEqual(json.loads(namespace['_CONFIG_JSON'])['steps'], steps)
        ast.parse(code)  # 全体が、正しいPythonである
        bundle = cg.make_bundle(steps, tricky, VIEWS)
        again = cg.make_bundle(steps, tricky, VIEWS)
        self.assertEqual(bundle, again)
        self.assertEqual(bundle.executed_code_sha256, cg.sha256_text(code))
        self.assertEqual(bundle.sql_sha256, cg.sha256_text(cg.steps_text(steps)))
        self.assertIsNone(cg.make_bundle([], tricky, VIEWS).sql_sha256)  # 別のSQLがない実行
        self.assertNotEqual(bundle.executed_code_sha256, cg.make_bundle(steps, tricky + ' ', VIEWS).executed_code_sha256)
        self.assertTrue(bundle.wrapper_version.startswith('1-'))


def select_node(from_table=None, cte=None, where=None):
    """DuckDBの構文木(json_serialize_sqlの形)の最小の例。"""
    node = {'type': 'SELECT_NODE', 'modifiers': [], 'cte_map': {'map': cte or []},
            'select_list': [{'class': 'STAR', 'type': 'STAR'}], 'from_table': from_table or {'type': 'EMPTY'}, 'where_clause': where}
    return node


def table(name, schema=''):
    return {'type': 'BASE_TABLE', 'schema_name': schema, 'table_name': name, 'catalog_name': ''}


def tree(node):
    return {'error': False, 'statements': [{'node': node}]}


def cte(name, node):
    return {'key': name, 'value': {'aliases': [], 'query': {'node': node}}}


class GuardTreeTest(SimpleTestCase):
    """構文木の検査(duckdb不要の純粋な部分)。未知の構文を拒否し、WITHの名前の有効範囲を守る。"""
    ALLOWED = ['v_ai_shipment', 'w_a']

    def reason(self, statement_tree):
        with self.assertRaises(guard.GuardError) as caught:
            guard.validate_tree(statement_tree, self.ALLOWED)
        return caught.exception.code

    def test_allowed_references_pass(self):
        guard.validate_tree(tree(select_node(table('v_ai_shipment'))), self.ALLOWED)
        guard.validate_tree(tree(select_node(table('W_A', 'main'))), self.ALLOWED)  # 大文字・mainスキーマ

    def test_unknown_table_reference_types_are_rejected_not_ignored(self):
        for kind in ('SHOW_REF', 'COLUMN_DATA', 'DELIM_GET', 'FUTURE_REF'):
            self.assertEqual(self.reason(tree(select_node({'type': kind}))), 'syntax_not_supported', kind)

    def test_unknown_expression_classes_are_rejected(self):
        node = select_node(table('v_ai_shipment'), where={'class': 'PARAMETER', 'type': 'VALUE_PARAMETER'})
        self.assertEqual(self.reason(tree(node)), 'syntax_not_supported')
        node = select_node(table('v_ai_shipment'), where={'class': 'FUTURE_CLASS', 'type': 'X'})
        self.assertEqual(self.reason(tree(node)), 'syntax_not_supported')

    def test_unknown_query_node_type_is_rejected(self):
        self.assertEqual(self.reason({'error': False, 'statements': [{'node': {'type': 'FUTURE_NODE'}}]}), 'query_not_select')

    def test_with_names_are_visible_only_inside_their_own_query(self):
        inner = select_node(table('x'))
        ok = select_node(table('x'), cte=[cte('x', select_node(table('v_ai_shipment')))])
        guard.validate_tree(tree(ok), self.ALLOWED)  # 同じ問い合わせの中では使える
        # 別の枝(FROMの副問い合わせの中だけで定義したWITH)の名前を、外側で使う
        sibling = select_node({'type': 'JOIN', 'left': {'type': 'SUBQUERY', 'subquery': {'node': select_node(table('x'), cte=[cte('x', select_node(table('v_ai_shipment')))])}},
                               'right': table('x')})
        self.assertEqual(self.reason(tree(sibling)), 'reference_not_allowed')
        # 別の副問い合わせの中で定義したWITHの名前を、システムのテーブル名として使う
        shadow = select_node(table('sqlite_master'), where={'class': 'SUBQUERY', 'type': 'SUBQUERY', 'subquery': {'node': select_node(
            {'type': 'EMPTY'}, cte=[cte('sqlite_master', select_node({'type': 'EMPTY'}))])}})
        self.assertEqual(self.reason(tree(shadow)), 'reference_not_allowed')
        self.assertIsNotNone(inner)

    def test_a_non_recursive_with_cannot_see_itself_but_a_recursive_one_can(self):
        self_reference = select_node(table('sqlite_master'), cte=[cte('sqlite_master', select_node(table('sqlite_master')))])
        self.assertEqual(self.reason(tree(self_reference)), 'reference_not_allowed')  # 自分自身の名前は、実在のシステムテーブルを指す
        recursive = {'type': 'RECURSIVE_CTE_NODE', 'left': select_node({'type': 'EMPTY'}), 'right': select_node(table('t'))}
        guard.validate_tree(tree(select_node(table('t'), cte=[cte('t', recursive)])), self.ALLOWED)

    def test_later_with_definitions_see_earlier_ones_only(self):
        ok = select_node(table('b'), cte=[cte('a', select_node(table('v_ai_shipment'))), cte('b', select_node(table('a')))])
        guard.validate_tree(tree(ok), self.ALLOWED)
        backwards = select_node(table('a'), cte=[cte('b', select_node(table('a'))), cte('a', select_node(table('v_ai_shipment')))])
        self.assertEqual(self.reason(tree(backwards)), 'reference_not_allowed')  # 先に定義されていない名前

    def test_forbidden_schema_functions_and_depth(self):
        self.assertEqual(self.reason(tree(select_node(table('tables', 'information_schema')))), 'reference_not_allowed')
        self.assertEqual(self.reason(tree(select_node({'type': 'TABLE_FUNCTION', 'function': {'function_name': 'duckdb_tables'}}))), 'table_function_not_allowed')
        self.assertEqual(self.reason(tree(select_node(table('v_ai_shipment'), where={'class': 'FUNCTION', 'type': 'FUNCTION', 'function_name': 'getenv'}))), 'function_not_allowed')
        deep = select_node(table('v_ai_shipment'))
        for _ in range(guard.MAX_TREE_DEPTH + 10):
            deep = select_node({'type': 'SUBQUERY', 'subquery': {'node': deep}})
        self.assertEqual(self.reason(tree(deep)), 'query_too_deep')  # 深すぎる構文木は、再帰の上限に頼らず拒否する


class PayloadTest(CodegenBase):
    def test_the_instruction_explains_how_rows_are_read_so_that_models_do_not_use_column_names_on_tuples(self):
        # 実機で、モデルが load_view の結果を直接forで回し、row['列名']で読んで、実行時に失敗した(2026-10-06)
        plan = self.new_plan()
        for external in (False, True):
            system = cg.build_messages(plan, external=external)[0]['content']
            for part in ('結果オブジェクトで、それ自体をforで回したり', '各行はタプル', 'for code, name, qty in rows', '中間テーブルは、con.sql(', 'load_viewに渡せるのは承認済みビュー名だけ'):
                self.assertIn(part, system)

    def test_the_fixed_product_code_rule_is_in_the_code_generation_instruction_for_local_and_external(self):
        # 製品別の集計は、必ず品番で集計し、品番→製品名→数量の順で出す(BOSS承認 2026-10-06)
        plan = self.new_plan()
        for external in (False, True):
            system = cg.build_messages(plan, external=external)[0]['content']
            for part in ('品番(product_code)でGROUP BY', '「品番」「製品名」「数量」の順', '製品名だけで集計しない', 'グラフのラベルにも、品番を含める'):
                self.assertIn(part, system)

    def test_external_payload_replaces_names_in_every_free_text_and_excludes_data_counts_and_users(self):
        plan = self.new_plan()
        messages = cg.build_messages(plan, external=True)
        text = json.dumps(messages, ensure_ascii=False)
        self.assertNotIn('ＳＥＣＲＥＴ', text)  # 目的文・題名・手順・出力案のすべてで、置換されている
        for fragment in ('CODE-目的', 'CODE-題名', 'CODE-手順1', 'CODE-出力'):
            self.assertIn(fragment, text)
        self.assertNotIn('2724', text)  # 承認件数は送らない
        self.assertNotIn('498', text)
        self.assertNotIn(str(OWNER), text)  # 利用者は送らない
        self.assertNotIn('run-tester', text)
        payload = json.loads(messages[1]['content'])
        columns = {d['view']: [c['name'] for c in d['columns']] for d in payload['datasets']}
        self.assertEqual(columns['v_ai_shipment'], DATASETS[0]['fields'])  # 列名と型だけ(idの値は、そもそも持たない)
        self.assertTrue(all('type' in c for d in payload['datasets'] for c in d['columns']))

    def test_local_qwen_payload_is_not_redacted_and_needs_no_confirmation(self):
        plan = self.new_plan(provider='qwen', model='local')
        with patch.object(cg, 'build_analysis_code_redactor', side_effect=AssertionError('ローカルでは、置換を呼ばない')):
            result = cg.preview(OWNER, plan['id'], plan['revision'])
        self.assertFalse(result['confirmation_required'])
        self.assertNotIn('confirmation', result)
        self.assertIn('ＳＥＣＲＥＴ目的', json.dumps(result['messages'], ensure_ascii=False))

    def test_redaction_failure_stops_before_any_send(self):
        plan = self.new_plan()
        confirmation = self.confirmation_for(plan)
        failing = SimpleNamespace(redact_text=lambda text: (_ for _ in ()).throw(AnalysisError('同名で特定できません。')))
        with patch.object(cg, 'build_analysis_code_redactor', lambda: failing), patch.object(cg, '_call_ai') as call:
            with self.assertRaises(AnalysisError):
                cg.generate(OWNER, plan['id'], plan['revision'], confirmation)
        call.assert_not_called()
        self.assertEqual(self.current(plan)['revision'], plan['revision'])  # 回数も数えていない


class ProviderRecheckTest(CodegenBase):
    def test_revoked_external_permission_stops_preview_and_generation_before_any_send(self):
        plan = self.new_plan()
        confirmation = self.confirmation_for(plan)
        denied = AnalysisError('外部AIへの送信が管理設定で許可されていません。', 403)
        with patch.object(cg, 'resolve_planning_provider', side_effect=denied), patch.object(cg, '_call_ai') as call:
            with self.assertRaises(AnalysisError) as caught:
                cg.preview(OWNER, plan['id'], plan['revision'])
            self.assertEqual(caught.exception.status_code, 403)
            with self.assertRaises(AnalysisError):
                cg.generate(OWNER, plan['id'], plan['revision'], confirmation)
        call.assert_not_called()
        self.assertEqual(self.current(plan)['revision'], plan['revision'])  # 回数も数えていない

    def test_changed_provider_settings_are_rejected(self):
        plan = self.new_plan()
        with patch.object(cg, 'resolve_planning_provider', lambda data: ('openrouter', 'x')), self.assertRaises(AnalysisError) as caught:
            cg.preview(OWNER, plan['id'], plan['revision'])
        self.assertEqual(caught.exception.status_code, 409)


class ConfirmationTest(CodegenBase):
    def test_generation_requires_a_matching_confirmation_and_sends_nothing_otherwise(self):
        plan = self.new_plan()
        with patch.object(cg, '_call_ai') as call:
            for bad in (None, '', 'x' * 64):
                with self.assertRaises(AnalysisError) as caught:
                    cg.generate(OWNER, plan['id'], plan['revision'], bad)
                self.assertEqual(caught.exception.status_code, 409)
        call.assert_not_called()

    def test_confirmation_is_bound_to_plan_revision_model_attempt_and_content(self):
        plan = self.new_plan()
        good = cg._confirmation(OWNER, plan['id'], plan['revision'], 'deepseek', 'm1', 1, cg.payload_hash(cg.build_messages(plan, True)))
        self.assertEqual(good, self.confirmation_for(plan))
        base = (OWNER, plan['id'], plan['revision'], 'deepseek', 'm1', 1, cg.payload_hash(cg.build_messages(plan, True)))
        variants = [(OWNER + 1,) + base[1:], (base[0], 'other') + base[2:], base[:2] + (base[2] + 1,) + base[3:],
                    base[:3] + ('openrouter',) + base[4:], base[:4] + ('m2',) + base[5:], base[:5] + (2,) + base[6:], base[:6] + ('0' * 64,)]
        self.assertTrue(all(cg._confirmation(*variant) != good for variant in variants))

    def test_changed_content_invalidates_the_confirmation(self):
        plan = self.new_plan()
        confirmation = self.confirmation_for(plan)
        with patch.object(cg, 'build_analysis_code_redactor', lambda: SimpleNamespace(redact_text=lambda text: text + '!')), \
                patch.object(cg, '_call_ai') as call, self.assertRaises(AnalysisError):
            cg.generate(OWNER, plan['id'], plan['revision'], confirmation)  # 送る内容が変わった(置換結果が違う)
        call.assert_not_called()

    def test_confirmation_cannot_be_reused_after_generation_started(self):
        plan = self.new_plan()
        confirmation = self.confirmation_for(plan)
        with patch.object(cg, '_call_ai', return_value='not json'):
            cg.generate(OWNER, plan['id'], plan['revision'], confirmation)
        with patch.object(cg, '_call_ai') as call, self.assertRaises(AnalysisError) as caught:
            cg.generate(OWNER, plan['id'], plan['revision'], confirmation)  # 同じ確認コード・同じ版
        self.assertEqual(caught.exception.status_code, 409)
        call.assert_not_called()

    def test_concurrent_requests_send_only_once(self):
        plan = self.new_plan()
        confirmation = self.confirmation_for(plan)
        calls, outcomes = [], []

        def slow_ai(*args):
            calls.append(1)
            time.sleep(0.6)
            return GOOD_RESPONSE

        def attempt():
            try:
                cg.generate(OWNER, plan['id'], plan['revision'], confirmation)
                outcomes.append('ok')
            except AnalysisError as exc:
                outcomes.append(exc.status_code)

        with patch.object(cg, '_call_ai', slow_ai):
            threads = [threading.Thread(target=attempt) for _ in range(3)]
            [t.start() for t in threads]
            [t.join() for t in threads]
        self.assertEqual(len(calls), 1)  # 外部AIへの送信は、1回だけ
        self.assertEqual(sorted(map(str, outcomes)), ['409', '409', 'ok'])
        self.assertEqual(self.current(plan)['codegen']['attempts'], 1)


class GenerationTest(CodegenBase):
    def test_success_is_held_only_in_redis_with_hashes_and_without_extending_the_ttl(self):
        plan = self.new_plan()
        ttl_before = self.store.client.pttl(self.store._key(plan['id']))
        result, call = self.generate(plan)
        call.assert_called_once()
        state = result['codegen']
        self.assertEqual((state['status'], state['attempts'], state['inflight']), ('generated', 1, None))
        bundle = cg.make_bundle(GOOD_STEPS, GOOD_PYTHON, VIEWS)
        self.assertEqual((state['sql_sha256'], state['python_sha256'], state['executed_code_sha256'], state['wrapper_version']),
                         (bundle.sql_sha256, bundle.python_sha256, bundle.executed_code_sha256, bundle.wrapper_version))
        self.assertLessEqual(self.store.client.pttl(self.store._key(plan['id'])), ttl_before)  # 有効期限を延長しない
        self.assertEqual(cg.describe_codegen(result)['inflight_state'], None)

    def test_failures_are_counted_and_the_limit_is_never_exceeded(self):
        plan = self.new_plan()
        responses = ['not json', '{"unsupported": "足りない"}', json.dumps({'steps': [{'name': 'bad', 'query': 'SELECT 1'}], 'python': GOOD_PYTHON}),
                     json.dumps({'steps': [], 'python': 'import os\nemit_report("x")'})]
        reasons = []
        for response in responses:
            result, _ = self.generate(plan, response)
            plan = result
            reasons.append(result['codegen']['reasons'])
            self.assertEqual(result['codegen']['status'], 'failed')
        self.assertEqual(plan['codegen']['attempts'], cg.MAX_GENERATIONS)
        self.assertIn('response_invalid', reasons[0])
        self.assertIn('ai_unsupported', reasons[1])
        self.assertIn('step_name_invalid', reasons[2])
        self.assertIn('python:import_not_allowed', reasons[3])
        with patch.object(cg, '_call_ai') as call, self.assertRaises(AnalysisError) as caught:
            cg.generate(OWNER, plan['id'], plan['revision'], cg.preview(OWNER, plan['id'], plan['revision'])['confirmation'])
        self.assertEqual(caught.exception.status_code, 409)
        call.assert_not_called()  # 5回目は、送信しない
        self.assertEqual(len(plan['codegen']['history']), 4)

    def test_ai_request_failure_is_counted_too(self):
        plan = self.new_plan()
        with patch.object(cg, '_call_ai', side_effect=cg.chat_service.LocalAIError('通信失敗')):
            result = cg.generate(OWNER, plan['id'], plan['revision'], self.confirmation_for(plan))
        self.assertEqual((result['codegen']['status'], result['codegen']['attempts'], result['codegen']['reasons']), ('failed', 1, ['ai_request_failed']))

    def test_no_code_is_stored_when_validation_fails(self):
        plan = self.new_plan()
        result, _ = self.generate(plan, json.dumps({'steps': [], 'python': 'import os\nemit_report("x")'}))
        self.assertNotIn('python', result['codegen'])
        self.assertNotIn('steps', result['codegen'])

    def test_generation_requires_data_approval(self):
        store = AnalysisPlanStore()
        plan = store.create(OWNER, {'provider': 'deepseek', 'model': 'm'}, 30)
        self.keys.append(store._key(plan['id']))
        with self.assertRaises(AnalysisError):
            cg.preview(OWNER, plan['id'], plan['revision'])


class InflightTest(CodegenBase):
    def crash_during_generation(self, plan):
        with patch.object(cg, '_call_ai', side_effect=Crash()), self.assertRaises(Crash):
            cg.generate(OWNER, plan['id'], plan['revision'], self.confirmation_for(plan))
        return self.current(plan)

    def age_inflight(self, plan, seconds):
        key = self.store._key(plan['id'])
        raw = json.loads(self.store.client.get(key))
        raw['codegen']['inflight']['started_at'] = (datetime.now() - timedelta(seconds=seconds)).isoformat()
        self.store.client.set(key, json.dumps(raw, ensure_ascii=False), xx=True, keepttl=True)
        return self.current(plan)

    def test_process_stop_leaves_generating_that_is_shown_as_unknown_without_resend_or_extension(self):
        plan = self.new_plan()
        stuck = self.crash_during_generation(plan)
        self.assertEqual((stuck['codegen']['status'], stuck['codegen']['attempts']), ('generating', 1))
        self.assertEqual(cg.describe_codegen(stuck)['inflight_state'], 'running')
        ttl = self.store.client.pttl(self.store._key(plan['id']))
        with patch.object(cg, '_call_ai') as call, self.assertRaises(AnalysisError) as caught:
            cg.generate(OWNER, stuck['id'], stuck['revision'], cg.preview(OWNER, stuck['id'], stuck['revision'])['confirmation'])
        call.assert_not_called()  # 自動の再送はしない
        self.assertEqual(caught.exception.status_code, 409)
        old = self.age_inflight(stuck, cg.inflight_limit_seconds('deepseek') + 5)
        state = cg.describe_codegen(old)
        self.assertEqual(state['inflight_state'], 'unknown')
        self.assertIn('状態不明', state['inflight_message'])
        self.assertLessEqual(self.store.client.pttl(self.store._key(plan['id'])), ttl)  # 期限を延長しない

    def test_release_is_only_for_unknown_state_and_does_not_refund_attempts_or_extend_ttl(self):
        plan = self.new_plan()
        stuck = self.crash_during_generation(plan)
        with self.assertRaises(AnalysisError):  # まだ「生成中」。解除できない
            cg.release_inflight(OWNER, stuck['id'], stuck['revision'])
        old = self.age_inflight(stuck, cg.inflight_limit_seconds('deepseek') + 5)
        ttl = self.store.client.pttl(self.store._key(plan['id']))
        released = cg.release_inflight(OWNER, old['id'], old['revision'])
        self.assertEqual((released['codegen']['status'], released['codegen']['attempts'], released['codegen']['inflight']), ('failed', 1, None))
        self.assertLessEqual(self.store.client.pttl(self.store._key(plan['id'])), ttl)
        self.assertEqual(released['codegen']['history'][-1]['reasons'], ['inflight_released'])

    def test_late_response_after_release_is_discarded(self):
        plan = self.new_plan()
        confirmation = self.confirmation_for(plan)
        started = threading.Event()
        proceed = threading.Event()
        outcome = {}

        def slow_ai(*args):
            started.set()
            proceed.wait(5)
            return GOOD_RESPONSE

        def worker():
            try:
                cg.generate(OWNER, plan['id'], plan['revision'], confirmation)
            except AnalysisError as exc:
                outcome['error'] = exc

        with patch.object(cg, '_call_ai', slow_ai):
            thread = threading.Thread(target=worker)
            thread.start()
            started.wait(5)
            running = self.current(plan)
            old = self.age_inflight(running, cg.inflight_limit_seconds('deepseek') + 5)
            cg.release_inflight(OWNER, old['id'], old['revision'])  # 利用者が、状態不明として解除した
            proceed.set()
            thread.join(10)
        self.assertEqual(outcome['error'].status_code, 409)
        final = self.current(plan)
        self.assertEqual(final['codegen']['status'], 'failed')  # 遅れて届いた応答は、反映されない
        self.assertNotIn('python', final['codegen'])

    def test_redis_expiry_during_generation_discards_the_result_and_does_not_recreate_the_plan(self):
        plan = self.new_plan()
        confirmation = self.confirmation_for(plan)

        def expire_then_answer(*args):
            self.store.client.delete(self.store._key(plan['id']))
            return GOOD_RESPONSE

        with patch.object(cg, '_call_ai', expire_then_answer), self.assertRaises(AnalysisError) as caught:
            cg.generate(OWNER, plan['id'], plan['revision'], confirmation)
        self.assertEqual(caught.exception.status_code, 410)
        self.assertEqual(self.store.client.exists(self.store._key(plan['id'])), 0)  # 再作成しない

    def test_save_failure_leaves_generating_and_does_not_resend(self):
        plan = self.new_plan()
        confirmation = self.confirmation_for(plan)
        real_update = AnalysisPlanStore.update
        calls = {'n': 0}

        def failing_second_update(self_store, *args, **kwargs):
            calls['n'] += 1
            if calls['n'] >= 2:  # 1回目は「生成中」の保存。結果の保存が失敗する
                raise AnalysisError('保存できませんでした。', 503)
            return real_update(self_store, *args, **kwargs)

        with patch.object(cg, '_call_ai', return_value=GOOD_RESPONSE) as call, \
                patch.object(AnalysisPlanStore, 'update', failing_second_update), self.assertRaises(AnalysisError) as caught:
            cg.generate(OWNER, plan['id'], plan['revision'], confirmation)
        self.assertEqual(caught.exception.status_code, 503)
        call.assert_called_once()
        stuck = self.current(plan)
        self.assertEqual((stuck['codegen']['status'], stuck['codegen']['attempts']), ('generating', 1))
        self.assertEqual(cg.describe_codegen(stuck)['inflight_state'], 'running')  # 後で、状態不明として表示される


class TrialAndApprovalTest(CodegenBase):
    def generated_plan(self):
        plan = self.new_plan()
        result, _ = self.generate(plan)
        return result

    def setUp(self):
        super().setUp()
        self.launcher = FakeLauncher()
        self.addCleanup(self.launcher.close)
        override = override_settings(AI_ANALYSIS_LAUNCHER_URL=self.launcher.url)
        override.enable()
        self.addCleanup(override.disable)

    def trial_report(self, report):
        self.launcher.respond = lambda header: {'status': 'ok', 'result': {'report': json.dumps(report)}, 'cleanup': {'ok': True}}

    def test_trial_sends_no_data_and_a_pass_allows_approval_of_that_exact_code(self):
        plan = self.generated_plan()
        self.trial_report({'trial': 'passed', 'steps': 1})
        updated, trial = cg.run_trial(OWNER, plan['id'], plan['revision'])
        self.assertEqual(trial['status'], 'passed')
        body = self.launcher.bodies[0]
        kinds = []
        offset = 0
        import struct
        while offset + 5 <= len(body):
            kinds.append(body[offset:offset + 1])
            (size,) = struct.unpack('>I', body[offset + 1:offset + 5])
            offset += 5 + size
        self.assertEqual(kinds, [b'H', b'E'])  # データのフレームは、1つも送らない
        header = json.loads(body[5:5 + struct.unpack('>I', body[1:5])[0]])
        self.assertTrue(all(view['expected_rows'] == 0 for view in header['views']))
        self.assertIn('"mode": "trial"', header['code'])
        with self.assertRaises(AnalysisError):  # 確認したコードと違うハッシュでは、承認できない
            cg.approve_code(OWNER, updated['id'], updated['revision'], '0' * 64)
        approved = cg.approve_code(OWNER, updated['id'], updated['revision'], updated['codegen']['executed_code_sha256'])
        self.assertEqual(approved['codegen']['status'], 'code_approved')
        bundle = cg.bundle_from_plan(approved)  # 承認済みのコードから、実行に使うコードを再計算できる
        self.assertEqual(bundle.executed_code_sha256, approved['codegen']['executed_code_sha256'])

    def test_failed_and_unverified_trials_cannot_be_approved(self):
        plan = self.generated_plan()
        self.trial_report({'trial': 'failed', 'step': 'w_daily', 'reason': 'reference_not_allowed', 'message': 'x'})
        updated, trial = cg.run_trial(OWNER, plan['id'], plan['revision'])
        self.assertEqual((trial['status'], trial['reason'], trial['step']), ('failed', 'reference_not_allowed', 'w_daily'))
        with self.assertRaises(AnalysisError) as caught:
            cg.approve_code(OWNER, updated['id'], updated['revision'], updated['codegen']['executed_code_sha256'])
        self.assertEqual(caught.exception.status_code, 409)
        # launcherが使用中: 検証済みとしない
        self.launcher.respond = lambda header: {'status': 'refused', 'reason': 'busy', 'detail': '実行中'}
        updated, trial = cg.run_trial(OWNER, updated['id'], updated['revision'])
        self.assertEqual((trial['status'], trial['reason']), ('unverified', 'busy'))
        with self.assertRaises(AnalysisError):
            cg.approve_code(OWNER, updated['id'], updated['revision'], updated['codegen']['executed_code_sha256'])

    def test_unavailable_launcher_is_unverified_and_no_history_is_written(self):
        plan = self.generated_plan()
        with override_settings(AI_ANALYSIS_LAUNCHER_URL=''):
            updated, trial = cg.run_trial(OWNER, plan['id'], plan['revision'])
        self.assertEqual((trial['status'], trial['reason']), ('unverified', 'launcher_disabled'))
        self.assertFalse(hasattr(cg, 'AIAnalysisRun'))  # 試行は、分析の実行履歴を使わない(Redisの分析案だけ)
        with self.assertRaises(AnalysisError):
            cg.approve_code(OWNER, updated['id'], updated['revision'], updated['codegen']['executed_code_sha256'])

    def test_approval_needs_a_pass_for_the_same_code_hash(self):
        plan = self.generated_plan()
        self.trial_report({'trial': 'passed', 'steps': 1})
        updated, _ = cg.run_trial(OWNER, plan['id'], plan['revision'])
        key = self.store._key(plan['id'])
        raw = json.loads(self.store.client.get(key))
        raw['codegen']['trial']['executed_code_sha256'] = '1' * 64  # 別のコードに対する合格
        self.store.client.set(key, json.dumps(raw, ensure_ascii=False), xx=True, keepttl=True)
        current = self.current(plan)
        with self.assertRaises(AnalysisError):
            cg.approve_code(OWNER, current['id'], current['revision'], current['codegen']['executed_code_sha256'])

    def test_run_requires_approval_and_detects_changed_wrapper_or_code(self):
        plan = self.generated_plan()
        with self.assertRaises(AnalysisError):
            cg.bundle_from_plan(plan)  # 未承認
        approved = {**plan, 'codegen': {**plan['codegen'], 'status': 'code_approved'}}
        cg.bundle_from_plan(approved)
        changed = {**approved, 'codegen': {**approved['codegen'], 'python': approved['codegen']['python'] + '\n'}}
        with self.assertRaises(AnalysisError):
            cg.bundle_from_plan(changed)
        with patch.object(cg, 'WRAPPER_VERSION', 'other-version'), self.assertRaises(AnalysisError):
            cg.bundle_from_plan(approved)  # 外枠の版が変わっていれば、承認時のコードとは別物として扱う


REAL = os.environ.get('AI_ANALYSIS_LAUNCHER_URL_FOR_TEST')


@unittest.skipUnless(REAL, '実launcherの確認は、接続先を指定したときだけ実行する')
class RealContainerGuardTest(CodegenBase):
    """実launcher(Docker)で、固定外枠の検査を、実際のDuckDBで確認する。試行は実DBを使わない。"""

    def setUp(self):
        super().setUp()
        override = override_settings(AI_ANALYSIS_LAUNCHER_URL=REAL)
        override.enable()
        self.addCleanup(override.disable)

    def trial_for(self, steps, python=GOOD_PYTHON):
        plan = self.new_plan()
        key = self.store._key(plan['id'])
        raw = json.loads(self.store.client.get(key))
        bundle = cg.make_bundle(steps, python, VIEWS)
        raw['codegen'] = {'status': 'generated', 'attempts': 1, 'inflight': None, 'steps': steps, 'python': python,
                          'executed_code_sha256': bundle.executed_code_sha256, 'wrapper_version': bundle.wrapper_version, 'trial': None}
        self.store.client.set(key, json.dumps(raw, ensure_ascii=False), xx=True, keepttl=True)
        current = self.current(plan)
        for _ in range(15):  # 前のジョブの後始末が終わるまで、launcherは使用中として断る
            _, trial = cg.run_trial(OWNER, current['id'], current['revision'])
            if trial['reason'] not in ('busy', 'launcher_unreachable'):
                return trial
            time.sleep(2)
            current = self.current(plan)
        return trial

    def test_valid_steps_pass_and_violations_are_rejected_by_the_real_duckdb(self):
        self.assertEqual(self.trial_for(GOOD_STEPS)['status'], 'passed')
        cases = {
            'システムビュー': ('SELECT * FROM information_schema.tables', 'reference_not_allowed'),
            'メタデータ関数': ('SELECT * FROM duckdb_tables()', 'table_function_not_allowed'),
            '外部ファイル関数': ("SELECT * FROM read_csv('x.csv')", 'table_function_not_allowed'),
            'ファイルのリテラル': ("SELECT * FROM 'x.csv'", 'reference_not_allowed'),
            '環境関数': ("SELECT getenv('HOME')", 'function_not_allowed'),
            '複数の文': ('SELECT 1; SELECT 2', 'query_not_single_select'),
            'INSERT': ("INSERT INTO v_ai_shipment VALUES (1, 1, NULL, NULL, NULL, NULL)", 'query_not_single_select'),
            '未承認のテーブル': ('SELECT * FROM other_table', 'reference_not_allowed'),
            '未承認の列': ('SELECT note FROM v_ai_shipment', 'query_failed'),
            'SHOW': ('SELECT * FROM (SHOW TABLES)', 'syntax_not_supported'),
            'DESCRIBE': ('SELECT * FROM (DESCRIBE v_ai_shipment)', 'syntax_not_supported'),
            '括弧なしのシステム名': ('SELECT * FROM duckdb_tables', 'reference_not_allowed'),
            'パラメータ': ('SELECT ? FROM v_ai_shipment', 'syntax_not_supported'),
            'WITHの別の枝の名前': ('SELECT * FROM (WITH x AS (SELECT 1 AS a) SELECT a FROM x) s, x', 'reference_not_allowed'),
            'WITHの名前でシステムテーブルを隠す': ('SELECT (WITH sqlite_master AS (SELECT 1) SELECT 1), * FROM sqlite_master', 'reference_not_allowed'),
            '再帰でないWITHの自己参照': ('WITH sqlite_master AS (SELECT * FROM sqlite_master) SELECT * FROM sqlite_master', 'reference_not_allowed'),
        }
        for label, (query, reason) in cases.items():
            with self.subTest(label):
                trial = self.trial_for([{'name': 'w_x', 'query': query}])
                self.assertEqual((trial['status'], trial['reason']), ('failed', reason), trial)
        # CTE・結合・中間テーブルの参照は許可する
        ok = self.trial_for([
            {'name': 'w_a', 'query': 'WITH x AS (SELECT id, quantity FROM v_ai_shipment) SELECT id, quantity FROM x'},
            {'name': 'w_b', 'query': 'SELECT a.id, r.qty FROM w_a a JOIN v_ai_purchase_receipt r ON a.id = r.id'},
        ])
        self.assertEqual(ok['status'], 'passed', ok)


    def test_common_analytical_sql_is_not_over_rejected(self):
        """許可リスト方式で、よく使う分析用のSQLを誤って拒否しないこと(1回の試行で、まとめて確認する)。"""
        queries = [
            "SELECT shipment_date, sum(quantity) FILTER (WHERE quantity > 0) AS s FROM v_ai_shipment GROUP BY shipment_date HAVING sum(quantity) > 1 ORDER BY 2 DESC LIMIT 10 OFFSET 2",
            "SELECT DISTINCT ON (id) id, CASE WHEN quantity > 1 THEN 'a' ELSE 'b' END c, CAST(quantity AS INTEGER), quantity::DOUBLE FROM v_ai_shipment",
            "SELECT id, row_number() OVER (PARTITION BY shipment_date ORDER BY id ROWS BETWEEN 1 PRECEDING AND CURRENT ROW) FROM v_ai_shipment QUALIFY row_number() OVER () < 5",
            "SELECT * EXCLUDE (customer_code) FROM v_ai_shipment",
            "SELECT COLUMNS('q.*') FROM v_ai_shipment",
            "SELECT a.id, b.qty FROM v_ai_shipment a LEFT JOIN v_ai_purchase_receipt b ON a.id = b.id",
            "SELECT * FROM v_ai_shipment JOIN v_ai_purchase_receipt USING (id)",
            "SELECT * FROM (VALUES (1),(2)) t(x)",
            "SELECT * FROM range(5) t(x)",
            "SELECT id FROM v_ai_shipment WHERE EXISTS (SELECT 1 FROM v_ai_purchase_receipt r WHERE r.id = v_ai_shipment.id) AND id IN (1,2,3) AND customer_code LIKE 'a%' AND quantity BETWEEN 1 AND 2",
            "SELECT date_trunc('month', shipment_date), strftime(shipment_date, '%Y'), coalesce(customer_code,''), nullif(id,0), try_cast(customer_code AS INTEGER) FROM v_ai_shipment",
            "SELECT id FROM v_ai_shipment UNION ALL SELECT id FROM v_ai_purchase_receipt",
            "WITH RECURSIVE t(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM t WHERE n < 5) SELECT * FROM t",
            "WITH a AS (SELECT id FROM v_ai_shipment), b AS (SELECT id FROM a) SELECT * FROM a JOIN b USING (id)",
            "SELECT year(shipment_date) y, sum(quantity) OVER (ORDER BY id) FROM v_ai_shipment",
            "FROM v_ai_shipment SELECT id",
            "SELECT 1 FROM v_ai_shipment GROUP BY ALL",
        ]
        steps = [{'name': f'w_q{i}', 'query': query} for i, query in enumerate(queries)]
        trial = self.trial_for(steps)
        self.assertEqual(trial['status'], 'passed', trial)


class ApiWiringTest(CodegenBase):
    """APIの入口(権限・入力検査・サービスへの接続)。"""

    def call(self, view, plan, body):
        from rest_framework.test import APIRequestFactory, force_authenticate
        request = APIRequestFactory().post('/x/', body, format='json')
        force_authenticate(request, user=SimpleNamespace(pk=OWNER, is_authenticated=True))
        with patch('ai.analysis_permissions._has_resource_permission', return_value=True):
            return view.as_view()(request, plan_id=plan['id'])

    def test_endpoints_validate_input_and_reach_the_services(self):
        from ai import views
        plan = self.new_plan()
        response = self.call(views.AIAnalysisCodegenPreviewView, plan, {'revision': plan['revision']})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['confirmation_required'])
        self.assertEqual(self.call(views.AIAnalysisCodegenPreviewView, plan, {'revision': plan['revision'], 'extra': 1}).status_code, 400)
        self.assertEqual(self.call(views.AIAnalysisCodegenView, plan, {}).status_code, 400)
        with patch.object(cg, '_call_ai', return_value=GOOD_RESPONSE):
            generated = self.call(views.AIAnalysisCodegenView, plan, {'revision': plan['revision'], 'confirmation': response.data['confirmation']})
        self.assertEqual(generated.status_code, 200)
        self.assertEqual(generated.data['codegen']['status'], 'generated')
        self.assertEqual(generated.data['codegen_state']['inflight_state'], None)
        self.assertNotIn('owner_id', generated.data)  # 利用者IDは返さない
        current = generated.data
        self.assertEqual(self.call(views.AIAnalysisCodegenApproveView, current, {'revision': current['revision'], 'executed_code_sha256': 'x'}).status_code, 409)  # 試行前は承認できない
        self.assertEqual(self.call(views.AIAnalysisCodegenReleaseView, current, {'revision': current['revision']}).status_code, 409)

    def test_urls_are_registered(self):
        from django.urls import reverse
        for name in ('preview', 'trial', 'approve', 'release'):
            self.assertTrue(reverse(f'ai-analysis-codegen-{name}', kwargs={'plan_id': '12345678-1234-5678-1234-567812345678'}))
        self.assertTrue(reverse('ai-analysis-codegen', kwargs={'plan_id': '12345678-1234-5678-1234-567812345678'}))


# ---- 変数つきのコード生成(段階2-B。BOSS承認 2026-10-06) ----
PARAM_STEPS = [{'name': 'w_daily', 'query': (
    'SELECT shipment_date, SUM(quantity) AS q FROM v_ai_shipment WHERE customer_code = {{customer_code}} '
    'AND shipment_date BETWEEN {{period_from}} AND {{period_to}} GROUP BY shipment_date')}]
PARAM_PYTHON = GOOD_PYTHON + "\nemit_report('顧客 ' + {{customer_code}} + ' ' + {{period_from}})"
PARAM_DEFS = [
    {'name': 'customer_code', 'type': 'customer_code', 'label': '顧客コード', 'default': 'C-001'},
    {'name': 'period_from', 'type': 'date', 'label': '開始日'},
    {'name': 'period_to', 'type': 'date', 'label': '終了日'},
]


def param_response(steps=PARAM_STEPS, python=PARAM_PYTHON, parameters=PARAM_DEFS):
    body = {'steps': steps, 'python': python}
    if parameters is not None:
        body['parameters'] = parameters
    return json.dumps(body, ensure_ascii=False)


class ParseResponseTest(SimpleTestCase):
    def test_parameters_are_optional_and_the_old_form_is_unchanged(self):
        kind, steps, python, parameters = cg.parse_response_full(param_response())
        self.assertEqual((kind, steps, python, parameters), ('generated', PARAM_STEPS, PARAM_PYTHON, PARAM_DEFS))
        self.assertEqual(cg.parse_response_full(GOOD_RESPONSE), ('generated', GOOD_STEPS, GOOD_PYTHON, None))
        self.assertEqual(cg.parse_response(param_response())[:2], ('generated', PARAM_STEPS))  # 従来の関数は、3つ組のまま
        self.assertEqual(cg.parse_response_full('{"unsupported": "理由"}')[:2], ('unsupported', '理由'))

    def test_a_malformed_parameters_field_is_invalid(self):
        for parameters in ([], {}, 'x', 5, None):
            raw = json.dumps({'steps': GOOD_STEPS, 'python': GOOD_PYTHON, 'parameters': parameters}, ensure_ascii=False)
            self.assertEqual(cg.parse_response_full(raw)[0], 'invalid', parameters)
        extra = json.dumps({'steps': GOOD_STEPS, 'python': GOOD_PYTHON, 'parameters': PARAM_DEFS, 'extra': 1}, ensure_ascii=False)
        self.assertEqual(cg.parse_response_full(extra)[0], 'invalid')

    def test_the_instruction_explains_variables_quotes_and_the_return_format(self):
        for part in ('{{period_from}} と {{period_to}}', '前後に引用符を付けない', '"parameters"', 'product_code、customer_code、ship_to_code',
                     '日付(2026-08-01 など)・コード(V000000000 など)を、直接書かない', '使った変数は、すべて parameters に書き', '辞書・集合の閉じ括弧を連続させない'):
            self.assertIn(part, cg.SYSTEM_PROMPT)


class ParameterGenerationTest(CodegenBase):
    def setUp(self):
        super().setUp()
        from ai.services import analysis_template_params as params
        self.params = params
        patcher = patch.dict(params.TYPES['customer_code'], {'exists': lambda value: value == 'C-001'})
        patcher.start()
        self.addCleanup(patcher.stop)

    def codegen_of(self, response):
        plan = self.new_plan()
        self.generate(plan, response)
        return self.current(plan), self.current(plan)['codegen']

    def test_variables_become_a_concrete_runnable_code_and_the_source_form_is_kept_for_the_template(self):
        plan, state = self.codegen_of(param_response())
        self.assertEqual(state['status'], 'generated')
        query = state['steps'][0]['query']
        self.assertIn("customer_code = 'C-001' AND shipment_date BETWEEN '2026-01-01' AND '2026-01-31'", query)
        self.assertNotIn('{{', json.dumps(state['steps']) + state['python'])
        self.assertIn("emit_report('顧客 ' + 'C-001' + ' ' + '2026-01-01')", state['python'])
        source = state['template_source']
        self.assertEqual((source['steps'], source['python']), (PARAM_STEPS, PARAM_PYTHON))
        self.assertEqual({item['name']: item['default'] for item in source['parameters']},
                         {'customer_code': 'C-001', 'period_from': '2026-01-01', 'period_to': '2026-01-31'})
        bundle = cg.make_bundle(state['steps'], state['python'], VIEWS)
        self.assertEqual((state['executed_code_sha256'], state['sql_sha256']), (bundle.executed_code_sha256, bundle.sql_sha256))

    def test_the_period_values_come_from_the_plan_not_from_the_ai(self):
        defs = [PARAM_DEFS[0], {**PARAM_DEFS[1], 'default': '2020-05-05'}, {**PARAM_DEFS[2], 'default': '2020-06-06'}]
        _, state = self.codegen_of(param_response(parameters=defs))
        defaults = {item['name']: item['default'] for item in state['template_source']['parameters']}
        self.assertEqual((defaults['period_from'], defaults['period_to']), ('2026-01-01', '2026-01-31'))

    def test_a_response_without_parameters_is_unchanged_and_has_no_template_source(self):
        _, state = self.codegen_of(GOOD_RESPONSE)
        self.assertEqual(state['status'], 'generated')
        self.assertNotIn('template_source', state)
        self.assertEqual(state['steps'], GOOD_STEPS)

    def test_each_variable_problem_is_a_fixed_reason_and_a_failed_generation_that_still_counts(self):
        s = lambda query: [{'name': 'w_daily', 'query': query}]
        base = PARAM_STEPS[0]['query']
        cases = {
            'parameters_source_invalid': [
                param_response(steps=s(base.replace('{{customer_code}}', '{{other}}'))),                       # 定義にない変数
                param_response(parameters=PARAM_DEFS + [{'name': 'second', 'type': 'customer_code', 'label': '別の顧客', 'default': 'C-001'}]),  # 使われない定義
                param_response(python=PARAM_PYTHON + "\nx = 'C-001'"),                                         # 元の値が残っている
                param_response(python=PARAM_PYTHON + "\nd = '2026-03-03'"),                                    # 日付の直書き
                param_response(steps=s(base.replace('{{customer_code}}', "'{{customer_code}}'"))),             # 引用符つき
            ],
            'parameters_invalid': [
                param_response(parameters=[{**PARAM_DEFS[0], 'type': 'supplier'}, *PARAM_DEFS[1:]]),          # 種類の不正
                param_response(parameters=[{**PARAM_DEFS[0], 'default': 'C-999'}, *PARAM_DEFS[1:]]),          # 実在しない値
                param_response(parameters=[{'name': 'customer_code', 'type': 'customer_code', 'label': 'x'}, *PARAM_DEFS[1:]]),  # 元の値がない
                param_response(parameters=PARAM_DEFS[:2]),                                                      # 期間が組でない
                param_response(parameters=['x']),                                                               # 項目の形
                param_response(parameters=[{'name': [], 'type': 'date', 'label': 'x'}]),                        # 名前がリスト(例外にならず、理由コードになる)
                param_response(parameters=[{'name': {}, 'type': 'date', 'label': 'x'}]),                        # 名前が辞書
                param_response(parameters=[{'name': 5, 'type': 'date', 'label': 'x'}]),                         # 名前が数値
                param_response(parameters=[{**PARAM_DEFS[0], 'type': ['product_code']}, *PARAM_DEFS[1:]]),     # 種類がリスト
                param_response(parameters=[{**PARAM_DEFS[0], 'default': ['C-001']}, *PARAM_DEFS[1:]]),         # 元の値がリスト
                param_response(parameters=[{**PARAM_DEFS[0], 'label': {}}, *PARAM_DEFS[1:]]),                  # ラベルが辞書
            ],
        }
        for reason, responses in cases.items():
            for response in responses:
                with self.subTest(reason=reason, response=response[:60]):
                    plan = self.new_plan()
                    self.generate(plan, response)
                    state = self.current(plan)['codegen']
                    self.assertEqual(state['status'], 'failed')
                    self.assertEqual(state['attempts'], 1)
                    self.assertNotIn('template_source', state)
                    self.assertEqual(state['reasons'], [reason])

    def test_a_malformed_code_shape_with_parameters_is_a_fixed_reason_and_never_a_stuck_generation(self):
        for steps in ('x', [5], [{'name': 'w_a'}], [{'name': 'w_a', 'query': 5}]):
            with self.subTest(steps=str(steps)):
                plan = self.new_plan()
                self.generate(plan, param_response(steps=steps))
                state = self.current(plan)['codegen']
                self.assertEqual((state['status'], state['inflight'], state['attempts']), ('failed', None, 1))
                self.assertNotIn('template_source', state)

    def test_an_unavailable_value_source_is_a_fixed_reason_not_a_crash_or_a_stuck_generation(self):
        def broken(value):
            raise AnalysisError('顧客コードを確認できません。', 503)

        with patch.dict(self.params.TYPES['customer_code'], {'exists': broken}):
            plan = self.new_plan()
            self.generate(plan, param_response())
        state = self.current(plan)['codegen']
        self.assertEqual((state['status'], state['reasons'], state['inflight']), ('failed', ['parameters_unavailable'], None))

    def test_the_concrete_code_is_still_checked_by_the_usual_rules(self):
        plan = self.new_plan()
        self.generate(plan, param_response(python=PARAM_PYTHON + chr(10) + 'import os'))
        state = self.current(plan)['codegen']
        self.assertEqual(state['status'], 'failed')
        self.assertIn('python:import_not_allowed', state['reasons'])
        self.assertNotIn('template_source', state)

    def test_the_generated_plan_can_be_saved_as_a_template_in_the_variable_form(self):
        from ai.services import analysis_template_service as service
        plan, state = self.codegen_of(param_response())
        stored = self.store.update(plan['id'], OWNER, plan['revision'], lambda current: current['codegen'].update(
            status='code_approved', code_approved_at=datetime.now().isoformat()))
        fields = service._fields_from_plan(stored)
        self.assertEqual((fields['sql_steps'], fields['python_code']), (PARAM_STEPS, PARAM_PYTHON))
        self.assertEqual([item['name'] for item in fields['parameters']], ['customer_code', 'period_from', 'period_to'])
        self.assertEqual(fields['executed_code_sha256'], state['executed_code_sha256'])

    def test_a_plan_without_variables_and_with_a_fixed_date_cannot_be_saved_as_a_template(self):
        from ai.services import analysis_template_service as service
        dated = [{'name': 'w_daily', 'query': "SELECT shipment_date, SUM(quantity) AS q FROM v_ai_shipment WHERE shipment_date >= '2026-01-01' GROUP BY shipment_date"}]
        plan, _ = self.codegen_of(json.dumps({'steps': dated, 'python': GOOD_PYTHON}, ensure_ascii=False))
        stored = self.store.update(plan['id'], OWNER, plan['revision'], lambda current: current['codegen'].update(
            status='code_approved', code_approved_at=datetime.now().isoformat()))
        with self.assertRaises(AnalysisError) as caught:
            service._fields_from_plan(stored)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertIn('固定の日付', str(caught.exception.detail))
        # 日付のないコードは、従来どおり保存できる
        plain, _ = self.codegen_of(GOOD_RESPONSE)
        stored = self.store.update(plain['id'], OWNER, plain['revision'], lambda current: current['codegen'].update(
            status='code_approved', code_approved_at=datetime.now().isoformat()))
        self.assertEqual(service._fields_from_plan(stored)['parameters'], [])
