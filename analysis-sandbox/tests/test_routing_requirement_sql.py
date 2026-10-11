"""親品と加工後品の照合例を実DuckDB・固定外枠で検証する。実AI生成の品質検証ではない。"""
import json
import unittest
from pathlib import Path

import test_isolation as helpers


VIEW = 'v_ai_routing_step'
COLUMNS = [
    {'name': 'id', 'type': 'BIGINT'}, {'name': 'routing_id', 'type': 'BIGINT'},
    {'name': 'output_product_code', 'type': 'VARCHAR'}, {'name': 'parent_product_code', 'type': 'VARCHAR'},
]
# NULL・空文字・同ルーティング内の複数一致・他ルーティングだけの一致・自己一致・単一一致。
ROWS = [
    [1, 1, 'A', None], [2, 1, 'B', ''], [3, 1, 'C', 'A'], [4, 1, 'D', 'Z'],
    [5, 1, 'SELF', 'SELF'], [6, 1, 'A', None], [7, 1, 'E', 'B'], [8, 2, 'Z', None],
    [9, 1, None, ''], [10, 1, '', None],
]
QUERY = """
WITH w_steps AS (
    SELECT id AS engineering_id, routing_id, output_product_code, parent_product_code
    FROM v_ai_routing_step
)
SELECT s1.engineering_id AS original_id, s1.routing_id, s1.output_product_code,
       s1.parent_product_code, s2.engineering_id AS matching_id,
       CASE WHEN s1.parent_product_code IS NULL OR s1.parent_product_code = '' THEN '親品空欄'
            WHEN s2.engineering_id IS NULL THEN '一致工程なし' ELSE '一致あり' END AS match_status
FROM w_steps s1 LEFT JOIN w_steps s2
  ON s1.routing_id = s2.routing_id
 AND s1.parent_product_code = s2.output_product_code
 AND s1.parent_product_code IS NOT NULL AND s1.parent_product_code <> ''
 AND s1.engineering_id <> s2.engineering_id
"""
PYTHON = "rows = con.sql('SELECT original_id, routing_id, output_product_code, parent_product_code, matching_id, match_status FROM w_matches ORDER BY original_id, matching_id').fetchall()\nemit_table('照合', ['工程ID', 'ルーティングID', '加工後品', '親品', '一致工程ID', '判定'], [list(row) for row in rows])"


class RoutingRequirementSQLTest(unittest.TestCase):
    def tearDown(self):
        self.assertEqual(helpers.leftover_containers(), [])

    def run_guard(self, query, mode, rows):
        guard = (Path(__file__).resolve().parents[2] / 'pm_backend/apps/ai/services/analysis_guard_runtime.py').read_text(encoding='utf-8')
        config = json.dumps({'mode': mode, 'approved': [VIEW], 'steps': [{'name': 'w_matches', 'query': query}]})
        code = f'_CONFIG_JSON = {config!r}\n_PYTHON_SOURCE = {PYTHON!r}\n' + guard
        views = [{'name': VIEW, 'columns': COLUMNS, 'expected_rows': len(rows), 'unique_key': 'id'}]
        return helpers.run(code, views=views, chunks=[(0, rows)] if rows else [])

    def test_renamed_source_column_fails_and_projected_name_passes_trial(self):
        wrong = QUERY.replace('s1.engineering_id <> s2.engineering_id', 's1.id <> s2.id')
        result = self.run_guard(wrong, 'trial', [])
        self.assertEqual(result['status'], 'ok', result)  # 試行のSQL失敗は固定外枠が報告として返す。
        report = json.loads(result['result']['report'])
        self.assertEqual((report['trial'], report['reason'], report['step']), ('failed', 'query_failed', 'w_matches'))
        self.assertTrue(result['cleanup']['ok'])
        result = self.run_guard(QUERY, 'trial', [])
        self.assertEqual(result['status'], 'ok', result)
        self.assertEqual(json.loads(result['result']['report'])['trial'], 'passed')
        self.assertTrue(result['cleanup']['ok'])

    def test_match_direction_missing_states_multiple_matches_and_all_source_rows(self):
        result = self.run_guard(QUERY, 'run', ROWS)
        self.assertEqual(result['status'], 'ok', result)
        table = result['result']['tables'][0]
        self.assertEqual(table['columns'], ['工程ID', 'ルーティングID', '加工後品', '親品', '一致工程ID', '判定'])
        self.assertEqual(table['rows'], [
            [1, 1, 'A', None, None, '親品空欄'], [2, 1, 'B', '', None, '親品空欄'],
            [3, 1, 'C', 'A', 1, '一致あり'], [3, 1, 'C', 'A', 6, '一致あり'],
            [4, 1, 'D', 'Z', None, '一致工程なし'], [5, 1, 'SELF', 'SELF', None, '一致工程なし'],
            [6, 1, 'A', None, None, '親品空欄'], [7, 1, 'E', 'B', 2, '一致あり'],
            [8, 2, 'Z', None, None, '親品空欄'], [9, 1, None, '', None, '親品空欄'],
            [10, 1, '', None, None, '親品空欄'],
        ])
        self.assertEqual({row[0] for row in table['rows']}, {row[0] for row in ROWS})
        self.assertTrue(result['cleanup']['ok'])
