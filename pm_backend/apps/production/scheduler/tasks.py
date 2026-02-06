"""
定時タスク: 在庫再計算
全アクティブラインの在庫・計画在庫・進度を再計算する
"""
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger('production')


def run_inventory_recalculation():
    """
    全アクティブラインの在庫を再計算する

    Returns:
        dict: 実行結果 {lines_processed, duration_seconds, errors}
    """
    from masters.models import Line
    from orders.utils.calendar_utils import get_business_today
    from production.inventory.inventory_calculator import recalculate_inventory_for_line
    from production.models_schedule_config import ScheduleConfig

    # 実行開始を記録
    config = ScheduleConfig.objects.filter(task_name='INVENTORY_RECALC').first()
    if config:
        config.last_run_at = datetime.now()
        config.last_run_status = 'RUNNING'
        config.last_run_message = '実行中...'
        config.save(update_fields=['last_run_at', 'last_run_status', 'last_run_message'])

    start_time = time.perf_counter()
    today = get_business_today()
    start_date = today - timedelta(days=5)
    end_date = today + timedelta(days=45)

    # 全アクティブラインを取得
    active_lines = Line.objects.filter(is_active=True)
    lines_processed = 0
    errors = []

    for line in active_lines:
        try:
            logger.info(
                f'[スケジューラ] ライン {line.line_code} ({line.line_name}) の在庫再計算開始'
            )
            recalculate_inventory_for_line(
                line_id=line.id,
                start_date=start_date,
                end_date=end_date,
                include_progress=True,
                line_final_only=False,
            )
            lines_processed += 1
            logger.info(f'[スケジューラ] ライン {line.line_code} 完了')
        except Exception as e:
            error_msg = f'ライン {line.line_code}: {str(e)}'
            logger.error(f'[スケジューラ] {error_msg}', exc_info=True)
            errors.append(error_msg)

    duration = time.perf_counter() - start_time
    success = len(errors) == 0

    result = {
        'lines_processed': lines_processed,
        'duration_seconds': round(duration, 2),
        'errors': errors,
    }

    if config:
        config.last_run_status = 'SUCCESS' if success else 'FAILED'
        config.last_run_duration_seconds = round(duration, 2)
        error_summary = '\n'.join(errors) if errors else ''
        config.last_run_message = (
            f'{lines_processed}ライン処理完了 ({round(duration, 1)}秒)'
            + (f'\nエラー: {error_summary}' if error_summary else '')
        )
        config.save(update_fields=[
            'last_run_status', 'last_run_message', 'last_run_duration_seconds',
        ])

    logger.info(
        f'[スケジューラ] 在庫再計算完了: {lines_processed}ライン, '
        f'{round(duration, 1)}秒, エラー: {len(errors)}件'
    )

    return result
