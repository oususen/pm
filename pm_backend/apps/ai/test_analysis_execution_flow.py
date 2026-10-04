"""実Redis→ワーカーループ→開発DB読み取り→WSL Docker→履歴・結果APIの通し確認。

履歴・設定はSQLiteテストDBだけ。実AIは呼ばず、承認済みコードはテストの固定値。
AI_ANALYSIS_LAUNCHER_URL_FOR_TESTの明示設定時だけ実行する。
ワーカーループは別スレッドで動かすため、独立プロセスの耐障害確認とは区別する。
"""
import json
import os
import threading
import time
import unittest
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from ai.analysis_execution_views import AIAnalysisExecuteView, AIAnalysisJobView, AIAnalysisJobCancelView, AIAnalysisRunsView
from ai.config.models import AIAnalysisExecutionPolicy
from ai.models import AIAnalysisRun
from ai.services import analysis_job_service as jobs
from ai.services.analysis_codegen_service import make_bundle
from ai.test_analysis_execution import PROPOSAL, approved_counts


@unittest.skipUnless(os.environ.get('AI_ANALYSIS_LAUNCHER_URL_FOR_TEST'), '実launcherの明示設定が必要')
class ExecutionFlowTests(TransactionTestCase):
    databases = {'default'}

    def setUp(self):
        self.overrides = override_settings(DEBUG=True, ALLOWED_HOSTS=['testserver'], AI_ANALYSIS_LAUNCHER_URL=os.environ['AI_ANALYSIS_LAUNCHER_URL_FOR_TEST'])
        self.overrides.enable()
        self.addCleanup(self.overrides.disable)
        self.prefix = patch.object(jobs.JobStore, 'prefix', 'test:analysis:flow:' + uuid4().hex + ':')
        self.prefix.start()
        self.addCleanup(self.prefix.stop)
        self.user = get_user_model().objects.create(username='analysis-flow-test')
        AIAnalysisExecutionPolicy.objects.create(plan_cache_ttl_minutes=5, max_memory_mb=512, max_cpu_cores=1, max_execution_seconds=30)
        self.store, self.factory = jobs.JobStore(), APIRequestFactory()
        self.counts = approved_counts()
        self.plan_ids, self.worker_errors = [], []
        self.stop = threading.Event()
        def worker():
            try:
                jobs.worker_loop(self.stop)
            except Exception as exc:
                self.worker_errors.append(type(exc).__name__)
        self.thread = threading.Thread(target=worker, daemon=True)
        self.thread.start()
        self.wait(lambda: self.store.client.get(self.store.worker_key))
        self.addCleanup(self.cleanup)

    def cleanup(self):
        active = self.store.client.get(self.store.active_key)
        if active:
            try:
                self.store.cancel(active, self.user.pk)
            except Exception:
                pass
        self.stop.set()
        self.thread.join(45)
        self.assertFalse(self.thread.is_alive(), 'テストワーカーが残っています')
        keys = list(self.store.client.scan_iter(self.store.prefix + '*'))
        if keys:
            self.store.client.delete(*keys)
        for plan_id in self.plan_ids:
            self.store.client.delete(self.store.plans._key(plan_id))

    def wait(self, condition):
        until = time.monotonic() + 60
        while time.monotonic() < until:
            value = condition()
            if value:
                return value
            if self.worker_errors:
                self.fail('ワーカーエラー: ' + ','.join(self.worker_errors))
            time.sleep(0.1)
        self.fail('通し確認が期限内に終わりませんでした')

    def approved(self, python):
        proposal = {**PROPOSAL, 'conditions': '指定期間の全登録行'}
        plan = self.store.plans.create(self.user.pk, proposal, 5)
        self.plan_ids.append(plan['id'])
        bundle = make_bundle([], python, [d['view'] for d in proposal['datasets']])
        plan.update(status='data_approved', method_approved_at=datetime.now().isoformat(), data_approved_at=datetime.now().isoformat(),
                    preview={'datasets': [{'view': v, 'rows': n} for v, n in self.counts.items()], 'over_limit': False},
                    codegen={'status': 'code_approved', 'steps': [], 'python': python,
                             'executed_code_sha256': bundle.executed_code_sha256, 'wrapper_version': bundle.wrapper_version,
                             'trial': {'status': 'passed', 'executed_code_sha256': bundle.executed_code_sha256}})
        self.store.client.set(self.store.plans._key(plan['id']), json.dumps(plan), ex=300)
        return plan, bundle

    def request(self, view, method='get', data=None, **kwargs):
        request = self.factory.get('/') if method == 'get' else self.factory.post('/', data or {}, format='json')
        force_authenticate(request, self.user)
        return view.as_view()(request, **kwargs)

    def execute(self, python):
        plan, bundle = self.approved(python)
        response = self.request(AIAnalysisExecuteView, 'post', {'revision': plan['revision'], 'executed_code_sha256': bundle.executed_code_sha256}, plan_id=plan['id'])
        self.assertEqual(response.status_code, 202, response.data)
        return response.data['id'], bundle

    def test_success_result_and_history_from_actual_snapshot(self):
        job_id, bundle = self.execute("emit_table('出荷', ['行数', '数量'], con.sql('SELECT COUNT(*), SUM(quantity) FROM v_ai_shipment').fetchall())\n"
                                      "emit_chart('bar', '数量', ['a'], [{'name':'s','values':[1]}])\nemit_report('通し確認')")
        self.wait(lambda: self.store.get(job_id, self.user.pk)['status'] in jobs.TERMINAL)
        response = self.request(AIAnalysisJobView, job_id=job_id)
        self.assertEqual(response.data['status'], 'success', response.data)
        self.assertEqual(response.data['counts'], self.counts)
        self.assertEqual(response.data['result']['tables'][0]['rows'][0][0], self.counts['v_ai_shipment'])
        run = AIAnalysisRun.objects.get(pk=response.data['run_id'])
        self.assertEqual(run.executed_code_sha256, bundle.executed_code_sha256)
        self.assertEqual(run.status, 'success')
        self.assertIsNotNone(run.loaded_at)
        self.assertEqual(run.cleanup, {'db_connection': 'closed', 'container': 'closed'})
        self.assertNotIn('通し確認', json.dumps(run.__dict__, default=str, ensure_ascii=False))
        history = self.request(AIAnalysisRunsView)
        self.assertEqual(history.status_code, 200, history.data)
        self.assertEqual(history.data['results'][0]['id'], run.pk)
        self.assertNotIn('result', history.data['results'][0])
        self.assertFalse(self.store.client.exists(self.store.active_key))

    def test_cancel_after_python_started_discards_result_and_updates_history(self):
        job_id, _ = self.execute("emit_report('途中結果は採用しない')\nwhile True: pass")
        # E送信後も実行中であることを確認する。run_idだけでは取得中との区別にならない。
        self.wait(lambda: self.store.raw(job_id).get('run_id'))
        self.wait(lambda: self.request(AIAnalysisJobView, job_id=job_id).data['status'] == 'running')
        control = jobs.ExecutionControl(self.store, self.store.raw(job_id))
        self.wait(lambda: control.launcher('GET')[1].get('stage') == 'python')
        response = self.request(AIAnalysisJobCancelView, 'post', job_id=job_id)
        self.assertEqual(response.status_code, 202, response.data)
        self.wait(lambda: self.store.get(job_id, self.user.pk)['status'] in jobs.TERMINAL)
        job = self.store.get(job_id, self.user.pk)
        self.assertEqual(job['status'], 'cancelled', job)
        self.assertIsNone(job['result'])
        self.assertEqual(job['cleanup'], {'db_connection': 'closed', 'container': 'closed'})
        run = AIAnalysisRun.objects.get(pk=job['run_id'])
        self.assertEqual(run.status, 'cancelled')
        self.assertEqual(run.reason, 'user_cancelled')
        self.assertEqual(run.cleanup, job['cleanup'])
