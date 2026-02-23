"""
定時タスク: 取り込み/在庫計算/進度計算
"""
import json
import logging
import time
from datetime import datetime, timedelta

from django.test import RequestFactory
from rest_framework.parsers import JSONParser
from rest_framework.request import Request

logger = logging.getLogger('production')

SUPPORTED_TASKS = {
    'INVENTORY_RECALC': {
        'label': '取り込み＋在庫・計画在庫・進度再計算',
        'pickup_prod': True,
        'pickup_purchase': True,
        'inventory': True,
        'progress': False,
        'include_progress_in_inventory': True,
    },
    'PICKUP_ONLY': {
        'label': '取り込みのみ',
        'pickup_prod': True,
        'pickup_purchase': True,
        'inventory': False,
        'progress': False,
        'include_progress_in_inventory': False,
    },
    'INVENTORY_ONLY': {
        'label': '在庫計算のみ',
        'pickup_prod': False,
        'pickup_purchase': False,
        'inventory': True,
        'progress': False,
        'include_progress_in_inventory': False,
    },
    'PROGRESS_ONLY': {
        'label': '進度計算のみ',
        'pickup_prod': False,
        'pickup_purchase': False,
        'inventory': False,
        'progress': True,
        'include_progress_in_inventory': False,
    },
}


def _create_drf_request(data):
    """スケジューラ用のDRFリクエストを作成"""
    factory = RequestFactory()
    django_request = factory.post(
        '/',
        data=json.dumps(data),
        content_type='application/json',
    )
    return Request(django_request, parsers=[JSONParser()])


def run_inventory_recalculation(task_name='INVENTORY_RECALC'):
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
    from production.inventory.progress_calculator import recalculate_progress_qty
    from production.models_line_backlog import LineBacklog
    from production.models_schedule_config import ScheduleConfig
    from production.views import LineBacklogViewSet
    from django.db.models import Min

    task_name = (task_name or 'INVENTORY_RECALC').upper()
    task_spec = SUPPORTED_TASKS.get(task_name)
    if not task_spec:
        raise ValueError(f'未対応のタスクです: {task_name}')

    # 実行開始を記録
    config = ScheduleConfig.objects.filter(task_name=task_name).first()
    if config:
        config.last_run_at = datetime.now()
        config.last_run_status = 'RUNNING'
        config.last_run_message = '実行中...'
        config.save(update_fields=['last_run_at', 'last_run_status', 'last_run_message'])

    start_time = time.perf_counter()
    today = get_business_today()
    force_today_base = task_name in {'INVENTORY_ONLY', 'PROGRESS_ONLY'}
    if force_today_base:
        start_date = today
        days_after = int(config.range_days_after or 45) if config else 45
        end_date = start_date + timedelta(days=days_after)
    elif config and config.range_base_day:
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
    progress_count = 0

    # ViewSetインスタンスを準備
    viewset = LineBacklogViewSet()
    viewset.format_kwarg = None
    viewset.kwargs = {}

    if task_spec['pickup_prod']:
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

    if task_spec['pickup_purchase']:
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

    active_lines = Line.objects.filter(is_active=True)
    if task_spec['inventory']:
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
                    include_progress=task_spec['include_progress_in_inventory'],
                    line_final_only=False,
                )
                recalc_count += 1
            except Exception as e:
                error_msg = f'在庫再計算 {line.line_code}: {str(e)}'
                logger.error(f'[スケジューラ] {error_msg}', exc_info=True)
                errors.append(error_msg)

    if task_spec['progress']:
        logger.info(
            f'[スケジューラ] Step 4: 進度再計算開始 ({active_lines.count()}ライン)'
        )
        for line in active_lines:
            try:
                products = (
                    LineBacklog.objects.filter(
                        line_id=line.id,
                        plan_date__range=[start_date, end_date],
                    )
                    .values('product_id')
                    .annotate(min_process_id=Min('process_id'))
                    .filter(product_id__isnull=False, min_process_id__isnull=False)
                )
                for row in products:
                    recalculate_progress_qty(
                        line_id=line.id,
                        product_id=row['product_id'],
                        start_date=start_date,
                        end_date=end_date,
                    )
                    progress_count += 1
            except Exception as e:
                error_msg = f'進度再計算 {line.line_code}: {str(e)}'
                logger.error(f'[スケジューラ] {error_msg}', exc_info=True)
                errors.append(error_msg)

    duration = time.perf_counter() - start_time
    success = len(errors) == 0

    result = {
        'pickup_lines': pickup_count,
        'purchase_suppliers': purchase_count,
        'recalc_lines': recalc_count,
        'progress_products': progress_count,
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
            f'[{task_spec["label"]}] 期間: {start_date_str}〜{end_date_str}, '
            f'取込: {pickup_count}ライン, 購買取込: {purchase_count}仕入先, '
            f'在庫再計算: {recalc_count}ライン, 進度再計算: {progress_count}製品 ({round(duration, 1)}秒)'
            + (f'\nエラー: {error_summary}' if error_summary else '')
        )
        config.save(update_fields=[
            'last_run_status', 'last_run_message', 'last_run_duration_seconds',
        ])

    logger.info(
        f'[スケジューラ] 完了({task_name}): pickup={pickup_count}, purchase={purchase_count}, '
        f'recalc={recalc_count}, progress={progress_count}, {round(duration, 1)}秒, エラー={len(errors)}件'
    )

    return result
