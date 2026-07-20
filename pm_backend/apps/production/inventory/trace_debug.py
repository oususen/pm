"""
特定ライン・製品の自動タスク計算過程を追跡するための一時的なデバッグログ。

原因不明の数値ずれ調査用（対象: L2200 タンクライン(line_id=11) / YD60008491(product_id=397)）。
原因が判明したら本モジュールごと削除して構わない。
"""
import logging
from datetime import timedelta

logger = logging.getLogger('production')

TRACE_TARGETS = {
    (11, 397),  # L2200 タンクライン / YD60008491
}


def is_traced(line_id, product_id):
    try:
        key = (int(line_id), int(product_id))
    except (TypeError, ValueError):
        return False
    return key in TRACE_TARGETS


def trace_log(line_id, product_id, plan_date, message):
    """対象ライン・製品のみ、開始日〜明日（業務日付基準）の範囲でログ出力する。"""
    if not is_traced(line_id, product_id):
        return
    if plan_date is not None:
        from orders.utils.calendar_utils import get_business_today
        tomorrow = get_business_today() + timedelta(days=1)
        if plan_date > tomorrow:
            return
    logger.info(f'[TRACE line={line_id} product={product_id} date={plan_date}] {message}')
