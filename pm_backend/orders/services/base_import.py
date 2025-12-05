import csv
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from orders.models import StgOrderRaw, StgOrderDaily
from masters.models import Customer, Product


class BaseImportService:
    """Base class for CSV import services"""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def decode_file(self, file):
        """Decode CSV file with multiple encoding attempts"""
        file.seek(0)
        raw_data = file.read()

        encodings = ['cp932', 'shift-jis', 'utf-8-sig', 'utf-8', 'iso-2022-jp']
        for encoding in encodings:
            try:
                return raw_data.decode(encoding), encoding
            except UnicodeDecodeError:
                continue

        return None, None

    def parse_date(self, date_str):
        """Parse date string in multiple formats"""
        if not date_str or date_str == '':
            return None

        date_str = str(date_str).strip()
        
        # Try YYYYMMDD format
        if len(date_str) == 8 and date_str.isdigit():
            try:
                return datetime.strptime(date_str, '%Y%m%d').date()
            except ValueError:
                pass

        # Try YYYY/MM/DD format
        if '/' in date_str:
            try:
                return datetime.strptime(date_str, '%Y/%m/%d').date()
            except ValueError:
                pass

        # Try YYYY-MM-DD format
        if '-' in date_str:
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        return None

    def parse_quantity(self, quantity_str):
        """Parse quantity string to Decimal"""
        if not quantity_str or quantity_str == '':
            return None

        try:
            quantity_str = str(quantity_str).strip().replace(',', '')
            return Decimal(quantity_str)
        except:
            return None

    def save_to_database(self, raw_records, file, customer_code):
        """Save raw records and create daily records

        Returns:
            tuple: (raw_count, daily_count, min_raw_id, max_raw_id)
        """
        with transaction.atomic():
            # Save raw records
            created_raws = StgOrderRaw.objects.bulk_create(raw_records)

            # Re-fetch to ensure we have primary keys
            raw_records_with_ids = StgOrderRaw.objects.filter(
                source_file=file.name,
                customer_code=customer_code
            ).order_by('-id')[:len(raw_records)]

            # Track min and max IDs for this import
            raw_ids = [r.id for r in raw_records_with_ids]
            min_raw_id = min(raw_ids) if raw_ids else None
            max_raw_id = max(raw_ids) if raw_ids else None

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

                # Check and register product if not exists
                product_name_for_master = raw.product_name if raw.product_name else raw.product_code
                product_name_half_for_master = raw.product_name_halfwidth if raw.product_name_halfwidth else None
                product, created = Product.objects.get_or_create(
                    product_code=raw.product_code,
                    defaults={
                        'product_name': product_name_for_master,
                        'product_name_halfwidth': product_name_half_for_master,
                        'category': 'PURCHASED',  # Default to purchased item
                        'unit': '個',
                        'is_active': True
                    }
                )
                if created:
                    self.warnings.append(f'Auto-registered new product: {raw.product_code} ({product_name_for_master})')

                daily = StgOrderDaily(
                    raw=raw,
                    customer=customer,
                    order_type=raw.order_type,
                    version_no='v1',
                    product_code=raw.product_code,
                    product_name=raw.product_name,
                    product_name_halfwidth=raw.product_name_halfwidth,
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

        return len(created_raws), len(daily_records), min_raw_id, max_raw_id

    def import_csv(self, file, customer_code, order_type, source_system='CSV'):
        """
        Import CSV file - to be implemented by subclasses
        
        Subclasses should:
        1. Decode the file
        2. Parse CSV data
        3. Extract product_code, due_date, quantity
        4. Create StgOrderRaw records
        5. Call save_to_database()
        """
        raise NotImplementedError("Subclasses must implement import_csv method")
