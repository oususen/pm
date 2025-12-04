import csv
import json
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from orders.models import StgOrderRaw, StgOrderDaily, Order, OrderLine
from masters.models import Customer, Product


class CSVImportService:
    """CSV Import Service for Orders"""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def import_csv(self, file, customer_code, order_type, source_system='CSV'):
        """
        Import CSV file and create staging data

        Args:
            file: Uploaded file object
            customer_code: Customer code
            order_type: 'FIRM' or 'FORECAST'
            source_system: Source system name

        Returns:
            dict: Import result with statistics
        """
        self.errors = []
        self.warnings = []

        try:
            # Read CSV file
            file.seek(0)
            decoded_file = file.read().decode('utf-8-sig')
            csv_data = csv.DictReader(decoded_file.splitlines())

            raw_records = []
            row_no = 1

            for row in csv_data:
                row_no += 1
                try:
                    raw_record = self._create_raw_record(
                        row, row_no, customer_code, order_type,
                        source_system, file.name
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

            # Save to database
            with transaction.atomic():
                StgOrderRaw.objects.bulk_create(raw_records)

                # Process raw data to daily
                daily_records = self._process_to_daily(raw_records)
                if daily_records:
                    StgOrderDaily.objects.bulk_create(daily_records)

            return {
                'success': True,
                'message': f'Imported {len(raw_records)} raw records, created {len(daily_records)} daily records',
                'raw_count': len(raw_records),
                'daily_count': len(daily_records),
                'errors': self.errors,
                'warnings': self.warnings
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Import failed: {str(e)}',
                'errors': self.errors + [str(e)]
            }

    def _create_raw_record(self, row, row_no, customer_code, order_type, source_system, source_file):
        """Create a raw staging record from CSV row"""
        # Extract fields from CSV row
        product_code = row.get('product_code', '').strip()
        due_date_str = row.get('due_date', '').strip()
        quantity_str = row.get('quantity', '0').strip()

        # Parse date
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y/%m/%d').date()
                except ValueError:
                    self.warnings.append(f"Row {row_no}: Invalid date format: {due_date_str}")

        # Parse quantity
        quantity = None
        if quantity_str:
            try:
                quantity = Decimal(quantity_str)
            except:
                self.warnings.append(f"Row {row_no}: Invalid quantity: {quantity_str}")

        return StgOrderRaw(
            customer_code=customer_code,
            order_type=order_type,
            source_system=source_system,
            source_file=source_file,
            source_row_no=row_no,
            record_token=row.get('record_token', ''),
            due_date=due_date,
            product_code=product_code,
            quantity=quantity,
            raw_payload=row,
            parse_status='PENDING'
        )

    def _process_to_daily(self, raw_records):
        """Process raw records to daily normalized records"""
        daily_records = []

        for raw in raw_records:
            if not raw.product_code or not raw.due_date or not raw.quantity:
                raw.parse_status = 'ERROR'
                raw.error_message = 'Missing required fields'
                continue

            # Find customer
            try:
                customer = Customer.objects.get(customer_code=raw.customer_code)
            except Customer.DoesNotExist:
                raw.parse_status = 'ERROR'
                raw.error_message = f'Customer not found: {raw.customer_code}'
                continue

            daily = StgOrderDaily(
                raw=raw,
                customer=customer,
                order_type=raw.order_type,
                version_no='v1',
                product_code=raw.product_code,
                due_date=raw.due_date,
                quantity=raw.quantity,
                plant_code=raw.raw_payload.get('plant_code', ''),
                ship_to_code=raw.raw_payload.get('ship_to_code', ''),
                source_system=raw.source_system,
                source_file=raw.source_file
            )
            daily_records.append(daily)
            raw.parse_status = 'PARSED'

        return daily_records

    def create_orders_from_staging(self):
        """Create orders from staging daily data"""
        # Get all parsed daily records
        daily_records = StgOrderDaily.objects.filter(
            raw__parse_status='PARSED'
        ).select_related('customer')

        # Group by customer, order_type, version_no
        orders_dict = {}
        for daily in daily_records:
            key = (daily.customer_id, daily.order_type, daily.version_no, daily.source_file)
            if key not in orders_dict:
                orders_dict[key] = []
            orders_dict[key].append(daily)

        created_orders = 0
        created_lines = 0

        with transaction.atomic():
            for (customer_id, order_type, version_no, source_file), dailies in orders_dict.items():
                # Create order header
                order, created = Order.objects.get_or_create(
                    customer_id=customer_id,
                    order_no=f"CSV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    order_type=order_type,
                    version_no=version_no,
                    defaults={
                        'source_system': dailies[0].source_system,
                        'source_file': source_file,
                        'order_date': datetime.now().date(),
                        'status': 'OPEN'
                    }
                )

                if created:
                    created_orders += 1

                # Create order lines
                line_no = 1
                for daily in dailies:
                    # Find product
                    try:
                        product = Product.objects.get(product_code=daily.product_code)
                    except Product.DoesNotExist:
                        product = None

                    OrderLine.objects.create(
                        order=order,
                        line_no=line_no,
                        product=product,
                        product_code=daily.product_code,
                        quantity=daily.quantity,
                        due_date=daily.due_date,
                        plant_code=daily.plant_code,
                        ship_to_code=daily.ship_to_code
                    )
                    line_no += 1
                    created_lines += 1

        return {
            'orders': created_orders,
            'lines': created_lines
        }
