from datetime import datetime
import logging
import time

from production.models_schedule_config import ScheduleConfig
from production.production_actual_reconcile import run_production_actual_reconcile

logger = logging.getLogger('production')


def run_production_actual_reconcile_check(*, apply_fix=False, created_by=None):
    task_name = 'PRODUCTION_ACTUAL_RECONCILE_CHECK'
    config = ScheduleConfig.objects.filter(task_name=task_name, line__isnull=True).first()
    if not config:
        config, _ = ScheduleConfig.objects.get_or_create(
            task_name=task_name,
            line=None,
            defaults={
                'scheduled_hour': 2,
                'scheduled_minute': 30,
                'is_enabled': False,
            },
        )

    mode_label = '修正' if apply_fix else '比較'
    config.last_run_at = datetime.now()
    config.last_run_status = 'RUNNING'
    config.last_run_message = f'{mode_label}を実行中...'
    config.save(update_fields=['last_run_at', 'last_run_status', 'last_run_message'])

    started = time.perf_counter()
    try:
        result = run_production_actual_reconcile(
            task_config=config,
            apply_fix=apply_fix,
            created_by=created_by,
        )
        success = result.get('status') == 'SUCCESS'
        duration = round(time.perf_counter() - started, 2)
        config.last_run_status = 'SUCCESS' if success else 'FAILED'
        config.last_run_duration_seconds = duration
        config.last_run_message = (
            f'[{mode_label}] 比較:{result.get("compared_count", 0)}件 '
            f'差分:{result.get("diff_count", 0)}件 修正:{result.get("fixed_count", 0)}件 '
            f'レポートID:{result.get("report_id", "-")}'
            + (f'\n{result.get("message")}' if result.get('message') else '')
        )
        config.save(update_fields=[
            'last_run_status',
            'last_run_duration_seconds',
            'last_run_message',
        ])
        return result
    except Exception as exc:
        duration = round(time.perf_counter() - started, 2)
        logger.exception('生産実績整合チェック実行中にエラー')
        config.last_run_status = 'FAILED'
        config.last_run_duration_seconds = duration
        config.last_run_message = f'実行中にエラーが発生しました: {exc}'
        config.save(update_fields=[
            'last_run_status',
            'last_run_duration_seconds',
            'last_run_message',
        ])
        raise
