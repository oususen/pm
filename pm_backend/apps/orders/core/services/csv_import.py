import csv
import json
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from orders.core.models import StgOrderRaw, StgOrderDaily, Order, OrderLine
from masters.models import Customer, Product


class CSVImportService:
    """CSV Import Service for Orders"""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def import_csv(self, file, customer_code, order_type, source_system='CSV'):
        """
        Import CSV file and create staging data

        Args:
            file: Uploaded file object
            customer_code: Customer code
            order_type: 'FIRM' or 'FORECAST'
            source_system: Source system name

        Returns:
            dict: Import result with statistics
        """
        self.errors = []
        self.warnings = []

        try:
            # Read CSV file with encoding detection
            file.seek(0)
            raw_data = file.read()

            # Try multiple encodings
            decoded_file = None
            encodings = ['utf-8-sig', 'utf-8', 'shift-jis', 'cp932', 'iso-2022-jp']
            for encoding in encodings:
                try:
                    decoded_file = raw_data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if decoded_file is None:
                return {
                    'success': False,
                    'message': 'Failed to decode CSV file. Unsupported encoding.',
                    'errors': ['Could not decode file with any supported encoding (utf-8, shift-jis, cp932, iso-2022-jp)']
                }

            csv_data = csv.DictReader(decoded_file.splitlines())
            
            # Get header row to build column map
            header_row = csv_data.fieldnames
            col_map = self._build_header_map(header_row) if header_row else {}

            raw_records = []
            row_no = 1

            for row in csv_data:
                row_no += 1
                try:
                    raw_record = self._create_raw_record(
                        row, row_no, customer_code, order_type,
                        source_system, file.name, col_map
                    )
                    raw_records.append(raw_record)
                except Exception as e:
                    self.errors.append(f"Row {row_no}: {str(e)}")

            if not raw_records:
                return {
                    'success': False,
                    'message': 'No valid records found',
                    'errors': self.errors
                }

            # Save to database
            with transaction.atomic():
                # Save raw records
                created_raws = StgOrderRaw.objects.bulk_create(raw_records)

                # Re-fetch to ensure we have primary keys
                raw_records_with_ids = StgOrderRaw.objects.filter(
                    source_file=file.name,
                    customer_code=customer_code
                ).order_by('-id')[:len(raw_records)]

                # Track min and max IDs for this import
                raw_ids = [r.id for r in raw_records_with_ids]
                min_raw_id = min(raw_ids) if raw_ids else None
                max_raw_id = max(raw_ids) if raw_ids else None

                # Process raw data to daily using saved records
                daily_records = []
                error_count = 0
                success_count = 0

                for raw in raw_records_with_ids:
                    if not raw.product_code or not raw.due_date or raw.quantity is None:
                        raw.parse_status = 'ERROR'
                        raw.error_message = 'Missing required fields'
                        raw.save()
                        error_count += 1
                        continue

                    # Find customer
                    try:
                        customer = Customer.objects.get(customer_code=raw.customer_code)
                    except Customer.DoesNotExist:
                        raw.parse_status = 'ERROR'
                        raw.error_message = f'Customer not found: {raw.customer_code}'
                        raw.save()
                        error_count += 1
                        continue

                    daily = StgOrderDaily(
                        raw=raw,
                        customer=customer,
                        order_type=raw.order_type,
                        version_no='v1',
                        product_code=raw.product_code,
                        due_date=raw.due_date,
                        quantity=raw.quantity,
                        plant_code=raw.raw_payload.get('plant_code', ''),
                        ship_to_code=raw.raw_payload.get('ship_to_code', ''),
                        source_system=raw.source_system,
                        source_file=raw.source_file
                    )
                    daily_records.append(daily)
                    raw.parse_status = 'PARSED'
                    raw.save()
                    success_count += 1

                # Save daily records
                if daily_records:
                    StgOrderDaily.objects.bulk_create(daily_records)

            return {
                'success': True,
                'message': f'Imported {len(created_raws)} raw records, created {len(daily_records)} daily records',
                'raw_count': len(created_raws),
                'daily_count': len(daily_records),
                'min_raw_id': min_raw_id,
                'max_raw_id': max_raw_id,
                'errors': self.errors,
                'warnings': self.warnings
            }

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"CSV Import Exception: {error_details}")
            return {
                'success': False,
                'message': f'Import failed: {str(e)}',
                'errors': self.errors + [str(e)]
            }

    def _normalize_header(self, name):
        """Normalize header name for comparison"""
        if name is None:
            return ''
        normalized = str(name).strip().replace(' ', '').replace('\u3000', '')
        normalized = normalized.replace('_', '').replace('-', '').upper()
        normalized = normalized.lstrip('\ufeff')
        return normalized

    def _build_header_map(self, header_row):
        """Build mapping from Japanese/English headers to standard keys"""
        header_aliases = {
            'product_code': ['品目コード', '製品コード', '製品ｺｰﾄﾞ', '品番', '品目ｺｰﾄﾞ', '図番', '商品コード', '部品番号'],
            'due_date': ['納期', '納入日', '納品日', '納入指示日', '納期日', '納入予定日'],
            'quantity': ['数量', '注文数量', '発注数量', '発注数', '指示数', '納入指示数', '納品数量'],
        }
        
        # Create alias map
        alias_map = {}
        for key, aliases in header_aliases.items():
            for alias in aliases:
                alias_map[self._normalize_header(alias)] = key
        
        # Build column map
        col_map = {}
        for idx, name in enumerate(header_row or []):
            key = alias_map.get(self._normalize_header(name))
            if key and key not in col_map:
                col_map[key] = idx
        
        return col_map

    def _extract_field(self, row, key, col_map, default=''):
        """Extract field value from row using column map"""
        col_idx = col_map.get(key)
        if col_idx is not None and col_idx < len(row):
            val = row[col_idx]
            return str(val).strip() if val is not None else default
        return default

    def _create_raw_record(self, row, row_no, customer_code, order_type, source_system, source_file, col_map=None):
        """Create a raw staging record from CSV row
        
        Args:
            row: CSV row as dict (from DictReader) or list
            row_no: Row number
            customer_code: Customer code
            order_type: Order type
            source_system: Source system name
            source_file: Source file name
            col_map: Column index map for list-based rows
        """
        # Extract fields from CSV row
        if isinstance(row, dict):
            # DictReader case - use col_map if available, otherwise try aliases/direct keys
            if col_map:
                # col_map contains indices, but row is dict - try key-based approach
                # This is a fallback for dict, prefer direct key matching
                product_code = row.get('product_code', row.get('品目コード', row.get('品番', row.get('製品コード', row.get('図番', '')))))
                due_date_str = row.get('due_date', row.get('納期', row.get('納入日', row.get('納品日', row.get('納入指示日', '')))))
                quantity_str = row.get('quantity', row.get('発注数量', row.get('数量', row.get('注文数量', row.get('発注数', '0')))))
            else:
                product_code = row.get('product_code', row.get('品目コード', row.get('品番', '')))
                due_date_str = row.get('due_date', row.get('納期', ''))
                quantity_str = row.get('quantity', row.get('発注数量', row.get('数量', '0')))
            
            product_code = str(product_code).strip() if product_code else ''
            due_date_str = str(due_date_str).strip() if due_date_str else ''
            quantity_str = str(quantity_str).strip() if quantity_str else '0'
        else:
            # List case with column map
            if col_map:
                product_code = self._extract_field(row, 'product_code', col_map)
                due_date_str = self._extract_field(row, 'due_date', col_map)
                quantity_str = self._extract_field(row, 'quantity', col_map)
            else:
                product_code = ''
                due_date_str = ''
                quantity_str = '0'

        # Parse date
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y/%m/%d').date()
                except ValueError:
                    self.warnings.append(f"Row {row_no}: Invalid date format: {due_date_str}")

        # Parse quantity
        quantity = None
        if quantity_str:
            try:
                quantity = Decimal(quantity_str)
            except:
                self.warnings.append(f"Row {row_no}: Invalid quantity: {quantity_str}")

        return StgOrderRaw(
            customer_code=customer_code,
            order_type=order_type,
            source_system=source_system,
            source_file=source_file,
            source_row_no=row_no,
            record_token=row.get('record_token', ''),
            due_date=due_date,
            product_code=product_code,
            quantity=quantity,
            raw_payload=row,
            parse_status='PENDING'
        )


    def create_orders_from_staging(self, source_file=None, raw_id_range=None):
        """
        Create orders from staging daily data

        Args:
            source_file: Optional source file name to filter records (only process this file's data)
            raw_id_range: Optional tuple of (min_raw_id, max_raw_id) to filter by raw record ID range
        """
        from django.db.models import Q

        # Get all parsed daily records
        # Support multiple raw table types (raw, raw_kubota, raw_tiera, raw_rieden)
        query = StgOrderDaily.objects.filter(
            Q(raw__parse_status='PARSED') |
            Q(raw_kubota__parse_status='PARSED') |
            Q(raw_tiera__parse_status='PARSED') |
            Q(raw_rieden__parse_status='PARSED')
        )

        # Filter by raw ID range and source file
        # IMPORTANT: Must use BOTH raw_id_range AND source_file together to avoid cross-customer data mixing
        # Different raw tables (raw_tiera, raw_rieden, raw_kubota) can have overlapping ID ranges
        if raw_id_range and raw_id_range[0] is not None and raw_id_range[1] is not None and source_file:
            # Filter by raw ID range AND source file to ensure only records from this import are processed
            query = query.filter(source_file=source_file).filter(
                Q(raw__isnull=False, raw__id__gte=raw_id_range[0], raw__id__lte=raw_id_range[1]) |
                Q(raw_kubota__isnull=False, raw_kubota__id__gte=raw_id_range[0], raw_kubota__id__lte=raw_id_range[1]) |
                Q(raw_tiera__isnull=False, raw_tiera__id__gte=raw_id_range[0], raw_tiera__id__lte=raw_id_range[1]) |
                Q(raw_rieden__isnull=False, raw_rieden__id__gte=raw_id_range[0], raw_rieden__id__lte=raw_id_range[1])
            )
        # Fallback: filter by source file only if raw_id_range is not available
        elif source_file:
            query = query.filter(source_file=source_file)

        daily_records = query.select_related('customer')

        # Group by customer, order_type, version_no
        orders_dict = {}
        for daily in daily_records:
            key = (daily.customer_id, daily.order_type, daily.version_no, daily.source_file)
            if key not in orders_dict:
                orders_dict[key] = []
            orders_dict[key].append(daily)

        created_orders = 0
        updated_orders = 0
        created_lines = 0
        created_line_ids = []
        superseded_orders = 0
        additional_order_notices = []

        with transaction.atomic():
            for (customer_id, order_type, version_no, source_file), dailies in orders_dict.items():
                # Get customer code for order_no generation
                customer = Customer.objects.get(id=customer_id)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                first_daily = dailies[0] if dailies else None
                is_kubota_special = False

                # Track latest confirmed due date per product (for Tiera-specific cleanup)
                product_cutoffs = {}

                # Generate order_no based on order_type and customer
                if order_type == 'FORECAST':
                    # For Kubota, use calc_date from raw_payload if available
                    if customer.customer_code == '000196':
                        # Try to get calc_date from raw_kubota
                        first_daily = dailies[0] if dailies else None
                        if first_daily and hasattr(first_daily, 'raw_kubota') and first_daily.raw_kubota:
                            calc_date = first_daily.raw_kubota.raw_payload.get('calc_date', '')
                            if calc_date:
                                order_no = f"FC-{customer.customer_code}-{calc_date}"
                            else:
                                order_no = f"FC-{customer.customer_code}-{timestamp}"
                        else:
                            order_no = f"FC-{customer.customer_code}-{timestamp}"
                    else:
                        # Other customers: use timestamp (partial replacement strategy)
                        order_no = f"FC-{customer.customer_code}-{timestamp}"
                else:  # FIRM
                    # For Kubota, use issue_date from raw_payload if available
                    if customer.customer_code == '000196':
                        # Try to get issue_date from raw_kubota
                        factory_label = None
                        if first_daily and hasattr(first_daily, 'raw_kubota') and first_daily.raw_kubota:
                            raw_payload = first_daily.raw_kubota.raw_payload or {}
                            # 工場コード（CSV 1列目）を最優先で工場ラベルに変換
                            plant_code = str(raw_payload.get('plant_code', '')).strip()
                            plant_factory_map = {
                                '23': 'HIRAKATA',
                                '21': 'SAKAI',
                                '92': 'KMT',
                                '76': 'KMT',
                            }
                            if plant_code in plant_factory_map:
                                factory_label = plant_factory_map[plant_code]
                            else:
                                factory_label = raw_payload.get('factory')
                                if factory_label:
                                    factory_label = str(factory_label).strip()
                            is_kubota_special = (
                                raw_payload.get('special') is True
                                or raw_payload.get('format') == 'NVAN-2'
                                or (first_daily.raw_kubota.record_type or '').strip().upper() == 'SPECIAL'
                            )
                            if not factory_label:
                                data_no = (first_daily.raw_kubota.data_no or '').strip()
                                if data_no in ('47', '49'):
                                    factory_label = 'SAKAI'
                                elif data_no == '45':
                                    factory_label = 'HIRAKATA'
                                elif data_no == '27':
                                    factory_label = 'KMT'
                            if factory_label:
                                factory_label = factory_label.upper()
                                if is_kubota_special:
                                    factory_label = f"{factory_label}-sp"
                            issue_date = raw_payload.get('issue_date', '')
                            if issue_date:
                                if factory_label:
                                    order_no = f"FIRM-{customer.customer_code}-{factory_label}-{issue_date}"
                                else:
                                    order_no = f"FIRM-{customer.customer_code}-{issue_date}"
                            else:
                                if factory_label:
                                    order_no = f"FIRM-{customer.customer_code}-{factory_label}-{timestamp}"
                                else:
                                    order_no = f"FIRM-{customer.customer_code}-{timestamp}"
                        else:
                            if factory_label:
                                order_no = f"FIRM-{customer.customer_code}-{factory_label}-{timestamp}"
                            else:
                                order_no = f"FIRM-{customer.customer_code}-{timestamp}"
                    else:
                        # For Rieden, use order_date from raw_rieden
                        if first_daily and hasattr(first_daily, 'raw_rieden') and first_daily.raw_rieden:
                            order_date = first_daily.raw_rieden.order_date
                            if order_date:
                                order_no = f"FIRM-{customer.customer_code}-{order_date.strftime('%Y%m%d')}"
                            else:
                                order_no = f"FIRM-{customer.customer_code}-{timestamp}"
                        # For Tiera, use delivery_no from raw_tiera
                        elif first_daily and hasattr(first_daily, 'raw_tiera') and first_daily.raw_tiera:
                            delivery_no = first_daily.raw_tiera.delivery_no
                            if delivery_no:
                                order_no = f"FIRM-{customer.customer_code}-{delivery_no}"
                            else:
                                order_no = f"FIRM-{customer.customer_code}-{timestamp}"
                        else:
                            # Other customers: use timestamp
                            order_no = f"FIRM-{customer.customer_code}-{timestamp}"

                additional_order_items = []

                # Create order header
                order_defaults = {
                    'customer_id': customer_id,
                    'order_no': order_no,
                    'order_type': order_type,
                    'version_no': version_no,
                    'source_system': dailies[0].source_system,
                    'source_file': source_file,
                    'order_date': datetime.now().date(),
                    'status': 'OPEN'
                }
                if is_kubota_special:
                    order, created = Order.objects.get_or_create(
                        customer_id=customer_id,
                        order_no=order_no,
                        order_type=order_type,
                        version_no=version_no,
                        defaults=order_defaults
                    )
                    if not created:
                        # Special confirmed orders are re-imported; replace existing lines.
                        order.source_system = order_defaults['source_system']
                        order.source_file = order_defaults['source_file']
                        order.order_date = order_defaults['order_date']
                        order.status = 'OPEN'
                        order.save()
                        order.lines.all().delete()
                    created_orders += 1
                    line_no = 1
                    for daily in dailies:
                        try:
                            product = Product.objects.get(product_code=daily.product_code)
                        except Product.DoesNotExist:
                            product = None
                        kubota_no = None
                        if hasattr(daily, 'raw_kubota') and daily.raw_kubota:
                            rp = daily.raw_kubota.raw_payload or {}
                            kubota_no = rp.get('kubota_order_no') or daily.raw_kubota.order_no
                        line = OrderLine.objects.create(
                            order=order,
                            line_no=line_no,
                            product=product,
                            product_code=daily.product_code,
                            order_type=order_type,
                            customer_order_no=kubota_no,
                            quantity=daily.quantity,
                            due_date=daily.due_date,
                            plant_code=daily.plant_code,
                            ship_to_code=daily.ship_to_code
                        )
                        created_line_ids.append(line.id)
                        line_no += 1
                        created_lines += 1
                    continue  # skip generic line creation below

                elif customer.customer_code == '000196' and order_type == 'FIRM':
                    # クボタFIRM（非special）: 発注番号で追加/重複を行単位で判断
                    #   既存OPEN FIRM行(同製品+同日付)なし
                    #     - 同じ発行日で複数ファイルあり           → additional（order_no + "-tuika2"）
                    #     - 単独                                  → regular（通常 order_no）
                    #   既存あり、発注番号が違う                  → additional（order_no + "-tuika"）
                    #   既存あり、発注番号が同じ                  → 重複取込 → スキップ
                    def _get_kubota_no(d):
                        if hasattr(d, 'raw_kubota') and d.raw_kubota:
                            rp = d.raw_kubota.raw_payload or {}
                            return rp.get('kubota_order_no') or d.raw_kubota.order_no
                        return None

                    # 同じ order_no で複数ファイルがあるかチェック
                    def _check_duplicate_order_no(order_no_val):
                        """同じ order_no の Order がすでに存在するかチェック
                        
                        ロジック：
                        - ファイルA取込時：Order なし → False → regular になる
                        - ファイルB取込時：ファイルAの Order あり → True → -tuika2 になる
                        
                        exists() は SQL インデックスヒットで高速
                        """
                        if not order_no_val:
                            return False
                        return Order.objects.filter(
                            customer_id=customer_id,
                            order_type=order_type,
                            order_no=order_no_val
                        ).exists()
                    regular_dailies = []
                    additional_dailies = []
                    additional_tuika2_dailies = []
                    skipped_dup_count = 0

                    # 生成された order_no で複数ファイルがあるかチェック
                    has_duplicate_order_no = _check_duplicate_order_no(order_no)

                    for daily in dailies:
                        new_no = _get_kubota_no(daily)
                        existing_qs = OrderLine.objects.filter(
                            order__customer_id=customer_id,
                            order__order_type='FIRM',
                            order__status='OPEN',
                            product_code=daily.product_code,
                            due_date=daily.due_date,
                        )
                        if not existing_qs.exists():
                            # 同製品+同納期の既存行がない場合
                            if has_duplicate_order_no:
                                # order_no が重複 → -tuika2 対象
                                additional_tuika2_dailies.append(daily)
                            else:
                                # order_no が単独 → 通常
                                regular_dailies.append(daily)
                        elif new_no and new_no not in set(existing_qs.values_list('customer_order_no', flat=True)):
                            # 既存あり、発注番号が違う → -tuika 対象
                            additional_dailies.append(daily)
                        else:
                            # 同一発注番号が既に存在 → 重複取込のためスキップ
                            skipped_dup_count += 1

                    if skipped_dup_count:
                        self.warnings.append(
                            f'{skipped_dup_count}件は同一発注番号が既に存在するためスキップしました（重複取込）'
                        )

                    # 通常グループ: get_or_create（一意違反回避）
                    if regular_dailies:
                        reg_order, _ = Order.objects.get_or_create(
                            customer_id=customer_id,
                            order_no=order_no,
                            order_type=order_type,
                            version_no=version_no,
                            defaults=order_defaults
                        )
                        line_no = reg_order.lines.count() + 1
                        for daily in regular_dailies:
                            cutoff = product_cutoffs.get(daily.product_code)
                            if cutoff is None or daily.due_date > cutoff:
                                product_cutoffs[daily.product_code] = daily.due_date
                            try:
                                product = Product.objects.get(product_code=daily.product_code)
                            except Product.DoesNotExist:
                                product = None
                            line = OrderLine.objects.create(
                                order=reg_order,
                                line_no=line_no,
                                product=product,
                                product_code=daily.product_code,
                                order_type=order_type,
                                customer_order_no=_get_kubota_no(daily),
                                quantity=daily.quantity,
                                due_date=daily.due_date,
                                plant_code=daily.plant_code,
                                ship_to_code=daily.ship_to_code
                            )
                            created_line_ids.append(line.id)
                            line_no += 1
                            created_lines += 1
                        created_orders += 1

                    # 追加注文グループ: order_no に -tuika を付与
                    if additional_dailies:
                        tuika_order_no = f"{order_no}-tuika"
                        tuika_defaults = {**order_defaults, 'order_no': tuika_order_no}
                        tuika_order, _ = Order.objects.get_or_create(
                            customer_id=customer_id,
                            order_no=tuika_order_no,
                            order_type=order_type,
                            version_no=version_no,
                            defaults=tuika_defaults
                        )
                        line_no = tuika_order.lines.count() + 1
                        for daily in additional_dailies:
                            cutoff = product_cutoffs.get(daily.product_code)
                            if cutoff is None or daily.due_date > cutoff:
                                product_cutoffs[daily.product_code] = daily.due_date
                            try:
                                product = Product.objects.get(product_code=daily.product_code)
                            except Product.DoesNotExist:
                                product = None
                            line = OrderLine.objects.create(
                                order=tuika_order,
                                line_no=line_no,
                                product=product,
                                product_code=daily.product_code,
                                order_type=order_type,
                                customer_order_no=_get_kubota_no(daily),
                                quantity=daily.quantity,
                                due_date=daily.due_date,
                                plant_code=daily.plant_code,
                                ship_to_code=daily.ship_to_code
                            )
                            created_line_ids.append(line.id)
                            line_no += 1
                            created_lines += 1
                        created_orders += 1

                    # 発行日重複グループ: order_no に -tuika2-{取込日} を付与
                    if additional_tuika2_dailies:
                        # ファイル名から取込日を抽出（最初の8文字 YYYYMMDD）
                        import_date = ''
                        if source_file and len(source_file) >= 8:
                            # パターン: 20260304取込済_RCV_JVAN - 47sakai.csv
                            import_date = source_file[:8]
                            # 数字8文字だけ抽出（日付形式確認）
                            if not import_date.isdigit():
                                import_date = ''
                        
                        if import_date:
                            tuika2_order_no = f"{order_no}-tuika2-{import_date}"
                        else:
                            # フォールバック：日付が取得できない場合はタイムスタンプ
                            tuika2_order_no = f"{order_no}-tuika2-{timestamp}"
                        
                        tuika2_defaults = {**order_defaults, 'order_no': tuika2_order_no}
                        tuika2_order, _ = Order.objects.get_or_create(
                            customer_id=customer_id,
                            order_no=tuika2_order_no,
                            order_type=order_type,
                            version_no=version_no,
                            defaults=tuika2_defaults
                        )
                        line_no = tuika2_order.lines.count() + 1
                        for daily in additional_tuika2_dailies:
                            cutoff = product_cutoffs.get(daily.product_code)
                            if cutoff is None or daily.due_date > cutoff:
                                product_cutoffs[daily.product_code] = daily.due_date
                            try:
                                product = Product.objects.get(product_code=daily.product_code)
                            except Product.DoesNotExist:
                                product = None
                            line = OrderLine.objects.create(
                                order=tuika2_order,
                                line_no=line_no,
                                product=product,
                                product_code=daily.product_code,
                                order_type=order_type,
                                customer_order_no=_get_kubota_no(daily),
                                quantity=daily.quantity,
                                due_date=daily.due_date,
                                plant_code=daily.plant_code,
                                ship_to_code=daily.ship_to_code
                            )
                            created_line_ids.append(line.id)
                            line_no += 1
                            created_lines += 1
                        created_orders += 1

                    continue  # skip generic line creation below

                else:
                    if order_type == 'FORECAST':
                        # FORECAST再取込対応: 同一order_noの既存注文があれば行を置換
                        order, created = Order.objects.get_or_create(
                            customer_id=customer_id,
                            order_no=order_no,
                            order_type=order_type,
                            version_no=version_no,
                            defaults=order_defaults
                        )
                        if created:
                            created_orders += 1
                        else:
                            order.source_system = order_defaults['source_system']
                            order.source_file = order_defaults['source_file']
                            order.order_date = order_defaults['order_date']
                            order.status = 'OPEN'
                            order.save()
                            order.lines.all().delete()
                            updated_orders += 1
                    else:
                        order = Order.objects.create(**order_defaults)
                        created_orders += 1

                # Process order lines
                if order_type == 'FORECAST':
                    # For FORECAST: Partial replacement strategy
                    # Kubota(000196) は納入先単位で上書きし、別納入先（例: ZGHC）を巻き込まない
                    if customer.customer_code == '000196':
                        product_shipto_earliest_dates = {}
                        for daily in dailies:
                            ship_to = (daily.ship_to_code or '').strip()
                            key = (daily.product_code, ship_to)
                            current_earliest = product_shipto_earliest_dates.get(key)
                            if current_earliest is None or daily.due_date < current_earliest:
                                product_shipto_earliest_dates[key] = daily.due_date

                        # 自分自身（再取込で再利用した注文）は除外する
                        for (product_code, ship_to), earliest_date in product_shipto_earliest_dates.items():
                            q = Order.objects.filter(
                                customer_id=customer_id,
                                order_type='FORECAST',
                                status='OPEN',
                                lines__product_code=product_code,
                                lines__due_date__gte=earliest_date,
                            ).exclude(id=order.id)

                            if ship_to:
                                q = q.filter(lines__ship_to_code=ship_to)
                            else:
                                q = q.filter(Q(lines__ship_to_code__isnull=True) | Q(lines__ship_to_code=''))

                            superseded_count = q.distinct().update(status='SUPERSEDED')
                            superseded_orders += superseded_count
                    else:
                        # その他得意先: 従来どおり品番単位
                        product_earliest_dates = {}
                        for daily in dailies:
                            current_earliest = product_earliest_dates.get(daily.product_code)
                            if current_earliest is None or daily.due_date < current_earliest:
                                product_earliest_dates[daily.product_code] = daily.due_date

                        # 自分自身（再取込で再利用した注文）は除外する
                        for product_code, earliest_date in product_earliest_dates.items():
                            superseded_count = Order.objects.filter(
                                customer_id=customer_id,
                                order_type='FORECAST',
                                status='OPEN',
                                lines__product_code=product_code,
                                lines__due_date__gte=earliest_date
                            ).exclude(id=order.id).distinct().update(status='SUPERSEDED')
                            superseded_orders += superseded_count

                    # Create new order lines
                    line_no = 1
                    for daily in dailies:
                        # Find product
                        try:
                            product = Product.objects.get(product_code=daily.product_code)
                        except Product.DoesNotExist:
                            product = None

                        line = OrderLine.objects.create(
                            order=order,
                            line_no=line_no,
                            product=product,
                            product_code=daily.product_code,
                            order_type=order_type,
                            quantity=daily.quantity,
                            due_date=daily.due_date,
                            plant_code=daily.plant_code,
                            ship_to_code=daily.ship_to_code
                        )
                        created_line_ids.append(line.id)
                        created_lines += 1
                        line_no += 1

                else:  # FIRM（クボタ以外: ティエラ、リーデン等）
                    line_no = 1
                    for daily in dailies:
                        # Find product
                        try:
                            product = Product.objects.get(product_code=daily.product_code)
                        except Product.DoesNotExist:
                            product = None

                        # Store latest due date per product for Tiera cleanup
                        cutoff = product_cutoffs.get(daily.product_code)
                        if cutoff is None or daily.due_date > cutoff:
                            product_cutoffs[daily.product_code] = daily.due_date

                        # Get customer_order_no from raw record
                        customer_order_no = None
                        if hasattr(daily, 'raw_rieden') and daily.raw_rieden:
                            customer_order_no = daily.raw_rieden.order_no
                        elif hasattr(daily, 'raw_tiera') and daily.raw_tiera:
                            customer_order_no = daily.raw_tiera.order_document_no

                        line = OrderLine.objects.create(
                            order=order,
                            line_no=line_no,
                            product=product,
                            product_code=daily.product_code,
                            order_type=order_type,
                            customer_order_no=customer_order_no,
                            quantity=daily.quantity,
                            due_date=daily.due_date,
                            plant_code=daily.plant_code,
                            ship_to_code=daily.ship_to_code
                        )
                        created_line_ids.append(line.id)
                        line_no += 1
                        created_lines += 1

                # 確定インポート時は内示をSUPERSEDEDにしない
                # 内示インポート時のみ、古い内示をSUPERSEDEDにする
                # （確定と内示は別々に管理する）
                if additional_order_items:
                    additional_order_notices.append({
                        'order_no': order_no,
                        'source_file': source_file,
                        'items': additional_order_items,
                    })

        return {
            'orders': created_orders,
            'updated_orders': updated_orders,
            'lines': created_lines,
            'created_line_ids': created_line_ids,
            'deleted_forecast_orders': superseded_orders,
            'additional_order_notices': additional_order_notices,
        }

    @staticmethod
    def get_active_order_lines_for_scheduling(customer_id=None, product_code=None,
                                               start_date=None, end_date=None,
                                               aggregate=True):
        """
        Get active order lines for scheduling.

        Priority: FIRM orders with status='OPEN' take precedence over FORECAST orders.
        If a FIRM order exists for a specific product/date, FORECAST orders are ignored.

        When multiple order lines exist for the same product_code + due_date combination
        (e.g., 10+ order lines with different order numbers), this method can either:
        - Return aggregated quantities (aggregate=True, default): Sums quantities by
          product_code + due_date for scheduling calculations
        - Return individual lines (aggregate=False): Preserves all order line details
          including individual order numbers for reference

        Args:
            customer_id: Filter by customer (optional)
            product_code: Filter by product code (optional)
            start_date: Filter by due_date >= start_date (optional)
            end_date: Filter by due_date <= end_date (optional)
            aggregate: If True (default), aggregate quantities by product_code + due_date.
                      If False, return individual order lines with all details.

        Returns:
            If aggregate=True: QuerySet with aggregated data containing:
                - customer_id
                - customer_code
                - product_code
                - due_date
                - total_quantity (sum of all quantities)
                - order_type (FIRM or FORECAST)
                - line_count (number of individual order lines)
                - order_numbers (comma-separated list of order numbers)

            If aggregate=False: QuerySet of OrderLine objects with all details
        """
        from django.db.models import Q, Sum, Count, F
        from django.db.models.functions import Coalesce

        # Base query: Only OPEN orders
        queryset = OrderLine.objects.filter(order__status='OPEN')

        # Apply filters
        if customer_id:
            queryset = queryset.filter(order__customer_id=customer_id)
        if product_code:
            queryset = queryset.filter(product_code=product_code)
        if start_date:
            queryset = queryset.filter(due_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(due_date__lte=end_date)

        if aggregate:
            # Aggregate quantities by product_code + due_date
            # Group by customer, product, due_date, and order_type
            aggregated = queryset.values(
                'order__customer_id',
                'order__customer__customer_code',
                'product_code',
                'due_date',
                'order__order_type'
            ).annotate(
                total_quantity=Sum('quantity'),
                line_count=Count('id'),
                customer_id=F('order__customer_id'),
                customer_code=F('order__customer__customer_code'),
                order_type=F('order__order_type')
            ).order_by('due_date', 'order__order_type', 'product_code')

            return aggregated
        else:
            # Return individual order lines with all details
            return queryset.select_related(
                'order',
                'order__customer',
                'product'
            ).order_by('due_date', 'order__order_type', 'product_code', 'order__order_no', 'line_no')
