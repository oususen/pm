"""
定時タスク: 自動安全在庫算出
"""
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import DecimalField, Value
from django.db.models import Sum
from django.db.models.functions import Coalesce

logger = logging.getLogger('production')


SUPPORTED_SAFETY_TASKS = {
    'AUTO_SAFETY_STOCK_INTERNAL': {
        'label': '自動安全在庫（社内）',
        'line_type': 'PROD',
    },
    'AUTO_SAFETY_STOCK_PURCHASE': {
        'label': '自動安全在庫（購入品）',
        'line_type': 'PURCHASE',
    },
}


def _to_decimal(value):
    return Decimal(str(value or 0))


def _round_to_int(value, min_value=0):
    rounded = int(value.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return rounded if rounded >= min_value else min_value


def run_auto_safety_stock(task_name='AUTO_SAFETY_STOCK_INTERNAL'):
    """
    実行日からN日間の需要（確定+内示）平均から安全在庫を算出し、StockAllocation.min_stock_qty を更新する。
    """
    from orders.utils.calendar_utils import get_business_today
    from production.models import LineDemand
    from production.models_production import StockAllocation
    from production.models_schedule_config import ScheduleConfig

    task_name = (task_name or 'AUTO_SAFETY_STOCK_INTERNAL').upper()
    task_spec = SUPPORTED_SAFETY_TASKS.get(task_name)
    if not task_spec:
        raise ValueError(f'未対応のタスクです: {task_name}')

    config = ScheduleConfig.objects.filter(task_name=task_name, line__isnull=True).first()
    if not config:
        config, _ = ScheduleConfig.objects.get_or_create(
            task_name=task_name,
            line=None,
            defaults={
                'scheduled_dom': 1,
                'scheduled_hour': 3,
                'scheduled_minute': 0 if task_name == 'AUTO_SAFETY_STOCK_INTERNAL' else 30,
                'is_enabled': False,
                'average_days_window': 60,
                'safety_days': 1,
            },
        )

    config.last_run_at = datetime.now()
    config.last_run_status = 'RUNNING'
    config.last_run_message = '実行中...'
    config.save(update_fields=['last_run_at', 'last_run_status', 'last_run_message'])

    start_time = time.perf_counter()
    success = True
    errors = []

    average_days_window = max(int(config.average_days_window or 60), 1)
    safety_days = max(int(config.safety_days or 1), 1)
    today = get_business_today()
    start_date = today
    end_date = today + timedelta(days=average_days_window - 1)

    line_type = task_spec['line_type']
    updated_count = 0
    created_count = 0
    target_product_count = 0

    try:
        base_qs = LineDemand.objects.filter(
            line__line_type=line_type,
            plan_date__gte=start_date,
            plan_date__lte=end_date,
            product_id__isnull=False,
        )
        target_product_ids = set(base_qs.values_list('product_id', flat=True).distinct())
        target_product_count = len(target_product_ids)

        if target_product_ids:
            daily_rows = (
                base_qs.values('product_id', 'plan_date')
                .annotate(
                    firm_day_qty=Coalesce(
                        Sum('firm_qty'),
                        Value(Decimal('0.000'), output_field=DecimalField(max_digits=14, decimal_places=3)),
                    ),
                    forecast_day_qty=Coalesce(
                        Sum('forecast_qty'),
                        Value(Decimal('0.000'), output_field=DecimalField(max_digits=14, decimal_places=3)),
                    ),
                )
            )
            total_qty_by_product = defaultdict(Decimal)
            day_count_by_product = defaultdict(int)
            for row in daily_rows:
                demand_qty = _to_decimal(row.get('firm_day_qty')) + _to_decimal(row.get('forecast_day_qty'))
                total_qty_by_product[row['product_id']] += demand_qty
                day_count_by_product[row['product_id']] += 1

            allocations_by_product = defaultdict(list)
            for allocation in StockAllocation.objects.filter(product_id__in=target_product_ids).select_related('product'):
                allocations_by_product[allocation.product_id].append(allocation)

            with transaction.atomic():
                for product_id in target_product_ids:
                    total_qty = total_qty_by_product.get(product_id, Decimal('0'))
                    actual_days = day_count_by_product.get(product_id, average_days_window)
                    avg_per_day = total_qty / Decimal(actual_days)
                    # 業務ルール: 自動算出結果が0でも最小在庫は最低1を保持する
                    safe_qty = _round_to_int(avg_per_day * Decimal(safety_days), min_value=1)
                    product_allocations = allocations_by_product.get(product_id, [])

                    if not product_allocations:
                        StockAllocation.objects.create(
                            product_id=product_id,
                            location='MAIN',
                            current_stock=Decimal('0'),
                            reserved_qty=Decimal('0'),
                            min_stock_qty=safe_qty,
                            is_bottleneck=False,
                        )
                        created_count += 1
                        continue

                    for allocation in product_allocations:
                        if int(allocation.min_stock_qty or 0) == safe_qty:
                            continue
                        allocation.min_stock_qty = safe_qty
                        allocation.save(update_fields=['min_stock_qty', 'updated_at'])
                        updated_count += 1
    except Exception as exc:
        logger.error(f'[{task_name}] 実行中にエラー', exc_info=True)
        success = False
        errors.append(str(exc))

    duration_seconds = round(time.perf_counter() - start_time, 2)
    if success:
        config.last_run_status = 'SUCCESS'
        config.last_run_message = (
            f'[{task_spec["label"]}] 期間: {start_date}〜{end_date}, '
            f'需要種別: 確定+内示(LineDemand), '
            f'平均算出日数: {average_days_window}日, 安全在庫日数: {safety_days}日, '
            f'対象製品: {target_product_count}件, 更新: {updated_count}件, 新規作成: {created_count}件'
        )
    else:
        config.last_run_status = 'FAILED'
        config.last_run_message = (
            f'[{task_spec["label"]}] 失敗: ' + '\n'.join(errors)
        )
    config.last_run_duration_seconds = duration_seconds
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
        'task_name': task_name,
        'line_type': line_type,
        'start_date': str(start_date),
        'end_date': str(end_date),
        'average_days_window': average_days_window,
        'safety_days': safety_days,
        'target_product_count': target_product_count,
        'updated_count': updated_count,
        'created_count': created_count,
        'duration_seconds': duration_seconds,
        'errors': errors,
    }
