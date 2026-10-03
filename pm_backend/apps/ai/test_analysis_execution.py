"""承認済みビューの取得・照合・分割送信(2-A)を検証する。開発DB(pm_ai_reader)の読み取りと、模擬launcherを使う。

実launcher(Docker)との通しは、AI_ANALYSIS_LAUNCHER_URL_FOR_TEST が設定されている場合だけ実行する。
"""
import hashlib
import http.server
import json
import os
import socket
import struct
import threading
import time
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from ai.services import analysis_execution_service as service
from ai.services.analysis_data_service import ANALYSIS_VIEWS
from ai.services.sql_queries import BASE_SQL_SCHEMA

POLICY = SimpleNamespace(max_memory_mb=512, max_cpu_cores=Decimal('1.0'), max_execution_seconds=60, max_fetch_rows=100_000)
PROPOSAL = {
    'datasets': [{'view': 'v_ai_purchase_receipt', 'fields': ['id', 'arrival_date', 'registered_at', 'qty', 'product_code', 'input_source']},
                 {'view': 'v_ai_shipment', 'fields': ['id', 'shipment_date', 'quantity', 'customer_code', 'remark_text']}],
    'date_from': '2020-01-01', 'date_to': '2030-12-31',
}
CHUNK = 500


def split_frames(body):
    frames, offset = [], 0
    while offset + 5 <= len(body):
        (size,) = struct.unpack('>I', body[offset + 1:offset + 5])
        frames.append((body[offset:offset + 1], body[offset + 5:offset + 5 + size]))
        offset += 5 + size
    return frames


def chunk_count(counts):
    return sum((n + CHUNK - 1) // CHUNK for n in counts.values())


class FakeLauncher:
    """受け取った本文を記録して、応答を返す模擬launcher(Dockerは使わない)。"""

    def __init__(self):
        outer = self
        self.bodies, self.declared = [], []
        self.respond = lambda header: {'status': 'ok', 'result': {'report': 'ok'},
                                       'diagnostics': {'rows_loaded': {v['name']: v['expected_rows'] for v in header['views']}}}

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                return

            def do_POST(self):
                length = int(self.headers['Content-Length'])
                outer.declared.append(length)
                data = b''
                while len(data) < length:
                    piece = self.rfile.read(min(65536, length - len(data)))
                    if not piece:
                        break
                    data += piece
                outer.bodies.append(data)
                if len(data) < length:
                    return
                body = json.dumps(outer.respond(json.loads(split_frames(data)[0][1]))).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.server.server_address[1]}'
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def approved_counts():
    """承認画面と同じ固定COUNTを、別の接続で数える(DjangoのテストDB機構は使わない)。"""
    connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
    try:
        cursor = connection.cursor()
        counts = {}
        for dataset in PROPOSAL['datasets']:
            view = dataset['view']
            field = ANALYSIS_VIEWS[view]['date_field']
            cursor.execute(f'SELECT COUNT(*) FROM `{view}` WHERE `{field}` >= %s AND `{field}` <= %s', [PROPOSAL['date_from'], PROPOSAL['date_to']])
            counts[view] = cursor.fetchone()[0]
        return counts
    finally:
        connection.close()


class ExecutionBase(SimpleTestCase):
    def setUp(self):
        self.launcher = FakeLauncher()
        self.addCleanup(self.launcher.close)
        overrides = override_settings(AI_ANALYSIS_LAUNCHER_URL=self.launcher.url)
        overrides.enable()
        self.addCleanup(overrides.disable)

    def run_job(self, code="emit_report('x')", counts=None, policy=POLICY, **kwargs):
        return service.execute_approved_analysis(PROPOSAL, counts or approved_counts(), code, policy, chunk_rows=CHUNK, **kwargs)

    def wait_for_body(self):
        deadline = time.time() + 5
        while not self.launcher.bodies and time.time() < deadline:
            time.sleep(0.05)
        return self.launcher.bodies[0] if self.launcher.bodies else b''


class FetchAndSendTest(ExecutionBase):
    def test_body_matches_declared_length_counts_and_ends_with_e(self):
        counts = approved_counts()
        self.assertGreater(sum(counts.values()), CHUNK)  # 複数チャンクになる件数であること
        result = self.run_job(counts=counts)
        self.assertEqual(result['status'], 'ok')
        body = self.launcher.bodies[0]
        self.assertEqual(len(body), self.launcher.declared[0])  # 本文長(フレーム込み)が、宣言どおり
        frames = split_frames(body)
        self.assertEqual(frames[0][0], b'H')
        self.assertEqual(frames[-1], (b'E', b''))
        self.assertEqual([kind for kind, _ in frames].count(b'E'), 1)  # 終端は最後の1回だけ
        header = json.loads(frames[0][1])
        self.assertEqual({v['name']: v['expected_rows'] for v in header['views']}, counts)
        sent = {}
        for _, payload in frames[1:-1]:
            index, rows = struct.unpack('>HI', payload[:6])
            name = header['views'][index]['name']
            sent[name] = sent.get(name, 0) + rows
        self.assertEqual(sent, counts)
        self.assertEqual(result['fetch']['counts'], counts)
        self.assertEqual(result['fetch']['sent_rows'], counts)  # 2回目に送った行数
        self.assertIsNotNone(result['fetch']['fetched_at'])
        self.assertIsNotNone(result['fetch']['sent_at'])  # 終端フレームまで送り終えた日時
        self.assertEqual(result['fetch']['cleanup'], {'db_connection': 'closed'})
        self.assertEqual(result['fetch']['body_bytes'], len(body))
        self.assertEqual(result['fetch']['chunks'], chunk_count(counts))
        self.assertTrue(all(view['unique_key'] == 'id' for view in header['views']))

    def test_header_carries_policy_limits_and_code_hash_is_recorded(self):
        result = self.run_job(code="emit_report('hash me')")
        header = json.loads(split_frames(self.launcher.bodies[0])[0][1])
        self.assertEqual(header['limits'], {'memory_mb': 512, 'cpus': 1.0, 'python_seconds': 60, 'duckdb_memory_limit_mb': 256, 'threads': 1})
        self.assertEqual(result['fetch']['code_sha256'], hashlib.sha256("emit_report('hash me')".encode()).hexdigest())

    def test_load_count_mismatch_from_launcher_is_not_adopted(self):
        self.launcher.respond = lambda header: {'status': 'ok', 'result': {'report': 'x'},
                                                'diagnostics': {'rows_loaded': {v['name']: v['expected_rows'] - 1 for v in header['views']}}}
        result = self.run_job()
        self.assertEqual((result['status'], result['reason']), ('failed', 'load_count_mismatch'))
        self.assertNotIn('result', result['launcher'])


class StopBeforeAnythingIsSentTest(ExecutionBase):
    def test_changed_count_stops_and_sends_nothing(self):
        counts = approved_counts()
        counts['v_ai_shipment'] += 1
        with self.assertRaises(service.ExecutionStopped) as caught:
            self.run_job(counts=counts)
        self.assertEqual(caught.exception.reason, 'approved_count_changed')
        self.assertEqual(self.launcher.bodies, [])

    def test_fetch_rows_limit_stops_and_sends_nothing(self):
        counts = approved_counts()
        policy = SimpleNamespace(**{**POLICY.__dict__, 'max_fetch_rows': sum(counts.values()) - 1})
        with self.assertRaises(service.ExecutionStopped) as caught:
            self.run_job(counts=counts, policy=policy)
        self.assertEqual(caught.exception.reason, 'fetch_rows_exceeded')
        self.assertEqual(self.launcher.bodies, [])

    def test_unsupported_values_are_rejected(self):
        for value, column_type in [('\\N', 'VARCHAR'), ('x', 'BIGINT'), (1.5, 'DECIMAL(18,3)'), (True, 'BIGINT')]:
            with self.assertRaises(service.ExecutionStopped) as caught:
                service._cell(value, column_type)
            self.assertEqual(caught.exception.reason, 'unsupported_value')

    def test_disabled_and_non_loopback_launcher_are_refused(self):
        for url, reason in [('', 'launcher_disabled'), ('http://10.0.1.232:8091', 'launcher_not_allowed'),
                            ('https://127.0.0.1:8091', 'launcher_not_allowed')]:
            with override_settings(AI_ANALYSIS_LAUNCHER_URL=url), self.assertRaises(service.ExecutionStopped) as caught:
                self.run_job()
            self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(self.launcher.bodies, [])


class SecondPassMismatchTest(ExecutionBase):
    """2回目の取得が1回目と違う、または失敗した場合は、終端フレームを送らず、実行を始めさせない。"""

    def assert_no_end_frame(self, reason, patcher):
        with patcher, self.assertRaises(service.ExecutionStopped) as caught:
            self.run_job()
        self.assertEqual(caught.exception.reason, reason)
        body = self.wait_for_body()
        self.assertLess(len(body), self.launcher.declared[0])  # 本文が不完全(宣言した長さに届かない)
        self.assertNotIn(b'E', [kind for kind, _ in split_frames(body)])
        self.assertEqual(len(self.launcher.bodies), 1)  # 応答は返らず、実行の要求として完結しない

    def test_changed_row_in_second_pass(self):
        real = service._data_frame
        state = {'calls': 0, 'first_pass': chunk_count(approved_counts())}

        def altered(index, rows, types):
            state['calls'] += 1
            if state['calls'] == state['first_pass'] + 2:  # 2回目の2番目のチャンクで、1行を変える
                changed = list(rows[0])
                changed[0] += 1_000_000  # id
                rows = [tuple(changed)] + list(rows[1:])
            return real(index, rows, types)

        self.assert_no_end_frame('refetch_mismatch', patch.object(service, '_data_frame', altered))

    def test_fewer_chunks_in_second_pass(self):
        real = service._chunks
        calls = {'n': 0}

        def dropping(*args, **kwargs):
            calls['n'] += 1
            for item in real(*args, **kwargs):
                if calls['n'] == 2:
                    return  # 2回目は、途中で打ち切る
                yield item

        self.assert_no_end_frame('refetch_mismatch', patch.object(service, '_chunks', dropping))

    def test_fetch_failure_in_second_pass(self):
        real = service._execute
        state = {'calls': 0, 'first_pass': chunk_count(approved_counts())}

        def failing(cursor, deadline, sql, params):
            if sql.startswith('SELECT `id`,'):
                state['calls'] += 1
                if state['calls'] > state['first_pass'] + 1:
                    raise service.ExecutionStopped('fetch_failed', '2回目の取得に失敗', 503)
            return real(cursor, deadline, sql, params)

        self.assert_no_end_frame('fetch_failed', patch.object(service, '_execute', failing))


class DeadlineTest(SimpleTestCase):
    SLOW_SELECT = 'SELECT COUNT(*) FROM v_ai_purchase_receipt a, v_ai_purchase_receipt b, v_ai_purchase_receipt c'  # 実行が終わらない読み取り

    def test_slow_select_stops_at_the_deadline(self):
        connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
        deadline = service.Deadline(2, 'stage_deadline_fetch')
        try:
            cursor = connection.cursor()
            started = time.monotonic()
            with self.assertRaises(service.ExecutionStopped) as caught:
                service._execute(cursor, deadline, self.SLOW_SELECT, [])
            self.assertEqual(caught.exception.reason, 'stage_deadline_fetch')
            self.assertLess(time.monotonic() - started, 6)
        finally:
            service._close_snapshot(connection, deadline.abandoned)  # 動いている問い合わせがある間は、閉じない

    def test_unresponsive_connection_stops_at_the_deadline(self):
        """DBの応答が止まっても、接続の読み取り期限(ここでは30秒)を待たず、取得の期限で止まる。"""
        connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
        deadline = service.Deadline(2, 'stage_deadline_fetch')
        try:
            real = connection.cursor()

            class IgnoresServerSideLimit:
                """サーバー側の期限(max_execution_time)が効かない状況を作る。"""

                def execute(self, sql, params=None):
                    if not sql.startswith('SET SESSION max_execution_time'):
                        real.execute(sql, params)

                def fetchall(self):
                    return real.fetchall()

            started = time.monotonic()
            with self.assertRaises(service.ExecutionStopped):
                service._execute(IgnoresServerSideLimit(), deadline, 'SELECT SLEEP(20)', [])
            self.assertLess(time.monotonic() - started, 4)
        finally:
            service._close_snapshot(connection, deadline.abandoned)

    def test_deadline_that_already_passed_stops(self):
        deadline = service.Deadline(0.01, 'stage_deadline_fetch')
        time.sleep(0.05)
        with self.assertRaises(service.ExecutionStopped):
            deadline.remaining()

    def test_transfer_stops_when_launcher_does_not_read(self):
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        frames = (b'D' + struct.pack('>I', 1_000_000) + b'x' * 1_000_000 for _ in range(500))  # 読まれなければ、送信バッファが埋まる
        started = time.monotonic()
        try:
            with self.assertRaises(service.ExecutionStopped) as caught:
                service._transmit('127.0.0.1', listener.getsockname()[1], 500 * 1_000_005, frames,
                                  service.Deadline(2, 'stage_deadline_transfer'), 5)
        finally:
            listener.close()
        self.assertEqual(caught.exception.reason, 'stage_deadline_transfer')
        self.assertLess(time.monotonic() - started, 6)


class PagingTest(SimpleTestCase):
    def test_non_increasing_key_is_rejected(self):
        class Cursor:
            def execute(self, *args):
                pass

            def fetchall(self):
                return [(1, 'a'), (2, 'b'), (2, 'c')]

        with self.assertRaises(service.ExecutionStopped) as caught:
            list(service._pages(Cursor(), service.Deadline(5, 'x'), 'v_ai_shipment', ['shipment_date'], '2020-01-01', '2030-12-31', 5))
        self.assertEqual(caught.exception.reason, 'duplicate_key')

    def test_column_types_cover_exactly_the_published_columns(self):
        for view in ANALYSIS_VIEWS:
            self.assertEqual(set(service.ANALYSIS_COLUMN_TYPES[view]), set(BASE_SQL_SCHEMA[view]))


@unittest.skipUnless(os.environ.get('AI_ANALYSIS_LAUNCHER_URL_FOR_TEST'), '実launcherの通しは、接続先を指定したときだけ実行する')
class RealLauncherTest(SimpleTestCase):
    """開発のWSL上のlauncher(実Docker)へ、開発DBの実データを送って実行する。"""

    def setUp(self):
        overrides = override_settings(AI_ANALYSIS_LAUNCHER_URL=os.environ['AI_ANALYSIS_LAUNCHER_URL_FOR_TEST'])
        overrides.enable()
        self.addCleanup(overrides.disable)

    CODE = '''
import json
out = {}
for name in ("v_ai_purchase_receipt", "v_ai_shipment"):
    out[name] = {"rows": con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0],
                 "ids": con.execute(f"SELECT COUNT(DISTINCT id) FROM {name}").fetchone()[0]}
out["qty_sum"] = str(con.execute("SELECT SUM(qty) FROM v_ai_purchase_receipt").fetchone()[0])
out["ship_sum"] = str(con.execute("SELECT SUM(quantity) FROM v_ai_shipment").fetchone()[0])
out["remark_nulls"] = con.execute("SELECT COUNT(*) FROM v_ai_shipment WHERE remark_text IS NULL").fetchone()[0]
out["empty_strings"] = con.execute("SELECT COUNT(*) FROM v_ai_shipment WHERE remark_text = ''").fetchone()[0]
emit_report(json.dumps(out))
'''

    def test_real_data_reaches_the_container_and_matches_the_database(self):
        counts = approved_counts()
        result = service.execute_approved_analysis(PROPOSAL, counts, self.CODE, POLICY, chunk_rows=CHUNK)
        self.assertEqual(result['status'], 'ok', result)
        report = json.loads(result['launcher']['result']['report'])
        # DB側の集計と、コンテナ内のDuckDBの集計が一致すること(値が変質していない)
        connection = service.open_snapshot_connection(service.Deadline(30, 'stage_deadline_fetch'), read_timeout=30)
        try:
            cursor = connection.cursor()
            cursor.execute('SELECT SUM(qty) FROM v_ai_purchase_receipt')
            qty_sum = cursor.fetchone()[0]
            cursor.execute("SELECT SUM(quantity), SUM(remark_text IS NULL), SUM(remark_text = '') FROM v_ai_shipment")
            ship_sum, remark_nulls, empty = cursor.fetchone()
        finally:
            connection.close()
        for view, rows in counts.items():
            self.assertEqual(report[view], {'rows': rows, 'ids': rows})
        self.assertEqual(Decimal(report['qty_sum']), qty_sum)
        self.assertEqual(Decimal(report['ship_sum']), ship_sum)
        self.assertEqual((report['remark_nulls'], report['empty_strings']), (int(remark_nulls), int(empty)))
        self.assertEqual(result['fetch']['fetched_rows'], counts)

    def test_second_pass_mismatch_leaves_the_launcher_usable(self):
        """2回目の不一致で中止しても、launcherは詰まらず、次のジョブを実行できる(未完結の本文は結果にならない)。"""
        real = service._data_frame
        state = {'calls': 0, 'first_pass': chunk_count(approved_counts())}

        def altered(index, rows, types):
            state['calls'] += 1
            if state['calls'] == state['first_pass'] + 2:
                changed = list(rows[0])
                changed[0] += 1_000_000
                rows = [tuple(changed)] + list(rows[1:])
            return real(index, rows, types)

        with patch.object(service, '_data_frame', altered), self.assertRaises(service.ExecutionStopped) as caught:
            service.execute_approved_analysis(PROPOSAL, approved_counts(), "emit_report('must not run')", POLICY, chunk_rows=CHUNK)
        self.assertEqual(caught.exception.reason, 'refetch_mismatch')
        for _ in range(20):  # 中止したジョブのコンテナの削除が終わるまで、launcherは実行中として新しいジョブを断る
            try:
                again = service.execute_approved_analysis(PROPOSAL, approved_counts(), "emit_report('next')", POLICY, chunk_rows=CHUNK)
            except service.ExecutionStopped as exc:
                self.assertEqual(exc.reason, 'launcher_unreachable')
                time.sleep(2)
                continue
            if again['status'] != 'refused':
                break
            time.sleep(2)
        self.assertEqual((again['status'], again['launcher']['result']['report']), ('ok', 'next'))


class HardDeadlineTest(SimpleTestCase):
    """DBの応答が止まっても・遅れて返っても、取得の期限(60秒の設定値)で止める。"""

    def test_blocked_query_is_abandoned_at_the_deadline(self):
        class Blocked:
            def execute(self, *args):
                time.sleep(6)

            def fetchall(self):
                return []

        deadline = service.Deadline(1, 'stage_deadline_fetch')
        started = time.monotonic()
        with self.assertRaises(service.ExecutionStopped) as caught:
            service._execute(Blocked(), deadline, 'SELECT 1', [])
        self.assertEqual(caught.exception.reason, 'stage_deadline_fetch')
        self.assertLess(time.monotonic() - started, 2.5)  # 読み取り期限(125秒)や問い合わせの完了を待たない
        self.assertTrue(deadline.abandoned and deadline.abandoned[0].is_alive())

    def test_result_returned_after_the_deadline_is_rejected(self):
        deadline = service.Deadline(5, 'stage_deadline_fetch')

        class Late:
            def execute(self, *args):
                pass

            def fetchall(self):
                deadline.end = time.monotonic() - 1  # 期限を過ぎてから返った状況
                return [(1,)]

        with self.assertRaises(service.ExecutionStopped) as caught:
            service._execute(Late(), deadline, 'SELECT 1', [])
        self.assertEqual(caught.exception.reason, 'stage_deadline_fetch')

    def test_connection_is_closed_after_the_abandoned_query_ends(self):
        from unittest.mock import MagicMock
        connection = MagicMock()
        worker = threading.Thread(target=time.sleep, args=(0.5,))
        worker.start()
        self.assertEqual(service._close_snapshot(connection, [worker]), 'pending')  # 動いている間は、完了ではなく待機中
        connection.close.assert_not_called()  # 動いている問い合わせがある間は、閉じない
        worker.join()
        deadline = time.time() + 3
        while not connection.close.called and time.time() < deadline:
            time.sleep(0.05)
        connection.rollback.assert_called_once()
        connection.close.assert_called_once()
        self.assertEqual(service._close_snapshot(MagicMock(), []), 'closed')

    def test_first_pass_that_ends_after_the_fetch_deadline_is_rejected(self):
        # 取得全体が、取得の期限(ここでは極端に短い値)を超えたら、実行しない
        launcher = FakeLauncher()
        self.addCleanup(launcher.close)
        with override_settings(AI_ANALYSIS_LAUNCHER_URL=launcher.url), self.assertRaises(service.ExecutionStopped) as caught:
            service.execute_approved_analysis(PROPOSAL, approved_counts(), 'x', POLICY, deadlines={'fetch': 0.001}, chunk_rows=CHUNK)
        self.assertEqual(caught.exception.reason, 'stage_deadline_fetch')
        self.assertEqual(launcher.bodies, [])


class ConnectionCleanupTest(SimpleTestCase):
    def test_connection_is_closed_when_transaction_start_fails(self):
        import mysql.connector
        from unittest.mock import MagicMock
        fake = MagicMock()
        fake.start_transaction.side_effect = mysql.connector.Error('開始できない')
        with patch.object(service.mysql.connector, 'connect', return_value=fake), self.assertRaises(service.ExecutionStopped) as caught:
            service.open_snapshot_connection(service.Deadline(5, 'stage_deadline_fetch'), read_timeout=5)
        self.assertEqual(caught.exception.reason, 'fetch_failed')
        fake.close.assert_called_once()

    def test_connection_is_closed_when_session_setup_fails(self):
        import mysql.connector
        from unittest.mock import MagicMock
        fake = MagicMock()
        fake.cursor.return_value.execute.side_effect = mysql.connector.Error('設定できない')
        with patch.object(service.mysql.connector, 'connect', return_value=fake), self.assertRaises(service.ExecutionStopped):
            service.open_snapshot_connection(service.Deadline(5, 'stage_deadline_fetch'), read_timeout=5)
        fake.close.assert_called_once()


class TimingTest(ExecutionBase):
    def test_transfer_time_excludes_launcher_execution_and_response_wait(self):
        def slow(header):
            time.sleep(1.5)
            return {'status': 'ok', 'result': {'report': 'ok'},
                    'diagnostics': {'rows_loaded': {v['name']: v['expected_rows'] for v in header['views']}}}

        self.launcher.respond = slow
        record = self.run_job()['fetch']
        self.assertGreaterEqual(record['launcher_seconds'], 1.4)
        self.assertLess(record['transfer_seconds'], 1.0)


class ConnectionStartDeadlineTest(SimpleTestCase):
    """接続・セッション設定・トランザクション開始の停止も、取得の期限で打ち切る。動作中の接続は無理に閉じず、後始末は待機中として扱う。"""

    def hanging_connect(self, where):
        from unittest.mock import MagicMock
        fake = MagicMock()

        def slow(*args, **kwargs):
            time.sleep(1.2)

        if where == 'start_transaction':
            fake.start_transaction.side_effect = slow
            return fake, lambda *a, **k: fake
        if where == 'session':
            fake.cursor.return_value.execute.side_effect = slow
            return fake, lambda *a, **k: fake

        def connect(*args, **kwargs):
            slow()
            return fake

        return fake, connect

    def test_each_start_step_is_cut_at_the_deadline_and_the_late_connection_is_closed_by_its_own_thread(self):
        for where in ('connect', 'session', 'start_transaction'):
            fake, connect = self.hanging_connect(where)
            deadline = service.Deadline(0.3, 'stage_deadline_fetch')
            started = time.monotonic()
            with patch.object(service.mysql.connector, 'connect', connect), self.assertRaises(service.ExecutionStopped) as caught:
                service.open_snapshot_connection(deadline, read_timeout=30)
            self.assertEqual(caught.exception.reason, 'stage_deadline_fetch', where)
            self.assertLess(time.monotonic() - started, 0.9, where)  # 開始処理の完了(1.2秒)を待たない
            self.assertTrue(deadline.abandoned and deadline.abandoned[0].is_alive(), where)
            deadline.abandoned[0].join(5)
            self.assertTrue(fake.close.called, where)  # 待ちをやめた後に開いた接続は、そのスレッドが閉じる

    def test_hung_start_is_reported_as_pending_cleanup_and_sends_nothing(self):
        launcher = FakeLauncher()
        self.addCleanup(launcher.close)
        fake, connect = self.hanging_connect('start_transaction')
        with override_settings(AI_ANALYSIS_LAUNCHER_URL=launcher.url), patch.object(service.mysql.connector, 'connect', connect),                 self.assertRaises(service.ExecutionStopped) as caught:
            service.execute_approved_analysis(PROPOSAL, {'v_ai_purchase_receipt': 1, 'v_ai_shipment': 1}, 'x', POLICY, deadlines={'fetch': 0.3})
        self.assertEqual(caught.exception.reason, 'stage_deadline_fetch')
        self.assertEqual(caught.exception.cleanup, {'db_connection': 'pending'})  # 完了ではなく、待機中
        self.assertEqual(launcher.bodies, [])
        time.sleep(1.5)  # 後始末のスレッドが、遅れて開いた接続を閉じる
        self.assertTrue(fake.close.called)


class CleanupFailureTest(SimpleTestCase):
    """後始末の異常系: rollbackが失敗してもcloseを試み、closeが失敗したら「完了」と記録しない。"""

    def fake(self, rollback_fails=False, close_fails=False):
        from unittest.mock import MagicMock
        fake = MagicMock()
        if rollback_fails:
            fake.rollback.side_effect = RuntimeError('rollback失敗')
        if close_fails:
            fake.close.side_effect = RuntimeError('close失敗')
        return fake

    def test_close_is_attempted_even_if_rollback_fails(self):
        fake = self.fake(rollback_fails=True)
        self.assertEqual(service._close_snapshot(fake, []), 'closed')
        fake.close.assert_called_once()

    def test_close_failure_is_reported_as_failed_not_closed(self):
        fake = self.fake(close_fails=True)
        self.assertEqual(service._close_snapshot(fake, []), 'failed')
        fake = self.fake(rollback_fails=True, close_fails=True)
        self.assertEqual(service._close_snapshot(fake, []), 'failed')

    def test_late_connection_is_closed_even_if_rollback_fails(self):
        fake = self.fake(rollback_fails=True)

        def connect(*args, **kwargs):
            time.sleep(0.8)
            return fake

        deadline = service.Deadline(0.2, 'stage_deadline_fetch')
        with patch.object(service.mysql.connector, 'connect', connect), self.assertRaises(service.ExecutionStopped):
            service.open_snapshot_connection(deadline, read_timeout=30)
        deadline.abandoned[0].join(5)
        fake.rollback.assert_called()
        fake.close.assert_called_once()  # rollbackが失敗しても、closeは呼ばれる

    def test_late_connection_close_failure_is_recorded(self):
        fake = self.fake(close_fails=True)

        def connect(*args, **kwargs):
            time.sleep(0.8)
            return fake

        deadline = service.Deadline(0.2, 'stage_deadline_fetch')
        with patch.object(service.mysql.connector, 'connect', connect), self.assertRaises(service.ExecutionStopped):
            service.open_snapshot_connection(deadline, read_timeout=30)
        deadline.abandoned[0].join(5)
        self.assertTrue(deadline.cleanup_failed)

    def test_connection_opened_just_after_the_deadline_is_closed_and_failure_recorded(self):
        fake = self.fake(close_fails=True)
        deadline = service.Deadline(5, 'stage_deadline_fetch')

        def connect(*args, **kwargs):
            deadline.end = time.monotonic() - 1  # 待ちをやめる前に開いたが、期限は過ぎている
            return fake

        with patch.object(service.mysql.connector, 'connect', connect), self.assertRaises(service.ExecutionStopped):
            service.open_snapshot_connection(deadline, read_timeout=30)
        fake.close.assert_called_once()
        self.assertTrue(deadline.cleanup_failed)  # execute_approved_analysisは、これを'failed'として記録する


class ManagementColumnTest(ExecutionBase):
    def test_execution_requires_the_management_column_in_the_approved_fields(self):
        proposal = {**PROPOSAL, 'datasets': [{'view': 'v_ai_shipment', 'fields': ['shipment_date', 'quantity']}]}
        with self.assertRaises(service.ExecutionStopped) as caught:
            service.execute_approved_analysis(proposal, {'v_ai_shipment': 1}, 'x', POLICY)
        self.assertEqual(caught.exception.reason, 'management_column_missing')
        self.assertEqual(self.launcher.bodies, [])  # 何も送らない

    def test_id_is_always_sent_and_confirmed_by_the_container(self):
        self.run_job()
        header = json.loads(split_frames(self.launcher.bodies[0])[0][1])
        for view in header['views']:
            self.assertEqual(view['unique_key'], 'id')
            self.assertEqual(view['columns'][0]['name'], 'id')


class ProgressOnStopTest(ExecutionBase):
    def test_stopped_run_carries_cleanup_and_progress_for_the_history(self):
        real = service._data_frame
        state = {'calls': 0, 'first_pass': chunk_count(approved_counts())}

        def altered(index, rows, types):
            state['calls'] += 1
            if state['calls'] == state['first_pass'] + 2:
                changed = list(rows[0])
                changed[0] += 1_000_000
                rows = [tuple(changed)] + list(rows[1:])
            return real(index, rows, types)

        with patch.object(service, '_data_frame', altered), self.assertRaises(service.ExecutionStopped) as caught:
            self.run_job()
        counts = approved_counts()
        self.assertEqual(caught.exception.cleanup, {'db_connection': 'closed'})
        self.assertEqual(caught.exception.progress['snapshot_counts'], counts)
        self.assertEqual(caught.exception.progress['fetched_rows'], counts)  # 1回目は、すべて取得できている
        self.assertLess(sum(caught.exception.progress['sent_rows'].values()), sum(counts.values()))  # 送信は、途中まで
        self.assertNotIn('sent_at', caught.exception.progress)  # 終端まで送っていない
