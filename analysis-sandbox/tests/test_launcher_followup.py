"""launcherの早期拒否・制御トークンを模擬Dockerで検証。Dockerも生成Pythonも実行しない。"""
import http.client
import json
import secrets
import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'launcher'))
import launcher as L


class LauncherFollowup(unittest.TestCase):
    def test_non_ascii_token_is_not_found(self):
        control = L.JobControl(str(uuid4()), secrets.token_hex(32), None)
        with patch.object(L, '_CONTROL', control):
            self.assertIsNone(L.find_control(control.job_id, '日本語'))
            self.assertIsNone(L.find_control(control.job_id, 'é'))
            self.assertIs(L.find_control(control.job_id, control.token), control)

    def test_refusal_before_header_and_cleanup_pending_proves_not_started(self):
        for source in (iter([]), iter([b'H\x00\x00\x00\x01!'])):
            with patch.object(L, 'retry_pending_cleanup', return_value=[]), patch.object(L, 'docker') as docker:
                result = L.run_job(source)
            self.assertEqual(result['cleanup']['state'], 'not_started')
            docker.assert_not_called()
        with patch.object(L, 'retry_pending_cleanup', return_value=['old']), patch.object(L, 'docker') as docker:
            result = L.run_job(iter([]))
        self.assertEqual(result['cleanup']['state'], 'not_started'); docker.assert_not_called()

    def test_docker_create_response_lost_still_attempts_cleanup(self):
        header = L.frame(b'H', json.dumps({'limits': {'memory_mb':512, 'cpus':1, 'python_seconds':30, 'threads':1}}).encode())
        def docker(*args, **kwargs):
            if args[0] == 'create': raise L.IsolationUnavailable('timeout')
            return SimpleNamespace(stdout='[]')
        with (patch.object(L, 'retry_pending_cleanup', return_value=[]), patch.object(L, 'preflight'),
              patch.object(L, 'pinned_image_id', return_value='sha256:x'), patch.object(L, 'docker', side_effect=docker),
              patch.object(L, 'remove_container', return_value=True) as remove):
            result = L.run_job(iter([header]))
        remove.assert_called_once()
        self.assertEqual(result['cleanup']['state'], 'closed')

    def test_same_id_busy_does_not_claim_prior_job_not_started(self):
        control = L.JobControl(str(uuid4()), secrets.token_hex(32), None)
        server = L.ThreadingHTTPServer(('127.0.0.1', 0), L.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with patch.object(L, '_CONTROL', control):
                for job_id, expected in ((control.job_id, 'unconfirmed'), (str(uuid4()), 'not_started')):
                    connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=10)
                    try:
                        # 拒否はヘッダ時点で返る。本文をまだ送らず、Windowsの未読本文RSTと分けて応答を検証する。
                        connection.putrequest('POST', '/v1/jobs')
                        connection.putheader('Content-Length', '1')
                        connection.putheader('X-Analysis-Job', job_id)
                        connection.putheader('X-Analysis-Control', control.token)
                        connection.endheaders()
                        response = connection.getresponse()
                        self.assertEqual(response.status, 409)
                        self.assertEqual(json.loads(response.read())['cleanup']['state'], expected)
                    finally: connection.close()
        finally:
            server.shutdown(); server.server_close(); thread.join(2)
