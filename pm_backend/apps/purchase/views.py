from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import re

from django.db.models import Max, Sum
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from masters.models import BOMItem, Calendar, CalendarDay, Line, Process, Product, Supplier
from orders.utils.calendar_utils import get_business_today
from production.models_process_realtime import ProcessRealtimeRecord
from production.models_line_backlog import LineBacklog
from production.models_line_plan import LinePlan
from production.serializers import LineBacklogSerializer
from production.serializers_process_realtime import (
    ProcessRealtimeCreateSerializer,
    resolve_workday_date_for_process,
)
from production.inventory.inventory_calculator import (
    recalculate_inventory_for_line,
)

from .models import EngineeringChangeCase, EngineeringChangePart, PurchasePlanLockSetting
from .serializers import PurchasePlanLockSettingSerializer


def _normalize_product_code(text: str) -> str:
    base = str(text or '').strip().upper()
    return re.sub(r'[^A-Z0-9]', '', base)


def _resolve_product_by_code(code: str):
    raw = str(code or '').strip()
    if not raw:
        return None

    # 1. 完全一致
    exact = Product.objects.filter(product_code=raw).first()
    if exact:
        return exact

    # 2. 前方一致/部分一致
    prefix = Product.objects.filter(product_code__istartswith=raw).order_by('product_code').first()
    if prefix:
        return prefix
    partial = Product.objects.filter(product_code__icontains=raw).order_by('product_code').first()
    if partial:
        return partial

    # 3. 記号除去した一致（例: YD40002386-28 と YD4000238628）
    target = _normalize_product_code(raw)
    if not target:
        return None
    for p in Product.objects.only('id', 'product_code', 'product_name'):
        if _normalize_product_code(p.product_code) == target:
            return p
    return None


def _resolve_purchase_line(supplier: Supplier | None):
    if not supplier:
        return None
    line_code = supplier.supplier_code
    line_name = f"仕入:{supplier.supplier_code} {supplier.supplier_name}"
    if len(line_name) > 50:
        line_name = line_name[:50]
    line_obj, created = Line.objects.get_or_create(
        line_code=line_code,
        defaults={
            'line_name': line_name,
            'line_type': 'PURCHASE',
            'is_active': True,
        }
    )
    if not created and line_obj.line_type != 'PURCHASE':
        line_obj.line_type = 'PURCHASE'
        line_obj.save(update_fields=['line_type'])
    return line_obj


def _resolve_inventory_effective_start_date(line_id: int, requested_start_date: date, end_date: date) -> date:
    line_obj = Line.objects.filter(id=line_id).first()
    calendar_id = getattr(line_obj, 'calendar_id', None) or Calendar.objects.filter(
        calendar_code='daiso'
    ).values_list('id', flat=True).first()
    workday_cache = {}

    def is_working_day(target_date):
        if not calendar_id:
            return target_date.weekday() < 5
        if target_date in workday_cache:
            return workday_cache[target_date]
        cal = CalendarDay.objects.filter(
            calendar_id=calendar_id,
            target_date=target_date,
        ).first()
        is_work = cal.is_working_day if cal is not None else target_date.weekday() < 5
        workday_cache[target_date] = is_work
        return is_work

    def get_prev_working_day(target_date):
        prev_date = target_date - timedelta(days=1)
        while not is_working_day(prev_date):
            prev_date = prev_date - timedelta(days=1)
        return prev_date

    def shift_working_days(target_date, days):
        if not days:
            return target_date
        if not calendar_id:
            return target_date + timedelta(days=days)
        step = 1 if days > 0 else -1
        remaining = abs(int(days))
        current = target_date
        while remaining > 0:
            current = current + timedelta(days=step)
            if is_working_day(current):
                remaining -= 1
        return current

    business_today = get_business_today()
    stock_start_dt = get_prev_working_day(get_prev_working_day(business_today))
    product_ids_for_line = list(
        LineBacklog.objects.filter(
            line_id=line_id,
            plan_date__lte=end_date,
        ).values_list('product_id', flat=True).distinct()
    )
    max_lt = 0
    if product_ids_for_line:
        max_lt = BOMItem.objects.filter(
            bom__is_active=True,
            child_product_id__in=product_ids_for_line,
        ).aggregate(v=Max('lead_time_days'))['v'] or 0
    planned_progress_start_dt = shift_working_days(business_today, -(int(max_lt) + 1))
    return min(requested_start_date, stock_start_dt, planned_progress_start_dt)


def _is_working_day(calendar_id, target_date, workday_cache):
    if not calendar_id:
        return target_date.weekday() < 5
    cache = workday_cache.setdefault(calendar_id, {})
    if target_date in cache:
        return cache[target_date]
    cal = CalendarDay.objects.filter(
        calendar_id=calendar_id,
        target_date=target_date,
    ).first()
    is_work = cal.is_working_day if cal is not None else target_date.weekday() < 5
    cache[target_date] = is_work
    return is_work


def _shift_business_days(calendar_id, target_date, days, workday_cache):
    if not days:
        if not calendar_id:
            return target_date
        if _is_working_day(calendar_id, target_date, workday_cache):
            return target_date
        current = target_date
        while True:
            current = current - timedelta(days=1)
            if _is_working_day(calendar_id, current, workday_cache):
                return current

    step = -1 if days > 0 else 1
    remaining = abs(int(days))
    current = target_date
    while remaining > 0:
        current = current + timedelta(days=step)
        if _is_working_day(calendar_id, current, workday_cache):
            remaining -= 1
    return current


class PurchaseActualCandidatesView(APIView):
    def get(self, request):
        product_code = (request.query_params.get('product_code') or '').strip()
        if not product_code:
            return Response({'detail': 'product_code is required'}, status=status.HTTP_400_BAD_REQUEST)

        product = _resolve_product_by_code(product_code)
        if not product:
            return Response({'detail': f'product not found: {product_code}'}, status=status.HTTP_404_NOT_FOUND)

        bom_items = list(
            BOMItem.objects.filter(child_product_id=product.id).select_related('supplier', 'line', 'process')
        )
        purchase_like = [
            item for item in bom_items
            if str(item.sourcing_type or '').upper() in ('BUY', 'SUBCON') or item.supplier_id
        ]

        process_purchase = (
            Process.objects.filter(process_code='PURCHASE').first()
            or Process.objects.filter(process_name__icontains='購買').first()
        )
        line_by_name = {str(l.line_name or '').strip(): l for l in Line.objects.filter(is_active=True)}
        line_by_code = {str(l.line_code or '').strip(): l for l in Line.objects.filter(is_active=True)}

        candidates = []
        for idx, item in enumerate(purchase_like):
            supplier = item.supplier
            if not supplier:
                continue
            # 在庫/残量一覧と同じ仕入ライン解決を使う
            line = _resolve_purchase_line(supplier)
            if not line:
                line = item.line
            if not line:
                line = line_by_name.get(str(supplier.supplier_name or '').strip()) or line_by_code.get(str(supplier.supplier_code or '').strip())
            process = item.process or process_purchase
            if not process and line:
                process = Process.objects.filter(
                    line_id=line.id, process_code='PURCHASE'
                ).first()
            if not process and line:
                process = Process.objects.filter(line_id=line.id).order_by('id').first()

            candidates.append({
                'key': f'{item.id}-{idx}',
                'step_no': int(item.id or 0),
                'supplier_id': supplier.id,
                'supplier_code': supplier.supplier_code,
                'supplier_name': supplier.supplier_name,
                'line_id': line.id if line else None,
                'line_code': line.line_code if line else supplier.supplier_code,
                'line_name': line.line_name if line else supplier.supplier_name,
                'process_id': process.id if process else None,
                'process_code': process.process_code if process else 'PURCHASE',
            })

        # 重複候補を圧縮
        uniq = {}
        for c in candidates:
            key = (c['supplier_id'], c['line_id'], c['process_id'])
            if key not in uniq:
                uniq[key] = c

        result = list(uniq.values())
        return Response({
            'product': {
                'id': product.id,
                'product_code': product.product_code,
                'product_name': product.product_name,
            },
            'candidates': result,
        })


class PurchaseActualRegisterView(APIView):
    def post(self, request):
        product_code = (request.data.get('product_code') or '').strip()
        if not product_code:
            return Response({'detail': 'product_code is required'}, status=status.HTTP_400_BAD_REQUEST)

        qty_raw = request.data.get('qty')
        try:
            qty = Decimal(str(qty_raw))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'detail': 'qty must be a number'}, status=status.HTTP_400_BAD_REQUEST)
        if qty <= 0:
            return Response({'detail': 'qty must be > 0'}, status=status.HTTP_400_BAD_REQUEST)

        process_id = request.data.get('process_id')
        supplier_id = request.data.get('supplier_id')
        line_id = request.data.get('line_id')

        supplier_obj = Supplier.objects.filter(id=supplier_id).first() if supplier_id else None
        canonical_line = _resolve_purchase_line(supplier_obj) if supplier_obj else None
        effective_line_id = canonical_line.id if canonical_line else line_id

        process_obj = None
        if process_id:
            process_obj = Process.objects.filter(id=process_id).first()

        if not process_obj and effective_line_id:
            process_obj = (
                Process.objects.filter(line_id=effective_line_id, process_code='PURCHASE').first()
                or Process.objects.filter(line_id=effective_line_id).order_by('id').first()
            )

        if not process_obj and canonical_line:
            process_obj = (
                Process.objects.filter(line_id=canonical_line.id, process_code='PURCHASE').first()
                or Process.objects.filter(line_id=canonical_line.id).order_by('id').first()
            )

        if not process_obj:
            process_obj = (
                Process.objects.filter(process_code='PURCHASE').first()
                or Process.objects.filter(process_name__icontains='購買').first()
            )
        if not process_obj:
            return Response({'detail': 'purchase process not found'}, status=status.HTTP_400_BAD_REQUEST)

        product = _resolve_product_by_code(product_code)
        if not product:
            return Response({'detail': f'product not found: {product_code}'}, status=status.HTTP_404_NOT_FOUND)

        payload = {
            'process_id': process_obj.id,
            'product_id': product.id,
            'record_type': 'PRODUCTION',
            'qty': qty,
            'operator_name': (request.data.get('operator_name') or '').strip(),
            'remarks': (request.data.get('remarks') or '').strip(),
            'event_data': {
                'source': 'PURCHASE_ACTUAL_INPUT',
                'arrival_date': (request.data.get('arrival_date') or '').strip(),
                'supplier_id': request.data.get('supplier_id'),
            },
        }

        serializer = ProcessRealtimeCreateSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        record = serializer.save()

        # 仕入れ在庫画面は購入先ライン単位で参照するため、
        # process.line と選択ラインが異なる場合は選択ラインへ actual を補正反映する。
        target_line_id = None
        try:
            target_line_id = int(effective_line_id) if effective_line_id else None
        except (TypeError, ValueError):
            target_line_id = None

        arrival_date_text = (request.data.get('arrival_date') or '').strip()
        target_date = record.timestamp.date()
        if arrival_date_text:
            try:
                target_date = date.fromisoformat(arrival_date_text.replace('/', '-'))
            except ValueError:
                target_date = record.timestamp.date()

        now = record.timestamp
        if getattr(now, 'tzinfo', None):
            from django.utils import timezone
            now = timezone.localtime(now).replace(tzinfo=None)
        serializer_plan_date = resolve_workday_date_for_process(process_obj, now)

        if target_line_id and (process_obj.line_id != target_line_id or target_date != serializer_plan_date):
            backlog, _ = LineBacklog.objects.get_or_create(
                line_id=target_line_id,
                process_id=process_obj.id,
                product_id=product.id,
                plan_date=target_date,
                sequence_no=0,
                defaults={
                    'order_qty': 0,
                    'plan_qty': 0,
                    'actual_qty': 0,
                    'stock_qty': 0,
                    'planned_stock_qty': 0,
                    'adjust_qty': 0,
                    'scrap_qty': 0,
                    'actual_shipment_qty': 0,
                }
            )
            backlog.actual_qty = int(backlog.actual_qty or 0) + int(qty)
            backlog.save(update_fields=['actual_qty'])

        return Response({'id': record.id, 'detail': 'created'}, status=status.HTTP_201_CREATED)


class PurchaseActualProgressView(APIView):
    def get(self, request):
        product_code = (request.query_params.get('product_code') or '').strip()
        start_date_text = (request.query_params.get('start_date') or '').strip()
        line_id = request.query_params.get('line_id')
        process_id = request.query_params.get('process_id')

        if not product_code:
            return Response({'detail': 'product_code is required'}, status=status.HTTP_400_BAD_REQUEST)

        product = _resolve_product_by_code(product_code)
        if not product:
            return Response({'detail': f'product not found: {product_code}'}, status=status.HTTP_404_NOT_FOUND)

        start_date = date.today()
        if start_date_text:
            try:
                start_date = date.fromisoformat(start_date_text.replace('/', '-'))
            except ValueError:
                return Response({'detail': 'start_date must be YYYY-MM-DD or YYYY/MM/DD'}, status=status.HTTP_400_BAD_REQUEST)
        end_date = start_date + timedelta(days=17)

        qs = LineBacklog.objects.filter(
            product_id=product.id,
            plan_date__gte=start_date,
            plan_date__lte=end_date,
        )
        if line_id:
            qs = qs.filter(line_id=line_id)
        if process_id:
            qs = qs.filter(process_id=process_id)

        rows_by_date = {}
        for obj in qs:
            key = obj.plan_date.isoformat()
            if key not in rows_by_date:
                rows_by_date[key] = {
                    'date': key,
                    'plan_demand': 0,
                    'actual_demand': 0,
                    'forecast': 0,
                    'firm': 0,
                    'inbound': 0,
                    'adjust': 0,
                    'stock': 0,
                    'planned_stock': 0,
                    'progress': 0,
                    'planned_progress': 0,
                }
            rows_by_date[key]['plan_demand'] += int(obj.demand_qty_plan or 0)
            rows_by_date[key]['actual_demand'] += int(obj.order_qty or 0)
            # 購買ラインでは order_qty を確定需要として扱う
            # 内示は別系統が未整備のため現時点では0固定
            rows_by_date[key]['firm'] += int(obj.order_qty or 0)
            rows_by_date[key]['forecast'] += 0
            rows_by_date[key]['inbound'] += int(obj.actual_qty or 0)
            rows_by_date[key]['adjust'] += int(obj.adjust_qty or 0)
            rows_by_date[key]['stock'] += int(obj.stock_qty or 0)
            rows_by_date[key]['planned_stock'] += int(obj.planned_stock_qty or 0)
            rows_by_date[key]['progress'] += int(obj.progress_qty or 0)
            rows_by_date[key]['planned_progress'] += int(obj.planned_progress_qty or 0)

        rows = []
        for i in range(18):
            d = start_date + timedelta(days=i)
            key = d.isoformat()
            rows.append(rows_by_date.get(key, {
                'date': key,
                'plan_demand': 0,
                'actual_demand': 0,
                'forecast': 0,
                'firm': 0,
                'inbound': 0,
                'adjust': 0,
                'stock': 0,
                'planned_stock': 0,
                'progress': 0,
                'planned_progress': 0,
            }))

        month_forecast = sum(r['forecast'] for r in rows)
        month_firm = sum(r['firm'] for r in rows)
        month_inbound = sum(r['inbound'] for r in rows)

        return Response({
            'product': {
                'id': product.id,
                'product_code': product.product_code,
                'product_name': product.product_name,
            },
            'summary': {
                'forecast': month_forecast,
                'firm': month_firm,
                'inbound': month_inbound,
            },
            'rows': rows,
        })


class PurchaseActualInquiryView(APIView):
    def get(self, request):
        start_date_text = (request.query_params.get('start_date') or '').strip()
        end_date_text = (request.query_params.get('end_date') or '').strip()
        product_code = (request.query_params.get('product_code') or '').strip()
        supplier_id = request.query_params.get('supplier_id')

        qs = ProcessRealtimeRecord.objects.filter(
            record_type='PRODUCTION',
            event_data__source='PURCHASE_ACTUAL_INPUT',
        ).select_related('product', 'process')

        if start_date_text:
            try:
                start_date = date.fromisoformat(start_date_text.replace('/', '-'))
                qs = qs.filter(timestamp__date__gte=start_date)
            except ValueError:
                return Response({'detail': 'start_date is invalid'}, status=status.HTTP_400_BAD_REQUEST)
        if end_date_text:
            try:
                end_date = date.fromisoformat(end_date_text.replace('/', '-'))
                qs = qs.filter(timestamp__date__lte=end_date)
            except ValueError:
                return Response({'detail': 'end_date is invalid'}, status=status.HTTP_400_BAD_REQUEST)
        if product_code:
            qs = qs.filter(product_code__icontains=product_code)
        if supplier_id:
            qs = qs.filter(event_data__supplier_id=int(supplier_id))

        rows = []
        for rec in qs.order_by('-timestamp', '-id')[:2000]:
            supplier_name = ''
            supplier_code = ''
            supplier_raw = (rec.event_data or {}).get('supplier_id')
            try:
                supplier = Supplier.objects.filter(id=int(supplier_raw)).first() if supplier_raw else None
            except (TypeError, ValueError):
                supplier = None
            if supplier:
                supplier_name = supplier.supplier_name or ''
                supplier_code = supplier.supplier_code or ''

            rows.append({
                'id': rec.id,
                'delivery_date': rec.timestamp.date().isoformat(),
                'product_code': rec.product_code or '',
                'product_name': rec.product_name or '',
                'supplier': f'{supplier_code} - {supplier_name}'.strip(' -'),
                'qty': float(rec.qty or 0),
                'operator_name': rec.operator_name or '',
            })

        return Response(rows)


class PurchaseActualBulkItemsView(APIView):
    """購入先と納入日から、その日の計画品目一覧を返す"""
    def get(self, request):
        supplier_id = request.query_params.get('supplier_id')
        plan_date_text = (request.query_params.get('plan_date') or '').strip()

        supplier = Supplier.objects.filter(id=supplier_id).first() if supplier_id else None
        if not supplier:
            return Response({'items': [], 'line_id': None, 'line_name': ''})

        line = _resolve_purchase_line(supplier)
        if not line:
            return Response({'items': [], 'line_id': None, 'line_name': ''})

        plan_date = date.today()
        if plan_date_text:
            try:
                plan_date = date.fromisoformat(plan_date_text.replace('/', '-'))
            except ValueError:
                pass

        process = (
            Process.objects.filter(line=line, process_code='PURCHASE').first()
            or Process.objects.filter(line=line).order_by('id').first()
        )

        # 仕入計画は LineBacklog.plan_qty (sequence_no=0) に格納されている
        backlogs = (
            LineBacklog.objects.filter(
                line__line_code=supplier.supplier_code,
                plan_date=plan_date,
                sequence_no=0,
                plan_qty__gt=0,
            )
            .select_related('product')
            .order_by('product__product_code')
        )

        product_map = {}
        for b in backlogs:
            if not b.product:
                continue
            pid = b.product_id
            if pid not in product_map:
                product_map[pid] = {
                    'product_id': pid,
                    'product_code': b.product.product_code,
                    'product_name': b.product.product_name,
                    'process_id': process.id if process else None,
                    'line_id': line.id,
                    'plan_qty': 0,
                    'actual_qty': 0,
                }
            product_map[pid]['plan_qty'] += int(b.plan_qty or 0)
            product_map[pid]['actual_qty'] += int(b.actual_qty or 0)

        items = sorted(product_map.values(), key=lambda x: x['product_code'])

        return Response({
            'line_id': line.id,
            'line_code': line.line_code,
            'line_name': line.line_name,
            'process_id': process.id if process else None,
            'items': items,
        })


class PurchasePlanLockSettingView(APIView):
    def get(self, request):
        setting = PurchasePlanLockSetting.objects.first()
        if not setting:
            user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
            setting = PurchasePlanLockSetting.objects.create(lock_days=0, updated_by=user)
        serializer = PurchasePlanLockSettingSerializer(setting)
        return Response(serializer.data)


class EngineeringChangeView(APIView):
    def get(self, request):
        today = date.today()
        default_calendar_id = Calendar.objects.filter(
            calendar_code='daiso'
        ).values_list('id', flat=True).first()
        parts = (
            EngineeringChangePart.objects
            .select_related('case__final_product', 'old_part', 'new_part')
            .order_by('-id')
        )
        old_part_ids = list({part.old_part_id for part in parts})
        parent_map = {}
        if old_part_ids:
            bom_items = (
                BOMItem.objects.filter(child_product_id__in=old_part_ids, bom__is_active=True)
                .select_related('bom__parent_product')
            )
            for bi in bom_items:
                parent = bi.bom.parent_product
                if not parent:
                    continue
                key = bi.child_product_id
                if key not in parent_map:
                    parent_map[key] = {}
                parent_map[key][parent.product_code] = {
                    'product_code': parent.product_code,
                    'product_name': parent.product_name,
                }

        workday_cache = {}
        lt_days_cache = {}
        rows = []
        for part in parts:
            # 完成品（案件）切替日を正とし、旧データ互換で部品切替日をフォールバック
            switch_date = part.case.switch_date or part.switch_date or today
            start_date = today
            display_end_date = switch_date if switch_date >= today else today

            base_qs = LineBacklog.objects.filter(
                product=part.old_part,
                plan_date__gte=start_date,
                plan_date__lte=display_end_date,
            )
            has_prod = base_qs.filter(line__line_type='PROD').exists()
            target_line_type = 'PROD' if has_prod else 'PURCHASE'
            purchase_plan_qty = base_qs.filter(line__line_type='PURCHASE').aggregate(v=Sum('plan_qty'))['v'] or 0
            production_plan_qty = base_qs.filter(line__line_type='PROD').aggregate(v=Sum('plan_qty'))['v'] or 0
            target_base_qs = base_qs.filter(line__line_type=target_line_type)

            lt_sample = (
                target_base_qs.select_related('product', 'line', 'process').order_by('plan_date').first()
                or LineBacklog.objects.filter(
                    product=part.old_part,
                    line__line_type=target_line_type,
                ).select_related('product', 'line', 'process').order_by('plan_date').first()
            )
            component_lt_days = 0
            component_switch_date = switch_date
            if lt_sample:
                lt_key = (lt_sample.product_id, lt_sample.line_id, lt_sample.process_id)
                if lt_key not in lt_days_cache:
                    lt_serializer = LineBacklogSerializer(instance=lt_sample)
                    lt_days_cache[lt_key] = int(lt_serializer.get_total_lt_days(lt_sample) or 0)
                component_lt_days = int(lt_days_cache[lt_key] or 0)
                calendar_id = getattr(lt_sample.line, 'calendar_id', None) or default_calendar_id
                component_switch_date = _shift_business_days(
                    calendar_id,
                    switch_date,
                    component_lt_days,
                    workday_cache,
                )

            component_end_date = component_switch_date if component_switch_date >= today else today
            required_base_qs = LineBacklog.objects.filter(
                product=part.old_part,
                plan_date__gte=start_date,
                plan_date__lte=component_end_date,
                line__line_type=target_line_type,
            )
            required_until_switch_qty = required_base_qs.aggregate(v=Sum('order_qty'))['v'] or 0
            # 購買BACKLOG運用で order_qty が未計算/0 の場合に備えて plan_qty をフォールバック
            if required_until_switch_qty == 0:
                required_until_switch_qty = required_base_qs.aggregate(v=Sum('plan_qty'))['v'] or 0

            today_qs = LineBacklog.objects.filter(product=part.old_part, plan_date=today)
            stock_qty = today_qs.aggregate(v=Sum('stock_qty'))['v'] or 0
            progress_qty = today_qs.aggregate(v=Sum('progress_qty'))['v'] or 0
            switch_day_prod_qs = LineBacklog.objects.filter(
                product=part.old_part,
                plan_date=component_switch_date,
                line__line_type=target_line_type,
            )
            switch_prod_planned_stock_qty = switch_day_prod_qs.aggregate(v=Sum('planned_stock_qty'))['v'] or 0
            switch_prod_progress_qty = switch_day_prod_qs.aggregate(v=Sum('progress_qty'))['v'] or 0
            switch_prod_planned_progress_qty = switch_day_prod_qs.aggregate(v=Sum('planned_progress_qty'))['v'] or 0
            # LT反映日に行がない場合、基準日以前の直近バックログ値を採用
            if (
                switch_prod_planned_stock_qty == 0
                and switch_prod_progress_qty == 0
                and switch_prod_planned_progress_qty == 0
            ):
                latest_qs = (
                    LineBacklog.objects.filter(
                        product=part.old_part,
                        plan_date__lte=component_switch_date,
                        line__line_type=target_line_type,
                    )
                    .order_by('-plan_date')
                )
                latest = latest_qs.first()
                if latest:
                    latest_day_qs = latest_qs.filter(plan_date=latest.plan_date)
                    switch_prod_planned_stock_qty = latest_day_qs.aggregate(v=Sum('planned_stock_qty'))['v'] or 0
                    switch_prod_progress_qty = latest_day_qs.aggregate(v=Sum('progress_qty'))['v'] or 0
                    switch_prod_planned_progress_qty = latest_day_qs.aggregate(v=Sum('planned_progress_qty'))['v'] or 0

            required = int(part.required_qty_after_eol or 0)
            parent_products = list((parent_map.get(part.old_part_id) or {}).values())
            parent_products.sort(key=lambda x: x['product_code'])
            rows.append({
                'id': part.id,
                'case_id': part.case_id,
                'case_code': part.case.case_code or f'EC-{part.case_id:06d}',
                'case_name': part.case.case_name or '',
                'final_product_code': part.case.final_product.product_code if part.case.final_product else '',
                'final_product_name': part.case.final_product.product_name if part.case.final_product else '',
                'switch_date': switch_date,
                'component_switch_date': component_switch_date,
                'component_lt_days': component_lt_days,
                'old_part_code': part.old_part.product_code,
                'old_part_name': part.old_part.product_name,
                'parent_products': parent_products,
                'parent_products_text': ', '.join([f"{x['product_code']} {x['product_name']}" for x in parent_products]),
                'new_part_code': part.new_part.product_code if part.new_part else '',
                'required_qty_after_eol': required,
                'purchase_plan_qty': purchase_plan_qty,
                'production_plan_qty': production_plan_qty,
                'required_until_switch_qty': required_until_switch_qty,
                'switch_prod_planned_stock_qty': switch_prod_planned_stock_qty,
                'switch_prod_progress_qty': switch_prod_progress_qty,
                'switch_prod_planned_progress_qty': switch_prod_planned_progress_qty,
                'stock_qty': stock_qty,
                'progress_qty': progress_qty,
                'excess_purchase_qty': purchase_plan_qty - required_until_switch_qty,
                'excess_production_qty': production_plan_qty - required,
            })
        return Response(rows)

    def post(self, request):
        final_product_code = (request.data.get('final_product_code') or '').strip()
        parts = request.data.get('parts') or []
        if not isinstance(parts, list) or not parts:
            return Response({'detail': 'parts is required'}, status=status.HTTP_400_BAD_REQUEST)

        final_product = None
        if final_product_code:
            try:
                final_product = Product.objects.get(product_code=final_product_code)
            except Product.DoesNotExist:
                return Response({'detail': f'final product not found: {final_product_code}'}, status=status.HTTP_400_BAD_REQUEST)

        case = EngineeringChangeCase.objects.create(
            case_name=(request.data.get('case_name') or '').strip() or None,
            final_product=final_product,
            switch_date=request.data.get('switch_date') or None,
            note=(request.data.get('note') or '').strip() or None,
        )
        case.case_code = f'EC-{case.id:06d}'
        case.save(update_fields=['case_code', 'updated_at'])

        created = 0
        for part in parts:
            old_code = (part.get('old_part_code') or '').strip()
            if not old_code:
                continue
            try:
                old_part = Product.objects.get(product_code=old_code)
            except Product.DoesNotExist:
                continue

            new_part = None
            new_code = (part.get('new_part_code') or '').strip()
            if new_code:
                new_part = Product.objects.filter(product_code=new_code).first()

            EngineeringChangePart.objects.create(
                case=case,
                switch_date=part.get('switch_date') or None,
                old_part=old_part,
                new_part=new_part,
                required_qty_after_eol=int(part.get('required_qty_after_eol') or 0),
                remark=(part.get('remark') or '').strip() or None,
            )
            created += 1

        if created == 0:
            case.delete()
            return Response({'detail': 'valid parts not found'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {'detail': 'created', 'case_id': case.id, 'case_code': case.case_code, 'created_parts': created},
            status=status.HTTP_201_CREATED
        )


class EngineeringChangePartDetailView(APIView):
    def put(self, request, pk: int):
        part = EngineeringChangePart.objects.select_related('case').filter(pk=pk).first()
        if not part:
            return Response(status=status.HTTP_404_NOT_FOUND)

        case_update_fields = []
        if 'final_product_code' in request.data:
            final_product_code = (request.data.get('final_product_code') or '').strip()
            if final_product_code:
                final_product = Product.objects.filter(product_code=final_product_code).first()
                if not final_product:
                    return Response({'detail': f'final product not found: {final_product_code}'}, status=status.HTTP_400_BAD_REQUEST)
                part.case.final_product = final_product
            else:
                part.case.final_product = None
            case_update_fields.append('final_product')
        if 'case_name' in request.data:
            part.case.case_name = (request.data.get('case_name') or '').strip() or None
            case_update_fields.append('case_name')
        if 'switch_date' in request.data:
            part.case.switch_date = request.data.get('switch_date') or None
            case_update_fields.append('switch_date')

        if case_update_fields:
            part.case.save(update_fields=[*case_update_fields, 'updated_at'])

        part_update_fields = ['updated_at']
        old_part_code = (request.data.get('old_part_code') or '').strip()
        if old_part_code:
            old_part = Product.objects.filter(product_code=old_part_code).first()
            if not old_part:
                return Response({'detail': f'old part not found: {old_part_code}'}, status=status.HTTP_400_BAD_REQUEST)
            part.old_part = old_part
            part_update_fields.append('old_part')

        if 'new_part_code' in request.data:
            new_part_code = (request.data.get('new_part_code') or '').strip()
            new_part = Product.objects.filter(product_code=new_part_code).first() if new_part_code else None
            if new_part_code and not new_part:
                return Response({'detail': f'new part not found: {new_part_code}'}, status=status.HTTP_400_BAD_REQUEST)
            part.new_part = new_part
            part_update_fields.append('new_part')

        if 'required_qty_after_eol' in request.data:
            part.required_qty_after_eol = int(request.data.get('required_qty_after_eol') or 0)
            part_update_fields.append('required_qty_after_eol')
        # 部品単位の切替日を扱いたい場合だけ明示キーで更新する
        if 'part_switch_date' in request.data:
            part.switch_date = request.data.get('part_switch_date') or None
            part_update_fields.append('switch_date')

        part.save(update_fields=part_update_fields)
        return Response({'detail': 'updated'})

    def delete(self, request, pk: int):
        part = EngineeringChangePart.objects.filter(pk=pk).first()
        if not part:
            return Response(status=status.HTTP_404_NOT_FOUND)
        case_id = part.case_id
        part.delete()
        if not EngineeringChangePart.objects.filter(case_id=case_id).exists():
            EngineeringChangeCase.objects.filter(pk=case_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def post(self, request):
        raw_days = request.data.get('lock_days')
        try:
            lock_days = int(raw_days)
        except (TypeError, ValueError):
            return Response({'detail': 'lock_days must be integer'}, status=status.HTTP_400_BAD_REQUEST)
        if lock_days < 0:
            return Response({'detail': 'lock_days must be >= 0'}, status=status.HTTP_400_BAD_REQUEST)

        setting = PurchasePlanLockSetting.objects.first()
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        if not setting:
            setting = PurchasePlanLockSetting.objects.create(lock_days=lock_days, updated_by=user)
        else:
            setting.lock_days = lock_days
            setting.updated_by = user
            setting.save(update_fields=['lock_days', 'updated_at', 'updated_by'])

        serializer = PurchasePlanLockSettingSerializer(setting)
        return Response(serializer.data)


class EngineeringChangeCaseRecalculateView(APIView):
    def post(self, request, case_id: int):
        today = get_business_today()
        case = EngineeringChangeCase.objects.filter(pk=case_id).first()
        if not case:
            return Response({'detail': 'case not found or no parts'}, status=status.HTTP_404_NOT_FOUND)

        parts = list(
            EngineeringChangePart.objects
            .select_related('old_part')
            .filter(case_id=case_id)
        )
        if not parts:
            return Response({'detail': 'case not found or no parts'}, status=status.HTTP_404_NOT_FOUND)

        switch_dates = [p.switch_date for p in parts if p.switch_date]
        end_date = case.switch_date or (max(switch_dates) if switch_dates else today)
        if end_date < today:
            end_date = today

        line_products_map = {}
        target_product_ids = set()
        for part in parts:
            product_id = part.old_part_id
            target_product_ids.add(product_id)
            line_ids = set()
            if getattr(part.old_part, 'line_id', None):
                line_ids.add(part.old_part.line_id)
            backlog_line_ids = (
                LineBacklog.objects.filter(
                    product_id=product_id,
                    plan_date__gte=today,
                    plan_date__lte=end_date,
                )
                .values_list('line_id', flat=True)
                .distinct()
            )
            line_ids.update([lid for lid in backlog_line_ids if lid])
            for line_id in line_ids:
                line_products_map.setdefault(line_id, set()).add(product_id)

        if not line_products_map:
            return Response({'detail': 'target lines not found'}, status=status.HTTP_404_NOT_FOUND)

        recalculated_lines = 0
        recalculated_pairs = 0
        effective_start_dates = {}
        for line_id in sorted(line_products_map.keys()):
            effective_start_dt = _resolve_inventory_effective_start_date(line_id, today, end_date)
            recalculate_inventory_for_line(
                line_id,
                effective_start_dt,
                end_date,
                include_progress=True,
                line_final_only=False,
            )
            effective_start_dates[str(line_id)] = str(effective_start_dt)
            recalculated_pairs += len(line_products_map[line_id])
            recalculated_lines += 1

        return Response({
            'detail': 'recalculated',
            'case_id': case_id,
            'line_count': recalculated_lines,
            'part_count': len(target_product_ids),
            'target_pairs': recalculated_pairs,
            'requested_start_date': str(today),
            'start_date': min(effective_start_dates.values()) if effective_start_dates else str(today),
            'effective_start_dates': effective_start_dates,
            'end_date': str(end_date),
        })
