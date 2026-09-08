import csv
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from orders.core.models import StgOrderRawKubota, StgOrderDaily
from masters.models import Customer, Product
from orders.core.services.ship_to_utils import ensure_ship_to_records, normalize_kubota_ship_to_code


class KubotaKmtNaijiImportService:
    """Kubota KMT Forecast (データNo=4) CSV Import Service"""

    DATA_NO = '4'
    FACTORY = 'KMT'

    COL_DATA_NO = 0
    COL_FACTORY = 1
    COL_PRODUCT_CODE = 7
    COL_PRODUCT_NAME = 8
    COL_SHIP_TO = 11  # 納入場所
    COL_INSPECTION_TYPE = 16
    COL_ORDER_NO = 18  # 注番（内示は空の場合あり）

    COL_PLAN_QTY_START = 46   # 予定納入指示数 1
    COL_PLAN_QTY_END = 70     # 予定納入指示数 25
    COL_DUE_DATE_START = 71   # 納入指示日 1
    COL_DUE_DATE_END = 95     # 納入指示日 25

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

    def _extract_calc_date(self, filename):
        # 先頭8桁 YYYYMMDD を calc_date として扱う（例: 20260415取込済_...）
        if filename and len(filename) >= 8 and filename[:8].isdigit():
            return filename[:8]
        return datetime.now().strftime('%Y%m%d')

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
            calc_date = self._extract_calc_date(file.name)

            for row in csv_reader:
                row_no += 1
                if len(row) <= self.COL_DUE_DATE_END:
                    continue

                data_no = row[self.COL_DATA_NO].strip() if len(row) > self.COL_DATA_NO else ''
                if data_no != self.DATA_NO:
                    continue

                product_code = row[self.COL_PRODUCT_CODE].strip() if len(row) > self.COL_PRODUCT_CODE else ''
                if not product_code:
                    continue

                product_name = row[self.COL_PRODUCT_NAME].strip() if len(row) > self.COL_PRODUCT_NAME else ''
                plant_code = row[self.COL_FACTORY].strip() if len(row) > self.COL_FACTORY else ''
                ship_to = normalize_kubota_ship_to_code(row[self.COL_SHIP_TO] if len(row) > self.COL_SHIP_TO else '')
                inspection_type = row[self.COL_INSPECTION_TYPE].strip() if len(row) > self.COL_INSPECTION_TYPE else ''
                order_no = row[self.COL_ORDER_NO].strip() if len(row) > self.COL_ORDER_NO else ''

                for idx in range(25):
                    qty_col = self.COL_PLAN_QTY_START + idx
                    date_col = self.COL_DUE_DATE_START + idx

                    due_date = self.parse_date(row[date_col].strip() if len(row) > date_col else '')
                    if not due_date:
                        continue

                    quantity = self.parse_quantity(row[qty_col].strip() if len(row) > qty_col else '')
                    if not quantity:
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
                            order_no=order_no,
                            inspection_type=inspection_type,
                            raw_payload={
                                'row': row,
                                'encoding': encoding,
                                'plant_code': plant_code,
                                'factory': self.FACTORY,
                                'ship_to': ship_to,
                                'calc_date': calc_date,
                                'forecast_slot': idx + 1,
                                'kubota_order_no': order_no,
                            },
                            parse_status='PENDING',
                        )
                    )

            if not raw_records:
                return {
                    'success': False,
                    'message': 'No valid データNo=4 forecast records found in file',
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
        from collections import defaultdict
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

            # 確定優先: 同一顧客・同一品番・同一納入先・同一納期にFIRMがあればFORECASTを除外
            # 直近90日のFIRMを参照して過去確定による恒久的な除外を避ける
            firm_cutoff = datetime.now() - timedelta(days=90)
            product_codes = list({r.product_code for r in raw_records_with_ids if r.product_code})
            firm_dates_by_product_shipto = defaultdict(set)
            if product_codes:
                firm_qs = StgOrderDaily.objects.filter(
                    customer=customer,
                    order_type='FIRM',
                    product_code__in=product_codes,
                    created_at__gte=firm_cutoff,
                ).values('product_code', 'ship_to_code', 'due_date')
                for row in firm_qs:
                    key = (row['product_code'], row['ship_to_code'] or '')
                    firm_dates_by_product_shipto[key].add(row['due_date'])

            for raw in raw_records_with_ids:
                if not raw.product_code or not raw.delivery_date or not raw.quantity:
                    raw.parse_status = 'ERROR'
                    raw.error_message = 'Missing required fields'
                    raw.save()
                    continue

                try:
                    raw_ship_to = (raw.raw_payload or {}).get('ship_to', '')
                    firm_key = (raw.product_code, raw_ship_to)
                    if raw.delivery_date in firm_dates_by_product_shipto.get(firm_key, set()):
                        raw.parse_status = 'PARSED'
                        raw.save()
                        continue

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
                            ship_to_code=raw_ship_to,
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

            ensure_ship_to_records(list(raw_records_with_ids), customer)

        return len(raw_records), len(daily_records), min_raw_id, max_raw_id
