"""開発限定の分析ジョブ。Redisの1件の引渡し枠を専用ワーカーが処理する(待ち行列なし)。

結果はRedisに一時保持するだけ。DB履歴には本文を保存しない。生存確認を失っても
稼働中の枠を自動解放しない。後始末未確認の実行と別の実行を重ねないためである。
"""
import http.client
import hashlib
import json
import logging
import secrets
import socket
import threading
import tempfile
import time
from copy import deepcopy
from datetime import datetime, timedelta
from uuid import uuid4
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import close_old_connections, transaction
from redis.exceptions import WatchError

from ai.config.service import get_analysis_execution_policy
from ai.models import AIAnalysisRun
from ai.services.analysis_codegen_service import bundle_from_plan
from ai.services.analysis_execution_service import ExecutionStopped, launcher_endpoint
from ai.services.analysis_plan_store import AnalysisError, AnalysisPlanStore
from ai.services.analysis_template_reuse_service import check_plan_template
from ai.services.analysis_worker_identity import (
    current_code_version, ensure_jst_clock, worker_registration, worker_version_matches,
)
from ai.services.analysis_run_service import (
    HEARTBEAT_SECONDS, STALE_SECONDS, HistoryError, failure_detail, reason_text, record_not_run, run_and_record,
    _container_cleanup,
)

logger = logging.getLogger(__name__)

MAX_RESULT_BYTES = 5 * 1024 * 1024  # runnerと同じ既承認の上限
TERMINAL = ('success', 'failed', 'cancelled', 'expired')
PUBLIC_FIELDS = ('id', 'plan_id', 'revision', 'status', 'reason', 'detail', 'created_at', 'finished_at',
                 'run_id', 'scope', 'counts', 'cleanup', 'result', 'result_expires_at', 'executed_code_sha256')
_PROCESS_LOCKS = []  # プロセス終了まで保持。Redis再起動で旧ワーカーとの二重実行を許さない。
# モジュール読込み時の版を固定する。heartbeatで新しいファイルの版を名乗らない。
_LOADED_CODE_VERSION = current_code_version()


class WorkerStaleError(AnalysisError):
    reason = 'worker_stale'

    def __init__(self):
        super().__init__('専用ワーカーを再起動してください。', 503)


def acquire_worker_lock(namespace):
    """Windows/WSLの専用ワーカーを同一ホストで1つにする。中身は1バイトで業務情報なし。"""
    import os
    name = hashlib.sha256((settings.AI_ANALYSIS_REDIS_URL + namespace).encode()).hexdigest()
    handle = open(Path(tempfile.gettempdir()) / ('pm-analysis-worker-' + name + '.lock'), 'a+b')
    try:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return handle
    except OSError as exc:
        handle.close()
        raise AnalysisError('同じホストの分析専用ワーカーが稼働しています。', 409) from exc


def execution_enabled():
    """本番で設定を誤って加えても有効化しない。専用ワーカーも同じ条件を使う。"""
    if not settings.DEBUG:
        raise AnalysisError('本番では、分析の実行基盤が有効化されていません。', 503)
    launcher_endpoint()


def checked_bundle(plan, revision, code_hash):
    if type(revision) is not int or plan['revision'] != revision:
        raise AnalysisError('分析案の版が変わりました。最新状態を確認してください。', 409)
    if datetime.fromisoformat(plan['expires_at']) <= datetime.now():
        raise AnalysisError('分析案の期限が切れました。', 410)
    if plan.get('status') != 'data_approved' or not plan.get('method_approved_at') or not plan.get('data_approved_at'):
        raise AnalysisError('分析手順・データ範囲の承認が必要です。', 409)
    bundle = bundle_from_plan(plan)
    trial = (plan.get('codegen') or {}).get('trial') or {}
    if (trial.get('status') != 'passed' or trial.get('executed_code_sha256') != bundle.executed_code_sha256
            or code_hash != bundle.executed_code_sha256):
        raise AnalysisError('試行に合格し、承認した同じコードだけを実行できます。', 409)
    if not plan.get('preview') or plan['preview'].get('over_limit'):
        raise AnalysisError('対象件数の確認と承認が必要です。', 409)
    return bundle


class JobStore:
    prefix = 'pm:ai:analysis:execution:'

    def __init__(self):
        self.plans = AnalysisPlanStore()
        self.client = self.plans.client
        self.active_key, self.worker_key = self.prefix + 'active', self.prefix + 'worker'

    def key(self, job_id):
        return self.prefix + str(job_id)

    def worker_current(self, raw):
        try:
            return worker_version_matches(raw, current_code_version())
        except OSError:
            return False  # 現行版を確認できない場合も実行しない。

    def raw(self, job_id):
        raw = self.client.get(self.key(job_id))
        if raw is None:
            raise AnalysisError('実行情報・結果の保持期限が切れたか、保持先が再起動しました。履歴で確認してください。', 410)
        return json.loads(raw)

    def get(self, job_id, owner_id):
        job = self.raw(job_id)
        if job['owner_id'] != owner_id:
            raise AnalysisError('実行が見つかりません。', 404)
        public = {k: job.get(k) for k in PUBLIC_FIELDS}
        if job['status'] not in TERMINAL and self.client.get(self.worker_key) != job['worker']:
            public.update(status='unknown', reason='worker_unknown', detail='生存確認失敗・状態不明です。停止や後始末完了とは断定できません。')
        return public

    def update(self, job_id, change, release=False, ttl=None):
        key = self.key(job_id)
        while True:
            try:
                with self.client.pipeline() as pipe:
                    pipe.watch(key, self.active_key)
                    job = json.loads(pipe.get(key) or 'null')
                    if job is None:
                        raise AnalysisError('実行状態を保存できません。', 503)
                    change(job)
                    active = pipe.get(self.active_key)
                    pipe.multi()
                    pipe.set(key, json.dumps(job, ensure_ascii=False, allow_nan=False), **({'ex': ttl} if ttl else {'keepttl': True}))
                    if release and active == job_id:
                        pipe.delete(self.active_key)
                    pipe.execute()
                    return job
            except WatchError:
                continue

    def submit(self, user, plan_id, revision, code_hash, template_confirmed=None):
        execution_enabled()
        policy = get_analysis_execution_policy()
        plan_key = self.plans._key(plan_id)
        try:
            with self.client.pipeline() as pipe:
                pipe.watch(plan_key, self.active_key, self.worker_key)
                plan = self.plans._decode(pipe.get(plan_key), user.pk)
                checked_bundle(plan, revision, code_hash)
                # テンプレート由来の分析案は、受付時にも状態・内容・本人の権限を確認し、未承認なら明示の確認(テンプレートIDつき)を求める
                check_plan_template(plan, user, template_confirmed, accepting=True)
                if pipe.get(self.active_key):
                    raise AnalysisError('実行中、または後始末未確認の分析があります。完了を待ってください。', 429)
                worker = pipe.get(self.worker_key)
                if not worker:
                    raise AnalysisError('分析専用ワーカーが起動していません。実行していません。', 503)
                if not self.worker_current(worker):
                    raise WorkerStaleError()
                job_id = str(uuid4())
                plan = deepcopy(plan)
                plan['revision'] += 1
                plan['execution'] = {'job_id': job_id}
                proposal = plan['proposal']
                snapshot = deepcopy(plan)
                snapshot.pop('codegen', None)  # コード本文は元の分析案だけに保持し、その期限を延ばさない。
                job = {
                    'id': job_id, 'owner_id': user.pk, 'plan_id': plan_id, 'revision': plan['revision'],
                    'status': 'pending', 'reason': '', 'detail': '', 'created_at': datetime.now().isoformat(),
                    'worker': worker, 'token': secrets.token_hex(32), 'cancel_requested': False,
                    'snapshot': snapshot, 'ttl': policy.plan_cache_ttl_minutes * 60,
                    'scope': {k: proposal[k] for k in ('datasets', 'date_from', 'date_to', 'conditions')},
                    'executed_code_sha256': code_hash, 'counts': None,
                    'cleanup': {'db_connection': 'not_started', 'container': 'not_started'},
                }
                pipe.multi()
                pipe.set(plan_key, json.dumps(plan, ensure_ascii=False), xx=True, keepttl=True)
                pipe.set(self.key(job_id), json.dumps(job, ensure_ascii=False), nx=True)
                pipe.set(self.active_key, job_id, nx=True)  # 生存不明で自動失効させない
                if not all(pipe.execute()):
                    raise AnalysisError('実行を受け付けられませんでした。自動再送せず状態を確認してください。', 503)
                return self.get(job_id, user.pk)
        except WatchError as exc:
            raise AnalysisError('別の操作と競合しました。自動再送せず最新状態を確認してください。', 409) from exc

    def cancel(self, job_id, owner_id):
        self.get(job_id, owner_id)
        def apply(job):
            if job['owner_id'] != owner_id:
                raise AnalysisError('実行が見つかりません。', 404)
            if job['status'] in TERMINAL:
                raise AnalysisError('この実行は終了しています。', 409)
            job.update(cancel_requested=True, status='cancel_requested')
        self.update(job_id, apply)
        return self.get(job_id, owner_id)


class ExecutionControl:
    """停止要求・Redis異常を監視する。ソケットを閉じる前に同じIDのlauncherへ中止を依頼する。"""
    def __init__(self, store, job):
        self.store, self.job_id, self.token, self.worker = store, job['id'], job['token'], job['worker']
        self.event, self.stop = threading.Event(), threading.Event()
        self.reason, self.sock = 'user_cancelled', None
        self.thread = threading.Thread(target=self.monitor, daemon=True)

    def check(self):
        if self.event.is_set():
            raise ExecutionStopped(self.reason, reason_text(self.reason), 409)

    def attach(self, sock):
        self.sock = sock
        if self.event.is_set():
            self.interrupt()

    def detach(self):
        self.sock = None

    def launcher(self, method):
        host, port = launcher_endpoint()
        connection = http.client.HTTPConnection(host, port, timeout=10)
        try:
            path = '/v1/jobs/' + self.job_id + ('/cancel' if method == 'POST' else '')
            connection.request(method, path, body=b'' if method == 'POST' else None, headers={'X-Analysis-Control': self.token})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def interrupt(self):
        try:
            self.launcher('POST')
        except Exception:
            pass  # 削除できたとは扱わない。最終状態の照合で未確認を残す。
        try:
            if self.sock is not None:
                self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def monitor(self):
        while not self.stop.wait(0.1):
            try:
                cancelled = self.store.raw(self.job_id)['cancel_requested']
                if self.store.client.get(self.store.worker_key) != self.worker:
                    self.reason, cancelled = 'worker_unknown', True
            except Exception:
                self.reason, cancelled = 'execution_state_unavailable', True
            if cancelled:
                self.event.set()
                self.interrupt()
                return


def _cleanup_complete(cleanup):
    return all(cleanup.get(k) in ('closed', 'not_started') for k in ('db_connection', 'container'))


def process_job(store, job_id, worker):
    """Webから独立したプロセスでのみ呼ぶ。本文は保存先Redisへ返すだけでログに出さない。"""
    job = store.raw(job_id)
    if job['worker'] != worker or job['status'] not in ('pending', 'cancel_requested'):
        return
    plan, run_id = job['snapshot'], None
    control = ExecutionControl(store, job)
    control.thread.start()
    cleanup_lock = threading.RLock()
    late_cleanup = {}
    def db_done(status):
        with cleanup_lock:
            late_cleanup['db_connection'] = status
            if store.raw(job_id)['status'] in TERMINAL:
                # 履歴確定後の通知は、同じロックで履歴とキャッシュを照合する。
                # trackerの通知が先に届いていても、最終確定でpendingへ戻したままにしない。
                if run_id is not None:
                    with transaction.atomic():
                        run = AIAnalysisRun.objects.select_for_update().get(pk=run_id)
                        run.cleanup = {**run.cleanup, 'db_connection': status}
                        run.save(update_fields=['cleanup'])
                def apply(current):
                    current['cleanup']['db_connection'] = status
                updated = store.update(job_id, apply)
                if _cleanup_complete(updated['cleanup']):
                    store.update(job_id, lambda current: None, release=True, ttl=job['ttl'])
    def started(pk):
        nonlocal run_id
        run_id = pk
        store.update(job_id, lambda current: current.update(run_id=pk))
    outcome, result, user, policy = None, None, None, None
    execution_entered = False
    try:
        execution_enabled()
        user = get_user_model().objects.get(pk=job['owner_id'])
        policy = get_analysis_execution_policy()
        try:
            current = store.plans.get(job['plan_id'], user.pk)
        except AnalysisError as exc:
            if exc.status_code != 410:
                raise
            run = record_not_run(user, plan, 'expired', 'plan_expired', policy)
            outcome = {'status': 'expired', 'reason': 'plan_expired', 'run_id': run.pk, 'cleanup': job['cleanup']}
        if outcome is None:
            # 受付後に却下・置換済みになった場合は、実行を開始しない(開始済みの実行は止めない)
            check_plan_template(current, user, accepting=False)
            bundle = checked_bundle(current, job['revision'], job['executed_code_sha256'])
            if job['cancel_requested']:
                run = record_not_run(user, plan, 'cancelled', 'user_cancelled', policy)
                outcome = {'status': 'cancelled', 'reason': 'user_cancelled', 'run_id': run.pk, 'cleanup': job['cleanup']}
            else:
                store.update(job_id, lambda current: current.update(status='running') if not current['cancel_requested'] else None)
                execution_entered = True
                result = run_and_record(user, current, bundle, policy, control=control, on_started=started, on_cleanup_done=db_done)
                fetch, launcher = result.get('fetch') or {}, result.get('launcher') or {}
                cleanup = {**fetch.get('cleanup', {}), 'container': _container_cleanup(launcher)}
                ok = result['status'] == 'ok' and _cleanup_complete(cleanup)
                outcome = {'status': 'success' if ok else 'failed', 'reason': '' if ok else result.get('reason') or launcher.get('reason') or 'cleanup_pending',
                           'run_id': result['run_id'], 'cleanup': cleanup, 'counts': fetch.get('fetched_rows')}
                if not ok:  # 子のPython異常終了の、例外の種類名つきの説明を、ジョブ・履歴の確定まで引き渡す(Codex P2)
                    outcome['detail'] = failure_detail(outcome['reason'], launcher)
    except Exception as exc:
        reason = getattr(exc, 'reason', 'history_failed' if isinstance(exc, HistoryError) else (
            'plan_expired' if isinstance(exc, AnalysisError) and exc.status_code == 410 else 'execution_failed'))
        progress = getattr(exc, 'progress', {})
        # 開始行の保存失敗は取得前と確定できる。それ以外で項目が欠けた場合は、未開始と推測しない。
        not_started = not execution_entered or (isinstance(exc, HistoryError) and exc.outcome is None and run_id is None)
        db_cleanup = {'db_connection': 'not_started' if not_started else 'unconfirmed'}
        outcome = {'status': 'cancelled' if reason == 'user_cancelled' else ('expired' if reason == 'plan_expired' else 'failed'), 'reason': reason,
                   'run_id': getattr(exc, 'run_id', run_id), 'counts': progress.get('fetched_rows'),
                   'cleanup': {**db_cleanup, **(getattr(exc, 'cleanup', {}) or {}), 'container': 'unconfirmed' if progress.get('transmit_started') else 'not_started'}}
        if isinstance(exc, HistoryError) and exc.outcome:
            outcome['cleanup'] = exc.outcome.get('cleanup', outcome['cleanup'])
        if run_id is None and user is not None and policy is not None and not isinstance(exc, HistoryError):
            # 引渡し後に版・承認が変わった場合も、実行せず履歴へ固定文だけを残す。
            try:
                run = record_not_run(user, plan, outcome['status'], outcome['reason'], policy)
                outcome['run_id'] = run.pk
            except HistoryError:
                outcome.update(reason='history_failed')
    finally:
        control.stop.set()
        control.thread.join(11)
        close_old_connections()
    # 通信を中止した場合も、launcherの削除完了を別経路で照合する。無応答・404を完了と見なさない。
    if outcome['cleanup'].get('container') == 'unconfirmed':
        until = time.monotonic() + 30  # 既存launcherの後始末猶予
        while time.monotonic() < until:
            try:
                status, state = control.launcher('GET')
                if status != 200:
                    break
                if state.get('done'):
                    outcome['cleanup']['container'] = state.get('cleanup', 'unconfirmed')
                    break
            except Exception:
                break
            time.sleep(0.1)
    with cleanup_lock:
        outcome['cleanup'].update(late_cleanup)
        def finish(current):
            # 中止要求が結果確定より先なら、成功結果を絶対に採用しない。
            if current['cancel_requested'] and outcome['status'] == 'success':
                outcome.update(status='cancelled', reason='user_cancelled')
            # 子のPythonの異常終了だけ、例外の種類名を足した説明(analysis_run_service.child_failure_detail)をそのまま使う
            detail = outcome.get('detail') if outcome['reason'] == 'child_exit_nonzero' and outcome.get('detail') else (reason_text(outcome['reason']) if outcome['reason'] else '')
            current.update(outcome, detail=detail, finished_at=datetime.now().isoformat())
            current.pop('snapshot', None)
            current.pop('result', None)
            if current['status'] == 'success':
                body = result['launcher']['result']
                try:
                    valid = len(json.dumps(body, ensure_ascii=False, allow_nan=False).encode('utf-8')) <= MAX_RESULT_BYTES
                except (ValueError, TypeError):
                    valid = False
                if valid:
                    current['result'] = body
                else:
                    current.update(status='failed', reason='result_too_large', detail=reason_text('result_too_large'))
            current['result_expires_at'] = (datetime.now() + timedelta(seconds=job['ttl'])).isoformat()
            # 履歴の最終更新にも成功してから結果を保存する。Redisの競合時は同じ確定を再照合する。
            if outcome.get('run_id'):
                with transaction.atomic():
                    run = AIAnalysisRun.objects.select_for_update().get(pk=outcome['run_id'])
                    run.cleanup = current['cleanup']
                    run.status, run.reason, run.detail = current['status'], current['reason'], current['detail']
                    run.save(update_fields=['cleanup', 'status', 'reason', 'detail'])
        completed = store.update(job_id, finish, ttl=job['ttl'] if _cleanup_complete(outcome['cleanup']) else None)
        if _cleanup_complete(completed['cleanup']):
            store.update(job_id, lambda current: None, release=True)


def reconcile_cleanup(store, job_id):
    """終端ジョブの後始末だけを再照合する。404・無応答・healthのidleは削除の証拠にしない。"""
    job = store.raw(job_id)
    if job['status'] not in TERMINAL or job.get('cleanup', {}).get('container') not in ('unconfirmed', 'pending'):
        return
    try:
        status, state = ExecutionControl(store, job).launcher('GET')
    except Exception:
        return
    if status != 200 or state.get('done') is not True or state.get('cleanup') not in ('closed', 'not_started'):
        return
    def apply(current):
        if current['status'] not in TERMINAL:
            return
        current['cleanup']['container'] = state['cleanup']
        if current.get('run_id'):
            with transaction.atomic():
                run = AIAnalysisRun.objects.select_for_update().get(pk=current['run_id'])
                run.cleanup = current['cleanup']
                run.save(update_fields=['cleanup'])
    updated = store.update(job_id, apply)
    if _cleanup_complete(updated['cleanup']):
        store.update(job_id, lambda current: None, release=True, ttl=job['ttl'])


def worker_loop(stop=None):
    """管理コマンドから明示起動する。Webサーバー・本番の起動処理には組み込まない。"""
    execution_enabled()
    if settings.USE_TZ or settings.TIME_ZONE != 'Asia/Tokyo':
        raise AnalysisError('専用ワーカーの時刻設定をJST・naiveにしてください。', 503)
    try:
        ensure_jst_clock()
    except ValueError:
        raise AnalysisError('専用ワーカーの時刻帯をJSTに設定してください。', 503) from None
    if _LOADED_CODE_VERSION != current_code_version():
        raise WorkerStaleError()
    stop = stop or threading.Event()
    store, worker = JobStore(), worker_registration(uuid4().hex, _LOADED_CODE_VERSION)
    process_lock = acquire_worker_lock(store.prefix)
    try:
        host, port = launcher_endpoint()
        connection = http.client.HTTPConnection(host, port, timeout=HEARTBEAT_SECONDS)
        try:
            connection.request('GET', '/v1/health')
            response = connection.getresponse()
            health = json.loads(response.read())
            if response.status != 200 or health.get('status') != 'ready' or health.get('busy') is not False:
                raise AnalysisError('隔離基盤が利用不可、実行中、または後始末未確認です。', 503)
        finally:
            connection.close()
    except Exception:
        process_lock.close()
        raise
    try:
        claimed = store.client.set(store.worker_key, worker, nx=True, ex=STALE_SECONDS)
    except Exception:
        process_lock.close()
        raise
    if not claimed:
        process_lock.close()
        raise AnalysisError('分析専用ワーカーはすでに起動しています。', 409)
    _PROCESS_LOCKS.append(process_lock)
    def renew():
        while not stop.wait(HEARTBEAT_SECONDS):
            try:
                ok = store.client.eval("if redis.call('get',KEYS[1])==ARGV[1] then return redis.call('expire',KEYS[1],ARGV[2]) else return 0 end",
                                       1, store.worker_key, worker, STALE_SECONDS)
                if not ok:
                    stop.set()
            except Exception:
                stop.set()
    thread = threading.Thread(target=renew, daemon=True)
    thread.start()
    try:
        while not stop.wait(0.1):
            job_id = store.client.get(store.active_key)
            if job_id:
                job = store.raw(job_id)
                if job['status'] in TERMINAL:
                    reconcile_cleanup(store, job_id)
                    stop.wait(HEARTBEAT_SECONDS)  # 未解決の終端ジョブを0.1秒ごとに読み続けない。
                elif job['worker'] == worker:
                    process_job(store, job_id, worker)
                else:
                    stop.wait(HEARTBEAT_SECONDS)  # 旧ワーカーの未完了ジョブを再実行しない。
    except Exception:
        logger.error('分析専用ワーカーが異常終了しました。実行枠を保持し、状態不明として復旧確認を要求します。')
        raise AnalysisError('分析専用ワーカーが異常終了しました。状態と後始末を確認してください。', 503) from None
    finally:
        stop.set()
        thread.join(11)
        try:
            store.client.eval("if redis.call('get',KEYS[1])==ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end", 1, store.worker_key, worker)
        except Exception:
            logger.error('ワーカー生存キーを削除できません。既存の有効期限まで残る可能性があります。実行枠は保持します。')
