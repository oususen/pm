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

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

from masters.models import Calendar, CalendarDay, KubotaSakaiTruck, Line, Process, Product
from orders.core.models import KubotaSakaiDueAdjustment, KubotaSakaiTripAssignment
from production.models_line_backlog import LineBacklog
from system_settings.models import SystemSetting

from .services.truck_load_calculator import calculate_truck_load

# クボタ配送ライン定数
KUBOTA_DELIVERY_LINE_CODE = 'KUBOTA_DELIVERY'
KUBOTA_DELIVERY_LINE_NAME = 'クボタ配送ライン'
KUBOTA_DELIVERY_PROCESS_CODE = 'KUBOTA_DELIVERY'
KUBOTA_DELIVERY_PROCESS_NAME = 'クボタ配送工程'

# plan_id プレフィックス（pickup カスケードでクボタ便を識別するためのマーカー）
KUBOTA_TRIP_PLAN_ID_PREFIX = 'KBT_T'


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
    code_hits = rows.filter(
        Q(calendar_code__iexact='kubota_sakai')
        | Q(calendar_code__iexact='kobota_sakai')
        | Q(calendar_code__icontains='kubota')
        | Q(calendar_code__icontains='kobota')
    )
    if code_hits.exists():
        return code_hits.order_by('id').first()
    name_hits = rows.filter(Q(calendar_name__icontains='クボタ') & Q(calendar_name__icontains='堺'))
    return name_hits.order_by('id').first()


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


def _get_deadline_days():
    row = SystemSetting.objects.filter(key='kubota_sakai.assignment_deadline_days').first()
    if not row:
        return 3
    try:
        return max(int(row.value), 0)
    except Exception:
        return 3


def _build_load_item(product, qty):
    """Product オブジェクトから積載計算用アイテムを構築"""
    container = getattr(product, 'used_container', None) if product else None
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

    capacity = getattr(product, 'capacity', None) if product else None
    if not capacity and container:
        capacity = container.capacity

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


# ---------------------------------------------------------------------------
# API View
# ---------------------------------------------------------------------------

class KubotaSakaiTripPlanView(APIView):
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

        rows = []
        for adj in adjustments:
            product = products.get(adj.product_code)
            container = getattr(product, 'used_container', None) if product else None
            current_assignments = assignment_map.get(adj.id, [])
            assigned_qty = sum((_to_decimal(a.qty) for a in current_assignments), Decimal('0'))
            delivery_qty = _to_decimal(adj.delivery_qty)
            unassigned_qty = delivery_qty - assigned_qty
            deadline_date = _subtract_business_days(target_date, deadline_days, calendar_map)
            overdue = unassigned_qty > 0 and today > deadline_date

            rows.append({
                'due_adjustment_id': adj.id,
                'due_date': target_date.isoformat(),
                'product_code': adj.product_code,
                'product_name': product.product_name if product else '',
                'ship_to_code': adj.ship_to_code or '',
                'source_order_no': adj.source_order_no or '',
                'order_type': adj.order_type,
                'delivery_qty': str(delivery_qty),
                'assigned_qty': str(assigned_qty),
                'unassigned_qty': str(unassigned_qty),
                'container_name': getattr(container, 'name', '') if container else '',
                'capacity': getattr(product, 'capacity', None) if product else None,
                'overdue': overdue,
                'deadline_date': deadline_date.isoformat(),
                'allocations': [
                    {
                        'id': a.id,
                        'truck_id': a.truck_id,
                        'truck_name': a.truck.name if a.truck_id else '',
                        'qty': str(a.qty),
                    }
                    for a in current_assignments
                ],
            })

        # 便一覧 + 占有率サマリー
        trucks = list(KubotaSakaiTruck.objects.filter(is_active=True).order_by('display_order', 'name'))
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
                'occupancy_percent': str(load['occupancy_percent']),
                'total_weight': str(load['total_weight']),
                'errors': load['errors'],
            })

        return Response({
            'target_date': target_date.isoformat(),
            'is_holiday': is_holiday,
            'assignment_deadline_days': deadline_days,
            'rows': rows,
            'trucks': [
                {
                    'id': t.id,
                    'name': t.name,
                    'alias_name': t.alias_name,
                    'default_use': t.default_use,
                    'width': t.width,
                    'depth': t.depth,
                    'departure_time': _format_hhmm(t.departure_time),
                    'arrival_time': _format_hhmm(t.arrival_time),
                    'arrival_day_offset': t.arrival_day_offset,
                }
                for t in trucks
            ],
            'truck_summaries': truck_summaries,
        })

    def post(self, request):
        target_date = _parse_date(request.data.get('target_date'))
        rows = request.data.get('rows')
        if not target_date:
            return Response({'detail': 'target_date は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(rows, list):
            return Response({'detail': 'rows は配列で指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

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

        # Product lookup（積載チェック用）
        product_codes = set(a.product_code for a in adj_map.values())
        products = {
            p.product_code: p
            for p in Product.objects.select_related('used_container').filter(product_code__in=product_codes)
        }

        errors = []
        normalized = []
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

            normalized_allocations = []
            total = Decimal('0')
            for al in allocations:
                truck_id = int(al.get('truck_id') or 0)
                qty = _to_decimal(al.get('qty'))
                if qty <= 0:
                    continue
                truck = truck_map.get(truck_id)
                if not truck:
                    errors.append({'due_adjustment_id': adj_id, 'detail': f'便が不正です: {truck_id}'})
                    continue
                normalized_allocations.append({'truck_id': truck_id, 'qty': qty})
                total += qty

            if total > _to_decimal(adj.delivery_qty):
                errors.append({
                    'due_adjustment_id': adj_id,
                    'detail': f'割付数量超過: delivery={adj.delivery_qty} assigned={total}',
                })
                continue

            normalized.append({'adj_id': adj_id, 'allocations': normalized_allocations})

        if errors:
            return Response(
                {'detail': '入力エラーがあります。', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user if request.user and request.user.is_authenticated else None

        with transaction.atomic():
            # 対象行の既存割付を削除 → 再作成
            # NOTE:
            # 過去実装や便変更の影響で同一 due_adjustment に別日付の割付が残ると、
            # 同じ明細が二重計上されるため departure_date で絞らず全削除する。
            KubotaSakaiTripAssignment.objects.filter(
                due_adjustment_id__in=[n['adj_id'] for n in normalized],
            ).delete()

            create_items = []
            for row in normalized:
                for al in row['allocations']:
                    create_items.append(
                        KubotaSakaiTripAssignment(
                            due_adjustment_id=row['adj_id'],
                            truck_id=al['truck_id'],
                            departure_date=target_date,
                            qty=al['qty'],
                            created_by=user,
                        )
                    )
            if create_items:
                KubotaSakaiTripAssignment.objects.bulk_create(create_items)

            # 積載チェック（全便対象）
            all_today = list(
                KubotaSakaiTripAssignment.objects.select_related('due_adjustment', 'truck')
                .filter(departure_date=target_date)
            )
            per_truck = defaultdict(list)
            for item in all_today:
                per_truck[item.truck_id].append(item)

            save_errors = []
            for truck_id, items in per_truck.items():
                truck = items[0].truck
                load_items = []
                for item in items:
                    product = products.get(item.due_adjustment.product_code)
                    if product:
                        load_items.append(_build_load_item(product, item.qty))
                load = calculate_truck_load(load_items, truck)
                if load['errors']:
                    save_errors.append({
                        'truck_id': truck_id,
                        'truck_name': truck.alias_name or truck.name,
                        'errors': load['errors'],
                    })

            if save_errors:
                transaction.set_rollback(True)
                return Response(
                    {'detail': '便積載制約エラーがあります。', 'errors': save_errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # LineBacklog 同期（LinePlan不使用、LineBacklog直接保存）
            _sync_kubota_delivery_backlog_for_date(target_date)

        return Response({
            'saved_rows': len(normalized),
            'saved_allocations': len(create_items),
        })


class KubotaSakaiTripLoadPreviewView(APIView):
    """未保存の便割付入力を使って便占有率を試算する。"""

    def post(self, request):
        target_date = _parse_date(request.data.get('target_date'))
        rows = request.data.get('rows')
        if not target_date:
            return Response({'detail': 'target_date は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(rows, list):
            return Response({'detail': 'rows は配列で指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

        due_adjustments = list(
            KubotaSakaiDueAdjustment.objects.filter(
                due_date=target_date,
                delivery_qty__gt=0,
            ).order_by('id')
        )
        due_adjustment_map = {item.id: item for item in due_adjustments}

        posted_alloc_map = {}
        truck_ids = set()
        errors = []
        for row in rows:
            try:
                due_adjustment_id = int(row.get('due_adjustment_id') or 0)
            except (TypeError, ValueError):
                due_adjustment_id = 0
            if due_adjustment_id <= 0:
                continue
            if due_adjustment_id not in due_adjustment_map:
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
                normalized_allocations.append({'truck_id': truck_id, 'qty': qty})
                truck_ids.add(truck_id)
            posted_alloc_map[due_adjustment_id] = normalized_allocations

        if errors:
            return Response({'detail': '入力エラーがあります。', 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        existing_map = defaultdict(list)
        for item in KubotaSakaiTripAssignment.objects.filter(
            due_adjustment_id__in=[d.id for d in due_adjustments],
            departure_date=target_date,
        ).order_by('id'):
            existing_map[item.due_adjustment_id].append({'truck_id': item.truck_id, 'qty': _to_decimal(item.qty)})
            truck_ids.add(item.truck_id)

        trucks = list(KubotaSakaiTruck.objects.filter(is_active=True).order_by('display_order', 'name'))
        if truck_ids:
            truck_ids.update([truck.id for truck in trucks])
        truck_map = {truck.id: truck for truck in trucks}

        product_codes = set(item.product_code for item in due_adjustments)
        products = {
            product.product_code: product
            for product in Product.objects.select_related('used_container').filter(product_code__in=product_codes)
        }

        per_truck_load_items = defaultdict(list)
        for due_adjustment in due_adjustments:
            product = products.get(due_adjustment.product_code)
            allocations = posted_alloc_map.get(due_adjustment.id, existing_map.get(due_adjustment.id, []))
            for allocation in allocations:
                truck = truck_map.get(allocation['truck_id'])
                if not truck or not product:
                    continue
                per_truck_load_items[truck.id].append(_build_load_item(product, allocation['qty']))

        summaries = []
        for truck in trucks:
            load = calculate_truck_load(per_truck_load_items.get(truck.id, []), truck)
            summaries.append({
                'truck_id': truck.id,
                'truck_name': truck.alias_name or truck.name,
                'occupancy_percent': str(load['occupancy_percent']),
                'total_weight': str(load['total_weight']),
                'errors': load['errors'],
            })

        return Response({
            'target_date': target_date.isoformat(),
            'truck_summaries': summaries,
        })


class KubotaSakaiTripLoadDetailView(APIView):
    """便ごとの占有計算明細を返す（CSV出力用）。"""

    def get(self, request):
        target_date = _parse_date(request.query_params.get('target_date'))
        if not target_date:
            return Response({'detail': 'target_date は必須です。'}, status=status.HTTP_400_BAD_REQUEST)

        assignments = list(
            KubotaSakaiTripAssignment.objects.select_related('due_adjustment', 'truck')
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

        grouped = {}
        for assignment in assignments:
            key = (assignment.truck_id, assignment.due_adjustment.product_code)
            if key not in grouped:
                grouped[key] = {
                    'truck': assignment.truck,
                    'product_code': assignment.due_adjustment.product_code,
                    'qty': Decimal('0'),
                }
            grouped[key]['qty'] += _to_decimal(assignment.qty)

        rows = []
        for item in grouped.values():
            truck = item['truck']
            product_code = item['product_code']
            qty = item['qty']
            product = products.get(product_code)
            container = getattr(product, 'used_container', None) if product else None

            capacity = getattr(product, 'capacity', None) if product else None
            if not capacity and container:
                capacity = container.capacity
            if not capacity:
                capacity = 1
            capacity = max(int(_to_decimal(capacity)), 1)

            load_item = _build_load_item(product, qty)
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


class KubotaSakaiPickupDetailPdfView(APIView):
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
        products = {
            p.product_code: p
            for p in Product.objects.select_related('used_container').filter(product_code__in=product_codes)
        }

        # departure_date -> truck_id -> product_code で集計
        grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(Decimal)))
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
            product_code = item.due_adjustment.product_code
            grouped[departure_date][truck.id][product_code] += _to_decimal(item.qty)
            if truck.id not in truck_meta:
                truck_meta[truck.id] = {
                    'name': truck.name,
                    'alias_name': truck.alias_name or '',
                    'display_order': truck.display_order or 0,
                    'departure_time': _format_hhmm(truck.departure_time),
                }

        pdf_bytes = self._render_pdf(start_date, end_date, grouped, truck_meta, products)
        filename = f"クボタ堺_集荷明細表_{start_date:%Y%m%d}_{end_date:%Y%m%d}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def _render_pdf(self, start_date, end_date, grouped, truck_meta, products):
        try:
            pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
        except Exception:
            pass

        font_name = 'HeiseiKakuGo-W5'
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
            c.setFont(font_name, 9)
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

        def draw_truck_title(truck_text, dep_time):
            c.setFont(font_name, 10)
            c.drawString(left + 2 * mm, y, f'便: {truck_text}')
            if dep_time:
                c.drawString(left + 34 * mm, y, f'出発時刻：{dep_time}')

        def draw_columns():
            c.setFont(font_name, 9)
            c.drawString(left + 8 * mm, y, '品番')
            c.drawString(left + 58 * mm, y, '品名')
            c.drawRightString(left + 162 * mm, y, '容器数')
            c.drawRightString(left + 180 * mm, y, '数量')

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
            if y < 28 * mm:
                c.showPage()
                page_no += 1
                draw_header(page_no)
                y = top - 14 * mm - (line_h * 2)
            if dep_idx > 0:
                # 日と日の間に2行ぶんの余白を入れてから二重線を描画
                y -= (line_h * 2)
                draw_double_line(y + 1.8 * mm, width=1.3, gap=1.2 * mm)
                # 二重線の後も2行ぶん余白を入れる
                y -= (line_h * 2)

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
                draw_truck_title(truck_label, departure_time)
                y -= line_h

                draw_columns()
                y -= line_h

                product_codes = sorted(grouped[dep][truck_id].keys())
                for prod_idx, code in enumerate(product_codes):
                    if y < 16 * mm:
                        c.showPage()
                        page_no += 1
                        draw_header(page_no)
                        y = top - 14 * mm - (line_h * 2)
                        draw_departure_title(dep, continuation=True)
                        y -= line_h
                        draw_truck_title(truck_label, departure_time)
                        y -= line_h
                        draw_columns()
                        y -= line_h
                    qty = grouped[dep][truck_id][code]
                    product = products.get(code)
                    name = (product.product_name if product else '') or ''
                    capacity_val = _to_decimal(getattr(product, 'capacity', None) if product else None, default='0')
                    if capacity_val <= 0:
                        container = getattr(product, 'used_container', None) if product else None
                        capacity_val = _to_decimal(getattr(container, 'capacity', None) if container else None, default='0')
                    if capacity_val <= 0:
                        capacity_val = Decimal('1')
                    container_count = (qty / capacity_val).to_integral_value(rounding=ROUND_CEILING)
                    qty_text = str(qty.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
                    container_text = str(container_count)
                    c.setFont(font_name, 9)
                    c.drawString(left + 8 * mm, y, str(code))
                    c.drawString(left + 58 * mm, y, name[:28])
                    c.drawRightString(left + 162 * mm, y, container_text)
                    c.drawRightString(left + 180 * mm, y, qty_text)
                    if prod_idx < len(product_codes) - 1:
                        draw_line(y - 1.4 * mm, width=0.6, dashed=True)
                    y -= line_h
                y -= 1.5 * mm

            y -= 2.5 * mm

        c.save()
        buf.seek(0)
        return buf.read()
