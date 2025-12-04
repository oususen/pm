# CSV Import Services

This directory contains CSV import services for different customers and formats.

## Architecture

The system uses a factory pattern where the appropriate import service is selected based on the customer code.

### File Structure

```
orders/services/
├── __init__.py
├── README.md (this file)
├── csv_import.py          # Default/Generic CSV import service
└── [customer]_import.py   # Customer-specific import services
```

## Default CSV Format (csv_import.py)

The default service expects CSV files with the following headers:

| Column Name    | Required | Description                    | Format            |
|----------------|----------|--------------------------------|-------------------|
| product_code   | Yes      | Product/Part code              | String            |
| due_date       | Yes      | Delivery date                  | YYYY-MM-DD or YYYY/MM/DD |
| quantity       | Yes      | Order quantity                 | Number            |
| plant_code     | No       | Plant/Factory code             | String            |
| ship_to_code   | No       | Ship-to location code          | String            |
| record_token   | No       | Unique record identifier       | String            |

### Example CSV:

```csv
product_code,due_date,quantity,plant_code,ship_to_code
PROD001,2025-01-15,100,PLANT01,SHIP01
PROD002,2025-01-20,200,PLANT01,SHIP02
PROD003,2025-02-10,150,PLANT02,SHIP01
```

Sample file: `d:\pm\sample_order.csv`

## Creating Customer-Specific Import Services

### Step 1: Create a new service file

Create a new file: `orders/services/[customer_name]_import.py`

Example: `tiera_import.py`, `honda_import.py`, etc.

### Step 2: Define the import service class

```python
# orders/services/tiera_import.py
import csv
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from orders.models import StgOrderRaw
from masters.models import Customer

class TieraImportService:
    """Tiera customer-specific CSV import service"""

    # Column index definitions (0-based)
    COL_ORDER_NUMBER = 7
    COL_PRODUCT_CODE = 11
    COL_DELIVERY_DATE = 13
    COL_QUANTITY = 15

    def __init__(self):
        self.errors = []
        self.warnings = []

    def import_csv(self, file, customer_code, order_type, source_system='CSV'):
        """Import Tiera-specific CSV format"""
        self.errors = []
        self.warnings = []

        try:
            # Read CSV with CP932 encoding (Shift-JIS variant)
            file.seek(0)
            raw_data = file.read()

            # Try decoding
            encodings = ['cp932', 'shift-jis', 'utf-8-sig', 'utf-8']
            decoded_file = None
            for encoding in encodings:
                try:
                    decoded_file = raw_data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if decoded_file is None:
                return {
                    'success': False,
                    'message': 'Failed to decode CSV file',
                    'errors': ['Unsupported encoding']
                }

            # Parse CSV (no header, using column indexes)
            lines = decoded_file.splitlines()
            csv_reader = csv.reader(lines)

            raw_records = []
            row_no = 0

            for row in csv_reader:
                row_no += 1

                # Skip header or empty rows
                if row_no == 1 or len(row) < max(self.COL_PRODUCT_CODE, self.COL_DELIVERY_DATE, self.COL_QUANTITY):
                    continue

                try:
                    # Extract data by column index
                    product_code = row[self.COL_PRODUCT_CODE].strip()
                    delivery_date_str = row[self.COL_DELIVERY_DATE].strip()
                    quantity_str = row[self.COL_QUANTITY].strip()

                    # Parse date (YYYYMMDD format)
                    due_date = None
                    if delivery_date_str and len(delivery_date_str) == 8:
                        try:
                            due_date = datetime.strptime(delivery_date_str, '%Y%m%d').date()
                        except ValueError:
                            self.warnings.append(f"Row {row_no}: Invalid date format: {delivery_date_str}")

                    # Parse quantity
                    quantity = None
                    if quantity_str:
                        try:
                            quantity = Decimal(quantity_str)
                        except:
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
                        raw_payload={'row': row},  # Store entire row for reference
                        parse_status='PENDING'
                    )
                    raw_records.append(raw_record)

                except Exception as e:
                    self.errors.append(f"Row {row_no}: {str(e)}")

            if not raw_records:
                return {
                    'success': False,
                    'message': 'No valid records found',
                    'errors': self.errors
                }

            # Save to database (continue with standard process...)
            # ... (same as default service)

            return {
                'success': True,
                'message': f'Imported {len(raw_records)} records',
                'raw_count': len(raw_records),
                'errors': self.errors,
                'warnings': self.warnings
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Import failed: {str(e)}',
                'errors': self.errors + [str(e)]
            }
```

### Step 3: Register the service in views.py

Edit `orders/views.py` and add your customer code mapping:

```python
def _get_import_service(self, customer_code):
    """Select appropriate import service based on customer code"""
    from .services.csv_import import CSVImportService

    # Add customer-specific services
    if customer_code == 'TIERA':
        from .services.tiera_import import TieraImportService
        return TieraImportService()
    elif customer_code == 'HONDA':
        from .services.honda_import import HondaImportService
        return HondaImportService()
    # Add more customers here...

    # Default service
    return CSVImportService()
```

## Testing

1. Use the sample CSV file to test the default service:
   - File: `d:\pm\sample_order.csv`
   - Customer: Any customer code
   - Expected: 3 records imported successfully

2. For customer-specific formats:
   - Create the appropriate customer-specific import service
   - Register it in views.py
   - Upload the customer's CSV file
   - Verify the data is correctly parsed

## Column Index vs Column Name

- **Column Index** (recommended for fixed-format files):
  - Use when CSV has no header or fixed column positions
  - Example: Tiera's format with data in columns 11, 13, 15
  - More reliable for Excel-exported CSVs

- **Column Name** (recommended for flexible formats):
  - Use when CSV has a header row with named columns
  - Example: Default service expecting 'product_code', 'due_date', 'quantity'
  - More flexible but requires consistent header names

## Troubleshooting

### Problem: All records show ERROR status

**Cause**: CSV format doesn't match the expected format

**Solution**:
1. Check the CSV file format
2. Create a customer-specific import service if needed
3. Verify column names/indexes match the data

### Problem: Encoding errors

**Cause**: CSV file uses unsupported encoding

**Solution**:
Add the encoding to the `encodings` list in the import service:
```python
encodings = ['cp932', 'shift-jis', 'utf-8-sig', 'utf-8', 'iso-2022-jp']
```

### Problem: Date parsing errors

**Cause**: Date format doesn't match expected format

**Solution**:
Add date format handling in the import service:
```python
# Try multiple date formats
for fmt in ['%Y%m%d', '%Y-%m-%d', '%Y/%m/%d']:
    try:
        due_date = datetime.strptime(date_str, fmt).date()
        break
    except ValueError:
        continue
```
