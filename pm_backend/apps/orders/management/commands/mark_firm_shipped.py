from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from orders.core.models import OrderLine
from shipping.models import ShipmentActual, ShipmentActualHistory


class Command(BaseCommand):
    help = "Create shipment actuals from firm order lines for a given year."

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

    def _create_history(self, instance, action):
        ShipmentActualHistory.objects.create(
            shipment_actual=instance,
            action=action,
            shipment_date=instance.shipment_date,
            product_code=instance.product_code,
            customer_code=instance.customer_code,
            ship_to_code=instance.ship_to_code,
            quantity=instance.quantity,
            remark=instance.remark,
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
        ).select_related("order__customer", "product")

        firm_map = defaultdict(lambda: {"qty": Decimal("0"), "product_id": None, "customer_id": None})
        for ol in order_lines:
            if not ol.due_date or not ol.product_code:
                continue
            customer_code = ol.order.customer.customer_code if ol.order_id else None
            ship_to_code = ol.ship_to_code or None
            key = (ol.product_code, customer_code, ship_to_code, ol.due_date)
            firm_map[key]["qty"] += Decimal(str(ol.quantity or 0))
            if not firm_map[key]["product_id"] and ol.product_id:
                firm_map[key]["product_id"] = ol.product_id
            if not firm_map[key]["customer_id"] and ol.order.customer_id:
                firm_map[key]["customer_id"] = ol.order.customer_id

        total_candidates = len(firm_map)
        created = 0
        updated = 0
        unchanged = 0
        duplicates = 0

        for (product_code, customer_code, ship_to_code, due_date), info in firm_map.items():
            qty = info["qty"]
            qs = ShipmentActual.objects.filter(
                shipment_date=due_date,
                product_code=product_code,
                customer_code=customer_code,
                ship_to_code=ship_to_code,
            )

            if qs.count() > 1:
                duplicates += 1
                continue

            if not qs.exists():
                created += 1
                if dry_run:
                    continue
                instance = ShipmentActual.objects.create(
                    shipment_date=due_date,
                    product_id=info["product_id"],
                    product_code=product_code,
                    customer_id=info["customer_id"],
                    customer_code=customer_code,
                    ship_to_code=ship_to_code,
                    quantity=qty,
                )
                self._create_history(instance, "CREATE")
                continue

            instance = qs.first()
            updates = {}
            if Decimal(str(instance.quantity or 0)) != qty:
                updates["quantity"] = qty
            if not instance.product_id and info["product_id"]:
                updates["product_id"] = info["product_id"]
            if not instance.customer_id and info["customer_id"]:
                updates["customer_id"] = info["customer_id"]

            if not updates:
                unchanged += 1
                continue

            updated += 1
            if dry_run:
                continue
            self._create_history(instance, "UPDATE")
            ShipmentActual.objects.filter(pk=instance.id).update(**updates)

        self.stdout.write(
            "Done. candidates=%s created=%s updated=%s unchanged=%s duplicates=%s dry_run=%s"
            % (total_candidates, created, updated, unchanged, duplicates, dry_run)
        )
