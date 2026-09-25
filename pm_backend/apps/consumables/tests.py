from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import ApprovalRequest, ApprovalRouteConfig, Department, UserProfile

from .models import (
    Consumable,
    ConsumableDispatchOrder,
    ConsumableRequest,
    ConsumableStockMovement,
    ConsumableSupplier,
)
from .scheduler_tasks import calc_auto_request_quantity, create_auto_requests
from .services import normalize_qr_code_value
from .views import ConsumableStockMovementViewSet, ConsumableViewSet
from .views_dispatch import ConsumableDispatchOrderViewSet


class ConsumableTestBase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='worker', password='x', last_name='山田', first_name='太郎')
        team = Department.objects.create(name='製缶1班', level='team', display_id=1)
        UserProfile.objects.create(user=self.user, role='staff', employee_code='W001', team=team)
        self.admin = User.objects.create_superuser(username='boss', password='x', last_name='管理')
        self.supplier = ConsumableSupplier.objects.create(name='テスト商事', email='test@example.com')
        self.item = Consumable.objects.create(
            code='MASINA-00172', name='手袋', unit='双', stock_quantity=10, safety_stock=5,
            order_unit=10, unit_price=Decimal('120'), supplier=self.supplier,
        )

    def call(self, viewset, action, method, user, data=None, pk=None, query=''):
        request = getattr(self.factory, method)(f'/api/consumables/x/{query}', data or {}, format='json')
        force_authenticate(request, user=user)
        kwargs = {'pk': pk} if pk is not None else {}
        return viewset.as_view({method: action})(request, **kwargs)


class StockMovementTest(ConsumableTestBase):
    def test_outbound_decreases_stock_and_records_team(self):
        res = self.call(ConsumableStockMovementViewSet, 'outbound', 'post', self.user,
                        {'consumable': self.item.id, 'quantity': 3})
        self.assertEqual(res.status_code, 201)
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock_quantity, 7)
        mv = ConsumableStockMovement.objects.get()
        self.assertEqual(mv.stock_after, 7)
        self.assertEqual(mv.team_name, '製缶1班')
        self.assertEqual(mv.worker_name, '山田 太郎')
        self.assertEqual(mv.total_amount, Decimal('360'))

    def test_outbound_over_stock_is_rejected(self):
        res = self.call(ConsumableStockMovementViewSet, 'outbound', 'post', self.user,
                        {'consumable': self.item.id, 'quantity': 11})
        self.assertEqual(res.status_code, 400)
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock_quantity, 10)
        self.assertFalse(ConsumableStockMovement.objects.exists())

    def test_stock_cannot_be_changed_by_master_edit(self):
        res = self.call(ConsumableViewSet, 'partial_update', 'patch', self.admin,
                        {'stock_quantity': 99}, pk=self.item.id)
        self.assertEqual(res.status_code, 400)


class QrLookupTest(ConsumableTestBase):
    def test_normalize_existing_label_formats(self):
        self.assertEqual(normalize_qr_code_value('管理番号：MASINA-00172 品名：手袋'), 'MASINA-00172')
        self.assertEqual(normalize_qr_code_value('code=MASINA-00172name=手袋'), 'MASINA-00172')
        self.assertEqual(normalize_qr_code_value('6 MASINA-00172 日東'), 'MASINA-00172')

    def test_lookup_ignores_case_and_hyphen(self):
        res = self.call(ConsumableViewSet, 'lookup', 'get', self.user, query='?qr=masina00172')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['id'], self.item.id)


class AutoRequestTest(ConsumableTestBase):
    def test_quantity_formula_keeps_syomohin_behavior(self):
        # int((5*2-5)/10 + 1)*10 = 10、max(10, 10) = 10
        self.assertEqual(calc_auto_request_quantity(5, 5, 10), 10)
        # 端数がなくても1単位多くなる: int((10*2-0)/10 + 1)*10 = 30
        self.assertEqual(calc_auto_request_quantity(0, 10, 10), 30)

    def test_auto_request_is_not_duplicated(self):
        self.item.stock_quantity = 5
        self.item.save()
        self.assertEqual(create_auto_requests(), 1)
        self.assertEqual(create_auto_requests(), 0)
        req = ConsumableRequest.objects.get()
        self.assertEqual(req.request_type, 'auto')
        self.assertEqual(req.status, ConsumableRequest.STATUS_REQUESTED)

    def test_item_above_safety_stock_is_skipped(self):
        self.assertEqual(create_auto_requests(), 0)


@patch('consumables.views_dispatch.save_dispatch_order_pdf', return_value=b'%PDF')
class DispatchOrderTest(ConsumableTestBase):
    def setUp(self):
        super().setUp()
        ApprovalRouteConfig.objects.create(item_key='consumable_dispatch_order', item_name='消耗品注文書')
        self.req = ConsumableRequest.objects.create(
            consumable=self.item, quantity=20, unit_price=Decimal('120'), total_amount=Decimal('2400'),
            status=ConsumableRequest.STATUS_PREPARING, requested_at=datetime.now(),
        )

    def create_order(self):
        res = self.call(ConsumableDispatchOrderViewSet, 'create_order', 'post', self.admin,
                        {'supplier': self.supplier.id, 'request_ids': [self.req.id]})
        self.assertEqual(res.status_code, 201, res.data)
        return ConsumableDispatchOrder.objects.get(id=res.data['id'])

    def test_create_order_makes_approval_request(self, _pdf):
        order = self.create_order()
        self.assertTrue(order.order_number.startswith('PO-'))
        self.assertEqual(order.approval_request.status, 'created')
        self.assertEqual(order.approval_request.context['dispatch_order_id'], order.id)
        self.assertEqual(order.items.count(), 1)

    def test_cannot_send_before_approval(self, _pdf):
        order = self.create_order()
        res = self.call(ConsumableDispatchOrderViewSet, 'send', 'post', self.admin, {}, pk=order.id)
        self.assertEqual(res.status_code, 400)

    def test_receive_increases_stock_and_completes_request(self, _pdf):
        order = self.create_order()
        order.status = ConsumableDispatchOrder.STATUS_SENT
        order.save()
        ConsumableRequest.objects.filter(id=self.req.id).update(status=ConsumableRequest.STATUS_ORDERED)

        res = self.call(ConsumableDispatchOrderViewSet, 'receive', 'post', self.user, {}, pk=order.id)
        self.assertEqual(res.status_code, 200, res.data)
        self.item.refresh_from_db()
        self.assertEqual(self.item.stock_quantity, 30)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, ConsumableRequest.STATUS_RECEIVED)
        mv = ConsumableStockMovement.objects.get()
        self.assertEqual(mv.inbound_type, ConsumableStockMovement.INBOUND_DISPATCH)

    def test_delete_unsent_order_frees_requests(self, _pdf):
        order = self.create_order()
        approval_id = order.approval_request_id
        res = self.call(ConsumableDispatchOrderViewSet, 'destroy', 'delete', self.admin, pk=order.id)
        self.assertEqual(res.status_code, 204)
        self.assertFalse(ApprovalRequest.objects.filter(id=approval_id).exists())
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, ConsumableRequest.STATUS_PREPARING)
        self.assertFalse(self.req.dispatch_items.exists())
