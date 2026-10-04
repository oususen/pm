"""2-C後半の中止HTTPを実Dockerで確認する。生成Pythonはコンテナ内だけで実行する。"""
import http.client
import json
import secrets
import socket
import sys
import threading
import time
import unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'launcher'))
import launcher as L


class CancelHttpTests(unittest.TestCase):
    def setUp(self):
        self.server = L.ThreadingHTTPServer(('127.0.0.1', 0), L.Handler)
        self.port = self.server.server_address[1]
        self.serving = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.serving.start()
        self.job_id, self.token = str(uuid4()), secrets.token_hex(32)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.serving.join(2)
        self.assertEqual(L.docker('ps', '-aq', '--filter', f'label={L.LABEL}=1').stdout.split(), [])

    def request(self, method, suffix='', token=None, job_id=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=40)
        try:
            connection.request(method, '/v1/jobs/' + (job_id or self.job_id) + suffix,
                               body=b'' if method == 'POST' else None, headers={'X-Analysis-Control': token or self.token})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def start(self, code, partial=False):
        header = {'limits': {'memory_mb': 512, 'cpus': 1.0, 'python_seconds': 30, 'duckdb_memory_limit_mb': 256, 'threads': 1},
                  'code': code, 'views': []}
        body = L.encode_frames(header, [])
        output = {}
        def run():
            connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=50)
            try:
                connection.putrequest('POST', '/v1/jobs')
                connection.putheader('Content-Length', str(len(body)))
                connection.putheader('X-Analysis-Job', self.job_id)
                connection.putheader('X-Analysis-Control', self.token)
                connection.endheaders()
                connection.send(body[:-5] if partial else body)
                response = connection.getresponse()
                output.update(status=response.status, result=json.loads(response.read()))
            finally:
                connection.close()
        thread = threading.Thread(target=run)
        thread.start()
        for _ in range(100):
            status, _ = self.request('GET')
            if status == 200:
                return thread, output
            time.sleep(0.05)
        self.fail('ジョブが登録されませんでした')

    def assert_cancelled(self, thread, output, expected_cleanup=('closed', 'not_started')):
        thread.join(45)
        self.assertFalse(thread.is_alive())
        self.assertNotIn('result', output['result'])
        self.assertEqual(output['result']['reason'], 'user_cancelled')
        status, state = self.request('GET')
        self.assertEqual(status, 200)
        self.assertTrue(state['done'])
        # 中止が作成より先か後かはHTTP受付との競合で変わる。未作成と削除完了を混同しない。
        self.assertIn(state['cleanup'], expected_cleanup)
        self.assertEqual(state['cleanup'], output['result']['cleanup']['state'])
        self.assertTrue(output['result']['cleanup']['ok'])
        self.assertEqual(self.request('POST', '/cancel')[0], 409)

    def test_cancel_running_python_deletes_container_and_rejects_partial_result(self):
        thread, output = self.start("emit_report('PARTIAL')\nwhile True: pass")
        # preflight後にコンテナが稼働したことを確認してから中止する。
        until = time.monotonic() + 30
        while time.monotonic() < until:
            if L.docker('ps', '-q', '--filter', f'label={L.LABEL}=1').stdout.strip():
                break
            time.sleep(0.1)
        self.assertLess(time.monotonic(), until)
        while time.monotonic() < until and self.request('GET')[1].get('stage') != 'python':
            time.sleep(0.1)
        self.assertEqual(self.request('GET')[1]['stage'], 'python')
        self.assertEqual(self.request('POST', '/cancel')[0], 202)
        self.assert_cancelled(thread, output, expected_cleanup=('closed',))

    def test_cancel_incomplete_transfer_unblocks_body_and_prevents_python(self):
        thread, output = self.start("emit_report('MUST-NOT-RUN')", partial=True)
        self.assertEqual(self.request('POST', '/cancel')[0], 202)
        self.assert_cancelled(thread, output)

    def test_cancel_during_preflight_does_not_start_a_container(self):
        entered, release = threading.Event(), threading.Event()
        original = L.preflight
        def preflight(*args):
            entered.set()
            release.wait(10)
            return original(*args)
        with patch.object(L, 'preflight', side_effect=preflight), patch.object(L, 'create_command', wraps=L.create_command) as create:
            thread, output = self.start("emit_report('MUST-NOT-RUN')")
            self.assertTrue(entered.wait(10))
            self.assertEqual(self.request('POST', '/cancel')[0], 202)
            release.set()
            self.assert_cancelled(thread, output, expected_cleanup=('not_started',))
            create.assert_not_called()

    def test_wrong_token_and_other_id_cannot_cancel_the_job(self):
        thread, output = self.start("while True: pass")
        self.assertEqual(self.request('POST', '/cancel', token='0' * 64)[0], 404)
        self.assertEqual(self.request('POST', '/cancel', job_id=str(uuid4()))[0], 404)
        self.assertEqual(self.request('POST', '/cancel')[0], 202)
        self.assert_cancelled(thread, output)

    def test_cleanup_failure_is_not_confirmation(self):
        with patch.object(L, 'run_job', return_value={'status': 'failed', 'reason': 'user_cancelled', 'cleanup': {'ok': False}}):
            thread, output = self.start("emit_report('x')")
            thread.join(10)
        self.assertEqual(self.request('GET')[1]['cleanup'], 'unconfirmed')

    def test_unexpected_launcher_error_is_not_confirmation(self):
        with patch.object(L, 'run_job', side_effect=RuntimeError('SECRET')):
            thread, output = self.start("emit_report('x')")
            thread.join(10)
        self.assertEqual(output['status'], 500)
        self.assertEqual(self.request('GET')[1]['cleanup'], 'unconfirmed')
        self.assertNotIn('SECRET', json.dumps(output))


if __name__ == '__main__':
    unittest.main()
