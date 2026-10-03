"""承認済みビューを同一スナップショットで取得・照合し、隔離実行のlauncherへ分割送信する(開発限定。第2段階の2-A)。

方針(AI分析基盤仕様書の2.2.1・2.2.3・4.6-2):
- 件数確認と全行の取得は、`pm_ai_reader`の1つの接続・1つのトランザクション(REPEATABLE READ)で行う。
- launcherは、送信前に本文の総バイト数を要求する。全データを溜めずに満たすため、同じスナップショットを2回読む。
  1回目は、件数・一意キー・総バイト数・チャンクごとのSHA-256を計算して行を破棄する。
  2回目は、同じ順序で再取得して送る。チャンクごとに1回目のSHA-256と照合し、1つでも違えば、そのチャンクを送らずに中止する。
- 実行の開始につながる終端フレーム(E)は、2回目の全チャンクが1回目と一致した後にだけ送る。
  それまでに中止した場合は、Eを送らずに接続を閉じる(launcherは本文が不完全な入力として結果を採用しない)。
- 取得は一意キー(id)の順に、キーを基準としたページ送りで行う(LIMITは分割のためで、打切りではない。合計は件数と照合する)。
- 取得・転送の各段階には、全体の期限を設ける。待ち続けるSELECTも、期限で止める。
- 本番は、`AI_ANALYSIS_LAUNCHER_URL`が未設定のため実行しない。ループバック以外の接続先は拒否する。
"""
import hashlib
import http.client
import json
import math
import socket
import struct
import threading
import time
from datetime import date, datetime
from decimal import Decimal
from urllib.parse import urlsplit

import mysql.connector
from django.conf import settings

from ai.services.analysis_data_service import ANALYSIS_VIEWS, MANAGEMENT_COLUMN, validate_datasets
from ai.services.analysis_plan_store import AnalysisError
from ai.services.sql_queries import BASE_SQL_SCHEMA

# 検証用の暫定値(開発限定。実測後にBOSSが確定する)。launcherの転送・投入の予算と同じ60秒。
CHUNK_ROWS = 5_000
DEADLINES = {'fetch': 60, 'transfer': 60}
LAUNCHER_STAGE_SECONDS = 60 + 60 + 20 + 30  # launcher側の転送・投入・監督の猶予・後始末。応答待ちの上限の計算に使う
NULL_MARK = '\\N'
ER_QUERY_TIMEOUT = 3024  # MySQLのmax_execution_time超過
ER_LOCK_WAIT_TIMEOUT = 1205  # メタデータロックなどの待ち時間超過(lock_wait_timeout)
LOOPBACK_HOSTS = ('127.0.0.1', 'localhost', '::1')

# DuckDBの列型。ビューの実際の列型(開発DBのSHOW COLUMNS)に合わせる。推測で追加しない。
ANALYSIS_COLUMN_TYPES = {
    'v_ai_purchase_receipt': {
        'id': 'BIGINT', 'arrival_date': 'DATE', 'registered_at': 'TIMESTAMP', 'supplier_id': 'BIGINT',
        'line_id': 'BIGINT', 'product_id': 'BIGINT', 'product_code': 'VARCHAR', 'product_name': 'VARCHAR',
        'qty': 'DECIMAL(18,3)', 'process_id': 'BIGINT', 'input_source': 'VARCHAR',
    },
    'v_ai_shipment': {
        'id': 'BIGINT', 'shipment_date': 'DATE', 'product_code': 'VARCHAR', 'product_id': 'BIGINT',
        'product_name': 'VARCHAR', 'customer_code': 'VARCHAR', 'ship_to_code': 'VARCHAR',
        'quantity': 'DECIMAL(18,3)', 'trip_allocation_id': 'BIGINT', 'remark_text': 'VARCHAR',
    },
}


class ExecutionStopped(AnalysisError):
    """取得・照合・送信のいずれかで、実行を止めた。reasonは、実行履歴に残す失敗理由。"""

    def __init__(self, reason, detail, status=503):
        self.reason = reason
        self.cleanup = None  # 接続の後始末の状態。実行中に止めた場合は、execute_approved_analysisが設定する
        super().__init__(detail, status)


class Deadline:
    """段階ごとの全体の期限。残り時間を返し、超過したら止める。"""

    def __init__(self, seconds, reason):
        self.end = time.monotonic() + seconds
        self.reason = reason
        self.abandoned = []  # 期限で待ちをやめたDB問い合わせのスレッド(終了するまで、接続を閉じない)
        self.cleanup_failed = False  # 接続を閉じる処理に失敗した

    def remaining(self):
        left = self.end - time.monotonic()
        if left <= 0:
            raise ExecutionStopped(self.reason, f'{self.reason}: 期限を超えました。', 408)
        return left


def launcher_endpoint():
    """launcherの接続先。未設定・ループバック以外は使わない(本番は実行しない)。"""
    url = getattr(settings, 'AI_ANALYSIS_LAUNCHER_URL', '')
    if not url:
        raise ExecutionStopped('launcher_disabled', '分析の隔離実行は無効です(AI_ANALYSIS_LAUNCHER_URLが未設定)。', 503)
    parts = urlsplit(url)
    if parts.scheme != 'http' or parts.hostname not in LOOPBACK_HOSTS or not parts.port:
        raise ExecutionStopped('launcher_not_allowed', '隔離実行のlauncherは、開発のループバック接続(http)だけを許可します。', 503)
    return parts.hostname, parts.port


def open_snapshot_connection(deadline, read_timeout):
    """`pm_ai_reader`専用の接続を、Djangoの共有接続とは別に開く(トランザクションを他の処理と共有しない)。

    接続・セッション設定・トランザクション開始も、取得の期限の対象とする。別スレッドで実行し、期限で待ちをやめる。
    待ちをやめた後に開けた接続は、そのスレッドが閉じる(deadline.abandonedへ残し、後始末は「待機中」として扱う)。
    """
    config = settings.DATABASES['ai_reader']
    if config['USER'] != 'pm_ai_reader':
        raise ExecutionStopped('reader_misconfigured', '分析用DB接続をpm_ai_readerへ設定してください。', 503)
    options = dict(config['OPTIONS'])
    init_command = options.pop('init_command', None)
    state = {'connection': None, 'error': None, 'abandoned': False}
    lock = threading.Lock()

    def work():
        connection = None
        try:
            connection = mysql.connector.connect(
                user=config['USER'], password=config['PASSWORD'], host=config['HOST'], port=int(config['PORT']),
                database=config['NAME'], read_timeout=read_timeout, **options,
            )
            cursor = connection.cursor()
            if init_command:
                cursor.execute(init_command)
            cursor.execute('SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            cursor.close()
            connection.start_transaction(consistent_snapshot=True, isolation_level='REPEATABLE READ')
        except BaseException as exc:
            if connection is not None:  # 接続後の失敗(トランザクション開始など)でも、接続を残さない
                try:
                    connection.close()
                except Exception:
                    pass
            state['error'] = exc
            return
        with lock:
            if state['abandoned']:  # 期限で待ちをやめた後に開けた接続は、ここで閉じる(rollbackが失敗しても、closeは試みる)
                if _close_connection(connection) == 'failed':
                    deadline.cleanup_failed = True
                return
            state['connection'] = connection

    left = deadline.remaining()  # 期限切れなら、接続を開始する前に止める(開始後に例外を出して、接続を残さない)
    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    worker.join(left)
    with lock:
        if state['connection'] is None and state['error'] is None:
            state['abandoned'] = True
            deadline.abandoned.append(worker)
            raise ExecutionStopped(deadline.reason, f'{deadline.reason}: 分析用DBへの接続・開始が期限内に終わりませんでした。', 408)
    if state['error'] is not None:
        if isinstance(state['error'], (mysql.connector.Error, OSError)):
            raise ExecutionStopped('fetch_failed', '分析用DBへ接続できません。', 503) from state['error']
        raise state['error']
    if time.monotonic() >= deadline.end:  # 期限を過ぎて開いた接続は使わない
        if _close_snapshot(state['connection'], []) == 'failed':
            deadline.cleanup_failed = True
        raise ExecutionStopped(deadline.reason, f'{deadline.reason}: 分析用DBへの接続が期限を過ぎました。', 408)
    return state['connection']


def _execute(cursor, deadline, sql, params):
    """期限つきでSELECTを実行して全行を返す。期限(残り時間)を超えたら、必ずそこで止める。

    - 実行が長引く場合はサーバー側のmax_execution_time、ロック待ちはlock_wait_timeoutで止める。
    - DBの応答が止まった場合も、別スレッドで実行して待ちを期限でやめる(接続の読み取り期限に依存しない)。
      待ちをやめた場合、そのスレッドはdeadline.abandonedへ残し、接続の後始末はスレッドの終了後に行う。
    - 期限を過ぎて返った結果は、採用しない。
    """
    left = deadline.remaining()
    box = {}

    def work():
        try:
            cursor.execute('SET SESSION max_execution_time = %s, lock_wait_timeout = %s',
                           [max(1, int(left * 1000)), max(1, math.ceil(left))])
            cursor.execute(sql, params)
            box['rows'] = cursor.fetchall()
        except BaseException as exc:  # スレッド内の例外は、呼び出し側で判定する
            box['error'] = exc

    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    worker.join(left)
    if worker.is_alive():
        deadline.abandoned.append(worker)
        raise ExecutionStopped(deadline.reason, f'{deadline.reason}: データベースの応答が期限内に返りませんでした。', 408)
    error = box.get('error')
    if error is not None:
        if isinstance(error, (mysql.connector.Error, OSError)):
            if getattr(error, 'errno', None) in (ER_QUERY_TIMEOUT, ER_LOCK_WAIT_TIMEOUT) or time.monotonic() >= deadline.end                     or isinstance(error, (socket.timeout, TimeoutError)):
                raise ExecutionStopped(deadline.reason, f'{deadline.reason}: データベースの応答が期限内に返りませんでした。', 408) from error
            raise ExecutionStopped('fetch_failed', 'データの取得に失敗しました。', 503) from error
        raise error
    if time.monotonic() >= deadline.end:  # 期限を過ぎて返った結果は、採用しない
        raise ExecutionStopped(deadline.reason, f'{deadline.reason}: 期限を過ぎて応答が返りました。', 408)
    return box['rows']


def _close_connection(connection):
    """rollbackの成否にかかわらずcloseを試み、closeできたら'closed'、できなければ'failed'を返す(失敗を握りつぶさない)。"""
    try:
        connection.rollback()
    except Exception:
        pass  # rollbackに失敗しても、接続を閉じればトランザクションは終わる。closeは必ず試みる
    try:
        connection.close()
    except Exception:
        return 'failed'
    return 'closed'


def _close_snapshot(connection, abandoned, on_done=None):
    """トランザクションと接続を閉じ、状態('closed' / 'pending' / 'failed')を返す。

    期限で待ちをやめた問い合わせ・接続開始がまだ動いている間は、接続を閉じず、その終了後に閉じる(動作中に閉じない)。
    その間は「後始末の完了」ではなく「待機中(pending)」として扱う。接続を閉じられなかった場合は'failed'とする。
    """
    def close():
        for worker in abandoned:
            worker.join()
        return 'closed' if connection is None else _close_connection(connection)

    def close_later():
        status = close()
        if on_done is not None:  # 待機中だった後始末の最終結果(closed / failed)を、履歴へ反映するために通知する
            try:
                on_done(status)
            except Exception:
                pass

    if any(worker.is_alive() for worker in abandoned):
        threading.Thread(target=close_later, daemon=True).start()
        return 'pending'
    return close()


def _cell(value, column_type):
    """値を、DuckDBへ投入するCSVの文字列へ変換する。型が宣言と合わない値・NULL記号と同じ文字列は、受け付けない。"""
    if value is None:
        return NULL_MARK
    kind = type(value)
    if column_type == 'BIGINT' and kind is int:
        return str(value)
    if column_type == 'DATE' and kind is date:
        return value.isoformat()
    if column_type == 'TIMESTAMP' and kind is datetime:
        return value.isoformat(sep=' ', timespec='microseconds')
    if column_type == 'DECIMAL(18,3)' and kind is Decimal:
        return format(value, 'f')
    if column_type == 'VARCHAR' and kind is str and value != NULL_MARK:
        return value
    raise ExecutionStopped('unsupported_value', f'{column_type}の列に、投入できない値({kind.__name__})があります。', 422)


def _frame(kind, payload):
    return kind + struct.pack('>I', len(payload)) + payload


def _data_frame(index, rows, types):
    """チャンクを、launcherのデータフレーム(D)へ変換する。同じ行は、必ず同じバイト列になる。"""
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator='\n')
    for row in rows:
        writer.writerow([_cell(value, column_type) for value, column_type in zip(row, types)])
    return _frame(b'D', struct.pack('>HI', index, len(rows)) + buffer.getvalue().encode('utf-8'))


def _pages(cursor, deadline, view, fields, date_from, date_to, chunk_rows):
    """一意キー(id)の順に、キーを基準にしてページ送りで取得する。キーが単調増加でなければ失敗にする。"""
    date_field = ANALYSIS_VIEWS[view]['date_field']
    columns = ', '.join(f'`{field}`' for field in fields)
    base = f'SELECT `id`, {columns} FROM `{view}` WHERE `{date_field}` >= %s AND `{date_field}` <= %s'
    last = None
    while True:
        if last is None:
            sql, params = f'{base} ORDER BY `id` LIMIT %s', [date_from, date_to, chunk_rows]
        else:
            sql, params = f'{base} AND `id` > %s ORDER BY `id` LIMIT %s', [date_from, date_to, last, chunk_rows]
        rows = _execute(cursor, deadline, sql, params)
        if not rows:
            return
        for row in rows:
            if last is not None and row[0] <= last:
                raise ExecutionStopped('duplicate_key', f'{view}: 一意キー(id)が重複または逆順です。', 422)
            last = row[0]
        yield [row[1:] for row in rows]
        if len(rows) < chunk_rows:
            return


def _count(cursor, deadline, view, date_from, date_to):
    date_field = ANALYSIS_VIEWS[view]['date_field']
    rows = _execute(cursor, deadline, f'SELECT COUNT(*) FROM `{view}` WHERE `{date_field}` >= %s AND `{date_field}` <= %s', [date_from, date_to])
    return rows[0][0]


def _header_frame(code, datasets, counts, policy):
    cpus = float(policy.max_cpu_cores)
    views = []
    for dataset in datasets:
        view, fields = dataset['view'], dataset['fields']
        views.append({
            'name': view,
            'columns': [{'name': field, 'type': ANALYSIS_COLUMN_TYPES[view][field]} for field in fields],
            'expected_rows': counts[view],
            'unique_key': MANAGEMENT_COLUMN,
        })
    header = {
        'limits': {'memory_mb': policy.max_memory_mb, 'cpus': cpus, 'python_seconds': policy.max_execution_seconds,
                   'duckdb_memory_limit_mb': policy.max_memory_mb // 2, 'threads': math.ceil(cpus)},
        'code': code, 'views': views,
    }
    return _frame(b'H', json.dumps(header, ensure_ascii=False).encode('utf-8'))


def _chunks(cursor, deadline, datasets, date_from, date_to, chunk_rows):
    """(ビュー番号, フレーム)を、ビュー順・キー順に返す。"""
    for index, dataset in enumerate(datasets):
        view = dataset['view']
        types = [ANALYSIS_COLUMN_TYPES[view][field] for field in dataset['fields']]
        for rows in _pages(cursor, deadline, view, dataset['fields'], date_from, date_to, chunk_rows):
            yield index, rows, _data_frame(index, rows, types)


def _transmit(host, port, length, frames, transfer, response_timeout, timing=None):
    """本文を、フレームごとに送る。送信元(frames)が例外を出したら、Eを送らずに接続を閉じる。

    timing(辞書)へ、send_seconds(本文の送信だけの時間)を記録する。
    """
    timing = {} if timing is None else timing
    started = time.monotonic()
    connection = http.client.HTTPConnection(host, port, timeout=transfer.remaining())
    try:
        connection.putrequest('POST', '/v1/jobs')
        connection.putheader('Content-Length', str(length))
        connection.endheaders()
        for frame in frames:
            connection.sock.settimeout(transfer.remaining())
            connection.sock.sendall(frame)
        timing['send_seconds'] = time.monotonic() - started  # 本文の送信だけの時間(2回目の取得を含む)。launcherの実行・応答待ちは含めない
        connection.sock.settimeout(response_timeout)
        response = connection.getresponse()
        return response.status, json.loads(response.read().decode('utf-8'))
    except (socket.timeout, TimeoutError) as exc:
        raise ExecutionStopped('stage_deadline_transfer', '転送の期限内にlauncherへ送れませんでした。', 408) from exc
    except (OSError, http.client.HTTPException, ValueError) as exc:
        # launcherは、実行中のジョブがある場合などに、本文を読まずに応答して接続を閉じる。応答を読めれば、その理由を返す
        try:
            connection.sock.settimeout(2)
            early = connection.getresponse()
            return early.status, json.loads(early.read().decode('utf-8'))
        except Exception:
            pass
        raise ExecutionStopped('launcher_unreachable', 'launcherとの通信に失敗しました(実行中のジョブがある場合も、この失敗になります)。', 503) from exc
    finally:
        connection.close()  # 中止した場合は、Eを送らないまま閉じる(launcherは不完全な本文として結果を採用しない)


def execute_approved_analysis(proposal, approved_counts, code, policy, deadlines=None, chunk_rows=CHUNK_ROWS, on_cleanup_done=None):
    """承認済みの範囲を取得・照合して送り、launcherの結果を返す。履歴の保存は呼び出し側(analysis_run_service)が行う。

    止めた場合のExecutionStoppedには、cleanup(後始末の状態)とprogress(そこまでの件数・日時)を付ける。
    on_cleanup_done: 待機中(pending)だった接続の後始末が終わったときに、最終状態(closed / failed)を通知する。

    proposal: {'datasets': [{'view', 'fields'}], 'date_from', 'date_to'}。承認済み。
    approved_counts: {ビュー名: 承認時のCOUNT}。
    code: 生成コード(2-Bでの生成物。ここでは文字列として受け取るだけ)。
    返り値: {'status', 'launcher': launcherの応答, 'fetch': 取得・照合の記録}
    """
    host, port = launcher_endpoint()
    datasets = validate_datasets(proposal['datasets'], proposal['date_from'], proposal['date_to'])
    date_from, date_to = proposal['date_from'], proposal['date_to']
    for dataset in datasets:
        missing = [f for f in dataset['fields'] if f not in ANALYSIS_COLUMN_TYPES[dataset['view']]]
        if MANAGEMENT_COLUMN not in dataset['fields']:  # 重複・欠落の確認に必要な管理列は、承認済みの取得列に含まれていること
            raise ExecutionStopped('management_column_missing', f'{dataset["view"]}: 管理列({MANAGEMENT_COLUMN})が承認済みの取得列にありません。', 422)
        if missing or set(ANALYSIS_COLUMN_TYPES[dataset['view']]) != set(BASE_SQL_SCHEMA[dataset['view']]):
            raise ExecutionStopped('column_type_unknown', f'{dataset["view"]}: 列型が未定義の列があります。', 422)
    limits = {**DEADLINES, **(deadlines or {})}
    fetch = Deadline(limits['fetch'], 'stage_deadline_fetch')
    started = time.monotonic()
    transfer = None
    connection = None
    cleanup = {}
    progress = {}  # 止めた場合に、履歴へ残す、そこまでの件数・日時

    def finish():
        """接続の後始末(1回だけ)。期限で待ちをやめた問い合わせが動いている間は、'pending'(待機中)とする。"""
        if 'db_connection' not in cleanup:
            status = _close_snapshot(connection, [*fetch.abandoned, *(transfer.abandoned if transfer else [])], on_cleanup_done)
            failed = fetch.cleanup_failed or (transfer is not None and transfer.cleanup_failed)
            cleanup['db_connection'] = 'failed' if failed else status
        return dict(cleanup)

    try:
        connection = open_snapshot_connection(fetch, read_timeout=math.ceil(limits['fetch'] + limits['transfer']) + 5)  # read_timeoutは最後の備え。期限は別スレッドで守る
        cursor = connection.cursor()
        # 1. 同じスナップショットでCOUNTし、承認時の件数・上限と照合する(違えば、何も送らずに止める)
        counts = {}
        for dataset in datasets:
            counts[dataset['view']] = _count(cursor, fetch, dataset['view'], date_from, date_to)
        changed = {v: (approved_counts.get(v), n) for v, n in counts.items() if approved_counts.get(v) != n}
        if changed:
            raise ExecutionStopped('approved_count_changed', f'承認時から件数が変わりました。再度、件数確認と承認が必要です: {changed}', 409)
        if sum(counts.values()) > policy.max_fetch_rows:
            raise ExecutionStopped('fetch_rows_exceeded', f'対象が上限({policy.max_fetch_rows}行)を超えました。期間・条件を絞ってください。', 413)
        # 2. 1回目の取得: 件数・一意キー・総バイト数・チャンクごとのSHA-256を計算し、行は破棄する
        header = _header_frame(code, datasets, counts, policy)
        digests, loaded, body_length = [], {d['view']: 0 for d in datasets}, len(header) + 5
        for index, rows, frame in _chunks(cursor, fetch, datasets, date_from, date_to, chunk_rows):
            digests.append(hashlib.sha256(frame).digest())
            loaded[datasets[index]['view']] += len(rows)
            body_length += len(frame)
        progress.update(snapshot_counts=dict(counts), fetched_rows=dict(loaded))
        fetch.remaining()  # 1回目の全体が、取得の期限を超えていないこと
        if loaded != counts:
            raise ExecutionStopped('fetch_count_mismatch', f'取得行数がCOUNTと一致しません: 取得{loaded} / COUNT{counts}', 422)
        fetch_seconds = time.monotonic() - started
        progress.update(fetched_at=datetime.now(), fetch_seconds=round(fetch_seconds, 3))

        # 3. 2回目の取得を送信する。チャンクごとに1回目と照合し、全件が一致した後にだけ、終端(E)を送る
        transfer = Deadline(limits['transfer'], 'stage_deadline_transfer')
        transfer_started = time.monotonic()
        timing = {}

        sent_rows = {d['view']: 0 for d in datasets}
        progress['sent_rows'] = sent_rows  # 送ったチャンクまでの行数(中止時は、途中まで)

        def frames():
            yield header
            sent = 0
            for index, rows, frame in _chunks(cursor, transfer, datasets, date_from, date_to, chunk_rows):
                if sent >= len(digests) or hashlib.sha256(frame).digest() != digests[sent]:
                    raise ExecutionStopped('refetch_mismatch', '2回目の取得が1回目と一致しません。同一スナップショットを確認できないため、実行しません。', 409)
                sent += 1
                sent_rows[datasets[index]['view']] += len(rows)
                yield frame
            if sent != len(digests):
                raise ExecutionStopped('refetch_mismatch', '2回目の取得の件数が1回目と一致しません。', 409)
            yield _frame(b'E', b'')
            progress['sent_at'] = datetime.now()  # 終端フレームまで送り終えた日時

        response_timeout = limits['transfer'] + LAUNCHER_STAGE_SECONDS + policy.max_execution_seconds
        status, launcher = _transmit(host, port, body_length, frames(), transfer, response_timeout, timing)
        total_seconds = time.monotonic() - transfer_started
    except Exception as exc:
        exc.cleanup = finish()  # 履歴へ残す後始末の状態(closed / pending / failed)
        exc.progress = dict(progress)
        raise
    finally:
        finish()
    record = {
        'views': [d['view'] for d in datasets], 'date_from': date_from, 'date_to': date_to,
        'approved_counts': dict(approved_counts), 'counts': counts, 'fetched_rows': loaded, 'sent_rows': dict(sent_rows), 'chunks': len(digests),
        'fetched_at': progress['fetched_at'], 'sent_at': progress.get('sent_at'),
        'body_bytes': body_length, 'fetch_seconds': round(fetch_seconds, 3), 'transfer_seconds': round(timing.get('send_seconds', total_seconds), 3),
        'launcher_seconds': round(total_seconds - timing.get('send_seconds', total_seconds), 3),
        'code_sha256': hashlib.sha256(code.encode('utf-8')).hexdigest(), 'http_status': status, 'cleanup': dict(cleanup),
    }
    # 投入後の照合: コンテナへ投入された行数が、Djangoが送った行数と一致しない結果は採用しない
    if launcher.get('status') == 'ok':
        rows_loaded = (launcher.get('diagnostics') or {}).get('rows_loaded')
        if rows_loaded != counts:
            return {'status': 'failed', 'reason': 'load_count_mismatch', 'launcher': {k: v for k, v in launcher.items() if k != 'result'}, 'fetch': record}
    return {'status': launcher.get('status'), 'launcher': launcher, 'fetch': record}
