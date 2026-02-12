import csv
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from orders.core.models import StgOrderRawKubota, StgOrderDaily
from masters.models import Customer, Product


class KubotaHirakataSpecialKakuteiImportService:
    """Kubota Hirakata special confirmed order CSV import service (RCV_NVAN-2)."""

    DATA_NO = '47'
    COL_DATA_NO = 0
    COL_ORDER_NO = 3
    COL_PRODUCT_CODE = 5
    COL_PRODUCT_NAME = 10
    COL_INSPECTION_TYPE = 14
    COL_DELIVERY_DATE = 23
    COL_QUANTITY = 24
    COL_ISSUE_DATE = 26

    def __init__(self):
        self.errors = []
        self.warnings = []

    def decode_file(self, file):
        """Decode CSV file with Shift-JIS encoding."""
        file.seek(0)
        raw_data = file.read()

        encodings = ['cp932', 'shift-jis', 'utf-8-sig', 'utf-8']
        for encoding in encodings:
            try:
                return raw_data.decode(encoding), encoding
            except UnicodeDecodeError:
                continue

        return None, None

    def parse_date_from_mmdd(self, date_str):
        """Parse date string in MMDD format (4 digits) with year inference."""
        if not date_str or str(date_str).strip() == '':
            return None

        date_str = str(date_str).strip()

        if len(date_str) == 4 and date_str.isdigit():
            try:
                mm = int(date_str[:2])
                dd = int(date_str[2:4])
                today = datetime.today().date()
                year = today.year

                if mm > today.month + 6:
                    year -= 1
                elif mm < today.month - 6:
                    year += 1

                return datetime(year, mm, dd).date()
            except ValueError:
                pass

        if len(date_str) == 3 and date_str.isdigit():
            try:
                mm = int(date_str[0])
                dd = int(date_str[1:3])
                today = datetime.today().date()
                year = today.year

                if mm > today.month + 6:
                    year -= 1
                elif mm < today.month - 6:
                    year += 1

                return datetime(year, mm, dd).date()
            except ValueError:
                pass

        if len(date_str) == 6 and date_str.isdigit():
            try:
                yy = int(date_str[:2])
                mm = int(date_str[2:4])
                dd = int(date_str[4:6])
                yyyy = 2000 + yy
                return datetime(yyyy, mm, dd).date()
            except ValueError:
                pass

        if len(date_str) == 8 and date_str.isdigit():
            try:
                yyyy = int(date_str[:4])
                mm = int(date_str[4:6])
                dd = int(date_str[6:8])
                return datetime(yyyy, mm, dd).date()
            except ValueError:
                pass

        return None

    def parse_quantity(self, quantity_str):
        """Parse quantity string to Decimal."""
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
        """Import Kubota Hirakata special confirmed order CSV (NO=47)."""
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
            decoded_file, encoding = self.decode_file(file)
            if decoded_file is None:
                return {
                    'success': False,
                    'message': 'Failed to decode CSV file',
                    'errors': ['Unsupported encoding']
                }

            lines = decoded_file.splitlines()
            csv_reader = csv.reader(lines)

            raw_records = []
            row_no = 0

            for row in csv_reader:
                row_no += 1

                if row_no == 1:
                    continue

                if len(row) <= self.COL_QUANTITY:
                    continue

                data_no = row[self.COL_DATA_NO].strip() if len(row) > self.COL_DATA_NO else ''
                if data_no != self.DATA_NO:
                    continue

                try:
                    product_code = row[self.COL_PRODUCT_CODE].strip() if len(row) > self.COL_PRODUCT_CODE else ''
                    if not product_code:
                        continue

                    product_name = row[self.COL_PRODUCT_NAME].strip() if len(row) > self.COL_PRODUCT_NAME else ''
                    inspection_type = row[self.COL_INSPECTION_TYPE].strip() if len(row) > self.COL_INSPECTION_TYPE else ''
                    delivery_date_str = row[self.COL_DELIVERY_DATE].strip() if len(row) > self.COL_DELIVERY_DATE else ''
                    quantity_str = row[self.COL_QUANTITY].strip() if len(row) > self.COL_QUANTITY else ''
                    issue_date_str = row[self.COL_ISSUE_DATE].strip() if len(row) > self.COL_ISSUE_DATE else ''
                    order_no = row[self.COL_ORDER_NO].strip() if len(row) > self.COL_ORDER_NO else ''

                    if order_no:
                        if order_no in existing_order_nos or order_no in file_order_nos:
                            self.warnings.append(f"Row {row_no}: Duplicate order_no {order_no} skipped")
                            continue
                        file_order_nos.add(order_no)

                    delivery_date = self.parse_date_from_mmdd(delivery_date_str)
                    if not delivery_date:
                        self.warnings.append(f"Row {row_no}: Invalid date: {delivery_date_str}")
                        continue

                    quantity = self.parse_quantity(quantity_str)
                    if not quantity:
                        self.warnings.append(f"Row {row_no}: Invalid or zero quantity: {quantity_str}")
                        continue

                    raw_payload = {
                        'row': row,
                        'encoding': encoding,
                        'issue_date': issue_date_str,
                        'factory': 'HIRAKATA',
                        'special': True,
                        'format': 'NVAN-2'
                    }
                    if order_no:
                        raw_payload['kubota_order_no'] = order_no

                    raw_record = StgOrderRawKubota(
                        customer_code=customer_code,
                        order_type=order_type,
                        source_system=source_system,
                        source_file=file.name,
                        source_row_no=row_no,
                        data_no=self.DATA_NO,
                        record_type='SPECIAL',
                        product_name=product_name,
                        product_code=product_code,
                        inspection_type=inspection_type,
                        delivery_date=delivery_date,
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
                    'message': f'No valid {self.DATA_NO} special order records found in file.',
                    'errors': self.errors,
                    'warnings': self.warnings
                }

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
            print(f"Kubota Hirakata Special Kakutei Import Exception: {error_details}")
            return {
                'success': False,
                'message': f'Import failed: {str(e)}',
                'errors': self.errors + [str(e)]
            }

    def save_to_database(self, raw_records, file, customer_code):
        """Save raw records and create daily records."""
        with transaction.atomic():
            StgOrderRawKubota.objects.bulk_create(raw_records)

            raw_records_with_ids = StgOrderRawKubota.objects.filter(
                source_file=file.name,
                customer_code=customer_code,
                data_no=self.DATA_NO
            ).order_by('-id')[:len(raw_records)]

            raw_ids = [r.id for r in raw_records_with_ids]
            min_raw_id = min(raw_ids) if raw_ids else None
            max_raw_id = max(raw_ids) if raw_ids else None

            try:
                customer = Customer.objects.get(customer_code=customer_code)
            except Customer.DoesNotExist:
                raise ValueError(f'Customer not found: {customer_code}')

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

            if daily_records:
                StgOrderDaily.objects.bulk_create(daily_records)

        return len(raw_records), len(daily_records), min_raw_id, max_raw_id
