"""開発の明示的な実行枠復旧。確認の欠落・競合は解除しない。"""
import json
import queue
import subprocess
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import UUID

from django.conf import settings
from django.db import transaction
from redis.exceptions import WatchError

from ai.models import AIAnalysisRun
from ai.services.analysis_job_service import JobStore, TERMINAL, acquire_worker_lock, execution_enabled
from ai.services.analysis_plan_store import AnalysisError
from ai.services.analysis_run_service import HEARTBEAT_SECONDS, reason_text
from ai.services.analysis_execution_service import launcher_endpoint


@contextmanager
def launcher_guard():
    """WSLのlauncherロックを保持したまま、停止とDocker残骸ゼロを読み取り確認する。"""
    path = Path(settings.BASE_DIR).parent / 'analysis-sandbox' / 'tools' / 'recovery_guard.py'
    linux_path = '/mnt/' + path.drive[0].lower() + path.as_posix()[2:]
    process = subprocess.Popen(['wsl.exe', '-d', 'Ubuntu-24.04', '-u', 'root', '--', 'python3', linux_path],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    messages = queue.Queue()
    reader = threading.Thread(target=lambda: messages.put(process.stdout.readline()), daemon=True)
    reader.start()
    try:
        line = messages.get(timeout=HEARTBEAT_SECONDS)
        evidence = json.loads(line)
        if process.poll() is not None or evidence != {'launcher_stopped': True, 'containers_absent': True}:
            raise AnalysisError('launcher停止・コンテナ不在を確認できません。解除しません。', 409)
        yield lambda: process.poll() is None  # 確認プロセスが終了してロックが失われた場合は、更新直前にも拒否する。
    except (ValueError, queue.Empty, OSError) as exc:
        raise AnalysisError('復旧の安全確認に失敗しました。解除しません。', 409) from exc
    finally:
        if process.stdin:
            process.stdin.close()
        try:
            process.wait(timeout=HEARTBEAT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()  # 自分が起動した確認用プロセスだけを終了する。
            process.wait()
        process.stdout.close()
        reader.join(1)


def recover_slot(job_id, apply=False):
    """既定は確認のみ。DBがpending/failed/未確認なら、証拠を作れないため解除しない。"""
    execution_enabled()
    if launcher_endpoint()[1] != 8091:
        raise AnalysisError('復旧コマンドは標準の開発launcher(8091)だけが対象です。解除しません。', 409)
    try:
        if str(UUID(job_id)) != job_id:
            raise ValueError()
    except (ValueError, TypeError):
        raise AnalysisError('正しいジョブIDが必須です。', 400) from None
    store = JobStore()
    process_lock = acquire_worker_lock(store.prefix)
    try:
        with launcher_guard() as guard_alive:
            with store.client.pipeline() as pipe:
                pipe.watch(store.active_key, store.worker_key, store.key(job_id))
                if pipe.get(store.active_key) != job_id or pipe.get(store.worker_key):
                    raise AnalysisError('対象の実行枠が一致しないか、ワーカーの生存キーが残っています。解除しません。', 409)
                job = json.loads(pipe.get(store.key(job_id)) or 'null')
                if not isinstance(job, dict) or job.get('id') != job_id:
                    raise AnalysisError('対象ジョブを確認できません。解除しません。', 409)
                if job.get('cleanup', {}).get('db_connection') not in ('closed', 'not_started'):
                    raise AnalysisError('DB接続の後始末を確認できません。解除しません。', 409)
                # 履歴がある場合は、Redisの記録だけを根拠にせず履歴側も照合する。
                with transaction.atomic():
                    run = None
                    if job.get('run_id'):
                        run = AIAnalysisRun.objects.select_for_update().get(pk=job['run_id'])
                        if run.plan_id != job['plan_id'] or run.cleanup.get('db_connection') not in ('closed', 'not_started'):
                            raise AnalysisError('実行履歴の後始末を照合できません。解除しません。', 409)
                    if not apply:
                        if not guard_alive():
                            raise AnalysisError('復旧の確認ロックが失われました。解除しません。', 409)
                        return {'job_id': job_id, 'checks_passed': True, 'released': False}
                    job['cleanup']['container'] = 'closed'
                    job['recovery'] = {'at': datetime.now().isoformat(), 'source': 'management_command'}
                    job.pop('result', None)  # 復旧で結果の採否を推測・再表示しない。
                    job.pop('snapshot', None)
                    if job['status'] not in TERMINAL:
                        job.update(status='unknown', reason='worker_unknown', detail=reason_text('worker_unknown'))
                    if run is not None:
                        run.cleanup = job['cleanup']
                        if run.status in ('running', 'unknown'):
                            run.status, run.reason, run.detail = 'unknown', 'worker_unknown', reason_text('worker_unknown')
                        run.save(update_fields=['cleanup', 'status', 'reason', 'detail'])
                    if not guard_alive():
                        raise AnalysisError('復旧の確認ロックが失われました。解除しません。', 409)
                    pipe.multi()
                    pipe.set(store.key(job_id), json.dumps(job, ensure_ascii=False), ex=job['ttl'])
                    pipe.delete(store.active_key)  # WATCHしたジョブID・生存キー・状態が変わっていれば全体を拒否。
                    pipe.execute()
                return {'job_id': job_id, 'checks_passed': True, 'released': True}
    except WatchError as exc:
        raise AnalysisError('確認中に実行状態が変わりました。解除しません。', 409) from exc
    finally:
        process_lock.close()
