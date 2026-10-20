"""取得列数とPythonの展開個数を、空DuckDB・実隔離コンテナで照合する。"""
import json
import unittest
from pathlib import Path

import test_isolation as helpers


FULL_SOURCE = '''summary = con.sql("SELECT process_code, process_name, stddev_daily FROM w_process_summary").fetchall()
emit_table('集計', ['工程コード', '工程名', '標準偏差'], summary)
emit_table('変動', ['工程コード', '工程名', '標準偏差'], summary)
top5 = con.sql("SELECT process_code, process_name FROM w_process_summary WHERE stddev_daily IS NOT NULL ORDER BY stddev_daily DESC LIMIT 5").fetchall()
top5_codes = [r[0] for r in top5]
days = sorted({str(r[0]) for r in con.sql("SELECT business_day FROM w_process_daily").fetchall()})
rows = con.sql("SELECT process_code, process_name, business_day, qty FROM w_process_daily ORDER BY business_day").fetchall()
amounts = {}
for code, name, day, qty in rows:
    if code in top5_codes:
        amounts[(code, str(day))] = float(qty)
series = [{'name': code + ' ' + (name or ''), 'values': [amounts.get((code, d), 0.0) for d in days]} for code, name, _ in top5]
emit_chart('line', '推移', days, series)
'''


class PythonUnpackTrial(unittest.TestCase):
    def tearDown(self):
        self.assertEqual(helpers.leftover_containers(), [])

    def trial(self, source):
        guard = (Path(__file__).resolve().parents[2] / 'pm_backend/apps/ai/services/analysis_guard_runtime.py').read_text(encoding='utf-8')
        steps = [
            {'name': 'w_process_summary', 'query': "SELECT ''::VARCHAR AS process_code, ''::VARCHAR AS process_name, 0.0 AS stddev_daily WHERE FALSE"},
            {'name': 'w_process_daily', 'query': "SELECT ''::VARCHAR AS process_code, ''::VARCHAR AS process_name, DATE '2026-09-01' AS business_day, 0.0 AS qty WHERE FALSE"},
        ]
        config = json.dumps({'mode': 'trial', 'approved': [], 'steps': steps})
        code = f'_CONFIG_JSON = {config!r}\n_PYTHON_SOURCE = {source!r}\n' + guard
        result = helpers.run(code)
        self.assertEqual(result['status'], 'ok', result)
        self.assertTrue(result['cleanup']['ok'])
        return json.loads(result['result']['report'])

    def test_actual_failure_flow_is_detected_before_python_execution(self):
        report = self.trial(FULL_SOURCE)
        self.assertEqual(report['trial'], 'failed')
        self.assertEqual(report['reason'], 'python_unpack_mismatch')
        self.assertIsNone(report['step'])
        self.assertNotIn('SELECT', report['message'])

    def test_corrected_two_variables_pass_without_executing_python(self):
        report = self.trial(FULL_SOURCE.replace('for code, name, _ in top5', 'for code, name in top5') + '\nraise ValueError("実行禁止")')
        self.assertEqual(report['trial'], 'passed')

    def test_bound_width_uses_star_cte_alias_and_commas_in_values(self):
        for sql in (
            'SELECT * FROM w_process_summary',
            "WITH c AS (SELECT process_code AS code, concat(process_name, ',x') AS name, coalesce(stddev_daily, 0) AS qty FROM w_process_summary) SELECT * FROM c",
        ):
            with self.subTest(sql=sql):
                report = self.trial(f'rows = con.sql({sql!r}).fetchall()\nalias = rows\nresult = [a for a, b in alias]\nemit_report("x")')
                self.assertEqual(report['reason'], 'python_unpack_mismatch')

    def test_for_set_and_dict_comprehension_are_checked(self):
        for loop in ('for a, b, c in rows:\n    pass', 'result = {a for a, b, c in rows}', 'result = {a: b for a, b, c in rows}'):
            with self.subTest(loop=loop):
                report = self.trial('rows = con.execute("SELECT process_code, process_name FROM w_process_summary").fetchall()\n' + loop + '\nemit_report("x")')
                self.assertEqual(report['reason'], 'python_unpack_mismatch')

    def test_unknown_or_changed_values_do_not_create_new_rejections(self):
        prefix = 'rows = con.sql("SELECT process_code, process_name FROM w_process_summary").fetchall()\n'
        for change in (
            'rows = [(1, 2, 3)]', 'alias = rows\nalias.append((1, 2, 3))',
            'if True:\n    rows = [(1, 2, 3)]', 'rows[0:0] = [(1, 2, 3)]',
            'def alter():\n    rows.append((1, 2, 3))\nalter()',
        ):
            with self.subTest(change=change):
                self.assertEqual(self.trial(prefix + change + '\nresult = [a for a, b, c in rows]\nemit_report("x")')['trial'], 'passed')
        for source in (
            'query = "SELECT 1, 2"\nrows = con.sql(query).fetchall()\nx = [a for a,b,c in rows]',
            'rows = con.sql("SELECT 1,2").fetchall()\nx = [a for a,*b in rows]',
            'def f():\n    rows = con.sql("SELECT 1,2").fetchall()\n    return [a for a,b,c in rows]',
            'rows = con.sql("SELECT 1,2").fetchall()\nx = (a for a,b,c in rows)',
            'rows = con.sql("SELECT 1,2").fetchall()\nx = False and [a for a,b,c in rows]',
        ):
            with self.subTest(source=source):
                self.assertEqual(self.trial(source + '\nemit_report("x")')['trial'], 'passed')

    def test_shadowed_connection_builtin_and_deleted_values_are_unknown(self):
        prefix = 'top5 = con.sql("SELECT process_code, process_name FROM w_process_summary").fetchall()\n'
        cases = (
            'connections = []\nout = [[x for a,b,x in con.sql("SELECT 1,2").fetchall()] for con in connections]',
            prefix + 'funcs = []\nout = [sorted(top5) for sorted in funcs]\nfor a,b,c in top5:\n    pass',
            prefix + 'del top5\nfor a,b,c in top5:\n    pass',
            prefix + 'del top5[:]\nfor a,b,c in top5:\n    pass',
        )
        for source in cases:
            with self.subTest(source=source):
                self.assertEqual(self.trial(source + '\nemit_report("x")')['trial'], 'passed')


if __name__ == '__main__':
    unittest.main()
