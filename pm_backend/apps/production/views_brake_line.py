"""
ブレーキライン専用ビュー
- BrakeLinePlanView: 自動計画取得（昨日のレーザ実績 → 今日の計画）
- BrakeLineActualAddView: 実績累積加算（後方互換用）
- BrakeLineRecordView: 作業記録（開始/終了/中断/再開/一時終了）
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from itertools import groupby
import logging

from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from masters.models import BreakTime, Calendar, CalendarDay, Equipment, Line, Process, Product, RoutingStep
from django.conf import settings
from orders.utils.calendar_utils import DAY_BOUNDARY_HOUR, get_business_today, WorkingDayCalculator
from production.models_brake_line_record import BrakeLineRecord
from production.models_line_backlog import LineBacklog
from production.models_record_inquiry_setting import ProductionRecordInquirySetting
from production.services.brake_spot_session_sync import find_equipment_active_product_conflict
from production.models_process_work_session_change_history import ProcessWorkSessionChangeHistory
from production.serializers_process_realtime import check_plan_overrun

logger = logging.getLogger(__name__)


def _get_line_break_config(line_id):
    """ラインのカレンダーIDと休憩定義を取得してキャッシュ用に返す"""
    try:
        line = Line.objects.get(pk=line_id)
    except Line.DoesNotExist:
        return None
    calendar_id = line.calendar_id
    if not calendar_id:
        from masters.models import Calendar as Cal
        calendar_id = Cal.objects.filter(calendar_code='daiso').values_list('id', flat=True).first()
    if not calendar_id:
        return None
    return {'calendar_id': calendar_id}


def _deduct_break_seconds(break_config, start_dt, end_dt, raw_seconds):
    """セッションの生時間から、カレンダー休憩の重複分だけを減算する"""
    if not break_config:
        return raw_seconds
    calendar_id = break_config['calendar_id']

    check_date = start_dt.date() - timedelta(days=1)
    last_date = end_dt.date() + timedelta(days=1)
    total_break = 0

    while check_date <= last_date:
        cal_day = CalendarDay.objects.filter(
            calendar_id=calendar_id, target_date=check_date,
        ).first()
        if cal_day and cal_day.work_pattern_id:
            breaks = BreakTime.objects.filter(
                work_pattern_id=cal_day.work_pattern_id,
            ).order_by('order')
            for br in breaks:
                br_start_min = br.break_start.hour * 60 + br.break_start.minute
                br_end_min = br.break_end.hour * 60 + br.break_end.minute
                if br_end_min <= br_start_min:
                    br_end_min += 24 * 60
                base = datetime.combine(check_date, time(0, 0))
                br_start_dt = base + timedelta(minutes=br_start_min)
                br_end_dt = base + timedelta(minutes=br_end_min)
                overlap_start = max(start_dt, br_start_dt)
                overlap_end = min(end_dt, br_end_dt)
                if overlap_end > overlap_start:
                    total_break += int((overlap_end - overlap_start).total_seconds())
        check_date += timedelta(days=1)

    return max(raw_seconds - total_break, 0)


class BrakeLinePlanView(APIView):
    """
    ブレーキライン自動計画取得
    GET /api/production/brake-line-plan/?date=YYYY-MM-DD

    今日の計画 = 昨日のレーザ実績（FINISHED）の製品
    product_mappings が設定されている場合はレーザ品番 → ブレーキ品番に変換
    """

    def get(self, request):
        # 計画日の決定（未指定 → 8時区切りの今日）
        plan_date_str = request.query_params.get('date')
        if plan_date_str:
            try:
                plan_date = date.fromisoformat(plan_date_str)
            except ValueError:
                return Response({'detail': '日付形式が不正です（YYYY-MM-DD）'}, status=400)
        else:
            plan_date = get_business_today()

        # daisoカレンダで「計画日の直前営業日」= レーザ実績参照日
        daiso_cal = Calendar.objects.filter(calendar_code__iexact='daiso').first()
        calc = WorkingDayCalculator(daiso_cal)  # カレンダ未登録の場合は週末スキップで代替
        laser_date = calc.get_prev_working_day(plan_date)

        # ブレーキライン設定取得
        try:
            setting = ProductionRecordInquirySetting.objects.get(
                tab_key=ProductionRecordInquirySetting.TAB_BRAKE
            )
        except ProductionRecordInquirySetting.DoesNotExist:
            return Response({'detail': 'ブレーキライン設定が存在しません。管理者に連絡してください。'}, status=404)

        target_line_codes = setting.target_line_codes or []
        product_mappings = setting.product_mappings or []

        # ブレーキラインのLine取得
        lines = list(
            Line.objects.filter(line_code__in=target_line_codes, is_active=True)
            .values('id', 'line_code', 'line_name')
        )
        if not lines:
            return Response({
                'plan_date': str(plan_date),
                'laser_date': str(laser_date),
                'lines': [],
                'processes': [],
                'items': [],
            })

        line_ids = [l['id'] for l in lines]

        # ブレーキラインの工程取得（Process.line FK で紐付け）
        processes = list(
            Process.objects.filter(line_id__in=line_ids, is_active=True)
            .values('id', 'process_code', 'process_name')
            .order_by('process_code')
        )
        process_ids = [p['id'] for p in processes]

        # 工程ごとの加工対象品（RoutingStep.output_product）を事前取得
        process_product_ids: dict[int, set[int]] = {}
        if process_ids:
            for row in (
                RoutingStep.objects
                .filter(process_id__in=process_ids, output_product__isnull=False)
                .values('process_id', 'output_product_id')
                .distinct()
            ):
                pid = row['process_id']
                process_product_ids.setdefault(pid, set()).add(row['output_product_id'])

        # レーザライン設定取得（レーザ実績は LineBacklog.actual_qty から参照）
        laser_line_codes = []
        try:
            laser_setting = ProductionRecordInquirySetting.objects.get(
                tab_key=ProductionRecordInquirySetting.TAB_LASER
            )
            laser_line_codes = laser_setting.target_line_codes or []
        except ProductionRecordInquirySetting.DoesNotExist:
            laser_line_codes = []

        laser_line_ids = list(
            Line.objects
            .filter(line_code__in=laser_line_codes, is_active=True)
            .values_list('id', flat=True)
        )

        # レーザ実績（line_backlog.actual_qty）を品番ごとに集計
        laser_qs = (
            LineBacklog.objects
            .filter(
                plan_date=laser_date,
                line_id__in=laser_line_ids,
                actual_qty__gt=0,
            )
            .values('product__product_code', 'product__product_name', 'product_id')
            .annotate(laser_qty=Sum('actual_qty'))
        )

        # ブレーキ品番変換ルール: レーザ品番 + "B"
        # product_mappings に個別上書きがあればそちらを優先する
        override_dict: dict[str, str] = {}
        for m in product_mappings:
            if isinstance(m, dict):
                lc = m.get('laser_product_code') or m.get('from')
                bc = m.get('brake_product_code') or m.get('to')
                if lc and bc:
                    override_dict[lc] = bc

        # {brake_product_code: {laser_qty, product_id}}
        brake_plan: dict[str, dict] = {}
        for row in laser_qs:
            laser_code = row['product__product_code']
            laser_qty = float(row['laser_qty'] or 0)
            if laser_qty <= 0:
                continue

            # 個別上書きがあれば使用、なければ末尾に"B"を付与
            brake_code = override_dict.get(laser_code, laser_code + 'B')

            if brake_code in brake_plan:
                brake_plan[brake_code]['laser_qty'] += laser_qty
            else:
                brake_plan[brake_code] = {
                    'laser_qty': laser_qty,
                    'product_id': None,
                }

        # ブレーキ品番の製品情報をDBから取得
        brake_codes = list(brake_plan.keys())
        brake_products = {
            p.product_code: p
            for p in Product.objects.filter(product_code__in=brake_codes)
        }
        for code, info in list(brake_plan.items()):
            p = brake_products.get(code)
            if p:
                info['product_name'] = p.product_name
                info['product_id'] = p.id
            else:
                # 品番マスタに存在しない = ブレーキライン加工対象外 → スキップ
                del brake_plan[code]

        # 計画行は sequence_no>0 から取得
        backlogs_qs = LineBacklog.objects.filter(
            plan_date=plan_date,
            line_id__in=line_ids,
            sequence_no__gt=0,
        ).select_related('product', 'process', 'line')

        # 実績は sequence_no=0 行から取得
        actual_map = {
            (row['line_id'], row['process_id'], row['product_id']): int(row['total'] or 0)
            for row in (
                LineBacklog.objects
                .filter(
                    plan_date=plan_date,
                    line_id__in=line_ids,
                    sequence_no=0,
                )
                .values('line_id', 'process_id', 'product_id')
                .annotate(total=Sum('actual_qty'))
            )
        }

        # (line_id, process_id, product_id) → 計画backlog
        backlog_map: dict[tuple, LineBacklog] = {}
        for lb in backlogs_qs:
            key = (lb.line_id, lb.process_id, lb.product_id)
            existing = backlog_map.get(key)
            if existing is None:
                backlog_map[key] = lb
                continue

            # 同じ品番の複数計画行がある場合は小さい sequence_no を優先
            if lb.sequence_no < existing.sequence_no:
                backlog_map[key] = lb

        line_map = {line['id']: line for line in lines}
        process_map = {proc['id']: proc for proc in processes}

        # 結果組み立て
        items = []
        item_keys = set()
        for brake_code, info in brake_plan.items():
            product_id = info.get('product_id')
            product_name = info.get('product_name', '')
            laser_qty = info['laser_qty']

            for line in lines:
                line_id = line['id']
                for proc in processes:
                    process_id = proc['id']
                    allowed_products = process_product_ids.get(process_id)
                    if product_id and allowed_products is not None and product_id not in allowed_products:
                        continue
                    lb = backlog_map.get((line_id, process_id, product_id))
                    key = (line_id, process_id, product_id or f'code:{brake_code}')
                    if key in item_keys:
                        continue
                    plan_qty = int(lb.plan_qty) if lb else 0
                    if plan_qty <= 0:
                        plan_qty = int(laser_qty)
                    items.append({
                        'product_id': product_id,
                        'product_code': brake_code,
                        'product_name': product_name,
                        'line_id': line_id,
                        'line_code': line['line_code'],
                        'line_name': line['line_name'],
                        'process_id': process_id,
                        'process_code': proc['process_code'],
                        'process_name': proc['process_name'],
                        'laser_qty': laser_qty,
                        'plan_qty': plan_qty,
                        'actual_qty': actual_map.get((line_id, process_id, product_id), 0),
                        'backlog_id': lb.id if lb else None,
                        'sequence_no': lb.sequence_no if lb else 1,
                        'equipment_id': None,
                        'is_manual': False,
                    })
                    item_keys.add(key)

        # 追加加工（手動追加）で保存済みの作業記録を復元
        manual_records_qs = (
            BrakeLineRecord.objects
            .filter(plan_date=plan_date, line_id__in=line_ids)
            .select_related('product')
            .order_by('-recorded_at')
        )
        if process_map:
            manual_records_qs = manual_records_qs.filter(process_id__in=list(process_map.keys()))

        latest_manual_records = {}
        manual_codes = set()
        for rec in manual_records_qs:
            product_code = (rec.product.product_code if rec.product_id else rec.product_code) or ''
            product_code = product_code.strip()
            if not rec.product_id and not product_code:
                continue
            rec_key = (rec.line_id, rec.process_id, rec.product_id or f'code:{product_code}')
            if rec_key in latest_manual_records:
                continue
            latest_manual_records[rec_key] = rec
            if not rec.product_id and product_code:
                manual_codes.add(product_code)

        manual_products_by_code = {
            p.product_code: p for p in Product.objects.filter(product_code__in=list(manual_codes))
        }

        for rec in latest_manual_records.values():
            line_data = line_map.get(rec.line_id)
            process_data = process_map.get(rec.process_id)
            if not line_data or not process_data:
                continue

            product = rec.product
            product_code = (product.product_code if product else rec.product_code or '').strip()
            mapped_product = manual_products_by_code.get(product_code) if not product else product
            product_id = product.id if product else (mapped_product.id if mapped_product else None)
            product_name = (
                (product.product_name if product else '')
                or (mapped_product.product_name if mapped_product else '')
                or '（追加）'
            )

            key = (rec.line_id, rec.process_id, product_id or f'code:{product_code}')
            if key in item_keys:
                continue

            lb = backlog_map.get((rec.line_id, rec.process_id, product_id)) if product_id else None
            items.append({
                'product_id': product_id,
                'product_code': product_code,
                'product_name': product_name,
                'line_id': rec.line_id,
                'line_code': line_data['line_code'],
                'line_name': line_data['line_name'],
                'process_id': rec.process_id,
                'process_code': process_data['process_code'],
                'process_name': process_data['process_name'],
                'laser_qty': 0,
                'plan_qty': int(lb.plan_qty) if lb else 0,
                'actual_qty': actual_map.get((rec.line_id, rec.process_id, product_id), 0),
                'backlog_id': lb.id if lb else None,
                'sequence_no': lb.sequence_no if lb else (rec.sequence_no or 1),
                'equipment_id': rec.equipment_id,
                'is_manual': True,
            })
            item_keys.add(key)

        # 前日以前に中断（PAUSE/TEMP_END）したまま未解決のアイテムを carryover として追加
        PAUSED_ACTIONS = {
            BrakeLineRecord.OPERATOR_ACTION_PAUSE,
            BrakeLineRecord.OPERATOR_ACTION_TEMP_END,
        }
        carryover_qs = (
            BrakeLineRecord.objects
            .filter(plan_date__lt=plan_date, line_id__in=line_ids)
            .select_related('product')
            .order_by('-recorded_at')
        )
        if process_map:
            carryover_qs = carryover_qs.filter(process_id__in=list(process_map.keys()))

        seen_carryover_keys: set = set()
        carryover_manual_codes: set = set()
        carryover_recs = []
        for rec in carryover_qs:
            product_code_raw = (rec.product.product_code if rec.product_id else rec.product_code) or ''
            product_code_raw = product_code_raw.strip()
            if not rec.product_id and not product_code_raw:
                continue
            rec_key = (rec.line_id, rec.process_id, rec.product_id or f'code:{product_code_raw}')
            if rec_key in seen_carryover_keys:
                continue
            seen_carryover_keys.add(rec_key)
            if rec.operator_action not in PAUSED_ACTIONS:
                continue
            if rec_key in item_keys:
                continue
            carryover_recs.append(rec)
            if not rec.product_id and product_code_raw:
                carryover_manual_codes.add(product_code_raw)

        carryover_products_by_code = {
            p.product_code: p for p in Product.objects.filter(product_code__in=list(carryover_manual_codes))
        }

        for rec in carryover_recs:
            line_data = line_map.get(rec.line_id)
            process_data = process_map.get(rec.process_id)
            if not line_data or not process_data:
                continue

            product = rec.product
            product_code = (product.product_code if product else rec.product_code or '').strip()
            mapped_product = carryover_products_by_code.get(product_code) if not product else product
            product_id = product.id if product else (mapped_product.id if mapped_product else None)
            product_name = (
                (product.product_name if product else '')
                or (mapped_product.product_name if mapped_product else '')
                or '（追加）'
            )

            key = (rec.line_id, rec.process_id, product_id or f'code:{product_code}')
            if key in item_keys:
                continue

            lb = backlog_map.get((rec.line_id, rec.process_id, product_id)) if product_id else None
            items.append({
                'product_id': product_id,
                'product_code': product_code,
                'product_name': product_name,
                'line_id': rec.line_id,
                'line_code': line_data['line_code'],
                'line_name': line_data['line_name'],
                'process_id': rec.process_id,
                'process_code': process_data['process_code'],
                'process_name': process_data['process_name'],
                'laser_qty': 0,
                'plan_qty': int(lb.plan_qty) if lb else 0,
                'actual_qty': actual_map.get((rec.line_id, rec.process_id, product_id), 0),
                'backlog_id': lb.id if lb else None,
                'sequence_no': lb.sequence_no if lb else (rec.sequence_no or 1),
                'equipment_id': rec.equipment_id,
                'is_manual': True,
                'is_carryover': True,
                'carryover_plan_date': str(rec.plan_date),
            })
            item_keys.add(key)

        # 後工程の取得（製品マスタの next_process フィールドから）
        product_ids = [item['product_id'] for item in items if item.get('product_id')]
        next_process_map = {}
        if product_ids:
            for p in Product.objects.filter(id__in=product_ids).select_related('next_process'):
                if p.next_process_id:
                    next_process_map[p.id] = p.next_process.process_name
        for item in items:
            pid = item.get('product_id')
            item['next_process_name'] = next_process_map.get(pid, '') if pid else ''

        return Response({
            'plan_date': str(plan_date),
            'laser_date': str(laser_date),
            'lines': lines,
            'processes': processes,
            'items': items,
        })


class BrakeLineProductsView(APIView):
    """
    ブレーキライン加工品一覧（追加加工用セレクト向け）
    GET /api/production/brake-line-products/
    品番末尾が'B'の有効製品を返す（product_mappings上書き分も含む）
    """

    def get(self, request):
        try:
            setting = ProductionRecordInquirySetting.objects.get(
                tab_key=ProductionRecordInquirySetting.TAB_BRAKE
            )
        except ProductionRecordInquirySetting.DoesNotExist:
            return Response([], status=200)

        product_mappings = setting.product_mappings or []
        process_id = request.query_params.get('process_id')

        # 個別マッピングで指定されたブレーキ品番
        override_codes = set()
        for m in product_mappings:
            if isinstance(m, dict):
                bc = m.get('brake_product_code') or m.get('to')
                if bc:
                    override_codes.add(bc)

        from django.db.models import Q

        # 工程が指定されている場合:
        # ルーティング上、その工程で加工される品番（RoutingStep.output_product）で絞る
        if process_id:
            process_obj = Process.objects.filter(id=process_id, is_active=True).only('id', 'line_id').first()
            if not process_obj:
                return Response([], status=200)

            # その工程を持つRoutingStepのoutput_product_id（その工程で生産される品番）
            routing_product_ids = set(
                RoutingStep.objects.filter(
                    process_id=process_obj.id,
                    output_product__isnull=False,
                ).values_list('output_product_id', flat=True).distinct()
            )

            # process_id指定時はRoutingStep.output_productのみで絞る（スポットラインと同方式）
            products = (
                Product.objects.filter(
                    is_active=True,
                    id__in=routing_product_ids,
                )
                .order_by('product_code')
                .values('id', 'product_code', 'product_name')
            )
        else:
            # 工程未指定: 全ブレーキ品を返す
            products = (
                Product.objects.filter(
                    Q(product_code__endswith='B') | Q(product_code__in=override_codes),
                    is_active=True,
                )
                .order_by('product_code')
                .values('id', 'product_code', 'product_name')
            )

        return Response(list(products))


class BrakeLineEquipmentsView(APIView):
    """
    ブレーキライン設備一覧
    GET /api/production/brake-line-equipments/?process_id=X
    ブレーキライン（target_line_codes）かつ指定工程に紐づく有効設備を返す
    """

    def get(self, request):
        try:
            setting = ProductionRecordInquirySetting.objects.get(
                tab_key=ProductionRecordInquirySetting.TAB_BRAKE
            )
        except ProductionRecordInquirySetting.DoesNotExist:
            return Response([], status=200)

        target_line_codes = setting.target_line_codes or []
        process_id = request.query_params.get('process_id')

        lines = Line.objects.filter(line_code__in=target_line_codes, is_active=True)

        # ブレーキラインに紐づく設備を返す（工程フィルターは使わない）
        # 設備は工程に関係なく全台使用可能なため
        qs = Equipment.objects.filter(line__in=lines, is_active=True)
        equipments = list(
            qs.order_by('display_order', 'equipment_code')
            .values('id', 'equipment_code', 'equipment_name')
        )

        # line FK が未設定の場合はフォールバック: 全有効設備を返す
        if not equipments:
            equipments = list(
                Equipment.objects.filter(is_active=True)
                .order_by('display_order', 'equipment_code')
                .values('id', 'equipment_code', 'equipment_name')
            )

        return Response(equipments)


class BrakeLineActualAddView(APIView):
    """
    ブレーキライン実績 累積加算
    POST /api/production/brake-line-actual/add/

    payload: {
        line_id, process_id, product_id, plan_date, qty,
        sequence_no (互換用。実績保存先には使用しない)
    }
    LineBacklog(sequence_no=0).actual_qty を原子的に加算する。
    レコードが存在しない場合は新規作成。
    """

    @transaction.atomic
    def post(self, request):
        line_id = request.data.get('line_id')
        process_id = request.data.get('process_id')
        product_id = request.data.get('product_id')
        plan_date_str = request.data.get('plan_date')
        qty_raw = request.data.get('qty', 0)
        # バリデーション
        if not all([line_id, process_id, product_id, plan_date_str]):
            return Response(
                {'detail': 'line_id / process_id / product_id / plan_date は必須です'},
                status=400,
            )
        try:
            qty = int(qty_raw)
        except (ValueError, TypeError):
            return Response({'detail': 'qty は整数で入力してください'}, status=400)
        if qty <= 0:
            return Response({'detail': 'qty は1以上で入力してください'}, status=400)
        try:
            plan_date = date.fromisoformat(plan_date_str)
        except ValueError:
            return Response({'detail': '日付形式が不正です（YYYY-MM-DD）'}, status=400)

        # 実績は sequence_no=0 の基礎行に加算
        obj, created = LineBacklog.objects.get_or_create(
            plan_date=plan_date,
            process_id=process_id,
            product_id=product_id,
            line_id=line_id,
            sequence_no=0,
            defaults={'actual_qty': qty},
        )
        if not created:
            LineBacklog.objects.filter(pk=obj.pk).update(
                actual_qty=F('actual_qty') + qty
            )
            obj.refresh_from_db()

        response_data = {
            'id': obj.id,
            'plan_date': str(obj.plan_date),
            'actual_qty': int(obj.actual_qty),
            'plan_qty': int(obj.plan_qty),
            'created': created,
        }

        # 計画超過チェック
        try:
            process_obj = Process.objects.get(pk=process_id)
            product_obj = Product.objects.get(pk=product_id)
            overrun = check_plan_overrun(process_obj, product_obj, plan_date)
            if overrun:
                response_data['plan_overrun_warning'] = overrun
        except (Process.DoesNotExist, Product.DoesNotExist):
            pass

        return Response(response_data)


class BrakeLineRecordView(APIView):
    """
    ブレーキライン作業記録（状態管理）
    GET  /api/production/brake-line-record/?plan_date=YYYY-MM-DD&process_id=X
         → {item_key: last_operator_action} を返す
    POST /api/production/brake-line-record/
         → 作業記録を保存。operator_action=END の場合は LineBacklog も加算。
    """

    def get(self, request):
        plan_date_str = request.query_params.get('plan_date')
        process_id    = request.query_params.get('process_id')

        if not plan_date_str:
            return Response({'detail': 'plan_date は必須です'}, status=400)
        try:
            plan_date = date.fromisoformat(plan_date_str)
        except ValueError:
            return Response({'detail': '日付形式が不正です（YYYY-MM-DD）'}, status=400)

        qs = BrakeLineRecord.objects.filter(plan_date=plan_date).select_related('equipment')
        if process_id:
            qs = qs.filter(process_id=process_id)

        # 各 (process_id, product_id / product_code, equipment) の最新アクション
        item_state_map = {}
        item_operator_map = {}  # item_key -> START/RESUME した作業者名
        latest_by_equipment = {}
        for rec in qs.order_by('-recorded_at'):
            product_key = rec.product_id or rec.product_code
            if product_key:
                equipment_key = f"id:{rec.equipment_id}" if rec.equipment_id else 'none'
                item_key = f"{rec.process_id}-{product_key}-{equipment_key}"
                if item_key not in item_state_map:
                    item_state_map[item_key] = rec.operator_action
                    # 加工中（START/RESUME）の場合は開始者を記録
                    if rec.operator_action in {
                        BrakeLineRecord.OPERATOR_ACTION_START,
                        BrakeLineRecord.OPERATOR_ACTION_RESUME,
                    }:
                        item_operator_map[item_key] = rec.operator

            if rec.equipment_id:
                equipment_key = f"id:{rec.equipment_id}"
                if equipment_key not in latest_by_equipment:
                    latest_by_equipment[equipment_key] = rec

        # 前日以前に中断（PAUSE/TEMP_END）したまま未解決のレコードを carryover として追加
        PAUSED_ACTIONS = {BrakeLineRecord.OPERATOR_ACTION_PAUSE, BrakeLineRecord.OPERATOR_ACTION_TEMP_END}
        carryover_qs = BrakeLineRecord.objects.filter(
            plan_date__lt=plan_date
        ).select_related('equipment')
        if process_id:
            carryover_qs = carryover_qs.filter(process_id=process_id)

        seen_carryover = set()
        for rec in carryover_qs.order_by('-recorded_at'):
            product_key = rec.product_id or rec.product_code
            if not product_key:
                continue
            equipment_key = f"id:{rec.equipment_id}" if rec.equipment_id else 'none'
            item_key = f"{rec.process_id}-{product_key}-{equipment_key}"
            if item_key in seen_carryover:
                continue
            seen_carryover.add(item_key)
            # 既に今日の記録で状態が確定している場合はスキップ
            if item_key in item_state_map:
                continue
            # 最新アクションが PAUSE/TEMP_END の場合のみ carryover 追加
            if rec.operator_action in PAUSED_ACTIONS:
                item_state_map[item_key] = rec.operator_action
                if rec.equipment_id and equipment_key not in latest_by_equipment:
                    latest_by_equipment[equipment_key] = rec

        # 設備ごとの加工中状態は plan_date に関係なく全期間の最新レコードで判定
        processing_by_equipment = {}
        global_equipment_qs = BrakeLineRecord.objects.select_related('equipment')
        if process_id:
            global_equipment_qs = global_equipment_qs.filter(process_id=process_id)
        global_latest_by_equipment = {}
        for rec in global_equipment_qs.order_by('-recorded_at', '-id'):
            if rec.equipment_id:
                equipment_key = f"id:{rec.equipment_id}"
                if equipment_key not in global_latest_by_equipment:
                    global_latest_by_equipment[equipment_key] = rec
        for equipment_key, rec in global_latest_by_equipment.items():
            if rec.operator_action not in {
                BrakeLineRecord.OPERATOR_ACTION_START,
                BrakeLineRecord.OPERATOR_ACTION_RESUME,
            }:
                continue
            processing_by_equipment[equipment_key] = {
                'equipment_id': rec.equipment_id,
                'equipment_code': rec.equipment.equipment_code if rec.equipment else '',
                'equipment_name': rec.equipment.equipment_name if rec.equipment else '',
                'product_code': rec.product_code or '',
                'process_id': rec.process_id,
            }

        return Response({
            'item_states': item_state_map,
            'item_operators': item_operator_map,
            'processing_by_equipment': processing_by_equipment,
        })

    @transaction.atomic
    def post(self, request):
        line_id        = request.data.get('line_id')
        process_id     = request.data.get('process_id')
        product_id     = request.data.get('product_id')
        product_code   = request.data.get('product_code', '')
        equipment_id   = request.data.get('equipment_id')
        plan_date_str  = request.data.get('plan_date')
        operator       = request.data.get('operator', '')
        operator_action        = str(request.data.get('operator_action', '')).upper()
        operator_action_reason = request.data.get('operator_action_reason', '')
        qty_raw        = request.data.get('qty', 0)
        record_sequence_no = int(request.data.get('sequence_no', 1))

        # バリデーション
        if not all([line_id, process_id, plan_date_str, operator_action]):
            return Response(
                {'detail': 'line_id / process_id / plan_date / operator_action は必須です'},
                status=400,
            )
        valid_actions = {c[0] for c in BrakeLineRecord.OPERATOR_ACTION_CHOICES}
        if operator_action not in valid_actions:
            return Response({'detail': f'operator_action が不正です: {operator_action}'}, status=400)
        try:
            plan_date = date.fromisoformat(plan_date_str)
        except ValueError:
            return Response({'detail': '日付形式が不正です（YYYY-MM-DD）'}, status=400)

        if operator_action == BrakeLineRecord.OPERATOR_ACTION_START:
            conflict = find_equipment_active_product_conflict(
                equipment_id=equipment_id,
                product_id=product_id or None,
                product_code=product_code,
            )
            if conflict:
                equipment_label = (
                    (conflict.equipment.equipment_name if conflict.equipment else '')
                    or (conflict.equipment.equipment_code if conflict.equipment else '')
                    or 'この設備'
                )
                conflict_product_code = str(conflict.product_code or '').strip() or '前の品番'
                conflict_date = str(conflict.plan_date or '')
                return Response(
                    {
                        'detail_code': 'production.error.equipmentBusyWithProduct',
                        'detail_params': {
                            'equipment': equipment_label,
                            'product': conflict_product_code,
                            'date': conflict_date,
                        },
                        'detail': (
                            f'{equipment_label} は {conflict_product_code}（{conflict_date}）が未終了です。'
                            '先に終了してください。'
                        )
                    },
                    status=400,
                )

        qty = 0
        if operator_action in {
            BrakeLineRecord.OPERATOR_ACTION_END,
            BrakeLineRecord.OPERATOR_ACTION_PAUSE,
        }:
            try:
                qty = int(qty_raw)
            except (ValueError, TypeError):
                return Response({'detail': 'qty は整数で入力してください'}, status=400)
            if operator_action == BrakeLineRecord.OPERATOR_ACTION_END and qty <= 0:
                return Response({'detail': 'qty は1以上で入力してください'}, status=400)
            if operator_action == BrakeLineRecord.OPERATOR_ACTION_PAUSE and qty < 0:
                return Response({'detail': 'qty は0以上で入力してください'}, status=400)

        # 作業記録を保存
        rec = BrakeLineRecord.objects.create(
            plan_date=plan_date,
            line_id=line_id,
            process_id=process_id,
            product_id=product_id or None,
            product_code=product_code,
            equipment_id=equipment_id or None,
            operator=operator,
            operator_user=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
            operator_action=operator_action,
            operator_action_reason=operator_action_reason,
            qty=qty,
            sequence_no=record_sequence_no,
        )

        # END / PAUSE の場合は LineBacklog(sequence_no=0) に実績を加算
        backlog_data = None
        if operator_action in {
            BrakeLineRecord.OPERATOR_ACTION_END,
            BrakeLineRecord.OPERATOR_ACTION_PAUSE,
        } and qty > 0 and product_id:
            obj, created = LineBacklog.objects.get_or_create(
                plan_date=plan_date,
                process_id=process_id,
                product_id=product_id,
                line_id=line_id,
                sequence_no=0,
                defaults={'actual_qty': qty},
            )
            if not created:
                LineBacklog.objects.filter(pk=obj.pk).update(
                    actual_qty=F('actual_qty') + qty
                )
                obj.refresh_from_db()
            backlog_data = {
                'backlog_id':  obj.id,
                'actual_qty':  int(obj.actual_qty),
                'plan_qty':    int(obj.plan_qty),
            }

        # 計画超過チェック
        plan_overrun_warning = None
        if backlog_data and product_id:
            try:
                process_obj = Process.objects.get(pk=process_id)
                product_obj = Product.objects.get(pk=product_id)
                plan_overrun_warning = check_plan_overrun(process_obj, product_obj, plan_date)
            except (Process.DoesNotExist, Product.DoesNotExist):
                pass

        response_data = {
            'id':              rec.id,
            'operator':        rec.operator,
            'operator_action': rec.operator_action,
            'equipment':       rec.equipment_id,
            'equipment_code':  rec.equipment.equipment_code if rec.equipment else '',
            'equipment_name':  rec.equipment.equipment_name if rec.equipment else '',
            'product_code':    rec.product_code or '',
            'qty':             rec.qty,
            'recorded_at':     rec.recorded_at.isoformat(),
            'backlog':         backlog_data,
        }
        if plan_overrun_warning:
            response_data['plan_overrun_warning'] = plan_overrun_warning

        return Response(response_data, status=201)


class BrakeLineSessionView(APIView):
    """
    ブレーキライン作業記録をセッション形式で返す（生産実績照会用）
    GET /brake-line-sessions/
    Params: start_date, end_date, line_id, process_id, product_code
    operator_action（START/RESUME → END/PAUSE/TEMP_END）の対でセッションを構築する。
    """

    def get(self, request):
        qs = BrakeLineRecord.objects.select_related('process', 'product', 'line', 'equipment')

        start_date_str        = request.query_params.get('start_date', '').strip()
        end_date_str          = request.query_params.get('end_date', '').strip()
        recorded_at_start_str = request.query_params.get('recorded_at_start', '').strip()
        recorded_at_end_str   = request.query_params.get('recorded_at_end', '').strip()
        line_id        = request.query_params.get('line_id', '').strip()
        process_id     = request.query_params.get('process_id', '').strip()
        product_code_f = request.query_params.get('product_code', '').strip()

        if start_date_str:
            try:
                qs = qs.filter(plan_date__gte=date.fromisoformat(start_date_str))
            except ValueError:
                pass
        if end_date_str:
            try:
                qs = qs.filter(plan_date__lte=date.fromisoformat(end_date_str))
            except ValueError:
                pass
        # 実施日（recorded_at）での絞り込み（日替わり時刻8:00を考慮）
        # 例: end=3/23 → recorded_at < 3/24 08:00（3/24 06:08は3/23扱い）
        if recorded_at_start_str:
            try:
                d = date.fromisoformat(recorded_at_start_str)
                boundary = datetime.combine(d, time(DAY_BOUNDARY_HOUR, 0))
                if settings.USE_TZ:
                    boundary = timezone.make_aware(boundary, timezone.get_current_timezone())
                qs = qs.filter(recorded_at__gte=boundary)
            except ValueError:
                pass
        if recorded_at_end_str:
            try:
                d = date.fromisoformat(recorded_at_end_str)
                boundary = datetime.combine(d + timedelta(days=1), time(DAY_BOUNDARY_HOUR, 0))
                if settings.USE_TZ:
                    boundary = timezone.make_aware(boundary, timezone.get_current_timezone())
                qs = qs.filter(recorded_at__lt=boundary)
            except ValueError:
                pass
        if line_id:
            qs = qs.filter(line_id=line_id)
        if process_id:
            qs = qs.filter(process_id=process_id)
        if product_code_f:
            qs = qs.filter(
                Q(product_code__icontains=product_code_f) |
                Q(product__product_code__icontains=product_code_f)
            )

        records = list(qs.order_by('line_id', 'process_id', 'product_id', 'equipment_id', 'recorded_at'))

        START_ACTIONS = {BrakeLineRecord.OPERATOR_ACTION_START, BrakeLineRecord.OPERATOR_ACTION_RESUME}
        END_ACTIONS   = {
            BrakeLineRecord.OPERATOR_ACTION_END,
            BrakeLineRecord.OPERATOR_ACTION_PAUSE,
            BrakeLineRecord.OPERATOR_ACTION_TEMP_END,
        }

        def group_key(r):
            return (r.line_id, r.process_id, r.product_id or r.product_code, r.equipment_id)

        sessions = []
        for _key, grp in groupby(records, key=group_key):
            group = list(grp)
            open_rec = None
            pause_rec = None  # 中断待機セッション用：直前のPAUSE/TEMP_ENDレコード
            for rec in group:
                action = rec.operator_action
                if action in START_ACTIONS:
                    # PAUSE→RESUME の待機セッションを生成
                    if action == BrakeLineRecord.OPERATOR_ACTION_RESUME and pause_rec is not None:
                        wait_started_at = pause_rec.recorded_at
                        wait_ended_at   = rec.recorded_at
                        wait_duration   = int((wait_ended_at - wait_started_at).total_seconds())
                        w_proc    = pause_rec.process
                        w_product = pause_rec.product
                        w_p_code  = (w_product.product_code if w_product else '') or pause_rec.product_code or ''
                        w_p_name  = (w_product.product_name if w_product else '') or ''
                        w_pr_code = (w_proc.process_code if w_proc else '') or ''
                        w_pr_name = (w_proc.process_name if w_proc else '') or ''
                        sessions.append({
                            'id':                   f'wait_{pause_rec.id}',
                            'start_record_id':      pause_rec.id,
                            'end_record_id':        rec.id,
                            'started_at':           wait_started_at.isoformat(),
                            'ended_at':             wait_ended_at.isoformat(),
                            'session_type':         'PAUSE',
                            'start_action':         'PAUSE',
                            'end_action':           'RESUME',
                            'pause_reason':         pause_rec.operator_action_reason or '',
                            'process_code':         w_pr_code,
                            'process_name':         w_pr_name,
                            'product_code':         w_p_code,
                            'product_name':         w_p_name,
                            'operator_name':        pause_rec.operator or '',
                            'duration_seconds':     wait_duration,
                            'effective_work_seconds': 0,
                            'production_qty':       0,
                            'issue_count':          0,
                            'issue_flags':          [],
                            'record_source':        'BRAKE',
                            'line_id':              pause_rec.line_id,
                            'plan_date':            str(pause_rec.plan_date),
                        })
                        pause_rec = None
                    open_rec = rec
                elif action in END_ACTIONS:
                    start_rec = open_rec
                    started_at = start_rec.recorded_at if start_rec else rec.recorded_at
                    ended_at   = rec.recorded_at
                    duration   = int((ended_at - started_at).total_seconds()) if start_rec else 0

                    proc    = (start_rec or rec).process
                    product = (start_rec or rec).product
                    p_code  = (product.product_code if product else '') or (start_rec.product_code if start_rec else '') or rec.product_code or ''
                    p_name  = (product.product_name if product else '') or ''
                    pr_code = (proc.process_code if proc else '') or ''
                    pr_name = (proc.process_name if proc else '') or ''

                    sessions.append({
                        'id':                   rec.id,
                        'start_record_id':      start_rec.id if start_rec else None,
                        'end_record_id':        rec.id,
                        'started_at':           started_at.isoformat(),
                        'ended_at':             ended_at.isoformat(),
                        'session_type':         'WORK',
                        'start_action':         start_rec.operator_action if start_rec else '',
                        'end_action':           action,
                        'pause_reason':         rec.operator_action_reason or '',
                        'process_code':         pr_code,
                        'process_name':         pr_name,
                        'product_code':         p_code,
                        'product_name':         p_name,
                        'operator_name':        (start_rec or rec).operator or '',
                        'duration_seconds':     duration,
                        'effective_work_seconds': duration,
                        'production_qty':       int(rec.qty) if action in {
                            BrakeLineRecord.OPERATOR_ACTION_END,
                            BrakeLineRecord.OPERATOR_ACTION_PAUSE,
                        } else 0,
                        'issue_count':          0,
                        'issue_flags':          [],
                        'record_source':        'BRAKE',
                        'line_id':              rec.line_id,
                        'plan_date':            str(rec.plan_date),
                    })
                    if action == BrakeLineRecord.OPERATOR_ACTION_END:
                        open_rec = None
                        pause_rec = None
                    elif action in {BrakeLineRecord.OPERATOR_ACTION_PAUSE, BrakeLineRecord.OPERATOR_ACTION_TEMP_END}:
                        pause_rec = rec
                        open_rec = None

            # 未終了・未復帰の中断待機セッション（PAUSE後まだRESUMEしていない）
            if pause_rec and not open_rec:
                now = timezone.now()
                w_proc    = pause_rec.process
                w_product = pause_rec.product
                sessions.append({
                    'id':                   f'wait_{pause_rec.id}',
                    'start_record_id':      pause_rec.id,
                    'end_record_id':        None,
                    'started_at':           pause_rec.recorded_at.isoformat(),
                    'ended_at':             None,
                    'session_type':         'PAUSE',
                    'start_action':         'PAUSE',
                    'end_action':           '',
                    'pause_reason':         pause_rec.operator_action_reason or '',
                    'process_code':         (w_proc.process_code if w_proc else '') or '',
                    'process_name':         (w_proc.process_name if w_proc else '') or '',
                    'product_code':         (w_product.product_code if w_product else '') or pause_rec.product_code or '',
                    'product_name':         (w_product.product_name if w_product else '') or '',
                    'operator_name':        pause_rec.operator or '',
                    'duration_seconds':     int((now - pause_rec.recorded_at).total_seconds()),
                    'effective_work_seconds': 0,
                    'production_qty':       0,
                    'issue_count':          0,
                    'issue_flags':          [],
                    'record_source':        'BRAKE',
                    'line_id':              pause_rec.line_id,
                    'plan_date':            str(pause_rec.plan_date),
                })

            # 未終了（加工中）セッション
            if open_rec:
                now     = timezone.now()
                proc    = open_rec.process
                product = open_rec.product
                p_code  = (product.product_code if product else '') or open_rec.product_code or ''
                p_name  = (product.product_name if product else '') or ''
                pr_code = (proc.process_code if proc else '') or ''
                pr_name = (proc.process_name if proc else '') or ''
                sessions.append({
                    'id':                   open_rec.id,
                    'start_record_id':      open_rec.id,
                    'end_record_id':        None,
                    'started_at':           open_rec.recorded_at.isoformat(),
                    'ended_at':             None,
                    'session_type':         'WORK',
                    'start_action':         open_rec.operator_action,
                    'end_action':           '',
                    'pause_reason':         '',
                    'process_code':         pr_code,
                    'process_name':         pr_name,
                    'product_code':         p_code,
                    'product_name':         p_name,
                    'operator_name':        open_rec.operator or '',
                    'duration_seconds':     int((now - open_rec.recorded_at).total_seconds()),
                    'effective_work_seconds': int((now - open_rec.recorded_at).total_seconds()),
                    'production_qty':       0,
                    'issue_count':          0,
                    'issue_flags':          [],
                    'record_source':        'BRAKE',
                    'line_id':              open_rec.line_id,
                    'plan_date':            str(open_rec.plan_date),
                })

        line_breaks_cache = {}
        for s in sessions:
            if s.get('session_type') != 'WORK':
                continue
            s_started = s.get('started_at')
            s_ended = s.get('ended_at')
            if not s_started or not s_ended:
                continue
            start_dt = datetime.fromisoformat(s_started)
            end_dt = datetime.fromisoformat(s_ended)
            raw_seconds = int((end_dt - start_dt).total_seconds())
            if raw_seconds <= 0:
                continue

            lid = s.get('line_id')
            if lid is not None and lid not in line_breaks_cache:
                line_breaks_cache[lid] = _get_line_break_config(lid)
            break_config = line_breaks_cache.get(lid)

            s['effective_work_seconds'] = _deduct_break_seconds(
                break_config, start_dt, end_dt, raw_seconds,
            )

        sessions.sort(key=lambda s: s.get('started_at') or '', reverse=True)
        return Response(sessions)


class BrakeLineSessionDetailView(APIView):
    """
    ブレーキラインセッション更新/削除
    PATCH  /brake-line-sessions/{session_id}/
    DELETE /brake-line-sessions/{session_id}/
    """

    START_ACTIONS = {BrakeLineRecord.OPERATOR_ACTION_START, BrakeLineRecord.OPERATOR_ACTION_RESUME}
    END_ACTIONS = {
        BrakeLineRecord.OPERATOR_ACTION_END,
        BrakeLineRecord.OPERATOR_ACTION_PAUSE,
        BrakeLineRecord.OPERATOR_ACTION_TEMP_END,
    }
    BACKLOG_COUNTABLE_ACTIONS = {
        BrakeLineRecord.OPERATOR_ACTION_END,
        BrakeLineRecord.OPERATOR_ACTION_PAUSE,
    }

    @staticmethod
    def _parse_dt(value):
        if value in (None, ''):
            return None
        try:
            dt = datetime.fromisoformat(str(value))
        except ValueError:
            return None
        # USE_TZ=False のため naive datetime で返す（settings.py に合わせる）
        if timezone.is_aware(dt):
            return timezone.localtime(dt).replace(tzinfo=None)
        return dt

    @classmethod
    def _find_prev_start_record(cls, end_record):
        if not end_record:
            return None
        qs = BrakeLineRecord.objects.filter(
            line_id=end_record.line_id,
            process_id=end_record.process_id,
            equipment_id=end_record.equipment_id,
            recorded_at__lte=end_record.recorded_at,
            operator_action__in=list(cls.START_ACTIONS),
        ).order_by('-recorded_at', '-id')
        if end_record.product_id:
            qs = qs.filter(product_id=end_record.product_id)
        else:
            qs = qs.filter(product_code=end_record.product_code)
        return qs.first()

    @staticmethod
    def _to_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _resolve_records(self, request, session_id):
        record = BrakeLineRecord.objects.filter(id=session_id).first()
        if not record:
            return None, None, None

        start_record_id = self._to_int(request.data.get('start_record_id'))
        end_record_id = self._to_int(request.data.get('end_record_id'))
        start_record = BrakeLineRecord.objects.filter(id=start_record_id).first() if start_record_id else None
        end_record = BrakeLineRecord.objects.filter(id=end_record_id).first() if end_record_id else None

        if start_record or end_record:
            return record, start_record, end_record

        # 後方互換: 旧クライアントはIDを送らないため推定ロジックを残す
        if record.operator_action in self.END_ACTIONS:
            return record, self._find_prev_start_record(record), record
        if record.operator_action in self.START_ACTIONS:
            return record, record, None
        return record, None, record

    @staticmethod
    def _apply_backlog_delta(record, delta_qty):
        if not record or int(delta_qty or 0) == 0:
            return
        if not record.product_id:
            return
        obj, _created = LineBacklog.objects.get_or_create(
            plan_date=record.plan_date,
            process_id=record.process_id,
            product_id=record.product_id,
            line_id=record.line_id,
            sequence_no=0,
            defaults={'actual_qty': 0},
        )
        LineBacklog.objects.filter(pk=obj.pk).update(actual_qty=F('actual_qty') + int(delta_qty))

    @transaction.atomic
    def patch(self, request, session_id):
        record, start_record, end_record = self._resolve_records(request, session_id)
        if not record:
            return Response({'detail': '対象セッションが存在しません。'}, status=404)

        old_qty = int(end_record.qty or 0) if end_record and end_record.operator_action in self.BACKLOG_COUNTABLE_ACTIONS else 0
        ref_rec = end_record or start_record or record
        before_snapshot = {
            'product_code': ref_rec.product_code or '',
            'started_at': (start_record.recorded_at.strftime('%Y/%m/%d %H:%M') if start_record and start_record.recorded_at else ''),
            'ended_at': (end_record.recorded_at.strftime('%Y/%m/%d %H:%M') if end_record and end_record.recorded_at else ''),
            'production_qty': old_qty,
            'operator_name': ref_rec.operator or '',
        }

        new_started_at = self._parse_dt(request.data.get('started_at'))
        new_ended_at = self._parse_dt(request.data.get('ended_at'))
        production_qty_raw = request.data.get('production_qty')

        new_product_code = request.data.get('product_code')
        new_product = None
        product_changed = False
        if new_product_code is not None:
            new_product_code = str(new_product_code).strip()
            if not new_product_code:
                return Response({'detail': '品番は必須です。'}, status=400)
            new_product = Product.objects.filter(product_code=new_product_code).first()
            if not new_product:
                return Response({'detail': f'品番 {new_product_code} が見つかりません。'}, status=400)
            ref_record = end_record or start_record or record
            if ref_record.product_id != new_product.id:
                product_changed = True

        if product_changed and old_qty:
            self._apply_backlog_delta(end_record, -old_qty)

        if product_changed:
            for rec in [r for r in (start_record, end_record) if r]:
                rec.product = new_product
                rec.product_code = new_product.product_code
                rec.save(update_fields=['product_id', 'product_code'])

        new_operator_name = request.data.get('operator_name')
        if new_operator_name is not None:
            new_operator_name = str(new_operator_name).strip()
            for rec in [r for r in (start_record, end_record) if r]:
                rec.operator = new_operator_name
                rec.save(update_fields=['operator'])

        if new_started_at and start_record:
            start_record.recorded_at = new_started_at
            start_record.save(update_fields=['recorded_at'])
        if new_ended_at and end_record:
            end_record.recorded_at = new_ended_at
            end_record.save(update_fields=['recorded_at'])

        if end_record and end_record.operator_action in self.BACKLOG_COUNTABLE_ACTIONS and production_qty_raw is not None:
            try:
                new_qty = int(production_qty_raw)
            except (TypeError, ValueError):
                return Response({'detail': 'production_qty は整数で入力してください。'}, status=400)
            if new_qty < 0:
                return Response({'detail': 'production_qty は0以上で入力してください。'}, status=400)
            end_record.qty = new_qty
            end_record.save(update_fields=['qty'])
            if product_changed:
                self._apply_backlog_delta(end_record, new_qty)
            else:
                self._apply_backlog_delta(end_record, new_qty - old_qty)
        elif product_changed and old_qty:
            self._apply_backlog_delta(end_record, old_qty)

        ref_rec_after = end_record or start_record or record
        final_qty = int(end_record.qty or 0) if end_record and end_record.operator_action in self.BACKLOG_COUNTABLE_ACTIONS else 0
        after_snapshot = {
            'product_code': ref_rec_after.product_code or '',
            'started_at': (start_record.recorded_at.strftime('%Y/%m/%d %H:%M') if start_record and start_record.recorded_at else ''),
            'ended_at': (end_record.recorded_at.strftime('%Y/%m/%d %H:%M') if end_record and end_record.recorded_at else ''),
            'production_qty': final_qty,
            'operator_name': ref_rec_after.operator or '',
        }
        if before_snapshot != after_snapshot:
            change_reason = str(request.data.get('change_reason') or '実績変更').strip()
            changed_by = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
            diff_parts = []
            labels = {'product_code': '品番', 'started_at': '開始時刻', 'ended_at': '終了時刻', 'production_qty': '実績数量', 'operator_name': '作業者'}
            for key, label in labels.items():
                bv, av = str(before_snapshot.get(key) or ''), str(after_snapshot.get(key) or '')
                if bv != av:
                    diff_parts.append(f"{label}: {bv or '—'} → {av or '—'}")
            ProcessWorkSessionChangeHistory.objects.create(
                session=None,
                session_record_id=record.id,
                operation_type='UPDATE',
                process_id=ref_rec_after.process_id,
                product_id=ref_rec_after.product_id,
                product_code=ref_rec_after.product_code or '',
                product_name='',
                plan_date=ref_rec_after.plan_date,
                reason=change_reason,
                change_summary=' / '.join(diff_parts) or '変更なし',
                before_data=before_snapshot,
                after_data=after_snapshot,
                changed_by=changed_by,
            )

        return Response({'detail': '更新しました。'})

    @transaction.atomic
    def delete(self, request, session_id):
        record, start_record, end_record = self._resolve_records(request, session_id)
        if not record:
            return Response(status=204)

        if end_record and end_record.operator_action in self.END_ACTIONS:
            rollback_qty = int(end_record.qty or 0) if end_record.operator_action in self.BACKLOG_COUNTABLE_ACTIONS else 0
            if rollback_qty:
                self._apply_backlog_delta(end_record, -rollback_qty)
            end_record.delete()
            if start_record:
                start_record.delete()
            return Response(status=204)

        if start_record and start_record.operator_action in self.START_ACTIONS:
            if start_record.id == record.id:
                record.delete()
            else:
                start_record.delete()
            return Response(status=204)

        rollback_qty = int(record.qty or 0) if record.operator_action in self.BACKLOG_COUNTABLE_ACTIONS else 0
        if rollback_qty:
            self._apply_backlog_delta(record, -rollback_qty)
        record.delete()
        return Response(status=204)
