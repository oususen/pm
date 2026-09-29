"""受注領域のAI読み取り専用集計。"""
from datetime import date, timedelta

from django.db.models import Exists, OuterRef

from masters.models import Routing
from orders.core.models import OrderLine
from orders.utils.calendar_utils import get_business_today

from ai.services.query_common import AI_DB_ALIAS


def get_missing_routing_orders(arguments):
    """受注画面と同じルールで、ルーティング未設定品番を最小項目へ集計する。"""
    due_date_from_text = str(arguments.get('due_date_from') or '').strip()
    if due_date_from_text:
        try:
            due_date_from = date.fromisoformat(due_date_from_text)
        except ValueError:
            return {'status': 'invalid_request', 'detail': '納期開始日はYYYY-MM-DDで指定してください。'}, None, None
    else:
        due_date_from = get_business_today() - timedelta(days=90)

    queryset = (
        OrderLine.objects.using(AI_DB_ALIAS)
        .filter(order__status='OPEN', product__isnull=False, due_date__gte=due_date_from)
        .annotate(
            has_routing=Exists(
                Routing.objects.using(AI_DB_ALIAS).filter(product=OuterRef('product'), is_active=True)
            )
        )
        .filter(has_routing=False)
        .select_related('order', 'order__customer')
        .order_by('due_date', 'order__customer__customer_code', 'product_code')
    )
    grouped = {}
    for record in queryset:
        key = (record.product_code or '').strip().lower()
        if key:
            grouped.setdefault(key, []).append(record)

    business_today = get_business_today()

    def sort_by_due_date(record, reverse=False):
        due = record.due_date or (date.min if reverse else date.max)
        order_time = record.order.updated_at or record.order.created_at or record.updated_at or record.created_at
        timestamp = order_time.timestamp() if order_time else 0
        customer_code = record.order.customer.customer_code if record.order and record.order.customer else ''
        if reverse:
            return (due, timestamp, record.order_id or 0, customer_code)
        return (due, -timestamp, -(record.order_id or 0), customer_code)

    selected = {}
    for key, records in grouped.items():
        future_records = [record for record in records if record.due_date and record.due_date >= business_today]
        selected[key] = min(future_records, key=sort_by_due_date) if future_records else max(
            records, key=lambda record: sort_by_due_date(record, reverse=True)
        )

    rows = sorted(selected.values(), key=lambda record: (record.due_date or date.max, record.product_code or ''))
    by_due_date = {}
    by_order_type = {}
    for record in rows:
        due_label = record.due_date.isoformat() if record.due_date else '納期未設定'
        by_due_date[due_label] = by_due_date.get(due_label, 0) + 1
        order_type = record.order_type or record.order.order_type or '種別未設定'
        by_order_type[order_type] = by_order_type.get(order_type, 0) + 1

    max_items = 30
    items = [
        {
            'product_code': record.product_code,
            'due_date': record.due_date.isoformat() if record.due_date else None,
            'representative_order_quantity': float(record.quantity or 0),
            'order_type': record.order_type or record.order.order_type or '',
        }
        for record in rows[:max_items]
    ]
    period = {'start_date': due_date_from.isoformat(), 'end_date': None}
    result = {
        'status': 'ok',
        'source': '受注明細（ルーティング未設定・画面と同一条件）',
        'period': period,
        'unique_product_count': len(rows),
        'order_type_counts': by_order_type,
        'due_date_counts': [{'due_date': due_date, 'product_count': count} for due_date, count in by_due_date.items()],
        'items': items,
        'items_truncated': len(rows) > max_items,
        'quantity_note': '数量は品番ごとに画面表示対象として選ばれた代表受注明細の数量であり、全受注明細の合計ではない。',
        'privacy_note': '得意先名、受注番号、受注明細は外部AIへ送信していない。',
    }
    chart = {
        'labels': list(by_due_date.keys()),
        'values': list(by_due_date.values()),
        'series_label': '品番数',
    }
    return result, chart, period
