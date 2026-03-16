"""
ブレーキライン専用ビュー
- BrakeLinePlanView: 自動計画取得（昨日のレーザ実績 → 今日の計画）
- BrakeLineActualAddView: 実績累積加算（後方互換用）
- BrakeLineRecordView: 作業記録（開始/終了/中断/再開/一時終了）
"""
from datetime import date
from decimal import Decimal
from itertools import groupby

from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from masters.models import Calendar, Equipment, Line, Process, Product, RoutingStep
from orders.utils.calendar_utils import get_business_today, WorkingDayCalculator
from production.models_brake_line_record import BrakeLineRecord
from production.models_laser_actual import LaserActualDetail
from production.models_line_backlog import LineBacklog
from production.models_record_inquiry_setting import ProductionRecordInquirySetting


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

        # 昨日のレーザ実績（FINISHED）を品番ごとに集計
        laser_qs = (
            LaserActualDetail.objects
            .filter(
                actual__work_date=laser_date,
                detail_type=LaserActualDetail.DETAIL_TYPE_FINISHED,
            )
            .values('product_code', 'product_name', 'product_id')
            .annotate(laser_qty=Sum(F('total_qty') - F('scrap_qty')))
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
            laser_code = row['product_code']
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

        # 今日のLineBacklogを取得（実績参照用）
        backlogs_qs = LineBacklog.objects.filter(
            plan_date=plan_date,
            line_id__in=line_ids,
        ).select_related('product', 'process', 'line')

        # (line_id, process_id, product_id) → backlog
        # 同じキーが複数ある場合は sequence_no=0（実績行）を優先
        backlog_map: dict[tuple, LineBacklog] = {}
        for lb in backlogs_qs:
            key = (lb.line_id, lb.process_id, lb.product_id)
            existing = backlog_map.get(key)
            if existing is None or lb.sequence_no < existing.sequence_no:
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
                    lb = backlog_map.get((line_id, process_id, product_id))
                    key = (line_id, process_id, product_id or f'code:{brake_code}')
                    if key in item_keys:
                        continue
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
                        'plan_qty': int(lb.plan_qty) if lb else int(laser_qty),
                        'actual_qty': int(lb.actual_qty) if lb else 0,
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
                'actual_qty': int(lb.actual_qty) if lb else 0,
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
                'actual_qty': int(lb.actual_qty) if lb else 0,
                'backlog_id': lb.id if lb else None,
                'sequence_no': lb.sequence_no if lb else (rec.sequence_no or 1),
                'equipment_id': rec.equipment_id,
                'is_manual': True,
                'is_carryover': True,
                'carryover_plan_date': str(rec.plan_date),
            })
            item_keys.add(key)

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

            products = (
                Product.objects.filter(
                    Q(product_code__endswith='B') | Q(product_code__in=override_codes),
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
        sequence_no (default: 1)
    }
    LineBacklog.actual_qty を原子的に加算する。
    レコードが存在しない場合は新規作成。
    """

    @transaction.atomic
    def post(self, request):
        line_id = request.data.get('line_id')
        process_id = request.data.get('process_id')
        product_id = request.data.get('product_id')
        plan_date_str = request.data.get('plan_date')
        qty_raw = request.data.get('qty', 0)
        sequence_no = int(request.data.get('sequence_no', 1))

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

        # LineBacklog を get_or_create してから原子的に加算
        obj, created = LineBacklog.objects.get_or_create(
            plan_date=plan_date,
            process_id=process_id,
            product_id=product_id,
            line_id=line_id,
            sequence_no=sequence_no,
            defaults={'actual_qty': qty},
        )
        if not created:
            LineBacklog.objects.filter(pk=obj.pk).update(
                actual_qty=F('actual_qty') + qty
            )
            obj.refresh_from_db()

        return Response({
            'id': obj.id,
            'plan_date': str(obj.plan_date),
            'actual_qty': int(obj.actual_qty),
            'plan_qty': int(obj.plan_qty),
            'created': created,
        })


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

        processing_by_equipment = {}
        for equipment_key, rec in latest_by_equipment.items():
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
        sequence_no    = int(request.data.get('sequence_no', 1))

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

        qty = 0
        if operator_action == BrakeLineRecord.OPERATOR_ACTION_END:
            try:
                qty = int(qty_raw)
            except (ValueError, TypeError):
                return Response({'detail': 'qty は整数で入力してください'}, status=400)
            if qty <= 0:
                return Response({'detail': 'qty は1以上で入力してください'}, status=400)

        # 作業記録を保存
        rec = BrakeLineRecord.objects.create(
            plan_date=plan_date,
            line_id=line_id,
            process_id=process_id,
            product_id=product_id or None,
            product_code=product_code,
            equipment_id=equipment_id or None,
            operator=operator,
            operator_action=operator_action,
            operator_action_reason=operator_action_reason,
            qty=qty,
            sequence_no=sequence_no,
        )

        # END の場合は LineBacklog に実績を加算
        backlog_data = None
        if operator_action == BrakeLineRecord.OPERATOR_ACTION_END and qty > 0 and product_id:
            obj, created = LineBacklog.objects.get_or_create(
                plan_date=plan_date,
                process_id=process_id,
                product_id=product_id,
                line_id=line_id,
                sequence_no=sequence_no,
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

        return Response({
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
        }, status=201)


class BrakeLineSessionView(APIView):
    """
    ブレーキライン作業記録をセッション形式で返す（生産実績照会用）
    GET /brake-line-sessions/
    Params: start_date, end_date, line_id, process_id, product_code
    operator_action（START/RESUME → END/PAUSE/TEMP_END）の対でセッションを構築する。
    """

    def get(self, request):
        qs = BrakeLineRecord.objects.select_related('process', 'product', 'line', 'equipment')

        start_date_str = request.query_params.get('start_date', '').strip()
        end_date_str   = request.query_params.get('end_date', '').strip()
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
            for rec in group:
                action = rec.operator_action
                if action in START_ACTIONS:
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
                        'id':                   (start_rec or rec).id,
                        'started_at':           started_at.isoformat(),
                        'ended_at':             ended_at.isoformat(),
                        'session_type':         'WORK' if action == BrakeLineRecord.OPERATOR_ACTION_END else 'PAUSE',
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
                        'production_qty':       int(rec.qty) if action == BrakeLineRecord.OPERATOR_ACTION_END else 0,
                        'issue_count':          0,
                        'issue_flags':          [],
                        'record_source':        'BRAKE',
                        'line_id':              rec.line_id,
                        'plan_date':            str(rec.plan_date),
                    })
                    if action == BrakeLineRecord.OPERATOR_ACTION_END:
                        open_rec = None

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

        sessions.sort(key=lambda s: s.get('started_at') or '', reverse=True)
        return Response(sessions)
