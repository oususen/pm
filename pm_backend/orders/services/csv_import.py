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
            # Read CSV file with encoding detection
            file.seek(0)
            raw_data = file.read()

            # Try multiple encodings
            decoded_file = None
            encodings = ['utf-8-sig', 'utf-8', 'shift-jis', 'cp932', 'iso-2022-jp']
            for encoding in encodings:
                try:
                    decoded_file = raw_data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if decoded_file is None:
                return {
                    'success': False,
                    'message': 'Failed to decode CSV file. Unsupported encoding.',
                    'errors': ['Could not decode file with any supported encoding (utf-8, shift-jis, cp932, iso-2022-jp)']
                }

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
                # Save raw records
                created_raws = StgOrderRaw.objects.bulk_create(raw_records)

                # Re-fetch to ensure we have primary keys
                raw_records_with_ids = StgOrderRaw.objects.filter(
                    source_file=file.name,
                    customer_code=customer_code
                ).order_by('-id')[:len(raw_records)]

                # Process raw data to daily using saved records
                daily_records = []
                error_count = 0
                success_count = 0

                for raw in raw_records_with_ids:
                    if not raw.product_code or not raw.due_date or not raw.quantity:
                        raw.parse_status = 'ERROR'
                        raw.error_message = 'Missing required fields'
                        raw.save()
                        error_count += 1
                        continue

                    # Find customer
                    try:
                        customer = Customer.objects.get(customer_code=raw.customer_code)
                    except Customer.DoesNotExist:
                        raw.parse_status = 'ERROR'
                        raw.error_message = f'Customer not found: {raw.customer_code}'
                        raw.save()
                        error_count += 1
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
                    raw.save()
                    success_count += 1

                # Save daily records
                if daily_records:
                    StgOrderDaily.objects.bulk_create(daily_records)

            return {
                'success': True,
                'message': f'Imported {len(created_raws)} raw records, created {len(daily_records)} daily records',
                'raw_count': len(created_raws),
                'daily_count': len(daily_records),
                'errors': self.errors,
                'warnings': self.warnings
            }

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"CSV Import Exception: {error_details}")
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
        superseded_orders = 0

        with transaction.atomic():
            for (customer_id, order_type, version_no, source_file), dailies in orders_dict.items():
                # Get customer code for order_no generation
                customer = Customer.objects.get(id=customer_id)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

                # Generate order_no based on order_type
                if order_type == 'FORECAST':
                    order_no = f"FC-{customer.customer_code}-{timestamp}"

                    # Delete existing forecast orders for this customer (overwrite)
                    old_forecast_orders = Order.objects.filter(
                        customer_id=customer_id,
                        order_type='FORECAST',
                        status='OPEN'
                    )
                    deleted_count = old_forecast_orders.count()
                    old_forecast_orders.delete()
                    if deleted_count > 0:
                        superseded_orders += deleted_count

                else:  # FIRM
                    order_no = f"FIRM-{customer.customer_code}-{timestamp}"

                # Create order header
                order = Order.objects.create(
                    customer_id=customer_id,
                    order_no=order_no,
                    order_type=order_type,
                    version_no=version_no,
                    source_system=dailies[0].source_system,
                    source_file=source_file,
                    order_date=datetime.now().date(),
                    status='OPEN'
                )
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

                # If this is a FIRM order, supersede overlapping FORECAST orders
                if order_type == 'FIRM':
                    # Get all due dates from this firm order
                    firm_due_dates = [daily.due_date for daily in dailies]
                    firm_product_codes = [daily.product_code for daily in dailies]

                    # Find forecast orders with overlapping products and dates
                    overlapping_forecast_orders = Order.objects.filter(
                        customer_id=customer_id,
                        order_type='FORECAST',
                        status='OPEN',
                        lines__product_code__in=firm_product_codes,
                        lines__due_date__in=firm_due_dates
                    ).distinct()

                    superseded_count = overlapping_forecast_orders.update(status='SUPERSEDED')
                    superseded_orders += superseded_count

        return {
            'orders': created_orders,
            'lines': created_lines,
            'deleted_forecast_orders': superseded_orders
        }

    @staticmethod
    def get_active_order_lines_for_scheduling(customer_id=None, product_code=None,
                                               start_date=None, end_date=None,
                                               aggregate=True):
        """
        Get active order lines for scheduling.

        Priority: FIRM orders with status='OPEN' take precedence over FORECAST orders.
        If a FIRM order exists for a specific product/date, FORECAST orders are ignored.

        When multiple order lines exist for the same product_code + due_date combination
        (e.g., 10+ order lines with different order numbers), this method can either:
        - Return aggregated quantities (aggregate=True, default): Sums quantities by
          product_code + due_date for scheduling calculations
        - Return individual lines (aggregate=False): Preserves all order line details
          including individual order numbers for reference

        Args:
            customer_id: Filter by customer (optional)
            product_code: Filter by product code (optional)
            start_date: Filter by due_date >= start_date (optional)
            end_date: Filter by due_date <= end_date (optional)
            aggregate: If True (default), aggregate quantities by product_code + due_date.
                      If False, return individual order lines with all details.

        Returns:
            If aggregate=True: QuerySet with aggregated data containing:
                - customer_id
                - customer_code
                - product_code
                - due_date
                - total_quantity (sum of all quantities)
                - order_type (FIRM or FORECAST)
                - line_count (number of individual order lines)
                - order_numbers (comma-separated list of order numbers)

            If aggregate=False: QuerySet of OrderLine objects with all details
        """
        from django.db.models import Q, Sum, Count, F
        from django.db.models.functions import Coalesce

        # Base query: Only OPEN orders
        queryset = OrderLine.objects.filter(order__status='OPEN')

        # Apply filters
        if customer_id:
            queryset = queryset.filter(order__customer_id=customer_id)
        if product_code:
            queryset = queryset.filter(product_code=product_code)
        if start_date:
            queryset = queryset.filter(due_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(due_date__lte=end_date)

        if aggregate:
            # Aggregate quantities by product_code + due_date
            # Group by customer, product, due_date, and order_type
            aggregated = queryset.values(
                'order__customer_id',
                'order__customer__customer_code',
                'product_code',
                'due_date',
                'order__order_type'
            ).annotate(
                total_quantity=Sum('quantity'),
                line_count=Count('id'),
                customer_id=F('order__customer_id'),
                customer_code=F('order__customer__customer_code'),
                order_type=F('order__order_type')
            ).order_by('due_date', 'order__order_type', 'product_code')

            return aggregated
        else:
            # Return individual order lines with all details
            return queryset.select_related(
                'order',
                'order__customer',
                'product'
            ).order_by('due_date', 'order__order_type', 'product_code', 'order__order_no', 'line_no')
