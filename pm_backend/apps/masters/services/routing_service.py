from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Q

from masters.models import Routing
from orders.utils.calendar_utils import DAY_BOUNDARY_HOUR


def normalize_routing_reference_datetime(reference=None):
    """ルーティング有効判定に使う基準日時を正規化する。"""
    if reference is None:
        return datetime.now()

    if isinstance(reference, date) and not isinstance(reference, datetime):
        return datetime.combine(reference, time(DAY_BOUNDARY_HOUR, 0))

    if reference.tzinfo is not None and reference.utcoffset() is not None:
        app_tz = ZoneInfo(settings.TIME_ZONE)
        return reference.astimezone(app_tz).replace(tzinfo=None)

    return reference


def build_effective_routing_q(reference=None, prefix=''):
    ref_dt = normalize_routing_reference_datetime(reference)
    return (
        Q(**{f'{prefix}is_active': True})
        & (Q(**{f'{prefix}valid_from_datetime__isnull': True}) | Q(**{f'{prefix}valid_from_datetime__lte': ref_dt}))
        & (Q(**{f'{prefix}valid_to_datetime__isnull': True}) | Q(**{f'{prefix}valid_to_datetime__gte': ref_dt}))
    )


def get_effective_routing_queryset(reference=None):
    return Routing.objects.filter(build_effective_routing_q(reference)).order_by(
        '-is_default',
        '-valid_from_datetime',
        '-id',
    )


def resolve_effective_routing(product_id, reference=None):
    if not product_id:
        return None
    return get_effective_routing_queryset(reference).filter(product_id=product_id).first()
