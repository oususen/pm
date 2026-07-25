"""
長期負荷計算サービス

LineDemand（顧客需要）× LineCycleTime（ライン別サイクルタイム）から
ライン・工程別の長期負荷を算出する。
"""
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional

from django.db.models import F

from masters.models import Line, CalendarDay, LineCycleTime, Process, RoutingStep
from ..models import LineDemand


class LineLoadService:
    LT_LOOKBACK_DAYS = 31

    @staticmethod
    def _month_start(target_date):
        return target_date.replace(day=1)

    @classmethod
    def _next_month_start(cls, target_date):
        if target_date.month == 12:
            return target_date.replace(year=target_date.year + 1, month=1, day=1)
        return target_date.replace(month=target_date.month + 1, day=1)

    @classmethod
    def _month_end(cls, target_date):
        return cls._next_month_start(target_date) - timedelta(days=1)

    @classmethod
    def _previous_month_start(cls, target_date):
        return cls._month_start(cls._month_start(target_date) - timedelta(days=1))

    @staticmethod
    def _is_working_day(calendar_id, target_date, calendar_day_cache):
        if not calendar_id:
            return target_date.weekday() < 5
        key = (calendar_id, target_date)
        if key in calendar_day_cache:
            return calendar_day_cache[key]
        return target_date.weekday() < 5

    @classmethod
    def _shift_business_days_forward(cls, base_date, days, calendar_id, calendar_day_cache):
        remaining = max(int(days or 0), 0)
        current = base_date
        while remaining > 0:
            current = current + timedelta(days=1)
            if cls._is_working_day(calendar_id, current, calendar_day_cache):
                remaining -= 1
        return current

    @classmethod
    def _list_working_days_in_month(cls, month_start, calendar_id, calendar_day_cache):
        current = month_start
        month_end = cls._month_end(month_start)
        working_days = []
        while current <= month_end:
            if cls._is_working_day(calendar_id, current, calendar_day_cache):
                working_days.append(current)
            current += timedelta(days=1)
        return working_days

    def _rebalance_month_bucket_demands(
        self,
        demand_map,
        final_line_by_product_code,
        line_calendar_map,
        calendar_day_cache,
        start_date,
        end_date,
    ):
        month_cursor = self._month_start(start_date)
        last_month = self._month_start(end_date)
        target_months = []
        while month_cursor <= last_month:
            target_months.append(month_cursor)
            month_cursor = self._next_month_start(month_cursor)

        for product_code, line_id in final_line_by_product_code.items():
            calendar_id = line_calendar_map.get(line_id)
            for month_start in target_months:
                working_days = self._list_working_days_in_month(month_start, calendar_id, calendar_day_cache)
                if len(working_days) < 3:
                    continue
                visible_working_days = [day for day in working_days if start_date <= day <= end_date]
                if not visible_working_days:
                    continue

                prev_month_start = self._previous_month_start(month_start)
                prev_working_days = self._list_working_days_in_month(prev_month_start, calendar_id, calendar_day_cache)
                if not prev_working_days:
                    continue

                prev_total = sum(demand_map.get((product_code, day), 0) for day in prev_working_days)
                prev_daily_avg = prev_total / len(prev_working_days)
                if prev_daily_avg <= 0:
                    continue

                first_three_days = working_days[:3]
                first_three_total = sum(demand_map.get((product_code, day), 0) for day in first_three_days)
                if first_three_total < prev_daily_avg * 10:
                    continue

                month_total = sum(demand_map.get((product_code, day), 0) for day in visible_working_days)
                if month_total <= 0:
                    continue

                for day in visible_working_days:
                    demand_map.pop((product_code, day), None)

                qty_per_day = month_total / len(visible_working_days)
                for day in visible_working_days:
                    demand_map[(product_code, day)] = qty_per_day

    def _build_final_product_demand_map(
        self,
        product_codes: set[str],
        start_date,
        end_date,
    ) -> Dict[tuple[str, Any], float]:
        if not product_codes:
            return {}

        final_step_rows = RoutingStep.objects.filter(
            routing__is_active=True,
            routing__product__is_final_product=True,
            routing__product__product_code__in=product_codes,
            output_product_id=F('routing__product_id'),
            line_id__isnull=False,
        ).order_by(
            'routing__product__product_code',
            'step_no',
            'id',
        ).values_list(
            'routing__product__product_code',
            'line_id',
        )

        final_line_by_product_code = {}
        for product_code, line_id in final_step_rows:
            final_line_by_product_code[product_code] = line_id

        if not final_line_by_product_code:
            return {}

        final_line_ids = set(final_line_by_product_code.values())
        line_calendar_map = dict(
            Line.objects.filter(id__in=final_line_ids).values_list('id', 'calendar_id')
        )
        fetch_start_date = self._previous_month_start(start_date) - timedelta(days=self.LT_LOOKBACK_DAYS)
        calendar_day_rows = CalendarDay.objects.filter(
            calendar_id__in=[cid for cid in line_calendar_map.values() if cid],
            target_date__gte=fetch_start_date,
            target_date__lte=end_date + timedelta(days=self.LT_LOOKBACK_DAYS),
        ).values('calendar_id', 'target_date', 'is_working_day')
        calendar_day_cache = {
            (row['calendar_id'], row['target_date']): bool(row['is_working_day'])
            for row in calendar_day_rows
        }
        demand_qs = LineDemand.objects.filter(
            line_id__in=final_line_ids,
            product__is_final_product=True,
            product_code__in=final_line_by_product_code.keys(),
            plan_date__gte=fetch_start_date,
            plan_date__lte=end_date,
        ).values(
            'line_id',
            'product_code',
            'plan_date',
            'lead_time_days',
            'firm_is_shifted',
            'forecast_is_shifted',
            'forecast_qty',
            'firm_qty',
        )

        demand_map = defaultdict(float)
        for row in demand_qs:
            if final_line_by_product_code.get(row['product_code']) != row['line_id']:
                continue
            line_calendar_id = line_calendar_map.get(row['line_id'])
            lead_time_days = int(row.get('lead_time_days') or 0)

            forecast_qty = float(row['forecast_qty'] or 0)
            if forecast_qty > 0:
                forecast_date = row['plan_date']
                if row.get('forecast_is_shifted') and lead_time_days > 0:
                    forecast_date = self._shift_business_days_forward(
                        row['plan_date'],
                        lead_time_days,
                        line_calendar_id,
                        calendar_day_cache,
                    )
                if fetch_start_date <= forecast_date <= end_date:
                    demand_map[(row['product_code'], forecast_date)] += forecast_qty

            firm_qty = float(row['firm_qty'] or 0)
            if firm_qty > 0:
                firm_date = row['plan_date']
                if row.get('firm_is_shifted') and lead_time_days > 0:
                    firm_date = self._shift_business_days_forward(
                        row['plan_date'],
                        lead_time_days,
                        line_calendar_id,
                        calendar_day_cache,
                    )
                if fetch_start_date <= firm_date <= end_date:
                    demand_map[(row['product_code'], firm_date)] += firm_qty

        self._rebalance_month_bucket_demands(
            demand_map,
            final_line_by_product_code,
            line_calendar_map,
            calendar_day_cache,
            start_date,
            end_date,
        )

        filtered_map = defaultdict(float)
        for (product_code, plan_date), qty in demand_map.items():
            if start_date <= plan_date <= end_date and qty > 0:
                filtered_map[(product_code, plan_date)] += qty

        return filtered_map

    def calculate(
        self,
        line_ids: List[int],
        start_date,
        end_date,
        aggregate: str = 'daily',
    ) -> Dict[str, Any]:
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        lines = Line.objects.filter(id__in=line_ids, is_active=True)
        line_map = {l.id: l for l in lines}

        cycle_times = LineCycleTime.objects.filter(
            line_id__in=line_ids,
            is_active=True,
        ).select_related('product', 'process')

        # {(line_id, product_code): {process_id: cycle_time_sec}}
        ct_map = defaultdict(dict)
        target_lines_by_product_code = defaultdict(set)
        process_ids = set()
        for ct in cycle_times:
            ct_map[(ct.line_id, ct.product.product_code)][ct.process_id] = float(ct.cycle_time_sec)
            target_lines_by_product_code[ct.product.product_code].add(ct.line_id)
            process_ids.add(ct.process_id)

        process_map = {p.id: p for p in Process.objects.filter(id__in=process_ids)}

        final_demand_map = self._build_final_product_demand_map(
            set(target_lines_by_product_code.keys()),
            start_date,
            end_date,
        )

        # {(line_id, plan_date): {process_id: load_seconds}}
        load_map = defaultdict(lambda: defaultdict(float))
        for (product_code, plan_date), demand_qty in final_demand_map.items():
            for target_line_id in target_lines_by_product_code.get(product_code, set()):
                ct_by_process = ct_map.get((target_line_id, product_code))
                if not ct_by_process:
                    continue
                for proc_id, ct_sec in ct_by_process.items():
                    load_map[(target_line_id, plan_date)][proc_id] += demand_qty * ct_sec

        calendar_days = CalendarDay.objects.filter(
            calendar__line__in=lines,
            target_date__gte=start_date,
            target_date__lte=end_date,
        ).select_related('calendar')

        # {(calendar_id, date): work_minutes}
        cal_map = {}
        for cd in calendar_days:
            cal_map[(cd.calendar_id, cd.target_date)] = cd.work_minutes or 0

        line_calendar = {l.id: l.calendar_id for l in lines if l.calendar_id}

        results = []
        for line_id, line in line_map.items():
            cal_id = line_calendar.get(line_id)
            daily_data = []
            current = start_date
            while current <= end_date:
                process_loads = load_map.get((line_id, current), {})
                avail_min = cal_map.get((cal_id, current), 0) if cal_id else 0
                avail_sec = avail_min * 60

                process_detail = []
                total_load_sec = 0
                for proc_id, load_sec in process_loads.items():
                    proc = process_map.get(proc_id)
                    equipment_count = max(int(getattr(proc, 'equipment_count', 1) or 1), 1)
                    adjusted_load_sec = load_sec / equipment_count
                    util = (adjusted_load_sec / avail_sec * 100) if avail_sec > 0 else 0
                    process_detail.append({
                        'process_id': proc_id,
                        'process_code': proc.process_code if proc else '',
                        'process_name': proc.process_name if proc else '',
                        'equipment_count': equipment_count,
                        'raw_load_sec': round(load_sec, 1),
                        'raw_load_min': round(load_sec / 60, 1),
                        'load_sec': round(adjusted_load_sec, 1),
                        'load_min': round(adjusted_load_sec / 60, 1),
                        'utilization': round(util, 1),
                    })
                    total_load_sec += adjusted_load_sec

                line_util = (total_load_sec / avail_sec * 100) if avail_sec > 0 else 0

                daily_data.append({
                    'date': current.isoformat(),
                    'available_min': avail_min,
                    'line_load_sec': round(total_load_sec, 1),
                    'line_load_min': round(total_load_sec / 60, 1),
                    'utilization': round(line_util, 1),
                    'is_working_day': avail_min > 0,
                    'processes': sorted(process_detail, key=lambda x: x['process_code']),
                })
                current += timedelta(days=1)

            if aggregate == 'weekly':
                daily_data = self._aggregate_weekly(daily_data)
            elif aggregate == 'monthly':
                daily_data = self._aggregate_monthly(daily_data)

            results.append({
                'line_id': line_id,
                'line_code': line.line_code,
                'line_name': line.line_name,
                'data': daily_data,
            })

        return {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'aggregate': aggregate,
            'lines': sorted(results, key=lambda x: x['line_code']),
        }

    def _aggregate_weekly(self, daily_data: List[dict]) -> List[dict]:
        weeks = defaultdict(list)
        for d in daily_data:
            dt = datetime.fromisoformat(d['date'])
            week_start = (dt - timedelta(days=dt.weekday())).date()
            weeks[week_start].append(d)

        result = []
        for week_start in sorted(weeks.keys()):
            days = weeks[week_start]
            working_days = [d for d in days if d['is_working_day']]
            total_avail = sum(d['available_min'] for d in working_days)
            total_load_sec = sum(d['line_load_sec'] for d in days)

            if total_avail == 0 and total_load_sec == 0:
                result.append({
                    'date': week_start.isoformat(),
                    'week_label': f"{week_start.strftime('%m/%d')}~",
                    'available_min': 0,
                    'line_load_sec': 0,
                    'line_load_min': 0,
                    'utilization': 0,
                    'is_working_day': False,
                    'processes': [],
                })
                continue
            util = (total_load_sec / (total_avail * 60) * 100) if total_avail > 0 else 0

            proc_totals = defaultdict(lambda: {
                'raw_load_sec': 0,
                'load_sec': 0,
                'code': '',
                'name': '',
                'equipment_count': 1,
            })
            for d in days:
                for p in d['processes']:
                    proc_totals[p['process_id']]['raw_load_sec'] += p.get('raw_load_sec', p['load_sec'])
                    proc_totals[p['process_id']]['load_sec'] += p['load_sec']
                    proc_totals[p['process_id']]['code'] = p['process_code']
                    proc_totals[p['process_id']]['name'] = p['process_name']
                    proc_totals[p['process_id']]['equipment_count'] = p.get('equipment_count', 1)

            processes = []
            for pid, pt in proc_totals.items():
                p_util = (pt['load_sec'] / (total_avail * 60) * 100) if total_avail > 0 else 0
                processes.append({
                    'process_id': pid,
                    'process_code': pt['code'],
                    'process_name': pt['name'],
                    'equipment_count': pt['equipment_count'],
                    'raw_load_sec': round(pt['raw_load_sec'], 1),
                    'raw_load_min': round(pt['raw_load_sec'] / 60, 1),
                    'load_sec': round(pt['load_sec'], 1),
                    'load_min': round(pt['load_sec'] / 60, 1),
                    'utilization': round(p_util, 1),
                })

            result.append({
                'date': week_start.isoformat(),
                'week_label': f"{week_start.strftime('%m/%d')}~",
                'available_min': total_avail,
                'line_load_sec': round(total_load_sec, 1),
                'line_load_min': round(total_load_sec / 60, 1),
                'utilization': round(util, 1),
                'is_working_day': total_avail > 0 or total_load_sec > 0,
                'processes': sorted(processes, key=lambda x: x['process_code']),
            })

        return result

    def _aggregate_monthly(self, daily_data: List[dict]) -> List[dict]:
        months = defaultdict(list)
        for d in daily_data:
            dt = datetime.fromisoformat(d['date'])
            month_key = dt.date().replace(day=1)
            months[month_key].append(d)

        result = []
        for month_start in sorted(months.keys()):
            days = months[month_start]
            working_days = [d for d in days if d['is_working_day']]
            total_avail = sum(d['available_min'] for d in working_days)
            total_load_sec = sum(d['line_load_sec'] for d in days)

            if total_avail == 0 and total_load_sec == 0:
                result.append({
                    'date': month_start.isoformat(),
                    'month_label': f"{month_start.strftime('%Y/%m')}",
                    'available_min': 0,
                    'line_load_sec': 0, 'line_load_min': 0,
                    'utilization': 0, 'is_working_day': False, 'processes': [],
                })
                continue
            util = (total_load_sec / (total_avail * 60) * 100) if total_avail > 0 else 0

            proc_totals = defaultdict(lambda: {
                'raw_load_sec': 0,
                'load_sec': 0,
                'code': '',
                'name': '',
                'equipment_count': 1,
            })
            for d in days:
                for p in d['processes']:
                    proc_totals[p['process_id']]['raw_load_sec'] += p.get('raw_load_sec', p['load_sec'])
                    proc_totals[p['process_id']]['load_sec'] += p['load_sec']
                    proc_totals[p['process_id']]['code'] = p['process_code']
                    proc_totals[p['process_id']]['name'] = p['process_name']
                    proc_totals[p['process_id']]['equipment_count'] = p.get('equipment_count', 1)

            processes = []
            for pid, pt in proc_totals.items():
                p_util = (pt['load_sec'] / (total_avail * 60) * 100) if total_avail > 0 else 0
                processes.append({
                    'process_id': pid, 'process_code': pt['code'], 'process_name': pt['name'],
                    'equipment_count': pt['equipment_count'],
                    'raw_load_sec': round(pt['raw_load_sec'], 1),
                    'raw_load_min': round(pt['raw_load_sec'] / 60, 1),
                    'load_sec': round(pt['load_sec'], 1), 'load_min': round(pt['load_sec'] / 60, 1),
                    'utilization': round(p_util, 1),
                })

            result.append({
                'date': month_start.isoformat(),
                'month_label': f"{month_start.strftime('%Y/%m')}",
                'available_min': total_avail,
                'line_load_sec': round(total_load_sec, 1), 'line_load_min': round(total_load_sec / 60, 1),
                'utilization': round(util, 1), 'is_working_day': total_avail > 0 or total_load_sec > 0,
                'processes': sorted(processes, key=lambda x: x['process_code']),
            })

        return result

    def get_coverage_summary(self, line_ids: List[int]) -> Dict[str, Any]:
        """サイクルタイム登録状況サマリ"""
        lines = Line.objects.filter(id__in=line_ids, is_active=True)

        from masters.models import Product
        final_products = Product.objects.filter(
            is_final_product=True, is_active=True,
        ).values_list('id', 'product_code', 'product_name')

        result = []
        for line in lines:
            registered = set(
                LineCycleTime.objects.filter(line=line, is_active=True)
                .values_list('product_id', flat=True)
                .distinct()
            )
            total = len(final_products)
            covered = len([p for p in final_products if p[0] in registered])
            result.append({
                'line_id': line.id,
                'line_code': line.line_code,
                'line_name': line.line_name,
                'total_products': total,
                'registered_products': covered,
                'coverage_pct': round(covered / total * 100, 1) if total > 0 else 0,
            })

        return {'lines': sorted(result, key=lambda x: x['line_code'])}
