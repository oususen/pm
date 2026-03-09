from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

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


class OrderLineViewSet(viewsets.ModelViewSet):
    """受注明細ViewSet"""
    queryset = OrderLine.objects.filter(order__status='OPEN').select_related('order', 'order__customer', 'product')
    serializer_class = OrderLineSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['order', 'product', 'due_date']
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
        detail=False,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser],
        authentication_classes=[],
        permission_classes=[AllowAny],
    )
    def upload_hirakata_special(self, request):
        """Upload Kubota Hirakata special confirmed order CSV"""
        try:
            file = request.FILES.get('file')
            customer_code = request.data.get('customer_code')
            order_type = request.data.get('order_type', 'FIRM')
            source_system = request.data.get('source_system', 'CSV')

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

            if customer_code != '000196':
                return Response(
                    {'error': 'This endpoint is only for customer_code 000196'},
                    status=status.HTTP_400_BAD_REQUEST
                )

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

            from .services.kubota_hirakata_special_kakutei_import import (
                KubotaHirakataSpecialKakuteiImportService,
            )
            import_service = KubotaHirakataSpecialKakuteiImportService()
            result = import_service.import_csv(file, customer_code, order_type, source_system)

            if result['success']:
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

                return Response(result, status=status.HTTP_201_CREATED)

            print(f"CSV Import Error: {result}")
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
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
            qty_series = [
                s['quantities'][ds]
                for s in snapshots
                if ds in s['quantities']
            ]
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
        _max_diff_val = None
        _max_diff_date = None
        _min_diff_val = None
        _min_diff_date = None

        for ds in all_due_dates:
            firm_qty = firm_quantities.get(ds)
            if firm_qty is None:
                continue
            n_dates_with_firm += 1
            qty_series = [
                s['quantities'][ds]
                for s in snapshots
                if ds in s['quantities']
            ]
            if not qty_series:
                continue
            has_shortage = False
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
            if has_shortage:
                n_dates_shortage += 1

        import math
        n = len(all_errors)
        if n > 0:
            abs_errors = [abs(e) for e in all_errors]
            shortage_diffs = [-e for e in all_errors if e < 0]  # 内示過小の絶対量

            mae = round(sum(abs_errors) / n, 2)
            max_diff = round(_max_diff_val, 2)         # 最大差（内示 - 確定）符号付き
            max_diff_date = _max_diff_date             # 最大差が発生した納期
            min_diff = round(_min_diff_val, 2)         # 最小差（内示 - 確定）符号付き
            min_diff_date = _min_diff_date             # 最小差が発生した納期
            mean_err = round(sum(all_errors) / n, 2)  # 符号付き平均（負=内示過小傾向）
            sigma = round(statistics.stdev(all_errors), 2) if n >= 2 else 0.0

            # 内示過小率（何割の納期で一度でも内示＜確定があったか）
            shortage_rate = round(n_dates_shortage / n_dates_with_firm * 100, 1) if n_dates_with_firm > 0 else 0.0
            # 最大過小量（確定を最も下回ったスナップショットの量）
            max_shortage = round(max(shortage_diffs), 2) if shortage_diffs else 0.0

            # 安全在庫推奨（Z×σ）。バイアスがある場合は補正
            bias = -mean_err if mean_err < 0 else 0.0
            ss_90 = round(1.28 * sigma + bias, 1)
            ss_95 = round(1.65 * sigma + bias, 1)
            ss_99 = round(2.33 * sigma + bias, 1)
        else:
            mae = max_diff = max_diff_date = min_diff = min_diff_date = mean_err = sigma = None
            shortage_rate = max_shortage = None
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
            'max_shortage': max_shortage,        # 最大過小量（欠品ワーストケース）
            'safety_stock_90': ss_90,
            'safety_stock_95': ss_95,
            'safety_stock_99': ss_99,
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
