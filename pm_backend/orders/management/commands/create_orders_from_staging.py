from django.core.management.base import BaseCommand
from orders.domains.orders.services.csv_import import CSVImportService


class Command(BaseCommand):
    help = 'Create orders from all staging daily data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source-file',
            type=str,
            help='Filter by source file name (optional)',
        )

    def handle(self, *args, **options):
        service = CSVImportService()
        source_file = options.get('source_file')

        self.stdout.write('Creating orders from staging data...')

        result = service.create_orders_from_staging(source_file=source_file)

        self.stdout.write(self.style.SUCCESS(
            f'Successfully created {result["orders"]} orders with {result["lines"]} lines'
        ))

        if result.get('deleted_forecast_orders', 0) > 0:
            self.stdout.write(self.style.WARNING(
                f'Superseded {result["deleted_forecast_orders"]} forecast orders'
            ))
