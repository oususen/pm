"""消耗品 安全在庫割れの自動注文依頼（定時タスク）"""
import logging
import time
from datetime import datetime

from django.db import transaction
from django.db.models import F

from production.models_schedule_config import ScheduleConfig

from .models import Consumable, ConsumableRequest

logger = logging.getLogger('consumables')

TASK_NAME = 'CONSUMABLE_AUTO_REQUEST'
AUTO_REQUESTER_NAME = 'システム自動'


def calc_auto_request_quantity(stock_quantity, safety_stock, order_unit):
    """
    自動依頼の数量（syomohin の式をそのまま移植。2026-09-25 BOSS決定）
    max(発注単位, int((安全在庫×2 − 在庫) / 発注単位 + 1) × 発注単位)
    ※端数がなくても1単位多くなる現行挙動を維持する
    """
    order_unit = max(int(order_unit or 1), 1)
    return max(order_unit, int((safety_stock * 2 - stock_quantity) / order_unit + 1) * order_unit)


def create_auto_requests():
    """
    在庫数 <= 安全在庫 の有効な消耗品のうち、未完了の依頼（依頼中・発注準備・発注済）が
    1件もない品目に自動依頼を作る（毎日動かしても重複させない）。作成件数を返す。
    """
    open_ids = ConsumableRequest.objects.filter(
        status__in=ConsumableRequest.OPEN_STATUSES
    ).values_list('consumable_id', flat=True)
    targets = (
        Consumable.objects.filter(is_active=True, stock_quantity__lte=F('safety_stock'))
        .exclude(id__in=open_ids)
        .order_by('code')
    )
    now = datetime.now()
    created = 0
    with transaction.atomic():
        for consumable in targets:
            quantity = calc_auto_request_quantity(
                consumable.stock_quantity, consumable.safety_stock, consumable.order_unit
            )
            ConsumableRequest.objects.create(
                consumable=consumable,
                quantity=quantity,
                unit_price=consumable.unit_price,
                total_amount=consumable.unit_price * quantity,
                deadline='通常',
                requester=None,
                requester_name=AUTO_REQUESTER_NAME,
                request_type='auto',
                status=ConsumableRequest.STATUS_REQUESTED,
                note=f'自動発注依頼（在庫: {consumable.stock_quantity}, 安全在庫: {consumable.safety_stock}）',
                requested_at=now,
            )
            created += 1
    return created


def _finish(config, status, message, started):
    from production.models_schedule_config import record_schedule_run_log

    config.last_run_status = status
    config.last_run_duration_seconds = round(time.perf_counter() - started, 2)
    config.last_run_message = message
    config.save(update_fields=['last_run_status', 'last_run_duration_seconds', 'last_run_message'])
    record_schedule_run_log(
        config,
        status=config.last_run_status,
        message=config.last_run_message,
        duration_seconds=config.last_run_duration_seconds,
    )


def run_consumable_auto_request(*, created_by=None):
    config, _ = ScheduleConfig.objects.get_or_create(
        task_name=TASK_NAME,
        line=None,
        defaults={'scheduled_hour': 7, 'scheduled_minute': 0, 'is_enabled': False},
    )
    config.last_run_at = datetime.now()
    config.last_run_status = 'RUNNING'
    config.last_run_message = '自動依頼を作成中...'
    config.save(update_fields=['last_run_at', 'last_run_status', 'last_run_message'])

    started = time.perf_counter()
    try:
        created = create_auto_requests()
        _finish(config, 'SUCCESS', f'{created}件の自動注文依頼を作成しました', started)
        return {'status': 'SUCCESS', 'created': created}
    except Exception as exc:
        logger.exception('消耗品 自動注文依頼の作成中にエラー')
        _finish(config, 'FAILED', f'実行中にエラーが発生しました: {exc}', started)
        raise
