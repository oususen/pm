import csv
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from orders.models import StgOrderRawKubota, StgOrderDaily
from masters.models import Customer, Product


class KubotaSakaiNaijiImportService:
    """Kubota Sakai Factory Forecast (36番内示) CSV Import Service

    Format: RCV_JVAN_36_(堺).csv
    - Data No: 36 (forecast)
    - Structure: V2 header row + V3 data row pairs
    - Encoding: Shift-JIS (cp932)
    - Horizontal data: 3 months × 31 days = 93 columns
    - Grouping: product_code + inspection_type (同じ品番で検査区分が複数存在)

    Column mapping:
    - Column 0: data_no = "36"
    - Column 8: product_code (品番)
    - Column 18: inspection_type (検査区分) - N, NS, TS, $ etc.
    - Column 24: record_type (レコード識別) - "V2" or "V3"
    - Column 26: start_month (スタート月度) - YYMM format
    - Columns 27-121: Date headers (V2) and quantities (V3)
      - V2: Date strings in YYMMDD format (e.g., "51201", "51202")
      - V3: Quantities (e.g., 72, 56, 64)
    """

    DATA_NO = '36'
    COL_DATA_NO = 0
    COL_PRODUCT_CODE = 8
    COL_INSPECTION_TYPE = 18
    COL_RECORD_TYPE = 24
    COL_START_MONTH = 26
    COL_DATA_START = 27  # Start of 93 columns (date/quantity)
    COL_DATA_END = 120   # End of 93 columns (27 + 93 - 1 = 119, but check actual file)

    def __init__(self):
        self.errors = []
        self.warnings = []

    def decode_file(self, file):
        """Decode CSV file with Shift-JIS encoding"""
        file.seek(0)
        raw_data = file.read()

        encodings = ['cp932', 'shift-jis', 'utf-8-sig', 'utf-8']
        for encoding in encodings:
            try:
                return raw_data.decode(encoding), encoding
            except UnicodeDecodeError:
                continue

        return None, None

    def parse_date_from_yymdd(self, date_str, start_year=None):
        """Parse date string in YYMDD or YMMDD format (5 digits)

        Args:
            date_str: Date string like "51201" (year=25, month=12, day=01)
                     or "60209" (year=6→2026, month=02, day=09)
            start_year: Optional start year (YY format) to handle year boundary

        Returns:
            datetime.date or None
        """
        if not date_str or date_str.strip() == '':
            return None

        date_str = str(date_str).strip()

        # YMMDD format (5 digits) - single digit year
        # Example: "60209" → year=6 (2026), month=02, day=09
        if len(date_str) == 5 and date_str.isdigit():
            try:
                y = int(date_str[0])
                mm = int(date_str[1:3])
                dd = int(date_str[3:5])
                yyyy = 2020 + y  # Assume 2020s decade
                return datetime(yyyy, mm, dd).date()
            except (ValueError, IndexError):
                pass

        # YYMDD format (5 digits) - fallback for two-digit year with single-digit month
        if len(date_str) == 5 and date_str.isdigit():
            try:
                yy = int(date_str[:2])
                m = int(date_str[2])
                dd = int(date_str[3:5])

                # Convert YY to full year (assume 20xx)
                yyyy = 2000 + yy

                return datetime(yyyy, m, dd).date()
            except (ValueError, IndexError):
                pass

        # YYMMDD format (6 digits)
        if len(date_str) == 6 and date_str.isdigit():
            try:
                yy = int(date_str[:2])
                mm = int(date_str[2:4])
                dd = int(date_str[4:6])

                # Convert YY to full year (assume 20xx)
                yyyy = 2000 + yy

                return datetime(yyyy, mm, dd).date()
            except ValueError:
                pass

        return None

    def parse_quantity(self, quantity_str):
        """Parse quantity string to Decimal"""
        if not quantity_str or str(quantity_str).strip() == '':
            return None

        try:
            quantity_str = str(quantity_str).strip().replace(',', '')
            qty = Decimal(quantity_str)
            if qty == 0:
                return None
            return qty
        except:
            return None

    def import_csv(self, file, customer_code, order_type, source_system='CSV'):
        """Import Kubota Sakai forecast CSV (36番内示)

        Args:
            file: Uploaded file object
            customer_code: Customer code (should be Kubota's code)
            order_type: Should be 'FORECAST'
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

            # Group V2+V3 pairs by (product_code, inspection_type)
            v2_rows = {}  # Key: (product_code, inspection_type), Value: (row_data, row_no)
            v3_rows = {}  # Key: (product_code, inspection_type), Value: (row_data, row_no)

            row_no = 0

            for row in csv_reader:
                row_no += 1

                # Skip if not enough columns
                if len(row) < self.COL_DATA_START:
                    continue

                # Filter by data_no
                if len(row) > self.COL_DATA_NO and row[self.COL_DATA_NO].strip() != self.DATA_NO:
                    continue

                try:
                    # Extract key fields
                    product_code = row[self.COL_PRODUCT_CODE].strip() if len(row) > self.COL_PRODUCT_CODE else ''
                    inspection_type = row[self.COL_INSPECTION_TYPE].strip() if len(row) > self.COL_INSPECTION_TYPE else ''
                    record_type = row[self.COL_RECORD_TYPE].strip() if len(row) > self.COL_RECORD_TYPE else ''

                    if not product_code:
                        continue

                    # Group by (product_code, inspection_type)
                    key = (product_code, inspection_type)

                    if record_type == 'V2':
                        v2_rows[key] = (row, row_no)
                    elif record_type == 'V3':
                        v3_rows[key] = (row, row_no)

                except Exception as e:
                    self.errors.append(f"Row {row_no}: Failed to parse - {str(e)}")

            # Process V2+V3 pairs
            raw_records = []

            for key in v2_rows.keys():
                if key not in v3_rows:
                    self.warnings.append(f"Product {key[0]} (inspection={key[1]}): V2 found but V3 missing")
                    continue

                v2_row, v2_row_no = v2_rows[key]
                v3_row, v3_row_no = v3_rows[key]

                try:
                    product_code, inspection_type = key

                    # Extract start month
                    start_month = v2_row[self.COL_START_MONTH].strip() if len(v2_row) > self.COL_START_MONTH else ''

                    # Extract date headers (V2) and quantities (V3)
                    date_headers = []
                    quantities = []

                    for col_idx in range(self.COL_DATA_START, min(len(v2_row), len(v3_row))):
                        date_str = v2_row[col_idx].strip() if col_idx < len(v2_row) else ''
                        qty_str = v3_row[col_idx].strip() if col_idx < len(v3_row) else ''

                        # Only store if date is present
                        if date_str:
                            date_headers.append(date_str)
                            quantities.append(qty_str)

                    # Create raw record
                    raw_record = StgOrderRawKubota(
                        customer_code=customer_code,
                        order_type=order_type,
                        source_file=file.name,
                        source_row_no=v2_row_no,  # Use V2 row number as primary
                        data_no=self.DATA_NO,
                        record_type='V2+V3',  # Indicate this is a pair
                        product_code=product_code,
                        inspection_type=inspection_type,
                        start_month=start_month,
                        date_headers=date_headers,
                        quantities=quantities,
                        raw_payload={
                            'v2_row': v2_row,
                            'v3_row': v3_row,
                            'v2_row_no': v2_row_no,
                            'v3_row_no': v3_row_no,
                            'encoding': encoding
                        },
                        parse_status='PENDING'
                    )
                    raw_records.append(raw_record)

                except Exception as e:
                    self.errors.append(f"Product {product_code} (inspection={inspection_type}): {str(e)}")

            if not raw_records:
                return {
                    'success': False,
                    'message': f'No valid 36番 forecast records found in file',
                    'errors': self.errors
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
            print(f"Kubota Sakai Naiji Import Exception: {error_details}")
            return {
                'success': False,
                'message': f'Import failed: {str(e)}',
                'errors': self.errors + [str(e)]
            }

    def save_to_database(self, raw_records, file, customer_code):
        """Save raw records and create daily records

        For Kubota forecast (36番), we need to:
        1. Save StgOrderRawKubota records with horizontal data (JSON)
        2. Convert horizontal data to vertical (daily) records in StgOrderDaily

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
                data_no=self.DATA_NO
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

            # Convert horizontal data to daily records
            daily_records = []
            error_count = 0

            for raw in raw_records_with_ids:
                if not raw.date_headers or not raw.quantities:
                    raw.parse_status = 'ERROR'
                    raw.error_message = 'Missing date headers or quantities'
                    raw.save()
                    error_count += 1
                    continue

                # Process each date+quantity pair
                try:
                    for idx, (date_str, qty_str) in enumerate(zip(raw.date_headers, raw.quantities)):
                        # Parse date
                        due_date = self.parse_date_from_yymdd(date_str)

                        # Skip if date cannot be parsed (e.g., AA01, A011, 10, 0)
                        if not due_date:
                            continue

                        # Parse quantity
                        quantity = self.parse_quantity(qty_str)
                        if not quantity:
                            # Skip zero or invalid quantities
                            continue

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

                        # Create daily record
                        daily = StgOrderDaily(
                            raw_kubota=raw,
                            customer=customer,
                            order_type=raw.order_type,
                            version_no='v1',
                            product_code=raw.product_code,
                            due_date=due_date,
                            quantity=quantity,
                            source_system='CSV',
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
