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

NAME_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,62}$')
COLUMN_TYPES = {'BIGINT', 'INTEGER', 'DOUBLE', 'DECIMAL(18,3)', 'VARCHAR', 'DATE', 'TIMESTAMP', 'BOOLEAN'}
NULL_MARK = '\\N'
OOM_EVENTS = '/sys/fs/cgroup/memory.events'
DATA_DIR = '/tmp/data'
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


def receive(stream):
    """フレーム: 種別1バイト + 長さ4バイト(BE) + 本文。H=ヘッダJSON、D=データ(view番号2B + 行数4B + CSV)、E=終端。"""
    header = None
    rows_seen = {}
    os.makedirs(DATA_DIR, mode=0o700, exist_ok=True)
    while True:
        kind = read_exact(stream, 1)
        (length,) = struct.unpack('>I', read_exact(stream, 4))
        if length > MAX_FRAME_BYTES:
            raise JobFailed('frame_too_large', f'{length}バイト')
        payload = read_exact(stream, length)
        if kind == b'H':
            if header is not None:
                raise JobFailed('protocol_error', 'ヘッダが重複しています。')
            header = json.loads(payload.decode('utf-8'))
        elif kind == b'D':
            if header is None:
                raise JobFailed('protocol_error', 'ヘッダより前にデータが届きました。')
            index, rows = struct.unpack('>HI', payload[:6])
            if index >= len(header['views']):
                raise JobFailed('protocol_error', 'ビュー番号が不正です。')
            with open(f'{DATA_DIR}/{index}.csv', 'ab') as handle:
                handle.write(payload[6:])
            rows_seen[index] = rows_seen.get(index, 0) + rows
        elif kind == b'E':
            break
        else:
            raise JobFailed('protocol_error', '不明なフレーム種別です。')
    if header is None:
        raise JobFailed('protocol_error', 'ヘッダがありません。')
    return header, rows_seen


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


def prepare(header, rows_seen):
    """受信件数と投入後の件数・一意キーを照合し、不一致なら失敗にする。"""
    import duckdb

    connection = duckdb.connect(DB_PATH, config={
        'memory_limit': f"{header['limits']['duckdb_memory_limit_mb']}MB", 'threads': header['limits']['threads'],
    })
    loaded = {}
    try:
        for index, view in enumerate(header['views']):
            name = view['name']
            if rows_seen.get(index, 0) != view['expected_rows']:
                raise JobFailed('row_count_mismatch', f'{name}: 受信{rows_seen.get(index, 0)}行 / 期待{view["expected_rows"]}行')
            columns = ', '.join(f'"{c["name"]}" {c["type"]}' for c in view['columns'])
            connection.execute(f'CREATE TABLE "{name}" ({columns})')
            path = f'{DATA_DIR}/{index}.csv'
            if os.path.exists(path):
                connection.execute(f"COPY \"{name}\" FROM '{path}' (FORMAT csv, HEADER false, NULLSTR '{NULL_MARK}')")
            count = connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            if count != view['expected_rows']:
                raise JobFailed('insert_count_mismatch', f'{name}: 投入{count}行 / 期待{view["expected_rows"]}行')
            key = view.get('unique_key')
            if key is not None:
                distinct = connection.execute(f'SELECT COUNT(DISTINCT "{key}") FROM "{name}"').fetchone()[0]
                if distinct != count:
                    raise JobFailed('duplicate_key', f'{name}: {key}に重複があります。')
            loaded[name] = count
    finally:
        connection.close()
    return loaded


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
        result = json.loads(raw.decode('utf-8'))
        if not isinstance(result, dict) or set(result) != {'tables', 'charts', 'report'}:
            raise ValueError('構造が不正です。')
        for table in result['tables']:
            if set(table) != {'name', 'columns', 'rows'} or len(table['rows']) > MAX_TABLE_ROWS:
                raise ValueError('表が不正、または行数が上限を超えています。')
            if any(len(row) != len(table['columns']) for row in table['rows']):
                raise ValueError('表の列数が一致しません。')
    except (ValueError, TypeError, KeyError) as exc:
        raise JobFailed('result_invalid', str(exc)) from exc
    return raw


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
        header, rows_seen = receive(sys.stdin.buffer)
        validate_header(header)
        received = time.monotonic()
        loaded = prepare(header, rows_seen)
        prepared = time.monotonic()
        code, timed_out, stderr_reader = run_user_code(header)
        finished = time.monotonic()
        oom_after = read_oom_kills()
        diagnostics.update({
            'oom_kill': None if oom_after is None else oom_after - baseline, 'rows_loaded': loaded,
            'seconds': {'receive': round(received - started, 3), 'prepare': round(prepared - received, 3),
                        'python': round(finished - prepared, 3)},
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
