from dataclasses import dataclass
from datetime import datetime, timedelta, time, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import json

from django.db.models import Q
import logging
from rest_framework.exceptions import ValidationError

from masters.models import RoutingStep, Line, Process, Calendar, CalendarDay, WorkPattern, BreakTime, BOM, BOMItem, Product
from system_settings.models import SystemSetting
from ..models_line_backlog import LineBacklog
from ..models_line_plan import LinePlan
from ..models_gantt_display_product_map import GanttDisplayProductMap

logger = logging.getLogger(__name__)

COPRODUCT_CHILD_DISPLAY_EXCEPTION_PRODUCT_CODES = {'YD40002683'}
COPRODUCT_CHILD_DISPLAY_EXCEPTION_PROCESS_CODES = {'4001'}

GANTT_EXCLUDED_PROCESS_RULES_KEY = 'production.gantt_excluded_process_rules'
PROCESS_PREV_DAY_SHIFT_RULES_KEY = 'production.process_prev_day_shift_rules'
PROCESS_GANTT_START_TIME_RULES_KEY = 'production.process_gantt_start_time_rules'


def _load_prev_day_shift_qty_by_line_process() -> Dict[Tuple[str, str], Decimal]:
    row = SystemSetting.objects.filter(key=PROCESS_PREV_DAY_SHIFT_RULES_KEY).first()
    if not row or not row.value:
        return {}
    try:
        raw = json.loads(row.value)
    except Exception:
        return {}
    if not isinstance(raw, list):
        return {}
    result: Dict[Tuple[str, str], Decimal] = {}
    for item in raw:
        line_code = str((item or {}).get('lineCode') or '').strip().upper()
        process_code = str((item or {}).get('processCode') or '').strip().upper()
        shift_qty_raw = (item or {}).get('shiftQty', 0)
        if not line_code or not process_code:
            continue
        try:
            shift_qty = Decimal(str(int(float(shift_qty_raw))))
        except Exception:
            continue
        if shift_qty <= 0:
            continue
        result[(line_code, process_code)] = shift_qty
    return result

def _load_gantt_start_time_by_line_process() -> Dict[Tuple[str, str], time]:
    row = SystemSetting.objects.filter(key=PROCESS_GANTT_START_TIME_RULES_KEY).first()
    if not row or not row.value:
        return {}
    try:
        raw = json.loads(row.value)
    except Exception:
        return {}
    if not isinstance(raw, list):
        return {}
    result: Dict[Tuple[str, str], time] = {}
    for item in raw:
        line_code = str((item or {}).get('lineCode') or '').strip().upper()
        process_code = str((item or {}).get('processCode') or '').strip().upper()
        start_time_raw = str((item or {}).get('startTime') or '').strip()
        if not line_code or not process_code:
            continue
        try:
            t = datetime.strptime(start_time_raw, '%H:%M').time()
        except Exception:
            continue
        result[(line_code, process_code)] = t
    return result

def _load_gantt_excluded_process_codes_by_line() -> Dict[str, set]:
    row = SystemSetting.objects.filter(key=GANTT_EXCLUDED_PROCESS_RULES_KEY).first()
    if not row or not row.value:
        return {}
    try:
        raw = json.loads(row.value)
    except Exception:
        return {}
    if not isinstance(raw, list):
        return {}
    result: Dict[str, set] = {}
    for item in raw:
        line_code = str((item or {}).get('lineCode') or '').strip().upper()
        process_code = str((item or {}).get('processCode') or '').strip().upper()
        if not line_code or not process_code:
            continue
        result.setdefault(line_code, set()).add(process_code)
    return result


@dataclass
class ProcessSpec:
    process_id: int
    process_code: str
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
        self.calendar_id = line.calendar_id or Calendar.objects.filter(calendar_code='daiso').values_list('id', flat=True).first()
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

    def is_registered_working_day(self, target_date) -> bool:
        """CalendarDayに稼働日として登録されているか（未登録日はFalse）"""
        cal = self._get_calendar_day(target_date)
        if cal is None:
            return False
        return cal.is_working_day is not False

    def get_day_end(self, target_date):
        segments = self.get_segments(target_date)
        if segments:
            return segments[-1][1]
        return self._get_previous_working_end(target_date)


def _get_cycle_setup(step: RoutingStep, product_id: int, plan_date) -> Tuple[float, float]:
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
            process_code=step.process.process_code if step.process_id else '',
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


def _build_l2201_synthetic_spec(product: Product, process, cycle_time_minutes: float, process_number: int = 0) -> Optional[ProcessSpec]:
    process_obj = process or getattr(product, 'process', None)
    process_id = getattr(process_obj, 'id', None) or getattr(product, 'process_id', None)
    if not product or not process_id:
        return None
    return ProcessSpec(
        process_id=process_id,
        process_code=getattr(process_obj, 'process_code', '') or '',
        process_name=getattr(process_obj, 'process_name', '') or '',
        process_number=process_number or 0,
        cycle_time_minutes=float(cycle_time_minutes or 0.0),
        setup_time_minutes=0.0,
        parallel_count=1,
        parallel_group=1,
        output_product_id=product.id,
        output_product_code=product.product_code or '',
        output_product_name=product.product_name or '',
        transfer_time_minutes=0.0,
    )


def _build_line_final_backlog_fallback_specs(
    backlog_rows: List[LineBacklog],
    product: Product,
    step_no_by_process: Dict[int, int],
) -> List[ProcessSpec]:
    """自品番ルーティング未登録のライン最終品向けに、LineBacklog工程行からProcessSpecを組み立てる。"""
    specs = []
    seen = set()
    for row in backlog_rows:
        if not row.process_id or row.process_id in seen:
            continue
        seen.add(row.process_id)
        process_obj = getattr(row, 'process', None)
        specs.append(ProcessSpec(
            process_id=row.process_id,
            process_code=getattr(process_obj, 'process_code', '') or '',
            process_name=getattr(process_obj, 'process_name', '') or '',
            process_number=step_no_by_process.get(row.process_id, 0),
            cycle_time_minutes=float(getattr(row, 'cycle_time_min', 0.0) or 0.0),
            setup_time_minutes=0.0,
            parallel_count=1,
            parallel_group=1,
            output_product_id=product.id,
            output_product_code=product.product_code or '',
            output_product_name=product.product_name or '',
            transfer_time_minutes=0.0,
        ))
    specs.sort(key=lambda s: (s.process_number or 0, s.process_id or 0))
    return specs


def _build_line_final_output_step_no_by_process(
    product_id: int,
    steps_by_product: Dict[int, List[RoutingStep]],
) -> Dict[int, int]:
    """
    ライン最終品を output_product とするステップの step_no を工程別に返す。
    同一工程に複数候補がある場合は、もっとも後工程側（最大step_no）を優先する。
    """
    result: Dict[int, int] = {}
    for step in steps_by_product.get(product_id, []):
        if step.output_product_id != product_id or not step.process_id:
            continue
        step_no = step.step_no or 0
        current = result.get(step.process_id)
        if current is None or step_no > current:
            result[step.process_id] = step_no
    return result


def _build_line_final_line_process_fallback_specs(
    line_id: int,
    product: Product,
    step_no_by_process: Dict[int, int],
    target_process_ids: Optional[List[int]] = None,
) -> List[ProcessSpec]:
    """ライン最終品の自品番ルーティング未登録時に、ライン工程からProcessSpecを組み立てる。"""
    specs = []
    processes = Process.objects.filter(line_id=line_id, is_active=True)
    if target_process_ids:
        processes = processes.filter(id__in=target_process_ids)
    processes = processes.order_by('process_code', 'id')
    for proc in processes:
        specs.append(ProcessSpec(
            process_id=proc.id,
            process_code=proc.process_code or '',
            process_name=proc.process_name or '',
            process_number=step_no_by_process.get(proc.id, 0),
            cycle_time_minutes=0.0,
            setup_time_minutes=0.0,
            parallel_count=1,
            parallel_group=1,
            output_product_id=product.id,
            output_product_code=product.product_code or '',
            output_product_name=product.product_name or '',
            transfer_time_minutes=0.0,
        ))
    specs.sort(key=lambda s: (s.process_number or 0, s.process_id or 0))
    return specs


def _resolve_line_final_fallback_coproduct_step(
    process_id: int,
    steps_by_process: Dict[int, List[RoutingStep]],
    coproduct_parent_map: Dict[int, Product],
    bom_multiplier_map: Dict[int, Decimal],
) -> Optional[RoutingStep]:
    """
    ライン最終品フォールバック時に、工程ごとの連産品ドライバ子品番を表すRoutingStepを返す。
    条件:
    - output_product が連産品ドライバ子（coproduct_parent_mapに存在）
    - かつ、対象最終品の通常BOM配下に存在（bom_multiplier_mapに存在）
    """
    candidates = _sort_routing_steps(steps_by_process.get(process_id, []))
    for step in candidates:
        child_id = step.output_product_id
        if not child_id:
            continue
        if child_id not in coproduct_parent_map:
            continue
        if child_id not in bom_multiplier_map:
            continue
        return step
    return None


def _resolve_line_final_fallback_cycle_step(
    process_id: int,
    steps_by_process: Dict[int, List[RoutingStep]],
    bom_multiplier_map: Dict[int, Decimal],
) -> Optional[RoutingStep]:
    """
    ライン最終品フォールバック時に、工程のサイクルタイム補完に使うRoutingStepを返す。
    優先順位:
    1. 出力品が当該最終品のBOM配下にあり、MINUTEかつduration_min>0 の工程
    2. 上記が無ければ、MINUTEかつduration_min>0 の工程
    """
    candidates = _sort_routing_steps(steps_by_process.get(process_id, []))
    preferred = []
    fallback = []
    for step in candidates:
        if step.time_unit != 'MINUTE' or not step.duration_min or step.duration_min <= 0:
            continue
        fallback.append(step)
        output_id = step.output_product_id
        if output_id and output_id in bom_multiplier_map:
            preferred.append(step)
    if preferred:
        return preferred[0]
    if fallback:
        return fallback[0]
    return None


def _sort_routing_steps(steps: List[RoutingStep]) -> List[RoutingStep]:
    return sorted(steps, key=lambda s: (s.step_no or 0, getattr(s, 'parallel_group', 1) or 1, s.id or 0))


def _select_steps_for_gantt_product(product: Product, steps_by_product: Dict[int, List[RoutingStep]], is_l2201_line: bool) -> List[RoutingStep]:
    steps = list(steps_by_product.get(product.id, []))
    if not steps:
        return []
    if not is_l2201_line:
        return _sort_routing_steps(steps)

    owned_steps = [step for step in steps if step.routing_id and step.routing.product_id == product.id]
    return _sort_routing_steps(owned_steps)


def _calculate_total_minutes(spec: ProcessSpec, quantity: Decimal) -> float:
    if spec.cycle_time_minutes <= 0:
        return 0.0
    return (spec.cycle_time_minutes * float(quantity)) + spec.setup_time_minutes


def _pick_active_bom(
    parent_product_id: int,
    plan_date,
    cache: Optional[Dict[Tuple[int, date], Optional[BOM]]] = None,
):
    key = (parent_product_id, plan_date)
    if cache is not None and key in cache:
        return cache[key]

    bom = (
        BOM.objects.filter(
            parent_product_id=parent_product_id,
            is_active=True,
            valid_from__lte=plan_date,
        )
        .filter(Q(valid_to__gte=plan_date) | Q(valid_to__isnull=True))
        .order_by('-valid_from')
        .first()
    )
    if cache is not None:
        cache[key] = bom
    return bom


def _resolve_coproduct_driver_child(
    parent_product_id: int,
    plan_date,
    cache: Optional[Dict[Tuple[int, date], Optional[Tuple[int, float]]]] = None,
) -> Optional[Tuple[int, float]]:
    """
    連産親品番から代表子品番（is_coproduct_driver=true）を解決する。
    Returns:
      (child_product_id, duration_min) / 見つからない場合は None
    """
    key = (parent_product_id, plan_date)
    if cache is not None and key in cache:
        return cache[key]

    bom = (
        BOM.objects.filter(
            parent_product_id=parent_product_id,
            is_coproduct=True,
            is_active=True,
            valid_from__lte=plan_date,
        )
        .filter(Q(valid_to__gte=plan_date) | Q(valid_to__isnull=True))
        .order_by('-valid_from', '-id')
        .first()
    )
    if not bom:
        if cache is not None:
            cache[key] = None
        return None

    item = (
        BOMItem.objects.filter(
            bom_id=bom.id,
            is_coproduct_driver=True,
        )
        .order_by('id')
        .first()
    )
    if not item:
        if cache is not None:
            cache[key] = None
        return None

    resolved = (item.child_product_id, float(item.duration_min or 0.0))
    if cache is not None:
        cache[key] = resolved
    return resolved


def _resolve_cycle_step_for_output_product(
    process_id: int,
    output_product_id: int,
    steps_by_process: Dict[int, List[RoutingStep]],
) -> Optional[RoutingStep]:
    """同一工程内で output_product が一致するRoutingStepを優先選択する。"""
    candidates = _sort_routing_steps(steps_by_process.get(process_id, []))
    for step in candidates:
        if step.output_product_id != output_product_id:
            continue
        if step.time_unit != 'MINUTE' or not step.duration_min or step.duration_min <= 0:
            continue
        return step
    return None


def _resolve_cycle_step_from_final_product_routing(
    *,
    line_id: int,
    line_final_product_id: int,
    process_id: int,
    driver_child_id: int,
    plan_date,
    cache: Optional[Dict[Tuple[int, int, int, date], Optional[RoutingStep]]] = None,
) -> Optional[RoutingStep]:
    """
    ライン最終品を子に持つ最終品BOMを起点に、
    同工程かつ output_product=代表子品番 のルーティングステップを解決する。
    """
    key = (line_final_product_id, process_id, driver_child_id, plan_date)
    if cache is not None and key in cache:
        return cache[key]

    final_product_ids = list(
        BOMItem.objects.filter(
            child_product_id=line_final_product_id,
            bom__is_active=True,
            bom__is_coproduct=False,
            bom__valid_from__lte=plan_date,
        )
        .filter(Q(bom__valid_to__gte=plan_date) | Q(bom__valid_to__isnull=True))
        .values_list('bom__parent_product_id', flat=True)
        .distinct()
    )
    if not final_product_ids:
        if cache is not None:
            cache[key] = None
        return None

    day_start = datetime.combine(plan_date, time(0, 0))
    day_end = datetime.combine(plan_date, time(23, 59, 59))

    candidates = list(
        RoutingStep.objects.filter(
            line_id=line_id,
            process_id=process_id,
            output_product_id=driver_child_id,
            time_unit='MINUTE',
            duration_min__gt=0,
            routing__is_active=True,
            routing__product_id__in=final_product_ids,
        )
        .filter(
            Q(routing__valid_from_datetime__isnull=True) | Q(routing__valid_from_datetime__lte=day_end)
        )
        .filter(
            Q(routing__valid_to_datetime__isnull=True) | Q(routing__valid_to_datetime__gte=day_start)
        )
        .select_related('routing')
    )
    if not candidates:
        if cache is not None:
            cache[key] = None
        return None

    # is_default優先 → valid_from新しい順 → step_no小さい順 → id小さい順
    candidates.sort(
        key=lambda s: (
            0 if getattr(s.routing, 'is_default', False) else 1,
            -(getattr(s.routing, 'valid_from_datetime', None).timestamp() if getattr(s.routing, 'valid_from_datetime', None) else float('-inf')),
            s.step_no or 0,
            s.id or 0,
        )
    )
    selected = candidates[0]
    if cache is not None:
        cache[key] = selected
    return selected


def _build_bom_multiplier_map(
    final_product_id: int,
    plan_date,
    *,
    active_bom_cache: Optional[Dict[Tuple[int, date], Optional[BOM]]] = None,
    bom_items_cache: Optional[Dict[int, List[BOMItem]]] = None,
) -> Dict[int, Decimal]:
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

        bom = _pick_active_bom(product_id, plan_date, cache=active_bom_cache)
        if not bom:
            continue

        if bom_items_cache is not None:
            items = bom_items_cache.get(bom.id)
            if items is None:
                items = list(BOMItem.objects.filter(bom_id=bom.id))
                bom_items_cache[bom.id] = items
        else:
            items = list(BOMItem.objects.filter(bom_id=bom.id))

        for item in items:
            if item.quantity is None:
                continue
            qty = Decimal(item.quantity)
            if item.loss_rate is not None:
                qty = qty * (Decimal('1') + Decimal(item.loss_rate))
            child_id = item.child_product_id
            multipliers[child_id] = multipliers.get(child_id, Decimal('0')) + (delta * qty)
            queue.append(child_id)
    return multipliers


def _build_coproduct_maps(plan_date) -> tuple:
    """
    連産品関連のマップを構築
    Returns:
        parent_map: 代表品(is_coproduct_driver=True)から親への対応（連産品展開用）
        all_children_set: 連産品の全ての子製品のセット（ガントチャートから除外用）
        driver_cycle_time_map: 連産品の親ID -> 代表品のサイクルタイム(分)
    """
    coproduct_boms = BOM.objects.filter(
        is_coproduct=True,
        is_active=True,
        valid_from__lte=plan_date,
    ).filter(Q(valid_to__gte=plan_date) | Q(valid_to__isnull=True)).select_related('parent_product')
    parent_map: Dict[int, Product] = {}
    all_children_set: set = set()
    driver_cycle_time_map: Dict[int, float] = {}  # 親製品ID -> 代表品のサイクルタイム
    for bom in coproduct_boms:
        for item in bom.items.select_related('child_product'):
            if item.child_product_id:
                # 全ての子製品をセットに追加（ガントチャートから除外用）
                all_children_set.add(item.child_product_id)
                # is_coproduct_driver=True の子製品のみを連産品展開の対象とする
                if item.is_coproduct_driver:
                    parent_map[item.child_product_id] = bom.parent_product
                    # 代表品のサイクルタイム（duration_min）を保存
                    if item.duration_min and item.duration_min > 0:
                        driver_cycle_time_map[bom.parent_product_id] = float(item.duration_min)
    return parent_map, all_children_set, driver_cycle_time_map


def _build_coproduct_parent_map(plan_date) -> Dict[int, Product]:
    """後方互換性のためのラッパー"""
    parent_map, _, _ = _build_coproduct_maps(plan_date)
    return parent_map


def _build_display_product_map_by_final(line_id: int) -> Tuple[Dict[int, Dict[int, Product]], Dict[int, Dict[int, set]]]:
    """
    ラインごとの表示品マップを構築する。
    Returns:
        primary_map: { final_product_id: { process_id: display_product } }  (先頭1件)
        all_ids_map: { final_product_id: { process_id: set(display_product_ids) } }
    """
    rows = (
        GanttDisplayProductMap.objects
        .filter(line_id=line_id)
        .select_related('display_product')
        .order_by('final_product_id', 'process_id', 'id')
    )
    primary: Dict[int, Dict[int, Product]] = {}
    all_ids: Dict[int, Dict[int, set]] = {}
    for row in rows:
        final_id = int(row.final_product_id)
        process_id = int(row.process_id)
        process_map = primary.setdefault(final_id, {})
        if process_id not in process_map and row.display_product_id:
            process_map[process_id] = row.display_product
        ids_map = all_ids.setdefault(final_id, {})
        id_set = ids_map.setdefault(process_id, set())
        if row.display_product_id:
            id_set.add(int(row.display_product_id))
    return primary, all_ids


def _resolve_display_product_override(
    *,
    process_id: int,
    display_map: Dict[int, Product],
    default_product_id: Optional[int],
    default_product_code: str,
    default_product_name: str,
    all_display_ids: Optional[Dict[int, set]] = None,
) -> Tuple[Optional[int], str, str]:
    """
    工程単位の表示品マップがある場合は表示品を上書きする。
    ただし、現在の出力品が同じ工程の表示品マップに登録済みならそのまま維持する。
    マップ未登録の工程は従来ロジックの値をそのまま返す。
    """
    mapped = display_map.get(int(process_id)) if display_map else None
    if not mapped:
        return default_product_id, default_product_code, default_product_name
    if all_display_ids and default_product_id:
        ids_for_process = all_display_ids.get(int(process_id))
        if ids_for_process and int(default_product_id) in ids_for_process:
            return default_product_id, default_product_code, default_product_name
    return mapped.id, mapped.product_code or '', mapped.product_name or ''


def _is_coproduct_sub_process(spec: ProcessSpec, coproduct_parent_map: Dict[int, Product]) -> bool:
    """連産品BOMの子品目を出力する工程かどうかを判定（名前依存なし）"""
    return bool(spec.output_product_id and spec.output_product_id in coproduct_parent_map)


def _is_coproduct_child(spec: ProcessSpec, coproduct_children_set: set) -> bool:
    """連産品の子品目を出力する工程かどうかを判定（除外用）"""
    return bool(spec.output_product_id and spec.output_product_id in coproduct_children_set)

def _is_coproduct_child_display_exception(spec: ProcessSpec, plan_product: Optional[Product] = None) -> bool:
    """連産子でも工程ガントに表示する特例判定。"""
    product_codes = {
        str(getattr(spec, 'output_product_code', '') or '').strip().upper(),
        str(getattr(plan_product, 'product_code', '') or '').strip().upper(),
    }
    if not (product_codes & COPRODUCT_CHILD_DISPLAY_EXCEPTION_PRODUCT_CODES):
        return False
    process_code = str(getattr(spec, 'process_code', '') or '').strip()
    return process_code in COPRODUCT_CHILD_DISPLAY_EXCEPTION_PROCESS_CODES


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
    is_l2201_line = str(getattr(line, 'line_code', '') or '').strip().upper() == 'L2201'
    line_code_upper = str(getattr(line, 'line_code', '') or '').strip().upper()
    prev_day_shift_qty_by_line_process = _load_prev_day_shift_qty_by_line_process()
    gantt_start_time_by_line_process = _load_gantt_start_time_by_line_process()
    gantt_excluded_codes = _load_gantt_excluded_process_codes_by_line().get(line_code_upper, set())

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
    qs_plan = LinePlan.objects.filter(
        line_id=line_id,
        plan_date__gte=start_date,
        plan_date__lte=end_date,
        plan_qty__gt=0,
    ).select_related('product', 'process')
    qs_backlog = LineBacklog.objects.filter(
        line_id=line_id,
        plan_date__gte=start_date,
        plan_date__lte=end_date,
        plan_qty__gt=0,
    ).select_related('product', 'process')
    # 9958687のLinePlan優先はL2201専用。通常ラインは従来どおりLineBacklogを使用。
    use_line_plan = is_l2201_line and qs_plan.exists()
    qs_all = qs_plan if use_line_plan else qs_backlog
    qs_final = qs_all.filter(product__is_line_final_product=True)
    # L2201(工程4221)は非最終品の計画も工程ガント生成対象に含める。
    use_final_only = (not is_l2201_line) and qs_final.exists()
    qs = qs_final if use_final_only else qs_all

    logger.info(
        'gantt_plans: line_id=%s start=%s end=%s clear=%s source=%s line_plan=%s backlog=%s source_all=%s source_final=%s using=%s',
        line_id,
        start_date,
        end_date,
        clear_existing,
        'line_plan' if use_line_plan else 'line_backlog',
        qs_plan.count(),
        qs_backlog.count(),
        qs_all.count(),
        qs_final.count(),
        'final' if use_final_only else 'all',
    )

    # 最終工程のプロセスを特定
    product_ids = list({obj.product_id for obj in qs})
    steps_qs = RoutingStep.objects.filter(
        line_id=line_id
    ).select_related('routing', 'process', 'output_product')

    steps_by_product: Dict[int, List[RoutingStep]] = {}
    steps_by_process: Dict[int, List[RoutingStep]] = {}
    for step in steps_qs:
        steps_by_process.setdefault(step.process_id, []).append(step)
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
    backlog_rows_by_key: Dict[Tuple[int, date, int], List[LineBacklog]] = {}
    if not use_line_plan:
        for backlog_row in qs_backlog:
            key = (backlog_row.product_id, backlog_row.plan_date, backlog_row.sequence_no or 0)
            backlog_rows_by_key.setdefault(key, []).append(backlog_row)

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
    remaining_shift_by_process_date: Dict[Tuple[date, int], Decimal] = {}

    # 連産品マップを日付ごとにキャッシュ（ループ外で構築）
    _coproduct_cache: Dict[date, tuple] = {}
    # BOM乗数マップを製品×日付ごとにキャッシュ
    _multiplier_cache: Dict[Tuple[int, date], Dict[int, Decimal]] = {}
    _active_bom_cache: Dict[Tuple[int, date], Optional[BOM]] = {}
    _bom_items_cache: Dict[int, List[BOMItem]] = {}
    _coproduct_driver_cache: Dict[Tuple[int, date], Optional[Tuple[int, float]]] = {}
    _cycle_from_final_routing_cache: Dict[Tuple[int, int, int, date], Optional[RoutingStep]] = {}
    # ライン最終品×工程の表示品マップ（ライン単位で1回だけ取得）
    display_product_map_by_final, display_product_all_ids_by_final = _build_display_product_map_by_final(line_id)

    tank_prev_day_plans = []

    plans = []
    for obj in base_plans:
        product = obj.product
        line_final_output_step_no_by_process = _build_line_final_output_step_no_by_process(product.id, steps_by_product)
        display_product_map = display_product_map_by_final.get(int(product.id), {})
        display_product_all_ids = display_product_all_ids_by_final.get(int(product.id), {})
        backlog_key = (obj.product_id, obj.plan_date, obj.sequence_no or 0)
        plan_backlog_rows = backlog_rows_by_key.get(backlog_key, [])
        # キャッシュ付きBOM乗数マップ
        _mult_key = (product.id, obj.plan_date)
        if _mult_key not in _multiplier_cache:
            _multiplier_cache[_mult_key] = _build_bom_multiplier_map(
                product.id,
                obj.plan_date,
                active_bom_cache=_active_bom_cache,
                bom_items_cache=_bom_items_cache,
            )
        multiplier_map = _multiplier_cache[_mult_key]
        # キャッシュ付き連産品マップ
        if obj.plan_date not in _coproduct_cache:
            _coproduct_cache[obj.plan_date] = _build_coproduct_maps(obj.plan_date)
        coproduct_parent_map, coproduct_children_set, driver_cycle_time_map = _coproduct_cache[obj.plan_date]
        coproduct_parent_ids = {parent.id for parent in coproduct_parent_map.values()}
        l2201_synthetic_plan = is_l2201_line and getattr(product, 'is_line_final_product', False)
        steps = _select_steps_for_gantt_product(product, steps_by_product, is_l2201_line)
        owned_steps = [step for step in steps if step.routing_id and step.routing.product_id == product.id]
        use_line_final_line_process_fallback = (
            (not is_l2201_line)
            and getattr(product, 'is_line_final_product', False)
            and not owned_steps
        )

        if use_line_final_line_process_fallback:
            fallback_step_no_by_process = dict(step_no_by_process)
            fallback_step_no_by_process.update(line_final_output_step_no_by_process)
            # 表示品マップがある最終品は、マップ登録工程のみをフォールバック対象にする
            fallback_target_process_ids = list(display_product_map.keys()) if display_product_map else None
            process_specs = _build_line_final_line_process_fallback_specs(
                line_id,
                product,
                fallback_step_no_by_process,
                target_process_ids=fallback_target_process_ids,
            )
            # 工程別連産品マッピング: driver子品番をspecにセットし、後段で親(ST)表示へ置換させる
            for spec in process_specs:
                resolved_from_display_map = False
                mapped_product = display_product_map.get(int(spec.process_id)) if display_product_map else None
                if mapped_product:
                    driver_child = _resolve_coproduct_driver_child(
                        mapped_product.id,
                        obj.plan_date,
                        cache=_coproduct_driver_cache,
                    )
                    if driver_child:
                        driver_child_id, _driver_duration = driver_child
                        driver_child_product = Product.objects.filter(id=driver_child_id).first()
                        if driver_child_product:
                            spec.output_product_id = driver_child_product.id
                            spec.output_product_code = driver_child_product.product_code or ''
                            spec.output_product_name = driver_child_product.product_name or ''
                        final_routing_cycle_step = _resolve_cycle_step_from_final_product_routing(
                            line_id=line_id,
                            line_final_product_id=product.id,
                            process_id=spec.process_id,
                            driver_child_id=driver_child_id,
                            plan_date=obj.plan_date,
                            cache=_cycle_from_final_routing_cache,
                        )
                        if final_routing_cycle_step:
                            spec.parallel_count = final_routing_cycle_step.parallel_count or 1
                            spec.parallel_group = getattr(final_routing_cycle_step, 'parallel_group', 1) or 1
                            spec.transfer_time_minutes = float(getattr(final_routing_cycle_step, 'transfer_time_minutes', 0.0))
                            cycle_time_min, setup_time_min = _get_cycle_setup(final_routing_cycle_step, driver_child_id, obj.plan_date)
                            if cycle_time_min > 0:
                                spec.cycle_time_minutes = cycle_time_min
                                spec.setup_time_minutes = setup_time_min
                        explicit_cycle_step = _resolve_cycle_step_for_output_product(
                            spec.process_id,
                            driver_child_id,
                            steps_by_process,
                        )
                        if (spec.cycle_time_minutes <= 0) and explicit_cycle_step:
                            spec.parallel_count = explicit_cycle_step.parallel_count or 1
                            spec.parallel_group = getattr(explicit_cycle_step, 'parallel_group', 1) or 1
                            spec.transfer_time_minutes = float(getattr(explicit_cycle_step, 'transfer_time_minutes', 0.0))
                            cycle_time_min, setup_time_min = _get_cycle_setup(explicit_cycle_step, driver_child_id, obj.plan_date)
                            if cycle_time_min > 0:
                                spec.cycle_time_minutes = cycle_time_min
                                spec.setup_time_minutes = setup_time_min
                        resolved_from_display_map = True

                if not resolved_from_display_map:
                    driver_step = _resolve_line_final_fallback_coproduct_step(
                        spec.process_id,
                        steps_by_process,
                        coproduct_parent_map,
                        multiplier_map,
                    )
                    if not driver_step:
                        continue
                    child = driver_step.output_product
                    if not child:
                        continue
                    spec.output_product_id = child.id
                    spec.output_product_code = child.product_code or ''
                    spec.output_product_name = child.product_name or ''
                    spec.parallel_count = driver_step.parallel_count or 1
                    spec.parallel_group = getattr(driver_step, 'parallel_group', 1) or 1
                    spec.transfer_time_minutes = float(getattr(driver_step, 'transfer_time_minutes', 0.0))
                    cycle_time_min, setup_time_min = _get_cycle_setup(driver_step, child.id, obj.plan_date)
                    if cycle_time_min > 0:
                        spec.cycle_time_minutes = cycle_time_min
                        spec.setup_time_minutes = setup_time_min
            for spec in process_specs:
                if spec.cycle_time_minutes > 0:
                    continue
                cycle_step = _resolve_line_final_fallback_cycle_step(
                    spec.process_id,
                    steps_by_process,
                    multiplier_map,
                )
                if not cycle_step:
                    continue
                spec.parallel_count = cycle_step.parallel_count or 1
                spec.parallel_group = getattr(cycle_step, 'parallel_group', 1) or 1
                spec.transfer_time_minutes = float(getattr(cycle_step, 'transfer_time_minutes', 0.0))
                cycle_time_min, setup_time_min = _get_cycle_setup(cycle_step, product.id, obj.plan_date)
                if cycle_time_min > 0:
                    spec.cycle_time_minutes = cycle_time_min
                    spec.setup_time_minutes = setup_time_min
            # ライン工程が空の場合のみ、同一keyのBacklog工程行へフォールバック
            if not process_specs and plan_backlog_rows:
                process_specs = _build_line_final_backlog_fallback_specs(
                    plan_backlog_rows,
                    product,
                    fallback_step_no_by_process,
                )
        if not steps and l2201_synthetic_plan:
            # L2201専用: 自分を親に持つルーティングが無いライン最終品は計画行の工程で1本扱いにする
            synthetic_cycle_time = driver_cycle_time_map.get(product.id, 0.0) if product.id in coproduct_parent_ids else 0.0
            synthetic_spec = _build_l2201_synthetic_spec(
                product,
                getattr(obj, 'process', None),
                synthetic_cycle_time,
                step_no_by_process.get(getattr(obj, 'process_id', None) or getattr(product, 'process_id', None), 0),
            )
            if not synthetic_spec:
                logger.warning(
                    'gantt_plans: skip L2201 synthetic plan_id=%s product_id=%s code=%s because synthetic spec could not be built',
                    getattr(obj, 'plan_id', None),
                    product.id,
                    getattr(product, 'product_code', ''),
                )
                continue
            process_specs = [synthetic_spec]
        elif not use_line_final_line_process_fallback:
            if not steps and is_l2201_line:
                logger.warning(
                    'gantt_plans: skip L2201 plan_id=%s product_id=%s code=%s because no owned routing steps were found',
                    getattr(obj, 'plan_id', None),
                    product.id,
                    getattr(product, 'product_code', ''),
                )
                continue
            if not steps:
                steps = default_steps
            if not steps:
                continue
            process_specs = _build_process_specs(steps, obj.plan_qty, obj.plan_date, product.id)
        process_specs.sort(key=lambda s: (s.process_number or 0, s.parallel_group or 1))

        if gantt_excluded_codes:
            process_specs = [s for s in process_specs if s.process_code not in gantt_excluded_codes]

        qty_label = str(obj.plan_qty).rstrip('0').rstrip('.')
        if '.' in qty_label:
            qty_label = qty_label.replace('.', 'p')
        sequence = obj.sequence_no or 0
        plan_id = f"{product.product_code}_{obj.plan_date.strftime('%Y%m%d')}_{qty_label}_{sequence}"

        coproduct_groups = {}
        for spec in process_specs:
            if not _is_coproduct_sub_process(spec, coproduct_parent_map):
                continue
            if spec.cycle_time_minutes <= 0:
                raise ValidationError(
                    f"連産工程のサイクルタイムを解決できませんでした: "
                    f"line={line_id}, product={getattr(product, 'product_code', obj.product_id)}, "
                    f"process={spec.process_code or spec.process_id}, output={spec.output_product_code or spec.output_product_id}"
                )
            parent = coproduct_parent_map[spec.output_product_id]
            group_key = f"{plan_id}_{spec.process_id}_{parent.id}"
            qty_product_id = spec.output_product_id or obj.product_id
            process_qty = multiplier_map.get(qty_product_id, Decimal('1')) * obj.plan_qty
            # 連産工程ではBOM側durationは使わず、RoutingStep由来のcycle_time_minutesのみ使用
            total_minutes = float(process_qty) * spec.cycle_time_minutes + (spec.setup_time_minutes or 0)
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
                    logger.info(
                        'gantt_plans: skip scheduled spec (coproduct group unresolved) '
                        'plan_id=%s date=%s seq=%s process_id=%s process_code=%s output_product_id=%s output_product_code=%s '
                        'group_key=%s group_exists=%s order_spec_match=%s',
                        plan_id,
                        obj.plan_date,
                        obj.sequence_no,
                        spec.process_id,
                        spec.process_code,
                        spec.output_product_id,
                        spec.output_product_code,
                        group_key,
                        bool(group),
                        bool(group and group.get('order_spec') is spec),
                    )
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
            # 連産品の子（代表品でない）はスキップ（親の工程として一緒に処理される）
            if (
                (not is_l2201_line)
                and _is_coproduct_child(spec, coproduct_children_set)
                and (not _is_coproduct_child_display_exception(spec, product))
            ):
                logger.info(
                    'gantt_plans: skip scheduled spec (coproduct child hidden) '
                    'plan_id=%s date=%s seq=%s process_id=%s process_code=%s output_product_id=%s output_product_code=%s plan_product_code=%s',
                    plan_id,
                    obj.plan_date,
                    obj.sequence_no,
                    spec.process_id,
                    spec.process_code,
                    spec.output_product_id,
                    spec.output_product_code,
                    getattr(product, 'product_code', ''),
                )
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

        # 9958687の0件スキップはL2201専用。通常ラインは従来挙動を維持。
        if is_l2201_line and (not scheduled_specs):
            logger.warning(
                'gantt_plans: skip plan_id=%s product_id=%s code=%s because no schedulable specs remained',
                plan_id,
                obj.product_id,
                getattr(product, 'product_code', ''),
            )
            continue
        if not scheduled_specs:
            logger.info(
                'gantt_plans: scheduled_specs empty after filtering '
                'plan_id=%s date=%s seq=%s product_id=%s product_code=%s process_specs=%s coproduct_groups=%s',
                plan_id,
                obj.plan_date,
                obj.sequence_no,
                obj.product_id,
                getattr(product, 'product_code', ''),
                len(process_specs),
                len(coproduct_groups),
            )

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

                process_key = (obj.plan_date, spec.process_id)
                configured_start_time = gantt_start_time_by_line_process.get(
                    (line_code_upper, str(spec.process_code or '').strip().upper())
                )
                prev_day_shift_qty = prev_day_shift_qty_by_line_process.get((line_code_upper, str(spec.process_code or '').strip().upper()), Decimal('0'))
                prev_day_shift_first = prev_day_shift_qty > 0 and process_key not in previous_process_end_by_date
                bw_effective_shift = prev_day_shift_qty if prev_day_shift_first else remaining_shift_by_process_date.get(process_key, Decimal('0'))
                is_chain_schedule = prev_day_shift_qty > 0

                if is_chain_schedule:
                    chain_bw_effective = effective_minutes
                    if bw_effective_shift > 0:
                        bw_qty = max(entry['process_qty'] - bw_effective_shift, Decimal('0'))
                        bw_total = _calculate_total_minutes(spec, bw_qty)
                        chain_bw_effective = bw_total / max(spec.parallel_count, 1)
                    if process_key in previous_process_end_by_date:
                        start_time = previous_process_end_by_date[process_key]
                    else:
                        chain_start = configured_start_time or line_earliest_start.time()
                        start_time = datetime.combine(obj.plan_date, chain_start)
                    end_time = calendar.add_working_minutes(start_time, chain_bw_effective)
                elif i == len(scheduled_specs) - 1:
                    # 最終工程: アンカー時刻に固定
                    start_time = anchor_dt
                    end_time = current_end_time
                else:
                    if bw_effective_shift > 0:
                        bw_qty = max(entry['process_qty'] - bw_effective_shift, Decimal('0'))
                        bw_total = _calculate_total_minutes(spec, bw_qty)
                        effective_minutes = bw_total / max(spec.parallel_count, 1)
                    # 後方パイプライン制約を適用
                    next_entry = scheduled_specs[i + 1]
                    next_start_time = scheduled_times[i + 1]['start']
                    next_cycle_time = next_entry['cycle_time_minutes']
                    gap_minutes = spec.transfer_time_minutes

                    # 開始-開始制約（後方）: 現工程の開始 <= 次工程の開始 - cycle_time - gap
                    # E2E制約を使うと前工程が不必要に早く開始されるため、S2S制約のみを使用
                    start_time = calendar.subtract_working_minutes(
                        next_start_time, current_cycle_time + gap_minutes
                    )
                    end_time = calendar.add_working_minutes(start_time, effective_minutes)

                # 前のsequenceの終了時刻があれば、それ以降から開始（チェーン方式は上で処理済み）
                if not is_chain_schedule and process_key in previous_process_end_by_date:
                    prev_process_end = previous_process_end_by_date[process_key]
                    if start_time < prev_process_end:
                        start_time = prev_process_end
                        end_time = calendar.add_working_minutes(start_time, effective_minutes)
                        logger.info(
                            'gantt_plans: plan_id=%s i=%s adjusted by prev_process_end=%s new_start=%s',
                            plan_id, i, prev_process_end, start_time
                        )
                elif not is_chain_schedule and configured_start_time:
                    # 強制開始: ライン×工程の当日先頭SEQは設定開始時刻に固定
                    start_time = datetime.combine(obj.plan_date, configured_start_time)
                    end_time = calendar.add_working_minutes(start_time, effective_minutes)

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

                # 前日シフト: 残量があればSEQ2以降にも繰り越し適用
                process_key = (obj.plan_date, spec.process_id)
                prev_day_shift_qty = prev_day_shift_qty_by_line_process.get((line_code_upper, str(spec.process_code or '').strip().upper()), Decimal('0'))
                prev_day_shift_first = prev_day_shift_qty > 0 and process_key not in previous_process_end_by_date
                effective_shift = prev_day_shift_qty if prev_day_shift_first else remaining_shift_by_process_date.get(process_key, Decimal('0'))
                tank_prev_qty = Decimal('0')
                if effective_shift > 0:
                    tank_prev_qty = min(effective_shift, process_qty)
                    process_qty = max(process_qty - tank_prev_qty, Decimal('0'))
                    total_minutes = _calculate_total_minutes(spec, process_qty)
                    effective_minutes = total_minutes / max(spec.parallel_count, 1)
                    remaining_shift_by_process_date[process_key] = effective_shift - tank_prev_qty

                output_product_id = spec.output_product_id
                output_product_code = spec.output_product_code
                output_product_name = spec.output_product_name
                coproduct_group_key = entry['coproduct_group_key']
                coproduct_child_id = entry['coproduct_child_id']
                if (not is_l2201_line) and output_product_id and output_product_id in coproduct_parent_map:
                    parent = coproduct_parent_map[output_product_id]
                    coproduct_child_id = coproduct_child_id or output_product_id
                    output_product_id = parent.id
                    output_product_code = parent.product_code
                    output_product_name = parent.product_name
                    coproduct_group_key = coproduct_group_key or f"{plan_id}_{spec.process_id}_{parent.id}"
                output_product_id, output_product_code, output_product_name = _resolve_display_product_override(
                    process_id=spec.process_id,
                    display_map=display_product_map,
                    default_product_id=output_product_id,
                    default_product_code=output_product_code,
                    default_product_name=output_product_name,
                    all_display_ids=display_product_all_ids,
                )
                process_plan = {
                    'process_id': spec.process_id,
                    'process_code': spec.process_code,
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

                # 前日ガントエントリ生成
                if tank_prev_qty > 0:
                    _generate_prev_day_shift_entry(
                        tank_prev_day_plans, calendar, spec, entry,
                        tank_prev_qty, obj, product, plan_id, line_id,
                        output_product_id, output_product_code, output_product_name,
                    )

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

                process_key = (obj.plan_date, spec.process_id)
                configured_start_time = gantt_start_time_by_line_process.get(
                    (line_code_upper, str(spec.process_code or '').strip().upper())
                )
                prev_day_shift_qty = prev_day_shift_qty_by_line_process.get((line_code_upper, str(spec.process_code or '').strip().upper()), Decimal('0'))
                prev_day_shift_first = prev_day_shift_qty > 0 and process_key not in previous_process_end_by_date
                effective_shift = prev_day_shift_qty if prev_day_shift_first else remaining_shift_by_process_date.get(process_key, Decimal('0'))
                tank_prev_qty = Decimal('0')
                if effective_shift > 0:
                    tank_prev_qty = min(effective_shift, process_qty)
                    process_qty = max(process_qty - tank_prev_qty, Decimal('0'))
                    total_minutes = _calculate_total_minutes(spec, process_qty)
                    effective_minutes = total_minutes / max(spec.parallel_count, 1)
                    remaining_shift_by_process_date[process_key] = effective_shift - tank_prev_qty

                if process_key in previous_process_end_by_date:
                    prev_process_end = previous_process_end_by_date[process_key]
                    current_start_time = max(current_start_time, prev_process_end)
                    logger.info(
                        'gantt_plans: plan_id=%s adjusted by prev_process_end=%s new_current_start_time=%s',
                        plan_id, prev_process_end, current_start_time
                    )
                elif configured_start_time:
                    current_start_time = datetime.combine(obj.plan_date, configured_start_time)

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
                if (not is_l2201_line) and output_product_id and output_product_id in coproduct_parent_map:
                    parent = coproduct_parent_map[output_product_id]
                    coproduct_child_id = coproduct_child_id or output_product_id
                    output_product_id = parent.id
                    output_product_code = parent.product_code
                    output_product_name = parent.product_name
                    coproduct_group_key = coproduct_group_key or f"{plan_id}_{spec.process_id}_{parent.id}"
                output_product_id, output_product_code, output_product_name = _resolve_display_product_override(
                    process_id=spec.process_id,
                    display_map=display_product_map,
                    default_product_id=output_product_id,
                    default_product_code=output_product_code,
                    default_product_name=output_product_name,
                    all_display_ids=display_product_all_ids,
                )
                process_plan = {
                    'process_id': spec.process_id,
                    'process_code': spec.process_code,
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

                # 前日ガントエントリ生成
                if tank_prev_qty > 0:
                    _generate_prev_day_shift_entry(
                        tank_prev_day_plans, calendar, spec, entry,
                        tank_prev_qty, obj, product, plan_id, line_id,
                        output_product_id, output_product_code, output_product_name,
                    )

                # 次工程の開始時刻を計算（パイプライン処理を考慮）
                if i + 1 < len(scheduled_specs):
                    next_entry = scheduled_specs[i + 1]
                    next_spec = next_entry['spec']

                    if spec.process_number == next_spec.process_number:
                        # 同じprocess_number内の次の品番は、現在の品番の終了後から開始
                        current_start_time = end_time
                        logger.info(
                            'gantt_plans: plan_id=%s i=%s same_process: end=%s next_start_time=%s',
                            plan_id, i, end_time, current_start_time
                        )
                    else:
                        # 異なるprocess_numberへの移行
                        # 同じprocess_numberの最初の工程からS2S制約を計算
                        first_same_process_start = start_time
                        first_same_process_cycle = entry['cycle_time_minutes']
                        first_same_process_gap = spec.transfer_time_minutes
                        for j in range(i - 1, -1, -1):
                            prev_entry = scheduled_specs[j]
                            if prev_entry['spec'].process_number == spec.process_number:
                                first_same_process_start = processes_plan[j]['start_time']
                                first_same_process_cycle = prev_entry['cycle_time_minutes']
                                first_same_process_gap = prev_entry['spec'].transfer_time_minutes
                            else:
                                break

                        s2s_limit = calendar.add_working_minutes(
                            first_same_process_start,
                            first_same_process_cycle + first_same_process_gap
                        )
                        current_start_time = s2s_limit

                        logger.info(
                            'gantt_plans: plan_id=%s i=%s pipeline: first_start=%s cycle=%.1f gap=%.1f '
                            's2s_limit=%s next_start_time=%s',
                            plan_id, i, first_same_process_start, first_same_process_cycle,
                            first_same_process_gap, s2s_limit, current_start_time
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

    # タンクライン箱組の前日ガントエントリを追加
    if tank_prev_day_plans:
        plans.extend(tank_prev_day_plans)
        logger.info('gantt_plans: added %s tank hakogumi prev-day entries', len(tank_prev_day_plans))

    plans = _merge_consecutive_subprocess_entries(plans)
    logger.info('gantt_plans: generated_plans=%s', len(plans))
    return plans


def _generate_prev_day_shift_entry(
    tank_prev_day_plans, calendar, spec, entry,
    tank_prev_qty, obj, product, plan_id, line_id,
    output_product_id, output_product_code, output_product_name,
):
    """前日勤務終了から逆算して前日シフト分のガントエントリを生成"""
    prev_total_min = _calculate_total_minutes(spec, tank_prev_qty)
    prev_effective_min = prev_total_min / max(spec.parallel_count, 1)
    if prev_effective_min <= 0:
        return

    # 前営業日を検索（CalendarDayに稼働日として登録されている日のみ）
    prev_day = obj.plan_date - timedelta(days=1)
    while not calendar.is_registered_working_day(prev_day):
        prev_day -= timedelta(days=1)
        if (obj.plan_date - prev_day).days > 30:
            logger.warning('gantt_plans: no working day found within 30 days before %s', obj.plan_date)
            return

    prev_day_end = calendar.get_day_end(prev_day)
    prev_start = calendar.subtract_working_minutes(prev_day_end, prev_effective_min)

    # 前日シフト行が工程ごとに上書きされないよう識別子を分離する
    prev_plan_id = f"{plan_id}_hakogumi_prev_p{spec.process_id}_o{output_product_id or 0}"
    prev_process_plan = {
        'process_id': spec.process_id,
        'process_code': spec.process_code,
        'process_name': spec.process_name,
        'process_number': spec.process_number,
        'parallel_group': spec.parallel_group,
        'output_product_id': output_product_id,
        'output_product_code': output_product_code,
        'output_product_name': output_product_name,
        'coproduct_group_key': None,
        'coproduct_child_id': None,
        'quantity': float(tank_prev_qty),
        'cycle_time_minutes': entry['cycle_time_minutes'],
        'setup_time_minutes': entry['setup_time_minutes'],
        'total_minutes_required': prev_total_min,
        'effective_minutes': prev_effective_min,
        'parallel_count': spec.parallel_count,
        'start_time': prev_start.isoformat(),
        'end_time': prev_day_end.isoformat(),
        'transfer_time_minutes': spec.transfer_time_minutes,
        'is_continuous': True,
    }

    tank_prev_day_plans.append({
        'plan_id': prev_plan_id,
        'line_id': line_id,
        'product_id': product.id,
        'plan_date': prev_day,
        'plan_qty': tank_prev_qty,
        'sequence_no': obj.sequence_no,
        'start_datetime': prev_start,
        'end_datetime': prev_day_end,
        'processes_plan': [prev_process_plan],
    })
    logger.info(
        'gantt_plans: tank hakogumi prev-day entry: plan_id=%s date=%s start=%s end=%s qty=%s',
        prev_plan_id, prev_day, prev_start, prev_day_end, tank_prev_qty,
    )


def _merge_consecutive_subprocess_entries(plans):
    """同一サブ工程出力品のうち、時間的に連続するエントリを1つに統合する"""
    if len(plans) <= 1:
        return plans

    # 同一工程×同日で、時間帯にどの出力品が存在するかを事前に作る
    process_slots = {}
    for plan in plans:
        plan_date = plan.get('plan_date')
        for proc in plan['processes_plan']:
            try:
                start_dt = datetime.fromisoformat(proc['start_time'])
                end_dt = datetime.fromisoformat(proc['end_time'])
            except Exception:
                continue
            slot_key = (proc.get('process_id'), plan_date)
            process_slots.setdefault(slot_key, []).append(
                (start_dt, end_dt, proc.get('output_product_id'))
            )

    def _has_other_product_in_gap(process_id, plan_date, output_product_id, gap_start, gap_end):
        """空き区間に同一工程の他製品が存在するか判定"""
        if gap_end <= gap_start:
            return False
        for s, e, out_pid in process_slots.get((process_id, plan_date), []):
            if out_pid == output_product_id:
                continue
            if s < gap_end and e > gap_start:
                return True
        return False

    proc_groups = {}
    for plan in plans:
        plan_date = plan.get('plan_date')
        for proc in plan['processes_plan']:
            key = (proc['process_id'], proc.get('output_product_id'), plan_date)
            proc_groups.setdefault(key, []).append({
                'plan': plan,
                'proc': proc,
            })

    merged_count = 0
    for key, entries in proc_groups.items():
        if len(entries) <= 1:
            continue

        entries.sort(key=lambda e: datetime.fromisoformat(e['proc']['start_time']))

        runs = []
        current_run = [entries[0]]
        for i in range(1, len(entries)):
            prev_proc = entries[i - 1]['proc']
            curr_proc = entries[i]['proc']
            prev_end = datetime.fromisoformat(prev_proc['end_time'])
            curr_start = datetime.fromisoformat(curr_proc['start_time'])
            # 接続/重なりは連続扱い
            if curr_start <= prev_end:
                current_run.append(entries[i])
            # ギャップがあっても、その間に同一工程の他製品が無ければ連続扱い
            elif not _has_other_product_in_gap(
                prev_proc.get('process_id'),
                key[2],
                prev_proc.get('output_product_id'),
                prev_end,
                curr_start,
            ):
                current_run.append(entries[i])
            else:
                runs.append(current_run)
                current_run = [entries[i]]
        runs.append(current_run)

        for run in runs:
            if len(run) <= 1:
                continue

            first_proc = run[0]['proc']
            for entry in run[1:]:
                proc = entry['proc']
                first_start = datetime.fromisoformat(first_proc['start_time'])
                first_end = datetime.fromisoformat(first_proc['end_time'])
                proc_start = datetime.fromisoformat(proc['start_time'])
                proc_end = datetime.fromisoformat(proc['end_time'])
                first_proc['start_time'] = min(first_start, proc_start).isoformat()
                first_proc['end_time'] = max(first_end, proc_end).isoformat()
                first_proc['quantity'] = float(first_proc['quantity']) + float(proc['quantity'])
                first_proc['total_minutes_required'] = (
                    float(first_proc.get('total_minutes_required', 0))
                    + float(proc.get('total_minutes_required', 0))
                )
                first_proc['effective_minutes'] = (
                    float(first_proc.get('effective_minutes', 0))
                    + float(proc.get('effective_minutes', 0))
                )
                entry['plan']['processes_plan'].remove(proc)
                merged_count += 1

    if merged_count:
        logger.info('gantt_plans: merged %s subprocess entries', merged_count)
        for plan in plans:
            procs = plan['processes_plan']
            if procs:
                all_starts = [datetime.fromisoformat(p['start_time']) for p in procs]
                all_ends = [datetime.fromisoformat(p['end_time']) for p in procs]
                plan['start_datetime'] = min(all_starts)
                plan['end_datetime'] = max(all_ends)

    return plans
