"""
日次計画乖離レポートAPI
計画（LineBacklog.plan_qty）vs 実績（LineBacklog.actual_qty）の乖離を
工程・製品ごとに集計する。
"""
from collections import defaultdict
from datetime import date

from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from masters.models import Calendar
from orders.utils.calendar_utils import get_business_today, WorkingDayCalculator
from masters.models import Line
from production.models_laser_actual import LaserActual, LaserActualDetail
from production.models_line_backlog import LineBacklog
from production.models_record_confirmation import ProductionRecordConfirmation


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

    LineBacklog(sequence_no>0).plan_qty と
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

        # 工程・製品別に計画数を集計（全ライン: LineBacklog sequence_no>0）
        # key: (line_id, process_id, product_id)
        plan_map = {}  # key -> plan_qty
        info_map = {}  # key -> {line_code, process_name, ...}
        plan_filter = Q(
            plan_date=target_date,
            sequence_no__gt=0,
        )
        if line_id:
            plan_filter &= Q(line_id=line_id)
        if line_type:
            plan_filter &= Q(line__line_type=line_type)
        if process_id:
            plan_filter &= Q(process_id=process_id)

        for row in (
            LineBacklog.objects
            .filter(plan_filter)
            .exclude(plan_qty=0)
            .values(
                'line_id', 'line__line_code', 'line__line_name',
                'process_id', 'process__process_code', 'process__process_name',
                'product_id', 'product__product_code', 'product__product_name',
                'plan_qty',
            )
        ):
            key = (row['line_id'], row['process_id'], row['product_id'])
            plan_map[key] = plan_map.get(key, 0) + int(row['plan_qty'] or 0)
            if key not in info_map:
                info_map[key] = {
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

        # レーザライン選択時: 重複実績検出
        laser_duplicates = []
        if line_id:
            try:
                selected_line = Line.objects.get(id=line_id)
                if 'レーザ' in (selected_line.line_name or ''):
                    laser_duplicates = self._detect_laser_duplicates(target_date)
            except Line.DoesNotExist:
                pass

        # 確認済みフラグ取得
        confirmation = None
        if line_id and process_id:
            conf = ProductionRecordConfirmation.objects.filter(
                work_date=target_date, line_id=line_id, process_id=process_id,
            ).select_related('confirmed_by').first()
            if conf:
                confirmation = {
                    'confirmed_by_name': (
                        conf.confirmed_by.get_full_name() or conf.confirmed_by.username
                    ) if conf.confirmed_by else '',
                    'confirmed_at': conf.confirmed_at.isoformat() if conf.confirmed_at else None,
                }

        return Response({
            'date': str(target_date),
            'items': items,
            'summary': {
                'total': len(items),
                'over_count': sum(1 for x in items if x['status'] == 'over'),
                'short_count': sum(1 for x in items if x['status'] == 'short'),
                'unplanned_count': sum(1 for x in items if x['status'] == 'unplanned'),
            },
            'laser_duplicates': laser_duplicates,
            'confirmation': confirmation,
        })

    @staticmethod
    def _detect_laser_duplicates(target_date):
        """
        レーザ実績の重複検出:
        同じ日に同じ品番（完成品）で同じ数量のレコードが2件以上ある場合を検出
        """
        details = (
            LaserActualDetail.objects
            .filter(
                actual__work_date=target_date,
                detail_type=LaserActualDetail.DETAIL_TYPE_COMPONENT,
            )
            .exclude(total_qty=0)
            .select_related('actual')
            .values(
                'product_code', 'total_qty',
                'actual__id', 'actual__pattern_no',
                'actual__shot_count', 'actual__created_at',
                'actual__equipment_code',
            )
        )

        # (品番, 数量) でグルーピング
        groups = defaultdict(list)
        for d in details:
            key = (d['product_code'], float(d['total_qty']))
            groups[key].append(d)

        duplicates = []
        for (product_code, total_qty), records in groups.items():
            if len(records) < 2:
                continue
            duplicates.append({
                'product_code': product_code,
                'total_qty': total_qty,
                'count': len(records),
                'records': [
                    {
                        'actual_id': r['actual__id'],
                        'pattern_no': r['actual__pattern_no'],
                        'shot_count': r['actual__shot_count'],
                        'equipment_code': r['actual__equipment_code'],
                        'created_at': r['actual__created_at'].isoformat() if r['actual__created_at'] else None,
                    }
                    for r in records
                ],
            })

        # 数量の大きい順
        duplicates.sort(key=lambda x: x['total_qty'], reverse=True)
        return duplicates
