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
        demand_qs = LineDemand.objects.filter(
            line_id__in=final_line_ids,
            product__is_final_product=True,
            product_code__in=final_line_by_product_code.keys(),
            plan_date__gte=start_date,
            plan_date__lte=end_date,
        ).values(
            'line_id',
            'product_code',
            'plan_date',
            'forecast_qty',
            'firm_qty',
        )

        demand_map = defaultdict(float)
        for row in demand_qs:
            if final_line_by_product_code.get(row['product_code']) != row['line_id']:
                continue
            qty = float(row['forecast_qty'] or 0) + float(row['firm_qty'] or 0)
            if qty <= 0:
                continue
            demand_map[(row['product_code'], row['plan_date'])] += qty

        return demand_map

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
                max_load_sec = 0
                for proc_id, load_sec in process_loads.items():
                    proc = process_map.get(proc_id)
                    util = (load_sec / avail_sec * 100) if avail_sec > 0 else 0
                    process_detail.append({
                        'process_id': proc_id,
                        'process_code': proc.process_code if proc else '',
                        'process_name': proc.process_name if proc else '',
                        'load_sec': round(load_sec, 1),
                        'load_min': round(load_sec / 60, 1),
                        'utilization': round(util, 1),
                    })
                    if load_sec > max_load_sec:
                        max_load_sec = load_sec

                line_util = (max_load_sec / avail_sec * 100) if avail_sec > 0 else 0

                daily_data.append({
                    'date': current.isoformat(),
                    'available_min': avail_min,
                    'line_load_sec': round(max_load_sec, 1),
                    'line_load_min': round(max_load_sec / 60, 1),
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
            if not working_days:
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

            total_avail = sum(d['available_min'] for d in working_days)
            total_load_sec = sum(d['line_load_sec'] for d in working_days)
            util = (total_load_sec / (total_avail * 60) * 100) if total_avail > 0 else 0

            proc_totals = defaultdict(lambda: {'load_sec': 0, 'code': '', 'name': ''})
            for d in working_days:
                for p in d['processes']:
                    proc_totals[p['process_id']]['load_sec'] += p['load_sec']
                    proc_totals[p['process_id']]['code'] = p['process_code']
                    proc_totals[p['process_id']]['name'] = p['process_name']

            processes = []
            for pid, pt in proc_totals.items():
                p_util = (pt['load_sec'] / (total_avail * 60) * 100) if total_avail > 0 else 0
                processes.append({
                    'process_id': pid,
                    'process_code': pt['code'],
                    'process_name': pt['name'],
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
                'is_working_day': True,
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
            if not working_days:
                result.append({
                    'date': month_start.isoformat(),
                    'month_label': f"{month_start.strftime('%Y/%m')}",
                    'available_min': 0,
                    'line_load_sec': 0, 'line_load_min': 0,
                    'utilization': 0, 'is_working_day': False, 'processes': [],
                })
                continue

            total_avail = sum(d['available_min'] for d in working_days)
            total_load_sec = sum(d['line_load_sec'] for d in working_days)
            util = (total_load_sec / (total_avail * 60) * 100) if total_avail > 0 else 0

            proc_totals = defaultdict(lambda: {'load_sec': 0, 'code': '', 'name': ''})
            for d in working_days:
                for p in d['processes']:
                    proc_totals[p['process_id']]['load_sec'] += p['load_sec']
                    proc_totals[p['process_id']]['code'] = p['process_code']
                    proc_totals[p['process_id']]['name'] = p['process_name']

            processes = []
            for pid, pt in proc_totals.items():
                p_util = (pt['load_sec'] / (total_avail * 60) * 100) if total_avail > 0 else 0
                processes.append({
                    'process_id': pid, 'process_code': pt['code'], 'process_name': pt['name'],
                    'load_sec': round(pt['load_sec'], 1), 'load_min': round(pt['load_sec'] / 60, 1),
                    'utilization': round(p_util, 1),
                })

            result.append({
                'date': month_start.isoformat(),
                'month_label': f"{month_start.strftime('%Y/%m')}",
                'available_min': total_avail,
                'line_load_sec': round(total_load_sec, 1), 'line_load_min': round(total_load_sec / 60, 1),
                'utilization': round(util, 1), 'is_working_day': True,
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
