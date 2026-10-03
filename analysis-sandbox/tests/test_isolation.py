"""ジョブ用コンテナの隔離・資源制限・結果採否の検証(実Dockerが必要)。

開発専用。WSLのUbuntuでrootとして実行する:
  wsl.exe -d Ubuntu-24.04 -u root -- python3 -m unittest discover -s /mnt/d/pm/analysis-sandbox/tests -v

テスト用の「生成コード」は、このファイルに書いた攻撃を模したスクリプトで、コンテナの中だけで実行する(Windows・Djangoでは実行しない)。
"""
import json
import math
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
