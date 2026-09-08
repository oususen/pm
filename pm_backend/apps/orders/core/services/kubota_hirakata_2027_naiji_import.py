import csv
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from orders.core.models import StgOrderRawKubota, StgOrderDaily
from masters.models import Customer, Product
from orders.core.services.ship_to_utils import ensure_ship_to_records, normalize_kubota_ship_to_code


class KubotaHirakata2027NaijiImportService:
    """Kubota Hirakata 2027+ Forecast CSV Import Service

    2027年以降の枚方内示は堺と同じ列構成を使用する。
    ただし運用分離のため、専用サービスとして保持する。
    """

    DATA_NO = '36'
    COL_DATA_NO = 0
    COL_FACTORY = 1
    COL_CALC_DATE = 4
    COL_PRODUCT_CODE = 8
    COL_PRODUCT_NAME = 11
    COL_SHIP_TO = 12
    COL_INSPECTION_TYPE = 17
    COL_RECORD_TYPE = 24
    COL_START_MONTH = 25
    COL_MONTH_TOTAL = 26
    COL_DATA_START = 27
    COL_DATA_END = 119

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
        """Parse date string in YYMDD or YMMDD format"""
        if not date_str or date_str.strip() == '':
            return None

        date_str = str(date_str).strip()

        if len(date_str) == 5 and date_str.isdigit():
            try:
                y = int(date_str[0])
                mm = int(date_str[1:3])
                dd = int(date_str[3:5])
                return datetime(2020 + y, mm, dd).date()
            except (ValueError, IndexError):
                pass

        if len(date_str) == 5 and date_str.isdigit():
            try:
                yy = int(date_str[:2])
                m = int(date_str[2])
                dd = int(date_str[3:5])
                return datetime(2000 + yy, m, dd).date()
            except (ValueError, IndexError):
                pass

        if len(date_str) == 6 and date_str.isdigit():
            try:
                yy = int(date_str[:2])
                mm = int(date_str[2:4])
                dd = int(date_str[4:6])
                return datetime(2000 + yy, mm, dd).date()
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
        """現行枚方内示の旧形式を判定する"""
        if not rows:
            return False

        header = [
            str(col or '').strip().replace(' ', '').replace('　', '')
            for col in rows[0]
        ]
        return (
            len(rows[0]) == 123
            and '日程ライン圧縮' in header
            and not any('初月度(' in col for col in header)
        )

    def import_csv(self, file, customer_code, order_type, source_system='CSV'):
        """Import Kubota Hirakata 2027+ forecast CSV"""
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

            v2_rows = {}
            v3_rows = {}
            row_no = 0

            for row in csv_reader:
                row_no += 1

                if len(row) < self.COL_DATA_START:
                    continue

                if len(row) > self.COL_DATA_NO and row[self.COL_DATA_NO].strip() != self.DATA_NO:
                    continue

                try:
                    product_code = row[self.COL_PRODUCT_CODE].strip() if len(row) > self.COL_PRODUCT_CODE else ''
                    plant_code = row[self.COL_FACTORY].strip() if len(row) > self.COL_FACTORY else ''
                    inspection_type = row[self.COL_INSPECTION_TYPE].strip() if len(row) > self.COL_INSPECTION_TYPE else ''
                    record_type = row[self.COL_RECORD_TYPE].strip() if len(row) > self.COL_RECORD_TYPE else ''
                    ship_to = normalize_kubota_ship_to_code(row[self.COL_SHIP_TO] if len(row) > self.COL_SHIP_TO else '')

                    if not product_code:
                        continue

                    key = (product_code, inspection_type, ship_to)

                    if record_type == 'V2':
                        v2_rows[key] = (row, row_no)
                    elif record_type == 'V3':
                        v3_rows[key] = (row, row_no)

                except Exception as e:
                    self.errors.append(f"Row {row_no}: Failed to parse - {str(e)}")

            raw_records = []

            for key in v2_rows.keys():
                if key not in v3_rows:
                    self.warnings.append(f"Product {key[0]} (inspection={key[1]}, ship_to={key[2]}): V2 found but V3 missing")
                    continue

                v2_row, v2_row_no = v2_rows[key]
                v3_row, v3_row_no = v3_rows[key]

                try:
                    product_code, inspection_type, ship_to_code = key
                    calc_date = v2_row[self.COL_CALC_DATE].strip() if len(v2_row) > self.COL_CALC_DATE else ''
                    product_name = v2_row[self.COL_PRODUCT_NAME].strip() if len(v2_row) > self.COL_PRODUCT_NAME else ''
                    start_month = v2_row[self.COL_START_MONTH].strip() if len(v2_row) > self.COL_START_MONTH else ''
                    plant_code = v2_row[self.COL_FACTORY].strip() if len(v2_row) > self.COL_FACTORY else ''

                    date_headers = []
                    quantities = []
                    for col_idx in range(self.COL_DATA_START, min(len(v2_row), len(v3_row))):
                        date_str = v2_row[col_idx].strip() if col_idx < len(v2_row) else ''
                        qty_str = v3_row[col_idx].strip() if col_idx < len(v3_row) else ''
                        if date_str:
                            date_headers.append(date_str)
                            quantities.append(qty_str)

                    raw_record = StgOrderRawKubota(
                        customer_code=customer_code,
                        order_type=order_type,
                        source_file=file.name,
                        source_row_no=v2_row_no,
                        data_no=self.DATA_NO,
                        record_type='V2+V3',
                        product_code=product_code,
                        product_name=product_name,
                        inspection_type=inspection_type,
                        start_month=start_month,
                        date_headers=date_headers,
                        quantities=quantities,
                        raw_payload={
                            'v2_row': v2_row,
                            'v3_row': v3_row,
                            'v2_row_no': v2_row_no,
                            'v3_row_no': v3_row_no,
                            'calc_date': calc_date,
                            'plant_code': plant_code,
                            'ship_to': ship_to_code,
                            'encoding': encoding,
                            'factory': 'HIRAKATA_2027',
                        },
                        parse_status='PENDING'
                    )
                    raw_records.append(raw_record)

                except Exception as e:
                    self.errors.append(f"Product {product_code} (inspection={inspection_type}): {str(e)}")

            if not raw_records:
                return {
                    'success': False,
                    'message': 'No valid 36 forecast records found in file',
                    'errors': self.errors
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
            print(f"Kubota Hirakata 2027 Naiji Import Exception: {error_details}")
            return {
                'success': False,
                'message': f'Import failed: {str(e)}',
                'errors': self.errors + [str(e)]
            }

    def save_to_database(self, raw_records, file, customer_code):
        """Save raw records and create daily records"""
        from collections import defaultdict

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

            from datetime import timedelta
            firm_cutoff = datetime.now() - timedelta(days=90)
            product_codes = list({r.product_code for r in raw_records_with_ids})
            firm_dates_by_product_shipto = defaultdict(set)
            firm_qs = StgOrderDaily.objects.filter(
                customer=customer,
                order_type='FIRM',
                product_code__in=product_codes,
                created_at__gte=firm_cutoff,
            ).values('product_code', 'ship_to_code', 'due_date')
            for r in firm_qs:
                ship_to = (r['ship_to_code'] or '').strip()
                firm_dates_by_product_shipto[(r['product_code'], ship_to)].add(r['due_date'])

            daily_records = []
            skipped_firm = 0

            for raw in raw_records_with_ids:
                if not raw.date_headers or not raw.quantities:
                    raw.parse_status = 'ERROR'
                    raw.error_message = 'Missing date headers or quantities'
                    raw.save()
                    continue

                try:
                    for date_str, qty_str in zip(raw.date_headers, raw.quantities):
                        due_date = self.parse_date_from_yymdd(date_str)
                        if not due_date:
                            continue

                        raw_ship_to = ((raw.raw_payload or {}).get('ship_to', '') or '').strip()
                        firm_key = (raw.product_code, raw_ship_to)
                        if due_date in firm_dates_by_product_shipto.get(firm_key, set()):
                            skipped_firm += 1
                            continue

                        quantity = self.parse_quantity(qty_str)
                        if not quantity:
                            continue

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
                            due_date=due_date,
                            quantity=quantity,
                            ship_to_code=raw_ship_to,
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

            if skipped_firm > 0:
                self.warnings.append(f'確定優先: {skipped_firm}件の内示を除外（同一品番・納期でFIRM存在）')

        return len(raw_records), len(daily_records), min_raw_id, max_raw_id
