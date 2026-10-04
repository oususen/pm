"""ワーカー起動版・拒否・JST。Redisは専用キー、取得・AI・Dockerは呼ばない。"""
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from ai import analysis_execution_views as views
from ai.services import analysis_job_service as jobs, analysis_worker_identity as identity
from ai.services.analysis_plan_store import AnalysisError
from ai import test_analysis_jobs as job_cases


@override_settings(DEBUG=True, AI_ANALYSIS_LAUNCHER_URL='http://127.0.0.1:8091')
class WorkerVersionTests(SimpleTestCase):
    setUp = job_cases.JobTests.setUp
    save_plan = job_cases.JobTests.save_plan
    cleanup = job_cases.JobTests.cleanup
    submit = job_cases.JobTests.submit

    def test_same_version_is_accepted_without_executing_in_request(self):
        with patch.object(jobs, 'run_and_record') as run:
            job = self.submit()
        run.assert_not_called()
        self.assertEqual(job['status'], 'pending')
        self.assertEqual(self.store.raw(job['id'])['worker'], self.worker)
        self.assertNotIn('code_version', json.dumps(job))

    def test_old_missing_malformed_version_rejects_without_mutating_or_history(self):
        before = self.store.client.get(self.store.plans._key(self.plan['id']))
        for raw in (uuid4().hex, 'SECRET', '[]', '{}', identity.worker_registration('old', '0' * 64),
                    json.dumps({'id': 'old', 'code_version': None})):
            with self.subTest(raw=raw):
                self.store.client.set(self.store.worker_key, raw, ex=60)
                with patch.object(jobs, 'run_and_record') as run, patch.object(jobs, 'record_not_run') as record:
                    with self.assertRaises(jobs.WorkerStaleError) as error:
                        self.submit()
                    self.assertEqual(error.exception.reason, 'worker_stale')
                    self.assertEqual(str(error.exception.detail), '専用ワーカーを再起動してください。')
                    self.assertNotIn('SECRET', str(error.exception.detail))
                    run.assert_not_called()
                    record.assert_not_called()
                self.assertEqual(self.store.client.get(self.store.plans._key(self.plan['id'])), before)
                self.assertIsNone(self.store.client.get(self.store.active_key))
                self.assertEqual(set(self.store.client.scan_iter(self.store.prefix + '*')), {self.store.worker_key})

    def test_current_disk_version_is_read_on_each_submission_not_cached_web_version(self):
        with patch.object(jobs, 'current_code_version', return_value='changed'):
            with self.assertRaises(jobs.WorkerStaleError):
                self.submit()
        self.assertIsNone(self.store.client.get(self.store.active_key))

    def test_unreadable_current_code_is_not_accepted(self):
        with patch.object(jobs, 'current_code_version', side_effect=OSError('SECRET')):
            with self.assertRaises(jobs.WorkerStaleError):
                self.submit()
        self.assertIsNone(self.store.client.get(self.store.active_key))

    def test_api_reason_and_availability_are_fixed_and_do_not_leak_metadata(self):
        self.store.client.set(self.store.worker_key, 'SECRET-old-worker', ex=60)
        factory = APIRequestFactory()
        with patch.object(views, 'JobStore', return_value=self.store), patch('ai.analysis_permissions._has_resource_permission', return_value=True):
            request = factory.post('/', {'revision': self.plan['revision'], 'executed_code_sha256': self.hash}, format='json')
            force_authenticate(request, self.user)
            response = views.AIAnalysisExecuteView.as_view()(request, plan_id=self.plan['id'])
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.data, {'reason': 'worker_stale', 'detail': '専用ワーカーを再起動してください。'})
            request = factory.get('/')
            force_authenticate(request, self.user)
            response = views.AIAnalysisExecutionOptionsView.as_view()(request)
            self.assertFalse(response.data['ready'])
            self.assertEqual(response.data['reason'], 'worker_stale')
            self.assertEqual(response.data['notice'], '専用ワーカーを再起動してください。')
            self.assertNotIn('SECRET', str(response.data))

    def test_heartbeat_keeps_startup_version_after_disk_changes(self):
        self.store.client.delete(self.store.worker_key)
        connection = MagicMock()
        connection.getresponse.return_value.status = 200
        connection.getresponse.return_value.read.return_value = b'{"status":"ready","busy":false}'
        real_version = jobs._LOADED_CODE_VERSION
        stop = threading.Event()
        registrations = []
        original_set = self.store.client.set
        def register(key, value, **kwargs):
            registrations.append(value)
            return original_set(key, value, **kwargs)
        def renewal(script, count, key, raw, seconds=None):
            self.assertEqual(json.loads(raw)['code_version'], real_version)
            self.assertEqual(self.store.client.get(key), raw)
            if seconds is None:
                return self.store.client.delete(key)
            stop.set()
            return 1
        with (patch.object(jobs, 'JobStore', return_value=self.store), patch.object(jobs, 'acquire_worker_lock') as lock,
              patch.object(jobs.http.client, 'HTTPConnection', return_value=connection),
              patch.object(self.store.client, 'set', side_effect=register),
              patch.object(self.store.client, 'eval', side_effect=renewal),
              patch.object(jobs, 'current_code_version', side_effect=[real_version, 'changed']) as version,
              patch.object(jobs, 'HEARTBEAT_SECONDS', 0.01)):
            jobs.worker_loop(stop)
            version.assert_called_once()
            jobs._PROCESS_LOCKS.remove(lock.return_value)
        self.assertEqual(len(registrations), 1)
        self.assertEqual(json.loads(registrations[0])['code_version'], real_version)

    def test_old_loaded_worker_cannot_register_new_disk_version(self):
        with patch.object(jobs, 'current_code_version', return_value='changed'), patch.object(jobs, 'JobStore') as store:
            with self.assertRaises(jobs.WorkerStaleError):
                jobs.worker_loop()
            store.assert_not_called()

    def test_worker_jst_check_precedes_registration(self):
        with patch.object(jobs, 'ensure_jst_clock', side_effect=ValueError('SECRET')), patch.object(jobs, 'JobStore') as store:
            with self.assertRaises(AnalysisError) as error:
                jobs.worker_loop()
            self.assertNotIn('SECRET', str(error.exception.detail))
            store.assert_not_called()
        for configuration in ({'USE_TZ': True}, {'TIME_ZONE': 'UTC'}):
            with override_settings(**configuration), patch.object(jobs, 'JobStore') as store:
                with self.assertRaises(AnalysisError):
                    jobs.worker_loop()
                store.assert_not_called()


class WorkerIdentityTests(SimpleTestCase):
    def test_each_declared_source_is_present_and_influences_the_hash(self):
        original = identity.current_code_version()
        self.assertEqual(len(original), 64)
        for name in identity.WORKER_FILES:
            self.assertTrue((identity.SOURCE_ROOT / name).is_file())
        original_read = Path.read_bytes
        for name in identity.WORKER_FILES:
            def changed(path, target=name):
                data = original_read(path)
                return data + b'changed' if path == identity.SOURCE_ROOT / target else data
            with self.subTest(name=name), patch.object(Path, 'read_bytes', changed):
                self.assertNotEqual(identity.current_code_version(), original)

    def test_jst_naive_clock_is_accepted_and_utc_is_rejected(self):
        for hours, accepted in ((9, True), (0, False)):
            now = MagicMock()
            now.tzinfo = None
            now.astimezone.return_value.utcoffset.return_value = timedelta(hours=hours)
            with patch.object(identity, 'datetime') as clock:
                clock.now.return_value = now
                if accepted:
                    identity.ensure_jst_clock()
                else:
                    with self.assertRaises(ValueError):
                        identity.ensure_jst_clock()
        identity.ensure_jst_clock()
        self.assertIsNone(datetime.now().tzinfo)

    def test_aware_clock_is_not_allowed(self):
        with patch.object(identity, 'datetime') as clock:
            clock.now.return_value = datetime(2026, 10, 4, tzinfo=timezone.utc)
            with self.assertRaises(ValueError):
                identity.ensure_jst_clock()

    def test_status_script_reuses_version_check_and_keeps_utf8_bom(self):
        script = Path(__file__).resolve().parents[3] / 'scripts' / 'analysis-dev.ps1'
        data = script.read_bytes()
        self.assertTrue(data.startswith(b'\xef\xbb\xbf'))
        source = data.decode('utf-8-sig')
        self.assertIn('worker_version_matches(worker, current_code_version())', source)
        self.assertIn('if ($state.worker_stale)', source)
        self.assertIn('専用ワーカーを再起動してください。', source)
        guidance = '起動できない場合は、PCの時刻帯が日本標準時か確認してください'
        status = source.split('function Show-Status {', 1)[1].split('function Start-Dev {', 1)[0]
        start = source.split('function Start-Dev {', 1)[1].split('function Stop-Dev {', 1)[0]
        failure = start.split("$ok = Wait-For '専用ワーカー'", 1)[1].split("Write-Host '  専用ワーカー: 起動しました。'", 1)[0]
        self.assertIn(guidance, status)
        self.assertIn(guidance, start.split('# 1. Redis', 1)[0])
        self.assertIn(guidance, failure)
