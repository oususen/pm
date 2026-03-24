"""
スポットライン（ナットスポット工程）専用ビュー
- SpotLinePlanView:      計画取得（LineBacklog から当日計画）
- SpotLineEquipmentsView: 設備一覧
- SpotLineProductsView:  加工品一覧（追加用）
- SpotLineRecordView:    作業記録（開始/終了/中断/再開）
BrakeLineRecord モデルを流用（line FK で区別）。
"""
from datetime import date

from django.db import models, transaction
from django.db.models import F
from rest_framework.response import Response
from rest_framework.views import APIView

from masters.models import Equipment, Line, Process, Product, RoutingStep
from orders.utils.calendar_utils import get_business_today
from production.models_brake_line_record import BrakeLineRecord
from production.models_line_backlog import LineBacklog
from production.models_record_inquiry_setting import ProductionRecordInquirySetting


def _get_spot_setting():
    return ProductionRecordInquirySetting.objects.filter(
        tab_key=ProductionRecordInquirySetting.TAB_SPOT
    ).first()


def _get_spot_line_ids(setting):
    if not setting:
        return []
    target_line_codes = setting.target_line_codes or []
    return list(
        Line.objects.filter(line_code__in=target_line_codes, is_active=True)
        .values_list('id', flat=True)
    )


class SpotLinePlanView(APIView):
    """
    スポットライン計画取得
    GET /api/production/spot-line-plan/?date=YYYY-MM-DD

    LineBacklog から L0013 + 対象工程の当日計画を返す。
    """

    def get(self, request):
        plan_date_str = request.query_params.get('date')
        if plan_date_str:
            try:
                plan_date = date.fromisoformat(plan_date_str)
            except ValueError:
                return Response({'detail': '日付形式が不正です（YYYY-MM-DD）'}, status=400)
        else:
            plan_date = get_business_today()

        setting = _get_spot_setting()
        if not setting:
            return Response({'detail': 'スポットライン設定が存在しません。管理者に連絡してください。'}, status=404)

        target_line_codes = setting.target_line_codes or []
        lines = list(
            Line.objects.filter(line_code__in=target_line_codes, is_active=True)
            .values('id', 'line_code', 'line_name')
        )
        if not lines:
            return Response({
                'plan_date': str(plan_date),
                'lines': [],
                'processes': [],
                'items': [],
            })

        line_ids = [ln['id'] for ln in lines]

        # 対象ラインに紐づく工程を取得
        processes = list(
            Process.objects.filter(line_id__in=line_ids, is_active=True)
            .values('id', 'process_code', 'process_name')
            .order_by('process_code')
        )
        process_ids = [p['id'] for p in processes]

        line_map = {ln['id']: ln for ln in lines}
        process_map = {p['id']: p for p in processes}

        # LineBacklog から計画を取得（sequence_no > 0 のみ）
        backlogs_qs = (
            LineBacklog.objects
            .filter(
                plan_date=plan_date,
                line_id__in=line_ids,
                sequence_no__gt=0,
            )
            .select_related('product', 'process')
        )
        if process_ids:
            backlogs_qs = backlogs_qs.filter(process_id__in=process_ids)

        # 実績は seq_no=0 行に保存されるため、対象品番の seq_no=0 行を先に取得してマップ化
        actual_map = {
            (a.line_id, a.process_id, a.product_id): int(a.actual_qty or 0)
            for a in LineBacklog.objects.filter(
                plan_date=plan_date,
                line_id__in=line_ids,
                sequence_no=0,
            )
        }

        items = []
        seen_keys = set()

        for lb in backlogs_qs.order_by('sequence_no', 'product__product_code'):
            if not lb.product_id:
                continue
            plan_qty = int(lb.plan_qty or 0)
            if plan_qty <= 0:
                continue
            line_data = line_map.get(lb.line_id)
            process_data = process_map.get(lb.process_id)
            if not line_data or not process_data:
                continue
            key = (lb.line_id, lb.process_id, lb.product_id, lb.sequence_no)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            actual_qty = actual_map.get((lb.line_id, lb.process_id, lb.product_id), 0)
            items.append({
                'product_id':   lb.product_id,
                'product_code': lb.product.product_code,
                'product_name': lb.product.product_name,
                'line_id':      lb.line_id,
                'line_code':    line_data['line_code'],
                'line_name':    line_data['line_name'],
                'process_id':   lb.process_id,
                'process_code': process_data['process_code'],
                'process_name': process_data['process_name'],
                'plan_qty':     plan_qty,
                'actual_qty':   actual_qty,
                'backlog_id':   lb.id,
                'sequence_no':  lb.sequence_no,
                'equipment_id': None,
                'is_manual':    False,
            })

        # 手動追加分（BrakeLineRecord で保存済みで LineBacklog にない品番）
        manual_qs = (
            BrakeLineRecord.objects
            .filter(plan_date=plan_date, line_id__in=line_ids)
            .select_related('product')
            .order_by('-recorded_at')
        )
        if process_ids:
            manual_qs = manual_qs.filter(process_id__in=process_ids)

        existing_keys = {(it['line_id'], it['process_id'], it['product_id']) for it in items}
        seen_manual: set = set()

        for rec in manual_qs:
            if not rec.product_id:
                continue
            key3 = (rec.line_id, rec.process_id, rec.product_id)
            if key3 in existing_keys or key3 in seen_manual:
                continue
            seen_manual.add(key3)

            line_data = line_map.get(rec.line_id)
            process_data = process_map.get(rec.process_id)
            if not line_data or not process_data:
                continue

            lb = (
                LineBacklog.objects
                .filter(
                    plan_date=plan_date,
                    line_id=rec.line_id,
                    process_id=rec.process_id,
                    product_id=rec.product_id,
                    sequence_no__gt=0,
                )
                .first()
            )
            product_code = rec.product.product_code if rec.product else rec.product_code or ''
            product_name = rec.product.product_name if rec.product else ''

            items.append({
                'product_id':   rec.product_id,
                'product_code': product_code,
                'product_name': product_name,
                'line_id':      rec.line_id,
                'line_code':    line_data['line_code'],
                'line_name':    line_data['line_name'],
                'process_id':   rec.process_id,
                'process_code': process_data['process_code'],
                'process_name': process_data['process_name'],
                'plan_qty':     int(lb.plan_qty) if lb else 0,
                'actual_qty':   actual_map.get((rec.line_id, rec.process_id, rec.product_id), 0),
                'backlog_id':   lb.id if lb else None,
                'sequence_no':  lb.sequence_no if lb else 1,
                'equipment_id': None,
                'is_manual':    True,
            })

        return Response({
            'plan_date': str(plan_date),
            'lines':     lines,
            'processes': processes,
            'items':     items,
        })


class SpotLineEquipmentsView(APIView):
    """
    スポットライン設備一覧
    GET /api/production/spot-line-equipments/
    """

    def get(self, request):
        setting = _get_spot_setting()
        if not setting:
            return Response([], status=200)

        target_line_codes = setting.target_line_codes or []
        lines = Line.objects.filter(line_code__in=target_line_codes, is_active=True)

        qs = Equipment.objects.filter(line__in=lines, is_active=True)
        equipments = list(
            qs.order_by('display_order', 'equipment_code')
            .values('id', 'equipment_code', 'equipment_name')
        )
        if not equipments:
            equipments = list(
                Equipment.objects.filter(is_active=True)
                .order_by('display_order', 'equipment_code')
                .values('id', 'equipment_code', 'equipment_name')
            )
        return Response(equipments)


class SpotLineProductsView(APIView):
    """
    スポットライン加工品一覧（手動追加用）
    GET /api/production/spot-line-products/?process_id=X&date=YYYY-MM-DD
    """

    def get(self, request):
        process_id = request.query_params.get('process_id')
        search = request.query_params.get('search', '').strip()

        if not process_id:
            return Response([], status=200)

        # 指定工程の output_product に設定されている品番をルーティングから取得（有効品番のみ）
        product_ids = (
            RoutingStep.objects
            .filter(process_id=process_id, output_product__isnull=False)
            .values_list('output_product_id', flat=True)
            .distinct()
        )

        qs = Product.objects.filter(id__in=product_ids, is_active=True).order_by('product_code')

        if search:
            qs = qs.filter(
                models.Q(product_code__icontains=search) |
                models.Q(product_name__icontains=search)
            )

        products = [
            {
                'id':           p.id,
                'product_code': p.product_code,
                'product_name': p.product_name,
            }
            for p in qs
        ]
        return Response(products)


class SpotLineRecordView(APIView):
    """
    スポットライン作業記録
    GET  /api/production/spot-line-record/?plan_date=YYYY-MM-DD&process_id=X
    POST /api/production/spot-line-record/
         operator_action=END の場合は LineBacklog.actual_qty も加算。
    """

    def get(self, request):
        plan_date_str = request.query_params.get('plan_date')
        process_id = request.query_params.get('process_id')

        if not plan_date_str:
            return Response({'detail': 'plan_date は必須です'}, status=400)
        try:
            plan_date = date.fromisoformat(plan_date_str)
        except ValueError:
            return Response({'detail': '日付形式が不正です（YYYY-MM-DD）'}, status=400)

        setting = _get_spot_setting()
        line_ids = _get_spot_line_ids(setting)

        qs = (
            BrakeLineRecord.objects
            .filter(plan_date=plan_date, line_id__in=line_ids)
            .select_related('equipment')
        )
        if process_id:
            qs = qs.filter(process_id=process_id)

        item_state_map = {}
        item_operator_map = {}
        latest_by_equipment = {}

        for rec in qs.order_by('-recorded_at'):
            product_key = rec.product_id or rec.product_code
            if product_key:
                equipment_key = f"id:{rec.equipment_id}" if rec.equipment_id else 'none'
                item_key = f"{rec.process_id}-{product_key}-{equipment_key}"
                if item_key not in item_state_map:
                    item_state_map[item_key] = rec.operator_action
                    if rec.operator_action in {
                        BrakeLineRecord.OPERATOR_ACTION_START,
                        BrakeLineRecord.OPERATOR_ACTION_RESUME,
                    }:
                        item_operator_map[item_key] = rec.operator
            if rec.equipment_id:
                eq_key = f"id:{rec.equipment_id}"
                if eq_key not in latest_by_equipment:
                    latest_by_equipment[eq_key] = rec

        # 前日以前の中断を carryover
        PAUSED = {BrakeLineRecord.OPERATOR_ACTION_PAUSE, BrakeLineRecord.OPERATOR_ACTION_TEMP_END}
        carryover_qs = (
            BrakeLineRecord.objects
            .filter(plan_date__lt=plan_date, line_id__in=line_ids)
            .select_related('equipment')
        )
        if process_id:
            carryover_qs = carryover_qs.filter(process_id=process_id)

        seen_carryover: set = set()
        for rec in carryover_qs.order_by('-recorded_at'):
            product_key = rec.product_id or rec.product_code
            if not product_key:
                continue
            equipment_key = f"id:{rec.equipment_id}" if rec.equipment_id else 'none'
            item_key = f"{rec.process_id}-{product_key}-{equipment_key}"
            if item_key in seen_carryover or item_key in item_state_map:
                continue
            seen_carryover.add(item_key)
            if rec.operator_action in PAUSED:
                item_state_map[item_key] = rec.operator_action

        processing_by_equipment = {}
        for eq_key, rec in latest_by_equipment.items():
            if rec.operator_action not in {
                BrakeLineRecord.OPERATOR_ACTION_START,
                BrakeLineRecord.OPERATOR_ACTION_RESUME,
            }:
                continue
            processing_by_equipment[eq_key] = {
                'equipment_id':   rec.equipment_id,
                'equipment_code': rec.equipment.equipment_code if rec.equipment else '',
                'equipment_name': rec.equipment.equipment_name if rec.equipment else '',
                'product_code':   rec.product_code or '',
                'process_id':     rec.process_id,
            }

        return Response({
            'item_states':              item_state_map,
            'item_operators':           item_operator_map,
            'processing_by_equipment':  processing_by_equipment,
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
        # 複数設備同時使用時、2台目以降は actual_qty 加算をスキップする
        # （qty検証も不要。数量は1台目のみカウント）
        skip_qty_update = str(request.data.get('skip_qty_update', 'false')).lower() in ('true', '1')

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
        if not skip_qty_update and operator_action in {BrakeLineRecord.OPERATOR_ACTION_END, BrakeLineRecord.OPERATOR_ACTION_PAUSE}:
            try:
                qty = int(qty_raw)
            except (ValueError, TypeError):
                return Response({'detail': 'qty は整数で入力してください'}, status=400)
            if operator_action == BrakeLineRecord.OPERATOR_ACTION_END and qty <= 0:
                return Response({'detail': 'qty は1以上で入力してください'}, status=400)
            if operator_action == BrakeLineRecord.OPERATOR_ACTION_PAUSE and qty < 0:
                return Response({'detail': 'qty は0以上で入力してください'}, status=400)

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

        # END / PAUSE の場合は LineBacklog.actual_qty を加算
        backlog_data = None
        if operator_action in {
            BrakeLineRecord.OPERATOR_ACTION_END,
            BrakeLineRecord.OPERATOR_ACTION_PAUSE,
        } and qty > 0 and product_id:
            # 実績は sequence_no=0 行に積む（計画行 sequence_no>0 とは分離）
            obj, created = LineBacklog.objects.get_or_create(
                plan_date=plan_date,
                process_id=process_id,
                product_id=product_id,
                line_id=line_id,
                sequence_no=0,
                defaults={'actual_qty': qty},
            )
            if not created:
                LineBacklog.objects.filter(pk=obj.pk).update(actual_qty=F('actual_qty') + qty)
                obj.refresh_from_db()
            backlog_data = {
                'backlog_id': obj.id,
                'actual_qty': int(obj.actual_qty),
                'plan_qty':   int(obj.plan_qty),
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
