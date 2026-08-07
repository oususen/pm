from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from masters.models import ContainerCapacity, Product, Supplier, SupplierTruck
from .models import PurchaseAutoOrderSendConfig


class PurchaseAutoOrderSendTruckLoadCheckViewTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='tester', password='secret')
        self.supplier = Supplier.objects.create(supplier_code='S001', supplier_name='テスト仕入先')
        self.config = PurchaseAutoOrderSendConfig.objects.create(supplier=self.supplier)
        self.container = ContainerCapacity.objects.create(
            name='箱',
            width=100,
            depth=100,
            height=100,
            capacity=1,
            can_mix=True,
            stackable=True,
            max_stack=1,
        )
        self.product = Product.objects.create(
            product_code='P001',
            product_name='テスト品',
            used_container=self.container,
            capacity=1,
        )
        self.truck = SupplierTruck.objects.create(
            supplier=self.supplier,
            name='TRUCK-01',
            width=1000,
            depth=1000,
            height=1000,
            max_weight=10000,
            departure_time='08:00:00',
            arrival_time='12:00:00',
        )

    def test_truck_load_check_returns_result(self):
        self.client.force_login(self.user)
        url = reverse('purchase-auto-order-send-truck-load-check', args=[self.config.id])
        response = self.client.post(
            url,
            {
                'truck_id': self.truck.id,
                'items': [
                    {'product_code': self.product.product_code, 'qty': 1},
                ],
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['can_fit'])
        self.assertEqual(data['truck']['id'], self.truck.id)
        self.assertEqual(data['assignments'][0]['product_code'], self.product.product_code)
