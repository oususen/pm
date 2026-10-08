"""分析の実行履歴(AI分析基盤仕様書§5.5)を、実行の前後で保存する。

方針:
- 開始時に`running`の行を保存し、保存できなければ実行しない。
- 実行中は、別スレッドがheartbeat_atを更新する(生存確認)。停止の判定は、heartbeatが一定時間途切れた`running`の行だけを、
  条件付き更新で`unknown`(生存確認失敗・状態不明)にする。実行が停止したとは断定しない。起動時の一括更新はしない。
- 終了時は、元の実行結果(状態・理由・後始末)を確定して保存する。確定できなければ、結果を返さずに、元の結果を含むエラーにする。
  「必ず保存できる」とは保証しない。
- 後始末が`pending`の間は、完了扱いにしない。待機中の処理が終わったときに、`pending`の行だけを最終状態へ更新する。
- コード本文・結果の中身・取得した明細行・個人情報・AIの応答本文は保存しない(ハッシュと件数と理由だけ)。
"""
import builtins
import hashlib
import logging
import os
import re
import socket
import threading
from datetime import datetime, timedelta
from uuid import uuid4

from django.db import close_old_connections, transaction

from ai.models import AIAnalysisRun
from ai.services.analysis_execution_service import (
    CHUNK_ROWS, DEADLINES, ExecutionStopped, execute_approved_analysis,
)
from ai.services.analysis_plan_store import AnalysisError

logger = logging.getLogger(__name__)

# 開発用の暫定値(BOSS承認 2026-10-04)。
HEARTBEAT_SECONDS = 10
STALE_SECONDS = 60
# 失敗理由の説明は、理由コードごとの固定文だけを保存する。launcher・DuckDB・例外の説明文は、実データを含み得るため保存しない。
REASON_TEXT = {
    'approved_count_changed': '承認時から件数が変わりました。',
    'fetch_rows_exceeded': '対象が取得行数の上限を超えました。',
    'fetch_count_mismatch': '取得行数がCOUNTと一致しませんでした。',
    'refetch_mismatch': '2回目の取得が1回目と一致しませんでした。',
    'duplicate_key': '一意キー(id)の重複または逆順を検出しました。',
    'stage_deadline_fetch': '取得の期限を超えました。',
    'stage_deadline_transfer': '転送の期限を超えました。',
    'stage_deadline_load': '投入の期限を超えました。',
    'stage_deadline_python': 'Pythonの実行時間を超えました。',
    'fetch_failed': 'データの取得に失敗しました。',
    'unsupported_value': '投入できない値を検出しました。',
    'management_column_missing': '管理列(id)が取得列にありません。',
    'column_type_unknown': '列型が未定義の列があります。',
    'launcher_disabled': '隔離実行が無効です。',
    'launcher_not_allowed': '隔離実行の接続先が許可されていません。',
    'launcher_unreachable': 'launcherとの通信に失敗しました。',
    'load_count_mismatch': 'コンテナへの投入行数が送信行数と一致しませんでした。',
    'busy': '実行中のジョブがあります。',
    'isolation_unavailable': '隔離機能を確認できませんでした。',
    'cleanup_pending': '前回のコンテナを削除できていません。',
    'unexpected_error': '想定外のエラーが発生しました。',
    'plan_expired': '分析案の有効期限が切れました。',
    'template_unavailable': 'テンプレートが再利用できない状態になったため、実行しませんでした。',
    'user_cancelled': '利用者が実行を中止しました。',
    'heartbeat_lost': '生存確認が途切れました。実行が停止したとは断定できないため、状態不明として記録します。',
    'worker_unknown': '分析専用ワーカーの生存確認が失敗しました。状態不明です。',
    'execution_state_unavailable': '実行状態の保持先との通信が失敗しました。',
    'execution_failed': '実行を開始・継続できませんでした。',
    'history_failed': '実行履歴の保存に失敗したため、結果を返しません。',
    'result_too_large': '結果の容量上限を超えました。',
    'result_invalid': '結果の形式が正しくありません。グラフの横軸(x)は値のリストで、各系列の値の個数をxと同じにしてください。',
    'child_exit_nonzero': 'Pythonの実行に失敗しました。出力関数の引数の型・個数やコードを確認してください。',
}
GENERIC_REASON_TEXT = '失敗しました。詳細は理由コードを参照してください。'


def reason_text(reason):
    return REASON_TEXT.get(reason, GENERIC_REASON_TEXT)


UNKNOWN_DETAIL = '生存確認が途切れました。実行が停止したとは断定できないため、状態不明として記録します。'
DELETED_USER_LABEL = '削除済みユーザー'
WORKER_ID = f'{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}'  # プロセスの起動ごとに異なる。実行を担当するプロセスの識別


class HistoryError(Exception):
    """履歴を保存・確定できなかった。元の実行結果(outcome)を含める。結果は呼び出し側へ返さない。"""

    def __init__(self, message, outcome=None):
        super().__init__(message)
        self.outcome = outcome


def sha256_of(text):
    return None if text is None else hashlib.sha256(text.encode('utf-8')).hexdigest()


def _parse(value):
    return datetime.fromisoformat(value) if value else None


def _settings_snapshot(policy, deadlines, chunk_rows):
    limits = {**DEADLINES, **(deadlines or {})}
    return {
        'max_fetch_rows': policy.max_fetch_rows, 'max_execution_seconds': policy.max_execution_seconds,
        'max_memory_mb': policy.max_memory_mb, 'max_cpu_cores': str(policy.max_cpu_cores),
        'plan_cache_ttl_minutes': getattr(policy, 'plan_cache_ttl_minutes', None),
        'fetch_deadline_seconds': limits['fetch'], 'transfer_deadline_seconds': limits['transfer'], 'chunk_rows': chunk_rows,
    }


def mark_unknown_stale(now=None, stale_seconds=STALE_SECONDS):
    """heartbeatが途切れた`running`の行だけを、`unknown`にする。

    更新は、読んだときの状態とheartbeatのままである行に限る(条件付き更新)。遅れて戻った処理が更新した行は、条件に合わず変わらない。
    後始末は完了扱いにせず、pendingとする。更新した件数を返す。
    """
    limit = (now or datetime.now()) - timedelta(seconds=stale_seconds)
    changed = 0
    for run in AIAnalysisRun.objects.filter(status='running', heartbeat_at__lt=limit).only('pk', 'heartbeat_at'):
        changed += AIAnalysisRun.objects.filter(pk=run.pk, status='running', heartbeat_at=run.heartbeat_at).update(
            status='unknown', reason='heartbeat_lost', detail=reason_text('heartbeat_lost'),
            cleanup={'db_connection': 'pending', 'container': 'pending'},
        )
    return changed


class Heartbeat:
    """実行中、heartbeat_atを定期的に更新する別スレッド。自分の行が`running`の間だけ更新する。"""

    def __init__(self, run, interval=HEARTBEAT_SECONDS):
        self.run, self.interval = run, interval
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self):
        try:
            while not self.stopped.wait(self.interval):
                try:
                    AIAnalysisRun.objects.filter(pk=self.run.pk, worker_id=self.run.worker_id, status='running').update(
                        heartbeat_at=datetime.now())
                except Exception:
                    logger.exception('分析実行の生存確認の更新に失敗しました: run=%s', self.run.pk)
        finally:
            close_old_connections()

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.stopped.set()
        self.thread.join(timeout=5)


class CleanupTracker:
    """待機中(pending)だった後始末の最終結果を、履歴へ反映する。

    履歴の確定の書き込みと、通知の反映は、同じロックの下で行う。確定の直前・最中に通知が届いても、取りこぼさない。
    """

    def __init__(self, run_id):
        self.run_id, self.final, self.finished = run_id, None, False
        self.lock = threading.RLock()

    def notify(self, status):
        """接続の後始末が、遅れて終わった(closed / failed)。"""
        with self.lock:
            self.final = status
            if self.finished:
                self._update_db()

    def finalize(self, write):
        """確定する後始末へ、すでに届いた最終結果を反映して、書き込み(write(merge))を行う。書き込みの間、通知は待たせる。"""
        with self.lock:
            result = write(self._merge)
            self.finished = True
            return result

    def _merge(self, cleanup):
        if cleanup.get('db_connection') == 'pending' and self.final:
            return {**cleanup, 'db_connection': self.final}
        return cleanup

    def _update_db(self):
        try:
            with transaction.atomic():
                run = AIAnalysisRun.objects.select_for_update().get(pk=self.run_id)
                if run.cleanup.get('db_connection') == 'pending':
                    run.cleanup = {**run.cleanup, 'db_connection': self.final}
                    run.save(update_fields=['cleanup'])
        except Exception:
            logger.exception('後始末の最終結果を履歴へ反映できませんでした(pendingのまま残ります): run=%s', self.run_id)
        finally:
            close_old_connections()


def _template_columns(plan):
    """テンプレートから作成した分析案の、テンプレートの行のidと版。それ以外はNULL。"""
    template = plan.get('template') or {}
    return {'template_id': template.get('id'), 'template_version': template.get('version')}


def _refinement_columns(plan):
    """結果の改良から作った分析案の、追加の指示(原文)と、改良の元の実行。それ以外はNULL。"""
    refinement = plan.get('refinement') or {}
    return {'refinement_instruction': refinement.get('instruction'), 'refined_from_run_id': refinement.get('from_run_id')}


def start_run(user, plan, bundle, policy, deadlines=None, chunk_rows=CHUNK_ROWS):
    """`running`の行を保存する。保存できなければ、HistoryErrorとし、実行しない。

    bundle: 実行するコードと識別(SQL・Pythonのハッシュ、固定外枠を含むコード全体のハッシュ、外枠の版)。"""
    proposal = plan['proposal']
    now = datetime.now()
    try:
        return AIAnalysisRun.objects.create(
            plan_id=plan['id'], user=user, views=proposal['datasets'], **_template_columns(plan), **_refinement_columns(plan),
            date_from=proposal['date_from'], date_to=proposal['date_to'], conditions=proposal.get('conditions', ''),
            method_approved_at=_parse(plan.get('method_approved_at')), data_approved_at=_parse(plan.get('data_approved_at')),
            approved_counts={d['view']: d['rows'] for d in (plan.get('preview') or {}).get('datasets', [])},
            sql_sha256=bundle.sql_sha256, python_sha256=bundle.python_sha256,
            executed_code_sha256=bundle.executed_code_sha256, wrapper_version=bundle.wrapper_version,
            settings_snapshot=_settings_snapshot(policy, deadlines, chunk_rows),
            status='running', worker_id=WORKER_ID, heartbeat_at=now, started_at=now,
        )
    except Exception as exc:
        raise HistoryError('実行履歴を保存できないため、分析を実行しません。') from exc


def _container_cleanup(launcher):
    """launcherのジョブ用コンテナの後始末。launcherの応答に後始末の結果がなければ、未確認(unconfirmed)とする。

    削除できていなければ完了扱いにしない(launcherが次のジョブの前に再試行する)。
    """
    if not launcher or 'cleanup' not in launcher:
        return 'unconfirmed'
    if launcher['cleanup'].get('state') == 'not_started':
        return 'not_started'
    return 'closed' if (launcher['cleanup'] or {}).get('ok') else 'pending'


LOADED_AT_TOLERANCE_SECONDS = 5  # 取得完了より前、現在より後の時刻は、時計のずれなどの異常として採用しない


def _loaded_at(diagnostics, fetched_at, now=None):
    """コンテナが報告した投入完了の時刻(epoch秒)を、日時にする。報告がない・値が不正・範囲外ならNULL(推測で補わない)。"""
    epoch = diagnostics.get('loaded_at_epoch')
    if type(epoch) not in (int, float) or epoch != epoch:
        return None
    try:
        loaded_at = datetime.fromtimestamp(epoch)
    except (OverflowError, OSError, ValueError):
        return None
    tolerance = timedelta(seconds=LOADED_AT_TOLERANCE_SECONDS)
    if (fetched_at is not None and loaded_at < fetched_at - tolerance) or loaded_at > (now or datetime.now()) + tolerance:
        return None
    return loaded_at


# 例外名の許可リスト: 組み込みの例外クラスと、ガードの`GuardError`だけ。自由な名前(データを混ぜた名前など)は、取り出さない(evaluator指摘、BOSS承認 2026-10-08)
ALLOWED_EXCEPTION_NAMES = frozenset({name for name, value in vars(builtins).items() if isinstance(value, type) and issubclass(value, BaseException)} | {'GuardError'})
# GuardErrorの理由コードの許可リスト(analysis_guard_runtime.pyで定義した固定コード。未知のコードは、表示・保存しない。Codex P1)
GUARD_CODES = frozenset({
    'chart_series_invalid', 'chart_x_not_list', 'function_not_allowed', 'import_not_allowed', 'python_rejected', 'query_empty',
    'query_failed', 'query_not_select', 'query_not_single_select', 'query_too_deep', 'query_unparseable', 'reference_not_allowed',
    'source_modified', 'step_name_invalid', 'steps_invalid', 'syntax_not_supported', 'table_columns_not_list', 'table_function_not_allowed',
    'table_rows_invalid',
})
# コンテナ内では、外枠が`user_code`という名前で動くため、例外名に`user_code.`が付く。この接頭辞だけを外す(任意の修飾名は外さない。Codex P2)
EXCEPTION_LINE = re.compile(r'^(?:user_code\.)?([A-Za-z_][A-Za-z0-9_]{0,60})(?::\s*(.*))?$')


def child_failure_detail(diagnostics):
    """子のPythonが異常終了したとき、標準エラーの最終行から、例外の種類名(と、ガードの理由コード)だけを取り出す。

    メッセージの本文・コードの行・値は、実データを含み得るため、取り出さない(固定の形に合う場合だけ。BOSS承認 2026-10-08)。
    """
    lines = [line.strip() for line in str(diagnostics.get('stderr') or '').splitlines() if line.strip()]
    found = EXCEPTION_LINE.match(lines[-1]) if lines else None
    if not found or found.group(1) not in ALLOWED_EXCEPTION_NAMES:
        return ''
    name, code = found.groups()
    return f'例外: {name}' + (f'({code.strip()})' if name == 'GuardError' and code and code.strip() in GUARD_CODES else '')


def failure_detail(reason, launcher):
    """失敗の説明(データを含まない)。child_exit_nonzeroだけ、例外の種類名を足す。"""
    extra = child_failure_detail((launcher or {}).get('diagnostics') or {}) if reason == 'child_exit_nonzero' else ''
    return (reason_text(reason) + (f' ({extra})' if extra else ''))[:300]


def outcome_from_result(result):
    fetch, launcher = result.get('fetch') or {}, result.get('launcher') or {}
    diagnostics = launcher.get('diagnostics') or {}
    seconds = diagnostics.get('seconds') or {}
    ok = result.get('status') == 'ok'
    reason = '' if ok else (result.get('reason') or launcher.get('reason') or 'launcher_failed')
    return {
        'status': 'success' if ok else 'failed', 'reason': reason,
        'detail': '' if ok else failure_detail(reason, launcher),
        'cleanup': {**(fetch.get('cleanup') or {}), 'container': _container_cleanup(launcher)},
        'snapshot_counts': fetch.get('counts'), 'fetched_rows': fetch.get('fetched_rows'), 'sent_rows': fetch.get('sent_rows'),
        'loaded_rows': diagnostics.get('rows_loaded'),
        'unique_key_check': {'column': 'id', 'django': 'ok', 'container': 'ok' if ok else (
            'failed' if reason == 'duplicate_key' else 'not_confirmed')},
        'fetched_at': fetch.get('fetched_at'), 'sent_at': fetch.get('sent_at'),
        'loaded_at': _loaded_at(diagnostics, fetch.get('fetched_at')),
        'fetch_seconds': fetch.get('fetch_seconds'), 'transfer_seconds': fetch.get('transfer_seconds'),
        'launcher_seconds': fetch.get('launcher_seconds'),
        'container_load_seconds': seconds.get('receive_and_load'), 'python_seconds': seconds.get('python'),
    }


def outcome_from_exception(exc):
    progress = getattr(exc, 'progress', None) or {}
    stopped = isinstance(exc, ExecutionStopped)
    return {
        'status': 'cancelled' if stopped and exc.reason == 'user_cancelled' else 'failed', 'reason': exc.reason if stopped else 'unexpected_error',
        'detail': reason_text(exc.reason if stopped else 'unexpected_error'),
        # 送信を始める前に止めた場合だけ、コンテナは作られていない。送信後は、開始・削除を確認できないため未確認とする
        'cleanup': {**(getattr(exc, 'cleanup', None) or {}), 'container': 'unconfirmed' if progress.get('transmit_started') else 'not_started'},
        'snapshot_counts': progress.get('snapshot_counts'), 'fetched_rows': progress.get('fetched_rows'),
        'sent_rows': progress.get('sent_rows'), 'loaded_rows': None,
        'unique_key_check': {'column': 'id', 'django': 'failed' if getattr(exc, 'reason', '') == 'duplicate_key' else (
            'ok' if progress.get('fetched_rows') is not None else 'not_confirmed'), 'container': 'not_run'},
        'fetched_at': progress.get('fetched_at'), 'sent_at': progress.get('sent_at'), 'loaded_at': None,
        'fetch_seconds': progress.get('fetch_seconds'), 'transfer_seconds': None, 'launcher_seconds': None,
        'container_load_seconds': None, 'python_seconds': None,
    }


def finish_run(run, outcome, tracker=None):
    """元の実行結果を確定する。更新できる行は、自分のworker_idで、`running`または`unknown`のものに限る。"""
    def write(merge=lambda cleanup: cleanup):
        fields = dict(outcome)
        fields['cleanup'] = merge(fields['cleanup'])
        fields['finished_at'] = datetime.now()
        updated = AIAnalysisRun.objects.filter(pk=run.pk, worker_id=run.worker_id, status__in=('running', 'unknown')).update(**fields)
        if updated != 1:
            raise HistoryError('実行履歴の行を確定できません(行が変更または削除されています)。', outcome)

    if tracker is None:
        write()
    else:
        tracker.finalize(write)


def run_and_record(user, plan, bundle, policy, deadlines=None, chunk_rows=CHUNK_ROWS, control=None, on_started=None, on_cleanup_done=None):
    """履歴を保存しながら、承認済みの分析を実行する。

    開始行を保存できなければ実行しない。確定に失敗した場合は、結果を返さず、元の結果を含むHistoryErrorを送出する。
    実行が失敗した場合は、履歴を確定した後に、元の例外をそのまま送出する(run_idを付ける)。
    """
    if plan.get('status') != 'data_approved':
        raise AnalysisError('データ範囲の承認後に実行してください。', 409)
    try:
        mark_unknown_stale()
    except Exception:
        logger.exception('停止した可能性のある実行の判定に失敗しました')
    run = start_run(user, plan, bundle, policy, deadlines, chunk_rows)
    heartbeat = Heartbeat(run).start()
    tracker = CleanupTracker(run.pk)
    result, error = None, None
    try:
        if on_started is not None:
            on_started(run.pk)
        def notify(status):
            tracker.notify(status)
            if on_cleanup_done is not None:
                on_cleanup_done(status)
        args = {'control': control} if control is not None else {}
        result = execute_approved_analysis(
            plan['proposal'], run.approved_counts, bundle.executed_code, policy, deadlines, chunk_rows, on_cleanup_done=notify, **args)
        outcome = outcome_from_result(result)
    except Exception as exc:
        error, outcome = exc, outcome_from_exception(exc)
    finally:
        heartbeat.stop()
    try:
        finish_run(run, outcome, tracker)
    except Exception as save_error:
        logger.error('実行履歴を確定できませんでした: run=%s 元の結果=%s', run.pk, {k: outcome.get(k) for k in ('status', 'reason', 'cleanup')},
                     exc_info=save_error)
        raise HistoryError('実行履歴を確定できないため、結果を返しません。', outcome) from save_error
    if error is not None:
        error.run_id = run.pk
        raise error
    result['run_id'] = run.pk
    return result


def record_not_run(user, plan, status, reason, policy):
    """実行前の期限切れ・中止・検証失敗を記録する。実行コードを組み立てないためハッシュはNULL。"""
    if status not in ('expired', 'cancelled', 'failed'):
        raise ValueError('statusはexpired・cancelled・failedです。')
    proposal = plan['proposal']
    now = datetime.now()
    try:
        return AIAnalysisRun.objects.create(
            plan_id=plan['id'], user=user, views=proposal['datasets'], date_from=proposal['date_from'], date_to=proposal['date_to'],
            **_template_columns(plan),
            conditions=proposal.get('conditions', ''), method_approved_at=_parse(plan.get('method_approved_at')),
            data_approved_at=_parse(plan.get('data_approved_at')),
            approved_counts={d['view']: d['rows'] for d in (plan.get('preview') or {}).get('datasets', [])},
            settings_snapshot=_settings_snapshot(policy, None, CHUNK_ROWS), status=status, reason=reason, detail=reason_text(reason),
            cleanup={'db_connection': 'not_started', 'container': 'not_started'},
            worker_id=WORKER_ID, heartbeat_at=now, started_at=now, finished_at=now,
        )
    except Exception as exc:
        raise HistoryError('実行履歴を保存できませんでした。') from exc


def visible_runs(user, include_all):
    """閲覧できる履歴。実行者本人のものと、設定(settings.ai / can_edit)を持つ管理者はすべて。判定した後に、停止の判定も行う。"""
    try:
        mark_unknown_stale()
    except Exception:
        logger.exception('停止した可能性のある実行の判定に失敗しました')
    queryset = AIAnalysisRun.objects.select_related('user')
    return queryset if include_all else queryset.filter(user=user)


def serialize_run(run):
    return {
        'id': run.pk, 'plan_id': run.plan_id, 'status': run.status, 'status_label': run.get_status_display(),
        'reason': run.reason, 'detail': run.detail,
        'refinement_instruction': run.refinement_instruction, 'refined_from_run_id': run.refined_from_run_id,
        'executed_by': run.user.get_username() if run.user_id else DELETED_USER_LABEL,
        'views': run.views, 'date_from': run.date_from.isoformat(), 'date_to': run.date_to.isoformat(), 'conditions': run.conditions,
        'approved_counts': run.approved_counts, 'snapshot_counts': run.snapshot_counts, 'fetched_rows': run.fetched_rows,
        'sent_rows': run.sent_rows, 'loaded_rows': run.loaded_rows, 'unique_key_check': run.unique_key_check,
        'sql_sha256': run.sql_sha256, 'python_sha256': run.python_sha256,
        'executed_code_sha256': run.executed_code_sha256, 'wrapper_version': run.wrapper_version, 'settings': run.settings_snapshot,
        'cleanup': run.cleanup,
        'started_at': run.started_at.isoformat(),
        'fetched_at': run.fetched_at.isoformat() if run.fetched_at else None,
        'sent_at': run.sent_at.isoformat() if run.sent_at else None,
        'loaded_at': run.loaded_at.isoformat() if run.loaded_at else None,
        'finished_at': run.finished_at.isoformat() if run.finished_at else None,
        'seconds': {key: getattr(run, key) for key in ('fetch_seconds', 'transfer_seconds', 'launcher_seconds', 'container_load_seconds', 'python_seconds')},
    }
