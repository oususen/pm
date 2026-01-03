from datetime import date

from django.core.management.base import BaseCommand
from django.db.models import F

from orders.models import OrderLine


class Command(BaseCommand):
    help = "Set OrderLine.actual_shipment_qty to firm quantities for a given year."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=2025,
            help="Target year (default: 2025)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Calculate only, do not update DB",
        )

    def handle(self, *args, **options):
        year = int(options["year"])
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        dry_run = bool(options["dry_run"])

        order_lines = OrderLine.objects.filter(
            order__status="OPEN",
            order__order_type="FIRM",
            due_date__range=[start_date, end_date],
        )

        total_candidates = order_lines.count()
        targets = order_lines.exclude(actual_shipment_qty=F("quantity"))
        total_updates = targets.count()

        if total_updates and not dry_run:
            total_updates = targets.update(actual_shipment_qty=F("quantity"))

        self.stdout.write(
            "Done. candidates=%s updated=%s dry_run=%s"
            % (total_candidates, total_updates, dry_run)
        )
