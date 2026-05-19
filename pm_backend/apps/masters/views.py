from rest_framework import viewsets, status, parsers, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Exists, OuterRef, Q
from django.core.files.storage import default_storage
import django_filters
import os
import uuid
import csv
from io import StringIO
from decimal import Decimal, InvalidOperation
from datetime import date, datetime, timedelta
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.datavalidation import DataValidation
from .models import (
    Product, Customer, Process, Line, Supplier, Calendar, CalendarDay, WorkPattern, BreakTime,
    BOM, BOMItem, Routing, RoutingStep, RoutingStepMaterial, ProductGroup, ContainerCapacity, Equipment, Contact,
    KubotaSakaiTruck, MobileDevice, MobileDeviceInventory
)
from .serializers import (
    ProductSerializer, CustomerSerializer, ProcessSerializer, LineSerializer,
    SupplierSerializer, CalendarSerializer, CalendarDaySerializer, WorkPatternSerializer, BreakTimeSerializer,
    BOMSerializer, BOMItemSerializer, RoutingSerializer, RoutingListSerializer, RoutingStepSerializer,
    RoutingStepMaterialSerializer, ProductGroupSerializer, ContainerCapacitySerializer, EquipmentSerializer, ContactSerializer,
    KubotaSakaiTruckSerializer, MobileDeviceSerializer, MobileDeviceInventorySerializer
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

    def filter_next_process_unset(self, queryset, name, value):
        if value is None:
            return queryset
        if value:
            return queryset.filter(next_process__isnull=True)
        return queryset.filter(next_process__isnull=False)


class ProductViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['product_code', 'product_name']
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


class ProductGroupViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = ProductGroup.objects.all()
    serializer_class = ProductGroupSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['group_code', 'group_name']
    ordering_fields = ['group_code', 'created_at']
    ordering = ['group_code']


class ContainerCapacityViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = ContainerCapacity.objects.all()
    serializer_class = ContainerCapacitySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'container_code']
    ordering_fields = ['name', 'capacity']
    ordering = ['name']


class EquipmentViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = Equipment.objects.all().select_related('line', 'process')
    serializer_class = EquipmentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'line', 'process']
    search_fields = ['equipment_code', 'equipment_name', 'line__line_code', 'line__line_name', 'process__process_code', 'process__process_name']
    ordering_fields = ['display_order', 'equipment_code', 'created_at']
    ordering = ['display_order', 'equipment_code']


class KubotaSakaiTruckViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = KubotaSakaiTruck.objects.all()
    serializer_class = KubotaSakaiTruckSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'default_use']
    search_fields = ['name', 'alias_name']
    ordering_fields = ['display_order', 'name', 'departure_time']
    ordering = ['display_order', 'name']


class CustomerViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    filterset_fields = ['is_active']
    search_fields = ['customer_code', 'customer_name']
    ordering_fields = ['customer_code', 'created_at']
    ordering = ['customer_code']


class ProcessViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = Process.objects.all()
    serializer_class = ProcessSerializer
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

        for step in routing_steps:
            routing = step.routing
            if not routing or not routing.product:
                continue

            # 1-0. この工程の出力品目（中間品）を追加
            output_product = step.output_product
            if output_product and output_product.id not in products_map:
                products_map[output_product.id] = {
                    'product': output_product,
                    'relation_type': 'output_product',
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
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'line_type']
    search_fields = ['line_code', 'line_name']
    ordering_fields = ['line_code', 'created_at']
    ordering = ['line_code']


class ProductionLineViewSet(viewsets.ReadOnlyModelViewSet):
    """生産ライン一覧（読み取り専用）。生産計画など他機能からも参照されるため認証のみで許可"""
    queryset = Line.objects.filter(line_type='PROD')
    serializer_class = LineSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active']
    search_fields = ['line_code', 'line_name']
    ordering_fields = ['line_code', 'created_at']
    ordering = ['line_code']


class SupplierViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    search_fields = ['supplier_code', 'supplier_name', 'order_email']
    ordering_fields = ['supplier_code']
    ordering = ['supplier_code']


class CalendarViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = Calendar.objects.all()
    serializer_class = CalendarSerializer
    search_fields = ['calendar_code', 'calendar_name']
    ordering_fields = ['calendar_code', 'created_at']
    ordering = ['calendar_code']

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
    filterset_fields = ['calendar', 'is_working_day']
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
    queryset = BOM.objects.all()
    serializer_class = BOMSerializer
    filterset_fields = ['parent_product', 'is_active']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()

        # デバッグログ
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"BOM Filter Params: {dict(self.request.query_params)}")

        # 親製品（品番/品名）検索
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(parent_product__product_code__icontains=search) |
                Q(parent_product__product_name__icontains=search)
            )

        # 最終品フィルタ（親製品のis_final_productフィールドで絞り込み）
        is_final = self.request.query_params.get('parent_is_final', None)
        if is_final is not None and is_final != '':
            is_final_bool = is_final.lower() == 'true'
            queryset = queryset.filter(parent_product__is_final_product=is_final_bool)

        # ライン最終品フィルタ（親製品のis_line_final_productフィールドで絞り込み）
        is_line_final = self.request.query_params.get('parent_is_line_final', None)
        if is_line_final is not None and is_line_final != '':
            is_line_final_bool = is_line_final.lower() == 'true'
            queryset = queryset.filter(parent_product__is_line_final_product=is_line_final_bool)

        # 連産品フィルタ
        is_coproduct = self.request.query_params.get('is_coproduct', None)
        if is_coproduct is not None and is_coproduct != '':
            is_coproduct_bool = is_coproduct.lower() == 'true'
            queryset = queryset.filter(is_coproduct=is_coproduct_bool)

        # 版フィルタ
        version = self.request.query_params.get('version', None)
        if version:
            queryset = queryset.filter(version__icontains=version)

        # 作成日フィルタ（From）
        created_from = self.request.query_params.get('created_from', None)
        if created_from:
            logger.info(f"Filtering by created_from: {created_from}")
            from datetime import datetime
            created_from_dt = datetime.strptime(created_from, '%Y-%m-%d')
            queryset = queryset.filter(created_at__gte=created_from_dt)

        # 作成日フィルタ（To）
        created_to = self.request.query_params.get('created_to', None)
        if created_to:
            logger.info(f"Filtering by created_to: {created_to}")
            from datetime import datetime, timedelta
            created_to_dt = datetime.strptime(created_to, '%Y-%m-%d')
            # その日の23:59:59まで含めるため、翌日の00:00:00未満とする
            created_to_dt = created_to_dt + timedelta(days=1)
            queryset = queryset.filter(created_at__lt=created_to_dt)

        logger.info(f"Final queryset count: {queryset.count()}")
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
                    walk_bom(child_bom, parent_prefix=child_prefix, level=level + 1, visited=visited, cumulative_lt=item_cumulative_lt)

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
        for p in Process.objects.select_related('line').order_by('process_code'):
            ws_process.append([
                p.process_code,
                p.process_name,
                p.line.line_code if p.line else '',
                p.line.line_name if p.line else '',
                '有効' if p.is_active else '無効',
            ])

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
        line_code = supplier.supplier_code
        line_name = f"仕入:{supplier.supplier_code} {supplier.supplier_name}"
        if len(line_name) > 50:
            line_name = line_name[:50]
        line_obj, _ = Line.objects.get_or_create(
            line_code=line_code,
            defaults={
                'line_name': line_name,
                'line_type': 'PURCHASE',
                'is_active': True,
            }
        )

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
        line_code = supplier.supplier_code
        line_name = f"仕入:{supplier.supplier_code} {supplier.supplier_name}"
        if len(line_name) > 50:
            line_name = line_name[:50]
        line_obj, _ = Line.objects.get_or_create(
            line_code=line_code,
            defaults={
                'line_name': line_name,
                'line_type': 'PURCHASE',
                'is_active': True,
            }
        )

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
        filename = f"bom_tree_{product_code}.xlsx"

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response


class BOMItemViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = BOMItem.objects.all()
    serializer_class = BOMItemSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['bom', 'child_product', 'sourcing_type', 'process', 'line', 'time_unit', 'supplier']
    ordering_fields = ['created_at']
    ordering = ['id']

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

    def perform_update(self, serializer):
        sync_fields = [key for key in ('lead_time_days', 'duration_min') if key in serializer.validated_data]
        item = serializer.save()
        if sync_fields:
            self._sync_item_fields_to_routing(item, sync_fields)


class RoutingViewSet(MastersPermissionMixin, viewsets.ModelViewSet):
    queryset = Routing.objects.all().select_related('product')
    serializer_class = RoutingSerializer
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

    def _resolve_sync_target_bom(self, step: RoutingStep):
        if getattr(step, 'source_bom_item_id', None):
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

    def _select_sync_target_items(self, step: RoutingStep, bom: BOM):
        if getattr(step, 'source_bom_item_id', None):
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

    def perform_update(self, serializer):
        sync_fields = [key for key in ('lead_time_days', 'duration_min') if key in serializer.validated_data]
        step = serializer.save()
        if sync_fields:
            self._sync_step_fields_to_bom(step, sync_fields)

    def perform_create(self, serializer):
        # 新規工程作成時もBOMItem側に値を伝播し、後続編集で発生しがちなBOM/Routingのズレを防ぐ
        step = serializer.save()
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

    MANUAL_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        'pm-ui', 'public', 'manual'
    )

    def _resolve_path(self, doc_path):
        from pathlib import Path
        safe = Path(self.MANUAL_DIR).joinpath(doc_path).resolve()
        if not str(safe).startswith(str(Path(self.MANUAL_DIR).resolve())):
            return None
        return safe

    @action(detail=False, methods=['get'], url_path='read')
    def read_doc(self, request):
        doc_path = request.query_params.get('path', '')
        if not doc_path:
            return Response({'detail': 'path required'}, status=status.HTTP_400_BAD_REQUEST)
        fpath = self._resolve_path(doc_path)
        if not fpath or not fpath.exists():
            return Response({'detail': 'not found'}, status=status.HTTP_404_NOT_FOUND)
        content = fpath.read_text(encoding='utf-8')
        return Response({'path': doc_path, 'content': content})

    @action(detail=False, methods=['post'], url_path='write')
    def write_doc(self, request):
        doc_path = request.data.get('path', '')
        content = request.data.get('content', '')
        if not doc_path:
            return Response({'detail': 'path required'}, status=status.HTTP_400_BAD_REQUEST)
        fpath = self._resolve_path(doc_path)
        if not fpath:
            return Response({'detail': 'invalid path'}, status=status.HTTP_400_BAD_REQUEST)
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content, encoding='utf-8')
        return Response({'path': doc_path, 'saved': True})


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
