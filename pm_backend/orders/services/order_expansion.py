from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple

from django.db import transaction

from masters.models import Routing
from orders.models import LineDemand, OrderLine


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

    def expand_open_orders(self, clear_existing: bool = True) -> Dict[str, object]:
        """
        OPEN受注明細をライン需要に展開し、t_line_demand を再生成する。
        """
        aggregated: Dict[Tuple[int, str, object], Dict[str, object]] = {}

        order_lines = OrderLine.objects.filter(
            order__status='OPEN'
        ).select_related('order', 'product')

        for ol in order_lines:
            product = ol.product
            if not product:
                self.warnings.append(f"製品マスタ未登録のためスキップ: {ol.product_code}")
                continue

            steps = self._get_routing_steps(product_id=product.id)
            if not steps:
                self.warnings.append(f"ルーティング未設定のためスキップ: {product.product_code}")
                continue

            required_date = ol.due_date
            for step in reversed(steps):
                if not step.line_id:
                    self.warnings.append(f"ライン未設定の工程をスキップ: routing_step_id={step.id}")
                    continue

                lead_days = self._resolve_lead_time_days(step)
                target_date = required_date - timedelta(days=lead_days)
                step_product = step.output_product if step.output_product_id else product
                product_code = step_product.product_code if step_product else ol.product_code
                product_id = step_product.id if step_product else (product.id if product else None)

                key = (step.line_id, product_code, target_date)
                entry = aggregated.get(key)
                if not entry:
                    entry = {
                        'line_id': step.line_id,
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

                qty = ol.quantity or Decimal('0')
                if ol.order.order_type == 'FIRM':
                    entry['firm_qty'] += qty
                else:
                    entry['forecast_qty'] += qty
                entry['order_numbers'].add(ol.order.order_no)

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

    def _resolve_lead_time_days(self, step) -> int:
        """工程のLT（日）を決定する。"""
        if step.time_unit == 'DAY':
            if step.lead_time_days and step.lead_time_days > 0:
                return step.lead_time_days
            if step.line and step.line.lead_time_days:
                return max(step.line.lead_time_days, 0)
        return 0

    def _calc_progress(self, numerator: Decimal, denominator: Decimal) -> Decimal:
        """0除算を避けつつ進捗（0-1）を小数3桁で返す。"""
        if denominator is None or denominator == 0:
            return Decimal('0')
        return (numerator / denominator).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
