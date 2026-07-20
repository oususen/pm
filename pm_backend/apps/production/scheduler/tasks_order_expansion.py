"""
定時タスク: 自動受注展開
OPEN受注をLineDemandへ展開する
"""
import logging
import time
from datetime import datetime

logger = logging.getLogger('production')


def run_order_expansion():
    """OPEN受注をLineDemandへ展開"""
    from production.models_schedule_config import ScheduleConfig
    from production.services.order_expansion import OrderExpansionService

    config = ScheduleConfig.objects.filter(task_name='ORDER_EXPANSION').first()
    if config:
        config.last_run_at = datetime.now()
        config.last_run_status = 'RUNNING'
        config.last_run_message = '実行中...'
        config.save(update_fields=['last_run_at', 'last_run_status', 'last_run_message'])

    start_time = time.perf_counter()
    success = True
    result = {}
    error_message = ''

    try:
        service = OrderExpansionService()
        result = service.expand_open_orders(clear_existing=False) or {}
        errors = result.get('errors') or []
        success = len(errors) == 0
        if not success:
            error_message = '\n'.join(str(e) for e in errors)
    except Exception as e:
        logger.error('[ORDER_EXPANSION] 実行中にエラー', exc_info=True)
        success = False
        error_message = str(e)

    duration = round(time.perf_counter() - start_time, 2)
    # OrderExpansionServiceの返却キーに合わせる（後方互換で旧キーも拾う）
    expanded_count = int(result.get('created', result.get('expanded_count', 0)) or 0)
    cleared_count = int(result.get('cleared', 0) or 0)
    warning_count = len(result.get('warnings') or [])

    if config:
        config.last_run_status = 'SUCCESS' if success else 'FAILED'
        config.last_run_duration_seconds = duration
        base_message = (
            f'受注展開完了: 展開件数={expanded_count}, クリア件数={cleared_count}, 警告件数={warning_count}, 実行時間={duration}秒'
        )
        config.last_run_message = base_message if success else f'{base_message}\nエラー: {error_message}'
        config.save(update_fields=[
            'last_run_status',
            'last_run_message',
            'last_run_duration_seconds',
        ])

        from production.models_schedule_config import record_schedule_run_log
        record_schedule_run_log(
            config,
            status=config.last_run_status,
            message=config.last_run_message,
            duration_seconds=config.last_run_duration_seconds,
        )

    return {
        'success': success,
        'expanded_count': expanded_count,
        'cleared_count': cleared_count,
        'warning_count': warning_count,
        'duration_seconds': duration,
        'errors': result.get('errors', []) if isinstance(result, dict) else [error_message] if error_message else [],
    }
