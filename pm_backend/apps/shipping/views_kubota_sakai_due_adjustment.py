from datetime import date, datetime, timedelta
from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Max, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from masters.models import Calendar, Contact, Line, Process, Product
from orders.core.models import KubotaSakaiDueAdjustment, OrderLine
from production.models_plan_change_log import ProductionPlanChangeLog
from orders.utils.calendar_utils import WorkingDayCalculator, get_business_today
from system_settings.models import SystemSetting
from .serializers import KubotaSakaiDueAdjustmentSerializer
from .services.email_service import EmailService


KUBOTA_CUSTOMER_CODE = '000196'
KUBOTA_DUE_ADJUSTMENT_LINE_CODE = 'KBT_DUE_ADJ'
KUBOTA_DUE_ADJUSTMENT_LINE_NAME = 'クボタ納期調整'
KUBOTA_DUE_ADJUSTMENT_PROCESS_CODE = 'KBT_DUE_ADJ'
KUBOTA_DUE_ADJUSTMENT_PROCESS_NAME = 'クボタ納期調整'


def _get_lock_date():
    return SystemSetting.get_lock_date('kubota_sakai_due')


def _resolve_kubota_calendar():
    rows = Calendar.objects.all()
    exact_hits = rows.filter(
        Q(calendar_code__iexact='kubota_sakai')
        | Q(calendar_code__iexact='kobota_sakai')
    )
    if exact_hits.exists():
        return exact_hits.order_by('id').first()
    name_hits = rows.filter(Q(calendar_name__icontains='クボタ') & Q(calendar_name__icontains='堺'))
    if name_hits.exists():
        return name_hits.order_by('id').first()
    return None


def _get_due_plan_lock_date():
    try:
        setting = SystemSetting.objects.get(key='lock_days.kubota_sakai_due_plan')
        days = int(str(setting.value or '0').strip())
        if days <= 0:
            return None
        base_date = get_business_today()
        calculator = WorkingDayCalculator(_resolve_kubota_calendar())
        return calculator.add_working_days(base_date, days)
    except (SystemSetting.DoesNotExist, ValueError, TypeError):
        return None


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


def _resolve_due_adjustment_line_process():
    line = (
        Line.objects.filter(
            Q(line_name=KUBOTA_DUE_ADJUSTMENT_LINE_NAME)
            | Q(line_code=KUBOTA_DUE_ADJUSTMENT_LINE_CODE)
        )
        .order_by('id')
        .first()
    )
    if not line:
        line = Line.objects.create(
            line_code=KUBOTA_DUE_ADJUSTMENT_LINE_CODE,
            line_name=KUBOTA_DUE_ADJUSTMENT_LINE_NAME,
            line_type='OTHER',
            is_active=True,
        )

    process = (
        Process.objects.filter(
            Q(process_name=KUBOTA_DUE_ADJUSTMENT_PROCESS_NAME)
            | Q(process_code=KUBOTA_DUE_ADJUSTMENT_PROCESS_CODE)
        )
        .order_by('id')
        .first()
    )
    if not process:
        process = Process.objects.create(
            process_code=KUBOTA_DUE_ADJUSTMENT_PROCESS_CODE,
            process_name=KUBOTA_DUE_ADJUSTMENT_PROCESS_NAME,
            line=line,
            management_unit='DAY',
            is_active=True,
        )
    elif process.line_id != line.id:
        process.line = line
        process.save(update_fields=['line'])

    return line, process


def _to_log_int_qty(value):
    num = _parse_decimal(value)
    if num is None:
        return 0
    return int(num.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _build_due_adjustment_plan_id(product_code, due_date, ship_to_code=None, source_order_no=None):
    product = str(product_code or '').strip() or 'UNKNOWN'
    ship_to = str(ship_to_code or '').strip() or 'NO_SHIP'
    source = str(source_order_no or '').strip() or 'TOTAL'
    plan_id = f'KBT_DUE_{product}_{due_date:%Y%m%d}_{ship_to}_{source}'
    return plan_id[:255]


def _create_due_adjustment_change_log(
    product_code,
    ship_to_code,
    due_date,
    before_qty,
    after_qty,
    reason,
    user,
    line,
    process,
    product_cache,
):
    code = str(product_code or '').strip()
    if not code:
        return False

    if code not in product_cache:
        product_cache[code] = Product.objects.filter(product_code=code).order_by('id').first()
    product = product_cache.get(code)
    if not product:
        return False

    ProductionPlanChangeLog.objects.create(
        plan_date=due_date,
        product_id=product.id,
        process_id=process.id,
        line_id=line.id,
        sequence_no=1,
        plan_id=_build_due_adjustment_plan_id(
            product_code=code,
            due_date=due_date,
            ship_to_code=ship_to_code,
            source_order_no='TOTAL',
        ),
        before_qty=_to_log_int_qty(before_qty),
        after_qty=_to_log_int_qty(after_qty),
        reason=reason,
        changed_by=user,
    )
    return True


def _line_priority_for_allocation(row):
    """同日内での注番割当優先順位。
    FIRM を優先し、注番文字列昇順。FORECAST(注番NULL)は後ろ。
    """
    order_rank = 0 if row.order_type == 'FIRM' else 1
    source = row.source_order_no or ''
    null_rank = 1 if row.source_order_no is None else 0
    return (row.due_date, order_rank, null_rank, source, row.id)


def _bucket_priority(row):
    """需要バケットの優先順（納期調整での注番紐づけ順）。"""
    order_rank = 0 if row.order_type == 'FIRM' else 1
    null_rank = 1 if row.source_order_no is None else 0
    source = row.source_order_no or ''
    return (row.due_date, order_rank, null_rank, source, row.id)


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

        # 締め日以前は取込対象外
        lock_date = _get_lock_date()
        if lock_date:
            if start_date <= lock_date:
                start_date = lock_date + timedelta(days=1)
            if start_date > end_date:
                return Response({
                    'created': 0, 'updated': 0, 'deleted_forecast': 0,
                    'total_demand_rows': 0,
                    'lock_date': lock_date.isoformat(),
                    'detail': f'{lock_date} まで締め済みのため取込対象がありません。',
                })

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
            # 需要として存在していた内示が取込対象から消えた場合のみ引き継ぎ削除する。
            # demand_qty=0 の調整用内示行は保持する。
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
                if (
                    existing_row.order_type == 'FORECAST'
                    and (existing_row.demand_qty or Decimal('0')) > 0
                    and dp_key in firm_keys_by_date_product
                ):
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

        # 表示期間より前の繰越残量を計算（品番+納入場所別）
        carry_qs = KubotaSakaiDueAdjustment.objects.filter(
            due_date__lt=start_date,
        ).order_by('product_code', 'ship_to_code')
        carry_remaining = {}  # (product_code, ship_to_code) → Decimal
        for row in carry_qs:
            gkey = (row.product_code, row.ship_to_code or '')
            if gkey not in carry_remaining:
                carry_remaining[gkey] = Decimal('0')
            carry_remaining[gkey] += row.delivery_qty - row.demand_qty

        # テーブル全体の最新調整日
        last_adjusted_at_raw = KubotaSakaiDueAdjustment.objects.aggregate(
            last=Max('updated_at')
        )['last']
        last_adjusted_at = last_adjusted_at_raw.strftime('%Y-%m-%d %H:%M') if last_adjusted_at_raw else None

        # 表示期間内のデータ取得
        qs = KubotaSakaiDueAdjustment.objects.filter(
            due_date__range=(start_date, end_date),
        ).order_by('product_code', 'ship_to_code', 'source_order_no', 'due_date')

        # 外側グループ: 品番+納入場所、内側: 注番
        outer_groups = {}
        for row in qs:
            outer_key = f"{row.product_code}||{row.ship_to_code or ''}"
            if outer_key not in outer_groups:
                gkey = (row.product_code, row.ship_to_code or '')
                outer_groups[outer_key] = {
                    'group_key': outer_key,
                    'product_code': row.product_code,
                    'ship_to_code': row.ship_to_code,
                    'carry_remaining': str(carry_remaining.get(gkey, Decimal('0'))),
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
                }
            li = outer_groups[outer_key]['lines_map'][line_key]
            d_str = row.due_date.isoformat()
            li['demand_by_date'][d_str] = str(row.demand_qty)
            li['delivery_by_date'][d_str] = str(row.delivery_qty)
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
                })
            lines_out.sort(key=lambda x: (x['source_order_no'] is None, x['source_order_no'] or ''))
            rows.append({
                'group_key': og['group_key'],
                'product_code': og['product_code'],
                'ship_to_code': og['ship_to_code'],
                'carry_remaining': og['carry_remaining'],
                'lines': lines_out,
            })

        rows.sort(key=lambda r: (r['product_code'] or '', r['ship_to_code'] or ''))

        lock_date = _get_lock_date()
        due_plan_lock_date = _get_due_plan_lock_date()
        return Response({
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'horizon_days': horizon_days,
            'lock_date': lock_date.isoformat() if lock_date else None,
            'due_plan_lock_date': due_plan_lock_date.isoformat() if due_plan_lock_date else None,
            'last_adjusted_at': last_adjusted_at,
            'rows': rows,
        })

    # ========== bulk_save ==========
    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        """delivery_qty を保存し、注番紐づけをFIFOで確定して残量を再計算する。"""
        rows = request.data.get('rows')
        if not isinstance(rows, list):
            return Response({'detail': 'rows は配列で指定してください。'}, status=status.HTTP_400_BAD_REQUEST)
        change_reason = str(request.data.get('change_reason') or '').strip()
        allow_due_plan_lock_update = bool(change_reason)

        user = request.user if request.user and request.user.is_authenticated else None
        now = datetime.now()
        lock_date = _get_lock_date()
        due_plan_lock_date = _get_due_plan_lock_date()
        updated_count = 0
        change_log_count = 0
        affected_groups = set()
        log_line = None
        log_process = None
        product_cache = {}
        if allow_due_plan_lock_update:
            log_line, log_process = _resolve_due_adjustment_line_process()
        # 入力値（セル値）: (product_code, ship_to_code, source_order_no, due_date) -> delivery
        input_delivery_map = {}
        # 行分解を再実行しないために保持
        parsed_line_rows = []

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
                parsed_line_rows.append((product_code, ship_to_code, source_order_no, delivery_by_date))
                affected_groups.add((product_code, ship_to_code or ''))

                for date_str, qty_val in delivery_by_date.items():
                    due_date_val = _parse_date(date_str)
                    if not due_date_val:
                        continue
                    if lock_date and due_date_val <= lock_date:
                        continue
                    if due_plan_lock_date and due_date_val <= due_plan_lock_date and not allow_due_plan_lock_update:
                        continue
                    delivery = _parse_decimal(qty_val)
                    if delivery is None:
                        delivery = Decimal('0')
                    if delivery < 0:
                        delivery = Decimal('0')
                    input_delivery_map[(product_code, ship_to_code, source_order_no, due_date_val)] = delivery

            # 入力で指定されたキーで行が無いものは先に作成（demand=0）
            for product_code, ship_to_code, source_order_no, delivery_by_date in parsed_line_rows:
                for date_str, qty_val in delivery_by_date.items():
                    due_date_val = _parse_date(date_str)
                    if not due_date_val:
                        continue
                    key = (product_code, ship_to_code, source_order_no, due_date_val)
                    if key not in input_delivery_map:
                        continue
                    exists = KubotaSakaiDueAdjustment.objects.filter(
                        product_code=product_code,
                        ship_to_code=ship_to_code,
                        source_order_no=source_order_no,
                        due_date=due_date_val,
                    ).exists()
                    if exists:
                        continue
                    KubotaSakaiDueAdjustment.objects.create(
                        product_code=product_code,
                        ship_to_code=ship_to_code,
                        source_order_no=source_order_no,
                        order_type='FIRM' if source_order_no else 'FORECAST',
                        due_date=due_date_val,
                        demand_qty=Decimal('0'),
                        delivery_qty=Decimal('0'),
                        remaining_qty=Decimal('0'),
                        updated_by=user,
                        updated_at=now,
                    )

            # グループごとにFIFO再配分して delivery_qty を確定
            # 重要: 日付別の計画数量（Σdelivery@date）は維持し、注番のみ再紐づけする。
            for product_code, ship_to_code_norm in affected_groups:
                ship_to_code = ship_to_code_norm or None
                group_rows = list(
                    KubotaSakaiDueAdjustment.objects.filter(
                        product_code=product_code,
                        ship_to_code=ship_to_code,
                    )
                )
                if not group_rows:
                    continue
                existing_by_key = {
                    (r.source_order_no, r.due_date): r
                    for r in group_rows
                }
                before_date_totals = defaultdict(lambda: Decimal('0'))
                for adj in group_rows:
                    before_date_totals[adj.due_date] += (adj.delivery_qty or Decimal('0'))

                # 日付別総納入量（入力で上書き、未入力は既存値）
                date_totals = defaultdict(lambda: Decimal('0'))
                touched_dates = set()
                for adj in group_rows:
                    key = (adj.product_code, adj.ship_to_code, adj.source_order_no, adj.due_date)
                    qty = input_delivery_map.get(key, adj.delivery_qty or Decimal('0'))
                    if qty < 0:
                        qty = Decimal('0')
                    date_totals[adj.due_date] += qty
                for key, qty in input_delivery_map.items():
                    p, s, so, d = key
                    if p != product_code or (s or None) != ship_to_code:
                        continue
                    touched_dates.add(d)
                    if (so, d) not in existing_by_key:
                        add_qty = qty if qty and qty > 0 else Decimal('0')
                        date_totals[d] += add_qty

                # 需要バケット（注番紐づけ先）
                demand_buckets = [r for r in group_rows if (r.demand_qty or Decimal('0')) > 0]
                demand_buckets.sort(key=_bucket_priority)

                # demandが全く無いグループは日付総量を既存の行優先でそのまま保持
                if not demand_buckets:
                    fallback_rows = sorted(group_rows, key=_line_priority_for_allocation)
                    for adj in fallback_rows:
                        d = adj.due_date
                        new_delivery = date_totals.get(d, Decimal('0'))
                        if adj.delivery_qty != new_delivery:
                            adj.delivery_qty = new_delivery
                            adj.updated_by = user
                            adj.updated_at = now
                            adj.save(update_fields=['delivery_qty', 'updated_by', 'updated_at'])
                            updated_count += 1
                    if allow_due_plan_lock_update:
                        for target_date in sorted(touched_dates):
                            before_total = before_date_totals.get(target_date, Decimal('0'))
                            after_total = date_totals.get(target_date, Decimal('0'))
                            if before_total == after_total:
                                continue
                            if _create_due_adjustment_change_log(
                                product_code=product_code,
                                ship_to_code=ship_to_code,
                                due_date=target_date,
                                before_qty=before_total,
                                after_qty=after_total,
                                reason=change_reason,
                                user=user,
                                line=log_line,
                                process=log_process,
                                product_cache=product_cache,
                            ):
                                change_log_count += 1
                    continue

                # FIFOで日別数量を注番へ割付
                remaining_demands = [b.demand_qty or Decimal('0') for b in demand_buckets]
                alloc_map = defaultdict(lambda: Decimal('0'))  # (source_order_no, ship_date) -> qty
                ship_dates = sorted(date_totals.keys())

                bucket_idx = 0
                for ship_date in ship_dates:
                    qty_left = date_totals[ship_date]
                    if qty_left <= 0:
                        continue

                    while qty_left > 0 and bucket_idx < len(demand_buckets):
                        rem = remaining_demands[bucket_idx]
                        if rem <= 0:
                            bucket_idx += 1
                            continue
                        take = rem if rem <= qty_left else qty_left
                        bucket = demand_buckets[bucket_idx]
                        alloc_key = (bucket.source_order_no, ship_date)
                        alloc_map[alloc_key] += take
                        remaining_demands[bucket_idx] -= take
                        qty_left -= take
                        if remaining_demands[bucket_idx] <= 0:
                            bucket_idx += 1

                    # 需要超過分は最終バケットへ保持
                    if qty_left > 0:
                        last_bucket = demand_buckets[-1]
                        alloc_key = (last_bucket.source_order_no, ship_date)
                        alloc_map[alloc_key] += qty_left

                # 書き戻し（既存行更新/不足行作成/不要行ゼロ化）
                bucket_meta = {}
                for b in demand_buckets:
                    if b.source_order_no not in bucket_meta:
                        bucket_meta[b.source_order_no] = {
                            'order_type': b.order_type,
                            'order_line_id': b.order_line_id,
                        }

                new_keys = set(alloc_map.keys())
                all_candidate_keys = set(existing_by_key.keys()) | new_keys

                for source_order_no, ship_date in all_candidate_keys:
                    new_delivery = alloc_map.get((source_order_no, ship_date), Decimal('0'))
                    adj = existing_by_key.get((source_order_no, ship_date))

                    if adj:
                        if adj.delivery_qty != new_delivery:
                            adj.delivery_qty = new_delivery
                            adj.updated_by = user
                            adj.updated_at = now
                            adj.save(update_fields=['delivery_qty', 'updated_by', 'updated_at'])
                            updated_count += 1
                        continue

                    if new_delivery <= 0:
                        continue

                    meta = bucket_meta.get(source_order_no, {})
                    KubotaSakaiDueAdjustment.objects.create(
                        product_code=product_code,
                        ship_to_code=ship_to_code,
                        source_order_no=source_order_no,
                        order_type=meta.get('order_type') or ('FIRM' if source_order_no else 'FORECAST'),
                        due_date=ship_date,
                        demand_qty=Decimal('0'),
                        delivery_qty=new_delivery,
                        remaining_qty=Decimal('0'),
                        order_line_id=meta.get('order_line_id'),
                        updated_by=user,
                        updated_at=now,
                    )
                    updated_count += 1
                if allow_due_plan_lock_update:
                    for target_date in sorted(touched_dates):
                        before_total = before_date_totals.get(target_date, Decimal('0'))
                        after_total = date_totals.get(target_date, Decimal('0'))
                        if before_total == after_total:
                            continue
                        if _create_due_adjustment_change_log(
                            product_code=product_code,
                            ship_to_code=ship_to_code,
                            due_date=target_date,
                            before_qty=before_total,
                            after_qty=after_total,
                            reason=change_reason,
                            user=user,
                            line=log_line,
                            process=log_process,
                            product_cache=product_cache,
                        ):
                            change_log_count += 1

            # 残量再計算
            _recalculate_remaining_for_groups(affected_groups)

        return Response({
            'updated': updated_count,
            'affected_groups': len(affected_groups),
            'change_logs': change_log_count,
        })

    # ========== get_contacts ==========
    @action(detail=False, methods=['get'])
    def get_contacts(self, request):
        contacts = Contact.objects.filter(
            contact_type='納期調整',
            is_active=True,
        ).order_by('display_order', 'id')
        result = []
        for c in contacts:
            name = c.company_name or ''
            if c.department:
                name += f' {c.department}'
            if c.contact_person:
                name += f' {c.contact_person}'
            result.append({
                'id': c.id,
                'display_name': name.strip(),
                'email': c.email,
            })
        return Response(result)

    # ========== send_email ==========
    @action(detail=False, methods=['post'])
    def send_email(self, request):
        to_emails = request.data.get('to_emails', [])
        cc_emails = request.data.get('cc_emails', [])
        subject = str(request.data.get('subject') or '').strip()
        body = str(request.data.get('body') or '').strip()

        if not to_emails:
            return Response(
                {'detail': '宛先を指定してください。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not subject:
            return Response(
                {'detail': '件名を入力してください。'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_id = request.user.id if request.user and request.user.is_authenticated else None
        email_service = EmailService()
        smtp_config = email_service.get_smtp_config(user_id)
        if not smtp_config:
            return Response(
                {'detail': 'SMTP設定が見つかりません。管理者に連絡してください。'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart()
            msg['From'] = smtp_config['user']
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            recipients = list(to_emails)
            if cc_emails:
                recipients.extend(cc_emails)

            with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
                server.starttls()
                server.login(smtp_config['user'], smtp_config['password'])
                server.send_message(msg, to_addrs=recipients)

            return Response({
                'success': True,
                'message': f'メールを送信しました（宛先: {len(to_emails)}件）',
            })

        except smtplib.SMTPAuthenticationError:
            return Response(
                {'detail': 'SMTP認証エラー: ユーザー名またはパスワードが正しくありません。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {'detail': f'メール送信エラー: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def _recalculate_remaining_for_groups(groups):
    """(product_code, ship_to_code) のグループごとに、全注番合算で残量を時系列再計算。
    残量 = 累積(納入) - 累積(受注)  ※LT考慮なし、注番をまたいで合算
    締め日以前の行はremaining_qtyを変更しない。
    """
    lock_date = _get_lock_date()

    for product_code, ship_to_code in groups:
        all_rows = list(KubotaSakaiDueAdjustment.objects.filter(
            product_code=product_code,
            ship_to_code=ship_to_code or None,
        ).order_by('due_date', 'source_order_no'))

        if not all_rows:
            continue

        # 日付ごとに全注番の demand/delivery を合算
        date_demand = defaultdict(lambda: Decimal('0'))
        date_delivery = defaultdict(lambda: Decimal('0'))
        for row in all_rows:
            date_demand[row.due_date] += row.demand_qty
            date_delivery[row.due_date] += row.delivery_qty

        all_dates = sorted(set(date_demand.keys()) | set(date_delivery.keys()))
        remaining_at_date = {}
        cum_demand = Decimal('0')
        cum_delivery = Decimal('0')
        for d in all_dates:
            cum_demand += date_demand.get(d, Decimal('0'))
            cum_delivery += date_delivery.get(d, Decimal('0'))
            remaining_at_date[d] = cum_delivery - cum_demand

        # 各行に残量をセット（締め日以前はスキップ）
        for row in all_rows:
            if lock_date and row.due_date <= lock_date:
                continue
            new_remaining = remaining_at_date.get(row.due_date, Decimal('0'))
            if row.remaining_qty != new_remaining:
                row.remaining_qty = new_remaining
                row.save(update_fields=['remaining_qty'])
