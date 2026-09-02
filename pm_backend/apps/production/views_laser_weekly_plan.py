from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_CEILING

from django.db.models import Q
from masters.models import Product
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models_laser_weekly_plan import LaserWeeklyMaterialGroup, LaserWeeklyPatternInitialProgress, LaserWeeklyPatternManualQuantity, LaserWeeklyPlanManualQuantity, LaserWeeklyPlanTarget
from .models_laser_pattern import LaserPattern
from .models_line_plan import LinePlan
from .models_line_backlog import LineBacklog
from .serializers import LaserWeeklyMaterialGroupSerializer, LaserWeeklyPlanTargetSerializer
from .services.recalc_start_date import _build_workday_helpers, _resolve_calendar_id


class LaserWeeklyPlanTargetViewSet(viewsets.ModelViewSet):
    queryset = LaserWeeklyPlanTarget.objects.select_related('downstream_line', 'product', 'finished_product', 'laser_pattern__processing_freq_pattern')
    serializer_class = LaserWeeklyPlanTargetSerializer
    pagination_class = None


class LaserWeeklyMaterialGroupViewSet(viewsets.ModelViewSet):
    queryset = LaserWeeklyMaterialGroup.objects.prefetch_related('patterns')
    serializer_class = LaserWeeklyMaterialGroupSerializer


class LaserWeeklyPlanViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='downstream-products')
    def downstream_products(self, request):
        try:
            line_id = int(request.query_params['line_id'])
        except (KeyError, TypeError, ValueError):
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        backlog_product_ids = LineBacklog.objects.filter(line_id=line_id).values('product_id')
        products = Product.objects.filter(is_line_final_product=True).filter(
            Q(line_id=line_id) | Q(id__in=backlog_product_ids),
        ).order_by('product_code').values('id', 'product_code', 'product_name')
        return Response(list(products))

    @action(detail=False, methods=['post'], url_path='manual-quantities')
    def save_manual_quantities(self, request):
        quantities = request.data.get('quantities', [])
        if not isinstance(quantities, list):
            return Response({'detail': 'quantities must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        target_ids = {item.get('target_id') for item in quantities if item.get('target_id')}
        targets = {target.id: target for target in LaserWeeklyPlanTarget.objects.filter(id__in=target_ids)}
        for item in quantities:
            try:
                target = targets[int(item['target_id'])]
                plan_date = datetime.strptime(item['plan_date'], '%Y-%m-%d').date()
                sheets_decimal = Decimal(str(item['sheets']))
                if sheets_decimal < 0 or sheets_decimal != sheets_decimal.to_integral_value():
                    raise ValueError
                sheets = int(sheets_decimal)
            except (InvalidOperation, KeyError, TypeError, ValueError):
                return Response({'detail': '手動回数の値が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
            LaserWeeklyPlanManualQuantity.objects.update_or_create(
                target=target, plan_date=plan_date, defaults={'sheets': sheets},
            )
        return Response({'saved_count': len(quantities)})

    @action(detail=False, methods=['post'], url_path='pattern-manual-quantities')
    def save_pattern_manual_quantities(self, request):
        quantities = request.data.get('quantities', [])
        if not isinstance(quantities, list):
            return Response({'detail': 'quantities must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        pattern_ids = {item.get('laser_pattern_id') for item in quantities if item.get('laser_pattern_id')}
        patterns = {pattern.id: pattern for pattern in LaserPattern.objects.filter(id__in=pattern_ids)}
        for item in quantities:
            try:
                pattern = patterns[int(item['laser_pattern_id'])]
                plan_date = datetime.strptime(item['plan_date'], '%Y-%m-%d').date()
                sheets_decimal = Decimal(str(item['sheets']))
                if sheets_decimal < 0 or sheets_decimal != sheets_decimal.to_integral_value():
                    raise ValueError
                sheets = int(sheets_decimal)
            except (InvalidOperation, KeyError, TypeError, ValueError):
                return Response({'detail': '手動回数の値が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
            LaserWeeklyPatternManualQuantity.objects.update_or_create(
                laser_pattern=pattern, plan_date=plan_date, defaults={'sheets': sheets},
            )
        return Response({'saved_count': len(quantities)})

    @action(detail=False, methods=['post'], url_path='save-initial-progress')
    def save_initial_progress(self, request):
        items = request.data.get('items', [])
        if not isinstance(items, list):
            return Response({'detail': 'items must be a list'}, status=status.HTTP_400_BAD_REQUEST)
        for item in items:
            try:
                laser_pattern_id = int(item['laser_pattern_id'])
                week_start_date = datetime.strptime(item['week_start_date'], '%Y-%m-%d').date()
                initial_progress = int(item['initial_progress'])
                is_locked = bool(item.get('is_locked', True))
            except (KeyError, TypeError, ValueError):
                return Response({'detail': '期首進度の値が不正です。'}, status=status.HTTP_400_BAD_REQUEST)
            LaserWeeklyPatternInitialProgress.objects.update_or_create(
                laser_pattern_id=laser_pattern_id, week_start_date=week_start_date,
                defaults={'initial_progress': initial_progress, 'is_locked': is_locked},
            )
        return Response({'saved_count': len(items)})

    def _calc_freq_initial_sheets(self, pattern_row, automatic_daily, dates, is_workday_fn=None):
        """加工頻度に基づいてmanual_sheetsの初期値を計算する。"""
        freq_type = pattern_row.get('freq_type', 'DAILY')
        if freq_type == 'DAILY':
            return {day: daily['automatic_sheets'] for day, daily in automatic_daily.items()}

        sorted_days = [d.isoformat() for d in dates]
        result = {day: 0 for day in sorted_days}

        def _is_biz(d):
            return is_workday_fn(d) if is_workday_fn else d.weekday() < 5

        if freq_type == 'WEEKLY':
            dow = pattern_row.get('freq_day_of_week')
            if dow is None:
                return {day: daily['automatic_sheets'] for day, daily in automatic_daily.items()}
            processing_days = [d for d in sorted_days if datetime.strptime(d, '%Y-%m-%d').date().weekday() == dow]
            if not processing_days:
                return {day: daily['automatic_sheets'] for day, daily in automatic_daily.items()}
            for i, proc_day in enumerate(processing_days):
                if i + 1 < len(processing_days):
                    next_proc = processing_days[i + 1]
                    covered = [d for d in sorted_days if proc_day <= d < next_proc]
                else:
                    covered = [d for d in sorted_days if d >= proc_day]
                total = sum(automatic_daily.get(d, {}).get('automatic_sheets', 0) for d in covered)
                result[proc_day] = total

        elif freq_type == 'EVERY_N_DAYS':
            interval = pattern_row.get('freq_interval_days') or 2
            start_date = pattern_row.get('freq_start_date')
            if not start_date:
                return {day: daily['automatic_sheets'] for day, daily in automatic_daily.items()}
            # 開始日より前の日は自回数をそのまま使用（毎日加工扱い）
            for day_str in sorted_days:
                day_date = datetime.strptime(day_str, '%Y-%m-%d').date()
                if day_date < start_date:
                    result[day_str] = automatic_daily.get(day_str, {}).get('automatic_sheets', 0)
            # 開始日から表示開始日までの営業日数をカウント（カレンダー考慮）
            biz_days_from_start = 0
            scan_date = start_date
            first_day = dates[0] if dates else None
            if first_day and scan_date < first_day:
                while scan_date < first_day:
                    scan_date += timedelta(days=1)
                    if _is_biz(scan_date):
                        biz_days_from_start += 1
            # 加工日の特定（開始日以降のみ）
            processing_indices = set()
            for idx, day_str in enumerate(sorted_days):
                day_date = datetime.strptime(day_str, '%Y-%m-%d').date()
                if day_date < start_date:
                    continue
                if day_date == start_date or (biz_days_from_start % interval == 0):
                    processing_indices.add(idx)
                biz_days_from_start += 1
            proc_list = sorted(processing_indices)
            for pi, idx in enumerate(proc_list):
                if pi + 1 < len(proc_list):
                    next_idx = proc_list[pi + 1]
                else:
                    next_idx = len(sorted_days)
                covered = sorted_days[idx:next_idx]
                total = sum(automatic_daily.get(d, {}).get('automatic_sheets', 0) for d in covered)
                result[sorted_days[idx]] = total

        return result

    def _calc_auto_initial_progress(self, pattern_id, week_start_date, targets, pattern_manual_map, plan_map, order_map, target_demand_dates):
        prev_start = week_start_date - timedelta(days=7)
        prev_dates = [prev_start + timedelta(days=i) for i in range(7) if (prev_start + timedelta(days=i)).weekday() < 5]
        if not prev_dates:
            return 0
        prev_locked = LaserWeeklyPatternInitialProgress.objects.filter(
            laser_pattern_id=pattern_id, week_start_date=prev_start, is_locked=True,
        ).first()
        prev_initial = prev_locked.initial_progress if prev_locked else 0
        cum_auto = 0
        cum_manual = 0
        pattern_targets = [t for t in targets if t.laser_pattern_id == pattern_id]
        for day in prev_dates:
            day_auto = 0
            for target in pattern_targets:
                take = next((x.units_per_shot for x in target.laser_pattern.finished_items.all() if x.finished_product_id == target.finished_product_id), None)
                if not take or take <= 0:
                    continue
                demand_date = target_demand_dates.get((target.id, day))
                if demand_date is None:
                    continue
                key = (target.downstream_line_id, target.product_id, demand_date)
                qty = plan_map[key] if target.quantity_source == 'PLAN_QTY' else order_map[key]
                sheets = int((qty / take).to_integral_value(rounding=ROUND_CEILING)) if qty > 0 else 0
                day_auto += sheets
            cum_auto += day_auto
            manual = pattern_manual_map.get((pattern_id, day), day_auto)
            cum_manual += manual
        return prev_initial + cum_manual - cum_auto

    def list(self, request):
        try:
            requested_start_date = datetime.strptime(request.query_params['start_date'], '%Y-%m-%d').date()
        except (KeyError, ValueError):
            return Response({'detail': 'start_date is required (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
        end_date_param = request.query_params.get('end_date')
        if end_date_param:
            try:
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
            except ValueError:
                return Response({'detail': 'end_date must be YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
            if end_date < requested_start_date:
                return Response({'detail': 'end_date must be on or after start_date'}, status=status.HTTP_400_BAD_REQUEST)
            start_date = requested_start_date
            dates = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1) if (start_date + timedelta(days=i)).weekday() < 5]
        else:
            start_date = requested_start_date - timedelta(days=requested_start_date.weekday())
            dates = [start_date + timedelta(days=i) for i in range(14) if (start_date + timedelta(days=i)).weekday() < 5]
        if not dates:
            return Response({'detail': '稼働日の範囲を指定してください。'}, status=status.HTTP_400_BAD_REQUEST)
        targets = list(LaserWeeklyPlanTarget.objects.filter(is_active=True).select_related('downstream_line', 'product', 'finished_product', 'laser_pattern__equipment__process__line', 'laser_pattern__material', 'laser_pattern__processing_freq_pattern').prefetch_related('laser_pattern__finished_items'))
        manual_map = {
            (item.target_id, item.plan_date): item.sheets
            for item in LaserWeeklyPlanManualQuantity.objects.filter(
                target_id__in=[target.id for target in targets],
                plan_date__range=(dates[0], dates[-1]),
            )
        }
        prev_week_start = start_date - timedelta(days=7)
        pattern_manual_map = {
            (item.laser_pattern_id, item.plan_date): item.sheets
            for item in LaserWeeklyPatternManualQuantity.objects.filter(
                laser_pattern_id__in=[target.laser_pattern_id for target in targets],
                plan_date__range=(prev_week_start, dates[-1]),
            )
        }
        target_demand_dates = {}
        workday_helpers = {}
        for target in targets:
            laser_process = target.laser_pattern.equipment.process
            laser_line_id = laser_process.line_id if laser_process else None
            calendar_id = _resolve_calendar_id(laser_line_id)
            shift_working_days = workday_helpers.setdefault(
                calendar_id,
                _build_workday_helpers(calendar_id),
            )[2]
            prev_dates = [prev_week_start + timedelta(days=i) for i in range(7) if (prev_week_start + timedelta(days=i)).weekday() < 5]
            for day in prev_dates + dates:
                target_demand_dates[(target.id, day)] = shift_working_days(day, target.lead_time_days)

        plan_map, order_map = defaultdict(Decimal), defaultdict(Decimal)
        if targets:
            demand_dates = set(target_demand_dates.values())
            for plan in LinePlan.objects.filter(line_id__in={t.downstream_line_id for t in targets}, product_id__in={t.product_id for t in targets}, plan_date__in=demand_dates):
                plan_map[(plan.line_id, plan.product_id, plan.plan_date)] += Decimal(plan.plan_qty or 0)
            for backlog in LineBacklog.objects.filter(line_id__in={t.downstream_line_id for t in targets}, product_id__in={t.product_id for t in targets}, plan_date__in=demand_dates, sequence_no=0):
                order_map[(backlog.line_id, backlog.product_id, backlog.plan_date)] += Decimal(backlog.order_qty or 0)
        rows, totals, pattern_totals, material_totals = [], defaultdict(Decimal), {}, {}
        for target in targets:
            take = next((x.units_per_shot for x in target.laser_pattern.finished_items.all() if x.finished_product_id == target.finished_product_id), None)
            name = target.laser_pattern.equipment.equipment_name or ''
            machine = 'TK' if '1' in name or '１' in name else 'AJ' if '2' in name or '２' in name else ''
            if not take or take <= 0 or not machine:
                continue
            hours = Decimal(target.laser_pattern.process_time_min or 0) / Decimal(60)
            daily = {}
            for day in dates:
                key = (target.downstream_line_id, target.product_id, target_demand_dates[(target.id, day)])
                qty = plan_map[key] if target.quantity_source == 'PLAN_QTY' else order_map[key]
                sheets = int((qty / take).to_integral_value(rounding=ROUND_CEILING)) if qty > 0 else 0
                manual_sheets = sheets
                daily[day.isoformat()] = {
                    'demand_qty': str(qty),
                    'automatic_sheets': sheets,
                    'manual_sheets': manual_sheets,
                }
                freq = target.laser_pattern.processing_freq_pattern
                pattern_row = pattern_totals.setdefault(target.laser_pattern_id, {
                    'laser_pattern_id': target.laser_pattern_id,
                    'pattern_no': target.laser_pattern.pattern_no,
                    'thickness': str(target.laser_pattern.material.size_thickness or ''),
                    'machine': machine,
                    'hours_per_sheet': str(hours),
                    'material_id': target.laser_pattern.material_id,
                    'material_code': target.laser_pattern.material.product_code,
                    'material_name': target.laser_pattern.material.product_name,
                    'order_lot_min': target.laser_pattern.material.order_lot_min or 1,
                    'order_lot_multiple': target.laser_pattern.material.order_lot_multiple or 1,
                    'freq_type': freq.frequency_type if freq else 'DAILY',
                    'freq_day_of_week': freq.day_of_week if freq else None,
                    'freq_interval_days': freq.interval_days if freq else None,
                    'freq_start_date': target.laser_pattern.processing_start_date,
                    'calendar_id': calendar_id,
                    'product_codes': set(),
                    'downstream_line_names': set(),
                    'take_qtys': set(),
                    'lead_time_days': set(),
                    'daily': defaultdict(lambda: {
                        'demand_qty': Decimal('0'),
                        'automatic_sheets': 0,
                        'manual_sheets': 0,
                    }),
                })
                pattern_row['downstream_line_names'].add(target.downstream_line.line_name)
                pattern_row['product_codes'].add(target.product.product_code)
                pattern_row['take_qtys'].add(str(take))
                pattern_row['lead_time_days'].add(target.lead_time_days)
                pattern_daily = pattern_row['daily'][day.isoformat()]
                pattern_daily['demand_qty'] += qty
                pattern_daily['automatic_sheets'] += sheets
                pattern_daily['manual_sheets'] += manual_sheets
            rows.append({'id': target.id, 'downstream_line_name': target.downstream_line.line_name, 'product_code': target.product.product_code, 'product_name': target.product.product_name, 'pattern_no': target.laser_pattern.pattern_no, 'take_qty': str(take), 'thickness': str(target.laser_pattern.material.size_thickness or ''), 'machine': machine, 'hours_per_sheet': str(hours), 'lead_time_days': target.lead_time_days, 'quantity_source': target.quantity_source, 'daily': daily})
        pattern_rows = []
        for pattern_row in sorted(pattern_totals.values(), key=lambda item: item['pattern_no']):
            pattern_row['downstream_line_names'] = sorted(pattern_row['downstream_line_names'])
            pattern_row['representative_product_code'] = sorted(pattern_row.pop('product_codes'))[0]
            pattern_row['take_qtys'] = sorted(pattern_row['take_qtys'], key=Decimal)
            pattern_row['lead_time_days'] = sorted(pattern_row['lead_time_days'])
            automatic_daily = pattern_row['daily']
            pattern_row['daily'] = {}
            material_row = material_totals.setdefault(pattern_row['material_id'], {
                'material_id': pattern_row['material_id'],
                'material_code': pattern_row['material_code'],
                'material_name': pattern_row['material_name'],
                'thickness': pattern_row['thickness'],
                'order_lot_min': pattern_row.get('order_lot_min', 1),
                'order_lot_multiple': pattern_row.get('order_lot_multiple', 1),
                'daily': defaultdict(int),
            })
            cal_id = pattern_row.get('calendar_id')
            is_workday_fn = workday_helpers[cal_id][0] if cal_id in workday_helpers else None
            freq_initial = self._calc_freq_initial_sheets(
                pattern_row, automatic_daily, dates, is_workday_fn,
            )
            has_any_saved = any(
                (pattern_row['laser_pattern_id'], d) in pattern_manual_map for d in dates
            )
            for day, daily in automatic_daily.items():
                day_date = datetime.strptime(day, '%Y-%m-%d').date()
                if has_any_saved:
                    manual_sheets = pattern_manual_map.get((pattern_row['laser_pattern_id'], day_date), daily['automatic_sheets'])
                else:
                    manual_sheets = freq_initial.get(day, daily['automatic_sheets'])
                pattern_row['daily'][day] = {
                    'demand_qty': str(daily['demand_qty']),
                    'automatic_sheets': daily['automatic_sheets'],
                    'manual_sheets': manual_sheets,
                }
                totals[(pattern_row['laser_pattern_id'], day, pattern_row['machine'])] += manual_sheets
                material_row['daily'][day] += manual_sheets
            pattern_rows.append(pattern_row)

        initial_progress_map = {
            item.laser_pattern_id: item
            for item in LaserWeeklyPatternInitialProgress.objects.filter(
                laser_pattern_id__in=[pr['laser_pattern_id'] for pr in pattern_rows],
                week_start_date=start_date,
            )
        }
        for pattern_row in pattern_rows:
            pid = pattern_row['laser_pattern_id']
            saved = initial_progress_map.get(pid)
            if saved and saved.is_locked:
                pattern_row['initial_progress'] = saved.initial_progress
                pattern_row['initial_progress_locked'] = True
            else:
                auto_val = self._calc_auto_initial_progress(
                    pid, start_date, targets, pattern_manual_map,
                    plan_map, order_map, target_demand_dates,
                )
                pattern_row['initial_progress'] = auto_val
                pattern_row['initial_progress_locked'] = False

        material_rows = []
        for material_row in sorted(material_totals.values(), key=lambda item: item['material_code']):
            material_row['daily'] = dict(material_row['daily'])
            material_rows.append(material_row)
        return Response({
            'start_date': start_date.isoformat(),
            'dates': [d.isoformat() for d in dates],
            'rows': rows,
            'pattern_rows': pattern_rows,
            'material_rows': material_rows,
            'pattern_totals': {':'.join(map(str, key)): str(value) for key, value in totals.items()},
        })
