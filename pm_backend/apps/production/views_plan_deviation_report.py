"""
日次計画乖離レポートAPI
ガントチャート計画（LineGanttPlan）vs 実績（LineBacklog.actual_qty）の乖離を
工程・製品ごとに集計する。
"""
from datetime import date

from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from masters.models import Calendar
from orders.utils.calendar_utils import get_business_today, WorkingDayCalculator
from production.models_line_backlog import LineBacklog
from production.models_line_gantt_plan import LineGanttPlan


def _get_previous_business_day():
    """DAISOカレンダで前営業日を取得する"""
    today = get_business_today()
    cal = Calendar.objects.filter(calendar_code='daiso').first()
    calc = WorkingDayCalculator(cal)
    return calc.get_prev_working_day(today)


class PlanDeviationReportView(APIView):
    """
    計画乖離レポート
    GET /api/production/plan-deviation-report/?date=YYYY-MM-DD&line_id=X

    ガントチャート上の計画（LineGanttPlan.processes_plan）と
    LineBacklog(sequence_no=0).actual_qty を比較し、乖離のある行を返す。
    """

    def get(self, request):
        # 対象日（未指定なら前営業日）
        date_str = request.query_params.get('date')
        if date_str:
            try:
                target_date = date.fromisoformat(date_str)
            except ValueError:
                return Response({'detail': '日付形式が不正です（YYYY-MM-DD）'}, status=400)
        else:
            target_date = _get_previous_business_day()

        line_id = request.query_params.get('line_id')
        line_type = request.query_params.get('line_type')
        process_id = request.query_params.get('process_id')
        if process_id:
            try:
                process_id = int(process_id)
            except (ValueError, TypeError):
                process_id = None

        # ガントチャート計画を取得
        gantt_filter = Q(plan_date=target_date)
        if line_id:
            gantt_filter &= Q(line_id=line_id)
        if line_type:
            gantt_filter &= Q(line__line_type=line_type)

        gantt_plans = LineGanttPlan.objects.filter(gantt_filter).select_related('line', 'product')

        # 工程・製品別に計画数を集計
        # key: (line_id, process_id, product_id)
        plan_map = {}  # key -> plan_qty
        info_map = {}  # key -> {line_code, process_name, ...}
        for gp in gantt_plans:
            processes = gp.processes_plan or []
            for pp in processes:
                pp_process_id = pp.get('process_id')
                output_product_id = pp.get('output_product_id') or gp.product_id
                qty = pp.get('quantity', 0)
                if not pp_process_id or not qty:
                    continue
                if process_id and pp_process_id != process_id:
                    continue

                key = (gp.line_id, pp_process_id, output_product_id)
                plan_map[key] = plan_map.get(key, 0) + int(qty)
                if key not in info_map:
                    info_map[key] = {
                        'line_id': gp.line_id,
                        'line_code': gp.line.line_code if gp.line else '',
                        'line_name': gp.line.line_name if gp.line else '',
                        'process_id': process_id,
                        'process_code': '',
                        'process_name': pp.get('process_name', ''),
                        'product_id': output_product_id,
                        'product_code': pp.get('output_product_code', ''),
                        'product_name': pp.get('output_product_name', ''),
                    }

        # 実績数取得（sequence_no=0）
        actual_filter = Q(plan_date=target_date, sequence_no=0)
        if line_id:
            actual_filter &= Q(line_id=line_id)
        if line_type:
            actual_filter &= Q(line__line_type=line_type)
        if process_id:
            actual_filter &= Q(process_id=process_id)

        actual_map = {}
        actual_info = {}
        for row in (
            LineBacklog.objects
            .filter(actual_filter)
            .exclude(actual_qty=0)
            .values(
                'line_id', 'line__line_code', 'line__line_name',
                'process_id', 'process__process_code', 'process__process_name',
                'product_id', 'product__product_code', 'product__product_name',
                'actual_qty',
            )
        ):
            key = (row['line_id'], row['process_id'], row['product_id'])
            actual_map[key] = row['actual_qty'] or 0
            actual_info[key] = {
                'line_id': row['line_id'],
                'line_code': row['line__line_code'],
                'line_name': row['line__line_name'],
                'process_id': row['process_id'],
                'process_code': row['process__process_code'],
                'process_name': row['process__process_name'],
                'product_id': row['product_id'],
                'product_code': row['product__product_code'],
                'product_name': row['product__product_name'],
            }

        # 全キーを統合（計画あり or 実績あり）
        all_keys = set(plan_map.keys()) | set(actual_map.keys())

        # 乖離データ構築
        items = []
        for key in all_keys:
            plan_qty = plan_map.get(key, 0)
            actual_qty = actual_map.get(key, 0)
            deviation = actual_qty - plan_qty

            # 乖離がない行はスキップ
            if deviation == 0:
                continue

            # マスタ情報取得（ガント計画情報を優先、なければ実績側の情報）
            info = info_map.get(key) or actual_info.get(key)
            if not info:
                continue

            deviation_rate = round(deviation / plan_qty * 100, 1) if plan_qty else None

            # 状態判定
            if plan_qty == 0 and actual_qty > 0:
                status = 'unplanned'
            elif deviation > 0:
                status = 'over'
            else:
                status = 'short'

            items.append({
                **info,
                'plan_qty': plan_qty,
                'actual_qty': actual_qty,
                'deviation': deviation,
                'deviation_rate': deviation_rate,
                'status': status,
            })

        # 乖離数の絶対値でソート（大きい順）
        items.sort(key=lambda x: abs(x['deviation']), reverse=True)

        return Response({
            'date': str(target_date),
            'items': items,
            'summary': {
                'total': len(items),
                'over_count': sum(1 for x in items if x['status'] == 'over'),
                'short_count': sum(1 for x in items if x['status'] == 'short'),
                'unplanned_count': sum(1 for x in items if x['status'] == 'unplanned'),
            },
        })
