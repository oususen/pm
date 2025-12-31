import csv
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from orders.models import StgOrderRawKubota, StgOrderDaily
from masters.models import Customer, Product


class KubotaHirakataKakuteiImportService:
    """Kubota Hirakata Kakutei (Confirmed) CSV Import Service

    Format: NO=45 type (RCV_NVAN.csv)
    - Column 0: NO (データNo) = "45"
    - Column 5: Product Code (品番)
    - Column 18: Delivery Date (納入指示日) - YYMMDD format
    - Column 19: Quantity (納入指示数)
    """

    DATA_NO = '45'
    COL_DATA_NO = 0
    COL_PRODUCT_CODE = 5
    COL_ORDER_NO = 3  # 注番
    COL_DELIVERY_DATE = 18  # 納入指示日 (YYMMDD format)
    COL_QUANTITY = 19  # 納入指示数

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

    def import_csv(self, file, customer_code, order_type, source_system='CSV'):
        """Import Kubota Hirakata confirmed order CSV (NO=45)

        Args:
            file: Uploaded file object
            customer_code: Customer code (should be Kubota's code)
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

            raw_records = []
            row_no = 0

            for row in csv_reader:
                row_no += 1

                # Skip header
                if row_no == 1:
                    continue

                # Check minimum columns
                required_cols = max(self.COL_DATA_NO, self.COL_PRODUCT_CODE,
                                   self.COL_DELIVERY_DATE, self.COL_QUANTITY) + 1
                if len(row) < required_cols:
                    continue

                # Filter by data_no
                data_no = row[self.COL_DATA_NO].strip() if len(row) > self.COL_DATA_NO else ''
                if data_no != self.DATA_NO:
                    continue

                try:
                    # Extract data
                    product_code = row[self.COL_PRODUCT_CODE].strip() if len(row) > self.COL_PRODUCT_CODE else ''
                    delivery_date_str = row[self.COL_DELIVERY_DATE].strip() if len(row) > self.COL_DELIVERY_DATE else ''
                    quantity_str = row[self.COL_QUANTITY].strip() if len(row) > self.COL_QUANTITY else ''
                    order_no = row[self.COL_ORDER_NO].strip() if len(row) > self.COL_ORDER_NO else ''

                    if not product_code:
                        continue

                    # Parse date (YYMMDD format)
                    due_date = self.parse_date_from_yymmdd(delivery_date_str)
                    if not due_date:
                        self.warnings.append(f"Row {row_no}: Invalid date: {delivery_date_str}")
                        continue

                    # Parse quantity
                    quantity = self.parse_quantity(quantity_str)
                    if not quantity or quantity == 0:
                        self.warnings.append(f"Row {row_no}: Invalid or zero quantity: {quantity_str}")
                        continue

                    # Create raw record
                    raw_record = StgOrderRawKubota(
                        customer_code=customer_code,
                        order_type=order_type,
                        source_system=source_system,
                        source_file=file.name,
                        source_row_no=row_no,
                        data_no=self.DATA_NO,
                        record_type='',  # Not applicable for confirmed orders
                        product_code=product_code,
                        delivery_date=due_date,
                        quantity=quantity,
                        order_no=order_no,
                        raw_payload={'row': row, 'encoding': encoding},
                        parse_status='PENDING'
                    )
                    raw_records.append(raw_record)

                except Exception as e:
                    self.errors.append(f"Row {row_no}: {str(e)}")

            if not raw_records:
                return {
                    'success': False,
                    'message': f'No valid records found with NO=45',
                    'errors': self.errors,
                    'warnings': self.warnings + ['Column positions may need adjustment if file format changed.']
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
                        due_date=raw.delivery_date,
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
