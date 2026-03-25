from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
import django_filters

from .models import (
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


class OrderViewSet(viewsets.ModelViewSet):
    """受注ヘッダViewSet"""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['customer', 'order_type', 'status', 'order_date']
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
        fields = ['order', 'product', 'due_date', 'customer_code', 'product_code', 'ship_to_code']


class OrderLineViewSet(viewsets.ModelViewSet):
    """受注明細ViewSet"""
    queryset = OrderLine.objects.filter(order__status='OPEN').select_related('order', 'order__customer', 'product')
    serializer_class = OrderLineSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OrderLineFilter
    search_fields = ['product_code']
    ordering_fields = ['due_date', 'line_no']
    ordering = ['line_no']


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
            factory: Explicit factory code (e.g., 'SAKAI', 'HIRAKATA')
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

        # Customer: 000018 (リーデン)
        elif customer_code == '000018':
            if order_type == 'FIRM':
                # リーデン_確定
                from .services.rieden_kakutei_import import RiedenKakuteiImportService
                return RiedenKakuteiImportService()

        # Default service
        return CSVImportService()

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
                    # Use raw ID range to filter only records from this import
                    raw_id_range = (result.get('min_raw_id'), result.get('max_raw_id'))
                    order_result = order_service.create_orders_from_staging(
                        source_file=file.name,
                        raw_id_range=raw_id_range
                    )
                    # Merge results
                    result['orders_created'] = order_result.get('orders', 0)
                    result['lines_created'] = order_result.get('lines', 0)
                    result['superseded_forecast_orders'] = order_result.get('deleted_forecast_orders', 0)
                    result['additional_order_notices'] = order_result.get('additional_order_notices', [])
                except Exception as e:
                    # If order creation fails, still return the staging import success
                    # but include the error
                    result['order_creation_error'] = str(e)
                    result['message'] = f"CSV imported to staging successfully, but order creation failed: {str(e)}"

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
    def _compute_naiji_summary(product_code, start_date, end_date):
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
        )
        if start_date:
            firm_qs = firm_qs.filter(due_date__gte=start_date)
        if end_date:
            firm_qs = firm_qs.filter(due_date__lte=end_date)
        firm_quantities = {}
        for row in firm_qs.values('due_date').annotate(total_qty=_Sum('quantity')):
            firm_quantities[row['due_date'].isoformat()] = float(row['total_qty'])

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

        stable_days_list = []
        for ds in all_due_dates:
            firm_qty = firm_quantities.get(ds)
            if firm_qty is None:
                continue
            due_date_obj = date.fromisoformat(ds)
            current_streak_start = None
            _seen_positive = False
            for sf in ordered_files:
                if ds not in snapshots_map[sf]:
                    continue
                qty = snapshots_map[sf][ds]
                # 内示未着荷（数量=0）のスナップショットは収束判定から除外
                if not _seen_positive:
                    if qty <= 0:
                        continue
                    _seen_positive = True
                snap_date = snapshot_dates[sf].date()
                if abs(qty - firm_qty) < 0.5:
                    if current_streak_start is None:
                        current_streak_start = snap_date
                else:
                    current_streak_start = None
            if current_streak_start is not None:
                days = (due_date_obj - current_streak_start).days
                if days >= 0:
                    stable_days_list.append((days, ds))

        if stable_days_list:
            days_vals = [d for d, _ in stable_days_list]
            stable_days_mean = round(sum(days_vals) / len(days_vals), 1)
            _min_e = min(stable_days_list, key=lambda x: x[0])
            _max_e = max(stable_days_list, key=lambda x: x[0])
            stable_days_min, stable_days_min_date = _min_e
            stable_days_max, stable_days_max_date = _max_e
            stable_days_count = len(stable_days_list)
        else:
            stable_days_mean = stable_days_min = stable_days_min_date = None
            stable_days_max = stable_days_max_date = stable_days_count = None

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
            'stable_days_min': stable_days_min,
            'stable_days_min_date': stable_days_min_date,
            'stable_days_max': stable_days_max,
            'stable_days_max_date': stable_days_max_date,
            'stable_days_count': stable_days_count,
        }

    @action(detail=False, methods=['get'])
    def kubota_naiji_products(self, request):
        """クボタ内示（36番）の製品一覧を返す"""
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
        results = [
            {
                'product_code': r['product_code'],
                'product_name': r['product_name'] or '',
                'snapshot_count': r['snapshot_count'],
                'latest_file_date': r['latest_file_date'].date().isoformat() if r['latest_file_date'] else None,
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
        """
        from datetime import datetime, date
        import statistics

        product_code = request.query_params.get('product_code')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

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

        for raw in qs:
            if not raw.date_headers or not raw.quantities:
                continue
            sf = raw.source_file
            if sf not in snapshots_map:
                snapshots_map[sf] = {}
                snapshot_dates[sf] = raw.created_at

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
                'quantities': snapshots_map[sf],
            })

        # 確定数量（FIRM）を OrderLine（OPEN受注）から取得
        # StgOrderDailyは過去の取込履歴が混在するため、現在有効な確定受注を使用する
        from django.db.models import Sum as _Sum
        firm_qs = (
            OrderLine.objects
            .filter(
                order__order_type='FIRM',
                order__status='OPEN',
                product_code=product_code,
            )
        )
        if start_date:
            firm_qs = firm_qs.filter(due_date__gte=start_date)
        if end_date:
            firm_qs = firm_qs.filter(due_date__lte=end_date)

        firm_quantities = {}
        for row in firm_qs.values('due_date').annotate(total_qty=_Sum('quantity')):
            firm_quantities[row['due_date'].isoformat()] = float(row['total_qty'])

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
        # 各納期について、最後に連続して確定値と一致し始めた日から納期までの日数
        stable_days_list = []  # (days, due_date_str)
        for ds in all_due_dates:
            firm_qty = firm_quantities.get(ds)
            if firm_qty is None:
                continue
            due_date_obj = date.fromisoformat(ds)
            current_streak_start = None
            _seen_positive = False
            for sf in ordered_files:
                if ds not in snapshots_map[sf]:
                    continue
                qty = snapshots_map[sf][ds]
                # 内示未着荷（数量=0）のスナップショットは収束判定から除外
                if not _seen_positive:
                    if qty <= 0:
                        continue
                    _seen_positive = True
                snap_date = snapshot_dates[sf].date()
                if abs(qty - firm_qty) < 0.5:  # 一致（小数誤差考慮）
                    if current_streak_start is None:
                        current_streak_start = snap_date
                else:
                    current_streak_start = None  # 不一致でリセット
            if current_streak_start is not None:
                days = (due_date_obj - current_streak_start).days
                if days >= 0:
                    stable_days_list.append((days, ds))

        if stable_days_list:
            days_vals = [d for d, _ in stable_days_list]
            stable_days_mean = round(sum(days_vals) / len(days_vals), 1)
            _min_entry = min(stable_days_list, key=lambda x: x[0])
            _max_entry = max(stable_days_list, key=lambda x: x[0])
            stable_days_min = _min_entry[0]
            stable_days_min_date = _min_entry[1]
            stable_days_max = _max_entry[0]
            stable_days_max_date = _max_entry[1]
            stable_days_count = len(stable_days_list)
        else:
            stable_days_mean = stable_days_min = stable_days_min_date = None
            stable_days_max = stable_days_max_date = stable_days_count = None

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
            'stable_days_min': stable_days_min,         # 収束安定期間 最短日数
            'stable_days_min_date': stable_days_min_date, # 最短が発生した納期
            'stable_days_max': stable_days_max,         # 収束安定期間 最長日数
            'stable_days_max_date': stable_days_max_date, # 最長が発生した納期
            'stable_days_count': stable_days_count,     # 収束確認できた納期数
        }

        return Response({
            'product_code': product_code,
            'due_dates': all_due_dates,
            'snapshots': snapshots,
            'firm_quantities': firm_quantities,
            'statistics': stat_results,
            'period_summary': period_summary,
        })

    @action(detail=False, methods=['get'])
    def kubota_naiji_batch_report(self, request):
        """複数製品のクボタ内示分析サマリーをExcelで返す

        Query params:
            product_codes: カンマ区切りの品番リスト（必須）
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

        product_codes = [c.strip() for c in codes_str.split(',') if c.strip()]
        if not product_codes:
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
        ws.append(['', '', '', '予測誤差（全スナップショット − 確定）', '', '', '', '', '', '', '欠品リスク', '', '', '', '', '推奨安全在庫量', '', '', '収束安定期間（日数）', '', '', '', '', '', ''])
        cat_row = 2
        # カテゴリセル結合とスタイル
        cat_ranges = [(4, 10), (11, 15), (16, 18), (19, 25)]
        cat_labels = ['予測誤差（全スナップショット − 確定）', '欠品リスク（内示＜確定）', '推奨安全在庫量（Z×σ）', '収束安定期間（内示＝確定が続いた日数）']
        cat_fills = ['2E75B6', 'C00000', '375623', '7030A0']
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
            '収束\n平均日', '収束\n最短日', '収束最短日', '収束\n最長日', '収束最長日', '収束\n対象件数', '分析\n納期数',
        ]
        ws.append(headers)
        header_row = 3
        header_col_fills = (
            ['1F4E79'] * 3 +
            ['2E75B6'] * 7 +
            ['C00000'] * 5 +
            ['375623'] * 3 +
            ['7030A0'] * 7
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

        for row_idx, product_code in enumerate(product_codes, start=4):
            summary = StgOrderRawViewSet._compute_naiji_summary(product_code, start_date, end_date)
            row_data = [
                summary['product_code'],
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
                _v(summary['stable_days_min']),
                _v(summary['stable_days_min_date']),
                _v(summary['stable_days_max']),
                _v(summary['stable_days_max_date']),
                _v(summary['stable_days_count']),
                _v(summary['analyzed_dates']),
            ]
            ws.append(row_data)
            # 行スタイル
            row_fill = 'EBF3FB' if row_idx % 2 == 0 else 'FFFFFF'
            for col_idx in range(1, 26):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.border = border
                cell.alignment = Alignment(horizontal='center', vertical='center')
                if col_idx in (1, 2):
                    cell.alignment = Alignment(horizontal='left', vertical='center')
                cell.fill = PatternFill(start_color=row_fill, end_color=row_fill, fill_type='solid')

        # 列幅設定
        col_widths = [18, 20, 8, 7, 12, 7, 12, 7, 7, 7, 10, 10, 9, 10, 9, 9, 9, 9, 8, 8, 12, 8, 12, 8, 8]
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
    def kubota_naiji_batch_preview(self, request):
        """複数製品の内示分析サマリーをJSONで返す（画面プレビュー用）"""
        from datetime import datetime

        codes_str = request.query_params.get('product_codes', '')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        product_codes = [c.strip() for c in codes_str.split(',') if c.strip()]
        if not product_codes:
            return Response({'error': 'product_codes は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        except ValueError:
            return Response({'error': '日付形式が不正です (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        results = [
            StgOrderRawViewSet._compute_naiji_summary(pc, start_date, end_date)
            for pc in product_codes
        ]
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


from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import get_user_model

@api_view(['GET', 'PATCH'])
@permission_classes([AllowAny])
def kubota_sakai_import_config_view(request):
    """クボタ堺確定取り込み通知設定 GET/PATCH"""
    from .models import KubotaSakaiImportConfig
    config = KubotaSakaiImportConfig.get_solo()
    User = get_user_model()

    if request.method == 'GET':
        notify_users = [
            {'id': u.id, 'full_name': u.get_full_name() or u.username}
            for u in config.notify_users.all()
        ]
        all_users = [
            {'id': u.id, 'full_name': u.get_full_name() or u.username}
            for u in User.objects.filter(is_active=True).order_by('last_name', 'first_name')
        ]
        return Response({'notify_users': notify_users, 'all_users': all_users})

    # PATCH
    user_ids = request.data.get('notify_user_ids', [])
    config.notify_users.set(user_ids)
    notify_users = [
        {'id': u.id, 'full_name': u.get_full_name() or u.username}
        for u in config.notify_users.all()
    ]
    return Response({'notify_users': notify_users})
