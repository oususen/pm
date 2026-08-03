from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
import django_filters
from django.db.models import Exists, Max, Min, OuterRef, Q
import csv
import json
import re
from datetime import date, datetime, timedelta
from orders.utils.calendar_utils import get_business_today

from masters.models import Routing
from shipping.services.email_service import EmailService
from system_settings.models import SystemSetting

from .models import (
    FirstArticleNoticeLog,
    Order,
    OrderLine,
    StgOrderDaily,
    StgOrderRaw,
    StgOrderRawKubota,
    StgOrderRawRieden,
    StgOrderRawTiera,
)
from .serializers import (
    OrderLineSerializer,
    OrderSerializer,
    StgOrderDailySerializer,
    StgOrderRawSerializer,
)
from .services.csv_import import CSVImportService


ORDER_FIRST_ARTICLE_DAYS_KEY = 'orders.first_article.days'
ORDER_FIRST_ARTICLE_RECIPIENT_IDS_KEY = 'orders.first_article.recipient_user_ids'
DEFAULT_ORDER_FIRST_ARTICLE_DAYS = 90


def _parse_order_first_article_user_ids(raw_value):
    if raw_value is None:
        return []
    text = str(raw_value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return sorted(set(int(v) for v in parsed if v is not None))
    except Exception:
        pass
    return []


def _get_order_first_article_settings():
    days_setting = SystemSetting.objects.filter(key=ORDER_FIRST_ARTICLE_DAYS_KEY).first()
    ids_setting = SystemSetting.objects.filter(key=ORDER_FIRST_ARTICLE_RECIPIENT_IDS_KEY).first()

    try:
        days = int(str(days_setting.value).strip()) if days_setting and str(days_setting.value).strip() else DEFAULT_ORDER_FIRST_ARTICLE_DAYS
    except (TypeError, ValueError):
        days = DEFAULT_ORDER_FIRST_ARTICLE_DAYS
    if days < 1:
        days = 1

    recipient_user_ids = _parse_order_first_article_user_ids(ids_setting.value if ids_setting else '')
    return {
        'days': days,
        'recipient_user_ids': recipient_user_ids,
    }


def _resolve_user_emails(user_ids):
    if not user_ids:
        return []
    from django.contrib.auth import get_user_model
    User = get_user_model()
    users = User.objects.filter(id__in=user_ids, is_active=True).exclude(email='')
    return list(users.values_list('email', flat=True))


def _build_order_first_article_body(candidates, days, user=None):
    lines = [
        '受注取込で、お久しぶり製品が検出されました。',
        '内容を確認してください。',
        '',
        f'判定条件: 納期から{days}日遡った期間に同一品番の受注明細がないこと',
        '',
        '対象一覧:',
    ]
    for item in candidates:
        lines.append(
            f"- 得意先: {item.get('customer_code') or '-'} / 品番: {item.get('product_code') or '-'} / 納期: {item.get('due_date') or '-'} / 数量: {item.get('quantity') or '-'} / 受注番号: {item.get('order_no') or '-'}"
        )

    if user and getattr(user, 'is_authenticated', False):
        name = f"{getattr(user, 'last_name', '')} {getattr(user, 'first_name', '')}".strip() or getattr(user, 'username', '')
        if name:
            lines.extend(['', f'取込者: {name}'])

    lines.extend(['', '以上'])
    return '\n'.join(lines)


def _collect_order_first_article_candidates(created_line_ids, days):
    if not created_line_ids:
        return []

    line_qs = (
        OrderLine.objects.filter(id__in=created_line_ids)
        .select_related('order', 'order__customer')
        .order_by('due_date', 'id')
    )

    # (customer_id, product_code, due_date, quantity) ごとに代表行を収集
    key_map = {}
    for line in line_qs:
        product_code = str(line.product_code or '').strip()
        due_date = line.due_date
        if not product_code or not due_date:
            continue
        customer_id = line.order.customer_id if line.order else None
        key = (customer_id, product_code, due_date, line.quantity)
        if key not in key_map:
            key_map[key] = line

    if not key_map:
        return []

    # まとめクエリ: 各 (customer_id, product_code) の window 内に過去受注があるか一括判定
    recent_keys = set()
    or_conditions = Q()
    checked_pairs = set()
    for (customer_id, product_code, due_date, _qty) in key_map:
        pair = (customer_id, product_code)
        if pair in checked_pairs:
            continue
        checked_pairs.add(pair)
        window_start = due_date - timedelta(days=days)
        or_conditions |= Q(
            order__customer_id=customer_id,
            product_code=product_code,
            due_date__gte=window_start,
            due_date__lt=due_date,
        )
    if or_conditions:
        recent_qs = (
            OrderLine.objects.filter(or_conditions)
            .exclude(id__in=created_line_ids)
            .values_list('order__customer_id', 'product_code')
            .distinct()
        )
        for cid, pc in recent_qs:
            recent_keys.add((cid, pc))

    # 通知済みログで同一内容を除外
    notified_keys = set()
    log_conditions = Q()
    for (customer_id, product_code, due_date, qty) in key_map:
        if (customer_id, product_code) in recent_keys:
            continue
        log_conditions |= Q(
            customer_id=customer_id,
            product_code=product_code,
            due_date=due_date,
            quantity=qty,
        )
    if log_conditions:
        for row in FirstArticleNoticeLog.objects.filter(log_conditions).values_list(
            'customer_id', 'product_code', 'due_date', 'quantity'
        ):
            notified_keys.add(row)

    candidates = []
    for (customer_id, product_code, due_date, qty), line in key_map.items():
        if (customer_id, product_code) in recent_keys:
            continue
        if (customer_id, product_code, due_date, qty) in notified_keys:
            continue
        candidates.append({
            'order_line_id': line.id,
            'customer_id': customer_id,
            'customer_code': line.order.customer.customer_code if line.order and line.order.customer else '',
            'order_no': line.order.order_no if line.order else '',
            'product_code': product_code,
            'due_date': due_date.isoformat(),
            'quantity': str(qty),
        })

    return candidates


def _send_order_first_article_notice(*, created_line_ids, user=None):
    settings_data = _get_order_first_article_settings()
    days = settings_data['days']
    recipient_user_ids = settings_data['recipient_user_ids']
    recipients = _resolve_user_emails(recipient_user_ids)
    candidates = _collect_order_first_article_candidates(created_line_ids, days)

    result = {
        'enabled': bool(recipient_user_ids),
        'days': days,
        'recipient_user_ids': recipient_user_ids,
        'candidate_count': len(candidates),
        'candidates': candidates,
        'sent': False,
        'message': '',
    }

    if not candidates:
        result['message'] = 'お久しぶり製品はありませんでした。'
        return result

    if not recipients:
        result['message'] = 'お久しぶり製品はありましたが、送信先が未設定のためメール送信していません。'
        return result

    today_label = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    subject = f'【受注】お久しぶり製品通知 {today_label}'
    body = _build_order_first_article_body(candidates, days, user=user)
    user_id = user.id if user and getattr(user, 'is_authenticated', False) else None
    send_result = EmailService().send_plain_email(
        to_emails=recipients,
        subject=subject,
        body=body,
        user_id=user_id,
    )
    result['sent'] = bool(send_result.get('success'))
    result['message'] = send_result.get('message') or ('メールを送信しました。' if result['sent'] else 'メール送信に失敗しました。')

    if result['sent']:
        from decimal import Decimal
        logs = []
        for c in candidates:
            logs.append(FirstArticleNoticeLog(
                customer_id=c['customer_id'],
                product_code=c['product_code'],
                due_date=c['due_date'],
                quantity=Decimal(c['quantity']),
            ))
        if logs:
            FirstArticleNoticeLog.objects.bulk_create(logs, ignore_conflicts=True)

    return result


class OrderFilter(django_filters.FilterSet):
    order_no = django_filters.CharFilter(method='filter_order_no')
    product_code = django_filters.CharFilter(method='filter_product_code')
    due_date_from = django_filters.DateFilter(method='filter_due_date_from')
    due_date_to = django_filters.DateFilter(method='filter_due_date_to')
    ship_to_code = django_filters.CharFilter(method='filter_ship_to_code')

    class Meta:
        model = Order
        fields = ['order_no', 'customer', 'order_type', 'status', 'order_date']

    def filter_order_no(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(order_no__icontains=value) |
            Q(lines__customer_order_no__icontains=value)
        ).distinct()

    def filter_product_code(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(lines__product_code__icontains=value).distinct()

    def filter_due_date_from(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(lines__due_date__gte=value).distinct()

    def filter_due_date_to(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(lines__due_date__lte=value).distinct()

    def filter_ship_to_code(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(lines__ship_to_code__icontains=value).distinct()


class OrderViewSet(viewsets.ModelViewSet):
    """受注ヘッダViewSet"""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OrderFilter
    search_fields = ['order_no', 'source_file']
    ordering_fields = ['order_date', 'created_at', 'id']
    ordering = ['-order_date', '-id']

    def get_queryset(self):
        qs = Order.objects.select_related('customer')
        # 詳細取得時のみ明細をプリフェッチしてレスポンスサイズを抑える
        if self.action != 'list':
            qs = qs.prefetch_related('lines')
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            from .serializers import OrderListSerializer
            return OrderListSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=['patch'])
    def close(self, request, pk=None):
        order = self.get_object()
        if order.status == 'CLOSED':
            return Response({'detail': 'すでにクローズ済みです'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'CLOSED'
        order.save(update_fields=['status'])
        return Response({'status': 'CLOSED'})

    def destroy(self, request, *args, **kwargs):
        """受注削除：Order + OrderLine（cascade）+ ステージングレコードをまとめて削除"""
        order = self.get_object()
        source_file = order.source_file

        # ステージングレコード削除（source_file が一致するもの・全顧客対応）
        if source_file:
            StgOrderRaw.objects.filter(source_file=source_file).delete()
            StgOrderRawKubota.objects.filter(source_file=source_file).delete()
            StgOrderRawTiera.objects.filter(source_file=source_file).delete()
            StgOrderRawRieden.objects.filter(source_file=source_file).delete()
            StgOrderDaily.objects.filter(source_file=source_file).delete()

        # Order 削除（OrderLine は CASCADE で自動削除）
        order.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderLineFilter(django_filters.FilterSet):
    due_date__gte = django_filters.DateFilter(field_name='due_date', lookup_expr='gte')
    due_date__lte = django_filters.DateFilter(field_name='due_date', lookup_expr='lte')
    order_type = django_filters.CharFilter(method='filter_order_type')
    customer_code = django_filters.CharFilter(
        field_name='order__customer__customer_code', lookup_expr='endswith'
    )
    product_code = django_filters.CharFilter(
        field_name='product_code', lookup_expr='icontains'
    )
    ship_to_code = django_filters.CharFilter(
        field_name='ship_to_code', lookup_expr='icontains'
    )

    class Meta:
        model = OrderLine
        fields = [
            'order', 'product', 'due_date', 'due_date__gte', 'due_date__lte',
            'order_type', 'customer_code', 'product_code', 'ship_to_code'
        ]

    def filter_order_type(self, queryset, name, value):
        if not value:
            return queryset
        raw_values = [v.strip().upper() for v in str(value).split(',') if v.strip()]
        valid_values = [v for v in raw_values if v in {'FIRM', 'FORECAST'}]
        if not valid_values:
            return queryset.none()
        return queryset.filter(
            Q(order_type__in=valid_values) |
            (Q(order_type__isnull=True) & Q(order__order_type__in=valid_values))
        )


class OrderLineViewSet(viewsets.ModelViewSet):
    """受注明細ViewSet"""
    queryset = OrderLine.objects.filter(order__status='OPEN').select_related('order', 'order__customer', 'product')
    serializer_class = OrderLineSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OrderLineFilter
    search_fields = ['product_code']
    ordering_fields = ['due_date', 'line_no']
    ordering = ['line_no']

    @action(detail=False, methods=['get'], url_path='missing-routing-items')
    def missing_routing_items(self, request):
        """ルーティング未設定の受注明細を一覧化する。"""
        qs = (
            self.get_queryset()
            .filter(product__isnull=False)
            .annotate(
                has_routing=Exists(
                    Routing.objects.filter(product=OuterRef('product'), is_active=True)
                )
            )
            .filter(has_routing=False)
            .select_related('order', 'order__customer', 'product')
            .order_by('due_date', 'order__customer__customer_code', 'product_code')
        )
        due_date_gte = request.query_params.get('due_date__gte')
        if due_date_gte:
            qs = qs.filter(due_date__gte=due_date_gte)

        records = list(qs)
        grouped = {}
        business_today = get_business_today()

        def sort_by_due_date(record, reverse=False):
            due = record.due_date or (date.min if reverse else date.max)
            order_time = record.order.updated_at or record.order.created_at or record.updated_at or record.created_at
            timestamp = order_time.timestamp() if order_time else 0
            customer_code = record.order.customer.customer_code if record.order and record.order.customer else ''
            if reverse:
                return (due, timestamp, record.order_id or 0, customer_code)
            return (due, -timestamp, -(record.order_id or 0), customer_code)

        for record in records:
            key = (record.product_code or '').strip().lower()
            if not key:
                continue
            grouped.setdefault(key, []).append(record)

        deduped = {}
        for key, product_records in grouped.items():
            future_records = [record for record in product_records if record.due_date and record.due_date >= business_today]
            if future_records:
                deduped[key] = min(future_records, key=sort_by_due_date)
            else:
                deduped[key] = max(product_records, key=lambda record: sort_by_due_date(record, reverse=True))

        deduped_list = sorted(
            deduped.values(),
            key=lambda item: (
                item.due_date or date.max,
                (item.order.customer.customer_code if item.order and item.order.customer else ''),
                item.product_code or '',
                item.order_id or 0,
            ),
        )

        serializer = self.get_serializer(deduped_list, many=True)
        return Response({
            'count': len(deduped),
            'results': serializer.data,
        })

    @action(detail=False, methods=['get'], url_path='customer-product-codes')
    def customer_product_codes(self, request):
        customer_code = str(request.query_params.get('customer_code', '')).strip()
        if not customer_code:
            return Response(
                {'detail': 'customer_code は必須です。'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = self.get_queryset().filter(order__customer__customer_code=customer_code)

        order_type = str(request.query_params.get('order_type', '')).strip().upper()
        if order_type:
            raw_values = [v.strip() for v in order_type.split(',') if v.strip()]
            valid_values = [v for v in raw_values if v in {'FIRM', 'FORECAST'}]
            if not valid_values:
                return Response(
                    {'customer_code': customer_code, 'order_type': order_type, 'count': 0, 'product_codes': []}
                )
            qs = qs.filter(
                Q(order_type__in=valid_values) |
                (Q(order_type__isnull=True) & Q(order__order_type__in=valid_values))
            )

        product_codes = list(
            qs.exclude(product_code__isnull=True)
              .exclude(product_code__exact='')
              .values_list('product_code', flat=True)
              .distinct()
        )
        return Response(
            {
                'customer_code': customer_code,
                'order_type': order_type or None,
                'count': len(product_codes),
                'product_codes': sorted(product_codes),
            }
        )


class StgOrderRawViewSet(viewsets.ModelViewSet):
    """受注取込ステージング（生データ）ViewSet"""
    queryset = StgOrderRaw.objects.all()
    serializer_class = StgOrderRawSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['customer_code', 'order_type', 'parse_status', 'source_file']
    search_fields = ['customer_code', 'product_code', 'source_file']
    ordering_fields = ['created_at', 'due_date']
    ordering = ['-created_at']

    def _get_import_service(self, customer_code, order_type, filename, factory=None, is_tiera_t3=False):
        """Select appropriate import service based on customer code, order type, and factory

        Args:
            customer_code: Customer code
            order_type: 'FIRM' or 'FORECAST'
            filename: CSV filename (for fallback detection)
            factory: Explicit factory code (e.g., 'SAKAI', 'HIRAKATA', 'KMT')
            is_tiera_t3: True の場合はティエラT3専用ロジックを利用
        """
        # Import services here to avoid circular imports
        from .services.csv_import import CSVImportService

        # Extract location from filename (fallback)
        filename_lower = filename.lower()

        # Customer: 000001 (ティエラ)
        if customer_code == '000001':
            if order_type == 'FORECAST':
                # ティエラ_内示
                if is_tiera_t3:
                    from .services.tiera_naiji_t3_import import TieraNaijiT3ImportService
                    return TieraNaijiT3ImportService()
                from .services.tiera_naiji_import import TieraNaijiImportService
                return TieraNaijiImportService()
            elif order_type == 'FIRM':
                # ティエラ_確定
                if is_tiera_t3:
                    from .services.tiera_kakutei_t3_import import TieraKakuteiT3ImportService
                    return TieraKakuteiT3ImportService()
                from .services.tiera_kakutei_import import TieraKakuteiImportService
                return TieraKakuteiImportService()

        # Customer: 000196 (クボタ)
        elif customer_code == '000196':
            # Determine factory: explicit parameter > filename detection
            detected_factory = factory
            if not detected_factory:
                if '堺' in filename or 'sakai' in filename_lower:
                    detected_factory = 'SAKAI'
                elif '枚方' in filename or 'hirakata' in filename_lower:
                    detected_factory = 'HIRAKATA'
                elif 'kmt' in filename_lower:
                    detected_factory = 'KMT'

            if detected_factory == 'SAKAI':
                if order_type == 'FORECAST':
                    # クボタ_堺_内示
                    from .services.kubota_sakai_naiji_import import KubotaSakaiNaijiImportService
                    return KubotaSakaiNaijiImportService()
                elif order_type == 'FIRM':
                    # クボタ_堺_確定
                    from .services.kubota_sakai_kakutei_import import KubotaSakaiKakuteiImportService
                    return KubotaSakaiKakuteiImportService()
            elif detected_factory == 'HIRAKATA':
                if order_type == 'FORECAST':
                    # クボタ_枚方_内示
                    from .services.kubota_hirakata_naiji_import import KubotaHirakataNaijiImportService
                    return KubotaHirakataNaijiImportService()
                elif order_type == 'FIRM':
                    # クボタ_枚方_確定
                    from .services.kubota_hirakata_kakutei_import import KubotaHirakataKakuteiImportService
                    return KubotaHirakataKakuteiImportService()
            elif detected_factory == 'HIRAKATA_2027':
                if order_type == 'FORECAST':
                    # クボタ_枚方_内示（2027年以降）
                    from .services.kubota_hirakata_2027_naiji_import import KubotaHirakata2027NaijiImportService
                    return KubotaHirakata2027NaijiImportService()
                elif order_type == 'FIRM':
                    # クボタ_枚方_確定（2027年以降）
                    from .services.kubota_hirakata_2027_kakutei_import import KubotaHirakata2027KakuteiImportService
                    return KubotaHirakata2027KakuteiImportService()
            elif detected_factory == 'KMT':
                if order_type == 'FORECAST':
                    # クボタ_KMT_内示
                    from .services.kubota_kmt_naiji_import import KubotaKmtNaijiImportService
                    return KubotaKmtNaijiImportService()
                elif order_type == 'FIRM':
                    # クボタ_KMT_確定
                    from .services.kubota_kmt_kakutei_import import KubotaKmtKakuteiImportService
                    return KubotaKmtKakuteiImportService()

        # Customer: 000018 (リーデン)
        elif customer_code == '000018':
            if order_type == 'FIRM':
                # リーデン_確定
                from .services.rieden_kakutei_import import RiedenKakuteiImportService
                return RiedenKakuteiImportService()

        # Default service
        return CSVImportService()

    def _infer_kubota_factory_from_file(self, file, order_type):
        """Infer Kubota factory from CSV contents using No + 工場 columns.

        Rule:
        - 工場 23 => HIRAKATA
        - 工場 21 => SAKAI
        - 工場 92/76 => KMT
        - Fallback by No when 工場が取れない:
          27 => KMT, 45 => HIRAKATA, 49 => SAKAI
        """
        try:
            file.seek(0)
            raw_data = file.read()
            decoded = None
            for enc in ('cp932', 'shift-jis', 'utf-8-sig', 'utf-8'):
                try:
                    decoded = raw_data.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if decoded is None:
                return None

            plant_map = {
                '23': 'HIRAKATA',
                '21': 'SAKAI',
                '92': 'KMT',
                '76': 'KMT',
            }
            no_fallback_map = {
                '27': 'KMT',
                '45': 'HIRAKATA',
                '49': 'SAKAI',
            }

            for row_no, row in enumerate(csv.reader(decoded.splitlines()), start=1):
                if row_no > 300:
                    break
                if len(row) < 2:
                    continue
                no_val = (row[0] or '').strip()
                plant_val = (row[1] or '').strip()

                # Skip header-like rows
                if not no_val.isdigit():
                    continue

                if plant_val in plant_map:
                    return plant_map[plant_val]

                if order_type == 'FIRM' and no_val in no_fallback_map:
                    return no_fallback_map[no_val]
            return None
        except Exception:
            return None
        finally:
            file.seek(0)

    def _is_kubota_hirakata_2027_format(self, file, order_type):
        """Detect Hirakata 2027+ format that should not be accepted by legacy HIRAKATA."""
        try:
            file.seek(0)
            raw_data = file.read()
            decoded = None
            for enc in ('cp932', 'shift-jis', 'utf-8-sig', 'utf-8'):
                try:
                    decoded = raw_data.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if decoded is None:
                return False

            rows = list(csv.reader(decoded.splitlines()))
            if not rows:
                return False

            header = rows[0]
            normalized_header = [
                str(col or '').strip().replace(' ', '').replace('　', '')
                for col in header
            ]

            if order_type == 'FIRM':
                # 現行枚方確定: 34列 / 注番あり / 発注番号なし
                if len(header) != 34:
                    return True
                if '注番' not in normalized_header:
                    return True
                if '発注番号' in normalized_header:
                    return True

                sample_rows = []
                for row in rows[1:]:
                    data_no = row[0].strip() if len(row) > 0 else ''
                    if data_no not in ('45', '47'):
                        continue
                    sample_rows.append(row)
                    if len(sample_rows) >= 5:
                        break

                for row in sample_rows:
                    data_no = row[0].strip() if len(row) > 0 else ''
                    legacy_order_no = row[3].strip() if len(row) > 3 else ''
                    new_order_no = row[33].strip() if len(row) > 33 else ''
                    if data_no == '47' and not legacy_order_no and new_order_no:
                        return True

            elif order_type == 'FORECAST':
                # 現行枚方内示: 123列 / 日程ライン圧縮あり / 初月度(指示日/指示数)系ではない
                if len(header) != 123:
                    return True
                if '日程ライン圧縮' not in normalized_header:
                    return True
                if any('初月度(' in col for col in normalized_header):
                    return True

            return False
        except Exception:
            return False
        finally:
            file.seek(0)

    def _is_kubota_hirakata_legacy_format(self, file, order_type):
        """Detect current Hirakata format that should not be accepted by HIRAKATA_2027."""
        try:
            file.seek(0)
            raw_data = file.read()
            decoded = None
            for enc in ('cp932', 'shift-jis', 'utf-8-sig', 'utf-8'):
                try:
                    decoded = raw_data.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if decoded is None:
                return False

            rows = list(csv.reader(decoded.splitlines()))
            if not rows:
                return False

            header = rows[0]
            normalized_header = [
                str(col or '').strip().replace(' ', '').replace('　', '')
                for col in header
            ]

            if order_type == 'FIRM':
                return (
                    len(header) == 34
                    and '注番' in normalized_header
                    and '発注番号' not in normalized_header
                )

            if order_type == 'FORECAST':
                return (
                    len(header) == 123
                    and '日程ライン圧縮' in normalized_header
                    and not any('初月度(' in col for col in normalized_header)
                )

            return False
        except Exception:
            return False
        finally:
            file.seek(0)

    @action(
        detail=False,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser],
        authentication_classes=[],
        permission_classes=[AllowAny],
    )
    def upload_csv(self, request):
        """Upload CSV file and import to staging"""
        try:
            file = request.FILES.get('file')
            customer_code = request.data.get('customer_code')
            order_type = request.data.get('order_type', 'FIRM')
            source_system = request.data.get('source_system', 'CSV')
            factory = request.data.get('factory')  # Optional: for multi-factory customers like Kubota
            is_tiera_t3 = str(request.data.get('is_tiera_t3', '')).strip().lower() in ('1', 'true', 'on')

            if not file:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not customer_code:
                return Response(
                    {'error': 'Customer code is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Kubotaは No + 工場 で自動判定可能だが、UIで工場選択がある場合は不一致をエラーにする
            if customer_code == '000196':
                inferred_factory = self._infer_kubota_factory_from_file(file, order_type)
                is_hirakata_2027_format = self._is_kubota_hirakata_2027_format(file, order_type)
                is_hirakata_legacy_format = self._is_kubota_hirakata_legacy_format(file, order_type)

                if factory == 'HIRAKATA' and is_hirakata_2027_format:
                    return Response(
                        {
                            'success': False,
                            'error': 'このCSVは枚方2027年以降の新形式です。',
                            'message': '旧「枚方工場」では取り込めません。「枚方工場（27年以降）」を選択して再アップロードしてください。',
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if factory == 'HIRAKATA_2027' and is_hirakata_legacy_format:
                    return Response(
                        {
                            'success': False,
                            'error': 'このCSVは2026年までの枚方形式です。',
                            'message': '「枚方工場（27年以降）」では取り込めません。旧「枚方工場」を選択して再アップロードしてください。',
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # 工場未指定時のみ CSV から推定して補完
                if not factory:
                    if inferred_factory == 'HIRAKATA' and is_hirakata_2027_format:
                        factory = 'HIRAKATA_2027'
                    elif inferred_factory:
                        factory = inferred_factory
                # 工場指定済みで不一致なら、誤取込防止のためエラー
                elif inferred_factory and factory != inferred_factory:
                    is_hirakata_compatible = (
                        inferred_factory == 'HIRAKATA' and factory == 'HIRAKATA_2027'
                    )
                    if is_hirakata_compatible:
                        pass
                    else:
                        factory_name_map = {
                            'SAKAI': '堺',
                            'HIRAKATA': '枚方',
                            'HIRAKATA_2027': '枚方（2027年以降）',
                            'KMT': 'KMT',
                        }
                        selected_name = factory_name_map.get(factory, factory)
                        inferred_name = factory_name_map.get(inferred_factory, inferred_factory)
                        return Response(
                            {
                                'success': False,
                                'error': (
                                    f'選択工場（{selected_name}）とCSV実データ工場（{inferred_name}）が一致しません。'
                                ),
                                'message': (
                                    f'このファイルは {inferred_name} 向けデータです。'
                                    f'{inferred_name} を選択して再アップロードしてください。'
                                ),
                            },
                            status=status.HTTP_400_BAD_REQUEST
                        )

            # リーデンは現行運用で「確定（FIRM）のみ」受付
            if customer_code == '000018' and order_type != 'FIRM':
                return Response(
                    {
                        'success': False,
                        'error': 'リーデン取込は確定（FIRM）のみ対応です。',
                        'message': 'customer_code=000018 の場合、order_type=FIRM を指定してください。'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check for duplicate file name across all raw tables
            if (StgOrderRaw.objects.filter(source_file=file.name).exists() or
                StgOrderRawKubota.objects.filter(source_file=file.name).exists() or
                StgOrderRawTiera.objects.filter(source_file=file.name).exists() or
                StgOrderRawRieden.objects.filter(source_file=file.name).exists()):
                return Response(
                    {
                        'success': False,
                        'error': f'このファイル名は既にアップロード済みです: {file.name}',
                        'message': f'ファイル名 \"{file.name}\" は既にステージングに存在します。別のファイル名でアップロードしてください。'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Select appropriate import service based on customer code, order type, and factory
            import_service = self._get_import_service(
                customer_code,
                order_type,
                file.name,
                factory,
                is_tiera_t3=is_tiera_t3
            )
            result = import_service.import_csv(file, customer_code, order_type, source_system)

            if result['success']:
                # Automatically create orders from staging after successful upload
                # Always use CSVImportService for order creation (common logic)
                try:
                    order_service = CSVImportService()
                    raw_id_range = (result.get('min_raw_id'), result.get('max_raw_id'))
                    order_result = order_service.create_orders_from_staging(
                        source_file=file.name,
                        raw_id_range=raw_id_range
                    )
                    result['orders_created'] = order_result.get('orders', 0)
                    result['lines_created'] = order_result.get('lines', 0)
                    result['superseded_forecast_orders'] = order_result.get('deleted_forecast_orders', 0)
                    result['additional_order_notices'] = order_result.get('additional_order_notices', [])
                except Exception as e:
                    result['order_creation_error'] = str(e)
                    result['message'] = f"CSV imported to staging successfully, but order creation failed: {str(e)}"

                if 'order_creation_error' not in result and customer_code == '000196' and order_type == 'FIRM':
                    try:
                        created_line_ids = order_result.get('created_line_ids') or []
                        if created_line_ids:
                            due_range = OrderLine.objects.filter(id__in=created_line_ids).aggregate(
                                min_due_date=Min('due_date'),
                                max_due_date=Max('due_date'),
                            )
                            sync_start = due_range.get('min_due_date')
                            sync_end = due_range.get('max_due_date')
                            if sync_start and sync_end:
                                from shipping.views_kubota_sakai_due_adjustment import sync_kubota_sakai_due_adjustments_from_orders
                                lock_date = SystemSetting.get_lock_date('kubota_sakai_due')
                                if lock_date and sync_start <= lock_date:
                                    sync_start = lock_date + timedelta(days=1)
                                if sync_start <= sync_end:
                                    result['kubota_sakai_due_adjustment_sync'] = sync_kubota_sakai_due_adjustments_from_orders(
                                        sync_start,
                                        sync_end,
                                    )
                                else:
                                    result['kubota_sakai_due_adjustment_sync'] = {
                                        'skipped': True,
                                        'detail': f'{lock_date} まで締め済みのため同期対象なし',
                                    }
                    except Exception as e:
                        result['due_adjustment_sync_error'] = str(e)

                # 通知は受注作成とは独立して実行（通知失敗で取込結果を汚さない）
                if 'order_creation_error' not in result:
                    try:
                        result['first_article_notice'] = _send_order_first_article_notice(
                            created_line_ids=order_result.get('created_line_ids') or [],
                            user=request.user,
                        )
                    except Exception as e:
                        result['first_article_notice'] = {
                            'enabled': False,
                            'candidate_count': 0,
                            'candidates': [],
                            'sent': False,
                            'message': f'通知処理でエラーが発生しました: {str(e)}',
                        }

                return Response(result, status=status.HTTP_201_CREATED)
            else:
                # Log error details
                print(f"CSV Import Error: {result}")
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False, methods=['post']
    )
    def create_orders(self, request):
        """Create orders from staging data"""
        try:
            service = CSVImportService()
            result = service.create_orders_from_staging()
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    def _compute_naiji_summary(product_code, start_date, end_date, ship_to=''):
        """製品1件の内示分析サマリーを計算して返す。

        Returns: dict (period_summary と同じキー構成) + 'snapshot_count', 'product_name'
        """
        from datetime import date
        import statistics
        from django.db.models import Sum as _Sum
        from masters.models import Calendar as _Calendar
        from orders.utils.calendar_utils import WorkingDayCalculator

        # 製品名取得
        first = StgOrderRawKubota.objects.filter(
            product_code=product_code, data_no='36', parse_status='PARSED'
        ).values('product_name').first()
        product_name = first['product_name'] if first else ''

        qs = (
            StgOrderRawKubota.objects
            .filter(product_code=product_code, data_no='36', parse_status='PARSED')
            .order_by('created_at', 'id')
        )

        def _parse_date_str(date_str):
            s = str(date_str).strip()
            try:
                if len(s) == 5 and s.isdigit():
                    y = int(s[0]); mm = int(s[1:3]); dd = int(s[3:5])
                    return date(2020 + y, mm, dd)
                if len(s) == 6 and s.isdigit():
                    yy = int(s[:2]); mm = int(s[2:4]); dd = int(s[4:6])
                    return date(2000 + yy, mm, dd)
            except (ValueError, IndexError):
                pass
            return None

        snapshots_map = {}
        snapshot_dates = {}
        for raw in qs:
            if not raw.date_headers or not raw.quantities:
                continue
            if ship_to:
                raw_ship_to = ((raw.raw_payload or {}).get('ship_to', '') or '').strip()
                if raw_ship_to != ship_to:
                    continue
            sf = raw.source_file
            if sf not in snapshots_map:
                snapshots_map[sf] = {}
                snapshot_dates[sf] = raw.created_at
            for dh, qty_str in zip(raw.date_headers, raw.quantities):
                due_date = _parse_date_str(dh)
                if not due_date:
                    continue
                if start_date and due_date < start_date:
                    continue
                if end_date and due_date > end_date:
                    continue
                try:
                    qty = float(qty_str) if qty_str and str(qty_str).strip() else 0.0
                except (ValueError, TypeError):
                    qty = 0.0
                ds = due_date.isoformat()
                snapshots_map[sf][ds] = snapshots_map[sf].get(ds, 0.0) + qty

        try:
            kubota_cal = _Calendar.objects.get(calendar_code='kubota_muke')
        except _Calendar.DoesNotExist:
            kubota_cal = None
        _wdc = WorkingDayCalculator(kubota_cal)

        all_due_dates = sorted({
            ds
            for qtys in snapshots_map.values()
            for ds in qtys.keys()
            if _wdc.is_working_day(date.fromisoformat(ds))
        })

        ordered_files = sorted(snapshots_map.keys(), key=lambda f: snapshot_dates[f])

        firm_qs = OrderLine.objects.filter(
            order__order_type='FIRM', order__status='OPEN', product_code=product_code,
        ).exclude(ship_to_code='971')
        if ship_to:
            firm_qs = firm_qs.filter(ship_to_code=ship_to)
        if start_date:
            firm_qs = firm_qs.filter(due_date__gte=start_date)
        if end_date:
            firm_qs = firm_qs.filter(due_date__lte=end_date)
        firm_quantities = {}
        for row in firm_qs.values('due_date').annotate(total_qty=_Sum('quantity')):
            firm_quantities[row['due_date'].isoformat()] = float(row['total_qty'])

        def _parse_yymmdd(s):
            s = str(s).strip()
            if len(s) == 6 and s.isdigit():
                try:
                    return date(2000 + int(s[:2]), int(s[2:4]), int(s[4:6]))
                except ValueError:
                    pass
            return None

        def _extract_kubota_firm_issue_date(order_no):
            parts = re.split(r'[-_]', str(order_no or ''))
            for part in parts[2:]:
                parsed = _parse_yymmdd(part)
                if parsed is not None:
                    return parsed
            return None

        firm_dates = {}
        for line in firm_qs.select_related('order').only('due_date', 'order__order_no'):
            issue_date_obj = _extract_kubota_firm_issue_date(line.order.order_no)
            if issue_date_obj is None:
                continue
            ds = line.due_date.isoformat()
            if ds not in firm_dates or issue_date_obj > firm_dates[ds]:
                firm_dates[ds] = issue_date_obj

        all_errors = []
        date_max_shortages = []  # 各納期の最大過小量（ワースト集計用）
        n_dates_with_firm = 0
        n_dates_shortage = 0
        _max_diff_val = _max_diff_date = _min_diff_val = _min_diff_date = None

        for ds in all_due_dates:
            firm_qty = firm_quantities.get(ds)
            if firm_qty is None:
                continue
            n_dates_with_firm += 1
            _raw = [snapshots_map[sf][ds] for sf in ordered_files if ds in snapshots_map[sf]]
            # 内示未着荷（数量=0）のスナップショットを先頭から除外
            _first_pos = next((i for i, q in enumerate(_raw) if q > 0), None)
            qty_series = _raw[_first_pos:] if _first_pos is not None else []
            if not qty_series:
                continue
            has_shortage = False
            _date_worst = 0.0
            for q in qty_series:
                err = q - firm_qty
                all_errors.append(err)
                if _max_diff_val is None or err > _max_diff_val:
                    _max_diff_val = err; _max_diff_date = ds
                if _min_diff_val is None or err < _min_diff_val:
                    _min_diff_val = err; _min_diff_date = ds
                if q < firm_qty:
                    has_shortage = True
                    s = firm_qty - q
                    if s > _date_worst:
                        _date_worst = s
            if _date_worst > 0:
                date_max_shortages.append(round(_date_worst, 1))
            if has_shortage:
                n_dates_shortage += 1

        from datetime import timedelta as _timedelta

        def _count_working_days(d_from, d_to):
            """d_from → d_to の営業日数（正負あり、kubota_mukeカレンダー参照）"""
            if d_from == d_to:
                return 0
            step = 1 if d_to > d_from else -1
            count = 0
            cur = d_from + _timedelta(days=step)
            while cur != d_to + _timedelta(days=step):
                if _wdc.is_working_day(cur):
                    count += step
                cur += _timedelta(days=step)
            return count

        stable_days_list = []
        firm_stable_days_list = []
        pre_converge_shortage_count = 0
        n_converge_total = 0
        firm_delay_count = 0
        firm_delay_total = 0
        for ds in all_due_dates:
            firm_qty = firm_quantities.get(ds)
            if firm_qty is None:
                continue
            due_date_obj = date.fromisoformat(ds)
            current_streak_start = None
            prev_qty = None
            for sf in ordered_files:
                if ds not in snapshots_map[sf]:
                    continue
                qty = snapshots_map[sf][ds]
                if qty <= 0:
                    continue
                snap_date = snapshot_dates[sf].date()
                if abs(qty - firm_qty) < 0.5:
                    if current_streak_start is None:
                        current_streak_start = snap_date
                else:
                    current_streak_start = None
                    prev_qty = qty
            if current_streak_start is not None:
                n_converge_total += 1
                if prev_qty is not None and prev_qty < firm_qty - 0.5:
                    pre_converge_shortage_count += 1
                days = _count_working_days(current_streak_start, due_date_obj)
                if days >= 0:
                    stable_days_list.append((days, ds))
                    firm_date_obj = firm_dates.get(ds)
                    if firm_date_obj is not None:
                        fdays = _count_working_days(current_streak_start, firm_date_obj)
                        firm_stable_days_list.append((fdays, ds))
                        firm_delay_total += 1
                        if firm_date_obj >= due_date_obj:
                            firm_delay_count += 1

        if stable_days_list:
            days_vals = sorted([d for d, _ in stable_days_list])
            stable_days_mean = round(sum(days_vals) / len(days_vals), 1)
            stable_days_median = days_vals[len(days_vals) // 2] if len(days_vals) % 2 == 1 else round((days_vals[len(days_vals) // 2 - 1] + days_vals[len(days_vals) // 2]) / 2, 1)
            stable_days_std = round(statistics.stdev(days_vals), 1) if len(days_vals) >= 2 else 0.0
            _min_e = min(stable_days_list, key=lambda x: x[0])
            _max_e = max(stable_days_list, key=lambda x: x[0])
            stable_days_min, stable_days_min_date = _min_e
            stable_days_max, stable_days_max_date = _max_e
            stable_days_count = len(stable_days_list)
            _n = len(days_vals)
            within_7_dates = sorted([ds for d, ds in stable_days_list if d <= 7])
            stable_days_dist = {
                'within_7': sum(1 for d in days_vals if d <= 7),
                'within_7_pct': round(sum(1 for d in days_vals if d <= 7) / _n * 100, 1),
                'within_7_dates': within_7_dates,
                'within_8_14': sum(1 for d in days_vals if 8 <= d <= 14),
                'within_8_14_pct': round(sum(1 for d in days_vals if 8 <= d <= 14) / _n * 100, 1),
                'within_15_21': sum(1 for d in days_vals if 15 <= d <= 21),
                'within_15_21_pct': round(sum(1 for d in days_vals if 15 <= d <= 21) / _n * 100, 1),
                'over_21': sum(1 for d in days_vals if d > 21),
                'over_21_pct': round(sum(1 for d in days_vals if d > 21) / _n * 100, 1),
            }
        else:
            stable_days_mean = stable_days_min = stable_days_min_date = None
            stable_days_max = stable_days_max_date = stable_days_count = None
            stable_days_median = stable_days_std = None
            stable_days_dist = None

        if firm_stable_days_list:
            fdays_vals = [d for d, _ in firm_stable_days_list]
            firm_stable_days_mean = round(sum(fdays_vals) / len(fdays_vals), 1)
            _fmin_e = min(firm_stable_days_list, key=lambda x: x[0])
            _fmax_e = max(firm_stable_days_list, key=lambda x: x[0])
            firm_stable_days_min, firm_stable_days_min_date = _fmin_e
            firm_stable_days_max, firm_stable_days_max_date = _fmax_e
            firm_stable_days_count = len(firm_stable_days_list)
        else:
            firm_stable_days_mean = firm_stable_days_min = firm_stable_days_min_date = None
            firm_stable_days_max = firm_stable_days_max_date = firm_stable_days_count = None
        firm_stable_days_negative_rate = round(firm_delay_count / firm_delay_total * 100, 1) if firm_delay_total > 0 else None

        n = len(all_errors)
        total_dates = len(all_due_dates)
        if n > 0:
            from collections import Counter as _Counter
            abs_errors = [abs(e) for e in all_errors]
            mae = round(sum(abs_errors) / n, 2)
            max_diff = round(_max_diff_val, 2)
            max_diff_date = _max_diff_date
            min_diff = round(_min_diff_val, 2)
            min_diff_date = _min_diff_date
            mean_err = round(sum(all_errors) / n, 2)
            sigma = round(statistics.stdev(all_errors), 2) if n >= 2 else 0.0
            shortage_rate = round(n_dates_shortage / n_dates_with_firm * 100, 1) if n_dates_with_firm > 0 else 0.0
            # ワースト1・2位（納期単位の最大過小量でランキング）
            if date_max_shortages:
                _counter = _Counter(date_max_shortages)
                _sorted = sorted(_counter.items(), key=lambda x: x[0], reverse=True)
                max_shortage = _sorted[0][0]
                worst1_rate = round(_sorted[0][1] / n_dates_with_firm * 100, 1) if n_dates_with_firm > 0 else None
                worst2_qty = _sorted[1][0] if len(_sorted) > 1 else None
                worst2_rate = round(_sorted[1][1] / n_dates_with_firm * 100, 1) if len(_sorted) > 1 and n_dates_with_firm > 0 else None
            else:
                max_shortage = 0.0
                worst1_rate = worst2_qty = worst2_rate = None
            bias = -mean_err if mean_err < 0 else 0.0
            ss_90 = round(1.28 * sigma + bias, 1)
            ss_95 = round(1.65 * sigma + bias, 1)
            ss_99 = round(2.33 * sigma + bias, 1)
        else:
            mae = max_diff = max_diff_date = min_diff = min_diff_date = mean_err = sigma = None
            shortage_rate = max_shortage = worst1_rate = worst2_qty = worst2_rate = None
            ss_90 = ss_95 = ss_99 = None
            n_dates_with_firm = 0
            n_dates_shortage = 0

        return {
            'product_code': product_code,
            'product_name': product_name,
            'snapshot_count': len(ordered_files),
            'analyzed_dates': len(all_due_dates),
            'dates_with_firm': n_dates_with_firm,
            'mae': mae,
            'max_diff': max_diff,
            'max_diff_date': max_diff_date,
            'min_diff': min_diff,
            'min_diff_date': min_diff_date,
            'mean_error': mean_err,
            'sigma': sigma,
            'shortage_rate': shortage_rate,
            'shortage_dates': n_dates_shortage,
            'max_shortage': max_shortage,
            'worst1_rate': worst1_rate,
            'worst2_qty': worst2_qty,
            'worst2_rate': worst2_rate,
            'safety_stock_90': ss_90,
            'safety_stock_95': ss_95,
            'safety_stock_99': ss_99,
            'stable_days_mean': stable_days_mean,
            'stable_days_median': stable_days_median,
            'stable_days_std': stable_days_std,
            'stable_days_dist': stable_days_dist,
            'stable_days_min': stable_days_min,
            'stable_days_min_date': stable_days_min_date,
            'stable_days_max': stable_days_max,
            'stable_days_max_date': stable_days_max_date,
            'stable_days_count': stable_days_count,
            'firm_stable_days_mean': firm_stable_days_mean,
            'firm_stable_days_min': firm_stable_days_min,
            'firm_stable_days_min_date': firm_stable_days_min_date,
            'firm_stable_days_max': firm_stable_days_max,
            'firm_stable_days_max_date': firm_stable_days_max_date,
            'firm_stable_days_count': firm_stable_days_count,
            'firm_stable_days_negative_rate': firm_stable_days_negative_rate,
            'pre_converge_shortage_rate': round(pre_converge_shortage_count / n_converge_total * 100, 1) if n_converge_total > 0 else None,
            'pre_converge_shortage_count': pre_converge_shortage_count,
            'pre_converge_total': n_converge_total,
        }

    @action(detail=False, methods=['get'])
    def kubota_naiji_products(self, request):
        """クボタ内示（36番）の製品一覧を返す（納入地情報付き）"""
        from django.db.models import Count, Max

        qs = (
            StgOrderRawKubota.objects
            .filter(data_no='36', parse_status='PARSED')
            .values('product_code', 'product_name')
            .annotate(
                snapshot_count=Count('id'),
                latest_file_date=Max('created_at'),
            )
            .order_by('product_code')
        )

        # 製品ごとの納入地一覧を取得
        from collections import defaultdict
        ship_to_map = defaultdict(set)
        for raw in StgOrderRawKubota.objects.filter(data_no='36', parse_status='PARSED').only('product_code', 'raw_payload'):
            st = ((raw.raw_payload or {}).get('ship_to', '') or '').strip()
            if st:
                ship_to_map[raw.product_code].add(st)

        results = [
            {
                'product_code': r['product_code'],
                'product_name': r['product_name'] or '',
                'snapshot_count': r['snapshot_count'],
                'latest_file_date': r['latest_file_date'].date().isoformat() if r['latest_file_date'] else None,
                'ship_to_list': sorted(ship_to_map.get(r['product_code'], [])),
            }
            for r in qs
        ]
        return Response(results)

    @action(detail=False, methods=['get'])
    def kubota_naiji_analysis(self, request):
        """クボタ内示の変化推移分析データを返す

        Query params:
            product_code: 品番（必須）
            start_date: 納期開始 (YYYY-MM-DD)
            end_date: 納期終了 (YYYY-MM-DD)
            ship_to: 納入地コード（任意、指定時はその納入地のみ）
        """
        from datetime import datetime, date
        import statistics

        product_code = request.query_params.get('product_code')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        ship_to = request.query_params.get('ship_to', '').strip()

        if not product_code:
            return Response({'error': 'product_code は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        # 日付文字列を解析
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        except ValueError:
            return Response({'error': '日付形式が不正です (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        # 内示データ取得（取込日順）
        qs = (
            StgOrderRawKubota.objects
            .filter(product_code=product_code, data_no='36', parse_status='PARSED')
            .order_by('created_at', 'id')
        )

        def _parse_date_str(date_str):
            """YMMDD(5桁) または YYMMDD(6桁) 形式の日付文字列をdateオブジェクトに変換"""
            s = str(date_str).strip()
            try:
                if len(s) == 5 and s.isdigit():
                    y = int(s[0])
                    mm = int(s[1:3])
                    dd = int(s[3:5])
                    return date(2020 + y, mm, dd)
                if len(s) == 6 and s.isdigit():
                    yy = int(s[:2])
                    mm = int(s[2:4])
                    dd = int(s[4:6])
                    return date(2000 + yy, mm, dd)
            except (ValueError, IndexError):
                pass
            return None

        # スナップショットごとに日別数量を収集
        # 同じsource_fileは同一スナップショット
        snapshots_map = {}  # source_file -> {due_date_str -> qty}
        snapshot_dates = {}  # source_file -> created_at
        snapshot_calc_dates = {}  # source_file -> calc_date (YYMMDD)

        for raw in qs:
            if not raw.date_headers or not raw.quantities:
                continue
            # 納入地フィルタ
            if ship_to:
                raw_ship_to = ((raw.raw_payload or {}).get('ship_to', '') or '').strip()
                if raw_ship_to != ship_to:
                    continue
            sf = raw.source_file
            if sf not in snapshots_map:
                snapshots_map[sf] = {}
                snapshot_dates[sf] = raw.created_at
                calc_date_str = (raw.raw_payload or {}).get('calc_date', '')
                if calc_date_str and len(str(calc_date_str)) == 6:
                    try:
                        s = str(calc_date_str)
                        snapshot_calc_dates[sf] = date(2000 + int(s[:2]), int(s[2:4]), int(s[4:6])).isoformat()
                    except (ValueError, IndexError):
                        pass

            for dh, qty_str in zip(raw.date_headers, raw.quantities):
                due_date = _parse_date_str(dh)
                if not due_date:
                    continue
                # 期間フィルタ
                if start_date and due_date < start_date:
                    continue
                if end_date and due_date > end_date:
                    continue
                try:
                    qty = float(qty_str) if qty_str and str(qty_str).strip() else 0.0
                except (ValueError, TypeError):
                    qty = 0.0
                # 同一納期で複数inspection_typeがある場合は合算
                ds = due_date.isoformat()
                snapshots_map[sf][ds] = snapshots_map[sf].get(ds, 0.0) + qty

        # クボタカレンダーで休日除きフィルタ
        from masters.models import Calendar as _Calendar
        from orders.utils.calendar_utils import WorkingDayCalculator
        try:
            kubota_cal = _Calendar.objects.get(calendar_code='kubota_muke')
        except _Calendar.DoesNotExist:
            kubota_cal = None
        _wdc = WorkingDayCalculator(kubota_cal)

        # 対象納期の全体集合（休日除き）
        all_due_dates = sorted({
            ds
            for qtys in snapshots_map.values()
            for ds in qtys.keys()
            if _wdc.is_working_day(date.fromisoformat(ds))
        })

        # スナップショット一覧（時系列順）
        ordered_files = sorted(snapshots_map.keys(), key=lambda f: snapshot_dates[f])
        snapshots = []
        for sf in ordered_files:
            snapshots.append({
                'source_file': sf,
                'snapshot_date': snapshot_dates[sf].date().isoformat(),
                'calc_date': snapshot_calc_dates.get(sf),
                'quantities': snapshots_map[sf],
            })

        # 確定数量（FIRM）を OrderLine（OPEN受注）から取得
        # StgOrderDailyは過去の取込履歴が混在するため、現在有効な確定受注を使用する
        # KMT納入先(ship_to_code='971')は内示がないため除外
        from django.db.models import Sum as _Sum
        firm_qs = (
            OrderLine.objects
            .filter(
                order__order_type='FIRM',
                order__status='OPEN',
                product_code=product_code,
            )
            .exclude(ship_to_code='971')
        )
        if ship_to:
            firm_qs = firm_qs.filter(ship_to_code=ship_to)
        if start_date:
            firm_qs = firm_qs.filter(due_date__gte=start_date)
        if end_date:
            firm_qs = firm_qs.filter(due_date__lte=end_date)

        firm_quantities = {}
        for row in firm_qs.values('due_date').annotate(total_qty=_Sum('quantity')):
            firm_quantities[row['due_date'].isoformat()] = float(row['total_qty'])

        def _parse_yymmdd_str(s):
            s = str(s).strip()
            if len(s) == 6 and s.isdigit():
                try:
                    return date(2000 + int(s[:2]), int(s[2:4]), int(s[4:6]))
                except ValueError:
                    pass
            return None

        def _extract_kubota_firm_issue_date_str(order_no):
            parts = re.split(r'[-_]', str(order_no or ''))
            for part in parts[2:]:
                parsed = _parse_yymmdd_str(part)
                if parsed is not None:
                    return parsed
            return None

        firm_dates = {}
        for line in firm_qs.select_related('order').only('due_date', 'order__order_no'):
            issue_date_obj = _extract_kubota_firm_issue_date_str(line.order.order_no)
            if issue_date_obj is None:
                continue
            ds = line.due_date.isoformat()
            if ds not in firm_dates or issue_date_obj > date.fromisoformat(firm_dates[ds]):
                firm_dates[ds] = issue_date_obj.isoformat()

        # 統計計算（納期ごと）
        stat_results = {}
        for ds in all_due_dates:
            _raw = [s['quantities'][ds] for s in snapshots if ds in s['quantities']]
            # 内示未着荷（数量=0）のスナップショットを先頭から除外
            _first_pos = next((i for i, q in enumerate(_raw) if q > 0), None)
            qty_series = _raw[_first_pos:] if _first_pos is not None else []
            if not qty_series:
                continue

            mean_val = sum(qty_series) / len(qty_series)
            std_val = statistics.stdev(qty_series) if len(qty_series) >= 2 else 0.0
            min_val = min(qty_series)
            max_val = max(qty_series)
            first_qty = qty_series[0]
            last_qty = qty_series[-1]
            firm_qty = firm_quantities.get(ds)

            stat_results[ds] = {
                'count': len(qty_series),
                'mean': round(mean_val, 2),
                'std_dev': round(std_val, 2),
                'min': min_val,
                'max': max_val,
                'range': round(max_val - min_val, 2),
                'cv': round(std_val / mean_val * 100, 2) if mean_val else 0.0,
                'first_qty': first_qty,
                'last_qty': last_qty,
                'first_to_last_change': round(last_qty - first_qty, 2),
                'first_to_last_pct': round((last_qty - first_qty) / first_qty * 100, 1) if first_qty else None,
                'firm_qty': firm_qty,
                'last_vs_firm': round(last_qty - firm_qty, 2) if firm_qty is not None else None,
                'last_vs_firm_pct': round((last_qty - firm_qty) / firm_qty * 100, 1) if firm_qty else None,
            }

        # ---- 期間全体サマリー（安全在庫分析用）----
        # 全スナップショット × 全納期 の誤差リスト（確定データがある納期のみ）
        # ※最終内示だけでなく、全取込時点の内示と確定の差を集計する
        all_errors = []      # snapshot_qty - firm（符号付き、全スナップショット分）
        n_dates_with_firm = 0  # 確定データがある納期数
        n_dates_shortage = 0   # 一度でも内示＜確定になった納期数
        date_max_shortages = []  # 各納期の最大過小量（ワースト集計用）
        _max_diff_val = None
        _max_diff_date = None
        _min_diff_val = None
        _min_diff_date = None

        for ds in all_due_dates:
            firm_qty = firm_quantities.get(ds)
            if firm_qty is None:
                continue
            n_dates_with_firm += 1
            _raw = [s['quantities'][ds] for s in snapshots if ds in s['quantities']]
            qty_series = [q for q in _raw if q > 0]
            if not qty_series:
                continue
            has_shortage = False
            _date_worst = 0.0
            for q in qty_series:
                err = q - firm_qty
                all_errors.append(err)
                if _max_diff_val is None or err > _max_diff_val:
                    _max_diff_val = err
                    _max_diff_date = ds
                if _min_diff_val is None or err < _min_diff_val:
                    _min_diff_val = err
                    _min_diff_date = ds
                if q < firm_qty:
                    has_shortage = True
                    s = firm_qty - q
                    if s > _date_worst:
                        _date_worst = s
            if _date_worst > 0:
                date_max_shortages.append((round(_date_worst, 1), ds))  # (過小量, 納期)
            if has_shortage:
                n_dates_shortage += 1

        # ---- 収束安定期間（内示が確定値と一致してから納期まで何日間） ----
        from datetime import timedelta as _timedelta
        def _count_working_days(d_from, d_to):
            if d_from == d_to:
                return 0
            step = 1 if d_to > d_from else -1
            count = 0
            cur = d_from + _timedelta(days=step)
            while cur != d_to + _timedelta(days=step):
                if _wdc.is_working_day(cur):
                    count += step
                cur += _timedelta(days=step)
            return count

        stable_days_list = []  # (days, due_date_str)
        converge_dates = {}  # 納期別の収束日
        pre_converge_shortage_count = 0
        pre_converge_shortage_dates = []
        n_converge_total = 0
        firm_due_lt5_count = 0  # 納期まで5営業日未満で確定した件数
        firm_due_lt5_total = 0  # 確定発行日がある件数
        firm_converge_on_or_after_firm_count = 0  # 確定一致日が確定日以後の件数
        firm_converge_on_or_after_firm_total = 0  # 確定一致日と確定日が比較できる件数
        firm_converge_on_or_after_firm_dates = []  # 条件に該当した納期日
        for ds in all_due_dates:
            firm_qty = firm_quantities.get(ds)
            if firm_qty is None:
                continue
            due_date_obj = date.fromisoformat(ds)
            current_streak_start = None
            prev_qty = None  # 収束直前のスナップショット数量
            for sf in ordered_files:
                if ds not in snapshots_map[sf]:
                    continue
                qty = snapshots_map[sf][ds]
                if qty <= 0:
                    continue
                snap_date = snapshot_dates[sf].date()
                if abs(qty - firm_qty) < 0.5:
                    if current_streak_start is None:
                        current_streak_start = snap_date
                else:
                    current_streak_start = None
                    prev_qty = qty
            if current_streak_start is not None:
                converge_dates[ds] = current_streak_start.isoformat()
                n_converge_total += 1
                if prev_qty is not None and prev_qty < firm_qty - 0.5:
                    pre_converge_shortage_count += 1
                    pre_converge_shortage_dates.append((round(firm_qty - prev_qty, 1), ds))
                days = _count_working_days(current_streak_start, due_date_obj)
                if days >= 0:
                    stable_days_list.append((days, ds))
                    firm_date_str = firm_dates.get(ds)
                    if firm_date_str:
                        firm_date_obj = date.fromisoformat(firm_date_str)
                        firm_due_lt5_total += 1
                        if _count_working_days(firm_date_obj, due_date_obj) < 5:
                            firm_due_lt5_count += 1
                        firm_converge_on_or_after_firm_total += 1
                        if current_streak_start >= firm_date_obj:
                            firm_converge_on_or_after_firm_count += 1
                            firm_converge_on_or_after_firm_dates.append(ds)

        firm_due_lt5_rate = round(firm_due_lt5_count / firm_due_lt5_total * 100, 1) if firm_due_lt5_total > 0 else None
        firm_converge_on_or_after_firm_rate = round(firm_converge_on_or_after_firm_count / firm_converge_on_or_after_firm_total * 100, 1) if firm_converge_on_or_after_firm_total > 0 else None

        if stable_days_list:
            days_vals = sorted([d for d, _ in stable_days_list])
            stable_days_mean = round(sum(days_vals) / len(days_vals), 1)
            stable_days_median = days_vals[len(days_vals) // 2] if len(days_vals) % 2 == 1 else round((days_vals[len(days_vals) // 2 - 1] + days_vals[len(days_vals) // 2]) / 2, 1)
            stable_days_std = round(statistics.stdev(days_vals), 1) if len(days_vals) >= 2 else 0.0
            _min_entry = min(stable_days_list, key=lambda x: x[0])
            _max_entry = max(stable_days_list, key=lambda x: x[0])
            stable_days_min = _min_entry[0]
            stable_days_min_date = _min_entry[1]
            stable_days_max = _max_entry[0]
            stable_days_max_date = _max_entry[1]
            stable_days_count = len(stable_days_list)
            _n = len(days_vals)
            within_7_dates = sorted([ds for d, ds in stable_days_list if d <= 7])
            stable_days_dist = {
                'within_7': sum(1 for d in days_vals if d <= 7),
                'within_7_pct': round(sum(1 for d in days_vals if d <= 7) / _n * 100, 1),
                'within_7_dates': within_7_dates,
                'within_8_14': sum(1 for d in days_vals if 8 <= d <= 14),
                'within_8_14_pct': round(sum(1 for d in days_vals if 8 <= d <= 14) / _n * 100, 1),
                'within_15_21': sum(1 for d in days_vals if 15 <= d <= 21),
                'within_15_21_pct': round(sum(1 for d in days_vals if 15 <= d <= 21) / _n * 100, 1),
                'over_21': sum(1 for d in days_vals if d > 21),
                'over_21_pct': round(sum(1 for d in days_vals if d > 21) / _n * 100, 1),
            }
        else:
            stable_days_mean = stable_days_min = stable_days_min_date = None
            stable_days_max = stable_days_max_date = stable_days_count = None
            stable_days_median = stable_days_std = None
            stable_days_dist = None

        from collections import Counter as _Counter
        n = len(all_errors)
        total_dates = len(all_due_dates)
        if n > 0:
            abs_errors = [abs(e) for e in all_errors]

            mae = round(sum(abs_errors) / n, 2)
            max_diff = round(_max_diff_val, 2)         # 最大差（内示 - 確定）符号付き
            max_diff_date = _max_diff_date             # 最大差が発生した納期
            min_diff = round(_min_diff_val, 2)         # 最小差（内示 - 確定）符号付き
            min_diff_date = _min_diff_date             # 最小差が発生した納期
            mean_err = round(sum(all_errors) / n, 2)  # 符号付き平均（負=内示過小傾向）
            sigma = round(statistics.stdev(all_errors), 2) if n >= 2 else 0.0

            # 内示過小率（何割の納期で一度でも内示＜確定があったか）
            shortage_rate = round(n_dates_shortage / n_dates_with_firm * 100, 1) if n_dates_with_firm > 0 else 0.0
            # ワースト1・2位（納期単位の最大過小量でランキング）
            if date_max_shortages:
                _qty_list = [qty for qty, _ in date_max_shortages]
                _counter = _Counter(_qty_list)
                _sorted = sorted(_counter.items(), key=lambda x: x[0], reverse=True)
                max_shortage = _sorted[0][0]
                worst1_rate = round(_sorted[0][1] / n_dates_with_firm * 100, 1) if n_dates_with_firm > 0 else None
                worst1_dates = sorted([ds for qty, ds in date_max_shortages if qty == max_shortage])
                worst2_qty = _sorted[1][0] if len(_sorted) > 1 else None
                worst2_rate = round(_sorted[1][1] / n_dates_with_firm * 100, 1) if len(_sorted) > 1 and n_dates_with_firm > 0 else None
                worst2_dates = sorted([ds for qty, ds in date_max_shortages if qty == worst2_qty]) if worst2_qty is not None else []
            else:
                max_shortage = 0.0
                worst1_rate = worst2_qty = worst2_rate = None
                worst1_dates = worst2_dates = []

            # 安全在庫推奨（Z×σ）。バイアスがある場合は補正
            bias = -mean_err if mean_err < 0 else 0.0
            ss_90 = round(1.28 * sigma + bias, 1)
            ss_95 = round(1.65 * sigma + bias, 1)
            ss_99 = round(2.33 * sigma + bias, 1)
        else:
            mae = max_diff = max_diff_date = min_diff = min_diff_date = mean_err = sigma = None
            shortage_rate = max_shortage = worst1_rate = worst2_qty = worst2_rate = None
            worst1_dates = worst2_dates = []
            ss_90 = ss_95 = ss_99 = None
            n_dates_with_firm = 0
            n_dates_shortage = 0

        period_summary = {
            'analyzed_dates': len(all_due_dates),
            'dates_with_firm': n_dates_with_firm,
            'mae': mae,                          # 平均絶対誤差（全スナップショット）
            'max_diff': max_diff,                # 最大差（内示 - 確定、全スナップショット中の最大値）
            'max_diff_date': max_diff_date,      # 最大差が発生した納期
            'min_diff': min_diff,                # 最小差（内示 - 確定、全スナップショット中の最小値）
            'min_diff_date': min_diff_date,      # 最小差が発生した納期
            'mean_error': mean_err,              # 平均差（符号付き。負=内示過小傾向）
            'sigma': sigma,                      # 予測誤差の標準偏差（全スナップショット）
            'shortage_rate': shortage_rate,      # 内示過小が発生した納期の割合(%)
            'shortage_dates': n_dates_shortage,  # 内示過小が発生した納期数
            'max_shortage': max_shortage,        # ワースト1位の過小量
            'worst1_rate': worst1_rate,          # ワースト1位の出現率
            'worst1_dates': worst1_dates,        # ワースト1位が発生した納期リスト
            'worst2_qty': worst2_qty,            # ワースト2位の過小量
            'worst2_rate': worst2_rate,          # ワースト2位の出現率
            'worst2_dates': worst2_dates,        # ワースト2位が発生した納期リスト
            'safety_stock_90': ss_90,
            'safety_stock_95': ss_95,
            'safety_stock_99': ss_99,
            'stable_days_mean': stable_days_mean,       # 収束安定期間 平均日数
            'stable_days_median': stable_days_median,   # 収束安定期間 中央値
            'stable_days_std': stable_days_std,         # 収束安定期間 標準偏差
            'stable_days_dist': stable_days_dist,       # 収束日数 分布
            'stable_days_min': stable_days_min,         # 収束安定期間 最短日数
            'stable_days_min_date': stable_days_min_date, # 最短が発生した納期
            'stable_days_max': stable_days_max,         # 収束安定期間 最長日数
            'stable_days_max_date': stable_days_max_date, # 最長が発生した納期
            'stable_days_count': stable_days_count,     # 収束確認できた納期数
            'pre_converge_shortage_rate': round(pre_converge_shortage_count / n_converge_total * 100, 1) if n_converge_total > 0 else None,
            'pre_converge_shortage_count': pre_converge_shortage_count,
            'pre_converge_total': n_converge_total,
            'pre_converge_shortage_dates': sorted(pre_converge_shortage_dates, key=lambda x: -x[0]),
            'firm_due_lt5_count': firm_due_lt5_count,
            'firm_due_lt5_total': firm_due_lt5_total,
            'firm_due_lt5_rate': firm_due_lt5_rate,
            'firm_converge_on_or_after_firm_count': firm_converge_on_or_after_firm_count,
            'firm_converge_on_or_after_firm_total': firm_converge_on_or_after_firm_total,
            'firm_converge_on_or_after_firm_rate': firm_converge_on_or_after_firm_rate,
            'firm_converge_on_or_after_firm_dates': sorted(firm_converge_on_or_after_firm_dates),
        }

        return Response({
            'product_code': product_code,
            'due_dates': all_due_dates,
            'snapshots': snapshots,
            'firm_quantities': firm_quantities,
            'firm_dates': firm_dates,
            'converge_dates': converge_dates,
            'statistics': stat_results,
            'period_summary': period_summary,
        })

    @action(detail=False, methods=['get'])
    def kubota_naiji_batch_report(self, request):
        """複数製品のクボタ内示分析サマリーをExcelで返す

        Query params:
            product_codes: カンマ区切りの品番リスト（品番:納入地 形式対応）
            start_date: 納期開始 (YYYY-MM-DD)
            end_date: 納期終了 (YYYY-MM-DD)
        """
        from datetime import datetime
        import io
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from django.http import HttpResponse

        codes_str = request.query_params.get('product_codes', '')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        entries = [c.strip() for c in codes_str.split(',') if c.strip()]
        if not entries:
            return Response({'error': 'product_codes は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        except ValueError:
            return Response({'error': '日付形式が不正です (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        # Excel生成
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'クボタ内示分析'

        # ヘッダースタイル
        header_fill = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
        header_font = Font(color='FFFFFF', bold=True, size=10)
        sub_fill = PatternFill(start_color='2E75B6', end_color='2E75B6', fill_type='solid')
        sub_font = Font(color='FFFFFF', bold=True, size=9)
        center = Alignment(horizontal='center', vertical='center', wrap_text=True)
        thin = Side(style='thin', color='CCCCCC')
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        # 期間情報
        period_str = ''
        if start_date_str:
            period_str += f'納期: {start_date_str}'
        if end_date_str:
            period_str += f' ～ {end_date_str}'
        ws.append([f'クボタ内示変化推移分析 一括レポート　{period_str}'])
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=25)
        title_cell = ws.cell(row=1, column=1)
        title_cell.font = Font(bold=True, size=12, color='1F4E79')
        title_cell.alignment = Alignment(horizontal='left', vertical='center')
        ws.row_dimensions[1].height = 22

        # カテゴリヘッダー行
        ws.append(['', '', '', '予測誤差（全スナップショット − 確定）', '', '', '', '', '', '', '欠品リスク', '', '', '', '', '推奨安全在庫量', '', '', '収束安定期間（日数）', '', '', '', '', '', '', '安定日数（確定登録まで）', '', '', '', ''])
        cat_row = 2
        # カテゴリセル結合とスタイル
        cat_ranges = [(4, 10), (11, 15), (16, 18), (19, 25), (26, 31)]
        cat_labels = ['予測誤差（全スナップショット − 確定）', '欠品リスク（内示＜確定）', '推奨安全在庫量（Z×σ）', '収束安定期間（内示＝確定が続いた日数）', '安定日数（収束開始→確定登録日）']
        cat_fills = ['2E75B6', 'C00000', '375623', '7030A0', 'BF8F00']
        for (start_col, end_col), label, fill_color in zip(cat_ranges, cat_labels, cat_fills):
            ws.merge_cells(start_row=cat_row, start_column=start_col, end_row=cat_row, end_column=end_col)
            cell = ws.cell(row=cat_row, column=start_col)
            cell.value = label
            cell.font = Font(color='FFFFFF', bold=True, size=9)
            cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type='solid')
            cell.alignment = center
            cell.border = border

        # 製品情報カラム見出し
        for col in range(1, 4):
            cell = ws.cell(row=cat_row, column=col)
            cell.fill = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
            cell.border = border

        # 列ヘッダー行
        headers = [
            '品番', '品名', 'スナップ\nショット数',
            '最大差', '最大差日', '最小差', '最小差日', 'MAE', '平均差', 'σ',
            '内示過小率(%)', 'ワースト1\n過小量', 'ワースト1\n出現率(%)', 'ワースト2\n過小量', 'ワースト2\n出現率(%)',
            '安全在庫\n90%', '安全在庫\n95%', '安全在庫\n99%',
            '収束\n平均日', '収束\n中央値', '収束\n標準偏差', '収束\n≤7日', '収束\n8-14日', '収束\n15-21日', '収束\n≥22日', '収束\n最短日', '収束最短日', '収束\n最長日', '収束最長日', '収束\n対象件数', '分析\n納期数',
            '安定\n平均日', '安定\n最短日', '安定最短日', '安定\n最長日', '安定\n対象件数', '安定\nマイナス率%',
        ]
        ws.append(headers)
        header_row = 3
        header_col_fills = (
            ['1F4E79'] * 3 +
            ['2E75B6'] * 7 +
            ['C00000'] * 5 +
            ['375623'] * 3 +
            ['7030A0'] * 13 +
            ['BF8F00'] * 6
        )
        for col_idx, (hdr, fill_color) in enumerate(zip(headers, header_col_fills), start=1):
            cell = ws.cell(row=header_row, column=col_idx)
            cell.value = hdr
            cell.font = Font(color='FFFFFF', bold=True, size=9)
            cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type='solid')
            cell.alignment = center
            cell.border = border
        ws.row_dimensions[header_row].height = 30

        # データ行
        def _v(val):
            return val if val is not None else ''

        for row_idx, entry in enumerate(entries, start=4):
            pc, st = self._parse_product_code_ship_to(entry)
            summary = StgOrderRawViewSet._compute_naiji_summary(pc, start_date, end_date, ship_to=st)
            display_code = f"{summary['product_code']} ({st})" if st else summary['product_code']
            row_data = [
                display_code,
                summary['product_name'],
                _v(summary['snapshot_count']),
                _v(summary['max_diff']),
                _v(summary['max_diff_date']),
                _v(summary['min_diff']),
                _v(summary['min_diff_date']),
                _v(summary['mae']),
                _v(summary['mean_error']),
                _v(summary['sigma']),
                _v(summary['shortage_rate']),
                _v(summary['max_shortage']),
                _v(summary['worst1_rate']),
                _v(summary['worst2_qty']),
                _v(summary['worst2_rate']),
                _v(summary['safety_stock_90']),
                _v(summary['safety_stock_95']),
                _v(summary['safety_stock_99']),
                _v(summary['stable_days_mean']),
                _v(summary.get('stable_days_median')),
                _v(summary.get('stable_days_std')),
                _v(summary.get('stable_days_dist', {}).get('within_7') if summary.get('stable_days_dist') else None),
                _v(summary.get('stable_days_dist', {}).get('within_8_14') if summary.get('stable_days_dist') else None),
                _v(summary.get('stable_days_dist', {}).get('within_15_21') if summary.get('stable_days_dist') else None),
                _v(summary.get('stable_days_dist', {}).get('over_21') if summary.get('stable_days_dist') else None),
                _v(summary['stable_days_min']),
                _v(summary['stable_days_min_date']),
                _v(summary['stable_days_max']),
                _v(summary['stable_days_max_date']),
                _v(summary['stable_days_count']),
                _v(summary['analyzed_dates']),
                _v(summary['firm_stable_days_mean']),
                _v(summary['firm_stable_days_min']),
                _v(summary['firm_stable_days_min_date']),
                _v(summary['firm_stable_days_max']),
                _v(summary['firm_stable_days_count']),
                _v(summary['firm_stable_days_negative_rate']),
            ]
            ws.append(row_data)
            # 行スタイル
            row_fill = 'EBF3FB' if row_idx % 2 == 0 else 'FFFFFF'
            for col_idx in range(1, 38):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.border = border
                cell.alignment = Alignment(horizontal='center', vertical='center')
                if col_idx in (1, 2):
                    cell.alignment = Alignment(horizontal='left', vertical='center')
                cell.fill = PatternFill(start_color=row_fill, end_color=row_fill, fill_type='solid')

        # 列幅設定
        col_widths = [18, 20, 8, 7, 12, 7, 12, 7, 7, 7, 10, 10, 9, 10, 9, 9, 9, 9, 8, 8, 8, 8, 8, 8, 8, 8, 12, 8, 12, 8, 8, 8, 8, 12, 8, 8, 10]
        for i, w in enumerate(col_widths, start=1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

        ws.freeze_panes = 'A4'

        # ファイル返却
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        period_label = f'{start_date_str or ""}_{end_date_str or ""}'
        filename = f'クボタ内示分析_{period_label}.xlsx'
        from urllib.parse import quote
        response = HttpResponse(
            buf.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(filename)}"
        return response

    @action(detail=False, methods=['get'])
    @staticmethod
    def _parse_product_code_ship_to(code_str):
        """'品番:納入地' or '品番' を (product_code, ship_to) に分解"""
        if ':' in code_str:
            pc, st = code_str.split(':', 1)
            return pc.strip(), st.strip()
        return code_str.strip(), ''

    @action(detail=False, methods=['get'])
    def kubota_naiji_batch_preview(self, request):
        """複数製品の内示分析サマリーをJSONで返す（画面プレビュー用）"""
        from datetime import datetime

        codes_str = request.query_params.get('product_codes', '')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        entries = [c.strip() for c in codes_str.split(',') if c.strip()]
        if not entries:
            return Response({'error': 'product_codes は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        except ValueError:
            return Response({'error': '日付形式が不正です (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        for entry in entries:
            pc, st = self._parse_product_code_ship_to(entry)
            summary = StgOrderRawViewSet._compute_naiji_summary(pc, start_date, end_date, ship_to=st)
            if st:
                summary['ship_to'] = st
            results.append(summary)
        return Response(results)

    @action(detail=False, methods=['get'])
    def check_filename(self, request):
        """Check if filename already exists in staging"""
        filename = request.query_params.get('filename')
        if not filename:
            return Response(
                {'error': 'Filename parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        exists = StgOrderRaw.objects.filter(source_file=filename).exists()

        return Response({
            'exists': exists,
            'filename': filename,
            'message': f'ファイル名 \"{filename}\" は既にアップロード済みです。' if exists else 'このファイル名は使用できます。'
        })


class StgOrderDailyViewSet(viewsets.ModelViewSet):
    """受注取込ステージング（日別）ViewSet"""
    queryset = StgOrderDaily.objects.all().select_related('customer', 'raw')
    serializer_class = StgOrderDailySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['customer', 'order_type', 'due_date']
    search_fields = ['product_code']
    ordering_fields = ['due_date', 'created_at']
    ordering = ['due_date']

    # ---- 汎用内示分析 API ----

    @action(detail=False, methods=['get'])
    def naiji_customers(self, request):
        """内示データがある顧客一覧"""
        from orders.core.services.naiji_analysis_service import get_naiji_customers
        return Response(get_naiji_customers())

    @action(detail=False, methods=['get'])
    def naiji_products(self, request):
        """指定顧客の内示製品一覧"""
        from orders.core.services.naiji_analysis_service import get_naiji_products
        customer_id = request.query_params.get('customer_id')
        if not customer_id:
            return Response({'error': 'customer_id は必須です'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(get_naiji_products(int(customer_id)))

    @action(detail=False, methods=['get'])
    def naiji_analysis(self, request):
        """内示変化推移分析（汎用版）"""
        from datetime import datetime
        from orders.core.services.naiji_analysis_service import compute_naiji_analysis

        customer_id = request.query_params.get('customer_id')
        product_code = request.query_params.get('product_code')
        if not customer_id or not product_code:
            return Response({'error': 'customer_id と product_code は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        ship_to = request.query_params.get('ship_to', '').strip()
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        except ValueError:
            return Response({'error': '日付形式が不正です (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        result = compute_naiji_analysis(int(customer_id), product_code, start_date, end_date, ship_to)
        return Response(result)

    @action(detail=False, methods=['get'])
    def naiji_batch_preview(self, request):
        """複数製品の内示分析サマリーをJSONで返す"""
        from datetime import datetime
        from orders.core.services.naiji_analysis_service import compute_naiji_summary

        customer_id = request.query_params.get('customer_id')
        codes_str = request.query_params.get('product_codes', '')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not customer_id:
            return Response({'error': 'customer_id は必須です'}, status=status.HTTP_400_BAD_REQUEST)
        entries = [c.strip() for c in codes_str.split(',') if c.strip()]
        if not entries:
            return Response({'error': 'product_codes は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        except ValueError:
            return Response({'error': '日付形式が不正です (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        for entry in entries:
            pc, st = (entry.split(':', 1) + [''])[:2]
            pc, st = pc.strip(), st.strip()
            summary = compute_naiji_summary(int(customer_id), pc, start_date, end_date, ship_to=st)
            if st:
                summary['ship_to'] = st
            results.append(summary)
        return Response(results)

    @action(detail=False, methods=['get'])
    def naiji_batch_report(self, request):
        """複数製品の内示分析サマリーをExcelで返す"""
        from datetime import datetime
        from django.http import HttpResponse
        from urllib.parse import quote
        from orders.core.services.naiji_analysis_service import generate_batch_report_excel

        customer_id = request.query_params.get('customer_id')
        codes_str = request.query_params.get('product_codes', '')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not customer_id:
            return Response({'error': 'customer_id は必須です'}, status=status.HTTP_400_BAD_REQUEST)
        entries = [c.strip() for c in codes_str.split(',') if c.strip()]
        if not entries:
            return Response({'error': 'product_codes は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        except ValueError:
            return Response({'error': '日付形式が不正です (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        buf, customer_name = generate_batch_report_excel(int(customer_id), entries, start_date, end_date)
        period_label = f'{start_date_str or ""}_{end_date_str or ""}'
        filename = f'{customer_name}_内示分析_{period_label}.xlsx'
        response = HttpResponse(
            buf.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(filename)}"
        return response


from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import get_user_model

@api_view(['GET', 'PATCH'])
def order_first_article_setting_view(request):
    """受注お久しぶり製品通知設定 GET/PATCH"""
    User = get_user_model()

    def _user_list():
        return [
            {'id': u.id, 'employee_code': getattr(u, 'employee_code', '') or '', 'username': u.username,
             'last_name': u.last_name, 'first_name': u.first_name}
            for u in User.objects.filter(is_active=True).order_by('last_name', 'first_name')
        ]

    if request.method == 'GET':
        settings_data = _get_order_first_article_settings()
        settings_data['all_users'] = _user_list()
        settings_data['notice_logs'] = [
            {
                'id': row.id,
                'customer_code': row.customer.customer_code if row.customer else '',
                'customer_name': row.customer.customer_name if row.customer else '',
                'product_code': row.product_code,
                'due_date': row.due_date.isoformat() if row.due_date else '',
                'quantity': str(row.quantity),
                'notified_at': row.notified_at.strftime('%Y-%m-%d %H:%M:%S') if row.notified_at else '',
            }
            for row in FirstArticleNoticeLog.objects.select_related('customer')
            .order_by('-notified_at', '-id')[:100]
        ]
        return Response(settings_data)

    days = request.data.get('days', DEFAULT_ORDER_FIRST_ARTICLE_DAYS)
    recipient_user_ids = request.data.get('recipient_user_ids', [])

    try:
        days = int(days)
    except (TypeError, ValueError):
        return Response({'detail': '判定日数は整数で指定してください。'}, status=status.HTTP_400_BAD_REQUEST)
    if days < 1:
        return Response({'detail': '判定日数は1以上で指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

    cleaned_ids = sorted(set(int(v) for v in recipient_user_ids if v is not None))
    SystemSetting.objects.update_or_create(
        key=ORDER_FIRST_ARTICLE_DAYS_KEY,
        defaults={
            'value': str(days),
            'description': '受注お久しぶり製品通知の判定日数',
            'updated_by': request.user if getattr(request.user, 'is_authenticated', False) else None,
        },
    )
    SystemSetting.objects.update_or_create(
        key=ORDER_FIRST_ARTICLE_RECIPIENT_IDS_KEY,
        defaults={
            'value': json.dumps(cleaned_ids),
            'description': '受注お久しぶり製品通知の送信先ユーザーID',
            'updated_by': request.user if getattr(request.user, 'is_authenticated', False) else None,
        },
    )
    return Response({
        'days': days,
        'recipient_user_ids': cleaned_ids,
    })


@api_view(['GET', 'PATCH'])
@permission_classes([AllowAny])
def kubota_sakai_import_config_view(request):
    """クボタ堺確定取り込み通知設定 GET/PATCH"""
    from .models import KubotaSakaiImportConfig
    config = KubotaSakaiImportConfig.get_solo()
    User = get_user_model()

    def _user_dict(u):
        return {
            'id': u.id,
            'username': u.username,
            'last_name': u.last_name,
            'first_name': u.first_name,
            'email': u.email,
            'profile': {'employee_code': getattr(u, 'employee_code', '') or ''},
        }

    if request.method == 'GET':
        notify_user_ids = list(config.notify_users.values_list('id', flat=True))
        all_users = [
            _user_dict(u)
            for u in User.objects.filter(is_active=True).order_by('last_name', 'first_name')
        ]
        return Response({
            'notify_user_ids': notify_user_ids,
            'email_enabled': config.email_enabled,
            'all_users': all_users,
        })

    # PATCH
    user_ids = request.data.get('notify_user_ids')
    if user_ids is not None:
        config.notify_users.set(user_ids)
    email_enabled = request.data.get('email_enabled')
    if email_enabled is not None:
        config.email_enabled = bool(email_enabled)
        config.save(update_fields=['email_enabled'])
    notify_user_ids = list(config.notify_users.values_list('id', flat=True))
    return Response({
        'notify_user_ids': notify_user_ids,
        'email_enabled': config.email_enabled,
    })
