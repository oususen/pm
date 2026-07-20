"""
特定ライン・製品の自動タスク計算過程を追跡するための一時的なデバッグログ。

原因不明の数値ずれ調査用（対象: L2200 タンクライン / YD60008491）。
原因が判明したら本モジュールごと削除して構わない。
"""
import logging
from datetime import timedelta
from functools import lru_cache

from orders.utils.calendar_utils import get_business_today
from masters.models import Line, Product

logger = logging.getLogger('production.trace')

TRACE_TARGET_CODES = {
    ('L2200', 'YD60008491'),
}
TRACE_FUTURE_DAYS = 7


@lru_cache(maxsize=1)
def _resolved_trace_targets():
    resolved = set()
    for line_code, product_code in TRACE_TARGET_CODES:
        line = Line.objects.filter(line_code=line_code).only('id').first()
        product = Product.objects.filter(product_code=product_code).only('id').first()
        if line and product:
            resolved.add((line.id, product.id))
    return resolved


@lru_cache(maxsize=1)
def _resolved_trace_line_ids():
    return {line_id for line_id, _ in _resolved_trace_targets()}


@lru_cache(maxsize=1)
def _resolved_trace_product_ids():
    return {product_id for _, product_id in _resolved_trace_targets()}


def is_traced(line_id, product_id):
    try:
        key = (int(line_id), int(product_id))
    except (TypeError, ValueError):
        return False
    return key in _resolved_trace_targets()


def is_traced_line(line_id):
    try:
        target_line_id = int(line_id)
    except (TypeError, ValueError):
        return False
    return target_line_id in _resolved_trace_line_ids()


def is_traced_product(product_id):
    try:
        target_product_id = int(product_id)
    except (TypeError, ValueError):
        return False
    return target_product_id in _resolved_trace_product_ids()


def _should_emit_for_date(plan_date):
    if plan_date is None:
        return True
    return plan_date <= (get_business_today() + timedelta(days=TRACE_FUTURE_DAYS))


def trace_log(line_id, product_id, plan_date, message):
    """対象ライン・製品のみログ出力する。"""
    if not is_traced(line_id, product_id):
        return
    if not _should_emit_for_date(plan_date):
        return
    logger.info(f'[TRACE line={line_id} product={product_id} date={plan_date}] {message}')


def trace_line_log(line_id, plan_date, message):
    """対象ラインのみの定時タスク進行ログを出力する。"""
    if not is_traced_line(line_id):
        return
    if not _should_emit_for_date(plan_date):
        return
    logger.info(f'[TRACE line={line_id} date={plan_date}] {message}')


def trace_line_code_log(line_code, plan_date, message):
    """対象ラインコードのみの定時タスク進行ログを出力する。"""
    target_codes = {target_line_code for target_line_code, _ in TRACE_TARGET_CODES}
    if str(line_code or '').strip() not in target_codes:
        return
    if not _should_emit_for_date(plan_date):
        return
    logger.info(f'[TRACE line_code={line_code} date={plan_date}] {message}')
