from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from shipping.models import ShipmentActual, ShipmentActualHistory, ShippingProgress
from shipping.services.shipping_progress import get_progress_horizon_days, recalculate_shipping_progress


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except ValueError:
        return None


def _trip_status_label(status_value):
    mapping = {
        'PLANNED': '計画',
        'LOADING': '積込中',
        'DEPARTED': '出発済',
        'CLOSED': '完了',
    }
    return mapping.get(str(status_value or '').strip().upper(), str(status_value or ''))


class ShippingProgressHorizonSettingView(APIView):
    """出荷進度再計算日数の設定API。"""

    def get(self, request):
        days = get_progress_horizon_days()
        return Response({'horizon_days': days})

    def post(self, request):
        try:
            days = int(request.data.get('horizon_days', 0))
        except (ValueError, TypeError):
            return Response({'detail': 'horizon_days は整数で指定してください。'}, status=status.HTTP_400_BAD_REQUEST)
        if days < 1:
            return Response({'detail': 'horizon_days は1以上にしてください。'}, status=status.HTTP_400_BAD_REQUEST)

        from system_settings.models import SystemSetting
        obj, created = SystemSetting.objects.get_or_create(
            key='shipping.progress_horizon_days',
            defaults={'value': str(days), 'description': '出荷進度の再計算先日数（変更があった日から何日先まで進度を再計算するか）'},
        )
        if not created:
            obj.value = str(days)
            obj.save(update_fields=['value'])

        return Response({'horizon_days': days})


class ShippingProgressView(APIView):
    """出荷進度照会API。"""

    def get(self, request):
        start_date = _parse_date(request.query_params.get('start_date'))
        end_date = _parse_date(request.query_params.get('end_date'))
        if not start_date or not end_date:
            return Response(
                {'detail': 'start_date と end_date は必須です。'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product_code = (request.query_params.get('product_code') or '').strip()
        customer_code = (request.query_params.get('customer_code') or '').strip()
        ship_to_code = (request.query_params.get('ship_to_code') or '').strip()

        qs = ShippingProgress.objects.filter(plan_date__range=(start_date, end_date))
        if product_code:
            qs = qs.filter(product_code__icontains=product_code)
        if customer_code:
            qs = qs.filter(customer_code__icontains=customer_code)
        if ship_to_code:
            qs = qs.filter(ship_to_code__icontains=ship_to_code)

        rows = list(qs.order_by('product_code', 'customer_code', 'ship_to_code', 'plan_date'))

        data = []
        for row in rows:
            data.append({
                'id': row.id,
                'plan_date': row.plan_date.isoformat(),
                'product_code': row.product_code,
                'customer_code': row.customer_code or '',
                'ship_to_code': row.ship_to_code or '',
                'forecast_qty': row.forecast_qty,
                'firm_qty': row.firm_qty,
                'actual_qty': row.actual_qty,
                'adjust_qty': row.adjust_qty,
                'progress_qty': row.progress_qty,
            })

        return Response({'results': data})

    def post(self, request):
        """進度再計算をトリガーする。"""
        start_date = _parse_date(request.data.get('start_date'))
        end_date = _parse_date(request.data.get('end_date'))
        if not start_date or not end_date:
            return Response(
                {'detail': 'start_date と end_date は必須です。'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recalculate_shipping_progress(start_date, end_date)
        return Response({'detail': '進度を再計算しました。'})


class ShippingProgressAdjustView(APIView):
    """進度調整API。adjust_qty を更新して進度を再計算する。"""

    def post(self, request):
        items = request.data.get('items')
        if not isinstance(items, list) or not items:
            return Response(
                {'detail': 'items は配列で指定してください。'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated = 0
        min_date = None
        max_date = None
        for item in items:
            row_id = item.get('id')
            adjust_qty = item.get('adjust_qty')
            if not row_id or adjust_qty is None:
                continue
            try:
                adjust_val = int(adjust_qty)
            except (ValueError, TypeError):
                continue

            try:
                row = ShippingProgress.objects.get(id=row_id)
            except ShippingProgress.DoesNotExist:
                continue

            if row.adjust_qty != adjust_val:
                row.adjust_qty = adjust_val
                row.save(update_fields=['adjust_qty', 'updated_at'])
                updated += 1
                if min_date is None or row.plan_date < min_date:
                    min_date = row.plan_date
                if max_date is None or row.plan_date > max_date:
                    max_date = row.plan_date

        if min_date and max_date:
            calc_end = max_date + timedelta(days=get_progress_horizon_days())
            recalculate_shipping_progress(min_date, calc_end)

        return Response({'detail': f'調整値を{updated}件更新しました。', 'updated': updated})


class ShippingActualEditView(APIView):
    """実績変更API。ShipmentActual の数量を変更して進度を再計算する。"""

    def get(self, request):
        start_date = _parse_date(request.query_params.get('start_date'))
        end_date = _parse_date(request.query_params.get('end_date'))
        if not start_date or not end_date:
            return Response(
                {'detail': 'start_date と end_date は必須です。'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product_code = (request.query_params.get('product_code') or '').strip()
        customer_code = (request.query_params.get('customer_code') or '').strip()
        ship_to_code = (request.query_params.get('ship_to_code') or '').strip()

        qs = ShipmentActual.objects.filter(shipment_date__range=(start_date, end_date))
        if product_code:
            qs = qs.filter(product_code__icontains=product_code)
        if customer_code:
            qs = qs.filter(customer_code__icontains=customer_code)
        if ship_to_code:
            qs = qs.filter(ship_to_code__icontains=ship_to_code)

        qs = qs.select_related('shipping_trip_allocation__trip')
        rows = list(qs.order_by('shipment_date', 'product_code', 'customer_code', 'id'))

        data = []
        for row in rows:
            trip = getattr(getattr(row, 'shipping_trip_allocation', None), 'trip', None)
            is_locked = bool(trip and trip.status in ('DEPARTED', 'CLOSED'))
            trip_code = ''
            trip_status = ''
            if trip:
                trip_code = (trip.trip_code or '').strip() or (trip.trip_ref or '')
                trip_status = _trip_status_label(trip.status)
            data.append({
                'id': row.id,
                'shipment_date': row.shipment_date.isoformat(),
                'product_code': row.product_code,
                'customer_code': row.customer_code or '',
                'ship_to_code': (row.ship_to_code or '').strip(),
                'quantity': int(row.quantity),
                'trip_code': trip_code,
                'trip_status': trip_status,
                'business_type': getattr(trip, 'business_type', '') if trip else '',
                'is_locked': is_locked,
                'lock_reason': '出発済/完了の便実績はここでは変更できません。' if is_locked else '',
            })

        return Response({'results': data})

    def post(self, request):
        items = request.data.get('items')
        if not isinstance(items, list) or not items:
            return Response(
                {'detail': 'items は配列で指定してください。'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated = 0
        min_date = None
        max_date = None
        for item in items:
            row_id = item.get('id')
            new_qty = item.get('quantity')
            if not row_id or new_qty is None:
                continue
            try:
                new_qty_val = Decimal(str(new_qty))
            except (InvalidOperation, ValueError, TypeError):
                continue

            try:
                actual = ShipmentActual.objects.select_related('shipping_trip_allocation__trip').get(id=row_id)
            except ShipmentActual.DoesNotExist:
                continue

            trip = getattr(getattr(actual, 'shipping_trip_allocation', None), 'trip', None)
            if trip and trip.status in ('DEPARTED', 'CLOSED'):
                return Response(
                    {'detail': f'便実績は実績変更画面から更新できません。対象ID: {actual.id}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if actual.quantity != new_qty_val:
                ShipmentActualHistory.objects.create(
                    shipment_actual=actual,
                    action='UPDATE',
                    shipment_date=actual.shipment_date,
                    product_code=actual.product_code,
                    customer_code=actual.customer_code,
                    ship_to_code=actual.ship_to_code,
                    quantity=actual.quantity,
                    remark=actual.remark,
                )
                actual.quantity = new_qty_val
                actual.save(update_fields=['quantity', 'updated_at'])
                updated += 1
                if min_date is None or actual.shipment_date < min_date:
                    min_date = actual.shipment_date
                if max_date is None or actual.shipment_date > max_date:
                    max_date = actual.shipment_date

        if min_date and max_date:
            calc_end = max_date + timedelta(days=get_progress_horizon_days())
            recalculate_shipping_progress(min_date, calc_end)

        return Response({'detail': f'実績を{updated}件更新しました。', 'updated': updated})
