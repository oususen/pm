import csv
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.db.models import Max
from orders.core.models import StgOrderRawKubota, StgOrderDaily
from orders.core.services.ship_to_utils import ensure_ship_to_records
from masters.models import Customer, Product


class KubotaHirakata2027KakuteiImportService:
    """Kubota Hirakata 2027+ Confirmed CSV Import Service

    2027年以降の枚方確定は堺と同じ列構成を使用する。
    ただし運用分離のため、専用サービスとして保持する。
    """

    SUPPORTED_DATA_NOS = ('45', '47')
    COL_DATA_NO = 0
    COL_FACTORY = 1
    COL_PRODUCT_CODE = 5
    COL_PRODUCT_NAME = 10
    COL_SHIP_TO = 12
    COL_SHIP_TO_NAME = 13
    COL_INSPECTION_TYPE = 14
    COL_DELIVERY_DATE = 23
    COL_QUANTITY = 24
    COL_ISSUE_DATE = 26
    COL_ORDER_NO = 33

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

    def parse_date_from_mmdd(self, date_str):
        """Parse date string in MMDD / YYMMDD / YYYYMMDD format"""
        if not date_str or str(date_str).strip() == '':
            return None

        date_str = str(date_str).strip()

        if len(date_str) == 3 and date_str.isdigit():
            date_str = '0' + date_str

        if len(date_str) == 4 and date_str.isdigit():
            try:
                mm = int(date_str[:2])
                dd = int(date_str[2:4])

                from datetime import date
                today = date.today()
                current_year = today.year
                current_month = today.month

                if mm > current_month + 6:
                    year = current_year - 1
                elif mm < current_month - 6:
                    year = current_year + 1
                else:
                    year = current_year

                return datetime(year, mm, dd).date()
            except ValueError:
                pass

        if len(date_str) == 6 and date_str.isdigit():
            try:
                yy = int(date_str[:2])
                mm = int(date_str[2:4])
                dd = int(date_str[4:6])
                return datetime(2000 + yy, mm, dd).date()
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
        """Parse quantity string to Decimal"""
        if not quantity_str or str(quantity_str).strip() == '':
            return None

        try:
            quantity_str = str(quantity_str).strip().replace(',', '')
            qty = Decimal(quantity_str)
            if qty == 0:
                return None
            return qty
        except Exception:
            return None

    def _is_legacy_format(self, rows):
        """現行枚方確定の旧形式を判定する"""
        if not rows:
            return False

        header = [
            str(col or '').strip().replace(' ', '').replace('　', '')
            for col in rows[0]
        ]
        return (
            len(rows[0]) == 34
            and '注番' in header
            and '発注番号' not in header
        )

    def import_csv(self, file, customer_code, order_type, source_system='CSV'):
        """Import Kubota Hirakata 2027+ confirmed order CSV"""
        self.errors = []
        self.warnings = []

        try:
            decoded_file, encoding = self.decode_file(file)
            if decoded_file is None:
                return {
                    'success': False,
                    'message': 'Failed to decode CSV file',
                    'errors': ['Unsupported encoding']
                }

            lines = decoded_file.splitlines()
            rows = list(csv.reader(lines))
            if self._is_legacy_format(rows):
                return {
                    'success': False,
                    'message': 'このCSVは現在の枚方形式です。',
                    'errors': ['「枚方工場（27年以降）」では取り込めません。'],
                    'warnings': ['旧「枚方工場」を選択して取り込んでください。']
                }

            csv_reader = iter(rows)

            raw_records = []
            row_no = 0

            for row in csv_reader:
                row_no += 1

                required_cols = max(
                    self.COL_DATA_NO,
                    self.COL_PRODUCT_CODE,
                    self.COL_DELIVERY_DATE,
                    self.COL_QUANTITY
                ) + 1
                if len(row) < required_cols:
                    continue

                data_no = row[self.COL_DATA_NO].strip() if len(row) > self.COL_DATA_NO else ''
                if data_no not in self.SUPPORTED_DATA_NOS:
                    continue

                try:
                    product_code = row[self.COL_PRODUCT_CODE].strip() if len(row) > self.COL_PRODUCT_CODE else ''
                    product_name = row[self.COL_PRODUCT_NAME].strip() if len(row) > self.COL_PRODUCT_NAME else ''
                    plant_code = row[self.COL_FACTORY].strip() if len(row) > self.COL_FACTORY else ''
                    ship_to = row[self.COL_SHIP_TO].strip() if len(row) > self.COL_SHIP_TO else ''
                    ship_to_name = row[self.COL_SHIP_TO_NAME].strip() if len(row) > self.COL_SHIP_TO_NAME else ''
                    inspection_type = row[self.COL_INSPECTION_TYPE].strip() if len(row) > self.COL_INSPECTION_TYPE else ''
                    delivery_date_str = row[self.COL_DELIVERY_DATE].strip() if len(row) > self.COL_DELIVERY_DATE else ''
                    quantity_str = row[self.COL_QUANTITY].strip() if len(row) > self.COL_QUANTITY else ''
                    issue_date_str = row[self.COL_ISSUE_DATE].strip() if len(row) > self.COL_ISSUE_DATE else ''
                    order_no = row[self.COL_ORDER_NO].strip() if len(row) > self.COL_ORDER_NO else ''

                    if not product_code:
                        continue

                    delivery_date = self.parse_date_from_mmdd(delivery_date_str)
                    if not delivery_date:
                        self.warnings.append(f"Row {row_no}: Invalid date: {delivery_date_str}")
                        continue

                    quantity = self.parse_quantity(quantity_str)
                    if not quantity:
                        self.warnings.append(f"Row {row_no}: Invalid or zero quantity: {quantity_str}")
                        continue

                    raw_record = StgOrderRawKubota(
                        customer_code=customer_code,
                        order_type=order_type,
                        source_file=file.name,
                        source_row_no=row_no,
                        data_no=data_no,
                        record_type='',
                        product_name=product_name,
                        product_code=product_code,
                        delivery_date=delivery_date,
                        quantity=quantity,
                        order_no=order_no,
                        inspection_type=inspection_type,
                        raw_payload={
                            'row': row,
                            'encoding': encoding,
                            'plant_code': plant_code,
                            'issue_date': issue_date_str,
                            'order_no': order_no,
                            'ship_to': ship_to,
                            'ship_to_name': ship_to_name,
                            'factory': 'HIRAKATA_2027',
                        },
                        parse_status='PENDING'
                    )
                    raw_records.append(raw_record)

                except Exception as e:
                    self.errors.append(f"Row {row_no}: {str(e)}")

            if not raw_records:
                return {
                    'success': False,
                    'message': 'No valid 45/47 confirmed order records found in file',
                    'errors': self.errors,
                    'warnings': self.warnings
                }

            raw_count, daily_count, min_raw_id, max_raw_id, forecast_diffs = self.save_to_database(raw_records, file, customer_code)

            changed_diffs = [d for d in forecast_diffs if d['diff'] != 0]
            if changed_diffs:
                self._create_diff_notification(changed_diffs, file.name)

            return {
                'success': True,
                'message': f'Imported {raw_count} raw records, created {daily_count} daily records',
                'raw_count': raw_count,
                'daily_count': daily_count,
                'min_raw_id': min_raw_id,
                'max_raw_id': max_raw_id,
                'forecast_diffs': forecast_diffs,
                'errors': self.errors,
                'warnings': self.warnings
            }

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Kubota Hirakata 2027 Kakutei Import Exception: {error_details}")
            return {
                'success': False,
                'message': f'Import failed: {str(e)}',
                'errors': self.errors + [str(e)]
            }

    def save_to_database(self, raw_records, file, customer_code):
        """Save raw records and create daily records"""
        with transaction.atomic():
            StgOrderRawKubota.objects.bulk_create(raw_records)

            raw_records_with_ids = StgOrderRawKubota.objects.filter(
                source_file=file.name,
                customer_code=customer_code,
                data_no__in=self.SUPPORTED_DATA_NOS
            ).order_by('-id')[:len(raw_records)]

            raw_ids = [r.id for r in raw_records_with_ids]
            min_raw_id = min(raw_ids) if raw_ids else None
            max_raw_id = max(raw_ids) if raw_ids else None

            try:
                customer = Customer.objects.get(customer_code=customer_code)
            except Customer.DoesNotExist:
                raise ValueError(f'Customer not found: {customer_code}')

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
                            'product_name': raw.product_name if raw.product_name else raw.product_code,
                            'category': 'UNKNOWN',
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
                        ship_to_code=(raw.raw_payload or {}).get('ship_to', ''),
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
                    self.errors.append(f"Product {raw.product_code}: {str(e)}")

            if daily_records:
                StgOrderDaily.objects.bulk_create(daily_records)

            ensure_ship_to_records(list(raw_records_with_ids), customer)

            forecast_diffs = []
            if daily_records:
                firm_dict = {}
                for daily in daily_records:
                    key = (daily.product_code, daily.due_date)
                    firm_dict[key] = firm_dict.get(key, Decimal('0')) + daily.quantity

                product_codes = list({k[0] for k in firm_dict.keys()})
                due_dates = list({k[1] for k in firm_dict.keys()})

                max_id_qs = (
                    StgOrderDaily.objects
                    .filter(
                        customer=customer,
                        order_type='FORECAST',
                        product_code__in=product_codes,
                        due_date__in=due_dates,
                    )
                    .values('product_code', 'due_date')
                    .annotate(max_id=Max('id'))
                )
                latest_ids = [row['max_id'] for row in max_id_qs]
                forecast_dict = {
                    (rec.product_code, rec.due_date): rec.quantity
                    for rec in StgOrderDaily.objects
                    .filter(id__in=latest_ids)
                    .only('product_code', 'due_date', 'quantity')
                }

                for (product_code, due_date) in sorted(firm_dict.keys()):
                    if (product_code, due_date) not in forecast_dict:
                        continue
                    firm_qty = int(firm_dict[(product_code, due_date)])
                    forecast_qty = int(forecast_dict[(product_code, due_date)])
                    forecast_diffs.append({
                        'product_code': product_code,
                        'due_date': str(due_date),
                        'firm_qty': firm_qty,
                        'forecast_qty': forecast_qty,
                        'diff': firm_qty - forecast_qty,
                    })

        return len(raw_records), len(daily_records), min_raw_id, max_raw_id, forecast_diffs

    def _create_diff_notification(self, changed_diffs, filename):
        """枚方2027では堺専用通知を作成しない。"""
        return
