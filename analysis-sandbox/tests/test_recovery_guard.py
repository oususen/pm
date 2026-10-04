"""復旧の読み取り確認で、証拠が一つでも欠けたら合格を返さない。WSLで実行する。"""
import importlib.util
import io
import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location('recovery_guard', Path(__file__).resolve().parents[1] / 'tools/recovery_guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class RecoveryEvidence(unittest.TestCase):
    def check(self, *, connection=guard.errno.ECONNREFUSED, docker=None, lock=None):
        output = io.StringIO()
        sock = MagicMock()
        sock.__enter__.return_value = sock
        sock.connect_ex.return_value = connection
        docker = docker or subprocess.CompletedProcess([], 0, stdout='')
        with (patch('builtins.open', MagicMock()), patch.object(guard.fcntl, 'flock', side_effect=lock),
              patch.object(guard.socket, 'socket', return_value=sock),
              patch.object(guard.subprocess, 'run', side_effect=docker if isinstance(docker, Exception) else None,
                           return_value=docker), patch.object(guard.sys, 'stdout', output),
              patch.object(guard.sys, 'stdin') as stdin):
            try:
                guard.main()
            except (RuntimeError, OSError, subprocess.SubprocessError):
                self.assertEqual(output.getvalue(), '')
                stdin.read.assert_not_called()
                return False
            stdin.read.assert_called_once_with(1)
            self.assertEqual(output.getvalue().strip(), '{"launcher_stopped": true, "containers_absent": true}')
            return True

    def test_launcher_lock_failure_has_no_confirmation(self):
        self.assertFalse(self.check(lock=BlockingIOError()))

    def test_live_or_unreachable_launcher_has_no_confirmation(self):
        for state in (0, guard.errno.ETIMEDOUT, guard.errno.EHOSTUNREACH):
            self.assertFalse(self.check(connection=state))

    def test_docker_failure_or_container_present_has_no_confirmation(self):
        for result in (subprocess.CalledProcessError(1, ['docker']), subprocess.TimeoutExpired(['docker'], 10),
                       subprocess.CompletedProcess([], 0, stdout='container-id\n')):
            self.assertFalse(self.check(docker=result))

    def test_all_evidence_is_required_before_holding_the_lock(self):
        self.assertTrue(self.check())
