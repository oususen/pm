"""日付列を持たないビュー(date_field=None)の全行取得(サイクルB)を検証する。

偽のDB接続・カーソルと模擬launcherだけを使い、開発DBへは接続しない(SimpleTestCaseのみ)。
試験側で ANALYSIS_VIEWS / ANALYSIS_COLUMN_TYPES / BASE_SQL_SCHEMA を patch して、date_field=None の試験用ビューを使う。
"""
import re
import struct
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ai.services import analysis_data_service as data_service
from ai.services import analysis_execution_service as service
from ai.services.analysis_data_service import ANALYSIS_VIEWS, build_where, count_target_rows, validate_datasets
from ai.services.analysis_plan_store import AnalysisError
from ai.services.sql_queries import BASE_SQL_SCHEMA
from ai.test_analysis_execution import ExecutionBase, split_frames

MASTER = 'v_ai_testmaster'  # 試験用の日付なしビュー
DATED = 'v_ai_shipment'     # 既存の日付ありビュー
MASTER_ROWS = [(i, f'C{i:03d}', f'名称{i}') for i in range(1, 13)]  # id, code, name (12行)
SHIPMENT_ROWS = [(100 + i, date(2026, 8, 25) + timedelta(days=i), Decimal('1.000')) for i in range(0, 20)]  # 8/25〜9/13
PERIOD = ('2026-09-01', '2026-09-10')
CHUNK = 5
POLICY = SimpleNamespace(max_memory_mb=512, max_cpu_cores=Decimal('1.0'), max_execution_seconds=60, max_fetch_rows=100_000)
MASTER_DATASET = {'view': MASTER, 'fields': ['id', 'code', 'name']}
DATED_DATASET = {'view': DATED, 'fields': ['id', 'shipment_date', 'quantity']}


def dated_in_period():
    return [row for row in SHIPMENT_ROWS if PERIOD[0] <= row[1].isoformat() <= PERIOD[1]]


COLUMNS = {MASTER: ('id', 'code', 'name'), DATED: ('id', 'shipment_date', 'quantity')}


class FakeCursor:
    """固定形のSQLだけを解釈する偽のカーソル。実行したSQLとパラメータを記録する。"""

    def __init__(self, tables):
        self.tables, self.log, self.result = tables, [], []

    def execute(self, sql, params=None):
        params = list(params or [])
        if sql.startswith('SET SESSION'):
            return
        self.log.append((sql, list(params)))
        view = re.search(r'FROM `(\w+)`', sql).group(1)
        rows = list(self.tables[view])
        if re.search(r'WHERE `\w+` >= %s AND `\w+` <= %s', sql):
            start, end = params.pop(0), params.pop(0)
            rows = [r for r in rows if start <= r[1].isoformat() <= end]  # 日付ありの試験用ビューは、2列目が日付
        if '`id` > %s' in sql:
            last = params.pop(0)
            rows = [r for r in rows if r[0] > last]
        if sql.startswith('SELECT COUNT(*)'):
            self.result = [(len(rows),)]
            return
        rows.sort(key=lambda r: r[0])
        names = re.findall(r'`(\w+)`', sql.split(' FROM ')[0])  # SELECT句の列(先頭は管理列idで、取得列にもidがあれば重複する)
        positions = [COLUMNS[view].index(name) for name in names]
        self.result = [tuple(r[i] for i in positions) for r in rows[:params.pop(0)]]

    def fetchall(self):
        return self.result


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def rollback(self):
        pass

    def close(self):
        pass


class PatchedViewsMixin:
    """試験用の日付なしビューを、試験の間だけ登録する(本番の定義は変えない)。"""

    def patch_views(self):
        for target, key, value in [
            (ANALYSIS_VIEWS, MASTER, {'label': '試験用マスタ', 'date_field': None, 'quantity_field': None, 'description': '試験用'}),
            (service.ANALYSIS_COLUMN_TYPES, MASTER, {'id': 'BIGINT', 'code': 'VARCHAR', 'name': 'VARCHAR'}),
            (BASE_SQL_SCHEMA, MASTER, ('id', 'code', 'name')),
        ]:
            patcher = patch.dict(target, {key: value})
            patcher.start()
            self.addCleanup(patcher.stop)


class BuildWhereAndSqlTest(PatchedViewsMixin, SimpleTestCase):
    def setUp(self):
        self.patch_views()

    def test_b1_dated_view_sql_and_params_are_unchanged(self):
        # 変更前(HEAD)のコードが組み立てていた文字列とパラメータを、固定して比較する
        cursor = FakeCursor({DATED: SHIPMENT_ROWS})
        service._count(cursor, service.Deadline(5, 'x'), DATED, *PERIOD)
        self.assertEqual(cursor.log[-1], (
            'SELECT COUNT(*) FROM `v_ai_shipment` WHERE `shipment_date` >= %s AND `shipment_date` <= %s', list(PERIOD)))
        pages = list(service._pages(cursor, service.Deadline(5, 'x'), DATED, ['shipment_date', 'quantity'], *PERIOD, 3))
        self.assertEqual(sum(len(p) for p in pages), len(dated_in_period()))
        select_log = cursor.log[1:]
        head = 'SELECT `id`, `shipment_date`, `quantity` FROM `v_ai_shipment` WHERE `shipment_date` >= %s AND `shipment_date` <= %s'
        self.assertEqual(select_log[0], (f'{head} ORDER BY `id` LIMIT %s', [*PERIOD, 3]))
        last_id = dated_in_period()[2][0]
        self.assertEqual(select_log[1], (f'{head} AND `id` > %s ORDER BY `id` LIMIT %s', [*PERIOD, last_id, 3]))
        # 承認画面のCOUNT
        mock_cursor = MagicMock()
        mock_cursor.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (7,)
        connection = MagicMock()
        connection.cursor.return_value = mock_cursor
        with patch.object(data_service, 'settings', SimpleNamespace(DATABASES={'ai_reader': {'USER': 'pm_ai_reader'}})), patch.object(
                data_service, 'connections', {'ai_reader': connection}):
            count_target_rows({'datasets': [DATED_DATASET], 'date_from': PERIOD[0], 'date_to': PERIOD[1]})
        mock_cursor.execute.assert_called_once_with(
            'SELECT COUNT(*) FROM `v_ai_shipment` WHERE `shipment_date` >= %s AND `shipment_date` <= %s', list(PERIOD))

    def test_b2_dateless_view_has_no_period_where_or_params(self):
        cursor = FakeCursor({MASTER: MASTER_ROWS})
        service._count(cursor, service.Deadline(5, 'x'), MASTER, *PERIOD)
        self.assertEqual(cursor.log[-1], ('SELECT COUNT(*) FROM `v_ai_testmaster`', []))
        pages = list(service._pages(cursor, service.Deadline(5, 'x'), MASTER, ['code', 'name'], *PERIOD, CHUNK))
        self.assertEqual([len(p) for p in pages], [5, 5, 2])  # 期間で絞らず全12行
        select_log = cursor.log[1:]
        head = 'SELECT `id`, `code`, `name` FROM `v_ai_testmaster`'
        self.assertEqual(select_log[0], (f'{head} ORDER BY `id` LIMIT %s', [CHUNK]))
        self.assertEqual(select_log[1], (f'{head} WHERE `id` > %s ORDER BY `id` LIMIT %s', [5, CHUNK]))  # ANDで始めない
        self.assertEqual(select_log[2], (f'{head} WHERE `id` > %s ORDER BY `id` LIMIT %s', [10, CHUNK]))
        for sql, params in cursor.log:
            self.assertNotIn(PERIOD[0], params)
            self.assertNotIn('AND', sql)
            self.assertNotIn(' >= ', sql)
        self.assertEqual(build_where(MASTER, *PERIOD), ('', []))
        # 承認画面のCOUNT
        mock_cursor = MagicMock()
        mock_cursor.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (12,)
        connection = MagicMock()
        connection.cursor.return_value = mock_cursor
        with patch.object(data_service, 'settings', SimpleNamespace(DATABASES={'ai_reader': {'USER': 'pm_ai_reader'}})), patch.object(
                data_service, 'connections', {'ai_reader': connection}):
            preview = count_target_rows({'datasets': [MASTER_DATASET], 'date_from': PERIOD[0], 'date_to': PERIOD[1]})
        mock_cursor.execute.assert_called_once_with('SELECT COUNT(*) FROM `v_ai_testmaster`', [])
        self.assertEqual(preview['total_rows'], 12)

    def test_b3_validate_datasets_date_field_rule(self):
        # 日付なし: 日付列がなくても通る
        self.assertEqual(validate_datasets([{'view': MASTER, 'fields': ['code']}], *PERIOD), [{'view': MASTER, 'fields': ['code']}])
        # 日付あり: 日付列がなければ従来どおり拒否
        with self.assertRaises(AnalysisError) as caught:
            validate_datasets([{'view': DATED, 'fields': ['quantity']}], *PERIOD)
        self.assertEqual(str(caught.exception.args[0] if caught.exception.args else caught.exception), '対象期間の根拠となる日付フィールドが必要です。')
        validate_datasets([{'view': DATED, 'fields': ['shipment_date']}], *PERIOD)

    def test_b7_missing_date_field_key_stops_with_key_error(self):
        patcher = patch.dict(ANALYSIS_VIEWS, {MASTER: {'label': '宣言なし', 'quantity_field': None, 'description': '試験用'}})
        patcher.start()
        self.addCleanup(patcher.stop)
        with self.assertRaises(KeyError):
            validate_datasets([{'view': MASTER, 'fields': ['code']}], *PERIOD)
        with self.assertRaises(KeyError):
            build_where(MASTER, *PERIOD)
        with self.assertRaises(KeyError):
            service._count(FakeCursor({MASTER: MASTER_ROWS}), service.Deadline(5, 'x'), MASTER, *PERIOD)
        with self.assertRaises(KeyError):
            list(service._pages(FakeCursor({MASTER: MASTER_ROWS}), service.Deadline(5, 'x'), MASTER, ['code'], *PERIOD, CHUNK))

    def test_b8_no_forbidden_time_apis_in_changed_files(self):
        forbidden = ['timezone' + '.now', 'timezone' + '.localtime', 'toISO' + 'String']
        base = Path(__file__).parent / 'services'
        for name in ['analysis_data_service.py', 'analysis_execution_service.py']:
            text = (base / name).read_text(encoding='utf-8')
            for word in forbidden:
                self.assertNotIn(word, text, f'{name}: {word}')


class RunWithFakeDatabaseTest(PatchedViewsMixin, ExecutionBase):
    """実行時の件数照合を、偽のDB接続と模擬launcherで確認する。"""

    def setUp(self):
        super().setUp()
        self.patch_views()
        self.cursor = FakeCursor({MASTER: MASTER_ROWS, DATED: SHIPMENT_ROWS})
        patcher = patch.object(service, 'open_snapshot_connection', lambda *a, **k: FakeConnection(self.cursor))
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_proposal(self, datasets, counts, policy=POLICY):
        proposal = {'datasets': datasets, 'date_from': PERIOD[0], 'date_to': PERIOD[1]}
        return service.execute_approved_analysis(proposal, counts, "emit_report('x')", policy, chunk_rows=CHUNK)

    def sent_rows(self):
        body = self.launcher.bodies[0]
        header = None
        sent = {}
        for kind, payload in split_frames(body):
            if kind == b'H':
                header = json.loads(payload)
            elif kind == b'D':
                index, rows = struct.unpack('>HI', payload[:6])
                name = header['views'][index]['name']
                sent[name] = sent.get(name, 0) + rows
        return sent

    def test_b4_dateless_counts_match_count_pages_and_approved_count(self):
        counts = {MASTER: len(MASTER_ROWS)}
        # _count と承認時COUNT(count_target_rows)が一致する
        self.assertEqual(service._count(self.cursor, service.Deadline(5, 'x'), MASTER, *PERIOD), counts[MASTER])
        result = self.run_proposal([MASTER_DATASET], counts)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['fetch']['counts'], counts)
        self.assertEqual(result['fetch']['sent_rows'], counts)
        self.assertEqual(self.sent_rows(), counts)  # 全ページの合計=COUNT=全12行
        self.assertEqual(result['fetch']['chunks'], 3)
        for sql, params in self.cursor.log:
            self.assertNotIn(PERIOD[0], params)

    def test_b5_dateless_count_changed_stops_before_sending(self):
        with self.assertRaises(service.ExecutionStopped) as caught:
            self.run_proposal([MASTER_DATASET], {MASTER: len(MASTER_ROWS) + 1})
        self.assertEqual(caught.exception.reason, 'approved_count_changed')
        self.assertEqual(self.launcher.bodies, [])

    def test_b5_dateless_fetch_rows_exceeded(self):
        policy = SimpleNamespace(**{**POLICY.__dict__, 'max_fetch_rows': len(MASTER_ROWS) - 1})
        with self.assertRaises(service.ExecutionStopped) as caught:
            self.run_proposal([MASTER_DATASET], {MASTER: len(MASTER_ROWS)}, policy)
        self.assertEqual(caught.exception.reason, 'fetch_rows_exceeded')
        self.assertEqual(self.launcher.bodies, [])

    def test_b5_dateless_refetch_mismatch(self):
        real = service._data_frame
        state = {'calls': 0}

        def altered(index, rows, types):
            state['calls'] += 1
            if state['calls'] == 3 + 2:  # 1回目は3チャンク。2回目の2番目のチャンクで1行を変える
                changed = list(rows[0])
                changed[0] += 1_000_000
                rows = [tuple(changed)] + list(rows[1:])
            return real(index, rows, types)

        with patch.object(service, '_data_frame', altered), self.assertRaises(service.ExecutionStopped) as caught:
            self.run_proposal([MASTER_DATASET], {MASTER: len(MASTER_ROWS)})
        self.assertEqual(caught.exception.reason, 'refetch_mismatch')

    def test_b6_mixed_views_period_applies_only_to_dated_and_total_is_compared(self):
        dated_count = len(dated_in_period())
        self.assertNotEqual(dated_count, len(SHIPMENT_ROWS))  # 期間で絞られる試験データであること
        counts = {MASTER: len(MASTER_ROWS), DATED: dated_count}
        result = self.run_proposal([MASTER_DATASET, DATED_DATASET], counts)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(self.sent_rows(), counts)
        for sql, params in self.cursor.log:
            if '`v_ai_testmaster`' in sql:
                self.assertNotIn(PERIOD[0], params)
            else:
                self.assertEqual(params[:2], list(PERIOD))
        # 合計(12 + 期間内の出荷)が max_fetch_rows と比較される
        policy = SimpleNamespace(**{**POLICY.__dict__, 'max_fetch_rows': sum(counts.values()) - 1})
        self.launcher.bodies.clear()
        with self.assertRaises(service.ExecutionStopped) as caught:
            self.run_proposal([MASTER_DATASET, DATED_DATASET], counts, policy)
        self.assertEqual(caught.exception.reason, 'fetch_rows_exceeded')
        self.assertEqual(self.launcher.bodies, [])
        # 日付ありビューの承認時件数が違えば、日付なしが一致していても止まる
        with self.assertRaises(service.ExecutionStopped) as caught:
            self.run_proposal([MASTER_DATASET, DATED_DATASET], {**counts, DATED: dated_count + 1})
        self.assertEqual(caught.exception.reason, 'approved_count_changed')
