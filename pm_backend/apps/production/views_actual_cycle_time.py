"""出来高集計・実績サイクル時間計算API"""
from itertools import groupby
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_date
from datetime import datetime, time, timedelta
from decimal import Decimal

from .models_process_work_session import ProcessWorkSession
from .models_brake_line_record import BrakeLineRecord
from .models_actual_cycle_time import ActualCycleTime, FinishedProductCycleTime
from .services.gantt_planning import LineWorkCalendar
from .views_process_realtime import _calculate_effective_work_seconds
from masters.models import Process, Line, Product
from masters.services.bom_service import BOMService
from orders.utils.calendar_utils import DAY_BOUNDARY_HOUR


def _build_business_boundary(d, day_offset=0):
    target = d + timedelta(days=day_offset)
    return datetime.combine(target, time(DAY_BOUNDARY_HOUR, 0))


def _collect_brake_sessions(process_id, line_id, d_start, d_end):
    """BrakeLineRecordからSTART→ENDペアのセッションを構築して返す。"""
    qs = BrakeLineRecord.objects.filter(
        process_id=process_id,
        plan_date__gte=d_start,
        plan_date__lte=d_end,
    ).select_related('product')

    if line_id:
        qs = qs.filter(line_id=line_id)

    records = list(qs.order_by('process_id', 'product_id', 'equipment_id', 'recorded_at'))

    START_ACTIONS = {BrakeLineRecord.OPERATOR_ACTION_START, BrakeLineRecord.OPERATOR_ACTION_RESUME}
    END_ACTIONS = {BrakeLineRecord.OPERATOR_ACTION_END, BrakeLineRecord.OPERATOR_ACTION_PAUSE}

    def group_key(r):
        return (r.process_id, r.product_id or r.product_code, r.equipment_id)

    sessions = []
    for _key, grp in groupby(records, key=group_key):
        group = list(grp)
        open_rec = None
        for rec in group:
            action = rec.operator_action
            if action in START_ACTIONS:
                open_rec = rec
            elif action in END_ACTIONS:
                if not open_rec:
                    continue
                qty = int(rec.qty or 0)
                if qty <= 0:
                    open_rec = None
                    continue
                duration = int((rec.recorded_at - open_rec.recorded_at).total_seconds())
                product = open_rec.product or rec.product
                sessions.append({
                    'product_id': (product.id if product else None) or rec.product_id or open_rec.product_id,
                    'product_code': (product.product_code if product else '') or rec.product_code or open_rec.product_code or '',
                    'product_name': (product.product_name if product else '') or '',
                    'qty': qty,
                    'duration_seconds': max(duration, 0),
                })
                if action == BrakeLineRecord.OPERATOR_ACTION_END:
                    open_rec = None

    return sessions


class ActualCycleTimeCalcView(APIView):
    """実績サイクル時間を計算して返す"""

    def get(self, request):
        process_id = request.query_params.get('process_id')
        line_id = request.query_params.get('line_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not process_id or not start_date or not end_date:
            return Response(
                {'error': 'process_id, start_date, end_date は必須です'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        d_start = parse_date(start_date)
        d_end = parse_date(end_date)
        if not d_start or not d_end:
            return Response({'error': '日付形式が不正です'}, status=status.HTTP_400_BAD_REQUEST)

        process = Process.objects.filter(id=process_id).select_related('line').first()
        if not process:
            return Response({'error': '工程が見つかりません'}, status=status.HTTP_404_NOT_FOUND)

        resolved_line_id = int(line_id) if line_id else (process.line_id if process.line_id else None)

        # --- ProcessWorkSession から集計 ---
        pws_qs = ProcessWorkSession.objects.filter(
            process_id=process_id,
            session_type='WORK',
            status='CLOSED',
            started_at__gte=_build_business_boundary(d_start),
            started_at__lt=_build_business_boundary(d_end, day_offset=1),
            production_qty__gt=0,
        ).select_related('process__line', 'product')

        if line_id:
            pws_qs = pws_qs.filter(process__line_id=line_id)

        pws_sessions = list(pws_qs)

        calendar = None
        if resolved_line_id:
            try:
                line_obj = Line.objects.get(id=resolved_line_id)
                calendar = LineWorkCalendar(line_obj)
            except Exception:
                pass

        product_map = {}
        pws_session_ids = set()

        for s in pws_sessions:
            pid = s.product_id
            if not pid:
                continue
            pws_session_ids.add(s.id)
            if pid not in product_map:
                product_map[pid] = {
                    'product_id': pid,
                    'product_code': s.product_code or (s.product.product_code if s.product else ''),
                    'product_name': s.product_name or (s.product.product_name if s.product else ''),
                    'total_qty': Decimal('0'),
                    'total_seconds': 0,
                    'session_count': 0,
                }
            entry = product_map[pid]
            entry['total_qty'] += s.production_qty or Decimal('0')
            ended_at = s.ended_at or datetime.now()
            eff_sec = _calculate_effective_work_seconds(calendar, s.started_at, ended_at)
            entry['total_seconds'] += int(eff_sec)
            entry['session_count'] += 1

        # --- BrakeLineRecord から集計（ProcessWorkSessionに無いデータを補完） ---
        brake_sessions = _collect_brake_sessions(process_id, line_id, d_start, d_end)
        for bs in brake_sessions:
            pid = bs['product_id']
            if not pid:
                continue
            if pid not in product_map:
                product_map[pid] = {
                    'product_id': pid,
                    'product_code': bs['product_code'],
                    'product_name': bs['product_name'],
                    'total_qty': Decimal('0'),
                    'total_seconds': 0,
                    'session_count': 0,
                }
            entry = product_map[pid]
            entry['total_qty'] += Decimal(str(bs['qty']))
            entry['total_seconds'] += bs['duration_seconds']
            entry['session_count'] += 1

        if not product_map:
            return Response({
                'process_id': int(process_id),
                'line_id': resolved_line_id,
                'start_date': start_date,
                'end_date': end_date,
                'items': [],
                'summary': {'total_qty': 0, 'total_seconds': 0, 'avg_cycle_time_sec': None},
            })

        items = []
        grand_qty = Decimal('0')
        grand_seconds = 0
        for pid, entry in sorted(product_map.items(), key=lambda x: x[1]['product_code']):
            qty = entry['total_qty']
            sec = entry['total_seconds']
            ct = float((Decimal(str(sec)) / qty).quantize(Decimal('0.01'))) if qty > 0 else None
            items.append({
                'product_id': entry['product_id'],
                'product_code': entry['product_code'],
                'product_name': entry['product_name'],
                'total_qty': float(qty),
                'total_seconds': sec,
                'cycle_time_sec': ct,
                'session_count': entry['session_count'],
            })
            grand_qty += qty
            grand_seconds += sec

        avg_ct = float((Decimal(str(grand_seconds)) / grand_qty).quantize(Decimal('0.01'))) if grand_qty > 0 else None

        return Response({
            'process_id': int(process_id),
            'line_id': resolved_line_id,
            'start_date': start_date,
            'end_date': end_date,
            'items': items,
            'summary': {
                'total_qty': float(grand_qty),
                'total_seconds': grand_seconds,
                'avg_cycle_time_sec': avg_ct,
            },
        })


class ActualCycleTimeSaveView(APIView):
    """計算した実績サイクル時間をDBに保存"""

    def post(self, request):
        process_id = request.data.get('process_id')
        line_id = request.data.get('line_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        items = request.data.get('items', [])

        if not process_id or not start_date or not end_date or not items:
            return Response({'error': '必須パラメータが不足しています'}, status=status.HTTP_400_BAD_REQUEST)

        d_start = parse_date(start_date)
        d_end = parse_date(end_date)
        if not d_start or not d_end:
            return Response({'error': '日付形式が不正です'}, status=status.HTTP_400_BAD_REQUEST)

        from masters.models import Process
        process = Process.objects.filter(id=process_id).first()
        operating_rate = float(process.operating_rate) if process else 100.0

        saved_count = 0
        for item in items:
            product_id = item.get('product_id')
            total_qty = item.get('total_qty')
            total_seconds = item.get('total_seconds')
            cycle_time_sec = item.get('cycle_time_sec')
            if not product_id or not cycle_time_sec:
                continue

            ct = Decimal(str(cycle_time_sec))
            rate = Decimal(str(operating_rate))
            adjusted_ct = (ct / (rate / Decimal('100'))).quantize(Decimal('0.01')) if rate > 0 else ct

            ActualCycleTime.objects.update_or_create(
                product_id=product_id,
                process_id=process_id,
                line_id=line_id,
                calc_from_date=d_start,
                calc_to_date=d_end,
                defaults={
                    'total_qty': Decimal(str(total_qty or 0)),
                    'total_seconds': int(total_seconds or 0),
                    'cycle_time_sec': ct,
                    'adjusted_cycle_time_sec': adjusted_ct,
                    'operating_rate_applied': rate,
                },
            )
            saved_count += 1

        return Response({'saved_count': saved_count, 'operating_rate': float(operating_rate)})


class ActualCycleTimeDeleteByPeriodView(APIView):
    """指定期間の実績CT・完成品CTを一括削除"""

    def delete(self, request):
        calc_from_date = request.query_params.get('calc_from_date')
        calc_to_date = request.query_params.get('calc_to_date')
        line_id = request.query_params.get('line_id')
        process_id = request.query_params.get('process_id')

        if not calc_from_date or not calc_to_date:
            return Response({'error': 'calc_from_date, calc_to_date は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        d_from = parse_date(calc_from_date)
        d_to = parse_date(calc_to_date)
        if not d_from or not d_to:
            return Response({'error': '日付形式が不正です'}, status=status.HTTP_400_BAD_REQUEST)

        act_qs = ActualCycleTime.objects.filter(calc_from_date=d_from, calc_to_date=d_to)
        fin_qs = FinishedProductCycleTime.objects.filter(calc_from_date=d_from, calc_to_date=d_to)
        if line_id:
            act_qs = act_qs.filter(line_id=line_id)
            fin_qs = fin_qs.filter(line_id=line_id)
        if process_id:
            act_qs = act_qs.filter(process_id=process_id)
            fin_qs = fin_qs.filter(process_id=process_id)

        act_count = act_qs.count()
        fin_count = fin_qs.count()
        act_qs.delete()
        fin_qs.delete()

        return Response({
            'deleted_actual': act_count,
            'deleted_finished': fin_count,
        })


class ActualCycleTimeListView(APIView):
    """保存済み実績サイクル時間の照会"""

    def get(self, request):
        process_id = request.query_params.get('process_id')
        line_id = request.query_params.get('line_id')

        qs = ActualCycleTime.objects.select_related('product', 'process', 'line').order_by(
            'process__process_code', 'line__line_code', '-calc_from_date', 'product__product_code',
        )
        if process_id:
            qs = qs.filter(process_id=process_id)
        if line_id:
            qs = qs.filter(line_id=line_id)

        items = []
        for r in qs[:2000]:
            items.append({
                'id': r.id,
                'product_id': r.product_id,
                'product_code': r.product.product_code,
                'product_name': r.product.product_name,
                'process_id': r.process_id,
                'process_code': r.process.process_code,
                'process_name': r.process.process_name,
                'line_id': r.line_id,
                'line_code': r.line.line_code if r.line else '',
                'line_name': r.line.line_name if r.line else '',
                'calc_from_date': str(r.calc_from_date),
                'calc_to_date': str(r.calc_to_date),
                'total_qty': float(r.total_qty),
                'total_seconds': r.total_seconds,
                'cycle_time_sec': float(r.cycle_time_sec),
                'adjusted_cycle_time_sec': float(r.adjusted_cycle_time_sec) if r.adjusted_cycle_time_sec else None,
                'operating_rate_applied': float(r.operating_rate_applied) if r.operating_rate_applied else None,
                'calculated_at': r.calculated_at.strftime('%Y-%m-%d %H:%M') if r.calculated_at else '',
            })

        return Response(items)


class FinishedProductCycleTimeListView(APIView):
    """保存済み完成品サイクル時間の照会"""

    def get(self, request):
        process_id = request.query_params.get('process_id')
        line_id = request.query_params.get('line_id')

        qs = FinishedProductCycleTime.objects.select_related(
            'finished_product', 'process', 'line',
        ).order_by(
            'process__process_code', 'line__line_code', '-calc_from_date', 'finished_product__product_code',
        )
        if process_id:
            qs = qs.filter(process_id=process_id)
        if line_id:
            qs = qs.filter(line_id=line_id)

        items = []
        for r in qs[:2000]:
            items.append({
                'id': r.id,
                'finished_product_id': r.finished_product_id,
                'finished_product_code': r.finished_product.product_code,
                'finished_product_name': r.finished_product.product_name,
                'process_id': r.process_id,
                'process_code': r.process.process_code,
                'process_name': r.process.process_name,
                'line_id': r.line_id,
                'line_code': r.line.line_code if r.line else '',
                'line_name': r.line.line_name if r.line else '',
                'calc_from_date': str(r.calc_from_date),
                'calc_to_date': str(r.calc_to_date),
                'cycle_time_sec': float(r.cycle_time_sec),
                'calculated_at': r.calculated_at.strftime('%Y-%m-%d %H:%M') if r.calculated_at else '',
            })

        return Response(items)


class FinishedProductCycleTimeLatestForLineView(APIView):
    """指定ラインの最新完成品CT（製品×工程別）をマトリクス用マップで返す"""

    def get(self, request):
        line_id = request.query_params.get('line_id')
        if not line_id:
            return Response({'error': 'line_id は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        qs = FinishedProductCycleTime.objects.filter(
            line_id=line_id,
        ).order_by('finished_product_id', 'process_id', '-calc_from_date')

        best = {}
        for r in qs:
            key = f'{r.finished_product_id}_{r.process_id}'
            if key not in best:
                best[key] = {
                    'cycle_time_sec': float(r.cycle_time_sec),
                    'calc_from_date': str(r.calc_from_date),
                    'calc_to_date': str(r.calc_to_date),
                }

        return Response({
            'line_id': int(line_id),
            'count': len(best),
            'values': best,
        })


class FinishedProductCycleTimeConsolidatedView(APIView):
    """完成品×工程のサイクル時間を集約（同一完成品の複数部品を合算）"""

    def get(self, request):
        process_id = request.query_params.get('process_id')
        line_id = request.query_params.get('line_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not process_id or not line_id or not start_date or not end_date:
            return Response(
                {'error': 'process_id, line_id, start_date, end_date は必須です'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        d_start = parse_date(start_date)
        d_end = parse_date(end_date)

        actual_cts = ActualCycleTime.objects.filter(
            process_id=process_id,
            line_id=line_id,
            calc_from_date=d_start,
            calc_to_date=d_end,
        ).select_related('product')

        if not actual_cts.exists():
            return Response({
                'process_id': int(process_id),
                'line_id': int(line_id),
                'items': [],
                'message': '実績サイクル時間が保存されていません。先に実績サイクル時間を計算・保存してください。',
            })

        ct_by_product = {}
        for act in actual_cts:
            ct_by_product[act.product_id] = {
                'product_id': act.product_id,
                'product_code': act.product.product_code,
                'product_name': act.product.product_name,
                'cycle_time_sec': float(act.cycle_time_sec),
            }

        bom_service = BOMService()
        consolidated = {}

        for product_id, ct_info in ct_by_product.items():
            parents = bom_service.get_where_used(product_id, recursive=True)
            self._accumulate(parents, product_id, ct_info, Decimal('1'), consolidated, bom_service)

        items = []
        for fp_id, entry in sorted(consolidated.items(), key=lambda x: x[1]['finished_product_code']):
            entry['total_cycle_time_sec'] = float(
                Decimal(str(entry['total_cycle_time_sec'])).quantize(Decimal('0.01'))
            )
            for comp in entry['components']:
                comp['finished_cycle_time_sec'] = float(
                    Decimal(str(comp['finished_cycle_time_sec'])).quantize(Decimal('0.01'))
                )
            items.append(entry)

        return Response({
            'process_id': int(process_id),
            'line_id': int(line_id),
            'start_date': start_date,
            'end_date': end_date,
            'items': items,
        })

    def _accumulate(self, parents, component_product_id, ct_info, cumulative_qty, consolidated, bom_service):
        if not parents:
            return
        for parent in parents:
            parent_id = parent['parent_product_id']
            bom_qty = Decimal(str(parent.get('quantity', 1)))
            total_qty = cumulative_qty * bom_qty

            if parent.get('is_final_product'):
                if parent_id not in consolidated:
                    consolidated[parent_id] = {
                        'finished_product_id': parent_id,
                        'finished_product_code': parent['parent_product_code'],
                        'finished_product_name': parent['parent_product_name'],
                        'components': [],
                        'total_cycle_time_sec': 0,
                    }
                component_ct = Decimal(str(ct_info['cycle_time_sec']))
                finished_ct = float(component_ct * total_qty)
                consolidated[parent_id]['components'].append({
                    'component_product_id': component_product_id,
                    'component_product_code': ct_info['product_code'],
                    'component_product_name': ct_info['product_name'],
                    'bom_qty': float(total_qty),
                    'component_cycle_time_sec': ct_info['cycle_time_sec'],
                    'finished_cycle_time_sec': finished_ct,
                })
                consolidated[parent_id]['total_cycle_time_sec'] += finished_ct

            further_parents = parent.get('parents', [])
            if further_parents:
                self._accumulate(
                    further_parents, component_product_id, ct_info, total_qty, consolidated, bom_service,
                )


class FinishedProductCycleTimeSaveView(APIView):
    """完成品サイクル時間をDBに保存"""

    def post(self, request):
        process_id = request.data.get('process_id')
        line_id = request.data.get('line_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        items = request.data.get('items', [])

        if not process_id or not line_id or not start_date or not end_date or not items:
            return Response({'error': '必須パラメータが不足しています'}, status=status.HTTP_400_BAD_REQUEST)

        d_start = parse_date(start_date)
        d_end = parse_date(end_date)

        saved_count = 0
        for item in items:
            finished_product_id = item.get('finished_product_id')
            total_cycle_time_sec = item.get('total_cycle_time_sec')
            if not finished_product_id or total_cycle_time_sec is None:
                continue

            FinishedProductCycleTime.objects.update_or_create(
                finished_product_id=finished_product_id,
                process_id=process_id,
                line_id=line_id,
                calc_from_date=d_start,
                calc_to_date=d_end,
                defaults={
                    'cycle_time_sec': Decimal(str(total_cycle_time_sec)),
                },
            )
            saved_count += 1

        return Response({'saved_count': saved_count})
