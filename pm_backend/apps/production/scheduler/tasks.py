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


def _resolve_effective_start_date(
    line,
    requested_start_date,
    end_date,
    today,
    *,
    include_stock_anchor,
    include_lt_anchor,
    product_id=None,
):
    """API と同じ開始日補正を、定時タスク側でも適用する。"""
    from django.db.models import Max

    from masters.models import BOMItem, Calendar, CalendarDay
    from production.models_line_backlog import LineBacklog
    from production.inventory.inventory_calculator import _get_max_parent_bom_lead_time

    calendar_id = getattr(line, 'calendar_id', None) or Calendar.objects.filter(
        calendar_code='daiso'
    ).values_list('id', flat=True).first()
    workday_cache = {}

    def is_working_day(target_date):
        if not calendar_id:
            return target_date.weekday() < 5
        if target_date in workday_cache:
            return workday_cache[target_date]
        cal = CalendarDay.objects.filter(
            calendar_id=calendar_id,
            target_date=target_date,
        ).first()
        is_work = cal.is_working_day if cal is not None else target_date.weekday() < 5
        workday_cache[target_date] = is_work
        return is_work

    def get_prev_working_day(target_date):
        prev_date = target_date - timedelta(days=1)
        while not is_working_day(prev_date):
            prev_date = prev_date - timedelta(days=1)
        return prev_date

    def shift_working_days(target_date, days):
        if not days:
            return target_date
        if not calendar_id:
            return target_date + timedelta(days=days)
        step = 1 if days > 0 else -1
        remaining = abs(int(days))
        current = target_date
        while remaining > 0:
            current = current + timedelta(days=step)
            if is_working_day(current):
                remaining -= 1
        return current

    effective_start_date = requested_start_date

    if include_stock_anchor:
        stock_start_dt = get_prev_working_day(get_prev_working_day(today))
        effective_start_date = min(effective_start_date, stock_start_dt)

    if include_lt_anchor:
        max_lt = 0
        if product_id is not None:
            max_lt = _get_max_parent_bom_lead_time(product_id)
        else:
            product_ids = list(
                LineBacklog.objects.filter(
                    line_id=line.id,
                    plan_date__lte=end_date,
                ).values_list('product_id', flat=True).distinct()
            )
            if product_ids:
                max_lt = BOMItem.objects.filter(
                    bom__is_active=True,
                    child_product_id__in=product_ids,
                ).aggregate(v=Max('lead_time_days'))['v'] or 0
        lt_start_dt = shift_working_days(today, -(int(max_lt) + 1))
        effective_start_date = min(effective_start_date, lt_start_dt)

    return effective_start_date


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
    from production.inventory.inventory_calculator import recalculate_inventory_for_line, _build_adjustment_maps
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
                effective_start_date = _resolve_effective_start_date(
                    line,
                    start_date,
                    end_date,
                    today,
                    include_stock_anchor=True,
                    include_lt_anchor=True,
                )
                logger.info(
                    f'[スケジューラ] 在庫再計算: ライン {line.line_code} ({line.line_name}) '
                    f'要求開始={start_date} 実効開始={effective_start_date}'
                )
                recalc_result = recalculate_inventory_for_line(
                    line_id=line.id,
                    start_date=effective_start_date,
                    end_date=end_date,
                    include_progress=task_spec['include_progress_in_inventory'],
                    line_final_only=False,
                )
                recalc_count += 1
                if task_spec['include_progress_in_inventory'] and isinstance(recalc_result, dict):
                    progress_count += int(
                        recalc_result.get('progress_product_count')
                        or recalc_result.get('product_count')
                        or 0
                    )
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
                line_effective_start_date = _resolve_effective_start_date(
                    line,
                    start_date,
                    end_date,
                    today,
                    include_stock_anchor=False,
                    include_lt_anchor=True,
                )
                logger.info(
                    f'[スケジューラ] 進度再計算: ライン {line.line_code} ({line.line_name}) '
                    f'要求開始={start_date} 実効開始={line_effective_start_date}'
                )
                adjustment_maps = _build_adjustment_maps(line.id, line_effective_start_date, end_date)
                products = (
                    LineBacklog.objects.filter(
                        line_id=line.id,
                        plan_date__range=[line_effective_start_date, end_date],
                    )
                    .values('product_id')
                    .annotate(min_process_id=Min('process_id'))
                    .filter(product_id__isnull=False, min_process_id__isnull=False)
                )
                for row in products:
                    product_effective_start_date = _resolve_effective_start_date(
                        line,
                        start_date,
                        end_date,
                        today,
                        include_stock_anchor=False,
                        include_lt_anchor=True,
                        product_id=row['product_id'],
                    )
                    recalculate_progress_qty(
                        line_id=line.id,
                        product_id=row['product_id'],
                        start_date=product_effective_start_date,
                        end_date=end_date,
                        progress_adjust_map=adjustment_maps.get('PROGRESS'),
                        planned_progress_adjust_map=adjustment_maps.get('PLANNED_PROGRESS'),
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
