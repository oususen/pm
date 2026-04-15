import csv
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from orders.core.models import StgOrderRawKubota, StgOrderDaily
from masters.models import Customer, Product


class KubotaKmtKakuteiImportService:
    """Kubota KMT Confirmed (NO=27) CSV Import Service"""

    DATA_NO = '27'
    FACTORY = 'KMT'

    COL_DATA_NO = 0
    COL_CHUBAN = 3  # 注番（顧客発注番号）
    COL_PRODUCT_CODE = 5
    COL_PRODUCT_NAME = 10
    COL_SHIP_TO = 12
    COL_INSPECTION_TYPE = 14
    COL_DELIVERY_DATE = 21  # 納期(YYYYMMDD)
    COL_QUANTITY = 22  # 指示数
    COL_ISSUE_DATE = 24  # 発行日(YYMMDD)

    def __init__(self):
        self.errors = []
        self.warnings = []

    def decode_file(self, file):
        file.seek(0)
        raw_data = file.read()
        for encoding in ('cp932', 'shift-jis', 'utf-8-sig', 'utf-8'):
            try:
                return raw_data.decode(encoding), encoding
            except UnicodeDecodeError:
                continue
        return None, None

    def parse_date(self, date_str):
        if not date_str:
            return None
        s = str(date_str).strip()
        if len(s) == 8 and s.isdigit():
            try:
                return datetime.strptime(s, '%Y%m%d').date()
            except ValueError:
                return None
        if len(s) == 6 and s.isdigit():
            try:
                return datetime.strptime(s, '%y%m%d').date()
            except ValueError:
                return None
        return None

    def parse_quantity(self, quantity_str):
        if not quantity_str:
            return None
        try:
            qty = Decimal(str(quantity_str).strip().replace(',', ''))
            if qty == 0:
                return None
            return qty
        except Exception:
            return None

    def import_csv(self, file, customer_code, order_type, source_system='CSV'):
        self.errors = []
        self.warnings = []

        try:
            decoded_file, encoding = self.decode_file(file)
            if decoded_file is None:
                return {
                    'success': False,
                    'message': 'Failed to decode CSV file',
                    'errors': ['Unsupported encoding'],
                }

            csv_reader = csv.reader(decoded_file.splitlines())
            raw_records = []
            row_no = 0

            for row in csv_reader:
                row_no += 1
                if len(row) <= self.COL_QUANTITY:
                    continue

                data_no = row[self.COL_DATA_NO].strip() if len(row) > self.COL_DATA_NO else ''
                if data_no != self.DATA_NO:
                    continue

                product_code = row[self.COL_PRODUCT_CODE].strip() if len(row) > self.COL_PRODUCT_CODE else ''
                if not product_code:
                    continue

                product_name = row[self.COL_PRODUCT_NAME].strip() if len(row) > self.COL_PRODUCT_NAME else ''
                ship_to = row[self.COL_SHIP_TO].strip() if len(row) > self.COL_SHIP_TO else ''
                inspection_type = row[self.COL_INSPECTION_TYPE].strip() if len(row) > self.COL_INSPECTION_TYPE else ''
                due_date_str = row[self.COL_DELIVERY_DATE].strip() if len(row) > self.COL_DELIVERY_DATE else ''
                qty_str = row[self.COL_QUANTITY].strip() if len(row) > self.COL_QUANTITY else ''
                issue_date = row[self.COL_ISSUE_DATE].strip() if len(row) > self.COL_ISSUE_DATE else ''
                chuban = row[self.COL_CHUBAN].strip() if len(row) > self.COL_CHUBAN else ''

                due_date = self.parse_date(due_date_str)
                if not due_date:
                    self.warnings.append(f'Row {row_no}: Invalid date: {due_date_str}')
                    continue

                quantity = self.parse_quantity(qty_str)
                if not quantity:
                    self.warnings.append(f'Row {row_no}: Invalid or zero quantity: {qty_str}')
                    continue

                raw_records.append(
                    StgOrderRawKubota(
                        customer_code=customer_code,
                        order_type=order_type,
                        source_file=file.name,
                        source_row_no=row_no,
                        data_no=self.DATA_NO,
                        record_type='',
                        product_name=product_name,
                        product_code=product_code,
                        delivery_date=due_date,
                        quantity=quantity,
                        order_no=chuban,
                        inspection_type=inspection_type,
                        raw_payload={
                            'row': row,
                            'encoding': encoding,
                            'factory': self.FACTORY,
                            'ship_to': ship_to,
                            'issue_date': issue_date,
                            'kubota_order_no': chuban,  # 注番（Excel列4）
                        },
                        parse_status='PENDING',
                    )
                )

            if not raw_records:
                return {
                    'success': False,
                    'message': 'No valid NO=27 confirmed order records found in file',
                    'errors': self.errors,
                    'warnings': self.warnings,
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
                'warnings': self.warnings,
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Import failed: {str(e)}',
                'errors': self.errors + [str(e)],
            }

    def save_to_database(self, raw_records, file, customer_code):
        with transaction.atomic():
            StgOrderRawKubota.objects.bulk_create(raw_records)

            raw_records_with_ids = StgOrderRawKubota.objects.filter(
                source_file=file.name,
                customer_code=customer_code,
                data_no=self.DATA_NO,
            ).order_by('-id')[:len(raw_records)]

            raw_ids = [r.id for r in raw_records_with_ids]
            min_raw_id = min(raw_ids) if raw_ids else None
            max_raw_id = max(raw_ids) if raw_ids else None

            customer = Customer.objects.get(customer_code=customer_code)
            daily_records = []

            for raw in raw_records_with_ids:
                if not raw.product_code or not raw.delivery_date or not raw.quantity:
                    raw.parse_status = 'ERROR'
                    raw.error_message = 'Missing required fields'
                    raw.save()
                    continue

                try:
                    product, created = Product.objects.get_or_create(
                        product_code=raw.product_code,
                        defaults={
                            'product_name': raw.product_name or raw.product_code,
                            'category': 'UNKNOWN',
                            'unit': '個',
                            'is_active': True,
                            'is_final_product': True,
                        },
                    )
                    if created:
                        self.warnings.append(f'Auto-registered new product: {raw.product_code}')

                    daily_records.append(
                        StgOrderDaily(
                            raw_kubota=raw,
                            customer=customer,
                            order_type=raw.order_type,
                            version_no='v1',
                            product_code=raw.product_code,
                            due_date=raw.delivery_date,
                            quantity=raw.quantity,
                            ship_to_code=(raw.raw_payload or {}).get('ship_to', ''),
                            source_system='CSV',
                            source_file=raw.source_file,
                        )
                    )

                    raw.parse_status = 'PARSED'
                    raw.save()
                except Exception as e:
                    raw.parse_status = 'ERROR'
                    raw.error_message = str(e)
                    raw.save()
                    self.errors.append(f'Product {raw.product_code}: {str(e)}')

            if daily_records:
                StgOrderDaily.objects.bulk_create(daily_records)

        return len(raw_records), len(daily_records), min_raw_id, max_raw_id

