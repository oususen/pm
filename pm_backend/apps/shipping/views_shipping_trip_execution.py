from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import ProgrammingError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from masters.models import KubotaSakaiTruck, Product
from orders.core.models import ShippingTrip, ShippingTripAllocation, ShippingTripNotice
from orders.utils.calendar_utils import WorkingDayCalculator
from shipping.models import ShipmentActual, ShipmentActualHistory, ShipmentActualSplit, ShippingTripAllocationSplit, ShipToLeadTimeColorExclusion, ShipToLeadTime
from shipping.services.shipping_progress import get_progress_horizon_days
from shipping.views_kubota_sakai_trip_assignment import _resolve_kubota_line_calendar

SPLIT_TOKEN = '|PD='
REMARK_MAX_LEN = 200
TRIP_NOTICE_TYPE_NORMAL = 'NORMAL'
TRIP_NOTICE_TYPE_URGENT = 'URGENT'
TRIP_NOTICE_TYPE_VENDOR = 'VENDOR'
TRIP_NOTICE_VALID_TYPES = {TRIP_NOTICE_TYPE_NORMAL, TRIP_NOTICE_TYPE_URGENT, TRIP_NOTICE_TYPE_VENDOR}


def _normalize_trip_notice_type(value):
    notice_type = str(value or '').strip().upper()
    if notice_type in TRIP_NOTICE_VALID_TYPES:
        return notice_type
    return TRIP_NOTICE_TYPE_NORMAL


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except ValueError:
        return None


def _to_decimal(value, default='0'):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _format_qty(value):
    qty = _to_decimal(value)
    return str(qty.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _format_dt(value):
    if not value:
        return None
    try:
        return value.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return str(value)


def _decode_remark_splits(remark):
    text = str(remark or '')
    if SPLIT_TOKEN not in text:
        return []
    raw = text.split(SPLIT_TOKEN, 1)[1].strip()
    if not raw:
        return []
    results = []
    for part in raw.split(','):
        chunk = part.strip()
        if not chunk or ':' not in chunk:
            continue
        date_str, qty_str = chunk.split(':', 1)
        parsed_date = _parse_date(date_str.strip())
        qty = _to_decimal(qty_str.strip())
        if not parsed_date or qty <= 0:
            continue
        results.append({
            'production_date': parsed_date.isoformat(),
            'quantity': _format_qty(qty),
        })
    return results


def _normalize_split_rows(rows, default_order_no=''):
    normalized = []
    for idx, item in enumerate(rows or []):
        production_date = _parse_date(item.get('production_date'))
        qty = _to_decimal(item.get('quantity'))
        source_order_no = str(item.get('source_order_no') or default_order_no or '').strip()
        if not production_date or qty <= 0:
            continue
        normalized.append({
            'line_no': idx + 1,
            'production_date': production_date.isoformat(),
            'quantity': _format_qty(qty),
            'source_order_no': source_order_no,
        })
    return normalized


def _encode_remark(marker, splits):
    normalized = []
    for item in (splits or []):
        production_date = _parse_date(item.get('production_date'))
        qty = _to_decimal(item.get('quantity'))
        if not production_date or qty <= 0:
            continue
        normalized.append(f"{production_date.isoformat()}:{_format_qty(qty)}")
    if not normalized:
        return marker
    return f"{marker}{SPLIT_TOKEN}{','.join(normalized)}"


def _actual_split_rows(actual, default_order_no=''):
    if actual:
        split_rows = list(actual.splits.all()) if hasattr(actual, 'splits') else list(
            ShipmentActualSplit.objects.filter(shipment_actual=actual).order_by('line_no', 'id')
        )
        if split_rows:
            return [
                {
                    'line_no': int(item.line_no or 0),
                    'production_date': item.production_date.isoformat(),
                    'quantity': _format_qty(item.quantity),
                    'source_order_no': str(item.source_order_no or default_order_no or '').strip(),
                }
                for item in split_rows
            ]
    return _normalize_split_rows(_decode_remark_splits(getattr(actual, 'remark', None) if actual else None), default_order_no)


def _save_actual_split_rows(actual, split_rows):
    ShipmentActualSplit.objects.filter(shipment_actual=actual).delete()
    normalized = _normalize_split_rows(split_rows)
    if not normalized:
        return
    ShipmentActualSplit.objects.bulk_create([
        ShipmentActualSplit(
            shipment_actual=actual,
            line_no=item['line_no'],
            production_date=_parse_date(item['production_date']),
            quantity=_to_decimal(item['quantity']),
            source_order_no=item['source_order_no'] or '',
        )
        for item in normalized
    ])


def _allocation_split_rows(allocation, default_order_no=''):
    split_rows = list(getattr(allocation, 'production_splits', []).all()) if hasattr(getattr(allocation, 'production_splits', None), 'all') else list(
        ShippingTripAllocationSplit.objects.filter(shipping_trip_allocation=allocation).order_by('line_no', 'id')
    )
    return [
        {
            'line_no': int(item.line_no or 0),
            'production_date': item.production_date.isoformat(),
            'quantity': _format_qty(item.quantity),
            'source_order_no': str(item.source_order_no or default_order_no or '').strip(),
        }
        for item in split_rows
    ]


def _save_allocation_split_rows(allocation, split_rows):
    ShippingTripAllocationSplit.objects.filter(shipping_trip_allocation=allocation).delete()
    normalized = _normalize_split_rows(split_rows)
    if not normalized:
        return
    ShippingTripAllocationSplit.objects.bulk_create([
        ShippingTripAllocationSplit(
            shipping_trip_allocation=allocation,
            line_no=item['line_no'],
            production_date=_parse_date(item['production_date']),
            quantity=_to_decimal(item['quantity']),
            source_order_no=item['source_order_no'] or '',
        )
        for item in normalized
    ])


def _legacy_trip_actual_marker(trip_id, allocation_id):
    return f'[TRIP_ACTUAL]{trip_id}:{allocation_id}'


def _find_actual_for_allocation(allocation, trip_id=None, actual_by_allocation=None):
    if actual_by_allocation and allocation.id in actual_by_allocation:
        return actual_by_allocation.get(allocation.id)

    actual = (
        ShipmentActual.objects
        .filter(shipping_trip_allocation_id=allocation.id)
        .prefetch_related('splits')
        .order_by('-id')
        .first()
    )
    if actual:
        return actual

    marker = _legacy_trip_actual_marker(trip_id or allocation.trip_id, allocation.id)
    return (
        ShipmentActual.objects
        .filter(remark__startswith=marker)
        .prefetch_related('splits')
        .order_by('-id')
        .first()
    )


def _legacy_actuals_for_allocation(allocation, trip_id=None):
    results = list(
        ShipmentActual.objects
        .filter(shipping_trip_allocation_id=allocation.id)
        .order_by('id')
    )
    marker = _legacy_trip_actual_marker(trip_id or allocation.trip_id, allocation.id)
    legacy_rows = list(
        ShipmentActual.objects
        .filter(shipping_trip_allocation__isnull=True, remark__startswith=marker)
        .order_by('id')
    )
    existing_ids = {item.id for item in results}
    for item in legacy_rows:
        if item.id not in existing_ids:
            results.append(item)
    return results


def _save_production_splits_for_trip(trip, raw_actuals):
    if not isinstance(raw_actuals, list):
        return {'detail': 'actuals は配列で指定してください。'}, status.HTTP_400_BAD_REQUEST

    allocations = list(ShippingTripAllocation.objects.filter(trip_id=trip.id).order_by('id'))
    allocation_map = {a.id: a for a in allocations}
    split_map = {}
    for item in raw_actuals:
        try:
            allocation_id = int(item.get('allocation_id') or 0)
        except Exception:
            allocation_id = 0
        if allocation_id <= 0 or allocation_id not in allocation_map:
            continue
        split_map[allocation_id] = item.get('production_splits') or []

    updated_count = 0
    for allocation in allocations:
        default_order_no = str(allocation.source_order_no or '').strip()
        split_rows = split_map.get(allocation.id) or []
        normalized_split_rows = _normalize_split_rows(split_rows, default_order_no)
        existing_split_rows = _allocation_split_rows(allocation, default_order_no)
        if existing_split_rows != normalized_split_rows:
            _save_allocation_split_rows(allocation, normalized_split_rows)
            updated_count += 1
        if trip.status in ('PLANNED', 'LOADING'):
            legacy_actuals = _legacy_actuals_for_allocation(allocation, trip.id)
            for actual in legacy_actuals:
                ShipmentActualHistory.objects.create(
                    shipment_actual=actual,
                    action='DELETE',
                    shipment_date=actual.shipment_date,
                    product_code=actual.product_code,
                    customer_code=actual.customer_code,
                    ship_to_code=actual.ship_to_code,
                    quantity=actual.quantity,
                    remark=actual.remark,
                )
            if legacy_actuals:
                ShipmentActual.objects.filter(id__in=[item.id for item in legacy_actuals]).delete()

    return {'updated': updated_count}, None


def _trip_input_matches_plan(trip, raw_actuals):
    allocations = list(ShippingTripAllocation.objects.filter(trip_id=trip.id).order_by('id'))
    normalized = {}
    if isinstance(raw_actuals, list):
        for item in raw_actuals:
            try:
                allocation_id = int(item.get('allocation_id') or 0)
            except Exception:
                allocation_id = 0
            if allocation_id > 0:
                normalized[allocation_id] = _to_decimal(item.get('quantity'))
    for allocation in allocations:
        if normalized.get(allocation.id, Decimal('0')) != _to_decimal(allocation.qty):
            return False
    return True


def _register_actuals_for_trips(trips, shipment_date, raw_actuals, close_trip=False):
    trip = trips[0]
    if not isinstance(raw_actuals, list):
        return {'detail': 'actuals は配列で指定してください。'}, status.HTTP_400_BAD_REQUEST

    trip_ids = [item.id for item in trips]
    allocations = list(
        ShippingTripAllocation.objects.select_related('trip').filter(trip_id__in=trip_ids).order_by('id')
    )
    allocation_map = {a.id: a for a in allocations}

    normalized = {}
    split_map = {}
    for item in raw_actuals:
        try:
            allocation_id = int(item.get('allocation_id') or 0)
        except Exception:
            allocation_id = 0
        qty = _to_decimal(item.get('quantity'))
        if allocation_id <= 0 or allocation_id not in allocation_map:
            continue
        normalized[allocation_id] = qty
        split_map[allocation_id] = item.get('production_splits') or []

    created_count = 0
    updated_count = 0
    deleted_count = 0
    for allocation in allocations:
        qty = normalized.get(allocation.id, Decimal('0'))
        marker = _legacy_trip_actual_marker(allocation.trip_id, allocation.id)
        existing = _find_actual_for_allocation(allocation, allocation.trip_id)
        default_order_no = str(allocation.source_order_no or '').strip()
        split_rows = split_map[allocation.id] if allocation.id in split_map else _allocation_split_rows(allocation, default_order_no)
        normalized_split_rows = _normalize_split_rows(split_rows, default_order_no)
        final_remark = _encode_remark(marker, split_rows)
        if len(final_remark) > REMARK_MAX_LEN:
            return {
                'detail': f'生産日内訳が長すぎます。品番 {allocation.product_code} の内訳を短くしてください。'
            }, status.HTTP_400_BAD_REQUEST

        if qty <= 0:
            if existing:
                ShipmentActualHistory.objects.create(
                    shipment_actual=existing,
                    action='DELETE',
                    shipment_date=existing.shipment_date,
                    product_code=existing.product_code,
                    customer_code=existing.customer_code,
                    ship_to_code=existing.ship_to_code,
                    quantity=existing.quantity,
                    remark=existing.remark,
                )
                existing.delete()
                deleted_count += 1
            continue

        if existing:
            ShipmentActualHistory.objects.create(
                shipment_actual=existing,
                action='UPDATE',
                shipment_date=existing.shipment_date,
                product_code=existing.product_code,
                customer_code=existing.customer_code,
                ship_to_code=existing.ship_to_code,
                quantity=existing.quantity,
                remark=existing.remark,
            )
            existing.shipment_date = shipment_date
            existing.shipping_trip_allocation = allocation
            existing.product_code = allocation.product_code
            existing.customer_code = trip.customer_code
            existing.ship_to_code = allocation.ship_to_code or trip.ship_to_code
            existing.quantity = qty
            existing.remark = final_remark
            existing.save()
            _save_actual_split_rows(existing, normalized_split_rows)
            updated_count += 1
        else:
            created = ShipmentActual.objects.create(
                shipment_date=shipment_date,
                shipping_trip_allocation=allocation,
                product_code=allocation.product_code,
                customer_code=allocation.trip.customer_code,
                ship_to_code=allocation.ship_to_code or allocation.trip.ship_to_code,
                quantity=qty,
                remark=final_remark,
            )
            _save_actual_split_rows(created, normalized_split_rows)
            ShipmentActualHistory.objects.create(
                shipment_actual=created,
                action='CREATE',
                shipment_date=created.shipment_date,
                product_code=created.product_code,
                customer_code=created.customer_code,
                ship_to_code=created.ship_to_code,
                quantity=created.quantity,
                remark=created.remark,
            )
            created_count += 1

    if close_trip:
        for item in trips:
            if item.status != 'CLOSED':
                item.status = 'CLOSED'
                item.save(update_fields=['status'])

    return {
        'detail': '出荷実績を登録しました。',
        'created': created_count,
        'updated': updated_count,
        'deleted': deleted_count,
    }, None


def _display_user_name(user):
    if not user:
        return ''
    last = str(getattr(user, 'last_name', '') or '').strip()
    first = str(getattr(user, 'first_name', '') or '').strip()
    if last and first:
        return f'{last} {first}'
    if last:
        return last
    if first:
        return first
    full = str(user.get_full_name() or '').strip()
    if full:
        return full
    return str(getattr(user, 'username', '') or '')


def _trip_truck_id(trip):
    trip_ref = str(getattr(trip, 'trip_ref', '') or '').strip()
    if not trip_ref.startswith('TRUCK:'):
        return None
    try:
        return int(trip_ref.split(':', 1)[1])
    except Exception:
        return None


def _trip_actual_departure_date(trip, calc, truck_offset_map):
    truck_id = _trip_truck_id(trip)
    offset = 0
    if truck_id:
        offset = max(int(truck_offset_map.get(truck_id) or 0), 0)
    if offset <= 0:
        return trip.departure_date
    return calc.subtract_working_days(trip.departure_date, offset)


def _trip_notice_map(trips):
    if not trips:
        return {}
    try:
        rows = ShippingTripNotice.objects.filter(
            business_type__in={str(item.business_type or '').strip() for item in trips},
            customer_code__in={str(item.customer_code or '').strip() for item in trips},
            departure_date__in={item.departure_date for item in trips if item.departure_date},
            trip_ref__in={str(item.trip_ref or '').strip() for item in trips if str(item.trip_ref or '').strip()},
        )
    except ProgrammingError:
        return {}
    result = {}
    for row in rows:
        notice_text = str(row.notice_text or '').strip()
        if not notice_text:
            continue
        key = (
            str(row.business_type or '').strip(),
            str(row.customer_code or '').strip(),
            row.departure_date,
            str(row.trip_ref or '').strip(),
        )
        if key not in result:
            result[key] = []
        result[key].append({
            'notice_text': notice_text,
            'notice_type': _normalize_trip_notice_type(getattr(row, 'notice_type', TRIP_NOTICE_TYPE_NORMAL)),
        })
    return result


def _build_trip_payload(trip, allocations, product_meta_map, ship_to_style_map, calc, truck_offset_map, actual_by_allocation=None, trip_notice_map=None):
    details = []
    total_qty = Decimal('0')
    for item in allocations:
        qty = _to_decimal(item.qty)
        total_qty += qty
        actual = (actual_by_allocation or {}).get(item.id) if trip.status in ('DEPARTED', 'CLOSED') else None
        if not actual and trip.status in ('DEPARTED', 'CLOSED'):
            actual = _find_actual_for_allocation(item, trip.id)
        default_order_no = str(item.source_order_no or '').strip()
        container_name = ''
        if item.container_id:
            container_name = getattr(item.container, 'name', '') if item.container else ''
        details.append({
            'allocation_id': item.id,
            'product_code': item.product_code,
            'product_name': product_meta_map.get(item.product_code, {}).get('product_name', ''),
            'capacity': int(product_meta_map.get(item.product_code, {}).get('capacity') or 1),
            'customer_code': trip.customer_code,
            'ship_to_code': item.ship_to_code or '',
            'bg_color': ship_to_style_map.get((trip.customer_code, item.ship_to_code or ''), {}).get('bg_color', ''),
            'text_color': ship_to_style_map.get((trip.customer_code, item.ship_to_code or ''), {}).get('text_color', ''),
            'source_order_no': default_order_no,
            'due_date': item.due_date.isoformat() if item.due_date else None,
            'qty': _format_qty(qty),
            'container_name': container_name,
            'container_count': item.container_count,
            'production_splits': _actual_split_rows(actual, default_order_no) if actual else _allocation_split_rows(item, default_order_no),
        })

    details.sort(key=lambda x: (x['product_code'], x['ship_to_code'], x['due_date'] or ''))
    trip_code = (trip.trip_code or '').strip() or (trip.trip_ref or '')
    loading_user = getattr(trip, 'loading_by', None)
    departed_user = getattr(trip, 'departed_by', None)
    actual_departure_date = _trip_actual_departure_date(trip, calc, truck_offset_map)
    contact_notices = (trip_notice_map or {}).get((
        str(trip.business_type or '').strip(),
        str(trip.customer_code or '').strip(),
        actual_departure_date,
        str(trip.trip_ref or '').strip(),
    )) or []
    return {
        'id': trip.id,
        'trip_ids': [trip.id],
        'business_type': trip.business_type,
        'customer_code': trip.customer_code,
        'ship_to_code': trip.ship_to_code or '',
        'departure_date': trip.departure_date.isoformat(),
        'actual_departure_date': actual_departure_date.isoformat(),
        'trip_ref': trip.trip_ref,
        'trip_code': trip_code,
        'departure_time_plan': trip.departure_time_plan.strftime('%H:%M') if trip.departure_time_plan else None,
        'departure_time_actual': _format_dt(trip.departure_time_actual),
        'status': trip.status,
        'loading_by': _display_user_name(loading_user),
        'departed_by': _display_user_name(departed_user),
        'has_contact_notice': bool(contact_notices),
        'contact_notices': contact_notices,
        'total_qty': _format_qty(total_qty),
        'detail_count': len(details),
        'details': details,
    }


def _trip_group_key(payload):
    return (
        str(payload.get('actual_departure_date') or payload.get('departure_date') or ''),
        str(payload.get('business_type') or ''),
        str(payload.get('trip_ref') or '').strip(),
    )


def _merged_trip_status(statuses):
    normalized = [str(status or '').strip().upper() for status in statuses if status]
    if not normalized:
        return 'PLANNED'
    if len(set(normalized)) == 1:
        return normalized[0]
    for status in ('CLOSED', 'DEPARTED', 'LOADING', 'PLANNED'):
        if status in normalized:
            return status
    return normalized[0]


def _merge_trip_payloads(payloads):
    base = dict(payloads[0])
    all_trip_ids = []
    ship_to_codes = []
    details = []
    total_qty = Decimal('0')
    statuses = []
    merged_notices = []
    seen_notice_types = set()

    for payload in payloads:
        all_trip_ids.extend(payload.get('trip_ids') or [payload.get('id')])
        ship_to_code = str(payload.get('ship_to_code') or '').strip()
        if ship_to_code and ship_to_code not in ship_to_codes:
            ship_to_codes.append(ship_to_code)
        details.extend(payload.get('details') or [])
        total_qty += _to_decimal(payload.get('total_qty'))
        statuses.append(payload.get('status'))
        for n in payload.get('contact_notices') or []:
            nt = _normalize_trip_notice_type(n.get('notice_type'))
            if nt not in seen_notice_types:
                seen_notice_types.add(nt)
                merged_notices.append(n)

    details.sort(key=lambda x: (x['product_code'], x['ship_to_code'], x['due_date'] or '', x['allocation_id']))

    base['id'] = all_trip_ids[0] if all_trip_ids else base.get('id')
    base['trip_ids'] = all_trip_ids
    base['ship_to_code'] = '+'.join(ship_to_codes) if ship_to_codes else ''
    base['status'] = _merged_trip_status(statuses)
    base['has_contact_notice'] = bool(merged_notices)
    base['contact_notices'] = merged_notices
    base['total_qty'] = _format_qty(total_qty)
    base['detail_count'] = len(details)
    base['details'] = details
    return base


def _collect_truck_offset_map():
    return {
        row['id']: max(int(row['arrival_day_offset'] or 0), 0)
        for row in KubotaSakaiTruck.objects.filter(is_active=True).values('id', 'arrival_day_offset')
    }


def _expanded_trip_queryset(date_from, date_to, business_type, calc, max_offset):
    expanded_to = calc.add_working_days(date_to, max_offset) if max_offset > 0 else date_to
    qs = ShippingTrip.objects.filter(departure_date__gte=date_from, departure_date__lte=expanded_to)
    if business_type:
        qs = qs.filter(business_type=business_type)
    return qs


class ShippingTripExecutionView(APIView):
    """便確認（実行）向けAPI。"""

    def get(self, request):
        departure_date = _parse_date(request.query_params.get('departure_date'))
        if not departure_date:
            return Response({'detail': 'departure_date は必須です。'}, status=status.HTTP_400_BAD_REQUEST)

        business_type = (request.query_params.get('business_type') or '').strip()
        calendar = _resolve_kubota_line_calendar()
        calc = WorkingDayCalculator(calendar)
        truck_offset_map = _collect_truck_offset_map()
        max_offset = max(truck_offset_map.values(), default=0)
        candidate_dates = [departure_date]
        for offset in range(1, max_offset + 1):
            candidate_dates.append(calc.add_working_days(departure_date, offset))

        if business_type == 'KUBOTA_SAKAI':
            base_qs = ShippingTrip.objects.filter(business_type=business_type, departure_date__in=candidate_dates)
        elif business_type:
            base_qs = ShippingTrip.objects.filter(departure_date=departure_date, business_type=business_type)
        else:
            from django.db.models import Q
            base_qs = ShippingTrip.objects.filter(
                Q(departure_date=departure_date) |
                Q(business_type='KUBOTA_SAKAI', departure_date__in=candidate_dates)
            )

        trips = list(
            base_qs
            .select_related('run', 'loading_by', 'departed_by')
            .order_by('business_type', 'departure_time_plan', 'trip_code', 'trip_ref', 'id')
        )
        trip_notice_map = _trip_notice_map(trips)
        trip_ids = [t.id for t in trips]
        allocations = list(
            ShippingTripAllocation.objects
            .select_related('container')
            .filter(trip_id__in=trip_ids)
            .order_by('trip_id', 'product_code', 'id')
        )
        product_codes = {a.product_code for a in allocations}
        product_meta_map = {
            p.product_code: {
                'product_name': p.product_name,
                'capacity': max(int(_to_decimal(getattr(p, 'capacity', None), default='1')), 1),
            }
            for p in Product.objects.filter(product_code__in=product_codes)
        }
        customer_codes = {str(t.customer_code or '').strip() for t in trips if str(t.customer_code or '').strip()}
        ship_to_codes = {str(a.ship_to_code or '').strip() for a in allocations if str(a.ship_to_code or '').strip()}
        ship_to_style_map = {}
        target_color_keys = set()
        target_ship_to_keys = set()
        if customer_codes and ship_to_codes:
            for row in ShipToLeadTime.objects.filter(
                customer__customer_code__in=customer_codes,
                ship_to_code__in=ship_to_codes,
                is_active=True,
            ).values('customer__customer_code', 'ship_to_code', 'bg_color', 'text_color'):
                ship_to_style_map[(str(row['customer__customer_code'] or '').strip(), str(row['ship_to_code'] or '').strip())] = {
                    'bg_color': str(row.get('bg_color') or '').strip(),
                    'text_color': str(row.get('text_color') or '').strip(),
                }
            for row in ShipToLeadTimeColorExclusion.objects.filter(
                ship_to_lead_time__customer__customer_code__in=customer_codes,
                ship_to_lead_time__ship_to_code__in=ship_to_codes,
                ship_to_lead_time__is_active=True,
            ).values(
                'ship_to_lead_time__customer__customer_code',
                'ship_to_lead_time__ship_to_code',
                'product_code',
            ):
                customer_code = str(row['ship_to_lead_time__customer__customer_code'] or '').strip()
                ship_to_code = str(row['ship_to_lead_time__ship_to_code'] or '').strip()
                product_code = str(row['product_code'] or '').strip()
                target_ship_to_keys.add((customer_code, ship_to_code))
                target_color_keys.add((customer_code, ship_to_code, product_code))

        allocations_by_trip = defaultdict(list)
        for item in allocations:
            allocations_by_trip[item.trip_id].append(item)

        allocation_ids = [item.id for item in allocations]
        actual_rows = ShipmentActual.objects.none()
        if allocation_ids:
            actual_rows = (
                ShipmentActual.objects
                .filter(shipping_trip_allocation_id__in=allocation_ids)
                .prefetch_related('splits')
                .order_by('id')
            )
        actual_by_allocation = {}
        for actual in actual_rows:
            if actual.shipping_trip_allocation_id:
                actual_by_allocation[actual.shipping_trip_allocation_id] = actual

        raw_trips_payload = [
            _build_trip_payload(
                trip,
                allocations_by_trip.get(trip.id, []),
                product_meta_map,
                ship_to_style_map,
                calc,
                truck_offset_map,
                actual_by_allocation,
                trip_notice_map,
            )
            for trip in trips
        ]
        for payload in raw_trips_payload:
            for detail in payload.get('details') or []:
                ship_to_key = (
                    str(detail.get('customer_code') or '').strip(),
                    str(detail.get('ship_to_code') or '').strip(),
                )
                product_key = (
                    ship_to_key[0],
                    ship_to_key[1],
                    str(detail.get('product_code') or '').strip(),
                )
                if ship_to_key in target_ship_to_keys and product_key not in target_color_keys:
                    detail['bg_color'] = ''
                    detail['text_color'] = ''
        grouped_payloads = defaultdict(list)
        for payload in raw_trips_payload:
            if payload.get('actual_departure_date') != departure_date.isoformat():
                continue
            grouped_payloads[_trip_group_key(payload)].append(payload)
        trips_payload = [_merge_trip_payloads(items) for _, items in sorted(grouped_payloads.items(), key=lambda x: x[0])]

        business_types = list(
            ShippingTrip.objects
            .filter(departure_date=departure_date)
            .values_list('business_type', flat=True)
            .distinct()
            .order_by('business_type')
        )

        status_count = defaultdict(int)
        for payload in trips_payload:
            status_count[payload.get('status')] += 1

        prev_business_day = calc.subtract_working_days(departure_date, 1).isoformat()

        return Response({
            'departure_date': departure_date.isoformat(),
            'prev_business_day': prev_business_day,
            'business_type': business_type,
            'business_types': business_types,
            'summary': {
                'total': len(trips_payload),
                'planned': status_count.get('PLANNED', 0),
                'loading': status_count.get('LOADING', 0),
                'departed': status_count.get('DEPARTED', 0),
                'closed': status_count.get('CLOSED', 0),
            },
            'trips': trips_payload,
        })

    def post(self, request):
        trip_id = request.data.get('trip_id')
        raw_trip_ids = request.data.get('trip_ids') or []
        action = (request.data.get('action') or '').strip()
        trip_ids = []
        if isinstance(raw_trip_ids, list):
            for value in raw_trip_ids:
                try:
                    normalized_id = int(value)
                except Exception:
                    normalized_id = 0
                if normalized_id > 0 and normalized_id not in trip_ids:
                    trip_ids.append(normalized_id)
        if not trip_ids and trip_id:
            try:
                normalized_id = int(trip_id)
            except Exception:
                normalized_id = 0
            if normalized_id > 0:
                trip_ids.append(normalized_id)
        if not trip_ids:
            return Response({'detail': 'trip_id または trip_ids は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        if action not in ('mark_loading', 'mark_departed', 'reopen', 'register_actual', 'save_production_dates'):
            return Response({'detail': 'action が不正です。'}, status=status.HTTP_400_BAD_REQUEST)

        trips = list(ShippingTrip.objects.filter(id__in=trip_ids).order_by('id'))
        if not trips:
            return Response({'detail': '対象便が見つかりません。'}, status=status.HTTP_404_NOT_FOUND)
        trip = trips[0]

        if action == 'mark_loading':
            if any(item.status in ('DEPARTED', 'CLOSED') for item in trips):
                return Response({'detail': '出発済/完了の便は積込完了に戻せません。'}, status=status.HTTP_400_BAD_REQUEST)
            for item in trips:
                result, error_status = _save_production_splits_for_trip(item, request.data.get('actuals') or [])
                if error_status:
                    return Response(result, status=error_status)
            if any(not _trip_input_matches_plan(item, request.data.get('actuals') or []) for item in trips):
                return Response(
                    {'detail': '実績合計が計画数と一致しないため、積込完了できません。'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            for item in trips:
                item.status = 'LOADING'
                if getattr(request.user, 'is_authenticated', False):
                    item.loading_by = request.user
                item.save()
        elif action == 'mark_departed':
            if any(item.status == 'CLOSED' for item in trips):
                return Response({'detail': '完了便は出発更新できません。'}, status=status.HTTP_400_BAD_REQUEST)
            if any(item.status != 'LOADING' for item in trips):
                return Response({'detail': '積込完了の便のみ出発更新できます。'}, status=status.HTTP_400_BAD_REQUEST)
            result, error_status = _register_actuals_for_trips(
                trips,
                trip.departure_date,
                request.data.get('actuals') or [],
                close_trip=False,
            )
            if error_status:
                return Response(result, status=error_status)
            departure_now = datetime.now()
            for item in trips:
                item.status = 'DEPARTED'
                if not item.departure_time_actual:
                    item.departure_time_actual = departure_now
                if getattr(request.user, 'is_authenticated', False):
                    item.departed_by = request.user
                    if not item.loading_by:
                        item.loading_by = request.user
                item.save()
            # 出荷進度を再計算
            try:
                from shipping.services.shipping_progress import recalculate_shipping_progress
                calc_start = trip.departure_date - timedelta(days=1)
                calc_end = trip.departure_date + timedelta(days=get_progress_horizon_days())
                recalculate_shipping_progress(calc_start, calc_end)
            except Exception:
                pass
        elif action == 'reopen':
            existing_actuals = []
            allocation_ids = list(
                ShippingTripAllocation.objects.filter(trip_id__in=trip_ids).values_list('id', flat=True)
            )
            if allocation_ids:
                existing_actuals.extend(list(
                    ShipmentActual.objects.filter(shipping_trip_allocation_id__in=allocation_ids).order_by('id')
                ))
            for item in trips:
                marker_prefix = f'[TRIP_ACTUAL]{item.id}:'
                existing_actuals.extend(list(
                    ShipmentActual.objects.filter(
                        shipping_trip_allocation__isnull=True,
                        remark__startswith=marker_prefix,
                    ).order_by('id')
                ))
            for actual in existing_actuals:
                ShipmentActualHistory.objects.create(
                    shipment_actual=actual,
                    action='DELETE',
                    shipment_date=actual.shipment_date,
                    product_code=actual.product_code,
                    customer_code=actual.customer_code,
                    ship_to_code=actual.ship_to_code,
                    quantity=actual.quantity,
                    remark=actual.remark,
                )
            if existing_actuals:
                ShipmentActual.objects.filter(id__in=[a.id for a in existing_actuals]).delete()

            for item in trips:
                item.status = 'PLANNED'
                item.departure_time_actual = None
                item.loading_by = None
                item.departed_by = None
                item.save()
            # 出荷進度を再計算（実績削除後）
            try:
                from shipping.services.shipping_progress import recalculate_shipping_progress
                calc_start = trip.departure_date - timedelta(days=1)
                calc_end = trip.departure_date + timedelta(days=get_progress_horizon_days())
                recalculate_shipping_progress(calc_start, calc_end)
            except Exception:
                pass
        elif action == 'save_production_dates':
            total_updated = 0
            for item in trips:
                result, error_status = _save_production_splits_for_trip(item, request.data.get('actuals') or [])
                if error_status:
                    return Response(result, status=error_status)
                total_updated += result.get('updated', 0)
            return Response({
                'detail': '生産日内訳を保存しました。',
                'updated': total_updated,
            })
        elif action == 'register_actual':
            if any(item.status != 'DEPARTED' for item in trips):
                return Response(
                    {'detail': '出発済の便のみ実績登録できます。'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            shipment_date = _parse_date(request.data.get('shipment_date')) or trip.departure_date
            result, error_status = _register_actuals_for_trips(
                trips,
                shipment_date,
                request.data.get('actuals') or [],
                close_trip=True,
            )
            if error_status:
                return Response(result, status=error_status)
            # 出荷進度を再計算
            try:
                from shipping.services.shipping_progress import recalculate_shipping_progress
                calc_start = shipment_date - timedelta(days=1)
                calc_end = shipment_date + timedelta(days=get_progress_horizon_days())
                recalculate_shipping_progress(calc_start, calc_end)
            except Exception:
                pass
            return Response(result)

        allocations = list(
            ShippingTripAllocation.objects
            .select_related('container')
            .filter(trip_id__in=trip_ids)
            .order_by('product_code', 'id')
        )
        product_codes = {a.product_code for a in allocations}
        product_meta_map = {
            p.product_code: {
                'product_name': p.product_name,
                'capacity': max(int(_to_decimal(getattr(p, 'capacity', None), default='1')), 1),
            }
            for p in Product.objects.filter(product_code__in=product_codes)
        }
        ship_to_style_map = {}
        trip_notice_map = _trip_notice_map(trips)
        calc = WorkingDayCalculator(_resolve_kubota_line_calendar())
        truck_offset_map = _collect_truck_offset_map()
        merged_payload = _merge_trip_payloads([
            _build_trip_payload(
                item,
                [allocation for allocation in allocations if allocation.trip_id == item.id],
                product_meta_map,
                ship_to_style_map,
                calc,
                truck_offset_map,
                trip_notice_map=trip_notice_map,
            )
            for item in trips
        ])
        return Response({
            'trip': merged_payload,
        })


class ShippingTripProgressView(APIView):
    """便進捗確認向けAPI。"""

    def get(self, request):
        date_from = _parse_date(request.query_params.get('date_from'))
        date_to = _parse_date(request.query_params.get('date_to'))
        if not date_from or not date_to:
            return Response({'detail': 'date_from と date_to は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        if date_from > date_to:
            return Response({'detail': 'date_from は date_to 以前を指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

        business_type = (request.query_params.get('business_type') or '').strip()
        status_filter = (request.query_params.get('status') or '').strip().upper()
        calendar = _resolve_kubota_line_calendar()
        calc = WorkingDayCalculator(calendar)
        truck_offset_map = _collect_truck_offset_map()
        max_offset = max(truck_offset_map.values(), default=0)

        qs = _expanded_trip_queryset(date_from, date_to, business_type, calc, max_offset)
        if status_filter in ('PLANNED', 'LOADING', 'DEPARTED', 'CLOSED'):
            qs = qs.filter(status=status_filter)
        trips = list(
            qs.select_related('run__created_by', 'loading_by', 'departed_by')
            .order_by('departure_date', 'business_type', 'departure_time_plan', 'trip_code', 'trip_ref', 'id')
        )

        grouped_trips = defaultdict(list)
        for trip in trips:
            actual_departure_date = _trip_actual_departure_date(trip, calc, truck_offset_map)
            if actual_departure_date < date_from or actual_departure_date > date_to:
                continue
            payload = {
                'id': trip.id,
                'departure_date': trip.departure_date.isoformat(),
                'actual_departure_date': actual_departure_date.isoformat(),
                'business_type': trip.business_type,
                'trip_ref': trip.trip_ref,
                'trip_code': (trip.trip_code or '').strip() or (trip.trip_ref or ''),
                'ship_to_code': trip.ship_to_code or '',
                'status': trip.status,
                'departure_time_plan': trip.departure_time_plan.strftime('%H:%M') if trip.departure_time_plan else None,
                'departure_time_actual': _format_dt(trip.departure_time_actual),
                'loading_by': _display_user_name(getattr(trip, 'loading_by', None)),
                'departed_by': _display_user_name(getattr(trip, 'departed_by', None)),
                'created_by': _display_user_name(getattr(getattr(trip, 'run', None), 'created_by', None)),
            }
            grouped_trips[_trip_group_key(payload)].append(payload)

        daily = defaultdict(lambda: {'total': 0, 'planned': 0, 'loading': 0, 'departed': 0, 'closed': 0})
        trip_rows = []
        for _, payloads in sorted(grouped_trips.items(), key=lambda x: x[0]):
            merged = _merge_trip_payloads(payloads)
            key = merged.get('actual_departure_date') or merged.get('departure_date')
            daily[key]['total'] += 1
            if merged.get('status') == 'PLANNED':
                daily[key]['planned'] += 1
            elif merged.get('status') == 'LOADING':
                daily[key]['loading'] += 1
            elif merged.get('status') == 'DEPARTED':
                daily[key]['departed'] += 1
            elif merged.get('status') == 'CLOSED':
                daily[key]['closed'] += 1

            created_by = next((item.get('created_by') for item in payloads if item.get('created_by')), '')
            loading_by = next((item.get('loading_by') for item in payloads if item.get('loading_by')), '')
            departed_by = next((item.get('departed_by') for item in payloads if item.get('departed_by')), '')
            if merged.get('status') == 'PLANNED':
                shipping_staff = ''
            elif merged.get('status') == 'LOADING' and loading_by:
                shipping_staff = loading_by
            elif merged.get('status') in ('DEPARTED', 'CLOSED') and departed_by:
                shipping_staff = departed_by
            elif created_by:
                shipping_staff = created_by
            else:
                shipping_staff = ''
            trip_rows.append({
                'id': merged.get('id'),
                'departure_date': key,
                'business_type': merged.get('business_type'),
                'trip_code': merged.get('trip_code'),
                'ship_to_code': merged.get('ship_to_code'),
                'status': merged.get('status'),
                'departure_time_plan': merged.get('departure_time_plan'),
                'departure_time_actual': merged.get('departure_time_actual'),
                'shipping_staff': shipping_staff,
            })

        business_types = sorted({row.get('business_type') for row in trip_rows if row.get('business_type')})

        return Response({
            'date_from': date_from.isoformat(),
            'date_to': date_to.isoformat(),
            'business_type': business_type,
            'status': status_filter,
            'business_types': business_types,
            'daily_summary': [
                {'date': day, **summary}
                for day, summary in sorted(daily.items(), key=lambda x: x[0])
            ],
            'trips': trip_rows,
        })
