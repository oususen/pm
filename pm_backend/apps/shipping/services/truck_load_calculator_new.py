from collections import defaultdict
from decimal import Decimal, ROUND_CEILING


def _to_decimal(value, default='0'):
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _pack_slots(bed_len, bed_wid, slots):
    """
    フロアスロットを幾何学的に敷き詰める（表示座標: 長手=横, 幅=縦）。
    - bed_len: 長手方向（横）の最大長 / bed_wid: 幅方向（縦）の最大長
    - 収まらないスロットも配置し（can_fit=False）、見た目で超過を分かるようにする
    returns: (placed, can_fit, max_x, max_y)
    """
    placed = []
    row_x = Decimal('0')
    row_y = Decimal('0')
    row_h = Decimal('0')
    can_fit = True
    max_x = Decimal('0')
    max_y = Decimal('0')
    for slot in slots:
        length = _to_decimal(slot.get('length'))
        width = _to_decimal(slot.get('width'))
        # 長手方向が溢れたら次レーンへ
        if row_x + length > bed_len:
            row_x = Decimal('0')
            row_y += row_h
            row_h = Decimal('0')
        # 幅方向が溢れる場合は超過扱い（配置は続行）
        if row_y + width > bed_wid:
            can_fit = False
        placed.append({
            'product_code': slot.get('product_code', ''),
            'qty': str(slot.get('qty', Decimal('0'))),
            'container_name': slot.get('container_name', ''),
            'layers': slot.get('layers', 1),
            'x': str(row_x),
            'y': str(row_y),
            'w': str(length),
            'd': str(width),
            'rotated': bool(slot.get('rotated', False)),
        })
        row_x += length
        row_h = max(row_h, width)
        max_x = max(max_x, row_x)
        max_y = max(max_y, row_y + width)
    return placed, can_fit, max_x, max_y


def _calc_remaining(bed_len, bed_wid, base_slots, type_records):
    """
    現在の積載(base_slots)に加えて、各容器をあと何箱置けるかを幾何学的に判定する。
    """
    result = {}
    for record in type_records:
        label = record['label']
        extra = 0
        while extra < 500:
            test_slots = list(base_slots)
            for _ in range(extra + 1):
                test_slots.append({
                    'product_code': '',
                    'qty': Decimal('0'),
                    'length': record['length'],
                    'width': record['width'],
                    'rotated': record['rotated'],
                })
            _, fits, _, _ = _pack_slots(bed_len, bed_wid, test_slots)
            if fits:
                extra += 1
            else:
                break
        if extra > 0:
            result[label] = max(result.get(label, 0), extra)
    return [{'label': key, 'count': value} for key, value in result.items()]


def calculate_truck_load(assignments, truck):
    """
    幾何学的パッキングによる積載判定（新ロジック）。
    - 段積みは1フットプリントにまとめ、回転で多く積める向きを採用
    - 実際に荷台へ収まるか(can_fit)を判定し、収まらなければ warnings に「積載超過」を出す
    - errors: 保存ブロック対象（荷台不正・重量超過・混載不可）
    - warnings: 警告のみ（積載超過）
    assignments: [
      {
        'product_code': str,
        'qty': Decimal|int|float,
        'unit_weight': Decimal|None,  # kg/個
        'container': {
          'width': int|None, 'depth': int|None, 'height': int|None,
          'capacity': int|None, 'can_mix': bool|None, 'stackable': bool|None, 'max_stack': int|None,
          'name': str|None
        }
      }, ...
    ]
    """
    bed_width = _to_decimal(truck.width)  # 荷台幅 → 表示上の縦（短手）
    bed_depth = _to_decimal(truck.depth)  # 荷台奥行 → 表示上の横（長手）
    bed_height = _to_decimal(truck.height)
    truck_max_weight = _to_decimal(truck.max_weight)

    errors = []
    if bed_width <= 0 or bed_depth <= 0:
        errors.append('便マスタの荷台サイズが不正です。')
        return {
            'can_fit': False,
            'occupancy_percent': Decimal('0'),
            'total_weight': Decimal('0'),
            'placed': [],
            'remaining': [],
            'errors': errors,
            'warnings': [],
        }

    total_weight = Decimal('0')
    non_mix_products = set()
    all_products = set()
    type_records = []
    slots = []

    # 同一製品・同一容器（同一寸法・入数）の割付を合算してから容器数・段数を計算する。
    # 別注番に分かれていても同じ製品・容器なら合算し、段積みで効率よく詰められるようにする。
    group_qty = defaultdict(Decimal)
    group_meta = {}
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
        cw = _to_decimal(container.get('width'))
        cd = _to_decimal(container.get('depth'))
        ch = _to_decimal(container.get('height'))
        capacity = _to_decimal(container.get('capacity'), default='1')
        if capacity <= 0:
            capacity = Decimal('1')
        can_mix = bool(container.get('can_mix', True))
        stackable = bool(container.get('stackable', True))
        max_stack = int(container.get('max_stack') or 999)

        if not can_mix and product_code:
            non_mix_products.add(product_code)
        if cw <= 0 or cd <= 0:
            continue

        key = (
            product_code,
            str(cw), str(cd), str(ch), str(capacity),
            can_mix, stackable, max_stack,
            str(container.get('name') or ''),
        )
        group_qty[key] += qty
        group_meta.setdefault(key, {
            'product_code': product_code,
            'container': container,
            'cw': cw,
            'cd': cd,
            'ch': ch,
            'capacity': capacity,
            'can_mix': can_mix,
            'stackable': stackable,
            'max_stack': max_stack,
        })

    for key, meta in group_meta.items():
        qty = group_qty[key]
        product_code = meta['product_code']
        container = meta['container']
        cw = meta['cw']
        cd = meta['cd']
        ch = meta['ch']
        capacity = meta['capacity']
        stackable = meta['stackable']
        max_stack = meta['max_stack']

        container_count = (qty / capacity).to_integral_value(rounding=ROUND_CEILING)
        # 段数（現在のルール: min(トラック高さ÷容器高さ, 最大段数)）
        layers = Decimal('1')
        if stackable and ch > 0 and bed_height > 0:
            truck_layers = int(bed_height // ch)
            if truck_layers > 0:
                layers = Decimal(str(min(truck_layers, max_stack if max_stack > 0 else truck_layers)))
        floor_slots = container_count
        if layers > 0:
            floor_slots = (container_count / layers).to_integral_value(rounding=ROUND_CEILING)

        # 回転判定（回転で多く積める向きを採用）
        cap_normal = int(bed_depth // cd) * int(bed_width // cw)
        cap_rotated = int(bed_depth // cw) * int(bed_width // cd)
        rotated = cap_rotated > cap_normal
        # 表示座標: 横=長手(奥行), 縦=幅
        length = cd if not rotated else cw  # 長手方向の長さ
        width = cw if not rotated else cd   # 幅方向の長さ
        if length <= 0 or width <= 0:
            continue

        container_name = str(container.get('name') or '') or product_code
        type_records.append({
            'label': container_name,
            'length': length,
            'width': width,
            'rotated': rotated,
        })
        for _ in range(int(floor_slots)):
            slots.append({
                'product_code': product_code,
                'qty': qty,
                'container_name': container_name,
                'layers': int(layers),
                'length': length,
                'width': width,
                'rotated': rotated,
            })

    # パッキング（収まらないものも配置し、can_fit 判定）
    placed, can_fit, _, _ = _pack_slots(bed_depth, bed_width, slots)

    # 占有率（実フットプリント面積ベース。超過時は100%超）
    bed_area = bed_width * bed_depth
    occupied_area = sum(_to_decimal(p['w']) * _to_decimal(p['d']) for p in placed)
    occupancy_ratio = occupied_area / bed_area if bed_area > 0 else Decimal('0')
    occupancy_percent = (occupancy_ratio * Decimal('100')).quantize(Decimal('0.1'))

    warnings = []
    if not can_fit:
        warnings.append('積載超過：実際の配置で荷台に収まりません。')
    if truck_max_weight > 0 and total_weight > truck_max_weight:
        errors.append('積載重量が最大積載重量を超えています。')
    mixed_blocked = bool(non_mix_products) and len(all_products) > 1
    if mixed_blocked:
        errors.append('混載不可容器を含むため、同一便に複数品番を割り付けできません。')

    # 残りスペース（収まる場合のみ、幾何学的に判定）
    remaining = []
    if can_fit:
        remaining = _calc_remaining(bed_depth, bed_width, slots, type_records)

    return {
        'can_fit': can_fit,
        'occupancy_percent': occupancy_percent,
        'total_weight': total_weight,
        'placed': placed,
        'remaining': remaining,
        'errors': errors,
        'warnings': warnings,
    }
