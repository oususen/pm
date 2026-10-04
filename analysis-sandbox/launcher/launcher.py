"""開発専用launcher。1ジョブ=1コンテナで、Dockerを操作するのはこのプロセスだけ。

- 承認範囲: 開発での検証に限定する(本番は別途判断)。DockerソケットはLinuxのroot相当の権限なので、
  このプロセスはDjango・生成コードから分離し、スキーマ検証したジョブだけを受け付ける。
- 隔離が確認できない場合は実行しない(fail-closed): 起動時・各ジョブ前にpreflight、コンテナ作成後にinspectで完全照合する。
- データは分割転送する: 本文全体をメモリに保持せず、フレーム(ヘッダ→5,000行単位のチャンク→終端)を受信するたびに
  コンテナへ流し、コンテナ内でも、チャンクごとにDuckDBへ順次投入する。
- 結果を採用するのは、終了コード0・OOMなし・期限内・出力が完結・件数照合済みの場合だけ。それ以外は結果を全て破棄する。
- 稼働中のジョブは削除しない: launcherは単一インスタンスで、起動時の掃除は、前のlauncherが残した孤児(別のlauncher IDの
  ラベルを持つコンテナ)だけを対象にする。
"""
import csv
import hashlib
import io
import itertools
import json
import math
import os
import re
import secrets
import socket
import struct
import subprocess
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

IMAGE = os.environ.get('ANALYSIS_JOB_IMAGE', 'pm-analysis-job:dev')
LABEL = 'pm.analysis.job'
OWNER_LABEL = 'pm.analysis.launcher'
LAUNCHER_ID = uuid.uuid4().hex[:12]  # このlauncherプロセスのID。ジョブ用コンテナに付け、孤児との区別に使う。
NULL_MARK = '\\N'

# 検証用の暫定値(BOSS承認前)。
TMPFS_MB = 128
TMPFS_OPTIONS = f'rw,noexec,nosuid,nodev,size={TMPFS_MB}m,uid=10001,gid=10001,mode=0700'
SHM_BYTES = 64 * 1024 * 1024  # Dockerの既定。/dev/shmも、メモリに数えられるため、拡大を許さない
PIDS_LIMIT = 128
MAX_RESULT_BYTES = 5 * 1024 * 1024
MAX_STDOUT_BYTES = MAX_RESULT_BYTES + 256 * 1024  # 結果 + ヘッダ + 診断情報(stderr 64KBなど)
MAX_REQUEST_BYTES = 64 * 1024 * 1024
MAX_FRAME_BYTES = 32 * 1024 * 1024
STAGE_DEADLINES = {'transfer': 60, 'load': 60, 'margin': 20}
# 分析実行設定(設定画面)の保存可能範囲と同じ。テストだけが、小さい値を使うために別の範囲を渡す。
PRODUCTION_RANGES = {'memory_mb': (512, 4096), 'cpus': (0.5, 2.0), 'python_seconds': (30, 600)}


class IsolationUnavailable(Exception):
    """隔離機能が確認できない。実行を無効にする。"""


class Busy(Exception):
    pass


class ResultRejected(Exception):
    pass


class TransferTimeout(Exception):
    """データの転送(受信)が、期限内に終わらなかった。"""


class InvalidInput(Exception):
    """リクエスト本文の構造が不正。"""


def docker(*args, timeout=60, check=True, input_text=None):
    """dockerコマンドを実行する。時間切れは例外にせず、checkなしなら終了コード124として返す(ロックを残さないため)。"""
    try:
        result = subprocess.run(['docker', *args], capture_output=True, text=True, timeout=timeout, input=input_text)
    except subprocess.TimeoutExpired:
        if check:
            raise IsolationUnavailable(f'docker {args[0]}が{timeout}秒以内に終わりませんでした。')
        return subprocess.CompletedProcess(['docker', *args], 124, '', 'timeout')
    if check and result.returncode != 0:
        raise IsolationUnavailable(f'docker {args[0]}に失敗しました: {result.stderr.strip()[:200]}')
    return result


def pinned_image_id():
    value = os.environ.get('ANALYSIS_JOB_IMAGE_ID')
    path = Path(__file__).resolve().parent.parent / '.image-id'
    if not value and path.exists():
        value = path.read_text(encoding='ascii').strip()
    if not value:
        raise IsolationUnavailable('固定したジョブ用イメージのIDが未設定です(build.pyで作成してください)。')
    return value


def preflight(info=None):
    """隔離に必要な機能を確認する。1つでも満たせなければ、実行を無効にする。"""
    if info is None:
        info = json.loads(docker('info', '--format', '{{json .}}').stdout)
    if str(info.get('CgroupVersion')) != '2':
        raise IsolationUnavailable('cgroup v2でないため、メモリ・CPU・プロセス数をジョブごとに強制できません。')
    if not any('seccomp' in str(option) for option in info.get('SecurityOptions') or []):
        raise IsolationUnavailable('Dockerのseccompが有効ではありません。')
    expected = pinned_image_id()
    actual = docker('image', 'inspect', IMAGE, '--format', '{{.Id}}').stdout.strip()
    if actual != expected:
        raise IsolationUnavailable('ジョブ用イメージが、固定したイメージと一致しません。')
    # 実際に小さなコンテナを起動し、メモリ・CPU・プロセス数がcgroupへ反映されることをコンテナ内から確認する。
    probe = (
        "print(open('/sys/fs/cgroup/memory.max').read().strip(),"
        "open('/sys/fs/cgroup/cpu.max').read().strip(),open('/sys/fs/cgroup/pids.max').read().strip())"
    )
    output = docker(
        'run', '--rm', '--network', 'none', '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
        '--user', '10001:10001', '--memory', '64m', '--memory-swap', '64m', '--cpus', '0.5', '--pids-limit', '16',
        '--entrypoint', 'python', IMAGE, '-I', '-c', probe, timeout=60,
    ).stdout.split()
    if output != [str(64 * 1024 * 1024), '50000', '100000', '16']:
        raise IsolationUnavailable(f'cgroupの制限が反映されていません: {output}')
    return {'docker': info.get('ServerVersion'), 'cgroup': '2', 'image': actual}


def validate_limits(limits, ranges):
    memory, cpus, seconds = limits.get('memory_mb'), limits.get('cpus'), limits.get('python_seconds')
    if type(memory) is not int or not ranges['memory_mb'][0] <= memory <= ranges['memory_mb'][1]:
        raise IsolationUnavailable('memory_mbが範囲外です。')
    if type(cpus) not in (int, float) or not ranges['cpus'][0] <= cpus <= ranges['cpus'][1] or (cpus * 2) % 1:
        raise IsolationUnavailable('cpusが範囲外、または0.5コア単位ではありません。')
    if type(seconds) is not int or not ranges['python_seconds'][0] <= seconds <= ranges['python_seconds'][1]:
        raise IsolationUnavailable('python_secondsが範囲外です。')
    if limits.get('threads') != math.ceil(cpus):
        raise IsolationUnavailable('threadsは、cpusの切り上げにしてください。')


def create_command(name, limits):
    memory = f"{limits['memory_mb']}m"
    return [
        'create', '-i', '--name', name, '--label', f'{LABEL}=1', '--label', f'{OWNER_LABEL}={LAUNCHER_ID}',
        '--network', 'none', '--read-only', '--tmpfs', f'/tmp:{TMPFS_OPTIONS}',
        '--memory', memory, '--memory-swap', memory, '--cpus', str(limits['cpus']), '--pids-limit', str(PIDS_LIMIT),
        '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--user', '10001:10001', '--log-driver', 'none', IMAGE,
    ]


def verify_container(inspected, limits, image_id, image_env):
    """作成したコンテナの設定を、期待値と完全に照合する。1つでも違えば、起動しない。"""
    host, config = inspected['HostConfig'], inspected['Config']
    problems = []

    def expect(label, actual, wanted):
        if actual != wanted:
            problems.append(f'{label}: {actual!r}(期待 {wanted!r})')

    memory = limits['memory_mb'] * 1024 * 1024
    expect('image', inspected.get('Image'), image_id)
    expect('network', host.get('NetworkMode'), 'none')
    expect('readonly_rootfs', host.get('ReadonlyRootfs'), True)
    expect('privileged', host.get('Privileged'), False)
    expect('memory', host.get('Memory'), memory)
    expect('memory_swap', host.get('MemorySwap'), memory)
    expect('cpus', host.get('NanoCpus'), int(limits['cpus'] * 1_000_000_000))
    expect('pids', host.get('PidsLimit'), PIDS_LIMIT)
    expect('cap_drop', host.get('CapDrop'), ['ALL'])
    expect('cap_add', host.get('CapAdd') or [], [])
    expect('no_new_privileges', [str(o).split(':')[0] for o in host.get('SecurityOpt') or []], ['no-new-privileges'])
    expect('user', config.get('User'), '10001:10001')
    expect('binds', host.get('Binds') or [], [])
    expect('mounts', inspected.get('Mounts') or [], [])
    expect('devices', host.get('Devices') or [], [])
    expect('ports', host.get('PortBindings') or {}, {})
    expect('pid_mode', host.get('PidMode') or '', '')
    expect('ipc_mode', host.get('IpcMode'), 'private')
    expect('userns_mode', host.get('UsernsMode') or '', '')
    expect('oom_kill_disable', bool(host.get('OomKillDisable')), False)
    expect('env', sorted(config.get('Env') or []), sorted(image_env))
    expect('label', (config.get('Labels') or {}).get(LABEL), '1')
    expect('owner_label', (config.get('Labels') or {}).get(OWNER_LABEL), LAUNCHER_ID)
    # 一時領域は、場所だけでなく、容量・実行禁止・setuid禁止・デバイス禁止・所有者・権限まで完全に照合する。
    tmpfs = host.get('Tmpfs') or {}
    expect('tmpfs_mounts', sorted(tmpfs), ['/tmp'])
    expect('tmpfs_options', sorted((tmpfs.get('/tmp') or '').split(',')), sorted(TMPFS_OPTIONS.split(',')))
    expect('shm_size', host.get('ShmSize'), SHM_BYTES)
    expect('sysctls', host.get('Sysctls') or {}, {})
    expect('ulimits', host.get('Ulimits') or [], [])
    expect('volumes_from', host.get('VolumesFrom') or [], [])
    expect('runtime', host.get('Runtime'), 'runc')
    expect('storage_opt', host.get('StorageOpt') or {}, {})
    if problems:
        raise IsolationUnavailable('隔離条件を確認できないため実行しません: ' + '; '.join(problems))


def parse_result_stream(raw):
    """出力は、完結した1つのメッセージ(先頭・長さ・SHA-256・終端)だけを受け入れる。"""
    magic, end = b'PMRESULT1\n', b'\nPMEND\n'
    if not raw.startswith(magic):
        raise ResultRejected('出力の先頭が不正です。')
    rest = raw[len(magic):]
    newline = rest.find(b'\n')
    if newline < 0:
        raise ResultRejected('ヘッダが途中で終わっています。')
    try:
        header = json.loads(rest[:newline].decode('utf-8'))
        length = header['length']
    except (ValueError, KeyError, UnicodeDecodeError) as exc:
        raise ResultRejected('ヘッダを解析できません。') from exc
    body, tail = rest[newline + 1:newline + 1 + length], rest[newline + 1 + length:]
    if len(body) != length or tail != end:
        raise ResultRejected('出力が途中で終了、または余分なデータがあります(終端マーカーなし)。')
    if hashlib.sha256(body).hexdigest() != header.get('sha256'):
        raise ResultRejected('SHA-256が一致しません。')
    return header, body


class StageClock:
    """段階ごとの期限を、各段階の全体の予算として判定する。チャンクの到着などでリセットしない。

    transfer: データの受信を待っている時間の合計(HTTP本文の受信の開始から数え、HTTP・launcherでの待ちを含む)。
    load: DuckDBへの投入・件数と一意キーの照合に費やした時間の合計。
    python: 生成コードの実行時間(Python実行時間 + 余裕)。
    転送と投入は、チャンクごとに交互に進む(順次投入)ため、監督プロセスが状態の切替(PMSTATE)を通知し、
    launcherが自分の時計で、状態ごとの時間を積算する。
    """

    def __init__(self, transfer_started, deadlines, python_seconds, control=None):
        self._lock = threading.Lock()
        self.used = {'transfer': 0.0, 'load': 0.0}
        self.state, self.since = 'transfer', transfer_started
        self.deadlines, self.python_seconds = deadlines, python_seconds
        self.control = control

    def switch(self, name, now):
        with self._lock:
            if self.state in self.used:
                self.used[self.state] += now - self.since
            self.state, self.since = name, now
            if self.control is not None:
                self.control.stage = name

    def violation(self, now):
        with self._lock:
            if self.state in self.used:
                if self.used[self.state] + (now - self.since) > self.deadlines[self.state]:
                    return f'stage_deadline_{self.state}'
            elif self.state == 'python' and now - self.since > self.python_seconds + self.deadlines['margin']:
                return 'stage_deadline_python'
        return None


def evaluate(stdout, state, kill_reason, overflow):
    """結果を採用してよいかを判定する。OOM・強制終了・不完全な出力・上限超過では、途中の結果も採用しない。"""
    container = {'exit_code': state.get('ExitCode'), 'oom_killed': bool(state.get('OOMKilled'))}

    def failed(reason, detail='', diagnostics=None):
        return {'status': 'failed', 'reason': reason, 'detail': detail, 'container': container, 'diagnostics': diagnostics or {}}

    # 判定の前に、可能なら診断情報(OOM回数など)を取り出す。結果は、下の判定をすべて通るまで採用しない。
    try:
        header, body = parse_result_stream(stdout)
        diagnostics = {k: v for k, v in header.items() if k not in ('status', 'length', 'sha256')}
        parse_error = None
    except ResultRejected as exc:
        header, body, diagnostics, parse_error = {}, b'', {}, exc
    if kill_reason:
        return failed(kill_reason if isinstance(kill_reason, str) else 'launcher_deadline',
                      '期限を超えたため、コンテナを強制終了しました。', diagnostics)
    if overflow:
        return failed('output_too_large', 'コンテナの出力が上限を超えました。', diagnostics)
    if state.get('OOMKilled'):
        return failed('container_oom_killed', 'コンテナ内のプロセスがメモリ上限で終了されました。', diagnostics)
    if parse_error is not None:
        return failed('incomplete_or_corrupt_output', str(parse_error))
    if header.get('status') != 'ok':
        return failed(header.get('reason', 'job_failed'), header.get('detail', ''), diagnostics)
    if state.get('ExitCode') != 0:
        return failed('exit_code_nonzero', f"終了コード{state.get('ExitCode')}", diagnostics)
    if header.get('oom_kill') != 0:
        return failed('oom_killed', 'ジョブ内でOOMによる終了がありました。', diagnostics)
    if len(body) > MAX_RESULT_BYTES:
        return failed('result_too_large', '', diagnostics)
    return {'status': 'ok', 'result': json.loads(body.decode('utf-8')), 'container': container, 'diagnostics': diagnostics}


_LOCK = threading.Lock()
_ACTIVE = set()  # このlauncherが、いま実行中のジョブ用コンテナ名。掃除の対象にしない。
_PENDING_CLEANUP = set()  # 削除に失敗したコンテナ。解消するまで、新しいジョブを受け付けない(fail-closed)。
_CONTROL_LOCK = threading.Lock()
_CONTROL = None  # 現在または直前の1件だけ。コンテナ名をHTTP入力から受け取らない。


class JobControl:
    def __init__(self, job_id, token, connection):
        self.job_id, self.token, self.connection = job_id, token, connection
        self.cancel = threading.Event()
        self.done = False
        self.cleanup = None
        self.stage = 'transfer'

    def request_cancel(self):
        with _CONTROL_LOCK:
            if self.done:
                return False
            self.cancel.set()
            # 不完全な本文の受信待ちも止める。応答の送信側は閉じない。
            try:
                self.connection.shutdown(socket.SHUT_RD)
            except OSError:
                pass
            return True


def find_control(job_id, token):
    if not isinstance(token, str) or not token.isascii():
        return None
    with _CONTROL_LOCK:
        if _CONTROL is not None and _CONTROL.job_id == job_id and secrets.compare_digest(_CONTROL.token, token):
            return _CONTROL
    return None


def remove_container(name):
    """コンテナを削除する。時間切れ・失敗でも例外にせず、成否を返す。存在しなければ成功とみなす。"""
    try:
        result = docker('rm', '-f', name, check=False)
    except Exception:  # dockerコマンドが実行できない場合も、ロックを残さず失敗として扱う
        return False
    return result.returncode == 0 or 'No such container' in (result.stderr or '')


def retry_pending_cleanup():
    """前回削除できなかったコンテナを、削除し直す。まだ残っているものを返す。"""
    for name in list(_PENDING_CLEANUP):
        if remove_container(name):
            _PENDING_CLEANUP.discard(name)
    return sorted(_PENDING_CLEANUP)


def sweep_leftovers():
    """前のlauncherが異常終了して残した孤児(別のlauncher IDのラベルを持つ、またはラベルがないコンテナ)だけを削除する。

    このlauncherが管理しているコンテナ(実行中のジョブ、削除待ち)は削除しない。launcherは単一インスタンス
    (acquire_single_instance_lock)なので、別のlauncher IDのコンテナは、停止済みのlauncherのものである。
    """
    listed = docker('ps', '-a', '--filter', f'label={LABEL}=1', '--format',
                    '{{.Names}}\t{{.Label "' + OWNER_LABEL + '"}}', check=False)
    if listed.returncode != 0:  # 残骸の有無を確認できないまま、受付を始めない
        raise IsolationUnavailable('起動時の孤児の一覧を取得できません: ' + (listed.stderr or '').strip()[:200])
    removed = 0
    for line in listed.stdout.splitlines():
        name, _, owner = line.partition('\t')
        if not name or name in _ACTIVE or name in _PENDING_CLEANUP or owner == LAUNCHER_ID:
            continue
        if remove_container(name):
            removed += 1
        else:
            _PENDING_CLEANUP.add(name)  # 削除できない残骸がある間は、新しいジョブを受け付けない
    return removed


def acquire_single_instance_lock(path=None):
    """launcherを、1つのプロセスに限定する(複数だと、互いのジョブを孤児として掃除してしまうため)。返したハンドルを保持している間、有効。"""
    import fcntl

    handle = open(path or os.environ.get('ANALYSIS_LAUNCHER_LOCK', '/run/pm-analysis-launcher.lock'), 'w')
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        raise IsolationUnavailable('別のlauncherが稼働中です。launcherは1つだけ起動できます。') from exc
    return handle


def read_progress(stream, clock):
    """監督プロセスのstderr。PMSTATE行で状態の切替を知る(生成コードのstderrは別のパイプで、ここには届かない)。"""
    for line in iter(stream.readline, b''):
        text = line.decode('utf-8', 'replace').strip()
        if text.startswith('PMSTATE '):
            name = text.split(' ', 1)[1]
            if name in ('transfer', 'load', 'python'):
                clock.switch(name, time.monotonic())


def read_limited(stream, limit, sink):
    """出力を上限+1バイトまで読む。超過したらoverflowを立てる(後で強制終了する)。"""
    total = 0
    while True:
        chunk = stream.read(65536)
        if not chunk:
            return
        total += len(chunk)
        if total > limit:
            sink['overflow'] = True
            return
        sink['data'] += chunk


def frame(kind, payload):
    return kind + struct.pack('>I', len(payload)) + payload


def iter_frames(data):
    """バイト列を、フレームに分けて順に返す(テスト・小さな入力用)。"""
    offset = 0
    while offset < len(data):
        (size,) = struct.unpack('>I', data[offset + 1:offset + 5])
        yield data[offset:offset + 5 + size]
        offset += 5 + size


def iter_http_frames(read1, set_timeout, length, started, deadline):
    """HTTP本文を、1フレームずつ受信して返す。本文全体は保持しない(メモリは、最大でも1フレーム分)。

    期限は、受信を始めた時刻から数える全体の期限で、フレームの到着ではリセットしない。
    本文の長さ(Content-Length)とフレームの区切りが合わない場合は、不正な入力として拒否する。
    """
    remaining = length

    def read_n(count):
        data = b''
        while len(data) < count:
            left = started + deadline - time.monotonic()
            if left <= 0:
                raise TransferTimeout('転送の期限内に、本文を受信できませんでした。')
            set_timeout(left)
            try:
                piece = read1(min(count - len(data), 65536))
            except (TimeoutError, OSError) as exc:
                raise TransferTimeout('転送の期限内に、本文を受信できませんでした。') from exc
            if not piece:
                raise InvalidInput('本文が途中で終了しました。')
            data += piece
        return data

    while remaining > 0:
        if remaining < 5:
            raise InvalidInput('フレームの区切りが本文の長さと合いません。')
        head = read_n(5)
        (size,) = struct.unpack('>I', head[1:5])
        if size > MAX_FRAME_BYTES or 5 + size > remaining:
            raise InvalidInput('フレームの大きさが不正です。')
        payload = read_n(size) if size else b''
        remaining -= 5 + size
        yield head + payload


def header_from_frame(first):
    if first[:1] != b'H':
        raise InvalidInput('先頭フレームがヘッダではありません。')
    try:
        return json.loads(first[5:].decode('utf-8'))
    except ValueError as exc:
        raise InvalidInput('ヘッダを解析できません。') from exc


def run_job(source, ranges=PRODUCTION_RANGES, deadlines=None, info=None, transfer_started=None, control=None):
    """ジョブを1つ実行する。同時に実行できるのは1件だけ。どの経路でも、実行ロックは必ず解放する。

    source: フレームのバイト列、またはフレームを順に返すイテレータ(HTTPでは、受信しながら返す)。
    transfer_started: 転送の期限を数え始める時刻(time.monotonic)。HTTPでは、本文の受信を始めた時刻を渡す。
    """
    if not _LOCK.acquire(blocking=False):
        raise Busy('実行中のジョブがあります。')
    try:
        frames = iter_frames(source) if isinstance(source, (bytes, bytearray)) else iter(source)
        return _run_locked(frames, ranges, deadlines, info, transfer_started or time.monotonic(), control)
    finally:
        _LOCK.release()


def _run_locked(frames, ranges, deadlines, info, transfer_started, control=None):
    pending = retry_pending_cleanup()
    if pending:
        return {'status': 'refused', 'reason': 'cleanup_pending',
                'cleanup': {'ok': True, 'state': 'not_started'},
                'detail': f'前回のコンテナを削除できていないため、新しいジョブを受け付けません: {pending}'}
    try:
        first = next(frames)
    except TransferTimeout:
        return {'status': 'failed', 'reason': 'stage_deadline_transfer', 'detail': '転送の期限内に、ヘッダを受信できませんでした。', 'cleanup': {'ok': True, 'state': 'not_started'}}
    except (StopIteration, InvalidInput):
        return {'status': 'refused', 'reason': 'input_invalid', 'detail': 'ヘッダを受信できません。', 'cleanup': {'ok': True, 'state': 'not_started'}}
    if control is not None and control.cancel.is_set():
        return {'status': 'failed', 'reason': 'user_cancelled', 'cleanup': {'ok': True, 'state': 'not_started'}}
    name = f'pmjob-{uuid.uuid4().hex[:16]}'
    created = False
    creation_attempted = False
    result = None
    try:
        try:
            header = header_from_frame(first)
        except InvalidInput as exc:
            raise IsolationUnavailable(str(exc)) from exc
        limits = header.get('limits') or {}
        validate_limits(limits, ranges)
        preflight(info)
        image_id = pinned_image_id()
        image_env = json.loads(docker('image', 'inspect', IMAGE, '--format', '{{json .Config.Env}}').stdout)
        if control is not None and control.cancel.is_set():
            return {'status': 'failed', 'reason': 'user_cancelled', 'cleanup': {'ok': True, 'state': 'not_started'}}
        _ACTIVE.add(name)
        creation_attempted = True  # Dockerの応答が失われても、作成済みの可能性がある。
        docker(*create_command(name, limits))
        created = True
        verify_container(json.loads(docker('inspect', name).stdout)[0], limits, image_id, image_env)
        deadlines = {**STAGE_DEADLINES, **(deadlines or {})}
        clock = StageClock(transfer_started, deadlines, limits['python_seconds'], control)
        process = subprocess.Popen(['docker', 'start', '-a', '-i', name], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        sink, feed_state = {'data': b'', 'overflow': False}, {'error': None}

        def feed():
            """受信したフレームを、受信するたびにコンテナへ流す(本文全体を保持しない)。"""
            try:
                for item in itertools.chain([first], frames):
                    process.stdin.write(item)
                    process.stdin.flush()
                process.stdin.close()
            except (BrokenPipeError, OSError):
                pass  # コンテナが先に終了した(入力の検証に失敗した場合など)
            except Exception as exc:  # 受信の期限超過・不正な入力
                feed_state['error'] = exc
                try:
                    process.stdin.close()
                except OSError:
                    pass

        threads = [threading.Thread(target=feed, daemon=True),
                   threading.Thread(target=read_limited, args=(process.stdout, MAX_STDOUT_BYTES, sink), daemon=True),
                   threading.Thread(target=read_progress, args=(process.stderr, clock), daemon=True)]
        for thread in threads:
            thread.start()
        kill_reason = None
        while process.poll() is None:
            if control is not None and control.cancel.is_set():
                kill_reason = 'user_cancelled'
                docker('kill', name, check=False)
                break
            violation = None if sink['overflow'] else clock.violation(time.monotonic())
            if sink['overflow'] or violation:
                kill_reason = violation
                docker('kill', name, check=False)
                break
            time.sleep(0.05)
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        for thread in threads[1:]:
            thread.join(5)
        for pipe in (process.stdout, process.stderr):
            pipe.close()
        state = json.loads(docker('inspect', name).stdout)[0]['State']
        result = evaluate(sink['data'], state, kill_reason, sink['overflow'])
        if result['status'] == 'ok':
            # 結果を採用する前に、本文の受信が完結したことを確認する。宣言した長さに満たない・期限超過・不正な構造のまま、
            # コンテナだけが完結した場合は、結果を採用しない(転送の残り時間まで待つ)。
            left = max(0.0, transfer_started + deadlines['transfer'] - time.monotonic())
            threads[0].join(left + 0.5)
            error = feed_state['error']
            if threads[0].is_alive() or error is not None:
                incomplete = 'input_invalid' if error is not None and not isinstance(error, TransferTimeout) \
                    else 'stage_deadline_transfer'
                result = evaluate(sink['data'], state, incomplete, sink['overflow'])
    except IsolationUnavailable as exc:
        result = {'status': 'refused', 'reason': 'isolation_unavailable', 'detail': str(exc)}
    finally:
        cleanup_ok = True
        if creation_attempted:
            cleanup_ok = remove_container(name)
            if not cleanup_ok:
                _PENDING_CLEANUP.add(name)
        _ACTIVE.discard(name)
    # 後始末の成否は、結果と一緒に返す(実行履歴へ残す)。削除できなかった場合は、解消するまで新しいジョブを受け付けない。
    cleanup = {'ok': cleanup_ok, 'state': 'not_started' if not creation_attempted else ('closed' if cleanup_ok else 'unconfirmed')}
    result['cleanup'] = cleanup
    if control is not None and control.cancel.is_set():
        result = {'status': 'failed', 'reason': 'user_cancelled', 'cleanup': cleanup}
    return result


def rows_to_csv(rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator='\n')
    for row in rows:
        writer.writerow([NULL_MARK if value is None else value for value in row])
    return buffer.getvalue().encode('utf-8')


def encode_frames(header, chunks):
    """chunks: [(view番号, 行リスト)]。1チャンクの行数は呼出し側で分割する(提案: 5,000行)。"""
    out = frame(b'H', json.dumps(header, ensure_ascii=False).encode('utf-8'))
    for index, rows in chunks:
        out += frame(b'D', struct.pack('>HI', index, len(rows)) + rows_to_csv(rows))
    return out + frame(b'E', b'')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def _send(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        try:
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # 中止で呼出し側が閉じた場合。削除状態は制御窓口に保持済みで、結果の再送はしない。

    def do_GET(self):
        if self.path.startswith('/v1/jobs/'):
            control = find_control(self.path[len('/v1/jobs/'):], self.headers.get('X-Analysis-Control', ''))
            if control is None:
                return self._send(404, {'reason': 'not_found'})
            return self._send(200, {'done': control.done, 'cleanup': control.cleanup, 'stage': control.stage})
        if self.path != '/v1/health':
            return self._send(404, {'detail': 'not found'})
        try:
            self._send(200, {'status': 'ready', 'busy': _LOCK.locked() or bool(_PENDING_CLEANUP), **preflight()})
        except IsolationUnavailable as exc:
            self._send(503, {'status': 'refused', 'reason': 'isolation_unavailable', 'detail': str(exc)})

    # 転送の期限(Djangoからの本文の受信を含む)。テストだけが、短い値に差し替える。
    transfer_deadline = STAGE_DEADLINES['transfer']

    def do_POST(self):
        global _CONTROL
        started = time.monotonic()
        if self.path.startswith('/v1/jobs/') and self.path.endswith('/cancel'):
            control = find_control(self.path[len('/v1/jobs/'):-len('/cancel')], self.headers.get('X-Analysis-Control', ''))
            if control is None:
                return self._send(404, {'reason': 'not_found'})
            accepted = control.request_cancel()
            return self._send(202 if accepted else 409, {'accepted': accepted, 'done': control.done, 'cleanup': control.cleanup})
        if self.path != '/v1/jobs':
            return self._send(404, {'detail': 'not found'})
        try:
            length = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            length = 0
        if not 0 < length <= MAX_REQUEST_BYTES:
            return self._send(413, {'status': 'refused', 'reason': 'request_size', 'detail': '本文の大きさが不正です。', 'cleanup': {'ok': True, 'state': 'not_started'}})
        control = None
        job_id, token = self.headers.get('X-Analysis-Job'), self.headers.get('X-Analysis-Control')
        if job_id is not None or token is not None:
            try:
                valid = str(uuid.UUID(job_id)) == job_id and re.fullmatch('[0-9a-f]{64}', token or '')
            except (ValueError, TypeError):
                valid = False
            if not valid:
                return self._send(400, {'reason': 'control_invalid', 'cleanup': {'ok': True, 'state': 'not_started'}})
            with _CONTROL_LOCK:
                if _CONTROL is not None and (not _CONTROL.done or _CONTROL.job_id == job_id):
                    # 同じIDの再受付は、以前のジョブも未開始と誤認させない。
                    state = (_CONTROL.cleanup or 'unconfirmed') if _CONTROL.job_id == job_id else 'not_started'
                    return self._send(409, {'status': 'refused', 'reason': 'busy', 'cleanup': {'state': state, 'ok': state in ('closed', 'not_started')}})
                control = JobControl(job_id, token, self.connection)
                _CONTROL = control
        # 本文は、受信しながら1フレームずつコンテナへ流す(全体をメモリに保持しない)。結果を返したら、接続は閉じる。
        self.close_connection = True
        source = iter_http_frames(self.rfile.read1, self.connection.settimeout, length, started, self.transfer_deadline)
        try:
            result = run_job(source, transfer_started=started, control=control)
        except Busy:
            if control is not None:
                with _CONTROL_LOCK:
                    control.done, control.cleanup = True, 'not_started'
            return self._send(429, {'status': 'refused', 'reason': 'busy', 'detail': '実行中のジョブがあります。', 'cleanup': {'ok': True, 'state': 'not_started'}})
        except Exception as exc:  # 想定外の例外も、ロックを残さず、結果なしの失敗として返す
            if control is not None:
                with _CONTROL_LOCK:
                    control.done, control.cleanup = True, 'unconfirmed'
            return self._send(500, {'status': 'failed', 'reason': 'launcher_error', 'detail': type(exc).__name__})
        if control is not None:
            with _CONTROL_LOCK:
                if control.cancel.is_set():
                    result = {k: v for k, v in result.items() if k != 'result'}
                    result.update(status='failed', reason='user_cancelled')
                cleanup = result.get('cleanup') or {}
                control.cleanup = cleanup.get('state') or ('closed' if cleanup.get('ok') is True else 'unconfirmed')
                control.done = True
        if result['status'] == 'ok':
            status = 200
        elif result['status'] == 'refused':
            status = 503
        elif result.get('reason') == 'stage_deadline_transfer':
            status = 408
        else:
            status = 422
        self._send(status, result)


def serve(host='127.0.0.1', port=8091):
    lock = acquire_single_instance_lock()  # 保持している間、他のlauncherは起動できない
    print(f'起動時に孤児を削除: {sweep_leftovers()}件', flush=True)
    try:
        ThreadingHTTPServer((host, port), Handler).serve_forever()
    finally:
        lock.close()


if __name__ == '__main__':
    serve()
