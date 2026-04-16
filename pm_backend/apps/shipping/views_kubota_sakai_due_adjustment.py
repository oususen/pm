from datetime import date, datetime, timedelta
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from orders.core.models import KubotaSakaiDueAdjustment, OrderLine
from .serializers import KubotaSakaiDueAdjustmentSerializer


KUBOTA_CUSTOMER_CODE = '000196'


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except ValueError:
        return None


def _parse_decimal(value):
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _source_order_no(order_line):
    """FIRM は OrderLine.customer_order_no、FORECAST は NULL。"""
    order_type = getattr(order_line.order, 'order_type', None) if order_line.order_id else None
    if order_type == 'FORECAST':
        return None
    value = (order_line.customer_order_no or '').strip()
    return value or None


class KubotaSakaiDueAdjustmentViewSet(viewsets.ModelViewSet):
    queryset = KubotaSakaiDueAdjustment.objects.all()
    serializer_class = KubotaSakaiDueAdjustmentSerializer

    # ========== import_orders ==========
    @action(detail=False, methods=['post'])
    def import_orders(self, request):
        """ORDER_LINE から受注を取り込み、t_kubota_sakai_due_adjustment へ差分更新。"""
        start_date = _parse_date(request.data.get('start_date'))
        horizon_days = int(request.data.get('horizon_days') or 30)
        if horizon_days < 1:
            horizon_days = 1
        if horizon_days > 180:
            horizon_days = 180
        if not start_date:
            start_date = date.today()
        end_date = start_date + timedelta(days=horizon_days - 1)

        # 対象 OrderLine: クボタ堺 + OPEN + 納期が期間内
        line_qs = OrderLine.objects.select_related('order', 'order__customer', 'product').filter(
            order__status='OPEN',
            order__customer__customer_code=KUBOTA_CUSTOMER_CODE,
            due_date__range=(start_date, end_date),
        ).order_by('product_code', 'due_date', 'ship_to_code', 'id')
        line_list = list(line_qs)

        # FIRM/FORECAST 重複排除: 同日・同品番・同納入場所で FIRM があれば FORECAST を除外
        firm_key_set = set()
        for line in line_list:
            order_type = getattr(line.order, 'order_type', None)
            if order_type == 'FIRM':
                firm_key_set.add((line.product_code, line.due_date, line.ship_to_code or ''))

        surviving_lines = []
        for line in line_list:
            order_type = getattr(line.order, 'order_type', None)
            key = (line.product_code, line.due_date, line.ship_to_code or '')
            if order_type == 'FORECAST' and key in firm_key_set:
                continue
            surviving_lines.append(line)

        # グルーピング: 品番 + 納入場所 + 注番 + 日付 → demand_qty 合算
        demand_map = {}  # key: (product_code, ship_to_code, source_order_no, due_date) → dict
        for line in surviving_lines:
            order_type = getattr(line.order, 'order_type', None) or 'FORECAST'
            src_order_no = _source_order_no(line)
            ship_to = line.ship_to_code or ''
            key = (line.product_code, ship_to, src_order_no or '', line.due_date)

            if key not in demand_map:
                demand_map[key] = {
                    'product_code': line.product_code,
                    'ship_to_code': ship_to or None,
                    'source_order_no': src_order_no,
                    'order_type': order_type,
                    'due_date': line.due_date,
                    'demand_qty': Decimal('0'),
                    'order_line_id': line.id,
                }
            demand_map[key]['demand_qty'] += (line.quantity or Decimal('0'))
            # FIRM が1つでもあれば FIRM
            if order_type == 'FIRM':
                demand_map[key]['order_type'] = 'FIRM'

        # 差分更新
        created_count = 0
        updated_count = 0
        deleted_count = 0

        with transaction.atomic():
            # 既存レコード取得（期間内）
            existing_qs = KubotaSakaiDueAdjustment.objects.filter(
                due_date__range=(start_date, end_date),
            )
            existing_map = {}
            for row in existing_qs:
                ekey = (row.product_code, row.ship_to_code or '', row.source_order_no or '', row.due_date)
                existing_map[ekey] = row

            processed_keys = set()

            for key, data in demand_map.items():
                processed_keys.add(key)
                existing = existing_map.get(key)

                if existing:
                    # 既存行 → demand_qty と order_type を更新（delivery_qty は保持）
                    changed = False
                    if existing.demand_qty != data['demand_qty']:
                        existing.demand_qty = data['demand_qty']
                        changed = True
                    if existing.order_type != data['order_type']:
                        existing.order_type = data['order_type']
                        changed = True
                    if existing.order_line_id != data['order_line_id']:
                        existing.order_line_id = data['order_line_id']
                        changed = True
                    if changed:
                        existing.save(update_fields=['demand_qty', 'order_type', 'order_line_id'])
                        updated_count += 1
                else:
                    # 新規行
                    KubotaSakaiDueAdjustment.objects.create(
                        product_code=data['product_code'],
                        ship_to_code=data['ship_to_code'],
                        source_order_no=data['source_order_no'],
                        order_type=data['order_type'],
                        due_date=data['due_date'],
                        demand_qty=data['demand_qty'],
                        delivery_qty=Decimal('0'),
                        remaining_qty=Decimal('0'),
                        order_line_id=data['order_line_id'],
                    )
                    created_count += 1

            # 内示→確定の遷移処理:
            # 同日・同品番・同納入場所で FIRM 行があれば、FORECAST 行の delivery_qty を引き継いで削除
            firm_keys_by_date_product = {}  # (product_code, ship_to_code, due_date) → FIRM key
            forecast_keys_by_date_product = {}  # (product_code, ship_to_code, due_date) → FORECAST key
            for key, data in demand_map.items():
                product_code, ship_to, src_order_no, due_date_val = key
                dp_key = (product_code, ship_to, due_date_val)
                if data['order_type'] == 'FIRM':
                    firm_keys_by_date_product[dp_key] = key
                elif data['order_type'] == 'FORECAST':
                    forecast_keys_by_date_product[dp_key] = key

            # 既存テーブルの FORECAST 行で、同日に FIRM が来たもの
            for ekey, existing_row in list(existing_map.items()):
                if ekey in processed_keys:
                    continue  # 既に更新済み
                product_code, ship_to, src_order_no, due_date_val = ekey
                dp_key = (product_code, ship_to, due_date_val)
                if existing_row.order_type == 'FORECAST' and dp_key in firm_keys_by_date_product:
                    # FIRM 行に delivery_qty を引き継ぎ
                    firm_key = firm_keys_by_date_product[dp_key]
                    firm_row = existing_map.get(firm_key) or KubotaSakaiDueAdjustment.objects.filter(
                        product_code=firm_key[0],
                        ship_to_code=firm_key[1] or None,
                        source_order_no=firm_key[2] or None,
                        due_date=firm_key[3],
                    ).first()
                    if firm_row and existing_row.delivery_qty > 0:
                        firm_row.delivery_qty += existing_row.delivery_qty
                        firm_row.save(update_fields=['delivery_qty'])
                    existing_row.delete()
                    deleted_count += 1

            # 残量再計算（取り込み後）
            affected_groups = set()
            for key in processed_keys:
                affected_groups.add((key[0], key[1]))  # (product_code, ship_to_code)
            _recalculate_remaining_for_groups(affected_groups)

        return Response({
            'created': created_count,
            'updated': updated_count,
            'deleted_forecast': deleted_count,
            'total_demand_rows': len(demand_map),
        })

    # ========== grid ==========
    @action(detail=False, methods=['get'])
    def grid(self, request):
        """テーブルから直接読み込み、画面表示用のデータを返す。"""
        start_date = _parse_date(request.query_params.get('start_date'))
        horizon_days = int(request.query_params.get('horizon_days') or 30)
        if horizon_days < 1:
            horizon_days = 1
        if horizon_days > 180:
            horizon_days = 180
        if not start_date:
            start_date = date.today()
        end_date = start_date + timedelta(days=horizon_days - 1)

        qs = KubotaSakaiDueAdjustment.objects.filter(
            due_date__range=(start_date, end_date),
        ).order_by('product_code', 'ship_to_code', 'source_order_no', 'due_date')

        # 外側グループ: 品番+納入場所、内側: 注番
        outer_groups = {}
        for row in qs:
            outer_key = f"{row.product_code}||{row.ship_to_code or ''}"
            if outer_key not in outer_groups:
                outer_groups[outer_key] = {
                    'group_key': outer_key,
                    'product_code': row.product_code,
                    'ship_to_code': row.ship_to_code,
                    'lines_map': {},
                }
            line_key = f"{row.product_code}||{row.ship_to_code or ''}||{row.source_order_no or ''}"
            if line_key not in outer_groups[outer_key]['lines_map']:
                outer_groups[outer_key]['lines_map'][line_key] = {
                    'line_key': line_key,
                    'source_order_no': row.source_order_no,
                    'order_type': row.order_type,
                    'demand_by_date': {},
                    'delivery_by_date': {},
                    'remaining_by_date': {},
                }
            li = outer_groups[outer_key]['lines_map'][line_key]
            d_str = row.due_date.isoformat()
            li['demand_by_date'][d_str] = str(row.demand_qty)
            li['delivery_by_date'][d_str] = str(row.delivery_qty)
            li['remaining_by_date'][d_str] = str(row.remaining_qty)
            # FIRM が1つでもあれば全体を FIRM に
            if row.order_type == 'FIRM':
                li['order_type'] = 'FIRM'

        rows = []
        for outer_key, og in outer_groups.items():
            lines_out = []
            for line_key, li in og['lines_map'].items():
                lines_out.append({
                    'line_key': li['line_key'],
                    'source_order_no': li['source_order_no'],
                    'order_type': li['order_type'],
                    'demand_by_date': li['demand_by_date'],
                    'delivery_by_date': li['delivery_by_date'],
                    'remaining_by_date': li['remaining_by_date'],
                })
            # 注番付き FIRM を先、内示（NULL）を後に
            lines_out.sort(key=lambda x: (x['source_order_no'] is None, x['source_order_no'] or ''))
            rows.append({
                'group_key': og['group_key'],
                'product_code': og['product_code'],
                'ship_to_code': og['ship_to_code'],
                'lines': lines_out,
            })

        rows.sort(key=lambda r: (r['product_code'] or '', r['ship_to_code'] or ''))

        return Response({
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'horizon_days': horizon_days,
            'rows': rows,
        })

    # ========== bulk_save ==========
    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        """delivery_qty を保存し、残量を再計算する。"""
        rows = request.data.get('rows')
        if not isinstance(rows, list):
            return Response({'detail': 'rows は配列で指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user if request.user and request.user.is_authenticated else None
        now = datetime.now()
        updated_count = 0
        affected_groups = set()

        with transaction.atomic():
            for row in rows:
                line_key = row.get('line_key', '')
                delivery_by_date = row.get('delivery_by_date', {})
                if not line_key or not delivery_by_date:
                    continue

                # line_key = "product_code||ship_to_code||source_order_no"
                parts = line_key.split('||')
                if len(parts) != 3:
                    continue
                product_code, ship_to_code, source_order_no = parts
                ship_to_code = ship_to_code or None
                source_order_no = source_order_no or None

                for date_str, qty_val in delivery_by_date.items():
                    due_date_val = _parse_date(date_str)
                    if not due_date_val:
                        continue
                    delivery = _parse_decimal(qty_val)
                    if delivery is None:
                        delivery = Decimal('0')

                    adj = KubotaSakaiDueAdjustment.objects.filter(
                        product_code=product_code,
                        ship_to_code=ship_to_code,
                        source_order_no=source_order_no,
                        due_date=due_date_val,
                    ).first()

                    if adj:
                        if adj.delivery_qty != delivery:
                            adj.delivery_qty = delivery
                            adj.updated_by = user
                            adj.updated_at = now
                            adj.save(update_fields=['delivery_qty', 'updated_by', 'updated_at'])
                            updated_count += 1
                    else:
                        # テーブルに行がない場合（demand=0 だが delivery を入れたい場合）
                        KubotaSakaiDueAdjustment.objects.create(
                            product_code=product_code,
                            ship_to_code=ship_to_code,
                            source_order_no=source_order_no,
                            order_type='FIRM' if source_order_no else 'FORECAST',
                            due_date=due_date_val,
                            demand_qty=Decimal('0'),
                            delivery_qty=delivery,
                            remaining_qty=Decimal('0'),
                            updated_by=user,
                            updated_at=now,
                        )
                        updated_count += 1

                    affected_groups.add((product_code, ship_to_code or ''))

            # 残量再計算
            _recalculate_remaining_for_groups(affected_groups)

        return Response({
            'updated': updated_count,
            'affected_groups': len(affected_groups),
        })


def _recalculate_remaining_for_groups(groups):
    """(product_code, ship_to_code) のグループごとに、注番別で残量を時系列再計算。
    残量 = 累積(demand_qty) - 累積(delivery_qty)  ※LT考慮なし
    """
    for product_code, ship_to_code in groups:
        qs = KubotaSakaiDueAdjustment.objects.filter(
            product_code=product_code,
            ship_to_code=ship_to_code or None,
        ).order_by('source_order_no', 'due_date')

        # 注番別にグルーピング
        by_order_no = defaultdict(list)
        for row in qs:
            by_order_no[row.source_order_no or ''].append(row)

        for order_no, rows in by_order_no.items():
            rows.sort(key=lambda r: r.due_date)
            cumulative_demand = Decimal('0')
            cumulative_delivery = Decimal('0')
            for row in rows:
                cumulative_demand += row.demand_qty
                cumulative_delivery += row.delivery_qty
                new_remaining = cumulative_demand - cumulative_delivery
                if row.remaining_qty != new_remaining:
                    row.remaining_qty = new_remaining
                    row.save(update_fields=['remaining_qty'])
