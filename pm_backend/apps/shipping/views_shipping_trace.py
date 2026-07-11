from collections import defaultdict

from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from masters.models import Calendar
from orders.core.models import KubotaSakaiDueAdjustment, ShippingTripAllocation
from orders.utils.calendar_utils import WorkingDayCalculator
from shipping.models import ShipmentActual
from shipping.serializers import ShipmentActualSerializer
from shipping.views_shipping_trip_execution import _collect_truck_offset_map, _trip_actual_departure_date


class ShippingActualTraceView(APIView):
    """便割付と出荷実績を突合して追跡一覧を返す。"""

    def get(self, request):
        params = request.query_params
        product_code = str(params.get('product_code') or '').strip()
        ship_to_code = str(params.get('ship_to_code') or '').strip()
        source_order_no = str(params.get('source_order_no') or '').strip()
        trip_keyword = str(params.get('trip_keyword') or '').strip()
        departure_date_gte = params.get('departure_date__gte')
        departure_date_lte = params.get('departure_date__lte')
        shipment_date_gte = params.get('shipment_date__gte')
        shipment_date_lte = params.get('shipment_date__lte')
        calc = WorkingDayCalculator(Calendar.objects.first())
        truck_offset_map = _collect_truck_offset_map()

        allocation_qs = (
            ShippingTripAllocation.objects
            .select_related('trip')
            .filter(trip__isnull=False)
            .order_by('-trip__departure_date', 'trip__trip_code', 'id')
        )
        if product_code:
            allocation_qs = allocation_qs.filter(product_code__icontains=product_code)
        if ship_to_code:
            allocation_qs = allocation_qs.filter(ship_to_code__icontains=ship_to_code)
        if trip_keyword:
            allocation_qs = allocation_qs.filter(
                Q(trip__trip_code__icontains=trip_keyword) |
                Q(trip__trip_ref__icontains=trip_keyword)
            )
        if departure_date_gte:
            allocation_qs = allocation_qs.filter(trip__departure_date__gte=departure_date_gte)
        if departure_date_lte:
            allocation_qs = allocation_qs.filter(trip__departure_date__lte=departure_date_lte)

        allocation_rows = list(allocation_qs)
        due_ids = [
            row.source_id
            for row in allocation_rows
            if str(row.source_type or '').strip() == 'KUBOTA_SAKAI_DUE' and row.source_id
        ]
        due_map = {
            row['id']: row
            for row in KubotaSakaiDueAdjustment.objects.filter(id__in=due_ids).values(
                'id', 'source_order_no', 'ship_to_code', 'due_date', 'order_line__due_date'
            )
        }

        if source_order_no:
            allocation_rows = [
                row for row in allocation_rows
                if source_order_no.lower() in str((due_map.get(row.source_id) or {}).get('source_order_no') or '').lower()
            ]

        allocation_ids = [row.id for row in allocation_rows]
        actual_qs = (
            ShipmentActual.objects
            .select_related('product', 'customer', 'shipping_trip_allocation__trip')
            .prefetch_related('splits')
            .filter(shipping_trip_allocation_id__in=allocation_ids)
            .order_by('-shipment_date', '-id')
        )
        if shipment_date_gte:
            actual_qs = actual_qs.filter(shipment_date__gte=shipment_date_gte)
        if shipment_date_lte:
            actual_qs = actual_qs.filter(shipment_date__lte=shipment_date_lte)

        actual_rows = list(actual_qs)
        actual_by_allocation = {}
        for actual in actual_rows:
            allocation_id = actual.shipping_trip_allocation_id
            if allocation_id and allocation_id not in actual_by_allocation:
                actual_by_allocation[allocation_id] = actual

        serializer = ShipmentActualSerializer(actual_rows, many=True, context={'request': request})
        serialized_actual_map = {
            row['shipping_trip_allocation']: row
            for row in serializer.data
            if row.get('shipping_trip_allocation')
        }

        results = []
        for allocation in allocation_rows:
            actual = actual_by_allocation.get(allocation.id)
            serialized_actual = serialized_actual_map.get(allocation.id)
            due = due_map.get(allocation.source_id) if str(allocation.source_type or '').strip() == 'KUBOTA_SAKAI_DUE' else None
            source_no = str((due or {}).get('source_order_no') or '').strip()
            original_due_date = (due or {}).get('order_line__due_date') or (due or {}).get('due_date') or allocation.due_date
            original_due_date_str = original_due_date.isoformat() if original_due_date else None
            if actual and not serialized_actual:
                continue

            actual_departure_date = _trip_actual_departure_date(allocation.trip, calc, truck_offset_map)
            actual_departure_date_str = actual_departure_date.isoformat() if actual_departure_date else None

            if actual:
                row = dict(serialized_actual)
                row['source_order_nos'] = row.get('source_order_nos') or ([source_no] if source_no else [])
                row['departure_date'] = actual_departure_date_str
                row['original_due_date'] = original_due_date_str
            else:
                trip = allocation.trip
                trip_code = (trip.trip_code or '').strip() or (trip.trip_ref or '').strip()
                row = {
                    'id': f'alloc-{allocation.id}',
                    'shipment_date': None,
                    'shipping_trip_allocation': allocation.id,
                    'product': None,
                    'product_code': allocation.product_code,
                    'product_name': None,
                    'customer': None,
                    'customer_code': trip.customer_code,
                    'customer_name': None,
                    'ship_to_code': allocation.ship_to_code or trip.ship_to_code or '',
                    'quantity': str(allocation.qty),
                    'remark': '',
                    'production_splits': [],
                    'trip_id': trip.id,
                    'trip_code': trip_code,
                    'trip_ref': trip.trip_ref,
                    'business_type': trip.business_type,
                    'departure_date': actual_departure_date_str,
                    'original_due_date': original_due_date_str,
                    'departure_time_plan': trip.departure_time_plan.strftime('%H:%M') if trip.departure_time_plan else None,
                    'departure_time_actual': trip.departure_time_actual.strftime('%Y-%m-%d %H:%M') if trip.departure_time_actual else None,
                    'source_order_nos': [source_no] if source_no else [],
                    'created_at': None,
                    'updated_at': None,
                }
            results.append(row)

        def sort_key(item):
            return (
                item.get('shipment_date') or '9999-12-31',
                item.get('departure_date') or '9999-12-31',
                item.get('trip_code') or '',
                item.get('product_code') or '',
                item.get('ship_to_code') or '',
            )

        results.sort(key=sort_key)
        results.reverse()
        return Response(results)
