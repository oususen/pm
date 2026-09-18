from datetime import date, datetime, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from masters.models import BOM, BOMItem, Line, Process, Product, Routing, RoutingStep, Supplier
from production.models_line_backlog import LineBacklog
from production.models_process_realtime import ProcessRealtimeRecord
from production.views import LineBacklogViewSet
from purchase.order_proposal_views import _write_plan_qty_on_final_approval
from purchase.models import PurchaseOrderProposal, PurchaseOrderProposalLine
from purchase.process_resolver import (
    resolve_purchase_line,
    resolve_supplier_process,
    resolve_supplier_routing_process,
)
from purchase.views import (
    PurchaseActualBulkRegisterView,
    PurchaseActualDetailView,
    PurchaseActualRegisterView,
    PurchaseReceivingView,
)


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

    def test_resolve_supplier_routing_process_without_bom(self):
        supplier_line = resolve_purchase_line(self.subcon_supplier)
        self.g_process.line = None
        self.g_process.save(update_fields=['line'])
        routing = Routing.objects.create(
            product=self.parent,
            routing_code='R-SUB-NO-BOM',
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=self.g_process,
            line=supplier_line,
            supplier=self.subcon_supplier,
            output_product=self.subcon_child,
        )

        process = resolve_supplier_routing_process(
            supplier=self.subcon_supplier,
            line=supplier_line,
            product=self.subcon_child,
            reference=date(2026, 7, 21),
        )

        self.assertIsNotNone(process)
        self.assertEqual(process.id, self.g_process.id)

    def test_purchase_actual_register_uses_routing_process_without_bom(self):
        supplier_line = resolve_purchase_line(self.subcon_supplier)
        self.g_process.line = None
        self.g_process.save(update_fields=['line'])
        routing = Routing.objects.create(
            product=self.parent,
            routing_code='R-ACTUAL-NO-BOM',
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=self.g_process,
            line=supplier_line,
            supplier=self.subcon_supplier,
            output_product=self.subcon_child,
        )

        view = PurchaseActualRegisterView.as_view()
        request = self.factory.post(
            '/api/purchase-actual/register/',
            {
                'supplier_id': self.subcon_supplier.id,
                'product_code': self.subcon_child.product_code,
                'qty': 5,
                'arrival_date': '2026-07-21',
                'line_id': supplier_line.id,
            },
            format='json',
        )
        response = view(request)

        self.assertEqual(response.status_code, 201)
        record = ProcessRealtimeRecord.objects.get(id=response.data['id'])
        self.assertEqual(record.process_id, self.g_process.id)
        backlog = LineBacklog.objects.get(
            line_id=supplier_line.id,
            process_id=self.g_process.id,
            product_id=self.subcon_child.id,
            plan_date=date(2026, 7, 21),
            sequence_no=0,
        )
        self.assertEqual(backlog.actual_qty, 5)

    @patch('purchase.views._recalculate_purchase_supplier_progress')
    def test_purchase_actual_bulk_register_recalculates_progress_once(self, mock_progress):
        supplier_line = resolve_purchase_line(self.subcon_supplier)
        self.g_process.line = None
        self.g_process.save(update_fields=['line'])
        second_product = Product.objects.create(
            product_code='SUB-02',
            product_name='外作子品目2',
        )
        for index, product in enumerate([self.subcon_child, second_product], start=1):
            routing = Routing.objects.create(
                product=product,
                routing_code=f'R-BULK-{index}',
                is_default=True,
                is_active=True,
            )
            RoutingStep.objects.create(
                routing=routing,
                step_no=10,
                process=self.g_process,
                line=supplier_line,
                supplier=self.subcon_supplier,
                output_product=product,
            )

        request = self.factory.post(
            '/api/purchase-actual/bulk-register/',
            {
                'supplier_id': self.subcon_supplier.id,
                'arrival_date': '2026-07-21',
                'items': [
                    {'product_code': self.subcon_child.product_code, 'qty': 5},
                    {'product_code': second_product.product_code, 'qty': 7},
                ],
            },
            format='json',
        )
        response = PurchaseActualBulkRegisterView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['success_count'], 2)
        self.assertEqual(response.data['error_count'], 0)
        self.assertEqual(ProcessRealtimeRecord.objects.filter(
            event_data__source='PURCHASE_ACTUAL_INPUT',
        ).count(), 2)
        mock_progress.assert_called_once()
        self.assertEqual(
            mock_progress.call_args.kwargs['product_ids'],
            sorted([self.subcon_child.id, second_product.id]),
        )

    @patch('purchase.views._recalculate_purchase_supplier_progress')
    def test_purchase_actual_edit_and_delete_adjust_child_shipment(self, mock_progress):
        supplier_line = resolve_purchase_line(self.subcon_supplier)
        self.g_process.line = None
        self.g_process.save(update_fields=['line'])
        routing = Routing.objects.create(
            product=self.subcon_child,
            routing_code='R-EDIT-CHILD',
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=self.g_process,
            line=supplier_line,
            supplier=self.subcon_supplier,
            output_product=self.subcon_child,
        )
        component_line = Line.objects.create(
            line_code='COMPONENT-LINE',
            line_name='子部品ライン',
        )
        component_process = Process.objects.create(
            process_code='COMPONENT-PROC',
            process_name='子部品工程',
            line=component_line,
        )
        component = Product.objects.create(
            product_code='COMPONENT-01',
            product_name='子部品',
        )
        bom = BOM.objects.create(
            parent_product=self.subcon_child,
            version='v-child',
            valid_from=date(2026, 1, 1),
            is_active=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=component,
            quantity=2,
            process=component_process,
            line=component_line,
        )

        create_request = self.factory.post(
            '/api/purchase-actual/register/',
            {
                'supplier_id': self.subcon_supplier.id,
                'product_code': self.subcon_child.product_code,
                'qty': 5,
                'arrival_date': '2026-07-21',
            },
            format='json',
        )
        create_response = PurchaseActualRegisterView.as_view()(create_request)
        record_id = create_response.data['id']
        child_backlog = LineBacklog.objects.get(
            line=component_line,
            process=component_process,
            product=component,
            plan_date=date(2026, 7, 21),
            sequence_no=0,
        )
        self.assertEqual(child_backlog.actual_shipment_qty, 10)

        update_request = self.factory.put(
            f'/api/purchase-actual/{record_id}/',
            {
                'supplier_id': self.subcon_supplier.id,
                'qty': 8,
                'arrival_date': '2026-07-21',
            },
            format='json',
        )
        update_response = PurchaseActualDetailView.as_view()(update_request, record_id=record_id)
        self.assertEqual(update_response.status_code, 200)
        child_backlog.refresh_from_db()
        self.assertEqual(child_backlog.actual_shipment_qty, 16)

        delete_request = self.factory.delete(f'/api/purchase-actual/{record_id}/')
        delete_response = PurchaseActualDetailView.as_view()(delete_request, record_id=record_id)
        self.assertEqual(delete_response.status_code, 204)
        child_backlog.refresh_from_db()
        self.assertEqual(child_backlog.actual_shipment_qty, 0)
        self.assertGreaterEqual(mock_progress.call_count, 3)

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

    def test_pickup_purchase_creates_base_rows_on_routing_business_dates(self):
        supplier_line = resolve_purchase_line(self.buy_supplier)
        purchase_process = resolve_supplier_process(
            supplier=self.buy_supplier,
            line=supplier_line,
            product=self.buy_child,
            sourcing_type='BUY',
            create_purchase_process=True,
        )
        routing = Routing.objects.create(
            product=self.parent,
            routing_code='R-PICKUP-BASE',
            is_default=True,
            is_active=True,
            valid_from_datetime=datetime(2026, 7, 21, 7, 59),
            valid_to_datetime=datetime(2026, 7, 22, 7, 59),
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=purchase_process,
            line=supplier_line,
            supplier=self.buy_supplier,
            output_product=self.buy_child,
        )

        view = LineBacklogViewSet.as_view({'post': 'pickup_purchase'})
        request = self.factory.post(
            '/api/line-backlogs/pickup_purchase/',
            {
                'supplier_id': self.buy_supplier.id,
                'start_date': '2026-07-19',
                'end_date': '2026-07-22',
            },
            format='json',
        )
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['routing_base_created'], 2)
        rows = LineBacklog.objects.filter(
            line=supplier_line,
            process=purchase_process,
            product=self.buy_child,
            sequence_no=0,
        ).order_by('plan_date')
        self.assertEqual(list(rows.values_list('plan_date', flat=True)), [
            date(2026, 7, 20),
            date(2026, 7, 21),
        ])
        self.assertTrue(all(row.order_qty == 0 for row in rows))
        self.assertTrue(all(row.demand_qty_plan == 0 for row in rows))

    def test_pickup_purchase_creates_unbounded_base_rows_and_clears_only_legacy_plan_demand(self):
        supplier_line = resolve_purchase_line(self.buy_supplier)
        purchase_process = resolve_supplier_process(
            supplier=self.buy_supplier,
            line=supplier_line,
            product=self.buy_child,
            sourcing_type='BUY',
            create_purchase_process=True,
        )
        routing = Routing.objects.create(
            product=self.parent,
            routing_code='R-PICKUP-BASE-UNBOUNDED',
            is_default=True,
            is_active=True,
            valid_from_datetime=None,
            valid_to_datetime=None,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=purchase_process,
            line=supplier_line,
            supplier=self.buy_supplier,
            output_product=self.buy_child,
        )
        plan_row = LineBacklog.objects.create(
            plan_date=date(2026, 7, 20),
            process=purchase_process,
            product=self.buy_child,
            line=supplier_line,
            sequence_no=1,
            plan_qty=9,
            order_qty=77,
            order_qty_actual=55,
            demand_qty_plan=66,
        )

        view = LineBacklogViewSet.as_view({'post': 'pickup_purchase'})
        request = self.factory.post(
            '/api/line-backlogs/pickup_purchase/',
            {
                'supplier_id': self.buy_supplier.id,
                'start_date': '2026-07-20',
                'end_date': '2026-07-21',
            },
            format='json',
        )
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['routing_base_created'], 2)
        self.assertEqual(response.data['legacy_plan_demand_cleared'], 1)
        self.assertEqual(
            LineBacklog.objects.filter(
                line=supplier_line,
                process=purchase_process,
                product=self.buy_child,
                sequence_no=0,
            ).count(),
            2,
        )
        plan_row.refresh_from_db()
        self.assertEqual(plan_row.plan_qty, 9)
        self.assertEqual(plan_row.order_qty, 0)
        self.assertEqual(plan_row.order_qty_actual, 0)
        self.assertEqual(plan_row.demand_qty_plan, 0)

    def test_pickup_purchase_skips_routing_step_without_process(self):
        supplier_line = resolve_purchase_line(self.buy_supplier)
        routing = Routing.objects.create(
            product=self.parent,
            routing_code='R-PICKUP-BASE-NO-PROCESS',
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=None,
            line=supplier_line,
            supplier=self.buy_supplier,
            output_product=self.buy_child,
        )

        view = LineBacklogViewSet.as_view({'post': 'pickup_purchase'})
        request = self.factory.post(
            '/api/line-backlogs/pickup_purchase/',
            {
                'supplier_id': self.buy_supplier.id,
                'start_date': '2026-07-20',
                'end_date': '2026-07-21',
            },
            format='json',
        )
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['routing_base_created'], 0)
        self.assertEqual(response.data['routing_base_skipped_no_process'], 1)

    @patch('production.services.backlog_pickup_service.normalize_routing_reference_datetime', return_value=None)
    def test_pickup_purchase_uses_requested_dates_when_routing_datetime_normalization_returns_none(self, _normalize):
        supplier_line = resolve_purchase_line(self.buy_supplier)
        purchase_process = resolve_supplier_process(
            supplier=self.buy_supplier,
            line=supplier_line,
            product=self.buy_child,
            sourcing_type='BUY',
            create_purchase_process=True,
        )
        routing = Routing.objects.create(
            product=self.parent,
            routing_code='R-PICKUP-BASE-NORMALIZE-NONE',
            is_default=True,
            is_active=True,
            valid_from_datetime=datetime(2026, 7, 1, 8, 0),
            valid_to_datetime=datetime(2026, 7, 31, 8, 0),
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=purchase_process,
            line=supplier_line,
            supplier=self.buy_supplier,
            output_product=self.buy_child,
        )

        view = LineBacklogViewSet.as_view({'post': 'pickup_purchase'})
        request = self.factory.post(
            '/api/line-backlogs/pickup_purchase/',
            {
                'supplier_id': self.buy_supplier.id,
                'start_date': '2026-07-20',
                'end_date': '2026-07-21',
            },
            format='json',
        )
        response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['routing_base_created'], 2)
        self.assertEqual(
            list(
                LineBacklog.objects.filter(
                    line=supplier_line,
                    process=purchase_process,
                    product=self.buy_child,
                    sequence_no=0,
                ).order_by('plan_date').values_list('plan_date', flat=True)
            ),
            [date(2026, 7, 20), date(2026, 7, 21)],
        )

    def test_pickup_purchase_rejects_period_longer_than_120_days(self):
        view = LineBacklogViewSet.as_view({'post': 'pickup_purchase'})
        request = self.factory.post(
            '/api/line-backlogs/pickup_purchase/',
            {
                'supplier_id': self.buy_supplier.id,
                'start_date': '2026-01-01',
                'end_date': '2026-05-01',
            },
            format='json',
        )

        response = view(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn('120', response.data['detail'])

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
        self.assertEqual(response.data['detail'], '有効な仕入先ルーティング工程を一意に特定できない品番があります')
        self.assertEqual(len(response.data['unresolved_items']), 1)
        self.assertEqual(response.data['unresolved_items'][0]['product_id'], unresolved_product.id)
