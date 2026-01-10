import csv
import io
from pathlib import Path

from django.core.management.base import BaseCommand

from orders.domains.orders.models import StgOrderRawTiera
from orders.domains.orders.services.csv_import import CSVImportService
from orders.domains.orders.services.tiera_kakutei_import import TieraKakuteiImportService
from orders.domains.orders.services.tiera_naiji_import import TieraNaijiImportService


ENCODINGS = ['cp932', 'shift-jis', 'utf-8-sig', 'utf-8', 'iso-2022-jp']


class NamedBytesIO(io.BytesIO):
    def __init__(self, data, name):
        super().__init__(data)
        self.name = name


def decode_bytes(data):
    for encoding in ENCODINGS:
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return None, None


def detect_order_type(data):
    decoded, _ = decode_bytes(data)
    if decoded is None:
        return None

    reader = csv.reader(decoded.splitlines())
    for row in reader:
        if not row:
            continue
        marker = row[0].strip()
        if marker == 'B17':
            return 'FORECAST'
        if marker == 'Y55':
            return 'FIRM'
    return None


class Command(BaseCommand):
    help = "Import all Tiera order CSVs from a path"

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            required=True,
            help='Root path to search for CSV files',
        )
        parser.add_argument(
            '--recursive',
            action='store_true',
            default=True,
            help='Search CSVs recursively (default: true)',
        )
        parser.add_argument(
            '--no-skip-existing',
            action='store_true',
            help='Re-import even if source_file already exists',
        )

    def handle(self, *args, **options):
        base_path = Path(options['path'])
        if not base_path.exists():
            self.stderr.write(f'Path not found: {base_path}')
            return

        recursive = options['recursive']
        skip_existing = not options['no_skip_existing']

        if base_path.is_file():
            files = [base_path]
        else:
            files = list(base_path.rglob('*.csv')) if recursive else list(base_path.glob('*.csv'))

        if not files:
            self.stdout.write('No CSV files found.')
            return

        files = sorted(files, key=lambda p: p.as_posix())

        total_files = 0
        imported_files = 0
        skipped_files = 0
        error_files = 0
        total_raw = 0
        total_daily = 0
        total_orders = 0
        total_lines = 0
        total_superseded = 0

        for path in files:
            total_files += 1
            data = path.read_bytes()
            order_type = detect_order_type(data)
            if order_type not in ('FORECAST', 'FIRM'):
                continue

            if skip_existing and StgOrderRawTiera.objects.filter(source_file=path.name).exists():
                skipped_files += 1
                self.stdout.write(f'Skip (exists): {path.name}')
                continue

            import_service = (
                TieraNaijiImportService()
                if order_type == 'FORECAST'
                else TieraKakuteiImportService()
            )
            file_obj = NamedBytesIO(data, path.name)

            result = import_service.import_csv(
                file_obj,
                customer_code='000001',
                order_type=order_type,
                source_system='CSV'
            )

            if not result.get('success'):
                error_files += 1
                self.stderr.write(f'Import failed: {path.name} -> {result.get("message")}')
                continue

            imported_files += 1
            total_raw += int(result.get('raw_count') or 0)
            total_daily += int(result.get('daily_count') or 0)

            order_service = CSVImportService()
            raw_id_range = (result.get('min_raw_id'), result.get('max_raw_id'))
            order_result = order_service.create_orders_from_staging(
                source_file=path.name,
                raw_id_range=raw_id_range
            )
            total_orders += int(order_result.get('orders') or 0)
            total_lines += int(order_result.get('lines') or 0)
            total_superseded += int(order_result.get('deleted_forecast_orders') or 0)

            self.stdout.write(
                f'Imported: {path.name} '
                f'raw={result.get("raw_count")} daily={result.get("daily_count")} '
                f'orders={order_result.get("orders")} lines={order_result.get("lines")}'
            )

        self.stdout.write(
            'Done. '
            f'files={total_files} imported={imported_files} '
            f'skipped={skipped_files} errors={error_files} '
            f'raw={total_raw} daily={total_daily} '
            f'orders={total_orders} lines={total_lines} '
            f'superseded={total_superseded}'
        )
