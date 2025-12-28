import csv
from orders.models import StgOrderRaw
from .base_import import BaseImportService


class TieraKakuteiImportService(BaseImportService):
    """Tiera Kakutei (Confirmed) CSV Import Service

    Format: Y55 type
    - Column 0: Data Type (データ区分) = "Y55"
    - Column 6: Product Code (図番)
    - Column 13: Delivery Date (納期) - YYYYMMDD format
    - Column 11: Product Name (品名)
    - Column 15: Quantity (数量)
    - Column 43: C表No/不良通知Ｎｏ
    - Header names are used when present: 図番 / 納期 / 注文数量(数量) / 品名(納品書用品名) / C表No/不良通知Ｎｏ
    """

    IDENTIFIER_COL = 0  # データ区分
    IDENTIFIER_VALUE = 'Y55'
    COL_PRODUCT_CODE = 6   # 図番
    COL_DELIVERY_DATE = 13  # 納期 (YYYYMMDD format)
    COL_PRODUCT_NAME = 11  # 品名
    COL_QUANTITY = 15      # 数量
    COL_C_TABLE_NO = 43    # C表No/不良通知Ｎｏ

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
            col_map = {}

            # Read header row (if exists)
            header = next(csv_reader, None)
            if header:
                row_no = 1
                for idx, name in enumerate(header):
                    col_map[name.strip()] = idx

            for row in csv_reader:
                row_no += 1

                # Check minimum columns
                product_code_col = col_map.get('図番', self.COL_PRODUCT_CODE)
                delivery_date_col = col_map.get('納期', self.COL_DELIVERY_DATE)
                quantity_col = col_map.get('注文数量', self.COL_QUANTITY)
                if '数量' in col_map:
                    quantity_col = col_map['数量']
                required_cols = max(
                    self.IDENTIFIER_COL,
                    product_code_col,
                    delivery_date_col,
                    quantity_col,
                ) + 1
                if len(row) < required_cols:
                    continue

                # Filter by identifier
                if row[self.IDENTIFIER_COL].strip() != self.IDENTIFIER_VALUE:
                    continue

                try:
                    # Extract data
                    product_code = row[product_code_col].strip()
                    delivery_date_str = row[delivery_date_col].strip()
                    quantity_str = row[quantity_col].strip()
                    product_name_col = (
                        col_map.get('品名')
                        or col_map.get('納品書用品名')
                        or self.COL_PRODUCT_NAME
                    )
                    product_name = ''
                    if product_name_col is not None and len(row) > product_name_col:
                        product_name = row[product_name_col].strip()
                    c_table_col = col_map.get('C表No/不良通知Ｎｏ', self.COL_C_TABLE_NO)
                    c_table_no = ''
                    if c_table_col is not None and len(row) > c_table_col:
                        c_table_no = row[c_table_col].strip()

                    # Parse date
                    due_date = self.parse_date(delivery_date_str)
                    if not due_date:
                        self.warnings.append(f"Row {row_no}: Invalid date: {delivery_date_str}")

                    # Parse quantity
                    quantity = self.parse_quantity(quantity_str)
                    if not quantity:
                        self.warnings.append(f"Row {row_no}: Invalid quantity: {quantity_str}")

                    # Create raw record
                    raw_record = StgOrderRaw(
                        customer_code=customer_code,
                        order_type=order_type,
                        source_system=source_system,
                        source_file=file.name,
                        source_row_no=row_no,
                        record_token='',
                        due_date=due_date,
                        product_code=product_code,
                        product_name=product_name,
                        quantity=quantity,
                        raw_payload={
                            'row': row,
                            'encoding': encoding,
                            'c_table_no_or_defect_notice_no': c_table_no,
                        },
                        parse_status='PENDING'
                    )
                    raw_records.append(raw_record)

                except Exception as e:
                    self.errors.append(f"Row {row_no}: {str(e)}")

            if not raw_records:
                return {
                    'success': False,
                    'message': f'No valid Y55 records found in file',
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
            print(f"Tiera Kakutei Import Exception: {error_details}")
            return {
                'success': False,
                'message': f'Import failed: {str(e)}',
                'errors': self.errors + [str(e)]
            }
