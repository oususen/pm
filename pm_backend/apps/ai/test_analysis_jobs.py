"""2-C後半。Redisは開発用を使うが、AI・DB更新・Dockerは模擬する。専用のキーだけを掃除する。"""
import json
import threading
import time
from copy import deepcopy
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from ai import analysis_execution_views as views
from ai.services import analysis_job_service as jobs
from ai.services.analysis_codegen_service import make_bundle
from ai.services.analysis_execution_service import Deadline, ExecutionStopped, _execute
from ai.services.analysis_plan_store import AnalysisError

POLICY = SimpleNamespace(plan_cache_ttl_minutes=5, max_memory_mb=512, max_cpu_cores=1,
                         max_execution_seconds=60, max_fetch_rows=100000)


@override_settings(DEBUG=True, AI_ANALYSIS_LAUNCHER_URL='http://127.0.0.1:8091')
class JobTests(SimpleTestCase):
    def setUp(self):
        self.prefix_patch = patch.object(jobs.JobStore, 'prefix', 'test:analysis:jobs:' + uuid4().hex + ':')
        self.prefix_patch.start()
        self.addCleanup(self.prefix_patch.stop)
        self.store = jobs.JobStore()
        self.user = SimpleNamespace(pk=987006, is_authenticated=True)
        self.worker = jobs.worker_registration(uuid4().hex, jobs.current_code_version())
        self.store.client.set(self.store.worker_key, self.worker, ex=60)
        self.policy_patch = patch.object(jobs, 'get_analysis_execution_policy', return_value=POLICY)
        self.policy_patch.start()
        self.addCleanup(self.policy_patch.stop)
        proposal = {'datasets': [{'view': 'v_ai_shipment', 'fields': ['id', 'quantity']}],
                    'date_from': '2026-09-01', 'date_to': '2026-09-30', 'conditions': '指定期間の全行'}
        self.plan = self.store.plans.create(self.user.pk, proposal, 5)
        bundle = make_bundle([], 'emit_report("SECRET-CODE")', ['v_ai_shipment'])
        self.plan.update(status='data_approved', method_approved_at=datetime.now().isoformat(), data_approved_at=datetime.now().isoformat(),
                         preview={'datasets': [{'view': 'v_ai_shipment', 'rows': 3}], 'over_limit': False},
                         codegen={'status': 'code_approved', 'steps': [], 'python': bundle.python,
                                  'executed_code_sha256': bundle.executed_code_sha256, 'wrapper_version': bundle.wrapper_version,
                                  'trial': {'status': 'passed', 'executed_code_sha256': bundle.executed_code_sha256}})
        self.hash = bundle.executed_code_sha256
        self.save_plan()
        self.addCleanup(self.cleanup)

    def save_plan(self):
        self.store.client.set(self.store.plans._key(self.plan['id']), json.dumps(self.plan), ex=300)

    def cleanup(self):
        keys = list(self.store.client.scan_iter(self.store.prefix + '*'))
        if keys:
            self.store.client.delete(*keys)
        self.store.client.delete(self.store.plans._key(self.plan['id']))

    def submit(self):
        return self.store.submit(self.user, self.plan['id'], self.plan['revision'], self.hash)

    def process(self, job_id, execute=None):
        result = {'status': 'ok', 'run_id': 42,
                  'fetch': {'cleanup': {'db_connection': 'closed'}, 'fetched_rows': {'v_ai_shipment': 3}},
                  'launcher': {'cleanup': {'ok': True}, 'result': {'tables': [], 'charts': [], 'report': 'SECRET-RESULT'}}}
        def default(*args, **kwargs):
            kwargs['on_started'](42)
            return result
        self.run = MagicMock()
        with (patch.object(jobs, 'get_user_model') as users, patch.object(jobs, 'run_and_record', side_effect=execute or default) as run,
              patch.object(jobs, 'AIAnalysisRun') as model, patch.object(jobs.transaction, 'atomic')):
            users.return_value.objects.get.return_value = self.user
            model.objects.select_for_update.return_value.get.return_value = self.run
            jobs.process_job(self.store, job_id, self.worker)
            return run

    def test_submit_is_async_and_private_fields_not_returned(self):
        with patch.object(jobs, 'run_and_record') as execute:
            job = self.submit()
        execute.assert_not_called()
        self.assertEqual(job['status'], 'pending')
        self.assertFalse({'snapshot', 'token', 'owner_id', 'worker'} & set(job))
        self.assertIsNone(job['result'])
        self.assertNotIn('codegen', self.store.raw(job['id'])['snapshot'])
        self.assertNotIn('SECRET-CODE', json.dumps(self.store.raw(job['id'])))
        self.assertEqual(self.store.client.ttl(self.store.key(job['id'])), -1)
        self.assertLessEqual(self.store.client.ttl(self.store.plans._key(self.plan['id'])), 300)

    def test_concurrent_submit_only_one_is_accepted(self):
        barrier, responses = threading.Barrier(2), []
        def call():
            barrier.wait()
            try:
                responses.append(self.submit())
            except AnalysisError as exc:
                responses.append(exc.status_code)
        threads = [threading.Thread(target=call) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(5)
        self.assertEqual(sum(isinstance(r, dict) for r in responses), 1)
        self.assertTrue(any(r in (409, 429) for r in responses if isinstance(r, int)))

    def test_requires_worker_and_production_is_disabled(self):
        self.store.client.delete(self.store.worker_key)
        with self.assertRaises(AnalysisError) as error:
            self.submit()
        self.assertEqual(error.exception.status_code, 503)
        with override_settings(DEBUG=False), self.assertRaises(AnalysisError):
            jobs.execution_enabled()
        self.assertFalse(self.store.client.exists(self.store.active_key))

    def test_rejects_revision_approval_trial_hash_and_expiry(self):
        original = deepcopy(self.plan)
        changes = [lambda p: p.update(revision=2), lambda p: p.update(status='awaiting_data'),
                   lambda p: p.update(data_approved_at=None), lambda p: p['codegen']['trial'].update(status='failed'),
                   lambda p: p['codegen']['trial'].update(executed_code_sha256='wrong'),
                   lambda p: p['codegen'].update(python='emit_report("changed")'),
                   lambda p: p.update(expires_at=(datetime.now() - timedelta(seconds=1)).isoformat())]
        for change in changes:
            with self.subTest(change=change):
                modified = deepcopy(original)
                change(modified)
                self.store.client.set(self.store.plans._key(original['id']), json.dumps(modified), ex=300)
                with self.assertRaises(AnalysisError):
                    self.submit()
                self.assertFalse(self.store.client.exists(self.store.active_key))

    def test_other_user_cannot_read_or_cancel_and_expired_result_is_410(self):
        job = self.submit()
        for operation in (self.store.get, self.store.cancel):
            with self.assertRaises(AnalysisError) as error:
                operation(job['id'], self.user.pk + 1)
            self.assertEqual(error.exception.status_code, 404)
        self.store.client.delete(self.store.key(job['id']))
        with self.assertRaises(AnalysisError) as error:
            self.store.get(job['id'], self.user.pk)
        self.assertEqual(error.exception.status_code, 410)

    def test_worker_loss_is_unknown_and_slot_is_not_released(self):
        job = self.submit()
        self.store.client.delete(self.store.worker_key)
        self.assertEqual(self.store.get(job['id'], self.user.pk)['status'], 'unknown')
        self.assertEqual(self.store.client.get(self.store.active_key), job['id'])

    def test_success_result_is_cached_and_history_has_no_body(self):
        job = self.submit()
        self.process(job['id'])
        actual = self.store.get(job['id'], self.user.pk)
        self.assertEqual(actual['status'], 'success')
        self.assertEqual(actual['result']['report'], 'SECRET-RESULT')
        self.assertLessEqual(self.store.client.ttl(self.store.key(job['id'])), 300)
        self.assertFalse(self.store.client.exists(self.store.active_key))
        self.assertNotIn('snapshot', self.store.raw(job['id']))
        self.assertNotIn('SECRET', str(self.run.save.call_args))

    def test_cancel_before_execution_records_without_running(self):
        job = self.submit()
        self.store.cancel(job['id'], self.user.pk)
        with patch.object(jobs, 'record_not_run', return_value=SimpleNamespace(pk=41)) as record:
            execute = self.process(job['id'])
        execute.assert_not_called()
        self.assertEqual(record.call_args.args[2:4], ('cancelled', 'user_cancelled'))
        self.assertEqual(self.store.get(job['id'], self.user.pk)['status'], 'cancelled')

    def test_expired_plan_before_worker_records_and_does_not_run(self):
        job = self.submit()
        self.store.client.delete(self.store.plans._key(self.plan['id']))
        with patch.object(jobs, 'record_not_run', return_value=SimpleNamespace(pk=41)):
            execute = self.process(job['id'])
        execute.assert_not_called()
        self.assertEqual(self.store.get(job['id'], self.user.pk)['status'], 'expired')

    def test_template_plan_is_checked_at_accept_with_the_confirmation_and_not_accepted_when_unavailable(self):
        from ai.services.analysis_template_reuse_service import TemplateUnavailable
        with patch.object(jobs, 'check_plan_template') as check:
            job = self.store.submit(self.user, self.plan['id'], self.plan['revision'], self.hash, 9)
        self.assertEqual(job['status'], 'pending')
        args, kwargs = check.call_args
        self.assertEqual((args[0]['id'], args[1], args[2], kwargs), (self.plan['id'], self.user, 9, {'accepting': True}))
        self.store.client.delete(self.store.active_key)
        with patch.object(jobs, 'check_plan_template', side_effect=TemplateUnavailable()):
            with self.assertRaises(AnalysisError) as error:
                self.store.submit(self.user, self.plan['id'], self.plan['revision'] + 1, self.hash)
        self.assertEqual(error.exception.status_code, 409)

    def test_template_plan_refused_at_accept_leaves_no_job_or_active_key(self):
        from ai.services.analysis_template_reuse_service import TemplateUnavailable
        with patch.object(jobs, 'check_plan_template', side_effect=TemplateUnavailable()):
            with self.assertRaises(AnalysisError):
                self.submit()
        self.assertFalse(self.store.client.exists(self.store.active_key))
        self.assertEqual(list(self.store.client.scan_iter(self.store.prefix + 'job:*')), [])

    def test_template_that_became_unavailable_before_the_worker_starts_is_recorded_and_not_run(self):
        from ai.services.analysis_template_reuse_service import TemplateUnavailable
        job = self.submit()
        with patch.object(jobs, 'check_plan_template', side_effect=TemplateUnavailable()) as check,                 patch.object(jobs, 'record_not_run', return_value=SimpleNamespace(pk=41)) as record:
            execute = self.process(job['id'])
        execute.assert_not_called()
        self.assertEqual(check.call_args.kwargs, {'accepting': False})
        self.assertEqual(record.call_args.args[2:4], ('failed', 'template_unavailable'))
        actual = self.store.get(job['id'], self.user.pk)
        self.assertEqual((actual['status'], actual['reason']), ('failed', 'template_unavailable'))
        self.assertEqual(actual['cleanup'], {'db_connection': 'not_started', 'container': 'not_started'})
        self.assertFalse(self.store.client.exists(self.store.active_key))

    def test_cancel_racing_success_discards_result(self):
        job = self.submit()
        def execute(*args, **kwargs):
            kwargs['on_started'](42)
            self.store.cancel(job['id'], self.user.pk)
            return {'status': 'ok', 'run_id': 42, 'fetch': {'cleanup': {'db_connection': 'closed'}},
                    'launcher': {'cleanup': {'ok': True}, 'result': {'report': 'NEVER-ADOPT'}}}
        self.process(job['id'], execute)
        actual = self.store.get(job['id'], self.user.pk)
        self.assertEqual(actual['status'], 'cancelled')
        self.assertIsNone(actual['result'])
        self.assertEqual(self.run.status, 'cancelled')

    def test_changed_revision_after_handoff_records_failure_without_execution(self):
        job = self.submit()
        plan = self.store.plans.get(self.plan['id'], self.user.pk)
        plan['revision'] += 1
        self.store.client.set(self.store.plans._key(plan['id']), json.dumps(plan), ex=300)
        with patch.object(jobs, 'record_not_run', return_value=SimpleNamespace(pk=41)) as record:
            execute = self.process(job['id'])
        execute.assert_not_called()
        self.assertEqual(record.call_args.args[2], 'failed')
        self.assertEqual(self.store.get(job['id'], self.user.pk)['status'], 'failed')

    def test_cleanup_pending_blocks_next_run_and_late_completion_releases(self):
        job = self.submit()
        callbacks = []
        def execute(*args, **kwargs):
            kwargs['on_started'](42)
            callbacks.append(kwargs['on_cleanup_done'])
            raise self.stopped('stage_deadline_fetch', {'db_connection': 'pending'})
        self.process(job['id'], execute)
        self.assertEqual(self.store.client.get(self.store.active_key), job['id'])
        with patch.object(jobs, 'AIAnalysisRun') as model, patch.object(jobs.transaction, 'atomic'):
            model.objects.select_for_update.return_value.get.return_value = self.run
            callbacks[0]('closed')
        self.assertEqual(self.run.cleanup['db_connection'], 'closed')
        self.assertFalse(self.store.client.exists(self.store.active_key))

    @staticmethod
    def stopped(reason, cleanup, sent=False):
        exc = ExecutionStopped(reason, 'SECRET-DETAIL')
        exc.cleanup, exc.progress = cleanup, {'transmit_started': sent}
        return exc

    def test_cancellation_after_transfer_checks_launcher_cleanup(self):
        job = self.submit()
        def execute(*args, **kwargs):
            raise self.stopped('user_cancelled', {'db_connection': 'closed'}, True)
        with patch.object(jobs.ExecutionControl, 'launcher', return_value=(200, {'done': True, 'cleanup': 'closed'})):
            self.process(job['id'], execute)
        actual = self.store.get(job['id'], self.user.pk)
        self.assertEqual(actual['cleanup']['container'], 'closed')
        self.assertNotIn('SECRET', json.dumps(actual))

    def test_unconfirmed_container_does_not_release_slot(self):
        job = self.submit()
        def execute(*args, **kwargs):
            raise self.stopped('launcher_unreachable', {'db_connection': 'closed'}, True)
        with patch.object(jobs.ExecutionControl, 'launcher', return_value=(404, {})):
            self.process(job['id'], execute)
        self.assertEqual(self.store.get(job['id'], self.user.pk)['cleanup']['container'], 'unconfirmed')
        self.assertEqual(self.store.client.get(self.store.active_key), job['id'])

    def test_history_save_failure_never_publishes_result(self):
        job = self.submit()
        model = MagicMock()
        model.objects.select_for_update.return_value.get.return_value.save.side_effect = RuntimeError('SECRET-DB')
        result = {'status': 'ok', 'run_id': 42, 'fetch': {'cleanup': {'db_connection': 'closed'}},
                  'launcher': {'cleanup': {'ok': True}, 'result': {'report': 'SECRET-RESULT'}}}
        with (patch.object(jobs, 'get_user_model') as users, patch.object(jobs, 'run_and_record', return_value=result),
              patch.object(jobs, 'AIAnalysisRun', model), patch.object(jobs.transaction, 'atomic')):
            users.return_value.objects.get.return_value = self.user
            with self.assertRaises(RuntimeError):
                jobs.process_job(self.store, job['id'], self.worker)
        self.assertIsNone(self.store.get(job['id'], self.user.pk)['result'])
        self.assertEqual(self.store.client.get(self.store.active_key), job['id'])


class CancellationTests(SimpleTestCase):
    def test_os_lock_prevents_second_worker_even_without_redis_lease(self):
        namespace = 'test-lock:' + uuid4().hex
        first = jobs.acquire_worker_lock(namespace)
        try:
            with self.assertRaises(AnalysisError):
                jobs.acquire_worker_lock(namespace)
        finally:
            first.close()
        jobs.acquire_worker_lock(namespace).close()

    @override_settings(DEBUG=True, AI_ANALYSIS_LAUNCHER_URL='http://127.0.0.1:8091')
    def test_worker_requires_confirmed_idle_health_and_releases_startup_lock(self):
        for health in ({'status': 'ready'}, {'status': 'ready', 'busy': True}, {'status': 'other', 'busy': False}):
            with (patch.object(jobs, 'JobStore') as store, patch.object(jobs, 'acquire_worker_lock') as lock,
                  patch.object(jobs.http.client, 'HTTPConnection') as connection):
                response = connection.return_value.getresponse.return_value
                response.status, response.read.return_value = 200, json.dumps(health).encode()
                with self.assertRaises(AnalysisError):
                    jobs.worker_loop()
                store.return_value.client.set.assert_not_called()
                lock.return_value.close.assert_called_once()

    def test_db_wait_cancel_does_not_close_live_connection_or_adopt_late_rows(self):
        event, release = threading.Event(), threading.Event()
        def check():
            if event.is_set():
                raise ExecutionStopped('user_cancelled', '中止')
        cursor = MagicMock()
        cursor.fetchall.side_effect = lambda: release.wait(2) or [('LATE',)]
        deadline = Deadline(2, 'stage_deadline_fetch', SimpleNamespace(check=check))
        threading.Timer(0.1, event.set).start()
        try:
            with self.assertRaises(ExecutionStopped) as stopped:
                _execute(cursor, deadline, 'SELECT 1', [])
            self.assertEqual(stopped.exception.reason, 'user_cancelled')
            self.assertEqual(len(deadline.abandoned), 1)
            self.assertTrue(deadline.abandoned[0].is_alive())
            cursor.close.assert_not_called()
        finally:
            release.set()
            for worker in deadline.abandoned:
                worker.join(2)


class ExecutionAPITests(SimpleTestCase):
    def setUp(self):
        # 入力・既存処理の回帰。実効権限はtest_analysis_permissionsで実モデルを検証する。
        permissions = patch('ai.analysis_permissions._has_resource_permission', return_value=True)
        permissions.start()
        self.addCleanup(permissions.stop)

    @override_settings(ALLOWED_HOSTS=['testserver'])
    def test_history_is_paginated_and_owner_or_admin_ui_selection_is_forwarded(self):
        user = SimpleNamespace(pk=44, is_authenticated=True)
        with patch.object(views, '_has_resource_permission', return_value=True), patch.object(views, 'visible_runs', return_value=list(range(51))) as visible, patch.object(views, 'serialize_run', side_effect=lambda row: {'id': row}):
            for all_users in ('false', 'true'):
                request = APIRequestFactory().get('/', {'page': 2, 'include_all': all_users})
                force_authenticate(request, user)
                response = views.AIAnalysisRunsView.as_view()(request)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['count'], 51)
                self.assertEqual(response.data['results'], [{'id': 50}])
                visible.assert_called_with(user, all_users == 'true')
            request = APIRequestFactory().get('/', {'page': 3})
            force_authenticate(request, user)
            self.assertEqual(views.AIAnalysisRunsView.as_view()(request).status_code, 404)

    def request(self, view, method='post', data=None, **kwargs):
        factory = APIRequestFactory()
        request = factory.get('/') if method == 'get' else factory.post('/', data or {}, format='json')
        force_authenticate(request, SimpleNamespace(pk=44, is_authenticated=True))
        return view.as_view()(request, **kwargs)

    def test_execute_only_accepts_revision_and_hash(self):
        with patch.object(views, 'JobStore') as store:
            store.return_value.submit.return_value = {'status': 'pending'}
            response = self.request(views.AIAnalysisExecuteView, data={'revision': 1, 'executed_code_sha256': 'hash'}, plan_id=uuid4())
            self.assertEqual(response.status_code, 202)
            response = self.request(views.AIAnalysisExecuteView, data={'revision': 1, 'code': 'NEVER'}, plan_id=uuid4())
            self.assertEqual(response.status_code, 400)
            self.assertEqual(store.return_value.submit.call_count, 1)

    def test_job_and_cancel_use_authenticated_owner(self):
        with patch.object(views, 'JobStore') as store:
            store.return_value.get.return_value = {'status': 'running'}
            store.return_value.cancel.return_value = {'status': 'cancel_requested'}
            job_id = uuid4()
            self.assertEqual(self.request(views.AIAnalysisJobView, 'get', job_id=job_id).status_code, 200)
            store.return_value.get.assert_called_with(str(job_id), 44)
            self.assertEqual(self.request(views.AIAnalysisJobCancelView, job_id=job_id).status_code, 202)
            store.return_value.cancel.assert_called_with(str(job_id), 44)
