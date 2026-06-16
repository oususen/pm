from datetime import date, datetime

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate

from masters.models import BOM, BOMItem, Line, Process, Product, Routing, Supplier
from masters.serializers import BOMItemSerializer
from masters.services.routing_service import (
    build_effective_routing_range_q,
    normalize_routing_reference_datetime,
    resolve_effective_routing,
)
from masters.views import BOMViewSet, SupplierViewSet


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

    def test_generate_routing_keeps_non_overlapping_default_routing(self):
        user = get_user_model().objects.create_user(
            username='routing_bom_tester',
            password='testpass123',
        )
        parent = Product.objects.create(
            product_code='TEST-BOM-PARENT',
            product_name='BOM親製品',
        )
        child = Product.objects.create(
            product_code='TEST-BOM-CHILD',
            product_name='BOM子製品',
        )
        line = Line.objects.create(
            line_code='TEST-BOM-LINE',
            line_name='BOM試験ライン',
        )
        process = Process.objects.create(
            process_code='TEST-BOM-PROC',
            process_name='BOM試験工程',
            line=line,
        )
        bom = BOM.objects.create(
            parent_product=parent,
            version='v1',
            valid_from=date(2026, 3, 1),
            is_active=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=child,
            quantity=1,
            sourcing_type='MAKE',
            process=process,
            line=line,
            time_unit='MINUTE',
            duration_min=10,
        )
        existing = Routing.objects.create(
            product=parent,
            routing_code='AUTO-TEST-BOM-PARENT-v1',
            is_default=True,
            is_active=True,
            valid_to_datetime=datetime(2026, 3, 31, 7, 59, 59),
        )

        factory = APIRequestFactory()
        request = factory.post(
            f'/api/masters/boms/{bom.id}/generate_routing/',
            {'valid_from_datetime': '2026-04-01T08:00:00'},
            format='json',
        )
        force_authenticate(request, user=user)
        response = BOMViewSet.as_view({'post': 'generate_routing'})(request, pk=bom.id)

        self.assertEqual(response.status_code, 201)

        existing.refresh_from_db()
        generated = Routing.objects.exclude(id=existing.id).get(product=parent, routing_code='AUTO-TEST-BOM-PARENT-v1')
        self.assertTrue(existing.is_default)
        self.assertTrue(generated.is_default)


class BOMItemValidationTest(TestCase):
    def test_self_reference_is_rejected(self):
        parent = Product.objects.create(
            product_code='TEST-BOM-SELF-PARENT',
            product_name='自己参照テスト親製品',
        )
        line = Line.objects.create(
            line_code='TEST-BOM-SELF-LINE',
            line_name='自己参照試験ライン',
        )
        process = Process.objects.create(
            process_code='TEST-BOM-SELF-PROC',
            process_name='自己参照試験工程',
            line=line,
        )
        bom = BOM.objects.create(
            parent_product=parent,
            version='v1',
            valid_from=date(2026, 4, 1),
            is_active=True,
        )

        serializer = BOMItemSerializer(data={
            'bom': bom.id,
            'child_product': parent.id,
            'quantity': '1.000',
            'sourcing_type': 'MAKE',
            'process': process.id,
            'line': line.id,
            'time_unit': 'MINUTE',
            'duration_min': 10,
            'lead_time_days': 0,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('child_product', serializer.errors)


class SupplierAutoLineTest(TestCase):
    def test_supplier_create_also_creates_purchase_line_with_same_code_and_name(self):
        user = get_user_model().objects.create_user(
            username='supplier_line_tester',
            password='testpass123',
        )
        factory = APIRequestFactory()
        request = factory.post(
            '/api/suppliers/',
            {
                'supplier_code': '000722',
                'supplier_name': '株式会社ハツメック',
                'supplier_type': 'both',
                'order_email': '',
                'calendar': None,
            },
            format='json',
        )
        force_authenticate(request, user=user)

        response = SupplierViewSet.as_view({'post': 'create'})(request)

        self.assertEqual(response.status_code, 201)
        supplier = Supplier.objects.get(supplier_code='000722')
        line = Line.objects.get(line_code='000722')
        self.assertEqual(line.line_name, supplier.supplier_name)
        self.assertEqual(line.line_type, 'PURCHASE')
        self.assertTrue(line.is_active)

    def test_supplier_create_zero_pads_numeric_code_to_six_digits(self):
        user = get_user_model().objects.create_user(
            username='supplier_code_padding_tester',
            password='testpass123',
        )
        factory = APIRequestFactory()
        request = factory.post(
            '/api/suppliers/',
            {
                'supplier_code': '95',
                'supplier_name': '有限会社ゼンツー',
                'supplier_type': 'both',
                'order_email': '',
                'calendar': None,
            },
            format='json',
        )
        force_authenticate(request, user=user)

        response = SupplierViewSet.as_view({'post': 'create'})(request)

        self.assertEqual(response.status_code, 201)
        supplier = Supplier.objects.get(supplier_name='有限会社ゼンツー')
        line = Line.objects.get(line_code='000095')
        self.assertEqual(supplier.supplier_code, '000095')
        self.assertEqual(line.line_code, '000095')
