from datetime import date
from decimal import Decimal
from math import ceil

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from masters.models import Line, Product, SupplierTruck
from production.models_line_backlog import LineBacklog
from .truck_load_calculator import calculate_truck_load

from .models import (
    PurchaseAutoOrderSendConfig,
    PurchaseOrderProposal,
    PurchaseOrderProposalLine,
)


def _build_truck_load_assignment(product, qty_value):
    """製品とそのコンテナ情報からトラック積載判定用のassignmentを構築する"""
    container = getattr(product, 'used_container', None)
    if not container:
        return None, 'container not configured'

    parent = getattr(container, 'parent_container', None)
    parent_dict = None
    if parent:
        parent_dict = {
            'id': parent.id,
            'container_code': getattr(parent, 'container_code', None),
            'width': getattr(parent, 'width', None),
            'depth': getattr(parent, 'depth', None),
            'height': getattr(parent, 'height', None),
            'capacity': getattr(container, 'parent_capacity', None),
            'can_mix': getattr(parent, 'can_mix', True),
            'stackable': getattr(parent, 'stackable', True),
            'max_stack': getattr(parent, 'max_stack', None),
            'name': getattr(parent, 'name', None),
            'orientation': getattr(parent, 'orientation', None),
        }
    return {
        'product_code': product.product_code,
        'qty': qty_value,
        'unit_weight': Decimal('0'),
        'container': {
            'id': container.id,
            'container_code': getattr(container, 'container_code', None),
            'width': getattr(container, 'width', None),
            'depth': getattr(container, 'depth', None),
            'height': getattr(container, 'height', None),
            'capacity': getattr(product, 'capacity', None) or getattr(container, 'capacity', None),
            'can_mix': getattr(container, 'can_mix', True),
            'stackable': getattr(container, 'stackable', True),
            'max_stack': getattr(container, 'max_stack', None),
            'name': getattr(container, 'name', None),
            'orientation': getattr(container, 'orientation', None),
            'parent': parent_dict,
        },
    }, None


def _fetch_items_from_proposals(supplier, delivery_date):
    """注文書（PurchaseOrderProposal）から品目を取得"""
    proposal_ids = list(
        PurchaseOrderProposal.objects
        .filter(supplier=supplier, desired_delivery_date=delivery_date)
        .exclude(status=PurchaseOrderProposal.STATUS_CANCELED)
        .values_list('id', flat=True)
    )
    if not proposal_ids:
        return {}

    lines = (
        PurchaseOrderProposalLine.objects
        .filter(proposal_id__in=proposal_ids, order_qty__gt=0)
        .select_related('product__used_container__parent_container')
    )
    product_qty_map = {}
    for line in lines:
        pid = line.product_id
        if pid in product_qty_map:
            product_qty_map[pid]['qty'] += line.order_qty
        else:
            product_qty_map[pid] = {
                'product': line.product,
                'qty': line.order_qty,
            }
    return product_qty_map


def _fetch_items_from_backlog(supplier, delivery_date):
    """購買計画（LineBacklog seq=1）から品目を取得"""
    line = (
        Line.objects.filter(line_code=supplier.supplier_code).first()
        or Line.objects.filter(line_name__icontains=str(supplier.supplier_name or '').strip()).first()
    )
    if not line:
        return {}

    backlogs = (
        LineBacklog.objects
        .filter(
            line=line,
            plan_date=delivery_date,
            sequence_no=1,
            plan_qty__gt=0,
        )
        .select_related('product__used_container__parent_container')
        .order_by('product__product_code')
    )
    product_qty_map = {}
    for b in backlogs:
        if not b.product:
            continue
        pid = b.product_id
        if pid in product_qty_map:
            product_qty_map[pid]['qty'] += int(b.plan_qty or 0)
        else:
            product_qty_map[pid] = {
                'product': b.product,
                'qty': int(b.plan_qty or 0),
            }
    return product_qty_map


class PurchaseAutoOrderSendTruckLoadCheckView(APIView):
    """トラック積載判定: 指定トラックに指定日の納入品目が積載できるか判定する"""

    def post(self, request, pk=None):
        config_id = None
        if pk is not None:
            config = PurchaseAutoOrderSendConfig.objects.filter(pk=pk).first()
            if not config:
                return Response({'detail': 'not found'}, status=status.HTTP_404_NOT_FOUND)
            config_id = config.id

        truck_id = request.data.get('truck_id')
        if not truck_id:
            return Response({'detail': 'truck_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        truck = SupplierTruck.objects.select_related('supplier').filter(pk=truck_id).first()
        if not truck:
            return Response({'detail': 'truck not found'}, status=status.HTTP_404_NOT_FOUND)

        delivery_date_str = (request.data.get('delivery_date') or '').strip()
        items = request.data.get('items')

        assignments = []
        invalid_items = []
        fetched_items = []
        data_source = None

        if delivery_date_str:
            try:
                delivery_date = date.fromisoformat(delivery_date_str)
            except ValueError:
                return Response({'detail': 'delivery_date must be YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

            # 1. 注文書から取得を試みる
            product_qty_map = _fetch_items_from_proposals(truck.supplier, delivery_date)
            if product_qty_map:
                data_source = 'proposal'
            else:
                # 2. 購買計画（LineBacklog）からフォールバック
                product_qty_map = _fetch_items_from_backlog(truck.supplier, delivery_date)
                if product_qty_map:
                    data_source = 'backlog'

            invalid_codes = set()
            for pid, info in product_qty_map.items():
                product = info['product']
                assignment, reason = _build_truck_load_assignment(product, info['qty'])
                if assignment:
                    assignments.append(assignment)
                else:
                    invalid_items.append({'product_code': product.product_code, 'reason': reason})
                    invalid_codes.add(product.product_code)

            for pid, info in product_qty_map.items():
                product = info['product']
                container = getattr(product, 'used_container', None)
                container_name = ''
                container_count = 0
                parent_name = ''
                if container:
                    container_name = container.name or ''
                    cap = getattr(product, 'capacity', None) or getattr(container, 'capacity', None) or 1
                    if cap and cap > 0:
                        container_count = ceil(info['qty'] / cap)
                    parent = getattr(container, 'parent_container', None)
                    if parent:
                        parent_name = parent.name or ''
                fetched_items.append({
                    'product_code': product.product_code,
                    'product_name': product.product_name,
                    'order_qty': info['qty'],
                    'has_container': product.product_code not in invalid_codes,
                    'container_name': container_name,
                    'container_count': container_count,
                    'parent_name': parent_name,
                })
        elif items and isinstance(items, list):
            data_source = 'manual'
            for item in items:
                product_code = str(item.get('product_code') or '').strip()
                qty = item.get('qty')
                if not product_code or qty in (None, ''):
                    continue
                try:
                    qty_value = int(qty)
                except (TypeError, ValueError):
                    invalid_items.append({'product_code': product_code, 'reason': 'qty must be an integer'})
                    continue
                if qty_value <= 0:
                    invalid_items.append({'product_code': product_code, 'reason': 'qty must be greater than 0'})
                    continue

                product = Product.objects.select_related('used_container__parent_container').filter(product_code=product_code).first()
                if not product:
                    invalid_items.append({'product_code': product_code, 'reason': 'product not found'})
                    continue

                assignment, reason = _build_truck_load_assignment(product, qty_value)
                if assignment:
                    assignments.append(assignment)
                else:
                    invalid_items.append({'product_code': product.product_code, 'reason': reason})
        else:
            return Response({'detail': 'delivery_date or items is required'}, status=status.HTTP_400_BAD_REQUEST)

        if invalid_items and not assignments:
            return Response(
                {
                    'detail': '一部の品番に容器設定がありません。',
                    'invalid_items': invalid_items,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not assignments:
            return Response({'detail': '対象品目がありません'}, status=status.HTTP_400_BAD_REQUEST)

        result = calculate_truck_load(assignments, truck)
        placed = result.get('placed', []) or []
        response_data = {
            'truck': {
                'id': truck.id,
                'name': truck.name,
                'alias_name': truck.alias_name,
                'width': truck.width,
                'depth': truck.depth,
                'height': truck.height,
                'max_weight': truck.max_weight,
            },
            'can_fit': result.get('can_fit', False),
            'occupancy_percent': float(result.get('occupancy_percent', 0) or 0),
            'total_weight': float(result.get('total_weight', 0) or 0),
            'errors': result.get('errors', []),
            'warnings': result.get('warnings', []),
            'placed': [
                {
                    'x': float(p.get('x', 0)),
                    'y': float(p.get('y', 0)),
                    'w': float(p.get('w', 0)),
                    'd': float(p.get('d', 0)),
                    'product_code': p.get('product_code', ''),
                    'qty': p.get('qty', 0),
                    'layers': p.get('layers', 1),
                    'rotated': p.get('rotated', False),
                }
                for p in placed
            ],
            'remaining': result.get('remaining', []),
            'invalid_items': invalid_items,
            'total_footprints': result.get('total_footprints', 0),
            'overflow_count': result.get('overflow_count', 0),
        }
        bed_depth = float(truck.depth or 0)
        bed_width = float(truck.width or 0)
        overflow_codes = set()
        for p in placed:
            px = float(p.get('x', 0))
            py = float(p.get('y', 0))
            pw = float(p.get('w', 0))
            pd = float(p.get('d', 0))
            pc = p.get('product_code', '')
            if pc and (px + pw > bed_depth or py + pd > bed_width):
                overflow_codes.add(pc)
        for fi in fetched_items:
            fi['loaded'] = fi['product_code'] not in overflow_codes and fi['has_container']
        if fetched_items:
            response_data['fetched_items'] = fetched_items
        if data_source:
            response_data['data_source'] = data_source
        if config_id is not None:
            response_data['config_id'] = config_id
        return Response(response_data)
