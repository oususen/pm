"""クボタ堺便計画 API（生産計画パターン準拠）

データフロー:
  OrderLine →(取込)→ KubotaSakaiDueAdjustment →(便計画)→ TripAssignment →(sync)→ LineBacklog
                                                                              → pickup カスケード → 前工程需要

LinePlan / LineGanttPlan は不使用。LineBacklog のみ直接保存。
plan_id に truck_id を埋め込み、pickup カスケードで arrival_day_offset ベースの LT 判定に使う。
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_HALF_UP
from io import BytesIO
import logging

from django.db import ProgrammingError, transaction
from django.db.models import Count, Max, Q
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

from masters.models import Calendar, CalendarDay, ContainerCapacity, KubotaSakaiTruck, Line, Process, Product, ProductContainer
from shipping.models import (
    KubotaSakaiDeliveryProgress,
    KubotaSakaiTripDisplaySetting,
    ShipToLeadTime,
)
from orders.core.models import (
    KubotaSakaiDueAdjustment,
    KubotaSakaiPseudoTruckProduct,
    KubotaSakaiTripAssignment,
    ShippingRun,
    ShippingTrip,
    ShippingTripAllocation,
    ShippingTripNotice,
)
from production.models_line_backlog import LineBacklog
from system_settings.models import SystemSetting

from .services.kubota_sakai_delivery_progress import recalculate_delivery_progress
from .services.truck_load_calculator import calculate_truck_load

# クボタ配送ライン定数
KUBOTA_DELIVERY_LINE_CODE = 'KUBOTA_DELIVERY'
KUBOTA_DELIVERY_LINE_NAME = 'クボタ配送ライン'
KUBOTA_DELIVERY_PROCESS_CODE = 'KUBOTA_DELIVERY'
KUBOTA_DELIVERY_PROCESS_NAME = 'クボタ配送工程'

# plan_id プレフィックス（pickup カスケードでクボタ便を識別するためのマーカー）
KUBOTA_TRIP_PLAN_ID_PREFIX = 'KBT_T'
KUBOTA_COMMON_BUSINESS_TYPE = 'KUBOTA_SAKAI'
KUBOTA_COMMON_SOURCE_TYPE = 'KUBOTA_SAKAI_DUE'
KUBOTA_CUSTOMER_CODE = '000196'
KUBOTA_DATE_HEADER_TRIP_REF = 'DATEHDR:MAIN'

logger = logging.getLogger(__name__)
TRIP_NOTICE_TYPE_NORMAL = 'NORMAL'
TRIP_NOTICE_TYPE_URGENT = 'URGENT'
TRIP_NOTICE_TYPE_VENDOR = 'VENDOR'
TRIP_NOTICE_VALID_TYPES = {TRIP_NOTICE_TYPE_NORMAL, TRIP_NOTICE_TYPE_URGENT, TRIP_NOTICE_TYPE_VENDOR}


def _normalize_trip_notice_type(value):
    notice_type = str(value or '').strip().upper()
    if notice_type in TRIP_NOTICE_VALID_TYPES:
        return notice_type
    return TRIP_NOTICE_TYPE_NORMAL


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

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
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def _append_container_option(
    options, container_id, container_name, capacity,
    width=None, depth=None, height=None, stackable=None, max_stack=None,
    orientation='free',
):
    if not container_id:
        return
    if any(int(item.get('container_id') or 0) == int(container_id) for item in options):
        return
    options.append({
        'container_id': container_id,
        'container_name': container_name or '',
        'capacity': capacity,
        'width': width,
        'depth': depth,
        'height': height,
        'stackable': stackable,
        'max_stack': max_stack,
        'orientation': orientation or 'free',
    })


def _to_int_qty(value):
    qty = _to_decimal(value)
    if qty <= 0:
        return 0
    return int(qty.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _format_hhmm(value):
    if not value:
        return ''
    try:
        return value.strftime('%H:%M')
    except Exception:
        return str(value)


def _physical_truck_key(truck):
    if not truck:
        return ''
    key = str(getattr(truck, 'physical_truck_code', '') or '').strip()
    if key:
        return key
    truck_id = getattr(truck, 'id', None)
    return f'TRUCK:{truck_id}' if truck_id else ''


def _calculate_assignment_area(item, truck):
    """1割付レコードの実効使用面積を返す。"""
    container = item.get('container') or {}
    qty = _to_decimal(item.get('qty'))
    capacity = _to_decimal(container.get('capacity'), default='1')
    if capacity <= 0:
        capacity = Decimal('1')

    width = _to_decimal(container.get('width'))
    depth = _to_decimal(container.get('depth'))
    height = _to_decimal(container.get('height'))
    if width <= 0 or depth <= 0 or qty <= 0:
        return Decimal('0')

    layers = Decimal('1')
    if bool(container.get('stackable', True)) and height > 0:
        truck_layers = int(_to_decimal(truck.height) // height)
        if truck_layers > 0:
            max_stack = int(container.get('max_stack') or 999)
            layers = Decimal(str(min(truck_layers, max_stack if max_stack > 0 else truck_layers)))

    effective_floor = width * depth / (layers if layers > 0 else Decimal('1'))
    container_count = (qty / capacity).to_integral_value(rounding=ROUND_CEILING)
    return effective_floor * container_count


def _resolve_kubota_calendar():
    rows = Calendar.objects.all()
    exact_hits = rows.filter(
        Q(calendar_code__iexact='kubota_sakai')
        | Q(calendar_code__iexact='kobota_sakai')
    )
    if exact_hits.exists():
        return exact_hits.order_by('id').first()
    name_hits = rows.filter(Q(calendar_name__icontains='クボタ') & Q(calendar_name__icontains='堺'))
    if name_hits.exists():
        return name_hits.order_by('id').first()
    return None


def _build_calendar_day_map(calendar):
    if not calendar:
        return {}
    return {
        item.target_date: bool(item.is_working_day)
        for item in CalendarDay.objects.filter(calendar_id=calendar.id)
    }


def _is_working_day(target_date, calendar_map):
    if target_date in calendar_map:
        return bool(calendar_map[target_date])
    return target_date.weekday() < 5


def _subtract_business_days(target_date, days, calendar_map):
    current = target_date
    remaining = max(int(days or 0), 0)
    while remaining > 0:
        current -= timedelta(days=1)
        if _is_working_day(current, calendar_map):
            remaining -= 1
    return current


def _add_business_days(target_date, days, calendar_map):
    current = target_date
    remaining = max(int(days or 0), 0)
    while remaining > 0:
        current += timedelta(days=1)
        if _is_working_day(current, calendar_map):
            remaining -= 1
    return current


def _truck_actual_departure_date(due_date, truck, calendar_map):
    if not due_date or not truck:
        return due_date
    offset_days = max(int(getattr(truck, 'arrival_day_offset', 0) or 0), 0)
    return _subtract_business_days(due_date, offset_days, calendar_map)


def _departure_summary_query_end(base_date, trucks):
    max_offset = 0
    for truck in trucks or []:
        try:
            max_offset = max(max_offset, int(getattr(truck, 'arrival_day_offset', 0) or 0))
        except Exception:
            continue
    return base_date + timedelta(days=max(14, max_offset * 3 + 7))


def _build_departure_truck_summaries(records, target_dates, products, truck_map):
    summaries_by_date = {d.isoformat(): [] for d in target_dates}
    per_group_load_items = defaultdict(list)
    per_group_errors = defaultdict(list)
    per_group_truck_ids = defaultdict(set)
    per_group_truck = {}
    truck_ids_by_physical_code = defaultdict(set)

    for truck in truck_map.values():
        physical_truck_code = str(getattr(truck, 'physical_truck_code', '') or '').strip()
        if physical_truck_code:
            truck_ids_by_physical_code[physical_truck_code].add(truck.id)

    for record in records:
        actual_departure_date = record.get('actual_departure_date')
        truck = record.get('truck')
        product = products.get(record.get('product_code'))
        if actual_departure_date not in target_dates or not truck or not product:
            continue
        group_key = (actual_departure_date, _physical_truck_key(truck))
        per_group_truck_ids[group_key].add(truck.id)
        per_group_truck.setdefault(group_key, truck)
        try:
            per_group_load_items[group_key].append(
                _build_load_item(
                    product,
                    record.get('qty'),
                    record.get('container_override'),
                    record.get('capacity_override'),
                )
            )
        except Exception:
            logger.exception(
                '実出発日便占有率集計に失敗しました: product_code=%s truck_id=%s due_date=%s',
                record.get('product_code'),
                getattr(truck, 'id', None),
                record.get('due_date'),
            )
            per_group_errors[group_key].append(f"{record.get('product_code')}: 積載データ生成失敗")

    for group_key, load_items in per_group_load_items.items():
        actual_departure_date, physical_truck_code = group_key
        representative_truck = per_group_truck[group_key]
        try:
            load = calculate_truck_load(load_items, representative_truck)
        except Exception:
            logger.exception(
                '実出発日便占有率プレビュー計算に失敗しました: departure_date=%s physical_truck_code=%s',
                actual_departure_date,
                physical_truck_code,
            )
            load = {
                'occupancy_percent': Decimal('0'),
                'total_weight': Decimal('0'),
                'errors': ['積載計算に失敗しました。'],
            }

        load_errors = list(per_group_errors.get(group_key, [])) + list(load.get('errors') or [])
        representative_physical_code = str(
            getattr(representative_truck, 'physical_truck_code', '') or ''
        ).strip()
        summary_truck_ids = per_group_truck_ids[group_key]
        if representative_physical_code:
            summary_truck_ids = truck_ids_by_physical_code[representative_physical_code]

        for truck_id in sorted(summary_truck_ids):
            truck = truck_map.get(truck_id) or representative_truck
            summaries_by_date[actual_departure_date.isoformat()].append({
                'truck_id': truck.id,
                'truck_name': truck.alias_name or truck.name,
                'physical_truck_code': truck.physical_truck_code or '',
                'occupancy_percent': str(load['occupancy_percent']),
                'total_weight': str(load['total_weight']),
                'can_fit': load.get('can_fit', False),
                'placed': load.get('placed', []),
                'remaining': load.get('remaining', []),
                'errors': load_errors,
                'warnings': list(load.get('warnings') or []),
            })

    return summaries_by_date


def _trip_notice_map_by_date(target_dates, truck_ids):
    target_dates = {item for item in (target_dates or []) if item}
    truck_ids = {int(item) for item in (truck_ids or []) if item}
    if not target_dates or not truck_ids:
        return {}

    try:
        rows = ShippingTripNotice.objects.filter(
            business_type=KUBOTA_COMMON_BUSINESS_TYPE,
            customer_code=KUBOTA_CUSTOMER_CODE,
            departure_date__in=target_dates,
            trip_ref__in=[f'TRUCK:{truck_id}' for truck_id in sorted(truck_ids)],
        ).values('departure_date', 'trip_ref', 'notice_text', 'notice_type')
    except ProgrammingError:
        return {}

    result = {}
    for row in rows:
        trip_ref = str(row.get('trip_ref') or '').strip()
        if not trip_ref.startswith('TRUCK:'):
            continue
        try:
            truck_id = int(trip_ref.split(':', 1)[1])
        except Exception:
            continue
        date_value = row.get('departure_date')
        if not date_value:
            continue
        notice_text = str(row.get('notice_text') or '').strip()
        if not notice_text:
            continue
        key = (date_value.isoformat(), truck_id)
        if key not in result:
            result[key] = []
        result[key].append({
            'notice_text': notice_text,
            'notice_type': _normalize_trip_notice_type(row.get('notice_type')),
        })
    return result


def _attach_trip_notices_to_summaries(summary_map_by_date, target_dates, truck_ids):
    notice_map = _trip_notice_map_by_date(target_dates, truck_ids)
    for raw_date, summaries in (summary_map_by_date or {}).items():
        for summary in summaries or []:
            truck_id = int(summary.get('truck_id') or 0)
            notices = notice_map.get((raw_date, truck_id), [])
            summary['contact_notices'] = notices
            summary['has_contact_notice'] = bool(notices)
    return summary_map_by_date


def _get_trip_notices(target_date, trip_ref):
    if not target_date or not trip_ref:
        return []
    try:
        rows = ShippingTripNotice.objects.filter(
            business_type=KUBOTA_COMMON_BUSINESS_TYPE,
            customer_code=KUBOTA_CUSTOMER_CODE,
            departure_date=target_date,
            trip_ref=trip_ref,
        ).values('notice_text', 'notice_type')
    except ProgrammingError:
        rows = []
    return [
        {
            'notice_type': _normalize_trip_notice_type(r['notice_type']),
            'notice_text': str(r.get('notice_text') or '').strip(),
        }
        for r in rows if str(r.get('notice_text') or '').strip()
    ]


def _locked_trip_map(target_date):
    locked = {}
    trips = ShippingTrip.objects.filter(
        business_type=KUBOTA_COMMON_BUSINESS_TYPE,
        customer_code=KUBOTA_CUSTOMER_CODE,
        departure_date=target_date,
        status__in=('DEPARTED', 'CLOSED'),
    ).values('trip_ref', 'status')
    for trip in trips:
        trip_ref = str(trip.get('trip_ref') or '').strip()
        if not trip_ref.startswith('TRUCK:'):
            continue
        try:
            truck_id = int(trip_ref.split(':', 1)[1])
        except Exception:
            continue
        locked[truck_id] = str(trip.get('status') or '').strip().upper()
    return locked


def _locked_status_label(status_value):
    status_key = str(status_value or '').strip().upper()
    if status_key == 'DEPARTED':
        return '出発済'
    if status_key == 'CLOSED':
        return '完了'
    return 'ロック'


def _locked_assignment_trucks_by_due(target_date, due_ids):
    result = defaultdict(set)
    if not due_ids:
        return result
    rows = ShippingTripAllocation.objects.filter(
        source_type=KUBOTA_COMMON_SOURCE_TYPE,
        source_id__in=due_ids,
        trip__business_type=KUBOTA_COMMON_BUSINESS_TYPE,
        trip__customer_code=KUBOTA_CUSTOMER_CODE,
        trip__departure_date=target_date,
        trip__status__in=('DEPARTED', 'CLOSED'),
    ).values_list('source_id', 'trip__trip_ref')
    for source_id, trip_ref in rows:
        trip_ref = str(trip_ref or '').strip()
        if not trip_ref.startswith('TRUCK:'):
            continue
        try:
            truck_id = int(trip_ref.split(':', 1)[1])
        except Exception:
            continue
        result[int(source_id)].add(truck_id)
    return result


def _get_deadline_days():
    row = SystemSetting.objects.filter(key='kubota_sakai.assignment_deadline_days').first()
    if not row:
        return 3
    try:
        return max(int(row.value), 0)
    except Exception:
        return 3


def _build_load_item(product, qty, container_override=None, capacity_override=None):
    """Product オブジェクトから積載計算用アイテムを構築"""
    container = container_override or (getattr(product, 'used_container', None) if product else None)
    unit_weight = Decimal('0')
    if product and all(
        getattr(product, f, None) is not None
        for f in ('specific_gravity', 'size_length', 'size_width', 'size_thickness')
    ):
        unit_weight = (
            _to_decimal(product.specific_gravity)
            * _to_decimal(product.size_length)
            * _to_decimal(product.size_width)
            * _to_decimal(product.size_thickness)
            / Decimal('1000000')
        )

    if capacity_override:
        capacity = capacity_override
    else:
        capacity = getattr(product, 'capacity', None) if product else None
        if not capacity and container:
            capacity = container.capacity

    parent = getattr(container, 'parent_container', None) if container else None
    parent_dict = None
    if parent:
        parent_dict = {
            'width': getattr(parent, 'width', None),
            'depth': getattr(parent, 'depth', None),
            'height': getattr(parent, 'height', None),
            'capacity': getattr(container, 'parent_capacity', None),
            'can_mix': getattr(parent, 'can_mix', True),
            'stackable': getattr(parent, 'stackable', True),
            'max_stack': getattr(parent, 'max_stack', 999),
            'orientation': getattr(parent, 'orientation', 'free'),
        }
    return {
        'product_code': product.product_code if product else '',
        'qty': _to_decimal(qty),
        'unit_weight': unit_weight,
        'container': {
            'width': getattr(container, 'width', None) if container else None,
            'depth': getattr(container, 'depth', None) if container else None,
            'height': getattr(container, 'height', None) if container else None,
            'capacity': capacity or 1,
            'can_mix': getattr(container, 'can_mix', True) if container else True,
            'stackable': getattr(container, 'stackable', True) if container else True,
            'max_stack': getattr(container, 'max_stack', 999) if container else 999,
            'orientation': getattr(container, 'orientation', 'free') if container else 'free',
            'parent': parent_dict,
        },
    }


# ---------------------------------------------------------------------------
# クボタ配送ライン / 工程の解決
# ---------------------------------------------------------------------------

def _resolve_kubota_delivery_line_process():
    calendar = _resolve_kubota_calendar()
    existing_process = (
        Process.objects.select_related('line')
        .filter(
            Q(process_code='4902')
            | Q(process_name__icontains='クボタ配送')
        )
        .order_by('id')
        .first()
    )
    if existing_process and existing_process.line_id:
        line = existing_process.line
        line_updates = []
        if not line.is_active:
            line.is_active = True
            line_updates.append('is_active')
        if calendar and line.calendar_id != calendar.id:
            line.calendar = calendar
            line_updates.append('calendar')
        if line_updates:
            line.save(update_fields=line_updates)
        return line, existing_process

    existing_line = (
        Line.objects.filter(
            Q(line_code='L3102')
            | Q(line_name__icontains='クボタ配送ライン')
        )
        .order_by('id')
        .first()
    )
    if existing_line:
        if not existing_line.is_active or (calendar and existing_line.calendar_id != calendar.id):
            line_updates = []
            if not existing_line.is_active:
                existing_line.is_active = True
                line_updates.append('is_active')
            if calendar and existing_line.calendar_id != calendar.id:
                existing_line.calendar = calendar
                line_updates.append('calendar')
            existing_line.save(update_fields=line_updates)

        process = (
            Process.objects.filter(
                line_id=existing_line.id,
                process_name__icontains='クボタ配送',
            )
            .order_by('id')
            .first()
        )
        if process:
            return existing_line, process

        created_process = Process.objects.create(
            process_code=KUBOTA_DELIVERY_PROCESS_CODE,
            process_name=KUBOTA_DELIVERY_PROCESS_NAME,
            line=existing_line,
        )
        return existing_line, created_process

    line_defaults = {
        'line_name': KUBOTA_DELIVERY_LINE_NAME,
        'line_type': 'OTHER',
        'is_active': True,
    }
    if calendar:
        line_defaults['calendar'] = calendar
    line, created = Line.objects.get_or_create(
        line_code=KUBOTA_DELIVERY_LINE_CODE,
        defaults=line_defaults,
    )
    update_fields = []
    if line.line_name != KUBOTA_DELIVERY_LINE_NAME:
        line.line_name = KUBOTA_DELIVERY_LINE_NAME
        update_fields.append('line_name')
    if line.line_type != 'OTHER':
        line.line_type = 'OTHER'
        update_fields.append('line_type')
    if not line.is_active:
        line.is_active = True
        update_fields.append('is_active')
    if calendar and line.calendar_id != calendar.id:
        line.calendar = calendar
        update_fields.append('calendar')
    if update_fields and not created:
        line.save(update_fields=update_fields)

    process, p_created = Process.objects.get_or_create(
        process_code=KUBOTA_DELIVERY_PROCESS_CODE,
        defaults={
            'process_name': KUBOTA_DELIVERY_PROCESS_NAME,
            'line': line,
        },
    )
    process_updates = []
    if process.process_name != KUBOTA_DELIVERY_PROCESS_NAME:
        process.process_name = KUBOTA_DELIVERY_PROCESS_NAME
        process_updates.append('process_name')
    if process.line_id != line.id:
        process.line = line
        process_updates.append('line')
    if process_updates and not p_created:
        process.save(update_fields=process_updates)

    return line, process


# ---------------------------------------------------------------------------
# LineBacklog 同期
# ---------------------------------------------------------------------------

def _sync_kubota_delivery_backlog_for_date(target_date):
    """便割付結果をクボタ配送ラインの LineBacklog に同期する。

    plan_id 形式: KBT_T{truck_id}_{product_code}_{YYYYMMDD}_{seq}
    pickup カスケードが plan_id から truck_id を抽出し、
    arrival_day_offset ベースで前工程リードタイムを決定する。
    """
    line, process = _resolve_kubota_delivery_line_process()
    assignments = list(
        KubotaSakaiTripAssignment.objects.select_related('due_adjustment', 'truck')
        .filter(departure_date=target_date)
        .order_by('truck_id', 'due_adjustment__product_code', 'id')
    )

    # 対象日の既存 plan 行を全削除（sequence_no > 0）
    LineBacklog.objects.filter(
        line_id=line.id,
        process_id=process.id,
        plan_date=target_date,
        sequence_no__gt=0,
    ).delete()

    # Product キャッシュ
    product_codes = set(a.due_adjustment.product_code for a in assignments)
    products = {
        p.product_code: p
        for p in Product.objects.filter(product_code__in=product_codes)
    }

    seq_counter = defaultdict(int)
    to_create = []
    for assignment in assignments:
        product_code = assignment.due_adjustment.product_code
        product = products.get(product_code)
        if not product:
            continue
        qty = _to_int_qty(assignment.qty)
        if qty <= 0:
            continue
        seq_counter[product.id] += 1
        plan_id = (
            f"{KUBOTA_TRIP_PLAN_ID_PREFIX}{assignment.truck_id}"
            f"_{product_code}_{target_date:%Y%m%d}_{seq_counter[product.id]}"
        )
        to_create.append(
            LineBacklog(
                plan_date=target_date,
                process_id=process.id,
                product_id=product.id,
                line_id=line.id,
                sequence_no=seq_counter[product.id],
                plan_qty=qty,
                plan_id=plan_id,
                order_qty=0,
                demand_qty_plan=0,
            )
        )

    if to_create:
        LineBacklog.objects.bulk_create(to_create)


# ---------------------------------------------------------------------------
# plan_id から truck_id を抽出するユーティリティ（pickup カスケード用）
# ---------------------------------------------------------------------------

def parse_truck_id_from_plan_id(plan_id):
    """plan_id が 'KBT_T{truck_id}_...' 形式ならtruck_idを返す。それ以外はNone。"""
    if not plan_id or not plan_id.startswith(KUBOTA_TRIP_PLAN_ID_PREFIX):
        return None
    try:
        rest = plan_id[len(KUBOTA_TRIP_PLAN_ID_PREFIX):]
        truck_id_str = rest.split('_', 1)[0]
        return int(truck_id_str)
    except (ValueError, IndexError):
        return None


def is_kubota_delivery_line(line_obj):
    """ラインがクボタ配送ラインかどうかを判定"""
    if not line_obj:
        return False
    line_code = str(getattr(line_obj, 'line_code', '') or '').strip()
    line_name = str(getattr(line_obj, 'line_name', '') or '').strip()
    return (
        line_code in ('L3102', KUBOTA_DELIVERY_LINE_CODE)
        or 'クボタ配送' in line_name
    )


def _sync_common_shipping_tables(target_date, normalized_rows, adj_map, truck_map, user, locked_truck_ids=None):
    """堺専用割付を共通出荷テーブルへ同期する。"""
    locked_truck_ids = {int(item) for item in (locked_truck_ids or set()) if item}
    locked_trip_refs = [f'TRUCK:{truck_id}' for truck_id in sorted(locked_truck_ids)]
    due_ids = [int(row['adj_id']) for row in normalized_rows]
    if due_ids:
        delete_qs = ShippingTripAllocation.objects.filter(
            source_type=KUBOTA_COMMON_SOURCE_TYPE,
            source_id__in=due_ids,
            trip__business_type=KUBOTA_COMMON_BUSINESS_TYPE,
            trip__customer_code=KUBOTA_CUSTOMER_CODE,
            trip__departure_date=target_date,
        )
        if locked_trip_refs:
            delete_qs = delete_qs.exclude(trip__trip_ref__in=locked_trip_refs)
        delete_qs.delete()

    run_cache = {}
    trip_cache = {}
    create_allocations = []

    for row in normalized_rows:
        adj = adj_map.get(int(row['adj_id']))
        if not adj:
            continue
        ship_to_code = str(adj.ship_to_code or '')

        run_key = (
            KUBOTA_COMMON_BUSINESS_TYPE,
            KUBOTA_CUSTOMER_CODE,
            ship_to_code,
            target_date,
            target_date,
        )
        run = run_cache.get(run_key)
        if not run:
            run, _ = ShippingRun.objects.get_or_create(
                business_type=KUBOTA_COMMON_BUSINESS_TYPE,
                customer_code=KUBOTA_CUSTOMER_CODE,
                ship_to_code=ship_to_code,
                target_date_from=target_date,
                target_date_to=target_date,
                defaults={
                    'status': 'OPEN',
                    'created_by': user,
                },
            )
            run_cache[run_key] = run

        for allocation in row.get('allocations') or []:
            truck_id = int(allocation.get('truck_id') or 0)
            qty = _to_decimal(allocation.get('qty'))
            if truck_id <= 0 or qty <= 0:
                continue
            truck = truck_map.get(truck_id)
            if not truck:
                continue
            trip_ref = f"TRUCK:{truck_id}"
            trip_key = (
                KUBOTA_COMMON_BUSINESS_TYPE,
                KUBOTA_CUSTOMER_CODE,
                ship_to_code,
                target_date,
                trip_ref,
            )
            trip = trip_cache.get(trip_key)
            if not trip:
                trip, created = ShippingTrip.objects.get_or_create(
                    business_type=KUBOTA_COMMON_BUSINESS_TYPE,
                    customer_code=KUBOTA_CUSTOMER_CODE,
                    ship_to_code=ship_to_code,
                    departure_date=target_date,
                    trip_ref=trip_ref,
                    defaults={
                        'run': run,
                        'trip_code': truck.alias_name or truck.name,
                        'departure_time_plan': truck.departure_time,
                        'status': 'PLANNED',
                    },
                )
                if not created:
                    trip_updates = []
                    if trip.run_id != run.id:
                        trip.run = run
                        trip_updates.append('run')
                    next_code = truck.alias_name or truck.name
                    if (trip.trip_code or '') != (next_code or ''):
                        trip.trip_code = next_code
                        trip_updates.append('trip_code')
                    if trip.departure_time_plan != truck.departure_time:
                        trip.departure_time_plan = truck.departure_time
                        trip_updates.append('departure_time_plan')
                    if trip_updates:
                        trip.save(update_fields=trip_updates + ['updated_at'])
                trip_cache[trip_key] = trip

            create_allocations.append(
                ShippingTripAllocation(
                    trip=trip,
                    source_type=KUBOTA_COMMON_SOURCE_TYPE,
                    source_id=adj.id,
                    product_code=adj.product_code,
                    ship_to_code=adj.ship_to_code or '',
                    due_date=adj.due_date,
                    qty=qty,
                )
            )

    if create_allocations:
        ShippingTripAllocation.objects.bulk_create(create_allocations)

    # DueAdjustment 再取込で削除された元明細を参照する共通割付を掃除
    common_allocations = list(
        ShippingTripAllocation.objects.filter(
            source_type=KUBOTA_COMMON_SOURCE_TYPE,
            trip__business_type=KUBOTA_COMMON_BUSINESS_TYPE,
            trip__customer_code=KUBOTA_CUSTOMER_CODE,
            trip__departure_date=target_date,
        ).values('id', 'source_id')
    )
    existing_due_ids = set(
        KubotaSakaiDueAdjustment.objects.filter(
            id__in=[int(row['source_id']) for row in common_allocations if row.get('source_id')]
        ).values_list('id', flat=True)
    )
    orphan_allocation_ids = [
        int(row['id'])
        for row in common_allocations
        if int(row['source_id']) not in existing_due_ids
    ]
    if orphan_allocation_ids:
        ShippingTripAllocation.objects.filter(id__in=orphan_allocation_ids).delete()

    # 当日・該当業務の空便を掃除
    empty_trip_ids = list(
        ShippingTrip.objects.filter(
            business_type=KUBOTA_COMMON_BUSINESS_TYPE,
            customer_code=KUBOTA_CUSTOMER_CODE,
            departure_date=target_date,
        )
        .annotate(allocation_count=Count('allocations'))
        .filter(allocation_count=0)
        .values_list('id', flat=True)
    )
    if empty_trip_ids:
        ShippingTrip.objects.filter(id__in=empty_trip_ids).delete()


# ---------------------------------------------------------------------------
# API View
# ---------------------------------------------------------------------------

class KubotaSakaiTripDisplaySettingViewNew(APIView):
    """クボタ堺便計画の表示順・色設定を取得/保存する。"""

    def get(self, request):
        rows = list(
            KubotaSakaiTripDisplaySetting.objects.all().order_by(
                'display_order', 'product_code', 'ship_to_code', 'id'
            )
        )
        return Response({
            'rows': [
                {
                    'id': row.id,
                    'product_code': row.product_code,
                    'ship_to_code': row.ship_to_code or '',
                    'display_order': row.display_order,
                    'bg_color': row.bg_color or '',
                    'text_color': row.text_color or '',
                    'plus_bg_color': row.plus_bg_color or '',
                    'plus_text_color': row.plus_text_color or '',
                }
                for row in rows
            ],
        })

    def post(self, request):
        rows = request.data.get('rows')
        if not isinstance(rows, list):
            return Response({'detail': 'rows は配列で指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

        create_items = []
        seen = set()
        for idx, row in enumerate(rows):
            product_code = str(row.get('product_code') or '').strip()
            ship_to_code = str(row.get('ship_to_code') or '').strip()
            if not product_code:
                continue
            key = (product_code, ship_to_code)
            if key in seen:
                continue
            seen.add(key)
            create_items.append(
                KubotaSakaiTripDisplaySetting(
                    product_code=product_code,
                    ship_to_code=ship_to_code,
                    display_order=int(row.get('display_order') or idx),
                    bg_color=str(row.get('bg_color') or '').strip(),
                    text_color=str(row.get('text_color') or '').strip(),
                    plus_bg_color=str(row.get('plus_bg_color') or '').strip(),
                    plus_text_color=str(row.get('plus_text_color') or '').strip(),
                )
            )

        with transaction.atomic():
            KubotaSakaiTripDisplaySetting.objects.all().delete()
            if create_items:
                KubotaSakaiTripDisplaySetting.objects.bulk_create(create_items)

        return Response({'detail': 'ok', 'count': len(create_items)})

class KubotaSakaiTripPlanViewNew(APIView):
    """クボタ堺便計画

    GET  → grid（DueAdjustment の delivery_qty > 0 を表示）
    POST → save（TripAssignment 保存 + LineBacklog 同期）
    """

    def get(self, request):
        target_date = _parse_date(request.query_params.get('target_date')) or date.today()
        keyword = str(request.query_params.get('keyword') or '').strip()

        # DueAdjustment から対象日の納入予定を取得
        adj_qs = KubotaSakaiDueAdjustment.objects.filter(
            due_date=target_date,
            delivery_qty__gt=0,
        )
        if keyword:
            adj_qs = adj_qs.filter(Q(product_code__icontains=keyword))

        adjustments = list(adj_qs.order_by('product_code', 'ship_to_code', 'source_order_no', 'id'))
        adj_ids = [a.id for a in adjustments]

        # Product lookup
        product_codes = set(a.product_code for a in adjustments)
        products = {
            p.product_code: p
            for p in Product.objects.select_related('used_container').filter(product_code__in=product_codes)
        }

        # テーブル全体の最新調整日
        last_adjusted_at_raw = KubotaSakaiDueAdjustment.objects.aggregate(
            last=Max('updated_at')
        )['last']
        last_adjusted_at = last_adjusted_at_raw.strftime('%Y-%m-%d %H:%M') if last_adjusted_at_raw else None

        # 既存割付
        existing = KubotaSakaiTripAssignment.objects.filter(
            due_adjustment_id__in=adj_ids,
            departure_date=target_date,
        ).select_related('truck').order_by('due_adjustment_id', 'id')
        assignment_map = defaultdict(list)
        for item in existing:
            assignment_map[item.due_adjustment_id].append(item)

        # カレンダー・期限
        calendar = _resolve_kubota_calendar()
        calendar_map = _build_calendar_day_map(calendar)
        deadline_days = _get_deadline_days()
        today = date.today()
        is_holiday = not _is_working_day(target_date, calendar_map)

        ship_to_name_map = {
            s.ship_to_code: s.ship_to_name
            for s in ShipToLeadTime.objects.filter(
                customer__customer_code=KUBOTA_CUSTOMER_CODE
            )
        }

        # 製品別容器マッピング
        pc_qs = ProductContainer.objects.select_related('product', 'container').filter(
            product__product_code__in=product_codes,
        ).order_by('product__product_code', 'container__name')
        product_containers_map = defaultdict(list)
        for pc in pc_qs:
            product_containers_map[pc.product.product_code].append({
                'container_id': pc.container_id,
                'container_name': pc.container.name,
                'capacity': pc.capacity,
                'width': pc.container.width,
                'depth': pc.container.depth,
                'height': pc.container.height,
                'stackable': pc.container.stackable,
                'max_stack': pc.container.max_stack,
                'orientation': pc.container.orientation or 'free',
            })
        for product_code, product in products.items():
            container = getattr(product, 'used_container', None)
            if not container:
                continue
            _append_container_option(
                product_containers_map[product_code],
                container.id,
                container.name,
                getattr(product, 'capacity', None) or getattr(container, 'capacity', None),
                container.width,
                container.depth,
                container.height,
                container.stackable,
                container.max_stack,
                container.orientation or 'free',
            )

        # 配送進捗を取得
        progress_map = {}
        for p in KubotaSakaiDeliveryProgress.objects.filter(plan_date=target_date):
            progress_map[(p.product_code, p.ship_to_code or '')] = {
                'progress_qty': p.progress_qty,
                'adjust_qty': p.adjust_qty,
            }

        rows = []
        locked_truck_status_map = _locked_trip_map(target_date)
        locked_assignment_map = _locked_assignment_trucks_by_due(target_date, [adj.id for adj in adjustments])
        for adj in adjustments:
            product = products.get(adj.product_code)
            container = getattr(product, 'used_container', None) if product else None
            current_assignments = assignment_map.get(adj.id, [])
            assigned_qty = sum((_to_decimal(a.qty) for a in current_assignments), Decimal('0'))
            delivery_qty = _to_decimal(adj.delivery_qty)
            unassigned_qty = assigned_qty - delivery_qty
            deadline_date = _subtract_business_days(target_date, deadline_days, calendar_map)
            overdue = unassigned_qty < 0 and today > deadline_date
            progress_info = progress_map.get((adj.product_code, adj.ship_to_code or ''), {})

            rows.append({
                'due_adjustment_id': adj.id,
                'due_date': target_date.isoformat(),
                'product_code': adj.product_code,
                'product_name': product.product_name if product else '',
                'ship_to_code': adj.ship_to_code or '',
                'ship_to_name': ship_to_name_map.get(adj.ship_to_code or '', ''),
                'source_order_no': adj.source_order_no or '',
                'order_type': adj.order_type,
                'coordination_note': str(adj.coordination_note or '').strip(),
                'delivery_qty': str(delivery_qty),
                'assigned_qty': str(assigned_qty),
                'unassigned_qty': str(unassigned_qty),
                'used_container_id': container.id if container else None,
                'container_name': getattr(container, 'name', '') if container else '',
                'capacity': getattr(product, 'capacity', None) if product else None,
                'progress_qty': progress_info.get('progress_qty', 0),
                'progress_adjust_qty': progress_info.get('adjust_qty', 0),
                'overdue': overdue,
                'deadline_date': deadline_date.isoformat(),
                'is_locked': False,
                'lock_reason': '',
                'allocations': [
                    {
                        'id': a.id,
                        'truck_id': a.truck_id,
                        'truck_name': a.truck.name if a.truck_id else '',
                        'container_id': a.container_id,
                        'qty': str(a.qty),
                        'is_locked': a.truck_id in locked_assignment_map.get(adj.id, set()),
                        'lock_reason': _locked_status_label(locked_truck_status_map.get(a.truck_id)) if a.truck_id in locked_assignment_map.get(adj.id, set()) else '',
                    }
                    for a in current_assignments
                ],
            })

        # 便一覧 + 占有率サマリー
        trucks = list(KubotaSakaiTruck.objects.filter(is_active=True).order_by('display_order', 'name'))
        truck_map = {truck.id: truck for truck in trucks}
        all_today = list(
            KubotaSakaiTripAssignment.objects.select_related('due_adjustment', 'truck')
            .filter(departure_date=target_date, truck_id__in=[t.id for t in trucks])
        )
        per_truck = defaultdict(list)
        for a in all_today:
            per_truck[a.truck_id].append(a)

        truck_summaries = []
        for truck in trucks:
            load_items = []
            for a in per_truck.get(truck.id, []):
                product = products.get(a.due_adjustment.product_code)
                if product:
                    load_items.append(_build_load_item(product, a.qty))
            load = calculate_truck_load(load_items, truck)
            truck_summaries.append({
                'truck_id': truck.id,
                'truck_name': truck.alias_name or truck.name,
                'physical_truck_code': truck.physical_truck_code or '',
                'occupancy_percent': str(load['occupancy_percent']),
                'total_weight': str(load['total_weight']),
                'can_fit': load['can_fit'],
                'placed': load['placed'],
                'remaining': load['remaining'],
                'errors': load['errors'],
                'warnings': load['warnings'],
            })

        calendar = _resolve_kubota_calendar()
        calendar_map = _build_calendar_day_map(calendar)
        departure_query_end = _departure_summary_query_end(target_date, trucks)
        departure_assignments = list(
            KubotaSakaiTripAssignment.objects.select_related('due_adjustment', 'truck', 'container')
            .filter(
                due_adjustment__due_date__gte=target_date,
                due_adjustment__due_date__lte=departure_query_end,
                truck_id__in=[t.id for t in trucks],
            )
        )
        departure_product_codes = {a.due_adjustment.product_code for a in departure_assignments}
        departure_products = {
            p.product_code: p
            for p in Product.objects.select_related('used_container').filter(product_code__in=departure_product_codes)
        }
        departure_container_ids = {a.container_id for a in departure_assignments if a.container_id}
        departure_pc_map = {}
        if departure_container_ids and departure_product_codes:
            for pc in ProductContainer.objects.select_related('product').filter(
                product__product_code__in=departure_product_codes,
                container_id__in=departure_container_ids,
            ):
                departure_pc_map[(pc.product.product_code, pc.container_id)] = pc.capacity
        departure_records = []
        for assignment in departure_assignments:
            actual_departure_date = _truck_actual_departure_date(
                assignment.due_adjustment.due_date,
                assignment.truck,
                calendar_map,
            )
            if actual_departure_date != target_date:
                continue
            capacity_override = None
            if assignment.container_id:
                capacity_override = departure_pc_map.get((assignment.due_adjustment.product_code, assignment.container_id))
                if not capacity_override and assignment.container:
                    capacity_override = assignment.container.capacity
            departure_records.append({
                'actual_departure_date': actual_departure_date,
                'due_date': assignment.due_adjustment.due_date,
                'truck': assignment.truck,
                'product_code': assignment.due_adjustment.product_code,
                'qty': assignment.qty,
                'container_override': assignment.container if assignment.container_id else None,
                'capacity_override': capacity_override,
            })
        departure_summaries_by_date = _build_departure_truck_summaries(
            departure_records,
            {target_date},
            departure_products,
            truck_map,
        )
        departure_summaries_by_date = _attach_trip_notices_to_summaries(
            departure_summaries_by_date,
            {target_date},
            truck_map.keys(),
        )
        current_notice_map = {
            int(item.get('truck_id') or 0): item.get('contact_notices', [])
            for item in departure_summaries_by_date.get(target_date.isoformat(), [])
        }
        for item in truck_summaries:
            notices = current_notice_map.get(int(item.get('truck_id') or 0), [])
            item['contact_notices'] = notices
            item['has_contact_notice'] = bool(notices)

        return Response({
            'target_date': target_date.isoformat(),
            'is_holiday': is_holiday,
            'assignment_deadline_days': deadline_days,
            'last_adjusted_at': last_adjusted_at,
            'rows': rows,
            'locked_trips': [
                {
                    'truck_id': truck_id,
                    'status': status_value,
                }
                for truck_id, status_value in sorted(locked_truck_status_map.items())
            ],
            'product_containers': dict(product_containers_map),
            'trucks': [
                {
                    'id': t.id,
                    'name': t.name,
                    'alias_name': t.alias_name,
                    'physical_truck_code': t.physical_truck_code or '',
                    'default_use': t.default_use,
                    'width': t.width,
                    'depth': t.depth,
                    'height': t.height,
                    'max_weight': t.max_weight,
                    'departure_time': _format_hhmm(t.departure_time),
                    'arrival_time': _format_hhmm(t.arrival_time),
                    'arrival_day_offset': t.arrival_day_offset,
                }
                for t in trucks
            ],
            'truck_summaries': truck_summaries,
            'departure_truck_summaries': departure_summaries_by_date.get(target_date.isoformat(), []),
            'date_header_notices': _get_trip_notices(target_date, KUBOTA_DATE_HEADER_TRIP_REF),
        })

    def post(self, request):
        target_date = _parse_date(request.data.get('target_date'))
        rows = request.data.get('rows')
        if not target_date:
            return Response({'detail': 'target_date は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(rows, list):
            return Response({'detail': 'rows は配列で指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

        locked_truck_status_map = _locked_trip_map(target_date)
        locked_truck_ids = {int(item) for item in locked_truck_status_map.keys()}

        # 対象 DueAdjustment / Truck 取得
        adj_ids = []
        truck_ids = set()
        for row in rows:
            adj_id = row.get('due_adjustment_id')
            if adj_id:
                adj_ids.append(int(adj_id))
            for al in row.get('allocations') or []:
                truck_id = al.get('truck_id')
                if truck_id:
                    truck_ids.add(int(truck_id))

        adj_map = {
            a.id: a
            for a in KubotaSakaiDueAdjustment.objects.filter(
                id__in=adj_ids,
                due_date=target_date,
                delivery_qty__gt=0,
            )
        }
        truck_map = {
            t.id: t
            for t in KubotaSakaiTruck.objects.filter(id__in=list(truck_ids), is_active=True)
        }
        existing_assignments = list(
            KubotaSakaiTripAssignment.objects.filter(
                due_adjustment_id__in=list(adj_map.keys()),
                departure_date=target_date,
            )
        )
        existing_assignments_by_due = defaultdict(list)
        for item in existing_assignments:
            existing_assignments_by_due[int(item.due_adjustment_id)].append(item)

        # Product lookup（積載チェック用）
        product_codes = set(a.product_code for a in adj_map.values())
        products = {
            p.product_code: p
            for p in Product.objects.select_related('used_container').filter(product_code__in=product_codes)
        }

        errors = []
        # due_adjustment_id ごとに集約して検証・保存する
        normalized_map = {}
        for row in rows:
            adj_id = int(row.get('due_adjustment_id') or 0)
            adj = adj_map.get(adj_id)
            if not adj:
                errors.append({'due_adjustment_id': adj_id, 'detail': '対象外の納期調整データです。'})
                continue
            allocations = row.get('allocations') or []
            if not isinstance(allocations, list):
                errors.append({'due_adjustment_id': adj_id, 'detail': 'allocations は配列で指定してください。'})
                continue

            locked_existing = {
                int(item.id): item
                for item in existing_assignments_by_due.get(adj_id, [])
                if int(item.truck_id or 0) in locked_truck_ids
            }
            seen_locked_ids = set()
            normalized_allocations = []
            row_total = Decimal('0')
            for al in allocations:
                allocation_id = int(al.get('id') or 0)
                truck_id = int(al.get('truck_id') or 0)
                qty = _to_decimal(al.get('qty'))
                if qty <= 0:
                    continue
                if truck_id in locked_truck_status_map:
                    locked_assignment = locked_existing.get(allocation_id)
                    container_id = None
                    try:
                        container_id = int(al.get('container_id') or 0) or None
                    except (TypeError, ValueError):
                        pass
                    if (
                        not locked_assignment
                        or int(locked_assignment.truck_id or 0) != truck_id
                        or _to_decimal(locked_assignment.qty) != qty
                        or int(locked_assignment.container_id or 0) != int(container_id or 0)
                    ):
                        errors.append({'due_adjustment_id': adj_id, 'detail': f'出発済/完了の便は編集できません: {truck_id}'})
                        continue
                    seen_locked_ids.add(allocation_id)
                    continue
                truck = truck_map.get(truck_id)
                if not truck:
                    errors.append({'due_adjustment_id': adj_id, 'detail': f'便が不正です: {truck_id}'})
                    continue
                container_id = None
                try:
                    container_id = int(al.get('container_id') or 0) or None
                except (TypeError, ValueError):
                    pass
                normalized_allocations.append({'truck_id': truck_id, 'qty': qty, 'container_id': container_id})
                row_total += qty

            if set(locked_existing.keys()) - seen_locked_ids:
                errors.append({'due_adjustment_id': adj_id, 'detail': '出発済/完了の便に割り付いた行は削除できません。'})
                continue

            if adj_id not in normalized_map:
                normalized_map[adj_id] = {'adj_id': adj_id, 'allocations': [], 'total': Decimal('0')}
            normalized_map[adj_id]['allocations'].extend(normalized_allocations)
            normalized_map[adj_id]['total'] += row_total

        normalized = []
        for item in normalized_map.values():
            adj = adj_map.get(item['adj_id'])
            if not adj:
                # 上流で弾いているが防御的にチェック
                errors.append({'due_adjustment_id': item['adj_id'], 'detail': '対象外の納期調整データです。'})
                continue
            normalized.append({'adj_id': item['adj_id'], 'allocations': item['allocations']})

        if errors:
            return Response(
                {'detail': '入力エラーがあります。', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user if request.user and request.user.is_authenticated else None
        calendar = _resolve_kubota_calendar()
        calendar_map = _build_calendar_day_map(calendar)

        with transaction.atomic():
            # 対象行の既存割付を削除 → 再作成
            # NOTE:
            # 過去実装や便変更の影響で同一 due_adjustment に別日付の割付が残ると、
            # 同じ明細が二重計上されるため departure_date で絞らず全削除する。
            delete_qs = KubotaSakaiTripAssignment.objects.filter(
                due_adjustment_id__in=[n['adj_id'] for n in normalized],
                departure_date=target_date,
            )
            if locked_truck_ids:
                delete_qs = delete_qs.exclude(truck_id__in=list(locked_truck_ids))
            delete_qs.delete()

            create_items = []
            for row in normalized:
                for al in row['allocations']:
                    create_items.append(
                        KubotaSakaiTripAssignment(
                            due_adjustment_id=row['adj_id'],
                            truck_id=al['truck_id'],
                            container_id=al.get('container_id'),
                            departure_date=target_date,
                            qty=al['qty'],
                            created_by=user,
                        )
                    )
            if create_items:
                KubotaSakaiTripAssignment.objects.bulk_create(create_items)

            # 積載チェック（実出発日 + 同一車両キー単位で判定）
            affected_departure_dates = set()
            for row in normalized:
                for al in row['allocations']:
                    truck = truck_map.get(al['truck_id'])
                    if truck:
                        affected_departure_dates.add(_truck_actual_departure_date(target_date, truck, calendar_map))

            validation_query_end = _departure_summary_query_end(
                max(affected_departure_dates) if affected_departure_dates else target_date,
                truck_map.values(),
            )
            surrounding_assignments = list(
                KubotaSakaiTripAssignment.objects.select_related('due_adjustment', 'truck', 'container')
                .filter(
                    due_adjustment__due_date__gte=min(affected_departure_dates) if affected_departure_dates else target_date,
                    due_adjustment__due_date__lte=validation_query_end,
                )
            )
            validation_product_codes = set(product_codes)
            validation_product_codes.update(
                item.due_adjustment.product_code
                for item in surrounding_assignments
                if item.due_adjustment_id
            )
            validation_products = {
                p.product_code: p
                for p in Product.objects.select_related('used_container').filter(product_code__in=validation_product_codes)
            }

            # 保存済み container_id → ProductContainer 入数マップ
            saved_container_ids = {item.container_id for item in surrounding_assignments if item.container_id}
            new_container_ids = {
                al.get('container_id')
                for row in normalized
                for al in row['allocations']
                if al.get('container_id')
            }
            saved_container_ids.update(new_container_ids)
            saved_pc_map = {}
            if saved_container_ids:
                for pc in ProductContainer.objects.select_related('product').filter(
                    product__product_code__in=validation_product_codes,
                    container_id__in=saved_container_ids,
                ):
                    saved_pc_map[(pc.product.product_code, pc.container_id)] = pc.capacity
            container_map = {}
            if saved_container_ids:
                container_map = {c.id: c for c in ContainerCapacity.objects.filter(id__in=saved_container_ids)}

            validation_records = []
            for item in surrounding_assignments:
                capacity_override = None
                if item.container_id:
                    capacity_override = saved_pc_map.get((item.due_adjustment.product_code, item.container_id))
                    if not capacity_override and item.container:
                        capacity_override = item.container.capacity
                validation_records.append({
                    'actual_departure_date': _truck_actual_departure_date(
                        item.due_adjustment.due_date,
                        item.truck,
                        calendar_map,
                    ),
                    'truck': item.truck,
                    'product_code': item.due_adjustment.product_code,
                    'qty': item.qty,
                    'container_override': item.container if item.container_id else None,
                    'capacity_override': capacity_override,
                })

            save_errors = []
            per_group = defaultdict(list)
            for record in validation_records:
                actual_departure_date = record['actual_departure_date']
                if actual_departure_date not in affected_departure_dates:
                    continue
                group_key = (actual_departure_date, _physical_truck_key(record['truck']))
                per_group[group_key].append(record)

            for group_key, items in per_group.items():
                actual_departure_date, physical_truck_code = group_key
                truck = items[0]['truck']
                load_items = []
                for item in items:
                    product = validation_products.get(item['product_code'])
                    if product:
                        load_items.append(
                            _build_load_item(
                                product,
                                item['qty'],
                                item.get('container_override'),
                                item.get('capacity_override'),
                            )
                        )
                load = calculate_truck_load(load_items, truck)
                if load['errors']:
                    save_errors.append({
                        'truck_id': truck.id,
                        'truck_name': truck.alias_name or truck.name,
                        'physical_truck_code': physical_truck_code,
                        'actual_departure_date': actual_departure_date.isoformat(),
                        'errors': load['errors'],
                    })

            if save_errors:
                transaction.set_rollback(True)
                return Response(
                    {'detail': '便積載制約エラーがあります。', 'errors': save_errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 共通出荷テーブルへ同時保存（堺専用と同一トランザクション）
            _sync_common_shipping_tables(
                target_date=target_date,
                normalized_rows=normalized,
                adj_map=adj_map,
                truck_map=truck_map,
                user=user,
                locked_truck_ids=locked_truck_ids,
            )

            # LineBacklog 同期（LinePlan不使用、LineBacklog直接保存）
            _sync_kubota_delivery_backlog_for_date(target_date)

        # 配送進捗再計算（target_date 以降）
        max_due_date = (
            KubotaSakaiDueAdjustment.objects.aggregate(
                max_date=Max('due_date')
            )['max_date'] or target_date
        )
        recalculate_delivery_progress(target_date, max(target_date, max_due_date))

        return Response({
            'saved_rows': len(normalized),
            'saved_allocations': len(create_items),
        })


class KubotaSakaiTripImportViewNew(APIView):
    """クボタ堺便計画 取込

    納期調整の保存結果を読み取り対象として確認し、便計画表示の再読込に使う。
    """

    def post(self, request):
        start_date = _parse_date(request.data.get('start_date')) or date.today()
        horizon_days = int(request.data.get('horizon_days') or 14)
        if horizon_days < 1:
            horizon_days = 1
        if horizon_days > 180:
            horizon_days = 180
        end_date = start_date + timedelta(days=horizon_days - 1)

        row_qs = KubotaSakaiDueAdjustment.objects.filter(
            due_date__range=(start_date, end_date),
            delivery_qty__gt=0,
        )
        return Response({
            'detail': '納期調整の保存結果を読み取りました。',
            'target_date_from': start_date.isoformat(),
            'target_date_to': end_date.isoformat(),
            'total_rows': row_qs.count(),
            'total_days': row_qs.values('due_date').distinct().count(),
        })


class KubotaSakaiTripLoadPreviewViewNew(APIView):
    """未保存の便割付入力を使って便占有率を試算する。"""

    def post(self, request):
        target_date = _parse_date(request.data.get('target_date'))
        rows = request.data.get('rows')
        if not target_date:
            return Response({'detail': 'target_date は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(rows, list):
            return Response({'detail': 'rows は配列で指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

        preview_rows_by_date = {target_date: rows}
        raw_preview_rows_by_date = request.data.get('preview_rows_by_date')
        if raw_preview_rows_by_date is not None:
            if not isinstance(raw_preview_rows_by_date, dict):
                return Response({'detail': 'preview_rows_by_date は日付をキーとするオブジェクトで指定してください。'}, status=status.HTTP_400_BAD_REQUEST)
            preview_rows_by_date = {}
            for raw_date, preview_rows in raw_preview_rows_by_date.items():
                preview_date = _parse_date(raw_date)
                if not preview_date or not isinstance(preview_rows, list):
                    return Response({'detail': 'preview_rows_by_date の日付またはrowsが不正です。'}, status=status.HTTP_400_BAD_REQUEST)
                preview_rows_by_date[preview_date] = preview_rows
            # target_date の入力値は常に rows を正として扱う。
            preview_rows_by_date[target_date] = rows

        preview_due_adjustments = list(
            KubotaSakaiDueAdjustment.objects.filter(
                due_date__in=preview_rows_by_date.keys(),
                delivery_qty__gt=0,
            ).order_by('id')
        )
        due_adjustments = [item for item in preview_due_adjustments if item.due_date == target_date]
        preview_due_adjustments_by_date = defaultdict(dict)
        preview_due_adjustment_map = {}
        for item in preview_due_adjustments:
            preview_due_adjustments_by_date[item.due_date][item.id] = item
            preview_due_adjustment_map[item.id] = item

        posted_preview_alloc_maps = {}
        errors = []
        for preview_date, preview_rows in preview_rows_by_date.items():
            posted_alloc_map_for_date = {}
            preview_due_adjustment_map_for_date = preview_due_adjustments_by_date[preview_date]
            for row in preview_rows:
                try:
                    due_adjustment_id = int(row.get('due_adjustment_id') or 0)
                except (TypeError, ValueError):
                    due_adjustment_id = 0
                if due_adjustment_id <= 0:
                    continue
                if due_adjustment_id not in preview_due_adjustment_map_for_date:
                    errors.append({'due_adjustment_id': due_adjustment_id, 'detail': '対象外の納期調整データです。'})
                    continue

                allocations = row.get('allocations') or []
                if not isinstance(allocations, list):
                    errors.append({'due_adjustment_id': due_adjustment_id, 'detail': 'allocations は配列で指定してください。'})
                    continue

                normalized_allocations = []
                for item in allocations:
                    try:
                        truck_id = int(item.get('truck_id') or 0)
                    except (TypeError, ValueError):
                        truck_id = 0
                    qty = _to_decimal(item.get('qty'))
                    if truck_id <= 0 or qty <= 0:
                        continue
                    container_id = None
                    try:
                        container_id = int(item.get('container_id') or 0) or None
                    except (TypeError, ValueError):
                        pass
                    normalized_allocations.append({'truck_id': truck_id, 'qty': qty, 'container_id': container_id})
                posted_alloc_map_for_date[due_adjustment_id] = normalized_allocations
            posted_preview_alloc_maps[preview_date] = posted_alloc_map_for_date

        if errors:
            return Response({'detail': '入力エラーがあります。', 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        posted_alloc_map = posted_preview_alloc_maps.get(target_date, {})
        preview_due_adjustment_ids = {
            due_adjustment_id
            for posted_alloc_map_for_date in posted_preview_alloc_maps.values()
            for due_adjustment_id in posted_alloc_map_for_date
        }

        preview_existing_assignments = list(
            KubotaSakaiTripAssignment.objects.select_related('due_adjustment', 'truck', 'container')
            .filter(due_adjustment_id__in=preview_due_adjustment_ids)
            .order_by('id')
        )
        existing_map = defaultdict(list)
        for item in preview_existing_assignments:
            if item.due_adjustment.due_date != target_date or item.departure_date != target_date:
                continue
            existing_map[item.due_adjustment_id].append({'truck_id': item.truck_id, 'qty': _to_decimal(item.qty)})

        trucks = list(KubotaSakaiTruck.objects.filter(is_active=True).order_by('display_order', 'name'))
        truck_map = {truck.id: truck for truck in trucks}
        calendar = _resolve_kubota_calendar()
        calendar_map = _build_calendar_day_map(calendar)

        product_codes = set(item.product_code for item in due_adjustments)
        products = {
            product.product_code: product
            for product in Product.objects.select_related('used_container').filter(product_code__in=product_codes)
        }

        all_container_ids = set()
        for allocs in posted_alloc_map.values():
            for al in allocs:
                if al.get('container_id'):
                    all_container_ids.add(al['container_id'])
        container_map = {}
        if all_container_ids:
            container_map = {c.id: c for c in ContainerCapacity.objects.filter(id__in=all_container_ids)}
        pc_capacity_map = {}
        if all_container_ids:
            for pc in ProductContainer.objects.select_related('product').filter(
                product__product_code__in=product_codes,
                container_id__in=all_container_ids,
            ):
                pc_capacity_map[(pc.product.product_code, pc.container_id)] = pc.capacity

        per_truck_load_items = defaultdict(list)
        per_truck_errors = defaultdict(list)

        for due_adjustment in due_adjustments:
            product = products.get(due_adjustment.product_code)
            allocations = posted_alloc_map.get(due_adjustment.id, existing_map.get(due_adjustment.id, []))
            for allocation in allocations:
                truck = truck_map.get(allocation['truck_id'])
                if not truck or not product:
                    continue
                container_override = None
                capacity_override = None
                cid = allocation.get('container_id')
                if cid and cid in container_map:
                    container_override = container_map[cid]
                    capacity_override = pc_capacity_map.get((due_adjustment.product_code, cid))
                    if not capacity_override:
                        capacity_override = container_override.capacity
                try:
                    per_truck_load_items[truck.id].append(
                        _build_load_item(product, allocation['qty'], container_override, capacity_override)
                    )
                except Exception:
                    logger.exception(
                        '便占有率プレビュー用積載データ生成に失敗しました: due_adjustment_id=%s truck_id=%s',
                        due_adjustment.id,
                        getattr(truck, 'id', None),
                    )
                    per_truck_errors[truck.id].append(f'{due_adjustment.product_code}: 積載データ生成失敗')

        summaries = []
        for truck in trucks:
            try:
                load = calculate_truck_load(per_truck_load_items.get(truck.id, []), truck)
            except Exception:
                logger.exception('便占有率プレビュー計算に失敗しました: truck_id=%s', truck.id)
                load = {
                    'can_fit': False,
                    'occupancy_percent': Decimal('0'),
                    'total_weight': Decimal('0'),
                    'placed': [],
                    'remaining': [],
                    'errors': ['積載計算に失敗しました。'],
                    'warnings': [],
                }
            load_errors = list(per_truck_errors.get(truck.id, [])) + list(load.get('errors') or [])
            summaries.append({
                'truck_id': truck.id,
                'truck_name': truck.alias_name or truck.name,
                'physical_truck_code': truck.physical_truck_code or '',
                'occupancy_percent': str(load['occupancy_percent']),
                'total_weight': str(load['total_weight']),
                'can_fit': load.get('can_fit', False),
                'placed': load.get('placed', []),
                'remaining': load.get('remaining', []),
                'errors': load_errors,
                'warnings': list(load.get('warnings') or []),
            })

        affected_departure_dates = set()
        for preview_date, posted_alloc_map_for_date in posted_preview_alloc_maps.items():
            for allocations in posted_alloc_map_for_date.values():
                for allocation in allocations:
                    truck = truck_map.get(allocation['truck_id'])
                    if truck:
                        affected_departure_dates.add(_truck_actual_departure_date(preview_date, truck, calendar_map))
        for item in preview_existing_assignments:
            truck = truck_map.get(item.truck_id)
            if truck:
                affected_departure_dates.add(
                    _truck_actual_departure_date(item.due_adjustment.due_date, truck, calendar_map)
                )

        departure_summaries_by_date = {}
        if affected_departure_dates:
            departure_query_end = _departure_summary_query_end(max(affected_departure_dates), trucks)
            surrounding_assignments = list(
                KubotaSakaiTripAssignment.objects.select_related('due_adjustment', 'truck', 'container')
                .filter(
                    due_adjustment__due_date__gte=min(affected_departure_dates),
                    due_adjustment__due_date__lte=departure_query_end,
                )
                .exclude(due_adjustment_id__in=preview_due_adjustment_ids)
            )

            departure_product_codes = {
                due_adjustment.product_code
                for due_adjustment_id, due_adjustment in preview_due_adjustment_map.items()
                if due_adjustment_id in preview_due_adjustment_ids
            }
            departure_product_codes.update(item.due_adjustment.product_code for item in surrounding_assignments)
            departure_products = {
                p.product_code: p
                for p in Product.objects.select_related('used_container').filter(product_code__in=departure_product_codes)
            }

            departure_container_ids = {item.container_id for item in surrounding_assignments if item.container_id}
            for posted_alloc_map_for_date in posted_preview_alloc_maps.values():
                for allocations in posted_alloc_map_for_date.values():
                    for allocation in allocations:
                        if allocation.get('container_id'):
                            departure_container_ids.add(allocation['container_id'])
            departure_container_map = {}
            if departure_container_ids:
                departure_container_map = {
                    c.id: c for c in ContainerCapacity.objects.filter(id__in=departure_container_ids)
                }
            departure_pc_map = {}
            if departure_container_ids and departure_product_codes:
                for pc in ProductContainer.objects.select_related('product').filter(
                    product__product_code__in=departure_product_codes,
                    container_id__in=departure_container_ids,
                ):
                    departure_pc_map[(pc.product.product_code, pc.container_id)] = pc.capacity

            departure_records = []
            for item in surrounding_assignments:
                capacity_override = None
                if item.container_id:
                    capacity_override = departure_pc_map.get((item.due_adjustment.product_code, item.container_id))
                    if not capacity_override and item.container:
                        capacity_override = item.container.capacity
                departure_records.append({
                    'actual_departure_date': _truck_actual_departure_date(
                        item.due_adjustment.due_date,
                        item.truck,
                        calendar_map,
                    ),
                    'due_date': item.due_adjustment.due_date,
                    'truck': item.truck,
                    'product_code': item.due_adjustment.product_code,
                    'qty': item.qty,
                    'container_override': item.container if item.container_id else None,
                    'capacity_override': capacity_override,
                })

            for posted_alloc_map_for_date in posted_preview_alloc_maps.values():
                for due_adjustment_id, allocations in posted_alloc_map_for_date.items():
                    due_adjustment = preview_due_adjustment_map[due_adjustment_id]
                    for allocation in allocations:
                        truck = truck_map.get(allocation['truck_id'])
                        if not truck:
                            continue
                        container_override = None
                        capacity_override = None
                        cid = allocation.get('container_id')
                        if cid and cid in departure_container_map:
                            container_override = departure_container_map[cid]
                            capacity_override = departure_pc_map.get((due_adjustment.product_code, cid))
                            if not capacity_override:
                                capacity_override = container_override.capacity
                        departure_records.append({
                            'actual_departure_date': _truck_actual_departure_date(
                                due_adjustment.due_date,
                                truck,
                                calendar_map,
                            ),
                            'due_date': due_adjustment.due_date,
                            'truck': truck,
                            'product_code': due_adjustment.product_code,
                            'qty': allocation['qty'],
                            'container_override': container_override,
                            'capacity_override': capacity_override,
                        })

            departure_summaries_by_date = _build_departure_truck_summaries(
                departure_records,
                affected_departure_dates,
                departure_products,
                truck_map,
            )
            departure_summaries_by_date = _attach_trip_notices_to_summaries(
                departure_summaries_by_date,
                affected_departure_dates,
                truck_map.keys(),
            )

        current_notice_map = {
            int(item.get('truck_id') or 0): item.get('contact_notices', [])
            for item in departure_summaries_by_date.get(target_date.isoformat(), [])
        }
        for item in summaries:
            notices = current_notice_map.get(int(item.get('truck_id') or 0), [])
            item['contact_notices'] = notices
            item['has_contact_notice'] = bool(notices)

        return Response({
            'target_date': target_date.isoformat(),
            'truck_summaries': summaries,
            'departure_truck_summaries_by_date': departure_summaries_by_date,
        })


class KubotaSakaiTripNoticeViewNew(APIView):
    """便ごとの事務所連絡メモを取得/保存する。"""

    def get(self, request):
        target_date = _parse_date(request.query_params.get('target_date'))
        truck_id = int(request.query_params.get('truck_id') or 0)
        trip_ref = str(request.query_params.get('trip_ref') or '').strip()
        if not target_date:
            return Response({'detail': 'target_date は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        if truck_id <= 0 and not trip_ref:
            return Response({'detail': 'truck_id または trip_ref は必須です。'}, status=status.HTTP_400_BAD_REQUEST)

        resolved_trip_ref = trip_ref or f'TRUCK:{truck_id}'
        notices = _get_trip_notices(target_date, resolved_trip_ref)
        return Response({
            'target_date': target_date.isoformat(),
            'truck_id': truck_id if truck_id > 0 else None,
            'trip_ref': resolved_trip_ref,
            'notices': notices,
        })

    def post(self, request):
        target_date = _parse_date(request.data.get('target_date'))
        truck_id = int(request.data.get('truck_id') or 0)
        trip_ref = str(request.data.get('trip_ref') or '').strip()
        notice_text = str(request.data.get('notice_text') or '').strip()
        notice_type = _normalize_trip_notice_type(request.data.get('notice_type'))
        if not target_date:
            return Response({'detail': 'target_date は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        if truck_id <= 0 and not trip_ref:
            return Response({'detail': 'truck_id または trip_ref は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        if len(notice_text) > 200:
            return Response({'detail': '連絡メモは200文字以内で入力してください。'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user if getattr(request.user, 'is_authenticated', False) else None
        resolved_trip_ref = trip_ref or f'TRUCK:{truck_id}'
        try:
            ShippingTripNotice.objects.exists()
        except ProgrammingError:
            return Response(
                {'detail': '連絡メモテーブルが未作成です。先に migration を実行してください。'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if notice_text:
            obj, _ = ShippingTripNotice.objects.get_or_create(
                business_type=KUBOTA_COMMON_BUSINESS_TYPE,
                customer_code=KUBOTA_CUSTOMER_CODE,
                departure_date=target_date,
                trip_ref=resolved_trip_ref,
                notice_type=notice_type,
                defaults={'notice_text': notice_text, 'updated_by': user},
            )
            update_fields = []
            if obj.notice_text != notice_text:
                obj.notice_text = notice_text
                update_fields.append('notice_text')
            if obj.updated_by_id != getattr(user, 'id', None):
                obj.updated_by = user
                update_fields.append('updated_by')
            if update_fields:
                obj.save(update_fields=update_fields + ['updated_at'])
        else:
            ShippingTripNotice.objects.filter(
                business_type=KUBOTA_COMMON_BUSINESS_TYPE,
                customer_code=KUBOTA_CUSTOMER_CODE,
                departure_date=target_date,
                trip_ref=resolved_trip_ref,
                notice_type=notice_type,
            ).delete()

        notices = _get_trip_notices(target_date, resolved_trip_ref)
        return Response({
            'target_date': target_date.isoformat(),
            'truck_id': truck_id if truck_id > 0 else None,
            'trip_ref': resolved_trip_ref,
            'notices': notices,
        })


class KubotaSakaiTripLoadDetailViewNew(APIView):
    """便ごとの占有計算明細を返す（CSV出力用）。"""

    def get(self, request):
        target_date = _parse_date(request.query_params.get('target_date'))
        if not target_date:
            return Response({'detail': 'target_date は必須です。'}, status=status.HTTP_400_BAD_REQUEST)

        assignments = list(
            KubotaSakaiTripAssignment.objects.select_related('due_adjustment', 'truck', 'container')
            .filter(departure_date=target_date)
            .order_by('truck__display_order', 'truck__name', 'id')
        )
        if not assignments:
            return Response({'target_date': target_date.isoformat(), 'rows': []})

        product_codes = {a.due_adjustment.product_code for a in assignments}
        products = {
            p.product_code: p
            for p in Product.objects.select_related('used_container').filter(product_code__in=product_codes)
        }

        # 割付に保存された container_id → ProductContainer 入数
        saved_cids = {a.container_id for a in assignments if a.container_id}
        ld_pc_map = {}
        if saved_cids:
            for pc in ProductContainer.objects.select_related('product').filter(
                product__product_code__in=product_codes,
                container_id__in=saved_cids,
            ):
                ld_pc_map[(pc.product.product_code, pc.container_id)] = pc.capacity

        grouped = {}
        for assignment in assignments:
            key = (assignment.truck_id, assignment.due_adjustment.product_code)
            if key not in grouped:
                grouped[key] = {
                    'truck': assignment.truck,
                    'product_code': assignment.due_adjustment.product_code,
                    'qty': Decimal('0'),
                    'container_override': None,
                }
            grouped[key]['qty'] += _to_decimal(assignment.qty)
            if assignment.container_id:
                grouped[key]['container_override'] = assignment.container

        rows = []
        for item in grouped.values():
            truck = item['truck']
            product_code = item['product_code']
            qty = item['qty']
            product = products.get(product_code)
            c_override = item.get('container_override')
            container = c_override or (getattr(product, 'used_container', None) if product else None)

            if c_override:
                capacity = ld_pc_map.get((product_code, c_override.id)) or getattr(c_override, 'capacity', None)
            else:
                capacity = getattr(product, 'capacity', None) if product else None
                if not capacity and container:
                    capacity = container.capacity
            if not capacity:
                capacity = 1
            capacity = max(int(_to_decimal(capacity)), 1)

            cap_override = ld_pc_map.get((product_code, c_override.id)) if c_override else None
            load_item = _build_load_item(product, qty, c_override, cap_override)
            used_area = _calculate_assignment_area(load_item, truck)
            truck_area = _to_decimal(truck.width) * _to_decimal(truck.depth)
            occupancy_percent = Decimal('0')
            if truck_area > 0:
                occupancy_percent = ((used_area / truck_area) * Decimal('100')).quantize(Decimal('0.01'))

            rows.append({
                'truck_id': truck.id,
                'truck_name': truck.name,
                'truck_alias_name': truck.alias_name or '',
                'truck_label': truck.alias_name or truck.name,
                'truck_area': str(truck_area.quantize(Decimal('1'))),
                'product_code': product_code,
                'qty': str(qty.quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
                'container_name': getattr(container, 'name', '') if container else '',
                'container_width': int(getattr(container, 'width', 0) or 0),
                'container_depth': int(getattr(container, 'depth', 0) or 0),
                'container_height': int(getattr(container, 'height', 0) or 0),
                'container_size': (
                    f"{int(getattr(container, 'width', 0) or 0)}x"
                    f"{int(getattr(container, 'depth', 0) or 0)}x"
                    f"{int(getattr(container, 'height', 0) or 0)}"
                ) if container else '-',
                'capacity': capacity,
                'container_count': str((qty / Decimal(str(capacity))).to_integral_value(rounding=ROUND_CEILING)),
                'used_container_area': str(used_area.quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
                'occupancy_percent': str(occupancy_percent),
            })

        rows.sort(key=lambda r: (r['truck_label'], r['product_code']))
        return Response({'target_date': target_date.isoformat(), 'rows': rows})


class KubotaSakaiPickupDetailPdfViewNew(APIView):
    """出発日別の集荷明細表PDFを返す。"""

    def get(self, request):
        start_date = _parse_date(request.query_params.get('start_date'))
        end_date = _parse_date(request.query_params.get('end_date'))
        if not start_date or not end_date:
            return Response({'detail': 'start_date と end_date は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        if start_date > end_date:
            return Response({'detail': '開始日は終了日以前を指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

        # kubota_sakai カレンダで営業日逆算（offset>=1）
        calendar = _resolve_kubota_calendar()
        calendar_map = _build_calendar_day_map(calendar)

        max_offset = KubotaSakaiTruck.objects.filter(is_active=True).order_by('-arrival_day_offset').values_list('arrival_day_offset', flat=True).first() or 0
        buffer_days = max(14, int(max_offset) * 3 + 7)
        due_end = end_date + timedelta(days=buffer_days)

        assignments = list(
            KubotaSakaiTripAssignment.objects.select_related('due_adjustment', 'truck')
            .filter(
                due_adjustment__due_date__gte=start_date,
                due_adjustment__due_date__lte=due_end,
                qty__gt=0,
            )
            .order_by('due_adjustment__due_date', 'truck__display_order', 'truck__name', 'id')
        )

        product_codes = {a.due_adjustment.product_code for a in assignments}
        ship_to_codes = {
            (a.due_adjustment.ship_to_code or '').strip()
            for a in assignments
            if (a.due_adjustment.ship_to_code or '').strip()
        }
        products = {
            p.product_code: p
            for p in Product.objects.select_related('used_container').filter(product_code__in=product_codes)
        }
        ship_to_name_map = {
            row.ship_to_code: row.ship_to_name
            for row in ShipToLeadTime.objects.filter(
                customer__customer_code=KUBOTA_CUSTOMER_CODE,
                ship_to_code__in=ship_to_codes,
            )
        }

        # 割付ごとの容器IDマップ（container_id が設定されている場合のみ）
        assignment_container_map = {}
        for item in assignments:
            if item.container_id:
                assignment_container_map[item.id] = item.container_id

        # ProductContainer 入数マップ
        all_container_ids = set(assignment_container_map.values())
        container_objs = {}
        pc_capacity_map = {}
        if all_container_ids:
            container_objs = {c.id: c for c in ContainerCapacity.objects.filter(id__in=all_container_ids)}
            for pc in ProductContainer.objects.select_related('product').filter(
                product__product_code__in=product_codes,
                container_id__in=all_container_ids,
            ):
                pc_capacity_map[(pc.product.product_code, pc.container_id)] = pc.capacity

        # departure_date -> truck_id -> (product_code, ship_to_code, source_order_no) で集計
        grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(Decimal)))
        # 容器別入数を保持: detail_key -> container_id
        detail_container_map = {}
        truck_meta = {}
        for item in assignments:
            truck = item.truck
            if not truck:
                continue
            offset_days = max(int(truck.arrival_day_offset or 0), 0)
            due_date = item.due_adjustment.due_date
            departure_date = _subtract_business_days(due_date, offset_days, calendar_map)
            if departure_date < start_date or departure_date > end_date:
                continue
            detail_key = (
                item.due_adjustment.product_code,
                (item.due_adjustment.ship_to_code or '').strip(),
                (item.due_adjustment.source_order_no or '').strip(),
            )
            grouped[departure_date][truck.id][detail_key] += _to_decimal(item.qty)
            if item.container_id:
                detail_container_map[(departure_date, truck.id, detail_key)] = item.container_id
            if truck.id not in truck_meta:
                truck_meta[truck.id] = {
                    'name': truck.name,
                    'alias_name': truck.alias_name or '',
                    'display_order': truck.display_order or 0,
                    'departure_time': _format_hhmm(truck.departure_time),
                    'arrival_day_offset': int(truck.arrival_day_offset or 0),
                }

        vendor_notice_map = {}
        vendor_rows = ShippingTripNotice.objects.filter(
            business_type=KUBOTA_COMMON_BUSINESS_TYPE,
            customer_code=KUBOTA_CUSTOMER_CODE,
            departure_date__gte=start_date,
            departure_date__lte=end_date,
            notice_type=TRIP_NOTICE_TYPE_VENDOR,
        )
        for row in vendor_rows:
            text = (row.notice_text or '').strip()
            if text:
                trip_ref = (row.trip_ref or '').strip()
                vendor_notice_map[(row.departure_date, trip_ref)] = text

        pdf_bytes = self._render_pdf(
            start_date,
            end_date,
            grouped,
            truck_meta,
            products,
            ship_to_name_map,
            detail_container_map=detail_container_map,
            pc_capacity_map=pc_capacity_map,
            container_objs=container_objs,
            vendor_notice_map=vendor_notice_map,
            calendar_map=calendar_map,
        )
        filename = f"クボタ堺_集荷明細表_{start_date:%Y%m%d}_{end_date:%Y%m%d}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def _render_pdf(self, start_date, end_date, grouped, truck_meta, products, ship_to_name_map,
                    detail_container_map=None, pc_capacity_map=None, container_objs=None,
                    vendor_notice_map=None, calendar_map=None):
        try:
            pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
        except Exception:
            pass

        font_name = 'HeiseiKakuGo-W5'
        font_size = 9
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        width, height = A4
        left = 12 * mm
        right = width - 12 * mm
        top = height - 12 * mm
        line_h = 5.6 * mm
        table_left = left + 4 * mm
        table_right = right - 1 * mm

        def draw_header(page_no):
            c.setFont(font_name, 14)
            c.drawString(left, top, 'クボタ堺 集荷明細表（出発日別）')
            c.setFont(font_name, font_size)
            c.drawString(left, top - 6.5 * mm, f'対象期間: {start_date:%Y-%m-%d} ～ {end_date:%Y-%m-%d}')
            c.drawRightString(right, top - 6.5 * mm, f'Page {page_no}')

        def draw_line(y_pos, width=1.0, dashed=False):
            c.saveState()
            c.setLineWidth(width)
            if dashed:
                c.setDash(1.5, 2.5)
            c.line(table_left, y_pos, table_right, y_pos)
            c.restoreState()

        def draw_double_line(y_pos, width=1.2, gap=1.2 * mm):
            c.saveState()
            c.setLineWidth(width)
            c.line(left, y_pos, table_right, y_pos)
            c.line(left, y_pos - gap, table_right, y_pos - gap)
            c.restoreState()

        def draw_departure_title(dep_date, continuation=False):
            c.setFont(font_name, 11)
            suffix = ' (続き)' if continuation else ''
            c.drawString(left, y, f'出発日: {dep_date:%Y-%m-%d}{suffix}')

        def draw_truck_title(truck_text, dep_time, arrival_date=None):
            c.setFont(font_name, 10)
            c.drawString(left + 2 * mm, y, f'便: {truck_text}')
            if dep_time:
                c.drawString(left + 34 * mm, y, f'出発時刻：{dep_time}')
            if arrival_date:
                c.drawString(left + 80 * mm, y, f'到着日：{arrival_date:%Y-%m-%d}')

        def draw_columns():
            c.setFont(font_name, font_size)
            c.drawString(left + 8 * mm, y, '品番')
            c.drawString(left + 39 * mm, y, '品名')
            c.drawString(left + 83 * mm, y, '納入地')
            c.drawString(left + 128 * mm, y, '注番')
            c.drawRightString(left + 162 * mm, y, '容器数')
            c.drawRightString(left + 180 * mm, y, '数量')

        def clip_text_to_width(text, max_width_mm):
            text = str(text or '')
            max_width = max_width_mm * mm
            if pdfmetrics.stringWidth(text, font_name, font_size) <= max_width:
                return text

            clipped = ''
            for ch in text:
                candidate = clipped + ch
                if pdfmetrics.stringWidth(candidate, font_name, font_size) > max_width:
                    break
                clipped = candidate
            return clipped

        # ヘッダ（対象期間）と最初の出発日の間を2行ぶん空ける
        y = top - 14 * mm - (line_h * 2)
        page_no = 1
        draw_header(page_no)

        departure_dates = sorted(grouped.keys())
        if not departure_dates:
            c.setFont(font_name, 11)
            c.drawString(left, y - 6 * mm, '対象データがありません。')
            c.save()
            buf.seek(0)
            return buf.read()

        for dep_idx, dep in enumerate(departure_dates):
            if dep_idx > 0:
                # 出荷日ごとに新しいページを開始（1日1ページ）
                c.showPage()
                page_no += 1
                draw_header(page_no)
                y = top - 14 * mm - (line_h * 2)

            draw_departure_title(dep)
            y -= line_h

            truck_ids = sorted(
                grouped[dep].keys(),
                key=lambda tid: (
                    int((truck_meta.get(tid) or {}).get('display_order') or 0),
                    str((truck_meta.get(tid) or {}).get('alias_name') or (truck_meta.get(tid) or {}).get('name') or ''),
                    int(tid),
                ),
            )
            for truck_idx, truck_id in enumerate(truck_ids):
                if y < 20 * mm:
                    c.showPage()
                    page_no += 1
                    draw_header(page_no)
                    y = top - 14 * mm - (line_h * 2)
                    draw_departure_title(dep, continuation=True)
                    y -= line_h
                if truck_idx > 0:
                    draw_line(y + 1.6 * mm, width=1.1, dashed=False)
                    y -= 1.8 * mm

                meta = truck_meta.get(truck_id) or {}
                truck_label = (meta.get('alias_name') or '').strip() or (meta.get('name') or f'便{truck_id}')
                departure_time = meta.get('departure_time') or ''
                arrival_offset = meta.get('arrival_day_offset', 0)
                arrival_date = _add_business_days(dep, arrival_offset, calendar_map or {}) if arrival_offset else dep
                draw_truck_title(truck_label, departure_time, arrival_date)
                y -= line_h

                draw_columns()
                y -= line_h

                detail_keys = sorted(
                    grouped[dep][truck_id].keys(),
                    key=lambda key: (key[0], key[1], key[2]),
                )
                for detail_idx, detail_key in enumerate(detail_keys):
                    if y < 16 * mm:
                        c.showPage()
                        page_no += 1
                        draw_header(page_no)
                        y = top - 14 * mm - (line_h * 2)
                        draw_departure_title(dep, continuation=True)
                        y -= line_h
                        draw_truck_title(truck_label, departure_time, arrival_date)
                        y -= line_h
                        draw_columns()
                        y -= line_h
                    product_code, ship_to_code, source_order_no = detail_key
                    qty = grouped[dep][truck_id][detail_key]
                    product = products.get(product_code)
                    name = (product.product_name if product else '') or ''
                    # 割付に保存された容器の入数を優先
                    capacity_val = Decimal('0')
                    saved_cid = (detail_container_map or {}).get((dep, truck_id, detail_key))
                    if saved_cid:
                        capacity_val = _to_decimal(
                            (pc_capacity_map or {}).get((product_code, saved_cid))
                            or getattr((container_objs or {}).get(saved_cid), 'capacity', None),
                            default='0',
                        )
                    if capacity_val <= 0:
                        capacity_val = _to_decimal(getattr(product, 'capacity', None) if product else None, default='0')
                    if capacity_val <= 0:
                        container = getattr(product, 'used_container', None) if product else None
                        capacity_val = _to_decimal(getattr(container, 'capacity', None) if container else None, default='0')
                    if capacity_val <= 0:
                        capacity_val = Decimal('1')
                    container_count = (qty / capacity_val).to_integral_value(rounding=ROUND_CEILING)
                    qty_text = str(qty.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
                    container_text = str(container_count)
                    ship_to_name = (ship_to_name_map.get(ship_to_code) or '').strip()
                    ship_to_text = ship_to_code
                    if ship_to_name:
                        ship_to_text = f'{ship_to_code} {ship_to_name}'
                    order_text = source_order_no or '内示'
                    c.setFont(font_name, font_size)
                    c.drawString(left + 8 * mm, y, str(product_code))
                    c.drawString(left + 39 * mm, y, clip_text_to_width(name, 42))
                    c.drawString(left + 83 * mm, y, clip_text_to_width(ship_to_text, 44))
                    c.drawString(left + 128 * mm, y, clip_text_to_width(order_text, 27))
                    c.drawRightString(left + 162 * mm, y, container_text)
                    c.drawRightString(left + 180 * mm, y, qty_text)
                    if detail_idx < len(detail_keys) - 1:
                        draw_line(y - 1.4 * mm, width=0.6, dashed=True)
                    y -= line_h

                trip_ref = f'TRUCK:{truck_id}'
                vendor_text = (vendor_notice_map or {}).get((dep, trip_ref), '')
                if vendor_text:
                    for vline in vendor_text.split('\n'):
                        vline = vline.strip()
                        if not vline:
                            continue
                        if y < 16 * mm:
                            c.showPage()
                            page_no += 1
                            draw_header(page_no)
                            y = top - 14 * mm - (line_h * 2)
                            draw_departure_title(dep, continuation=True)
                            y -= line_h
                            draw_truck_title(truck_label, departure_time, arrival_date)
                            y -= line_h
                        c.saveState()
                        c.setFillColorRGB(0.8, 0, 0)
                        c.setFont(font_name, font_size)
                        c.drawString(left + 8 * mm, y, f'【運送業者への連絡】{clip_text_to_width(vline, 155)}')
                        c.restoreState()
                        y -= line_h
                y -= 1.5 * mm

            y -= 2.5 * mm

        c.save()
        buf.seek(0)
        return buf.read()


class KubotaSakaiPseudoTruckProductViewNew(APIView):
    """擬似便対象製品マスタの取得・保存。

    GET  → 全製品の擬似便紐付けリストを返す
    POST → 製品×擬似便の紐付けを一括保存
    """

    def get(self, request):
        mappings = KubotaSakaiPseudoTruckProduct.objects.select_related('truck').all()
        result = defaultdict(list)
        for m in mappings:
            key = f"{m.product_code}||{m.ship_to_code or ''}"
            result[key].append({
                'truck_id': m.truck_id,
                'truck_name': m.truck.name if m.truck else '',
                'truck_alias': m.truck.alias_name if m.truck else '',
            })

        pseudo_trucks = list(
            KubotaSakaiTruck.objects.filter(is_active=True)
            .order_by('display_order', 'name')
        )
        pseudo_truck_list = []
        for t in pseudo_trucks:
            marker = (t.alias_name or t.name or '').strip().upper().replace('　', '')
            if marker in ('A', 'A便', 'Ａ', 'Ａ便', 'P', 'P便', 'Ｐ', 'Ｐ便'):
                pseudo_truck_list.append({
                    'id': t.id,
                    'name': t.name,
                    'alias_name': t.alias_name or '',
                })

        mapping_list = []
        for key, trucks in sorted(result.items()):
            product_code, ship_to_code = key.split('||', 1)
            mapping_list.append({
                'product_code': product_code,
                'ship_to_code': ship_to_code,
                'trucks': trucks,
            })

        return Response({
            'pseudo_trucks': pseudo_truck_list,
            'mappings': mapping_list,
        })

    def post(self, request):
        rows = request.data.get('rows')
        if not isinstance(rows, list):
            return Response(
                {'detail': 'rows は配列で指定してください。'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pseudo_trucks = set(
            KubotaSakaiTruck.objects.filter(is_active=True)
            .values_list('id', flat=True)
        )

        with transaction.atomic():
            KubotaSakaiPseudoTruckProduct.objects.all().delete()
            create_items = []
            for row in rows:
                product_code = str(row.get('product_code') or '').strip()
                ship_to_code = str(row.get('ship_to_code') or '').strip()
                truck_ids = row.get('truck_ids') or []
                if not product_code or not isinstance(truck_ids, list):
                    continue
                for tid in truck_ids:
                    tid = int(tid)
                    if tid in pseudo_trucks:
                        create_items.append(
                            KubotaSakaiPseudoTruckProduct(
                                product_code=product_code,
                                ship_to_code=ship_to_code,
                                truck_id=tid,
                            )
                        )
            if create_items:
                KubotaSakaiPseudoTruckProduct.objects.bulk_create(create_items)

        return Response({'saved': len(create_items)})


class KubotaSakaiDeliveryProgressAdjustViewNew(APIView):
    """配送進捗の調整値を保存し、再計算する。"""

    def post(self, request):
        rows = request.data.get('rows')
        if not isinstance(rows, list):
            return Response(
                {'detail': 'rows は配列で指定してください。'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        affected_dates = set()
        with transaction.atomic():
            for row in rows:
                plan_date = _parse_date(row.get('plan_date'))
                product_code = str(row.get('product_code') or '').strip()
                ship_to_code = str(row.get('ship_to_code') or '').strip()
                adjust_qty = int(row.get('adjust_qty') or 0)
                if not plan_date or not product_code:
                    continue

                obj, _ = KubotaSakaiDeliveryProgress.objects.get_or_create(
                    plan_date=plan_date,
                    product_code=product_code,
                    ship_to_code=ship_to_code,
                )
                if obj.adjust_qty != adjust_qty:
                    obj.adjust_qty = adjust_qty
                    obj.save(update_fields=['adjust_qty', 'updated_at'])
                    affected_dates.add(plan_date)

        if affected_dates:
            start = min(affected_dates)
            max_due_date = (
                KubotaSakaiDueAdjustment.objects.aggregate(
                    max_date=Max('due_date')
                )['max_date'] or start
            )
            end = max(max_due_date, max(affected_dates))
            recalculate_delivery_progress(start, end)

        return Response({'updated': len(affected_dates)})
