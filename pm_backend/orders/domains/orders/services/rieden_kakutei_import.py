import csv
import unicodedata
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from orders.domains.orders.models import StgOrderRawRieden, StgOrderDaily
from masters.models import Customer, Product


class RiedenKakuteiImportService:
    """Rieden Kakutei (Confirmed) CSV Import Service

    Format: 発注先コード=509 type
    - Column 0: Order No (発注番号) - Customer's order number
    - Column 1: Order Code (発注先コード) = "509" - Identifier
    - Simple 1 row = 1 order line format

    Column mapping:
    - Column 0: order_no (発注番号)
    - Column 1: order_code (発注先コード) = "509"
    - Column 2+: Other fields (product_code, delivery_date, quantity, etc.)
    """

    IDENTIFIER_COL = 1  # 発注先コード
    IDENTIFIER_VALUE = '509'
    COL_ORDER_NO = 0  # 発注番号
    COL_ORDER_DATE = 2  # 発注日
    COL_PRODUCT_CODE = 5  # 製品コード
    COL_DELIVERY_DATE = 9  # 納期
    COL_QUANTITY = 10  # 数量

    # 納入先コード関連
    SHIP_TO_KEYWORDS = ('納入', '納入先', 'delivery')
    SHIP_TO_CODE_KEYWORDS = ('コード', 'ｺｰﾄﾞ', 'code', 'cd')
    SHIP_TO_LEAD_TIME_DAYS = {
        '000010': 2,  # 納入先コード 000010 → 2営業日前出荷
        '000030': 2,  # 納入先コード 000030 → 2営業日前出荷
        '000050': 0,  # 納入先コード 000050 → 当日出荷
    }

    HEADER_ALIASES = {
        'order_no': ['発注番号', '発注No', '注文番号', '注文No', '受注番号'],
        'order_date': ['発注日', '発注年月日', '注文日', '受注日'],
        'identifier': ['発注先コード', '発注先ｺｰﾄﾞ', '発注CD', '発注コード', '発注ｺｰﾄﾞ'],
        'product_code': ['品目コード', '製品コード', '製品ｺｰﾄﾞ', '品番', '品目コード', '品目ｺｰﾄﾞ', '図番', '商品コード', '部品番号'],
        'delivery_date': ['納期', '納入日', '納品日', '納入指示日', '納期日', '納入予定日'],
        'quantity': ['数量', '注文数量', '発注数量', '発注数', '指示数', '納入指示数', '納品数量'],
        'ship_to_code': ['納入先コード', '納入先ｺｰﾄﾞ', '納入コード', '納入ｺｰﾄﾞ', '配送先コード', 'delivery code', 'ship to code'],
    }

    def __init__(self):
        self.errors = []
        self.warnings = []

    def decode_file(self, file):
        """Decode CSV file with multiple encoding attempts"""
        file.seek(0)
        raw_data = file.read()

        encodings = ['cp932', 'shift-jis', 'utf-8-sig', 'utf-8', 'iso-2022-jp']
        for encoding in encodings:
            try:
                return raw_data.decode(encoding), encoding
            except UnicodeDecodeError:
                continue

        return None, None

    def parse_date(self, date_str):
        """Parse date string in multiple formats"""
        if not date_str or date_str == '':
            return None

        date_str = str(date_str).strip()

        # Try YYYYMMDD format
        if len(date_str) == 8 and date_str.isdigit():
            try:
                return datetime.strptime(date_str, '%Y%m%d').date()
            except ValueError:
                pass

        # Try YYYY/MM/DD format
        if '/' in date_str:
            try:
                return datetime.strptime(date_str, '%Y/%m/%d').date()
            except ValueError:
                pass

        # Try YYYY-MM-DD format
        if '-' in date_str:
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        return None

    def parse_quantity(self, quantity_str):
        """Parse quantity string to Decimal"""
        if not quantity_str or quantity_str == '':
            return None

        try:
            quantity_str = str(quantity_str).strip().replace(',', '')
            return Decimal(quantity_str)
        except:
            return None

    def _normalize_header(self, name):
        if name is None:
            return ''
        normalized = str(name).strip().replace(' ', '').replace('\u3000', '')
        normalized = normalized.replace('_', '').replace('-', '').upper()
        normalized = normalized.lstrip('\ufeff')
        return normalized

    def _build_col_map(self, header_row):
        alias_map = {}
        for key, aliases in self.HEADER_ALIASES.items():
            for alias in aliases:
                alias_map[self._normalize_header(alias)] = key

        col_map = {}
        for idx, name in enumerate(header_row or []):
            key = alias_map.get(self._normalize_header(name))
            if key and key not in col_map:
                col_map[key] = idx
        return col_map

    def _looks_like_header(self, row):
        return bool(self._build_col_map(row))

    def _normalize_identifier(self, value):
        if value is None:
            return ''
        text = str(value).strip().lstrip('\ufeff')
        if text == '':
            return ''
        try:
            normalized = text.replace(',', '')
            dec = Decimal(normalized)
            if dec == dec.to_integral():
                return str(dec.to_integral())
        except Exception:
            pass
        return text

    def _normalize_ship_to_code(self, value):
        """納入先コードの正規化

        処理内容：
        1. Unicode正規化（NFKC）- 全角→半角変換
        2. ハイフン・スペース除去
        3. 数字のみの場合、6桁ゼロパディング

        Args:
            value: 納入先コード文字列

        Returns:
            正規化された納入先コード
        """
        if not value or str(value).strip() == '' or str(value) == 'nan':
            return ''

        normalized = unicodedata.normalize('NFKC', str(value).strip())
        normalized = normalized.replace('-', '').replace(' ', '').replace('　', '')

        if normalized.isdigit():
            normalized = normalized.zfill(6)

        return normalized

    def _find_ship_to_code_column(self, columns):
        """納入先コード列を検出

        Args:
            columns: CSV列名リスト

        Returns:
            納入先コード列名（見つからない場合はNone）
        """
        for col in columns:
            normalized = unicodedata.normalize('NFKC', str(col)).lower()

            # キーワードマッチング
            has_ship_to = any(keyword in normalized for keyword in self.SHIP_TO_KEYWORDS)
            has_code = any(keyword in normalized for keyword in self.SHIP_TO_CODE_KEYWORDS)

            if has_ship_to and has_code:
                return col

            # 英語パターン
            if 'delivery' in normalized and 'code' in normalized:
                return col
            if 'ship' in normalized and 'to' in normalized and 'code' in normalized:
                return col

        return None

    def _infer_columns(self, sample_rows):
        for row in sample_rows:
            for idx, cell in enumerate(row):
                if self._normalize_identifier(cell) != self.IDENTIFIER_VALUE:
                    continue

                # 発注先コード列（識別子）を見つけた
                identifier_col = idx

                # 発注番号は識別子の前にあるはず（通常は列0）
                order_no_col = None
                order_date_col = None
                if identifier_col > 0:
                    # 識別子の前の列をチェック
                    for j in range(identifier_col - 1, -1, -1):
                        cell_val = str(row[j]).strip() if j < len(row) else ''
                        if not cell_val:
                            continue
                        # 日付形式なら発注日候補
                        if self.parse_date(cell_val):
                            if order_date_col is None:
                                order_date_col = j
                        else:
                            # 日付でなければ発注番号候補
                            if order_no_col is None:
                                order_no_col = j

                # 納期を探す（識別子の後）
                date_idx = None
                for j in range(identifier_col + 1, len(row)):
                    if self.parse_date(row[j]):
                        date_idx = j
                        break
                if date_idx is None:
                    continue

                # 数量を探す（納期の後）
                qty_idx = None
                for j in range(date_idx + 1, len(row)):
                    if self.parse_quantity(row[j]):
                        qty_idx = j
                        break
                if qty_idx is None:
                    continue

                # 製品コードを探す（識別子と納期の間）
                product_idx = None
                for j in range(identifier_col + 1, date_idx):
                    cell_val = str(row[j]).strip() if j < len(row) else ''
                    if not cell_val:
                        continue
                    if self.parse_date(cell_val):
                        continue
                    product_idx = j
                    break

                if product_idx is None:
                    product_idx = identifier_col + 1 if identifier_col + 1 < len(row) else None

                if product_idx is None:
                    continue

                return {
                    'order_no_col': order_no_col,
                    'order_date_col': order_date_col,
                    'identifier_col': identifier_col,
                    'product_code_col': product_idx,
                    'delivery_date_col': date_idx,
                    'quantity_col': qty_idx,
                }
        return None

    def import_csv(self, file, customer_code, order_type, source_system='CSV'):
        """Import Rieden confirmed order CSV (発注コード=509)

        Args:
            file: Uploaded file object
            customer_code: Customer code (should be Rieden's code)
            order_type: Should be 'FIRM'
            source_system: Source system name

        Returns:
            dict: Import result with statistics
        """
        self.errors = []
        self.warnings = []

        try:
            # Decode file
            decoded_file, encoding = self.decode_file(file)
            if decoded_file is None:
                return {
                    'success': False,
                    'message': 'Failed to decode CSV file',
                    'errors': ['Unsupported encoding']
                }

            # Parse CSV
            lines = decoded_file.splitlines()
            csv_reader = csv.reader(lines)
            rows = list(csv_reader)

            raw_records = []
            col_map = {}

            header_detected = bool(rows and self._looks_like_header(rows[0]))
            if header_detected:
                col_map = self._build_col_map(rows[0])
                data_rows = rows[1:]
            else:
                data_rows = rows

            sample_rows = data_rows[:20]
            inferred_cols = self._infer_columns(sample_rows)

            order_no_col = col_map.get('order_no', self.COL_ORDER_NO)
            order_date_col = col_map.get('order_date', self.COL_ORDER_DATE)
            identifier_col = col_map.get('identifier', self.IDENTIFIER_COL)
            product_code_col = col_map.get('product_code', self.COL_PRODUCT_CODE)
            delivery_date_col = col_map.get('delivery_date', self.COL_DELIVERY_DATE)
            quantity_col = col_map.get('quantity', self.COL_QUANTITY)
            ship_to_code_col = col_map.get('ship_to_code')

            # 納入先コード列を自動検出
            if not ship_to_code_col and header_detected:
                ship_to_code_col = self._find_ship_to_code_column(rows[0])
                if ship_to_code_col:
                    self.warnings.append(f"Auto-detected ship_to_code column: {ship_to_code_col}")

            used_inferred = False
            if inferred_cols:
                if 'order_no' not in col_map and inferred_cols.get('order_no_col') is not None:
                    order_no_col = inferred_cols['order_no_col']
                    used_inferred = True
                if 'order_date' not in col_map and inferred_cols.get('order_date_col') is not None:
                    order_date_col = inferred_cols['order_date_col']
                    used_inferred = True
                if 'identifier' not in col_map:
                    identifier_col = inferred_cols['identifier_col']
                    used_inferred = True
                if 'product_code' not in col_map:
                    product_code_col = inferred_cols['product_code_col']
                    used_inferred = True
                if 'delivery_date' not in col_map:
                    delivery_date_col = inferred_cols['delivery_date_col']
                    used_inferred = True
                if 'quantity' not in col_map:
                    quantity_col = inferred_cols['quantity_col']
                    used_inferred = True
                if used_inferred:
                    self.warnings.append(
                        f"Auto-detected columns: 発注番号={order_no_col}, 発注日={order_date_col}, 発注先コード={identifier_col}, 製品コード={product_code_col}, 納期={delivery_date_col}, 数量={quantity_col}"
                    )

            row_offset = 1 if header_detected else 0
            for row_no, row in enumerate(data_rows, start=1 + row_offset):

                # Check minimum columns
                required_cols = max(identifier_col, product_code_col,
                                   delivery_date_col, quantity_col) + 1
                if len(row) < required_cols:
                    continue

                # Filter by identifier
                identifier_value = self._normalize_identifier(
                    row[identifier_col] if len(row) > identifier_col else ''
                )
                if identifier_value != self.IDENTIFIER_VALUE:
                    continue

                try:
                    # Extract data
                    order_no = row[order_no_col].strip() if order_no_col is not None and len(row) > order_no_col else ''
                    order_date_str = row[order_date_col].strip() if order_date_col is not None and len(row) > order_date_col else ''
                    product_code = row[product_code_col].strip() if len(row) > product_code_col else ''
                    delivery_date_str = row[delivery_date_col].strip() if len(row) > delivery_date_col else ''
                    quantity_str = row[quantity_col].strip() if len(row) > quantity_col else ''

                    # 納入先コードを抽出
                    ship_to_code = ''
                    if ship_to_code_col:
                        # ヘッダーから列位置を取得
                        if isinstance(ship_to_code_col, str):
                            # 列名の場合、インデックスを検索
                            try:
                                col_idx = rows[0].index(ship_to_code_col) if header_detected else None
                                if col_idx is not None and len(row) > col_idx:
                                    ship_to_code = self._normalize_ship_to_code(row[col_idx])
                            except (ValueError, IndexError):
                                pass
                        elif isinstance(ship_to_code_col, int) and len(row) > ship_to_code_col:
                            # 列インデックスの場合
                            ship_to_code = self._normalize_ship_to_code(row[ship_to_code_col])

                    if not product_code:
                        continue

                    # Parse order date
                    order_date = self.parse_date(order_date_str) if order_date_str else None

                    # Parse due date
                    due_date = self.parse_date(delivery_date_str)
                    if not due_date:
                        self.warnings.append(f"Row {row_no}: Invalid date: {delivery_date_str}")
                        continue

                    # Parse quantity
                    quantity = self.parse_quantity(quantity_str)
                    if not quantity:
                        self.warnings.append(f"Row {row_no}: Invalid or zero quantity: {quantity_str}")
                        continue

                    # Create raw record
                    raw_record = StgOrderRawRieden(
                        customer_code=customer_code,
                        order_type=order_type,
                        source_system=source_system,
                        source_file=file.name,
                        source_row_no=row_no,
                        order_no=order_no,
                        order_date=order_date,
                        order_code=self.IDENTIFIER_VALUE,
                        product_code=product_code,
                        due_date=due_date,
                        quantity=quantity,
                        raw_payload={
                            'row': row,
                            'encoding': encoding,
                            'ship_to_code': ship_to_code
                        },
                        parse_status='PENDING'
                    )
                    raw_records.append(raw_record)

                except Exception as e:
                    self.errors.append(f"Row {row_no}: {str(e)}")

            if not raw_records:
                warnings = list(self.warnings)
                warnings.append('Column positions may need adjustment. Check COL_* constants.')
                return {
                    'success': False,
                    'message': f'No valid records found with 発注コード=509',
                    'errors': self.errors,
                    'warnings': warnings
                }

            # Save to database
            raw_count, daily_count, min_raw_id, max_raw_id = self.save_to_database(raw_records, file, customer_code)

            return {
                'success': True,
                'message': f'Imported {raw_count} raw records, created {daily_count} daily records',
                'raw_count': raw_count,
                'daily_count': daily_count,
                'min_raw_id': min_raw_id,
                'max_raw_id': max_raw_id,
                'errors': self.errors,
                'warnings': self.warnings
            }

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Rieden Kakutei Import Exception: {error_details}")
            return {
                'success': False,
                'message': f'Import failed: {str(e)}',
                'errors': self.errors + [str(e)]
            }

    def save_to_database(self, raw_records, file, customer_code):
        """Save raw records and create daily records

        Returns:
            tuple: (raw_count, daily_count, min_raw_id, max_raw_id)
        """
        with transaction.atomic():
            # Save raw records
            StgOrderRawRieden.objects.bulk_create(raw_records)

            # Re-fetch to get primary keys
            raw_records_with_ids = StgOrderRawRieden.objects.filter(
                source_file=file.name,
                customer_code=customer_code
            ).order_by('-id')[:len(raw_records)]

            # Track min and max IDs
            raw_ids = [r.id for r in raw_records_with_ids]
            min_raw_id = min(raw_ids) if raw_ids else None
            max_raw_id = max(raw_ids) if raw_ids else None

            # Find customer
            try:
                customer = Customer.objects.get(customer_code=customer_code)
            except Customer.DoesNotExist:
                raise ValueError(f'Customer not found: {customer_code}')

            # Create daily records
            daily_records = []
            error_count = 0

            for raw in raw_records_with_ids:
                if not raw.product_code or not raw.due_date or not raw.quantity:
                    raw.parse_status = 'ERROR'
                    raw.error_message = 'Missing required fields'
                    raw.save()
                    error_count += 1
                    continue

                try:
                    # Auto-register product if not exists
                    product, created = Product.objects.get_or_create(
                        product_code=raw.product_code,
                        defaults={
                            'product_name': raw.product_code,  # Use code as name initially
                            'category': 'PURCHASED',
                            'unit': '個',
                            'is_active': True,
                            'is_final_product': True
                        }
                    )
                    if created:
                        self.warnings.append(f'Auto-registered new product: {raw.product_code}')

                    # 納入先コードを取得
                    ship_to_code = raw.raw_payload.get('ship_to_code', '') if raw.raw_payload else ''

                    # Create daily record
                    daily = StgOrderDaily(
                        raw_rieden=raw,
                        customer=customer,
                        order_type=raw.order_type,
                        version_no='v1',
                        product_code=raw.product_code,
                        due_date=raw.due_date,
                        quantity=raw.quantity,
                        ship_to_code=ship_to_code,
                        source_system=raw.source_system,
                        source_file=raw.source_file
                    )
                    daily_records.append(daily)

                    raw.parse_status = 'PARSED'
                    raw.save()

                except Exception as e:
                    raw.parse_status = 'ERROR'
                    raw.error_message = str(e)
                    raw.save()
                    error_count += 1
                    self.errors.append(f"Product {raw.product_code}: {str(e)}")

            # Save daily records
            if daily_records:
                StgOrderDaily.objects.bulk_create(daily_records)

        return len(raw_records), len(daily_records), min_raw_id, max_raw_id
