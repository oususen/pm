from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Q

from masters.models import Product
from orders.core.models import OrderLine
from shipping.models import DeliveryProgress


class Command(BaseCommand):
    help = (
        "t_order_line の明細から t_delivery_progress を追記します。"
        "対象は order.status=OPEN かつ FIRM のみ。"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--from-date",
            help="対象納期の開始日 (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--to-date",
            help="対象納期の終了日 (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="bulk_create のバッチサイズ (既定: 1000)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="登録せず件数のみ確認します",
        )

    def _parse_date(self, value):
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(f"日付形式が不正です: {value} (YYYY-MM-DD)") from exc

    def _normalize_quantity(self, qty):
        if qty is None:
            return 0, False
        if isinstance(qty, Decimal):
            if qty == qty.to_integral_value():
                return int(qty), False
            return int(qty), True
        return int(qty), False

    def handle(self, *args, **options):
        from_date = self._parse_date(options.get("from_date"))
        to_date = self._parse_date(options.get("to_date"))
        batch_size = int(options.get("batch_size") or 1000)
        dry_run = bool(options.get("dry_run"))

        firm_filter = Q(order_type="FIRM") | Q(order_type__isnull=True, order__order_type="FIRM")
        order_lines = OrderLine.objects.filter(order__status="OPEN").filter(firm_filter)

        if from_date:
            order_lines = order_lines.filter(due_date__gte=from_date)
        if to_date:
            order_lines = order_lines.filter(due_date__lte=to_date)

        order_lines = order_lines.select_related("order", "product")

        missing_product_codes = set()
        missing_product_count = 0
        fractional_qty_count = 0
        skipped = 0
        created = 0

        missing_code_candidates = {
            ol.product_code
            for ol in order_lines
            if not ol.product_id and ol.product_code
        }
        product_map = {}
        if missing_code_candidates:
            product_map = Product.objects.filter(
                product_code__in=missing_code_candidates
            ).in_bulk(field_name="product_code")

        buffer = []
        for ol in order_lines:
            if not ol.due_date:
                skipped += 1
                continue

            qty, fractional = self._normalize_quantity(ol.quantity)
            if qty <= 0:
                skipped += 1
                continue

            if fractional:
                fractional_qty_count += 1

            product_id = ol.product_id
            if not product_id and ol.product_code:
                product = product_map.get(ol.product_code)
                product_id = product.id if product else None
                if not product_id:
                    missing_product_codes.add(ol.product_code)
                    missing_product_count += 1

            buffer.append(
                DeliveryProgress(
                    order_id=ol.order_id,
                    product_id=product_id,
                    order_date=datetime.combine(ol.due_date, datetime.min.time()),
                    order_quantity=qty,
                    shipped_quantity=0,
                    remark=ol.remark or None,
                )
            )

            if len(buffer) >= batch_size:
                if not dry_run:
                    DeliveryProgress.objects.bulk_create(buffer, batch_size=batch_size)
                created += len(buffer)
                buffer = []

        if buffer:
            if not dry_run:
                DeliveryProgress.objects.bulk_create(buffer, batch_size=batch_size)
            created += len(buffer)

        self.stdout.write(self.style.SUCCESS("Import finished."))
        self.stdout.write(f"  created: {created}")
        self.stdout.write(f"  skipped: {skipped}")
        self.stdout.write(f"  missing_product: {missing_product_count}")
        if missing_product_codes:
            preview = ", ".join(sorted(missing_product_codes)[:10])
            self.stdout.write(f"  missing_product_codes: {preview}")
        self.stdout.write(f"  fractional_qty_lines: {fractional_qty_count}")
        if dry_run:
            self.stdout.write("  ※dry-runのためDB更新なし")
