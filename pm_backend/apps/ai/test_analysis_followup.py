"""承認された2-C追加修正。実AI・生成コードのWindows実行・Docker変更は行わない。"""
import json
import socket
import threading
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import UserPermission
from ai import analysis_execution_views as views
from ai.services import analysis_codegen_service as cg, analysis_guard_runtime as guard
from ai.services import analysis_job_service as jobs, analysis_recovery_service as recovery
from ai.services import analysis_run_service as runs, analysis_execution_service as execution
from ai.services.analysis_plan_store import AnalysisError
from ai.test_analysis_codegen import CodegenBase, GOOD_PYTHON, GOOD_STEPS, OWNER, VIEWS
from ai import test_analysis_jobs as job_cases


class OutputChecks(SimpleTestCase):
    def test_static_chart_literals_keywords_and_signed_numbers(self):
        for value in ('"月"', '123', '-1', 'None'):
            # Noneは依頼された静的検査の対象外。実行時に拒否する。
            source = f'emit_chart("bar", "t", {value}, [])'
            if value != 'None':
                self.assertIn('chart_x_not_list', guard.validate_python(source))
        self.assertIn('chart_x_not_list', guard.validate_python('emit_chart(kind="bar", title="t", x="月", series=[])'))
        for x in ('["8月", "9月"]', '[str(i) for i in [8,9]]', 'x'):
            self.assertEqual(guard.validate_python(f'emit_chart("bar", "t", {x}, [])'), [])

    def test_static_table_string_columns_and_rows(self):
        self.assertIn('table_columns_not_list', guard.validate_python('emit_table("t", "列", [])'))
        self.assertIn('table_rows_not_list', guard.validate_python('emit_table(name="t", columns=["列"], rows="行")'))
        self.assertEqual(guard.validate_python('emit_table("t", ["列"], [[1]])'), [])

    def test_trusted_output_wrappers_reject_dynamic_shapes_without_forwarding(self):
        table, chart = MagicMock(), MagicMock()
        emit_table, emit_chart = guard._checked_outputs(table, chart)
        for x, series in [('月', []), (['8','9'], [{'values':[1]}]), ([], 'SECRET')]:
            with self.assertRaises(guard.GuardError) as error:
                emit_chart('bar', 'SECRET', x, series)
            self.assertNotIn('SECRET', str(error.exception))
        chart.assert_not_called()
        for columns, rows in [('列', []), (['列'], '行'), (['列'], [[1,2]])]:
            with self.assertRaises(guard.GuardError):
                emit_table('t', columns, rows)
        table.assert_not_called()
        emit_chart('bar', 't', ['8','9'], [{'name':'数量', 'values':[1,None]}])
        emit_table('t', ['列'], [[1]])
        self.assertEqual((chart.call_count, table.call_count), (1, 1))

    def test_connect_refusal_has_no_transmission_but_header_failure_does(self):
        for where, started in [('connect', False), ('endheaders', True)]:
            connection = MagicMock()
            getattr(connection, where).side_effect = ConnectionRefusedError('SECRET')
            connection.getresponse.side_effect = OSError()
            timing = {}
            with patch.object(execution.http.client, 'HTTPConnection', return_value=connection):
                with self.assertRaises(execution.ExecutionStopped):
                    execution._transmit('127.0.0.1', 8091, 5, iter([]), execution.Deadline(60, 'stage_deadline_transfer'), 60, timing)
            self.assertEqual(timing.get('transmit_started', False), started)

    def test_tuple_outputs_are_normalized_without_changing_the_input(self):
        table, chart = MagicMock(), MagicMock()
        emit_table, emit_chart = guard._checked_outputs(table, chart)
        for columns in (['id', 'q'], ('id', 'q')):
            for rows in ([(1, 2), [3, 4]], ((1, 2), [3, 4])):
                emit_table('t', columns, rows)
                table.assert_called_with('t', ['id', 'q'], [[1, 2], [3, 4]])
                self.assertIsNot(table.call_args.args[1], columns)
                self.assertIsInstance(rows[0], tuple)
        for x in (['a', 'b'], ('a', 'b')):
            for values in ([1, None], (1, None)):
                original = {'name': 's', 'values': values}
                for series in ([original], (original,)):
                    emit_chart('bar', 't', x, series)
                    chart.assert_called_with('bar', 't', ['a', 'b'], [{'name': 's', 'values': [1, None]}])
                    self.assertIs(original['values'], values)
                    self.assertIsNot(chart.call_args.args[3][0], original)

    def test_string_dictionary_scalar_and_length_mismatch_are_still_rejected(self):
        table, chart = MagicMock(), MagicMock()
        emit_table, emit_chart = guard._checked_outputs(table, chart)
        for bad in ('SECRET', {'key': 1}, 1, None):
            for columns, rows in ((bad, []), (['q'], bad), (['q'], [bad])):
                with self.assertRaises(guard.GuardError):
                    emit_table('t', columns, rows)
            for x, series in ((bad, []), ([], bad), (['a'], [{'values': bad}])):
                with self.assertRaises(guard.GuardError) as error:
                    emit_chart('bar', 't', x, series)
                self.assertNotIn('SECRET', str(error.exception))
        for columns, rows in ((('id', 'q'), ((1,),)), ((1,), ((2,),))):
            with self.assertRaises(guard.GuardError):
                emit_table('t', columns, rows)
        with self.assertRaises(guard.GuardError):
            emit_chart('bar', 't', ('a', 'b'), ({'values': (1,)},))
        table.assert_not_called()
        chart.assert_not_called()

    def test_explicit_container_not_started_and_result_fixed_text(self):
        self.assertEqual(runs._container_cleanup({'cleanup': {'ok': True, 'state': 'not_started'}}), 'not_started')
        self.assertIn('横軸(x)', runs.reason_text('result_invalid'))


class WrapperRefresh(CodegenBase):
    def old_code(self):
        plan = self.new_plan()
        bundle = cg.make_bundle(GOOD_STEPS, GOOD_PYTHON, VIEWS)
        def apply(current):
            current['codegen'] = {'status': 'code_approved', 'attempts': 4, 'steps': GOOD_STEPS, 'python': GOOD_PYTHON,
                                  'sql_sha256': bundle.sql_sha256, 'python_sha256': bundle.python_sha256,
                                  'executed_code_sha256': 'old', 'wrapper_version': 'old',
                                  'trial': {'status':'passed'}, 'code_approved_at': 'old'}
        return self.store.update(plan['id'], OWNER, plan['revision'], apply)

    def test_refresh_does_not_call_ai_consume_count_or_extend_ttl_and_requires_trial(self):
        plan = self.old_code()
        ttl = self.store.client.ttl(self.store._key(plan['id']))
        with patch.object(cg, '_call_ai') as ai:
            updated = cg.refresh_wrapper(OWNER, plan['id'], plan['revision'])
        ai.assert_not_called()
        self.assertEqual(updated['codegen']['attempts'], 4)
        self.assertEqual(updated['codegen']['python'], GOOD_PYTHON)
        self.assertEqual(updated['codegen']['status'], 'generated')
        self.assertIsNone(updated['codegen']['trial'])
        self.assertNotIn('code_approved_at', updated['codegen'])
        self.assertLessEqual(self.store.client.ttl(self.store._key(plan['id'])), ttl)
        with self.assertRaises(AnalysisError):
            cg.approve_code(OWNER, plan['id'], updated['revision'], updated['codegen']['executed_code_sha256'])

    def test_changed_body_bad_static_check_owner_and_revision_reject(self):
        for changed in ('hash', 'check', 'owner', 'revision'):
            plan = self.old_code()
            owner, revision = OWNER, plan['revision']
            if changed == 'hash':
                plan['codegen']['python'] += '\n# changed'
            if changed == 'check':
                source = 'emit_chart("bar", "t", "月", [])'
                plan['codegen'].update(python=source, python_sha256=cg.sha256_text(source))
            if changed in ('hash', 'check'):
                self.store.client.set(self.store._key(plan['id']), json.dumps(plan), ex=100)
            if changed == 'owner': owner += 1
            if changed == 'revision': revision -= 1
            with self.assertRaises(AnalysisError):
                cg.refresh_wrapper(owner, plan['id'], revision)

    def test_missing_execution_information_is_not_cleanup_confirmation(self):
        plan = self.old_code()
        plan = self.store.update(plan['id'], OWNER, plan['revision'],
                                 lambda current: current.update(execution={'job_id': 'missing-job'}))
        with patch.object(jobs.JobStore, 'raw', side_effect=AnalysisError('実行情報がありません。', 410)), patch.object(cg, '_call_ai') as ai:
            with self.assertRaises(AnalysisError) as error:
                cg.refresh_wrapper(OWNER, plan['id'], plan['revision'])
        self.assertEqual(error.exception.status_code, 410)
        self.assertEqual(self.store.get(plan['id'], OWNER), plan)
        ai.assert_not_called()


@override_settings(DEBUG=True, AI_ANALYSIS_LAUNCHER_URL='http://127.0.0.1:8091')
class SlotFixes(SimpleTestCase):
    # 準備・模擬処理だけ共有する。既存の21テストは重複して再収集しない。
    setUp = job_cases.JobTests.setUp
    save_plan = job_cases.JobTests.save_plan
    cleanup = job_cases.JobTests.cleanup
    submit = job_cases.JobTests.submit
    process = job_cases.JobTests.process
    stopped = staticmethod(job_cases.JobTests.stopped)
    def test_history_start_column_missing_releases_slot_using_real_run_and_record(self):
        job = self.submit()
        def actual(*args, **kwargs):
            with patch.object(runs, 'mark_unknown_stale'), patch.object(runs, 'AIAnalysisRun') as model, patch.object(runs, 'execute_approved_analysis') as execute:
                model.objects.create.side_effect = OperationalError('Unknown column executed_code_sha256 SECRET')
                try:
                    return runs.run_and_record(*args, **kwargs)
                finally:
                    execute.assert_not_called()
        self.process(job['id'], actual)
        result = self.store.get(job['id'], self.user.pk)
        self.assertEqual(result['reason'], 'history_failed')
        self.assertEqual(result['cleanup'], {'db_connection':'not_started', 'container':'not_started'})
        self.assertIsNone(self.store.client.get(self.store.active_key))

    def test_periodic_reconcile_404_keeps_slot_then_closed_releases(self):
        job = self.submit()
        self.store.update(job['id'], lambda j: j.update(status='failed', cleanup={'db_connection':'closed','container':'unconfirmed'}))
        with patch.object(jobs.ExecutionControl, 'launcher', return_value=(404, {})):
            jobs.reconcile_cleanup(self.store, job['id'])
        self.assertEqual(self.store.client.get(self.store.active_key), job['id'])
        with patch.object(jobs.ExecutionControl, 'launcher', return_value=(200, {'done':True, 'cleanup':'closed'})):
            jobs.reconcile_cleanup(self.store, job['id'])
        self.assertIsNone(self.store.client.get(self.store.active_key))

    def test_worker_exception_deletes_lease_and_public_job_is_unknown(self):
        job = self.submit()
        self.store.client.delete(self.store.worker_key)
        # worker_loopが採用した生存IDへジョブを合わせ、処理中の例外を発生させる。
        def crash(store, job_id, worker):
            store.update(job_id, lambda j: j.update(worker=worker))
            raise RuntimeError('SECRET')
        original = self.store.raw
        def raw(job_id):
            result = original(job_id)
            result['worker'] = self.store.client.get(self.store.worker_key)
            return result
        connection = MagicMock()
        connection.getresponse.return_value.status = 200
        connection.getresponse.return_value.read.return_value = b'{"status":"ready","busy":false}'
        with (patch.object(jobs, 'JobStore', return_value=self.store), patch.object(self.store, 'raw', side_effect=raw),
              patch.object(jobs, 'process_job', side_effect=crash), patch.object(jobs, 'acquire_worker_lock') as lock,
              patch.object(jobs.http.client, 'HTTPConnection', return_value=connection)):
            with self.assertRaises(AnalysisError): jobs.worker_loop()
            jobs._PROCESS_LOCKS.remove(lock.return_value)
        self.assertIsNone(self.store.client.get(self.store.worker_key))
        self.assertEqual(self.store.get(job['id'], self.user.pk)['status'], 'unknown')
        self.assertEqual(self.store.client.get(self.store.active_key), job['id'])

    def test_recovery_dry_run_apply_and_any_missing_check_refuses(self):
        @contextmanager
        def confirmed(): yield lambda: True
        job = self.submit()
        self.store.client.delete(self.store.worker_key)
        self.store.update(job['id'], lambda j: j.update(status='failed', cleanup={'db_connection':'closed','container':'unconfirmed'}))
        with patch.object(recovery, 'JobStore', return_value=self.store), patch.object(recovery, 'launcher_guard', confirmed), patch.object(recovery, 'acquire_worker_lock'), patch.object(recovery.transaction, 'atomic'):
            self.assertFalse(recovery.recover_slot(job['id'])['released'])
            self.assertEqual(self.store.client.get(self.store.active_key), job['id'])
            for key in ('db', 'worker', 'active'):
                self.store.update(job['id'], lambda j: j['cleanup'].update(db_connection='pending' if key == 'db' else 'closed'))
                if key == 'worker': self.store.client.set(self.store.worker_key, 'alive')
                if key == 'active': self.store.client.set(self.store.active_key, 'other')
                with self.assertRaises(AnalysisError): recovery.recover_slot(job['id'], True)
                self.store.client.delete(self.store.worker_key)
                self.store.client.set(self.store.active_key, job['id'])
            self.assertTrue(recovery.recover_slot(job['id'], True)['released'])
            self.assertIsNone(self.store.client.get(self.store.active_key))

    def test_recovery_missing_launcher_docker_or_worker_lock_keeps_slot(self):
        job = self.submit()
        self.store.client.delete(self.store.worker_key)
        self.store.update(job['id'], lambda j: j.update(status='failed', cleanup={'db_connection':'closed','container':'unconfirmed'}))
        for check in ('launcher', 'docker', 'lock'):
            @contextmanager
            def missing():
                raise AnalysisError('未確認', 409)
                yield
            with patch.object(recovery, 'JobStore', return_value=self.store), patch.object(recovery, 'launcher_guard', missing), patch.object(recovery, 'acquire_worker_lock') as lock:
                if check == 'lock': lock.side_effect = AnalysisError('稼働中', 409)
                with self.assertRaises(AnalysisError): recovery.recover_slot(job['id'], True)
            self.assertEqual(self.store.client.get(self.store.active_key), job['id'])

    def test_recovery_lost_guard_and_watched_active_change_never_release(self):
        job = self.submit()
        self.store.client.delete(self.store.worker_key)
        self.store.update(job['id'], lambda j: j.update(status='failed', cleanup={'db_connection':'closed','container':'unconfirmed'}))
        @contextmanager
        def lost(): yield lambda: False
        @contextmanager
        def raced():
            def alive():
                self.store.client.set(self.store.active_key, 'new-job')
                return True
            yield alive
        for guard in (lost, raced):
            with patch.object(recovery, 'JobStore', return_value=self.store), patch.object(recovery, 'launcher_guard', guard), patch.object(recovery, 'acquire_worker_lock'), patch.object(recovery.transaction, 'atomic'):
                with self.assertRaises(AnalysisError): recovery.recover_slot(job['id'], True)
            self.assertEqual(self.store.raw(job['id'])['cleanup']['container'], 'unconfirmed')
        self.assertEqual(self.store.client.get(self.store.active_key), 'new-job')


@override_settings(ALLOWED_HOSTS=['testserver'])
class HistoryPermissions(TestCase):
    def request(self, user, include_all=True):
        request = APIRequestFactory().get('/', {'include_all':'true' if include_all else 'false'})
        force_authenticate(request, user)
        with patch.object(views, 'visible_runs', return_value=[]) as visible:
            response = views.AIAnalysisRunsView.as_view()(request)
        return response, visible

    def test_real_users_superuser_no_profile_individual_grant_view_only_and_parent(self):
        user = get_user_model().objects.create(username='no-profile')
        admin = get_user_model().objects.create(username='admin', is_superuser=True)
        self.assertEqual(self.request(admin)[0].status_code, 200)
        response, visible = self.request(user)
        self.assertEqual(response.status_code, 403); visible.assert_not_called()
        self.assertEqual(self.request(user, False)[0].status_code, 200)
        permission = UserPermission.objects.create(user=user, resource='settings.ai', can_edit=False, can_view=True)
        self.assertEqual(self.request(user)[0].status_code, 403)
        permission.can_edit = True; permission.save()
        self.assertEqual(self.request(user)[0].status_code, 200)
        permission.resource = 'settings'; permission.save()
        self.assertEqual(self.request(user)[0].status_code, 403)

    def test_permission_lookup_failure_is_403_not_all_history(self):
        user = get_user_model().objects.create(username='lookup-failed')
        with patch.object(views, '_has_resource_permission', side_effect=OperationalError('SECRET')):
            response, visible = self.request(user)
        self.assertEqual(response.status_code, 403); visible.assert_not_called()
