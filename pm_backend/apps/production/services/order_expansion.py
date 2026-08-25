from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Iterable, List, Tuple

from django.db import transaction
from django.utils import timezone

from masters.models import BOM, BOMItem, Line, Routing, RoutingStep
from orders.core.models import OrderLine
from orders.utils.calendar_utils import DAY_BOUNDARY_HOUR, get_business_today
from production.inventory.lead_time_utils import resolve_lead_days_for_step
from production.models import LineDemand


class OrderExpansionService:
    """
    受注をライン別の需要に展開するサービス。

    - FORECAST は OPEN データを毎回全件再集計し、forecast_qty を置換する
    - FIRM は未展開の OPEN データのみを増分反映し、展開後に is_expanded=True を立てる
    - clear_existing=True の場合は全件再構築し、FIRM 展開フラグも初期化し直す
    """

    LINE_DEMAND_UPDATE_FIELDS = [
        'routing_step',
        'process',
        'product',
        'lead_time_days',
        'is_shifted',
        'firm_is_shifted',
        'forecast_is_shifted',
        'forecast_qty',
        'firm_qty',
        'plan_qty',
        'plan_progress',
        'actual_progress',
        'order_numbers',
        'firm_order_numbers',
        'forecast_order_numbers',
    ]
    EXISTING_DEMAND_VALUE_FIELDS = [
        'id',
        'line_id',
        'product_code',
        'plan_date',
        'routing_step_id',
        'process_id',
        'product_id',
        'lead_time_days',
        'is_shifted',
        'firm_is_shifted',
        'forecast_is_shifted',
        'forecast_qty',
        'firm_qty',
        'plan_qty',
        'actual_qty',
        'plan_progress',
        'actual_progress',
        'order_numbers',
        'firm_order_numbers',
        'forecast_order_numbers',
    ]
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self._is_prefetched = False
        self._routing_cache: Dict[Tuple[int, object], List] = {}
        self._child_bom_cache: Dict[int, BOM | None] = {}
        self._bom_multiplier_cache: Dict[int, Dict[int, Decimal]] = {}
        self._bom_path_multiplier_cache: Dict[int, Dict[str, Decimal]] = {}
        self._supplier_line_cache: Dict[int, int | None] = {}

        self._calendar_day_cache: Dict[Tuple[int, date], bool] = {}
        self._line_cache: Dict[int, Line] = {}
        self._line_calendar_cache: Dict[int, int | None] = {}
        self._bom_items_by_bom: Dict[int, List[BOMItem]] = {}
        self._supplier_bom_items: Dict[int, BOMItem | None] = {}
        self._supplier_line_by_code: Dict[str, int | None] = {}
        self._routing_by_product: Dict[int, List[Tuple[Routing, List[RoutingStep]]]] = {}
        self._bom_by_parent: Dict[int, List[BOM]] = {}
        self._default_calendar_id: int | None = None
        self._routed_product_ids: set[int] = set()
        self._ship_to_additional_days: Dict[Tuple[int, str], int] = {}
        self._ship_to_calendar_cache: Dict[Tuple[int, str], int | None] = {}
        self._customer_calendar_cache: Dict[int, int | None] = {}

    def _prefetch_all(self):
        """全マスタデータをメモリにプリフェッチ（N+1クエリ解消）"""
        if self._is_prefetched:
            return

        from masters.models import Calendar, CalendarDay

        for line in Line.objects.all().select_related():
            self._line_cache[line.id] = line
            self._line_calendar_cache[line.id] = line.calendar_id

        all_items = list(
            BOMItem.objects
            .filter(bom__is_active=True, bom__is_coproduct=False)
            .select_related('child_product', 'supplier')
            .order_by('id')
        )
        for item in all_items:
            self._bom_items_by_bom.setdefault(item.bom_id, []).append(item)
            if item.child_product_id and item.supplier_id:
                self._supplier_bom_items[item.child_product_id] = item

        for line in self._line_cache.values():
            self._supplier_line_by_code[line.line_code] = line.id

        all_routings = list(
            Routing.objects.filter(is_active=True)
            .order_by('-is_default', '-valid_from_datetime', '-id')
        )
        all_steps = list(
            RoutingStep.objects
            .filter(routing__is_active=True)
            .select_related('line', 'output_product')
            .order_by('step_no')
        )
        steps_by_routing: Dict[int, List[RoutingStep]] = {}
        for step in all_steps:
            steps_by_routing.setdefault(step.routing_id, []).append(step)
        for routing in all_routings:
            self._routing_by_product.setdefault(routing.product_id, []).append(
                (routing, steps_by_routing.get(routing.id, []))
            )

        all_boms = list(
            BOM.objects.filter(is_active=True, is_coproduct=False)
            .order_by('-valid_from', '-id')
        )
        for bom in all_boms:
            self._bom_by_parent.setdefault(bom.parent_product_id, []).append(bom)

        self._default_calendar_id = Calendar.objects.filter(
            calendar_code='daiso'
        ).values_list('id', flat=True).first()
        self._routed_product_ids = set(self._routing_by_product.keys())

        from shipping.models import ShipToLeadTime
        from masters.models import Customer
        for stlt in ShipToLeadTime.objects.filter(is_active=True).select_related('customer'):
            key = (stlt.customer_id, (stlt.ship_to_code or '').strip())
            self._ship_to_additional_days[key] = stlt.additional_days
            if stlt.calendar_id:
                self._ship_to_calendar_cache[key] = stlt.calendar_id
        for customer in Customer.objects.filter(calendar__isnull=False).select_related('calendar'):
            self._customer_calendar_cache[customer.id] = customer.calendar_id

        max_lt = max(
            (resolve_lead_days_for_step(s) for s in all_steps if s),
            default=0,
        )
        due_dates = list(
            OrderLine.objects.filter(
                order__status='OPEN',
                product_id__in=self._routed_product_ids,
            ).values_list('due_date', flat=True)
        )
        if due_dates:
            margin = timedelta(days=max_lt * 2 + 30)
            date_min = min(due_dates) - margin
            date_max = max(due_dates) + timedelta(days=30)
            for cd in CalendarDay.objects.filter(
                target_date__gte=date_min,
                target_date__lte=date_max,
            ).only('calendar_id', 'target_date', 'is_working_day', 'is_holiday_work'):
                # 休日出勤日は受注展開では休日扱い
                self._calendar_day_cache[(cd.calendar_id, cd.target_date)] = (
                    cd.is_working_day and not cd.is_holiday_work
                )

        self._is_prefetched = True

    def expand_open_orders(self, clear_existing: bool = False) -> Dict[str, object]:
        """OPEN受注明細をライン需要に展開する。"""
        self._prefetch_all()
        self._collect_unrouted_warnings()

        forced_full_rebuild = bool(clear_existing or self._should_force_full_rebuild())
        if forced_full_rebuild:
            result = self._full_rebuild_open_orders()
            result['forced_full_rebuild'] = True
            return result

        result = self._expand_incremental()
        result['forced_full_rebuild'] = False
        return result

    def revert_firm_order_lines(self, order_line_ids: Iterable[int]) -> Dict[str, object]:
        """指定したFIRM受注明細の展開結果を差し戻し、未展開状態へ戻す。"""
        target_ids = sorted({int(v) for v in order_line_ids if v is not None})
        if not target_ids:
            return {
                'reverted_order_lines': 0,
                'updated_demands': 0,
                'deleted_demands': 0,
                'warnings': self.warnings,
                'errors': ['対象受注明細が指定されていません。'],
            }

        self._prefetch_all()

        target_qs = (
            OrderLine.objects
            .filter(id__in=target_ids, order__status='OPEN')
            .select_related('order', 'order__customer', 'product')
            .order_by('id')
        )
        order_lines = list(target_qs)
        found_ids = {line.id for line in order_lines}
        missing_ids = [line_id for line_id in target_ids if line_id not in found_ids]
        for line_id in missing_ids:
            self.warnings.append(f'差し戻し対象が見つかりません: order_line_id={line_id}')

        valid_lines: List[OrderLine] = []
        for order_line in order_lines:
            effective_order_type = (order_line.order_type or (order_line.order.order_type if order_line.order else '') or '').upper()
            if effective_order_type != 'FIRM':
                self.warnings.append(f'FIRM以外のためスキップ: order_line_id={order_line.id}')
                continue
            if not order_line.is_expanded:
                self.warnings.append(f'未展開のためスキップ: order_line_id={order_line.id}')
                continue
            valid_lines.append(order_line)

        if not valid_lines:
            return {
                'reverted_order_lines': 0,
                'updated_demands': 0,
                'deleted_demands': 0,
                'warnings': self.warnings,
                'errors': self.errors,
            }

        aggregated, _ = self._aggregate_order_lines(valid_lines)
        existing_map = self._load_existing_demand_rows()
        to_update: List[LineDemand] = []
        delete_ids: List[int] = []

        for key, entry in aggregated.items():
            existing = existing_map.get(key)
            if existing is None:
                self.errors.append(
                    f'差し戻し対象の需要が見つかりません: line_id={entry["line_id"]} product={entry["product_code"]} plan_date={entry["plan_date"]} routing_step_id={entry["routing_step_id"]} process_id={key[3]}'
                )
                continue

            demand = self._build_demand_instance_from_row(existing)
            revert_qty = Decimal(str(entry['firm_qty'] or 0))
            current_qty = Decimal(str(demand.firm_qty or 0))
            if current_qty < revert_qty:
                self.errors.append(
                    f'差し戻し数量が既存確定数量を超えます: demand_id={demand.id} current={current_qty} revert={revert_qty}'
                )
                continue

            demand.firm_qty = current_qty - revert_qty
            if demand.firm_qty == 0:
                demand.firm_is_shifted = False
            demand.firm_order_numbers = self._remove_order_numbers(
                demand.firm_order_numbers,
                entry['firm_order_numbers'],
            )
            self._refresh_demand_fields(demand)

            if self._is_empty_demand(demand):
                if demand.pk:
                    delete_ids.append(demand.pk)
                existing_map.pop(key, None)
            else:
                to_update.append(demand)

        if self.errors:
            return {
                'reverted_order_lines': 0,
                'updated_demands': 0,
                'deleted_demands': 0,
                'warnings': self.warnings,
                'errors': self.errors,
            }

        with transaction.atomic():
            if delete_ids:
                LineDemand.objects.filter(id__in=delete_ids).delete()
            if to_update:
                LineDemand.objects.bulk_update(
                    to_update,
                    self.LINE_DEMAND_UPDATE_FIELDS,
                    batch_size=1000,
                )
            OrderLine.objects.filter(id__in=[line.id for line in valid_lines]).update(
                is_expanded=False,
                expanded_at=None,
            )

        return {
            'reverted_order_lines': len(valid_lines),
            'updated_demands': len(to_update),
            'deleted_demands': len(delete_ids),
            'warnings': self.warnings,
            'errors': self.errors,
        }

    def expand_firm_order_lines(self, order_line_ids: Iterable[int]) -> Dict[str, object]:
        """指定したFIRM受注明細だけを増分展開する。"""
        target_ids = sorted({int(v) for v in order_line_ids if v is not None})
        if not target_ids:
            return {
                'expanded_order_lines': 0,
                'created': 0,
                'updated': 0,
                'warnings': self.warnings,
                'errors': ['対象受注明細が指定されていません。'],
            }

        self._prefetch_all()
        target_qs = (
            OrderLine.objects
            .filter(id__in=target_ids, order__status='OPEN')
            .select_related('order', 'order__customer', 'product')
            .order_by('id')
        )
        order_lines = list(target_qs)

        valid_lines: List[OrderLine] = []
        for order_line in order_lines:
            effective_order_type = (order_line.order_type or (order_line.order.order_type if order_line.order else '') or '').upper()
            if effective_order_type != 'FIRM':
                self.warnings.append(f'FIRM以外のためスキップ: order_line_id={order_line.id}')
                continue
            if order_line.is_expanded:
                self.warnings.append(f'展開済みのためスキップ: order_line_id={order_line.id}')
                continue
            valid_lines.append(order_line)

        if not valid_lines:
            return {
                'expanded_order_lines': 0,
                'created': 0,
                'updated': 0,
                'warnings': self.warnings,
                'errors': self.errors,
            }

        aggregated, _ = self._aggregate_order_lines(valid_lines)
        existing_map = self._load_existing_demand_rows()

        with transaction.atomic():
            firm_result = self._apply_incremental_firm_demands(aggregated, existing_map)
            OrderLine.objects.filter(id__in=[line.id for line in valid_lines]).update(
                is_expanded=True,
                expanded_at=datetime.now(),
            )

        return {
            'expanded_order_lines': len(valid_lines),
            'created': firm_result['created'],
            'updated': firm_result['updated'],
            'warnings': self.warnings,
            'errors': self.errors,
        }

    def _should_force_full_rebuild(self) -> bool:
        """
        既存LineDemandがあり、OPEN FIRM が全件未展開の状態は
        旧ロジックからの移行直後とみなして一度だけ全件再構築する。
        """
        if not LineDemand.objects.exists():
            return False

        open_firm_qs = OrderLine.objects.filter(order__status='OPEN', order__order_type='FIRM')
        total_firm = open_firm_qs.count()
        if total_firm == 0:
            return False

        unexpanded_firm = open_firm_qs.filter(is_expanded=False).count()
        return unexpanded_firm == total_firm

    def _collect_unrouted_warnings(self):
        forecast_codes = list(
            OrderLine.objects.filter(order__status='OPEN', order__order_type='FORECAST')
            .exclude(product_id__in=self._routed_product_ids)
            .values_list('product__product_code', flat=True)
            .distinct()
        )
        firm_codes = list(
            OrderLine.objects.filter(
                order__status='OPEN',
                order__order_type='FIRM',
                is_expanded=False,
            )
            .exclude(product_id__in=self._routed_product_ids)
            .values_list('product__product_code', flat=True)
            .distinct()
        )

        for code in sorted({code for code in forecast_codes + firm_codes if code}):
            self.warnings.append(f"ルーティング未設定のためスキップ: {code}")

    def _get_open_order_lines_queryset(self, order_type: str | None = None, is_expanded: bool | None = None):
        queryset = OrderLine.objects.filter(
            order__status='OPEN',
            product_id__in=self._routed_product_ids,
        ).select_related('order', 'order__customer', 'product')
        if order_type:
            queryset = queryset.filter(order__order_type=order_type)
        if is_expanded is not None:
            queryset = queryset.filter(is_expanded=is_expanded)
        return queryset.order_by('id')

    def _expand_incremental(self) -> Dict[str, object]:
        open_firm_source_keys = self._collect_open_firm_source_keys()
        forecast_aggregated, _ = self._aggregate_order_lines(
            self._get_open_order_lines_queryset(order_type='FORECAST'),
            exclude_forecast_source_keys=open_firm_source_keys,
        )
        firm_aggregated, processed_firm_line_ids = self._aggregate_order_lines(
            self._get_open_order_lines_queryset(order_type='FIRM', is_expanded=False)
        )

        existing_map = self._load_existing_demand_rows()

        with transaction.atomic():
            forecast_result = self._sync_forecast_demands(forecast_aggregated, existing_map)
            firm_result = self._apply_incremental_firm_demands(firm_aggregated, existing_map)

            if processed_firm_line_ids:
                OrderLine.objects.filter(id__in=processed_firm_line_ids).update(
                    is_expanded=True,
                    expanded_at=timezone.now(),
                )

        return {
            'cleared': 0,
            'created': forecast_result['created'] + firm_result['created'],
            'updated': forecast_result['updated'] + firm_result['updated'],
            'deleted': forecast_result['deleted'],
            'processed_order_lines': len(processed_firm_line_ids),
            'warnings': self.warnings,
            'errors': self.errors,
        }

    def _full_rebuild_open_orders(self) -> Dict[str, object]:
        open_firm_source_keys = self._collect_open_firm_source_keys()
        forecast_aggregated, _ = self._aggregate_order_lines(
            self._get_open_order_lines_queryset(order_type='FORECAST'),
            exclude_forecast_source_keys=open_firm_source_keys,
        )
        firm_aggregated, _ = self._aggregate_order_lines(
            self._get_open_order_lines_queryset(order_type='FIRM')
        )
        aggregated = self._merge_aggregated_demands(forecast_aggregated, firm_aggregated)
        actual_qty_map = self._load_existing_actual_qty_map()

        objects_to_create: List[LineDemand] = []
        for key, entry in aggregated.items():
            actual_qty = actual_qty_map.get(key, Decimal('0'))
            objects_to_create.append(self._build_line_demand(entry, actual_qty=actual_qty))

        routed_open_firm_qs = self._get_open_order_lines_queryset(order_type='FIRM').values_list('id', flat=True)

        with transaction.atomic():
            cleared = LineDemand.objects.count()
            if cleared:
                LineDemand.objects.all()._raw_delete(LineDemand.objects.db)

            if objects_to_create:
                LineDemand.objects.bulk_create(objects_to_create, batch_size=10000)

            firm_ids = list(routed_open_firm_qs)
            if firm_ids:
                OrderLine.objects.filter(id__in=firm_ids).update(
                    is_expanded=True,
                    expanded_at=timezone.now(),
                )

        return {
            'cleared': cleared,
            'created': len(objects_to_create),
            'updated': 0,
            'deleted': cleared,
            'processed_order_lines': len(firm_ids),
            'warnings': self.warnings,
            'errors': self.errors,
        }

    def _sync_forecast_demands(self, aggregated, existing_map):
        existing_forecast_keys = {
            key for key, demand in existing_map.items()
            if Decimal(str((demand.get('forecast_qty') if isinstance(demand, dict) else demand.forecast_qty) or 0)) > 0
        }
        target_keys = set(aggregated.keys()) | existing_forecast_keys

        to_create: List[LineDemand] = []
        to_update: List[LineDemand] = []
        delete_ids: List[int] = []

        for key in target_keys:
            entry = aggregated.get(key)
            existing = existing_map.get(key)

            if entry:
                if existing is None:
                    existing = self._build_line_demand(entry)
                    existing_map[key] = existing
                    to_create.append(existing)
                    continue

                existing = self._build_demand_instance_from_row(existing)
                self._apply_shared_entry_metadata(existing, entry)
                existing.forecast_qty = entry['forecast_qty']
                existing.forecast_is_shifted = bool(entry['forecast_is_shifted'])
                existing.forecast_order_numbers = self._normalize_order_numbers(
                    entry['forecast_order_numbers']
                )
                self._refresh_demand_fields(existing)
                to_update.append(existing)
                continue

            if existing is None:
                continue

            existing = self._build_demand_instance_from_row(existing)
            existing.forecast_qty = Decimal('0')
            existing.forecast_is_shifted = False
            existing.forecast_order_numbers = ''
            self._refresh_demand_fields(existing)

            if self._is_empty_demand(existing):
                if existing.pk:
                    delete_ids.append(existing.pk)
                existing_map.pop(key, None)
            else:
                to_update.append(existing)

        if delete_ids:
            LineDemand.objects.filter(id__in=delete_ids).delete()
        if to_create:
            LineDemand.objects.bulk_create(to_create, batch_size=10000)
            self._refresh_created_demands(to_create, existing_map)
        if to_update:
            LineDemand.objects.bulk_update(
                to_update,
                self.LINE_DEMAND_UPDATE_FIELDS,
                batch_size=1000,
            )

        return {
            'created': len(to_create),
            'updated': len(to_update),
            'deleted': len(delete_ids),
        }

    def _apply_incremental_firm_demands(self, aggregated, existing_map):
        to_create: List[LineDemand] = []
        to_update: List[LineDemand] = []

        for key, entry in aggregated.items():
            existing = existing_map.get(key)
            if existing is None:
                existing = self._build_line_demand(entry)
                existing_map[key] = existing
                to_create.append(existing)
                continue

            existing = self._build_demand_instance_from_row(existing)
            existing.firm_qty = (existing.firm_qty or Decimal('0')) + entry['firm_qty']
            existing.firm_is_shifted = bool(existing.firm_is_shifted or entry['firm_is_shifted'])
            existing.firm_order_numbers = self._merge_order_number_strings(
                existing.firm_order_numbers,
                self._normalize_order_numbers(entry['firm_order_numbers']),
            )
            self._refresh_demand_fields(existing)
            to_update.append(existing)

        if to_create:
            LineDemand.objects.bulk_create(to_create, batch_size=10000)
        if to_update:
            LineDemand.objects.bulk_update(
                to_update,
                self.LINE_DEMAND_UPDATE_FIELDS,
                batch_size=1000,
            )

        for created in to_create:
            existing_map[(created.line_id, created.product_code, created.plan_date, created.process_id)] = created

        return {
            'created': len(to_create),
            'updated': len(to_update),
        }

    def _load_existing_demand_rows(self):
        return {
            (row['line_id'], row['product_code'], row['plan_date'], row['process_id']): row
            for row in LineDemand.objects.values(*self.EXISTING_DEMAND_VALUE_FIELDS)
        }

    def _load_existing_actual_qty_map(self):
        return {
            (row['line_id'], row['product_code'], row['plan_date'], row['process_id']): Decimal(str(row['actual_qty'] or 0))
            for row in LineDemand.objects.values('line_id', 'product_code', 'plan_date', 'process_id', 'actual_qty')
        }

    def _refresh_created_demands(self, created_demands: List[LineDemand], existing_map):
        if not created_demands:
            return

        line_ids = {demand.line_id for demand in created_demands}
        product_codes = {demand.product_code for demand in created_demands}
        plan_dates = {demand.plan_date for demand in created_demands}

        refreshed = LineDemand.objects.filter(
            line_id__in=line_ids,
            product_code__in=product_codes,
            plan_date__in=plan_dates,
        ).values(*self.EXISTING_DEMAND_VALUE_FIELDS)
        for row in refreshed:
            existing_map[(row['line_id'], row['product_code'], row['plan_date'], row['process_id'])] = row

    def _aggregate_order_lines(self, order_lines: Iterable[OrderLine], exclude_forecast_source_keys=None):
        aggregated: Dict[Tuple[int, str, object, int | None], Dict[str, object]] = {}
        processed_ids: List[int] = []

        for order_line in order_lines:
            processed_ids.append(order_line.id)
            self._accumulate_order_line(
                aggregated,
                order_line,
                exclude_forecast_source_keys=exclude_forecast_source_keys,
            )

        return aggregated, processed_ids

    def _accumulate_order_line(self, aggregated, order_line: OrderLine, exclude_forecast_source_keys=None):
        if (
            order_line.order.order_type == 'FORECAST'
            and order_line.due_date
            and order_line.due_date <= get_business_today()
        ):
            return

        source_key = self._build_source_demand_key(order_line)
        if (
            order_line.order.order_type == 'FORECAST'
            and exclude_forecast_source_keys
            and source_key in exclude_forecast_source_keys
        ):
            return

        product = order_line.product
        if not product:
            return

        steps = self._get_routing_steps(product_id=product.id, reference=order_line.due_date)
        if not steps:
            return

        bom_multiplier, path_multiplier = self._get_bom_multiplier_maps(product.id)
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
        for product_id, routed_mult in routed_multiplier_by_product.items():
            if product_id == product.id:
                # 同一品番を複数工程で流すルーティングでは、
                # 完成品自身の数量を工程数で按分してはいけない。
                correction_by_product[product_id] = Decimal('1')
                continue
            expected_mult = bom_multiplier.get(product_id)
            if expected_mult is not None and routed_mult > 0:
                correction_by_product[product_id] = expected_mult / routed_mult
            else:
                correction_by_product[product_id] = Decimal('1')

        required_date = order_line.due_date
        customer_id = order_line.order.customer_id if order_line.order else None
        ship_to_code = (order_line.ship_to_code or '').strip()
        if customer_id and ship_to_code:
            additional_days = self._ship_to_additional_days.get((customer_id, ship_to_code))
            if additional_days:
                calendar_ids = self._resolve_demand_calendar_ids(None, customer_id, ship_to_code)
                required_date = self._shift_business_days(calendar_ids, required_date, additional_days)
        final_required_date = required_date

        path_step_map = {
            step.hierarchy_path: step
            for step in steps
            if step.hierarchy_path and step.hierarchy_path != 'final'
        }
        children_map = {}
        for path in path_step_map.keys():
            parent_path = path.rsplit('.', 1)[0] if '.' in path else None
            children_map.setdefault(parent_path, []).append(path)

        # 中間工程の階層補正: 非final・加工後品目=ルーティング製品・hierarchy_path未設定
        # の工程を仮想パスでツリーに組み込み、remark(親製品コード)で子部品を再配置
        _orphan_vpath_map = {}
        _existing_step_ids = {s.id for s in path_step_map.values()}
        _orphan_int_steps = [
            s for s in steps
            if s.hierarchy_path != 'final'
            and s.id not in _existing_step_ids
            and s.output_product_id == product.id
        ]
        if _orphan_int_steps:
            _orphan_int_steps.sort(key=lambda s: s.step_no, reverse=True)
            _int_vpaths = []
            for _ois in _orphan_int_steps:
                _vp = f"_oi_{_ois.id}"
                path_step_map[_vp] = _ois
                _orphan_vpath_map[_ois.id] = _vp
                _int_vpaths.append(_vp)
            children_map.setdefault(None, []).append(_int_vpaths[0])
            for _i in range(1, len(_int_vpaths)):
                children_map.setdefault(_int_vpaths[_i - 1], []).append(_int_vpaths[_i])
            _output_to_path = {}
            for _p, _s in path_step_map.items():
                if _s.output_product_id and _s.output_product:
                    _output_to_path[_s.output_product.product_code] = _p
            for _rp in list(children_map.get(None, [])):
                if _rp.startswith('_oi_'):
                    continue
                _rs = path_step_map.get(_rp)
                if not _rs:
                    continue
                _remark = (_rs.remark or '').strip()
                if not _remark:
                    continue
                _parent_path = _output_to_path.get(_remark)
                if _parent_path and _parent_path != _rp:
                    children_map[None].remove(_rp)
                    children_map.setdefault(_parent_path, []).append(_rp)

        final_step = next((step for step in steps if step.hierarchy_path == 'final'), None)
        if final_step:
            final_step_product = final_step.output_product if final_step.output_product_id else product
            final_calendar_ids = self._resolve_demand_calendar_ids(
                final_step.line_id,
                customer_id,
                ship_to_code,
            )
            lead_days = resolve_lead_days_for_step(final_step)
            final_required_date = self._shift_business_days(
                final_calendar_ids,
                required_date,
                lead_days,
            )

        required_by_path = {}

        def compute_required_date(path, parent_date):
            step = path_step_map.get(path)
            if not step:
                return
            step_product = step.output_product if step.output_product_id else product
            calendar_ids = self._resolve_demand_calendar_ids(
                step.line_id,
                customer_id,
                ship_to_code,
            )
            lead_days = resolve_lead_days_for_step(step)
            required_for_step = self._shift_business_days(
                calendar_ids,
                parent_date,
                lead_days,
            )
            required_by_path[path] = required_for_step
            for child_path in sorted(children_map.get(path, []), key=self._path_key):
                compute_required_date(child_path, required_for_step)

        for root_path in sorted(children_map.get(None, []), key=self._path_key):
            compute_required_date(root_path, final_required_date)

        for step in reversed(steps):
            if not step.line_id:
                self.warnings.append(f"ライン未設定の工程をスキップ: routing_step_id={step.id}")
                continue

            effective_line_id = step.line_id
            step_product = step.output_product if step.output_product_id else product
            line_obj = self._line_cache.get(step.line_id)
            if line_obj and line_obj.line_type == 'OUTSOURCE' and step_product:
                supplier_line_id = self._get_supplier_line_id(step_product.id)
                if supplier_line_id:
                    effective_line_id = supplier_line_id

            calendar_ids = self._resolve_demand_calendar_ids(
                effective_line_id,
                customer_id,
                ship_to_code,
            )
            lead_days = resolve_lead_days_for_step(step)
            if step.hierarchy_path == 'final':
                target_date = final_required_date
            elif step.hierarchy_path in required_by_path:
                target_date = required_by_path[step.hierarchy_path]
            elif step.id in _orphan_vpath_map and _orphan_vpath_map[step.id] in required_by_path:
                target_date = required_by_path[_orphan_vpath_map[step.id]]
            else:
                target_date = self._shift_business_days(calendar_ids, required_date, lead_days)

            is_shifted = bool(target_date != order_line.due_date)
            product_code = step_product.product_code if step_product else order_line.product_code
            product_id = step_product.id if step_product else product.id

            if step.hierarchy_path == 'final':
                base_mult = Decimal('1')
            else:
                base_mult = path_multiplier.get(step.hierarchy_path, Decimal('1'))
            correction = correction_by_product.get(product_id, Decimal('1'))

            key = (effective_line_id, product_code, target_date, step.process_id)
            entry = aggregated.get(key)
            if not entry:
                entry = {
                    'line_id': effective_line_id,
                    'routing_step_id': step.id,
                    'process_id': step.process_id,
                    'product_id': product_id,
                    'product_code': product_code,
                    'plan_date': target_date,
                    'lead_time_days': lead_days,
                    'firm_qty': Decimal('0'),
                    'forecast_qty': Decimal('0'),
                    'firm_is_shifted': False,
                    'forecast_is_shifted': False,
                    'firm_order_numbers': set(),
                    'forecast_order_numbers': set(),
                }
                aggregated[key] = entry

            qty = (order_line.quantity or Decimal('0')) * base_mult * correction
            if order_line.order.order_type == 'FIRM':
                entry['firm_qty'] += qty
                entry['firm_is_shifted'] = bool(entry['firm_is_shifted'] or is_shifted)
                entry['firm_order_numbers'].add(order_line.order.order_no)
            else:
                entry['forecast_qty'] += qty
                entry['forecast_is_shifted'] = bool(entry['forecast_is_shifted'] or is_shifted)
                entry['forecast_order_numbers'].add(order_line.order.order_no)

            if step.hierarchy_path == 'final':
                required_date = target_date

    def _build_source_demand_key(self, order_line: OrderLine):
        return (
            order_line.order.customer_id,
            order_line.product_code,
            (order_line.ship_to_code or '').strip(),
            order_line.due_date,
        )

    def _collect_open_firm_source_keys(self):
        return {
            self._build_source_demand_key(order_line)
            for order_line in self._get_open_order_lines_queryset(order_type='FIRM')
        }

    def _merge_aggregated_demands(self, forecast_aggregated, firm_aggregated):
        merged = {}
        for source in (forecast_aggregated, firm_aggregated):
            for key, entry in source.items():
                existing = merged.get(key)
                if existing is None:
                    merged[key] = {
                        'line_id': entry['line_id'],
                        'routing_step_id': entry['routing_step_id'],
                        'process_id': entry['process_id'],
                        'product_id': entry['product_id'],
                        'product_code': entry['product_code'],
                        'plan_date': entry['plan_date'],
                        'lead_time_days': entry['lead_time_days'],
                        'firm_qty': entry['firm_qty'],
                        'forecast_qty': entry['forecast_qty'],
                        'firm_is_shifted': bool(entry['firm_is_shifted']),
                        'forecast_is_shifted': bool(entry['forecast_is_shifted']),
                        'firm_order_numbers': set(entry['firm_order_numbers']),
                        'forecast_order_numbers': set(entry['forecast_order_numbers']),
                    }
                    continue

                existing['firm_qty'] += entry['firm_qty']
                existing['forecast_qty'] += entry['forecast_qty']
                existing['firm_is_shifted'] = bool(existing['firm_is_shifted'] or entry['firm_is_shifted'])
                existing['forecast_is_shifted'] = bool(existing['forecast_is_shifted'] or entry['forecast_is_shifted'])
                existing['firm_order_numbers'].update(entry['firm_order_numbers'])
                existing['forecast_order_numbers'].update(entry['forecast_order_numbers'])
        return merged

    def _build_demand_instance_from_row(self, row):
        return LineDemand(
            id=row['id'],
            line_id=row['line_id'],
            routing_step_id=row['routing_step_id'],
            process_id=row['process_id'],
            product_id=row['product_id'],
            product_code=row['product_code'],
            plan_date=row['plan_date'],
            lead_time_days=row['lead_time_days'],
            is_shifted=bool(row['is_shifted']),
            firm_is_shifted=bool(row['firm_is_shifted']),
            forecast_is_shifted=bool(row['forecast_is_shifted']),
            forecast_qty=Decimal(str(row['forecast_qty'] or 0)),
            firm_qty=Decimal(str(row['firm_qty'] or 0)),
            plan_qty=Decimal(str(row['plan_qty'] or 0)),
            actual_qty=Decimal(str(row['actual_qty'] or 0)),
            plan_progress=Decimal(str(row['plan_progress'] or 0)),
            actual_progress=Decimal(str(row['actual_progress'] or 0)),
            order_numbers=row['order_numbers'] or '',
            firm_order_numbers=row['firm_order_numbers'] or '',
            forecast_order_numbers=row['forecast_order_numbers'] or '',
        )

    def _build_line_demand(self, entry, existing=None, actual_qty: Decimal | None = None):
        if actual_qty is None:
            if existing is not None:
                if isinstance(existing, dict):
                    actual_qty = Decimal(str(existing.get('actual_qty') or 0))
                else:
                    actual_qty = existing.actual_qty
            else:
                actual_qty = Decimal('0')
        demand = LineDemand(
            line_id=entry['line_id'],
            routing_step_id=entry['routing_step_id'],
            process_id=entry['process_id'],
            product_id=entry['product_id'],
            product_code=entry['product_code'],
            plan_date=entry['plan_date'],
            lead_time_days=entry['lead_time_days'],
            forecast_qty=entry['forecast_qty'],
            firm_qty=entry['firm_qty'],
            actual_qty=actual_qty,
            firm_is_shifted=bool(entry['firm_is_shifted']),
            forecast_is_shifted=bool(entry['forecast_is_shifted']),
            firm_order_numbers=self._normalize_order_numbers(entry['firm_order_numbers']),
            forecast_order_numbers=self._normalize_order_numbers(entry['forecast_order_numbers']),
        )
        self._refresh_demand_fields(demand)
        return demand

    def _apply_shared_entry_metadata(self, demand: LineDemand, entry):
        demand.routing_step_id = entry['routing_step_id']
        demand.process_id = entry['process_id']
        demand.product_id = entry['product_id']
        demand.lead_time_days = entry['lead_time_days']

    def _refresh_demand_fields(self, demand: LineDemand):
        required_qty = (demand.forecast_qty or Decimal('0')) + (demand.firm_qty or Decimal('0'))
        actual_qty = demand.actual_qty or Decimal('0')
        demand.is_shifted = bool(demand.firm_is_shifted or demand.forecast_is_shifted)
        demand.plan_qty = required_qty
        demand.plan_progress = self._calc_progress(demand.plan_qty, required_qty)
        demand.actual_progress = self._calc_progress(actual_qty, required_qty)
        demand.order_numbers = self._merge_order_number_strings(
            demand.firm_order_numbers,
            demand.forecast_order_numbers,
        )

    def _is_empty_demand(self, demand: LineDemand) -> bool:
        return (
            (demand.forecast_qty or Decimal('0')) == 0
            and (demand.firm_qty or Decimal('0')) == 0
        )

    def _normalize_order_numbers(self, order_numbers) -> str:
        if isinstance(order_numbers, str):
            values = [item.strip() for item in order_numbers.split(',') if item.strip()]
        else:
            values = [str(item).strip() for item in order_numbers if str(item).strip()]

        merged = ','.join(sorted(set(values)))
        if len(merged) > 500:
            return merged[:500]
        return merged

    def _merge_order_number_strings(self, *values: str) -> str:
        merged_values = []
        for value in values:
            if not value:
                continue
            merged_values.extend(item.strip() for item in str(value).split(',') if item.strip())
        return self._normalize_order_numbers(merged_values)

    def _remove_order_numbers(self, current_value: str, values_to_remove) -> str:
        current_items = {
            item.strip()
            for item in str(current_value or '').split(',')
            if item and item.strip()
        }
        remove_items = {
            str(item).strip()
            for item in (values_to_remove or [])
            if str(item).strip()
        }
        return self._normalize_order_numbers(sorted(current_items - remove_items))

    def _resolve_calendar_id(self, line_id):
        if not line_id:
            return self._default_calendar_id
        cal_id = self._line_calendar_cache.get(line_id)
        return cal_id or self._default_calendar_id

    def _resolve_demand_calendar_ids(self, line_id, customer_id, ship_to_code=None):
        calendar_ids: List[int | None] = [self._resolve_calendar_id(line_id)]
        if customer_id and ship_to_code:
            ship_to_cal = self._ship_to_calendar_cache.get((customer_id, ship_to_code))
            if ship_to_cal and ship_to_cal not in calendar_ids:
                calendar_ids.append(ship_to_cal)
                return tuple(calendar_ids)
        if customer_id:
            customer_calendar_id = self._customer_calendar_cache.get(customer_id)
            if customer_calendar_id and customer_calendar_id not in calendar_ids:
                calendar_ids.append(customer_calendar_id)
        return tuple(calendar_ids)

    def _is_working_day(self, calendar_ids, target_date):
        if not calendar_ids:
            return target_date.weekday() < 5
        return all(self._is_single_calendar_working_day(calendar_id, target_date) for calendar_id in calendar_ids)

    def _is_single_calendar_working_day(self, calendar_id, target_date):
        if not calendar_id:
            return target_date.weekday() < 5
        key = (calendar_id, target_date)
        if key in self._calendar_day_cache:
            return self._calendar_day_cache[key]
        return target_date.weekday() < 5

    def _shift_business_days(self, calendar_ids, target_date, days):
        if not days:
            if not calendar_ids:
                return target_date
            if self._is_working_day(calendar_ids, target_date):
                return target_date
            current = target_date
            while True:
                current = current - timedelta(days=1)
                if self._is_working_day(calendar_ids, current):
                    return current

        step = -1 if days > 0 else 1
        remaining = abs(int(days))
        current = target_date
        while remaining > 0:
            current = current + timedelta(days=step)
            if self._is_working_day(calendar_ids, current):
                remaining -= 1
        return current

    def _path_key(self, path):
        try:
            return tuple(int(part) for part in str(path).split('.'))
        except Exception:
            return (str(path),)

    def _resolve_routing_in_memory(self, product_id: int, reference=None):
        """プリフェッチ済みルーティングからメモリ内で有効なルーティングを解決する。"""
        candidates = self._routing_by_product.get(product_id, [])
        if not candidates:
            return None, []

        if reference is None:
            ref_dt = datetime.now()
        elif isinstance(reference, date) and not isinstance(reference, datetime):
            ref_dt = datetime.combine(reference, time(DAY_BOUNDARY_HOUR, 0))
        else:
            ref_dt = reference

        for routing, steps in candidates:
            if routing.valid_from_datetime and routing.valid_from_datetime > ref_dt:
                continue
            if routing.valid_to_datetime and routing.valid_to_datetime < ref_dt:
                continue
            return routing, steps
        return None, []

    def _get_routing_steps(self, product_id: int, reference=None):
        """有効日時を考慮したルーティング工程一覧をキャッシュして返す（メモリ内解決）。"""
        cache_key = (product_id, reference)
        if cache_key in self._routing_cache:
            return self._routing_cache[cache_key]

        _, steps = self._resolve_routing_in_memory(product_id, reference)
        self._routing_cache[cache_key] = steps
        return steps

    def _pick_child_bom(self, product_id: int):
        """子製品の有効BOMを取得（メモリ内解決）。連産品BOMは除外。"""
        if product_id in self._child_bom_cache:
            return self._child_bom_cache[product_id]

        today = date.today()
        candidates = self._bom_by_parent.get(product_id, [])
        bom = None
        for candidate in candidates:
            if candidate.valid_from and candidate.valid_from <= today:
                bom = candidate
                break
        if not bom and candidates:
            bom = candidates[0]

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
        items = self._bom_items_by_bom.get(bom.id, [])
        for idx, item in enumerate(items, start=1):
            if not item.child_product_id:
                continue
            qty = Decimal(str(item.quantity or 0))
            if qty == 0:
                continue

            child_multiplier = current_multiplier * qty
            path_tuple = path_prefix + (idx,)
            path_key = '.'.join(str(part) for part in path_tuple)

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

        bom_item = self._supplier_bom_items.get(product_id)
        supplier_line_id = None
        if bom_item and bom_item.supplier_id:
            supplier_code = bom_item.supplier.supplier_code
            supplier_line_id = self._supplier_line_by_code.get(supplier_code)

        self._supplier_line_cache[product_id] = supplier_line_id
        return supplier_line_id

    def _calc_progress(self, numerator: Decimal, denominator: Decimal) -> Decimal:
        """0除算を避けつつ進捗（0-1）を小数3桁で返す。"""
        if denominator is None or denominator == 0:
            return Decimal('0')
        return (numerator / denominator).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
