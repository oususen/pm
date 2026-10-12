"""中間工程への再配置が親品IDを使い、品番変更に追従することを検証する。"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from masters.models import Calendar, Customer, Line, Process, Product, Routing, RoutingStep
from orders.core.models import Order, OrderLine
from production.models import LineDemand
from production.services.order_expansion import OrderExpansionService


class OrderExpansionParentProductTest(TestCase):
    def test_intermediate_parent_rename_keeps_child_date_and_quantity(self):
        calendar = Calendar.objects.create(calendar_code='PARENT-CAL', calendar_name='カレンダ')
        line = Line.objects.create(line_code='PARENT-LINE', line_name='ライン', calendar=calendar)
        process = Process.objects.create(process_code='PARENT-P', process_name='工程', line=line)
        customer = Customer.objects.create(customer_code='PARENT-CUSTOMER', customer_name='得意先')
        parent = Product.objects.create(product_code='FG-OLD', product_name='完成品', is_final_product=True)
        child = Product.objects.create(product_code='CHILD-ID', product_name='子品')
        routing = Routing.objects.create(product=parent, routing_code='PARENT-ROUTE', is_default=True)
        RoutingStep.objects.create(routing=routing, step_no=3, process=process, line=line, output_product=parent, parent_product=parent, hierarchy_path='final', lead_time_days=0)
        RoutingStep.objects.create(routing=routing, step_no=2, process=process, line=line, output_product=parent, parent_product=parent, hierarchy_path='', lead_time_days=2)
        child_step = RoutingStep.objects.create(routing=routing, step_no=1, process=process, line=line, output_product=child, parent_product=parent, hierarchy_path='1', lead_time_days=1, remark='FG-OLD')
        parent.product_code = 'FG-NEW'
        parent.save(update_fields=['product_code'])
        order = Order.objects.create(customer=customer, order_no='PARENT-ORDER', order_type='FIRM', status='OPEN', version_no='v1')
        due = date(2026, 11, 20)
        OrderLine.objects.create(order=order, line_no=1, product=parent, product_code=parent.product_code, order_type='FIRM', quantity=Decimal('5'), due_date=due)
        # 営業日算出は別仕様。ここでは階層によるLT累積だけを判定する。
        with patch.object(OrderExpansionService, '_shift_business_days', side_effect=lambda _cal, day, lead: day - timedelta(days=lead)):
            OrderExpansionService().expand_open_orders(clear_existing=True)
        demand = LineDemand.objects.get(routing_step=child_step)
        self.assertEqual(demand.plan_date, due - timedelta(days=3))
        self.assertEqual(demand.firm_qty, Decimal('5'))
        child_step.refresh_from_db()
        self.assertEqual(child_step.remark, 'FG-OLD')
