from datetime import date, datetime

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate

from masters.models import BOM, BOMItem, ContainerCapacity, Line, Process, Product, ProductContainer, Routing, Supplier
from masters.serializers import BOMItemSerializer, BOMSerializer, ProductSerializer
from masters.services.routing_service import (
    build_effective_routing_range_q,
    normalize_routing_reference_datetime,
    resolve_effective_routing,
)
from masters.views import BOMViewSet, LineViewSet, SupplierViewSet
from orders.core.models import KubotaSakaiDueAdjustment
from shipping.views_kubota_sakai_trip_assignment import KubotaSakaiTripPlanView


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


class BOMSerializerCoproductTest(TestCase):
    def test_virtual_set_parent_forces_coproduct_true(self):
        parent = Product.objects.create(
            product_code='TEST-VSET-PARENT',
            product_name='仮想セット親製品',
            is_virtual_set=True,
        )
        serializer = BOMSerializer(data={
            'parent_product': parent.id,
            'version': 'v1',
            'valid_from': '2026-07-10',
            'is_active': True,
            'is_coproduct': False,
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        bom = serializer.save()

        self.assertTrue(bom.is_coproduct)
        self.assertTrue(serializer.data['is_coproduct'])


class BOMDuplicateVersionActionTest(TestCase):
    def test_duplicate_version_creates_new_bom_with_same_parent_and_copied_items(self):
        user = get_user_model().objects.create_user(
            username='bom_duplicate_version_tester',
            password='testpass123',
        )
        parent = Product.objects.create(
            product_code='TEST-BOM-DUP-PARENT',
            product_name='BOM版複製テスト親製品',
        )
        child = Product.objects.create(
            product_code='TEST-BOM-DUP-CHILD',
            product_name='BOM版複製テスト子製品',
        )
        supplier = Supplier.objects.create(
            supplier_code='009999',
            supplier_name='版複製テスト仕入先',
            supplier_type='both',
        )
        bom = BOM.objects.create(
            parent_product=parent,
            version='v1',
            valid_from=date(2026, 7, 1),
            is_active=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=child,
            quantity=1,
            sourcing_type='SUBCON',
            supplier=supplier,
            time_unit='DAY',
            lead_time_days=3,
        )

        factory = APIRequestFactory()
        request = factory.post(
            f'/api/masters/boms/{bom.id}/duplicate_version/',
            {
                'version': 'v2',
                'valid_from': '2026-09-01',
                'is_active': True,
            },
            format='json',
        )
        force_authenticate(request, user=user)

        response = BOMViewSet.as_view({'post': 'duplicate_version'})(request, pk=bom.id)

        self.assertEqual(response.status_code, 201)
        new_bom = BOM.objects.get(id=response.data['new_bom_id'])
        self.assertEqual(new_bom.parent_product_id, bom.parent_product_id)
        self.assertEqual(new_bom.version, 'v2')
        self.assertEqual(new_bom.valid_from, date(2026, 9, 1))

        new_items = list(BOMItem.objects.filter(bom=new_bom))
        self.assertEqual(len(new_items), 1)
        self.assertEqual(new_items[0].child_product_id, child.id)
        self.assertEqual(new_items[0].supplier_id, supplier.id)
        self.assertEqual(new_items[0].lead_time_days, 3)

    def test_duplicate_version_rejects_same_version_name(self):
        user = get_user_model().objects.create_user(
            username='bom_duplicate_version_same_tester',
            password='testpass123',
        )
        parent = Product.objects.create(
            product_code='TEST-BOM-DUP-SAME-PARENT',
            product_name='BOM版複製同版テスト親製品',
        )
        bom = BOM.objects.create(
            parent_product=parent,
            version='v1',
            valid_from=date(2026, 7, 1),
            is_active=True,
        )

        factory = APIRequestFactory()
        request = factory.post(
            f'/api/masters/boms/{bom.id}/duplicate_version/',
            {
                'version': 'v1',
                'valid_from': '2026-09-01',
            },
            format='json',
        )
        force_authenticate(request, user=user)

        response = BOMViewSet.as_view({'post': 'duplicate_version'})(request, pk=bom.id)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], '元BOMと異なる版を指定してください。')


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

    def test_supplier_create_rejects_when_same_code_purchase_line_exists(self):
        user = get_user_model().objects.create_user(
            username='supplier_duplicate_line_tester',
            password='testpass123',
        )
        Line.objects.create(
            line_code='000722',
            line_name='既存購買ライン',
            line_type='PURCHASE',
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

        self.assertEqual(response.status_code, 400)
        self.assertIn('supplier_code', response.data)

    def test_supplier_update_syncs_purchase_line_code_and_name(self):
        user = get_user_model().objects.create_user(
            username='supplier_update_sync_tester',
            password='testpass123',
        )
        supplier = Supplier.objects.create(
            supplier_code='000722',
            supplier_name='旧仕入先名',
            supplier_type='both',
            order_email='',
        )
        Line.objects.create(
            line_code='000722',
            line_name='旧仕入先名',
            line_type='PURCHASE',
        )
        factory = APIRequestFactory()
        request = factory.put(
            f'/api/suppliers/{supplier.id}/',
            {
                'supplier_code': '000723',
                'supplier_name': '新仕入先名',
                'supplier_type': 'both',
                'order_email': '',
                'calendar': None,
            },
            format='json',
        )
        force_authenticate(request, user=user)

        response = SupplierViewSet.as_view({'put': 'update'})(request, pk=supplier.id)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Line.objects.filter(line_code='000722').exists())
        line = Line.objects.get(line_code='000723')
        self.assertEqual(line.line_name, '新仕入先名')
        self.assertEqual(line.line_type, 'PURCHASE')

    def test_purchase_line_code_cannot_be_updated_directly_when_linked_to_supplier(self):
        user = get_user_model().objects.create_user(
            username='purchase_line_lock_tester',
            password='testpass123',
        )
        Supplier.objects.create(
            supplier_code='000722',
            supplier_name='株式会社ハツメック',
            supplier_type='both',
            order_email='',
        )
        line = Line.objects.create(
            line_code='000722',
            line_name='株式会社ハツメック',
            line_type='PURCHASE',
        )
        factory = APIRequestFactory()
        request = factory.patch(
            f'/api/lines/{line.id}/',
            {'line_code': '000999'},
            format='json',
        )
        force_authenticate(request, user=user)

        response = LineViewSet.as_view({'patch': 'partial_update'})(request, pk=line.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn('line_code', response.data)

    def test_purchase_line_delete_is_blocked_when_linked_to_supplier(self):
        user = get_user_model().objects.create_user(
            username='purchase_line_delete_tester',
            password='testpass123',
        )
        Supplier.objects.create(
            supplier_code='000722',
            supplier_name='株式会社ハツメック',
            supplier_type='both',
            order_email='',
        )
        line = Line.objects.create(
            line_code='000722',
            line_name='株式会社ハツメック',
            line_type='PURCHASE',
        )
        factory = APIRequestFactory()
        request = factory.delete(f'/api/lines/{line.id}/')
        force_authenticate(request, user=user)

        response = LineViewSet.as_view({'delete': 'destroy'})(request, pk=line.id)

        self.assertEqual(response.status_code, 400)
        self.assertTrue(Line.objects.filter(id=line.id).exists())


class ProductSerializerContainerSyncTest(TestCase):
    def test_create_syncs_default_container_to_product_container(self):
        container = ContainerCapacity.objects.create(
            name='グレー小',
            container_code='GRAY-S',
            capacity=20,
        )
        serializer = ProductSerializer(data={
            'product_code': 'TEST-CONTAINER-CREATE',
            'product_name': '容器同期作成',
            'used_container': container.id,
            'capacity': 28,
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save()

        self.assertTrue(
            ProductContainer.objects.filter(
                product=product,
                container=container,
                capacity=28,
            ).exists()
        )

    def test_update_syncs_default_container_to_product_container(self):
        product = Product.objects.create(
            product_code='TEST-CONTAINER-UPDATE',
            product_name='容器同期更新',
        )
        container = ContainerCapacity.objects.create(
            name='グレー大',
            container_code='GRAY-L',
            capacity=18,
        )
        serializer = ProductSerializer(
            instance=product,
            data={
                'product_code': product.product_code,
                'product_name': product.product_name,
                'used_container': container.id,
                'capacity': 32,
            },
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        self.assertTrue(
            ProductContainer.objects.filter(
                product=product,
                container=container,
                capacity=32,
            ).exists()
        )


class KubotaSakaiTripPlanContainerFallbackTest(TestCase):
    def test_grid_includes_used_container_when_product_container_is_missing(self):
        container = ContainerCapacity.objects.create(
            name='グレー小',
            container_code='GRAY-S-FALLBACK',
            capacity=20,
        )
        Product.objects.create(
            product_code='TEST-KBT-CONTAINER',
            product_name='便計画容器候補',
            used_container=container,
            capacity=28,
        )
        KubotaSakaiDueAdjustment.objects.create(
            product_code='TEST-KBT-CONTAINER',
            ship_to_code='ZGHC',
            source_order_no='4500000001',
            order_type='FIRM',
            due_date=date(2026, 7, 29),
            demand_qty=28,
            delivery_qty=28,
            remaining_qty=0,
        )

        factory = APIRequestFactory()
        request = factory.get('/api/kubota-sakai-trip-assignments/grid/', {
            'target_date': '2026-07-29',
        })
        response = KubotaSakaiTripPlanView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['product_containers']['TEST-KBT-CONTAINER'],
            [{
                'container_id': container.id,
                'container_name': 'グレー小',
                'capacity': 28,
            }],
        )
