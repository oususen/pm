"""定時タスク実行系サービス"""
import threading
from datetime import datetime

from rest_framework import status
from rest_framework.response import Response

from production.models_schedule_config import ScheduleConfig


TASK_LABELS = {
    'INVENTORY_RECALC': '取り込み＋在庫再計算',
    'PICKUP_ONLY': '取り込みのみ',
    'INVENTORY_ONLY': '在庫計算のみ',
    'PROGRESS_ONLY': '進度計算のみ',
    'KUBOTA_SAKAI_DUE_SYNC': 'クボタ堺納期調整 取込+再配分',
    'AUTO_SAFETY_STOCK_INTERNAL': '自動安全在庫（社内）',
    'AUTO_SAFETY_STOCK_PURCHASE': '自動安全在庫（購入品）',
    'AUTO_PURCHASE_ORDER_CHECK': '発注タイミング日次チェック',
    'PURCHASE_ACTUAL_RECONCILE_CHECK': '納入実績整合チェック',
    'PRODUCTION_ACTUAL_RECONCILE_CHECK': '生産実績整合チェック',
    'PLAN_TO_ACTUAL_COPY': '計画実績自動セット',
    'ORDER_EXPANSION': '自動受注展開',
    'CONTAINER_IMPORT_TMP_CLEANUP': '荷姿設定Excel取込 一時ファイル削除',
}


def run_now(request, logger=None):
    task = str(request.data.get('task_name') or 'INVENTORY_RECALC').upper()
    config_id = request.data.get('config_id') or request.data.get('id')
    line_id = request.data.get('line')

    try:
        if task == 'AUTO_PLAN':
            result = _run_auto_plan(task=task, config_id=config_id, line_id=line_id)
            if isinstance(result, Response):
                return result
            return Response({'detail': '生産計画自動生成を実行しました', **(result or {})})

        label = _resolve_task_label(task)
        if not label:
            return Response(
                {'detail': f'未対応のタスクです: {task}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        running_response = _release_stale_running_if_needed(task)
        if running_response is not None:
            return running_response

        _run_task_in_background(task=task, config_id=config_id, logger=logger)
        return Response({
            'detail': f'{label}をバックグラウンドで開始しました。',
            'async': True,
        })
    except Exception as exc:
        if logger:
            logger.exception('手動実行に失敗')
        return Response(
            {'detail': f'実行に失敗しました: {str(exc)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def reset_status(request, logger=None):
    """死んだタスクの RUNNING 状態を手動リセットする"""
    task = str(request.data.get('task_name') or '').upper()
    config_id = request.data.get('config_id') or request.data.get('id')

    if not task:
        return Response(
            {'detail': 'task_name が必要です'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    filters = {'task_name': task, 'last_run_status': 'RUNNING'}
    if config_id:
        filters['id'] = config_id

    cfg = ScheduleConfig.objects.filter(**filters).first()
    if not cfg:
        return Response(
            {'detail': '実行中のタスクが見つかりません。既に完了している可能性があります。'},
            status=status.HTTP_404_NOT_FOUND,
        )

    old_message = (cfg.last_run_message or '').strip()
    reset_note = f'手動リセット ({datetime.now():%Y-%m-%d %H:%M})'
    cfg.last_run_status = 'FAILED'
    cfg.last_run_message = (old_message + '\n' if old_message else '') + reset_note
    cfg.save(update_fields=['last_run_status', 'last_run_message'])

    from production.models_schedule_config import record_schedule_run_log
    record_schedule_run_log(
        cfg,
        status='FAILED',
        message=reset_note,
        duration_seconds=cfg.last_run_duration_seconds,
        started_at=cfg.last_run_at,
    )

    label = _resolve_task_label(task) or task
    if logger:
        logger.info('タスク状態を手動リセット: %s (config_id=%s)', task, cfg.id)
    return Response({'detail': f'{label}の状態をリセットしました。'})


def request_cancel(request, logger=None):
    from production.scheduler.tasks import request_task_cancel

    task = str(request.data.get('task_name') or 'INVENTORY_RECALC').upper()
    config_id = request.data.get('config_id') or request.data.get('id')
    supported_tasks = {'INVENTORY_RECALC', 'PICKUP_ONLY', 'INVENTORY_ONLY', 'PROGRESS_ONLY'}

    if task not in supported_tasks:
        return Response(
            {'detail': f'このタスクはキャンセル未対応です: {task}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if config_id:
        exists = ScheduleConfig.objects.filter(id=config_id, task_name=task).exists()
        if not exists:
            return Response({'detail': '対象設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)

    result = request_task_cancel(task)
    if not result.get('ok'):
        if result.get('reason') == 'not_found':
            return Response({'detail': '対象設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        if result.get('reason') == 'not_running':
            return Response({'detail': '現在このタスクは実行中ではありません。'}, status=status.HTTP_409_CONFLICT)
        return Response({'detail': 'キャンセル要求に失敗しました。'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if result.get('already_requested'):
        return Response({'detail': '既にキャンセル要求済みです。停止完了までお待ちください。'})
    return Response({'detail': 'キャンセル要求を受け付けました。安全な区切りで停止します。'})


def _resolve_task_label(task_name):
    return TASK_LABELS.get(task_name)


def _resolve_auto_plan_target(config_id, line_id):
    if config_id:
        return ScheduleConfig.objects.filter(id=config_id).first()
    if line_id:
        return ScheduleConfig.objects.filter(task_name='AUTO_PLAN', line_id=line_id).first()
    return None


def _is_stale_cancel_requested_run(config):
    if not config or getattr(config, 'last_run_status', None) != 'RUNNING':
        return False
    message = str(getattr(config, 'last_run_message', '') or '')
    last_run_at = getattr(config, 'last_run_at', None)
    if '[CANCEL_REQUESTED]' not in message or not last_run_at:
        return False
    return last_run_at.date() < datetime.now().date()


def _release_stale_running_if_needed(task_name):
    running_cfg = ScheduleConfig.objects.filter(
        task_name=task_name,
        last_run_status='RUNNING',
    ).first()
    if not running_cfg:
        return None

    if _is_stale_cancel_requested_run(running_cfg):
        stale_message = (running_cfg.last_run_message or '').strip()
        stale_message = (stale_message + '\n' if stale_message else '') + '前日以前のキャンセル要求済み実行を残留扱いで解放しました。'
        running_cfg.last_run_status = 'FAILED'
        running_cfg.last_run_message = stale_message
        running_cfg.save(update_fields=['last_run_status', 'last_run_message'])
        return None

    running_msg = running_cfg.last_run_message or ''
    if '[CANCEL_REQUESTED]' in running_msg:
        detail = '既にキャンセル要求済みの実行が停止待ちです。完了までお待ちください。'
    else:
        detail = '既に実行中です。完了までお待ちください。必要なら「キャンセル要求」を実行してください。'
    return Response({'detail': detail}, status=status.HTTP_409_CONFLICT)


def _run_auto_plan(*, task, config_id, line_id):
    from production.scheduler.tasks_auto_plan import run_auto_plan

    if config_id or line_id:
        config = _resolve_auto_plan_target(config_id, line_id)
        if not config:
            return Response({'detail': '対象設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        return run_auto_plan(force=True, config_id=config.id)
    return run_auto_plan(force=True)


def _run_task_in_background(*, task, config_id, logger=None):
    def _run():
        import django
        django.db.connections.close_all()
        try:
            _execute_task(task=task, config_id=config_id)
        except Exception:
            if logger:
                logger.exception('バックグラウンドタスク実行に失敗')
            ScheduleConfig.objects.filter(
                task_name=task,
                last_run_status='RUNNING',
            ).update(last_run_status='FAILED', last_run_message='実行中にエラーが発生しました')

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def _execute_task(*, task, config_id=None):
    from production.scheduler.tasks import run_inventory_recalculation
    from production.scheduler.tasks_safety_stock import run_auto_safety_stock
    from production.scheduler.tasks_order_expansion import run_order_expansion
    from production.scheduler.tasks_purchase_actual_reconcile import run_purchase_actual_reconcile_check
    from production.scheduler.tasks_production_actual_reconcile import run_production_actual_reconcile_check
    from production.scheduler.tasks_plan_to_actual import run_plan_to_actual_copy
    from shipping.scheduler_tasks_kubota_sakai_due import run_kubota_sakai_due_sync
    from purchase.order_proposal_views import run_auto_purchase_order_check
    from masters.scheduler.tasks_container_import_cleanup import run_container_import_tmp_cleanup

    if task in {'AUTO_SAFETY_STOCK_INTERNAL', 'AUTO_SAFETY_STOCK_PURCHASE'}:
        run_auto_safety_stock(task_name=task)
    elif task == 'AUTO_PURCHASE_ORDER_CHECK':
        run_auto_purchase_order_check()
    elif task == 'PURCHASE_ACTUAL_RECONCILE_CHECK':
        run_purchase_actual_reconcile_check(apply_fix=False)
    elif task == 'PRODUCTION_ACTUAL_RECONCILE_CHECK':
        run_production_actual_reconcile_check(apply_fix=False)
    elif task == 'PLAN_TO_ACTUAL_COPY':
        if not config_id:
            raise ValueError('PLAN_TO_ACTUAL_COPY は config_id が必要です')
        run_plan_to_actual_copy(config_id=int(config_id))
    elif task == 'ORDER_EXPANSION':
        run_order_expansion()
    elif task == 'CONTAINER_IMPORT_TMP_CLEANUP':
        run_container_import_tmp_cleanup()
    elif task == 'KUBOTA_SAKAI_DUE_SYNC':
        run_kubota_sakai_due_sync()
    else:
        run_inventory_recalculation(task_name=task)
