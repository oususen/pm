import csv
from orders.models import StgOrderRaw
from .base_import import BaseImportService


class TieraNaijiImportService(BaseImportService):
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
                    raw_record = StgOrderRaw(
                        customer_code=customer_code,
                        order_type=order_type,
                        source_system=source_system,
                        source_file=file.name,
                        source_row_no=row_no,
                        record_token='',
                        due_date=due_date,
                        product_code=product_code,
                        product_name=product_name_full,
                        product_name_halfwidth=product_name_half,
                        quantity=quantity,
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
            raw_count, daily_count = self.save_to_database(raw_records, file, customer_code)

            return {
                'success': True,
                'message': f'Imported {raw_count} raw records, created {daily_count} daily records',
                'raw_count': raw_count,
                'daily_count': daily_count,
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
