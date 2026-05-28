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

from masters.models import BOM, BOMItem, Calendar
from orders.utils.calendar_utils import get_business_today, WorkingDayCalculator
from masters.models import Line
from production.models_laser_actual import LaserActual, LaserActualDetail
from production.models_line_backlog import LineBacklog
from production.models_gantt_display_product_map import GanttDisplayProductMap
from production.models_line_gantt_plan import LineGanttPlan
from production.models_plan_deviation_config import PlanDeviationLineConfig
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

        # 連産品の除外対象を取得
        active_coproduct_boms = BOM.objects.filter(is_coproduct=True, is_active=True)
        # 1) 連産品BOMの親製品（仮想セット品番）
        coproduct_parent_ids = set(
            active_coproduct_boms.values_list('parent_product_id', flat=True)
        )
        # 2) 連産品の子で代表品でない製品
        coproduct_non_driver_ids = set(
            BOMItem.objects
            .filter(bom__in=active_coproduct_boms, is_coproduct_driver=False)
            .values_list('child_product_id', flat=True)
        )
        coproduct_exclude_ids = coproduct_parent_ids | coproduct_non_driver_ids

        # LineGanttPlanを使用するライン一覧
        gantt_line_ids = set(
            PlanDeviationLineConfig.objects.values_list('line_id', flat=True)
        )

        # 工程・製品別に計画数を集計
        # key: (line_id, process_id, product_id)
        plan_map = {}  # key -> plan_qty
        info_map = {}  # key -> {line_code, process_name, ...}

        # --- LineBacklog から取得するライン（gantt_line_ids 以外） ---
        backlog_plan_filter = Q(
            plan_date=target_date,
            sequence_no__gt=0,
        )
        if line_id:
            backlog_plan_filter &= Q(line_id=line_id)
        if line_type:
            backlog_plan_filter &= Q(line__line_type=line_type)
        if process_id:
            backlog_plan_filter &= Q(process_id=process_id)
        if gantt_line_ids:
            backlog_plan_filter &= ~Q(line_id__in=gantt_line_ids)

        for row in (
            LineBacklog.objects
            .filter(backlog_plan_filter)
            .exclude(plan_qty=0)
            .exclude(product_id__in=coproduct_exclude_ids)
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

        # --- LineGanttPlan から取得するライン ---
        if gantt_line_ids:
            gantt_filter = Q(plan_date=target_date)
            if line_id:
                if int(line_id) in gantt_line_ids:
                    gantt_filter &= Q(line_id=line_id)
                else:
                    gantt_filter = None
            else:
                gantt_filter &= Q(line_id__in=gantt_line_ids)
                if line_type:
                    gantt_filter &= Q(line__line_type=line_type)

            if gantt_filter is not None:
                gantt_plans = (
                    LineGanttPlan.objects
                    .filter(gantt_filter)
                    .select_related('line', 'product')
                )
                from masters.models import Process
                process_cache = {}
                for gp in gantt_plans:
                    if not gp.processes_plan:
                        continue
                    for proc in gp.processes_plan:
                        proc_id = proc.get('process_id')
                        qty = proc.get('quantity', 0)
                        output_product_id = proc.get('output_product_id')
                        if not proc_id or not qty or not output_product_id:
                            continue
                        if process_id and proc_id != process_id:
                            continue
                        key = (gp.line_id, proc_id, output_product_id)
                        plan_map[key] = plan_map.get(key, 0) + int(qty)
                        if key not in info_map:
                            if proc_id not in process_cache:
                                try:
                                    process_cache[proc_id] = Process.objects.get(id=proc_id)
                                except Process.DoesNotExist:
                                    process_cache[proc_id] = None
                            proc_obj = process_cache[proc_id]
                            info_map[key] = {
                                'line_id': gp.line_id,
                                'line_code': gp.line.line_code,
                                'line_name': gp.line.line_name,
                                'process_id': proc_id,
                                'process_code': proc.get('process_code', proc_obj.process_code if proc_obj else ''),
                                'process_name': proc.get('process_name', proc_obj.process_name if proc_obj else ''),
                                'product_id': output_product_id,
                                'product_code': proc.get('output_product_code', ''),
                                'product_name': proc.get('output_product_name', ''),
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

        # ガント適用ライン以外: 連産品除外
        non_gantt_actual_filter = actual_filter
        if gantt_line_ids:
            non_gantt_actual_filter = actual_filter & ~Q(line_id__in=gantt_line_ids)
        for row in (
            LineBacklog.objects
            .filter(non_gantt_actual_filter)
            .exclude(actual_qty=0)
            .exclude(product_id__in=coproduct_exclude_ids)
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

        # ガント適用ライン: 連産品除外しない
        if gantt_line_ids:
            gantt_actual_filter = actual_filter & Q(line_id__in=gantt_line_ids)
            if line_id and int(line_id) not in gantt_line_ids:
                gantt_actual_filter = None
            if gantt_actual_filter is not None:
                for row in (
                    LineBacklog.objects
                    .filter(gantt_actual_filter)
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

        # ガント適用ライン: 表示マップに登録された(line, process, display_product)のみ許可
        gantt_allowed_keys = set()
        gantt_lines_with_map = set()
        if gantt_line_ids:
            for row in (
                GanttDisplayProductMap.objects
                .filter(line_id__in=gantt_line_ids)
                .values_list('line_id', 'process_id', 'display_product_id')
            ):
                gantt_allowed_keys.add(row)
                gantt_lines_with_map.add(row[0])

        # 乖離データ構築
        items = []
        for key in all_keys:
            line_id_of_key = key[0]

            # マップ登録があるガント適用ラインのみフィルタ
            if line_id_of_key in gantt_lines_with_map and key not in gantt_allowed_keys:
                continue

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
            'gantt_line_ids': sorted(gantt_line_ids),
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


class PlanDeviationLineConfigView(APIView):
    """計画乖離レポートのライン設定（LineGanttPlan使用ライン）"""

    def get(self, request):
        line_ids = list(
            PlanDeviationLineConfig.objects.values_list('line_id', flat=True)
        )
        return Response({'gantt_line_ids': sorted(line_ids)})

    def post(self, request):
        line_id = request.data.get('line_id')
        enabled = request.data.get('enabled', True)
        if not line_id:
            return Response({'detail': 'line_id は必須です'}, status=400)
        try:
            line_id = int(line_id)
        except (ValueError, TypeError):
            return Response({'detail': 'line_id が不正です'}, status=400)
        if not Line.objects.filter(id=line_id).exists():
            return Response({'detail': 'ライン不明'}, status=404)

        if enabled:
            PlanDeviationLineConfig.objects.get_or_create(line_id=line_id)
        else:
            PlanDeviationLineConfig.objects.filter(line_id=line_id).delete()

        line_ids = list(
            PlanDeviationLineConfig.objects.values_list('line_id', flat=True)
        )
        return Response({'gantt_line_ids': sorted(line_ids)})
