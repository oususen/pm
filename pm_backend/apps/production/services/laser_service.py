import math
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from django.db import transaction
from django.db.models import Sum

from masters.models import Calendar
from orders.models import OrderLine
from orders.utils.calendar_utils import add_working_days, get_business_today
from production.models_laser_actual import LaserActual, LaserActualDetail
from production.models_laser_pattern import LaserPattern
from production.serializers import LaserActualSerializer


def _parse_target_month(month_value):
    month_text = str(month_value or '').strip()
    if not month_text:
        today = get_business_today()
        month_start = today.replace(day=1)
    else:
        try:
            month_start = datetime.strptime(f'{month_text}-01', '%Y-%m-%d').date()
        except ValueError:
            return None, None, 'month must be YYYY-MM'

    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1, day=1)
    month_end = next_month - timedelta(days=1)
    return month_start, month_end, None


def _decimal_to_float(value, digits='0.001'):
    decimal_value = Decimal(str(value or 0)).quantize(Decimal(digits), rounding=ROUND_HALF_UP)
    return float(decimal_value)


def build_laser_monthly_material_summary(query_params, patterns_queryset):
    start_date_str = query_params.get('start_date')
    end_date_str = query_params.get('end_date')
    if start_date_str and end_date_str:
        try:
            month_start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            month_end = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if month_start > month_end:
                return {'detail': '開始日は終了日以前にしてください。'}, 400
        except ValueError:
            return {'detail': 'start_date/end_date は YYYY-MM-DD 形式で指定してください。'}, 400
    else:
        month_start, month_end, error_message = _parse_target_month(query_params.get('month'))
        if error_message:
            return {'detail': error_message}, 400

    try:
        shift_days = int(query_params.get('shift_days') or 0)
    except (ValueError, TypeError):
        shift_days = 0
    daiso_calendar = Calendar.objects.filter(calendar_code='daiso').first()
    if shift_days > 0:
        order_start = add_working_days(month_start, shift_days, daiso_calendar)
        order_end = add_working_days(month_end, shift_days, daiso_calendar)
    else:
        order_start = month_start
        order_end = month_end

    actual_start_str = query_params.get('actual_start_date') or start_date_str
    actual_end_str = query_params.get('actual_end_date') or end_date_str
    try:
        actual_start = datetime.strptime(actual_start_str, '%Y-%m-%d').date() if actual_start_str else month_start
        actual_end = datetime.strptime(actual_end_str, '%Y-%m-%d').date() if actual_end_str else month_end
    except ValueError:
        actual_start, actual_end = month_start, month_end

    patterns = list(patterns_queryset.filter(is_budget_target=True).order_by('pattern_no'))
    if not patterns:
        return {
            'month': month_start.strftime('%Y-%m'),
            'start_date': str(month_start),
            'end_date': str(month_end),
            'material_totals': [],
            'equipment_totals': [],
            'pattern_rows': [],
            'warnings': ['材料予算用パターンが登録されていません。'],
            'totals': {
                'material_type_count': 0,
                'pattern_count': 0,
                'required_shots': 0,
                'required_material_qty': 0,
                'total_process_time_min': 0,
            },
        }, 200

    finished_meta_by_code = {}
    product_pattern_map = {}
    warnings = []
    warning_details = []
    for pattern in patterns:
        for item in pattern.finished_items.all():
            product = item.finished_product
            if not product:
                continue
            product_code = str(product.product_code or '').strip()
            if not product_code:
                continue
            finished_meta_by_code.setdefault(product_code, {
                'product_id': product.id,
                'product_code': product_code,
                'product_name': product.product_name or '',
            })
            product_pattern_map.setdefault(product_code, []).append(pattern.pattern_no)

    duplicate_codes = {code: pattern_nos for code, pattern_nos in product_pattern_map.items() if len(pattern_nos) > 1}
    for code, pattern_nos in sorted(duplicate_codes.items()):
        meta = finished_meta_by_code.get(code, {})
        warnings.append(
            f"完成品 {code} {meta.get('product_name', '')} が複数パターンに登録されています: {', '.join(pattern_nos)}"
        )
        warning_details.append({
            'product_code': code,
            'product_name': meta.get('product_name', ''),
            'pattern_nos': pattern_nos,
        })

    product_pattern_list = [
        {
            'product_code': code,
            'product_name': finished_meta_by_code.get(code, {}).get('product_name', ''),
            'pattern_nos': pattern_nos,
        }
        for code, pattern_nos in sorted(product_pattern_map.items())
    ]

    if not finished_meta_by_code:
        return {
            'month': month_start.strftime('%Y-%m'),
            'start_date': str(month_start),
            'end_date': str(month_end),
            'material_totals': [],
            'equipment_totals': [],
            'pattern_rows': [],
            'warnings': ['材料予算用パターンに完成品情報がありません。'],
            'totals': {
                'material_type_count': 0,
                'pattern_count': 0,
                'required_shots': 0,
                'required_material_qty': 0,
                'total_process_time_min': 0,
            },
        }, 200

    order_rows = list(
        OrderLine.objects.filter(
            order__status='OPEN',
            product_code__in=list(finished_meta_by_code.keys()),
            due_date__gte=order_start,
            due_date__lte=order_end,
        )
        .values('product_code', 'due_date', 'order__order_type', 'order__customer__customer_code', 'ship_to_code')
        .annotate(total_qty=Sum('quantity'))
        .order_by('product_code', 'due_date', 'order__order_type', 'order__customer__customer_code', 'ship_to_code')
    )

    daily_order_map = {}
    for row in order_rows:
        product_code = str(row.get('product_code') or '').strip()
        due_date = row.get('due_date')
        if not product_code or not due_date:
            continue
        customer_code = str(row.get('order__customer__customer_code') or '').strip()
        ship_to_code = str(row.get('ship_to_code') or '').strip()
        key = (product_code, customer_code, ship_to_code, due_date)
        bucket = daily_order_map.setdefault(key, {'firm_qty': Decimal('0'), 'forecast_qty': Decimal('0')})
        qty = Decimal(str(row.get('total_qty') or 0))
        order_type = str(row.get('order__order_type') or '').upper()
        if order_type == 'FIRM':
            bucket['firm_qty'] += qty
        else:
            bucket['forecast_qty'] += qty

    monthly_order_map = {}
    for (product_code, _cust, _ship, _due_date), qty_map in daily_order_map.items():
        item = monthly_order_map.setdefault(product_code, {
            'firm_qty': Decimal('0'),
            'forecast_qty': Decimal('0'),
            'selected_qty': Decimal('0'),
            'firm_days': 0,
            'forecast_only_days': 0,
        })
        firm_qty = qty_map['firm_qty']
        forecast_qty = qty_map['forecast_qty']
        selected_qty = firm_qty if firm_qty > 0 else forecast_qty
        item['firm_qty'] += firm_qty
        item['forecast_qty'] += forecast_qty
        item['selected_qty'] += selected_qty
        if firm_qty > 0:
            item['firm_days'] += 1
        elif forecast_qty > 0:
            item['forecast_only_days'] += 1

    material_totals_map = {}
    equipment_totals_map = {}
    pattern_rows = []
    total_required_material_qty = Decimal('0')
    total_process_time_min = Decimal('0')
    total_weight_kg = Decimal('0')

    for pattern in patterns:
        finished_items = list(pattern.finished_items.all())
        if not finished_items:
            continue

        finished_rows = []
        selected_order_total = Decimal('0')
        pattern_required_material_qty = Decimal('0')

        for item in finished_items:
            product = item.finished_product
            product_code = str(getattr(product, 'product_code', '') or '').strip()
            units_per_shot = Decimal(str(item.units_per_shot or 0))
            order_summary = monthly_order_map.get(product_code, {})
            selected_qty = Decimal(str(order_summary.get('selected_qty') or 0))
            firm_qty = Decimal(str(order_summary.get('firm_qty') or 0))
            forecast_qty = Decimal(str(order_summary.get('forecast_qty') or 0))
            material_per_unit = (Decimal('1') / units_per_shot) if units_per_shot > 0 else Decimal('0')
            required_material_qty = (selected_qty / units_per_shot) if units_per_shot > 0 else Decimal('0')
            selected_order_total += selected_qty
            pattern_required_material_qty += required_material_qty

            if order_summary.get('firm_days') and order_summary.get('forecast_only_days'):
                selected_basis = 'MIXED'
            elif order_summary.get('firm_days'):
                selected_basis = 'FIRM'
            elif order_summary.get('forecast_only_days'):
                selected_basis = 'FORECAST'
            else:
                selected_basis = 'NONE'

            finished_rows.append({
                'finished_product_id': getattr(product, 'id', None),
                'finished_product_code': product_code,
                'finished_product_name': getattr(product, 'product_name', '') or '',
                'units_per_shot': _decimal_to_float(units_per_shot),
                'material_per_unit': _decimal_to_float(material_per_unit),
                'firm_qty': _decimal_to_float(firm_qty),
                'forecast_qty': _decimal_to_float(forecast_qty),
                'selected_qty': _decimal_to_float(selected_qty),
                'selected_basis': selected_basis,
                'required_material_qty': _decimal_to_float(required_material_qty),
            })

        if pattern_required_material_qty <= 0:
            continue

        process_time_min = Decimal(str(pattern.process_time_min or 0))
        total_process_time = process_time_min * pattern_required_material_qty
        material = pattern.material
        material_unit = getattr(material, 'unit', '') or ''
        equipment = pattern.equipment
        sg = getattr(material, 'specific_gravity', None)
        sl = getattr(material, 'size_length', None)
        sw = getattr(material, 'size_width', None)
        st = getattr(material, 'size_thickness', None)
        if sg and sl and sw and st:
            unit_weight_kg = Decimal(str(sg)) * Decimal(str(sl)) * Decimal(str(sw)) * Decimal(str(st)) / Decimal('1000000')
        else:
            unit_weight_kg = None
        pattern_weight_kg = (unit_weight_kg * pattern_required_material_qty) if unit_weight_kg is not None else None

        pack_qty = getattr(material, 'order_lot_min', None)
        if pack_qty and pack_qty > 0 and pattern_required_material_qty > 0:
            required_packages = math.ceil(float(pattern_required_material_qty) / float(pack_qty))
        else:
            required_packages = None

        pattern_rows.append({
            'pattern_id': pattern.id,
            'pattern_no': pattern.pattern_no,
            'material_id': getattr(material, 'id', None),
            'material_code': getattr(material, 'product_code', '') or '',
            'material_name': getattr(material, 'product_name', '') or '',
            'material_unit': material_unit,
            'specific_gravity': _decimal_to_float(sg) if sg is not None else None,
            'size_length': _decimal_to_float(sl) if sl is not None else None,
            'size_width': _decimal_to_float(sw) if sw is not None else None,
            'size_thickness': _decimal_to_float(st) if st is not None else None,
            'unit_weight_kg': _decimal_to_float(unit_weight_kg) if unit_weight_kg is not None else None,
            'total_weight_kg': _decimal_to_float(pattern_weight_kg) if pattern_weight_kg is not None else None,
            'pack_qty': pack_qty,
            'required_packages': required_packages,
            'equipment_id': getattr(pattern.equipment, 'id', None),
            'equipment_code': getattr(pattern.equipment, 'equipment_code', '') or '',
            'equipment_name': getattr(pattern.equipment, 'equipment_name', '') or '',
            'process_time_min': _decimal_to_float(process_time_min),
            'selected_order_qty_total': _decimal_to_float(selected_order_total),
            'required_shots': _decimal_to_float(pattern_required_material_qty),
            'required_material_qty': _decimal_to_float(pattern_required_material_qty),
            'total_process_time_min': _decimal_to_float(total_process_time),
            'finished_items': finished_rows,
        })

        material_key = getattr(material, 'id', None) or f'code:{getattr(material, "product_code", "")}'
        material_row = material_totals_map.setdefault(material_key, {
            'material_id': getattr(material, 'id', None),
            'material_code': getattr(material, 'product_code', '') or '',
            'material_name': getattr(material, 'product_name', '') or '',
            'material_unit': material_unit,
            'specific_gravity': _decimal_to_float(sg) if sg is not None else None,
            'size_length': _decimal_to_float(sl) if sl is not None else None,
            'size_width': _decimal_to_float(sw) if sw is not None else None,
            'size_thickness': _decimal_to_float(st) if st is not None else None,
            'unit_weight_kg': _decimal_to_float(unit_weight_kg) if unit_weight_kg is not None else None,
            'pack_qty': pack_qty,
            'pattern_count': 0,
            'required_material_qty': Decimal('0'),
            'required_shots': Decimal('0'),
            'total_weight_kg': Decimal('0') if unit_weight_kg is not None else None,
            'total_process_time_min': Decimal('0'),
        })
        material_row['pattern_count'] += 1
        material_row['required_material_qty'] += pattern_required_material_qty
        material_row['required_shots'] += pattern_required_material_qty
        material_row['total_process_time_min'] += total_process_time
        if material_row['total_weight_kg'] is not None and unit_weight_kg is not None:
            material_row['total_weight_kg'] += unit_weight_kg * pattern_required_material_qty

        equipment_key = getattr(equipment, 'id', None) or f'code:{getattr(equipment, "equipment_code", "")}'
        equipment_row = equipment_totals_map.setdefault(equipment_key, {
            'equipment_id': getattr(equipment, 'id', None),
            'equipment_code': getattr(equipment, 'equipment_code', '') or '',
            'equipment_name': getattr(equipment, 'equipment_name', '') or '',
            'pattern_count': 0,
            'total_process_time_min': Decimal('0'),
        })
        equipment_row['pattern_count'] += 1
        equipment_row['total_process_time_min'] += total_process_time

        total_required_material_qty += pattern_required_material_qty
        total_process_time_min += total_process_time
        if pattern_weight_kg is not None:
            total_weight_kg += pattern_weight_kg

    material_totals = []
    for item in sorted(material_totals_map.values(), key=lambda x: (x['material_code'], x['material_name'])):
        req_mat = item['required_material_qty']
        pack_qty_val = item.get('pack_qty')
        required_packages = math.ceil(float(req_mat) / float(pack_qty_val)) if pack_qty_val and pack_qty_val > 0 and req_mat > 0 else None
        tw = item.get('total_weight_kg')
        material_totals.append({
            'material_id': item['material_id'],
            'material_code': item['material_code'],
            'material_name': item['material_name'],
            'material_unit': item['material_unit'],
            'specific_gravity': item.get('specific_gravity'),
            'size_length': item.get('size_length'),
            'size_width': item.get('size_width'),
            'size_thickness': item.get('size_thickness'),
            'unit_weight_kg': item.get('unit_weight_kg'),
            'total_weight_kg': _decimal_to_float(tw) if isinstance(tw, Decimal) else tw,
            'pack_qty': pack_qty_val,
            'required_packages': required_packages,
            'pattern_count': item['pattern_count'],
            'required_material_qty': _decimal_to_float(req_mat),
            'required_shots': _decimal_to_float(item['required_shots']),
            'total_process_time_min': _decimal_to_float(item['total_process_time_min']),
        })

    equipment_totals = []
    for item in sorted(equipment_totals_map.values(), key=lambda x: (x['equipment_code'], x['equipment_name'])):
        equipment_totals.append({
            'equipment_id': item['equipment_id'],
            'equipment_code': item['equipment_code'],
            'equipment_name': item['equipment_name'],
            'pattern_count': item['pattern_count'],
            'total_process_time_min': _decimal_to_float(item['total_process_time_min']),
        })

    actual_rows = (
        LaserActual.objects
        .filter(work_date__gte=actual_start, work_date__lte=actual_end)
        .values(
            'material_id',
            'material__product_code',
            'material__product_name',
            'material__specific_gravity',
            'material__size_length',
            'material__size_width',
            'material__size_thickness',
            'pattern__material_id',
            'pattern__material__product_code',
            'pattern__material__product_name',
            'pattern__material__specific_gravity',
            'pattern__material__size_length',
            'pattern__material__size_width',
            'pattern__material__size_thickness',
            'equipment_id', 'equipment_code', 'equipment_name',
        )
        .annotate(
            actual_shot_count=Sum('shot_count'),
            actual_process_time_min=Sum('total_process_time'),
        )
    )

    actual_material_map = {}
    for row in actual_rows:
        mat_id = row['material_id'] or row['pattern__material_id']
        mat_code = row['material__product_code'] or row['pattern__material__product_code'] or ''
        mat_name = row['material__product_name'] or row['pattern__material__product_name'] or ''
        mat_key = mat_id or f'code:{mat_code}'
        if not mat_key:
            continue

        sg = row['material__specific_gravity'] or row['pattern__material__specific_gravity']
        sl = row['material__size_length'] or row['pattern__material__size_length']
        sw = row['material__size_width'] or row['pattern__material__size_width']
        st = row['material__size_thickness'] or row['pattern__material__size_thickness']
        if sg and sl and sw and st:
            uwkg = float(Decimal(str(sg)) * Decimal(str(sl)) * Decimal(str(sw)) * Decimal(str(st)) / Decimal('1000000'))
        else:
            uwkg = None

        mat = actual_material_map.setdefault(mat_key, {
            'material_id': mat_id,
            'material_code': mat_code,
            'material_name': mat_name,
            'actual_shot_count': 0,
            'actual_process_time_min': Decimal('0'),
            'unit_weight_kg': uwkg,
        })
        mat['actual_shot_count'] += int(row['actual_shot_count'] or 0)
        mat['actual_process_time_min'] += Decimal(str(row['actual_process_time_min'] or 0))

    actual_material_totals = []
    total_actual_shot_count = 0
    total_actual_weight_kg = Decimal('0')
    total_actual_process_time_min = Decimal('0')
    for item in sorted(actual_material_map.values(), key=lambda x: x['material_code']):
        shots = item['actual_shot_count']
        uwkg = item['unit_weight_kg']
        actual_weight_kg = float(Decimal(str(uwkg)) * shots) if uwkg else None
        total_actual_shot_count += shots
        total_actual_process_time_min += item['actual_process_time_min']
        if actual_weight_kg is not None:
            total_actual_weight_kg += Decimal(str(actual_weight_kg))
        actual_material_totals.append({
            'material_id': item['material_id'],
            'material_code': item['material_code'],
            'material_name': item['material_name'],
            'unit_weight_kg': uwkg,
            'actual_shot_count': shots,
            'actual_weight_kg': actual_weight_kg,
            'actual_process_time_min': _decimal_to_float(item['actual_process_time_min']),
        })

    actual_equipment_map = {}
    for row in actual_rows:
        eq_key = row['equipment_id'] or f'code:{row["equipment_code"]}'
        eq = actual_equipment_map.setdefault(eq_key, {
            'equipment_id': row['equipment_id'],
            'equipment_code': row.get('equipment_code') or '',
            'equipment_name': row.get('equipment_name') or '',
            'actual_shot_count': 0,
            'actual_process_time_min': Decimal('0'),
        })
        eq['actual_shot_count'] += int(row['actual_shot_count'] or 0)
        eq['actual_process_time_min'] += Decimal(str(row['actual_process_time_min'] or 0))

    actual_equipment_totals = [
        {
            'equipment_id': v['equipment_id'],
            'equipment_code': v['equipment_code'],
            'equipment_name': v['equipment_name'],
            'actual_shot_count': v['actual_shot_count'],
            'actual_process_time_min': _decimal_to_float(v['actual_process_time_min']),
        }
        for v in sorted(actual_equipment_map.values(), key=lambda x: x['equipment_code'])
    ]

    return {
        'month': month_start.strftime('%Y-%m'),
        'start_date': str(month_start),
        'end_date': str(month_end),
        'order_start_date': str(order_start),
        'order_end_date': str(order_end),
        'shift_days': shift_days,
        'actual_start_date': str(actual_start),
        'actual_end_date': str(actual_end),
        'material_totals': material_totals,
        'equipment_totals': equipment_totals,
        'pattern_rows': pattern_rows,
        'warnings': warnings,
        'warning_details': warning_details,
        'product_pattern_list': product_pattern_list,
        'totals': {
            'material_type_count': len(material_totals),
            'pattern_count': len(pattern_rows),
            'required_shots': _decimal_to_float(total_required_material_qty),
            'required_material_qty': _decimal_to_float(total_required_material_qty),
            'total_process_time_min': _decimal_to_float(total_process_time_min),
            'total_weight_kg': _decimal_to_float(total_weight_kg),
        },
        'actual_material_totals': actual_material_totals,
        'actual_equipment_totals': actual_equipment_totals,
        'actual_totals': {
            'total_shot_count': total_actual_shot_count,
            'total_weight_kg': _decimal_to_float(total_actual_weight_kg),
            'total_process_time_min': _decimal_to_float(total_actual_process_time_min),
        },
    }, 200


def list_current_processing_laser_actuals(scan_limit):
    try:
        scan_limit = int(scan_limit)
    except (TypeError, ValueError):
        scan_limit = 2000
    scan_limit = max(200, min(scan_limit, 10000))

    rows = (
        LaserActual.objects
        .order_by('-created_at', '-id')
        .values(
            'equipment_id',
            'equipment_code',
            'equipment_name',
            'pattern_id',
            'pattern_no',
            'operator_action',
        )[:scan_limit]
    )

    latest_by_equipment = {}
    for row in rows:
        equipment_id = str(row.get('equipment_id') or '').strip()
        equipment_code = str(row.get('equipment_code') or '').strip()
        equipment_name = str(row.get('equipment_name') or '').strip()
        if equipment_id:
            equipment_key = f'id:{equipment_id}'
        elif equipment_code:
            equipment_key = f'code:{equipment_code}'
        elif equipment_name:
            equipment_key = f'name:{equipment_name}'
        else:
            continue
        if equipment_key in latest_by_equipment:
            continue
        latest_by_equipment[equipment_key] = row

    active_rows = []
    for equipment_key, row in latest_by_equipment.items():
        action = str(row.get('operator_action') or '').upper()
        if action not in ('START', 'RESUME'):
            continue
        active_rows.append({
            'equipment_key': equipment_key,
            'equipment': row.get('equipment_id'),
            'equipment_code': str(row.get('equipment_code') or '').strip(),
            'equipment_name': str(row.get('equipment_name') or '').strip(),
            'pattern': row.get('pattern_id'),
            'pattern_no': str(row.get('pattern_no') or '').strip(),
        })

    active_rows.sort(
        key=lambda row: (
            str(row.get('equipment_name') or '').strip(),
            str(row.get('equipment_code') or '').strip(),
            int(row.get('equipment') or 0),
        )
    )
    return {'results': active_rows}


def delete_laser_actual(instance):
    with transaction.atomic():
        LaserActualSerializer.revert_backlog_for_instance(instance)
        instance.delete()


def update_laser_actual_detail_quantity(detail_id, total_qty_raw):
    with transaction.atomic():
        detail = (
            LaserActualDetail.objects
            .select_related('actual__equipment__process__line', 'product')
            .filter(id=detail_id, detail_type=LaserActualDetail.DETAIL_TYPE_COMPONENT)
            .first()
        )
        if not detail:
            return {'detail': '対象明細が存在しません（COMPONENTのみ更新可）。'}, 404

        actual = detail.actual
        if not LaserActualSerializer._is_countable_action(actual.operator_action):
            return {'detail': 'この実績は数量変更できません（END/PAUSEのみ）。'}, 400

        if total_qty_raw is None:
            return {'detail': 'total_qty は必須です。'}, 400

        try:
            new_qty = Decimal(str(total_qty_raw)).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, Exception):
            return {'detail': 'total_qty は数値で入力してください。'}, 400

        if new_qty < 0:
            return {'detail': 'total_qty は0以上で入力してください。'}, 400

        old_qty = detail.total_qty
        delta = int((new_qty - old_qty).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

        detail.total_qty = new_qty
        detail.save(update_fields=['total_qty'])

        if delta != 0 and actual.work_date and detail.product_id:
            process, line = LaserActualSerializer._resolve_component_process_line(actual.equipment, detail.product)
            if process and line:
                LaserActualSerializer.apply_backlog_delta_map({
                    (actual.work_date, line.id, process.id, detail.product_id): delta
                })

        return {'detail': '更新しました。'}, 200
