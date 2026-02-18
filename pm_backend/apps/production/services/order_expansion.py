from collections import defaultdict
from datetime import date, timedelta
import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple

from django.db import transaction

from masters.models import BOM, BOMItem, Line, Routing
from orders.core.models import OrderLine
from production.models import LineDemand


class OrderExpansionService:
    """
    受注をライン別の需要に展開するサービス。

    - OPENステータスの受注明細を対象に、製品のデフォルトルーティングをたどってライン別に数量を積み上げる
    - リードタイムは工程(time_unit='DAY')の lead_time_days を優先し、未設定の場合はラインの lead_time_days を使用
    - plan_qty は初期値として (forecast + firm) をセットし、進捗率を計算する
    """

    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self._routing_cache: Dict[int, List] = {}
        self._child_bom_cache: Dict[int, BOM | None] = {}
        self._bom_multiplier_cache: Dict[int, Dict[int, Decimal]] = {}
        self._bom_path_multiplier_cache: Dict[int, Dict[str, Decimal]] = {}
        self._supplier_line_cache: Dict[int, int | None] = {}  # product_id -> 仕入先ラインID

    def expand_open_orders(self, clear_existing: bool = True) -> Dict[str, object]:
        """
        OPEN受注明細をライン需要に展開し、t_line_demand を再生成する。
        """
        aggregated: Dict[Tuple[int, str, object], Dict[str, object]] = {}
        workday_cache: Dict[int, Dict[object, bool]] = {}
        calendar_cache: Dict[int, object] = {}
        default_calendar_id = None

        order_lines = OrderLine.objects.filter(
            order__status='OPEN'
        ).select_related('order', 'product')

        from masters.models import Calendar, CalendarDay

        default_calendar_id = Calendar.objects.filter(
            calendar_code='daiso'
        ).values_list('id', flat=True).first()

        def is_working_day(calendar_id, target_date):
            if not calendar_id:
                return target_date.weekday() < 5
            cache = workday_cache.setdefault(calendar_id, {})
            if target_date in cache:
                return cache[target_date]
            cal = CalendarDay.objects.filter(
                calendar_id=calendar_id,
                target_date=target_date
            ).first()
            is_work = cal.is_working_day if cal is not None else target_date.weekday() < 5
            cache[target_date] = is_work
            return is_work

        def shift_business_days(calendar_id, target_date, days):
            if not days:
                if not calendar_id:
                    return target_date
                if is_working_day(calendar_id, target_date):
                    return target_date
                current = target_date
                while True:
                    current = current - timedelta(days=1)
                    if is_working_day(calendar_id, current):
                        return current
            step = -1 if days > 0 else 1
            remaining = abs(int(days))
            current = target_date
            while remaining > 0:
                current = current + timedelta(days=step)
                if is_working_day(calendar_id, current):
                    remaining -= 1
            return current

        def resolve_calendar_id(line_id):
            if line_id in calendar_cache:
                return calendar_cache[line_id]
            from masters.models import Line
            line_obj = Line.objects.filter(id=line_id).first()
            cal_id = getattr(line_obj, 'calendar_id', None) or default_calendar_id
            calendar_cache[line_id] = cal_id
            return cal_id

        def path_key(path):
            try:
                return tuple(int(p) for p in str(path).split('.'))
            except Exception:
                return (str(path),)

        minutes_per_day = 480

        def calc_shift_days(prev_minutes, add_minutes):
            # 480分未満は0日扱い（切り捨て）
            prev_days = math.floor(prev_minutes / minutes_per_day) if prev_minutes > 0 else 0
            total_minutes = prev_minutes + add_minutes
            total_days = math.floor(total_minutes / minutes_per_day) if total_minutes > 0 else 0
            return total_days - prev_days, total_minutes

        for ol in order_lines:
            product = ol.product
            if not product:
                self.warnings.append(f"製品マスタ未登録のためスキップ: {ol.product_code}")
                continue

            steps = self._get_routing_steps(product_id=product.id)
            if not steps:
                self.warnings.append(f"ルーティング未設定のためスキップ: {product.product_code}")
                continue

            # BOM倍率マップ（品番別合計・パス別）を取得
            bom_multiplier, path_multiplier = self._get_bom_multiplier_maps(product.id)

            # ルーティング上の按分倍率を集計し、BOM合計との補正係数を算出
            routed_multiplier_by_product: Dict[int, Decimal] = defaultdict(Decimal)
            for step in steps:
                step_product = step.output_product if step.output_product_id else product
                if not step_product:
                    continue
                if step.hierarchy_path == 'final':
                    base_mult = Decimal('1')
                else:
                    base_mult = path_multiplier.get(step.hierarchy_path, Decimal('1'))
                routed_multiplier_by_product[step_product.id] += base_mult

            correction_by_product: Dict[int, Decimal] = {}
            for pid, routed_mult in routed_multiplier_by_product.items():
                expected_mult = bom_multiplier.get(pid)
                if expected_mult is not None and routed_mult > 0:
                    correction_by_product[pid] = expected_mult / routed_mult
                else:
                    correction_by_product[pid] = Decimal('1')

            required_date = ol.due_date
            final_required_date = required_date
            final_minutes = 0

            # hierarchy_pathに基づき、工程系統ごとにrequired_dateを計算
            path_step_map = {
                step.hierarchy_path: step
                for step in steps
                if step.hierarchy_path and step.hierarchy_path != 'final'
            }
            children_map = {}
            for path in path_step_map.keys():
                parent_path = path.rsplit('.', 1)[0] if '.' in path else None
                children_map.setdefault(parent_path, []).append(path)

            final_step = next((s for s in steps if s.hierarchy_path == 'final'), None)
            if final_step:
                final_calendar_id = resolve_calendar_id(final_step.line_id)
                # 最終工程はproductを渡す（最終品判定）
                lead_days = self._resolve_lead_time_days(final_step, product)
                step_minutes = final_step.duration_min or 0 if final_step.time_unit == 'MINUTE' else 0
                minute_shift, final_minutes = calc_shift_days(0, step_minutes)
                final_required_date = shift_business_days(
                    final_calendar_id,
                    required_date,
                    lead_days + minute_shift
                )

            required_by_path = {}

            def compute_required_date(path, parent_date, parent_minutes):
                step = path_step_map.get(path)
                if not step:
                    return
                calendar_id = resolve_calendar_id(step.line_id)
                # output_productまたはメイン製品を渡して最終品・ライン最終品を判定
                lead_days = self._resolve_lead_time_days(step, product)
                step_minutes = step.duration_min or 0 if step.time_unit == 'MINUTE' else 0
                minute_shift, total_minutes = calc_shift_days(parent_minutes, step_minutes)
                required_for_step = shift_business_days(
                    calendar_id,
                    parent_date,
                    lead_days + minute_shift
                )
                required_by_path[path] = (required_for_step, total_minutes)
                for child_path in sorted(children_map.get(path, []), key=path_key):
                    compute_required_date(child_path, required_for_step, total_minutes)

            for root_path in sorted(children_map.get(None, []), key=path_key):
                compute_required_date(root_path, final_required_date, final_minutes)

            for step in reversed(steps):
                if not step.line_id:
                    self.warnings.append(f"ライン未設定の工程をスキップ: routing_step_id={step.id}")
                    continue

                # OUTSOURCEラインの場合、BOMItemのsupplierから仕入先ラインに振り替える
                effective_line_id = step.line_id
                step_product = step.output_product if step.output_product_id else product
                if step.line and step.line.line_type == 'OUTSOURCE' and step_product:
                    supplier_line_id = self._get_supplier_line_id(step_product.id)
                    if supplier_line_id:
                        effective_line_id = supplier_line_id

                calendar_id = resolve_calendar_id(effective_line_id)
                # output_productまたはメイン製品を渡して最終品・ライン最終品を判定
                lead_days = self._resolve_lead_time_days(step, product)
                if step.hierarchy_path == 'final':
                    target_date = final_required_date
                elif step.hierarchy_path in required_by_path:
                    target_date = required_by_path[step.hierarchy_path][0]
                else:
                    target_date = shift_business_days(calendar_id, required_date, lead_days)
                product_code = step_product.product_code if step_product else ol.product_code
                product_id = step_product.id if step_product else (product.id if product else None)

                # BOMパス倍率 × 補正係数 → 合計がBOM倍率と一致
                if step.hierarchy_path == 'final':
                    base_mult = Decimal('1')
                else:
                    base_mult = path_multiplier.get(step.hierarchy_path, Decimal('1'))
                correction = correction_by_product.get(product_id, Decimal('1'))

                key = (effective_line_id, product_code, target_date)
                entry = aggregated.get(key)
                if not entry:
                    entry = {
                        'line_id': effective_line_id,
                        'routing_step_id': step.id,
                        'product_id': product_id,
                        'product_code': product_code,
                        'plan_date': target_date,
                        'lead_time_days': lead_days,
                        'forecast_qty': Decimal('0'),
                        'firm_qty': Decimal('0'),
                        'order_numbers': set(),
                    }
                    aggregated[key] = entry

                qty = (ol.quantity or Decimal('0')) * base_mult * correction
                if ol.order.order_type == 'FIRM':
                    entry['firm_qty'] += qty
                else:
                    entry['forecast_qty'] += qty
                entry['order_numbers'].add(ol.order.order_no)

                if step.hierarchy_path == 'final':
                    required_date = target_date

        objects_to_create: List[LineDemand] = []
        for data in aggregated.values():
            required_qty = (data['forecast_qty'] or Decimal('0')) + (data['firm_qty'] or Decimal('0'))
            plan_qty = required_qty
            actual_qty = Decimal('0')

            plan_progress = self._calc_progress(plan_qty, required_qty)
            actual_progress = self._calc_progress(actual_qty, required_qty)

            order_numbers = sorted(list(data['order_numbers']))
            order_numbers_str = ','.join(order_numbers)
            if len(order_numbers_str) > 500:
                order_numbers_str = order_numbers_str[:500]

            objects_to_create.append(
                LineDemand(
                    line_id=data['line_id'],
                    routing_step_id=data['routing_step_id'],
                    product_id=data['product_id'],
                    product_code=data['product_code'],
                    plan_date=data['plan_date'],
                    lead_time_days=data['lead_time_days'],
                    forecast_qty=data['forecast_qty'],
                    firm_qty=data['firm_qty'],
                    plan_qty=plan_qty,
                    actual_qty=actual_qty,
                    plan_progress=plan_progress,
                    actual_progress=actual_progress,
                    order_numbers=order_numbers_str,
                )
            )

        with transaction.atomic():
            cleared = 0
            if clear_existing:
                cleared, _ = LineDemand.objects.all().delete()

            if objects_to_create:
                LineDemand.objects.bulk_create(objects_to_create)

        return {
            'cleared': cleared if clear_existing else 0,
            'created': len(objects_to_create),
            'warnings': self.warnings,
            'errors': self.errors,
        }

    def _get_routing_steps(self, product_id: int):
        """デフォルトルーティングの工程一覧をキャッシュして返す。"""
        if product_id in self._routing_cache:
            return self._routing_cache[product_id]

        routing = Routing.objects.filter(
            product_id=product_id,
            is_active=True
        ).order_by('-is_default', '-id').first()

        if not routing:
            self._routing_cache[product_id] = []
            return []

        steps = list(
            routing.steps.select_related('line', 'output_product').order_by('step_no')
        )
        self._routing_cache[product_id] = steps
        return steps

    def _pick_child_bom(self, product_id: int):
        """子製品の有効BOMを取得（有効期間内優先、なければ最新有効）。連産品BOMは除外。"""
        if product_id in self._child_bom_cache:
            return self._child_bom_cache[product_id]

        today = date.today()
        bom = (
            BOM.objects.filter(
                parent_product_id=product_id,
                is_active=True,
                is_coproduct=False,
                valid_from__lte=today,
            )
            .order_by('-valid_from', '-id')
            .first()
        )
        if not bom:
            bom = (
                BOM.objects.filter(
                    parent_product_id=product_id,
                    is_active=True,
                    is_coproduct=False,
                )
                .order_by('-valid_from', '-id')
                .first()
            )

        self._child_bom_cache[product_id] = bom
        return bom

    def _collect_bom_multipliers(
        self,
        product_id: int,
        current_multiplier: Decimal,
        path_prefix: Tuple[int, ...],
        active_bom_ids: set,
        result: Dict[int, Decimal],
        path_result: Dict[str, Decimal],
    ):
        """
        BOMツリーを再帰的に辿り、品番別合計倍率とパス別倍率を構築する。
        連産品BOMは _pick_child_bom で除外済み。
        """
        bom = self._pick_child_bom(product_id)
        if not bom or bom.id in active_bom_ids:
            return

        next_active = active_bom_ids | {bom.id}

        items = (
            BOMItem.objects
            .filter(bom_id=bom.id)
            .select_related('child_product')
            .order_by('id')
        )
        for idx, item in enumerate(items, start=1):
            if not item.child_product_id:
                continue
            qty = Decimal(str(item.quantity or 0))
            if qty == 0:
                continue

            child_multiplier = current_multiplier * qty
            path_tuple = path_prefix + (idx,)
            path_key = '.'.join(str(p) for p in path_tuple)

            path_result[path_key] = (
                path_result.get(path_key, Decimal('0')) + child_multiplier
            )
            result[item.child_product_id] = (
                result.get(item.child_product_id, Decimal('0')) + child_multiplier
            )
            self._collect_bom_multipliers(
                product_id=item.child_product_id,
                current_multiplier=child_multiplier,
                path_prefix=path_tuple,
                active_bom_ids=next_active,
                result=result,
                path_result=path_result,
            )

    def _get_bom_multiplier_maps(self, product_id: int):
        """
        最終品1個あたりのBOM倍率を返す。
        - bom_multiplier: product_id -> 合計倍率（最終品自身は1）
        - path_multiplier: hierarchy_path -> 倍率（ステップ間の按分に使用）
        """
        cached = self._bom_multiplier_cache.get(product_id)
        cached_path = self._bom_path_multiplier_cache.get(product_id)
        if cached is not None and cached_path is not None:
            return cached, cached_path

        result: Dict[int, Decimal] = {product_id: Decimal('1')}
        path_result: Dict[str, Decimal] = {}
        self._collect_bom_multipliers(
            product_id=product_id,
            current_multiplier=Decimal('1'),
            path_prefix=(),
            active_bom_ids=set(),
            result=result,
            path_result=path_result,
        )

        self._bom_multiplier_cache[product_id] = result
        self._bom_path_multiplier_cache[product_id] = path_result
        return result, path_result

    def _get_supplier_line_id(self, product_id: int) -> int | None:
        """
        外注品のBOMItemからsupplierを取得し、対応する仕入先ライン（PURCHASE）のIDを返す。
        見つからない場合はNoneを返す。
        """
        if product_id in self._supplier_line_cache:
            return self._supplier_line_cache[product_id]

        bom_item = (
            BOMItem.objects
            .filter(child_product_id=product_id, supplier__isnull=False)
            .select_related('supplier')
            .first()
        )
        supplier_line_id = None
        if bom_item and bom_item.supplier_id:
            supplier_code = bom_item.supplier.supplier_code
            line = Line.objects.filter(line_code=supplier_code).first()
            if line:
                supplier_line_id = line.id

        self._supplier_line_cache[product_id] = supplier_line_id
        return supplier_line_id

    def _resolve_lead_time_days(self, step, main_product=None) -> int:
        """
        工程のLT（日）を決定する。
        - 最終品・ライン最終品（is_final_product or is_line_final_product）: ラインLT（Line.lead_time_days）のみ
        - 中間品: RoutingStep.lead_time_days のみ使用（MINUTE管理工程はstep_lt=0なのでLT=0）
        """
        # 最終工程、またはoutput_productが最終品・ライン最終品かどうかを判定
        product = step.output_product if step.output_product_id else main_product
        is_final = (step.hierarchy_path == 'final') or (
            product and (product.is_final_product or product.is_line_final_product)
        )

        if is_final:
            # 最終品・ライン最終品: DAY管理でstep_ltが設定されていればRoutingStep.lead_time_daysを最優先
            if step.time_unit == 'DAY' and step.lead_time_days:
                return max(step.lead_time_days, 0)
            # それ以外（MINUTE管理など）はラインLT
            if step.line and step.line.lead_time_days:
                return max(step.line.lead_time_days, 0)
            return 0
        else:
            # 中間品: RoutingStep.lead_time_days のみ使用（expand_processesと同じロジック）
            # MINUTE管理の工程はstep_lt=0なのでLT=0（分計算のみ）
            return max(step.lead_time_days or 0, 0)

    def _calc_progress(self, numerator: Decimal, denominator: Decimal) -> Decimal:
        """0除算を避けつつ進捗（0-1）を小数3桁で返す。"""
        if denominator is None or denominator == 0:
            return Decimal('0')
        return (numerator / denominator).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
