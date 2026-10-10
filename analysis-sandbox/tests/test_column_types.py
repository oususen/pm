"""job_mainの列型の検査(DECIMAL(p,s)の一般化)を検証する。Docker・DuckDBは使わない(検査関数だけを呼ぶ)。

実行: python -m unittest discover -s analysis-sandbox/tests -p "test_column_types.py" -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'job'))
import job_main as J  # noqa: E402


def header_with(column_type):
    return {
        'code': 'pass', 'limits': {'python_seconds': 5, 'duckdb_memory_limit_mb': 64, 'threads': 1},
        'views': [{'name': 'v', 'expected_rows': 0, 'columns': [{'name': 'c', 'type': column_type}]}],
    }


class ColumnTypeTest(unittest.TestCase):
    def test_existing_and_decimal_range_are_allowed(self):
        # A4: 既存の型と、DECIMAL(p,s)の範囲内(p 1〜38、s 0〜p)は許可する
        for ok in ['BIGINT', 'INTEGER', 'DOUBLE', 'VARCHAR', 'DATE', 'TIMESTAMP', 'BOOLEAN', 'DECIMAL(18,3)',
                   'DECIMAL(18,5)', 'DECIMAL(18,4)', 'DECIMAL(18,2)', 'DECIMAL(1,0)', 'DECIMAL(38,38)', 'DECIMAL(38,0)']:
            J.validate_header(header_with(ok))
            self.assertTrue(J.is_allowed_column_type(ok), ok)

    def test_out_of_range_and_malformed_are_refused_as_header_invalid(self):
        for bad in ['DECIMAL(39,2)', 'DECIMAL(18,19)', 'DECIMAL(0,0)', 'DECIMAL(100,2)', 'DECIMAL(18,2); DROP',
                    "DECIMAL(18,2)'); DROP TABLE x; --", 'decimal(18,3)', 'DECIMAL( 18,3)', 'DECIMAL(18, 3)',
                    'DECIMAL(18,3)\n', ' DECIMAL(18,3)', 'DECIMAL(18)', 'DECIMAL', 'DECIMAL(-1,0)', 'DECIMAL(１８,３)',
                    'bigint', 'BIGINT ', 'HUGEINT', '', None, 5, ['BIGINT']]:
            self.assertFalse(J.is_allowed_column_type(bad), repr(bad))
            with self.assertRaises(J.JobFailed, msg=repr(bad)) as caught:
                J.validate_header(header_with(bad))
            self.assertEqual(caught.exception.reason, 'header_invalid')


    def test_leading_zero_in_decimal_is_refused(self):
        # 先頭ゼロの数字は拒否(0単独、または先頭が1〜9の1〜2桁だけ許可)
        for ok in ['DECIMAL(18,3)', 'DECIMAL(10,0)', 'DECIMAL(5,0)', 'DECIMAL(38,2)', 'DECIMAL(3,3)']:
            self.assertTrue(J.is_allowed_column_type(ok), ok)
            J.validate_header(header_with(ok))
        for bad in ['DECIMAL(18,03)', 'DECIMAL(01,00)', 'DECIMAL(018,03)', 'DECIMAL(00,0)', 'DECIMAL(5,00)']:
            self.assertFalse(J.is_allowed_column_type(bad), bad)
            with self.assertRaises(J.JobFailed, msg=bad) as caught:
                J.validate_header(header_with(bad))
            self.assertEqual(caught.exception.reason, 'header_invalid')


if __name__ == '__main__':
    unittest.main()
