"""開発専用launcher。1ジョブ=1コンテナで、Dockerを操作するのはこのプロセスだけ。

- 承認範囲: 開発での検証に限定する(本番は別途判断)。DockerソケットはLinuxのroot相当の権限なので、
  このプロセスはDjango・生成コードから分離し、スキーマ検証したジョブだけを受け付ける。
- 隔離が確認できない場合は実行しない(fail-closed): 起動時・各ジョブ前にpreflight、コンテナ作成後にinspectで完全照合する。
- 結果を採用するのは、終了コード0・OOMなし・期限内・出力が完結・件数照合済みの場合だけ。それ以外は結果を全て破棄する。
"""
import csv
import hashlib
import io
import json
import math
import os
import struct
import subprocess
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

IMAGE = os.environ.get('ANALYSIS_JOB_IMAGE', 'pm-analysis-job:dev')
LABEL = 'pm.analysis.job'
NULL_MARK = '\\N'

# 検証用の暫定値(BOSS承認前)。
TMPFS_MB = 128
PIDS_LIMIT = 128
MAX_RESULT_BYTES = 5 * 1024 * 1024
MAX_STDOUT_BYTES = MAX_RESULT_BYTES + 256 * 1024  # 結果 + ヘッダ + 診断情報(stderr 64KBなど)
MAX_REQUEST_BYTES = 64 * 1024 * 1024
STAGE_DEADLINES = {'transfer': 60, 'load': 60, 'margin': 20}
# 分析実行設定(設定画面)の保存可能範囲と同じ。テストだけが、小さい値を使うために別の範囲を渡す。
PRODUCTION_RANGES = {'memory_mb': (512, 4096), 'cpus': (0.5, 2.0), 'python_seconds': (30, 600)}


class IsolationUnavailable(Exception):
    """隔離機能が確認できない。実行を無効にする。"""


class Busy(Exception):
    pass


class ResultRejected(Exception):
    pass


def docker(*args, timeout=60, check=True, input_text=None):
    result = subprocess.run(['docker', *args], capture_output=True, text=True, timeout=timeout, input=input_text)
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
        'create', '-i', '--name', name, '--label', f'{LABEL}=1', '--network', 'none', '--read-only',
        '--tmpfs', f'/tmp:rw,noexec,nosuid,nodev,size={TMPFS_MB}m,uid=10001,gid=10001,mode=0700',
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
    expect('userns_mode', host.get('UsernsMode') or '', '')
    expect('oom_kill_disable', bool(host.get('OomKillDisable')), False)
    expect('env', sorted(config.get('Env') or []), sorted(image_env))
    expect('tmpfs', sorted((host.get('Tmpfs') or {}).keys()), ['/tmp'])
    expect('label', (config.get('Labels') or {}).get(LABEL), '1')
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


def evaluate(stdout, state, launcher_killed, overflow):
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
    if launcher_killed:
        return failed('launcher_deadline', '期限を超えたため、コンテナを強制終了しました。', diagnostics)
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


def sweep_leftovers():
    """前回の異常終了で残ったジョブ用コンテナを削除する(ラベルで識別)。"""
    ids = docker('ps', '-aq', '--filter', f'label={LABEL}=1', check=False).stdout.split()
    if ids:
        docker('rm', '-f', *ids, check=False)
    return len(ids)


_LOCK = threading.Lock()


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


def run_job(frames, ranges=PRODUCTION_RANGES, deadlines=None, info=None):
    """ジョブを1つ実行する。同時に実行できるのは1件だけ。"""
    if not _LOCK.acquire(blocking=False):
        raise Busy('実行中のジョブがあります。')
    name = f'pmjob-{uuid.uuid4().hex[:16]}'
    created = False
    try:
        header = split_header(frames)
        limits = header.get('limits') or {}
        validate_limits({**limits, 'memory_mb': limits.get('memory_mb'), 'cpus': limits.get('cpus')}, ranges)
        preflight(info)
        image_id = pinned_image_id()
        image_env = json.loads(docker('image', 'inspect', IMAGE, '--format', '{{json .Config.Env}}').stdout)
        docker(*create_command(name, limits))
        created = True
        verify_container(json.loads(docker('inspect', name).stdout)[0], limits, image_id, image_env)
        deadlines = {**STAGE_DEADLINES, **(deadlines or {})}
        total = limits['python_seconds'] + deadlines['transfer'] + deadlines['load'] + deadlines['margin']
        process = subprocess.Popen(['docker', 'start', '-a', '-i', name], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        sink, ignored = {'data': b'', 'overflow': False}, {'data': b'', 'overflow': False}

        def feed():
            try:
                process.stdin.write(frames)
                process.stdin.close()
            except (BrokenPipeError, OSError):
                pass

        threads = [threading.Thread(target=feed, daemon=True),
                   threading.Thread(target=read_limited, args=(process.stdout, MAX_STDOUT_BYTES, sink), daemon=True),
                   threading.Thread(target=read_limited, args=(process.stderr, 4096, ignored), daemon=True)]
        for thread in threads:
            thread.start()
        launcher_killed = False
        started = time.monotonic()
        while process.poll() is None:
            if sink['overflow'] or time.monotonic() - started > total:
                launcher_killed = not sink['overflow']
                docker('kill', name, check=False)
                break
            time.sleep(0.05)
        process.wait(timeout=30)
        for thread in threads[1:]:
            thread.join(5)
        for pipe in (process.stdout, process.stderr):
            pipe.close()
        state = json.loads(docker('inspect', name).stdout)[0]['State']
        return evaluate(sink['data'], state, launcher_killed, sink['overflow'])
    except IsolationUnavailable as exc:
        return {'status': 'refused', 'reason': 'isolation_unavailable', 'detail': str(exc)}
    finally:
        if created:
            docker('rm', '-f', name, check=False)
        _LOCK.release()


def split_header(frames):
    if frames[:1] != b'H':
        raise IsolationUnavailable('先頭フレームがヘッダではありません。')
    (length,) = struct.unpack('>I', frames[1:5])
    return json.loads(frames[5:5 + length].decode('utf-8'))


def rows_to_csv(rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator='\n')
    for row in rows:
        writer.writerow([NULL_MARK if value is None else value for value in row])
    return buffer.getvalue().encode('utf-8')


def encode_frames(header, chunks):
    """chunks: [(view番号, 行リスト)]。1チャンクの行数は呼出し側で分割する(提案: 5,000行)。"""
    def frame(kind, payload):
        return kind + struct.pack('>I', len(payload)) + payload

    out = frame(b'H', json.dumps(header, ensure_ascii=False).encode('utf-8'))
    for index, rows in chunks:
        out += frame(b'D', struct.pack('>HI', index, len(rows)) + rows_to_csv(rows))
    return out + frame(b'E', b'')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def _send(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != '/v1/health':
            return self._send(404, {'detail': 'not found'})
        try:
            self._send(200, {'status': 'ready', **preflight()})
        except IsolationUnavailable as exc:
            self._send(503, {'status': 'refused', 'reason': 'isolation_unavailable', 'detail': str(exc)})

    def do_POST(self):
        if self.path != '/v1/jobs':
            return self._send(404, {'detail': 'not found'})
        length = int(self.headers.get('Content-Length') or 0)
        if not 0 < length <= MAX_REQUEST_BYTES:
            return self._send(413, {'status': 'refused', 'reason': 'request_size', 'detail': '本文の大きさが不正です。'})
        try:
            result = run_job(self.rfile.read(length))
        except Busy:
            return self._send(429, {'status': 'refused', 'reason': 'busy', 'detail': '実行中のジョブがあります。'})
        self._send(200 if result['status'] == 'ok' else 503 if result['status'] == 'refused' else 422, result)


def serve(host='127.0.0.1', port=8091):
    print(f'起動時に残骸を削除: {sweep_leftovers()}件', flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == '__main__':
    serve()
