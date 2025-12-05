import csv
from orders.models import StgOrderRaw
from .base_import import BaseImportService


class TieraKakuteiImportService(BaseImportService):
    """Tiera Kakutei (Confirmed) CSV Import Service

    Format: Y55 type
    - Column 0: Data Type (データ区分) = "Y55"
    - Column 6: Product Code (図番)
    - Column 8: Delivery Date (納期) - YYYYMMDD format
    - Column 11: Product Name (品名)
    - Column 15: Quantity (数量)
    """

    IDENTIFIER_COL = 0  # データ区分
    IDENTIFIER_VALUE = 'Y55'
    COL_PRODUCT_CODE = 6   # 図番
    COL_DELIVERY_DATE = 8  # 納期
    COL_QUANTITY = 15      # 数量

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
