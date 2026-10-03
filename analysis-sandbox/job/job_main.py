"""ジョブ用コンテナの監督プロセス(PID 1)。信頼するコードであり、生成コードは別プロセス(runtime.py)で実行する。

流れ: stdinでフレームを受信 → 件数を照合して一時DuckDBへ投入 → 生成コードを子プロセスで実行 →
結果を検証し、完結した1つのメッセージとしてstdoutへ出力する。
結果を採用してよいのは、出力が完結(終端マーカー・長さ・SHA-256)し、OOM・強制終了・上限超過がない場合だけ。
"""
import ctypes
import hashlib
import json
import os
import re
import signal
import struct
import subprocess
import sys
import threading
import time

# 検証用の暫定値(BOSS承認前)。上限を超えた場合は切り捨てずに失敗にする(ログだけは欠落を明示して切り捨てる)。
MAX_FRAME_BYTES = 32 * 1024 * 1024
MAX_CODE_BYTES = 64 * 1024
MAX_RESULT_BYTES = 5 * 1024 * 1024
MAX_TABLE_ROWS = 10_000
MAX_LOG_BYTES = 64 * 1024

CHART_KINDS = {'bar', 'line'}
NAME_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,62}$')
COLUMN_TYPES = {'BIGINT', 'INTEGER', 'DOUBLE', 'DECIMAL(18,3)', 'VARCHAR', 'DATE', 'TIMESTAMP', 'BOOLEAN'}
NULL_MARK = '\\N'
OOM_EVENTS = '/sys/fs/cgroup/memory.events'
CHUNK_PATH = '/tmp/chunk.csv'  # 投入中の1チャンクだけを置く一時ファイル(投入後に削除する)
MAX_CHUNK_ROWS = 5_000  # 1チャンクの行数の上限(分割サイズ。検証用の暫定値)。これを超えるフレームは拒否する
DB_PATH = '/tmp/job.duckdb'
META_PATH = '/tmp/job_meta.json'
CODE_PATH = '/tmp/user_code.py'
RESULT_PATH = '/tmp/result.json'


class JobFailed(Exception):
    def __init__(self, reason, detail=''):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


def set_undumpable():
    """/proc/<pid>/mem・environ・ptraceを、同じUIDの子プロセスから使えなくする。"""
    ctypes.CDLL(None).prctl(4, 0, 0, 0, 0)  # PR_SET_DUMPABLE = 4


def read_oom_kills():
    """cgroupのoom_kill回数。読めない場合は、判定できないため失敗にする(Noneを返す)。"""
    try:
        with open(OOM_EVENTS, encoding='ascii') as handle:
            for line in handle:
                key, value = line.split()
                if key == 'oom_kill':
                    return int(value)
    except (OSError, ValueError):
        return None
    return 0


def read_exact(stream, size):
    data = b''
    while len(data) < size:
        chunk = stream.read(size - len(data))
        if not chunk:
            raise JobFailed('input_truncated', '入力フレームが途中で終了しました。')
        data += chunk
    return data


def read_frame(stream):
    """フレーム: 種別1バイト + 長さ4バイト(BE) + 本文。H=ヘッダJSON、D=データ(view番号2B + 行数4B + CSV)、E=終端。"""
    kind = read_exact(stream, 1)
    (length,) = struct.unpack('>I', read_exact(stream, 4))
    if length > MAX_FRAME_BYTES:
        raise JobFailed('frame_too_large', f'{length}バイト')
    return kind, read_exact(stream, length)


def notify_state(name):
    """状態の切替(transfer=受信待ち、load=投入・照合、python=生成コードの実行)を、監督プロセスのstderrへ通知する。

    launcherが、状態ごとの時間を積算して、各段階の期限(各段階全体の予算)を判定する。生成コードのstderrは別のパイプ。
    """
    sys.stderr.write(f'PMSTATE {name}\n')
    sys.stderr.flush()


def validate_header(header):
    code = header.get('code')
    if not isinstance(code, str) or len(code.encode('utf-8')) > MAX_CODE_BYTES:
        raise JobFailed('code_invalid', f'生成コードは{MAX_CODE_BYTES}バイト以内の文字列にしてください。')
    limits = header.get('limits') or {}
    for key in ('python_seconds', 'duckdb_memory_limit_mb', 'threads'):
        if type(limits.get(key)) is not int or limits[key] < 1:
            raise JobFailed('header_invalid', f'limits.{key}が不正です。')
    for view in header.get('views') or []:
        if not NAME_PATTERN.match(str(view.get('name', ''))) or type(view.get('expected_rows')) is not int:
            raise JobFailed('header_invalid', 'ビュー定義が不正です。')
        for column in view.get('columns') or []:
            if not NAME_PATTERN.match(str(column.get('name', ''))) or column.get('type') not in COLUMN_TYPES:
                raise JobFailed('header_invalid', '列定義が不正です。')
        key = view.get('unique_key')
        if key is not None and key not in [c['name'] for c in view['columns']]:
            raise JobFailed('header_invalid', '一意キーが列にありません。')


def receive_and_load(stream):
    """ヘッダ(H)を受け取って表を作り、データ(D)は、1チャンク受信するたびにDuckDBへ順次投入する。

    本文全体は、メモリにも一時領域にも溜めない(一時領域に置くのは、投入中の1チャンクだけ)。
    チャンクごとに、申告された行数と投入された行数を照合し、終端(E)の後に、ビューごとの総件数と一意キーを照合する。
    1つでも合わなければ、失敗にする。
    """
    import duckdb

    notify_state('transfer')
    kind, payload = read_frame(stream)
    if kind != b'H':
        raise JobFailed('protocol_error', '先頭フレームがヘッダではありません。')
    try:
        header = json.loads(payload.decode('utf-8'))
    except ValueError as exc:
        raise JobFailed('header_invalid', 'ヘッダを解析できません。') from exc
    notify_state('load')
    validate_header(header)
    views = header['views']
    connection = duckdb.connect(DB_PATH, config={
        'memory_limit': f"{header['limits']['duckdb_memory_limit_mb']}MB", 'threads': header['limits']['threads'],
    })
    loaded = [0] * len(views)
    try:
        for view in views:
            columns = ', '.join(f'"{c["name"]}" {c["type"]}' for c in view['columns'])
            connection.execute(f'CREATE TABLE "{view["name"]}" ({columns})')
        while True:
            notify_state('transfer')
            kind, payload = read_frame(stream)
            if kind == b'E':
                break
            if kind != b'D':
                raise JobFailed('protocol_error', '不明なフレーム種別です。')
            notify_state('load')
            if len(payload) < 6:
                raise JobFailed('protocol_error', 'データフレームが短すぎます。')
            index, rows = struct.unpack('>HI', payload[:6])
            if index >= len(views):
                raise JobFailed('protocol_error', 'ビュー番号が不正です。')
            if rows > MAX_CHUNK_ROWS:
                raise JobFailed('chunk_too_large', f'1チャンクは{MAX_CHUNK_ROWS}行までです({rows}行)。')
            name = views[index]['name']
            with open(CHUNK_PATH, 'wb') as handle:
                handle.write(payload[6:])
            connection.execute(f"COPY \"{name}\" FROM '{CHUNK_PATH}' (FORMAT csv, HEADER false, NULLSTR '{NULL_MARK}')")
            os.remove(CHUNK_PATH)
            count = connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            if count - loaded[index] != rows:
                raise JobFailed('chunk_row_count_mismatch', f'{name}: 申告{rows}行 / 投入{count - loaded[index]}行')
            loaded[index] = count
            if count > views[index]['expected_rows']:
                raise JobFailed('row_count_exceeded', f'{name}: 期待{views[index]["expected_rows"]}行を超えました。')
        notify_state('load')
        result = {}
        for index, view in enumerate(views):
            name = view['name']
            if loaded[index] != view['expected_rows']:
                raise JobFailed('row_count_mismatch', f'{name}: 受信{loaded[index]}行 / 期待{view["expected_rows"]}行')
            key = view.get('unique_key')
            if key is not None:
                distinct = connection.execute(f'SELECT COUNT(DISTINCT "{key}") FROM "{name}"').fetchone()[0]
                if distinct != loaded[index]:
                    raise JobFailed('duplicate_key', f'{name}: {key}に重複があります。')
            result[name] = loaded[index]
    finally:
        connection.close()
    return header, result


def kill_everything_else():
    """生成コードが残したプロセスをすべて終了する(PID名前空間内の自分以外)。"""
    me = os.getpid()
    for name in os.listdir('/proc'):
        if name.isdigit() and int(name) != me:
            try:
                os.kill(int(name), signal.SIGKILL)
            except OSError:
                pass


class CappedReader(threading.Thread):
    """子プロセスの出力を、上限まで保持する。超過分は捨てて、欠落を明示する(結果ではなくログ用)。"""

    def __init__(self, pipe):
        super().__init__(daemon=True)
        self.pipe = pipe
        self.data = b''
        self.truncated = False

    def run(self):
        while True:
            chunk = self.pipe.read(4096)
            if not chunk:
                return
            room = MAX_LOG_BYTES - len(self.data)
            if room > 0:
                self.data += chunk[:room]
            if len(chunk) > room:
                self.truncated = True


def run_user_code(header):
    with open(CODE_PATH, 'w', encoding='utf-8') as handle:
        handle.write(header['code'])
    with open(META_PATH, 'w', encoding='utf-8') as handle:
        json.dump({'views': [v['name'] for v in header['views']],
                   'duckdb_memory_limit_mb': header['limits']['duckdb_memory_limit_mb'],
                   'threads': header['limits']['threads']}, handle)
    # 子の標準出力・エラー出力はパイプで受け取り、監督プロセスのstdout(結果の出力先)には繋がない。
    child = subprocess.Popen(
        [sys.executable, '-I', '/job/runtime.py'], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, close_fds=True, start_new_session=True, cwd='/tmp',
        env={'PATH': os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')},
    )
    stdout_reader, stderr_reader = CappedReader(child.stdout), CappedReader(child.stderr)
    stdout_reader.start()
    stderr_reader.start()
    timed_out = False
    try:
        child.wait(timeout=header['limits']['python_seconds'])
    except subprocess.TimeoutExpired:
        timed_out = True
    kill_everything_else()
    child.wait()
    stderr_reader.join(2)
    stdout_reader.join(2)
    return child.returncode, timed_out, stderr_reader


def load_result():
    """子が書いた結果は信頼せず、構造と上限を検証する。上限超過は切り捨てずに失敗にする。"""
    if not os.path.exists(RESULT_PATH):
        raise JobFailed('result_missing', '結果ファイルがありません。')
    size = os.path.getsize(RESULT_PATH)
    if size > MAX_RESULT_BYTES:
        raise JobFailed('result_too_large', f'{size}バイト(上限{MAX_RESULT_BYTES})')
    with open(RESULT_PATH, 'rb') as handle:
        raw = handle.read()
    try:
        result = json.loads(raw.decode('utf-8'), parse_constant=reject_constant)
        validate_result(result)
    except (ValueError, TypeError, KeyError) as exc:
        raise JobFailed('result_invalid', str(exc)) from exc
    return raw


def reject_constant(name):
    """NaN・Infinityは、標準のJSONではなく、画面で扱えないため拒否する。"""
    raise ValueError(f'JSONにない値です: {name}')


def is_scalar(value):
    return value is None or isinstance(value, (bool, int, float, str))


def validate_result(result):
    """結果の型を、表・グラフ・報告書のすべてについて厳密に検証する。1つでも不正なら、結果全体を採用しない。"""
    if type(result) is not dict or set(result) != {'tables', 'charts', 'report'}:
        raise ValueError('結果の構造が不正です。')
    if type(result['tables']) is not list or type(result['charts']) is not list:
        raise ValueError('tablesとchartsは配列にしてください。')
    if result['report'] is not None and type(result['report']) is not str:
        raise ValueError('reportは文字列またはnullにしてください。')
    for table in result['tables']:
        if type(table) is not dict or set(table) != {'name', 'columns', 'rows'}:
            raise ValueError('表の構造が不正です。')
        if type(table['name']) is not str or type(table['columns']) is not list or type(table['rows']) is not list:
            raise ValueError('表の名前・列・行の型が不正です。')
        if any(type(column) is not str for column in table['columns']):
            raise ValueError('表の列名は文字列にしてください。')
        if len(table['rows']) > MAX_TABLE_ROWS:
            raise ValueError(f'表の行数が上限({MAX_TABLE_ROWS})を超えています。')
        for row in table['rows']:
            if type(row) is not list or len(row) != len(table['columns']) or not all(is_scalar(v) for v in row):
                raise ValueError('表の行の列数または値の型が不正です。')
    for chart in result['charts']:
        if type(chart) is not dict or set(chart) != {'kind', 'title', 'x', 'series'}:
            raise ValueError('グラフの構造が不正です。')
        if chart['kind'] not in CHART_KINDS or type(chart['title']) is not str:
            raise ValueError('グラフの種類(bar・line)またはタイトルが不正です。')
        if type(chart['x']) is not list or not all(is_scalar(v) for v in chart['x']):
            raise ValueError('グラフのxは、値の配列にしてください。')
        if type(chart['series']) is not list:
            raise ValueError('グラフのseriesは配列にしてください。')
        for series in chart['series']:
            if type(series) is not dict or set(series) != {'name', 'values'} or type(series['name']) is not str:
                raise ValueError('グラフの系列の構造が不正です。')
            if type(series['values']) is not list or len(series['values']) != len(chart['x']) \
                    or not all(is_scalar(v) for v in series['values']):
                raise ValueError('グラフの系列の値の個数・型が、xと一致しません。')


def emit(status, body=b'', **meta):
    """完結した1つのメッセージ: PMRESULT1 + ヘッダ(長さ・SHA-256) + 本文 + 終端マーカー。"""
    header = {'status': status, 'length': len(body), 'sha256': hashlib.sha256(body).hexdigest(), **meta}
    out = sys.stdout.buffer
    out.write(b'PMRESULT1\n' + json.dumps(header, ensure_ascii=False).encode('utf-8') + b'\n' + body + b'\nPMEND\n')
    out.flush()


def main():
    set_undumpable()
    started = time.monotonic()
    diagnostics = {'oom_kill': None}
    baseline = read_oom_kills()
    try:
        if baseline is None:
            raise JobFailed('oom_status_unavailable', 'cgroupのOOM情報を読めないため、実行しません。')
        header, loaded = receive_and_load(sys.stdin.buffer)
        prepared = time.monotonic()
        notify_state('python')
        code, timed_out, stderr_reader = run_user_code(header)
        finished = time.monotonic()
        oom_after = read_oom_kills()
        diagnostics.update({
            'oom_kill': None if oom_after is None else oom_after - baseline, 'rows_loaded': loaded,
            'seconds': {'receive_and_load': round(prepared - started, 3), 'python': round(finished - prepared, 3)},
            'stderr': stderr_reader.data.decode('utf-8', 'replace'), 'stderr_truncated': stderr_reader.truncated,
        })
        if oom_after is None or oom_after != baseline:
            raise JobFailed('oom_killed', 'メモリ上限でプロセスが終了されました。結果は採用しません。')
        if timed_out:
            raise JobFailed('timeout', f"Python実行が{header['limits']['python_seconds']}秒を超えました。")
        if code != 0:
            reason = f'killed_by_signal_{-code}' if code < 0 else 'child_exit_nonzero'
            raise JobFailed(reason, f'終了コード{code}')
        body = load_result()
        emit('ok', body, **diagnostics)
        return 0
    except JobFailed as failure:
        emit('failed', b'', reason=failure.reason, detail=failure.detail, **diagnostics)
        return 3
    except BaseException as exc:  # 想定外の例外も、結果を出さずに失敗として報告する
        emit('failed', b'', reason='supervisor_error', detail=f'{type(exc).__name__}: {exc}'[:300], **diagnostics)
        return 3


if __name__ == '__main__':
    sys.exit(main())
