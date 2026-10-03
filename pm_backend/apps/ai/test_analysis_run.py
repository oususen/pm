"""分析の実行履歴(2-D): 保存・確定・生存確認・状態不明・後始末の反映・保存失敗・閲覧を検証する。

履歴はPM本体DB(テストDB)へ保存する。取得は開発DB(pm_ai_reader)の読み取りと、模擬launcherを使う。
"""
import json
import os
import unittest
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.db import models
from django.test import TransactionTestCase, override_settings

from ai.models import AIAnalysisRun
from ai.services import analysis_run_service as runs
from ai.services.analysis_execution_service import ExecutionStopped
from ai.test_analysis_execution import PROPOSAL, FakeLauncher, approved_counts

POLICY = SimpleNamespace(max_memory_mb=512, max_cpu_cores=Decimal('1.0'), max_execution_seconds=60, max_fetch_rows=100_000,
                         plan_cache_ttl_minutes=60)
PYTHON = "emit_report('SECRET-PYTHON-BODY')"
SQL = 'SELECT SECRET_SQL_BODY'
BUNDLE = SimpleNamespace(sql_sha256=runs.sha256_of(SQL), python_sha256=runs.sha256_of(PYTHON), executed_code=PYTHON,
                         executed_code_sha256=runs.sha256_of('WRAPPED' + PYTHON), wrapper_version='test-wrapper')


def make_plan(counts):
    proposal = {**PROPOSAL, 'conditions': '指定期間の全登録行（追加の絞り条件なし）'}
    return {
        'id': 'plan-1', 'status': 'data_approved', 'proposal': proposal,
        'method_approved_at': '2026-10-04T09:00:00', 'data_approved_at': '2026-10-04T09:01:00',
        'preview': {'datasets': [{'view': view, 'rows': rows} for view, rows in counts.items()], 'total_rows': sum(counts.values())},
    }


class RunBase(TransactionTestCase):
    databases = {'default'}

    def setUp(self):
        self.user = get_user_model().objects.create(username='run-tester')
        self.launcher = FakeLauncher()
        self.addCleanup(self.launcher.close)
        overrides = override_settings(AI_ANALYSIS_LAUNCHER_URL=self.launcher.url)
        overrides.enable()
        self.addCleanup(overrides.disable)
        self.counts = approved_counts()
        self.plan = make_plan(self.counts)

    def run_it(self, **kwargs):
        return runs.run_and_record(self.user, self.plan, BUNDLE, POLICY, chunk_rows=500, **kwargs)


class RecordTest(RunBase):
    def test_success_is_recorded_with_distinct_counts_two_hashes_and_no_code_body(self):
        self.launcher.respond = lambda header: {
            'status': 'ok', 'result': {'report': 'ok'}, 'cleanup': {'ok': True},
            'diagnostics': {'rows_loaded': {v['name']: v['expected_rows'] for v in header['views']}, 'loaded_at_epoch': time.time()}}
        result = self.run_it()
        run = AIAnalysisRun.objects.get(pk=result['run_id'])
        self.assertEqual((run.status, run.reason), ('success', ''))
        self.assertEqual(run.approved_counts, self.counts)  # 承認時
        self.assertEqual(run.snapshot_counts, self.counts)  # スナップショットのCOUNT
        self.assertEqual(run.fetched_rows, self.counts)  # 1回目の取得
        self.assertEqual(run.sent_rows, self.counts)  # 2回目の送信
        self.assertEqual(run.loaded_rows, self.counts)  # コンテナへの投入
        self.assertEqual(run.unique_key_check, {'column': 'id', 'django': 'ok', 'container': 'ok'})
        self.assertEqual(run.sql_sha256, runs.sha256_of(SQL))
        self.assertEqual(run.python_sha256, runs.sha256_of(PYTHON))
        self.assertEqual((run.executed_code_sha256, run.wrapper_version), (BUNDLE.executed_code_sha256, 'test-wrapper'))
        self.assertNotEqual(run.sql_sha256, run.python_sha256)
        self.assertEqual(run.cleanup['db_connection'], 'closed')
        self.assertEqual(run.worker_id, runs.WORKER_ID)
        self.assertIsNotNone(run.fetched_at)
        self.assertIsNotNone(run.sent_at)
        self.assertIsNotNone(run.finished_at)
        self.assertIsNotNone(run.loaded_at)  # コンテナが報告した投入完了の時刻
        self.assertTrue(run.fetched_at <= run.loaded_at <= run.finished_at)
        self.assertEqual(run.settings_snapshot['max_fetch_rows'], 100_000)
        self.assertEqual(run.method_approved_at, datetime(2026, 10, 4, 9, 0))
        # コード本文・結果の中身は、どの列にも保存しない
        dump = json.dumps({f.name: str(getattr(run, f.name)) for f in AIAnalysisRun._meta.fields}, ensure_ascii=False)
        self.assertNotIn('SECRET-PYTHON-BODY', dump)
        self.assertNotIn('SECRET_SQL_BODY', dump)

    def test_execution_failure_is_recorded_then_the_original_error_is_raised_with_run_id(self):
        counts = {**self.counts, 'v_ai_shipment': self.counts['v_ai_shipment'] + 1}
        self.plan = make_plan(counts)  # 承認時から件数が変わった状況
        with self.assertRaises(ExecutionStopped) as caught:
            self.run_it()
        run = AIAnalysisRun.objects.get(pk=caught.exception.run_id)
        self.assertEqual((run.status, run.reason), ('failed', 'approved_count_changed'))
        self.assertEqual(run.cleanup['db_connection'], 'closed')
        self.assertEqual(run.cleanup['container'], 'not_started')
        self.assertIsNone(run.loaded_rows)
        self.assertEqual(self.launcher.bodies, [])

    def test_launcher_failure_result_is_recorded_as_failed_with_its_reason(self):
        self.launcher.respond = lambda header: {'status': 'failed', 'reason': 'duplicate_key', 'detail': 'x', 'cleanup': {'ok': False},
                                                'diagnostics': {'rows_loaded': None}}
        result = self.run_it()
        run = AIAnalysisRun.objects.get(pk=result['run_id'])
        self.assertEqual((run.status, run.reason), ('failed', 'duplicate_key'))
        self.assertEqual(run.cleanup['container'], 'pending')  # コンテナを削除できていなければ、完了扱いにしない
        self.assertEqual(run.unique_key_check['container'], 'failed')

    def test_not_run_cases_are_recorded(self):
        run = runs.record_not_run(self.user, self.plan, 'expired', 'plan_expired', POLICY)
        self.assertEqual((run.status, run.reason, run.python_sha256), ('expired', 'plan_expired', None))
        with self.assertRaises(ValueError):
            runs.record_not_run(self.user, self.plan, 'success', 'x', POLICY)

    def test_unapproved_plan_is_not_executed(self):
        self.plan['status'] = 'awaiting_data'
        with self.assertRaises(Exception):
            self.run_it()
        self.assertEqual(AIAnalysisRun.objects.count(), 0)


class SaveFailureTest(RunBase):
    def test_start_save_failure_prevents_execution(self):
        with patch.object(runs.AIAnalysisRun.objects, 'create', side_effect=RuntimeError('DB障害')), \
                patch.object(runs, 'execute_approved_analysis') as execute, self.assertRaises(runs.HistoryError):
            self.run_it()
        execute.assert_not_called()
        self.assertEqual(self.launcher.bodies, [])

    def test_finish_failure_does_not_return_the_result_and_keeps_the_original_outcome(self):
        with patch.object(runs, 'finish_run', side_effect=RuntimeError('確定できない')), self.assertRaises(runs.HistoryError) as caught:
            self.run_it()
        self.assertEqual(caught.exception.outcome['status'], 'success')  # 元の結果は、エラーに残る
        self.assertEqual(AIAnalysisRun.objects.get().status, 'running')  # 確定できていない行を、成功と偽らない

    def test_finish_failure_after_an_execution_failure_keeps_the_original_reason(self):
        self.plan = make_plan({**self.counts, 'v_ai_shipment': 0})
        with patch.object(runs, 'finish_run', side_effect=RuntimeError('確定できない')), self.assertRaises(runs.HistoryError) as caught:
            self.run_it()
        self.assertEqual(caught.exception.outcome['reason'], 'approved_count_changed')

    def test_finish_does_not_touch_a_row_owned_by_another_worker(self):
        run = runs.start_run(self.user, self.plan, BUNDLE, POLICY)
        other = SimpleNamespace(pk=run.pk, worker_id='another-worker')
        with self.assertRaises(runs.HistoryError):
            runs.finish_run(other, runs.outcome_from_exception(RuntimeError('x')))
        self.assertEqual(AIAnalysisRun.objects.get(pk=run.pk).status, 'running')


class LivenessTest(RunBase):
    def make_running(self, heartbeat_age):
        run = runs.start_run(self.user, self.plan, BUNDLE, POLICY)
        AIAnalysisRun.objects.filter(pk=run.pk).update(heartbeat_at=datetime.now() - timedelta(seconds=heartbeat_age))
        return AIAnalysisRun.objects.get(pk=run.pk)

    def test_only_stale_running_rows_become_unknown_and_cleanup_is_not_complete(self):
        stale, fresh = self.make_running(120), self.make_running(5)
        self.assertEqual(runs.mark_unknown_stale(), 1)
        stale.refresh_from_db()
        fresh.refresh_from_db()
        self.assertEqual((stale.status, stale.reason), ('unknown', 'heartbeat_lost'))
        self.assertIn('断定できない', stale.detail)
        self.assertEqual(stale.cleanup, {'db_connection': 'pending', 'container': 'pending'})
        self.assertEqual(fresh.status, 'running')

    def test_a_row_whose_heartbeat_came_back_late_is_not_overwritten(self):
        stale = self.make_running(120)
        real_filter = runs.AIAnalysisRun.objects.filter

        def filter_then_heartbeat_returns(*args, **kwargs):
            queryset = real_filter(*args, **kwargs)
            if 'heartbeat_at__lt' in kwargs:
                rows = list(queryset.only('pk', 'heartbeat_at'))
                real_filter(pk=stale.pk).update(heartbeat_at=datetime.now())  # 判定の読み取りの後に、遅れていたheartbeatが戻る
                return SimpleNamespace(only=lambda *a: rows)
            return queryset

        with patch.object(runs.AIAnalysisRun.objects, 'filter', filter_then_heartbeat_returns):
            self.assertEqual(runs.mark_unknown_stale(), 0)
        stale.refresh_from_db()
        self.assertEqual(stale.status, 'running')

    def test_the_owner_can_still_report_the_real_outcome_of_an_unknown_run(self):
        stale = self.make_running(120)
        runs.mark_unknown_stale()
        runs.finish_run(stale, runs.outcome_from_exception(RuntimeError('x')))
        stale.refresh_from_db()
        self.assertEqual((stale.status, stale.reason), ('failed', 'unexpected_error'))

    def test_heartbeat_thread_updates_only_a_running_row_and_stops(self):
        run = runs.start_run(self.user, self.plan, BUNDLE, POLICY)
        AIAnalysisRun.objects.filter(pk=run.pk).update(heartbeat_at=datetime.now() - timedelta(seconds=30))
        before = AIAnalysisRun.objects.get(pk=run.pk).heartbeat_at
        beat = runs.Heartbeat(run, interval=0.2).start()
        time.sleep(0.8)
        self.assertGreater(AIAnalysisRun.objects.get(pk=run.pk).heartbeat_at, before)
        AIAnalysisRun.objects.filter(pk=run.pk).update(status='unknown')  # 状態不明にされた行は、更新しない
        frozen = AIAnalysisRun.objects.get(pk=run.pk).heartbeat_at
        time.sleep(0.6)
        self.assertEqual(AIAnalysisRun.objects.get(pk=run.pk).heartbeat_at, frozen)
        beat.stop()
        self.assertFalse(beat.thread.is_alive())

    def test_startup_does_not_mark_other_workers_fresh_runs(self):
        other = self.make_running(3)
        AIAnalysisRun.objects.filter(pk=other.pk).update(worker_id='another-worker:1:abcd')
        runs.run_and_record(self.user, self.plan, BUNDLE, POLICY, chunk_rows=500)
        self.assertEqual(AIAnalysisRun.objects.get(pk=other.pk).status, 'running')


class CleanupPendingTest(RunBase):
    def test_late_final_cleanup_before_finish_replaces_pending(self):
        run = runs.start_run(self.user, self.plan, BUNDLE, POLICY)
        tracker = runs.CleanupTracker(run.pk)
        tracker.notify('closed')  # 確定の前に、待機中だった後始末が終わった
        runs.finish_run(run, {**runs.outcome_from_exception(RuntimeError('x')), 'cleanup': {'db_connection': 'pending', 'container': 'not_started'}}, tracker)
        self.assertEqual(AIAnalysisRun.objects.get(pk=run.pk).cleanup['db_connection'], 'closed')

    def test_late_final_cleanup_after_finish_updates_only_a_pending_row(self):
        run = runs.start_run(self.user, self.plan, BUNDLE, POLICY)
        tracker = runs.CleanupTracker(run.pk)
        runs.finish_run(run, {**runs.outcome_from_exception(RuntimeError('x')), 'cleanup': {'db_connection': 'pending', 'container': 'not_started'}}, tracker)
        self.assertEqual(AIAnalysisRun.objects.get(pk=run.pk).cleanup['db_connection'], 'pending')  # 通知までは、完了扱いにしない
        tracker.notify('failed')
        self.assertEqual(AIAnalysisRun.objects.get(pk=run.pk).cleanup['db_connection'], 'failed')

    def test_a_closed_row_is_not_changed_by_a_late_notification(self):
        run = runs.start_run(self.user, self.plan, BUNDLE, POLICY)
        tracker = runs.CleanupTracker(run.pk)
        runs.finish_run(run, {**runs.outcome_from_exception(RuntimeError('x')), 'cleanup': {'db_connection': 'closed', 'container': 'not_started'}}, tracker)
        tracker.notify('failed')
        self.assertEqual(AIAnalysisRun.objects.get(pk=run.pk).cleanup['db_connection'], 'closed')

    def test_pending_connection_cleanup_in_a_real_run_is_recorded_as_pending_then_updated(self):
        """取得の期限で待ちをやめた問い合わせが動いている間は、pendingと記録し、終わったら最終状態へ更新する。"""
        real = runs.execute_approved_analysis

        def hung_start(*args, **kwargs):
            time.sleep(0.01)
            fake = MagicMock()
            fake.start_transaction.side_effect = lambda *a, **k: time.sleep(1.5)

            with patch('ai.services.analysis_execution_service.mysql.connector.connect', return_value=fake):
                return real(*args, **kwargs)

        with patch.object(runs, 'execute_approved_analysis', hung_start), self.assertRaises(ExecutionStopped) as caught:
            self.run_it(deadlines={'fetch': 0.3})
        run = AIAnalysisRun.objects.get(pk=caught.exception.run_id)
        self.assertEqual(run.reason, 'stage_deadline_fetch')
        self.assertEqual(run.cleanup['db_connection'], 'pending')  # 完了扱いにしない
        deadline = time.time() + 6
        while time.time() < deadline and AIAnalysisRun.objects.get(pk=run.pk).cleanup['db_connection'] == 'pending':
            time.sleep(0.1)
        self.assertEqual(AIAnalysisRun.objects.get(pk=run.pk).cleanup['db_connection'], 'closed')


class ViewingTest(RunBase):
    def test_deleted_user_is_shown_without_personal_data_and_the_run_survives(self):
        other = get_user_model().objects.create(username='other-user')
        mine = runs.record_not_run(self.user, self.plan, 'expired', 'plan_expired', POLICY)
        theirs = runs.record_not_run(other, self.plan, 'cancelled', 'user_cancelled', POLICY)
        self.assertEqual(sorted(r.pk for r in runs.visible_runs(self.user, include_all=False)), [mine.pk])
        self.assertEqual(sorted(r.pk for r in runs.visible_runs(self.user, include_all=True)), sorted([mine.pk, theirs.pk]))
        self.assertEqual(runs.serialize_run(AIAnalysisRun.objects.get(pk=theirs.pk))['executed_by'], 'other-user')
        # ユーザーの削除時は、履歴を消さずに実行者をNULLにする(SET_NULL)。テストDBは、他アプリの未管理テーブルを持たず、
        # ユーザーの実削除(関連行の収集)ができないため、削除の設定と、NULLになった後の表示を確認する。
        self.assertIs(AIAnalysisRun._meta.get_field('user').remote_field.on_delete, models.SET_NULL)
        AIAnalysisRun.objects.filter(pk=theirs.pk).update(user=None)
        run = AIAnalysisRun.objects.get(pk=theirs.pk)
        self.assertIsNone(run.user_id)
        self.assertEqual(runs.serialize_run(run)['executed_by'], '削除済みユーザー')

    def test_concurrent_runs_are_recorded_independently(self):
        first = runs.start_run(self.user, self.plan, BUNDLE, POLICY)
        second = runs.start_run(self.user, self.plan, BUNDLE, POLICY)
        self.assertNotEqual(first.pk, second.pk)
        threads = [threading.Thread(target=lambda r=r: runs.finish_run(r, runs.outcome_from_exception(RuntimeError('x')))) for r in (first, second)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(AIAnalysisRun.objects.filter(status='failed').count(), 2)


@unittest.skipUnless(os.environ.get('AI_ANALYSIS_LAUNCHER_URL_FOR_TEST'), '実launcherの通しは、接続先を指定したときだけ実行する')
class RealLauncherRecordTest(TransactionTestCase):
    """実launcher(Docker)で実行し、履歴の件数・後始末・所要時間が実際の値で保存されること。"""
    databases = {'default'}

    def test_real_run_is_recorded(self):
        user = get_user_model().objects.create(username='real-run')
        counts = approved_counts()
        code = "n = con.execute('SELECT COUNT(*) FROM v_ai_shipment').fetchone()[0]\nemit_report(str(n))"
        with override_settings(AI_ANALYSIS_LAUNCHER_URL=os.environ['AI_ANALYSIS_LAUNCHER_URL_FOR_TEST']):
            bundle = SimpleNamespace(sql_sha256=None, python_sha256=runs.sha256_of(code), executed_code=code,
                                 executed_code_sha256=runs.sha256_of(code), wrapper_version='test-wrapper')
            result = runs.run_and_record(user, make_plan(counts), bundle, POLICY, chunk_rows=500)
        run = AIAnalysisRun.objects.get(pk=result['run_id'])
        self.assertEqual(run.status, 'success', (run.reason, run.detail))
        self.assertEqual(result['launcher']['result']['report'], str(counts['v_ai_shipment']))
        self.assertEqual((run.fetched_rows, run.sent_rows, run.loaded_rows), (counts, counts, counts))
        self.assertIsNone(run.sql_sha256)  # 別のSQLがない実行
        self.assertTrue(run.fetched_at <= run.loaded_at <= run.finished_at)  # コンテナ内の投入が終わった実際の時刻
        self.assertLessEqual(run.loaded_at, run.finished_at)
        self.assertEqual(run.cleanup, {'db_connection': 'closed', 'container': 'closed'})
        self.assertGreater(run.container_load_seconds, 0)
        self.assertIsNotNone(run.python_seconds)


class ReviewFixTest(RunBase):
    """レビュー指摘4件: 実データを含み得る説明文を保存しない／通知と確定の競合／送信後の通信失敗は未確認／遅れて開いた接続の削除失敗。"""

    SECRET = 'SECRET-ROW-DATA-777'

    def test_failure_detail_is_a_fixed_text_and_never_the_launcher_or_exception_message(self):
        self.launcher.respond = lambda header: {'status': 'failed', 'reason': 'duckdb_error', 'cleanup': {'ok': True},
                                                'detail': f'Conversion Error: Could not convert string {self.SECRET} to INT',
                                                'diagnostics': {'stderr': self.SECRET}}
        run = AIAnalysisRun.objects.get(pk=self.run_it()['run_id'])
        self.assertEqual(run.reason, 'duckdb_error')
        self.assertNotIn(self.SECRET, json.dumps({f.name: str(getattr(run, f.name)) for f in AIAnalysisRun._meta.fields}, ensure_ascii=False))
        self.assertEqual(run.detail, runs.GENERIC_REASON_TEXT)  # 未知の理由コードは、固定の汎用文
        # 例外の説明文に実データが入っていても、保存しない
        error = ExecutionStopped('fetch_failed', f'取得失敗 {self.SECRET}')
        outcome = runs.outcome_from_exception(error)
        self.assertNotIn(self.SECRET, json.dumps(outcome, ensure_ascii=False, default=str))
        self.assertEqual(outcome['detail'], runs.REASON_TEXT['fetch_failed'])
        self.assertEqual(runs.outcome_from_exception(RuntimeError(self.SECRET))['detail'], runs.REASON_TEXT['unexpected_error'])

    def test_notification_arriving_during_the_final_write_is_not_lost(self):
        run = runs.start_run(self.user, self.plan, BUNDLE, POLICY)
        tracker = runs.CleanupTracker(run.pk)
        outcome = {**runs.outcome_from_exception(RuntimeError('x')), 'cleanup': {'db_connection': 'pending', 'container': 'not_started'}}
        real_filter = runs.AIAnalysisRun.objects.filter
        notifier = {}

        def filter_then_notify_during_write(*args, **kwargs):
            queryset = real_filter(*args, **kwargs)
            real_update = queryset.update

            def update(**fields):
                # 確定の書き込みの直前に、後始末の完了通知が届く
                notifier['thread'] = threading.Thread(target=tracker.notify, args=('closed',))
                notifier['thread'].start()
                time.sleep(0.3)
                notifier['blocked'] = notifier['thread'].is_alive()  # 書き込みが終わるまで、通知は待たされる
                return real_update(**fields)

            queryset.update = update
            return queryset

        with patch.object(runs.AIAnalysisRun.objects, 'filter', filter_then_notify_during_write):
            runs.finish_run(run, outcome, tracker)
        notifier['thread'].join(5)
        self.assertTrue(notifier['blocked'])
        self.assertEqual(AIAnalysisRun.objects.get(pk=run.pk).cleanup['db_connection'], 'closed')  # pendingのままにならない

    def test_communication_failure_after_sending_everything_leaves_the_container_unconfirmed(self):
        def no_response(header):
            raise RuntimeError('応答を返さずに終わる')

        self.launcher.respond = no_response
        with self.assertRaises(ExecutionStopped) as caught:
            self.run_it()
        run = AIAnalysisRun.objects.get(pk=caught.exception.run_id)
        self.assertEqual(run.reason, 'launcher_unreachable')
        self.assertEqual(run.cleanup['container'], 'unconfirmed')  # 開始・削除を確認できない
        self.assertEqual(len(self.launcher.bodies), 1)  # 全データは送り終えている

    def test_stop_after_sending_started_is_unconfirmed_but_before_sending_is_not_started(self):
        sent_rows = {'v_ai_shipment': 1}
        started = runs.outcome_from_exception(type('E', (ExecutionStopped,), {})('refetch_mismatch', 'x'))
        self.assertEqual(started['cleanup']['container'], 'not_started')
        error = ExecutionStopped('refetch_mismatch', 'x')
        error.progress = {'transmit_started': True, 'sent_rows': sent_rows}
        self.assertEqual(runs.outcome_from_exception(error)['cleanup']['container'], 'unconfirmed')

    def test_response_without_cleanup_result_is_unconfirmed(self):
        self.launcher.respond = lambda header: {'status': 'refused', 'reason': 'busy'}
        run = AIAnalysisRun.objects.get(pk=self.run_it()['run_id'])
        self.assertEqual((run.status, run.reason, run.cleanup['container']), ('failed', 'busy', 'unconfirmed'))

    def test_late_connection_close_failure_is_reported_as_failed_in_the_notification(self):
        fake = MagicMock()
        fake.close.side_effect = RuntimeError('close失敗')
        fake.start_transaction.side_effect = lambda *a, **k: time.sleep(1.2)
        real = runs.execute_approved_analysis

        def with_fake_connection(*args, **kwargs):
            with patch('ai.services.analysis_execution_service.mysql.connector.connect', return_value=fake):
                return real(*args, **kwargs)

        with patch.object(runs, 'execute_approved_analysis', with_fake_connection), self.assertRaises(ExecutionStopped) as caught:
            self.run_it(deadlines={'fetch': 0.3})
        run_id = caught.exception.run_id
        deadline = time.time() + 6
        while time.time() < deadline and AIAnalysisRun.objects.get(pk=run_id).cleanup['db_connection'] == 'pending':
            time.sleep(0.1)
        self.assertEqual(AIAnalysisRun.objects.get(pk=run_id).cleanup['db_connection'], 'failed')  # closedにならない


class LoadedAtTest(RunBase):
    """投入完了日時(コンテナの報告)。報告がない・不正・範囲外はNULLとし、推測で補わない。"""

    def test_loaded_at_is_taken_from_the_container_report_and_only_when_valid(self):
        fetched = datetime(2026, 10, 4, 10, 0, 0)
        now = datetime(2026, 10, 4, 10, 5, 0)
        good = (fetched + timedelta(seconds=30)).timestamp()
        self.assertEqual(runs._loaded_at({'loaded_at_epoch': good}, fetched, now), fetched + timedelta(seconds=30))
        for bad in (None, 'x', True, float('nan'), float('inf'), (fetched - timedelta(seconds=60)).timestamp(),
                    (now + timedelta(seconds=60)).timestamp()):
            self.assertIsNone(runs._loaded_at({'loaded_at_epoch': bad}, fetched, now), bad)
        self.assertIsNone(runs._loaded_at({}, fetched, now))

    def test_run_records_the_reported_time_and_a_failure_before_loading_leaves_it_null(self):
        report = {'epoch': None}

        def respond(header):
            report['epoch'] = time.time()
            return {'status': 'ok', 'result': {'report': 'ok'}, 'cleanup': {'ok': True},
                    'diagnostics': {'rows_loaded': {v['name']: v['expected_rows'] for v in header['views']},
                                    'loaded_at_epoch': report['epoch']}}

        self.launcher.respond = respond
        run = AIAnalysisRun.objects.get(pk=self.run_it()['run_id'])
        self.assertAlmostEqual(run.loaded_at.timestamp(), report['epoch'], delta=0.01)
        self.launcher.respond = lambda header: {'status': 'failed', 'reason': 'row_count_mismatch', 'cleanup': {'ok': True}, 'diagnostics': {}}
        failed = AIAnalysisRun.objects.get(pk=self.run_it()['run_id'])
        self.assertIsNone(failed.loaded_at)  # 投入が終わる前に失敗した実行は、報告がない
        self.assertIn('loaded_at', runs.serialize_run(failed))


@unittest.skipUnless(os.environ.get('AI_ANALYSIS_LAUNCHER_URL_FOR_TEST'), '実launcherの通しは、接続先を指定したときだけ実行する')
class RealCodegenToRunTest(TransactionTestCase):
    """生成(模擬AI)→ 試行(実コンテナ、実DBなし)→ コード承認 → 実行(実DBの実データ)→ 履歴まで、実launcher(Docker)で通す。"""
    databases = {'default'}

    def setUp(self):
        from ai.services import analysis_codegen_service as cg
        from ai.services.analysis_plan_store import AnalysisPlanStore
        self.cg = cg
        self.store = AnalysisPlanStore()
        self.user = get_user_model().objects.create(username='codegen-run')
        override = override_settings(AI_ANALYSIS_LAUNCHER_URL=os.environ['AI_ANALYSIS_LAUNCHER_URL_FOR_TEST'])
        override.enable()
        self.addCleanup(override.disable)
        for item in (patch.object(cg, 'build_analysis_code_redactor', lambda: SimpleNamespace(redact_text=lambda text: text)),
                     patch.object(cg, 'get_analysis_execution_policy', lambda: POLICY),
                     patch.object(cg, 'resolve_planning_provider', lambda data: (data['provider'], data['model']))):
            item.start()
            self.addCleanup(item.stop)
        self.counts = approved_counts()
        proposal = {**PROPOSAL, 'title': 't', 'steps': ['s'], 'outputs': ['o'], 'purpose': 'p', 'external_purpose': 'p', 'materials': [],
                    'conditions': '指定期間の全登録行（追加の絞り条件なし）', 'provider': 'deepseek', 'model': 'm'}
        plan = self.store.create(self.user.pk, proposal, 30)
        self.addCleanup(lambda: self.store.client.delete(self.store._key(plan['id'])))

        def approve(current):
            current['status'] = 'data_approved'
            current['preview'] = {'datasets': [{'view': v, 'rows': n} for v, n in self.counts.items()], 'total_rows': sum(self.counts.values())}
            current['method_approved_at'] = current['data_approved_at'] = datetime.now().isoformat()

        self.plan = self.store.update(plan['id'], self.user.pk, plan['revision'], approve)

    def go(self, steps, python):
        cg = self.cg
        response = json.dumps({'steps': steps, 'python': python}, ensure_ascii=False)
        confirmation = cg.preview(self.user.pk, self.plan['id'], self.plan['revision'])['confirmation']
        with patch.object(cg, '_call_ai', return_value=response):
            plan = cg.generate(self.user.pk, self.plan['id'], self.plan['revision'], confirmation)
        self.assertEqual(plan['codegen']['status'], 'generated', plan['codegen'])
        for _ in range(15):
            plan, trial = cg.run_trial(self.user.pk, plan['id'], plan['revision'])
            if trial['reason'] not in ('busy', 'launcher_unreachable'):
                break
            time.sleep(2)
        self.assertEqual(trial['status'], 'passed', trial)
        plan = cg.approve_code(self.user.pk, plan['id'], plan['revision'], plan['codegen']['executed_code_sha256'])
        return plan, cg.bundle_from_plan(plan)

    def test_generated_code_runs_on_real_data_and_the_history_identifies_the_executed_code(self):
        steps = [{'name': 'w_total', 'query': 'SELECT count(*) AS n, sum(quantity) AS q FROM v_ai_shipment'}]
        python = "import json\nn, q = con.sql('SELECT n, q FROM w_total').fetchone()\nemit_report(json.dumps({'n': n, 'q': str(q)}))"
        plan, bundle = self.go(steps, python)
        for _ in range(15):  # 試行のコンテナの後始末が終わるまで、launcherは使用中として断る
            try:
                result = runs.run_and_record(self.user, plan, bundle, POLICY, chunk_rows=500)
            except ExecutionStopped as exc:
                self.assertEqual(exc.reason, 'launcher_unreachable')
                time.sleep(2)
                continue
            if result['status'] != 'refused':
                break
            time.sleep(2)
        run = AIAnalysisRun.objects.get(pk=result['run_id'])
        self.assertEqual(run.status, 'success', (run.reason, run.detail))
        report = json.loads(result['launcher']['result']['report'])
        from ai.services.analysis_execution_service import open_snapshot_connection, Deadline
        connection = open_snapshot_connection(Deadline(30, 'x'), read_timeout=30)
        try:
            cursor = connection.cursor()
            cursor.execute('SELECT COUNT(*), SUM(quantity) FROM v_ai_shipment')
            count, total = cursor.fetchone()
        finally:
            connection.close()
        self.assertEqual((report['n'], Decimal(report['q'])), (count, total))  # 生成コードの結果が、DB側の集計と一致する
        self.assertEqual(run.sql_sha256, bundle.sql_sha256)
        self.assertEqual(run.python_sha256, bundle.python_sha256)
        self.assertEqual(run.executed_code_sha256, bundle.executed_code_sha256)
        self.assertEqual(run.wrapper_version, bundle.wrapper_version)
        self.assertEqual(run.executed_code_sha256, runs.sha256_of(bundle.executed_code))
        self.assertEqual(run.loaded_rows, self.counts)

    def test_guard_violation_in_python_sql_fails_the_run_without_a_result(self):
        steps = [{'name': 'w_total', 'query': 'SELECT count(*) AS n FROM v_ai_shipment'}]
        python = "con.sql('SELECT * FROM information_schema.tables').fetchall()\nemit_report('到達してはいけない')"
        plan, bundle = self.go(steps, python)  # 静的検査・試行(SQLだけ)では見つからず、実行時の窓口で拒否される
        for _ in range(15):
            try:
                result = runs.run_and_record(self.user, plan, bundle, POLICY, chunk_rows=500)
            except ExecutionStopped:
                time.sleep(2)
                continue
            if result['status'] != 'refused':
                break
            time.sleep(2)
        self.assertEqual(result['status'], 'failed')
        self.assertNotIn('result', result['launcher'])
        self.assertIn('reference_not_allowed', result['launcher']['diagnostics']['stderr'])
        run = AIAnalysisRun.objects.get(pk=result['run_id'])
        self.assertEqual(run.status, 'failed')


    def run_bundle(self, steps, python):
        """静的検査を通さずに、組み立てたコードを、そのまま実コンテナで実行する(実行時の防御だけを確認する)。"""
        bundle = self.cg.make_bundle(steps, python, [d['view'] for d in PROPOSAL['datasets']])
        for _ in range(15):
            try:
                result = runs.run_and_record(self.user, self.plan, bundle, POLICY, chunk_rows=500)
            except ExecutionStopped:
                time.sleep(2)
                continue
            if result['status'] != 'refused':
                return result
            time.sleep(2)
        return result

    def test_module_attributes_cannot_reach_sys_or_other_modules_at_runtime(self):
        """許可したモジュールの属性から、sys・osなどのモジュールへ届く迂回を、実行時に拒否する。"""
        cases = {
            'statistics.sys': "import statistics\nx = statistics.sys.modules\nemit_report('到達してはいけない')",
            'from import': "from statistics import sys\nemit_report('到達してはいけない')",
            'json.decoder': "import json\nx = json.decoder\nemit_report('到達してはいけない')",
            're.enum': "import re\nx = re.enum\nemit_report('到達してはいけない')",
        }
        for label, python in cases.items():
            with self.subTest(label):
                result = self.run_bundle([], python)
                self.assertEqual(result['status'], 'failed', result)
                self.assertNotIn('result', result['launcher'])
        ok = self.run_bundle([], "import statistics, json, decimal\nemit_report(json.dumps({'m': statistics.mean([1, 2, 3]), 'd': str(decimal.Decimal('1.5'))}))")
        self.assertEqual(ok['status'], 'ok', ok)
        self.assertEqual(json.loads(ok['launcher']['result']['report']), {'m': 2, 'd': '1.5'})
