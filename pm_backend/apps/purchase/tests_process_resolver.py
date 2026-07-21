from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from masters.models import BOM, BOMItem, Line, Process, Product, Supplier
from production.models_line_backlog import LineBacklog
from production.models_process_realtime import ProcessRealtimeRecord
from production.views import LineBacklogViewSet
from purchase.order_proposal_views import _write_plan_qty_on_final_approval
from purchase.models import PurchaseOrderProposal, PurchaseOrderProposalLine
from purchase.process_resolver import resolve_purchase_line, resolve_supplier_process
from purchase.views import PurchaseReceivingView


class PurchaseProcessResolverTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.g_line = Line.objects.create(
            line_code='GAI',
            line_name='外作ライン',
            line_type='OUTSOURCE',
        )
        self.g_process = Process.objects.create(
            process_code='G',
            process_name='外作',
            line=self.g_line,
            is_outsource=True,
        )
        self.parent = Product.objects.create(
            product_code='PARENT-01',
            product_name='親品目',
        )
        self.buy_child = Product.objects.create(
            product_code='BUY-01',
            product_name='購買子品目',
        )
        self.subcon_child = Product.objects.create(
            product_code='SUB-01',
            product_name='外作子品目',
        )
        self.buy_supplier = Supplier.objects.create(
            supplier_code='SUP-BUY',
            supplier_name='購買先',
            supplier_type='purchase',
        )
        self.subcon_supplier = Supplier.objects.create(
            supplier_code='SUP-SUB',
            supplier_name='外作先',
            supplier_type='outsource',
        )

    def test_resolve_supplier_process_returns_purchase_for_buy(self):
        line = resolve_purchase_line(self.buy_supplier)

        process = resolve_supplier_process(
            supplier=self.buy_supplier,
            line=line,
            product=self.buy_child,
            sourcing_type='BUY',
            create_purchase_process=True,
        )

        self.assertIsNotNone(process)
        self.assertEqual(process.process_code, 'PURCHASE')

    def test_resolve_supplier_process_prefers_outsource_process_for_subcon(self):
        line = resolve_purchase_line(self.subcon_supplier)
        bom = BOM.objects.create(
            parent_product=self.parent,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=self.subcon_child,
            quantity=1,
            sourcing_type='SUBCON',
            supplier=self.subcon_supplier,
            process=self.g_process,
            line=self.g_line,
            lead_time_days=1,
        )

        process = resolve_supplier_process(
            supplier=self.subcon_supplier,
            line=line,
            product=self.subcon_child,
            sourcing_type='SUBCON',
        )

        self.assertIsNotNone(process)
        self.assertEqual(process.id, self.g_process.id)

    def test_pickup_purchase_writes_subcon_backlog_with_outsource_process(self):
        supplier_line = resolve_purchase_line(self.subcon_supplier)
        bom = BOM.objects.create(
            parent_product=self.parent,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=self.subcon_child,
            quantity=2,
            sourcing_type='SUBCON',
            supplier=self.subcon_supplier,
            process=self.g_process,
            line=self.g_line,
            lead_time_days=1,
        )
        parent_process = Process.objects.create(
            process_code='PROC-PARENT',
            process_name='親工程',
            line=Line.objects.create(line_code='PARENT', line_name='親ライン'),
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 7, 22),
            process=parent_process,
            product=self.parent,
            line=parent_process.line,
            sequence_no=1,
            plan_qty=5,
        )

        view = LineBacklogViewSet.as_view({'post': 'pickup_purchase'})
        request = self.factory.post(
            '/api/line-backlogs/pickup_purchase/',
            {
                'supplier_id': self.subcon_supplier.id,
                'start_date': '2026-07-20',
                'end_date': '2026-07-31',
            },
            format='json',
        )
        response = view(request)

        self.assertEqual(response.status_code, 200)
        backlog = LineBacklog.objects.get(
            line_id=supplier_line.id,
            process_id=self.g_process.id,
            product_id=self.subcon_child.id,
            sequence_no=0,
        )
        self.assertEqual(backlog.order_qty, 10)
        self.assertEqual(backlog.demand_qty_plan, 10)

    def test_pickup_purchase_writes_buy_backlog_with_purchase_process(self):
        supplier_line = resolve_purchase_line(self.buy_supplier)
        purchase_process = resolve_supplier_process(
            supplier=self.buy_supplier,
            line=supplier_line,
            product=self.buy_child,
            sourcing_type='BUY',
            create_purchase_process=True,
        )
        bom = BOM.objects.create(
            parent_product=self.parent,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=self.buy_child,
            quantity=3,
            sourcing_type='BUY',
            supplier=self.buy_supplier,
            lead_time_days=1,
        )
        parent_process = Process.objects.create(
            process_code='PROC-PARENT-BUY',
            process_name='親工程購買',
            line=Line.objects.create(line_code='PARENT-BUY', line_name='親ライン購買'),
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 7, 22),
            process=parent_process,
            product=self.parent,
            line=parent_process.line,
            sequence_no=1,
            plan_qty=4,
        )

        view = LineBacklogViewSet.as_view({'post': 'pickup_purchase'})
        request = self.factory.post(
            '/api/line-backlogs/pickup_purchase/',
            {
                'supplier_id': self.buy_supplier.id,
                'start_date': '2026-07-20',
                'end_date': '2026-07-31',
            },
            format='json',
        )
        response = view(request)

        self.assertEqual(response.status_code, 200)
        backlog = LineBacklog.objects.get(
            line_id=supplier_line.id,
            process_id=purchase_process.id,
            product_id=self.buy_child.id,
            sequence_no=0,
        )
        self.assertEqual(backlog.order_qty, 12)
        self.assertEqual(backlog.demand_qty_plan, 12)

    def test_pickup_purchase_touches_updated_at_when_quantity_is_unchanged(self):
        supplier_line = resolve_purchase_line(self.buy_supplier)
        purchase_process = resolve_supplier_process(
            supplier=self.buy_supplier,
            line=supplier_line,
            product=self.buy_child,
            sourcing_type='BUY',
            create_purchase_process=True,
        )
        bom = BOM.objects.create(
            parent_product=self.parent,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=self.buy_child,
            quantity=3,
            sourcing_type='BUY',
            supplier=self.buy_supplier,
            lead_time_days=1,
        )
        parent_process = Process.objects.create(
            process_code='PROC-PARENT-BUY-TOUCH',
            process_name='親工程購買タッチ',
            line=Line.objects.create(line_code='PARENT-BUY-TOUCH', line_name='親ライン購買タッチ'),
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 7, 22),
            process=parent_process,
            product=self.parent,
            line=parent_process.line,
            sequence_no=1,
            plan_qty=4,
        )
        backlog = LineBacklog.objects.create(
            plan_date=date(2026, 7, 21),
            process_id=purchase_process.id,
            product_id=self.buy_child.id,
            line_id=supplier_line.id,
            sequence_no=0,
            order_qty=12,
            demand_qty_plan=12,
        )
        old_updated_at = timezone.now() - timedelta(days=30)
        LineBacklog.objects.filter(id=backlog.id).update(updated_at=old_updated_at)

        view = LineBacklogViewSet.as_view({'post': 'pickup_purchase'})
        request = self.factory.post(
            '/api/line-backlogs/pickup_purchase/',
            {
                'supplier_id': self.buy_supplier.id,
                'start_date': '2026-07-20',
                'end_date': '2026-07-31',
            },
            format='json',
        )
        response = view(request)

        self.assertEqual(response.status_code, 200)
        backlog.refresh_from_db()
        self.assertGreater(backlog.updated_at, old_updated_at)

    def test_final_approval_writes_subcon_plan_with_outsource_process(self):
        supplier_line = resolve_purchase_line(self.subcon_supplier)
        bom = BOM.objects.create(
            parent_product=self.parent,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=self.subcon_child,
            quantity=1,
            sourcing_type='SUBCON',
            supplier=self.subcon_supplier,
            process=self.g_process,
            line=self.g_line,
            lead_time_days=1,
        )
        proposal = PurchaseOrderProposal.objects.create(
            proposal_no='TEST-PO-001',
            supplier=self.subcon_supplier,
            order_date=date(2026, 7, 21),
            desired_delivery_date=date(2026, 7, 25),
        )
        PurchaseOrderProposalLine.objects.create(
            proposal=proposal,
            product=self.subcon_child,
            line=supplier_line,
            order_qty=12,
        )

        _write_plan_qty_on_final_approval(proposal)

        backlog = LineBacklog.objects.get(
            line_id=supplier_line.id,
            product_id=self.subcon_child.id,
            plan_date=date(2026, 7, 25),
            sequence_no=1,
        )
        self.assertEqual(backlog.process_id, self.g_process.id)
        self.assertEqual(backlog.plan_qty, 12)

    def test_final_approval_writes_buy_plan_with_purchase_process(self):
        supplier_line = resolve_purchase_line(self.buy_supplier)
        purchase_process = resolve_supplier_process(
            supplier=self.buy_supplier,
            line=supplier_line,
            product=self.buy_child,
            sourcing_type='BUY',
            create_purchase_process=True,
        )
        bom = BOM.objects.create(
            parent_product=self.parent,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=self.buy_child,
            quantity=1,
            sourcing_type='BUY',
            supplier=self.buy_supplier,
            lead_time_days=1,
        )
        proposal = PurchaseOrderProposal.objects.create(
            proposal_no='TEST-PO-002',
            supplier=self.buy_supplier,
            order_date=date(2026, 7, 21),
            desired_delivery_date=date(2026, 7, 25),
        )
        PurchaseOrderProposalLine.objects.create(
            proposal=proposal,
            product=self.buy_child,
            line=supplier_line,
            order_qty=8,
        )

        _write_plan_qty_on_final_approval(proposal)

        backlog = LineBacklog.objects.get(
            line_id=supplier_line.id,
            product_id=self.buy_child.id,
            plan_date=date(2026, 7, 25),
            sequence_no=1,
        )
        self.assertEqual(backlog.process_id, purchase_process.id)
        self.assertEqual(backlog.plan_qty, 8)

    def test_purchase_receiving_returns_error_when_supplier_process_is_unresolved(self):
        self.g_process.delete()
        unresolved_supplier = Supplier.objects.create(
            supplier_code='SUP-NO-PROC',
            supplier_name='工程未整備外作先',
            supplier_type='outsource',
        )
        unresolved_product = Product.objects.create(
            product_code='SUB-NO-PROC',
            product_name='工程未整備品',
        )

        view = PurchaseReceivingView.as_view()
        request = self.factory.post(
            '/api/purchase/receiving/',
            {
                'supplier_id': unresolved_supplier.id,
                'target_date': '2026-07-21',
                'items': [
                    {
                        'product_id': unresolved_product.id,
                        'received_qty': 5,
                    }
                ],
            },
            format='json',
        )
        response = view(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ProcessRealtimeRecord.objects.count(), 0)
        self.assertEqual(LineBacklog.objects.count(), 0)
        self.assertEqual(response.data['detail'], 'supplier process not found for some items')
        self.assertEqual(len(response.data['unresolved_items']), 1)
        self.assertEqual(response.data['unresolved_items'][0]['product_id'], unresolved_product.id)
