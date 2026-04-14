from decimal import Decimal


def _to_decimal(value, default='0'):
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def calculate_truck_load(assignments, truck):
    """
    assignments: [
      {
        'product_code': str,
        'qty': Decimal|int|float,
        'unit_weight': Decimal|None,  # kg/個
        'container': {
          'width': int|None, 'depth': int|None, 'height': int|None,
          'capacity': int|None, 'can_mix': bool|None, 'stackable': bool|None, 'max_stack': int|None
        }
      }, ...
    ]
    """
    truck_floor = _to_decimal(truck.width) * _to_decimal(truck.depth)
    truck_max_weight = _to_decimal(truck.max_weight)
    if truck_floor <= 0:
        return {
            'occupancy_ratio': Decimal('0'),
            'occupancy_percent': Decimal('0'),
            'total_weight': Decimal('0'),
            'mixed_blocked': False,
            'errors': ['便マスタの荷台サイズが不正です。'],
        }

    total_area = Decimal('0')
    total_weight = Decimal('0')
    non_mix_products = set()
    all_products = set()

    for item in assignments:
        qty = _to_decimal(item.get('qty'))
        if qty <= 0:
            continue

        product_code = str(item.get('product_code') or '')
        if product_code:
            all_products.add(product_code)

        unit_weight = _to_decimal(item.get('unit_weight'))
        total_weight += qty * unit_weight

        container = item.get('container') or {}
        width = _to_decimal(container.get('width'))
        depth = _to_decimal(container.get('depth'))
        height = _to_decimal(container.get('height'))
        capacity = _to_decimal(container.get('capacity'), default='1')
        if capacity <= 0:
            capacity = Decimal('1')

        can_mix = bool(container.get('can_mix', True))
        stackable = bool(container.get('stackable', True))
        max_stack = int(container.get('max_stack') or 999)

        if not can_mix and product_code:
            non_mix_products.add(product_code)

        if width <= 0 or depth <= 0:
            continue

        container_floor = width * depth
        container_count = qty / capacity

        layers = Decimal('1')
        if stackable and height > 0:
            truck_layers = int(_to_decimal(truck.height) // height)
            if truck_layers > 0:
                layers = Decimal(str(min(truck_layers, max_stack if max_stack > 0 else truck_layers)))

        effective_floor = container_floor / (layers if layers > 0 else Decimal('1'))
        total_area += effective_floor * container_count

    occupancy_ratio = total_area / truck_floor if truck_floor > 0 else Decimal('0')
    occupancy_percent = (occupancy_ratio * Decimal('100')).quantize(Decimal('0.1'))

    errors = []
    if occupancy_ratio > Decimal('1'):
        errors.append('占有率が100%を超えています。')
    if truck_max_weight > 0 and total_weight > truck_max_weight:
        errors.append('積載重量が最大積載重量を超えています。')

    mixed_blocked = bool(non_mix_products) and len(all_products) > 1
    if mixed_blocked:
        errors.append('混載不可容器を含むため、同一便に複数品番を割り付けできません。')

    return {
        'occupancy_ratio': occupancy_ratio,
        'occupancy_percent': occupancy_percent,
        'total_weight': total_weight,
        'mixed_blocked': mixed_blocked,
        'errors': errors,
    }
