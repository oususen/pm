from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import call, patch

from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory

from masters.models import Line, Process, Product, BOM, BOMItem, Routing, RoutingStep
from production.models_line_backlog import LineBacklog
from production.models_process_realtime import ProcessRealtimeRecord
from production.models_process_work_session_change_history import ProcessWorkSessionChangeHistory
from production.models_process_work_session import ProcessWorkSession
from production.services.process_realtime_backlog_service import (
    apply_delta_to_inventory_and_progress,
    recalculate_inventory_after_session_change,
)
from production.views_process_realtime import ProcessRealtimeRecordViewSet


class ProcessRealtimeSessionRecalcTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.line = Line.objects.create(
            line_code='LTEST-RT',
            line_name='実績再計算ライン',
        )
        self.process = Process.objects.create(
            process_code='PTEST-RT',
            process_name='実績再計算工程',
            line=self.line,
        )
        self.product = Product.objects.create(
            product_code='TEST-RT',
            product_name='実績再計算品',
        )

    def make_dt(self, year, month, day, hour, minute=0):
        value = datetime(year, month, day, hour, minute)
        if settings.USE_TZ:
            return timezone.make_aware(value)
        return value

    @patch('production.inventory.inventory_calculator.recalculate_inventory_for_line')
    def test_recalculate_helper_uses_plan_date_range(self, mock_recalculate):
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product=self.product,
            line=self.line,
            sequence_no=0,
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 7),
            process=self.process,
            product=self.product,
            line=self.line,
            sequence_no=0,
        )

        session = SimpleNamespace(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product_id=self.product.id,
        )

        recalculate_inventory_after_session_change(session)

        mock_recalculate.assert_called_once_with(
            line_id=self.line.id,
            start_date=date(2026, 3, 5),
            end_date=date(2026, 3, 7),
            include_progress=True,
            line_final_only=False,
            product_ids=[self.product.id],
        )

    @patch('production.inventory.inventory_calculator.recalculate_inventory_for_line')
    def test_recalculate_helper_expands_to_parent_line_with_lt(self, mock_recalculate):
        parent_line = Line.objects.create(
            line_code='LPARENT-RT',
            line_name='親ライン',
        )
        parent_process = Process.objects.create(
            process_code='PPARENT-RT',
            process_name='親工程',
            line=parent_line,
        )
        parent_product = Product.objects.create(
            product_code='PARENT-RT',
            product_name='親品番',
        )
        BOM.objects.create(
            parent_product=parent_product,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
        )
        bom = BOM.objects.get(parent_product=parent_product)
        BOMItem.objects.create(
            bom=bom,
            child_product=self.product,
            quantity=Decimal('1'),
            process=parent_process,
            line=parent_line,
            lead_time_days=2,
        )
        routing = Routing.objects.create(
            product=parent_product,
            routing_code='R-PARENT-RT',
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=parent_process,
            line=parent_line,
            output_product=self.product,
            lead_time_days=2,
        )

        LineBacklog.objects.create(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product=self.product,
            line=self.line,
            sequence_no=0,
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 7),
            process=self.process,
            product=self.product,
            line=self.line,
            sequence_no=0,
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 3),
            process=parent_process,
            product=parent_product,
            line=parent_line,
            sequence_no=0,
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 8),
            process=parent_process,
            product=parent_product,
            line=parent_line,
            sequence_no=0,
        )

        session = SimpleNamespace(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product_id=self.product.id,
        )

        recalculate_inventory_after_session_change(session)

        self.assertEqual(mock_recalculate.call_count, 2)
        mock_recalculate.assert_has_calls(
            [
                call(
                    line_id=self.line.id,
                    start_date=date(2026, 3, 5),
                    end_date=date(2026, 3, 7),
                    include_progress=True,
                    line_final_only=False,
                    product_ids=[self.product.id],
                ),
                call(
                    line_id=parent_line.id,
                    start_date=date(2026, 3, 3),
                    end_date=date(2026, 3, 8),
                    include_progress=True,
                    line_final_only=False,
                    product_ids=[parent_product.id],
                ),
            ],
            any_order=True,
        )

    @patch('production.inventory.inventory_calculator.recalculate_inventory_for_line')
    def test_recalculate_helper_uses_bom_item_process_to_select_lt(self, mock_recalculate):
        shared_line = Line.objects.create(
            line_code='LSHARED-RT',
            line_name='共通ライン',
        )
        process_a = Process.objects.create(
            process_code='PSHARED-A',
            process_name='共通工程A',
            line=shared_line,
        )
        process_b = Process.objects.create(
            process_code='PSHARED-B',
            process_name='共通工程B',
            line=shared_line,
        )
        parent_product = Product.objects.create(
            product_code='PARENT-PROC',
            product_name='親品番工程選択',
        )
        bom = BOM.objects.create(
            parent_product=parent_product,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=self.product,
            quantity=Decimal('1'),
            process=process_a,
            line=shared_line,
            lead_time_days=1,
        )
        routing = Routing.objects.create(
            product=parent_product,
            routing_code='R-PARENT-PROC',
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=process_b,
            line=shared_line,
            output_product=self.product,
            lead_time_days=4,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=20,
            process=process_a,
            line=shared_line,
            output_product=self.product,
            lead_time_days=1,
        )

        LineBacklog.objects.create(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product=self.product,
            line=self.line,
            sequence_no=0,
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 4),
            process=process_a,
            product=parent_product,
            line=shared_line,
            sequence_no=0,
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 8),
            process=process_a,
            product=parent_product,
            line=shared_line,
            sequence_no=0,
        )

        session = SimpleNamespace(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product_id=self.product.id,
        )

        recalculate_inventory_after_session_change(session)

        self.assertEqual(mock_recalculate.call_count, 2)
        mock_recalculate.assert_has_calls(
            [
                call(
                    line_id=shared_line.id,
                    start_date=date(2026, 3, 4),
                    end_date=date(2026, 3, 8),
                    include_progress=True,
                    line_final_only=False,
                    product_ids=[parent_product.id],
                ),
            ],
            any_order=True,
        )

    @patch('production.inventory.inventory_calculator.recalculate_inventory_for_line')
    def test_recalculate_helper_uses_coproduct_children_as_recalc_targets(self, mock_recalculate):
        child = Product.objects.create(
            product_code='CHILD-RECALC',
            product_name='連産子再計算',
        )
        parent = Product.objects.create(
            product_code='STYD-RECALC',
            product_name='連産親再計算',
            is_virtual_set=True,
        )
        bom = BOM.objects.create(
            parent_product=parent,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
            is_coproduct=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=child,
            quantity=Decimal('1'),
            process=self.process,
            line=self.line,
        )
        routing = Routing.objects.create(
            product=child,
            routing_code='R-CHILD-RECALC',
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=self.process,
            line=self.line,
            output_product=child,
            lead_time_days=1,
        )

        LineBacklog.objects.create(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product=child,
            line=self.line,
            sequence_no=0,
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 7),
            process=self.process,
            product=child,
            line=self.line,
            sequence_no=0,
        )

        session = SimpleNamespace(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product_id=parent.id,
        )

        recalculate_inventory_after_session_change(session)

        mock_recalculate.assert_called_once_with(
            line_id=self.line.id,
            start_date=date(2026, 3, 5),
            end_date=date(2026, 3, 7),
            include_progress=True,
            line_final_only=False,
            product_ids=[child.id],
        )

    @patch('production.services.process_realtime_backlog_service.recalculate_child_stock_after_record_edit')
    def test_apply_delta_uses_coproduct_child_as_bom_parent(self, mock_recalculate_child_stock):
        parent = Product.objects.create(
            product_code='STYD-DELTA',
            product_name='連産親差分',
            is_virtual_set=True,
        )
        coproduct_child = Product.objects.create(
            product_code='CHILD-DELTA',
            product_name='連産子差分',
        )
        component = Product.objects.create(
            product_code='COMP-DELTA',
            product_name='子部品差分',
        )
        coproduct_bom = BOM.objects.create(
            parent_product=parent,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
            is_coproduct=True,
        )
        BOMItem.objects.create(
            bom=coproduct_bom,
            child_product=coproduct_child,
            quantity=Decimal('2'),
            process=self.process,
            line=self.line,
        )
        child_bom = BOM.objects.create(
            parent_product=coproduct_child,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
            is_coproduct=False,
        )
        BOMItem.objects.create(
            bom=child_bom,
            child_product=component,
            quantity=Decimal('3'),
            process=self.process,
            line=self.line,
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product=coproduct_child,
            line=self.line,
            sequence_no=0,
            stock_qty=0,
            planned_stock_qty=0,
            progress_qty=0,
            planned_progress_qty=0,
        )
        LineBacklog.objects.create(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product=component,
            line=self.line,
            sequence_no=0,
            stock_qty=100,
            planned_stock_qty=100,
            actual_shipment_qty=0,
        )

        session = SimpleNamespace(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product_id=parent.id,
        )

        with patch('production.services.process_realtime_backlog_service.get_business_today', return_value=date(2026, 3, 5)):
            apply_delta_to_inventory_and_progress(session, 4)

        coproduct_child_backlog = LineBacklog.objects.get(
            line=self.line,
            process=self.process,
            product=coproduct_child,
            plan_date=date(2026, 3, 5),
            sequence_no=0,
        )
        component_backlog = LineBacklog.objects.get(
            line=self.line,
            process=self.process,
            product=component,
            plan_date=date(2026, 3, 5),
            sequence_no=0,
        )
        self.assertEqual(coproduct_child_backlog.stock_qty, 8)
        self.assertEqual(coproduct_child_backlog.planned_stock_qty, 8)
        self.assertEqual(coproduct_child_backlog.progress_qty, 8)
        self.assertEqual(coproduct_child_backlog.planned_progress_qty, 8)
        self.assertEqual(component_backlog.stock_qty, 76)
        self.assertEqual(component_backlog.planned_stock_qty, 76)
        self.assertEqual(component_backlog.actual_shipment_qty, 24)
        mock_recalculate_child_stock.assert_called_once_with(
            parent_plan_date=date(2026, 3, 5),
            today=date(2026, 3, 5),
            child_product_ids={component.id},
        )

    @patch('production.services.process_realtime_backlog_service.recalculate_inventory_after_session_change')
    @patch('production.views_process_realtime.resolve_workday_date_for_process', return_value=date(2026, 3, 5))
    def test_create_manual_session_triggers_recalculation(self, _mock_plan_date, mock_recalculate):
        view = ProcessRealtimeRecordViewSet.as_view({'post': 'sessions'})
        request = self.factory.post(
            '/api/process-realtime/sessions/',
            {
                'process_id': self.process.id,
                'product_code': self.product.product_code,
                'started_at': '2026-03-05T09:00:00',
                'ended_at': '2026-03-05T10:00:00',
                'production_qty': 5,
                'change_reason': '登録漏れ補完',
            },
            format='json',
        )

        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = ProcessWorkSession.objects.get()
        backlog = LineBacklog.objects.get(
            line=self.line,
            process=self.process,
            product=self.product,
            plan_date=date(2026, 3, 5),
            sequence_no=0,
        )
        self.assertEqual(backlog.actual_qty, 5)
        history = ProcessWorkSessionChangeHistory.objects.get(session_record_id=session.id)
        self.assertEqual(history.operation_type, 'ADD')
        self.assertEqual(history.reason, '登録漏れ補完')
        mock_recalculate.assert_called_once()
        self.assertEqual(mock_recalculate.call_args[0][0].id, session.id)

    @patch('production.services.process_realtime_backlog_service.recalculate_inventory_after_session_change')
    @patch('production.views_process_realtime.resolve_workday_date_for_process', return_value=date(2026, 3, 5))
    def test_create_manual_session_creates_coproduct_child_records(self, _mock_plan_date, mock_recalculate):
        parent = Product.objects.create(
            product_code='STYD-SET',
            product_name='連産親',
            is_virtual_set=True,
        )
        child = Product.objects.create(
            product_code='CHILD-01',
            product_name='連産子',
        )
        bom = BOM.objects.create(
            parent_product=parent,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
            is_coproduct=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=child,
            quantity=Decimal('2'),
            process=self.process,
            line=self.line,
        )

        view = ProcessRealtimeRecordViewSet.as_view({'post': 'sessions'})
        request = self.factory.post(
            '/api/process-realtime/sessions/',
            {
                'process_id': self.process.id,
                'product_code': parent.product_code,
                'started_at': '2026-03-05T09:00:00',
                'ended_at': '2026-03-05T10:00:00',
                'production_qty': 5,
                'change_reason': '連産補完',
            },
            format='json',
        )

        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = ProcessWorkSession.objects.get(product=parent)
        records = ProcessRealtimeRecord.objects.filter(
            record_type='PRODUCTION',
            event_data__work_session_id=session.id,
        ).order_by('product_code')
        self.assertEqual(records.count(), 2)
        parent_record = records.get(product=parent)
        child_record = records.get(product=child)
        self.assertEqual(parent_record.qty, Decimal('5'))
        self.assertEqual(child_record.qty, Decimal('10'))
        self.assertEqual(child_record.event_data.get('coproduct_parent_record_id'), parent_record.id)
        child_backlog = LineBacklog.objects.get(
            line=self.line,
            process=self.process,
            product=child,
            plan_date=date(2026, 3, 5),
            sequence_no=0,
        )
        self.assertEqual(child_backlog.actual_qty, 10)
        mock_recalculate.assert_called_once()

    @patch('production.services.process_realtime_backlog_service.recalculate_inventory_after_session_change')
    def test_session_detail_update_creates_history(self, mock_recalculate):
        started_at = self.make_dt(2026, 3, 5, 9)
        ended_at = self.make_dt(2026, 3, 5, 10)
        session = ProcessWorkSession.objects.create(
            process=self.process,
            product=self.product,
            product_code=self.product.product_code,
            product_name=self.product.product_name,
            plan_date=date(2026, 3, 5),
            session_no=1,
            session_type='WORK',
            start_action='MANUAL',
            end_action='END',
            started_at=started_at,
            ended_at=ended_at,
            status='CLOSED',
            duration_seconds=3600,
            production_qty=5,
        )

        view = ProcessRealtimeRecordViewSet.as_view({'patch': 'session_detail'})
        request = self.factory.patch(
            f'/api/process-realtime/sessions/{session.id}/',
            {
                'production_qty': 7,
                'change_reason': '数量訂正',
            },
            format='json',
        )
        response = view(request, session_id=session.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        history = ProcessWorkSessionChangeHistory.objects.get(session_record_id=session.id)
        self.assertEqual(history.operation_type, 'UPDATE')
        self.assertEqual(history.reason, '数量訂正')
        self.assertIn('実績数量', history.change_summary)
        self.assertEqual(int(history.before_data['production_qty']), 5)
        self.assertEqual(int(history.after_data['production_qty']), 7)
        mock_recalculate.assert_called_once()

    @patch('production.services.process_realtime_backlog_service.recalculate_inventory_after_session_change')
    def test_session_detail_update_syncs_coproduct_child_record_qty(self, mock_recalculate):
        parent = Product.objects.create(
            product_code='STYD-UPD',
            product_name='連産親更新',
            is_virtual_set=True,
        )
        child = Product.objects.create(
            product_code='CHILD-UPD',
            product_name='連産子更新',
        )
        bom = BOM.objects.create(
            parent_product=parent,
            version='v1',
            valid_from=date(2026, 1, 1),
            is_active=True,
            is_coproduct=True,
        )
        BOMItem.objects.create(
            bom=bom,
            child_product=child,
            quantity=Decimal('3'),
            process=self.process,
            line=self.line,
        )
        session = ProcessWorkSession.objects.create(
            process=self.process,
            product=parent,
            product_code=parent.product_code,
            product_name=parent.product_name,
            plan_date=date(2026, 3, 5),
            session_no=1,
            session_type='WORK',
            start_action='MANUAL',
            end_action='END',
            started_at=self.make_dt(2026, 3, 5, 9),
            ended_at=self.make_dt(2026, 3, 5, 10),
            status='CLOSED',
            duration_seconds=3600,
            production_qty=2,
        )
        ProcessRealtimeRecord.objects.create(
            process=self.process,
            product=parent,
            product_code=parent.product_code,
            product_name=parent.product_name,
            record_type='PRODUCTION',
            qty=Decimal('2'),
            event_data={'work_session_id': session.id},
        )
        ProcessRealtimeRecord.objects.create(
            process=self.process,
            product=child,
            product_code=child.product_code,
            product_name=child.product_name,
            record_type='PRODUCTION',
            qty=Decimal('6'),
            event_data={'work_session_id': session.id, 'coproduct_parent_record_id': 99999},
        )

        view = ProcessRealtimeRecordViewSet.as_view({'patch': 'session_detail'})
        request = self.factory.patch(
            f'/api/process-realtime/sessions/{session.id}/',
            {
                'production_qty': 4,
                'change_reason': '連産数量訂正',
            },
            format='json',
        )
        response = view(request, session_id=session.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        records = ProcessRealtimeRecord.objects.filter(
            record_type='PRODUCTION',
            event_data__work_session_id=session.id,
        )
        self.assertEqual(records.count(), 2)
        self.assertEqual(records.get(product=parent).qty, Decimal('4'))
        self.assertEqual(records.get(product=child).qty, Decimal('12'))
        mock_recalculate.assert_called_once()

    @patch('production.services.process_realtime_backlog_service.recalculate_inventory_after_session_change')
    def test_session_detail_delete_triggers_recalculation(self, mock_recalculate):
        started_at = self.make_dt(2026, 3, 5, 9)
        ended_at = self.make_dt(2026, 3, 5, 10)
        session = ProcessWorkSession.objects.create(
            process=self.process,
            product=self.product,
            product_code=self.product.product_code,
            product_name=self.product.product_name,
            plan_date=date(2026, 3, 5),
            session_no=1,
            session_type='WORK',
            start_action='MANUAL',
            end_action='END',
            started_at=started_at,
            ended_at=ended_at,
            status='CLOSED',
            duration_seconds=3600,
            production_qty=5,
        )
        backlog = LineBacklog.objects.create(
            plan_date=date(2026, 3, 5),
            process=self.process,
            product=self.product,
            line=self.line,
            sequence_no=0,
            actual_qty=5,
        )
        routing = Routing.objects.create(
            product=self.product,
            routing_code='R-DELETE-VALID',
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=self.process,
            line=self.line,
            output_product=self.product,
        )

        view = ProcessRealtimeRecordViewSet.as_view({'delete': 'session_detail'})
        request = self.factory.delete(
            f'/api/process-realtime/sessions/{session.id}/',
            {
                'change_reason': '誤登録のため削除',
            },
            format='json',
        )
        response = view(request, session_id=session.id)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        backlog.refresh_from_db()
        self.assertEqual(backlog.actual_qty, 0)
        self.assertFalse(ProcessWorkSession.objects.filter(id=session.id).exists())
        history = ProcessWorkSessionChangeHistory.objects.get(session_record_id=session.id)
        self.assertEqual(history.operation_type, 'DELETE')
        self.assertEqual(history.reason, '誤登録のため削除')
        self.assertIn('削除:', history.change_summary)
        self.assertEqual(int(history.before_data['production_qty']), 5)
        self.assertEqual(history.after_data, {})
        mock_recalculate.assert_called_once()

    @patch('production.views_process_realtime.recalculate_inventory_for_product_impact')
    def test_session_detail_delete_removes_invalid_process_backlogs_and_recalculates_valid_route(self, mock_recalculate):
        valid_process = Process.objects.create(
            process_code='PVALID-DELETE',
            process_name='正規工程',
            line=self.line,
        )
        invalid_process = Process.objects.create(
            process_code='PINVALID-DELETE',
            process_name='誤工程',
            line=self.line,
        )
        routing = Routing.objects.create(
            product=self.product,
            routing_code='R-INVALID-DELETE',
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=routing,
            step_no=10,
            process=valid_process,
            line=self.line,
            output_product=self.product,
        )
        session = ProcessWorkSession.objects.create(
            process=invalid_process,
            product=self.product,
            product_code=self.product.product_code,
            product_name=self.product.product_name,
            plan_date=date(2026, 3, 5),
            session_no=1,
            session_type='WORK',
            start_action='MANUAL',
            end_action='END',
            started_at=self.make_dt(2026, 3, 5, 9),
            ended_at=self.make_dt(2026, 3, 5, 10),
            status='CLOSED',
            duration_seconds=3600,
            production_qty=5,
        )
        LineBacklog.objects.create(
            plan_date=session.plan_date,
            process=invalid_process,
            product=self.product,
            line=self.line,
            sequence_no=0,
            actual_qty=5,
        )
        LineBacklog.objects.create(
            plan_date=session.plan_date,
            process=invalid_process,
            product=self.product,
            line=self.line,
            sequence_no=1,
            plan_qty=5,
        )
        ProcessRealtimeRecord.objects.create(
            process=invalid_process,
            product=self.product,
            product_code=self.product.product_code,
            product_name=self.product.product_name,
            record_type='PRODUCTION',
            qty=Decimal('5'),
            event_data={'work_session_id': session.id},
        )

        view = ProcessRealtimeRecordViewSet.as_view({'delete': 'session_detail'})
        request = self.factory.delete(
            f'/api/process-realtime/sessions/{session.id}/',
            {'change_reason': '誤工程のため削除'},
            format='json',
        )
        response = view(request, session_id=session.id)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(LineBacklog.objects.filter(
            line=self.line,
            process=invalid_process,
            product=self.product,
            plan_date=session.plan_date,
        ).exists())
        self.assertFalse(ProcessRealtimeRecord.objects.filter(
            event_data__work_session_id=session.id,
        ).exists())
        self.assertFalse(ProcessWorkSession.objects.filter(id=session.id).exists())
        mock_recalculate.assert_called_once_with(
            line_id=self.line.id,
            product_id=self.product.id,
            plan_date=date(2026, 3, 5),
        )

    @patch('production.views_process_realtime.resolve_workday_date_for_process', return_value=date(2026, 3, 5))
    def test_operator_action_end_without_start_is_rejected(self, _mock_plan_date):
        view = ProcessRealtimeRecordViewSet.as_view({'post': 'create'})
        request = self.factory.post(
            '/api/process-realtime/',
            {
                'process_id': self.process.id,
                'record_type': 'OPERATOR_ACTION',
                'product_id': self.product.id,
                'operator_name': 'テスト作業者',
                'production_qty': 5,
                'event_data': {
                    'action': 'END',
                },
                'remarks': '終了誤操作確認',
            },
            format='json',
        )

        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('開始されていないため終了できません', str(response.data))
        self.assertEqual(ProcessRealtimeRecord.objects.count(), 0)
        self.assertEqual(ProcessWorkSession.objects.count(), 0)
