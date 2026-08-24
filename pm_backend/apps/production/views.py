from rest_framework import viewsets, status
from rest_framework.views import APIView
from decimal import Decimal, InvalidOperation
from datetime import timedelta, datetime, date
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
    StockAllocationSerializer,
    ProductionOrderSerializer,
    ProductionOrderListSerializer,
    ProcessActualSerializer,
    LineBacklogAdjustmentSerializer,
    LaserPatternSerializer,
    LaserActualSerializer,
    LaserShiftRecordSerializer,
)
from .services import (
    backlog_pickup_service,
    backlog_recalc_service,
    backlog_save_service,
    gantt_plan_generation_service,
    gantt_schedule_adjustment_service,
    gantt_structure_mutation_service,
    line_plan_mutation_service,
)
from .services.recalc_start_date import (
    resolve_inventory_effective_start_date,
    resolve_product_recalc_start_date,
)
from .views_line_demand import LineDemandViewSet
from .views_plan_line_setting import ProductionPlanLineSettingView
from masters.models import Routing, RoutingStep, ProcessCycleTime, Line, Supplier, Process, Calendar, CalendarDay, BOM, BOMItem, Product, KubotaSakaiTruck
from masters.services.routing_service import build_effective_routing_q, build_effective_routing_range_q, normalize_routing_reference_datetime, resolve_effective_routing
from orders.utils.calendar_utils import get_business_today, add_working_days
from purchase.process_resolver import (
    is_outsource_process,
    resolve_purchase_line as resolve_supplier_purchase_line,
    resolve_supplier_process,
)
from django.db.models import Q

logger = logging.getLogger(__name__)

FLOOR_SHIPPING_TAB_KEY = 'floor-shipping'
FLOOR_SHIPPING_DELIVERY_LABEL = 'フロア配送'
FLOOR_SHIPPING_PM_SEQUENCE_THRESHOLD = 50
INVALID_SEQUENCE_SORT_VALUE = 10 ** 9

# クボタ配送ライン: plan_id から truck_id を抽出して arrival_day_offset ベースで LT を決定
KUBOTA_DELIVERY_LABELS = ('L3102', 'KUBOTA_DELIVERY', 'クボタ配送')


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
        return line_plan_mutation_service.bulk_delete(self, request)

    @action(detail=False, methods=['post'])
    def save(self, request):
        return line_plan_mutation_service.save(
            self,
            request,
            is_floor_shipping_delivery_line=_is_floor_shipping_delivery_line,
            logger=logger,
        )


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
        return backlog_save_service.save(
            self,
            request,
            resolve_effective_routing=resolve_effective_routing,
        )

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
        return gantt_plan_generation_service.generate(self, request, logger=logger)

    @action(detail=False, methods=['post'], url_path='manual-add')
    def manual_add(self, request):
        return gantt_structure_mutation_service.manual_add(self, request)

    @action(detail=False, methods=['post'], url_path='bulk-structure-save')
    def bulk_structure_save(self, request):
        return gantt_structure_mutation_service.bulk_structure_save(self, request)

    @action(detail=False, methods=['get'], url_path='singleproc-finished-entries')
    def singleproc_finished_entries(self, request):
        from .services.single_process_plan_query_service import list_finished_entries
        return list_finished_entries(self, request)

    @action(detail=False, methods=['post'], url_path='sub-process-save')
    def sub_process_save(self, request):
        from .services.single_process_plan import sub_process_save
        return sub_process_save(self, request)

    @action(detail=False, methods=['put'], url_path='bulk-update')
    def bulk_update(self, request):
        return gantt_schedule_adjustment_service.bulk_update(self, request)

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
        return gantt_structure_mutation_service.remove_process(self, request)


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


