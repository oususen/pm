import csv
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from orders.core.models import StgOrderRawKubota, StgOrderDaily
from masters.models import Customer, Product
from orders.core.services.ship_to_utils import ensure_ship_to_records


class KubotaHirakataKakuteiImportService:
    """Kubota Hirakata Kakutei (Confirmed) CSV Import Service

    Format NO=45 (RCV_NVAN.csv):
    - Column 0: NO (データNo) = "45"
    - Column 3: Order No (注番)
    - Column 5: Product Code (品番)
    - Column 8: Product Name (品名)
    - Column 18: Delivery Date (納入指示日) - YYMMDD format
    - Column 21: issue_date (発行日) - YYMMDD format (Order識別用)
    - Column 19: Quantity (納入指示数)
    - Column 13: Ship To (納入場所)

    Format NO=47 (RCV_NVAN.csv / NVAN-2 mixed in same file):
    - Column 0: NO (データNo) = "47"
    - Column 3: Order No (注番)
    - Column 5: Product Code (品番)
    - Column 10: Product Name (品名)
    - Column 14: Inspection Type (検区)
    - Column 23: Delivery Date (納期) - MMDD / MDD / YYMMDD / YYYYMMDD
    - Column 24: Quantity (指示数)
    - Column 26: issue_date (発行日) - YYMMDD format (Order識別用)
    - Column 12: Ship To (納場所)
    """

    # Supported formats
    DATA_NO_45 = '45'
    DATA_NO_47 = '47'

    # Column positions
    COL_DATA_NO = 0
    COL_FACTORY = 1
    COL_ORDER_NO = 3
    COL_SHIP_TO_45 = 13
    COL_SHIP_TO_47 = 12
    COL_SHIP_TO_NAME_47 = 13
    COL_PRODUCT_CODE_45 = 5
    COL_PRODUCT_NAME_45 = 8
    COL_DELIVERY_DATE_45 = 18
    COL_QUANTITY_45 = 19
    COL_ISSUE_DATE_45 = 21  # 発行日 (T_ORDER.ORDER_NO識別用)
    COL_INSPECTION_TYPE = 10

    COL_PRODUCT_CODE_47 = 5
    COL_PRODUCT_NAME_47 = 10
    COL_INSPECTION_TYPE_47 = 14
    COL_DELIVERY_DATE_47 = 23
    COL_QUANTITY_47 = 24
    COL_ISSUE_DATE_47 = 26  # 発行日 (T_ORDER.ORDER_NO識別用)
    
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

    def _is_2027_format(self, rows):
        """2027年以降の新形式を判定する"""
        if not rows:
            return False

        # 現行枚方確定は 34列・注番ベース。
        # これと異なる時点で新形式扱いに寄せる。
        if len(rows[0]) != 34:
            return True

        header = [
            str(col or '').strip().replace(' ', '').replace('　', '')
            for col in rows[0]
        ]
        if '注番' not in header:
            return True
        if '発注番号' in header:
            return True

        sample_rows = []
        for row in rows[1:]:
            data_no = row[self.COL_DATA_NO].strip() if len(row) > self.COL_DATA_NO else ''
            if data_no not in (self.DATA_NO_45, self.DATA_NO_47):
                continue
            sample_rows.append(row)
            if len(sample_rows) >= 5:
                break

        for row in sample_rows:
            data_no = row[self.COL_DATA_NO].strip() if len(row) > self.COL_DATA_NO else ''
            legacy_order_no = row[self.COL_ORDER_NO].strip() if len(row) > self.COL_ORDER_NO else ''
            new_order_no = row[33].strip() if len(row) > 33 else ''
            if data_no == self.DATA_NO_47 and not legacy_order_no and new_order_no:
                return True

        return False

    def parse_date_from_yymmdd(self, date_str):
        """Parse date from YYMMDD format to date object

        Examples: "260108" → 2026-01-08
        """
        if not date_str or date_str == '':
            return None

        date_str = str(date_str).strip()

        # YYMMDD format (6 digits)
        if len(date_str) == 6 and date_str.isdigit():
            try:
                yy = int(date_str[:2])
                mm = int(date_str[2:4])
                dd = int(date_str[4:6])
                yyyy = 2000 + yy
                return datetime(yyyy, mm, dd).date()
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

    def parse_date_from_mmdd(self, date_str, base_date=None):
        """Parse date string in MMDD/MDD format with year inference.

        Examples:
            "0115" -> 2026-01-15 (year inferred)
            "317"  -> 2026-03-17 (year inferred)
        """
        if not date_str or str(date_str).strip() == '':
            return None

        s = str(date_str).strip()
        if not s.isdigit():
            return None

        if base_date is None:
            base_date = datetime.today().date()

        def _infer_year(mm: int) -> int:
            year = base_date.year
            if mm > base_date.month + 6:
                return year - 1
            if mm < base_date.month - 6:
                return year + 1
            return year

        try:
            if len(s) == 4:
                mm = int(s[:2]); dd = int(s[2:4])
                return datetime(_infer_year(mm), mm, dd).date()
            if len(s) == 3:
                mm = int(s[0]); dd = int(s[1:3])
                return datetime(_infer_year(mm), mm, dd).date()
        except ValueError:
            return None

        return None

    def import_csv(self, file, customer_code, order_type, source_system='CSV'):
        """Import Kubota Hirakata confirmed order CSV (NO=45 / NO=47)

        Args:
            file: Uploaded file object
            customer_code: Customer code (should be Kubota's code)
            order_type: Should be 'FIRM'
            source_system: Source system name

        Returns:
            dict: Import result with statistics

        Note:
            RCV_NVAN は NO=45 と NO=47 が同一ファイルに混在する場合があります。
        """
        self.errors = []
        self.warnings = []
        existing_order_nos = set(
            StgOrderRawKubota.objects.filter(
                customer_code=customer_code,
                order_no__isnull=False
            ).values_list('order_no', flat=True)
        )
        file_order_nos = set()

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
            rows = list(csv.reader(lines))
            if self._is_2027_format(rows):
                return {
                    'success': False,
                    'message': 'このCSVは枚方2027年以降の新形式です。',
                    'errors': ['旧「枚方工場」では取り込めません。'],
                    'warnings': ['「枚方工場（27年以降）」を選択して取り込んでください。']
                }

            csv_reader = iter(rows)

            raw_records = []
            row_no = 0
            format_detected = None

            for row in csv_reader:
                row_no += 1

                # Detect format by data_no
                data_no = row[self.COL_DATA_NO].strip() if len(row) > self.COL_DATA_NO else ''

                if data_no == self.DATA_NO_45:
                    if format_detected is None:
                        format_detected = '45'
                elif data_no == self.DATA_NO_47:
                    if format_detected is None:
                        format_detected = '47'
                else:
                    # Header行や別レコードをスキップ
                    continue

                try:
                    if data_no == self.DATA_NO_45:
                        min_cols = max(
                            self.COL_PRODUCT_CODE_45,
                            self.COL_PRODUCT_NAME_45,
                            self.COL_DELIVERY_DATE_45,
                            self.COL_QUANTITY_45,
                            self.COL_ISSUE_DATE_45,
                            self.COL_ORDER_NO,
                            self.COL_INSPECTION_TYPE,
                        ) + 1
                        if len(row) < min_cols:
                            continue

                        product_code = row[self.COL_PRODUCT_CODE_45].strip() if len(row) > self.COL_PRODUCT_CODE_45 else ''
                        plant_code = row[self.COL_FACTORY].strip() if len(row) > self.COL_FACTORY else ''
                        product_name = row[self.COL_PRODUCT_NAME_45].strip() if len(row) > self.COL_PRODUCT_NAME_45 else ''
                        delivery_date_str = row[self.COL_DELIVERY_DATE_45].strip() if len(row) > self.COL_DELIVERY_DATE_45 else ''
                        quantity_str = row[self.COL_QUANTITY_45].strip() if len(row) > self.COL_QUANTITY_45 else ''
                        issue_date_str = row[self.COL_ISSUE_DATE_45].strip() if len(row) > self.COL_ISSUE_DATE_45 else ''
                        order_no = row[self.COL_ORDER_NO].strip() if len(row) > self.COL_ORDER_NO else ''
                        inspection_type = row[self.COL_INSPECTION_TYPE].strip() if len(row) > self.COL_INSPECTION_TYPE else ''
                        ship_to = row[self.COL_SHIP_TO_45].strip() if len(row) > self.COL_SHIP_TO_45 else ''

                        ship_to_name = ''

                        due_date = self.parse_date_from_yymmdd(delivery_date_str)
                        fmt = '45'

                    else:
                        min_cols = max(
                            self.COL_PRODUCT_CODE_47,
                            self.COL_PRODUCT_NAME_47,
                            self.COL_DELIVERY_DATE_47,
                            self.COL_QUANTITY_47,
                            self.COL_ISSUE_DATE_47,
                            self.COL_ORDER_NO,
                            self.COL_INSPECTION_TYPE_47,
                        ) + 1
                        if len(row) < min_cols:
                            continue

                        product_code = row[self.COL_PRODUCT_CODE_47].strip() if len(row) > self.COL_PRODUCT_CODE_47 else ''
                        plant_code = row[self.COL_FACTORY].strip() if len(row) > self.COL_FACTORY else ''
                        product_name = row[self.COL_PRODUCT_NAME_47].strip() if len(row) > self.COL_PRODUCT_NAME_47 else ''
                        delivery_date_str = row[self.COL_DELIVERY_DATE_47].strip() if len(row) > self.COL_DELIVERY_DATE_47 else ''
                        quantity_str = row[self.COL_QUANTITY_47].strip() if len(row) > self.COL_QUANTITY_47 else ''
                        issue_date_str = row[self.COL_ISSUE_DATE_47].strip() if len(row) > self.COL_ISSUE_DATE_47 else ''
                        order_no = row[self.COL_ORDER_NO].strip() if len(row) > self.COL_ORDER_NO else ''
                        inspection_type = row[self.COL_INSPECTION_TYPE_47].strip() if len(row) > self.COL_INSPECTION_TYPE_47 else ''
                        ship_to = row[self.COL_SHIP_TO_47].strip() if len(row) > self.COL_SHIP_TO_47 else ''
                        ship_to_name = row[self.COL_SHIP_TO_NAME_47].strip() if len(row) > self.COL_SHIP_TO_NAME_47 else ''

                        due_date = (
                            self.parse_date_from_mmdd(delivery_date_str)
                            or self.parse_date_from_yymmdd(delivery_date_str)
                        )
                        fmt = '47'

                    if not product_code:
                        continue

                    if order_no:
                        if order_no in existing_order_nos or order_no in file_order_nos:
                            self.warnings.append(f"Row {row_no}: Duplicate order_no {order_no} skipped")
                            continue
                        file_order_nos.add(order_no)

                    if not due_date:
                        self.warnings.append(f"Row {row_no}: Invalid date: {delivery_date_str}")
                        continue

                    # Parse quantity
                    quantity = self.parse_quantity(quantity_str)
                    if not quantity or quantity == 0:
                        self.warnings.append(f"Row {row_no}: Invalid or zero quantity: {quantity_str}")
                        continue

                    # Create raw record
                    raw_payload = {
                        'row': row,
                        'encoding': encoding,
                        'plant_code': plant_code,
                        'format': fmt
                    }
                    if issue_date_str:
                        raw_payload['issue_date'] = issue_date_str
                    if ship_to:
                        raw_payload['ship_to'] = ship_to
                    if ship_to_name:
                        raw_payload['ship_to_name'] = ship_to_name

                    raw_record = StgOrderRawKubota(
                        customer_code=customer_code,
                        order_type=order_type,
                        source_system=source_system,
                        source_file=file.name,
                        source_row_no=row_no,
                        data_no=data_no,
                        record_type='',  # Not applicable for confirmed orders
                        product_code=product_code,
                        product_name=product_name,
                        inspection_type=inspection_type,
                        delivery_date=due_date,
                        quantity=quantity,
                        order_no=order_no,
                        raw_payload=raw_payload,
                        parse_status='PENDING'
                    )
                    raw_records.append(raw_record)

                except Exception as e:
                    self.errors.append(f"Row {row_no}: {str(e)}")

            if not raw_records:
                return {
                    'success': False,
                    'message': f'No valid records found with NO=45/47',
                    'errors': self.errors,
                    'warnings': self.warnings + ['Column positions may need adjustment if file format changed.']
                }

            # Save to database
            raw_count, daily_count, min_raw_id, max_raw_id = self.save_to_database(raw_records, file, customer_code)

            format_msg = f"(Format: NO={format_detected})" if format_detected else ""
            return {
                'success': True,
                'message': f'Imported {raw_count} raw records, created {daily_count} daily records {format_msg}',
                'raw_count': raw_count,
                'daily_count': daily_count,
                'min_raw_id': min_raw_id,
                'max_raw_id': max_raw_id,
                'format': format_detected,
                'errors': self.errors,
                'warnings': self.warnings
            }

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Kubota Hirakata Kakutei Import Exception: {error_details}")
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
            StgOrderRawKubota.objects.bulk_create(raw_records)

            # Re-fetch to get primary keys
            raw_records_with_ids = StgOrderRawKubota.objects.filter(
                source_file=file.name,
                customer_code=customer_code,
                data_no__in=[self.DATA_NO_45, self.DATA_NO_47]
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
                if not raw.product_code or not raw.delivery_date or not raw.quantity:
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
                            'product_name': raw.product_name if raw.product_name else raw.product_code,
                            'category': 'UNKNOWN',  # 新規は未定で登録
                            'unit': '個',
                            'is_active': True,
                            'is_final_product': True
                        }
                    )
                    if created:
                        self.warnings.append(f'Auto-registered new product: {raw.product_code}')

                    # Create daily record
                    daily = StgOrderDaily(
                        raw_kubota=raw,
                        customer=customer,
                        order_type=raw.order_type,
                        version_no='v1',
                        product_code=raw.product_code,
                        due_date=raw.delivery_date,
                        quantity=raw.quantity,
                        ship_to_code=(raw.raw_payload or {}).get('ship_to', ''),
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

            ensure_ship_to_records(list(raw_records_with_ids), customer)

        return len(raw_records), len(daily_records), min_raw_id, max_raw_id
