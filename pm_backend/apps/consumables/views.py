from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath

from django.db import transaction
from django.db.models import F, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import HasResourcePermissionOrReadOnly

from .models import Consumable, ConsumableSupplier
from .serializers import ConsumableSerializer, ConsumableSupplierSerializer
from .services import (
    CONSUMABLE_CSV_ALIASES,
    SUPPLIER_CSV_ALIASES,
    open_request_status_map,
    read_csv_rows,
)


def _to_int(value, default=0):
    if value in (None, ''):
        return default
    try:
        return int(Decimal(str(value).replace(',', '')))
    except (InvalidOperation, ValueError):
        raise ValueError(f'数値ではありません: {value}')


def _to_decimal(value, default=Decimal('0')):
    if value in (None, ''):
        return default
    try:
        return Decimal(str(value).replace(',', ''))
    except InvalidOperation:
        raise ValueError(f'数値ではありません: {value}')


class ConsumableSupplierViewSet(viewsets.ModelViewSet):
    queryset = ConsumableSupplier.objects.all()
    serializer_class = ConsumableSupplierSerializer
    permission_classes = [IsAuthenticated, HasResourcePermissionOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'contact_person', 'email']
    ordering = ['name']

    def destroy(self, request, *args, **kwargs):
        supplier = self.get_object()
        if supplier.dispatch_orders.exists():
            return Response(
                {'detail': '注文書で使用中の購入先は削除できません。無効にしてください。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path='import-csv',
            parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def import_csv(self, request):
        """購入先CSV取込。購入先名が一致すれば更新、なければ追加する"""
        upload = request.FILES.get('file')
        if not upload:
            return Response({'detail': 'ファイルが必要です'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            rows = read_csv_rows(upload, SUPPLIER_CSV_ALIASES)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        created = updated = 0
        errors = []
        with transaction.atomic():
            for line_no, row in enumerate(rows, start=2):
                name = row.pop('name', '')
                if not name:
                    errors.append(f'{line_no}行目: 購入先名が空です')
                    continue
                _, is_created = ConsumableSupplier.objects.update_or_create(name=name, defaults=row)
                if is_created:
                    created += 1
                else:
                    updated += 1
        return Response({'created': created, 'updated': updated, 'errors': errors})


class ConsumableViewSet(viewsets.ModelViewSet):
    queryset = Consumable.objects.select_related('supplier')
    serializer_class = ConsumableSerializer
    permission_classes = [IsAuthenticated, HasResourcePermissionOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'supplier', 'category', 'storage_location']
    search_fields = ['code', 'order_code', 'name']
    ordering_fields = ['code', 'name', 'stock_quantity', 'updated_at']
    ordering = ['code']

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if params.get('shortage') == '1':
            qs = qs.filter(stock_quantity__lte=F('safety_stock'))
        order_status = params.get('order_status')
        if order_status:
            open_ids = open_request_status_map()
            if order_status == 'none':
                qs = qs.exclude(id__in=list(open_ids.keys()))
            else:
                qs = qs.filter(id__in=[cid for cid, st in open_ids.items() if st == order_status])
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == 'list':
            # 一覧の注文状態は1クエリでまとめて導出する
            context['order_status_map'] = open_request_status_map()
        return context

    def destroy(self, request, *args, **kwargs):
        consumable = self.get_object()
        if consumable.requests.exists() or consumable.movements.exists():
            return Response(
                {'detail': '依頼・入出庫履歴のある消耗品は削除できません。無効にしてください。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='by-code/(?P<code>[^/]+)')
    def by_code(self, request, code=None):
        """QR読取用: コード（または発注コード）で1件取得"""
        consumable = (
            self.get_queryset().filter(Q(code=code) | Q(order_code=code)).order_by('-is_active', 'id').first()
        )
        if not consumable:
            return Response({'detail': f'コード {code} の消耗品が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(consumable).data)

    @action(detail=False, methods=['get'], url_path='filter-options')
    def filter_options(self, request):
        base = Consumable.objects.filter(is_active=True)
        return Response({
            'categories': sorted({c for c in base.values_list('category', flat=True) if c}),
            'storage_locations': sorted({s for s in base.values_list('storage_location', flat=True) if s}),
        })

    @action(detail=True, methods=['post'], url_path='upload-image',
            parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def upload_image(self, request, pk=None):
        consumable = self.get_object()
        image = request.FILES.get('image')
        if not image:
            return Response({'detail': '画像ファイルが必要です'}, status=status.HTTP_400_BAD_REQUEST)
        consumable.image = image
        consumable.save(update_fields=['image', 'updated_at'])
        return Response(self.get_serializer(consumable).data)

    @action(detail=False, methods=['post'], url_path='import-csv',
            parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def import_csv(self, request):
        """
        消耗品CSV取込。コードが一致すれば更新、なければ追加する。
        - 購入先は購入先名で紐付ける（先に購入先CSVを取り込むこと）
        - 在庫数は新規追加時のみ設定する（既存品の在庫は入出庫以外で変えない）
        - 画像はファイル名を media/consumables/images/ 配下として紐付ける（ファイルは事前にコピー）
        """
        upload = request.FILES.get('file')
        if not upload:
            return Response({'detail': 'ファイルが必要です'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            rows = read_csv_rows(upload, CONSUMABLE_CSV_ALIASES)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        suppliers = {s.name: s for s in ConsumableSupplier.objects.all()}
        created = updated = 0
        errors = []
        with transaction.atomic():
            for line_no, row in enumerate(rows, start=2):
                code = row.get('code', '')
                name = row.get('name', '')
                if not code or not name:
                    errors.append(f'{line_no}行目: コードと品名は必須です')
                    continue

                supplier = None
                supplier_name = row.get('supplier_name', '')
                if supplier_name:
                    supplier = suppliers.get(supplier_name)
                    if supplier is None:
                        errors.append(f'{line_no}行目: 購入先「{supplier_name}」が未登録です')
                        continue

                try:
                    defaults = {
                        'name': name,
                        'order_code': row.get('order_code', ''),
                        'category': row.get('category', ''),
                        'unit': row.get('unit', ''),
                        'storage_location': row.get('storage_location', ''),
                        'safety_stock': _to_int(row.get('safety_stock')),
                        'order_unit': max(_to_int(row.get('order_unit'), 1), 1),
                        'unit_price': _to_decimal(row.get('unit_price')),
                        'supplier': supplier,
                        'note': row.get('note', ''),
                    }
                    stock_quantity = _to_int(row.get('stock_quantity'))
                except ValueError as exc:
                    errors.append(f'{line_no}行目: {exc}')
                    continue

                image_file = row.get('image_file', '')
                if image_file:
                    defaults['image'] = f'consumables/images/{PurePosixPath(image_file.replace(chr(92), "/")).name}'

                consumable = Consumable.objects.filter(code=code).first()
                if consumable:
                    for field, value in defaults.items():
                        setattr(consumable, field, value)
                    consumable.save()
                    updated += 1
                else:
                    Consumable.objects.create(code=code, stock_quantity=stock_quantity, **defaults)
                    created += 1
        return Response({'created': created, 'updated': updated, 'errors': errors})
