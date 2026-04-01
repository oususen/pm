from datetime import date, datetime

from django.test import TestCase

from masters.models import Product, Routing
from masters.services.routing_service import normalize_routing_reference_datetime, resolve_effective_routing


class RoutingEffectiveDatetimeTest(TestCase):
    def test_resolve_effective_routing_uses_business_boundary_time_for_date_reference(self):
        product = Product.objects.create(
            product_code='TEST-ROUTING-TIME',
            product_name='ルーティング時刻テスト',
        )
        old_routing = Routing.objects.create(
            product=product,
            routing_code='OLD',
            is_default=True,
            is_active=True,
            valid_to_datetime=datetime(2026, 4, 1, 7, 59, 59),
        )
        new_routing = Routing.objects.create(
            product=product,
            routing_code='NEW',
            is_default=True,
            is_active=True,
            valid_from_datetime=datetime(2026, 4, 1, 8, 0, 0),
        )

        resolved_before = resolve_effective_routing(product.id, date(2026, 3, 31))
        resolved_after = resolve_effective_routing(product.id, date(2026, 4, 1))

        self.assertEqual(resolved_before.id, old_routing.id)
        self.assertEqual(resolved_after.id, new_routing.id)

    def test_normalize_routing_reference_datetime_returns_naive_datetime_when_reference_is_none(self):
        normalized = normalize_routing_reference_datetime()

        self.assertIsNone(normalized.tzinfo)
