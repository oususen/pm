"""新しい外枠の出力検査を実コンテナで確認。Windowsでは実行しない。"""
import json
import unittest
from pathlib import Path

import test_isolation as helpers


class GuardOutputs(unittest.TestCase):
    def tearDown(self):
        self.assertEqual(helpers.leftover_containers(), [])

    def run_source(self, source, mode='run'):
        guard = (Path(__file__).resolve().parents[2] / 'pm_backend/apps/ai/services/analysis_guard_runtime.py').read_text(encoding='utf-8')
        config = json.dumps({'mode':mode, 'approved':[], 'steps':[]})
        code = f'_CONFIG_JSON = {config!r}\n_PYTHON_SOURCE = {source!r}\n' + guard
        return helpers.run(code)

    def test_valid_outputs_still_pass(self):
        result = self.run_source('x=["8月","9月"]\nemit_chart("bar","月別",x,[{"name":"数量","values":[1,None]}])\nemit_table("集計",["月","数量"],[["8月",1]])')
        self.assertEqual(result['status'], 'ok', result)
        self.assertEqual(result['result']['charts'][0]['x'], ['8月','9月'])
        self.assertEqual(result['result']['tables'][0]['rows'], [['8月',1]])

    def test_dynamic_invalid_outputs_fail_early_and_discard_everything(self):
        for source in (
            'x="月"\nemit_chart("bar","t",x,[{"name":"s","values":[1,2]}])',
            'x=["8","9"]\nemit_chart("bar","t",x,[{"name":"s","values":[1]}])',
            'cols="列"\nemit_table("t",cols,[[1]])',
            'rows="行"\nemit_table("t",["列"],rows)',
        ):
            result = self.run_source('emit_report("途中結果")\n' + source)
            self.assertEqual(result['status'], 'failed', result)
            self.assertEqual(result['reason'], 'child_exit_nonzero')
            self.assertNotIn('result', result)
            self.assertTrue(result['cleanup']['ok'])

    def test_trial_does_not_run_python_on_empty_data(self):
        result = self.run_source('x="月"\nemit_chart("bar","t",x,[])', 'trial')
        self.assertEqual(result['status'], 'ok', result)
        self.assertEqual(json.loads(result['result']['report'])['trial'], 'passed')

    def test_duckdb_fetchall_tuple_rows_can_be_passed_directly(self):
        result = self.run_source("rows=con.sql('SELECT 1 AS id, 2 AS q UNION ALL SELECT 3, NULL').fetchall()\nemit_table('t', ['id','q'], rows)")
        self.assertEqual(result['status'], 'ok', result)
        self.assertEqual(result['result']['tables'][0]['rows'], [[1, 2], [3, None]])
        self.assertTrue(result['cleanup']['ok'])

    def test_tuple_columns_rows_x_and_values_are_adopted_as_lists(self):
        result = self.run_source("emit_table('t', ('id','q'), ((1,2), [3,None]))\nemit_chart('bar','t',('a','b'),({'name':'s','values':(1,None)},))")
        self.assertEqual(result['status'], 'ok', result)
        self.assertEqual(result['result']['tables'][0]['columns'], ['id', 'q'])
        self.assertEqual(result['result']['tables'][0]['rows'], [[1, 2], [3, None]])
        self.assertEqual(result['result']['charts'][0]['x'], ['a', 'b'])
        self.assertEqual(result['result']['charts'][0]['series'][0]['values'], [1, None])
        self.assertTrue(result['cleanup']['ok'])

    def test_dictionary_scalar_and_tuple_length_mismatch_discard_results(self):
        for source in (
            "x={'a':1}\nemit_chart('bar','t',x,[])",
            "x=123\nemit_chart('bar','t',x,[])",
            "emit_chart('bar','t',('a','b'),[{'name':'s','values':(1,)}])",
            "rows={'id':1}\nemit_table('t',['id'],rows)",
            "emit_table('t',('id','q'),((1,),))",
        ):
            with self.subTest(source=source):
                result = self.run_source('emit_report("途中結果")\n' + source)
                self.assertEqual(result['status'], 'failed', result)
                self.assertEqual(result['reason'], 'child_exit_nonzero')
                self.assertNotIn('result', result)
                self.assertTrue(result['cleanup']['ok'])
