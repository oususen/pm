from datetime import date, timedelta

from django.test import TestCase
from rest_framework.test import APIClient

from masters.models import Customer, Product, Routing
from orders.core.models import Order, OrderLine


class MissingRoutingItemsAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.customer = Customer.objects.create(customer_code='C001', customer_name='顧客A')
        self.product_without_routing = Product.objects.create(product_code='P001', product_name='未ルーティング品')
        self.product_with_routing = Product.objects.create(product_code='P002', product_name='ルーティング済み品')
        Routing.objects.create(product=self.product_with_routing, routing_code='RT-001', is_active=True)

        self.old_order = Order.objects.create(
            customer=self.customer,
            order_no='ORD-000',
            order_type='FIRM',
            status='OPEN',
            order_date=date.today(),
        )
        self.order = Order.objects.create(
            customer=self.customer,
            order_no='ORD-001',
            order_type='FIRM',
            status='OPEN',
            order_date=date.today(),
        )
        OrderLine.objects.create(
            order=self.order,
            line_no=1,
            product=self.product_without_routing,
            product_code='P001',
            quantity=10,
            due_date=date.today(),
        )
        OrderLine.objects.create(
            order=self.old_order,
            line_no=1,
            product=self.product_without_routing,
            product_code='P001',
            quantity=1,
            due_date=date.today(),
        )
        OrderLine.objects.create(
            order=self.order,
            line_no=2,
            product=self.product_with_routing,
            product_code='P002',
            quantity=5,
            due_date=date.today(),
        )

    def test_missing_routing_items_returns_only_unrouted_order_lines(self):
        response = self.client.get('/api/order-lines/missing-routing-items/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['product_code'], 'P001')
        self.assertEqual(response.data['results'][0]['order_no'], 'ORD-001')
        self.assertEqual(response.data['results'][0]['customer_code'], 'C001')

    def test_missing_routing_items_does_not_truncate_results_before_deduplication(self):
        customer = Customer.objects.create(customer_code='C002', customer_name='顧客B')
        base_date = date.today() + timedelta(days=1)

        for idx in range(501):
            product = Product.objects.create(product_code=f'P{idx:03d}', product_name=f'品目{idx}')
            order = Order.objects.create(
                customer=customer,
                order_no=f'ORD-{idx:03d}',
                order_type='FIRM',
                status='OPEN',
                order_date=base_date,
            )
            OrderLine.objects.create(
                order=order,
                line_no=1,
                product=product,
                product_code=product.product_code,
                quantity=1,
                due_date=base_date,
            )

        response = self.client.get('/api/order-lines/missing-routing-items/')

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data['count'], 501)
        self.assertTrue(any(item['product_code'] == 'P500' for item in response.data['results']))
