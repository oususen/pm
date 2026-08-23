from rest_framework import viewsets, status
from rest_framework.views import APIView
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import timedelta, datetime, date
from uuid import uuid4
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
import django_filters
from django.db.models import Q, Max, Prefetch, Sum
from django.db import transaction
import logging
import csv
import io
import math
import json
from django.http import HttpResponse
from django.utils import timezone
from system_settings.models import SystemSetting

from .models import LineDemand
from .inventory.lead_time_utils import resolve_lead_days_for_step
from .inventory.trace_debug import trace_log
from orders.models import OrderLine
from .models_line_backlog import LineBacklog
from .models_line_backlog_adjustment import LineBacklogAdjustment
from .models_line_plan import LinePlan
from .models_production import StockAllocation, ProductionOrder, ProcessActual
from .models_line_gantt_plan import LineGanttPlan
from .models_line_daily_schedule_setting import LineDailyScheduleSetting
from .models_line_default_schedule_setting import LineDefaultScheduleSetting
from .models_auto_plan_aggregate_setting import AutoPlanAggregateSetting
from .models_plan_change_log import ProductionPlanChangeLog
from .models_plan_lock_setting import ProductionPlanLockSetting
from .models_record_inquiry_setting import ProductionRecordInquirySetting
from .models_schedule_config import ScheduleConfig, ScheduleRunLog
from .models_purchase_actual_reconcile import (
    PurchaseActualReconcileReport,
    PurchaseActualReconcileReportDetail,
)
from .models_production_actual_reconcile import (
    ProductionActualReconcileReport,
    ProductionActualReconcileReportDetail,
)
from .models_laser_pattern import LaserPattern
from .models_laser_actual import LaserActual, LaserActualDetail
from .models_laser_kadojiseki import LaserShiftRecord
from .serializers import (
    LineBacklogSerializer,
    LinePlanSerializer,
    ProductionPlanChangeLogSerializer,
    LineGanttPlanSerializer,
    LineDailyScheduleSettingSerializer,
    LineDefaultScheduleSettingSerializer,
    AutoPlanAggregateSettingSerializer,
    ProductionPlanLockSettingSerializer,
    ScheduleConfigSerializer,
    ScheduleRunLogSerializer,
    PurchaseActualReconcileReportSerializer,
    PurchaseActualReconcileReportDetailSerializer,
    ProductionActualReconcileReportSerializer,
    ProductionActualReconcileReportDetailSerializer,
    StockAllocationSerializer,
    ProductionOrderSerializer,
    ProductionOrderListSerializer,
    ProcessActualSerializer,
    LineBacklogAdjustmentSerializer,
    LaserPatternSerializer,
    LaserActualSerializer,
    LaserShiftRecordSerializer,
)
from .services.gantt_planning import generate_line_gantt_plans
from .services import backlog_pickup_service, backlog_recalc_service
from .services.recalc_start_date import (
    resolve_inventory_effective_start_date,
    resolve_product_recalc_start_date,
)
from .views_line_demand import LineDemandViewSet
from .views_plan_line_setting import ProductionPlanLineSettingView
from masters.models import Routing, RoutingStep, ProcessCycleTime, Line, Supplier, Process, Calendar, CalendarDay, BOM, BOMItem, Product, KubotaSakaiTruck
from masters.services.routing_service import build_effective_routing_q, build_effective_routing_range_q, normalize_routing_reference_datetime, resolve_effective_routing
from orders.utils.calendar_utils import DAY_BOUNDARY_HOUR, get_business_today, add_working_days
from purchase.process_resolver import (
    is_outsource_process,
    resolve_purchase_line as resolve_supplier_purchase_line,
    resolve_supplier_process,
)
from django.contrib.auth import get_user_model
from django.db.models import Q

logger = logging.getLogger(__name__)

FLOOR_SHIPPING_TAB_KEY = 'floor-shipping'
FLOOR_SHIPPING_DELIVERY_LABEL = 'フロア配送'
FLOOR_SHIPPING_PM_SEQUENCE_THRESHOLD = 50
INVALID_SEQUENCE_SORT_VALUE = 10 ** 9

# クボタ配送ライン: plan_id から truck_id を抽出して arrival_day_offset ベースで LT を決定
KUBOTA_DELIVERY_LABELS = ('L3102', 'KUBOTA_DELIVERY', 'クボタ配送')


def _is_stale_cancel_requested_run(config):
    if not config or getattr(config, 'last_run_status', None) != 'RUNNING':
        return False
    message = str(getattr(config, 'last_run_message', '') or '')
    last_run_at = getattr(config, 'last_run_at', None)
    if '[CANCEL_REQUESTED]' not in message or not last_run_at:
        return False
    return last_run_at.date() < datetime.now().date()


def _parse_optional_date(value):
    if value is None:
        return None
    if hasattr(value, 'year'):
        return value
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except Exception:
        return None


def _parse_product_ids(value):
    if value is None or value == '':
        return []
    if isinstance(value, str):
        items = [v.strip() for v in value.split(',') if v.strip()]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        raise ValueError('product_ids must be a list or comma separated string')

    result = []
    for item in items:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            raise ValueError('product_ids must be numeric')
    return sorted(set(result))


def _is_floor_shipping_delivery_line(line_obj):
    if not line_obj:
        return False
    line_code = str(getattr(line_obj, 'line_code', '') or '').strip()
    line_name = str(getattr(line_obj, 'line_name', '') or '').strip()
    return FLOOR_SHIPPING_DELIVERY_LABEL in f'{line_code} {line_name}'


def _is_kubota_delivery_line(line_obj):
    """クボタ配送ラインかどうかを判定"""
    if not line_obj:
        return False
    line_code = str(getattr(line_obj, 'line_code', '') or '').strip()
    line_name = str(getattr(line_obj, 'line_name', '') or '').strip()
    return any(label in f'{line_code} {line_name}' for label in KUBOTA_DELIVERY_LABELS)


class LineBacklogFilter(django_filters.FilterSet):
    """LineBacklogのカスタムフィルタ"""
    line = django_filters.NumberFilter(field_name='line_id')
    process = django_filters.NumberFilter(field_name='process_id')
    product = django_filters.NumberFilter(field_name='product_id')
    product__in = django_filters.CharFilter(method='filter_product_in')
    plan_date = django_filters.DateFilter(field_name='plan_date')
    plan_date__gte = django_filters.DateFilter(field_name='plan_date', lookup_expr='gte')
    plan_date__lte = django_filters.DateFilter(field_name='plan_date', lookup_expr='lte')
    line_search = django_filters.CharFilter(method='filter_line_search')
    process_search = django_filters.CharFilter(method='filter_process_search')
    product_search = django_filters.CharFilter(method='filter_product_search')

    class Meta:
        model = LineBacklog
        fields = []

    def filter_product_in(self, queryset, name, value):
        """カンマ区切りの製品IDリストでフィルタ"""
        if value:
            try:
                product_ids = [int(x.strip()) for x in value.split(',') if x.strip()]
                return queryset.filter(product_id__in=product_ids)
            except (ValueError, TypeError):
                return queryset.none()
        return queryset

    def filter_line_search(self, queryset, name, value):
        """ラインコード完全一致/名称部分一致フィルタ"""
        if value:
            return queryset.filter(
                Q(line__line_code__iexact=value) | Q(line__line_name__icontains=value)
            )
        return queryset

    def filter_process_search(self, queryset, name, value):
        """工程コード完全一致/名称部分一致フィルタ"""
        if value:
            return queryset.filter(
                Q(process__process_code__iexact=value) | Q(process__process_name__icontains=value)
            )
        return queryset

    def filter_product_search(self, queryset, name, value):
        """品番/品名の部分一致フィルタ"""
        if value:
            return queryset.filter(
                Q(product__product_code__icontains=value) | Q(product__product_name__icontains=value)
            )
        return queryset


class LinePlanFilter(django_filters.FilterSet):
    """LinePlanのカスタムフィルタ"""
    line = django_filters.NumberFilter(field_name='line_id')
    process = django_filters.NumberFilter(field_name='process_id')
    product = django_filters.NumberFilter(field_name='product_id')
    plan_date = django_filters.DateFilter(field_name='plan_date')
    plan_date__gte = django_filters.DateFilter(field_name='plan_date', lookup_expr='gte')
    plan_date__lte = django_filters.DateFilter(field_name='plan_date', lookup_expr='lte')

    class Meta:
        model = LinePlan
        fields = []


class ProductionPlanChangeLogFilter(django_filters.FilterSet):
    """ProductionPlanChangeLogのカスタムフィルタ"""
    line = django_filters.NumberFilter(field_name='line_id')
    process = django_filters.NumberFilter(field_name='process_id')
    product = django_filters.NumberFilter(field_name='product_id')
    changed_by = django_filters.NumberFilter(field_name='changed_by_id')
    plan_date = django_filters.DateFilter(field_name='plan_date')
    plan_date__gte = django_filters.DateFilter(field_name='plan_date', lookup_expr='gte')
    plan_date__lte = django_filters.DateFilter(field_name='plan_date', lookup_expr='lte')
    changed_at__gte = django_filters.DateTimeFilter(field_name='changed_at', lookup_expr='gte')
    changed_at__lte = django_filters.DateTimeFilter(field_name='changed_at', lookup_expr='lte')

    class Meta:
        model = ProductionPlanChangeLog
        fields = []


class LineGanttPlanFilter(django_filters.FilterSet):
    """LineGanttPlanのカスタムフィルタ"""
    line = django_filters.NumberFilter(field_name='line_id')
    product = django_filters.NumberFilter(field_name='product_id')
    plan_date = django_filters.DateFilter(field_name='plan_date')
    plan_date__gte = django_filters.DateFilter(field_name='plan_date', lookup_expr='gte')
    plan_date__lte = django_filters.DateFilter(field_name='plan_date', lookup_expr='lte')

    class Meta:
        model = LineGanttPlan
        fields = []


class ProductionPlanChangeLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductionPlanChangeLog.objects.all().select_related('line', 'process', 'product', 'changed_by')
    serializer_class = ProductionPlanChangeLogSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductionPlanChangeLogFilter
    search_fields = [
        'product__product_code',
        'product__product_name',
        'process__process_code',
        'process__process_name',
        'line__line_code',
        'line__line_name',
        'reason',
        'changed_by__username',
        'changed_by__first_name',
        'changed_by__last_name',
    ]
    ordering_fields = ['changed_at', 'plan_date', 'line', 'process', 'product', 'before_qty', 'after_qty']
    ordering = ['-changed_at', '-id']


class LinePlanViewSet(viewsets.ModelViewSet):
    queryset = LinePlan.objects.all().select_related('process', 'product', 'line')
    serializer_class = LinePlanSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = LinePlanFilter
    ordering_fields = ['plan_date', 'line', 'product']
    ordering = ['plan_date', 'line']

    @action(detail=False, methods=['post'], url_path='bulk-delete')
    def bulk_delete(self, request):
        """
        選択ライン・期間のLinePlan/LineGanttPlanを一括削除する
        期待payload: { line_id, start_date, end_date }
        """
        line_id = request.data.get('line_id')
        start_date_raw = request.data.get('start_date')
        end_date_raw = request.data.get('end_date')

        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not start_date_raw or not end_date_raw:
            return Response({'detail': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_date = datetime.strptime(str(start_date_raw), '%Y-%m-%d').date()
            end_date = datetime.strptime(str(end_date_raw), '%Y-%m-%d').date()
        except Exception:
            return Response({'detail': 'start_date/end_date must be YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

        if start_date > end_date:
            return Response({'detail': 'start_date must be <= end_date'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            deleted_plan_result = LinePlan.objects.filter(
                line_id=line_id,
                plan_date__gte=start_date,
                plan_date__lte=end_date,
            ).delete()
            deleted_gantt_result = LineGanttPlan.objects.filter(
                line_id=line_id,
                plan_date__gte=start_date,
                plan_date__lte=end_date,
            ).exclude(plan_id__startswith='SINGLEPROC_').delete()
            deleted_backlog_result = LineBacklog.objects.filter(
                line_id=line_id,
                plan_date__gte=start_date,
                plan_date__lte=end_date,
            ).exclude(sequence_no=0).exclude(plan_id__startswith='SINGLEPROC_').delete()

        deleted_plan = deleted_plan_result[0] if deleted_plan_result else 0
        deleted_gantt = deleted_gantt_result[0] if deleted_gantt_result else 0
        deleted_backlog = deleted_backlog_result[0] if deleted_backlog_result else 0

        return Response({
            'deleted_plan': deleted_plan,
            'deleted_gantt': deleted_gantt,
            'deleted_backlog': deleted_backlog,
            'line_id': line_id,
            'start_date': str(start_date),
            'end_date': str(end_date),
        })

    @action(detail=False, methods=['post'])
    def save(self, request):
        """
        ユーザーが入力した計画データをLinePlanに保存する
        期待payload: { line_id, items: [{product_id, process_id, plan_date, plan_qty?, sequence_no?}] }

        保存前に、該当ライン・日付・製品のすべてのLinePlanとLineGanttPlanを削除してから新規作成する
        """
        line_id = request.data.get('line_id')
        items = request.data.get('items', [])
        replace_dates = request.data.get('replace_dates', [])
        replace_product_ids = request.data.get('replace_product_ids', [])
        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(items, list):
            return Response({'detail': 'items must be a list'}, status=status.HTTP_400_BAD_REQUEST)
        if replace_dates and not isinstance(replace_dates, list):
            return Response({'detail': 'replace_dates must be a list'}, status=status.HTTP_400_BAD_REQUEST)
        if replace_product_ids and not isinstance(replace_product_ids, list):
            return Response({'detail': 'replace_product_ids must be a list'}, status=status.HTTP_400_BAD_REQUEST)
        if not items and not replace_dates:
            return Response({'detail': 'items or replace_dates is required'}, status=status.HTTP_400_BAD_REQUEST)
        line_obj = Line.objects.filter(id=line_id, is_active=True).only('id', 'line_code', 'line_name').first()
        if not line_obj:
            return Response({'detail': 'line not found'}, status=status.HTTP_400_BAD_REQUEST)
        raw_reason = request.data.get('change_reason')
        change_reason = None
        if raw_reason is not None:
            change_reason = str(raw_reason).strip()
            if not change_reason:
                return Response({'detail': 'change_reason is required'}, status=status.HTTP_400_BAD_REQUEST)

        from masters.models import Product
        from django.db import transaction

        def parse_plan_date(raw_date):
            if isinstance(raw_date, str):
                return datetime.strptime(raw_date, '%Y-%m-%d').date()
            return raw_date

        # 対象となる日付と製品を抽出
        affected_dates = set()
        affected_products = set()
        floor_shipping_plan_counts = {}
        for raw_date in replace_dates:
            try:
                affected_dates.add(parse_plan_date(raw_date))
            except Exception:
                continue
        for raw_product_id in replace_product_ids:
            try:
                product_id = int(raw_product_id)
            except (TypeError, ValueError):
                continue
            if product_id > 0:
                affected_products.add(product_id)
        for it in items:
            plan_date = it.get('plan_date')
            product_id = it.get('product_id')
            if plan_date and product_id:
                plan_date_obj = parse_plan_date(plan_date)
                affected_dates.add(plan_date_obj)
                affected_products.add(product_id)
                if _is_floor_shipping_delivery_line(line_obj):
                    try:
                        plan_qty_value = Decimal(str(it.get('plan_qty') or 0))
                    except Exception:
                        plan_qty_value = Decimal('0')
                    if plan_qty_value > 0:
                        count_key = (product_id, plan_date_obj)
                        floor_shipping_plan_counts[count_key] = floor_shipping_plan_counts.get(count_key, 0) + 1

        if _is_floor_shipping_delivery_line(line_obj):
            invalid_keys = [
                (product_id, plan_date_obj, count)
                for (product_id, plan_date_obj), count in floor_shipping_plan_counts.items()
                if count > 2
            ]
            if invalid_keys:
                product_ids = {product_id for product_id, _, _ in invalid_keys}
                product_code_map = {
                    product.id: product.product_code
                    for product in Product.objects.filter(id__in=product_ids).only('id', 'product_code')
                }
                first_product_id, first_plan_date, first_count = invalid_keys[0]
                product_label = product_code_map.get(first_product_id, str(first_product_id))
                return Response(
                    {'detail': f'フロア配送は同一日・同一品番で2件までです: {product_label} {first_plan_date} ({first_count}件)'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        created = 0
        deleted_plan = 0
        deleted_gantt = 0
        deleted_backlog = 0
        skipped = []
        product_cache = {}
        next_seq_cache = {}
        existing_plan_map = {}
        change_user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

        def get_next_sequence(plan_date_obj):
            """自動採番: 日付ごとに連番を生成"""
            cache_key = (line_id, plan_date_obj)
            if cache_key not in next_seq_cache:
                next_seq_cache[cache_key] = 1
            next_seq = next_seq_cache[cache_key]
            next_seq_cache[cache_key] = next_seq + 1
            return next_seq

        def record_change(before_qty, after_qty, plan_date_obj, product_id, process_id, line_id_val, sequence_no_val, plan_id_val):
            if not change_reason:
                return
            if before_qty == after_qty:
                return
            ProductionPlanChangeLog.objects.create(
                plan_date=plan_date_obj,
                product_id=product_id,
                process_id=process_id,
                line_id=line_id_val,
                sequence_no=sequence_no_val,
                plan_id=plan_id_val,
                before_qty=before_qty,
                after_qty=after_qty,
                reason=change_reason,
                changed_by=change_user,
            )

        indexed_items = list(enumerate(items))

        def _to_int_or_none(value):
            if value is None or value == '':
                return None
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        def _item_sort_key(indexed_item):
            original_idx, item = indexed_item
            plan_date_raw = item.get('plan_date')
            try:
                plan_date_obj = parse_plan_date(plan_date_raw)
            except Exception:
                plan_date_obj = date.max
            display_order = _to_int_or_none(item.get('display_order'))
            if display_order is None:
                display_order = 10**9
            return (plan_date_obj, display_order, original_idx)

        sorted_items = sorted(indexed_items, key=_item_sort_key)

        # トランザクション内で削除→作成を実行
        with transaction.atomic():
            if change_reason and affected_dates and affected_products:
                existing_plans = LinePlan.objects.filter(
                    line_id=line_id,
                    plan_date__in=affected_dates,
                    product_id__in=affected_products
                )
                for plan in existing_plans:
                    key = (plan.product_id, plan.process_id, plan.plan_date, plan.sequence_no)
                    existing_plan_map[key] = plan
            # 1. 該当LinePlanのplan_idを先に取得
            if affected_dates and affected_products:
                existing_plan_ids = list(LinePlan.objects.filter(
                    line_id=line_id,
                    plan_date__in=affected_dates,
                    product_id__in=affected_products
                ).values_list('plan_id', flat=True))

                # 2. 該当ライン・日付・製品のLinePlanを削除
                deleted_plan_result = LinePlan.objects.filter(
                    line_id=line_id,
                    plan_date__in=affected_dates,
                    product_id__in=affected_products
                ).delete()
                deleted_plan = deleted_plan_result[0] if deleted_plan_result else 0

                # 3. 該当ライン・日付・製品のLineGanttPlanを削除（単独計画行は保護）
                deleted_gantt_result = LineGanttPlan.objects.filter(
                    line_id=line_id,
                    plan_date__in=affected_dates,
                    product_id__in=affected_products
                ).exclude(plan_id__startswith='SINGLEPROC_').delete()
                deleted_gantt = deleted_gantt_result[0] if deleted_gantt_result else 0

                # 4. 該当ライン・日付・製品のLineBacklogを削除（計画レコードのみ、単独計画行は保護）
                # ルール: sequence_no > 0 のレコードは計画レコードとして削除（自動計画・手動計画問わず）
                #        sequence_no = 0 は在庫・需要・仕損などの基礎データとして保持
                #        sequence_no = NULL は実績レコードとして保持
                deleted_backlog_result = LineBacklog.objects.filter(
                    line_id=line_id,
                    plan_date__in=affected_dates,
                    product_id__in=affected_products,
                    sequence_no__gt=0,
                ).exclude(plan_id__startswith='SINGLEPROC_').delete()
                deleted_backlog = deleted_backlog_result[0] if deleted_backlog_result else 0

            # 4. 新規作成
            for _original_idx, it in sorted_items:
                try:
                    product_id = it.get('product_id')
                    process_id = it.get('process_id')
                    plan_date = it.get('plan_date')
                    if not product_id or not process_id or not plan_date:
                        skipped.append({'item': it, 'reason': 'product_id/process_id/plan_date required'})
                        continue

                    plan_qty_value = Decimal(str(it.get('plan_qty') or 0))
                    plan_date_obj = parse_plan_date(plan_date)

                    seq_in = it.get('sequence_no')
                    if seq_in in (None, '', 0):
                        # sequence_noが指定されていない場合は自動採番
                        if plan_qty_value > 0:
                            sequence_no = get_next_sequence(plan_date_obj)
                        else:
                            skipped.append({'item': it, 'reason': 'sequence_no required for zero quantity'})
                            continue
                    else:
                        try:
                            sequence_no = int(seq_in)
                        except (TypeError, ValueError):
                            skipped.append({'item': it, 'reason': 'invalid sequence_no'})
                            continue

                    existing_key = (product_id, process_id, plan_date_obj, sequence_no)
                    existing_plan = existing_plan_map.pop(existing_key, None)
                    before_qty = int(existing_plan.plan_qty or 0) if existing_plan else 0
                    before_plan_id = existing_plan.plan_id if existing_plan else None

                    # plan_qty <= 0 の場合はスキップ（既に削除済み）
                    if plan_qty_value <= 0:
                        record_change(
                            before_qty,
                            0,
                            plan_date_obj,
                            product_id,
                            process_id,
                            line_id,
                            sequence_no,
                            before_plan_id,
                        )
                        continue

                    if product_id not in product_cache:
                        try:
                            product = Product.objects.get(id=product_id)
                            product_cache[product_id] = product
                        except Product.DoesNotExist:
                            skipped.append({'item': it, 'reason': 'product not found'})
                            continue
                    product = product_cache[product_id]
                    product_code = product.product_code

                    qty_label = str(plan_qty_value).rstrip('0').rstrip('.')
                    if '.' in qty_label:
                        qty_label = qty_label.replace('.', 'p')

                    plan_id = f"{product_code}_{plan_date_obj.strftime('%Y%m%d')}_{qty_label}_{sequence_no}"

                    # 新規作成
                    LinePlan.objects.create(
                        plan_date=plan_date_obj,
                        process_id=process_id,
                        product_id=product_id,
                        line_id=line_id,
                        plan_qty=int(plan_qty_value),
                        plan_id=plan_id,
                        sequence_no=sequence_no,
                    )
                    # LineBacklogにも計画レコードを作成（sequence_no > 0）
                    # 既存の sequence_no=0 行（需要・在庫基礎データ）はそのまま保持
                    LineBacklog.objects.create(
                        plan_date=plan_date_obj,
                        process_id=process_id,
                        product_id=product_id,
                        line_id=line_id,
                        plan_qty=int(plan_qty_value),
                        plan_id=plan_id,
                        sequence_no=sequence_no,
                    )
                    created += 1
                    record_change(
                        before_qty,
                        int(plan_qty_value),
                        plan_date_obj,
                        product_id,
                        process_id,
                        line_id,
                        sequence_no,
                        plan_id,
                    )

                except Exception as e:
                    return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

            if change_reason:
                for plan in existing_plan_map.values():
                    record_change(
                        int(plan.plan_qty or 0),
                        0,
                        plan.plan_date,
                        plan.product_id,
                        plan.process_id,
                        line_id,
                        plan.sequence_no,
                        plan.plan_id,
                    )

        # チェックシートバッチ自動生成（製品の全工程テンプレート分を発行）
        try:
            from quality.services_checksheet import active_templates_for_product, prepare_batch as cs_prepare_batch
            from masters.models import Process as ProcessModel
            process_cache = {}
            processed_product_dates = set()
            for it in items:
                product_id = it.get('product_id')
                process_id = it.get('process_id')
                plan_date = it.get('plan_date')
                plan_qty_val = int(Decimal(str(it.get('plan_qty') or 0)))
                if not product_id or not process_id or not plan_date or plan_qty_val <= 0:
                    continue
                prod = product_cache.get(product_id)
                if not prod or not getattr(prod, 'is_line_final_product', False):
                    continue
                cache_key = (product_id, plan_date)
                if cache_key in processed_product_dates:
                    continue
                processed_product_dates.add(cache_key)
                templates = active_templates_for_product(product_id)
                if not templates:
                    continue
                plan_date_obj = parse_plan_date(plan_date)
                for tmpl in templates:
                    tmpl_process_id = tmpl.process_id
                    if tmpl_process_id not in process_cache:
                        try:
                            process_cache[tmpl_process_id] = ProcessModel.objects.get(id=tmpl_process_id)
                        except ProcessModel.DoesNotExist:
                            continue
                    cs_prepare_batch(
                        template=tmpl,
                        line=tmpl.line,
                        process=process_cache[tmpl_process_id],
                        product=prod,
                        quantity=plan_qty_val,
                        plan_date=plan_date_obj,
                        user=change_user,
                    )
        except Exception:
            logger.exception("チェックシートバッチ自動生成でエラー")

        return Response({
            'created': created,
            'deleted_plan': deleted_plan,
            'deleted_gantt': deleted_gantt,
            'deleted_backlog': deleted_backlog,
            'skipped': skipped
        })


class LineBacklogViewSet(viewsets.ModelViewSet):
    queryset = LineBacklog.objects.all().select_related('process', 'product', 'line', 'source_routing_step')
    serializer_class = LineBacklogSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = LineBacklogFilter
    ordering_fields = ['plan_date', 'line', 'product']
    ordering = ['plan_date', 'line']

    def list(self, request, *args, **kwargs):
        include_split = request.query_params.get('include_order_split')
        include_split = str(include_split).lower() in ['true', '1', 'yes']

        if not include_split:
            return super().list(request, *args, **kwargs)

        queryset = self.filter_queryset(self.get_queryset())
        items = list(queryset)
        self._attach_order_split(items)
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='delete-progress-group')
    def delete_progress_group(self, request):
        """
        進度のみ画面から、表示期間内の基礎データ行(sequence_no=0)を
        ライン・工程・品番単位で削除する。
        """
        line_id = request.data.get('line_id')
        process_id = request.data.get('process_id')
        product_id = request.data.get('product_id')
        start_date_raw = request.data.get('start_date')
        end_date_raw = request.data.get('end_date')

        if not line_id or not process_id or not product_id:
            return Response({'detail': 'line_id, process_id, product_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not start_date_raw or not end_date_raw:
            return Response({'detail': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            line_id = int(line_id)
            process_id = int(process_id)
            product_id = int(product_id)
            start_date = datetime.strptime(str(start_date_raw), '%Y-%m-%d').date()
            end_date = datetime.strptime(str(end_date_raw), '%Y-%m-%d').date()
        except Exception:
            return Response({'detail': 'invalid payload'}, status=status.HTTP_400_BAD_REQUEST)

        if start_date > end_date:
            return Response({'detail': 'start_date must be <= end_date'}, status=status.HTTP_400_BAD_REQUEST)

        target_qs = LineBacklog.objects.filter(
            line_id=line_id,
            process_id=process_id,
            product_id=product_id,
            plan_date__gte=start_date,
            plan_date__lte=end_date,
            sequence_no=0,
        )
        preview_rows = list(target_qs.values('id', 'plan_date', 'line_id', 'process_id', 'product_id'))
        deleted_result = target_qs.delete()
        deleted_count = deleted_result[0] if deleted_result else 0

        return Response({
            'deleted': deleted_count,
            'line_id': line_id,
            'process_id': process_id,
            'product_id': product_id,
            'start_date': str(start_date),
            'end_date': str(end_date),
            'sample_rows': preview_rows[:20],
        })

    @action(detail=False, methods=['post'], url_path='seed_progress_backlogs_from_demand')
    def seed_progress_backlogs_from_demand(self, request):
        return backlog_pickup_service.seed_progress_backlogs_from_demand(
            self,
            request,
            parse_optional_date=_parse_optional_date,
            parse_product_ids=_parse_product_ids,
            invalid_sequence_sort_value=INVALID_SEQUENCE_SORT_VALUE,
            floor_shipping_pm_sequence_threshold=FLOOR_SHIPPING_PM_SEQUENCE_THRESHOLD,
            is_floor_shipping_delivery_line=_is_floor_shipping_delivery_line,
            is_kubota_delivery_line=_is_kubota_delivery_line,
        )

    def _attach_order_split(self, items):
        from collections import defaultdict
        from django.db.models import Q

        if not items:
            return

        line_ids = {item.line_id for item in items if item.line_id}
        if not line_ids:
            return

        line_map = {line.id: line for line in Line.objects.filter(id__in=line_ids)}
        default_calendar_id = Calendar.objects.filter(calendar_code='daiso').values_list('id', flat=True).first()

        items_by_line = defaultdict(list)
        for item in items:
            items_by_line[item.line_id].append(item)

        for line_id, line_items in items_by_line.items():
            dates = [it.plan_date for it in line_items if it.plan_date]
            if not dates:
                continue

            min_date = min(dates)
            max_date = max(dates)

            line_obj = line_map.get(line_id)
            calendar_id = getattr(line_obj, 'calendar_id', None) or default_calendar_id

            unique_dates = sorted(set(dates))
            routing_q = build_effective_routing_q(unique_dates[0], prefix='routing__')
            for d in unique_dates[1:]:
                routing_q = routing_q | build_effective_routing_q(d, prefix='routing__')
            steps_on_line = RoutingStep.objects.filter(
                line_id=line_id
            ).filter(
                routing_q
            ).select_related('output_product', 'routing__product', 'line')

            final_products = set()
            for step in steps_on_line:
                product = step.output_product or (step.routing.product if step.routing_id else None)
                if product and product.is_final_product:
                    final_products.add(product.id)

            if not final_products:
                continue

            # LineDemandから確定/内示数量を取得（LTシフト済みのplan_dateを使用）
            demands = LineDemand.objects.filter(
                line_id=line_id,
                product_id__in=final_products,
                plan_date__gte=min_date,
                plan_date__lte=max_date,
            )

            firm_map = defaultdict(int)
            forecast_map = defaultdict(int)
            for ld in demands:
                key = (ld.product_id, ld.plan_date)
                firm_map[key] += int(ld.firm_qty or 0)
                forecast_map[key] += int(ld.forecast_qty or 0)

            for item in line_items:
                if item.product_id not in final_products:
                    continue
                key = (item.product_id, item.plan_date)
                item.firm_order_qty = firm_map.get(key, 0)
                item.forecast_order_qty = forecast_map.get(key, 0)

    @action(detail=False, methods=['post'], url_path='resolve_upstream_lines')
    def resolve_upstream_lines(self, request):
        return backlog_pickup_service.resolve_upstream_lines(
            self,
            request,
            parse_optional_date=_parse_optional_date,
            parse_product_ids=_parse_product_ids,
            invalid_sequence_sort_value=INVALID_SEQUENCE_SORT_VALUE,
            floor_shipping_pm_sequence_threshold=FLOOR_SHIPPING_PM_SEQUENCE_THRESHOLD,
            is_floor_shipping_delivery_line=_is_floor_shipping_delivery_line,
            is_kubota_delivery_line=_is_kubota_delivery_line,
        )

    @action(detail=False, methods=['post'])
    def pickup(self, request):
        return backlog_pickup_service.pickup(
            self,
            request,
            parse_optional_date=_parse_optional_date,
            parse_product_ids=_parse_product_ids,
            invalid_sequence_sort_value=INVALID_SEQUENCE_SORT_VALUE,
            floor_shipping_pm_sequence_threshold=FLOOR_SHIPPING_PM_SEQUENCE_THRESHOLD,
            is_floor_shipping_delivery_line=_is_floor_shipping_delivery_line,
            is_kubota_delivery_line=_is_kubota_delivery_line,
        )

    @action(detail=False, methods=['post'], url_path='pickup_for_products')
    def pickup_for_products(self, request):
        return backlog_pickup_service.pickup_for_products(
            self,
            request,
            parse_optional_date=_parse_optional_date,
            parse_product_ids=_parse_product_ids,
            invalid_sequence_sort_value=INVALID_SEQUENCE_SORT_VALUE,
            floor_shipping_pm_sequence_threshold=FLOOR_SHIPPING_PM_SEQUENCE_THRESHOLD,
            is_floor_shipping_delivery_line=_is_floor_shipping_delivery_line,
            is_kubota_delivery_line=_is_kubota_delivery_line,
        )

    @action(detail=False, methods=['post'], url_path='pickup_purchase')
    def pickup_purchase(self, request):
        return backlog_pickup_service.pickup_purchase(
            self,
            request,
            parse_optional_date=_parse_optional_date,
            parse_product_ids=_parse_product_ids,
            invalid_sequence_sort_value=INVALID_SEQUENCE_SORT_VALUE,
            floor_shipping_pm_sequence_threshold=FLOOR_SHIPPING_PM_SEQUENCE_THRESHOLD,
            is_floor_shipping_delivery_line=_is_floor_shipping_delivery_line,
            is_kubota_delivery_line=_is_kubota_delivery_line,
        )

    @action(detail=False, methods=['post'], url_path='pickup_purchase_for_products')
    def pickup_purchase_for_products(self, request):
        return backlog_pickup_service.pickup_purchase_for_products(
            self,
            request,
            parse_optional_date=_parse_optional_date,
            parse_product_ids=_parse_product_ids,
            invalid_sequence_sort_value=INVALID_SEQUENCE_SORT_VALUE,
            floor_shipping_pm_sequence_threshold=FLOOR_SHIPPING_PM_SEQUENCE_THRESHOLD,
            is_floor_shipping_delivery_line=_is_floor_shipping_delivery_line,
            is_kubota_delivery_line=_is_kubota_delivery_line,
        )

    @action(detail=False, methods=['post'])
    def expand_processes(self, request):
        return backlog_pickup_service.expand_processes(
            self,
            request,
            parse_optional_date=_parse_optional_date,
            parse_product_ids=_parse_product_ids,
            invalid_sequence_sort_value=INVALID_SEQUENCE_SORT_VALUE,
            floor_shipping_pm_sequence_threshold=FLOOR_SHIPPING_PM_SEQUENCE_THRESHOLD,
            is_floor_shipping_delivery_line=_is_floor_shipping_delivery_line,
            is_kubota_delivery_line=_is_kubota_delivery_line,
        )

    @action(detail=False, methods=['post'])
    def save(self, request):
        """
        ユーザーが入力した計画データをLineBacklogに保存する
        期待payload: { line_id, items: [{product_id, process_id, plan_date, plan_qty?, actual_qty?, stock_qty?, planned_stock_qty?, adjust_qty?, sequence_no?}] }

        plan_id ロジック:
        - plan_id = 製品コード_日付_数量_順番
        - 数量が変更されるとplan_idが変わるため、古いplan_idのレコードを削除
        - plan_qty=0の場合もplan_idに紐づくレコードを削除
        """
        line_id = request.data.get('line_id')
        items = request.data.get('items', [])
        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(items, list) or not items:
            return Response({'detail': 'items is required'}, status=status.HTTP_400_BAD_REQUEST)

        created = 0
        updated = 0
        deleted = 0
        skipped = []
        change_reason = request.data.get('change_reason')
        if isinstance(change_reason, str):
            change_reason = change_reason.strip()
        if not change_reason:
            change_reason = None

        # まず、製品コードを取得するために製品IDから製品情報を取得
        from masters.models import Product
        product_cache = {}
        plan_date_cache = {}
        change_user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

        def parse_plan_date(raw_date):
            if raw_date in plan_date_cache:
                return plan_date_cache[raw_date]
            if isinstance(raw_date, str):
                parsed = datetime.strptime(raw_date, '%Y-%m-%d').date()
            else:
                parsed = raw_date
            plan_date_cache[raw_date] = parsed
            return parsed

        def record_change(plan_date_value, product_id, process_id, line_id, before_qty, after_qty, plan_id_value, sequence_no_value):
            if not change_reason:
                return
            if before_qty == after_qty:
                return
            from purchase.models import PurchasePlanChangeLog
            PurchasePlanChangeLog.objects.create(
                plan_date=plan_date_value,
                product_id=product_id,
                process_id=process_id,
                line_id=line_id,
                sequence_no=sequence_no_value,
                plan_id=plan_id_value,
                before_qty=before_qty,
                after_qty=after_qty,
                reason=change_reason,
                changed_by=change_user,
            )

        for it in items:
            try:
                product_id = it.get('product_id')
                process_id = it.get('process_id')
                plan_date = it.get('plan_date')
                if not product_id or not process_id or not plan_date:
                    skipped.append({'item': it, 'reason': 'product_id/process_id/plan_date required'})
                    continue

                # 製品情報を取得（キャッシュを使用）
                if product_id not in product_cache:
                    try:
                        product = Product.objects.get(id=product_id)
                        product_cache[product_id] = product
                    except Product.DoesNotExist:
                        skipped.append({'item': it, 'reason': 'product not found'})
                        continue
                product = product_cache[product_id]
                product_code = product.product_code

                # plan_qty=0 の場合、plan_idに紐づくレコードを削除
                plan_qty_provided = 'plan_qty' in it
                plan_qty_value = None
                existing_plan_qty = 0
                existing_plan_id = None
                existing_sequence_no = None
                if plan_qty_provided:
                    plan_qty_value = Decimal(str(it['plan_qty'] or 0))
                    if plan_qty_value == 0:
                        # 既存レコードを取得（sequence_noで絞り込み）
                        _seq_for_zero = it.get('sequence_no') if it.get('sequence_no') is not None else 0
                        existing = LineBacklog.objects.filter(
                            plan_date=plan_date,
                            process_id=process_id,
                            product_id=product_id,
                            line_id=line_id,
                            sequence_no=_seq_for_zero,
                        ).first()

                        if existing and existing.plan_id:
                            existing_plan_qty = int(existing.plan_qty or 0)
                            existing_plan_id = existing.plan_id
                            existing_sequence_no = existing.sequence_no
                            ProductionOrder.objects.filter(order_no=existing.plan_id).delete()
                            # plan_idに紐づく全てのLineBacklogレコードを削除
                            deleted_count = LineBacklog.objects.filter(plan_id=existing.plan_id).delete()[0]
                            deleted += deleted_count
                            record_change(
                                parse_plan_date(plan_date),
                                product_id,
                                process_id,
                                line_id,
                                existing_plan_qty,
                                0,
                                existing_plan_id,
                                existing_sequence_no,
                            )
                            continue
                        elif existing:
                            existing_plan_qty = int(existing.plan_qty or 0)
                            existing_plan_id = existing.plan_id
                            existing_sequence_no = existing.sequence_no
                            # plan_idが無い場合は従来のロジック
                            def resolve_qty(field_name):
                                if field_name in it:
                                    return Decimal(str(it[field_name] or 0))
                                return Decimal(str(getattr(existing, field_name, 0) or 0))

                            actual_qty = resolve_qty('actual_qty')
                            stock_qty = resolve_qty('stock_qty')
                            planned_stock_qty = resolve_qty('planned_stock_qty')
                            adjust_qty = resolve_qty('adjust_qty')
                            order_qty = Decimal(str(existing.order_qty or 0))
                            demand_qty_plan = Decimal(str(existing.demand_qty_plan or 0))
                            seq_in = it.get('sequence_no', existing.sequence_no)
                            seq_val = 0 if seq_in is None else seq_in

                            if (
                                actual_qty == 0
                                and stock_qty == 0
                                and planned_stock_qty == 0
                                and adjust_qty == 0
                                and order_qty == 0
                                and demand_qty_plan == 0
                                and seq_val in (0, None, '')
                            ):
                                existing.delete()
                                deleted += 1
                                record_change(
                                    parse_plan_date(plan_date),
                                    product_id,
                                    process_id,
                                    line_id,
                                    existing_plan_qty,
                                    0,
                                    existing_plan_id,
                                    existing_sequence_no,
                                )
                                continue

                # sequence_noを取得（デフォルトは0）
                sequence_no = it.get('sequence_no')
                if sequence_no is None:
                    sequence_no = 0

                # 既存レコードを取得（sequence_noで絞り込み）
                existing = LineBacklog.objects.filter(
                    plan_date=plan_date,
                    process_id=process_id,
                    product_id=product_id,
                    line_id=line_id,
                    sequence_no=sequence_no,
                ).first()
                if existing:
                    existing_plan_qty = int(existing.plan_qty or 0)
                    existing_plan_id = existing.plan_id
                    existing_sequence_no = existing.sequence_no

                new_plan_id = None
                plan_date_obj = None
                if plan_qty_provided:
                    # plan_idを生成: 製品コード_YYYYMMDD_数量_順番
                    # gantt_planning.pyと同じフォーマットを使用
                    plan_date_obj = parse_plan_date(plan_date)

                    # 数量ラベルを生成（小数点以下の0を除去、小数点を'p'に変換）
                    qty_label = str(plan_qty_value).rstrip('0').rstrip('.')
                    if '.' in qty_label:
                        qty_label = qty_label.replace('.', 'p')

                    new_plan_id = f"{product_code}_{plan_date_obj.strftime('%Y%m%d')}_{qty_label}_{sequence_no}"

                    # 既存レコードがあり、plan_idが変更された場合、古いplan_idのレコードを削除
                    if existing and existing.plan_id and existing.plan_id != new_plan_id:
                        # 古いplan_idに紐づく全てのLineBacklogレコードを削除
                        old_plan_id = existing.plan_id
                        LineBacklog.objects.filter(plan_id=old_plan_id).delete()
                        ProductionOrder.objects.filter(order_no=old_plan_id).delete()
                        # existingは削除されたので、新規作成扱いになる
                        existing = None

                # 更新するフィールドを準備
                defaults = {}
                if plan_qty_provided:
                    defaults['plan_id'] = new_plan_id
                    defaults['plan_qty'] = plan_qty_value
                if 'actual_qty' in it:
                    defaults['actual_qty'] = Decimal(str(it['actual_qty']))
                if 'stock_qty' in it:
                    defaults['stock_qty'] = Decimal(str(it['stock_qty']))
                if 'planned_stock_qty' in it:
                    defaults['planned_stock_qty'] = Decimal(str(it['planned_stock_qty']))
                if 'adjust_qty' in it:
                    defaults['adjust_qty'] = Decimal(str(it['adjust_qty']))
                if 'sequence_no' in it:
                    defaults['sequence_no'] = sequence_no

                # LineBacklogに保存（sequence_noを検索条件に含める）
                defaults.pop('sequence_no', None)
                obj, is_created = LineBacklog.objects.update_or_create(
                    plan_date=plan_date,
                    process_id=process_id,
                    product_id=product_id,
                    line_id=line_id,
                    sequence_no=sequence_no,
                    defaults=defaults
                )
                if is_created:
                    created += 1
                else:
                    updated += 1

                if plan_qty_provided and plan_qty_value is not None:
                    after_qty = int(plan_qty_value)
                    record_change(
                        plan_date_obj or parse_plan_date(plan_date),
                        product_id,
                        process_id,
                        line_id,
                        existing_plan_qty,
                        after_qty,
                        new_plan_id or existing_plan_id,
                        sequence_no if 'sequence_no' in it or sequence_no is not None else existing_sequence_no,
                    )

                if plan_qty_provided and plan_qty_value is not None and plan_qty_value > 0 and new_plan_id:
                    routing = resolve_effective_routing(product_id, plan_date_obj)
                    ProductionOrder.objects.update_or_create(
                        order_no=new_plan_id,
                        defaults={
                            'product_id': product_id,
                            'routing_id': routing.id if routing else None,
                            'line_id': line_id,
                            'order_qty': plan_qty_value,
                            'scheduled_start_date': plan_date_obj,
                            'scheduled_end_date': plan_date_obj,
                            'priority': sequence_no or 0,
                        }
                    )
            except Exception as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'created': created, 'updated': updated, 'deleted': deleted, 'skipped': skipped})

    def _parse_stocktake_file(self, upload_file):
        """
        棚卸ファイル（xlsx/csv）を読み込み、品番ごとの数量に集約する。
        期待列: 製品番号, 製品名(任意), 数量
        """
        filename = (upload_file.name or '').lower()
        aggregated = {}
        row_count = 0

        def parse_qty(raw_value, row_no):
            text = '' if raw_value is None else str(raw_value).strip()
            if text == '':
                raise ValueError(f'数量が未入力です (行={row_no})')
            text = text.replace(',', '')
            try:
                qty = Decimal(text)
            except InvalidOperation:
                raise ValueError(f'数量が不正です: "{raw_value}" (行={row_no})')
            if qty < 0:
                raise ValueError(f'数量は0以上にしてください (行={row_no})')
            return qty

        def add_row(product_code, qty, row_no):
            if product_code is None:
                raise ValueError(f'製品番号が未入力です (行={row_no})')
            # Excelが数値型で読み込んだ場合の対応（26.0 → "26"）
            if isinstance(product_code, float) and product_code == int(product_code):
                code = str(int(product_code))
            else:
                code = str(product_code).strip()
            if not code:
                raise ValueError(f'製品番号が未入力です (行={row_no})')
            aggregated[code] = aggregated.get(code, Decimal('0')) + qty

        if filename.endswith('.xlsx'):
            from openpyxl import load_workbook

            wb = load_workbook(upload_file, data_only=True, read_only=True)
            ws = wb.active
            header = [str(v).strip() if v is not None else '' for v in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
            try:
                product_col = header.index('製品番号')
                qty_col = header.index('数量')
            except ValueError:
                raise ValueError('ヘッダーに「製品番号」「数量」列が必要です')

            for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                product_val = row[product_col] if product_col < len(row) else None
                qty_val = row[qty_col] if qty_col < len(row) else None
                if product_val in [None, ''] and qty_val in [None, '']:
                    continue
                qty = parse_qty(qty_val, idx)
                add_row(product_val, qty, idx)
                row_count += 1

        elif filename.endswith('.csv'):
            raw = upload_file.read()
            try:
                text = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = raw.decode('cp932')
            reader = csv.DictReader(io.StringIO(text))
            if not reader.fieldnames:
                raise ValueError('CSVヘッダーがありません')
            names = {name.strip() for name in reader.fieldnames if name}
            if '製品番号' not in names or '数量' not in names:
                raise ValueError('CSVヘッダーに「製品番号」「数量」列が必要です')

            for idx, row in enumerate(reader, start=2):
                product_val = row.get('製品番号')
                qty_val = row.get('数量')
                if (product_val is None or str(product_val).strip() == '') and (qty_val is None or str(qty_val).strip() == ''):
                    continue
                qty = parse_qty(qty_val, idx)
                add_row(product_val, qty, idx)
                row_count += 1
        else:
            raise ValueError('.xlsx または .csv ファイルを指定してください')

        if not aggregated:
            raise ValueError('棚卸データが見つかりません')

        return {
            'row_count': row_count,
            'rows': aggregated,
        }

    @action(detail=False, methods=['get'])
    def download_stocktake_template(self, request):
        """
        棚卸取込用テンプレートExcelを返す。
        """
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = 'stocktake'
        ws.append(['製品番号', '製品名', '数量'])
        ws.append(['ABC-001', 'サンプル製品A', 1500])
        ws.append(['ABC-002', 'サンプル製品B', 800.5])
        ws.append(['DEF-003', 'サンプル製品C', 0])

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="stocktake_template.xlsx"'
        return response

    @action(
        detail=False,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_stocktake_excel(self, request):
        """
        棚卸Excel/CSVを取り込み、在庫初期値を反映する。

        期待payload:
        - file: xlsx/csv
        - stocktake_date: YYYY-MM-DD
        """
        from .inventory.stocktake_initializer import (
            get_progress_upper_bound_date,
            _collect_stocktake_mapping_keys,
        )

        upload_file = request.FILES.get('file')
        stocktake_date_raw = request.data.get('stocktake_date')
        location = (request.data.get('location') or 'MAIN').strip() or 'MAIN'

        if not upload_file:
            return Response({'detail': 'file is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not stocktake_date_raw:
            return Response({'detail': 'stocktake_date is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            stocktake_date = datetime.strptime(str(stocktake_date_raw), '%Y-%m-%d').date()
        except ValueError as e:
            return Response({'detail': f'Invalid stocktake_date format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            parsed = self._parse_stocktake_file(upload_file)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        product_codes = list(parsed['rows'].keys())
        products = Product.objects.filter(product_code__in=product_codes).values('id', 'product_code')
        product_id_by_code = {p['product_code']: p['id'] for p in products}
        product_code_by_id = {pid: code for code, pid in product_id_by_code.items()}
        missing_codes = sorted([c for c in product_codes if c not in product_id_by_code])
        if missing_codes:
            return Response(
                {'detail': 'unknown product_code found', 'missing_product_codes': missing_codes},
                status=status.HTTP_400_BAD_REQUEST,
            )

        upper_bound_date = get_progress_upper_bound_date()
        baseline_date = stocktake_date

        allocation_created = 0
        allocation_updated = 0
        backlog_created = 0
        backlog_updated = 0

        try:
            with transaction.atomic():
                # 1) t_stock_allocation へ反映（MAIN固定）
                for code, qty in parsed['rows'].items():
                    product_id = product_id_by_code[code]
                    obj, created = StockAllocation.objects.get_or_create(
                        product_id=product_id,
                        location=location,
                        defaults={
                            'current_stock': qty,
                            'reserved_qty': Decimal('0'),
                            'min_stock_qty': 0,
                            'is_bottleneck': False,
                        }
                    )
                    if created:
                        allocation_created += 1
                    else:
                        obj.current_stock = qty
                        obj.reserved_qty = Decimal('0')
                        obj.save(update_fields=['current_stock', 'reserved_qty', 'updated_at'])
                        allocation_updated += 1

                # 2) line_backlog (sequence_no=0) へ棚卸在庫を反映
                target_product_ids = list(product_id_by_code.values())
                unique_keys, mapped_product_ids = _collect_stocktake_mapping_keys(
                    baseline_date,
                    target_product_ids,
                )

                for process_id, product_id, line_id in unique_keys:
                    # line_backlog はint管理のため、小数は切り捨てで保持
                    product_code = product_code_by_id.get(product_id)
                    stock_int = int(parsed['rows'][product_code]) if product_code else 0
                    obj, created = LineBacklog.objects.get_or_create(
                        plan_date=baseline_date,
                        process_id=process_id,
                        product_id=product_id,
                        line_id=line_id,
                        sequence_no=0,
                        defaults={
                            'demand_qty_plan': 0,
                            'order_qty': 0,
                            'plan_qty': 0,
                            'actual_qty': 0,
                            'stock_qty': stock_int,
                            'planned_stock_qty': 0,
                            'adjust_qty': 0,
                            'scrap_adjust_qty': 0,
                            'scrap_qty': 0,
                            'actual_shipment_qty': 0,
                            'progress_qty': 0,
                            'planned_progress_qty': 0,
                            'is_stocktake_fix': True,  # 棚卸確定フラグON
                        },
                    )
                    if created:
                        backlog_created += 1
                    else:
                        obj.stock_qty = stock_int
                        # planned_stock_qty は Step2(initialize_stocktake) で計算する。
                        # Step1(取込)では値を確定させないため0を保持する。
                        obj.planned_stock_qty = 0
                        obj.progress_qty = 0
                        obj.planned_progress_qty = 0
                        obj.is_stocktake_fix = True
                        obj.save(update_fields=['stock_qty', 'planned_stock_qty', 'progress_qty', 'planned_progress_qty', 'is_stocktake_fix', 'updated_at'])
                        backlog_updated += 1
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        unmapped_product_codes = sorted([
            code for code, pid in product_id_by_code.items() if pid not in mapped_product_ids
        ])

        return Response({
            'detail': 'Stocktake file imported successfully',
            'stocktake_date': stocktake_date.isoformat(),
            'baseline_date': baseline_date.isoformat(),
            'upper_bound_date': upper_bound_date.isoformat(),
            'location': location,
            'loaded_rows': parsed['row_count'],
            'product_count': len(product_codes),
            'allocation_created': allocation_created,
            'allocation_updated': allocation_updated,
            'backlog_created': backlog_created,
            'backlog_updated': backlog_updated,
            'unmapped_product_codes': unmapped_product_codes,
        })

    @action(detail=False, methods=['post'])
    def initialize_stocktake(self, request):
        """
        棚卸初期化（在庫/計画在庫/進度）を一括実行する。

        期待payload:
        - stocktake_date: YYYY-MM-DD
        - end_date: YYYY-MM-DD
        """
        from .inventory.stocktake_initializer import (
            initialize_progress_from_stocktake,
            initialize_planned_stock,
            ensure_stocktake_backlogs,
            get_progress_upper_bound_date,
            recalculate_progress_from_stocktake,
            recalculate_inventory_from_stocktake,
        )

        stocktake_date_raw = request.data.get('stocktake_date')
        end_date_raw = request.data.get('end_date')
        if not stocktake_date_raw:
            return Response({'detail': 'stocktake_date is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not end_date_raw:
            return Response({'detail': 'end_date is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            stocktake_dt = datetime.strptime(str(stocktake_date_raw), '%Y-%m-%d').date()
            end_dt = datetime.strptime(str(end_date_raw), '%Y-%m-%d').date()
        except ValueError as e:
            return Response({'detail': f'Invalid date format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        baseline_dt = stocktake_dt
        upper_bound = get_progress_upper_bound_date()

        if end_dt < baseline_dt:
            return Response(
                {'detail': 'end_date must be on or after resolved baseline_date'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            baseline_result = ensure_stocktake_backlogs(baseline_dt)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        line_ids = list(LineBacklog.objects.filter(
            plan_date__gte=baseline_dt,
            plan_date__lte=end_dt,
        ).values_list('line_id', flat=True).distinct())

        if not line_ids:
            return Response(
                {'detail': 'line_backlog rows not found in calculation range'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # 1. 計画在庫の初期値を正しく計算してセットする（専用ロジック）
            # stock_qty - パイプライン需要
            initialize_planned_stock(line_ids, baseline_dt)

            # 2. 棚卸専用の再計算（基準日以降）
            # 通常計算の「前々営業日以前スキップ」を使わず、棚卸日を起点に連鎖計算する。
            for line_id in line_ids:
                # 進度は棚卸初期化ロジックで別計算するため、ここでは在庫・計画在庫のみ再計算
                recalculate_inventory_from_stocktake(line_id, baseline_dt, end_dt)
            
            # 3. 進度の初期化（専用ロジック）
            progress_result = initialize_progress_from_stocktake(baseline_dt)
            progress_recalc_results = []
            for line_id in line_ids:
                progress_recalc_results.append(
                    recalculate_progress_from_stocktake(line_id, baseline_dt, end_dt)
                )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'detail': 'Stocktake initialization completed',
            'stocktake_date': stocktake_dt.isoformat(),
            'baseline_date': baseline_dt.isoformat(),
            'upper_bound_date': upper_bound.isoformat(),
            'end_date': end_dt.isoformat(),
            'line_count': len(line_ids),
            'baseline_backlog_created': baseline_result.get('backlog_created', 0),
            'baseline_backlog_updated': baseline_result.get('backlog_updated', 0),
            'baseline_unmapped_product_codes': baseline_result.get('unmapped_product_codes', []),
            'progress_recalc_line_count': len(progress_recalc_results),
            'progress_recalc_product_count': sum(r.get('product_count', 0) for r in progress_recalc_results),
            **progress_result,
        })

    @action(detail=False, methods=['post'])
    def recalculate_inventory(self, request):
        return backlog_recalc_service.recalculate_inventory(
            self,
            request,
            parse_product_ids=_parse_product_ids,
        )

    @action(detail=False, methods=['post'], url_path='recalculate_inventory_for_products')
    def recalculate_inventory_for_products(self, request):
        return backlog_recalc_service.recalculate_inventory_for_products(
            self,
            request,
            parse_product_ids=_parse_product_ids,
        )

    @action(detail=False, methods=['get'], url_path='batch_adjust_info')
    def batch_adjust_info(self, request):
        """
        工程またはライン上の全品番の調整対象日・現在調整値を返すAPI（一括調整用）。

        クエリパラメータ:
            process_code: str (process_code か line_code のいずれか必須)
            line_code: str (process_code か line_code のいずれか必須)
            adjust_type: str (required) - STOCK / PLANNED_STOCK / PROGRESS / PLANNED_PROGRESS
        """
        from .inventory.inventory_calculator import _get_max_parent_bom_lead_time, _get_direct_parent_bom_lead_time

        process_code = (request.query_params.get('process_code') or '').strip()
        line_code = (request.query_params.get('line_code') or '').strip()
        adjust_type = (request.query_params.get('adjust_type') or '').strip().upper()
        target_date_raw = (request.query_params.get('target_date') or '').strip()

        if not process_code and not line_code:
            return Response({'detail': 'process_code or line_code is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not adjust_type:
            return Response({'detail': 'adjust_type is required'}, status=status.HTTP_400_BAD_REQUEST)

        process = None
        line = None
        if process_code:
            process = Process.objects.filter(process_code=process_code, is_active=True).first()
            if not process:
                return Response({'detail': f'工程が見つかりません: {process_code}'}, status=status.HTTP_404_NOT_FOUND)
        if line_code:
            line = Line.objects.filter(line_code=line_code, is_active=True).first()
            if not line:
                return Response({'detail': f'ラインが見つかりません: {line_code}'}, status=status.HTTP_404_NOT_FOUND)

        # 在庫・計画在庫は直親LT、進度は累積LTを使用
        use_direct_lt = adjust_type in ('STOCK', 'PLANNED_STOCK')

        # (product, line, process) 組み合わせを取得（重複なし）
        from masters.models import Product as ProductModel
        backlog_filter = {}
        if process:
            backlog_filter['process'] = process
        if line:
            backlog_filter['line'] = line
        pl_pairs = list(
            LineBacklog.objects.filter(**backlog_filter)
            .values('product_id', 'line_id', 'process_id')
            .distinct()
        )
        product_ids = list({row['product_id'] for row in pl_pairs})
        line_ids = list({row['line_id'] for row in pl_pairs})
        process_ids = list({row['process_id'] for row in pl_pairs if row['process_id']})

        products = {p.id: p for p in ProductModel.objects.filter(id__in=product_ids)}
        lines = {l.id: l for l in Line.objects.filter(id__in=line_ids)}
        processes_map = {p.id: p for p in Process.objects.filter(id__in=process_ids)} if process_ids else {}

        today = get_business_today()
        selected_target_date = None
        if target_date_raw:
            try:
                selected_target_date = datetime.strptime(target_date_raw, '%Y-%m-%d').date()
            except ValueError as e:
                return Response({'detail': f'target_date形式が不正です: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        calendar_id = Calendar.objects.filter(calendar_code='daiso').values_list('id', flat=True).first()
        workday_cache = {}

        def is_working_day(d):
            if not calendar_id:
                return d.weekday() < 5
            if d in workday_cache:
                return workday_cache[d]
            cal = CalendarDay.objects.filter(calendar_id=calendar_id, target_date=d).first()
            result = cal.is_working_day if cal is not None else d.weekday() < 5
            workday_cache[d] = result
            return result

        def calc_start(max_lt):
            remaining = max_lt + 1
            current = today
            while remaining > 0:
                current = current - timedelta(days=1)
                if is_working_day(current):
                    remaining -= 1
            return current

        # 既存の調整値をまとめて取得
        adj_filter = {'adjust_type': adjust_type}
        if process:
            adj_filter['process'] = process
        if line:
            adj_filter['line'] = line
        existing = {
            (a.product_id, a.line_id, str(a.plan_date)): a.adjust_qty
            for a in LineBacklogAdjustment.objects.filter(**adj_filter)
        }

        # adjust_type に応じた指定日の値フィールドを決定
        value_field_map = {
            'STOCK': 'stock_qty',
            'PLANNED_STOCK': 'planned_stock_qty',
            'PROGRESS': 'progress_qty',
            'PLANNED_PROGRESS': 'planned_progress_qty',
        }
        value_field = value_field_map.get(adjust_type, 'stock_qty')
        target_value_date = selected_target_date or today

        target_value_filter = {
            'product_id__in': product_ids,
            'plan_date': target_value_date,
            'sequence_no': 0,
        }
        if process:
            target_value_filter['process'] = process
        if line:
            target_value_filter['line'] = line
        today_values = {
            (lb.product_id, lb.line_id): getattr(lb, value_field)
            for lb in LineBacklog.objects.filter(**target_value_filter)
        }

        results = []
        seen = set()
        for row in pl_pairs:
            pid = row['product_id']
            lid = row['line_id']
            pair_key = (pid, lid)
            if pair_key in seen:
                continue
            seen.add(pair_key)
            product = products.get(pid)
            line_obj = lines.get(lid)
            if not product or not line_obj:
                continue
            proc_id = row.get('process_id')
            proc_obj = processes_map.get(proc_id) if proc_id else None
            max_lt = _get_direct_parent_bom_lead_time(pid) if use_direct_lt else _get_max_parent_bom_lead_time(pid)
            calc_start_date = calc_start(max_lt)
            target_date = selected_target_date or calc_start_date
            results.append({
                'product_id': pid,
                'product_code': product.product_code,
                'product_name': product.product_name,
                'line_id': lid,
                'line_code': line_obj.line_code,
                'line_name': line_obj.line_name,
                'process_code': proc_obj.process_code if proc_obj else '',
                'calc_start_date': calc_start_date.isoformat(),
                'target_date': target_date.isoformat(),
                'adjust_qty': existing.get((pid, lid, target_date.isoformat()), 0),
                'value_today': today_values.get((pid, lid)),
            })

        results.sort(key=lambda x: (x['product_code'], x['line_code']))
        return Response({
            'process_id': process.id if process else None,
            'process_code': process.process_code if process else '',
            'process_name': process.process_name if process else '',
            'line_id': line.id if line else None,
            'line_code': line.line_code if line else '',
            'line_name': line.line_name if line else '',
            'line_ids': line_ids,
            'products': results,
        })

    @action(detail=False, methods=['get'], url_path='calc_start_date')
    def get_calc_start_date(self, request):
        """
        製品の calc_start_date（= today − (max親BOM LT + 1) 営業日）を返すAPI。
        在庫調整画面の表示開始日の自動設定に使用する。

        クエリパラメータ:
            product_id (required)
            base_date (optional, YYYY-MM-DD) - 表示開始日計算の基準日。未指定時は業務日付
        """
        from .inventory.inventory_calculator import _get_direct_parent_bom_lead_time

        product_id = request.query_params.get('product_id')
        base_date_raw = (request.query_params.get('base_date') or '').strip()
        if not product_id:
            return Response({'detail': 'product_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            product_id = int(product_id)
        except ValueError:
            return Response({'detail': 'product_id must be numeric'}, status=status.HTTP_400_BAD_REQUEST)

        if base_date_raw:
            try:
                today = datetime.strptime(base_date_raw, '%Y-%m-%d').date()
            except ValueError as e:
                return Response({'detail': f'base_date形式が不正です: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            today = get_business_today()
        max_lt = _get_direct_parent_bom_lead_time(product_id)

        # daiso カレンダーで営業日シフト
        calendar_id = Calendar.objects.filter(calendar_code='daiso').values_list('id', flat=True).first()
        workday_cache = {}

        def is_working_day(target_date):
            if not calendar_id:
                return target_date.weekday() < 5
            if target_date in workday_cache:
                return workday_cache[target_date]
            cal = CalendarDay.objects.filter(calendar_id=calendar_id, target_date=target_date).first()
            is_work = cal.is_working_day if cal is not None else target_date.weekday() < 5
            workday_cache[target_date] = is_work
            return is_work

        remaining = max_lt + 1
        current = today
        while remaining > 0:
            current = current - timedelta(days=1)
            if is_working_day(current):
                remaining -= 1

        return Response({
            'calc_start_date': current.isoformat(),
            'max_lt': max_lt,
        })

    @action(detail=False, methods=['post'], url_path='recalculate_inventory_deep')
    def recalculate_inventory_deep(self, request):
        return backlog_recalc_service.recalculate_inventory_deep(
            self,
            request,
            parse_product_ids=_parse_product_ids,
        )

    @action(detail=False, methods=['post'])
    def initialize_progress(self, request):
        """
        棚卸在庫を起点に進度(progress_qty / planned_progress_qty)を初期化するAPI

        期待payload: {
            stocktake_date: str (YYYY-MM-DD, required)
            baseline_date: str (YYYY-MM-DD, optional)  # 明示指定時のみ使用
        }
        """
        from .inventory.stocktake_initializer import (
            initialize_progress_from_stocktake,
            resolve_progress_baseline_date,
        )

        stocktake_date_raw = request.data.get('stocktake_date')
        baseline_date_raw = request.data.get('baseline_date')
        if not stocktake_date_raw and not baseline_date_raw:
            return Response(
                {'detail': 'stocktake_date is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        stocktake_dt = None
        if stocktake_date_raw:
            try:
                stocktake_dt = datetime.strptime(str(stocktake_date_raw), '%Y-%m-%d').date()
            except ValueError as e:
                return Response({'detail': f'Invalid stocktake_date format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        if baseline_date_raw:
            try:
                baseline_dt = datetime.strptime(str(baseline_date_raw), '%Y-%m-%d').date()
            except ValueError as e:
                return Response({'detail': f'Invalid baseline_date format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
            upper_bound = None
        else:
            try:
                baseline_dt, upper_bound = resolve_progress_baseline_date(stocktake_dt)
            except ValueError as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = initialize_progress_from_stocktake(baseline_dt)
            response_payload = {
                'detail': 'Progress initialized successfully',
                'baseline_date': baseline_dt.isoformat(),
                **result,
            }
            if stocktake_dt:
                response_payload['stocktake_date'] = stocktake_dt.isoformat()
            if upper_bound:
                response_payload['upper_bound_date'] = upper_bound.isoformat()
            return Response(response_payload)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def recalculate_scrap(self, request):
        return backlog_recalc_service.recalculate_scrap(
            self,
            request,
            parse_product_ids=_parse_product_ids,
        )

    @action(detail=False, methods=['post'], url_path='recalculate_scrap_for_products')
    def recalculate_scrap_for_products(self, request):
        return backlog_recalc_service.recalculate_scrap_for_products(
            self,
            request,
            parse_product_ids=_parse_product_ids,
        )


class LineGanttPlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LineGanttPlan.objects.all().select_related('line', 'product')
    serializer_class = LineGanttPlanSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = LineGanttPlanFilter
    ordering_fields = ['plan_date', 'line', 'product']
    ordering = ['plan_date', 'line']

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        ガント用ライン計画を生成して保存する。
        期待payload: { line_id, start_date, end_date, clear_existing?: bool, final_process_start_time?: str, adjust_to_break_end?: bool }
        """
        line_id = request.data.get('line_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        clear_existing = bool(request.data.get('clear_existing'))
        final_process_start_time = request.data.get('final_process_start_time')
        adjust_to_break_end = request.data.get('adjust_to_break_end', False)

        logger.info(
            'line_gantt_plans.generate: line_id=%s start=%s end=%s clear=%s final_time=%s adjust=%s',
            line_id, start_date, end_date, clear_existing, final_process_start_time, adjust_to_break_end
        )

        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not start_date or not end_date:
            return Response({'detail': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            line_id = int(line_id)
        except (TypeError, ValueError):
            return Response({'detail': 'line_id must be numeric'}, status=status.HTTP_400_BAD_REQUEST)

        plans = generate_line_gantt_plans(
            line_id,
            start_date,
            end_date,
            clear_existing=clear_existing,
            final_process_start_time=final_process_start_time,
            adjust_to_break_end=adjust_to_break_end
        )
        logger.info('line_gantt_plans.generate: plans=%s', len(plans))

        upserted = []
        for plan in plans:
            obj, _ = LineGanttPlan.objects.update_or_create(
                plan_id=plan['plan_id'],
                defaults={
                    'line_id': plan['line_id'],
                    'product_id': plan['product_id'],
                    'plan_date': plan['plan_date'],
                    'plan_qty': plan['plan_qty'],
                    'sequence_no': plan['sequence_no'],
                    'start_datetime': plan['start_datetime'],
                    'end_datetime': plan['end_datetime'],
                    'processes_plan': plan['processes_plan'],
                }
            )
            upserted.append(obj)

        if clear_existing:
            def parse_date(val):
                try:
                    return datetime.strptime(str(val), '%Y-%m-%d').date()
                except Exception:
                    return None

            start_dt = parse_date(start_date)
            end_dt = parse_date(end_date)
            qs = LineGanttPlan.objects.filter(line_id=line_id)
            if start_dt:
                qs = qs.filter(plan_date__gte=start_dt)
            if end_dt:
                qs = qs.filter(plan_date__lte=end_dt)
            plan_ids = [p['plan_id'] for p in plans]
            if plan_ids:
                qs = qs.exclude(plan_id__in=plan_ids)
            qs = qs.exclude(plan_id__startswith='MANUAL_').exclude(plan_id__startswith='SINGLEPROC_')
            deleted_count, _ = qs.delete()
            logger.info('line_gantt_plans.generate: cleared=%s', deleted_count)

        serializer = self.get_serializer(upserted, many=True)
        return Response(serializer.data)

    def _parse_gantt_datetime_value(self, value):
        if not value:
            return None
        try:
            raw = str(value).strip()
            if raw.endswith('Z'):
                raw = raw[:-1] + '+00:00'
            dt = datetime.fromisoformat(raw)
        except Exception:
            return None
        if getattr(dt, 'tzinfo', None) is not None:
            try:
                dt = timezone.localtime(dt).replace(tzinfo=None)
            except Exception:
                dt = dt.replace(tzinfo=None)
        return dt

    def _create_manual_gantt_plan(self, *, line_id, process_id, output_product_id, start_time, end_time, quantity_raw, process_number_raw=None):
        try:
            line_id = int(line_id)
            process_id = int(process_id)
            output_product_id = int(output_product_id)
        except (TypeError, ValueError):
            raise ValueError('line_id, process_id, output_product_id must be numeric')

        try:
            quantity = Decimal(str(quantity_raw)).quantize(Decimal('0.001'))
        except Exception:
            raise ValueError('quantity is invalid')
        if quantity <= 0:
            raise ValueError('quantity must be greater than 0')

        start_dt = self._parse_gantt_datetime_value(start_time)
        end_dt = self._parse_gantt_datetime_value(end_time)
        if not start_dt or not end_dt:
            raise ValueError('start_time and end_time must be ISO datetime')
        if end_dt <= start_dt:
            raise ValueError('end_time must be after start_time')

        line = Line.objects.filter(id=line_id).first()
        process = Process.objects.filter(id=process_id).first()
        output_product = Product.objects.filter(id=output_product_id).first()
        if not line or not process or not output_product:
            raise ValueError('line/process/product not found')

        routing_step = (
            RoutingStep.objects
            .filter(line_id=line_id, process_id=process_id)
            .filter(Q(output_product_id=output_product_id) | Q(output_product_id__isnull=True))
            .order_by('step_no', 'parallel_group')
            .first()
        )

        try:
            process_number = int(process_number_raw) if process_number_raw not in [None, ''] else None
        except (TypeError, ValueError):
            process_number = None
        if process_number is None:
            process_number = int(routing_step.step_no) if routing_step and routing_step.step_no is not None else 0

        parallel_group = int(routing_step.parallel_group) if routing_step and routing_step.parallel_group else 1
        parallel_count = int(routing_step.parallel_count) if routing_step and routing_step.parallel_count else 1
        duration_minutes = max((end_dt - start_dt).total_seconds() / 60.0, 0.0)

        plan_date_anchor = start_dt if start_dt.hour >= DAY_BOUNDARY_HOUR else (start_dt - timedelta(days=1))
        plan_date = plan_date_anchor.date()

        plan_id = (
            f"MANUAL_{line_id}_{output_product_id}_"
            f"{start_dt.strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
        )

        process_plan = [{
            'plan_id': plan_id,
            'process_id': process_id,
            'process_name': process.process_name,
            'process_number': process_number,
            'start_time': start_dt.strftime('%Y-%m-%dT%H:%M:%S'),
            'end_time': end_dt.strftime('%Y-%m-%dT%H:%M:%S'),
            'quantity': float(quantity),
            'cycle_time_minutes': 0.0,
            'setup_time_minutes': 0.0,
            'total_minutes_required': round(duration_minutes, 1),
            'parallel_group': parallel_group,
            'parallel_count': parallel_count,
            'transfer_time_minutes': 0.0,
            'output_product_id': output_product.id,
            'output_product_code': output_product.product_code,
            'output_product_name': output_product.product_name,
        }]

        return LineGanttPlan.objects.create(
            plan_id=plan_id,
            line_id=line_id,
            product_id=output_product_id,
            plan_date=plan_date,
            plan_qty=quantity,
            sequence_no=None,
            start_datetime=start_dt,
            end_datetime=end_dt,
            processes_plan=process_plan,
        )

    def _remove_gantt_process_entry(self, *, plan_id, process_id, output_product_id=None, change_user=None):
        if not plan_id or not process_id:
            raise ValueError('plan_id と process_id は必須です')
        try:
            process_id = int(process_id)
        except Exception:
            raise ValueError('process_id が不正です')
        if output_product_id in [None, '']:
            output_product_id = None
        else:
            try:
                output_product_id = int(output_product_id)
            except Exception:
                output_product_id = None

        plan = LineGanttPlan.objects.filter(plan_id=plan_id).first()
        if not plan or not plan.processes_plan:
            raise LookupError('対象の計画が見つかりません')

        original = list(plan.processes_plan)
        remaining = []
        removed_proc = None
        for proc in original:
            if removed_proc is None and str(proc.get('process_id')) == str(process_id):
                proc_out = proc.get('output_product_id')
                if output_product_id is not None and str(proc_out) != str(output_product_id):
                    remaining.append(proc)
                else:
                    removed_proc = proc
            else:
                remaining.append(proc)

        if removed_proc is None:
            raise LookupError('対象プロセスが見つかりません')

        change_reason = '工程ガントバー削除'
        backlog_filter = dict(plan_id=plan_id, process_id=process_id, sequence_no__gt=0)
        if output_product_id is not None:
            backlog_filter['product_id'] = output_product_id
        backlog_qs = LineBacklog.objects.filter(**backlog_filter)
        backlog_rows = list(backlog_qs)

        backlog_qs.delete()
        if remaining:
            starts, ends = [], []
            for proc in remaining:
                try:
                    starts.append(datetime.fromisoformat(proc['start_time']))
                    ends.append(datetime.fromisoformat(proc['end_time']))
                except Exception:
                    continue
            if starts:
                plan.start_datetime = min(starts)
            if ends:
                plan.end_datetime = max(ends)
            plan.processes_plan = remaining
            plan.save()
        else:
            ProductionOrder.objects.filter(order_no=plan_id).delete()
            plan.delete()

        before_qty = 0
        try:
            before_qty = int(Decimal(str(removed_proc.get('quantity') or 0)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        except Exception:
            pass
        if backlog_rows:
            for row in backlog_rows:
                row_qty = int(row.plan_qty or 0)
                if row_qty == 0:
                    continue
                ProductionPlanChangeLog.objects.create(
                    plan_date=row.plan_date,
                    product_id=row.product_id,
                    process_id=row.process_id,
                    line_id=row.line_id,
                    sequence_no=row.sequence_no,
                    plan_id=row.plan_id,
                    before_qty=row_qty,
                    after_qty=0,
                    reason=change_reason,
                    changed_by=change_user,
                )
        elif before_qty != 0:
            resolved_product_id = output_product_id or removed_proc.get('output_product_id')
            try:
                resolved_product_id = int(resolved_product_id)
            except Exception:
                resolved_product_id = None
            if resolved_product_id:
                ProductionPlanChangeLog.objects.create(
                    plan_date=plan.plan_date,
                    product_id=resolved_product_id,
                    process_id=process_id,
                    line_id=plan.line_id,
                    sequence_no=plan.sequence_no,
                    plan_id=plan_id,
                    before_qty=before_qty,
                    after_qty=0,
                    reason=change_reason,
                    changed_by=change_user,
                )

        return {'deleted': True, 'plan_removed': not remaining}

    @action(detail=False, methods=['post'], url_path='manual-add')
    def manual_add(self, request):
        """
        工程ガントに手動バーを1件追加する。
        期待payload: { line_id, process_id, output_product_id, start_time, end_time, quantity, process_number? }
        """
        try:
            with transaction.atomic():
                created = self._create_manual_gantt_plan(
                    line_id=request.data.get('line_id'),
                    process_id=request.data.get('process_id'),
                    output_product_id=request.data.get('output_product_id'),
                    start_time=request.data.get('start_time'),
                    end_time=request.data.get('end_time'),
                    quantity_raw=request.data.get('quantity'),
                    process_number_raw=request.data.get('process_number'),
                )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(created)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='bulk-structure-save')
    def bulk_structure_save(self, request):
        creates = request.data.get('creates') or []
        deletes = request.data.get('deletes') or []
        if not isinstance(creates, list) or not isinstance(deletes, list):
            return Response({'detail': 'creates と deletes は配列で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        if not creates and not deletes:
            return Response({'detail': '保存対象がありません'}, status=status.HTTP_400_BAD_REQUEST)

        change_user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        created_items = []
        deleted_count = 0
        try:
            with transaction.atomic():
                for create_item in creates:
                    created_items.append(self._create_manual_gantt_plan(
                        line_id=create_item.get('line_id'),
                        process_id=create_item.get('process_id'),
                        output_product_id=create_item.get('output_product_id'),
                        start_time=create_item.get('start_time'),
                        end_time=create_item.get('end_time'),
                        quantity_raw=create_item.get('quantity'),
                        process_number_raw=create_item.get('process_number'),
                    ))
                for delete_item in deletes:
                    self._remove_gantt_process_entry(
                        plan_id=delete_item.get('plan_id'),
                        process_id=delete_item.get('process_id'),
                        output_product_id=delete_item.get('output_product_id'),
                        change_user=change_user,
                    )
                    deleted_count += 1
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except LookupError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(created_items, many=True)
        return Response({
            'created': len(created_items),
            'deleted': deleted_count,
            'created_items': serializer.data,
        })

    @action(detail=False, methods=['get'], url_path='singleproc-finished-entries')
    def singleproc_finished_entries(self, request):
        """単独計画の完成品エントリ取得"""
        from .models_singleproc_finished_entry import SingleProcFinishedEntry
        line_id = request.query_params.get('line')
        process_id = request.query_params.get('process')
        date_gte = request.query_params.get('plan_date__gte')
        date_lte = request.query_params.get('plan_date__lte')
        if not line_id or not process_id:
            return Response([])
        qs = SingleProcFinishedEntry.objects.filter(
            line_id=line_id, process_id=process_id,
        ).select_related('product')
        if date_gte:
            qs = qs.filter(plan_date__gte=date_gte)
        if date_lte:
            qs = qs.filter(plan_date__lte=date_lte)
        data = [
            {
                'plan_date': str(e.plan_date),
                'sequence_no': e.sequence_no,
                'product_id': e.product_id,
                'product_code': e.product.product_code if e.product else '',
                'product_name': e.product.product_name if e.product else '',
                'quantity': e.quantity,
            }
            for e in qs.order_by('plan_date', 'sequence_no')
        ]
        return Response(data)

    @action(detail=False, methods=['post'], url_path='sub-process-save')
    def sub_process_save(self, request):
        """
        単独計画の保存。ロジックは services/single_process_plan.py に委譲。
        期待payload: {
            line_id, process_id,
            entries: [{ product_id, plan_date, plan_qty, sequence_no }, ...],
            finished_entries?: [{ product_id, plan_date, quantity, sequence_no }, ...],
            target_dates?: ['2026-06-27', ...],
            change_reason?: str
        }
        """
        from .services.single_process_plan import save_sub_process_plan
        from .models_singleproc_finished_entry import SingleProcFinishedEntry

        line_id = request.data.get('line_id')
        process_id = request.data.get('process_id')
        entries = request.data.get('entries', [])
        finished_entries = request.data.get('finished_entries', [])
        target_dates = request.data.get('target_dates', [])
        raw_reason = request.data.get('change_reason', 'サブ工程計画入力')
        change_reason = str(raw_reason).strip() if raw_reason else 'サブ工程計画入力'

        if not line_id or not process_id:
            return Response({'detail': 'line_id, process_id は必須です'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            line_id = int(line_id)
            process_id = int(process_id)
        except (TypeError, ValueError):
            return Response({'detail': 'line_id, process_id は数値で指定してください'}, status=status.HTTP_400_BAD_REQUEST)

        line = Line.objects.filter(id=line_id).first()
        process = Process.objects.filter(id=process_id).first()
        if not line or not process:
            return Response({'detail': 'ライン/工程が見つかりません'}, status=status.HTTP_404_NOT_FOUND)

        change_user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

        try:
            result = save_sub_process_plan(
                line=line, process=process, entries=entries, target_dates=target_dates,
                change_reason=change_reason, change_user=change_user,
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error('sub_process_save error: %s', e, exc_info=True)
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if finished_entries:
            try:
                delete_dates = set(target_dates)
                for fe in finished_entries:
                    d = str(fe.get('plan_date', '')).strip()
                    if d:
                        delete_dates.add(d)
                if delete_dates:
                    SingleProcFinishedEntry.objects.filter(
                        line_id=line_id, process_id=process_id, plan_date__in=list(delete_dates),
                    ).delete()
                objs = []
                for fe in finished_entries:
                    pid = fe.get('product_id')
                    qty = int(fe.get('quantity', 0))
                    seq = int(fe.get('sequence_no', 0))
                    plan_date = str(fe.get('plan_date', '')).strip()
                    if pid and qty > 0 and seq > 0 and plan_date:
                        objs.append(SingleProcFinishedEntry(
                            line_id=line_id, process_id=process_id,
                            plan_date=plan_date, sequence_no=seq,
                            product_id=int(pid), quantity=qty,
                        ))
                if objs:
                    SingleProcFinishedEntry.objects.bulk_create(objs)
            except Exception as e:
                logger.warning('finished_entries save error: %s', e)

        return Response(result)

    @action(detail=False, methods=['put'], url_path='bulk-update')
    def bulk_update(self, request):
        """
        ガントのドラッグ調整結果を一括保存する。
        期待payload: [{ plan_id, process_id, output_product_id?, start_time?, end_time?, quantity? }, ...]
        """
        updates = request.data
        if not isinstance(updates, list) or not updates:
            return Response({'detail': 'updates must be a non-empty list'}, status=status.HTTP_400_BAD_REQUEST)

        updated_count = 0
        change_log_count = 0
        change_user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        change_reason = '工程ガント数量編集'
        for update in updates:
            plan_id = update.get('plan_id')
            process_id = update.get('process_id')
            if not plan_id or not process_id:
                continue
            try:
                process_id = int(process_id)
            except Exception:
                continue
            output_product_id = update.get('output_product_id')
            if output_product_id in [None, '']:
                output_product_id = None
            else:
                try:
                    output_product_id = int(output_product_id)
                except Exception:
                    output_product_id = None
            start_time = update.get('start_time')
            end_time = update.get('end_time')
            has_quantity = 'quantity' in update
            quantity_value = None
            quantity_int_value = None
            if has_quantity:
                try:
                    quantity_value = Decimal(str(update.get('quantity')))
                    if quantity_value < 0:
                        has_quantity = False
                    else:
                        quantity_int_value = int(quantity_value.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
                except Exception:
                    has_quantity = False

            plan = LineGanttPlan.objects.filter(plan_id=plan_id).first()
            if not plan or not plan.processes_plan:
                continue

            processes_plan = list(plan.processes_plan)
            changed = False
            matched_output_product_id = None
            quantity_changed = False
            before_quantity_value = None
            for proc in processes_plan:
                if str(proc.get('process_id')) == str(process_id):
                    proc_output_product_id = proc.get('output_product_id')
                    if output_product_id is not None and str(proc_output_product_id) != str(output_product_id):
                        continue
                    matched_output_product_id = proc_output_product_id
                    if start_time:
                        proc['start_time'] = start_time
                        changed = True
                    if end_time:
                        proc['end_time'] = end_time
                        changed = True
                    if has_quantity and quantity_int_value is not None:
                        try:
                            before_qty = int(Decimal(str(proc.get('quantity') or 0)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
                        except Exception:
                            before_qty = 0
                        if before_qty != quantity_int_value:
                            proc['quantity'] = quantity_int_value
                            changed = True
                            quantity_changed = True
                            before_quantity_value = before_qty
                    if changed:
                        updated_count += 1
                    break

            if changed:
                starts = []
                ends = []
                for proc in processes_plan:
                    try:
                        starts.append(datetime.fromisoformat(proc['start_time']))
                        ends.append(datetime.fromisoformat(proc['end_time']))
                    except Exception:
                        continue
                if starts:
                    plan.start_datetime = min(starts)
                if ends:
                    plan.end_datetime = max(ends)
                plan.processes_plan = processes_plan
                plan.save()
                if quantity_changed and quantity_int_value is not None and matched_output_product_id:
                    try:
                        matched_output_product_id = int(matched_output_product_id)
                    except Exception:
                        matched_output_product_id = None
                if quantity_changed and quantity_int_value is not None and matched_output_product_id:
                    backlog_qs = LineBacklog.objects.filter(
                        line_id=plan.line_id,
                        process_id=process_id,
                        product_id=matched_output_product_id,
                        plan_id=plan_id,
                    )
                    backlog_rows = list(backlog_qs)
                    if backlog_rows:
                        backlog_qs.update(plan_qty=quantity_int_value)
                        for row in backlog_rows:
                            before_qty = int(row.plan_qty or 0)
                            if before_qty == quantity_int_value:
                                continue
                            ProductionPlanChangeLog.objects.create(
                                plan_date=row.plan_date,
                                product_id=row.product_id,
                                process_id=row.process_id,
                                line_id=row.line_id,
                                sequence_no=row.sequence_no,
                                plan_id=row.plan_id,
                                before_qty=before_qty,
                                after_qty=quantity_int_value,
                                reason=change_reason,
                                changed_by=change_user,
                            )
                            change_log_count += 1
                    elif before_quantity_value is not None:
                        ProductionPlanChangeLog.objects.create(
                            plan_date=plan.plan_date,
                            product_id=matched_output_product_id,
                            process_id=process_id,
                            line_id=plan.line_id,
                            sequence_no=plan.sequence_no,
                            plan_id=plan_id,
                            before_qty=before_quantity_value,
                            after_qty=quantity_int_value,
                            reason=change_reason,
                            changed_by=change_user,
                        )
                        change_log_count += 1

        return Response({'updated': updated_count, 'change_logs': change_log_count})

    @action(detail=False, methods=['post'], url_path='calc-end-time')
    def calc_end_time(self, request):
        """
        稼働カレンダーを使って開始時刻+稼働分数から終了時刻を計算する。
        期待payload: { line_id, start_time, working_minutes }
        """
        from .services.gantt_planning import LineWorkCalendar
        line_id = request.data.get('line_id')
        start_time_str = request.data.get('start_time')
        working_minutes = request.data.get('working_minutes')
        if not line_id or not start_time_str or working_minutes is None:
            return Response({'detail': 'line_id, start_time, working_minutes are required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            line = Line.objects.get(pk=line_id)
            start_dt = datetime.fromisoformat(start_time_str)
            minutes = float(working_minutes)
        except (Line.DoesNotExist, ValueError, TypeError) as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        calendar = LineWorkCalendar(line)
        end_dt = calendar.add_working_minutes(start_dt, minutes)
        return Response({'end_time': end_dt.isoformat()})

    @action(detail=False, methods=['post'], url_path='remove-process')
    def remove_process(self, request):
        """
        指定した1プロセスのガントバーを削除する。
        processes_plan から対象 process_id エントリのみ除去し、
        対応する LineBacklog(seq>0) も削除する。
        processes_plan が空になった場合は LineGanttPlan ごと削除。
        期待payload: { plan_id, process_id, output_product_id? }
        """
        change_user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        try:
            with transaction.atomic():
                result = self._remove_gantt_process_entry(
                    plan_id=request.data.get('plan_id'),
                    process_id=request.data.get('process_id'),
                    output_product_id=request.data.get('output_product_id'),
                    change_user=change_user,
                )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except LookupError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return Response(result)


# ========================================
# 製造実行系ViewSet
# ========================================

class StockAllocationFilter(django_filters.FilterSet):
    """在庫引当フィルタ"""
    product_code = django_filters.CharFilter(field_name='product__product_code', lookup_expr='icontains')
    is_bottleneck = django_filters.BooleanFilter()
    location = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = StockAllocation
        fields = ['product', 'product_code', 'location', 'is_bottleneck']


class StockAllocationViewSet(viewsets.ModelViewSet):
    """在庫引当ViewSet"""
    queryset = StockAllocation.objects.all().select_related('product').prefetch_related(
        Prefetch(
            'product__bomitem_set',
            queryset=BOMItem.objects.select_related('line', 'supplier'),
            to_attr='prefetched_bom_items',
        )
    )
    serializer_class = StockAllocationSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = StockAllocationFilter
    search_fields = ['product__product_code', 'product__product_name', 'location']
    ordering_fields = ['current_stock', 'reserved_qty', 'min_stock_qty', 'updated_at']
    ordering = ['-updated_at']

    @action(detail=True, methods=['post'])
    def reserve(self, request, pk=None):
        """
        在庫引当
        payload: { quantity: Decimal }
        """
        allocation = self.get_object()
        qty = request.data.get('quantity')

        if not qty:
            return Response({'detail': 'quantity is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            qty = Decimal(str(qty))
            if qty <= 0:
                return Response({'detail': 'quantity must be positive'}, status=status.HTTP_400_BAD_REQUEST)

            if allocation.available_qty < qty:
                return Response({
                    'detail': f'Insufficient stock. Available: {allocation.available_qty}, Requested: {qty}'
                }, status=status.HTTP_400_BAD_REQUEST)

            allocation.reserved_qty += qty
            allocation.save()

            serializer = self.get_serializer(allocation)
            return Response(serializer.data)

        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """
        引当解除
        payload: { quantity: Decimal }
        """
        allocation = self.get_object()
        qty = request.data.get('quantity')

        if not qty:
            return Response({'detail': 'quantity is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            qty = Decimal(str(qty))
            if qty <= 0:
                return Response({'detail': 'quantity must be positive'}, status=status.HTTP_400_BAD_REQUEST)

            if allocation.reserved_qty < qty:
                return Response({
                    'detail': f'Cannot release more than reserved. Reserved: {allocation.reserved_qty}, Requested: {qty}'
                }, status=status.HTTP_400_BAD_REQUEST)

            allocation.reserved_qty -= qty
            allocation.save()

            serializer = self.get_serializer(allocation)
            return Response(serializer.data)

        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProductionOrderFilter(django_filters.FilterSet):
    """製造指示フィルタ"""
    product_code = django_filters.CharFilter(field_name='product__product_code', lookup_expr='icontains')
    status = django_filters.MultipleChoiceFilter(choices=ProductionOrder._meta.get_field('status').choices)
    scheduled_start_date_from = django_filters.DateFilter(field_name='scheduled_start_date', lookup_expr='gte')
    scheduled_start_date_to = django_filters.DateFilter(field_name='scheduled_start_date', lookup_expr='lte')

    class Meta:
        model = ProductionOrder
        fields = ['product', 'product_code', 'line', 'status', 'scheduled_start_date']


class ProductionOrderViewSet(viewsets.ModelViewSet):
    """製造指示ViewSet"""
    queryset = ProductionOrder.objects.all().select_related(
        'product', 'routing', 'line', 'allocation'
    )
    serializer_class = ProductionOrderSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductionOrderFilter
    search_fields = ['order_no', 'product__product_code', 'product__product_name']
    ordering_fields = ['scheduled_start_date', 'scheduled_end_date', 'priority', 'created_at']
    ordering = ['-scheduled_start_date', 'priority']

    def get_queryset(self):
        qs = ProductionOrder.objects.select_related('product', 'routing', 'line', 'allocation')
        # 詳細取得時のみ工程実績をプリフェッチ
        if self.action != 'list':
            qs = qs.prefetch_related('actuals__process', 'actuals__line')
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductionOrderListSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=['post'], url_path='sync-from-plan')
    def sync_from_plan(self, request):
        """
        LineBacklog の plan_id を製造指示番号として同期する。
        payload: { line_id?, start_date?, end_date? }
        """
        line_id = request.data.get('line_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        backlog_qs = LineBacklog.objects.exclude(plan_id__isnull=True).exclude(plan_id='').filter(plan_qty__gt=0)
        if line_id:
            backlog_qs = backlog_qs.filter(line_id=line_id)
        if start_date:
            backlog_qs = backlog_qs.filter(plan_date__gte=start_date)
        if end_date:
            backlog_qs = backlog_qs.filter(plan_date__lte=end_date)

        from masters.models import Product
        product_cache = {}
        routing_cache = {}
        created = 0
        updated = 0
        skipped = 0
        seen = set()

        for backlog in backlog_qs.select_related('product'):
            plan_id = backlog.plan_id
            if not plan_id or plan_id in seen:
                continue
            seen.add(plan_id)

            plan_product_code = plan_id.split('_', 1)[0]
            product = product_cache.get(plan_product_code)
            if product is None:
                product = Product.objects.filter(product_code=plan_product_code).first()
                product_cache[plan_product_code] = product
            if not product:
                product = backlog.product
            if not product or not backlog.plan_date:
                skipped += 1
                continue

            routing = routing_cache.get(product.id)
            if routing is None:
                routing = resolve_effective_routing(product.id, backlog.plan_date)
                routing_cache[product.id] = routing

            defaults = {
                'product_id': product.id,
                'routing_id': routing.id if routing else None,
                'line_id': backlog.line_id,
                'order_qty': backlog.plan_qty,
                'scheduled_start_date': backlog.plan_date,
                'scheduled_end_date': backlog.plan_date,
                'priority': backlog.sequence_no or 0,
            }

            order, is_created = ProductionOrder.objects.get_or_create(
                order_no=plan_id,
                defaults=defaults
            )
            if is_created:
                created += 1
                continue
            if order.status != 'PLANNED':
                continue

            changed = False
            for key, value in defaults.items():
                if getattr(order, key) != value:
                    setattr(order, key, value)
                    changed = True
            if changed:
                order.save()
                updated += 1

        return Response({
            'created': created,
            'updated': updated,
            'skipped': skipped,
        })

    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """
        製造指示発行（計画済→指示済）
        """
        order = self.get_object()

        if order.status != 'PLANNED':
            return Response({
                'detail': f'Cannot release order with status: {order.get_status_display()}'
            }, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'RELEASED'
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        製造開始（指示済→進行中）
        """
        order = self.get_object()

        if order.status != 'RELEASED':
            return Response({
                'detail': f'Cannot start order with status: {order.get_status_display()}'
            }, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone
        order.status = 'IN_PROGRESS'
        order.actual_start_date = timezone.now()
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        製造完了（進行中→完了）
        """
        order = self.get_object()

        if order.status != 'IN_PROGRESS':
            return Response({
                'detail': f'Cannot complete order with status: {order.get_status_display()}'
            }, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone
        order.status = 'COMPLETED'
        order.actual_end_date = timezone.now()
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        製造中止
        """
        order = self.get_object()

        if order.status == 'COMPLETED':
            return Response({
                'detail': 'Cannot cancel completed order'
            }, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'CANCELED'
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)


class ProcessActualFilter(django_filters.FilterSet):
    """工程実績フィルタ"""
    production_order_no = django_filters.CharFilter(field_name='production_order__order_no', lookup_expr='icontains')
    completed_at_from = django_filters.DateTimeFilter(field_name='completed_at', lookup_expr='gte')
    completed_at_to = django_filters.DateTimeFilter(field_name='completed_at', lookup_expr='lte')

    class Meta:
        model = ProcessActual
        fields = ['production_order', 'process', 'line', 'operator']


class ProcessActualViewSet(viewsets.ModelViewSet):
    """工程実績ViewSet"""
    queryset = ProcessActual.objects.all().select_related(
        'production_order', 'production_order__product', 'routing_step', 'process', 'line'
    )
    serializer_class = ProcessActualSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProcessActualFilter
    search_fields = ['production_order__order_no', 'process__process_code', 'operator']
    ordering_fields = ['completed_at', 'actual_duration_min', 'created_at']
    ordering = ['-completed_at']


class LineDailyScheduleSettingViewSet(viewsets.ModelViewSet):
    """ライン別日次スケジュール設定ViewSet"""
    queryset = LineDailyScheduleSetting.objects.all().select_related('line')
    serializer_class = LineDailyScheduleSettingSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['line', 'plan_date']
    ordering_fields = ['plan_date', 'line']
    ordering = ['plan_date', 'line']

    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        """複数日の設定を一括保存"""
        settings_data = request.data.get('settings', [])
        if not settings_data:
            return Response({'error': 'settings is required'}, status=status.HTTP_400_BAD_REQUEST)

        created_count = 0
        updated_count = 0
        errors = []

        for setting_data in settings_data:
            line_id = setting_data.get('line')
            plan_date = setting_data.get('plan_date')

            if not line_id or not plan_date:
                errors.append({'error': 'line and plan_date are required', 'data': setting_data})
                continue

            try:
                obj, created = LineDailyScheduleSetting.objects.update_or_create(
                    line_id=line_id,
                    plan_date=plan_date,
                    defaults={
                        'final_process_start_time': setting_data.get('final_process_start_time'),
                        'adjust_to_break_end': setting_data.get('adjust_to_break_end', True),
                    }
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            except Exception as e:
                errors.append({'error': str(e), 'data': setting_data})

        return Response({
            'created': created_count,
            'updated': updated_count,
            'errors': errors
        }, status=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS)


class LineDefaultScheduleSettingViewSet(viewsets.ModelViewSet):
    """ライン別デフォルトスケジュール設定ViewSet"""

    queryset = LineDefaultScheduleSetting.objects.all().select_related('line')
    serializer_class = LineDefaultScheduleSettingSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['line']
    ordering_fields = ['line']
    ordering = ['line']

    def create(self, request, *args, **kwargs):
        """ライン単位でupsert（既存があれば更新）"""
        line_id = request.data.get('line')
        if not line_id:
            return Response({'detail': 'line is required'}, status=status.HTTP_400_BAD_REQUEST)

        final_process_start_time = request.data.get('final_process_start_time')
        adjust_to_break_end = request.data.get('adjust_to_break_end', True)
        if isinstance(adjust_to_break_end, str):
            adjust_to_break_end = adjust_to_break_end.lower() in ('true', '1', 'yes')

        obj, created = LineDefaultScheduleSetting.objects.update_or_create(
            line_id=line_id,
            defaults={
                'final_process_start_time': final_process_start_time or None,
                'adjust_to_break_end': adjust_to_break_end,
                'updated_by': request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
            }
        )
        serializer = self.get_serializer(obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        """複数ラインのデフォルト設定を一括保存"""
        settings_data = request.data.get('settings', [])
        if not settings_data:
            return Response({'error': 'settings is required'}, status=status.HTTP_400_BAD_REQUEST)

        created_count = 0
        updated_count = 0
        errors = []
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

        changed_line_ids = []
        for setting_data in settings_data:
            line_id = setting_data.get('line')
            if not line_id:
                errors.append({'error': 'line is required', 'data': setting_data})
                continue
            final_time = setting_data.get('final_process_start_time') or None
            adjust = setting_data.get('adjust_to_break_end', True)
            if isinstance(adjust, str):
                adjust = adjust.lower() in ('true', '1', 'yes')
            try:
                obj, created = LineDefaultScheduleSetting.objects.update_or_create(
                    line_id=line_id,
                    defaults={
                        'final_process_start_time': final_time,
                        'adjust_to_break_end': adjust,
                        'updated_by': user,
                    }
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                changed_line_ids.append(line_id)
            except Exception as e:
                errors.append({'error': str(e), 'data': setting_data})

        # デフォルト変更時は日別設定をリセット（次回ロード時に新デフォルトが適用される）
        if changed_line_ids:
            LineDailyScheduleSetting.objects.filter(line_id__in=changed_line_ids).delete()

        return Response(
            {
                'created': created_count,
                'updated': updated_count,
                'errors': errors,
            },
            status=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS,
        )


class AutoPlanAggregateSettingViewSet(viewsets.ModelViewSet):
    """自動計画まとめ生産設定ViewSet"""

    queryset = AutoPlanAggregateSetting.objects.all().select_related('line', 'product')
    serializer_class = AutoPlanAggregateSettingSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['line', 'product', 'is_active']
    search_fields = ['line__line_code', 'line__line_name', 'product__product_code', 'product__product_name']
    ordering_fields = ['line__line_code', 'product__product_code', 'aggregate_weekday', 'aggregate_days', 'updated_at']
    ordering = ['line__line_code', 'product__product_code']

    def perform_create(self, serializer):
        user = self.request.user if getattr(self.request, 'user', None) and self.request.user.is_authenticated else None
        serializer.save(updated_by=user)

    def perform_update(self, serializer):
        user = self.request.user if getattr(self.request, 'user', None) and self.request.user.is_authenticated else None
        serializer.save(updated_by=user)


from .views_laser import (
    LaserActualDetailUpdateView,
    LaserActualViewSet,
    LaserPatternViewSet,
    LaserShiftRecordViewSet,
)

class ProductionPlanLockSettingView(APIView):
    def get(self, request):
        setting = ProductionPlanLockSetting.objects.first()
        if not setting:
            user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
            setting = ProductionPlanLockSetting.objects.create(lock_days=0, updated_by=user)
        serializer = ProductionPlanLockSettingSerializer(setting)
        return Response(serializer.data)

    def post(self, request):
        raw_days = request.data.get('lock_days')
        try:
            lock_days = int(raw_days)
        except (TypeError, ValueError):
            return Response({'detail': 'lock_days must be integer'}, status=status.HTTP_400_BAD_REQUEST)
        if lock_days < 0:
            return Response({'detail': 'lock_days must be >= 0'}, status=status.HTTP_400_BAD_REQUEST)

        setting = ProductionPlanLockSetting.objects.first()
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        if not setting:
            setting = ProductionPlanLockSetting.objects.create(lock_days=lock_days, updated_by=user)
        else:
            setting.lock_days = lock_days
            setting.updated_by = user
            setting.save(update_fields=['lock_days', 'updated_at', 'updated_by'])

        serializer = ProductionPlanLockSettingSerializer(setting)
        return Response(serializer.data)


class ProductionRecordInquirySettingView(APIView):
    PROCESS_PREV_DAY_SHIFT_RULES_KEY = 'production.process_prev_day_shift_rules'
    PROCESS_GANTT_START_TIME_RULES_KEY = 'production.process_gantt_start_time_rules'
    PLANNED_STOCK_RULES_KEY = 'production.planned_stock_calc_rules'
    GANTT_EXCLUDED_PROCESS_RULES_KEY = 'production.gantt_excluded_process_rules'
    PRODUCT_MAPPINGS_KEY = 'production.product_mappings'

    def _normalize(self, value):
        return str(value or '').strip().upper()

    def _normalize_line_codes(self, values):
        source = values if isinstance(values, list) else []
        result = []
        seen = set()
        for item in source:
            code = self._normalize(item)
            if not code or code in seen:
                continue
            seen.add(code)
            result.append(code)
        return result

    def _normalize_mapping_rows(self, rows):
        source = rows if isinstance(rows, list) else []
        normalized = []
        for row in source:
            app_product_code = self._normalize((row or {}).get('appProductCode'))
            process_code = self._normalize((row or {}).get('processCode'))
            core_product_code = str((row or {}).get('coreProductCode') or '').strip()
            core_process_order = str((row or {}).get('coreProcessOrder') or '').strip()
            enter_count_raw = (row or {}).get('enterCount')
            enter_count = 2
            try:
                if enter_count_raw is not None and str(enter_count_raw).strip() != '':
                    value = int(float(enter_count_raw))
                    if 1 <= value <= 20:
                        enter_count = value
                    else:
                        enter_count = 2
            except (TypeError, ValueError):
                enter_count = 2
            if not app_product_code or not core_product_code:
                continue
            normalized.append({
                'appProductCode': app_product_code,
                'processCode': process_code,
                'coreProductCode': core_product_code,
                'coreProcessOrder': core_process_order,
                'enterCount': enter_count,
            })
        return normalized

    def _normalize_prev_day_shift_rules(self, rows):
        source = rows if isinstance(rows, list) else []
        normalized = []
        seen = set()
        for row in source:
            line_code = self._normalize((row or {}).get('lineCode'))
            process_code = self._normalize((row or {}).get('processCode'))
            shift_qty_raw = (row or {}).get('shiftQty', 0)
            try:
                shift_qty = int(float(shift_qty_raw))
            except (TypeError, ValueError):
                shift_qty = 0
            if not line_code or not process_code:
                continue
            if shift_qty <= 0:
                continue
            key = f'{line_code}|{process_code}'
            if key in seen:
                continue
            seen.add(key)
            normalized.append({
                'lineCode': line_code,
                'processCode': process_code,
                'shiftQty': shift_qty,
            })
        return normalized

    def _normalize_gantt_start_time_rules(self, rows):
        source = rows if isinstance(rows, list) else []
        normalized = []
        seen = set()
        for row in source:
            line_code = self._normalize((row or {}).get('lineCode'))
            process_code = self._normalize((row or {}).get('processCode'))
            start_time = str((row or {}).get('startTime') or '').strip()
            if not line_code or not process_code:
                continue
            try:
                parsed = datetime.strptime(start_time, '%H:%M').time()
                start_time = parsed.strftime('%H:%M')
            except (TypeError, ValueError):
                continue
            key = f'{line_code}|{process_code}'
            if key in seen:
                continue
            seen.add(key)
            normalized.append({
                'lineCode': line_code,
                'processCode': process_code,
                'startTime': start_time,
            })
        return normalized

    def _normalize_planned_stock_calc_rules(self, rows):
        source = rows if isinstance(rows, list) else []
        normalized = []
        seen = set()
        allowed_targets = {'STOCK', 'PLANNED_STOCK', 'DEMAND'}
        allowed_settings = {'ORDER_QTY', 'ACTUAL_OR_PLAN'}
        for row in source:
            line_code = self._normalize((row or {}).get('lineCode'))
            process_code = self._normalize((row or {}).get('processCode'))
            # 旧形式(item/mode)と新形式(calcTarget/setting)の両方を受ける
            calc_target = self._normalize((row or {}).get('calcTarget') or 'PLANNED_STOCK')
            setting = self._normalize((row or {}).get('setting'))
            old_item = self._normalize((row or {}).get('item'))
            old_mode = self._normalize((row or {}).get('mode'))
            if old_item == 'PARENT_SHIPMENT_SOURCE' and old_mode == 'PLAN':
                setting = 'ORDER_QTY'
            if setting == 'PARENT_PLAN':
                setting = 'ORDER_QTY'
            if old_item == 'PARENT_SHIPMENT_SOURCE' and calc_target not in allowed_targets:
                calc_target = 'PLANNED_STOCK'
            if not line_code or not process_code:
                continue
            if calc_target not in allowed_targets:
                continue
            if setting not in allowed_settings:
                continue
            key = f'{line_code}|{process_code}|{calc_target}'
            if key in seen:
                continue
            seen.add(key)
            normalized.append({
                'lineCode': line_code,
                'processCode': process_code,
                'calcTarget': calc_target,
                'setting': setting,
            })
        return normalized

    def _normalize_gantt_excluded_process_rules(self, rows):
        source = rows if isinstance(rows, list) else []
        normalized = []
        seen = set()
        for row in source:
            line_code = self._normalize((row or {}).get('lineCode'))
            process_code = self._normalize((row or {}).get('processCode'))
            if not line_code or not process_code:
                continue
            key = f'{line_code}|{process_code}'
            if key in seen:
                continue
            seen.add(key)
            normalized.append({'lineCode': line_code, 'processCode': process_code})
        return normalized

    def _build_response_payload(self):
        rows = ProductionRecordInquirySetting.objects.all()
        tabs = [{'key': r.tab_key, 'label': r.tab_name or r.tab_key, 'sort_order': r.sort_order} for r in rows]
        target_line_codes_by_tab = {r.tab_key: self._normalize_line_codes(r.target_line_codes) for r in rows}

        # フラットマッピング: SystemSettingから読込、なければタブ行からマージ（後方互換）
        flat_row = SystemSetting.objects.filter(key=self.PRODUCT_MAPPINGS_KEY).first()
        if flat_row:
            try:
                product_mappings = self._normalize_mapping_rows(json.loads(flat_row.value or '[]'))
            except Exception:
                product_mappings = []
        else:
            seen = set()
            product_mappings = []
            for row in rows:
                for m in self._normalize_mapping_rows(row.product_mappings):
                    key = f"{m['appProductCode']}__{m['processCode']}"
                    if key not in seen:
                        seen.add(key)
                        product_mappings.append(m)

        special_rules = {'prev_day_shift_rules': [], 'gantt_start_time_rules': [], 'planned_stock_calc_rules': [], 'gantt_excluded_process_rules': []}
        rules_row = SystemSetting.objects.filter(key=self.PROCESS_PREV_DAY_SHIFT_RULES_KEY).first()
        if rules_row:
            try:
                parsed = json.loads(rules_row.value or '[]')
            except Exception:
                parsed = []
            special_rules['prev_day_shift_rules'] = self._normalize_prev_day_shift_rules(parsed)
        start_time_row = SystemSetting.objects.filter(key=self.PROCESS_GANTT_START_TIME_RULES_KEY).first()
        if start_time_row:
            try:
                parsed = json.loads(start_time_row.value or '[]')
            except Exception:
                parsed = []
            special_rules['gantt_start_time_rules'] = self._normalize_gantt_start_time_rules(parsed)
        planned_stock_row = SystemSetting.objects.filter(key=self.PLANNED_STOCK_RULES_KEY).first()
        if planned_stock_row:
            try:
                parsed = json.loads(planned_stock_row.value or '[]')
            except Exception:
                parsed = []
            special_rules['planned_stock_calc_rules'] = self._normalize_planned_stock_calc_rules(parsed)
        gantt_excluded_row = SystemSetting.objects.filter(key=self.GANTT_EXCLUDED_PROCESS_RULES_KEY).first()
        if gantt_excluded_row:
            try:
                parsed = json.loads(gantt_excluded_row.value or '[]')
            except Exception:
                parsed = []
            special_rules['gantt_excluded_process_rules'] = self._normalize_gantt_excluded_process_rules(parsed)

        return {
            'tabs': tabs,
            'target_line_codes_by_tab': target_line_codes_by_tab,
            'product_mappings': product_mappings,
            'special_rules': special_rules,
        }

    def get(self, request):
        return Response(self._build_response_payload())

    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

        # タブ新規作成
        new_tab = payload.get('create_tab')
        if isinstance(new_tab, dict):
            tab_key = str(new_tab.get('key') or '').strip().lower()
            tab_name = str(new_tab.get('label') or '').strip()
            if tab_key and tab_name:
                max_order = ProductionRecordInquirySetting.objects.aggregate(m=Max('sort_order'))['m'] or 0
                ProductionRecordInquirySetting.objects.update_or_create(
                    tab_key=tab_key,
                    defaults={
                        'tab_name': tab_name,
                        'sort_order': max_order + 1,
                        'target_line_codes': [],
                        'updated_by': user,
                    },
                )
            return Response(self._build_response_payload())

        # タブ名変更
        rename_tab = payload.get('rename_tab')
        if isinstance(rename_tab, dict):
            tab_key = str(rename_tab.get('key') or '').strip().lower()
            new_name = str(rename_tab.get('label') or '').strip()
            if tab_key and new_name:
                ProductionRecordInquirySetting.objects.filter(tab_key=tab_key).update(tab_name=new_name, updated_by=user)
            return Response(self._build_response_payload())

        # タブ削除
        delete_tab_key = payload.get('delete_tab')
        if delete_tab_key:
            tab_key = str(delete_tab_key).strip().lower()
            ProductionRecordInquirySetting.objects.filter(tab_key=tab_key).delete()
            return Response(self._build_response_payload())

        raw_target = payload.get('target_line_codes_by_tab') if isinstance(payload.get('target_line_codes_by_tab'), dict) else {}
        raw_special_rules = payload.get('special_rules') if isinstance(payload.get('special_rules'), dict) else {}

        existing_rows = {row.tab_key: row for row in ProductionRecordInquirySetting.objects.all()}
        for tab_key, row in existing_rows.items():
            if tab_key in raw_target:
                target_source = raw_target[tab_key]
            else:
                target_source = row.target_line_codes
            row.target_line_codes = self._normalize_line_codes(target_source)
            row.updated_by = user
            row.save(update_fields=['target_line_codes', 'updated_by', 'updated_at'])

        # フラットマッピング保存
        if 'product_mappings' in payload:
            raw_product_mappings = payload.get('product_mappings', [])
            flat_mappings = self._normalize_mapping_rows(
                raw_product_mappings if isinstance(raw_product_mappings, list) else []
            )
            SystemSetting.objects.update_or_create(
                key=self.PRODUCT_MAPPINGS_KEY,
                defaults={
                    'value': json.dumps(flat_mappings, ensure_ascii=False),
                    'description': '生産実績照会 品番マッピング',
                    'updated_by': user,
                },
            )

        if 'prev_day_shift_rules' in raw_special_rules:
            rules = self._normalize_prev_day_shift_rules(raw_special_rules.get('prev_day_shift_rules'))
            SystemSetting.objects.update_or_create(
                key=self.PROCESS_PREV_DAY_SHIFT_RULES_KEY,
                defaults={
                    'value': json.dumps(rules, ensure_ascii=False),
                    'description': 'ライン工程別の前日シフト台数設定',
                    'updated_by': user,
                },
            )
        if 'gantt_start_time_rules' in raw_special_rules:
            rules = self._normalize_gantt_start_time_rules(raw_special_rules.get('gantt_start_time_rules'))
            SystemSetting.objects.update_or_create(
                key=self.PROCESS_GANTT_START_TIME_RULES_KEY,
                defaults={
                    'value': json.dumps(rules, ensure_ascii=False),
                    'description': 'ライン工程別のガント開始時刻設定',
                    'updated_by': user,
                },
            )
        if 'planned_stock_calc_rules' in raw_special_rules:
            rules = self._normalize_planned_stock_calc_rules(raw_special_rules.get('planned_stock_calc_rules'))
            SystemSetting.objects.update_or_create(
                key=self.PLANNED_STOCK_RULES_KEY,
                defaults={
                    'value': json.dumps(rules, ensure_ascii=False),
                    'description': 'ライン工程別の計画在庫計算特例設定',
                    'updated_by': user,
                },
            )
        if 'gantt_excluded_process_rules' in raw_special_rules:
            rules = self._normalize_gantt_excluded_process_rules(raw_special_rules.get('gantt_excluded_process_rules'))
            SystemSetting.objects.update_or_create(
                key=self.GANTT_EXCLUDED_PROCESS_RULES_KEY,
                defaults={
                    'value': json.dumps(rules, ensure_ascii=False),
                    'description': 'ライン工程別のガント展開除外設定',
                    'updated_by': user,
                },
            )

        return Response(self._build_response_payload())


class LineBacklogAdjustmentView(APIView):
    """LineBacklog調整の保存/取得API"""

    def get(self, request):
        qs = LineBacklogAdjustment.objects.select_related('line', 'product', 'process', 'updated_by').all().order_by('-plan_date', '-id')

        line_code = (request.query_params.get('line_code') or '').strip()
        product_code = (request.query_params.get('product_code') or '').strip()
        process_code = (request.query_params.get('process_code') or '').strip()
        adjust_type = (request.query_params.get('adjust_type') or '').strip().upper()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if line_code:
            qs = qs.filter(line__line_code=line_code)
        if product_code:
            qs = qs.filter(product__product_code=product_code)
        if process_code:
            qs = qs.filter(process__process_code=process_code)
        if adjust_type:
            qs = qs.filter(adjust_type=adjust_type)
        if start_date:
            qs = qs.filter(plan_date__gte=start_date)
        if end_date:
            qs = qs.filter(plan_date__lte=end_date)

        serializer = LineBacklogAdjustmentSerializer(qs[:500], many=True)
        return Response(serializer.data)

    def post(self, request):
        line_code = (request.data.get('line_code') or '').strip()
        product_code = (request.data.get('product_code') or '').strip()
        process_code = (request.data.get('process_code') or '').strip()
        plan_date_raw = request.data.get('plan_date')
        adjust_type = str(request.data.get('adjust_type') or '').upper().strip()
        reason = str(request.data.get('reason') or '').strip()

        if not line_code or not product_code or not plan_date_raw or not adjust_type:
            return Response({'detail': 'line_code, product_code, plan_date, adjust_type は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            plan_date = datetime.strptime(str(plan_date_raw), '%Y-%m-%d').date()
        except ValueError as e:
            return Response({'detail': f'plan_date形式が不正です: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            adjust_qty = int(request.data.get('adjust_qty', 0))
        except (TypeError, ValueError):
            return Response({'detail': 'adjust_qty は整数で指定してください'}, status=status.HTTP_400_BAD_REQUEST)

        valid_types = {'STOCK', 'PLANNED_STOCK', 'PROGRESS', 'PLANNED_PROGRESS'}
        if adjust_type not in valid_types:
            return Response({'detail': 'adjust_type が不正です'}, status=status.HTTP_400_BAD_REQUEST)

        line = Line.objects.filter(line_code=line_code, is_active=True).first()
        if not line:
            return Response({'detail': f'ラインが見つかりません: {line_code}'}, status=status.HTTP_400_BAD_REQUEST)

        product = Product.objects.filter(product_code=product_code).first()
        if not product:
            return Response({'detail': f'品番が見つかりません: {product_code}'}, status=status.HTTP_400_BAD_REQUEST)

        process = None
        if process_code:
            process = Process.objects.filter(process_code=process_code).first()
            if not process:
                return Response({'detail': f'工程が見つかりません: {process_code}'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        obj, _ = LineBacklogAdjustment.objects.update_or_create(
            line=line,
            product=product,
            process=process,
            plan_date=plan_date,
            adjust_type=adjust_type,
            defaults={
                'adjust_qty': adjust_qty,
                'reason': reason,
                'updated_by': user,
            },
        )
        serializer = LineBacklogAdjustmentSerializer(obj)
        return Response(serializer.data)

    def delete(self, request):
        pk = request.query_params.get('id')
        if not pk:
            return Response({'detail': 'id は必須です'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            obj = LineBacklogAdjustment.objects.get(pk=pk)
        except LineBacklogAdjustment.DoesNotExist:
            return Response({'detail': '対象レコードが見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ScheduleConfigView(APIView):
    """定時タスクスケジュール設定API"""

    def _ensure_defaults(self):
        """既定設定を補完（自動計画は社内/外作/購買ライン分を作成）"""
        inventory_defaults = [
            ('INVENTORY_RECALC', 7, 0, True),
            ('PICKUP_ONLY', 7, 30, False),
            ('INVENTORY_ONLY', 8, 0, False),
            ('PROGRESS_ONLY', 8, 30, False),
            ('KUBOTA_SAKAI_DUE_SYNC', 7, 45, False),
            ('AUTO_PURCHASE_ORDER_CHECK', 6, 30, False),
            ('PURCHASE_ACTUAL_RECONCILE_CHECK', 2, 0, False),
            ('PRODUCTION_ACTUAL_RECONCILE_CHECK', 2, 30, False),
            ('CONTAINER_IMPORT_TMP_CLEANUP', 3, 0, False),
        ]
        for task_name, hour, minute, is_enabled in inventory_defaults:
            ScheduleConfig.objects.get_or_create(
                task_name=task_name,
                line=None,
                defaults={
                    'scheduled_hour': hour,
                    'scheduled_minute': minute,
                    'is_enabled': is_enabled,
                    'range_base_day': 'TODAY',
                    'range_days_after': 45,
                },
            )
        ScheduleConfig.objects.get_or_create(
            task_name='ORDER_EXPANSION',
            line=None,
            defaults={
                'scheduled_hour': 6,
                'scheduled_minute': 0,
                'is_enabled': False,
                'range_base_day': 'TODAY',
                'range_days_after': 45,
            },
        )
        safety_defaults = [
            ('AUTO_SAFETY_STOCK_INTERNAL', 1, 3, 0, 60, 1, False),
            ('AUTO_SAFETY_STOCK_PURCHASE', 1, 3, 30, 60, 1, False),
        ]
        for task_name, dom, hour, minute, average_days_window, safety_days, is_enabled in safety_defaults:
            ScheduleConfig.objects.get_or_create(
                task_name=task_name,
                line=None,
                defaults={
                    'scheduled_dom': dom,
                    'scheduled_hour': hour,
                    'scheduled_minute': minute,
                    'is_enabled': is_enabled,
                    'range_base_day': 'TODAY',
                    'range_days_after': 45,
                    'average_days_window': average_days_window,
                    'safety_days': safety_days,
                },
            )
        base_plan = ScheduleConfig.objects.filter(task_name='AUTO_PLAN', line__isnull=False).first()
        if not base_plan:
            base_plan = ScheduleConfig.objects.filter(task_name='AUTO_PLAN', line__isnull=True).first()
        template = {
            'scheduled_hour': getattr(base_plan, 'scheduled_hour', 3) or 3,
            'scheduled_minute': getattr(base_plan, 'scheduled_minute', 0) or 0,
            'scheduled_dom': getattr(base_plan, 'scheduled_dom', 1),
            'is_enabled': getattr(base_plan, 'is_enabled', True),
            'include_next_month': getattr(base_plan, 'include_next_month', True),
            'include_second_month': getattr(base_plan, 'include_second_month', False),
            'include_third_month': getattr(base_plan, 'include_third_month', False),
        }
        target_types = ['PROD', 'OUTSOURCE', 'PURCHASE']
        for idx, line in enumerate(
            Line.objects.filter(is_active=True, line_type__in=target_types).order_by('line_type', 'line_code', 'id'),
            start=1
        ):
            ScheduleConfig.objects.get_or_create(
                task_name='AUTO_PLAN',
                line=line,
                defaults={**template, 'execution_order': idx},
            )

    def get(self, request):
        self._ensure_defaults()
        configs = ScheduleConfig.objects.select_related('line', 'process').order_by('task_name', 'execution_order', 'line__line_code')
        serializer = ScheduleConfigSerializer(configs, many=True)
        return Response(serializer.data)

    def post(self, request):
        config_id = request.data.get('id') or request.data.get('config_id')
        task_name = str(request.data.get('task_name', 'INVENTORY_RECALC')).upper()
        line_id = request.data.get('line')
        process_id = request.data.get('process')

        def to_bool(val, default=False):
            if val in (None, ''):
                return default
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in ('true', '1', 'yes', 'on')
            return bool(val)

        scheduled_hour = request.data.get('scheduled_hour')
        scheduled_minute = request.data.get('scheduled_minute', 0)
        scheduled_dom = request.data.get('scheduled_dom')
        execution_order = request.data.get('execution_order')
        range_base_day = (request.data.get('range_base_day') or 'TODAY').upper()
        range_days_after = request.data.get('range_days_after', 45)
        average_days_window = request.data.get('average_days_window', 60)
        safety_days = request.data.get('safety_days', 1)
        is_enabled = request.data.get('is_enabled', True)
        include_current_month = to_bool(request.data.get('include_current_month', False), False)
        include_next_month = to_bool(request.data.get('include_next_month', True), True)
        include_second_month = to_bool(request.data.get('include_second_month', False), False)
        include_third_month = to_bool(request.data.get('include_third_month', False), False)
        from_sequence_ui = to_bool(request.data.get('from_sequence_ui', False), False)

        try:
            scheduled_hour = int(scheduled_hour)
            scheduled_minute = int(scheduled_minute)
        except (TypeError, ValueError):
            return Response(
                {'detail': '時刻は整数で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (0 <= scheduled_hour <= 23) or not (0 <= scheduled_minute <= 59):
            return Response(
                {'detail': '時刻の範囲が不正です'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if scheduled_dom not in (None, '',):
            try:
                scheduled_dom = int(scheduled_dom)
            except (TypeError, ValueError):
                return Response({'detail': '実行日は1-31の整数で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
            if not (1 <= scheduled_dom <= 31):
                return Response({'detail': '実行日は1-31の範囲で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            scheduled_dom = None
        if execution_order in (None, ''):
            execution_order = None
        else:
            try:
                execution_order = int(execution_order)
            except (TypeError, ValueError):
                return Response({'detail': '実行順は整数で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
            if execution_order < 1:
                return Response({'detail': '実行順は1以上で指定してください'}, status=status.HTTP_400_BAD_REQUEST)

        if isinstance(is_enabled, str):
            is_enabled = is_enabled.lower() in ('true', '1', 'yes')

        allowed_base_days = {'TODAY', 'YESTERDAY', 'TWO_DAYS_AGO'}
        if range_base_day not in allowed_base_days:
            return Response(
                {'detail': '開始基準日は 今日 / 昨日 / 一昨日 から選択してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            range_days_after = int(range_days_after)
        except (TypeError, ValueError):
            return Response(
                {'detail': '何日後は整数で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (0 <= range_days_after <= 365):
            return Response(
                {'detail': '何日後は0〜365で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            average_days_window = int(average_days_window)
        except (TypeError, ValueError):
            return Response(
                {'detail': '実行日からの平均日数は整数で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (1 <= average_days_window <= 365):
            return Response(
                {'detail': '実行日からの平均日数は1〜365で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            safety_days = int(safety_days)
        except (TypeError, ValueError):
            return Response(
                {'detail': '安全在庫日数は整数で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (1 <= safety_days <= 365):
            return Response(
                {'detail': '安全在庫日数は1〜365で指定してください'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        line_obj = None
        process_obj = None
        safety_task_names = {'AUTO_SAFETY_STOCK_INTERNAL', 'AUTO_SAFETY_STOCK_PURCHASE'}
        if task_name == 'AUTO_PLAN':
            if not line_id:
                return Response({'detail': 'ラインを指定してください'}, status=status.HTTP_400_BAD_REQUEST)
            line_obj = Line.objects.filter(id=line_id, line_type__in=['PROD', 'OUTSOURCE', 'PURCHASE']).first()
            if not line_obj:
                return Response({'detail': '指定されたラインが見つかりません（社内/外作/購買ラインのみ設定可能）'}, status=status.HTTP_400_BAD_REQUEST)
            if not (include_current_month or include_next_month or include_second_month or include_third_month):
                return Response({'detail': '実行期間を1つ以上選択してください'}, status=status.HTTP_400_BAD_REQUEST)
        if task_name in safety_task_names and scheduled_dom is None:
            return Response({'detail': '安全在庫タスクは実行日（1-31）を指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        if task_name == 'PLAN_TO_ACTUAL_COPY':
            if not line_id:
                return Response({'detail': 'ラインを指定してください'}, status=status.HTTP_400_BAD_REQUEST)
            if not process_id:
                return Response({'detail': '工程を指定してください'}, status=status.HTTP_400_BAD_REQUEST)
            line_obj = Line.objects.filter(id=line_id, is_active=True).first()
            if not line_obj:
                return Response({'detail': '指定されたラインが見つかりません'}, status=status.HTTP_400_BAD_REQUEST)
            process_obj = Process.objects.filter(id=process_id, line_id=line_id).first()
            if not process_obj:
                return Response({'detail': '指定された工程が見つかりません（ライン不一致を含む）'}, status=status.HTTP_400_BAD_REQUEST)

        if config_id:
            config = ScheduleConfig.objects.filter(id=config_id).first()
            if not config:
                return Response({'detail': '設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        else:
            config, _ = ScheduleConfig.objects.get_or_create(
                task_name=task_name,
                line=line_obj,
                process=process_obj,
                defaults={
                    'scheduled_hour': scheduled_hour,
                    'scheduled_minute': scheduled_minute,
                    'scheduled_dom': scheduled_dom,
                    'range_base_day': range_base_day,
                    'range_days_after': range_days_after,
                    'average_days_window': average_days_window,
                    'safety_days': safety_days,
                    'is_enabled': is_enabled,
                    'include_current_month': include_current_month,
                    'include_next_month': include_next_month,
                    'include_second_month': include_second_month,
                    'include_third_month': include_third_month,
                },
            )

        if task_name == 'AUTO_PLAN' and getattr(config, 'auto_plan_sequence_locked', False) and not from_sequence_ui:
            return Response(
                {'detail': '自動計画は順序運用モードです。順序設定画面から編集してください。'},
                status=status.HTTP_409_CONFLICT,
            )

        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        config.scheduled_hour = scheduled_hour
        config.scheduled_minute = scheduled_minute
        config.scheduled_dom = scheduled_dom
        config.range_base_day = range_base_day
        config.range_days_after = range_days_after
        config.average_days_window = average_days_window
        config.safety_days = safety_days
        config.is_enabled = is_enabled
        config.include_current_month = include_current_month
        config.include_next_month = include_next_month
        config.include_second_month = include_second_month
        config.include_third_month = include_third_month
        if execution_order is not None:
            config.execution_order = execution_order
        if task_name == 'AUTO_PLAN':
            config.auto_plan_sequence_locked = from_sequence_ui
        if line_obj:
            config.line = line_obj
        if task_name == 'PLAN_TO_ACTUAL_COPY':
            config.process = process_obj
        config.updated_by = user
        update_fields = [
            'scheduled_hour', 'scheduled_minute', 'scheduled_dom',
            'range_base_day', 'range_days_after', 'average_days_window', 'safety_days',
            'is_enabled', 'include_current_month', 'include_next_month', 'include_second_month', 'include_third_month',
            'line', 'updated_at', 'updated_by',
        ]
        if task_name == 'PLAN_TO_ACTUAL_COPY':
            update_fields.append('process')
        if execution_order is not None:
            update_fields.append('execution_order')
        if task_name == 'AUTO_PLAN':
            update_fields.append('auto_plan_sequence_locked')
        config.save(update_fields=update_fields)

        notify_user_ids = request.data.get('notify_users', None)
        notify_user_codes = request.data.get('notify_user_codes', None)

        if notify_user_ids is not None:
            config.notify_users.set(notify_user_ids)
        elif notify_user_codes is not None:
            codes = notify_user_codes
            if isinstance(codes, str):
                import re
                codes = [c for c in re.split(r'[,\s]+', codes) if c]
            try:
                iter(codes)
            except TypeError:
                codes = []
            User = get_user_model()
            users = User.objects.filter(
                Q(profile__employee_code__in=codes) | Q(username__in=codes) | Q(email__in=codes)
            ).distinct()
            config.notify_users.set(users)

        serializer = ScheduleConfigSerializer(config)
        return Response(serializer.data)


class ScheduleRunLogView(APIView):
    """定時タスク実行履歴（直近分）"""

    def get(self, request):
        config_id = request.query_params.get('config_id')
        if not config_id:
            return Response({'detail': 'config_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        logs = ScheduleRunLog.objects.filter(config_id=config_id).order_by('-started_at')[:30]
        serializer = ScheduleRunLogSerializer(logs, many=True)
        return Response(serializer.data)


class ScheduleRunNowView(APIView):
    """定時タスクを手動実行（非同期）"""

    def post(self, request):
        import threading
        from .scheduler.tasks import run_inventory_recalculation
        from .scheduler.tasks_safety_stock import run_auto_safety_stock
        from .scheduler.tasks_auto_plan import run_auto_plan
        from .scheduler.tasks_order_expansion import run_order_expansion
        from .scheduler.tasks_purchase_actual_reconcile import run_purchase_actual_reconcile_check
        from .scheduler.tasks_production_actual_reconcile import run_production_actual_reconcile_check
        from .scheduler.tasks_plan_to_actual import run_plan_to_actual_copy
        from shipping.scheduler_tasks_kubota_sakai_due import run_kubota_sakai_due_sync
        from purchase.order_proposal_views import run_auto_purchase_order_check
        from masters.scheduler.tasks_container_import_cleanup import run_container_import_tmp_cleanup
        task = (request.data.get('task_name') or 'INVENTORY_RECALC').upper()
        task_labels = {
            'INVENTORY_RECALC': '取り込み＋在庫再計算',
            'PICKUP_ONLY': '取り込みのみ',
            'INVENTORY_ONLY': '在庫計算のみ',
            'PROGRESS_ONLY': '進度計算のみ',
            'KUBOTA_SAKAI_DUE_SYNC': 'クボタ堺納期調整 取込+再配分',
            'AUTO_SAFETY_STOCK_INTERNAL': '自動安全在庫（社内）',
            'AUTO_SAFETY_STOCK_PURCHASE': '自動安全在庫（購入品）',
            'AUTO_PURCHASE_ORDER_CHECK': '発注タイミング日次チェック',
            'PURCHASE_ACTUAL_RECONCILE_CHECK': '納入実績整合チェック',
            'PRODUCTION_ACTUAL_RECONCILE_CHECK': '生産実績整合チェック',
            'PLAN_TO_ACTUAL_COPY': '計画実績自動セット',
            'ORDER_EXPANSION': '自動受注展開',
            'CONTAINER_IMPORT_TMP_CLEANUP': '荷姿設定Excel取込 一時ファイル削除',
        }
        config_id = request.data.get('config_id') or request.data.get('id')
        line_id = request.data.get('line')
        try:
            if task == 'AUTO_PLAN':
                # config_id/line指定が無い場合は、設定済みAUTO_PLANを実行順で順次実行する
                if config_id:
                    config = ScheduleConfig.objects.filter(id=config_id).first()
                    if not config:
                        return Response({'detail': '対象設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
                    result = run_auto_plan(force=True, config_id=config.id)
                elif line_id:
                    config = ScheduleConfig.objects.filter(task_name='AUTO_PLAN', line_id=line_id).first()
                    if not config:
                        return Response({'detail': '対象設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
                    result = run_auto_plan(force=True, config_id=config.id)
                else:
                    result = run_auto_plan(force=True)
                return Response({'detail': '生産計画自動生成を実行しました', **(result or {})})
            elif task in task_labels:
                # 二重実行防止。
                # ただし、前日以前に開始されキャンセル要求済みの RUNNING は残留状態とみなし解放する。
                running_cfg = ScheduleConfig.objects.filter(
                    task_name=task,
                    last_run_status='RUNNING',
                ).first()
                if running_cfg:
                    if _is_stale_cancel_requested_run(running_cfg):
                        stale_message = (running_cfg.last_run_message or '').strip()
                        stale_message = (stale_message + '\n' if stale_message else '') + '前日以前のキャンセル要求済み実行を残留扱いで解放しました。'
                        running_cfg.last_run_status = 'FAILED'
                        running_cfg.last_run_message = stale_message
                        running_cfg.save(update_fields=['last_run_status', 'last_run_message'])
                    else:
                        running_msg = running_cfg.last_run_message or ''
                        if '[CANCEL_REQUESTED]' in running_msg:
                            detail = '既にキャンセル要求済みの実行が停止待ちです。完了までお待ちください。'
                        else:
                            detail = '既に実行中です。完了までお待ちください。必要なら「キャンセル要求」を実行してください。'
                        return Response({'detail': detail}, status=status.HTTP_409_CONFLICT)

                # バックグラウンドスレッドで実行
                def _run():
                    import django
                    django.db.connections.close_all()
                    try:
                        if task in {'AUTO_SAFETY_STOCK_INTERNAL', 'AUTO_SAFETY_STOCK_PURCHASE'}:
                            run_auto_safety_stock(task_name=task)
                        elif task == 'AUTO_PURCHASE_ORDER_CHECK':
                            run_auto_purchase_order_check()
                        elif task == 'PURCHASE_ACTUAL_RECONCILE_CHECK':
                            run_purchase_actual_reconcile_check(apply_fix=False)
                        elif task == 'PRODUCTION_ACTUAL_RECONCILE_CHECK':
                            run_production_actual_reconcile_check(apply_fix=False)
                        elif task == 'PLAN_TO_ACTUAL_COPY':
                            if not config_id:
                                raise ValueError('PLAN_TO_ACTUAL_COPY は config_id が必要です')
                            run_plan_to_actual_copy(config_id=int(config_id))
                        elif task == 'ORDER_EXPANSION':
                            run_order_expansion()
                        elif task == 'CONTAINER_IMPORT_TMP_CLEANUP':
                            run_container_import_tmp_cleanup()
                        elif task == 'KUBOTA_SAKAI_DUE_SYNC':
                            run_kubota_sakai_due_sync()
                        else:
                            run_inventory_recalculation(task_name=task)
                    except Exception:
                        logger.exception('バックグラウンドタスク実行に失敗')
                        ScheduleConfig.objects.filter(
                            task_name=task,
                            last_run_status='RUNNING',
                        ).update(last_run_status='FAILED', last_run_message='実行中にエラーが発生しました')

                thread = threading.Thread(target=_run, daemon=True)
                thread.start()
                return Response({
                    'detail': f'{task_labels[task]}をバックグラウンドで開始しました。',
                    'async': True,
                })
            else:
                return Response(
                    {'detail': f'未対応のタスクです: {task}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            logger.exception('手動実行に失敗')
            return Response(
                {'detail': f'実行に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PurchaseActualReconcileReportView(APIView):
    """納入実績整合チェックのレポート取得API"""

    def get(self, request):
        limit = request.query_params.get('limit', 10)
        detail_limit = request.query_params.get('detail_limit', 200)
        report_id = request.query_params.get('report_id')

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 50))

        try:
            detail_limit = int(detail_limit)
        except (TypeError, ValueError):
            detail_limit = 200
        detail_limit = max(1, min(detail_limit, 1000))

        report_qs = (
            PurchaseActualReconcileReport.objects
            .select_related('task_config', 'created_by')
            .order_by('-id')
        )
        if report_id:
            report_qs = report_qs.filter(id=report_id)

        reports = list(report_qs[:limit])
        latest = reports[0] if reports else None
        detail_rows = []
        if latest:
            detail_rows = list(
                PurchaseActualReconcileReportDetail.objects
                .filter(report_id=latest.id)
                .select_related('line', 'process', 'product')
                .order_by('plan_date', 'line__line_code', 'product__product_code')[:detail_limit]
            )

        return Response({
            'reports': PurchaseActualReconcileReportSerializer(reports, many=True).data,
            'details': PurchaseActualReconcileReportDetailSerializer(detail_rows, many=True).data,
            'latest_report_id': latest.id if latest else None,
        })


class PurchaseActualReconcileFixView(APIView):
    """納入実績整合チェックの手動修正実行API"""

    def post(self, request):
        from .scheduler.tasks_purchase_actual_reconcile import run_purchase_actual_reconcile_check

        task_name = 'PURCHASE_ACTUAL_RECONCILE_CHECK'
        running = ScheduleConfig.objects.filter(task_name=task_name, last_run_status='RUNNING').exists()
        if running:
            return Response(
                {'detail': '現在整合チェックが実行中です。完了後に再実行してください。'},
                status=status.HTTP_409_CONFLICT,
            )

        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        try:
            result = run_purchase_actual_reconcile_check(apply_fix=True, created_by=user)
            return Response({
                'detail': '修正を実行しました。',
                **result,
            })
        except Exception as e:
            logger.exception('納入実績整合修正に失敗')
            return Response(
                {'detail': f'修正に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ProductionActualReconcileReportView(APIView):
    """生産実績整合チェックのレポート取得API"""

    def get(self, request):
        limit = request.query_params.get('limit', 10)
        detail_limit = request.query_params.get('detail_limit', 200)
        report_id = request.query_params.get('report_id')

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 50))

        try:
            detail_limit = int(detail_limit)
        except (TypeError, ValueError):
            detail_limit = 200
        detail_limit = max(1, min(detail_limit, 1000))

        report_qs = (
            ProductionActualReconcileReport.objects
            .select_related('task_config', 'created_by')
            .order_by('-id')
        )
        if report_id:
            report_qs = report_qs.filter(id=report_id)

        reports = list(report_qs[:limit])
        latest = reports[0] if reports else None
        detail_rows = []
        if latest:
            detail_rows = list(
                ProductionActualReconcileReportDetail.objects
                .filter(report_id=latest.id)
                .select_related('line', 'process', 'product')
                .order_by('plan_date', 'line__line_code', 'product__product_code')[:detail_limit]
            )

        return Response({
            'reports': ProductionActualReconcileReportSerializer(reports, many=True).data,
            'details': ProductionActualReconcileReportDetailSerializer(detail_rows, many=True).data,
            'latest_report_id': latest.id if latest else None,
        })


class ProductionActualReconcileFixView(APIView):
    """生産実績整合チェックの手動修正実行API"""

    def post(self, request):
        from .scheduler.tasks_production_actual_reconcile import run_production_actual_reconcile_check

        task_name = 'PRODUCTION_ACTUAL_RECONCILE_CHECK'
        running = ScheduleConfig.objects.filter(task_name=task_name, last_run_status='RUNNING').exists()
        if running:
            return Response(
                {'detail': '現在整合チェックが実行中です。完了後に再実行してください。'},
                status=status.HTTP_409_CONFLICT,
            )

        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        try:
            result = run_production_actual_reconcile_check(apply_fix=True, created_by=user)
            return Response({
                'detail': '修正を実行しました。',
                **result,
            })
        except Exception as e:
            logger.exception('生産実績整合修正に失敗')
            return Response(
                {'detail': f'修正に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ScheduleCancelView(APIView):
    """定時タスクのキャンセル要求API（実行中タスク向け）"""

    def post(self, request):
        from .scheduler.tasks import request_task_cancel

        task = (request.data.get('task_name') or 'INVENTORY_RECALC').upper()
        config_id = request.data.get('config_id') or request.data.get('id')
        supported_tasks = {'INVENTORY_RECALC', 'PICKUP_ONLY', 'INVENTORY_ONLY', 'PROGRESS_ONLY'}

        if task not in supported_tasks:
            return Response(
                {'detail': f'このタスクはキャンセル未対応です: {task}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if config_id:
            exists = ScheduleConfig.objects.filter(id=config_id, task_name=task).exists()
            if not exists:
                return Response({'detail': '対象設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)

        result = request_task_cancel(task)
        if not result.get('ok'):
            if result.get('reason') == 'not_found':
                return Response({'detail': '対象設定が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
            if result.get('reason') == 'not_running':
                return Response({'detail': '現在このタスクは実行中ではありません。'}, status=status.HTTP_409_CONFLICT)
            return Response({'detail': 'キャンセル要求に失敗しました。'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if result.get('already_requested'):
            return Response({'detail': '既にキャンセル要求済みです。停止完了までお待ちください。'})
        return Response({'detail': 'キャンセル要求を受け付けました。安全な区切りで停止します。'})


class StockMigrationDetectView(APIView):
    """
    ルーティング変更による孤立在庫を検出するAPI。
    ピックアップ実行前に呼び出し、移行候補を返す。

    POST payload: { line_id }
    返却: [{ product_id, product_code, product_name, old_line_id, old_line_code, old_line_name,
             old_process_id, old_process_code, old_process_name, stock_qty, new_line_id,
             new_line_code, new_line_name, new_process_id, new_process_code, new_process_name }]
    """

    def post(self, request):
        from django.db.models import Q
        from masters.models import RoutingStep
        from .models_line_backlog import LineBacklog

        line_id = request.data.get('line_id')
        if not line_id:
            return Response({'detail': 'line_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        # 現在有効なルーティングでこのラインに属する品番を取得
        active_steps = RoutingStep.objects.filter(
            Q(line_id=line_id) | Q(line__isnull=True, process__line_id=line_id),
        ).filter(
            build_effective_routing_q(prefix='routing__')
        ).select_related('output_product', 'routing__product', 'process', 'line', 'process__line').order_by(
            '-routing__is_default',
            '-routing__valid_from_datetime',
            'step_no',
        )

        product_new_info = {}
        for step in active_steps:
            product = step.output_product or step.routing.product
            if not product:
                continue
            if product.id in product_new_info:
                continue
            process = step.process
            new_line = step.line or (process.line if hasattr(process, 'line') else None)
            product_new_info[product.id] = {
                'product': product,
                'new_line': new_line,
                'new_process': process,
            }

        seen = set()
        results = []

        # --- 方向1: 他ラインにある在庫を、このラインに引き寄せる検出 ---
        if product_new_info:
            product_ids = list(product_new_info.keys())
            orphaned_pull = (
                LineBacklog.objects
                .filter(
                    product_id__in=product_ids,
                    source_routing_step__isnull=True,
                    sequence_no=0,
                )
                .exclude(stock_qty=0)
                .exclude(line_id=line_id)
                .select_related('product', 'line', 'process')
                .order_by('product__product_code', '-plan_date')
            )

            for lb in orphaned_pull:
                key = (lb.product_id, lb.line_id, lb.process_id)
                if key in seen:
                    continue
                seen.add(key)
                new_info = product_new_info[lb.product_id]
                new_line = new_info['new_line']
                new_process = new_info['new_process']
                results.append({
                    'product_id': lb.product_id,
                    'product_code': lb.product.product_code,
                    'product_name': lb.product.product_name,
                    'old_line_id': lb.line_id,
                    'old_line_code': lb.line.line_code if lb.line else '',
                    'old_line_name': lb.line.line_name if lb.line else '',
                    'old_process_id': lb.process_id,
                    'old_process_code': lb.process.process_code if lb.process else '',
                    'old_process_name': lb.process.process_name if lb.process else '',
                    'stock_qty': lb.stock_qty,
                    'new_line_id': new_line.id if new_line else None,
                    'new_line_code': new_line.line_code if new_line else '',
                    'new_line_name': new_line.line_name if new_line else '',
                    'new_process_id': new_process.id if new_process else None,
                    'new_process_code': new_process.process_code if new_process else '',
                    'new_process_name': new_process.process_name if new_process else '',
                })

        # --- 方向2: このラインに在庫があるが、有効ルーティングが別ラインの品番を検出 ---
        local_backlogs = (
            LineBacklog.objects
            .filter(
                line_id=line_id,
                source_routing_step__isnull=True,
                sequence_no=0,
            )
            .exclude(stock_qty=0)
            .select_related('product', 'line', 'process')
            .order_by('product__product_code', '-plan_date')
        )

        # このラインに有効ルーティングがある品番IDを除外対象にする
        local_active_product_ids = set(product_new_info.keys())

        # ローカル在庫のうち、このラインに有効ルーティングがない品番を抽出
        reverse_candidate_product_ids = set()
        reverse_backlogs = []
        for lb in local_backlogs:
            if lb.product_id not in local_active_product_ids:
                reverse_candidate_product_ids.add(lb.product_id)
                reverse_backlogs.append(lb)

        if reverse_candidate_product_ids:
            # これらの品番の有効ルーティングがどのラインにあるか調べる
            reverse_steps = RoutingStep.objects.filter(
                Q(routing__product_id__in=reverse_candidate_product_ids) |
                Q(output_product_id__in=reverse_candidate_product_ids),
            ).filter(
                build_effective_routing_q(prefix='routing__')
            ).select_related('output_product', 'routing__product', 'process', 'line', 'process__line').order_by(
                '-routing__is_default',
                '-routing__valid_from_datetime',
                'step_no',
            )

            # 品番ごとに移行先（有効ルーティングのライン・工程）を特定
            reverse_new_info = {}
            for step in reverse_steps:
                product = step.output_product or step.routing.product
                if not product or product.id not in reverse_candidate_product_ids:
                    continue
                if product.id in reverse_new_info:
                    continue
                process = step.process
                new_line = step.line or (process.line if hasattr(process, 'line') else None)
                # 有効ルーティングがこのラインと同じなら孤立ではない
                if new_line and new_line.id == int(line_id):
                    continue
                reverse_new_info[product.id] = {
                    'product': product,
                    'new_line': new_line,
                    'new_process': process,
                }

            for lb in reverse_backlogs:
                if lb.product_id not in reverse_new_info:
                    continue
                key = (lb.product_id, lb.line_id, lb.process_id)
                if key in seen:
                    continue
                seen.add(key)
                new_info = reverse_new_info[lb.product_id]
                new_line = new_info['new_line']
                new_process = new_info['new_process']
                results.append({
                    'product_id': lb.product_id,
                    'product_code': lb.product.product_code,
                    'product_name': lb.product.product_name,
                    'old_line_id': lb.line_id,
                    'old_line_code': lb.line.line_code if lb.line else '',
                    'old_line_name': lb.line.line_name if lb.line else '',
                    'old_process_id': lb.process_id,
                    'old_process_code': lb.process.process_code if lb.process else '',
                    'old_process_name': lb.process.process_name if lb.process else '',
                    'stock_qty': lb.stock_qty,
                    'new_line_id': new_line.id if new_line else None,
                    'new_line_code': new_line.line_code if new_line else '',
                    'new_line_name': new_line.line_name if new_line else '',
                    'new_process_id': new_process.id if new_process else None,
                    'new_process_code': new_process.process_code if new_process else '',
                    'new_process_name': new_process.process_name if new_process else '',
                })

        return Response(results)


class StockMigrationExecuteView(APIView):
    """
    ルーティング変更による在庫移行を実行するAPI。

    POST payload:
    {
      migration_date: "YYYY-MM-DD",
      items: [
        { product_id, old_line_id, old_process_id, new_line_id, new_process_id, migrate_qty }
      ]
    }
    """

    def post(self, request):
        from datetime import date
        from django.db import transaction
        from .models_line_backlog import LineBacklog
        from .models_line_backlog_adjustment import LineBacklogAdjustment
        from .models_routing_migration_log import RoutingMigrationLog

        migration_date_str = request.data.get('migration_date')
        items = request.data.get('items', [])

        if not migration_date_str or not items:
            return Response({'detail': 'migration_date and items are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            migration_date = date.fromisoformat(migration_date_str)
        except ValueError:
            return Response({'detail': 'migration_date format must be YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

        # トランザクション前に全件バリデーション（部分失敗を防ぐ）
        validated = []
        for item in items:
            product_id = item.get('product_id')
            old_line_id = item.get('old_line_id')
            old_process_id = item.get('old_process_id')
            new_line_id = item.get('new_line_id')
            new_process_id = item.get('new_process_id')
            raw_qty = item.get('migrate_qty')

            if not all([product_id, old_line_id, old_process_id, new_line_id, new_process_id, raw_qty is not None]):
                return Response(
                    {'detail': f'必須フィールドが不足しています: {item}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                migrate_qty = int(raw_qty)
            except (TypeError, ValueError):
                return Response(
                    {'detail': f'migrate_qty は整数で指定してください: {raw_qty}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if migrate_qty == 0:
                return Response(
                    {'detail': f'品番ID {product_id}: migrate_qty は0以外で指定してください'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 孤立在庫（source_routing_step=NULL）の現在在庫を確認（超過移行を防ぐ）
            latest = (
                LineBacklog.objects
                .filter(
                    product_id=product_id,
                    line_id=old_line_id,
                    process_id=old_process_id,
                    sequence_no=0,
                    source_routing_step__isnull=True,
                )
                .exclude(stock_qty=0)
                .order_by('-plan_date')
                .first()
            )
            current_stock = latest.stock_qty if latest else 0
            # プラス在庫: migrate_qty は正で current_stock 以下
            # マイナス在庫: migrate_qty は負で current_stock 以上（絶対値で超えない）
            if current_stock > 0 and (migrate_qty < 0 or migrate_qty > current_stock):
                return Response(
                    {'detail': f'品番ID {product_id}: 移行数量({migrate_qty})が現在在庫({current_stock})を超えています'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if current_stock < 0 and (migrate_qty > 0 or migrate_qty < current_stock):
                return Response(
                    {'detail': f'品番ID {product_id}: 移行数量({migrate_qty})が現在在庫({current_stock})を超えています'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 同一内容の移行が既に実行済みでないか確認（二重実行防止）
            already_migrated = RoutingMigrationLog.objects.filter(
                product_id=product_id,
                old_line_id=old_line_id,
                old_process_id=old_process_id,
                new_line_id=new_line_id,
                new_process_id=new_process_id,
                migration_date=migration_date,
            ).exists()
            if already_migrated:
                return Response(
                    {'detail': f'品番ID {product_id}: 同日・同ライン組み合わせの移行が既に実行済みです。二重実行を防ぐためスキップしてください。'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            validated.append({
                'product_id': product_id,
                'old_line_id': old_line_id,
                'old_process_id': old_process_id,
                'new_line_id': new_line_id,
                'new_process_id': new_process_id,
                'migrate_qty': migrate_qty,
            })

        # 全件を1トランザクションで実行（1件でも失敗したら全ロールバック）
        migrated = []
        try:
            with transaction.atomic():
                for item in validated:
                    product_id = item['product_id']
                    old_line_id = item['old_line_id']
                    old_process_id = item['old_process_id']
                    new_line_id = item['new_line_id']
                    new_process_id = item['new_process_id']
                    migrate_qty = item['migrate_qty']
                    user = request.user if request.user.is_authenticated else None

                    # 旧ラインの在庫をマイナス調整
                    old_adj, _ = LineBacklogAdjustment.objects.get_or_create(
                        line_id=old_line_id,
                        product_id=product_id,
                        process_id=old_process_id,
                        plan_date=migration_date,
                        adjust_type='STOCK',
                        defaults={'adjust_qty': 0, 'reason': 'ルーティング変更による在庫移行（移行元）'},
                    )
                    old_adj.adjust_qty -= migrate_qty
                    old_adj.reason = 'ルーティング変更による在庫移行（移行元）'
                    old_adj.updated_by = user
                    old_adj.save()

                    # 新ラインの在庫をプラス調整
                    new_adj, _ = LineBacklogAdjustment.objects.get_or_create(
                        line_id=new_line_id,
                        product_id=product_id,
                        process_id=new_process_id,
                        plan_date=migration_date,
                        adjust_type='STOCK',
                        defaults={'adjust_qty': 0, 'reason': 'ルーティング変更による在庫移行（移行先）'},
                    )
                    new_adj.adjust_qty += migrate_qty
                    new_adj.reason = 'ルーティング変更による在庫移行（移行先）'
                    new_adj.updated_by = user
                    new_adj.save()

                    # 移行ログ記録
                    RoutingMigrationLog.objects.create(
                        product_id=product_id,
                        old_line_id=old_line_id,
                        old_process_id=old_process_id,
                        new_line_id=new_line_id,
                        new_process_id=new_process_id,
                        migrated_qty=migrate_qty,
                        migration_date=migration_date,
                        migrated_by=user,
                    )

                    migrated.append({
                        'product_id': product_id,
                        'migrate_qty': migrate_qty,
                    })
        except Exception as e:
            return Response(
                {'detail': f'移行処理中にエラーが発生しました（全件ロールバック済み）: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({'migrated': migrated, 'count': len(migrated)})


class FloorShippingPDFView(APIView):
    """フロア配送 8時着/15時着 明細PDF生成"""

    def get(self, request):
        line_id = request.query_params.get('line')
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        if not line_id or not start or not end:
            return Response(
                {'detail': 'line, start_date, end_date は必須です'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            from datetime import datetime as dt
            start_date = dt.strptime(start, '%Y-%m-%d').date()
            end_date = dt.strptime(end, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'detail': '日付形式が不正です (YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from production.services.floor_shipping_pdf import generate_floor_shipping_pdf
        try:
            pdf_bytes = generate_floor_shipping_pdf(int(line_id), start_date, end_date)
        except Exception as e:
            logger.exception('フロア配送PDF生成エラー')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        from django.http import HttpResponse as DjangoHttpResponse
        response = DjangoHttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f'フロア配送明細_{start}_{end}.pdf'
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class FloorShippingNewPDFView(APIView):
    """新品番ベースのフロア配送明細PDF"""

    def get(self, request):
        line_id = request.query_params.get('line')
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        if not line_id or not start or not end:
            return Response(
                {'detail': 'line, start_date, end_date は必須です'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            from datetime import datetime as dt
            start_date = dt.strptime(start, '%Y-%m-%d').date()
            end_date = dt.strptime(end, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'detail': '日付形式が不正です (YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from production.services.floor_shipping_pdf import generate_floor_shipping_new_pdf
        try:
            pdf_bytes = generate_floor_shipping_new_pdf(int(line_id), start_date, end_date)
        except Exception as e:
            logger.exception('新配送明細PDF生成エラー')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        from django.http import HttpResponse as DjangoHttpResponse
        response = DjangoHttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f'フロア配送明細_新_{start}_{end}.pdf'
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class FloorShippingLapPDFView(APIView):
    """フロア配送 ラップ期間用PDF（新旧品番併記、午前/午後各1ページ）"""

    def get(self, request):
        line_id = request.query_params.get('line')
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        if not line_id or not start or not end:
            return Response(
                {'detail': 'line, start_date, end_date は必須です'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            from datetime import datetime as dt
            start_date = dt.strptime(start, '%Y-%m-%d').date()
            end_date = dt.strptime(end, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'detail': '日付形式が不正です (YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from production.services.floor_shipping_pdf import generate_floor_shipping_lap_pdf
        try:
            pdf_bytes = generate_floor_shipping_lap_pdf(int(line_id), start_date, end_date)
        except Exception as e:
            logger.exception('フロア配送ラップPDF生成エラー')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        from django.http import HttpResponse as DjangoHttpResponse
        response = DjangoHttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f'フロア配送明細_ラップ_{start}_{end}.pdf'
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class HokushinDeliveryListPDFView(APIView):
    """北進納入リストPDF生成"""

    @staticmethod
    def _resolve_creator_name(request) -> str:
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return 'システム'

        last_name = (getattr(user, 'last_name', '') or '').strip()
        if last_name:
            return last_name

        username = (user.get_username() or '').strip()
        if username:
            return username

        email = (getattr(user, 'email', '') or '').strip()
        return email or 'システム'

    def get(self, request):
        line_id = request.query_params.get('line')
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        if not line_id or not start or not end:
            return Response(
                {'detail': 'line, start_date, end_date は必須です'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from datetime import datetime as dt

            start_date = dt.strptime(start, '%Y-%m-%d').date()
            end_date = dt.strptime(end, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'detail': '日付形式が不正です (YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from production.services.hokushin_delivery_list_pdf import generate_hokushin_delivery_list_pdf
        try:
            creator_name = self._resolve_creator_name(request)
            pdf_bytes = generate_hokushin_delivery_list_pdf(
                int(line_id),
                start_date,
                end_date,
                creator_name=creator_name,
            )
        except Exception as e:
            logger.exception('北進納入リストPDF生成エラー')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        from django.http import HttpResponse as DjangoHttpResponse

        response = DjangoHttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f'北進納入リスト_{start}_{end}.pdf'
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class HokushinDeliveryListNewPDFView(APIView):
    """新品番ベースの北進納入リストPDF"""

    @staticmethod
    def _resolve_creator_name(request) -> str:
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return 'システム'
        last_name = (getattr(user, 'last_name', '') or '').strip()
        if last_name:
            return last_name
        username = (user.get_username() or '').strip()
        if username:
            return username
        email = (getattr(user, 'email', '') or '').strip()
        return email or 'システム'

    def get(self, request):
        line_id = request.query_params.get('line')
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        if not line_id or not start or not end:
            return Response(
                {'detail': 'line, start_date, end_date は必須です'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            from datetime import datetime as dt
            start_date = dt.strptime(start, '%Y-%m-%d').date()
            end_date = dt.strptime(end, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'detail': '日付形式が不正です (YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from production.services.hokushin_delivery_list_pdf import generate_hokushin_delivery_list_new_pdf
        try:
            creator_name = self._resolve_creator_name(request)
            pdf_bytes = generate_hokushin_delivery_list_new_pdf(
                int(line_id), start_date, end_date, creator_name=creator_name,
            )
        except Exception as e:
            logger.exception('新北進納入リストPDF生成エラー')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        from django.http import HttpResponse as DjangoHttpResponse
        response = DjangoHttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f'北進納入リスト_新_{start}_{end}.pdf'
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class HokushinDeliveryListLapPDFView(APIView):
    """北進納入リスト ラップ期間用PDF（新旧品番併記、午前/午後各1ページ）"""

    def get(self, request):
        line_id = request.query_params.get('line')
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        if not line_id or not start or not end:
            return Response(
                {'detail': 'line, start_date, end_date は必須です'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from datetime import datetime as dt
            start_date = dt.strptime(start, '%Y-%m-%d').date()
            end_date = dt.strptime(end, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'detail': '日付形式が不正です (YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from production.services.hokushin_delivery_list_pdf import generate_hokushin_delivery_list_lap_pdf
        try:
            creator_name = HokushinDeliveryListPDFView._resolve_creator_name(request)
            pdf_bytes = generate_hokushin_delivery_list_lap_pdf(
                int(line_id), start_date, end_date, creator_name=creator_name,
            )
        except Exception as e:
            logger.exception('北進納入リストラップPDF生成エラー')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        from django.http import HttpResponse as DjangoHttpResponse
        response = DjangoHttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f'北進納入リスト_ラップ_{start}_{end}.pdf'
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class HokushinDeliveryPDFView(APIView):
    """㈱北進塗装様向け 納品書PDF生成（AM便 + 宵積み 2ページ）

    Query params:
        line: ライン ID（必須）
        preview: '1' ならPDFを生成せずデフォルト日付と便の有無をJSON返却
        am_delivery_date: AM便 納品日（YYYY-MM-DD、省略時=本日）
        yoi_delivery_date: 宵積み 納品日（YYYY-MM-DD、省略時=翌営業日）
    """

    def get(self, request):
        line_id = request.query_params.get('line')
        if not line_id:
            return Response(
                {'detail': 'line は必須です'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from datetime import datetime as dt
        from production.services.hokushin_delivery_pdf import (
            generate_hokushin_delivery_pdf,
            preview_hokushin_delivery,
            EmptyDeliveryError,
        )

        # 日付パラメータの解釈
        def _parse_date(key):
            raw = request.query_params.get(key)
            if not raw:
                return None
            try:
                return dt.strptime(raw, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError(f'{key} の日付形式が不正です (YYYY-MM-DD)')

        try:
            am_date = _parse_date('am_delivery_date')
            yoi_date = _parse_date('yoi_delivery_date')
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # プレビューモード: デフォルト日付と便の有無をJSONで返却
        if request.query_params.get('preview') == '1':
            try:
                data = preview_hokushin_delivery(int(line_id))
            except Exception as e:
                logger.exception('北進塗装納品書プレビューエラー')
                return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response(data)

        try:
            pdf_bytes = generate_hokushin_delivery_pdf(
                int(line_id), am_delivery_date=am_date, yoi_delivery_date=yoi_date
            )
        except EmptyDeliveryError as e:
            return Response(
                {'detail': str(e), 'code': 'EMPTY_DELIVERY'},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.exception('北進塗装納品書PDF生成エラー')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        from django.http import HttpResponse as DjangoHttpResponse
        from orders.utils.calendar_utils import get_business_today
        today = get_business_today()
        response = DjangoHttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f'北進塗装納品書_{today.strftime("%Y%m%d")}.pdf'
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class HokushinDeliveryAllPDFView(APIView):
    """㈱北進塗装様向け 納品書PDF（全製品版）

    Query params:
        line: ライン ID（必須）
        preview: '1' ならPDFを生成せずデフォルト日付と便の有無をJSON返却
        am_delivery_date: AM便 納品日（YYYY-MM-DD、省略時=本日）
        yoi_delivery_date: 宵積み 納品日（YYYY-MM-DD、省略時=翌営業日）
    """

    def get(self, request):
        line_id = request.query_params.get('line')
        if not line_id:
            return Response(
                {'detail': 'line は必須です'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from datetime import datetime as dt
        from production.services.hokushin_delivery_pdf import (
            generate_hokushin_delivery_all_pdf,
            preview_hokushin_delivery_all,
        )

        def _parse_date(key):
            raw = request.query_params.get(key)
            if not raw:
                return None
            try:
                return dt.strptime(raw, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError(f'{key} の日付形式が不正です (YYYY-MM-DD)')

        try:
            am_date = _parse_date('am_delivery_date')
            yoi_date = _parse_date('yoi_delivery_date')
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if request.query_params.get('preview') == '1':
            try:
                data = preview_hokushin_delivery_all(int(line_id))
            except Exception as e:
                logger.exception('北進塗装納品書（全製品）プレビューエラー')
                return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response(data)

        try:
            pdf_bytes = generate_hokushin_delivery_all_pdf(
                int(line_id), am_delivery_date=am_date, yoi_delivery_date=yoi_date
            )
        except Exception as e:
            logger.exception('北進塗装納品書（全製品）PDF生成エラー')
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        from django.http import HttpResponse as DjangoHttpResponse
        from orders.utils.calendar_utils import get_business_today
        today = get_business_today()
        response = DjangoHttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f'北進塗装納品書（全製品）_{today.strftime("%Y%m%d")}.pdf'
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


