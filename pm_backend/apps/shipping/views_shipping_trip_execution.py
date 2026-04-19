from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from masters.models import Product
from orders.core.models import ShippingTrip, ShippingTripAllocation
from shipping.models import ShipmentActual, ShipmentActualHistory


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except ValueError:
        return None


def _to_decimal(value, default='0'):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _format_qty(value):
    qty = _to_decimal(value)
    return str(qty.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _format_dt(value):
    if not value:
        return None
    try:
        return value.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return str(value)


def _display_user_name(user):
    if not user:
        return ''
    last = str(getattr(user, 'last_name', '') or '').strip()
    first = str(getattr(user, 'first_name', '') or '').strip()
    if last and first:
        return f'{last} {first}'
    if last:
        return last
    if first:
        return first
    full = str(user.get_full_name() or '').strip()
    if full:
        return full
    return str(getattr(user, 'username', '') or '')


def _build_trip_payload(trip, allocations, product_name_map):
    details = []
    total_qty = Decimal('0')
    for item in allocations:
        qty = _to_decimal(item.qty)
        total_qty += qty
        details.append({
            'allocation_id': item.id,
            'product_code': item.product_code,
            'product_name': product_name_map.get(item.product_code, ''),
            'ship_to_code': item.ship_to_code or '',
            'due_date': item.due_date.isoformat() if item.due_date else None,
            'qty': _format_qty(qty),
        })

    details.sort(key=lambda x: (x['product_code'], x['ship_to_code'], x['due_date'] or ''))
    trip_code = (trip.trip_code or '').strip() or (trip.trip_ref or '')
    loading_user = getattr(trip, 'loading_by', None)
    departed_user = getattr(trip, 'departed_by', None)
    return {
        'id': trip.id,
        'business_type': trip.business_type,
        'customer_code': trip.customer_code,
        'ship_to_code': trip.ship_to_code or '',
        'departure_date': trip.departure_date.isoformat(),
        'trip_ref': trip.trip_ref,
        'trip_code': trip_code,
        'departure_time_plan': trip.departure_time_plan.strftime('%H:%M') if trip.departure_time_plan else None,
        'departure_time_actual': _format_dt(trip.departure_time_actual),
        'status': trip.status,
        'loading_by': _display_user_name(loading_user),
        'departed_by': _display_user_name(departed_user),
        'total_qty': _format_qty(total_qty),
        'detail_count': len(details),
        'details': details,
    }


class ShippingTripExecutionView(APIView):
    """便確認（実行）向けAPI。"""

    def get(self, request):
        departure_date = _parse_date(request.query_params.get('departure_date'))
        if not departure_date:
            return Response({'detail': 'departure_date は必須です。'}, status=status.HTTP_400_BAD_REQUEST)

        business_type = (request.query_params.get('business_type') or '').strip()
        base_qs = ShippingTrip.objects.filter(departure_date=departure_date)
        if business_type:
            base_qs = base_qs.filter(business_type=business_type)

        trips = list(
            base_qs
            .select_related('run', 'loading_by', 'departed_by')
            .order_by('business_type', 'departure_time_plan', 'trip_code', 'trip_ref', 'id')
        )
        trip_ids = [t.id for t in trips]
        allocations = list(
            ShippingTripAllocation.objects
            .filter(trip_id__in=trip_ids)
            .order_by('trip_id', 'product_code', 'id')
        )
        product_codes = {a.product_code for a in allocations}
        product_name_map = {
            p.product_code: p.product_name
            for p in Product.objects.filter(product_code__in=product_codes)
        }

        allocations_by_trip = defaultdict(list)
        for item in allocations:
            allocations_by_trip[item.trip_id].append(item)

        trips_payload = [
            _build_trip_payload(trip, allocations_by_trip.get(trip.id, []), product_name_map)
            for trip in trips
        ]

        business_types = list(
            ShippingTrip.objects
            .filter(departure_date=departure_date)
            .values_list('business_type', flat=True)
            .distinct()
            .order_by('business_type')
        )

        status_count = defaultdict(int)
        for trip in trips:
            status_count[trip.status] += 1

        return Response({
            'departure_date': departure_date.isoformat(),
            'business_type': business_type,
            'business_types': business_types,
            'summary': {
                'total': len(trips),
                'planned': status_count.get('PLANNED', 0),
                'loading': status_count.get('LOADING', 0),
                'departed': status_count.get('DEPARTED', 0),
                'closed': status_count.get('CLOSED', 0),
            },
            'trips': trips_payload,
        })

    def post(self, request):
        trip_id = request.data.get('trip_id')
        action = (request.data.get('action') or '').strip()
        if not trip_id:
            return Response({'detail': 'trip_id は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        if action not in ('mark_loading', 'mark_departed', 'reopen', 'register_actual'):
            return Response({'detail': 'action が不正です。'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            trip = ShippingTrip.objects.get(id=trip_id)
        except ShippingTrip.DoesNotExist:
            return Response({'detail': '対象便が見つかりません。'}, status=status.HTTP_404_NOT_FOUND)

        if action == 'mark_loading':
            if trip.status in ('DEPARTED', 'CLOSED'):
                return Response({'detail': '出発済/完了の便は積込完了に戻せません。'}, status=status.HTTP_400_BAD_REQUEST)
            trip.status = 'LOADING'
            if getattr(request.user, 'is_authenticated', False):
                trip.loading_by = request.user
            trip.save()
        elif action == 'mark_departed':
            if trip.status == 'CLOSED':
                return Response({'detail': '完了便は出発更新できません。'}, status=status.HTTP_400_BAD_REQUEST)
            trip.status = 'DEPARTED'
            if not trip.departure_time_actual:
                trip.departure_time_actual = datetime.now()
            if getattr(request.user, 'is_authenticated', False):
                trip.departed_by = request.user
                if not trip.loading_by:
                    trip.loading_by = request.user
            trip.save()
        elif action == 'reopen':
            trip.status = 'PLANNED'
            trip.departure_time_actual = None
            trip.loading_by = None
            trip.departed_by = None
            trip.save()
        elif action == 'register_actual':
            if trip.status != 'DEPARTED':
                return Response(
                    {'detail': '出発済の便のみ実績登録できます。'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            shipment_date = _parse_date(request.data.get('shipment_date')) or trip.departure_date
            raw_actuals = request.data.get('actuals') or []
            if not isinstance(raw_actuals, list):
                return Response({'detail': 'actuals は配列で指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

            allocations = list(
                ShippingTripAllocation.objects.filter(trip_id=trip.id).order_by('id')
            )
            allocation_map = {a.id: a for a in allocations}

            normalized = {}
            for item in raw_actuals:
                try:
                    allocation_id = int(item.get('allocation_id') or 0)
                except Exception:
                    allocation_id = 0
                qty = _to_decimal(item.get('quantity'))
                if allocation_id <= 0 or allocation_id not in allocation_map:
                    continue
                normalized[allocation_id] = qty

            created_count = 0
            updated_count = 0
            deleted_count = 0
            for allocation in allocations:
                qty = normalized.get(allocation.id, Decimal('0'))
                marker = f'[TRIP_ACTUAL]{trip.id}:{allocation.id}'
                existing = ShipmentActual.objects.filter(remark=marker).order_by('-id').first()
                if qty <= 0:
                    if existing:
                        ShipmentActualHistory.objects.create(
                            shipment_actual=existing,
                            action='DELETE',
                            shipment_date=existing.shipment_date,
                            product_code=existing.product_code,
                            customer_code=existing.customer_code,
                            ship_to_code=existing.ship_to_code,
                            quantity=existing.quantity,
                            remark=existing.remark,
                        )
                        existing.delete()
                        deleted_count += 1
                    continue

                if existing:
                    ShipmentActualHistory.objects.create(
                        shipment_actual=existing,
                        action='UPDATE',
                        shipment_date=existing.shipment_date,
                        product_code=existing.product_code,
                        customer_code=existing.customer_code,
                        ship_to_code=existing.ship_to_code,
                        quantity=existing.quantity,
                        remark=existing.remark,
                    )
                    existing.shipment_date = shipment_date
                    existing.product_code = allocation.product_code
                    existing.customer_code = trip.customer_code
                    existing.ship_to_code = allocation.ship_to_code or trip.ship_to_code
                    existing.quantity = qty
                    existing.save()
                    updated_count += 1
                else:
                    created = ShipmentActual.objects.create(
                        shipment_date=shipment_date,
                        product_code=allocation.product_code,
                        customer_code=trip.customer_code,
                        ship_to_code=allocation.ship_to_code or trip.ship_to_code,
                        quantity=qty,
                        remark=marker,
                    )
                    ShipmentActualHistory.objects.create(
                        shipment_actual=created,
                        action='CREATE',
                        shipment_date=created.shipment_date,
                        product_code=created.product_code,
                        customer_code=created.customer_code,
                        ship_to_code=created.ship_to_code,
                        quantity=created.quantity,
                        remark=created.remark,
                    )
                    created_count += 1

            # 実績登録完了と同時に便を完了状態へ進める。
            if trip.status != 'CLOSED':
                trip.status = 'CLOSED'
                trip.save(update_fields=['status'])

            return Response({
                'detail': '出荷実績を登録しました。',
                'created': created_count,
                'updated': updated_count,
                'deleted': deleted_count,
            })

        allocations = list(
            ShippingTripAllocation.objects
            .filter(trip_id=trip.id)
            .order_by('product_code', 'id')
        )
        product_codes = {a.product_code for a in allocations}
        product_name_map = {
            p.product_code: p.product_name
            for p in Product.objects.filter(product_code__in=product_codes)
        }
        return Response({
            'trip': _build_trip_payload(trip, allocations, product_name_map),
        })


class ShippingTripProgressView(APIView):
    """便進捗確認向けAPI。"""

    def get(self, request):
        date_from = _parse_date(request.query_params.get('date_from'))
        date_to = _parse_date(request.query_params.get('date_to'))
        if not date_from or not date_to:
            return Response({'detail': 'date_from と date_to は必須です。'}, status=status.HTTP_400_BAD_REQUEST)
        if date_from > date_to:
            return Response({'detail': 'date_from は date_to 以前を指定してください。'}, status=status.HTTP_400_BAD_REQUEST)

        business_type = (request.query_params.get('business_type') or '').strip()
        status_filter = (request.query_params.get('status') or '').strip().upper()

        qs = ShippingTrip.objects.filter(departure_date__gte=date_from, departure_date__lte=date_to)
        if business_type:
            qs = qs.filter(business_type=business_type)
        if status_filter in ('PLANNED', 'LOADING', 'DEPARTED', 'CLOSED'):
            qs = qs.filter(status=status_filter)
        trips = list(
            qs.select_related('run__created_by', 'loading_by', 'departed_by')
            .order_by('departure_date', 'business_type', 'departure_time_plan', 'trip_code', 'trip_ref', 'id')
        )

        daily = defaultdict(lambda: {'total': 0, 'planned': 0, 'loading': 0, 'departed': 0, 'closed': 0})
        for trip in trips:
            key = trip.departure_date.isoformat()
            daily[key]['total'] += 1
            if trip.status == 'PLANNED':
                daily[key]['planned'] += 1
            elif trip.status == 'LOADING':
                daily[key]['loading'] += 1
            elif trip.status == 'DEPARTED':
                daily[key]['departed'] += 1
            elif trip.status == 'CLOSED':
                daily[key]['closed'] += 1

        business_types = list(
            ShippingTrip.objects
            .filter(departure_date__gte=date_from, departure_date__lte=date_to)
            .values_list('business_type', flat=True)
            .distinct()
            .order_by('business_type')
        )

        trip_rows = []
        for trip in trips:
            loading_user = getattr(trip, 'loading_by', None)
            departed_user = getattr(trip, 'departed_by', None)
            created_user = getattr(getattr(trip, 'run', None), 'created_by', None)
            if trip.status == 'PLANNED':
                shipping_staff = ''
            elif trip.status == 'LOADING' and loading_user:
                shipping_staff = _display_user_name(loading_user)
            elif trip.status == 'DEPARTED' and departed_user:
                shipping_staff = _display_user_name(departed_user)
            elif created_user:
                shipping_staff = _display_user_name(created_user)
            else:
                shipping_staff = ''
            trip_rows.append({
                'id': trip.id,
                'departure_date': trip.departure_date.isoformat(),
                'business_type': trip.business_type,
                'trip_code': (trip.trip_code or '').strip() or (trip.trip_ref or ''),
                'ship_to_code': trip.ship_to_code or '',
                'status': trip.status,
                'departure_time_plan': trip.departure_time_plan.strftime('%H:%M') if trip.departure_time_plan else None,
                'departure_time_actual': _format_dt(trip.departure_time_actual),
                'shipping_staff': shipping_staff,
            })

        return Response({
            'date_from': date_from.isoformat(),
            'date_to': date_to.isoformat(),
            'business_type': business_type,
            'status': status_filter,
            'business_types': business_types,
            'daily_summary': [
                {'date': day, **summary}
                for day, summary in sorted(daily.items(), key=lambda x: x[0])
            ],
            'trips': trip_rows,
        })
