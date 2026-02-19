"""
定時タスク: 取り込み → 在庫再計算
全アクティブラインの需要取り込みと在庫・計画在庫・進度を再計算する
"""
import json
import logging
import time
from datetime import datetime, timedelta

from django.test import RequestFactory
from rest_framework.parsers import JSONParser
from rest_framework.request import Request

logger = logging.getLogger('production')


def _create_drf_request(data):
    """スケジューラ用のDRFリクエストを作成"""
    factory = RequestFactory()
    django_request = factory.post(
        '/',
        data=json.dumps(data),
        content_type='application/json',
    )
    return Request(django_request, parsers=[JSONParser()])


def run_inventory_recalculation():
    """
    定時タスク: 取り込み → 在庫再計算

    実行順序:
    1. pickup (生産ラインの需要取り込み)
    2. pickup_purchase (購入先ラインの需要取り込み)
    3. recalculate_inventory (全ラインの在庫再計算)

    Returns:
        dict: 実行結果
    """
    from masters.models import Line, BOMItem
    from orders.utils.calendar_utils import get_business_today
    from production.inventory.inventory_calculator import recalculate_inventory_for_line
    from production.models_schedule_config import ScheduleConfig
    from production.views import LineBacklogViewSet

    # 実行開始を記録
    config = ScheduleConfig.objects.filter(task_name='INVENTORY_RECALC').first()
    if config:
        config.last_run_at = datetime.now()
        config.last_run_status = 'RUNNING'
        config.last_run_message = '実行中...'
        config.save(update_fields=['last_run_at', 'last_run_status', 'last_run_message'])

    start_time = time.perf_counter()
    today = get_business_today()
    if config and config.range_base_day:
        base_day = config.range_base_day
        if base_day == 'YESTERDAY':
            start_date = today - timedelta(days=1)
        elif base_day == 'TWO_DAYS_AGO':
            start_date = today - timedelta(days=2)
        else:
            start_date = today
        days_after = int(config.range_days_after or 45)
        end_date = start_date + timedelta(days=days_after)
    else:
        start_date = today - timedelta(days=5)
        end_date = today + timedelta(days=45)
    start_date_str = str(start_date)
    end_date_str = str(end_date)

    errors = []
    pickup_count = 0
    purchase_count = 0
    recalc_count = 0

    # ViewSetインスタンスを準備
    viewset = LineBacklogViewSet()
    viewset.format_kwarg = None
    viewset.kwargs = {}

    # ---- Step 1: pickup (生産ラインの需要取り込み) ----
    prod_lines = Line.objects.filter(is_active=True, line_type='PROD')
    logger.info(f'[スケジューラ] Step 1: pickup開始 ({prod_lines.count()}ライン)')

    for line in prod_lines:
        try:
            logger.info(
                f'[スケジューラ] pickup: ライン {line.line_code} ({line.line_name})'
            )
            request = _create_drf_request({
                'line_id': line.id,
                'start_date': start_date_str,
                'end_date': end_date_str,
            })
            viewset.request = request
            viewset.pickup(request)
            pickup_count += 1
        except Exception as e:
            error_msg = f'pickup {line.line_code}: {str(e)}'
            logger.error(f'[スケジューラ] {error_msg}', exc_info=True)
            errors.append(error_msg)

    # ---- Step 2: pickup_purchase (購入先ラインの需要取り込み) ----
    supplier_ids = list(
        BOMItem.objects.filter(
            sourcing_type__in=['BUY', 'SUBCON'],
            bom__is_active=True,
            supplier_id__isnull=False,
        ).values_list('supplier_id', flat=True).distinct()
    )
    logger.info(
        f'[スケジューラ] Step 2: pickup_purchase開始 ({len(supplier_ids)}仕入先)'
    )

    for supplier_id in supplier_ids:
        try:
            logger.info(
                f'[スケジューラ] pickup_purchase: supplier_id={supplier_id}'
            )
            request = _create_drf_request({
                'supplier_id': supplier_id,
                'start_date': start_date_str,
                'end_date': end_date_str,
            })
            viewset.request = request
            viewset.pickup_purchase(request)
            purchase_count += 1
        except Exception as e:
            error_msg = f'pickup_purchase supplier_id={supplier_id}: {str(e)}'
            logger.error(f'[スケジューラ] {error_msg}', exc_info=True)
            errors.append(error_msg)

    # ---- Step 3: recalculate_inventory (全ラインの在庫再計算) ----
    active_lines = Line.objects.filter(is_active=True)
    logger.info(
        f'[スケジューラ] Step 3: 在庫再計算開始 ({active_lines.count()}ライン)'
    )

    for line in active_lines:
        try:
            logger.info(
                f'[スケジューラ] 在庫再計算: ライン {line.line_code} ({line.line_name})'
            )
            recalculate_inventory_for_line(
                line_id=line.id,
                start_date=start_date,
                end_date=end_date,
                include_progress=True,
                line_final_only=False,
            )
            recalc_count += 1
        except Exception as e:
            error_msg = f'在庫再計算 {line.line_code}: {str(e)}'
            logger.error(f'[スケジューラ] {error_msg}', exc_info=True)
            errors.append(error_msg)

    duration = time.perf_counter() - start_time
    success = len(errors) == 0

    result = {
        'pickup_lines': pickup_count,
        'purchase_suppliers': purchase_count,
        'recalc_lines': recalc_count,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'duration_seconds': round(duration, 2),
        'errors': errors,
    }

    if config:
        config.last_run_status = 'SUCCESS' if success else 'FAILED'
        config.last_run_duration_seconds = round(duration, 2)
        error_summary = '\n'.join(errors) if errors else ''
        config.last_run_message = (
            f'期間: {start_date_str}〜{end_date_str}, '
            f'取込: {pickup_count}ライン, 購買取込: {purchase_count}仕入先, '
            f'在庫再計算: {recalc_count}ライン ({round(duration, 1)}秒)'
            + (f'\nエラー: {error_summary}' if error_summary else '')
        )
        config.save(update_fields=[
            'last_run_status', 'last_run_message', 'last_run_duration_seconds',
        ])

    logger.info(
        f'[スケジューラ] 完了: pickup={pickup_count}, purchase={purchase_count}, '
        f'recalc={recalc_count}, {round(duration, 1)}秒, エラー={len(errors)}件'
    )

    return result
