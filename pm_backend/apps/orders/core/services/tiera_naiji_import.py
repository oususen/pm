import csv
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from orders.core.models import StgOrderRawTiera, StgOrderDaily
from masters.models import Customer, Product


class TieraNaijiImportService:
    """Tiera Naiji (Forecast) CSV Import Service

    Format: B17 type
    - Column 0: Data Type (データ区分) = "B17"
    - Column 6: Product Code (図番)
    - Column 8: Delivery Date (納期) - YYYYMMDD format
    - Column 11: Quantity (数量)
    - Column 12: Product Name (品名・全角)
    - Column 13: Product Name Half-width (品名半角)
    """

    IDENTIFIER_COL = 0  # データ区分
    IDENTIFIER_VALUE = 'B17'
    COL_PRODUCT_CODE = 6   # 図番
    COL_DELIVERY_DATE = 8  # 納期
    COL_QUANTITY = 11      # 数量
    COL_PRODUCT_NAME_FULL = 12  # 品名（全角）列13
    COL_PRODUCT_NAME_HALF = 13  # 品名半角 列14

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

    def import_csv(self, file, customer_code, order_type, source_system='CSV'):
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

            raw_records = []
            row_no = 0

            for row in csv_reader:
                row_no += 1

                # Skip header
                if row_no == 1:
                    continue

                # Check minimum columns
                required_cols = max(self.IDENTIFIER_COL, self.COL_PRODUCT_CODE, 
                                   self.COL_DELIVERY_DATE, self.COL_QUANTITY) + 1
                if len(row) < required_cols:
                    continue

                # Filter by identifier
                if row[self.IDENTIFIER_COL].strip() != self.IDENTIFIER_VALUE:
                    continue

                try:
                    # Extract data
                    product_code = row[self.COL_PRODUCT_CODE].strip()
                    delivery_date_str = row[self.COL_DELIVERY_DATE].strip()
                    quantity_str = row[self.COL_QUANTITY].strip()
                    product_name_full = row[self.COL_PRODUCT_NAME_FULL].strip() if len(row) > self.COL_PRODUCT_NAME_FULL else ''
                    product_name_half = row[self.COL_PRODUCT_NAME_HALF].strip() if len(row) > self.COL_PRODUCT_NAME_HALF else ''

                    # Parse date
                    due_date = self.parse_date(delivery_date_str)
                    if not due_date:
                        self.warnings.append(f"Row {row_no}: Invalid date: {delivery_date_str}")

                    # Parse quantity
                    quantity = self.parse_quantity(quantity_str)
                    if not quantity:
                        self.warnings.append(f"Row {row_no}: Invalid quantity: {quantity_str}")

                    # Create raw record
                    raw_record = StgOrderRawTiera(
                        customer_code=customer_code,
                        order_type=order_type,
                        source_system=source_system,
                        source_file=file.name,
                        source_row_no=row_no,
                        data_type=self.IDENTIFIER_VALUE,
                        product_code=product_code,
                        due_date=due_date,
                        quantity=quantity,
                        product_name=product_name_full,
                        product_name_kana=product_name_half,
                        raw_payload={'row': row, 'encoding': encoding},
                        parse_status='PENDING'
                    )
                    raw_records.append(raw_record)

                except Exception as e:
                    self.errors.append(f"Row {row_no}: {str(e)}")

            if not raw_records:
                return {
                    'success': False,
                    'message': f'No valid B17 records found in file',
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
            print(f"Tiera Naiji Import Exception: {error_details}")
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
            StgOrderRawTiera.objects.bulk_create(raw_records)

            # Re-fetch to get primary keys
            raw_records_with_ids = StgOrderRawTiera.objects.filter(
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
                    product_name_for_master = raw.product_name if raw.product_name else raw.product_code
                    product_name_kana_for_master = raw.product_name_kana if raw.product_name_kana else None

                    product, created = Product.objects.get_or_create(
                        product_code=raw.product_code,
                        defaults={
                            'product_name': product_name_for_master,
                            'product_name_halfwidth': product_name_kana_for_master,
                            'category': 'UNKNOWN',  # 新規は未定で登録
                            'unit': '個',
                            'is_active': True,
                            'is_final_product': True
                        }
                    )
                    if created:
                        self.warnings.append(f'Auto-registered new product: {raw.product_code} ({product_name_for_master})')

                    # Create daily record
                    daily = StgOrderDaily(
                        raw_tiera=raw,
                        customer=customer,
                        order_type=raw.order_type,
                        version_no='v1',
                        product_code=raw.product_code,
                        product_name=raw.product_name,
                        product_name_halfwidth=raw.product_name_kana,
                        due_date=raw.due_date,
                        quantity=raw.quantity,
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
