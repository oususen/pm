from datetime import date, datetime

from django.test import TestCase

from masters.models import Product, Routing
from masters.services.routing_service import (
    build_effective_routing_range_q,
    normalize_routing_reference_datetime,
    resolve_effective_routing,
)


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

    def test_build_effective_routing_range_q_includes_routing_that_starts_mid_period(self):
        query = build_effective_routing_range_q(date(2026, 3, 31), date(2026, 4, 2))
        routing = Routing.objects.create(
            product=Product.objects.create(
                product_code='TEST-ROUTING-RANGE',
                product_name='ルーティング期間テスト',
            ),
            routing_code='RANGE',
            is_default=True,
            is_active=True,
            valid_from_datetime=datetime(2026, 4, 1, 8, 0, 0),
        )

        self.assertTrue(Routing.objects.filter(pk=routing.pk).filter(query).exists())

    def test_build_effective_routing_range_q_excludes_routing_ended_before_period(self):
        product = Product.objects.create(
            product_code='TEST-ROUTING-RANGE-END',
            product_name='ルーティング終了期間テスト',
        )
        ended = Routing.objects.create(
            product=product,
            routing_code='ENDED',
            is_default=True,
            is_active=True,
            valid_to_datetime=datetime(2026, 3, 31, 7, 59, 59),
        )

        query = build_effective_routing_range_q(date(2026, 4, 1), date(2026, 4, 2))
        self.assertFalse(Routing.objects.filter(pk=ended.pk).filter(query).exists())

    def test_build_effective_routing_range_q_excludes_inactive_routing(self):
        product = Product.objects.create(
            product_code='TEST-ROUTING-INACTIVE',
            product_name='ルーティング無効テスト',
        )
        inactive = Routing.objects.create(
            product=product,
            routing_code='INACTIVE',
            is_default=True,
            is_active=False,
            valid_from_datetime=datetime(2026, 4, 1, 8, 0, 0),
        )

        query = build_effective_routing_range_q(date(2026, 4, 1), date(2026, 4, 2))
        self.assertFalse(Routing.objects.filter(pk=inactive.pk).filter(query).exists())

    def test_build_effective_routing_range_q_handles_reversed_dates(self):
        product = Product.objects.create(
            product_code='TEST-ROUTING-REVERSED',
            product_name='ルーティング逆順期間テスト',
        )
        routing = Routing.objects.create(
            product=product,
            routing_code='REVERSED',
            is_default=True,
            is_active=True,
            valid_from_datetime=datetime(2026, 4, 1, 8, 0, 0),
        )

        query = build_effective_routing_range_q(date(2026, 4, 2), date(2026, 3, 31))
        self.assertTrue(Routing.objects.filter(pk=routing.pk).filter(query).exists())

    def test_build_effective_routing_range_q_respects_7_59_and_8_00_boundary(self):
        product = Product.objects.create(
            product_code='TEST-ROUTING-BOUNDARY',
            product_name='ルーティング境界期間テスト',
        )
        before_boundary = Routing.objects.create(
            product=product,
            routing_code='BEFORE',
            is_default=False,
            is_active=True,
            valid_to_datetime=datetime(2026, 4, 1, 7, 59, 59),
        )
        after_boundary = Routing.objects.create(
            product=product,
            routing_code='AFTER',
            is_default=True,
            is_active=True,
            valid_from_datetime=datetime(2026, 4, 1, 8, 0, 0),
        )

        before_query = build_effective_routing_range_q(date(2026, 3, 31), date(2026, 3, 31))
        after_query = build_effective_routing_range_q(date(2026, 4, 1), date(2026, 4, 1))

        self.assertTrue(Routing.objects.filter(pk=before_boundary.pk).filter(before_query).exists())
        self.assertFalse(Routing.objects.filter(pk=before_boundary.pk).filter(after_query).exists())
        self.assertTrue(Routing.objects.filter(pk=after_boundary.pk).filter(after_query).exists())
