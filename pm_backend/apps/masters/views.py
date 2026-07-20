from rest_framework import viewsets, status, parsers, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Exists, Max, OuterRef, Q
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import django_filters
import os
import uuid
import csv
import zipfile
import base64
import xml.etree.ElementTree as ET
from io import BytesIO, StringIO
from decimal import Decimal, InvalidOperation
from datetime import date, datetime, timedelta
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.datavalidation import DataValidation
from .models import (
    Product, Customer, Process, Line, Supplier, Calendar, CalendarDay, WorkPattern, BreakTime,
    BOM, BOMItem, Routing, RoutingStep, RoutingStepMaterial, ProductGroup, ContainerCapacity,
    ContainerCapacityImage, ProductContainer, Equipment, Contact,
    KubotaSakaiTruck, MobileDevice, MobileDeviceInventory, ManualDocument, ProductCodeMapping,
    ProductStockLocation,
)
from .serializers import (
    ProductSerializer, CustomerSerializer, ProcessSerializer, LineSerializer,
    SupplierSerializer, CalendarSerializer, CalendarDaySerializer, WorkPatternSerializer, BreakTimeSerializer,
    BOMSerializer, BOMListSerializer, BOMItemSerializer, RoutingSerializer, RoutingListSerializer, RoutingStepSerializer,
    RoutingStepMaterialSerializer, ProductGroupSerializer, ContainerCapacitySerializer, EquipmentSerializer, ContactSerializer,
    KubotaSakaiTruckSerializer, MobileDeviceSerializer, MobileDeviceInventorySerializer, ProductCodeMappingSerializer
)
from .services.routing_service import build_effective_routing_q, resolve_effective_routing
from accounts.permissions import HasResourcePermissionOrReadOnly
from django.utils.dateparse import parse_datetime, parse_date


class MastersPermissionMixin:
    """マスターデータ: 認証のみ（権限チェックはフロントエンドで行う）"""
    permission_classes = [IsAuthenticated, HasResourcePermissionOrReadOnly]
    # permission_resource = 'masters'  # フロントエンドで権限管理を行うため、バックエンドでは設定しない


def build_media_absolute_url(request, raw_url):
    """メディアURLを返す。相対パスはそのまま返してブラウザのオリジンで解決させる。
    proxyやHTTPS環境でのMixed Content問題を避けるため絶対URLには変換しない。"""
    if not raw_url:
        return raw_url
    path = str(raw_url)
    if path.startswith(('http://', 'https://')):
        return path
    # /で始まる相対パス（例: /media/products/xxx.jpg）はそのまま返す
    if path.startswith('/'):
        return path
    # 相対パスの場合はMEDIA_URLを付与
    from django.conf import settings as django_settings
    media_url = django_settings.MEDIA_URL.rstrip('/')
    return f"{media_url}/{path}"


def get_overlapping_default_routings(routing):
    """有効期間が重複する他の既定ルーティングを返す。"""
    qs = Routing.objects.filter(
        product_id=routing.product_id,
        is_default=True,
    ).exclude(id=routing.id)
    if routing.valid_from_datetime:
        qs = qs.exclude(valid_to_datetime__lt=routing.valid_from_datetime)
    if routing.valid_to_datetime:
        qs = qs.exclude(valid_from_datetime__gt=routing.valid_to_datetime)
    return qs


def ensure_supplier_purchase_line(supplier, previous_supplier_code=None):
    """仕入先に対応する購買ラインを作成または更新する。"""
    if not supplier:
        return None

    previous_code = str(previous_supplier_code or '').strip()
    expected_code = str(supplier.supplier_code or '').strip()
    expected_name = supplier.supplier_name[:50]

    line_obj = None
    if previous_code and previous_code != expected_code:
        line_obj = Line.objects.filter(line_code=previous_code, line_type='PURCHASE').first()

    if line_obj is None:
        line_obj = Line.objects.filter(line_code=expected_code).first()

    if line_obj is None:
        line_obj = Line.objects.create(
            line_code=expected_code,
            line_name=expected_name,
            line_type='PURCHASE',
            is_active=True,
        )
        return line_obj

    update_fields = []
    if line_obj.line_code != expected_code:
        line_obj.line_code = expected_code
        update_fields.append('line_code')
    if line_obj.line_name != expected_name:
        line_obj.line_name = expected_name
        update_fields.append('line_name')
    if line_obj.line_type != 'PURCHASE':
        line_obj.line_type = 'PURCHASE'
        update_fields.append('line_type')
    if not line_obj.is_active:
        line_obj.is_active = True
        update_fields.append('is_active')
    if update_fields:
        line_obj.save(update_fields=update_fields + ['updated_at'])

    return line_obj


class ProductFilter(django_filters.FilterSet):
    created_from = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_to = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    is_final_product = django_filters.BooleanFilter(field_name='is_final_product')
    is_line_final_product = django_filters.BooleanFilter(field_name='is_line_final_product')
    has_bom = django_filters.BooleanFilter(method='filter_has_bom')
    has_image = django_filters.BooleanFilter(method='filter_has_image')
    next_process_unset = django_filters.BooleanFilter(method='filter_next_process_unset')
    customer_code = django_filters.CharFilter(method='filter_customer_code')
    supplier_code = django_filters.CharFilter(method='filter_supplier_code')
    product_code = django_filters.CharFilter(field_name='product_code', lookup_expr='exact')
    product_codes_in = django_filters.CharFilter(method='filter_product_codes_in')
    stock_location = django_filters.CharFilter(method='filter_stock_location')
    processing_area = django_filters.CharFilter(field_name='processing_area', lookup_expr='exact')

    class Meta:
        model = Product
        fields = [
            'category',
            'is_active',
            'product_group',
            'is_final_product',
            'is_line_final_product',
            'has_bom',
            'has_image',
            'customer_code',
            'supplier_code',
            'line',
            'process',
            'next_process',
            'next_process_unset',
            'created_from',
            'created_to',
            'product_code',
            'product_codes_in',
            'stock_location',
            'processing_area',
        ]

    def filter_product_codes_in(self, queryset, name, value):
        if not value:
            return queryset
        codes = [c.strip() for c in value.split(',') if c.strip()]
        if not codes:
            return queryset
        return queryset.filter(product_code__in=codes)

    def filter_has_bom(self, queryset, name, value):
        if value is None:
            return queryset
        bom_exists = BOM.objects.filter(parent_product_id=OuterRef('pk'))
        queryset = queryset.annotate(_has_bom=Exists(bom_exists))
        if value:
            return queryset.filter(_has_bom=True)
        return queryset.filter(_has_bom=False)

    def filter_has_image(self, queryset, name, value):
        if value is None:
            return queryset
        if value:
            return queryset.exclude(image_url__isnull=True).exclude(image_url__exact='')
        return queryset.filter(Q(image_url__isnull=True) | Q(image_url__exact=''))

    def filter_customer_code(self, queryset, name, value):
        if not value:
            return queryset
        from orders.models import OrderLine

        order_lines = OrderLine.objects.filter(order__customer__customer_code=value)
        product_ids = order_lines.values_list('product_id', flat=True)
        product_codes = order_lines.values_list('product_code', flat=True)
        return queryset.filter(Q(id__in=product_ids) | Q(product_code__in=product_codes))

    def filter_supplier_code(self, queryset, name, value):
        if not value:
            return queryset
        supplier_items = BOMItem.objects.filter(
            child_product_id=OuterRef('pk'),
            supplier__supplier_code=value,
        )
        return queryset.annotate(_has_supplier=Exists(supplier_items)).filter(_has_supplier=True)

    def filter_stock_location(self, queryset, name, value):
        if not value:
            return queryset
        loc_product_ids = ProductStockLocation.objects.filter(
            location_name=value
        ).values_list('product_id', flat=True)
        return queryset.filter(Q(stock_location=value) | Q(id__in=loc_product_ids))

    def filter_next_process_unset(self, queryset, name, value):
        if value is None:
            return queryset
        if value:
            return queryset.filter(next_process__isnull=True)
        return queryset.filter(next_process__isnull=False)


class ProductViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = Product.objects.prefetch_related('stock_locations').all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['product_code', 'product_name', 'stock_location', 'stock_locations__location_name']
    ordering_fields = ['product_code', 'created_at']
    ordering = ['product_code']

    @action(detail=True, methods=['post'], url_path='upload_image', parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def upload_image(self, request, pk=None):
        product = self.get_object()
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'detail': 'ファイルがありません'}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(file_obj.name)[1] or ''
        filename = f"products/{product.product_code}_{uuid.uuid4().hex}{ext}"
        saved_path = default_storage.save(filename, file_obj)
        url = default_storage.url(saved_path)
        product.image_url = url
        product.save(update_fields=['image_url', 'updated_at'])
        absolute_url = build_media_absolute_url(request, url)
        return Response({'image_url': absolute_url}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='stock-locations')
    def set_stock_locations(self, request, pk=None):
        product = self.get_object()
        locations = request.data.get('locations', [])
        ProductStockLocation.objects.filter(product=product).delete()
        for i, loc in enumerate(locations):
            name = str(loc.get('location_name', '') if isinstance(loc, dict) else loc).strip()
            if name:
                ProductStockLocation.objects.create(product=product, location_name=name, sort_order=i)
        primary = locations[0] if locations else None
        primary_name = (primary.get('location_name', '') if isinstance(primary, dict) else str(primary)).strip() if primary else ''
        product.stock_location = primary_name
        product.save(update_fields=['stock_location', 'updated_at'])
        return Response({'stock_locations': list(
            product.stock_locations.values('id', 'location_name', 'sort_order')
        )})

    @action(detail=False, methods=['get'], url_path='line-final-candidates')
    def line_final_candidates(self, request):
        """ライン別にルーティングステップの出力品目を返す（ライン最終品の一括設定用）"""
        line_id = request.query_params.get('line_id')
        process_id = request.query_params.get('process_id')
        steps_qs = RoutingStep.objects.filter(
            line__isnull=False,
        ).filter(
            build_effective_routing_q(prefix='routing__')
        ).select_related('output_product', 'routing__product', 'line', 'process')

        if line_id:
            steps_qs = steps_qs.filter(line_id=line_id)
        if process_id:
            steps_qs = steps_qs.filter(process_id=process_id)

        # ライン別に出力品目を収集（重複排除）
        from collections import OrderedDict
        lines_map = OrderedDict()  # line_id -> {line_info, products: {product_id -> info}}

        for step in steps_qs.order_by('line__line_code', 'routing__product__product_code', 'step_no'):
            product = step.output_product or step.routing.product
            if not product:
                continue
            lid = step.line_id
            if lid not in lines_map:
                lines_map[lid] = {
                    'line_id': step.line.id,
                    'line_code': step.line.line_code,
                    'line_name': step.line.line_name,
                    'products': OrderedDict(),
                }
            if product.id not in lines_map[lid]['products']:
                lines_map[lid]['products'][product.id] = {
                    'id': product.id,
                    'product_code': product.product_code,
                    'product_name': product.product_name,
                    'is_line_final_product': product.is_line_final_product,
                    'is_final_product': product.is_final_product,
                    'category': product.category,
                }

        result = []
        for line_data in lines_map.values():
            result.append({
                'line_id': line_data['line_id'],
                'line_code': line_data['line_code'],
                'line_name': line_data['line_name'],
                'products': list(line_data['products'].values()),
            })
        return Response(result)

    @action(detail=False, methods=['get'], url_path='display-product-candidates')
    def display_product_candidates(self, request):
        """ライン+工程のoutput_product＋連産品を返す（ガント表示品マップ用）"""
        line_id = request.query_params.get('line_id')
        process_id = request.query_params.get('process_id')
        if not line_id or not process_id:
            return Response([])

        steps_qs = RoutingStep.objects.filter(
            line_id=line_id, process_id=process_id,
        ).filter(
            build_effective_routing_q(prefix='routing__')
        ).select_related('output_product')

        product_map = {}
        output_ids = set()
        for step in steps_qs:
            p = step.output_product
            if not p:
                continue
            output_ids.add(p.id)
            product_map[p.id] = {
                'id': p.id,
                'product_code': p.product_code,
                'product_name': p.product_name,
            }

        driver_items = BOMItem.objects.filter(
            bom__is_coproduct=True, bom__is_active=True,
            is_coproduct_driver=True, child_product_id__in=output_ids,
        ).select_related('bom__parent_product')
        for item in driver_items:
            pp = item.bom.parent_product
            if pp and pp.id not in product_map:
                product_map[pp.id] = {
                    'id': pp.id,
                    'product_code': pp.product_code,
                    'product_name': pp.product_name,
                }

        result = sorted(product_map.values(), key=lambda x: x['product_code'])
        return Response(result)

    @action(detail=False, methods=['post'], url_path='bulk-update-line-final')
    def bulk_update_line_final(self, request):
        """ライン最終品フラグを一括更新"""
        updates = request.data.get('updates', [])
        if not updates:
            return Response({'detail': '更新データがありません'}, status=status.HTTP_400_BAD_REQUEST)

        updated_count = 0
        for item in updates:
            product_id = item.get('id')
            is_line_final = item.get('is_line_final_product')
            if product_id is not None and is_line_final is not None:
                cnt = Product.objects.filter(id=product_id).update(is_line_final_product=is_line_final)
                updated_count += cnt

        return Response({'updated': updated_count})

    def _bulk_import_products(self, items):
        """製品データを一括登録。既存品番はスキップ。"""
        CATEGORY_MAP = {
            '集合部品': 'ASSEMBLY',
            '単体部品': 'SINGLE',
            '材料': 'MATERIAL',
            '購入品': 'PURCHASED',
            '外作品': 'OUTSOURCED',
        }
        MANAGEMENT_UNIT_MAP = {
            '日': 'DAY',
            '分': 'MINUTE',
            'DAY': 'DAY',
            'MINUTE': 'MINUTE',
        }
        if not items:
            raise serializers.ValidationError({'detail': 'データがありません'})

        existing_codes = set(
            Product.objects.filter(
                product_code__in=[i.get('product_code', '') for i in items]
            ).values_list('product_code', flat=True)
        )

        line_codes = {
            str(i.get('line_code') or '').strip()
            for i in items
            if str(i.get('line_code') or '').strip()
        }
        process_codes = {
            str(i.get('process_code') or '').strip()
            for i in items
            if str(i.get('process_code') or '').strip()
        }
        next_process_codes = {
            str(i.get('next_process_code') or '').strip()
            for i in items
            if str(i.get('next_process_code') or '').strip()
        }

        line_map = {
            line.line_code: line
            for line in Line.objects.filter(line_code__in=line_codes)
        }
        process_map = {
            process.process_code: process
            for process in Process.objects.filter(
                process_code__in=(process_codes | next_process_codes)
            )
        }

        def parse_bool(raw_value):
            value = str(raw_value or '').strip()
            return value in ['1', 'true', 'True', 'TRUE', 'はい', '有', '○']

        to_create = []
        skipped = []
        for item in items:
            code = (item.get('product_code') or '').strip()
            name = (item.get('product_name') or '').strip()
            category_raw = (item.get('category') or '').strip()
            line_code = (item.get('line_code') or '').strip()
            process_code = (item.get('process_code') or '').strip()
            next_process_code = (item.get('next_process_code') or '').strip()
            management_unit_raw = (item.get('management_unit') or '').strip()
            is_final_product_raw = item.get('is_final_product')
            is_line_final_product_raw = item.get('is_line_final_product')
            if not code:
                continue
            if code in existing_codes:
                skipped.append(code)
                continue
            category = CATEGORY_MAP.get(category_raw, 'UNKNOWN')
            to_create.append(Product(
                product_code=code,
                product_name=name or code,
                category=category,
                line=line_map.get(line_code),
                process=process_map.get(process_code),
                next_process=process_map.get(next_process_code),
                management_unit=MANAGEMENT_UNIT_MAP.get(management_unit_raw) if management_unit_raw else None,
                is_final_product=parse_bool(is_final_product_raw),
                is_line_final_product=parse_bool(is_line_final_product_raw),
            ))
            existing_codes.add(code)

        Product.objects.bulk_create(to_create)
        return {'created': len(to_create), 'skipped': len(skipped), 'skipped_codes': skipped}

    def _bulk_update_products(self, items, dry_run=False):
        """品番コードで照合し、既存は更新・未登録は新規作成（upsert）。空欄項目はスキップ。"""
        CATEGORY_MAP = {
            '集合部品': 'ASSEMBLY', '組立品': 'ASSEMBLY',
            '単体部品': 'SINGLE', '単品': 'SINGLE',
            '材料': 'MATERIAL',
            '購入品': 'PURCHASED',
            '外作品': 'OUTSOURCED',
        }
        MANAGEMENT_UNIT_MAP = {
            '日': 'DAY', '分': 'MINUTE', 'DAY': 'DAY', 'MINUTE': 'MINUTE',
        }
        TRANSFER_DEST_MAP = {
            '社内ライン': 'INLINE', '社内塗装': 'INPAINT',
            'CWL': 'CWL', '興和': 'KOWA', '直納': 'DIRECT', 'その他': 'OTHER',
        }
        if not items:
            raise serializers.ValidationError({'detail': 'データがありません'})

        codes = [str(i.get('product_code') or '').strip() for i in items]
        codes = [c for c in codes if c]
        existing_products = {
            p.product_code: p
            for p in Product.objects.filter(product_code__in=codes)
        }

        line_codes = {str(i.get('line_code') or '').strip() for i in items if str(i.get('line_code') or '').strip()}
        all_process_codes = set()
        for i in items:
            for key in ('process_code', 'next_process_code'):
                val = str(i.get(key) or '').strip()
                if val:
                    all_process_codes.add(val)
        group_codes = {str(i.get('product_group_code') or '').strip() for i in items if str(i.get('product_group_code') or '').strip()}

        line_map = {l.line_code: l for l in Line.objects.filter(line_code__in=line_codes)} if line_codes else {}
        process_map = {p.process_code: p for p in Process.objects.filter(process_code__in=all_process_codes)} if all_process_codes else {}
        group_map = {g.group_code: g for g in ProductGroup.objects.filter(group_code__in=group_codes)} if group_codes else {}

        def parse_bool(raw):
            val = str(raw or '').strip()
            if val in ('1', 'true', 'True', 'TRUE', 'はい', '有', '○'):
                return True
            if val in ('0', 'false', 'False', 'FALSE', 'いいえ', '無', '×'):
                return False
            return None

        def to_decimal_or_none(raw):
            val = str(raw or '').strip()
            if not val:
                return None
            try:
                return Decimal(val)
            except (InvalidOperation, ValueError):
                return None

        def to_int_or_none(raw):
            val = str(raw or '').strip()
            if not val:
                return None
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return None

        updated = []
        created = []
        skipped = []
        for item in items:
            code = str(item.get('product_code') or '').strip()
            if not code:
                continue
            product = existing_products.get(code)
            is_new = product is None
            if is_new:
                product = Product(
                    product_code=code,
                    product_name=code,
                    category='UNKNOWN',
                )

            changed_fields = []

            # 品名
            val = str(item.get('product_name') or '').strip()
            if val:
                product.product_name = val
                changed_fields.append('product_name')

            # カテゴリ
            val = str(item.get('category') or '').strip()
            if val:
                mapped = CATEGORY_MAP.get(val, val if val in dict(Product.CATEGORY_CHOICES) else None)
                if mapped:
                    product.category = mapped
                    changed_fields.append('category')

            # 単位
            val = str(item.get('unit') or '').strip()
            if val:
                product.unit = val
                changed_fields.append('unit')

            # 単価
            dec = to_decimal_or_none(item.get('unit_price'))
            if dec is not None:
                product.unit_price = dec
                changed_fields.append('unit_price')

            # 標準LT
            lt = to_int_or_none(item.get('standard_lt_days'))
            if lt is not None:
                product.standard_lt_days = lt
                changed_fields.append('standard_lt_days')

            # 自工程LT
            lt = to_int_or_none(item.get('self_lt_days'))
            if lt is not None:
                product.self_lt_days = lt
                changed_fields.append('self_lt_days')

            # ライン
            val = str(item.get('line_code') or '').strip()
            if val:
                line_obj = line_map.get(val)
                if line_obj:
                    product.line = line_obj
                    changed_fields.append('line')

            # 工程
            val = str(item.get('process_code') or '').strip()
            if val:
                proc_obj = process_map.get(val)
                if proc_obj:
                    product.process = proc_obj
                    changed_fields.append('process')

            # 後工程
            val = str(item.get('next_process_code') or '').strip()
            if val:
                proc_obj = process_map.get(val)
                if proc_obj:
                    product.next_process = proc_obj
                    changed_fields.append('next_process')

            # 管理区分
            val = str(item.get('management_unit') or '').strip()
            if val:
                mapped = MANAGEMENT_UNIT_MAP.get(val)
                if mapped:
                    product.management_unit = mapped
                    changed_fields.append('management_unit')

            # 最終品
            b = parse_bool(item.get('is_final_product'))
            if b is not None:
                product.is_final_product = b
                changed_fields.append('is_final_product')

            # ライン最終品
            b = parse_bool(item.get('is_line_final_product'))
            if b is not None:
                product.is_line_final_product = b
                changed_fields.append('is_line_final_product')

            # 機種名
            val = str(item.get('model_name') or '').strip()
            if val:
                product.model_name = val
                changed_fields.append('model_name')

            # 識別記号
            if 'identification_code' in item:
                product.identification_code = str(item.get('identification_code') or '').strip()
                changed_fields.append('identification_code')

            # 製品グループ
            val = str(item.get('product_group_code') or '').strip()
            if val:
                grp = group_map.get(val)
                if grp:
                    product.product_group = grp
                    changed_fields.append('product_group')

            # 移動先
            val = str(item.get('transfer_destination') or '').strip()
            if val:
                mapped = TRANSFER_DEST_MAP.get(val, val if val in dict(Product.TRANSFER_DESTINATION_CHOICES) else None)
                if mapped:
                    product.transfer_destination = mapped
                    changed_fields.append('transfer_destination')

            # 比重
            dec = to_decimal_or_none(item.get('specific_gravity'))
            if dec is not None:
                product.specific_gravity = dec
                changed_fields.append('specific_gravity')

            # 寸法
            for field_key, attr in [('size_length', 'size_length'), ('size_width', 'size_width'), ('size_thickness', 'size_thickness')]:
                dec = to_decimal_or_none(item.get(field_key))
                if dec is not None:
                    setattr(product, attr, dec)
                    changed_fields.append(attr)

            # 発注倍数
            v = to_int_or_none(item.get('order_lot_multiple'))
            if v is not None:
                product.order_lot_multiple = v
                changed_fields.append('order_lot_multiple')

            # 最小発注数
            v = to_int_or_none(item.get('order_lot_min'))
            if v is not None:
                product.order_lot_min = v
                changed_fields.append('order_lot_min')

            # 容器入り数
            v = to_int_or_none(item.get('capacity'))
            if v is not None:
                product.capacity = v
                changed_fields.append('capacity')

            # 置き場
            loc_names = []
            for loc_key in ('stock_location_1', 'stock_location_2', 'stock_location_3', 'stock_location_4'):
                val = str(item.get(loc_key) or '').strip()
                if val:
                    loc_names.append(val)
            has_locations = bool(loc_names)

            if is_new:
                if not dry_run:
                    product.save()
                    existing_products[code] = product
                    if has_locations:
                        for i, name in enumerate(loc_names):
                            ProductStockLocation.objects.create(product=product, location_name=name, sort_order=i)
                        product.stock_location = loc_names[0]
                        product.save(update_fields=['stock_location'])
                created.append(code)
            elif changed_fields or has_locations:
                if not dry_run:
                    if changed_fields:
                        changed_fields.append('updated_at')
                        product.save(update_fields=changed_fields)
                    if has_locations:
                        ProductStockLocation.objects.filter(product=product).delete()
                        for i, name in enumerate(loc_names):
                            ProductStockLocation.objects.create(product=product, location_name=name, sort_order=i)
                        product.stock_location = loc_names[0]
                        product.save(update_fields=['stock_location', 'updated_at'])
                updated.append(code)
            else:
                skipped.append(code)

        return {
            'created': len(created),
            'updated': len(updated),
            'skipped': len(skipped),
            'created_codes': created,
            'updated_codes': updated,
            'skipped_codes': skipped,
        }

    @action(detail=False, methods=['post'], parser_classes=[parsers.MultiPartParser, parsers.FormParser], url_path='bulk_update_import')
    def bulk_update_import(self, request):
        """製品の一括取込（CSV/Excel, upsert: 既存更新＋未登録新規）"""
        upload = request.FILES.get('file')
        if not upload:
            return Response({'detail': '取込ファイルがありません'}, status=status.HTTP_400_BAD_REQUEST)

        raw = upload.read()
        filename = (getattr(upload, 'name', '') or '').lower()
        input_rows = []

        HEADER_MAP = {
            '構成品番': 'product_code', '品番コード': 'product_code', '品番': 'product_code',
            '品名規格': 'product_name', '品名': 'product_name',
            '品番区分名': 'category', 'カテゴリ': 'category',
            '単位': 'unit',
            '単価': 'unit_price',
            '標準LT': 'standard_lt_days', '標準LT(日)': 'standard_lt_days',
            '自工程LT': 'self_lt_days', '自工程LT(日)': 'self_lt_days',
            'ライン情報': 'line_code', 'ラインコード': 'line_code',
            '工程情報': 'process_code', '工程コード': 'process_code',
            '後工程': 'next_process_code',
            '管理区分': 'management_unit',
            '最終品': 'is_final_product',
            'ライン最終品': 'is_line_final_product',
            '機種名': 'model_name',
            '識別記号': 'identification_code',
            '製品グループ': 'product_group_code', 'グループコード': 'product_group_code',
            '移動先': 'transfer_destination',
            '比重': 'specific_gravity', '比重(g/cm³)': 'specific_gravity',
            '縦': 'size_length', '縦(mm)': 'size_length',
            '横': 'size_width', '横(mm)': 'size_width',
            '厚さ': 'size_thickness', '厚さ(mm)': 'size_thickness',
            '発注倍数': 'order_lot_multiple',
            '最小発注数': 'order_lot_min',
            '容器入り数': 'capacity',
            '置き場1': 'stock_location_1',
            '置き場2': 'stock_location_2',
            '置き場3': 'stock_location_3',
            '置き場4': 'stock_location_4',
        }

        if filename.endswith('.xlsx') or filename.endswith('.xlsm'):
            from io import BytesIO
            try:
                wb = load_workbook(BytesIO(raw), data_only=True, read_only=True)
                ws = wb[wb.sheetnames[0]]
            except Exception:
                return Response({'detail': 'Excelファイルの読み取りに失敗しました'}, status=status.HTTP_400_BAD_REQUEST)
            excel_rows = list(ws.iter_rows(values_only=True))
            if not excel_rows:
                return Response({'detail': 'データがありません'}, status=status.HTTP_400_BAD_REQUEST)
            raw_headers = [str(v).strip() if v is not None else '' for v in excel_rows[0]]
            mapped_headers = [HEADER_MAP.get(h, h) for h in raw_headers]
            for row in excel_rows[1:]:
                if row is None or all((cell is None or str(cell).strip() == '') for cell in row):
                    continue
                row_dict = {}
                for i, key in enumerate(mapped_headers):
                    if not key:
                        continue
                    value = row[i] if i < len(row) else ''
                    row_dict[key] = '' if value is None else str(value).strip()
                input_rows.append(row_dict)
        else:
            text = None
            for enc in ('utf-8-sig', 'cp932', 'shift_jis', 'utf-8'):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if text is None:
                return Response({'detail': 'CSV文字コードを判別できません'}, status=status.HTTP_400_BAD_REQUEST)
            reader = csv.DictReader(StringIO(text))
            for row in reader:
                mapped_row = {}
                for orig_key, val in row.items():
                    mapped_key = HEADER_MAP.get(orig_key.strip(), orig_key.strip())
                    mapped_row[mapped_key] = str(val or '').strip()
                input_rows.append(mapped_row)

        if not input_rows:
            return Response({'detail': '取込データがありません'}, status=status.HTTP_400_BAD_REQUEST)

        seen = set()
        items = []
        for row in input_rows:
            code = str(row.get('product_code') or '').strip()
            if not code or code in seen:
                continue
            seen.add(code)
            items.append(row)

        dry_run = request.query_params.get('dry_run', '').lower() in ('true', '1')

        try:
            result = self._bulk_update_products(items, dry_run=dry_run)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    @action(detail=False, methods=['get'], url_path='update_import_template_xlsx')
    def update_import_template_xlsx(self, request):
        """更新取込用Excelテンプレート（全項目＋参照シート付き）"""
        wb = Workbook()
        ws = wb.active
        ws.title = '入力用'

        headers = [
            '構成品番', '品名規格', '品番区分名',
            'ライン情報', 'ライン名',
            '工程情報', '工程名',
            '後工程', '後工程名',
            '管理区分', '最終品', 'ライン最終品',
            '単位', '単価', '標準LT(日)', '自工程LT(日)',
            '機種名', '製品グループ', 'グループ名',
            '移動先',
            '比重(g/cm³)', '縦(mm)', '横(mm)', '厚さ(mm)',
            '発注倍数', '最小発注数', '容器入り数',
            '置き場1', '置き場2', '置き場3', '置き場4',
        ]
        ws.append(headers)
        ws.append([''] * len(headers))

        ws['E2'] = '=IFERROR(VLOOKUP(D2,ライン!A:B,2,FALSE),"")'
        ws['G2'] = '=IFERROR(VLOOKUP(F2,工程!A:B,2,FALSE),"")'
        ws['I2'] = '=IFERROR(VLOOKUP(H2,工程!A:B,2,FALSE),"")'
        ws['S2'] = '=IFERROR(VLOOKUP(R2,製品グループ!A:B,2,FALSE),"")'

        dv_category = DataValidation(type='list', formula1='"集合部品,単体部品,材料,購入品,外作品"', allow_blank=True)
        dv_unit_mgmt = DataValidation(type='list', formula1='"日,分"', allow_blank=True)
        dv_bool = DataValidation(type='list', formula1='"はい,いいえ"', allow_blank=True)
        dv_transfer = DataValidation(type='list', formula1='"社内ライン,社内塗装,CWL,興和,直納,その他"', allow_blank=True)
        ws.add_data_validation(dv_category)
        ws.add_data_validation(dv_unit_mgmt)
        ws.add_data_validation(dv_bool)
        ws.add_data_validation(dv_transfer)
        dv_category.add('C2:C5000')
        dv_unit_mgmt.add('J2:J5000')
        dv_bool.add('K2:K5000')
        dv_bool.add('L2:L5000')
        dv_transfer.add('T2:T5000')

        ws_guide = wb.create_sheet('使用説明')
        ws_guide.append(['項目', '内容'])
        ws_guide.append(['用途', '既存製品は更新、未登録品番は新規登録します'])
        ws_guide.append(['必須列', '構成品番（照合キー）'])
        ws_guide.append(['空欄の扱い', '空欄の列は元の値を維持します（上書きしません）'])
        ws_guide.append(['品番区分名', '集合部品 / 単体部品 / 材料 / 購入品 / 外作品'])
        ws_guide.append(['管理区分', '日 / 分'])
        ws_guide.append(['最終品・ライン最終品', 'はい / いいえ'])
        ws_guide.append(['移動先', '社内ライン / 社内塗装 / CWL / 興和 / 直納 / その他'])
        ws_guide.append(['置き場1〜4', '置き場名を最大4つまで入力可。置き場1が主置き場になります。空欄時は既存の置き場を維持。'])
        ws_guide.append(['注意', '同じ構成品番が複数行ある場合は先頭行のみ取込対象です。'])

        ws_process = wb.create_sheet('工程')
        ws_process.append(['工程コード', '工程名'])
        for p in Process.objects.order_by('process_code'):
            ws_process.append([p.process_code, p.process_name])

        ws_line = wb.create_sheet('ライン')
        ws_line.append(['ラインコード', 'ライン名'])
        for l in Line.objects.order_by('line_code'):
            ws_line.append([l.line_code, l.line_name])

        ws_group = wb.create_sheet('製品グループ')
        ws_group.append(['グループコード', 'グループ名'])
        for g in ProductGroup.objects.order_by('group_code'):
            ws_group.append([g.group_code, g.group_name])

        from io import BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        from django.http import HttpResponse
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="product_update_template.xlsx"'
        return response

    @action(detail=False, methods=['get'], url_path='import_template_xlsx')
    def import_template_xlsx(self, request):
        """製品インポート用Excelテンプレート（入力用＋使用説明＋工程＋ライン＋仕入先）"""
        wb = Workbook()
        ws = wb.active
        ws.title = '入力用'

        headers = [
            '品名規格', '構成品番', '品番区分名',
            'ライン情報', 'ライン名',
            '工程情報', '工程名',
            '後工程', '後工程名',
            '管理区分', '最終品', 'ライン最終品'
        ]
        ws.append(headers)
        ws.append(['', '', '', '', '', '', '', '', '', '', '', ''])

        # 参照関数（2行目）
        ws['E2'] = '=IFERROR(VLOOKUP(D2,ライン!A:B,2,FALSE),"")'
        ws['G2'] = '=IFERROR(VLOOKUP(F2,工程!A:B,2,FALSE),"")'
        ws['I2'] = '=IFERROR(VLOOKUP(H2,工程!A:B,2,FALSE),"")'

        # 入力規則
        dv_category = DataValidation(type='list', formula1='"集合部品,単体部品,材料,購入品,外作品"', allow_blank=True)
        dv_unit = DataValidation(type='list', formula1='"分,日"', allow_blank=True)
        dv_bool = DataValidation(type='list', formula1='"はい,いいえ"', allow_blank=True)
        ws.add_data_validation(dv_category)
        ws.add_data_validation(dv_unit)
        ws.add_data_validation(dv_bool)
        dv_category.add('C2:C2000')
        dv_unit.add('J2:J2000')
        dv_bool.add('K2:K2000')
        dv_bool.add('L2:L2000')

        # 説明シート
        ws_guide = wb.create_sheet('使用説明')
        ws_guide.append(['項目', '内容'])
        ws_guide.append(['必須列', '構成品番'])
        ws_guide.append(['推奨列', '品名規格, 品番区分名, ライン情報, 工程情報, 後工程, 管理区分, 最終品, ライン最終品'])
        ws_guide.append(['品番区分名', '集合部品 / 単体部品 / 材料 / 購入品 / 外作品'])
        ws_guide.append(['管理区分', '分 / 日'])
        ws_guide.append(['最終品・ライン最終品', 'はい / いいえ'])
        ws_guide.append(['注意1', 'ライン情報・工程情報・後工程は、それぞれマスタに存在するコードを入力してください。'])
        ws_guide.append(['注意2', '同じ構成品番が複数行ある場合は、先頭行のみ取込対象です。'])
        ws_guide.append(['注意3', '既存の構成品番はスキップされます。'])

        # 工程シート
        ws_process = wb.create_sheet('工程')
        ws_process.append(['工程コード', '工程名'])
        for p in Process.objects.order_by('process_code'):
            ws_process.append([p.process_code, p.process_name])

        # ラインシート
        ws_line = wb.create_sheet('ライン')
        ws_line.append(['ラインコード', 'ライン名'])
        for l in Line.objects.order_by('line_code'):
            ws_line.append([l.line_code, l.line_name])

        # 仕入先シート
        ws_supplier = wb.create_sheet('仕入先')
        ws_supplier.append(['仕入先コード', '仕入先名'])
        for s in Supplier.objects.order_by('supplier_code'):
            ws_supplier.append([s.supplier_code, s.supplier_name])

        from io import BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        from django.http import HttpResponse
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="product_import_template.xlsx"'
        return response

    @action(detail=False, methods=['post'], parser_classes=[parsers.MultiPartParser, parsers.FormParser], url_path='import_file')
    def import_file(self, request):
        """製品CSV/Excel取込"""
        upload = request.FILES.get('file')
        if not upload:
            return Response({'detail': '取込ファイルがありません'}, status=status.HTTP_400_BAD_REQUEST)

        raw = upload.read()
        filename = (getattr(upload, 'name', '') or '').lower()
        input_rows = []
        fieldnames = []

        if filename.endswith('.xlsx') or filename.endswith('.xlsm'):
            from io import BytesIO
            try:
                wb = load_workbook(BytesIO(raw), data_only=True, read_only=True)
                ws = wb[wb.sheetnames[0]]
            except Exception:
                return Response({'detail': 'Excelファイルの読み取りに失敗しました'}, status=status.HTTP_400_BAD_REQUEST)
            excel_rows = list(ws.iter_rows(values_only=True))
            if not excel_rows:
                return Response({'detail': 'Excelファイルにデータがありません'}, status=status.HTTP_400_BAD_REQUEST)
            fieldnames = [str(v).strip() if v is not None else '' for v in excel_rows[0]]
            for row in excel_rows[1:]:
                if row is None or all((cell is None or str(cell).strip() == '') for cell in row):
                    continue
                row_dict = {}
                for i, key in enumerate(fieldnames):
                    if not key:
                        continue
                    value = row[i] if i < len(row) else ''
                    row_dict[key] = '' if value is None else str(value).strip()
                input_rows.append(row_dict)
        else:
            text = None
            for enc in ('utf-8-sig', 'cp932', 'shift_jis', 'utf-8'):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if text is None:
                return Response({'detail': 'CSV文字コードを判別できません（UTF-8/Shift_JISのみ対応）'}, status=status.HTTP_400_BAD_REQUEST)
            reader = csv.DictReader(StringIO(text))
            fieldnames = reader.fieldnames or []
            input_rows = list(reader)

        if not input_rows:
            return Response({'detail': '取込データがありません'}, status=status.HTTP_400_BAD_REQUEST)

        items = []
        seen = set()
        for row in input_rows:
            product_code = str(row.get('構成品番') or '').strip()
            if not product_code or product_code in seen:
                continue
            seen.add(product_code)
            items.append({
                'product_code': product_code,
                'product_name': str(row.get('品名規格') or '').strip(),
                'category': str(row.get('品番区分名') or '').strip(),
                'line_code': str(row.get('ライン情報') or '').strip(),
                'process_code': str(row.get('工程情報') or '').strip(),
                'next_process_code': str(row.get('後工程') or '').strip(),
                'management_unit': str(row.get('管理区分') or '').strip(),
                'is_final_product': str(row.get('最終品') or '').strip(),
                'is_line_final_product': str(row.get('ライン最終品') or '').strip(),
            })

        try:
            result = self._bulk_import_products(items)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    @action(detail=False, methods=['post'], url_path='bulk-import')
    def bulk_import(self, request):
        """互換API: 既存のJSON配列取込"""
        items = request.data.get('items', [])
        try:
            result = self._bulk_import_products(items)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    @action(detail=True, methods=['get'], url_path='where-used')
    def where_used(self, request, pk=None):
        """
        逆展開：この製品がどの親製品で使われているかを取得

        Query Parameters:
            recursive: true/false - 再帰的に上位階層まで辿るか（デフォルト: false）
            reference_date: YYYY-MM-DD または ISO日時（ルーティング有効判定の基準日時）
        """
        from masters.services.bom_service import BOMService

        product = self.get_object()
        recursive = request.query_params.get('recursive', 'false').lower() == 'true'
        reference_raw = request.query_params.get('reference_date')
        reference_date = None
        if reference_raw:
            reference_date = parse_datetime(reference_raw)
            if reference_date is None:
                reference_date = parse_date(reference_raw)
            if reference_date is None:
                return Response(
                    {'detail': 'reference_date は YYYY-MM-DD または ISO日時で指定してください。'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        service = BOMService()
        step_cache = {}
        results = service.get_where_used(
            product.id,
            recursive=recursive,
            step_cache=step_cache,
            reference_date=reference_date,
        )
        self_info = service.get_where_used_self_info(
            product.id,
            context_cache=step_cache,
            reference_date=reference_date,
        )

        return Response({
            'product_id': product.id,
            'product_code': product.product_code,
            'product_name': product.product_name,
            'recursive': recursive,
            'self_info': self_info,
            'parents': results,
            'count': len(results),
        })

    @action(detail=True, methods=['get'], url_path='containers')
    def list_containers(self, request, pk=None):
        product = self.get_object()
        pcs = ProductContainer.objects.select_related('container').filter(
            product=product,
        ).order_by('container__name')
        return Response([
            {
                'id': pc.id,
                'container_id': pc.container_id,
                'container_code': pc.container.container_code or '',
                'container_name': pc.container.name,
                'capacity': pc.capacity,
            }
            for pc in pcs
        ])

    @action(detail=True, methods=['post'], url_path='containers/add')
    def add_container(self, request, pk=None):
        product = self.get_object()
        container_id = request.data.get('container_id')
        capacity = request.data.get('capacity')
        if not container_id:
            return Response({'detail': '容器を指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            container = ContainerCapacity.objects.get(id=container_id)
        except ContainerCapacity.DoesNotExist:
            return Response({'detail': '容器が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        try:
            capacity = int(capacity)
        except (TypeError, ValueError):
            return Response({'detail': '入数を整数で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        pc, created = ProductContainer.objects.update_or_create(
            product=product, container=container,
            defaults={'capacity': capacity},
        )
        return Response({
            'id': pc.id,
            'container_id': container.id,
            'container_code': container.container_code or '',
            'container_name': container.name,
            'capacity': pc.capacity,
            'created': created,
        })

    @action(detail=True, methods=['patch'], url_path=r'containers/(?P<pc_id>\d+)')
    def update_container(self, request, pk=None, pc_id=None):
        product = self.get_object()
        try:
            pc = product.product_containers.select_related('container').get(id=pc_id)
        except ProductContainer.DoesNotExist:
            return Response({'detail': '紐付けが見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        capacity = request.data.get('capacity')
        try:
            pc.capacity = int(capacity)
        except (TypeError, ValueError):
            return Response({'detail': '入数を整数で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        pc.save(update_fields=['capacity'])
        return Response({
            'id': pc.id,
            'container_id': pc.container_id,
            'container_code': pc.container.container_code or '',
            'container_name': pc.container.name,
            'capacity': pc.capacity,
        })

    @action(detail=True, methods=['delete'], url_path=r'containers/(?P<pc_id>\d+)/delete')
    def remove_container(self, request, pk=None, pc_id=None):
        product = self.get_object()
        try:
            pc = product.product_containers.get(id=pc_id)
        except ProductContainer.DoesNotExist:
            return Response({'detail': '紐付けが見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        pc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductGroupViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = ProductGroup.objects.all()
    serializer_class = ProductGroupSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['group_code', 'group_name']
    ordering_fields = ['group_code', 'created_at']
    ordering = ['group_code']


class ProductCodeMappingViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = ProductCodeMapping.objects.all()
    serializer_class = ProductCodeMappingSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['source_product_code', 'target_product_code', 'note']
    ordering_fields = ['source_product_code', 'updated_at', 'created_at']
    ordering = ['source_product_code']


def _container_excel_cell(row, idx):
    return row[idx] if row is not None and idx < len(row) else None


def _extract_container_excel_data(file_bytes):
    """荷姿設定Excelのバイト列から、シート全行の値と埋め込み画像の位置(行・列→media相対パス)を取り出す。
    画像が無い/drawing構成が読めないファイルの場合はimage_map・zfとも空/Noneのまま返す。
    """
    wb = load_workbook(BytesIO(file_bytes), data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    image_map = {}
    zf = None
    try:
        zf = zipfile.ZipFile(BytesIO(file_bytes))
        ns = {
            'xdr': 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing',
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        }
        rembed = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed'
        rels_root = ET.fromstring(zf.read('xl/drawings/_rels/drawing1.xml.rels'))
        rid_to_target = {rel.get('Id'): rel.get('Target') for rel in rels_root}
        drawing_root = ET.fromstring(zf.read('xl/drawings/drawing1.xml'))
        anchors = drawing_root.findall('xdr:twoCellAnchor', ns) + drawing_root.findall('xdr:oneCellAnchor', ns)
        for anchor in anchors:
            frm = anchor.find('xdr:from', ns)
            pic = anchor.find('xdr:pic', ns)
            if frm is None or pic is None:
                continue
            blip_fill = pic.find('xdr:blipFill', ns)
            blip = blip_fill.find('a:blip', ns) if blip_fill is not None else None
            if blip is None:
                continue
            rid = blip.get(rembed)
            target = rid_to_target.get(rid)
            if not target:
                continue
            row = int(frm.find('xdr:row', ns).text)
            col = int(frm.find('xdr:col', ns).text)
            image_map.setdefault(row, []).append((col, target))
    except KeyError:
        image_map = {}

    return rows, image_map, zf


def _build_container_import_cards(rows, image_map):
    """行データから荷姿設定カード（品番・荷姿名称・入数が確定しているもの）を抽出する。
    容器名・容器コードの決定や既存容器への紐付けは呼び出し側（人間の確認）に委ねるため、ここでは提案値のみ返す。
    """
    cell = _container_excel_cell
    block_rows = sorted(
        i for i in range(len(rows))
        if cell(rows[i], 0) == '品番' or cell(rows[i], 7) == '品番'
    )

    cards = []
    not_found = []
    skipped_undetermined = []

    for i in range(len(rows) - 1):
        row_a = rows[i]
        row_b = rows[i + 1]
        for offset in (0, 7):
            if cell(row_a, offset) != '品番' or cell(row_b, offset) != '品名':
                continue

            product_code = cell(row_a, offset + 1)
            container_name_raw = cell(row_a, offset + 4)
            product_name = cell(row_b, offset + 1)
            qty = cell(row_b, offset + 4)

            if not product_code:
                continue
            product_code = str(product_code).strip()

            if not container_name_raw or container_name_raw == '未定' or qty == '未定' or qty is None:
                skipped_undetermined.append({'product_code': product_code, 'product_name': product_name})
                continue

            container_name_raw = str(container_name_raw).strip()
            if container_name_raw.startswith('専用'):
                suggested_name = f"{container_name_raw}({product_code})"
            else:
                suggested_name = container_name_raw

            if not Product.objects.filter(product_code=product_code).exists():
                not_found.append({'product_code': product_code, 'product_name': product_name})
                continue

            qty_int = int(qty) if isinstance(qty, (int, float)) else None

            later_blocks = [b for b in block_rows if b > i]
            window_end = later_blocks[0] - 1 if later_blocks else len(rows) - 1
            image_targets = sorted({
                target
                for r in range(i, window_end + 1)
                for col, target in image_map.get(r, [])
                if offset <= col <= offset + 6
            })

            cards.append({
                'card_key': f"{i}_{offset}",
                'product_code': product_code,
                'product_name': product_name,
                'container_name_raw': container_name_raw,
                'suggested_container_name': suggested_name,
                'qty': qty_int,
                'image_targets': image_targets,
            })

    return cards, not_found, skipped_undetermined


CONTAINER_IMPORT_TMP_DIR = 'tmp/container_import'


class ContainerCapacityViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = ContainerCapacity.objects.all()
    serializer_class = ContainerCapacitySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'container_code']
    ordering_fields = ['name', 'capacity']
    ordering = ['name']

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related('product_containers__product')
        product = self.request.query_params.get('product')
        if product:
            qs = qs.filter(
                Q(product_containers__product__product_code__icontains=product)
                | Q(product_containers__product__product_name__icontains=product)
            ).distinct()
        return qs

    @action(detail=True, methods=['post'], url_path='products')
    def add_product(self, request, pk=None):
        container = self.get_object()
        product_code = (request.data.get('product_code') or '').strip()
        capacity = request.data.get('capacity')
        if not product_code:
            return Response({'detail': '品番を指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            product = Product.objects.get(product_code=product_code)
        except Product.DoesNotExist:
            return Response({'detail': f'品番 {product_code} が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        try:
            capacity = int(capacity)
        except (TypeError, ValueError):
            return Response({'detail': '入数を整数で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        pc, created = ProductContainer.objects.update_or_create(
            product=product, container=container,
            defaults={'capacity': capacity},
        )
        return Response({
            'id': pc.id, 'product_id': product.id,
            'product_code': product.product_code, 'product_name': product.product_name,
            'capacity': pc.capacity, 'created': created,
        })

    @action(detail=True, methods=['patch'], url_path=r'products/(?P<pc_id>\d+)')
    def update_product(self, request, pk=None, pc_id=None):
        container = self.get_object()
        try:
            pc = container.product_containers.get(id=pc_id)
        except ProductContainer.DoesNotExist:
            return Response({'detail': '紐付けが見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        capacity = request.data.get('capacity')
        try:
            pc.capacity = int(capacity)
        except (TypeError, ValueError):
            return Response({'detail': '入数を整数で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        pc.save(update_fields=['capacity'])
        return Response({
            'id': pc.id, 'product_id': pc.product_id,
            'product_code': pc.product.product_code, 'product_name': pc.product.product_name,
            'capacity': pc.capacity,
        })

    @action(detail=True, methods=['delete'], url_path=r'products/(?P<pc_id>\d+)/delete')
    def remove_product(self, request, pk=None, pc_id=None):
        container = self.get_object()
        try:
            pc = container.product_containers.get(id=pc_id)
        except ProductContainer.DoesNotExist:
            return Response({'detail': '紐付けが見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        pc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], url_path='import_excel_preview', parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def import_excel_preview(self, request):
        """客先別「荷姿設定」帳票をアップロードし、内容を解析してプレビューを返す（DBへは未反映）。
        容器コードの入力・既存容器への紐付け・写真の採用選択は import_excel_commit で人間の判断により確定する。
        """
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'ファイルが必要です'}, status=status.HTTP_400_BAD_REQUEST)

        file_bytes = file.read()
        rows, image_map, zf = _extract_container_excel_data(file_bytes)
        cards, not_found, skipped_undetermined = _build_container_import_cards(rows, image_map)

        import_token = uuid.uuid4().hex
        default_storage.save(f"{CONTAINER_IMPORT_TMP_DIR}/{import_token}.xlsx", ContentFile(file_bytes))

        for card in cards:
            previews = []
            if zf is not None:
                for target in card['image_targets']:
                    media_path = 'xl/' + target.replace('../', '')
                    try:
                        image_bytes = zf.read(media_path)
                    except KeyError:
                        continue
                    ext = os.path.splitext(media_path)[1].lstrip('.').lower() or 'png'
                    mime = 'jpeg' if ext == 'jpg' else ext
                    b64 = base64.b64encode(image_bytes).decode('ascii')
                    previews.append(f"data:image/{mime};base64,{b64}")
            card['images'] = previews
            del card['image_targets']

        return Response({
            'import_token': import_token,
            'cards': cards,
            'not_found': not_found,
            'skipped_undetermined': skipped_undetermined,
        })

    @action(detail=False, methods=['post'], url_path='import_excel_commit')
    def import_excel_commit(self, request):
        """import_excel_preview で確認したカードのうち、人間が決定した内容（容器コード・新規/既存紐付け・
        採用する写真）をもとに Product.used_container / capacity とContainerCapacityへ反映する。
        """
        import_token = request.data.get('import_token')
        decisions = request.data.get('decisions') or []
        if not import_token:
            return Response({'detail': 'import_tokenが必要です'}, status=status.HTTP_400_BAD_REQUEST)

        tmp_path = f"{CONTAINER_IMPORT_TMP_DIR}/{import_token}.xlsx"
        if not default_storage.exists(tmp_path):
            return Response(
                {'detail': '取込対象が見つかりません。プレビューの有効期限が切れた可能性があるため、再度アップロードしてください。'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with default_storage.open(tmp_path, 'rb') as f:
            file_bytes = f.read()

        rows, image_map, zf = _extract_container_excel_data(file_bytes)
        cards, _not_found, _skipped = _build_container_import_cards(rows, image_map)
        cards_by_key = {c['card_key']: c for c in cards}

        updated_products = []
        created_containers = []
        updated_containers = []
        image_applied_count = 0

        for decision in decisions:
            card = cards_by_key.get(decision.get('card_key'))
            if not card:
                continue

            container_code = (decision.get('container_code') or '').strip() or None
            mode = decision.get('mode') or 'create'
            existing_container_id = decision.get('existing_container_id')
            container_name = (decision.get('container_name') or card['suggested_container_name']).strip()
            keep_indices = decision.get('keep_image_indices') or []

            try:
                product = Product.objects.get(product_code=card['product_code'])
            except Product.DoesNotExist:
                continue

            if mode == 'update' and existing_container_id:
                try:
                    container = ContainerCapacity.objects.get(id=existing_container_id)
                except ContainerCapacity.DoesNotExist:
                    continue
                if container_code:
                    container.container_code = container_code
                container.capacity = card['qty']
                container.save(update_fields=['container_code', 'capacity'])
                updated_containers.append(container.name)
            else:
                created = False
                if container_code:
                    container, created = ContainerCapacity.objects.get_or_create(
                        container_code=container_code,
                        defaults={
                            'name': container_name,
                            'capacity': card['qty'],
                        },
                    )
                    changed = False
                    if container.name != container_name:
                        container.name = container_name
                        changed = True
                    if container.capacity != card['qty']:
                        container.capacity = card['qty']
                        changed = True
                    if changed:
                        container.save(update_fields=['name', 'capacity'])
                else:
                    container = ContainerCapacity.objects.create(
                        name=container_name,
                        container_code=None,
                        capacity=card['qty'],
                    )
                    created = True
                if created:
                    created_containers.append(container.name)

            product.used_container = container
            product.capacity = card['qty']
            product.save(update_fields=['used_container', 'capacity'])

            ProductContainer.objects.update_or_create(
                product=product,
                container=container,
                defaults={'capacity': card['qty']},
            )
            updated_products.append(card['product_code'])

            if zf is not None and keep_indices:
                existing_count = container.images.count()
                for order, idx in enumerate(keep_indices):
                    if not isinstance(idx, int) or idx < 0 or idx >= len(card['image_targets']):
                        continue
                    media_path = 'xl/' + card['image_targets'][idx].replace('../', '')
                    try:
                        image_bytes = zf.read(media_path)
                    except KeyError:
                        continue
                    ext = os.path.splitext(media_path)[1] or '.png'
                    filename = f"containers/{card['product_code']}_{uuid.uuid4().hex}{ext}"
                    saved_path = default_storage.save(filename, ContentFile(image_bytes))
                    url = default_storage.url(saved_path)
                    ContainerCapacityImage.objects.create(
                        container=container, image_url=url, sort_order=existing_count + order,
                    )
                    if not container.image_url:
                        container.image_url = url
                        container.save(update_fields=['image_url'])
                    image_applied_count += 1

        default_storage.delete(tmp_path)

        return Response({
            'updated_count': len(updated_products),
            'updated_products': updated_products,
            'created_containers': created_containers,
            'updated_containers': updated_containers,
            'image_applied_count': image_applied_count,
        })

    @action(detail=True, methods=['post'], url_path='upload_images', parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def upload_images(self, request, pk=None):
        container = self.get_object()
        files = request.FILES.getlist('files')
        if not files:
            return Response({'detail': 'ファイルがありません'}, status=status.HTTP_400_BAD_REQUEST)

        existing_count = container.images.count()
        for order, file_obj in enumerate(files):
            ext = os.path.splitext(file_obj.name)[1] or ''
            filename = f"containers/{container.id}_{uuid.uuid4().hex}{ext}"
            saved_path = default_storage.save(filename, file_obj)
            url = default_storage.url(saved_path)
            ContainerCapacityImage.objects.create(
                container=container, image_url=url, sort_order=existing_count + order,
            )
            if not container.image_url:
                container.image_url = url

        container.save(update_fields=['image_url'])
        serializer = self.get_serializer(container)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path=r'images/(?P<image_id>\d+)')
    def delete_image(self, request, pk=None, image_id=None):
        container = self.get_object()
        try:
            image = container.images.get(id=image_id)
        except ContainerCapacityImage.DoesNotExist:
            return Response({'detail': '画像が見つかりません'}, status=status.HTTP_404_NOT_FOUND)

        was_thumbnail = container.image_url == image.image_url
        image.delete()
        if was_thumbnail:
            next_image = container.images.order_by('sort_order', 'id').first()
            container.image_url = next_image.image_url if next_image else None
            container.save(update_fields=['image_url'])

        serializer = self.get_serializer(container)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EquipmentViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = Equipment.objects.all().select_related('line', 'process')
    serializer_class = EquipmentSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'line', 'process']
    search_fields = ['equipment_code', 'equipment_name', 'line__line_code', 'line__line_name', 'process__process_code', 'process__process_name']
    ordering_fields = ['display_order', 'equipment_code', 'created_at']
    ordering = ['display_order', 'equipment_code']


class KubotaSakaiTruckViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = KubotaSakaiTruck.objects.all()
    serializer_class = KubotaSakaiTruckSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'default_use']
    search_fields = ['name', 'alias_name']
    ordering_fields = ['display_order', 'name', 'departure_time']
    ordering = ['display_order', 'name']


class CustomerViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['customer_code', 'customer_name']
    ordering_fields = ['customer_code', 'created_at']
    ordering = ['customer_code']

    def get_queryset(self):
        return super().get_queryset().order_by('customer_code', 'id')


class ProcessViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = Process.objects.all()
    serializer_class = ProcessSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'is_outsource', 'line']
    search_fields = ['process_code', 'process_name']
    ordering_fields = ['process_code', 'created_at']
    ordering = ['process_code']

    @action(detail=True, methods=['get'], url_path='related-products')
    def related_products(self, request, pk=None):
        """
        工程に関連する製品を取得:
        - 連産品（仮想セット品番）: BOM.is_coproduct=true の親製品
        - 連産品の子品番: 連産品のBOM配下にある実際の製品
        - 使用する社内生産品: RoutingStepMaterial から取得した中間品
        - 使用する購入品: RoutingStepMaterial から取得した購入部品
        - BOM明細で工程が一致する子品番（中間品/連産品の子品番を補完）
        """
        process = self.get_object()
        products_map = {}  # key: product_id, value: {product, relation_type, process_id, sourcing_type}

        # 1. この工程を含むルーティングステップを取得
        routing_steps = RoutingStep.objects.filter(process=process).select_related('routing')

        # BOM由来の工程ID・調達区分マップを構築（ルーティング親製品のBOM明細から）
        bom_detail_map = {}  # child_product_id → {process_id, sourcing_type}
        routing_parent_ids = set()
        for step in routing_steps:
            if step.routing and step.routing.product_id:
                routing_parent_ids.add(step.routing.product_id)
        if routing_parent_ids:
            for bi in BOMItem.objects.filter(
                bom__parent_product_id__in=routing_parent_ids,
                bom__is_active=True,
            ).values('child_product_id', 'process_id', 'sourcing_type'):
                pid = bi['child_product_id']
                if pid not in bom_detail_map:
                    bom_detail_map[pid] = bi

        # 連産品BOMの子品番IDセットを事前構築（出力品/連産子の判定用）
        coproduct_child_ids = set(
            BOMItem.objects.filter(
                bom__is_coproduct=True, bom__is_active=True,
            ).values_list('child_product_id', flat=True)
        )

        for step in routing_steps:
            routing = step.routing
            if not routing or not routing.product:
                continue

            # 1-0. この工程の出力品目を追加（親に連産品があれば連産子、なければ出力品）
            output_product = step.output_product
            if output_product and output_product.id not in products_map:
                rel = 'coproduct_child' if output_product.id in coproduct_child_ids else 'output_product'
                products_map[output_product.id] = {
                    'product': output_product,
                    'relation_type': rel,
                    'process_id': process.id,
                    'sourcing_type': 'MAKE',
                }

            # 2. ルーティングの親製品を取得
            parent_product = routing.product

            # 2-1. 親製品が連産品かチェック
            try:
                bom = BOM.objects.get(parent_product=parent_product, is_coproduct=True)
                # 連産品の場合、親製品を追加
                if parent_product.id not in products_map:
                    products_map[parent_product.id] = {
                        'product': parent_product,
                        'relation_type': 'coproduct_parent',
                        'process_id': process.id,
                        'sourcing_type': 'MAKE',
                    }

                # 連産品の子品番を追加
                for child in bom.bom_items.all():
                    if child.child_product and child.child_product.id not in products_map:
                        products_map[child.child_product.id] = {
                            'product': child.child_product,
                            'relation_type': 'coproduct_child',
                            'process_id': process.id,
                            'sourcing_type': 'MAKE',
                        }
            except BOM.DoesNotExist:
                pass

            # 3. このルーティングステップで使用する材料を取得
            materials = RoutingStepMaterial.objects.filter(
                routing_step=step
            ).select_related('component')

            for material in materials:
                component = material.component
                if not component or component.id in products_map:
                    continue

                # カテゴリで社内生産品か購入品かを判定
                if component.category in ('ASSEMBLY', 'SINGLE'):
                    relation_type = 'intermediate'
                elif component.category in ('PURCHASED', 'MATERIAL'):
                    relation_type = 'purchased'
                else:
                    relation_type = 'other'

                bom_info = bom_detail_map.get(component.id, {})
                products_map[component.id] = {
                    'product': component,
                    'relation_type': relation_type,
                    'process_id': bom_info.get('process_id'),
                    'sourcing_type': bom_info.get('sourcing_type', ''),
                }

        # 4. BOM明細で工程が一致する子品番を追加（中間品/連産品の子品番補完）
        bom_items = BOMItem.objects.filter(process=process).select_related(
            'child_product',
            'bom__parent_product'
        )
        for item in bom_items:
            child = item.child_product
            if not child:
                continue
            if child.id not in products_map:
                relation_type = 'coproduct_child' if item.bom and item.bom.is_coproduct else 'bom_process_item'
                products_map[child.id] = {
                    'product': child,
                    'relation_type': relation_type,
                    'process_id': item.process_id,
                    'sourcing_type': item.sourcing_type or '',
                }

            # 連産品BOMの場合は親（仮想セット）も追加
            if item.bom and item.bom.is_coproduct and item.bom.parent_product:
                parent = item.bom.parent_product
                if parent.id not in products_map:
                    products_map[parent.id] = {
                        'product': parent,
                        'relation_type': 'coproduct_parent',
                        'process_id': process.id,
                        'sourcing_type': 'MAKE',
                    }

        # 結果をシリアライズ
        result = []
        for item in products_map.values():
            product = item['product']
            result.append({
                'id': product.id,
                'product_code': product.product_code,
                'product_name': product.product_name,
                'category': product.category,
                'relation_type': item['relation_type'],
                'process_id': item.get('process_id'),
                'sourcing_type': item.get('sourcing_type', ''),
            })

        return Response(result)


class LineViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = Line.objects.all()
    serializer_class = LineSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'line_type']
    search_fields = ['line_code', 'line_name']
    ordering_fields = ['line_code', 'created_at']
    ordering = ['line_code']

    def destroy(self, request, *args, **kwargs):
        line = self.get_object()
        if line.line_type == 'PURCHASE' and Supplier.objects.filter(supplier_code=line.line_code).exists():
            return Response(
                {'detail': '仕入先と紐づく購買ラインは手動削除できません。先に仕入先側を整理してください。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class ProductionLineViewSet(viewsets.ReadOnlyModelViewSet):
    """生産ライン一覧（読み取り専用）。生産計画など他機能からも参照されるため認証のみで許可"""
    queryset = Line.objects.filter(line_type='PROD')
    serializer_class = LineSerializer
    pagination_class = None
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active']
    search_fields = ['line_code', 'line_name']
    ordering_fields = ['line_code', 'created_at']
    ordering = ['line_code']


class SupplierViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    pagination_class = None
    search_fields = ['supplier_code', 'supplier_name', 'order_email']
    ordering_fields = ['supplier_code']
    ordering = ['supplier_code']

    def perform_create(self, serializer):
        supplier = serializer.save()
        ensure_supplier_purchase_line(supplier)

    def perform_update(self, serializer):
        previous_supplier_code = str(serializer.instance.supplier_code or '').strip()
        supplier = serializer.save()
        ensure_supplier_purchase_line(supplier, previous_supplier_code=previous_supplier_code)


class CalendarViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = Calendar.objects.all()
    serializer_class = CalendarSerializer
    pagination_class = None
    search_fields = ['calendar_code', 'calendar_name']
    ordering_fields = ['calendar_code', 'created_at']
    ordering = ['calendar_code']

    def perform_create(self, serializer):
        user = self.request.user if getattr(self.request, 'user', None) and self.request.user.is_authenticated else None
        serializer.save(created_by=user, updated_by=user)

    def perform_update(self, serializer):
        user = self.request.user if getattr(self.request, 'user', None) and self.request.user.is_authenticated else None
        serializer.save(updated_by=user)

    @action(detail=True, methods=['post'], url_path='copy_to')
    def copy_to(self, request, pk=None):
        """指定期間のカレンダー日データを別カレンダーにコピーする"""
        from datetime import date
        src_calendar = self.get_object()
        target_id = request.data.get('target_calendar_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        if not target_id or not start_date or not end_date:
            return Response({'error': 'target_calendar_id, start_date, end_date は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_calendar = Calendar.objects.get(pk=target_id)
        except Calendar.DoesNotExist:
            return Response({'error': 'コピー先カレンダーが見つかりません'}, status=status.HTTP_404_NOT_FOUND)

        # コピー元の期間内データ取得
        src_days = CalendarDay.objects.filter(
            calendar=src_calendar,
            target_date__gte=start_date,
            target_date__lte=end_date,
        )

        # コピー先の既存データを削除してから再作成（upsert）
        target_dates = [d.target_date for d in src_days]
        CalendarDay.objects.filter(calendar=target_calendar, target_date__in=target_dates).delete()

        new_days = [
            CalendarDay(
                calendar=target_calendar,
                target_date=d.target_date,
                is_working_day=d.is_working_day,
                work_minutes=d.work_minutes,
                work_pattern=d.work_pattern,
                note=d.note,
            )
            for d in src_days
        ]
        CalendarDay.objects.bulk_create(new_days)

        return Response({'copied': len(new_days)})


class WorkPatternViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = WorkPattern.objects.all()
    serializer_class = WorkPatternSerializer
    search_fields = ['pattern_code', 'pattern_name']
    ordering_fields = ['pattern_code', 'created_at']
    ordering = ['pattern_code']


class BreakTimeViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = BreakTime.objects.all()
    serializer_class = BreakTimeSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['work_pattern']
    ordering_fields = ['order']
    ordering = ['work_pattern', 'order']


class CalendarDayViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = CalendarDay.objects.all()
    serializer_class = CalendarDaySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        'calendar': ['exact'],
        'is_working_day': ['exact'],
        'target_date': ['exact', 'gte', 'lte'],
    }
    ordering_fields = ['target_date']
    ordering = ['target_date']
    pagination_class = None  # all days are returned to support range updates

    def create(self, request, *args, **kwargs):
        """
        Upsert by (calendar, target_date) so bulk range registration does not
        fail with unique constraint errors when records already exist.
        """
        calendar_id = request.data.get('calendar')
        target_date = request.data.get('target_date')
        existing = None
        if calendar_id and target_date:
            existing = CalendarDay.objects.filter(
                calendar_id=calendar_id,
                target_date=target_date
            ).first()

        serializer = self.get_serializer(instance=existing, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        headers = {} if existing else self.get_success_headers(serializer.data)
        status_code = status.HTTP_200_OK if existing else status.HTTP_201_CREATED
        return Response(serializer.data, status=status_code, headers=headers)


class BOMViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = BOM.objects.select_related('parent_product').all()
    serializer_class = BOMSerializer
    filterset_fields = ['parent_product', 'is_active']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return BOMListSerializer
        return BOMSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(parent_product__product_code__icontains=search) |
                Q(parent_product__product_name__icontains=search)
            )

        is_final = self.request.query_params.get('parent_is_final', None)
        if is_final is not None and is_final != '':
            is_final_bool = is_final.lower() == 'true'
            queryset = queryset.filter(parent_product__is_final_product=is_final_bool)

        is_line_final = self.request.query_params.get('parent_is_line_final', None)
        if is_line_final is not None and is_line_final != '':
            is_line_final_bool = is_line_final.lower() == 'true'
            queryset = queryset.filter(parent_product__is_line_final_product=is_line_final_bool)

        is_coproduct = self.request.query_params.get('is_coproduct', None)
        if is_coproduct is not None and is_coproduct != '':
            is_coproduct_bool = is_coproduct.lower() == 'true'
            if is_coproduct_bool:
                queryset = queryset.filter(Q(is_coproduct=True) | Q(parent_product__is_virtual_set=True))
            else:
                queryset = queryset.filter(is_coproduct=False, parent_product__is_virtual_set=False)

        version = self.request.query_params.get('version', None)
        if version:
            queryset = queryset.filter(version__icontains=version)

        created_from = self.request.query_params.get('created_from', None)
        if created_from:
            created_from_dt = datetime.strptime(created_from, '%Y-%m-%d')
            queryset = queryset.filter(created_at__gte=created_from_dt)

        created_to = self.request.query_params.get('created_to', None)
        if created_to:
            created_to_dt = datetime.strptime(created_to, '%Y-%m-%d')
            created_to_dt = created_to_dt + timedelta(days=1)
            queryset = queryset.filter(created_at__lt=created_to_dt)

        return queryset

    def _serialize_product(self, product: Product):
        return {
            'id': product.id,
            'code': product.product_code,
            'name': product.product_name,
            'is_phantom': product.is_phantom,
        }

    def _pick_child_bom(self, product: Product):
        """Active BOM for child product (latest by valid_from)."""
        today = date.today()
        qs = BOM.objects.filter(
            parent_product=product,
            is_active=True,
            valid_from__lte=today,
        ).order_by('-valid_from', '-id')
        child = qs.first()
        if child:
            return child
        # fallback: any active BOM
        return BOM.objects.filter(
            parent_product=product,
            is_active=True,
        ).order_by('-valid_from', '-id').first()

    def _build_item_node(self, item: BOMItem, visited_bom_ids: set):
        child_bom = self._pick_child_bom(item.child_product)
        # prevent infinite loops
        if child_bom and child_bom.id in visited_bom_ids:
            child_tree = None
        elif child_bom:
            child_tree = self._build_bom_tree(child_bom, visited_bom_ids)
        else:
            child_tree = None

        return {
            'id': item.id,
            'bom': item.bom_id,
            'child_product': self._serialize_product(item.child_product),
            'quantity': str(item.quantity),
            'loss_rate': str(item.loss_rate) if item.loss_rate is not None else None,
            'sourcing_type': item.sourcing_type,
            'supplier': {
                'id': item.supplier_id,
                'name': item.supplier.supplier_name if item.supplier else None,
            } if item.supplier_id else None,
            'process': item.process_id,
            'process_name': item.process.process_name if item.process else None,
            'line': item.line_id,
            'line_name': item.line.line_name if item.line else None,
            'time_unit': item.time_unit,
            'lead_time_days': item.lead_time_days,
            'duration_min': item.duration_min,
            'remark': item.remark,
            'child_bom': child_tree,
        }

    def _build_bom_tree(self, bom: BOM, visited_bom_ids: set):
        visited_bom_ids.add(bom.id)
        items_qs = BOMItem.objects.filter(bom=bom).select_related('child_product', 'supplier')
        items = [self._build_item_node(item, visited_bom_ids) for item in items_qs]
        return {
            'id': bom.id,
            'parent_product': self._serialize_product(bom.parent_product),
            'version': bom.version,
            'valid_from': bom.valid_from,
            'valid_to': bom.valid_to,
            'is_active': bom.is_active,
            'items': items,
        }

    def _build_tree_excel_rows(self, bom: BOM):
        """
        Excel出力と同一ロジックでBOM階層の行データを作成する。
        """
        rows = []
        today = date.today()

        def pick_child_bom(product):
            qs = BOM.objects.filter(
                parent_product=product,
                is_active=True,
                valid_from__lte=today,
            ).order_by('-valid_from', '-id')
            child = qs.first()
            if child:
                return child
            return BOM.objects.filter(
                parent_product=product,
                is_active=True,
            ).order_by('-valid_from', '-id').first()

        def walk_bom(b, parent_prefix='', level=0, visited=None, cumulative_lt=0):
            if visited is None:
                visited = set()
            if b.id in visited:
                return
            visited.add(b.id)

            if level == 0:
                root_label = '最上位組立（最終工程）'
                display_name = f"{root_label} [{b.parent_product.product_code}]" if b.parent_product else root_label
                process_display = ''
                line_display = ''
                root_lead_time_days = ''
                root_duration_min = ''
                if b.parent_product_id:
                    default_routing = resolve_effective_routing(b.parent_product_id)
                    if default_routing:
                        last_step = default_routing.steps.order_by('step_no').last()
                        if last_step:
                            if last_step.process:
                                process_display = f"{last_step.process.process_code} - {last_step.process.process_name}"
                            if last_step.line:
                                line_display = f"{last_step.line.line_code} - {last_step.line.line_name}"
                            if last_step.lead_time_days is not None:
                                root_lead_time_days = last_step.lead_time_days
                                cumulative_lt = last_step.lead_time_days
                            if last_step.duration_min is not None:
                                root_duration_min = last_step.duration_min

                rows.append({
                    'bom_id': b.id,
                    'parent_product': b.parent_product.product_code if b.parent_product else '',
                    'part_display': display_name,
                    'product_name': b.parent_product.product_name if b.parent_product else '',
                    'level': level,
                    'quantity': '',
                    'process': process_display,
                    'line': line_display,
                    'supplier': '',
                    'lead_time_days': root_lead_time_days,
                    'duration_min': root_duration_min,
                    'cumulative_lt': cumulative_lt,
                })

            items_qs = list(
                BOMItem.objects.filter(bom=b)
                .select_related('child_product', 'process', 'line', 'supplier')
                .order_by('id')
            )
            for idx, item in enumerate(items_qs):
                is_last = idx == len(items_qs) - 1
                connector = '└─ ' if is_last else '├─ '
                display_prefix = parent_prefix + connector
                display_name = display_prefix + (item.child_product.product_code if item.child_product else '')

                item_lt = item.lead_time_days or 0
                item_cumulative_lt = cumulative_lt + item_lt

                rows.append({
                    'bom_id': b.id,
                    'parent_product': b.parent_product.product_code if b.parent_product else '',
                    'part_display': display_name,
                    'product_name': item.child_product.product_name if item.child_product else '',
                    'level': level + 1,
                    'quantity': float(item.quantity) if item.quantity is not None else '',
                    'process': f"{item.process.process_code} - {item.process.process_name}" if item.process else '',
                    'line': f"{item.line.line_code} - {item.line.line_name}" if item.line else '',
                    'supplier': item.supplier.supplier_name if item.supplier else '',
                    'lead_time_days': item.lead_time_days if item.lead_time_days is not None else '',
                    'duration_min': item.duration_min if item.duration_min is not None else '',
                    'cumulative_lt': item_cumulative_lt,
                })

                child_bom = pick_child_bom(item.child_product) if item.child_product else None
                if child_bom and child_bom.id not in visited:
                    child_prefix = parent_prefix + ('   ' if is_last else '│  ')
                    # visited.copy() で枝ごとに独立させ、同一BOMが複数箇所に現れても全て展開する
                    # （visited はあくまで同一枝内の循環参照防止用）
                    walk_bom(child_bom, parent_prefix=child_prefix, level=level + 1, visited=visited.copy(), cumulative_lt=item_cumulative_lt)

        walk_bom(bom, parent_prefix='', level=0, visited=set())
        return rows

    @action(detail=True, methods=['get'])
    def tree(self, request, pk=None):
        bom = self.get_object()
        tree = self._build_bom_tree(bom, visited_bom_ids=set())
        return Response(tree)

    @action(detail=True, methods=['get'], url_path='tree_excel_rows')
    def tree_excel_rows(self, request, pk=None):
        bom = self.get_object()
        headers = [
            'BOM ID', '親製品', '部番表示', '製品名', '階層', '数量',
            '工程', 'ライン', '仕入先', 'リードタイム(日)', '所要時間(分)'
        ]
        rows = self._build_tree_excel_rows(bom)
        return Response({
            'headers': headers,
            'rows': rows,
        })

    @action(detail=False, methods=['get'], url_path='import_template_csv')
    def import_template_csv(self, request):
        headers = [
            '完成品', '親品番', '子品番', '数量',
            '工程コード', '工程名', 'ラインコード', 'ライン名', '調達区分', '仕入先コード', '仕入先名',
            'ＬＴ(日)', '所要時間(分)', '時間単位'
        ]
        sample_rows = [
            ['YD60000441', 'YD60000441', 'YD40000608S', '1', '4030', '', 'L2200', '', '自社製造', '', '', '0', '20', '分'],
            ['YD60000441', 'YD40000608S', 'YD40000608', '1', '4053', '', 'L2200', '', '自社製造', '', '', '0', '20', '分'],
            ['YD60000441', 'YD40000608', 'YD40000608H', '1', '4019', '', 'L2200', '', '自社製造', '', '', '0', '16', '分'],
        ]
        sio = StringIO()
        writer = csv.writer(sio, lineterminator='\n')
        writer.writerow(headers)
        writer.writerows(sample_rows)
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="bom_import_template.csv"'
        response.write('\ufeff')
        response.write(sio.getvalue())
        return response

    @action(detail=False, methods=['get'], url_path='import_template_xlsx')
    def import_template_xlsx(self, request):
        wb = Workbook()
        ws_input = wb.active
        ws_input.title = '入力用'

        headers = [
            '完成品', '親品番', '子品番', '数量',
            '工程コード', '工程名', 'ラインコード', 'ライン名', '調達区分', '仕入先コード', '仕入先名',
            'ＬＴ(日)', '所要時間(分)', '時間単位'
        ]
        ws_input.append(headers)
        ws_input.append(['YD60000441', 'YD60000441', 'YD40000608S', 1, '4030', '', 'L2200', '', '自社製造', '', '', 0, 20, '分'])
        ws_input.append(['YD60000441', 'YD40000608S', 'YD40000608', 1, '4053', '', 'L2200', '', '自社製造', '', '', 0, 20, '分'])
        ws_input.append(['YD60000441', 'YD40000608', 'YD40000608H', 1, '4019', '', 'L2200', '', '自社製造', '', '', 0, 16, '分'])

        # 工程コード(E列)を文字列書式に設定
        from openpyxl.styles import numbers
        for row_no in range(1, 5001):
            ws_input[f'E{row_no}'].number_format = numbers.FORMAT_TEXT

        # 工程コード(E列)入力時に工程名(F列)を自動表示
        for row_no in range(2, 5001):
            ws_input[f'F{row_no}'] = f'=IFERROR(VLOOKUP(E{row_no},工程!A:B,2,FALSE),"")'
            ws_input[f'H{row_no}'] = f'=IFERROR(VLOOKUP(G{row_no},ライン!A:B,2,FALSE),"")'
            ws_input[f'K{row_no}'] = f'=IFERROR(VLOOKUP(J{row_no},仕入先!A:B,2,FALSE),"")'

        # 調達区分は選択式（外注 / 購買 / 自社製造）
        sourcing_validation = DataValidation(
            type="list",
            formula1='"外注,購買,自社製造"',
            allow_blank=False
        )
        sourcing_validation.errorTitle = '入力エラー'
        sourcing_validation.error = '調達区分は「外注 / 購買 / 自社製造」から選択してください。'
        ws_input.add_data_validation(sourcing_validation)
        sourcing_validation.add('I2:I5000')

        # 時間単位は選択式（分 / 日）
        time_unit_validation = DataValidation(
            type="list",
            formula1='"分,日"',
            allow_blank=False
        )
        time_unit_validation.errorTitle = '入力エラー'
        time_unit_validation.error = '時間単位は「分 / 日」から選択してください。'
        ws_input.add_data_validation(time_unit_validation)
        time_unit_validation.add('N2:N5000')

        ws_guide = wb.create_sheet('使用説明')
        guide_rows = [
            ['項目', '内容'],
            ['必須列', '親品番, 子品番, 数量, 調達区分 + 補足'],
            ['任意列（現行取込ロジック）', '完成品'],
            ['調達区分', '自社製造 / 購買 / 外注（MAKE / BUY / SUBCON も可）'],
            ['時間単位', '分 または 日（MINUTE / DAY も可）'],
            ['注意1', '親品番・子品番・工程コード・ラインコード・仕入先コードは、各マスタに存在するコードを指定してください。工程名/ライン名/仕入先名はコードから自動表示されます。'],
            ['注意2', '同じ版/有効開始日で既存BOMがある場合、取込はエラーになります。'],
            ['注意3', '有効開始日・有効終了日・備考は取込画面で指定します。'],
            ['', ''],
            ['補足', ''],
            ['調達区分', '追加必須列'],
            ['自社製造', '工程コード, ラインコード, ＬＴ(日), 所要時間(分), 時間単位'],
            ['購入', '仕入先コード, ＬＴ(日), 時間単位'],
            ['外作', '仕入先コード, ＬＴ(日), 時間単位'],
        ]
        for row in guide_rows:
            ws_guide.append(row)

        # 参照用マスタシート（DB値）
        ws_process = wb.create_sheet('工程')
        ws_process.append(['工程コード', '工程名', 'ラインコード', 'ライン名', '有効'])
        proc_row_no = 2
        for p in Process.objects.select_related('line').order_by('process_code'):
            ws_process.append([
                p.process_code,
                p.process_name,
                p.line.line_code if p.line else '',
                p.line.line_name if p.line else '',
                '有効' if p.is_active else '無効',
            ])
            ws_process[f'A{proc_row_no}'].number_format = numbers.FORMAT_TEXT
            proc_row_no += 1

        ws_line = wb.create_sheet('ライン')
        ws_line.append(['ラインコード', 'ライン名', 'ライン種別', '有効'])
        for l in Line.objects.order_by('line_code'):
            ws_line.append([
                l.line_code,
                l.line_name,
                l.line_type or '',
                '有効' if l.is_active else '無効',
            ])

        ws_supplier = wb.create_sheet('仕入先')
        ws_supplier.append(['仕入先コード', '仕入先名', '有効'])
        for s in Supplier.objects.order_by('supplier_code'):
            supplier_active = getattr(s, 'is_active', True)
            ws_supplier.append([
                s.supplier_code,
                s.supplier_name,
                '有効' if supplier_active else '無効',
            ])

        from io import BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        from django.http import HttpResponse
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="bom_import_template.xlsx"'
        return response

    @action(detail=False, methods=['post'], parser_classes=[parsers.MultiPartParser, parsers.FormParser], url_path='import_csv')
    def import_csv(self, request):
        upload = request.FILES.get('file')
        if not upload:
            return Response({'detail': '取込ファイルがありません'}, status=status.HTTP_400_BAD_REQUEST)

        version = str(request.data.get('version') or 'v1').strip() or 'v1'
        use_existing_duplicates = str(request.data.get('use_existing_duplicates', 'false')).lower() in ['1', 'true', 'yes', 'on']
        completed_product_default = str(request.data.get('completed_product_code') or '').strip()
        valid_from_raw = str(request.data.get('valid_from') or '').strip()
        valid_to_raw = str(request.data.get('valid_to') or '').strip()
        item_remark = str(request.data.get('remark') or '').strip()
        is_active = str(request.data.get('is_active', 'true')).lower() in ['1', 'true', 'yes', 'on']

        if not valid_from_raw:
            return Response({'detail': '有効開始日を指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            valid_from = datetime.strptime(valid_from_raw, '%Y-%m-%d').date()
        except ValueError:
            return Response({'detail': '有効開始日は YYYY-MM-DD 形式で指定してください'}, status=status.HTTP_400_BAD_REQUEST)
        valid_to = None
        if valid_to_raw:
            try:
                valid_to = datetime.strptime(valid_to_raw, '%Y-%m-%d').date()
            except ValueError:
                return Response({'detail': '有効終了日は YYYY-MM-DD 形式で指定してください'}, status=status.HTTP_400_BAD_REQUEST)

        raw = upload.read()
        filename = (getattr(upload, 'name', '') or '').lower()
        input_rows = []
        fieldnames = []

        if filename.endswith('.xlsx') or filename.endswith('.xlsm'):
            from io import BytesIO
            try:
                wb = load_workbook(BytesIO(raw), data_only=True, read_only=True)
                ws = wb[wb.sheetnames[0]]
            except Exception:
                return Response({'detail': 'Excelファイルの読み取りに失敗しました'}, status=status.HTTP_400_BAD_REQUEST)

            excel_rows = list(ws.iter_rows(values_only=True))
            if not excel_rows:
                return Response({'detail': 'Excelファイルにデータがありません'}, status=status.HTTP_400_BAD_REQUEST)

            fieldnames = [str(v).strip() if v is not None else '' for v in excel_rows[0]]
            for row in excel_rows[1:]:
                if row is None:
                    continue
                if all((cell is None or str(cell).strip() == '') for cell in row):
                    continue
                row_dict = {}
                for i, key in enumerate(fieldnames):
                    if not key:
                        continue
                    value = row[i] if i < len(row) else ''
                    row_dict[key] = '' if value is None else str(value).strip()
                input_rows.append(row_dict)
        else:
            text = None
            for enc in ('utf-8-sig', 'cp932', 'shift_jis', 'utf-8'):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if text is None:
                return Response({'detail': 'CSV文字コードを判別できません（UTF-8/Shift_JISのみ対応）'}, status=status.HTTP_400_BAD_REQUEST)
            reader = csv.DictReader(StringIO(text))
            fieldnames = reader.fieldnames or []
            input_rows = list(reader)

        required_headers = ['親品番', '子品番', '数量', '調達区分']
        missing = [h for h in required_headers if h not in fieldnames]
        if missing:
            return Response({'detail': f'必須ヘッダー不足: {", ".join(missing)}'}, status=status.HTTP_400_BAD_REQUEST)

        # 1) 最優先で 品番存在チェック（M_PRODUCT=Product）
        early_errors = []
        early_product_codes = set()
        for idx, row in enumerate(input_rows, start=2):
            row_completed_code = str(row.get('完成品') or '').strip()
            if row_completed_code and completed_product_default and row_completed_code != completed_product_default:
                early_errors.append(
                    f'{idx}行目: 完成品が不一致です（完成品列: {row_completed_code} / 画面入力: {completed_product_default}）'
                )
                continue
            completed_code = row_completed_code or completed_product_default
            parent_code = str(row.get('親品番') or '').strip()
            child_code = str(row.get('子品番') or '').strip()
            if not completed_code:
                early_errors.append(f'{idx}行目: 完成品が未指定です（画面入力または完成品列を指定してください）')
            if not parent_code:
                early_errors.append(f'{idx}行目: 親品番が未指定です')
            if not child_code:
                early_errors.append(f'{idx}行目: 子品番が未指定です')
            if completed_code:
                early_product_codes.add(completed_code)
            if parent_code:
                early_product_codes.add(parent_code)
            if child_code:
                early_product_codes.add(child_code)

        if early_errors:
            return Response({'detail': 'チェックエラーがあります', 'errors': early_errors[:50]}, status=status.HTTP_400_BAD_REQUEST)

        existing_codes = set(Product.objects.filter(product_code__in=early_product_codes).values_list('product_code', flat=True))
        for idx, row in enumerate(input_rows, start=2):
            row_completed_code = str(row.get('完成品') or '').strip()
            completed_code = row_completed_code or completed_product_default
            parent_code = str(row.get('親品番') or '').strip()
            child_code = str(row.get('子品番') or '').strip()
            if completed_code and completed_code not in existing_codes:
                early_errors.append(f'{idx}行目: 完成品が未登録です ({completed_code})')
            if parent_code and parent_code not in existing_codes:
                early_errors.append(f'{idx}行目: 親品番が未登録です ({parent_code})')
            if child_code and child_code not in existing_codes:
                early_errors.append(f'{idx}行目: 子品番が未登録です ({child_code})')

        if early_errors:
            return Response({'detail': 'チェックエラーがあります', 'errors': early_errors[:50]}, status=status.HTTP_400_BAD_REQUEST)

        sourcing_map = {
            '自社製造': 'MAKE', 'MAKE': 'MAKE',
            '購買': 'BUY', '購入': 'BUY', 'BUY': 'BUY',
            '外注': 'SUBCON', 'SUBCON': 'SUBCON',
        }
        time_unit_map = {'日': 'DAY', 'DAY': 'DAY', '分': 'MINUTE', 'MINUTE': 'MINUTE'}

        row_errors = []
        parsed_rows = []
        for idx, row in enumerate(input_rows, start=2):
            row_has_error = False
            row_completed_code = str(row.get('完成品') or '').strip()
            if row_completed_code and completed_product_default and row_completed_code != completed_product_default:
                row_errors.append(
                    f'{idx}行目: 完成品が不一致です（完成品列: {row_completed_code} / 画面入力: {completed_product_default}）'
                )
                continue
            completed_code = row_completed_code or completed_product_default
            parent_code = str(row.get('親品番') or '').strip()
            child_code = str(row.get('子品番') or '').strip()
            quantity_raw = str(row.get('数量') or '').strip()
            if not completed_code:
                row_errors.append(f'{idx}行目: 完成品が未指定です（画面入力または完成品列を指定してください）')
                continue
            if not parent_code or not child_code or not quantity_raw:
                row_errors.append(f'{idx}行目: 必須項目不足（親品番/子品番/数量）')
                continue
            try:
                qty = Decimal(quantity_raw)
                if qty <= 0:
                    raise InvalidOperation
            except Exception:
                row_errors.append(f'{idx}行目: 数量が不正です')
                continue

            sourcing_raw = str(row.get('調達区分') or '').strip()
            sourcing_type = sourcing_map.get(sourcing_raw)
            if not sourcing_raw:
                row_errors.append(f'{idx}行目: 調達区分は必須です')
                continue
            if not sourcing_type:
                row_errors.append(f'{idx}行目: 調達区分が不正です ({sourcing_raw})')
                continue

            lead_raw = str(row.get('ＬＴ(日)') or row.get('リードタイム(日)') or '0').strip() or '0'
            duration_raw = str(row.get('所要時間(分)') or '0').strip() or '0'
            try:
                lead_time_days = int(lead_raw)
            except ValueError:
                row_errors.append(f'{idx}行目: リードタイム(日)が不正です')
                continue
            try:
                duration_min = int(duration_raw)
            except ValueError:
                row_errors.append(f'{idx}行目: 所要時間(分)が不正です')
                continue
            if lead_time_days < 0:
                row_errors.append(f'{idx}行目: リードタイム(日)は0以上で入力してください')
                continue
            if duration_min < 0:
                row_errors.append(f'{idx}行目: 所要時間(分)は0以上で入力してください')
                continue

            process_code = str(row.get('工程コード') or '').strip()
            line_code = str(row.get('ラインコード') or '').strip()
            supplier_code = str(row.get('仕入先コード') or '').strip()
            time_unit_raw = str(row.get('時間単位') or '').strip()
            time_unit = time_unit_map.get(time_unit_raw)

            # 区分別必須チェック
            if sourcing_type == 'MAKE':
                if not process_code:
                    row_errors.append(f'{idx}行目: 自社製造は工程コードが必須です')
                    row_has_error = True
                if not line_code:
                    row_errors.append(f'{idx}行目: 自社製造はラインコードが必須です')
                    row_has_error = True
                if not time_unit_raw:
                    row_errors.append(f'{idx}行目: 自社製造は時間単位が必須です')
                    row_has_error = True
                elif not time_unit:
                    row_errors.append(f'{idx}行目: 時間単位は「分」または「日」を指定してください')
                    row_has_error = True
                elif time_unit == 'MINUTE' and duration_min <= 0:
                    row_errors.append(f'{idx}行目: 自社製造で時間単位=分の場合、所要時間(分)を1以上で入力してください')
                    row_has_error = True
                elif time_unit == 'DAY' and lead_time_days <= 0:
                    row_errors.append(f'{idx}行目: 自社製造で時間単位=日の場合、リードタイム(日)を1以上で入力してください')
                    row_has_error = True
            elif sourcing_type in ['BUY', 'SUBCON']:
                if not supplier_code:
                    row_errors.append(f'{idx}行目: {sourcing_raw}は仕入先コードが必須です')
                    row_has_error = True
                if not time_unit_raw:
                    row_errors.append(f'{idx}行目: {sourcing_raw}は時間単位が必須です')
                    row_has_error = True
                elif time_unit != 'DAY':
                    row_errors.append(f'{idx}行目: {sourcing_raw}は時間単位=日で入力してください')
                    row_has_error = True
                if lead_time_days <= 0:
                    row_errors.append(f'{idx}行目: {sourcing_raw}はリードタイム(日)を1以上で入力してください')
                    row_has_error = True
                if process_code and sourcing_type == 'BUY':
                    row_errors.append(f'{idx}行目: 購入は工程コードを指定できません')
                    row_has_error = True
                # SUBCON は工程任意。未入力時はGに補完
                if sourcing_type == 'SUBCON' and not process_code:
                    process_code = 'G'

            if row_has_error:
                continue

            parsed_rows.append({
                'row_no': idx,
                'completed_code': completed_code,
                'parent_code': parent_code,
                'child_code': child_code,
                'quantity': qty,
                'process_code': process_code,
                'line_code': line_code,
                'sourcing_type': sourcing_type,
                'supplier_code': supplier_code,
                'lead_time_days': lead_time_days,
                'duration_min': duration_min,
                'time_unit': time_unit,
            })

        if row_errors:
            return Response({'detail': 'CSV内容にエラーがあります', 'errors': row_errors[:30]}, status=status.HTTP_400_BAD_REQUEST)
        if not parsed_rows:
            return Response({'detail': '有効なデータ行がありません'}, status=status.HTTP_400_BAD_REQUEST)

        from django.db import transaction
        with transaction.atomic():
            product_codes = set()
            process_codes = set()
            line_codes = set()
            supplier_codes = set()
            for row in parsed_rows:
                product_codes.add(row['child_code'])
                if row['parent_code']:
                    product_codes.add(row['parent_code'])
                if row.get('completed_code'):
                    product_codes.add(row['completed_code'])
                if row['process_code']:
                    process_codes.add(row['process_code'])
                if row['line_code']:
                    line_codes.add(row['line_code'])
                if row['supplier_code']:
                    supplier_codes.add(row['supplier_code'])

            product_map = {p.product_code: p for p in Product.objects.filter(product_code__in=product_codes)}
            process_map = {p.process_code: p for p in Process.objects.filter(process_code__in=process_codes)}
            line_map = {l.line_code: l for l in Line.objects.filter(line_code__in=line_codes)}
            supplier_map = {s.supplier_code: s for s in Supplier.objects.filter(supplier_code__in=supplier_codes)}

            for row in parsed_rows:
                if row['child_code'] not in product_map:
                    row_errors.append(f"{row['row_no']}行目: 子品番が未登録です ({row['child_code']})")
                if row['parent_code'] and row['parent_code'] not in product_map:
                    row_errors.append(f"{row['row_no']}行目: 親品番が未登録です ({row['parent_code']})")
                if row.get('completed_code') and row['completed_code'] not in product_map:
                    row_errors.append(f"{row['row_no']}行目: 完成品が未登録です ({row['completed_code']})")
                if row['process_code'] and row['process_code'] not in process_map:
                    row_errors.append(f"{row['row_no']}行目: 工程コードが未登録です ({row['process_code']})")
                if row['line_code'] and row['line_code'] not in line_map:
                    row_errors.append(f"{row['row_no']}行目: ラインコードが未登録です ({row['line_code']})")
                if row['supplier_code'] and row['supplier_code'] not in supplier_map:
                    row_errors.append(f"{row['row_no']}行目: 仕入先コードが未登録です ({row['supplier_code']})")

            if row_errors:
                return Response({'detail': 'マスタ参照エラーがあります', 'errors': row_errors[:30]}, status=status.HTTP_400_BAD_REQUEST)

            all_parent_codes = {
                row['parent_code']
                for row in parsed_rows
                if row['parent_code']
            }

            created_boms = {}
            created_item_count = 0
            duplicate_boms = []
            for parent_code in sorted(all_parent_codes):
                parent_product = product_map[parent_code]
                bom = BOM.objects.filter(
                    parent_product=parent_product,
                    version=version,
                ).order_by('-valid_from', '-id').first()
                if bom:
                    duplicate_boms.append(f'{parent_code} / {version}（既存開始日: {bom.valid_from}）')
                    if not use_existing_duplicates:
                        continue
                else:
                    bom = BOM.objects.create(
                        parent_product=parent_product,
                        version=version,
                        valid_from=valid_from,
                        valid_to=valid_to,
                        is_active=is_active,
                    )
                created_boms[parent_code] = bom

            if duplicate_boms and not use_existing_duplicates:
                return Response(
                    {
                        'detail': '既存BOM重複があります。再利用する場合は確認して実行してください。',
                        'duplicate_boms': duplicate_boms[:50],
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            for row in parsed_rows:
                parent_code = row['parent_code']
                parent_bom = created_boms.get(parent_code)
                if not parent_bom:
                    row_errors.append(f"{row['row_no']}行目: 親BOMを作成できませんでした ({parent_code})")
                    continue
                BOMItem.objects.create(
                    bom=parent_bom,
                    child_product=product_map[row['child_code']],
                    quantity=row['quantity'],
                    loss_rate=Decimal('0'),
                    sourcing_type=row['sourcing_type'],
                    supplier=supplier_map.get(row['supplier_code']),
                    process=process_map.get(row['process_code']),
                    line=line_map.get(row['line_code']),
                    time_unit=row['time_unit'],
                    lead_time_days=row['lead_time_days'],
                    duration_min=row['duration_min'] if row['duration_min'] > 0 else None,
                    remark=item_remark or None,
                )
                created_item_count += 1

            if row_errors:
                return Response({'detail': '取込中にエラーが発生しました', 'errors': row_errors[:30]}, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                'message': 'BOMを取り込みました',
                'created_boms': len(created_boms),
                'created_items': created_item_count,
                'reused_boms': len(duplicate_boms) if use_existing_duplicates else 0,
            }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], parser_classes=[parsers.MultiPartParser, parsers.FormParser], url_path='import_check')
    def import_check(self, request):
        upload = request.FILES.get('file')
        if not upload:
            return Response({'detail': '取込ファイルがありません'}, status=status.HTTP_400_BAD_REQUEST)
        version = str(request.data.get('version') or 'v1').strip() or 'v1'
        completed_product_default = str(request.data.get('completed_product_code') or '').strip()
        valid_from_raw = str(request.data.get('valid_from') or '').strip()
        valid_from = None
        if valid_from_raw:
            try:
                valid_from = datetime.strptime(valid_from_raw, '%Y-%m-%d').date()
            except ValueError:
                return Response({'detail': '有効開始日は YYYY-MM-DD 形式で指定してください'}, status=status.HTTP_400_BAD_REQUEST)

        raw = upload.read()
        filename = (getattr(upload, 'name', '') or '').lower()
        input_rows = []
        fieldnames = []

        if filename.endswith('.xlsx') or filename.endswith('.xlsm'):
            from io import BytesIO
            try:
                wb = load_workbook(BytesIO(raw), data_only=True, read_only=True)
                ws = wb[wb.sheetnames[0]]
            except Exception:
                return Response({'detail': 'Excelファイルの読み取りに失敗しました'}, status=status.HTTP_400_BAD_REQUEST)
            excel_rows = list(ws.iter_rows(values_only=True))
            if not excel_rows:
                return Response({'detail': 'Excelファイルにデータがありません'}, status=status.HTTP_400_BAD_REQUEST)
            fieldnames = [str(v).strip() if v is not None else '' for v in excel_rows[0]]
            for row in excel_rows[1:]:
                if row is None or all((cell is None or str(cell).strip() == '') for cell in row):
                    continue
                row_dict = {}
                for i, key in enumerate(fieldnames):
                    if not key:
                        continue
                    value = row[i] if i < len(row) else ''
                    row_dict[key] = '' if value is None else str(value).strip()
                input_rows.append(row_dict)
        else:
            text = None
            for enc in ('utf-8-sig', 'cp932', 'shift_jis', 'utf-8'):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if text is None:
                return Response({'detail': 'CSV文字コードを判別できません（UTF-8/Shift_JISのみ対応）'}, status=status.HTTP_400_BAD_REQUEST)
            reader = csv.DictReader(StringIO(text))
            fieldnames = reader.fieldnames or []
            input_rows = list(reader)

        required_headers = ['親品番', '子品番', '数量', '調達区分']
        missing = [h for h in required_headers if h not in fieldnames]
        if missing:
            return Response({'detail': f'必須ヘッダー不足: {", ".join(missing)}'}, status=status.HTTP_400_BAD_REQUEST)

        sourcing_map = {
            '自社製造': 'MAKE', 'MAKE': 'MAKE',
            '購買': 'BUY', '購入': 'BUY', 'BUY': 'BUY',
            '外注': 'SUBCON', 'SUBCON': 'SUBCON',
        }
        row_errors = []
        checked_count = 0
        parsed_rows = []
        for idx, row in enumerate(input_rows, start=2):
            row_has_error = False
            parent_code = str(row.get('親品番') or '').strip()
            child_code = str(row.get('子品番') or '').strip()
            quantity_raw = str(row.get('数量') or '').strip()
            row_completed_code = str(row.get('完成品') or '').strip()
            if row_completed_code and completed_product_default and row_completed_code != completed_product_default:
                row_errors.append(
                    f'{idx}行目: 完成品が不一致です（完成品列: {row_completed_code} / 画面入力: {completed_product_default}）'
                )
                continue
            completed_code = row_completed_code or completed_product_default
            if not completed_code:
                row_errors.append(f'{idx}行目: 完成品が未指定です（画面入力または完成品列を指定してください）')
                continue
            if not parent_code or not child_code or not quantity_raw:
                row_errors.append(f'{idx}行目: 必須項目不足（親品番/子品番/数量）')
                continue
            try:
                qty = Decimal(quantity_raw)
                if qty <= 0:
                    raise InvalidOperation
            except Exception:
                row_errors.append(f'{idx}行目: 数量が不正です')
                continue

            sourcing_raw = str(row.get('調達区分') or '').strip()
            sourcing_type = sourcing_map.get(sourcing_raw)
            if not sourcing_raw:
                row_errors.append(f'{idx}行目: 調達区分は必須です')
                continue
            if not sourcing_type:
                row_errors.append(f'{idx}行目: 調達区分が不正です ({sourcing_raw})')
                continue

            lead_raw = str(row.get('ＬＴ(日)') or row.get('リードタイム(日)') or '0').strip() or '0'
            duration_raw = str(row.get('所要時間(分)') or '0').strip() or '0'
            try:
                lead_time_days = int(lead_raw)
            except ValueError:
                row_errors.append(f'{idx}行目: リードタイム(日)が不正です')
                continue
            try:
                duration_min = int(duration_raw)
            except ValueError:
                row_errors.append(f'{idx}行目: 所要時間(分)が不正です')
                continue
            if lead_time_days < 0:
                row_errors.append(f'{idx}行目: リードタイム(日)は0以上で入力してください')
                row_has_error = True
            if duration_min < 0:
                row_errors.append(f'{idx}行目: 所要時間(分)は0以上で入力してください')
                row_has_error = True

            process_code = str(row.get('工程コード') or '').strip()
            line_code = str(row.get('ラインコード') or '').strip()
            supplier_code = str(row.get('仕入先コード') or '').strip()
            time_unit_raw = str(row.get('時間単位') or '').strip()
            time_unit = {'日': 'DAY', 'DAY': 'DAY', '分': 'MINUTE', 'MINUTE': 'MINUTE'}.get(time_unit_raw)

            if sourcing_type == 'MAKE':
                if not process_code:
                    row_errors.append(f'{idx}行目: 自社製造は工程コードが必須です')
                    row_has_error = True
                if not line_code:
                    row_errors.append(f'{idx}行目: 自社製造はラインコードが必須です')
                    row_has_error = True
                if not time_unit_raw:
                    row_errors.append(f'{idx}行目: 自社製造は時間単位が必須です')
                    row_has_error = True
                elif not time_unit:
                    row_errors.append(f'{idx}行目: 時間単位は「分」または「日」を指定してください')
                    row_has_error = True
                elif time_unit == 'MINUTE' and duration_min <= 0:
                    row_errors.append(f'{idx}行目: 自社製造で時間単位=分の場合、所要時間(分)を1以上で入力してください')
                    row_has_error = True
                elif time_unit == 'DAY' and lead_time_days <= 0:
                    row_errors.append(f'{idx}行目: 自社製造で時間単位=日の場合、リードタイム(日)を1以上で入力してください')
                    row_has_error = True
            elif sourcing_type in ['BUY', 'SUBCON']:
                if not supplier_code:
                    row_errors.append(f'{idx}行目: {sourcing_raw}は仕入先コードが必須です')
                    row_has_error = True
                if not time_unit_raw:
                    row_errors.append(f'{idx}行目: {sourcing_raw}は時間単位が必須です')
                    row_has_error = True
                elif time_unit != 'DAY':
                    row_errors.append(f'{idx}行目: {sourcing_raw}は時間単位=日で入力してください')
                    row_has_error = True
                if lead_time_days <= 0:
                    row_errors.append(f'{idx}行目: {sourcing_raw}はリードタイム(日)を1以上で入力してください')
                    row_has_error = True
                if process_code and sourcing_type == 'BUY':
                    row_errors.append(f'{idx}行目: 購入は工程コードを指定できません')
                    row_has_error = True

            if row_has_error:
                continue

            parsed_rows.append({
                'row_no': idx,
                'completed_code': completed_code,
                'parent_code': parent_code,
                'child_code': child_code,
                'process_code': process_code,
                'line_code': line_code,
                'supplier_code': supplier_code,
            })
            checked_count += 1

        if row_errors:
            return Response({'detail': 'チェックエラーがあります', 'errors': row_errors[:50]}, status=status.HTTP_400_BAD_REQUEST)

        product_codes = set()
        process_codes = set()
        line_codes = set()
        supplier_codes = set()
        parent_codes = set()
        for row in parsed_rows:
            product_codes.add(row['child_code'])
            product_codes.add(row['parent_code'])
            if row.get('completed_code'):
                product_codes.add(row['completed_code'])
            parent_codes.add(row['parent_code'])
            if row['process_code']:
                process_codes.add(row['process_code'])
            if row['line_code']:
                line_codes.add(row['line_code'])
            if row['supplier_code']:
                supplier_codes.add(row['supplier_code'])

        product_map = {p.product_code: p for p in Product.objects.filter(product_code__in=product_codes)}
        process_map = {p.process_code: p for p in Process.objects.filter(process_code__in=process_codes)}
        line_map = {l.line_code: l for l in Line.objects.filter(line_code__in=line_codes)}
        supplier_map = {s.supplier_code: s for s in Supplier.objects.filter(supplier_code__in=supplier_codes)}

        for row in parsed_rows:
            if row['child_code'] not in product_map:
                row_errors.append(f"{row['row_no']}行目: 子品番が未登録です ({row['child_code']})")
            if row['parent_code'] not in product_map:
                row_errors.append(f"{row['row_no']}行目: 親品番が未登録です ({row['parent_code']})")
            if row.get('completed_code') and row['completed_code'] not in product_map:
                row_errors.append(f"{row['row_no']}行目: 完成品が未登録です ({row['completed_code']})")
            if row['process_code'] and row['process_code'] not in process_map:
                row_errors.append(f"{row['row_no']}行目: 工程コードが未登録です ({row['process_code']})")
            if row['line_code'] and row['line_code'] not in line_map:
                row_errors.append(f"{row['row_no']}行目: ラインコードが未登録です ({row['line_code']})")
            if row['supplier_code'] and row['supplier_code'] not in supplier_map:
                row_errors.append(f"{row['row_no']}行目: 仕入先コードが未登録です ({row['supplier_code']})")

        duplicate_boms = []
        for parent_code in sorted(parent_codes):
            parent_product = product_map.get(parent_code)
            if not parent_product:
                continue
            exist_bom = BOM.objects.filter(
                parent_product=parent_product,
                version=version,
            ).order_by('-valid_from', '-id').first()
            if exist_bom:
                duplicate_boms.append(f'{parent_code} / {version}（既存開始日: {exist_bom.valid_from}）')

        if row_errors:
            return Response({'detail': 'チェックエラーがあります', 'errors': row_errors[:50]}, status=status.HTTP_400_BAD_REQUEST)
        message = 'チェックOKです'
        if duplicate_boms:
            message = 'チェックOK（既存BOM重複あり）'
        return Response(
            {
                'message': message,
                'checked_rows': checked_count,
                'duplicate_boms': duplicate_boms[:50],
            },
            status=status.HTTP_200_OK
        )

    def _collect_routing_items_recursive(
        self,
        bom: BOM,
        active_path_bom_ids: set,
        collector: list,
        depth: int = 0,
        path_prefix: tuple = (),
        include_buy: bool = False,
    ):
        """
        Depth-first collect routing items (MAKE/SUBCON/BUY) from bom and its descendants.

        - Child BOMs are traversed before appending the parent item (post-order) so
          downstream工程が先に生成される（前後関係を表す工程順に近づける）。
        - collector に (depth, path, item, parent_product) を詰める。path は階層内の通し。
        - include_buy=True の場合、BUY品も収集対象に含める
        - 同一BOMが別枝で再登場するケースは正しく再展開し、循環参照のみ抑止する
        """
        if bom.id in active_path_bom_ids:
            return

        next_path_bom_ids = set(active_path_bom_ids)
        next_path_bom_ids.add(bom.id)

        items_qs = BOMItem.objects.filter(bom=bom).select_related('child_product', 'process', 'line', 'supplier').order_by('id')
        for idx, item in enumerate(items_qs, start=1):
            child_bom = self._pick_child_bom(item.child_product)
            if child_bom:
                self._collect_routing_items_recursive(
                    child_bom,
                    next_path_bom_ids,
                    collector,
                    depth=depth + 1,
                    path_prefix=path_prefix + (idx,),
                    include_buy=include_buy,
                )
            target_types = ['MAKE', 'SUBCON', 'BUY'] if include_buy else ['MAKE', 'SUBCON']
            if item.sourcing_type in target_types:
                collector.append((depth, path_prefix + (idx,), item, bom.parent_product))

    def _get_or_create_purchase_line_and_process(self, supplier):
        """
        仕入先に対応する仮想ライン（仕入先コード）とPURCHASE工程を取得または作成する。
        """
        line_obj = ensure_supplier_purchase_line(supplier)

        process_code = 'PURCHASE'
        process_name = '購買'
        process_obj, _ = Process.objects.get_or_create(
            process_code=process_code,
            defaults={
                'process_name': process_name,
                'line': line_obj,
                'management_unit': 'DAY',
                'is_active': False,
            }
        )
        return line_obj, process_obj

    def _get_supplier_gaisaku_line_and_process(self, supplier):
        """
        外作品（SUBCON）用: 仕入先の仕入ラインと外作工程(G)を取得する。
        購買と同様に仕入先コードのラインを使い、工程は外作工程(process_code='G')。
        """
        line_obj = ensure_supplier_purchase_line(supplier)

        try:
            process_obj = Process.objects.get(process_code='G')
        except Process.DoesNotExist:
            raise ValueError('外作工程（process_code="G"）がマスタに存在しません。')

        return line_obj, process_obj

    def _resolve_generated_routing_valid_from(self, raw_value):
        if isinstance(raw_value, datetime):
            return raw_value
        if isinstance(raw_value, str) and raw_value.strip():
            parsed = parse_datetime(raw_value.strip())
            if parsed:
                return parsed
            raise ValueError('有効開始日時の形式が不正です。')

        default_dt = datetime.now() + timedelta(days=2)
        return default_dt.replace(hour=8, minute=0, second=0, microsecond=0)

    @action(detail=True, methods=['post'])
    def generate_routing(self, request, pk=None):
        """Generate or replace routing steps from BOM MAKE/SUBCON/BUY items (recursive)."""
        bom = self.get_object()
        include_buy = request.data.get('include_buy', True)
        routing_items_info = []
        self._collect_routing_items_recursive(
            bom,
            active_path_bom_ids=set(),
            collector=routing_items_info,
            include_buy=include_buy,
        )

        item_types = 'MAKE/SUBCON/BUY' if include_buy else 'MAKE/SUBCON'
        if not routing_items_info:
            return Response({'detail': f'No {item_types} items found in this BOM tree. Nothing to generate.'}, status=status.HTTP_400_BAD_REQUEST)

        # BOMに重複部品がないかチェック（RoutingStepMaterialのunique制約違反を事前に防ぐ）
        boms_to_check = set()
        for _, _, item, _ in routing_items_info:
            child_bom = self._pick_child_bom(item.child_product)
            if child_bom:
                boms_to_check.add(child_bom.id)
        duplicate_errors = []
        for bom_id in boms_to_check:
            items_in_bom = BOMItem.objects.filter(bom_id=bom_id).values_list('child_product_id', flat=True)
            seen, duplicates = set(), set()
            for pid in items_in_bom:
                if pid in seen:
                    duplicates.add(pid)
                seen.add(pid)
            if duplicates:
                from .models import BOM as BOMModel
                b = BOMModel.objects.select_related('parent_product').get(id=bom_id)
                dup_codes = list(
                    BOMItem.objects.filter(bom_id=bom_id, child_product_id__in=duplicates)
                    .values_list('child_product__product_code', flat=True).distinct()
                )
                duplicate_errors.append(
                    f'BOM「{b.parent_product.product_code}」に重複部品があります: {", ".join(dup_codes)}'
                )
        if duplicate_errors:
            return Response(
                {'detail': 'BOMに重複部品があるためルーティングを生成できません。\n' + '\n'.join(duplicate_errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Optional final step (manual input)
        final_process_id = request.data.get('final_process_id')
        final_line_id = request.data.get('final_line_id')
        final_time_unit = request.data.get('final_time_unit', 'MINUTE')
        final_lead_time_days = request.data.get('final_lead_time_days')
        final_duration_min = request.data.get('final_duration_min')

        final_process = None
        final_line = None

        if final_process_id:
            try:
                final_process = Process.objects.select_related('line').get(id=final_process_id)
            except Process.DoesNotExist:
                return Response({'detail': f'Final process not found: id={final_process_id}'}, status=status.HTTP_400_BAD_REQUEST)

            # 工程にラインが紐づいている場合は、そのラインを常に優先する
            if final_process.line_id:
                final_line = final_process.line
            elif final_line_id:
                try:
                    final_line = Line.objects.get(id=final_line_id)
                except Line.DoesNotExist:
                    return Response({'detail': f'Final line not found: id={final_line_id}'}, status=status.HTTP_400_BAD_REQUEST)

            if final_time_unit not in ['MINUTE', 'DAY']:
                return Response({'detail': 'final_time_unit must be MINUTE or DAY'}, status=status.HTTP_400_BAD_REQUEST)

            if final_time_unit == 'MINUTE':
                if not final_duration_min or int(final_duration_min) <= 0:
                    return Response({'detail': 'final_duration_min must be >0 when final_time_unit=MINUTE'}, status=status.HTTP_400_BAD_REQUEST)
                if final_lead_time_days is None or final_lead_time_days == '':
                    final_lead_time_days = 0
                elif int(final_lead_time_days) < 0:
                    return Response({'detail': 'final_lead_time_days must be >=0'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                if final_lead_time_days is None or int(final_lead_time_days) < 0:
                    return Response({'detail': 'final_lead_time_days must be >=0 when final_time_unit=DAY'}, status=status.HTTP_400_BAD_REQUEST)
                final_duration_min = None

        # Validate each item has process/time info
        # BUY品の場合は仕入先が必須（工程・ラインは自動設定される）
        for _, _, it, _ in routing_items_info:
            if it.sourcing_type == 'BUY':
                # BUY品は仕入先が必須
                if not it.supplier_id:
                    return Response({'detail': f'Supplier is required on BUY item {it.child_product.product_code}'}, status=status.HTTP_400_BAD_REQUEST)
                # BUY品はDAY単位でリードタイムを使用（time_unitが未設定ならDAYとみなす）
                if it.time_unit not in ['MINUTE', 'DAY', None, '']:
                    return Response({'detail': f'Invalid time_unit on BOM item {it.child_product.product_code}'}, status=status.HTTP_400_BAD_REQUEST)
            elif it.sourcing_type == 'SUBCON' and it.supplier_id:
                # SUBCON + 仕入先あり: 工程・ラインは自動設定（購買と同様）
                if it.lead_time_days is None or it.lead_time_days < 0:
                    return Response({'detail': f'リードタイム(日)を0以上で入力してください: {it.child_product.product_code}'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                # MAKE/SUBCON(仕入先なし)は工程が必須
                if not it.process_id:
                    return Response({'detail': f'Process is required on BOM item {it.child_product.product_code} ({it.sourcing_type})'}, status=status.HTTP_400_BAD_REQUEST)
                if it.time_unit not in ['MINUTE', 'DAY']:
                    return Response({'detail': f'Invalid time_unit on BOM item {it.child_product.product_code}'}, status=status.HTTP_400_BAD_REQUEST)
                if it.time_unit == 'MINUTE':
                    if it.duration_min is None or it.duration_min <= 0:
                        return Response({'detail': f'duration_min must be >0 (MINUTE) on BOM item {it.child_product.product_code}'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    if it.lead_time_days < 0:
                        return Response({'detail': f'lead_time_days must be >=0 (DAY) on BOM item {it.child_product.product_code}'}, status=status.HTTP_400_BAD_REQUEST)

        routing_code = request.data.get('routing_code') or f"AUTO-{bom.parent_product.product_code}-{bom.version}"
        description = request.data.get('description') or 'bomから自動生成した'
        set_default = request.data.get('is_default', True)
        try:
            valid_from_datetime = self._resolve_generated_routing_valid_from(request.data.get('valid_from_datetime'))
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # 同じルーティングコードの既存レコードをチェック
        existing = Routing.objects.filter(
            product=bom.parent_product, routing_code=routing_code,
        ).order_by('-valid_from_datetime')

        for ex in existing:
            if ex.valid_to_datetime is None:
                return Response(
                    {'detail': f'ルーティングコード "{routing_code}" の既存ルーティング(ID:{ex.id})に終了日が設定されていません。'
                               f'先に既存ルーティングの終了日を設定してから再実行してください。'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if valid_from_datetime and valid_from_datetime <= ex.valid_to_datetime:
                return Response(
                    {'detail': f'新しい開始日は既存ルーティング(ID:{ex.id})の終了日 {ex.valid_to_datetime:%Y-%m-%d %H:%M} より後に設定してください。'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        routing = Routing.objects.create(
            product=bom.parent_product,
            routing_code=routing_code,
            description=description,
            is_default=set_default,
            is_active=True,
            valid_from_datetime=valid_from_datetime,
        )
        if set_default:
            get_overlapping_default_routings(routing).update(is_default=False)
        created_steps = []
        max_depth = max((depth for depth, _, _, _ in routing_items_info), default=0)
        # step_no + parallel_group の一意性を保証するためにセットで管理
        used_step_keys = set()
        for idx, (depth, path, item, parent_product) in enumerate(routing_items_info, start=1):
            path_str = ".".join(str(p) for p in path) if path else "1"
            step_no = (max_depth - len(path) + 1) * 1000
            parallel_group = idx  # 通し番号で一意性を保証
            parent_product_code = parent_product.product_code if parent_product else ''

            # BUY品・SUBCON品(仕入先あり)は仕入先ラインを自動設定
            if item.sourcing_type == 'BUY' and item.supplier_id:
                purchase_line, purchase_process = self._get_or_create_purchase_line_and_process(item.supplier)
                step_process = purchase_process
                step_line = purchase_line
                step_time_unit = 'DAY'
                step_lead_time_days = item.lead_time_days or 1
                step_duration_min = None
                step_remark = parent_product_code
            elif item.sourcing_type == 'SUBCON' and item.supplier_id:
                # 外作品: 購買と同様に仕入先ラインを使い、工程は外作工程(G)
                gaisaku_line, gaisaku_process = self._get_supplier_gaisaku_line_and_process(item.supplier)
                step_process = gaisaku_process
                step_line = gaisaku_line
                step_time_unit = 'DAY'
                step_lead_time_days = item.lead_time_days or 1
                step_duration_min = None
                step_remark = parent_product_code
            else:
                step_process = item.process
                step_line = item.line
                step_time_unit = item.time_unit
                # lead_time_days と duration_min は直交した概念（投入LT と 加工サイクル）
                # ライン最終品では両方同時に必要になるため、time_unit で片方を0/Noneに落とさず両方コピーする
                step_lead_time_days = int(item.lead_time_days or 0)
                step_duration_min = item.duration_min
                step_remark = parent_product_code

            step = RoutingStep.objects.create(
                routing=routing,
                step_no=step_no,
                parallel_group=parallel_group,
                process=step_process,
                line=step_line,
                output_product=item.child_product,
                source_bom_item=item,
                hierarchy_depth=depth,
                hierarchy_path=path_str,
                time_unit=step_time_unit,
                lead_time_days=step_lead_time_days,
                duration_min=step_duration_min,
                remark=step_remark
            )
            created_steps.append((item, step))

        # Append final step if provided
        if final_process:
            final_parent_product_code = bom.parent_product.product_code if bom.parent_product_id else ''
            max_step_no = max([s.step_no for _, s in created_steps], default=0)
            RoutingStep.objects.create(
                routing=routing,
                step_no=max_step_no + 1,
                process=final_process,
                line=final_line,
                output_product=bom.parent_product,
                hierarchy_depth=0,
                hierarchy_path="final",
                time_unit=final_time_unit,
                lead_time_days=int(final_lead_time_days or 0),
                duration_min=int(final_duration_min) if final_time_unit == 'MINUTE' else None,
                remark=final_parent_product_code
            )

        # 自動で工程別部品を付与（対象ステップの商品に紐づく子BOMの明細を消費部品とする）
        for item, step in created_steps:
            child_bom = self._pick_child_bom(item.child_product)
            if not child_bom:
                continue
            child_items = BOMItem.objects.filter(bom=child_bom).select_related('child_product')
            for child_item in child_items:
                RoutingStepMaterial.objects.create(
                    routing_step=step,
                    component=child_item.child_product,
                    quantity=child_item.quantity,
                    consume_timing='START',
                    remark=f"Auto from child BOM {child_bom.id}"
                )

        serialized = RoutingSerializer(routing)
        return Response(
            {
                'message': 'Routing generated from BOM (recursive)',
                'routing': serialized.data,
                'generated_steps': len(routing_items_info),
                'replaced_existing': False,
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def copy(self, request, pk=None):
        """
        BOMを別の親製品にコピーする
        payload: { new_parent_product_id: int }
        """
        bom = self.get_object()
        new_parent_product_id = request.data.get('new_parent_product_id')

        if not new_parent_product_id:
            return Response({'detail': 'new_parent_product_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_parent_product = Product.objects.get(id=new_parent_product_id)
        except Product.DoesNotExist:
            return Response({'detail': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

        # 新しいBOMを作成
        new_bom = BOM.objects.create(
            parent_product=new_parent_product,
            version=bom.version,
            valid_from=bom.valid_from,
            valid_to=bom.valid_to,
            is_active=bom.is_active,
            is_coproduct=bom.is_coproduct,
        )

        # BOMItemをコピー
        items = BOMItem.objects.filter(bom=bom)
        for item in items:
            BOMItem.objects.create(
                bom=new_bom,
                child_product=item.child_product,
                quantity=item.quantity,
                loss_rate=item.loss_rate,
                sourcing_type=item.sourcing_type,
                supplier=item.supplier,
                process=item.process,
                line=item.line,
                time_unit=item.time_unit,
                lead_time_days=item.lead_time_days,
                duration_min=item.duration_min,
                is_coproduct_driver=item.is_coproduct_driver,
                remark=item.remark,
            )

        return Response({
            'message': 'BOM copied successfully',
            'new_bom_id': new_bom.id,
            'items_copied': items.count(),
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def export_excel(self, request, pk=None):
        """BOM階層をExcel出力（管理サイトと同じロジック）"""
        try:
            from openpyxl import Workbook
        except ImportError:
            return Response({'detail': 'openpyxl is not installed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        from django.http import HttpResponse

        bom = self.get_object()

        wb = Workbook()
        ws = wb.active
        ws.title = 'BOM Tree'
        headers = [
            'BOM ID', '親製品', '部番表示', '製品名', '階層', '数量',
            '工程', 'ライン', '仕入先', 'リードタイム(日)', '所要時間(分)'
        ]
        ws.append(headers)
        rows = self._build_tree_excel_rows(bom)
        for row in rows:
            ws.append([
                row['bom_id'],
                row['parent_product'],
                row['part_display'],
                row['product_name'],
                row['level'],
                row['quantity'],
                row['process'],
                row['line'],
                row['supplier'],
                row['lead_time_days'],
                row['duration_min'],
            ])

        product_code = bom.parent_product.product_code if bom.parent_product else str(bom.id)
        filename = f"{product_code}.xlsx"

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response


class BOMItemViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = BOMItem.objects.all()
    serializer_class = BOMItemSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['bom', 'child_product', 'sourcing_type', 'process', 'line', 'time_unit', 'supplier']
    ordering_fields = ['created_at']
    ordering = ['id']

    def _get_or_create_purchase_line_and_process(self, supplier):
        if not supplier:
            return None, None

        line_obj = ensure_supplier_purchase_line(supplier)

        process_obj = Process.objects.filter(process_code='K').first()

        return line_obj, process_obj

    def _get_supplier_gaisaku_line_and_process(self, supplier):
        if not supplier:
            return None, None

        line_obj = ensure_supplier_purchase_line(supplier)

        process_obj = Process.objects.filter(process_code='G').first()

        return line_obj, process_obj

    def _normalize_parent_bom_coproduct_flag(self, bom_item: BOMItem):
        bom = getattr(bom_item, 'bom', None)
        parent_product = getattr(bom, 'parent_product', None) if bom else None
        if bom and parent_product and getattr(parent_product, 'is_virtual_set', False) and not bom.is_coproduct:
            bom.is_coproduct = True
            bom.save(update_fields=['is_coproduct', 'updated_at'])

    def _select_sync_target_steps(self, bom_item: BOMItem):
        fk_qs = RoutingStep.objects.filter(source_bom_item_id=bom_item.id)
        if fk_qs.exists():
            return fk_qs

        bom = getattr(bom_item, 'bom', None)
        if bom is None or not bom_item.child_product_id:
            return RoutingStep.objects.none()
        parent_product = getattr(bom, 'parent_product', None)
        parent_code = getattr(parent_product, 'product_code', None)
        if not parent_code:
            return RoutingStep.objects.none()

        # BOMから自動生成されたRoutingStepは remark に親製品コードを保持している
        base_qs = RoutingStep.objects.filter(
            remark=parent_code,
            output_product_id=bom_item.child_product_id,
            routing__is_active=True,
        )
        if not base_qs.exists():
            return base_qs

        exact = base_qs.filter(process_id=bom_item.process_id, line_id=bom_item.line_id)
        if exact.exists():
            return exact

        if bom_item.process_id:
            process_matched = base_qs.filter(process_id=bom_item.process_id)
            if process_matched.exists():
                return process_matched

        if bom_item.line_id:
            line_matched = base_qs.filter(line_id=bom_item.line_id)
            if line_matched.exists():
                return line_matched

        return base_qs

    def _sync_item_fields_to_routing(self, bom_item: BOMItem, field_names):
        steps = self._select_sync_target_steps(bom_item)
        for step in steps:
            changed_fields = []

            if any(name in field_names for name in ('supplier', 'sourcing_type', 'process', 'line', 'time_unit')):
                if bom_item.sourcing_type == 'BUY' and bom_item.supplier_id:
                    line_obj, process_obj = self._get_or_create_purchase_line_and_process(bom_item.supplier)
                    if step.line_id != getattr(line_obj, 'id', None):
                        step.line = line_obj
                        changed_fields.append('line')
                    if process_obj and step.process_id != process_obj.id:
                        step.process = process_obj
                        changed_fields.append('process')
                    if step.supplier_id != bom_item.supplier_id:
                        step.supplier = bom_item.supplier
                        changed_fields.append('supplier')
                    if step.time_unit != 'DAY':
                        step.time_unit = 'DAY'
                        changed_fields.append('time_unit')
                elif bom_item.sourcing_type == 'SUBCON' and bom_item.supplier_id:
                    line_obj, process_obj = self._get_supplier_gaisaku_line_and_process(bom_item.supplier)
                    if step.line_id != getattr(line_obj, 'id', None):
                        step.line = line_obj
                        changed_fields.append('line')
                    if process_obj and step.process_id != process_obj.id:
                        step.process = process_obj
                        changed_fields.append('process')
                    if step.supplier_id != bom_item.supplier_id:
                        step.supplier = bom_item.supplier
                        changed_fields.append('supplier')
                    if step.time_unit != 'DAY':
                        step.time_unit = 'DAY'
                        changed_fields.append('time_unit')
                else:
                    if step.process_id != bom_item.process_id:
                        step.process = bom_item.process
                        changed_fields.append('process')
                    if step.line_id != bom_item.line_id:
                        step.line = bom_item.line
                        changed_fields.append('line')
                    if step.supplier_id != bom_item.supplier_id:
                        step.supplier = bom_item.supplier
                        changed_fields.append('supplier')
                    if bom_item.time_unit and step.time_unit != bom_item.time_unit:
                        step.time_unit = bom_item.time_unit
                        changed_fields.append('time_unit')

            if 'lead_time_days' in field_names:
                item_lt = int(getattr(bom_item, 'lead_time_days', 0) or 0)
                step_lt = int(getattr(step, 'lead_time_days', 0) or 0)
                if step_lt != item_lt:
                    step.lead_time_days = item_lt
                    changed_fields.append('lead_time_days')

            if 'duration_min' in field_names:
                item_duration = int(bom_item.duration_min) if bom_item.duration_min is not None else None
                step_duration = int(step.duration_min) if step.duration_min is not None else None
                if step_duration != item_duration:
                    step.duration_min = item_duration
                    changed_fields.append('duration_min')

            if changed_fields:
                step.save(update_fields=changed_fields + ['updated_at'])

    def _build_delete_preview(self, bom_item: BOMItem):
        steps = self._select_sync_target_steps(bom_item).select_related(
            'routing__product', 'process', 'line', 'supplier', 'source_bom_item'
        ).order_by('routing_id', 'step_no', 'parallel_group', 'id')

        affected_steps = []
        for step in steps:
            match_type = 'source_bom_item' if step.source_bom_item_id == bom_item.id else 'fallback'
            affected_steps.append({
                'id': step.id,
                'routing_id': step.routing_id,
                'routing_code': getattr(step.routing, 'routing_code', '') if step.routing_id else '',
                'routing_product_code': (
                    getattr(getattr(step.routing, 'product', None), 'product_code', '')
                    if step.routing_id else ''
                ),
                'step_no': step.step_no,
                'parallel_group': step.parallel_group,
                'process_code': getattr(step.process, 'process_code', '') if step.process_id else '',
                'process_name': getattr(step.process, 'process_name', '') if step.process_id else '',
                'line_code': getattr(step.line, 'line_code', '') if step.line_id else '',
                'line_name': getattr(step.line, 'line_name', '') if step.line_id else '',
                'supplier_name': getattr(step.supplier, 'supplier_name', '') if step.supplier_id else '',
                'output_product_code': getattr(step.output_product, 'product_code', '') if step.output_product_id else '',
                'match_type': match_type,
            })

        return {
            'bom_item_id': bom_item.id,
            'child_product_code': getattr(getattr(bom_item, 'child_product', None), 'product_code', ''),
            'child_product_name': getattr(getattr(bom_item, 'child_product', None), 'product_name', ''),
            'affected_steps_count': len(affected_steps),
            'affected_steps': affected_steps,
            'warning_message': (
                'このBOM明細を削除しても、関連ルーティング工程は自動削除されません。'
                ' 下記のルーティングを手動で確認・修正してください。'
                if affected_steps else
                'このBOM明細に紐づくルーティング工程は検出されませんでした。'
            ),
        }

    @action(detail=True, methods=['get'], url_path='delete_preview')
    def delete_preview(self, request, pk=None):
        bom_item = self.get_object()
        return Response(self._build_delete_preview(bom_item))

    def perform_update(self, serializer):
        if 'child_product' in serializer.validated_data:
            child_product = serializer.validated_data['child_product']
            bom_obj = serializer.instance.bom
            parent_product_id = bom_obj.parent_product_id
            child_product_id = child_product.id if hasattr(child_product, 'id') else child_product
            if self._check_circular_bom(parent_product_id, child_product_id):
                child_code = getattr(child_product, 'product_code', child_product_id)
                parent_code = bom_obj.parent_product.product_code
                raise serializers.ValidationError(
                    {'detail': f'{child_code} のBOMツリーに {parent_code} が含まれているため、'
                               f'変更すると循環参照になります。'}
                )

        sync_fields = [
            key for key in (
                'lead_time_days', 'duration_min', 'supplier', 'sourcing_type', 'process', 'line', 'time_unit',
            ) if key in serializer.validated_data
        ]
        item = serializer.save()
        self._normalize_parent_bom_coproduct_flag(item)
        if sync_fields:
            self._sync_item_fields_to_routing(item, sync_fields)

    def _find_active_bom(self, product):
        today = date.today()
        bom = BOM.objects.filter(
            parent_product=product, is_active=True, valid_from__lte=today,
        ).order_by('-valid_from', '-id').first()
        if bom:
            return bom
        return BOM.objects.filter(
            parent_product=product, is_active=True,
        ).order_by('-valid_from', '-id').first()

    def _resolve_step_fields(self, bom_item):
        process = bom_item.process
        line = bom_item.line
        supplier = bom_item.supplier
        time_unit = bom_item.time_unit or 'DAY'
        lead_time_days = int(bom_item.lead_time_days or 0)
        duration_min = bom_item.duration_min

        if bom_item.sourcing_type == 'BUY' and supplier:
            line, process = self._get_or_create_purchase_line_and_process(supplier)
            time_unit = 'DAY'
            lead_time_days = lead_time_days or 1
            duration_min = None
        elif bom_item.sourcing_type == 'SUBCON' and supplier:
            line, process = self._get_supplier_gaisaku_line_and_process(supplier)
            time_unit = 'DAY'
            lead_time_days = lead_time_days or 1
            duration_min = None

        return process, line, supplier, time_unit, lead_time_days, duration_min

    def _calc_next_hierarchy_path(self, routing, parent_path):
        if not parent_path or parent_path == 'final':
            return ''
        prefix = parent_path + '.'
        child_paths = RoutingStep.objects.filter(
            routing=routing, hierarchy_path__startswith=prefix,
        ).values_list('hierarchy_path', flat=True)
        max_idx = 0
        prefix_len = len(prefix)
        for cp in child_paths:
            segment = cp[prefix_len:].split('.')[0]
            try:
                max_idx = max(max_idx, int(segment))
            except (ValueError, IndexError):
                pass
        return f"{parent_path}.{max_idx + 1}"

    def _create_steps_recursive(self, bom_item, parent_step, routing,
                                parent_product_code, visited_bom_ids, collector):
        new_step_no = int(parent_step.step_no * 0.9)
        if new_step_no <= 0:
            raise ValueError(
                f'ルーティング「{routing.routing_code}」(ID:{routing.id}) の'
                f'ステップ「{parent_step.output_product.product_code}」(step_no={parent_step.step_no}) '
                f'の子として追加するとstep_no={new_step_no}になるため追加できません。'
                f'先にこのステップのstep_noを1以上に変更してください。'
            )

        process, line, supplier, time_unit, lt_days, dur_min = self._resolve_step_fields(bom_item)

        max_pg = RoutingStep.objects.filter(routing=routing).aggregate(
            v=Max('parallel_group'))['v'] or 0
        new_pg = max_pg + 1
        new_path = self._calc_next_hierarchy_path(routing, parent_step.hierarchy_path or '')

        new_step = RoutingStep.objects.create(
            routing=routing,
            step_no=new_step_no,
            parallel_group=new_pg,
            process=process,
            line=line,
            supplier=supplier,
            output_product=bom_item.child_product,
            source_bom_item=bom_item,
            hierarchy_depth=parent_step.hierarchy_depth + 1,
            hierarchy_path=new_path,
            time_unit=time_unit,
            lead_time_days=lt_days,
            duration_min=dur_min,
            remark=parent_product_code,
        )
        collector.append((bom_item, new_step))

        child_bom = self._find_active_bom(bom_item.child_product)
        if child_bom and child_bom.id not in visited_bom_ids:
            next_visited = visited_bom_ids | {child_bom.id}
            child_items = BOMItem.objects.filter(bom=child_bom).select_related(
                'child_product', 'process', 'line', 'supplier',
            ).order_by('id')
            child_product_code = bom_item.child_product.product_code
            for ci in child_items:
                self._create_steps_recursive(
                    ci, new_step, routing, child_product_code, next_visited, collector,
                )

    def _add_bom_item_to_routings(self, bom_item: BOMItem):
        """BOMItem追加時に、親製品をoutput_productとする全アクティブルーティングにステップを再帰追加"""
        parent_product = bom_item.bom.parent_product

        parent_steps = RoutingStep.objects.filter(
            output_product=parent_product,
            routing__is_active=True,
        ).select_related('routing')

        if not parent_steps.exists():
            return 0

        created_count = 0
        for parent_step in parent_steps:
            routing = parent_step.routing
            collector = []

            self._create_steps_recursive(
                bom_item, parent_step, routing,
                parent_product.product_code, set(), collector,
            )

            if collector:
                RoutingStepMaterial.objects.get_or_create(
                    routing_step=parent_step,
                    component=bom_item.child_product,
                    defaults={'quantity': bom_item.quantity, 'consume_timing': 'START'},
                )

                for ci, step in collector:
                    child_bom = self._find_active_bom(ci.child_product)
                    if not child_bom:
                        continue
                    for sub in BOMItem.objects.filter(bom=child_bom).select_related('child_product'):
                        RoutingStepMaterial.objects.get_or_create(
                            routing_step=step,
                            component=sub.child_product,
                            defaults={'quantity': sub.quantity, 'consume_timing': 'START'},
                        )

            created_count += len(collector)

        return created_count

    def _check_circular_bom(self, parent_product_id, child_product_id):
        """子製品のBOMツリー（子孫方向）に親製品が含まれていないか検証"""
        if parent_product_id == child_product_id:
            return True
        visited = set()
        queue = [child_product_id]
        while queue:
            pid = queue.pop()
            if pid in visited:
                continue
            visited.add(pid)
            descendant_ids = list(
                BOMItem.objects.filter(
                    bom__parent_product_id=pid, bom__is_active=True,
                ).values_list('child_product_id', flat=True)
            )
            for did in descendant_ids:
                if did == parent_product_id:
                    return True
                queue.append(did)
        return False

    def perform_create(self, serializer):
        bom_id = serializer.validated_data.get('bom')
        child_product = serializer.validated_data.get('child_product')
        bom_obj = bom_id if isinstance(bom_id, BOM) else BOM.objects.select_related('parent_product').get(id=bom_id)
        parent_product_id = bom_obj.parent_product_id
        child_product_id = child_product.id if hasattr(child_product, 'id') else child_product

        if self._check_circular_bom(parent_product_id, child_product_id):
            child_code = getattr(child_product, 'product_code', child_product_id)
            parent_code = bom_obj.parent_product.product_code
            raise serializers.ValidationError(
                {'detail': f'{child_code} のBOMツリーに {parent_code} が含まれているため、'
                           f'追加すると循環参照になります。'}
            )

        item = serializer.save()
        self._normalize_parent_bom_coproduct_flag(item)
        self._created_item = item

    def create(self, request, *args, **kwargs):
        from django.db import transaction
        add_to_routing = request.data.get('add_to_routing', False)
        try:
            with transaction.atomic():
                self._created_item = None
                response = super().create(request, *args, **kwargs)
                if add_to_routing and self._created_item:
                    count = self._add_bom_item_to_routings(self._created_item)
                    response.data['routing_steps_created'] = count
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return response


class RoutingViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = Routing.objects.all().select_related('product')
    serializer_class = RoutingSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['product', 'is_active', 'is_default']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return RoutingListSerializer
        return RoutingSerializer

    def _validate_routing_code_overlap(self, product_id, routing_code, valid_from_datetime, exclude_id=None):
        """同じルーティングコードの期間重複チェック"""
        existing = Routing.objects.filter(
            product_id=product_id, routing_code=routing_code,
        )
        if exclude_id:
            existing = existing.exclude(id=exclude_id)

        for ex in existing:
            if ex.valid_to_datetime is None:
                raise serializers.ValidationError(
                    {'detail': f'ルーティングコード "{routing_code}" の既存ルーティング(ID:{ex.id})に終了日が設定されていません。'
                               f'先に既存ルーティングの終了日を設定してから再実行してください。'}
                )
            if valid_from_datetime and valid_from_datetime <= ex.valid_to_datetime:
                raise serializers.ValidationError(
                    {'detail': f'新しい開始日は既存ルーティング(ID:{ex.id})の終了日 {ex.valid_to_datetime:%Y-%m-%d %H:%M} より後に設定してください。'}
                )

    def _get_overlapping_defaults(self, routing):
        """有効期間が重複する他の既定ルーティングを返す"""
        return get_overlapping_default_routings(routing)

    def perform_create(self, serializer):
        data = serializer.validated_data
        self._validate_routing_code_overlap(
            data['product'].id, data['routing_code'], data.get('valid_from_datetime'),
        )
        routing = serializer.save()
        if routing.is_default:
            self._get_overlapping_defaults(routing).update(is_default=False)

    def perform_update(self, serializer):
        data = serializer.validated_data
        self._validate_routing_code_overlap(
            data.get('product', serializer.instance.product).id,
            data.get('routing_code', serializer.instance.routing_code),
            data.get('valid_from_datetime', serializer.instance.valid_from_datetime),
            exclude_id=serializer.instance.id,
        )
        routing = serializer.save()
        if routing.is_default:
            self._get_overlapping_defaults(routing).update(is_default=False)


class RoutingStepViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = RoutingStep.objects.select_related(
        'routing',
        'process',
        'line',
        'supplier',
        'output_product',
        'source_bom_item',
    ).all()
    serializer_class = RoutingStepSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['routing', 'process', 'line', 'supplier', 'time_unit', 'source_bom_item']
    ordering_fields = ['step_no']
    ordering = ['routing', 'step_no']

    def _get_coproduct_driver_child_ids(self):
        return set(
            BOMItem.objects.filter(
                bom__is_coproduct=True,
                is_coproduct_driver=True,
            ).exclude(
                child_product_id__isnull=True
            ).values_list('child_product_id', flat=True).distinct()
        )

    def _build_representative_child_ids(self, step_list):
        if not step_list:
            return set()

        target_child_ids = {
            int(step.output_product_id)
            for step in step_list
            if getattr(step, 'output_product_id', None)
        }
        if not target_child_ids:
            return set()
        driver_ids = self._get_coproduct_driver_child_ids()
        return {pid for pid in target_child_ids if pid in driver_ids}

    @action(detail=False, methods=['get'], url_path='coproduct-driver-child-products')
    def coproduct_driver_child_products(self, request):
        ids = sorted(self._get_coproduct_driver_child_ids())
        return Response({
            'count': len(ids),
            'child_product_ids': ids,
        })

    def get_serializer_context(self):
        context = super().get_serializer_context()
        representative_child_ids = set()
        routing_id = self.request.query_params.get('routing')
        if routing_id and self.action == 'list':
            step_list = list(self.filter_queryset(self.get_queryset()))
            representative_child_ids = self._build_representative_child_ids(step_list)
        context['representative_child_ids'] = representative_child_ids
        return context

    def _resolve_sync_target_bom(self, step: RoutingStep, prefer_source=True):
        if prefer_source and getattr(step, 'source_bom_item_id', None):
            src = getattr(step, 'source_bom_item', None)
            if src and getattr(src, 'bom_id', None):
                return src.bom

        parent_code = str(getattr(step, 'remark', '') or '').strip()
        if not parent_code:
            return None

        base_qs = BOM.objects.filter(
            parent_product__product_code=parent_code,
            is_active=True,
        )
        if not base_qs.exists():
            return None

        ref_date = None
        routing = getattr(step, 'routing', None)
        if routing and getattr(routing, 'valid_from_datetime', None):
            ref_date = routing.valid_from_datetime.date()

        if ref_date:
            effective_qs = base_qs.filter(
                valid_from__lte=ref_date
            ).filter(
                Q(valid_to__isnull=True) | Q(valid_to__gte=ref_date)
            )
            target = effective_qs.order_by('-valid_from', '-id').first()
            if target:
                return target

        return base_qs.order_by('-valid_from', '-id').first()

    def _select_sync_target_items(self, step: RoutingStep, bom: BOM, prefer_source=True):
        if prefer_source and getattr(step, 'source_bom_item_id', None):
            return BOMItem.objects.filter(id=step.source_bom_item_id)

        is_final_step = str(getattr(step, 'hierarchy_path', '') or '').strip().lower() == 'final'

        if is_final_step:
            base_qs = BOMItem.objects.filter(
                bom_id=bom.id,
                sourcing_type__in=['MAKE', 'SUBCON'],
            )

            exact = base_qs.filter(process_id=step.process_id, line_id=step.line_id)
            if exact.exists():
                return exact

            # finalステップは誤同期を避けるため、process一致を必須にする
            # （line単独一致フォールバックは別工程へ誤反映しやすい）
            if step.process_id:
                process_matched = base_qs.filter(process_id=step.process_id)
                if process_matched.exists():
                    return process_matched

            return base_qs.none()

        qs = BOMItem.objects.filter(
            bom_id=bom.id,
            child_product_id=step.output_product_id,
        )
        if not qs.exists():
            return qs

        exact = qs.filter(process_id=step.process_id, line_id=step.line_id)
        if exact.exists():
            return exact

        if step.process_id:
            process_matched = qs.filter(process_id=step.process_id)
            if process_matched.exists():
                return process_matched

        if step.line_id:
            line_matched = qs.filter(line_id=step.line_id)
            if line_matched.exists():
                return line_matched

        return qs

    def _sync_step_fields_to_bom(self, step: RoutingStep, field_names):
        if not step.output_product_id:
            return

        bom = self._resolve_sync_target_bom(step)
        if not bom:
            return

        items = self._select_sync_target_items(step, bom)
        for item in items:
            changed_fields = []

            if 'lead_time_days' in field_names:
                step_lt = int(getattr(step, 'lead_time_days', 0) or 0)
                item_lt = int(getattr(item, 'lead_time_days', 0) or 0)
                if item_lt != step_lt:
                    item.lead_time_days = step_lt
                    changed_fields.append('lead_time_days')

            if 'duration_min' in field_names and getattr(step, 'time_unit', None) == 'MINUTE':
                step_duration = int(step.duration_min) if step.duration_min is not None else None
                item_duration = int(item.duration_min) if item.duration_min is not None else None
                if item_duration != step_duration:
                    item.duration_min = step_duration
                    changed_fields.append('duration_min')

            if changed_fields:
                item.save(update_fields=changed_fields + ['updated_at'])

    def _parse_usage_quantity_from_request(self):
        if 'usage_quantity' not in self.request.data:
            return None

        raw_value = self.request.data.get('usage_quantity')
        if raw_value is None or str(raw_value).strip() in ('', 'null'):
            return None

        try:
            quantity = Decimal(str(raw_value))
        except (InvalidOperation, TypeError, ValueError):
            raise serializers.ValidationError({'usage_quantity': '使用個数は0以上の整数で入力してください。'})

        if quantity < 0 or quantity != quantity.to_integral_value():
            raise serializers.ValidationError({'usage_quantity': '使用個数は0以上の整数で入力してください。'})
        return quantity

    def _sync_step_usage_quantity(self, step: RoutingStep, usage_quantity: Decimal):
        if not step.output_product_id:
            return

        parent_step_ids = []
        if step.hierarchy_path and '.' in step.hierarchy_path:
            parent_path = step.hierarchy_path.rsplit('.', 1)[0]
            parent_step_ids = list(
                RoutingStep.objects.filter(
                    routing_id=step.routing_id,
                    hierarchy_path=parent_path,
                ).values_list('id', flat=True)
            )

        if not parent_step_ids and step.remark:
            parent_step_ids = list(
                RoutingStep.objects.filter(
                    routing_id=step.routing_id,
                    output_product__product_code=step.remark,
                ).values_list('id', flat=True)
            )

        if parent_step_ids:
            material = RoutingStepMaterial.objects.filter(
                routing_step_id__in=parent_step_ids,
                component_id=step.output_product_id,
            ).order_by('id').first()
            if material:
                if material.quantity != usage_quantity:
                    material.quantity = usage_quantity
                    material.save(update_fields=['quantity', 'updated_at'])
                return

        bom = self._resolve_sync_target_bom(step)
        if not bom:
            return

        items = self._select_sync_target_items(step, bom)
        for item in items:
            if item.quantity != usage_quantity:
                item.quantity = usage_quantity
                item.save(update_fields=['quantity', 'updated_at'])

    def _resolve_step_usage_quantity(self, step: RoutingStep):
        if getattr(step, 'source_bom_item_id', None):
            src = getattr(step, 'source_bom_item', None)
            if src and getattr(src, 'quantity', None) is not None:
                return src.quantity

        parent_step_ids = []
        if step.hierarchy_path and '.' in step.hierarchy_path:
            parent_path = step.hierarchy_path.rsplit('.', 1)[0]
            parent_step_ids = list(
                RoutingStep.objects.filter(
                    routing_id=step.routing_id,
                    hierarchy_path=parent_path,
                ).values_list('id', flat=True)
            )

        if not parent_step_ids and step.remark:
            parent_step_ids = list(
                RoutingStep.objects.filter(
                    routing_id=step.routing_id,
                    output_product__product_code=step.remark,
                ).values_list('id', flat=True)
            )

        if parent_step_ids and step.output_product_id:
            material = RoutingStepMaterial.objects.filter(
                routing_step_id__in=parent_step_ids,
                component_id=step.output_product_id,
            ).order_by('id').first()
            if material and material.quantity is not None:
                return material.quantity

        bom = self._resolve_sync_target_bom(step, prefer_source=False)
        if not bom:
            return None

        item = self._select_sync_target_items(step, bom, prefer_source=False).order_by('id').first()
        if item and item.quantity is not None:
            return item.quantity
        return None

    def _cleanup_old_bom_item(self, old_bom_item_id, new_bom_item_id):
        """旧source_bom_itemが他工程から参照されていなければ削除"""
        if not old_bom_item_id or old_bom_item_id == new_bom_item_id:
            return
        other_refs = RoutingStep.objects.filter(
            source_bom_item_id=old_bom_item_id,
        ).exclude(source_bom_item_id=new_bom_item_id).exists()
        if not other_refs:
            BOMItem.objects.filter(id=old_bom_item_id).delete()

    def _sync_step_bom_linkage(self, step: RoutingStep, usage_quantity: Decimal = None):
        old_bom_item_id = getattr(step, 'source_bom_item_id', None)

        if not step.output_product_id or not step.remark:
            if old_bom_item_id:
                step.source_bom_item = None
                step.save(update_fields=['source_bom_item', 'updated_at'])
                self._cleanup_old_bom_item(old_bom_item_id, None)
            return

        bom = self._resolve_sync_target_bom(step, prefer_source=False)
        if not bom:
            if old_bom_item_id:
                step.source_bom_item = None
                step.save(update_fields=['source_bom_item', 'updated_at'])
                self._cleanup_old_bom_item(old_bom_item_id, None)
            return

        # 子と親が同じ製品の場合（中間工程）はBOM明細を作らない
        if step.output_product_id == bom.parent_product_id:
            if old_bom_item_id:
                step.source_bom_item = None
                step.save(update_fields=['source_bom_item', 'updated_at'])
                self._cleanup_old_bom_item(old_bom_item_id, None)
            return

        qty = usage_quantity if usage_quantity is not None else self._resolve_step_usage_quantity(step)
        if qty is None:
            qty = Decimal('1')

        raw_sourcing = str(self.request.data.get('sourcing_type') or '').upper()
        sourcing_type = raw_sourcing if raw_sourcing in ('MAKE', 'BUY', 'SUBCON') else ('SUBCON' if step.supplier_id else 'MAKE')

        existing_item = BOMItem.objects.filter(
            bom=bom,
            child_product_id=step.output_product_id,
        ).order_by('id').first()

        if existing_item:
            existing_item.quantity = qty
            existing_item.process_id = step.process_id
            existing_item.line_id = step.line_id
            existing_item.supplier_id = step.supplier_id
            existing_item.sourcing_type = sourcing_type
            existing_item.time_unit = step.time_unit or 'DAY'
            existing_item.lead_time_days = step.lead_time_days or 0
            existing_item.duration_min = step.duration_min
            existing_item.save()
            if step.source_bom_item_id != existing_item.id:
                step.source_bom_item = existing_item
                step.save(update_fields=['source_bom_item', 'updated_at'])
                self._cleanup_old_bom_item(old_bom_item_id, existing_item.id)
            return

        new_item = BOMItem.objects.create(
            bom=bom,
            child_product_id=step.output_product_id,
            quantity=qty,
            sourcing_type=sourcing_type,
            process_id=step.process_id,
            line_id=step.line_id,
            supplier_id=step.supplier_id,
            time_unit=step.time_unit or 'DAY',
            lead_time_days=step.lead_time_days or 0,
            duration_min=step.duration_min,
        )
        step.source_bom_item = new_item
        step.save(update_fields=['source_bom_item', 'updated_at'])
        self._cleanup_old_bom_item(old_bom_item_id, new_item.id)

    def _normalize_final_step_flags(self, routing_id):
        if not routing_id:
            return

        step_list = list(
            RoutingStep.objects.filter(routing_id=routing_id)
            .select_related('routing')
            .order_by('step_no', 'parallel_group', 'id')
        )
        if not step_list:
            return

        routing_product_id = None
        sample_routing = getattr(step_list[0], 'routing', None)
        if sample_routing:
            routing_product_id = getattr(sample_routing, 'product_id', None)
        if not routing_product_id:
            return

        final_candidates = [
            step for step in step_list
            if step.output_product_id == routing_product_id
        ]
        if not final_candidates:
            return

        final_step_id = final_candidates[-1].id
        for step in final_candidates:
            raw_path = str(step.hierarchy_path or '').strip()
            changed_fields = []

            if step.id == final_step_id:
                if raw_path != 'final':
                    # 子工程の階層パスから旧パスの接頭辞を除去
                    if raw_path:
                        old_prefix = raw_path + '.'
                        for sibling in step_list:
                            sib_path = str(sibling.hierarchy_path or '').strip()
                            if sib_path.startswith(old_prefix):
                                sibling.hierarchy_path = sib_path[len(old_prefix):]
                                sibling.save(update_fields=['hierarchy_path', 'updated_at'])
                    step.hierarchy_path = 'final'
                    changed_fields.append('hierarchy_path')
                if int(getattr(step, 'hierarchy_depth', 0) or 0) != 0:
                    step.hierarchy_depth = 0
                    changed_fields.append('hierarchy_depth')
            else:
                # 非final中間工程: 'final'が付いていたら除去、それ以外は手動設定を維持
                if raw_path == 'final':
                    step.hierarchy_path = ''
                    changed_fields.append('hierarchy_path')

            if changed_fields:
                step.save(update_fields=changed_fields + ['updated_at'])

    def perform_update(self, serializer):
        usage_quantity = self._parse_usage_quantity_from_request()
        sync_fields = [key for key in ('lead_time_days', 'duration_min') if key in serializer.validated_data]
        step = serializer.save()
        self._normalize_final_step_flags(step.routing_id)
        if any(key in serializer.validated_data for key in ('output_product', 'remark')):
            self._sync_step_bom_linkage(step, usage_quantity)
        if sync_fields:
            self._sync_step_fields_to_bom(step, sync_fields)
        if usage_quantity is not None:
            self._sync_step_usage_quantity(step, usage_quantity)

    def perform_create(self, serializer):
        usage_quantity = self._parse_usage_quantity_from_request()
        step = serializer.save()
        self._normalize_final_step_flags(step.routing_id)

        # BOMItem自動作成/更新: 親製品(remark)と加工後品目(output_product)が指定されている場合
        if step.output_product_id and step.remark:
            self._sync_step_bom_linkage(step, usage_quantity)
            return

        # BOM自動作成が不要な場合は既存のLT/所要時間同期のみ
        sync_fields = [key for key in ('lead_time_days', 'duration_min') if key in serializer.validated_data]
        if sync_fields:
            self._sync_step_fields_to_bom(step, sync_fields)


class RoutingStepMaterialViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = RoutingStepMaterial.objects.all().select_related('routing_step', 'component')
    serializer_class = RoutingStepMaterialSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['routing_step', 'component', 'consume_timing']
    search_fields = ['component__product_code', 'component__product_name']
    ordering_fields = ['routing_step', 'component']
    ordering = ['routing_step', 'component']

    def get_queryset(self):
        qs = super().get_queryset()
        routing_id = self.request.query_params.get('routing')
        if routing_id:
            qs = qs.filter(routing_step__routing_id=routing_id)
        return qs


class ContactFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Contact
        fields = ['contact_type', 'is_active']

    def filter_search(self, queryset, name, value):
        if value:
            return queryset.filter(
                Q(company_name__icontains=value) |
                Q(contact_person__icontains=value) |
                Q(department__icontains=value)
            )
        return queryset


class ContactViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ContactFilter
    search_fields = ['company_name', 'contact_person', 'email']
    ordering_fields = ['display_order', 'created_at']
    ordering = ['display_order', 'id']


# ---- 携帯端末管理 ----

class MobileDeviceFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    device_type = django_filters.CharFilter(field_name='device_type')
    manager_name = django_filters.CharFilter(field_name='manager_name', lookup_expr='icontains')

    class Meta:
        model = MobileDevice
        fields = ['status', 'device_type', 'manager_name']


class MobileDeviceViewSet(viewsets.ModelViewSet):
    queryset = MobileDevice.objects.all()
    serializer_class = MobileDeviceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MobileDeviceFilter
    search_fields = ['management_no', 'manufacturer', 'model_number', 'serial_number', 'location', 'manager_name']
    ordering_fields = ['management_no', 'created_at']
    ordering = ['-management_no']

    @action(detail=False, methods=['post'], parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def import_excel(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'ファイルが必要です'}, status=status.HTTP_400_BAD_REQUEST)
        from openpyxl import load_workbook
        wb = load_workbook(file, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(min_row=2, values_only=True))
        created = 0
        updated = 0
        for row in rows:
            mgmt_no = str(row[0] or '').strip()
            if not mgmt_no:
                continue
            device_type = MobileDevice.TYPE_TABLET if mgmt_no.endswith('T') else MobileDevice.TYPE_SMARTPHONE
            defaults = {
                'device_type': device_type,
                'manufacturer': str(row[1] or '').strip(),
                'model_number': str(row[2] or '').strip(),
                'serial_number': str(row[3] or '').strip(),
                'purchase_date': str(row[4] or '').strip(),
                'location': str(row[5] or '').strip(),
                'manager_name': str(row[6] or '').strip(),
                'note': str(row[9] or '').strip() if len(row) > 9 else '',
            }
            _, is_created = MobileDevice.objects.update_or_create(
                management_no=mgmt_no, defaults=defaults
            )
            if is_created:
                created += 1
            else:
                updated += 1
        return Response({'created': created, 'updated': updated})

    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        from openpyxl import Workbook
        from django.http import HttpResponse
        wb = Workbook()
        ws = wb.active
        ws.title = '台帳'
        headers = ['管理№', '製造元', '型番', 'S/N', '導入年月', '配置場所', '管理責任者', '遊休化年月', '管理除外年月', '備考']
        ws.append(headers)
        for d in MobileDevice.objects.all().order_by('-management_no'):
            ws.append([
                d.management_no, d.manufacturer, d.model_number, d.serial_number,
                d.purchase_date, d.location, d.manager_name,
                str(d.idle_date) if d.idle_date else '',
                str(d.disposed_date) if d.disposed_date else '',
                d.note,
            ])
        resp = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition'] = 'attachment; filename="mobile_devices.xlsx"'
        wb.save(resp)
        return resp

    @action(detail=False, methods=['get'])
    def print_labels(self, request):
        ids = request.query_params.get('ids', '')
        if ids:
            id_list = [int(x) for x in ids.split(',') if x.strip().isdigit()]
            devices = MobileDevice.objects.filter(id__in=id_list).order_by('management_no')
        else:
            devices = MobileDevice.objects.filter(status=MobileDevice.STATUS_ACTIVE).order_by('management_no')

        from django.http import HttpResponse
        buf = StringIO()
        writer = csv.writer(buf)
        for dev in devices:
            purchase = str(dev.purchase_date or '')
            writer.writerow([dev.management_no, dev.manufacturer, f"'{purchase}" if purchase else '', dev.location, dev.manager_name])
        resp = HttpResponse(buf.getvalue().encode('cp932'), content_type='text/csv; charset=shift_jis')
        resp['Content-Disposition'] = 'attachment; filename="tepra_labels.csv"'
        return resp

    @action(detail=False, methods=['get'])
    def inventory_checklist(self, request):
        from io import BytesIO
        from django.http import HttpResponse
        from reportlab.lib.units import mm
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.pdfgen import canvas as pdf_canvas
        from apps.shipping.services.shipping_pdf_generator import register_japanese_fonts

        register_japanese_fonts()

        devices = list(
            MobileDevice.objects.exclude(status=MobileDevice.STATUS_DISPOSED)
            .order_by('management_no')
        )

        buf = BytesIO()
        page_w, page_h = landscape(A4)
        c = pdf_canvas.Canvas(buf, pagesize=landscape(A4))

        margin_x = 12 * mm
        margin_y = 12 * mm
        row_h = 8 * mm
        header_h = 8 * mm
        title_h = 18 * mm

        check_cols = ['現物', 'ラベル', '管理No.', '配置場所', '動作']
        data_cols = [
            ('管理No.', 22 * mm),
            ('種別', 16 * mm),
            ('製造元', 22 * mm),
            ('型番', 22 * mm),
            ('配置場所', 35 * mm),
            ('管理責任者', 20 * mm),
        ]
        check_w = 14 * mm
        note_w = 30 * mm
        result_w = 14 * mm

        data_total = sum(w for _, w in data_cols)
        table_w = data_total + len(check_cols) * check_w + result_w + note_w

        usable_h = page_h - margin_y * 2 - title_h - header_h
        rows_per_page = int(usable_h / row_h)

        today_str = date.today().strftime('%Y/%m/%d')

        def draw_page(page_devices, page_num, total_pages):
            top_y = page_h - margin_y

            c.setFont('MSGothic', 14)
            c.drawString(margin_x, top_y - 10 * mm, '携帯端末 棚卸チェックシート')
            c.setFont('MSGothic', 8)
            c.drawString(margin_x + 160 * mm, top_y - 5 * mm, f'棚卸日:                    確認者:')
            c.drawString(margin_x + 160 * mm, top_y - 11 * mm, f'出力日: {today_str}    {page_num}/{total_pages}頁')

            y = top_y - title_h

            c.setFont('MSGothic', 6.5)
            c.setFillColorRGB(0.95, 0.95, 0.95)
            c.rect(margin_x, y - header_h, table_w, header_h, fill=1)
            c.setFillColorRGB(0, 0, 0)

            x = margin_x
            for label, w in data_cols:
                c.drawString(x + 1.5 * mm, y - header_h + 2.5 * mm, label)
                x += w
            for ck in check_cols:
                c.drawString(x + 1 * mm, y - header_h + 2.5 * mm, ck)
                x += check_w
            c.drawString(x + 1 * mm, y - header_h + 2.5 * mm, '結果')
            x += result_w
            c.drawString(x + 1 * mm, y - header_h + 2.5 * mm, '備考')

            c.setStrokeColorRGB(0.6, 0.6, 0.6)
            c.rect(margin_x, y - header_h, table_w, header_h)
            x = margin_x
            for _, w in data_cols:
                x += w
                c.line(x, y, x, y - header_h)
            for _ in check_cols:
                x += check_w
                c.line(x, y, x, y - header_h)
            x += result_w
            c.line(x, y, x, y - header_h)

            y -= header_h

            c.setFont('MSGothic', 6.5)
            for dev in page_devices:
                c.setStrokeColorRGB(0.7, 0.7, 0.7)
                c.rect(margin_x, y - row_h, table_w, row_h)

                x = margin_x
                type_label = 'タブレット' if dev.device_type == MobileDevice.TYPE_TABLET else 'スマホ'
                vals = [dev.management_no, type_label, dev.manufacturer, dev.model_number, dev.location, dev.manager_name]
                for i, (_, w) in enumerate(data_cols):
                    text = str(vals[i] or '')
                    max_chars = int(w / (2.2 * mm))
                    if len(text) > max_chars:
                        text = text[:max_chars - 1] + '…'
                    c.drawString(x + 1.5 * mm, y - row_h + 2.5 * mm, text)
                    c.line(x + w, y, x + w, y - row_h)
                    x += w

                for _ in check_cols:
                    c.rect(x + 4 * mm, y - row_h + 2 * mm, 4 * mm, 4 * mm)
                    c.line(x + check_w, y, x + check_w, y - row_h)
                    x += check_w

                c.line(x + result_w, y, x + result_w, y - row_h)

                y -= row_h

        total_pages = max(1, (len(devices) + rows_per_page - 1) // rows_per_page)
        for p in range(total_pages):
            if p > 0:
                c.showPage()
            start = p * rows_per_page
            end = start + rows_per_page
            draw_page(devices[start:end], p + 1, total_pages)

        c.save()
        buf.seek(0)
        resp = HttpResponse(buf.read(), content_type='application/pdf')
        resp['Content-Disposition'] = 'inline; filename="device_inventory_checklist.pdf"'
        return resp


class ManualDocumentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='read')
    def read_doc(self, request):
        doc_key = request.query_params.get('path', '')
        if not doc_key:
            return Response({'detail': 'path required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            doc = ManualDocument.objects.get(doc_key=doc_key)
        except ManualDocument.DoesNotExist:
            return Response({'detail': 'not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'path': doc_key, 'content': doc.content})

    @action(detail=False, methods=['post'], url_path='write')
    def write_doc(self, request):
        doc_key = request.data.get('path', '')
        content = request.data.get('content', '')
        if not doc_key:
            return Response({'detail': 'path required'}, status=status.HTTP_400_BAD_REQUEST)
        doc, _ = ManualDocument.objects.update_or_create(
            doc_key=doc_key,
            defaults={'content': content, 'updated_by': request.user},
        )
        return Response({'path': doc_key, 'saved': True})


class MobileDeviceInventoryFilter(django_filters.FilterSet):
    device = django_filters.NumberFilter(field_name='device_id')
    inventory_date = django_filters.DateFilter(field_name='inventory_date')
    result = django_filters.CharFilter(field_name='result')

    class Meta:
        model = MobileDeviceInventory
        fields = ['device', 'inventory_date', 'result']


class MobileDeviceInventoryViewSet(viewsets.ModelViewSet):
    queryset = MobileDeviceInventory.objects.select_related('device', 'checked_by', 'approved_by').all()
    serializer_class = MobileDeviceInventorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = MobileDeviceInventoryFilter
    ordering = ['-inventory_date', 'device__management_no']
