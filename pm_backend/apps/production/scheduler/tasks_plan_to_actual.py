"""
定時タスク: 計画実績自動セット

指定したライン・工程の業務日付（8時境界）計画合計を、
LineBacklog(sequence_no=0).actual_qty へ反映する。
"""
import logging
import time
from datetime import datetime
from decimal import Decimal

from django.db.models import Sum

logger = logging.getLogger('production')


def run_plan_to_actual_copy(config_id):
    from production.models_schedule_config import ScheduleConfig
    from production.models_line_plan import LinePlan
    from production.models_line_backlog import LineBacklog
    from orders.utils.calendar_utils import get_business_today

    config = ScheduleConfig.objects.select_related('line', 'process').filter(id=config_id).first()
    if not config:
        raise ValueError(f'設定が見つかりません: id={config_id}')
    if not config.line_id or not config.process_id:
        raise ValueError(f'ライン・工程の設定が必要です: id={config_id}')

    start_time = time.perf_counter()
    target_date = get_business_today()

    config.last_run_at = datetime.now()
    config.last_run_status = 'RUNNING'
    config.last_run_message = f'実行中... 対象日={target_date}'
    config.save(update_fields=['last_run_at', 'last_run_status', 'last_run_message'])

    created = 0
    updated = 0
    touched = 0
    skipped_existing_actual = 0
    errors = []

    try:
        plan_rows = (
            LinePlan.objects.filter(
                line_id=config.line_id,
                process_id=config.process_id,
                plan_date=target_date,
            )
            .values('product_id')
            .annotate(total_plan_qty=Sum('plan_qty'))
        )

        for row in plan_rows:
            product_id = row.get('product_id')
            total_plan_qty = row.get('total_plan_qty') or 0
            actual_qty = Decimal(str(total_plan_qty))
            existing = LineBacklog.objects.filter(
                line_id=config.line_id,
                process_id=config.process_id,
                product_id=product_id,
                plan_date=target_date,
                sequence_no=0,
            ).first()

            if existing and Decimal(str(existing.actual_qty or 0)) != 0:
                skipped_existing_actual += 1
                continue

            if existing:
                existing.actual_qty = actual_qty
                existing.save(update_fields=['actual_qty'])
                touched += 1
                updated += 1
            else:
                LineBacklog.objects.create(
                    line_id=config.line_id,
                    process_id=config.process_id,
                    product_id=product_id,
                    plan_date=target_date,
                    sequence_no=0,
                    actual_qty=actual_qty,
                )
                touched += 1
                created += 1

        duration = round(time.perf_counter() - start_time, 2)
        config.last_run_status = 'SUCCESS'
        config.last_run_duration_seconds = duration
        config.last_run_message = (
            f'[計画実績自動セット] 対象日: {target_date}, '
            f'ライン: {config.line.line_code if config.line_id else "-"}, '
            f'工程: {config.process.process_code if config.process_id else "-"}, '
            f'対象品番: {touched}件, 作成: {created}件, 更新: {updated}件, '
            f'既存実績ありスキップ: {skipped_existing_actual}件 ({duration}秒)'
        )
        config.save(update_fields=['last_run_status', 'last_run_duration_seconds', 'last_run_message'])
        return {
            'target_date': str(target_date),
            'line_id': config.line_id,
            'process_id': config.process_id,
            'touched': touched,
            'created': created,
            'updated': updated,
            'skipped_existing_actual': skipped_existing_actual,
            'duration_seconds': duration,
            'errors': errors,
        }
    except Exception as e:
        duration = round(time.perf_counter() - start_time, 2)
        logger.exception('[PLAN_TO_ACTUAL_COPY] 実行エラー')
        config.last_run_status = 'FAILED'
        config.last_run_duration_seconds = duration
        config.last_run_message = (
            f'[計画実績自動セット] 失敗 対象日: {target_date} '
            f'(line={config.line_id}, process={config.process_id}) / {str(e)}'
        )
        config.save(update_fields=['last_run_status', 'last_run_duration_seconds', 'last_run_message'])
        raise
