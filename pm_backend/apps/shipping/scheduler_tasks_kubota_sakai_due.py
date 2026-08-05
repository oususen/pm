"""
定時タスク: クボタ堺納期調整 取込 + 再配分
"""
import logging
import time
from datetime import datetime, timedelta

from notifications.models import Notification
from orders.utils.calendar_utils import get_business_today
from production.models_schedule_config import ScheduleConfig, record_schedule_run_log
from shipping.services.kubota_sakai_delivery_progress import recalculate_delivery_progress
from shipping.views_kubota_sakai_due_adjustment import (
    _rebalance_delivery_qty_for_groups,
    _recalculate_remaining_for_groups,
    sync_kubota_sakai_due_adjustments_from_orders,
)
from orders.core.models import KubotaSakaiDueAdjustment

logger = logging.getLogger('production')


def _resolve_task_date_range(config):
    today = get_business_today()
    base_day = getattr(config, 'range_base_day', 'TODAY') or 'TODAY'
    if base_day == 'YESTERDAY':
        start_date = today - timedelta(days=1)
    elif base_day == 'TWO_DAYS_AGO':
        start_date = today - timedelta(days=2)
    else:
        start_date = today
    days_after = int(getattr(config, 'range_days_after', 45) or 45)
    end_date = start_date + timedelta(days=days_after)
    return today, start_date, end_date


def run_kubota_sakai_due_sync():
    task_name = 'KUBOTA_SAKAI_DUE_SYNC'
    config = ScheduleConfig.objects.filter(task_name=task_name).first()
    started_at = datetime.now()
    if config:
        config.last_run_at = started_at
        config.last_run_status = 'RUNNING'
        config.last_run_message = '実行中...'
        config.save(update_fields=['last_run_at', 'last_run_status', 'last_run_message'])

    start_clock = time.perf_counter()
    errors = []
    result = {}

    try:
        today, start_date, end_date = _resolve_task_date_range(config)
        if start_date > end_date:
            result = {
                'created': 0,
                'updated': 0,
                'deleted_forecast': 0,
                'rebalanced_groups': 0,
                'rebalanced_rows': 0,
                'today': str(today),
                'start_date': str(start_date),
                'end_date': str(end_date),
                'skipped': True,
            }
        else:
            sync_result = sync_kubota_sakai_due_adjustments_from_orders(start_date, end_date)
            affected_groups = sync_result.get('affected_groups') or []
            rebalance_result = {
                'updated': 0,
                'affected_groups': 0,
            }
            if affected_groups:
                input_delivery_map = {}
                rows = KubotaSakaiDueAdjustment.objects.filter(
                    product_code__in=[group[0] for group in affected_groups],
                    due_date__range=(start_date, end_date),
                ).values(
                    'product_code', 'ship_to_code', 'source_order_no', 'due_date', 'delivery_qty'
                )
                affected_group_set = {(group[0], group[1] or '') for group in affected_groups}
                for row in rows:
                    gkey = (row['product_code'], row['ship_to_code'] or '')
                    if gkey not in affected_group_set:
                        continue
                    input_delivery_map[(
                        row['product_code'],
                        row['ship_to_code'],
                        row['source_order_no'],
                        row['due_date'],
                    )] = row['delivery_qty']

                updated_count, _ = _rebalance_delivery_qty_for_groups(
                    affected_groups=affected_groups,
                    input_delivery_map=input_delivery_map,
                    user=None,
                    now=datetime.now(),
                )
                _recalculate_remaining_for_groups(affected_groups)
                group_rows = KubotaSakaiDueAdjustment.objects.filter(
                    product_code__in=[group[0] for group in affected_groups],
                )
                progress_start = group_rows.order_by('due_date').values_list('due_date', flat=True).first()
                progress_end = group_rows.order_by('-due_date').values_list('due_date', flat=True).first()
                if progress_start and progress_end:
                    recalculate_delivery_progress(progress_start, progress_end)
                rebalance_result = {
                    'updated': updated_count,
                    'affected_groups': len(affected_groups),
                }

            result = {
                'created': sync_result.get('created', 0),
                'updated': sync_result.get('updated', 0),
                'deleted_forecast': sync_result.get('deleted_forecast', 0),
                'rebalanced_groups': rebalance_result['affected_groups'],
                'rebalanced_rows': rebalance_result['updated'],
                'today': str(today),
                'start_date': str(start_date),
                'end_date': str(end_date),
                'skipped': False,
            }

    except Exception as exc:
        logger.exception('[スケジューラ] KUBOTA_SAKAI_DUE_SYNC 実行失敗')
        errors.append(str(exc))
    finally:
        duration = round(time.perf_counter() - start_clock, 2)
        success = not errors
        if config:
            config.last_run_status = 'SUCCESS' if success else 'FAILED'
            config.last_run_duration_seconds = duration
            if success:
                if result.get('skipped'):
                    config.last_run_message = (
                        f'[クボタ堺納期調整 取込+再配分] 対象なし '
                        f"(today={result.get('today')}, 期間={result.get('start_date')}〜{result.get('end_date')})"
                    )
                else:
                    config.last_run_message = (
                        f"[クボタ堺納期調整 取込+再配分] 期間: {result.get('start_date')}〜{result.get('end_date')}, "
                        f"取込 新規:{result.get('created', 0)} 更新:{result.get('updated', 0)} "
                        f"内示→確定削除:{result.get('deleted_forecast', 0)}, "
                        f"再配分 グループ:{result.get('rebalanced_groups', 0)} 行更新:{result.get('rebalanced_rows', 0)} "
                        f"({duration}秒)"
                    )
            else:
                config.last_run_message = f"実行に失敗しました: {' / '.join(errors)}"
            config.save(update_fields=[
                'last_run_status',
                'last_run_message',
                'last_run_duration_seconds',
            ])
            record_schedule_run_log(
                config,
                status=config.last_run_status,
                message=config.last_run_message,
                duration_seconds=config.last_run_duration_seconds,
                started_at=started_at,
            )
            if not success and config.notify_users.exists():
                try:
                    today_date = datetime.now().date()
                    notification = Notification.objects.create(
                        title='[自動タスク失敗] クボタ堺納期調整 取込+再配分',
                        category='システム',
                        domain='出荷',
                        description=config.last_run_message or '詳細なし',
                        valid_from=None,
                        valid_to=today_date + timedelta(days=7),
                        operator_name='admin',
                    )
                    notification.target_users.set(config.notify_users.all())
                except Exception:
                    logger.exception('[スケジューラ] KUBOTA_SAKAI_DUE_SYNC 失敗通知作成失敗')

    if errors:
        raise RuntimeError(' / '.join(errors))
    return result
