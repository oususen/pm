from dataclasses import dataclass
from datetime import datetime, timedelta, time, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.db.models import Q
import logging
from rest_framework.exceptions import ValidationError

from masters.models import RoutingStep, ProcessCycleTime, Line, Calendar, CalendarDay, WorkPattern, BreakTime, BOM, BOMItem, Product
from ..models_line_backlog import LineBacklog

logger = logging.getLogger(__name__)

@dataclass
class ProcessSpec:
    process_id: int
    process_name: str
    process_number: int
    cycle_time_minutes: float
    setup_time_minutes: float
    parallel_count: int
    parallel_group: int = 1
    output_product_id: Optional[int] = None
    output_product_code: str = ''
    output_product_name: str = ''
    transfer_time_minutes: float = 0.0


class LineWorkCalendar:
    def __init__(self, line: Line):
        self.line = line
        self.calendar_id = line.calendar_id or Calendar.objects.filter(calendar_code='tiera_muke').values_list('id', flat=True).first()
        self._calendar_cache: Dict = {}
        self._pattern_cache: Dict = {}
        self._break_cache: Dict = {}
        self._segments_cache: Dict = {}

    def _get_calendar_day(self, target_date):
        if not self.calendar_id:
            return None
        if target_date in self._calendar_cache:
            return self._calendar_cache[target_date]
        cal = CalendarDay.objects.filter(calendar_id=self.calendar_id, target_date=target_date).first()
        self._calendar_cache[target_date] = cal
        return cal

    def _get_work_pattern(self, pattern_id):
        if not pattern_id:
            return None
        if pattern_id in self._pattern_cache:
            return self._pattern_cache[pattern_id]
        pattern = WorkPattern.objects.filter(id=pattern_id).first()
        self._pattern_cache[pattern_id] = pattern
        return pattern

    def _get_breaks(self, pattern_id):
        if not pattern_id:
            return []
        if pattern_id in self._break_cache:
            return self._break_cache[pattern_id]
        breaks = list(BreakTime.objects.filter(work_pattern_id=pattern_id).order_by('order'))
        self._break_cache[pattern_id] = breaks
        return breaks

    def _time_to_minutes(self, t: time) -> int:
        return t.hour * 60 + t.minute

    def _build_segments(self, target_date) -> List[Tuple[datetime, datetime]]:
        cal = self._get_calendar_day(target_date)
        if cal and cal.is_working_day is False:
            return []

        pattern = self._get_work_pattern(cal.work_pattern_id if cal else None)
        start_time = pattern.start_time if pattern and pattern.start_time else time(8, 0)
        start_min = self._time_to_minutes(start_time)

        if pattern and pattern.end_time:
            end_min = self._time_to_minutes(pattern.end_time)
            if end_min <= start_min:
                end_min += 24 * 60
        else:
            work_minutes = cal.work_minutes if cal and cal.work_minutes is not None else 480
            end_min = start_min + int(work_minutes)

        breaks = []
        if pattern:
            for br in self._get_breaks(pattern.id):
                br_start = self._time_to_minutes(br.break_start)
                br_end = self._time_to_minutes(br.break_end)
                if br_end <= br_start:
                    br_end += 24 * 60
                breaks.append((br_start, br_end))
            breaks.sort(key=lambda b: b[0])

        base = datetime.combine(target_date, time(0, 0))
        segments = []
        cursor = start_min
        for br_start, br_end in breaks:
            if br_start > cursor:
                segments.append((base + timedelta(minutes=cursor), base + timedelta(minutes=min(br_start, end_min))))
            cursor = max(cursor, br_end)
        if cursor < end_min:
            segments.append((base + timedelta(minutes=cursor), base + timedelta(minutes=end_min)))
        return segments

    def get_segments(self, target_date) -> List[Tuple[datetime, datetime]]:
        if target_date in self._segments_cache:
            return self._segments_cache[target_date]
        segments = self._build_segments(target_date)
        self._segments_cache[target_date] = segments
        return segments

    def _get_previous_working_end(self, start_date):
        check_date = start_date - timedelta(days=1)
        while True:
            segments = self.get_segments(check_date)
            if segments:
                return segments[-1][1]
            check_date -= timedelta(days=1)

    def _get_next_working_start(self, start_date):
        check_date = start_date + timedelta(days=1)
        while True:
            segments = self.get_segments(check_date)
            if segments:
                return segments[0][0]
            check_date += timedelta(days=1)

    def _get_workday_date(self, dt: datetime):
        segments = self.get_segments(dt.date())
        if not segments or dt < segments[0][0]:
            prev_date = dt.date() - timedelta(days=1)
            prev_segments = self.get_segments(prev_date)
            if prev_segments and prev_segments[-1][1] >= dt:
                return prev_date
        return dt.date()

    def _find_segment_index_before_or_containing(self, dt, segments):
        for i in range(len(segments) - 1, -1, -1):
            start, end = segments[i]
            if start <= dt <= end:
                return i
            if dt > end:
                return i
        return None

    def _find_segment_index_containing_or_after(self, dt, segments):
        for i, (start, end) in enumerate(segments):
            if start <= dt <= end:
                return i
            if dt < start:
                return i
        return None

    def subtract_working_minutes(self, end_dt: datetime, minutes: float) -> datetime:
        remaining = minutes
        current = end_dt
        while remaining > 0:
            work_date = self._get_workday_date(current)
            segments = self.get_segments(work_date)
            if not segments:
                current = self._get_previous_working_end(work_date)
                continue
            idx = self._find_segment_index_before_or_containing(current, segments)
            if idx is None:
                current = self._get_previous_working_end(work_date)
                continue
            seg_start, seg_end = segments[idx]
            if current > seg_end:
                current = seg_end
            if current < seg_start:
                current = self._get_previous_working_end(work_date)
                continue
            available = (current - seg_start).total_seconds() / 60
            if remaining <= available:
                return current - timedelta(minutes=remaining)
            remaining -= available
            current = seg_start
            if idx > 0:
                current = segments[idx - 1][1]
            else:
                current = self._get_previous_working_end(work_date)
        return current

    def add_working_minutes(self, start_dt: datetime, minutes: float) -> datetime:
        remaining = minutes
        current = start_dt
        while remaining > 0:
            work_date = self._get_workday_date(current)
            segments = self.get_segments(work_date)
            if not segments:
                current = self._get_next_working_start(work_date)
                continue
            idx = self._find_segment_index_containing_or_after(current, segments)
            if idx is None:
                current = self._get_next_working_start(work_date)
                continue
            seg_start, seg_end = segments[idx]
            if current < seg_start:
                current = seg_start
            available = (seg_end - current).total_seconds() / 60
            if remaining <= available:
                return current + timedelta(minutes=remaining)
            remaining -= available
            current = seg_end
            if idx + 1 < len(segments):
                current = segments[idx + 1][0]
            else:
                current = self._get_next_working_start(work_date)
        return current

    def get_day_end(self, target_date):
        segments = self.get_segments(target_date)
        if segments:
            return segments[-1][1]
        return self._get_previous_working_end(target_date)


def _pick_cycle_time(step: RoutingStep, product_id: int, plan_date) -> Optional[ProcessCycleTime]:
    candidates = ProcessCycleTime.objects.filter(
        process_id=step.process_id,
        product_id=product_id,
        is_active=True,
    ).filter(Q(line_id=step.line_id) | Q(line__isnull=True))
    best = None
    for ct in candidates:
        if ct.valid_from and plan_date < ct.valid_from:
            continue
        if ct.valid_to and plan_date > ct.valid_to:
            continue
        if best is None:
            best = ct
            continue
        if best.line_id is None and ct.line_id == step.line_id:
            best = ct
    return best


def _get_cycle_setup(step: RoutingStep, product_id: int, plan_date) -> Tuple[float, float]:
    ct = _pick_cycle_time(step, product_id, plan_date)
    if not ct and step.output_product_id and step.output_product_id != product_id:
        ct = _pick_cycle_time(step, step.output_product_id, plan_date)
    if not ct and step.routing_id and step.routing.product_id and step.routing.product_id != product_id:
        ct = _pick_cycle_time(step, step.routing.product_id, plan_date)
    if ct:
        return float(ct.cycle_time_min or 0), float(ct.setup_time_min or 0)
    if step.time_unit == 'MINUTE' and step.duration_min is not None:
        return float(step.duration_min or 0), 0.0
    return 0.0, 0.0


def _build_process_specs(steps: List[RoutingStep], plan_qty: Decimal, plan_date, product_id: int) -> List[ProcessSpec]:
    specs = []
    for step in steps:
        output_product = step.output_product or (step.routing.product if step.routing_id else None)
        cycle_time_min, setup_time_min = _get_cycle_setup(step, product_id, plan_date)
        parallel_count = step.parallel_count or 1
        parallel_group = getattr(step, 'parallel_group', 1) or 1
        specs.append(ProcessSpec(
            process_id=step.process_id,
            process_name=step.process.process_name if step.process_id else '',
            process_number=step.step_no or 0,
            cycle_time_minutes=cycle_time_min,
            setup_time_minutes=setup_time_min,
            parallel_count=parallel_count,
            parallel_group=parallel_group,
            output_product_id=output_product.id if output_product else None,
            output_product_code=output_product.product_code if output_product else '',
            output_product_name=output_product.product_name if output_product else '',
            transfer_time_minutes=float(getattr(step, 'transfer_time_minutes', 0.0)),
        ))
    return specs


def _calculate_total_minutes(spec: ProcessSpec, quantity: Decimal) -> float:
    if spec.cycle_time_minutes <= 0:
        return 0.0
    return (spec.cycle_time_minutes * float(quantity)) + spec.setup_time_minutes


def _pick_active_bom(parent_product_id: int, plan_date):
    return BOM.objects.filter(
        parent_product_id=parent_product_id,
        is_active=True,
        valid_from__lte=plan_date,
    ).filter(Q(valid_to__gte=plan_date) | Q(valid_to__isnull=True)).order_by('-valid_from').first()


def _build_bom_multiplier_map(final_product_id: int, plan_date) -> Dict[int, Decimal]:
    multipliers: Dict[int, Decimal] = {final_product_id: Decimal('1')}
    expanded: Dict[int, Decimal] = {final_product_id: Decimal('0')}
    queue = [final_product_id]
    while queue:
        product_id = queue.pop(0)
        total_mult = multipliers.get(product_id, Decimal('0'))
        prev_expanded = expanded.get(product_id, Decimal('0'))
        if total_mult <= prev_expanded:
            continue
        delta = total_mult - prev_expanded
        expanded[product_id] = total_mult

        bom = _pick_active_bom(product_id, plan_date)
        if not bom:
            continue
        for item in BOMItem.objects.filter(bom_id=bom.id):
            if item.quantity is None:
                continue
            qty = Decimal(item.quantity)
            if item.loss_rate is not None:
                qty = qty * (Decimal('1') + Decimal(item.loss_rate))
            child_id = item.child_product_id
            multipliers[child_id] = multipliers.get(child_id, Decimal('0')) + (delta * qty)
            queue.append(child_id)
    return multipliers


def _build_coproduct_parent_map(plan_date) -> Dict[int, Product]:
    coproduct_boms = BOM.objects.filter(
        is_coproduct=True,
        is_active=True,
        valid_from__lte=plan_date,
    ).filter(Q(valid_to__gte=plan_date) | Q(valid_to__isnull=True)).select_related('parent_product')
    parent_map: Dict[int, Product] = {}
    for bom in coproduct_boms:
        for item in bom.items.select_related('child_product'):
            if item.child_product_id:
                parent_map[item.child_product_id] = bom.parent_product
    return parent_map


def _is_coproduct_sub_process(spec: ProcessSpec, coproduct_parent_map: Dict[int, Product]) -> bool:
    """連産品BOMの子品目を出力する工程かどうかを判定（名前依存なし）"""
    return bool(spec.output_product_id and spec.output_product_id in coproduct_parent_map)


def _overlaps(start: datetime, end: datetime, item: Dict) -> bool:
    return start < item['end'] and end > item['start']


def _ensure_resource_lanes(resource_schedules: Dict[int, List[List[Dict]]], process_id: int, parallel_count: int):
    lanes = resource_schedules.setdefault(process_id, [])
    while len(lanes) < parallel_count:
        lanes.append([])
    return lanes


def _find_available_lane(lanes: List[List[Dict]], start: datetime, end: datetime) -> Optional[int]:
    for idx, lane in enumerate(lanes):
        has_conflict = False
        for item in lane:
            if _overlaps(start, end, item):
                has_conflict = True
                break
        if not has_conflict:
            return idx
    return None


def _latest_conflict_start(lanes: List[List[Dict]], start: datetime, end: datetime) -> Optional[datetime]:
    latest = None
    for lane in lanes:
        for item in lane:
            if _overlaps(start, end, item):
                if latest is None or item['start'] > latest:
                    latest = item['start']
    return latest


def _latest_conflict_end(lanes: List[List[Dict]], start: datetime, end: datetime) -> Optional[datetime]:
    latest = None
    for lane in lanes:
        for item in lane:
            if _overlaps(start, end, item):
                if latest is None or item['end'] > latest:
                    latest = item['end']
    return latest


def _reserve_process_slot_forward(calendar: LineWorkCalendar, target_start_time: datetime, minutes: float,
                                  lanes: List[List[Dict]]):
    start_time = target_start_time
    attempts = 0
    while True:
        end_time = calendar.add_working_minutes(start_time, minutes)
        lane_idx = _find_available_lane(lanes, start_time, end_time)
        if lane_idx is not None:
            return start_time, end_time, lane_idx

        conflict_end = _latest_conflict_end(lanes, start_time, end_time)
        if conflict_end and conflict_end > start_time:
            start_time = conflict_end
        else:
            start_time = calendar.add_working_minutes(start_time, 1)

        attempts += 1
        if attempts > 10000:
            logger.warning('gantt_plans: no available slot found after %s attempts for %s minutes from %s', attempts, minutes, target_start_time)
            # フォールバック: 最初のレーンにスロットを割り当て（重複が発生する可能性あり）
            return start_time, calendar.add_working_minutes(start_time, minutes), 0


def _reserve_process_slot_backward(calendar: LineWorkCalendar, target_end_time: datetime, minutes: float,
                                   lanes: List[List[Dict]]):
    end_time = target_end_time
    attempts = 0
    while True:
        start_time = calendar.subtract_working_minutes(end_time, minutes)
        lane_idx = _find_available_lane(lanes, start_time, end_time)
        if lane_idx is not None:
            return start_time, end_time, lane_idx
        conflict_start = _latest_conflict_start(lanes, start_time, end_time)
        if conflict_start and conflict_start < end_time:
            end_time = conflict_start
        else:
            end_time = calendar.subtract_working_minutes(end_time, 1)
        attempts += 1
        if attempts > 10000:
            logger.warning('gantt_plans: no available slot found after %s attempts', attempts)
            return start_time, end_time, 0


def generate_line_gantt_plans(line_id: int, start_date, end_date, clear_existing: bool = False, final_process_start_time: str = None, adjust_to_break_end: bool = False):
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    target_time_obj = None
    if final_process_start_time:
        try:
            target_time_obj = datetime.strptime(final_process_start_time, '%H:%M').time()
        except ValueError:
            logger.warning('Invalid time format for final_process_start_time: %s', final_process_start_time)

    line = Line.objects.filter(id=line_id).first()
    if not line:
        raise ValueError('line_id not found')

    # 日別設定を読み込み
    from ..models_line_daily_schedule_setting import LineDailyScheduleSetting
    daily_settings_qs = LineDailyScheduleSetting.objects.filter(
        line_id=line_id,
        plan_date__gte=start_date,
        plan_date__lte=end_date,
    )
    daily_settings_map = {}
    for setting in daily_settings_qs:
        daily_settings_map[setting.plan_date] = {
            'final_process_start_time': setting.final_process_start_time,
            'adjust_to_break_end': setting.adjust_to_break_end,
        }

    calendar = LineWorkCalendar(line)
    qs_all = LineBacklog.objects.filter(
        line_id=line_id,
        plan_date__gte=start_date,
        plan_date__lte=end_date,
        plan_qty__gt=0,
    ).select_related('product', 'process')
    qs_final = qs_all.filter(product__is_line_final_product=True)
    qs = qs_final if qs_final.exists() else qs_all

    logger.info(
        'gantt_plans: line_id=%s start=%s end=%s clear=%s backlog_all=%s backlog_final=%s using=%s',
        line_id, start_date, end_date, clear_existing, qs_all.count(), qs_final.count(),
        'final' if qs is qs_final else 'all'
    )

    # 最終工程のプロセスを特定
    product_ids = list({obj.product_id for obj in qs})
    steps_qs = RoutingStep.objects.filter(
        line_id=line_id
    ).select_related('routing', 'process', 'output_product')

    steps_by_product: Dict[int, List[RoutingStep]] = {}
    for step in steps_qs:
        product_keys = []
        if step.output_product_id:
            product_keys.append(step.output_product_id)
        if step.routing_id and step.routing.product_id:
            product_keys.append(step.routing.product_id)
        for pid in set(product_keys):
            steps_by_product.setdefault(pid, []).append(step)

    logger.info(
        'gantt_plans: product_ids=%s steps_products=%s steps_total=%s',
        len(product_ids), len(steps_by_product.keys()), steps_qs.count()
    )

    step_no_by_process = {}
    for steps in steps_by_product.values():
        for step in steps:
            step_no_by_process.setdefault(step.process_id, step.step_no or 0)

    default_steps = sorted(steps_qs, key=lambda s: (s.step_no or 0, getattr(s, 'parallel_group', 1) or 1))

    grouped = {}
    for obj in qs:
        key = (obj.product_id, obj.plan_date, obj.sequence_no or 0)
        current = grouped.get(key)
        obj_step_no = step_no_by_process.get(obj.process_id, 0)
        if not current:
            grouped[key] = (obj, obj_step_no)
            continue
        _, current_step_no = current
        if obj_step_no >= current_step_no:
            grouped[key] = (obj, obj_step_no)
    base_plans = [item[0] for item in grouped.values()]
    base_plans.sort(key=lambda o: (o.plan_date, (o.sequence_no or 0), o.product_id))
    logger.info('gantt_plans: base_plans grouped=%s', len(base_plans))

    if clear_existing:
        plan_ids = []
        for obj in base_plans:
            qty_label = str(obj.plan_qty).rstrip('0').rstrip('.')
            if '.' in qty_label:
                qty_label = qty_label.replace('.', 'p')
            sequence = obj.sequence_no or 0
            plan_ids.append(f"{obj.product.product_code}_{obj.plan_date.strftime('%Y%m%d')}_{qty_label}_{sequence}")
        if plan_ids:
            from ..models_line_gantt_plan import LineGanttPlan
            LineGanttPlan.objects.filter(plan_id__in=plan_ids).delete()

    resource_schedules: Dict[int, List[List[Dict]]] = {}

    # 計画期間全体で最も早い稼働開始時刻を取得
    line_earliest_start = None
    check_date = start_date
    while not line_earliest_start:
        segments = calendar.get_segments(check_date)
        if segments:
            line_earliest_start = segments[0][0]
            break
        check_date += timedelta(days=1)
        if check_date > end_date + timedelta(days=30):  # 安全のための上限
            break
    if not line_earliest_start:
        line_earliest_start = datetime.combine(start_date, time(8, 0))

    # 各工程の終了時刻を追跡（plan_dateとprocess_idごと）
    # キー: (plan_date, process_id), 値: 前のsequenceの終了時刻
    previous_process_end_by_date: Dict[Tuple[date, int], datetime] = {}

    plans = []
    for obj in base_plans:
        product = obj.product
        multiplier_map = _build_bom_multiplier_map(product.id, obj.plan_date)
        coproduct_parent_map = _build_coproduct_parent_map(obj.plan_date)
        steps = sorted(steps_by_product.get(product.id, []), key=lambda s: (s.step_no or 0, getattr(s, 'parallel_group', 1) or 1))
        if not steps:
            steps = default_steps
        if not steps:
            continue
        process_specs = _build_process_specs(steps, obj.plan_qty, obj.plan_date, product.id)
        process_specs.sort(key=lambda s: (s.process_number or 0, s.parallel_group or 1))

        qty_label = str(obj.plan_qty).rstrip('0').rstrip('.')
        if '.' in qty_label:
            qty_label = qty_label.replace('.', 'p')
        sequence = obj.sequence_no or 0
        plan_id = f"{product.product_code}_{obj.plan_date.strftime('%Y%m%d')}_{qty_label}_{sequence}"

        coproduct_groups = {}
        for spec in process_specs:
            if not _is_coproduct_sub_process(spec, coproduct_parent_map):
                continue
            parent = coproduct_parent_map[spec.output_product_id]
            group_key = f"{plan_id}_{spec.process_id}_{parent.id}"
            qty_product_id = spec.output_product_id or obj.product_id
            process_qty = multiplier_map.get(qty_product_id, Decimal('1')) * obj.plan_qty
            total_minutes = _calculate_total_minutes(spec, process_qty)
            effective_minutes = total_minutes / max(spec.parallel_count, 1)
            group = coproduct_groups.get(group_key)
            if not group:
                coproduct_groups[group_key] = {
                    'max_total_minutes': total_minutes,
                    'max_effective_minutes': effective_minutes,
                    'max_qty': process_qty,
                    'cycle_time_minutes': spec.cycle_time_minutes,
                    'setup_time_minutes': spec.setup_time_minutes,
                    'order_spec': spec,
                }
                continue
            group['order_spec'] = spec
            if total_minutes > group['max_total_minutes']:
                group['max_total_minutes'] = total_minutes
                group['cycle_time_minutes'] = spec.cycle_time_minutes
                group['setup_time_minutes'] = spec.setup_time_minutes
            if effective_minutes > group['max_effective_minutes']:
                group['max_effective_minutes'] = effective_minutes
            if process_qty > group['max_qty']:
                group['max_qty'] = process_qty

        scheduled_specs = []
        for spec in process_specs:
            if _is_coproduct_sub_process(spec, coproduct_parent_map):
                parent = coproduct_parent_map[spec.output_product_id]
                group_key = f"{plan_id}_{spec.process_id}_{parent.id}"
                group = coproduct_groups.get(group_key)
                if not group or group['order_spec'] is not spec:
                    continue
                scheduled_specs.append({
                    'spec': spec,
                    'process_qty': group['max_qty'],
                    'total_minutes': group['max_total_minutes'],
                    'effective_minutes': group['max_effective_minutes'],
                    'cycle_time_minutes': group.get('cycle_time_minutes', spec.cycle_time_minutes),
                    'setup_time_minutes': group.get('setup_time_minutes', spec.setup_time_minutes),
                    'coproduct_group_key': group_key,
                    'coproduct_child_id': None,
                })
                continue
            qty_product_id = spec.output_product_id or obj.product_id
            process_qty = multiplier_map.get(qty_product_id, Decimal('1')) * obj.plan_qty
            total_minutes = _calculate_total_minutes(spec, process_qty)
            effective_minutes = total_minutes / max(spec.parallel_count, 1)
            scheduled_specs.append({
                'spec': spec,
                'process_qty': process_qty,
                'total_minutes': total_minutes,
                'effective_minutes': effective_minutes,
                'cycle_time_minutes': spec.cycle_time_minutes,
                'setup_time_minutes': spec.setup_time_minutes,
                'coproduct_group_key': None,
                'coproduct_child_id': None,
            })

        current_start_time = line_earliest_start

        # 日別設定があればそれを優先、なければグローバル設定を使用
        daily_setting = daily_settings_map.get(obj.plan_date)
        if daily_setting and daily_setting['final_process_start_time']:
            day_target_time_obj = daily_setting['final_process_start_time']
            day_adjust_to_break_end = daily_setting['adjust_to_break_end']
        else:
            day_target_time_obj = target_time_obj
            day_adjust_to_break_end = adjust_to_break_end

        current_sequence_no = obj.sequence_no or 0

        # sequence_no=1かつ目標時刻が指定されている場合、後方スケジューリングを使用
        use_backward_scheduling = current_sequence_no == 1 and day_target_time_obj
        anchor_dt = None

        if use_backward_scheduling:
            anchor_dt = datetime.combine(obj.plan_date, day_target_time_obj)

            # アンカー時刻が稼働時間内かどうかを検証
            segments = calendar.get_segments(obj.plan_date) or []
            found_valid_slot = False
            for i, (seg_start, seg_end) in enumerate(segments):
                if seg_start <= anchor_dt <= seg_end:
                    found_valid_slot = True
                    break
                if day_adjust_to_break_end and i + 1 < len(segments):
                    next_seg_start = segments[i+1][0]
                    if seg_end < anchor_dt < next_seg_start:
                        logger.info('Adjusting anchor time from %s to break end %s', anchor_dt, next_seg_start)
                        anchor_dt = next_seg_start
                        found_valid_slot = True
                        break

            if not found_valid_slot:
                error_msg = f"指定された最終工程開始時刻 ({day_target_time_obj}) はラインの稼働時間外です。"
                raise ValidationError(error_msg)

        processes_plan = []

        if use_backward_scheduling:
            # 後方スケジューリング: 最終工程の開始時刻を固定し、前の工程を後ろから順にスケジュール
            logger.info('gantt_plans: plan_id=%s using backward scheduling, anchor=%s', plan_id, anchor_dt)

            # 各工程の開始・終了時刻を格納するリスト（後で逆順にする）
            scheduled_times: List[Dict] = [None] * len(scheduled_specs)

            # 最終工程の終了時刻を計算
            last_entry = scheduled_specs[-1]
            last_spec = last_entry['spec']
            last_effective_minutes = last_entry['effective_minutes']
            last_end_time = calendar.add_working_minutes(anchor_dt, last_effective_minutes)

            # 最終工程から後方にスケジュール
            current_end_time = last_end_time
            for i in range(len(scheduled_specs) - 1, -1, -1):
                entry = scheduled_specs[i]
                spec = entry['spec']
                effective_minutes = entry['effective_minutes']
                current_cycle_time = entry['cycle_time_minutes']

                # 前のsequenceの同じ工程の終了時刻を考慮
                process_key = (obj.plan_date, spec.process_id)

                if i == len(scheduled_specs) - 1:
                    # 最終工程: アンカー時刻に固定
                    start_time = anchor_dt
                    end_time = current_end_time
                else:
                    # 後方パイプライン制約を適用
                    next_entry = scheduled_specs[i + 1]
                    next_start_time = scheduled_times[i + 1]['start']
                    next_cycle_time = next_entry['cycle_time_minutes']
                    gap_minutes = spec.transfer_time_minutes

                    # 終了-終了制約（後方）: 現工程の終了 <= 次工程の終了 - next_cycle_time - gap
                    e2e_end_limit = calendar.subtract_working_minutes(
                        scheduled_times[i + 1]['end'], next_cycle_time + gap_minutes
                    )

                    # 開始-開始制約（後方）: 現工程の開始 <= 次工程の開始 - cycle_time - gap
                    s2s_end_limit = calendar.subtract_working_minutes(
                        next_start_time, current_cycle_time + gap_minutes
                    )
                    # 開始時刻から終了時刻を逆算
                    s2s_end_from_start = calendar.add_working_minutes(s2s_end_limit, effective_minutes)

                    # より早い終了時刻を採用（後方スケジューリングなので）
                    end_time = min(e2e_end_limit, s2s_end_from_start)
                    start_time = calendar.subtract_working_minutes(end_time, effective_minutes)

                # 前のsequenceの終了時刻があれば、それ以降から開始する必要がある
                if process_key in previous_process_end_by_date:
                    prev_process_end = previous_process_end_by_date[process_key]
                    if start_time < prev_process_end:
                        start_time = prev_process_end
                        end_time = calendar.add_working_minutes(start_time, effective_minutes)
                        logger.info(
                            'gantt_plans: plan_id=%s i=%s adjusted by prev_process_end=%s new_start=%s',
                            plan_id, i, prev_process_end, start_time
                        )

                # リソースレーンに登録
                lanes = _ensure_resource_lanes(resource_schedules, spec.process_id, spec.parallel_count)
                lane_idx = _find_available_lane(lanes, start_time, end_time)
                if lane_idx is None:
                    lane_idx = 0  # フォールバック
                lanes[lane_idx].append({
                    'start': start_time,
                    'end': end_time,
                    'plan_id': plan_id,
                })

                scheduled_times[i] = {'start': start_time, 'end': end_time, 'lane': lane_idx}

                logger.info(
                    'gantt_plans: plan_id=%s i=%s process=%s backward scheduled: start=%s end=%s lane=%s',
                    plan_id, i, spec.process_name, start_time, end_time, lane_idx
                )

            # processes_planを構築（順方向に）
            for i, entry in enumerate(scheduled_specs):
                spec = entry['spec']
                process_qty = entry['process_qty']
                total_minutes = entry['total_minutes']
                effective_minutes = entry['effective_minutes']
                start_time = scheduled_times[i]['start']
                end_time = scheduled_times[i]['end']

                output_product_id = spec.output_product_id
                output_product_code = spec.output_product_code
                output_product_name = spec.output_product_name
                coproduct_group_key = entry['coproduct_group_key']
                coproduct_child_id = entry['coproduct_child_id']
                if output_product_id and output_product_id in coproduct_parent_map:
                    parent = coproduct_parent_map[output_product_id]
                    coproduct_child_id = coproduct_child_id or output_product_id
                    output_product_id = parent.id
                    output_product_code = parent.product_code
                    output_product_name = parent.product_name
                    coproduct_group_key = coproduct_group_key or f"{plan_id}_{spec.process_id}_{parent.id}"

                process_plan = {
                    'process_id': spec.process_id,
                    'process_name': spec.process_name,
                    'process_number': spec.process_number,
                    'parallel_group': spec.parallel_group,
                    'output_product_id': output_product_id,
                    'output_product_code': output_product_code,
                    'output_product_name': output_product_name,
                    'coproduct_group_key': coproduct_group_key,
                    'coproduct_child_id': coproduct_child_id,
                    'quantity': float(process_qty),
                    'cycle_time_minutes': entry['cycle_time_minutes'],
                    'setup_time_minutes': entry['setup_time_minutes'],
                    'total_minutes_required': total_minutes,
                    'effective_minutes': effective_minutes,
                    'parallel_count': spec.parallel_count,
                    'start_time': start_time,
                    'end_time': end_time,
                    'transfer_time_minutes': spec.transfer_time_minutes,
                    'is_continuous': True,
                }
                processes_plan.append(process_plan)

                # この工程の終了時刻を記録（次のsequenceが同じ工程の直後から開始できるように）
                process_key = (obj.plan_date, spec.process_id)
                previous_process_end_by_date[process_key] = end_time

        else:
            # 前方スケジューリング（従来のロジック）
            for i, entry in enumerate(scheduled_specs):
                spec = entry['spec']
                process_qty = entry['process_qty']
                total_minutes = entry['total_minutes']
                effective_minutes = entry['effective_minutes']

                logger.info(
                    'gantt_plans: plan_id=%s i=%s process=%s current_start_time_before=%s',
                    plan_id, i, spec.process_name, current_start_time
                )

                # 前のsequenceの同じ工程の終了時刻があれば、それ以降から開始
                process_key = (obj.plan_date, spec.process_id)
                if process_key in previous_process_end_by_date:
                    prev_process_end = previous_process_end_by_date[process_key]
                    current_start_time = max(current_start_time, prev_process_end)
                    logger.info(
                        'gantt_plans: plan_id=%s adjusted by prev_process_end=%s new_current_start_time=%s',
                        plan_id, prev_process_end, current_start_time
                    )

                lanes = _ensure_resource_lanes(resource_schedules, spec.process_id, spec.parallel_count)
                start_time, end_time, lane_idx = _reserve_process_slot_forward(
                    calendar, current_start_time, effective_minutes, lanes
                )
                logger.info(
                    'gantt_plans: plan_id=%s i=%s process=%s scheduled: start=%s end=%s lane=%s',
                    plan_id, i, spec.process_name, start_time, end_time, lane_idx
                )
                lanes[lane_idx].append({
                    'start': start_time,
                    'end': end_time,
                    'plan_id': plan_id,
                })
                output_product_id = spec.output_product_id
                output_product_code = spec.output_product_code
                output_product_name = spec.output_product_name
                coproduct_group_key = entry['coproduct_group_key']
                coproduct_child_id = entry['coproduct_child_id']
                if output_product_id and output_product_id in coproduct_parent_map:
                    parent = coproduct_parent_map[output_product_id]
                    coproduct_child_id = coproduct_child_id or output_product_id
                    output_product_id = parent.id
                    output_product_code = parent.product_code
                    output_product_name = parent.product_name
                    coproduct_group_key = coproduct_group_key or f"{plan_id}_{spec.process_id}_{parent.id}"

                process_plan = {
                    'process_id': spec.process_id,
                    'process_name': spec.process_name,
                    'process_number': spec.process_number,
                    'parallel_group': spec.parallel_group,
                    'output_product_id': output_product_id,
                    'output_product_code': output_product_code,
                    'output_product_name': output_product_name,
                    'coproduct_group_key': coproduct_group_key,
                    'coproduct_child_id': coproduct_child_id,
                    'quantity': float(process_qty),
                    'cycle_time_minutes': entry['cycle_time_minutes'],
                    'setup_time_minutes': entry['setup_time_minutes'],
                    'total_minutes_required': total_minutes,
                    'effective_minutes': effective_minutes,
                    'parallel_count': spec.parallel_count,
                    'start_time': start_time,
                    'end_time': end_time,
                    'transfer_time_minutes': spec.transfer_time_minutes,
                    'is_continuous': True,
                }
                processes_plan.append(process_plan)

                # この工程の終了時刻を記録（次のsequenceが同じ工程の直後から開始できるように）
                previous_process_end_by_date[process_key] = end_time

                # 次工程の開始時刻を計算（パイプライン処理を考慮）
                if i + 1 < len(scheduled_specs):
                    gap_minutes = spec.transfer_time_minutes

                    # 開始-開始制約: 次工程は現工程の最初の1個が完了・搬送された後に開始可能
                    current_cycle_time = entry['cycle_time_minutes']
                    s2s_limit = calendar.add_working_minutes(start_time, current_cycle_time + gap_minutes)

                    # 次工程開始時刻は S2S 制約のみで決定
                    current_start_time = s2s_limit

                    logger.info(
                        'gantt_plans: plan_id=%s i=%s pipeline: start=%s end=%s cycle=%.1f gap=%.1f '
                        's2s_limit=%s next_start_time=%s',
                        plan_id, i, start_time, end_time, current_cycle_time, gap_minutes,
                        s2s_limit, current_start_time
                    )

        start_dt = processes_plan[0]['start_time'] if processes_plan else current_start_time
        end_dt = processes_plan[-1]['end_time'] if processes_plan else current_start_time

        serialized_plan = []
        for pp in processes_plan:
            pp_copy = pp.copy()
            pp_copy['start_time'] = pp['start_time'].isoformat()
            pp_copy['end_time'] = pp['end_time'].isoformat()
            serialized_plan.append(pp_copy)

        plans.append({
            'plan_id': plan_id,
            'line_id': line_id,
            'product_id': product.id,
            'plan_date': obj.plan_date,
            'plan_qty': obj.plan_qty,
            'sequence_no': obj.sequence_no,
            'start_datetime': start_dt,
            'end_datetime': end_dt,
            'processes_plan': serialized_plan,
        })

    logger.info('gantt_plans: generated_plans=%s', len(plans))
    return plans
