import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from masters.models import Product


class Command(BaseCommand):
    help = "Import unique products from '部品番号_整形' column in 品番原価構成表_階層付.csv into m_product."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="予備資料/品番原価構成表_階層付.csv",
            help="Path to CSV (UTF-8 with BOM) that contains 部品番号_整形 column.",
        )
        parser.add_argument(
            "--category",
            type=str,
            default="UNKNOWN",
            choices=[choice[0] for choice in Product.CATEGORY_CHOICES],
            help="Category to apply when creating new products.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["file"])
        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                if "部品番号_整形" not in reader.fieldnames:
                    raise CommandError("Column '部品番号_整形' not found in CSV header")

                records = list(reader)
        except UnicodeDecodeError as exc:
            raise CommandError(f"Failed to decode CSV as UTF-8: {exc}") from exc

        product_names = {}
        for row in records:
            code = (row.get("部品番号_整形") or "").strip()
            if not code:
                continue
            name = (row.get("品名規格") or "").strip() or code
            # 最初に出てきた品名を保持
            product_names.setdefault(code, name)

        unique_codes = set(product_names.keys())
        if not unique_codes:
            self.stdout.write(self.style.WARNING("No product codes found; nothing to do."))
            return

        existing_codes = set(
            Product.objects.filter(product_code__in=unique_codes).values_list("product_code", flat=True)
        )
        missing_codes = sorted(unique_codes - existing_codes)

        to_create = []
        for code in missing_codes:
            to_create.append(
                Product(
                    product_code=code,
                    product_name=product_names.get(code, code),
                    category=options["category"],
                    is_active=True,
                )
            )

        if not to_create:
            self.stdout.write(self.style.SUCCESS("All product codes already exist."))
            return

        created = Product.objects.bulk_create(to_create)
        self.stdout.write(
            self.style.SUCCESS(
                f"Inserted {len(created)} products (category={options['category']}), "
                f"skipped existing: {len(existing_codes)}"
            )
        )
