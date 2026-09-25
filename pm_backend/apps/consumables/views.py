import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath

from django.db import transaction
from django.contrib.auth import get_user_model
from django.db.models import Count, F, Sum, Value, Window
from django.db.models.functions import Replace, RowNumber
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import HasResourcePermissionOrReadOnly

from .models import Consumable, ConsumableRequest, ConsumableStockMovement, ConsumableSupplier
from .serializers import (
    ConsumableSerializer,
    ConsumableStockMovementSerializer,
    ConsumableSupplierSerializer,
)
from .services import (
    CONSUMABLE_CSV_ALIASES,
    SUPPLIER_CSV_ALIASES,
    business_day_range,
    display_user_name,
    normalize_qr_code_value,
    open_request_status_map,
    org_snapshot,
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
        if self.action in ('list', 'cards'):
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

    @action(detail=False, methods=['get'])
    def lookup(self, request):
        """
        QR読取用: QR文字列（?qr=）から消耗品を1件特定する。照合順は syomohin と同じ。
        1. コード完全一致（大文字小文字無視） 2. ハイフン・空白を除いて一致 3. 前方一致
        """
        code = normalize_qr_code_value(request.query_params.get('qr', ''))
        if not code:
            return Response({'detail': 'QRコードが空です'}, status=status.HTTP_400_BAD_REQUEST)

        qs = Consumable.objects.select_related('supplier').filter(is_active=True)
        consumable = qs.filter(code__iexact=code).first()
        if consumable is None:
            compact = re.sub(r'[-\s]', '', code)
            consumable = (
                qs.annotate(compact_code=Replace(Replace('code', Value('-'), Value('')), Value(' '), Value('')))
                .filter(compact_code__iexact=compact)
                .first()
            )
        if consumable is None:
            consumable = qs.filter(code__istartswith=code).order_by('code').first()
        if consumable is None:
            return Response({'detail': f'コード「{code}」の消耗品が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(consumable).data)

    @action(detail=False, methods=['get'])
    def cards(self, request):
        """在庫一覧（カード）用: 消耗品に未完了の依頼と直近2件の入庫を付けて返す"""
        items = list(self.filter_queryset(self.get_queryset()))
        ids = [item.id for item in items]
        data = self.get_serializer(items, many=True).data

        open_requests = {}
        for req in ConsumableRequest.objects.filter(
            consumable_id__in=ids, status__in=ConsumableRequest.OPEN_STATUSES
        ).order_by('-requested_at'):
            open_requests.setdefault(req.consumable_id, []).append({
                'id': req.id,
                'status': req.status,
                'status_label': req.get_status_display(),
                'quantity': req.quantity,
                'requested_at': req.requested_at,
                'ordered_at': req.ordered_at,
                'requester_name': req.requester_name,
            })

        # 品目ごとの直近2件（ROW_NUMBER）
        recent_inbounds = {}
        inbound_qs = (
            ConsumableStockMovement.objects.filter(
                consumable_id__in=ids, movement_type=ConsumableStockMovement.TYPE_INBOUND
            )
            .annotate(rn=Window(RowNumber(), partition_by=[F('consumable_id')],
                                order_by=[F('moved_at').desc(), F('id').desc()]))
            .filter(rn__lte=2)
        )
        for mv in inbound_qs:
            recent_inbounds.setdefault(mv.consumable_id, []).append({
                'quantity': mv.quantity,
                'moved_at': mv.moved_at,
                'inbound_type_label': mv.get_inbound_type_display(),
                'worker_name': mv.worker_name,
            })

        for row in data:
            row['open_requests'] = open_requests.get(row['id'], [])
            row['recent_inbounds'] = sorted(
                recent_inbounds.get(row['id'], []), key=lambda m: m['moved_at'], reverse=True
            )
        return Response(data)

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


ORG_LEVEL_FIELDS = {
    'division': 'division_name',
    'group': 'group_name',
    'team': 'team_name',
    'unit': 'unit_name',
}


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f'日付の形式が正しくありません: {value}')


def _resolve_worker(request, field='worker'):
    """作業者（依頼者）: 指定があればそのユーザー、なければログインユーザー"""
    worker_id = request.data.get(field)
    if not worker_id:
        return request.user
    worker = get_user_model().objects.select_related(
        'profile__division', 'profile__group', 'profile__team', 'profile__unit'
    ).filter(id=worker_id, is_active=True).first()
    if worker is None:
        raise ValueError('指定されたユーザーが見つかりません')
    return worker


class ConsumableStockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    """入出庫履歴の照会と、入庫・出庫の登録"""
    queryset = ConsumableStockMovement.objects.select_related('consumable')
    serializer_class = ConsumableStockMovementSerializer
    permission_classes = [IsAuthenticated, HasResourcePermissionOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['movement_type', 'inbound_type', 'consumable', 'worker']
    search_fields = ['consumable__code', 'consumable__name', 'worker_name', 'note']
    ordering = ['-moved_at', '-id']

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        # 期間は業務日（日替わり8時）で絞り込む
        start, end = business_day_range(_parse_date(params.get('date_from')), _parse_date(params.get('date_to')))
        if start:
            qs = qs.filter(moved_at__gte=start)
        if end:
            qs = qs.filter(moved_at__lt=end)
        org_field = ORG_LEVEL_FIELDS.get(params.get('org_level', ''))
        if org_field and 'org_name' in params:
            qs = qs.filter(**{org_field: params.get('org_name')})
        return qs

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """部署別集計。org_level（division/group/team/unit、初期値 team）ごとに数量・金額を合計する"""
        org_level = request.query_params.get('org_level') or 'team'
        org_field = ORG_LEVEL_FIELDS.get(org_level)
        if not org_field:
            return Response({'detail': 'org_level が正しくありません'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            qs = self.filter_queryset(self.get_queryset())
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        rows = (
            qs.values(org_field, 'movement_type')
            .annotate(count=Count('id'), quantity=Sum('quantity'), total_amount=Sum('total_amount'))
            .order_by(org_field, 'movement_type')
        )
        return Response([
            {
                'org_name': row[org_field] or '（未設定）',
                'movement_type': row['movement_type'],
                'count': row['count'],
                'quantity': row['quantity'],
                'total_amount': row['total_amount'],
            }
            for row in rows
        ])

    @action(detail=False, methods=['get'])
    def workers(self, request):
        """作業者の選択肢（有効な pm ユーザー。社員コード・班付き）"""
        users = (
            get_user_model().objects.filter(is_active=True)
            .select_related('profile__team')
            .order_by('profile__employee_code', 'username')
        )
        result = []
        for user in users:
            profile = getattr(user, 'profile', None)
            result.append({
                'id': user.id,
                'name': display_user_name(user),
                'employee_code': (profile.employee_code if profile else '') or '',
                'team_name': profile.team.name if profile and profile.team else '',
            })
        return Response(result)

    def _register(self, request, movement_type):
        consumable_id = request.data.get('consumable')
        try:
            quantity = _to_int(request.data.get('quantity'), 0)
            worker = _resolve_worker(request)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if not consumable_id or quantity <= 0:
            return Response({'detail': '消耗品と数量（1以上）を指定してください'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            consumable = Consumable.objects.select_for_update().filter(id=consumable_id).first()
            if consumable is None:
                return Response({'detail': '消耗品が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
            if movement_type == ConsumableStockMovement.TYPE_OUTBOUND:
                if consumable.stock_quantity < quantity:
                    return Response(
                        {'detail': f'在庫が不足しています（在庫: {consumable.stock_quantity}）'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                consumable.stock_quantity -= quantity
            else:
                consumable.stock_quantity += quantity
            consumable.save(update_fields=['stock_quantity', 'updated_at'])

            movement = ConsumableStockMovement.objects.create(
                consumable=consumable,
                movement_type=movement_type,
                inbound_type=(
                    ConsumableStockMovement.INBOUND_MANUAL
                    if movement_type == ConsumableStockMovement.TYPE_INBOUND else ''
                ),
                quantity=quantity,
                stock_after=consumable.stock_quantity,
                worker=worker,
                worker_name=display_user_name(worker),
                usage_line=request.data.get('usage_line', '') or '',
                unit_price=consumable.unit_price,
                total_amount=consumable.unit_price * quantity,
                note=request.data.get('note', '') or '',
                moved_at=datetime.now(),
                created_by=request.user,
                **org_snapshot(worker),
            )
        return Response(self.get_serializer(movement).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def outbound(self, request):
        return self._register(request, ConsumableStockMovement.TYPE_OUTBOUND)

    @action(detail=False, methods=['post'])
    def inbound(self, request):
        """手動入庫（注文書による発注分の一括入庫は注文書APIで行う）"""
        return self._register(request, ConsumableStockMovement.TYPE_INBOUND)
