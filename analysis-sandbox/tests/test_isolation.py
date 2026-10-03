"""ジョブ用コンテナの隔離・資源制限・結果採否の検証(実Dockerが必要)。

開発専用。WSLのUbuntuでrootとして実行する:
  wsl.exe -d Ubuntu-24.04 -u root -- python3 -m unittest discover -s /mnt/d/pm/analysis-sandbox/tests -v

テスト用の「生成コード」は、このファイルに書いた攻撃を模したスクリプトで、コンテナの中だけで実行する(Windows・Djangoでは実行しない)。
"""
import json
import math
import os
import struct
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'launcher'))
import launcher as L  # noqa: E402

# テストだけは、小さい値を使うため、範囲を緩める。launcher本体(PRODUCTION_RANGES)は設定画面の範囲のまま。
TEST_RANGES = {'memory_mb': (64, 4096), 'cpus': (0.5, 2.0), 'python_seconds': (1, 600)}
SHIPMENT_COLUMNS = [{'name': 'id', 'type': 'BIGINT'}, {'name': 'quantity', 'type': 'DECIMAL(18,3)'},
                    {'name': 'note', 'type': 'VARCHAR'}]


def make_header(code, memory_mb=256, cpus=1.0, python_seconds=20, views=None):
    return {
        'limits': {'memory_mb': memory_mb, 'cpus': cpus, 'python_seconds': python_seconds,
                   'duckdb_memory_limit_mb': memory_mb // 2, 'threads': math.ceil(cpus)},
        'code': code, 'views': views or [],
    }


def run(code, chunks=None, views=None, deadlines=None, **limits):
    frames = L.encode_frames(make_header(code, views=views, **limits), chunks or [])
    return L.run_job(frames, ranges=TEST_RANGES, deadlines=deadlines)


def report(result):
    return json.loads(result['result']['report'])


def leftover_containers():
    return L.docker('ps', '-aq', '--filter', f'label={L.LABEL}=1').stdout.split()


class IsolationBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        L.sweep_leftovers()

    def tearDown(self):
        self.assertEqual(leftover_containers(), [], 'ジョブ用コンテナが残っています(後始末の失敗)')


class DataLoadingTest(IsolationBase):
    def test_valid_job_loads_checks_counts_and_returns_tables(self):
        rows = [[1, '10.500', 'a'], [2, '3.000', None], [3, '7.250', 'c,"quoted"']]
        views = [{'name': 'v_ai_shipment', 'columns': SHIPMENT_COLUMNS, 'expected_rows': 3, 'unique_key': 'id'}]
        code = (
            "rel = load_view('v_ai_shipment')\n"
            "emit_table('合計', ['rows', 'sum'], con.sql('SELECT COUNT(*), SUM(quantity) FROM v_ai_shipment').fetchall())\n"
            "emit_table('NULL', ['n'], con.sql('SELECT COUNT(*) FROM v_ai_shipment WHERE note IS NULL').fetchall())\n"
            "emit_chart('bar', 't', ['a', 'b'], [{'name': 's', 'values': [1, 2]}])\nemit_report('完了')\n"
        )
        result = run(code, chunks=[(0, rows[:2]), (0, rows[2:])], views=views)
        self.assertEqual(result['status'], 'ok', result)
        self.assertEqual(result['result']['tables'][0]['rows'], [[3, '20.750']])
        self.assertEqual(result['result']['tables'][1]['rows'], [[1]])
        self.assertEqual(result['diagnostics']['rows_loaded'], {'v_ai_shipment': 3})
        self.assertEqual(result['diagnostics']['oom_kill'], 0)

    def test_count_and_key_mismatches_fail_without_a_result(self):
        views = [{'name': 'v_ai_shipment', 'columns': SHIPMENT_COLUMNS, 'expected_rows': 3, 'unique_key': 'id'}]
        two = [[1, '1', 'a'], [2, '2', 'b']]
        cases = [
            ('row_count_mismatch', [(0, two)], views),  # 期待3行に対して2行
            ('duplicate_key', [(0, two + [[2, '3', 'c']])], views),  # 一意キーの重複
        ]
        for reason, chunks, case_views in cases:
            with self.subTest(reason=reason):
                result = run("emit_report('到達してはいけない')", chunks=chunks, views=case_views)
                self.assertEqual((result['status'], result['reason']), ('failed', reason))
                self.assertNotIn('result', result)

    def test_bulk_load_of_100000_rows_in_5000_row_chunks(self):
        views = [{'name': 'v_ai_shipment', 'columns': SHIPMENT_COLUMNS, 'expected_rows': 100_000, 'unique_key': 'id'}]
        rows = [[i, '1.000', 'x'] for i in range(100_000)]
        chunks = [(0, rows[i:i + 5000]) for i in range(0, 100_000, 5000)]
        started = time.monotonic()
        result = run("emit_table('n', ['n'], con.sql('SELECT COUNT(*) FROM v_ai_shipment').fetchall())",
                     chunks=chunks, views=views, memory_mb=512)
        self.assertEqual(result['status'], 'ok', result)
        self.assertEqual(result['result']['tables'][0]['rows'], [[100_000]])
        print(f"\n[測定] 10万行: 全体{time.monotonic() - started:.1f}秒 / コンテナ内 {result['diagnostics']['seconds']}")


class NetworkAndFileTest(IsolationBase):
    def test_no_route_outside_the_container_but_loopback_remains(self):
        code = '''
import json, socket
out = {}
def attempt(host, port):
    s = socket.socket(); s.settimeout(2)
    try:
        s.connect((host, port)); return 'connected'
    except Exception as e:
        return type(e).__name__
    finally:
        s.close()
for name, target in {'internet': ('1.1.1.1', 53), 'docker_bridge': ('172.17.0.1', 22), 'dev_pc': ('10.0.1.36', 3306)}.items():
    out[name] = attempt(*target)
try:
    socket.gethostbyname('example.com'); out['dns'] = 'resolved'
except Exception as e:
    out['dns'] = type(e).__name__
out['interfaces'] = [l.split(':')[0].strip() for l in open('/proc/net/dev').read().splitlines()[2:]]
server = socket.socket(); server.bind(('127.0.0.1', 0)); server.listen(1)
client = socket.socket(); client.settimeout(2)
out['loopback'] = 'connected' if client.connect_ex(('127.0.0.1', server.getsockname()[1])) == 0 else 'failed'
emit_report(json.dumps(out))
'''
        result = run(code)
        self.assertEqual(result['status'], 'ok', result)
        observed = report(result)
        print(f'\n[通信] {observed}')
        for name in ('internet', 'docker_bridge', 'dev_pc'):
            self.assertNotEqual(observed[name], 'connected', name)
        self.assertNotEqual(observed['dns'], 'resolved')
        self.assertEqual(observed['interfaces'], ['lo'])  # ループバックだけが残る(外へは出られない)
        self.assertEqual(observed['loopback'], 'connected')  # ソケット作成の禁止ではない

    def test_no_inherited_sockets_and_only_standard_descriptors(self):
        code = '''
import json, os
fds = {}
for fd in os.listdir('/proc/self/fd'):
    try:
        fds[fd] = os.readlink('/proc/self/fd/' + fd)
    except OSError:
        pass
emit_report(json.dumps(fds))
'''
        result = run(code)
        self.assertEqual(result['status'], 'ok', result)
        links = report(result).values()
        self.assertFalse([link for link in links if link.startswith('socket:')], links)

    def test_filesystem_boundaries(self):
        code = '''
import json, os, subprocess
out = {}
def attempt(label, fn):
    try:
        fn(); out[label] = 'allowed'
    except Exception as e:
        out[label] = type(e).__name__
attempt('write_root', lambda: open('/blocked', 'w').write('x'))
attempt('write_etc', lambda: open('/etc/blocked', 'w').write('x'))
attempt('write_job', lambda: open('/job/blocked', 'w').write('x'))
attempt('write_tmp', lambda: open('/tmp/ok.txt', 'w').write('x'))
open('/tmp/run.sh', 'w').write('#!/bin/sh\\necho hi\\n'); os.chmod('/tmp/run.sh', 0o755)
attempt('exec_from_tmp', lambda: subprocess.run(['/tmp/run.sh'], check=True))
attempt('read_shadow', lambda: open('/etc/shadow').read())
found = []
for base, dirs, files in os.walk('/'):
    if base.startswith(('/proc', '/sys', '/dev')):
        dirs[:] = []; continue
    for name in files + dirs:
        if name in ('.env', 'pm_backend', 'docker.sock', 'id_rsa', 'firebase-service-account.json'):
            found.append(os.path.join(base, name))
out['secret_like_files'] = found
out['docker_sock'] = os.path.exists('/var/run/docker.sock')
out['uid'] = os.getuid()
import importlib.util
out['pip'] = importlib.util.find_spec('pip') is not None
emit_report(json.dumps(out))
'''
        result = run(code)
        self.assertEqual(result['status'], 'ok', result)
        out = report(result)
        for label in ('write_root', 'write_etc', 'write_job', 'exec_from_tmp', 'read_shadow'):
            self.assertNotEqual(out[label], 'allowed', label)
        self.assertEqual(out['write_tmp'], 'allowed')
        self.assertEqual((out['secret_like_files'], out['docker_sock'], out['uid'], out['pip']), ([], False, 10001, False))


class ParentAndProcessTest(IsolationBase):
    def test_parent_memory_environment_ptrace_and_signals(self):
        code = '''
import ctypes, json, os, signal
out = {}
def attempt(label, fn):
    try:
        fn(); out[label] = 'allowed'
    except Exception as e:
        out[label] = type(e).__name__
attempt('read_parent_mem', lambda: open('/proc/1/mem', 'rb').read(1))
attempt('read_parent_environ', lambda: open('/proc/1/environ', 'rb').read(1))
attempt('read_parent_maps', lambda: open('/proc/1/maps').read(1))
libc = ctypes.CDLL(None, use_errno=True)
out['ptrace_attach_result'] = libc.ptrace(16, 1, 0, 0)  # PTRACE_ATTACH。拒否されれば-1
out['ptrace_errno'] = ctypes.get_errno()
out['ppid'] = os.getppid()
for name in ('SIGSTOP', 'SIGKILL'):
    try:
        os.kill(1, getattr(signal, name)); out['signal_' + name] = 'sent'
    except Exception as e:
        out['signal_' + name] = type(e).__name__
emit_report(json.dumps(out))
'''
        started = time.monotonic()
        result = run(code, python_seconds=15)
        out = report(result) if result['status'] == 'ok' else {}
        print(f"\n[親へのアクセス] status={result['status']} reason={result.get('reason')} {out}")
        # 親(PID 1)への停止・終了シグナルでも、ジョブは決定的に終了する(ハングしない)。結果の採否は、通常の判定に従う。
        self.assertIn(result['status'], ('ok', 'failed'), result)
        self.assertLess(time.monotonic() - started, 40)
        if result['status'] == 'ok':
            for label in ('read_parent_mem', 'read_parent_environ', 'read_parent_maps'):
                self.assertNotEqual(out[label], 'allowed', label)
            self.assertEqual(out['ptrace_attach_result'], -1)

    def test_threads_and_forks_cannot_exceed_the_pids_limit(self):
        code = '''
import json, os, threading, time
out = {}
stop = threading.Event()
threads = []
try:
    while len(threads) < 1000:
        t = threading.Thread(target=stop.wait); t.start(); threads.append(t)
    out['threads'] = 'no_limit'
except Exception as e:
    out['threads'] = type(e).__name__
out['thread_count'] = len(threads)
children = []
try:
    for _ in range(1000):
        pid = os.fork()
        if pid == 0:
            time.sleep(30); os._exit(0)
        children.append(pid)
    out['forks'] = 'no_limit'
except Exception as e:
    out['forks'] = type(e).__name__
out['fork_count'] = len(children)
out['pids_max'] = open('/sys/fs/cgroup/pids.max').read().strip()
out['pids_peak'] = int(open('/sys/fs/cgroup/pids.peak').read()) if os.path.exists('/sys/fs/cgroup/pids.peak') else None
stop.set()
emit_report(json.dumps(out))
'''
        result = run(code, python_seconds=30)
        self.assertEqual(result['status'], 'ok', result)
        out = report(result)
        print(f'\n[プロセス数] {out}')
        self.assertNotEqual(out['threads'], 'no_limit')
        self.assertNotEqual(out['forks'], 'no_limit')
        self.assertLessEqual(out['thread_count'] + out['fork_count'], L.PIDS_LIMIT)
        self.assertEqual(out['pids_max'], str(L.PIDS_LIMIT))

    def test_supervisor_killed_from_outside_never_yields_a_result(self):
        def kill_later():
            for _ in range(100):
                ids = leftover_containers()
                if ids:
                    time.sleep(2.5)
                    L.docker('kill', ids[0], check=False)
                    return
                time.sleep(0.1)

        thread = threading.Thread(target=kill_later)
        thread.start()
        result = run("import time\nemit_report('start')\ntime.sleep(60)", python_seconds=50)
        thread.join()
        self.assertEqual(result['status'], 'failed', result)
        self.assertEqual(result['reason'], 'incomplete_or_corrupt_output')
        self.assertNotIn('result', result)


class ResourceLimitTest(IsolationBase):
    def test_single_process_oom_discards_everything(self):
        result = run("emit_report('先に出力')\nbuffer = bytearray(600 * 1024 * 1024)\nemit_report('到達しない')", memory_mb=256)
        self.assertEqual(result['status'], 'failed', result)
        self.assertIn(result['reason'], ('oom_killed', 'container_oom_killed'))
        self.assertNotIn('result', result)

    def test_child_only_oom_is_detected_even_when_the_main_child_succeeds(self):
        """孫プロセスだけがOOMで終了し、生成コード本体は終了コード0で正常終了する場合でも、結果を採用しない。"""
        code = '''
import subprocess, sys
grandchild = subprocess.Popen([sys.executable, '-c', 'b = bytearray(600 * 1024 * 1024)\\nimport time\\ntime.sleep(5)'])
code = grandchild.wait()
emit_table('正常に見える結果', ['x'], [[1]])
emit_report('孫の終了コード=%s' % code)
'''
        result = run(code, memory_mb=256, python_seconds=30)
        self.assertEqual(result['status'], 'failed', result)
        # Docker側のOOM検出(container_oom_killed)と、ジョブ内のcgroup検出(oom_killed)のどちらでも、結果を破棄する。
        self.assertIn(result['reason'], ('oom_killed', 'container_oom_killed'))
        self.assertNotIn('result', result)
        # 監督プロセスは生き残り、完結した出力を返していた(=子プロセスだけがOOMになった)ことを確認する。
        self.assertEqual(result['diagnostics'].get('oom_kill', 0) > 0 or result['container']['oom_killed'], True)
        print(f"\n[孫だけのOOM] reason={result['reason']} container={result['container']} diagnostics.oom_kill={result['diagnostics'].get('oom_kill')}")

    def test_memory_exhaustion_through_threads_is_contained(self):
        code = '''
import threading
held = []
def grab():
    held.append(bytearray(120 * 1024 * 1024))
threads = [threading.Thread(target=grab) for _ in range(8)]
[t.start() for t in threads]; [t.join() for t in threads]
emit_report('到達しない')
'''
        result = run(code, memory_mb=256)
        self.assertEqual(result['status'], 'failed', result)
        self.assertNotIn('result', result)

    def test_cpu_quota_is_enforced_for_threads_and_descendants(self):
        code = '''
import json, subprocess, sys, time
def usage():
    stat = dict(l.split() for l in open('/sys/fs/cgroup/cpu.stat'))
    return int(stat['usage_usec']), int(stat['nr_throttled'])
before_usage, before_throttled = usage()
start = time.monotonic()
busy = 'import time\\nt = time.time()\\nwhile time.time() - t < 4: pass'
procs = [subprocess.Popen([sys.executable, '-c', busy]) for _ in range(4)]
[p.wait() for p in procs]
wall = time.monotonic() - start
after_usage, after_throttled = usage()
emit_report(json.dumps({'cores_used': (after_usage - before_usage) / 1e6 / wall, 'throttled': after_throttled - before_throttled}))
'''
        result = run(code, cpus=0.5, python_seconds=30)
        self.assertEqual(result['status'], 'ok', result)
        out = report(result)
        print(f'\n[CPU] 上限0.5コア → {out}')
        # 許容誤差(+25%)は検証用の暫定値。実測してから確定する。
        self.assertLessEqual(out['cores_used'], 0.5 * 1.25, out)
        self.assertGreater(out['throttled'], 0, out)

    def test_python_time_limit_kills_loops_and_ignored_signals(self):
        code = "import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\nwhile True:\n    pass"
        started = time.monotonic()
        result = run(code, python_seconds=3)
        self.assertEqual((result['status'], result['reason']), ('failed', 'timeout'), result)
        self.assertLess(time.monotonic() - started, 30)
        self.assertNotIn('result', result)

    def test_tmpfs_exhaustion_fails_and_cleans_up(self):
        code = "with open('/tmp/fill.bin', 'wb') as f:\n    for _ in range(300):\n        f.write(b'x' * 1024 * 1024)\nemit_report('到達しない')"
        result = run(code, memory_mb=512)
        self.assertEqual(result['status'], 'failed', result)
        self.assertNotIn('result', result)


class OutputAdoptionTest(IsolationBase):
    def test_oversized_or_invalid_results_fail_instead_of_being_truncated(self):
        cases = {
            'result_too_large': "emit_report('x' * (6 * 1024 * 1024))",
            'result_invalid': "emit_table('t', ['a'], [[i] for i in range(10001)])",
        }
        for reason, code in cases.items():
            with self.subTest(reason=reason):
                result = run(code, memory_mb=512)
                self.assertEqual((result['status'], result['reason']), ('failed', reason), result)
                self.assertNotIn('result', result)

    def test_partial_or_forged_result_files_are_not_adopted(self):
        cases = {
            'result_invalid': "import os\nopen('/tmp/result.json', 'w').write('{\"tables\":')\nos._exit(0)",
            'child_exit_nonzero': (
                "import json, os\nopen('/tmp/result.json', 'w').write(json.dumps({'tables': [], 'charts': [], 'report': '部分的'}))\nos._exit(1)"
            ),
            'result_missing': "import os\nos._exit(0)",
        }
        for reason, code in cases.items():
            with self.subTest(reason=reason):
                result = run(code)
                self.assertEqual((result['status'], result['reason']), ('failed', reason), result)
                self.assertNotIn('result', result)

    def test_stderr_is_truncated_with_an_explicit_marker_but_results_are_not(self):
        result = run("import sys\nsys.stderr.write('e' * 200000)\nemit_report('ok')")
        self.assertEqual(result['status'], 'ok', result)
        self.assertTrue(result['diagnostics']['stderr_truncated'])
        self.assertLessEqual(len(result['diagnostics']['stderr']), 64 * 1024)

    def test_stream_parser_rejects_incomplete_or_tampered_output(self):
        import hashlib
        body = b'{"tables": [], "charts": [], "report": null}'
        header = json.dumps({'status': 'ok', 'length': len(body), 'sha256': hashlib.sha256(body).hexdigest()}).encode()
        good = b'PMRESULT1\n' + header + b'\n' + body + b'\nPMEND\n'
        self.assertEqual(L.parse_result_stream(good)[1], body)
        bad = {
            '終端マーカーなし': good[:-len(b'\nPMEND\n')],
            '途中で終了': good[:len(good) // 2],
            '余分なデータ': good + b'x',
            '本文の改ざん': good.replace(b'"report": null', b'"report": "x" '),
            '先頭が不正': b'x' + good,
            '空': b'',
        }
        for label, raw in bad.items():
            with self.subTest(label=label), self.assertRaises(L.ResultRejected):
                L.parse_result_stream(raw)

    def test_evaluate_refuses_every_abnormal_container_state(self):
        import hashlib
        body = b'{"tables": [], "charts": [], "report": null}'
        sha = hashlib.sha256(body).hexdigest()

        def stream(**extra):
            header = json.dumps({'status': 'ok', 'length': len(body), 'sha256': sha, 'oom_kill': 0, **extra}).encode()
            return b'PMRESULT1\n' + header + b'\n' + body + b'\nPMEND\n'

        ok_state = {'ExitCode': 0, 'OOMKilled': False}
        self.assertEqual(L.evaluate(stream(), ok_state, False, False)['status'], 'ok')
        abnormal = {
            'OOMKilledのコンテナ': (stream(), {'ExitCode': 0, 'OOMKilled': True}, False, False),
            '終了コード非0': (stream(), {'ExitCode': 137, 'OOMKilled': False}, False, False),
            'launcherによる強制終了': (stream(), ok_state, True, False),
            '出力上限超過': (stream(), ok_state, False, True),
            'ジョブ内のOOM記録': (stream(oom_kill=1), ok_state, False, False),
            '出力なし': (b'', {'ExitCode': 137, 'OOMKilled': False}, False, False),
        }
        for label, args in abnormal.items():
            with self.subTest(label=label):
                result = L.evaluate(*args)
                self.assertEqual(result['status'], 'failed')
                self.assertNotIn('result', result)


class FailClosedTest(IsolationBase):
    def test_preflight_refuses_when_isolation_features_are_missing(self):
        for info in ({'CgroupVersion': '1', 'SecurityOptions': ['name=seccomp,profile=builtin']},
                     {'CgroupVersion': '2', 'SecurityOptions': ['name=cgroupns']}):
            with self.subTest(info=info), self.assertRaises(L.IsolationUnavailable):
                L.preflight(info)
        before = leftover_containers()
        result = L.run_job(L.encode_frames(make_header("emit_report('x')"), []), ranges=TEST_RANGES,
                           info={'CgroupVersion': '1', 'SecurityOptions': []})
        self.assertEqual((result['status'], result['reason']), ('refused', 'isolation_unavailable'))
        self.assertEqual(leftover_containers(), before)  # コンテナを作らない

    def test_preflight_passes_on_this_environment(self):
        self.assertEqual(L.preflight()['cgroup'], '2')

    def test_inspect_verification_rejects_every_weakened_configuration(self):
        limits = {'memory_mb': 256, 'cpus': 1.0, 'python_seconds': 20, 'threads': 1}
        image_id = L.pinned_image_id()
        image_env = json.loads(L.docker('image', 'inspect', L.IMAGE, '--format', '{{json .Config.Env}}').stdout)

        def variant(replace=None, remove=None, extra=None):
            base = L.create_command('placeholder', limits)
            replacements = dict(replace or [])
            command = []
            skip = 0
            for part in base:
                if skip:
                    skip -= 1
                    continue
                if remove and part == remove[0]:
                    skip = remove[1]
                    continue
                if part in replacements:
                    command += [part, replacements[part]]
                    skip = 1
                    continue
                command.append(part)
            image = command.pop()
            return command + (extra or []) + [image]

        weakened = {
            'ネットワークあり': variant(replace=[('--network', 'bridge')]),
            '書き込み可能なルート': variant(remove=('--read-only', 0)),
            '特権': variant(extra=['--privileged']),
            'ホストのマウント': variant(extra=['-v', '/tmp:/mnt']),
            '余分な環境変数': variant(extra=['-e', 'SECRET=1']),
            'メモリ上限が違う': variant(replace=[('--memory', '4096m'), ('--memory-swap', '4096m')]),
            'CPU上限が違う': variant(replace=[('--cpus', '2.0')]),
            'スワップを許す': variant(replace=[('--memory-swap', '1024m')]),
            'プロセス数の制限なし': variant(remove=('--pids-limit', 1)),
            'ケーパビリティを落とさない': variant(remove=('--cap-drop', 1)),
            'rootで実行': variant(replace=[('--user', '0:0')]),
            'ポート公開': variant(extra=['-p', '127.0.0.1:18080:8080']),
            'tmpfsの容量が大きい': variant(replace=[('--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=4096m,uid=10001,gid=10001,mode=0700')]),
            'tmpfsで実行できる': variant(replace=[('--tmpfs', '/tmp:rw,nosuid,nodev,size=128m,uid=10001,gid=10001,mode=0700')]),
            'tmpfsでsetuidを許す': variant(replace=[('--tmpfs', '/tmp:rw,noexec,nodev,size=128m,uid=10001,gid=10001,mode=0700')]),
            'tmpfsでデバイスを許す': variant(replace=[('--tmpfs', '/tmp:rw,noexec,nosuid,size=128m,uid=10001,gid=10001,mode=0700')]),
            'tmpfsの権限が緩い': variant(replace=[('--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=128m,uid=10001,gid=10001,mode=1777')]),
            'tmpfsの所有者がroot': variant(replace=[('--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=128m,uid=0,gid=0,mode=0700')]),
            'tmpfsが追加される': variant(extra=['--tmpfs', '/var/tmp:rw,size=1g']),
            '共有メモリが大きい': variant(extra=['--shm-size', '2g']),
            'IPCがホスト': variant(extra=['--ipc', 'host']),
            'PIDがホスト': variant(extra=['--pid', 'host']),
            'ulimitを変更': variant(extra=['--ulimit', 'nofile=1048576']),
            'sysctlを変更': variant(extra=['--sysctl', 'net.core.somaxconn=1024']),
        }
        for label, command in weakened.items():
            name = f'pmjob-test-{abs(hash(label)) % 10**8}'
            command = [name if part == 'placeholder' else part for part in command]
            with self.subTest(label=label):
                try:
                    L.docker(*command)
                    inspected = json.loads(L.docker('inspect', name).stdout)[0]
                    with self.assertRaises(L.IsolationUnavailable):
                        L.verify_container(inspected, limits, image_id, image_env)
                finally:
                    L.docker('rm', '-f', name, check=False)

    def test_correct_configuration_passes_verification(self):
        limits = {'memory_mb': 256, 'cpus': 1.0, 'python_seconds': 20, 'threads': 1}
        name = 'pmjob-test-correct'
        image_env = json.loads(L.docker('image', 'inspect', L.IMAGE, '--format', '{{json .Config.Env}}').stdout)
        try:
            L.docker(*L.create_command(name, limits))
            L.verify_container(json.loads(L.docker('inspect', name).stdout)[0], limits, L.pinned_image_id(), image_env)
        finally:
            L.docker('rm', '-f', name, check=False)

    def test_startup_sweep_removes_leftover_containers(self):
        L.docker('create', '--name', 'pmjob-stray', '--label', f'{L.LABEL}=1', L.IMAGE)
        self.assertEqual(L.sweep_leftovers(), 1)
        self.assertEqual(leftover_containers(), [])

    def test_only_one_job_runs_at_a_time(self):
        holder = threading.Thread(target=lambda: run("import time\ntime.sleep(6)\nemit_report('x')", python_seconds=20))
        holder.start()
        time.sleep(1.5)
        with self.assertRaises(L.Busy):
            run("emit_report('x')")
        holder.join()

    def test_out_of_range_limits_are_refused_before_any_container_exists(self):
        before = leftover_containers()
        header = make_header("emit_report('x')", memory_mb=256)
        header['limits']['memory_mb'] = 300_000
        result = L.run_job(L.encode_frames(header, []), ranges=TEST_RANGES)
        self.assertEqual(result['status'], 'refused')
        self.assertEqual(leftover_containers(), before)


def container_names():
    return L.docker('ps', '-a', '--filter', f'label={L.LABEL}=1', '--format', '{{.Names}}').stdout.split()


class RunningJobProtectionTest(IsolationBase):
    """掃除は、稼働中のジョブを削除しない。削除するのは、停止済みのlauncherが残した孤児だけ。"""

    def test_sweep_never_removes_a_running_job(self):
        box = {}
        thread = threading.Thread(target=lambda: box.update(result=run("import time\ntime.sleep(5)\nemit_report('slow')", python_seconds=30)))
        thread.start()
        for _ in range(100):  # ジョブ用コンテナが現れるまで待つ
            if container_names():
                break
            time.sleep(0.1)
        time.sleep(1.5)
        removed = L.sweep_leftovers()  # 実行中のジョブがある間に掃除しても、そのコンテナは削除されない
        thread.join()
        self.assertEqual(removed, 0)
        self.assertEqual(box['result']['status'], 'ok', box['result'])

    def test_only_orphans_of_other_launchers_are_removed(self):
        for name, labels in (
            ('pmjob-orphan-other', [f'{L.OWNER_LABEL}=deadbeef0000']),  # 別のlauncherが残したもの
            ('pmjob-orphan-nolabel', []),  # 所有者のラベルがないもの
            ('pmjob-mine', [f'{L.OWNER_LABEL}={L.LAUNCHER_ID}']),  # このlauncherが管理しているもの
        ):
            command = ['create', '--name', name, '--label', f'{L.LABEL}=1']
            for label in labels:
                command += ['--label', label]
            L.docker(*command, L.IMAGE)
        try:
            self.assertEqual(L.sweep_leftovers(), 2)
            self.assertEqual(container_names(), ['pmjob-mine'])
        finally:
            L.docker('rm', '-f', 'pmjob-mine', check=False)

    def test_launcher_is_a_single_instance(self):
        import tempfile
        path = os.path.join(tempfile.mkdtemp(), 'launcher.lock')
        first = L.acquire_single_instance_lock(path)
        with self.assertRaises(L.IsolationUnavailable):
            L.acquire_single_instance_lock(path)
        first.close()
        L.acquire_single_instance_lock(path).close()  # 解放後は、再び取得できる


class StreamingTest(IsolationBase):
    """分割転送・順次投入: 本文全体をメモリに保持せず、チャンクを受信するたびに投入する。"""

    def test_http_frames_never_hold_the_whole_body(self):
        import tracemalloc
        payload = b'x' * (1024 * 1024)
        chunks = 200  # 本文の合計は約200MB

        def frame_stream():
            yield L.frame(b'H', b'{}')
            for _ in range(chunks):
                yield L.frame(b'D', payload)
            yield L.frame(b'E', b'')

        total = 5 + 2 + chunks * (5 + len(payload)) + 5
        source, buffer = frame_stream(), bytearray()

        def read1(count):
            if not buffer:
                try:
                    buffer.extend(next(source))
                except StopIteration:
                    return b''
            data = bytes(buffer[:count])
            del buffer[:count]
            return data

        tracemalloc.start()
        seen = sum(1 for _ in L.iter_http_frames(read1, lambda timeout: None, total, time.monotonic(), 60))
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        self.assertEqual(seen, chunks + 2)
        self.assertLess(peak, 8 * 1024 * 1024, f'ピークメモリ{peak}バイト(本文全体は200MB)')

    def test_chunks_are_loaded_in_order_and_no_chunk_file_remains(self):
        views = [{'name': 'v_ai_shipment', 'columns': SHIPMENT_COLUMNS, 'expected_rows': 20_000, 'unique_key': 'id'}]
        rows = [[i, '1.000', 'x'] for i in range(20_000)]
        chunks = [(0, rows[i:i + 5000]) for i in range(0, 20_000, 5000)]
        code = ("import json, os\nemit_report(json.dumps({'tmp': sorted(os.listdir('/tmp')), "
                "'rows': con.sql('SELECT COUNT(*) FROM v_ai_shipment').fetchone()[0]}))")
        result = run(code, chunks=chunks, views=views, memory_mb=512)
        self.assertEqual(result['status'], 'ok', result)
        observed = report(result)
        self.assertEqual(observed['rows'], 20_000)
        self.assertNotIn('chunk.csv', observed['tmp'])  # 投入後に、チャンクの一時ファイルを残さない
        self.assertNotIn('data', observed['tmp'])

    def test_chunk_level_checks_fail_the_job(self):
        def job(expected, claimed, csv_rows, code="emit_report('到達しない')"):
            header = make_header(code, views=[{'name': 'v_ai_shipment', 'columns': SHIPMENT_COLUMNS,
                                              'expected_rows': expected, 'unique_key': 'id'}])
            frames = (L.frame(b'H', json.dumps(header).encode()) +
                      L.frame(b'D', struct.pack('>HI', 0, claimed) + L.rows_to_csv(csv_rows)) + L.frame(b'E', b''))
            return L.run_job(frames, ranges=TEST_RANGES)

        two = [[1, '1', 'a'], [2, '2', 'b']]
        cases = {
            'chunk_too_large': job(6000, 6000, [[i, '1', 'x'] for i in range(6000)]),  # 1チャンクが5,000行を超える
            'chunk_row_count_mismatch': job(3, 3, two),  # 申告3行 / 実際2行
            'row_count_exceeded': job(1, 2, two),  # 期待1行を超えた
            'row_count_mismatch': job(3, 2, two),  # 終端まで受信しても、期待3行に満たない
        }
        for reason, result in cases.items():
            with self.subTest(reason=reason):
                self.assertEqual((result['status'], result.get('reason')), ('failed', reason), result)
                self.assertNotIn('result', result)


class ResultTypeTest(IsolationBase):
    """表だけでなく、グラフ・報告書の型も厳密に検証する。1つでも不正なら、結果全体を採用しない。"""

    def test_invalid_table_chart_and_report_types_are_never_adopted(self):
        chart = '{"kind": "bar", "title": "t", "x": [1, 2], "series": [{"name": "s", "values": [1, 2]}]}'
        invalid = {
            'report_dict': '{"tables": [], "charts": [], "report": {"a": 1}}',
            'report_number': '{"tables": [], "charts": [], "report": 5}',
            'report_list': '{"tables": [], "charts": [], "report": ["x"]}',
            'tables_not_list': '{"tables": {}, "charts": [], "report": null}',
            'charts_not_list': '{"tables": [], "charts": {}, "report": null}',
            'chart_unknown_kind': chart.replace('"bar"', '"pie"').join(['{"tables": [], "charts": [', '], "report": null}']),
            'chart_title_not_str': chart.replace('"t"', '5').join(['{"tables": [], "charts": [', '], "report": null}']),
            'chart_x_not_list': chart.replace('[1, 2], "series"', '"abc", "series"').join(['{"tables": [], "charts": [', '], "report": null}']),
            'chart_series_length_mismatch': chart.replace('"values": [1, 2]', '"values": [1]').join(['{"tables": [], "charts": [', '], "report": null}']),
            'chart_series_missing_values': chart.replace('"values": [1, 2]', '"vals": [1, 2]').join(['{"tables": [], "charts": [', '], "report": null}']),
            'chart_extra_key': chart.replace('"kind"', '"extra": 1, "kind"').join(['{"tables": [], "charts": [', '], "report": null}']),
            'chart_value_object': chart.replace('"values": [1, 2]', '"values": [{"a": 1}, 2]').join(['{"tables": [], "charts": [', '], "report": null}']),
            'table_cell_object': '{"tables": [{"name": "t", "columns": ["a"], "rows": [[{"a": 1}]]}], "charts": [], "report": null}',
            'table_name_not_str': '{"tables": [{"name": 5, "columns": ["a"], "rows": []}], "charts": [], "report": null}',
            'table_column_not_str': '{"tables": [{"name": "t", "columns": [5], "rows": []}], "charts": [], "report": null}',
            'table_row_length': '{"tables": [{"name": "t", "columns": ["a", "b"], "rows": [[1]]}], "charts": [], "report": null}',
            'nan_cell': '{"tables": [{"name": "t", "columns": ["a"], "rows": [[NaN]]}], "charts": [], "report": null}',
            'infinity_cell': '{"tables": [{"name": "t", "columns": ["a"], "rows": [[Infinity]]}], "charts": [], "report": null}',
        }
        for label, raw in invalid.items():
            with self.subTest(label=label):
                result = run("import os\nopen('/tmp/result.json', 'w').write(%r)\nos._exit(0)" % raw)
                self.assertEqual((result['status'], result.get('reason')), ('failed', 'result_invalid'), result)
                self.assertNotIn('result', result)

    def test_valid_chart_and_report_types_are_adopted(self):
        raw = '{"tables": [], "charts": [{"kind": "line", "title": "t", "x": ["a", "b"], "series": [{"name": "s", "values": [1, null]}]}], "report": "文"}'
        result = run("import os\nopen('/tmp/result.json', 'w').write(%r)\nos._exit(0)" % raw)
        self.assertEqual(result['status'], 'ok', result)
        self.assertEqual(result['result']['report'], '文')


class StageDeadlineTest(IsolationBase):
    """転送・投入・Pythonは、それぞれ各段階全体の期限。合算にせず、進捗(チャンクの到着)でリセットもしない。"""

    DEADLINES = {'transfer': 60, 'load': 60, 'margin': 20}

    def test_each_stage_has_its_own_budget_that_chunk_arrival_never_resets(self):
        # 転送(受信待ち)と投入は、チャンクごとに交互に進む。各段階の予算は、全体の合計で数え、リセットしない。
        clock = L.StageClock(1000, self.DEADLINES, 30)
        self.assertIsNone(clock.violation(1059))
        self.assertEqual(clock.violation(1061), 'stage_deadline_transfer')  # 受信開始から60秒
        clock = L.StageClock(1000, self.DEADLINES, 30)
        for index in range(10):  # 受信待ち(5秒)→投入(5秒)を10回繰り返す: 転送の合計50秒、投入の合計50秒
            clock.switch('load', 1000 + index * 10 + 5)
            clock.switch('transfer', 1000 + index * 10 + 10)
        self.assertEqual(clock.used, {'transfer': 50.0, 'load': 50.0})
        self.assertIsNone(clock.violation(1100 + 9))  # 転送の累計59秒 → 期限内(合算の119秒ではない)
        self.assertEqual(clock.violation(1100 + 11), 'stage_deadline_transfer')  # 累計61秒 → 超過(進捗があってもリセットされない)
        clock = L.StageClock(1000, self.DEADLINES, 30)
        clock.switch('load', 1001)
        self.assertIsNone(clock.violation(1060))
        self.assertEqual(clock.violation(1062), 'stage_deadline_load')  # 投入の累計が61秒
        clock = L.StageClock(1000, self.DEADLINES, 30)
        clock.switch('python', 1020)
        self.assertIsNone(clock.violation(1069))  # Python実行時間30秒 + 余裕20秒
        self.assertEqual(clock.violation(1071), 'stage_deadline_python')

    def test_transfer_deadline_counts_from_the_start_of_reception(self):
        # Djangoからの本文の受信に、すでに100秒かかった場合(転送の期限60秒を超過)。受信の開始時刻から数えるため、
        # コンテナの起動後は、監督プロセスの受信完了を待たずに、転送の期限超過として強制終了する。
        frames = L.encode_frames(make_header("emit_report('x')"), [])
        result = L.run_job(frames, ranges=TEST_RANGES, transfer_started=time.monotonic() - 100)
        self.assertEqual((result['status'], result['reason']), ('failed', 'stage_deadline_transfer'), result)
        self.assertNotIn('result', result)

    def test_truncated_input_fails_immediately_instead_of_waiting(self):
        frames = L.encode_frames(make_header("emit_report('x')"), [])[:-5]  # 終端フレームを欠く
        result = L.run_job(frames, ranges=TEST_RANGES)
        self.assertEqual((result['status'], result['reason']), ('failed', 'input_truncated'), result)
        self.assertNotIn('result', result)

    def test_slow_load_is_killed_at_the_load_deadline(self):
        views = [{'name': 'v_ai_shipment', 'columns': SHIPMENT_COLUMNS, 'expected_rows': 30_000, 'unique_key': 'id'}]
        rows = [[i, '1.000', 'x'] for i in range(30_000)]
        chunks = [(0, rows[i:i + 5000]) for i in range(0, 30_000, 5000)]
        result = run("emit_report('到達しない')", chunks=chunks, views=views, deadlines={'load': 0.01}, memory_mb=512)
        self.assertEqual((result['status'], result['reason']), ('failed', 'stage_deadline_load'), result)
        self.assertNotIn('result', result)


class CleanupLockTest(IsolationBase):
    """コンテナの削除が失敗・時間切れになっても、実行ロックは残さない。削除できていない間は、新しいジョブを受け付けない。"""

    def test_docker_command_timeouts_do_not_raise_out_of_cleanup(self):
        from unittest.mock import patch
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('docker', 1)):
            self.assertEqual(L.docker('rm', 'x', check=False).returncode, 124)
            self.assertFalse(L.remove_container('x'))
            with self.assertRaises(L.IsolationUnavailable):
                L.docker('ps')

    def test_failed_removal_releases_the_lock_and_blocks_new_jobs_until_cleaned(self):
        from unittest.mock import patch
        with patch.object(L, 'remove_container', return_value=False):
            first = run("emit_report('first')")
        self.assertEqual(first['status'], 'ok')  # 結果は完結している。後始末の失敗は、別に記録する
        self.assertFalse(first['cleanup']['ok'])
        self.assertTrue(leftover_containers())  # 実際に残っている
        with patch.object(L, 'remove_container', return_value=False):
            second = run("emit_report('second')")  # Busy(ロックが残った状態)にはならない
        self.assertEqual((second['status'], second['reason']), ('refused', 'cleanup_pending'))
        third = run("emit_report('third')")  # 削除できるようになれば、再試行で解消して実行できる
        self.assertEqual(third['status'], 'ok', third)
        self.assertTrue(third['cleanup']['ok'])
        self.assertEqual(L._PENDING_CLEANUP, set())

    def test_startup_sweep_failure_blocks_new_jobs(self):
        """起動時に孤児を削除できなかったら、受付を始めない(削除待ちとして記録し、解消するまでジョブを拒否する)。"""
        from unittest.mock import patch
        orphan = subprocess.run(
            ['docker', 'create', '--name', 'pmjob-orphan-test', '--label', f'{L.LABEL}=1', '--network', 'none', L.IMAGE],
            capture_output=True, text=True)
        self.assertEqual(orphan.returncode, 0, orphan.stderr)
        try:
            with patch.object(L, 'remove_container', return_value=False):
                self.assertEqual(L.sweep_leftovers(), 0)
                self.assertIn('pmjob-orphan-test', L._PENDING_CLEANUP)
                blocked = run("emit_report('x')")
            self.assertEqual((blocked['status'], blocked['reason']), ('refused', 'cleanup_pending'))
            self.assertTrue(leftover_containers())  # 残骸は、まだ残っている
            self.assertEqual(run("emit_report('after')")['status'], 'ok')  # 削除できれば解消して実行できる
            self.assertEqual(L._PENDING_CLEANUP, set())
        finally:
            subprocess.run(['docker', 'rm', '-f', 'pmjob-orphan-test'], capture_output=True)
            L._PENDING_CLEANUP.clear()

    def test_startup_sweep_refuses_to_start_when_listing_fails(self):
        from unittest.mock import patch
        failed = subprocess.CompletedProcess([], 1, '', 'daemon error')
        with patch.object(L, 'docker', return_value=failed), self.assertRaises(L.IsolationUnavailable):
            L.sweep_leftovers()

    def test_unexpected_exceptions_release_the_lock(self):
        from unittest.mock import patch
        with patch.object(L, 'preflight', side_effect=RuntimeError('想定外')), self.assertRaises(RuntimeError):
            run("emit_report('x')")
        self.assertEqual(run("emit_report('after')")['status'], 'ok')


class HttpApiTest(IsolationBase):
    """DjangoがHTTPで使う入口(開発では127.0.0.1のみ)。本番の範囲(設定画面と同じ)で入力を検証する。"""

    def test_health_job_range_size_and_busy_responses(self):
        import urllib.error
        import urllib.request

        server = L.ThreadingHTTPServer(('127.0.0.1', 0), L.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_address[1]}'

        def post(data, timeout=120):
            request = urllib.request.Request(base + '/v1/jobs', data=data, method='POST')
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    return response.status, json.load(response)
            except urllib.error.HTTPError as exc:
                return exc.code, json.load(exc)

        try:
            with urllib.request.urlopen(base + '/v1/health', timeout=60) as response:
                self.assertEqual(json.load(response)['status'], 'ready')
            ok_header = make_header("emit_report('http')", memory_mb=512, python_seconds=30)
            status, body = post(L.encode_frames(ok_header, []))
            self.assertEqual((status, body['status'], body['result']['report']), (200, 'ok', 'http'))
            # 設定画面の範囲外(メモリ256MB < 512MB)は、コンテナを作らずに拒否する(503)
            status, body = post(L.encode_frames(make_header("emit_report('x')", memory_mb=256), []))
            self.assertEqual((status, body['reason']), (503, 'isolation_unavailable'))
            # 空の本文は拒否する(413)
            self.assertEqual(post(b'')[0], 413)
            # 実行中に別のジョブが来たら、待たせずに429を返す
            slow = L.encode_frames(make_header("import time\ntime.sleep(6)\nemit_report('slow')", memory_mb=512, python_seconds=30), [])
            holder = threading.Thread(target=post, args=(slow,))
            holder.start()
            time.sleep(2)
            self.assertEqual(post(L.encode_frames(ok_header, []))[0], 429)
            holder.join()
        finally:
            server.shutdown()

    def test_large_job_is_streamed_over_http(self):
        import urllib.request

        server = L.ThreadingHTTPServer(('127.0.0.1', 0), L.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        views = [{'name': 'v_ai_shipment', 'columns': SHIPMENT_COLUMNS, 'expected_rows': 100_000, 'unique_key': 'id'}]
        rows = [[i, '1.000', 'x'] for i in range(100_000)]
        chunks = [(0, rows[i:i + 5000]) for i in range(0, 100_000, 5000)]
        header = make_header("emit_table('n', ['n'], con.sql('SELECT COUNT(*) FROM v_ai_shipment').fetchall())",
                             memory_mb=512, python_seconds=30, views=views)
        try:
            request = urllib.request.Request(f'http://127.0.0.1:{server.server_address[1]}/v1/jobs',
                                             data=L.encode_frames(header, chunks), method='POST')
            with urllib.request.urlopen(request, timeout=180) as response:
                body = json.load(response)
            self.assertEqual(body['status'], 'ok', body)
            self.assertEqual(body['result']['tables'][0]['rows'], [[100_000]])
            self.assertEqual(body['diagnostics']['rows_loaded'], {'v_ai_shipment': 100_000})
        finally:
            server.shutdown()

    def test_body_reception_has_a_whole_stage_deadline_that_progress_does_not_reset(self):
        import socket

        class ShortDeadlineHandler(L.Handler):
            transfer_deadline = 2

        server = L.ThreadingHTTPServer(('127.0.0.1', 0), ShortDeadlineHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        frames = L.encode_frames(make_header("emit_report('x')", memory_mb=512, python_seconds=30), [])

        def exchange(prefix, declared_length, dribble):
            with socket.create_connection(('127.0.0.1', server.server_address[1]), timeout=15) as connection:
                connection.sendall(b'POST /v1/jobs HTTP/1.1\r\nHost: x\r\nContent-Length: %d\r\n\r\n' % declared_length + prefix)
                for _ in range(dribble):  # 少しずつ送り続けても(進捗があっても)、受信開始から2秒で打ち切られる
                    time.sleep(0.8)
                    try:
                        connection.sendall(b'\x00')
                    except OSError:
                        break
                connection.settimeout(20)
                raw = b''
                while b'\r\n\r\n' not in raw or not raw.rstrip().endswith(b'}'):
                    piece = connection.recv(65536)
                    if not piece:
                        break
                    raw += piece
            head, _, body = raw.partition(b'\r\n\r\n')
            return head.split(b'\r\n')[0], json.loads(body or b'{}')

        try:
            # (a) ヘッダのフレームの途中で止まる: コンテナを作らずに、転送の期限超過(408)
            status_line, body = exchange(frames[:12], len(frames), 4)
            self.assertIn(b' 408 ', status_line)
            self.assertEqual(body['reason'], 'stage_deadline_transfer')
            self.assertEqual(leftover_containers(), [])
        finally:
            server.shutdown()

    def test_incomplete_body_is_not_adopted_even_if_the_container_finishes(self):
        """宣言した本文の長さに満たないまま、コンテナだけが完結しても、結果を採用しない(転送の期限超過)。"""
        import socket

        class ShortDeadlineHandler(L.Handler):
            transfer_deadline = 10

        server = L.ThreadingHTTPServer(('127.0.0.1', 0), ShortDeadlineHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        frames = L.encode_frames(make_header("emit_report('x')", memory_mb=512, python_seconds=30), [])
        try:
            with socket.create_connection(('127.0.0.1', server.server_address[1]), timeout=30) as connection:
                connection.sendall(b'POST /v1/jobs HTTP/1.1\r\nHost: x\r\nContent-Length: %d\r\n\r\n' % (len(frames) + 1000) + frames)
                connection.settimeout(30)
                raw = b''
                while not raw.rstrip().endswith(b'}'):
                    piece = connection.recv(65536)
                    if not piece:
                        break
                    raw += piece
            head, _, body = raw.partition(b'\r\n\r\n')
            self.assertIn(b' 408 ', head.split(b'\r\n')[0])
            payload = json.loads(body)
            self.assertEqual((payload['status'], payload['reason']), ('failed', 'stage_deadline_transfer'))
            self.assertNotIn('result', payload)
        finally:
            server.shutdown()


if __name__ == '__main__':
    unittest.main(verbosity=2)
