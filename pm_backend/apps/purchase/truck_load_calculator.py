"""
購買自動発注送信 専用の積載計算ロジック。
shipping.services.truck_load_calculator とは独立。

主な違い:
- グルーピングキーから capacity を除外し、同じ物理サイズの容器は
  capacity が異なっても1グループにまとめて段積みする
- コンテナ数は製品別に計算してからグループ内で合算
"""
from collections import defaultdict
from decimal import Decimal, ROUND_CEILING


def _to_decimal(value, default='0'):
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


# ---------------------------------------------------------------------------
# パッカー群（shipping版と同一ロジック）
# ---------------------------------------------------------------------------

def _slot_orientations(slot):
    return [(
        _to_decimal(slot.get('length')),
        _to_decimal(slot.get('width')),
        bool(slot.get('rotated', False)),
    )]


def _pack_shelf(bed_len, bed_wid, slots):
    placed = []
    row_x = Decimal('0')
    row_y = Decimal('0')
    row_h = Decimal('0')
    can_fit = True
    max_x = Decimal('0')
    max_y = Decimal('0')
    for slot in slots:
        len_a = _to_decimal(slot.get('length'))
        wid_a = _to_decimal(slot.get('width'))
        rot_a = bool(slot.get('rotated', False))
        chosen = None
        for (length, width, rotated) in _slot_orientations(slot):
            if row_x + length <= bed_len and row_y + width <= bed_wid:
                chosen = (length, width, rotated, row_x, row_y, False)
                break
            ny = row_y + row_h
            if length <= bed_len and ny + width <= bed_wid:
                chosen = (length, width, rotated, Decimal('0'), ny, True)
                break
        if chosen is None:
            can_fit = False
            length, width, rotated = len_a, wid_a, rot_a
            if row_x + length > bed_len:
                row_x = Decimal('0')
                row_y += row_h
                row_h = Decimal('0')
            x, y, new_lane = row_x, row_y, False
        else:
            length, width, rotated, x, y, new_lane = chosen
        if new_lane:
            row_x = Decimal('0')
            row_y = y
            row_h = Decimal('0')
        placed.append({
            'product_code': slot.get('product_code', ''),
            'qty': str(slot.get('qty', Decimal('0'))),
            'container_name': slot.get('container_name', ''),
            'slot_products': slot.get('slot_products', []),
            'layers': slot.get('layers', 1),
            'x': str(x), 'y': str(y),
            'w': str(length), 'd': str(width),
            'rotated': rotated,
            'lock_rotation': bool(slot.get('lock_rotation', False)),
        })
        row_x = x + length
        row_h = max(row_h, width)
        max_x = max(max_x, row_x)
        max_y = max(max_y, y + width)
    return {'placed': placed, 'can_fit': can_fit, 'max_x': max_x, 'max_y': max_y}


def _pack_guillotine(bed_len, bed_wid, slots):
    placed = []
    free_rects = [(Decimal('0'), Decimal('0'), bed_len, bed_wid)]
    can_fit = True
    max_x = Decimal('0')
    max_y = Decimal('0')
    of_x = Decimal('0')
    of_y = bed_wid
    of_h = Decimal('0')

    for slot in slots:
        len_a = _to_decimal(slot.get('length'))
        wid_a = _to_decimal(slot.get('width'))
        rot_a = bool(slot.get('rotated', False))

        best = None
        for rect_idx, (fx, fy, fw, fh) in enumerate(free_rects):
            for (length, width, rotated) in _slot_orientations(slot):
                if length <= fw and width <= fh:
                    rest_w = fw - length
                    rest_h = fh - width
                    score = min(rest_w, rest_h)
                    score_area = rest_w * rest_h
                    if best is None or score < best[0] or (score == best[0] and score_area < best[1]):
                        best = (score, score_area, rect_idx, fx, fy, length, width, rotated)

        if best is None:
            can_fit = False
            if of_x + len_a > bed_len:
                of_x = Decimal('0')
                of_y += of_h
                of_h = Decimal('0')
            placed.append({
                'product_code': slot.get('product_code', ''),
                'qty': str(slot.get('qty', Decimal('0'))),
                'container_name': slot.get('container_name', ''),
                'slot_products': slot.get('slot_products', []),
                'layers': slot.get('layers', 1),
                'x': str(of_x), 'y': str(of_y),
                'w': str(len_a), 'd': str(wid_a),
                'rotated': rot_a,
                'lock_rotation': bool(slot.get('lock_rotation', False)),
            })
            of_x += len_a
            of_h = max(of_h, wid_a)
            max_x = max(max_x, of_x)
            max_y = max(max_y, of_y + wid_a)
            continue

        _, _, rect_idx, fx, fy, length, width, rotated = best
        fw = free_rects[rect_idx][2]
        fh = free_rects[rect_idx][3]
        fx2 = fx + length
        fy2 = fy + width
        rest_w = fw - length
        rest_h = fh - width
        free_rects.pop(rect_idx)
        if rest_h >= rest_w:
            if rest_h > 0:
                free_rects.append((fx, fy2, length, rest_h))
            if rest_w > 0:
                free_rects.append((fx2, fy, rest_w, fh))
        else:
            if rest_w > 0:
                free_rects.append((fx2, fy, rest_w, width))
            if rest_h > 0:
                free_rects.append((fx, fy2, fw, rest_h))

        placed.append({
            'product_code': slot.get('product_code', ''),
            'qty': str(slot.get('qty', Decimal('0'))),
            'container_name': slot.get('container_name', ''),
            'slot_products': slot.get('slot_products', []),
            'layers': slot.get('layers', 1),
            'x': str(fx), 'y': str(fy),
            'w': str(length), 'd': str(width),
            'rotated': rotated,
            'lock_rotation': bool(slot.get('lock_rotation', False)),
        })
        max_x = max(max_x, fx2)
        max_y = max(max_y, fy2)

    return {'placed': placed, 'can_fit': can_fit, 'max_x': max_x, 'max_y': max_y}


def _pack_bay(bed_len, bed_wid, slots):
    placed = []
    sorted_slots = sorted(
        slots,
        key=lambda s: max(_to_decimal(s.get('length')), _to_decimal(s.get('width'))),
        reverse=True,
    )
    col_x = Decimal('0')
    bay_w = Decimal('0')
    bay_len = Decimal('0')
    can_fit = True
    max_x = Decimal('0')
    max_y = Decimal('0')
    of_x = Decimal('0')
    of_y = bed_wid
    of_h = Decimal('0')

    for slot in sorted_slots:
        len_a = _to_decimal(slot.get('length'))
        wid_a = _to_decimal(slot.get('width'))
        rot_a = bool(slot.get('rotated', False))
        options = _slot_orientations(slot)

        chosen = None
        best_opt = None
        for (length, width, rotated) in options:
            if bay_w + width <= bed_wid:
                if best_opt is None or width > best_opt[1]:
                    best_opt = (length, width, rotated)
        if best_opt is not None:
            chosen = best_opt
        else:
            col_x += bay_len
            bay_w = Decimal('0')
            bay_len = Decimal('0')
            for (length, width, rotated) in options:
                if width <= bed_wid:
                    if chosen is None or width > chosen[1]:
                        chosen = (length, width, rotated)

        if chosen is None:
            can_fit = False
            if of_x + len_a > bed_len:
                of_x = Decimal('0')
                of_y += of_h
                of_h = Decimal('0')
            placed.append({
                'product_code': slot.get('product_code', ''),
                'qty': str(slot.get('qty', Decimal('0'))),
                'container_name': slot.get('container_name', ''),
                'slot_products': slot.get('slot_products', []),
                'layers': slot.get('layers', 1),
                'x': str(of_x), 'y': str(of_y),
                'w': str(len_a), 'd': str(wid_a),
                'rotated': rot_a,
                'lock_rotation': bool(slot.get('lock_rotation', False)),
            })
            of_x += len_a
            of_h = max(of_h, wid_a)
            max_x = max(max_x, of_x)
            max_y = max(max_y, of_y + wid_a)
            continue

        length, width, rotated = chosen
        placed.append({
            'product_code': slot.get('product_code', ''),
            'qty': str(slot.get('qty', Decimal('0'))),
            'container_name': slot.get('container_name', ''),
            'slot_products': slot.get('slot_products', []),
            'layers': slot.get('layers', 1),
            'x': str(col_x), 'y': str(bay_w),
            'w': str(length), 'd': str(width),
            'rotated': rotated,
            'lock_rotation': bool(slot.get('lock_rotation', False)),
        })
        bay_w += width
        bay_len = max(bay_len, length)
        max_x = max(max_x, col_x + length)
        max_y = max(max_y, bay_w)

    total_len = col_x + bay_len
    max_x = max(max_x, total_len)
    if total_len > bed_len:
        can_fit = False
    return {'placed': placed, 'can_fit': can_fit, 'max_x': max_x, 'max_y': max_y}


def _pack_column(bed_len, bed_wid, slots):
    from math import ceil
    placed = []
    can_fit = True
    max_x = Decimal('0')
    max_y = Decimal('0')
    of_x = Decimal('0')
    of_y = bed_wid
    of_h = Decimal('0')

    groups = defaultdict(list)
    for slot in slots:
        name = slot.get('container_name', '') or slot.get('product_code', '')
        groups[name].append(slot)

    group_list = []
    for name, group_slots in groups.items():
        rep = group_slots[0]
        len_a = _to_decimal(rep.get('length'))
        wid_a = _to_decimal(rep.get('width'))
        locked = bool(rep.get('lock_rotation', False))
        fp_count = len(group_slots)
        options = []
        orientation_options = [(wid_a, len_a, False)]
        if not locked:
            orientation_options.append((len_a, wid_a, True))
        for (w, l, rotated) in orientation_options:
            if w > bed_wid or w <= 0 or l <= 0:
                continue
            max_units = int(bed_wid // w)
            if max_units < 1:
                continue
            per_row = int(bed_len // l)
            needed = ceil(fp_count / per_row) if per_row > 0 else max_units
            units = min(max_units, needed)
            eff_w = w * units
            options.append((eff_w, w, l, rotated, units))
        if not options:
            options = [(wid_a, wid_a, len_a, False, 1)]
        group_list.append((name, group_slots, options))

    bed_wid_int = int(bed_wid)
    N = len(group_list)
    dp = [None] * (bed_wid_int + 1)
    dp[0] = (Decimal('0'), [])
    for gi in range(N):
        name, group_slots, options = group_list[gi]
        for oi, (eff_w, w, l, rotated, units) in enumerate(options):
            eff_w_int = int(eff_w)
            if eff_w_int > bed_wid_int:
                continue
            for cur_w in range(bed_wid_int, -1, -1):
                if dp[cur_w] is None:
                    continue
                if any(item[0] == gi for item in dp[cur_w][1]):
                    continue
                if len(dp[cur_w][1]) >= 2:
                    continue
                new_w = cur_w + eff_w_int
                if new_w > bed_wid_int:
                    continue
                new_total = dp[cur_w][0] + eff_w
                if dp[new_w] is None or new_total > dp[new_w][0]:
                    dp[new_w] = (new_total, dp[cur_w][1] + [(gi, oi, eff_w, w, l, rotated, units)])

    best = None
    for w_int in range(bed_wid_int, -1, -1):
        if dp[w_int] is not None and dp[w_int][1]:
            best = dp[w_int][1]
            break

    chosen_groups = set()
    orientation_map = {}
    units_map = {}
    if best:
        for gi, oi, eff_w, w, l, rotated, units in best:
            chosen_groups.add(gi)
            orientation_map[gi] = (w, l, rotated)
            units_map[gi] = units
    for gi in range(N):
        if gi not in orientation_map:
            name, group_slots, options = group_list[gi]
            eff_w, w, l, rotated, units = options[0]
            orientation_map[gi] = (w, l, rotated)
            units_map[gi] = units

    ordered = [gi for gi in range(N) if gi in chosen_groups] + \
              [gi for gi in range(N) if gi not in chosen_groups]

    bands = []
    cur_y = Decimal('0')
    for gi in [g for g in ordered if g in chosen_groups]:
        name, group_slots, options = group_list[gi]
        w, l, rotated = orientation_map[gi]
        units = units_map[gi]
        group_bands = []
        for u in range(units):
            band_y = cur_y + w * u
            group_bands.append((band_y, w, Decimal('0')))
        for slot in group_slots:
            fitted = False
            for bi in range(len(group_bands)):
                band_y, band_w, band_x = group_bands[bi]
                if band_x + l <= bed_len:
                    placed.append({
                        'product_code': slot.get('product_code', ''),
                        'qty': str(slot.get('qty', Decimal('0'))),
                        'container_name': slot.get('container_name', ''),
                        'slot_products': slot.get('slot_products', []),
                        'layers': slot.get('layers', 1),
                        'x': str(band_x), 'y': str(band_y),
                        'w': str(l), 'd': str(w), 'rotated': rotated,
                        'lock_rotation': bool(slot.get('lock_rotation', False)),
                    })
                    group_bands[bi] = (band_y, band_w, band_x + l)
                    max_x = max(max_x, band_x + l)
                    fitted = True
                    break
            if not fitted:
                can_fit = False
                if of_x + l > bed_len:
                    of_x = Decimal('0')
                    of_y += of_h
                    of_h = Decimal('0')
                placed.append({
                    'product_code': slot.get('product_code', ''),
                    'qty': str(slot.get('qty', Decimal('0'))),
                    'container_name': slot.get('container_name', ''),
                    'slot_products': slot.get('slot_products', []),
                    'layers': slot.get('layers', 1),
                    'x': str(of_x), 'y': str(of_y),
                    'w': str(l), 'd': str(w), 'rotated': rotated,
                    'lock_rotation': bool(slot.get('lock_rotation', False)),
                })
                of_x += l
                of_h = max(of_h, w)
                max_x = max(max_x, of_x)
                max_y = max(max_y, of_y + w)
        bands.extend(group_bands)
        cur_y += w * units
        max_y = max(max_y, cur_y)

    for gi in [g for g in ordered if g not in chosen_groups]:
        name, group_slots, options = group_list[gi]
        w, l, rotated = orientation_map[gi]
        for slot in group_slots:
            fitted = False
            for bi, (band_y, band_w, band_used_x) in enumerate(bands):
                if w > band_w:
                    continue
                if band_used_x + l <= bed_len:
                    placed.append({
                        'product_code': slot.get('product_code', ''),
                        'qty': str(slot.get('qty', Decimal('0'))),
                        'container_name': slot.get('container_name', ''),
                        'slot_products': slot.get('slot_products', []),
                        'layers': slot.get('layers', 1),
                        'x': str(band_used_x), 'y': str(band_y),
                        'w': str(l), 'd': str(w), 'rotated': rotated,
                        'lock_rotation': bool(slot.get('lock_rotation', False)),
                    })
                    bands[bi] = (band_y, band_w, band_used_x + l)
                    max_x = max(max_x, band_used_x + l)
                    fitted = True
                    break
            if not fitted:
                can_fit = False
                if of_x + l > bed_len:
                    of_x = Decimal('0')
                    of_y += of_h
                    of_h = Decimal('0')
                placed.append({
                    'product_code': slot.get('product_code', ''),
                    'qty': str(slot.get('qty', Decimal('0'))),
                    'container_name': slot.get('container_name', ''),
                    'slot_products': slot.get('slot_products', []),
                    'layers': slot.get('layers', 1),
                    'x': str(of_x), 'y': str(of_y),
                    'w': str(l), 'd': str(w), 'rotated': rotated,
                    'lock_rotation': bool(slot.get('lock_rotation', False)),
                })
                of_x += l
                of_h = max(of_h, w)
                max_x = max(max_x, of_x)
                max_y = max(max_y, of_y + w)
    return {'placed': placed, 'can_fit': can_fit, 'max_x': max_x, 'max_y': max_y}


# ---------------------------------------------------------------------------
# バリアント生成・パッカー試行（shipping版と同一ロジック）
# ---------------------------------------------------------------------------

def _split_free_rect(rect, box):
    fx, fy, fw, fh = rect
    bx, by, bw, bh = box
    if bx >= fx + fw or fx >= bx + bw or by >= fy + fh or fy >= by + bh:
        return [rect]
    result = []
    if fx < bx:
        result.append((fx, fy, bx - fx, fh))
    if bx + bw < fx + fw:
        result.append((bx + bw, fy, fx + fw - bx - bw, fh))
    if fy < by:
        result.append((fx, fy, fw, by - fy))
    if by + bh < fy + fh:
        result.append((fx, by + bh, fw, fy + fh - by - bh))
    return [(x, y, w, h) for (x, y, w, h) in result if w > 0 and h > 0]


def _remove_contained(rects):
    result = []
    for i, (ax, ay, aw, ah) in enumerate(rects):
        contained = False
        for j, (bx, by, bw, bh) in enumerate(rects):
            if i != j and bx <= ax and by <= ay and bx + bw >= ax + aw and by + bh >= ay + ah:
                contained = True
                break
        if not contained:
            result.append((ax, ay, aw, ah))
    return result


def _compact_left(placed, bed_len, bed_wid):
    compacted = []
    for item in sorted(
        placed,
        key=lambda p: (_to_decimal(p.get('x')), _to_decimal(p.get('y'))),
    ):
        py = _to_decimal(item['y'])
        pw = _to_decimal(item['w'])
        pd = _to_decimal(item['d'])
        target_x = Decimal('0')
        for other in compacted:
            oy = _to_decimal(other['y'])
            od = _to_decimal(other['d'])
            if oy + od <= py or py + pd <= oy:
                continue
            target_x = max(target_x, _to_decimal(other['x']) + _to_decimal(other['w']))
        if target_x + pw > bed_len:
            target_x = max(Decimal('0'), bed_len - pw)
        compacted.append({**item, 'x': str(target_x)})
    return compacted


def _fill_gaps(in_bed, overflow, bed_len, bed_wid):
    if not overflow:
        return in_bed, overflow
    free_rects = [(Decimal('0'), Decimal('0'), bed_len, bed_wid)]
    for p in in_bed:
        box = (Decimal(p['x']), Decimal(p['y']), Decimal(p['w']), Decimal(p['d']))
        new_free = []
        for rect in free_rects:
            new_free.extend(_split_free_rect(rect, box))
        free_rects = _remove_contained(new_free)

    new_overflow = []
    for slot in overflow:
        slot_len = _to_decimal(slot.get('w'))
        slot_wid = _to_decimal(slot.get('d'))
        orientations = ((slot_len, slot_wid),)
        if not bool(slot.get('lock_rotation', False)):
            orientations = ((slot_len, slot_wid), (slot_wid, slot_len))
        best = None
        best_score = None
        for idx, (fx, fy, fw, fh) in enumerate(free_rects):
            for (length, width) in orientations:
                if length <= fw and width <= fh:
                    anchors = (
                        (fx, fy),
                        (fx + fw - length, fy),
                        (fx, fy + fh - width),
                        (fx + fw - length, fy + fh - width),
                    )
                    for px, py in anchors:
                        bottom_gap = bed_wid - (py + width)
                        score = (
                            bottom_gap,
                            min(fw - length, fh - width),
                            fx + fw - (px + length),
                            py, px,
                        )
                        if best_score is None or score < best_score:
                            best_score = score
                            best = (idx, length, width, px, py)
        if best is None:
            new_overflow.append(slot)
            continue
        _, length, width, fx, fy = best
        in_bed.append({
            **slot,
            'x': str(fx), 'y': str(fy),
            'w': str(length), 'd': str(width),
            'rotated': abs(length - slot_len) > Decimal('1'),
        })
        box = (fx, fy, length, width)
        new_free = []
        for rect in free_rects:
            new_free.extend(_split_free_rect(rect, box))
        free_rects = _remove_contained(new_free)
    return in_bed, new_overflow


def _swap_overflow(in_bed, overflow, bed_len, bed_wid):
    if not overflow:
        return in_bed, overflow
    improved = True
    while improved:
        improved = False
        for oi, o_item in enumerate(overflow):
            o_len = _to_decimal(o_item.get('w'))
            o_wid = _to_decimal(o_item.get('d'))
            o_orientations = [(o_len, o_wid)]
            if not bool(o_item.get('lock_rotation', False)):
                o_orientations.append((o_wid, o_len))
            for pi in range(len(in_bed) - 1, -1, -1):
                p_item = in_bed[pi]
                temp_in_bed = in_bed[:pi] + in_bed[pi + 1:]
                free_rects = [(Decimal('0'), Decimal('0'), bed_len, bed_wid)]
                for p in temp_in_bed:
                    box = (Decimal(p['x']), Decimal(p['y']),
                           Decimal(p['w']), Decimal(p['d']))
                    new_free = []
                    for rect in free_rects:
                        new_free.extend(_split_free_rect(rect, box))
                    free_rects = _remove_contained(new_free)
                o_best = None
                o_best_score = None
                for idx, (fx, fy, fw, fh) in enumerate(free_rects):
                    for (length, width) in o_orientations:
                        if length <= fw and width <= fh:
                            anchors = (
                                (fx, fy), (fx + fw - length, fy),
                                (fx, fy + fh - width), (fx + fw - length, fy + fh - width),
                            )
                            for ax, ay in anchors:
                                score = (min(fw - length, fh - width), ay, ax)
                                if o_best_score is None or score < o_best_score:
                                    o_best_score = score
                                    o_best = (length, width, ax, ay)
                if o_best is None:
                    continue
                ol, ow, ox, oy = o_best
                box = (ox, oy, ol, ow)
                new_free = []
                for rect in free_rects:
                    new_free.extend(_split_free_rect(rect, box))
                free_rects_after = _remove_contained(new_free)
                p_len = _to_decimal(p_item.get('w'))
                p_wid = _to_decimal(p_item.get('d'))
                p_orientations = [(p_len, p_wid)]
                if not bool(p_item.get('lock_rotation', False)):
                    p_orientations.append((p_wid, p_len))
                p_best = None
                p_best_score = None
                for idx, (fx, fy, fw, fh) in enumerate(free_rects_after):
                    for (length, width) in p_orientations:
                        if length <= fw and width <= fh:
                            anchors = (
                                (fx, fy), (fx + fw - length, fy),
                                (fx, fy + fh - width), (fx + fw - length, fy + fh - width),
                            )
                            for ax, ay in anchors:
                                score = (min(fw - length, fh - width), ay, ax)
                                if p_best_score is None or score < p_best_score:
                                    p_best_score = score
                                    p_best = (length, width, ax, ay)
                if p_best is None:
                    continue
                pl, pw_val, px, py = p_best
                in_bed = temp_in_bed
                in_bed.append({
                    **o_item,
                    'x': str(ox), 'y': str(oy),
                    'w': str(ol), 'd': str(ow),
                    'rotated': abs(ol - o_len) > Decimal('1'),
                })
                in_bed.append({
                    **p_item,
                    'x': str(px), 'y': str(py),
                    'w': str(pl), 'd': str(pw_val),
                    'rotated': abs(pl - p_len) > Decimal('1'),
                })
                overflow = overflow[:oi] + overflow[oi + 1:]
                improved = True
                break
            if improved:
                break
    return in_bed, overflow


def _split_in_bed_and_overflow(placed_all, bed_len, bed_wid):
    in_bed = []
    overflow = []
    for placed in placed_all:
        px = _to_decimal(placed['x'])
        py = _to_decimal(placed['y'])
        pw = _to_decimal(placed['w'])
        pd = _to_decimal(placed['d'])
        if px + pw <= bed_len and py + pd <= bed_wid:
            in_bed.append(placed)
        else:
            overflow.append(placed)
    return in_bed, overflow


def _finalize_pack_result(pack_result, bed_len, bed_wid, light=False):
    placed_all = pack_result['placed']
    in_bed, overflow = _split_in_bed_and_overflow(placed_all, bed_len, bed_wid)
    in_bed, overflow = _fill_gaps(in_bed, overflow, bed_len, bed_wid)
    if not light:
        in_bed, overflow = _swap_overflow(in_bed, overflow, bed_len, bed_wid)
        in_bed = _compact_left(in_bed, bed_len, bed_wid)
    placed = in_bed + overflow
    can_fit = not overflow
    max_x = max((_to_decimal(item['x']) + _to_decimal(item['w']) for item in placed), default=Decimal('0'))
    max_y = max((_to_decimal(item['y']) + _to_decimal(item['d']) for item in placed), default=Decimal('0'))
    return {'placed': placed, 'can_fit': can_fit, 'max_x': max_x, 'max_y': max_y}


def _sorted_slot_variants(slots):
    area_sorted = sorted(
        slots,
        key=lambda slot: (
            -(_to_decimal(slot.get('length')) * _to_decimal(slot.get('width'))),
            -max(_to_decimal(slot.get('length')), _to_decimal(slot.get('width'))),
        ),
    )
    long_side_sorted = sorted(
        slots,
        key=lambda slot: (
            -max(_to_decimal(slot.get('length')), _to_decimal(slot.get('width'))),
            -min(_to_decimal(slot.get('length')), _to_decimal(slot.get('width'))),
        ),
    )
    return [slots, area_sorted, long_side_sorted]


def _flip_slot_orientation(slot):
    return {
        **slot,
        'length': slot.get('width'),
        'width': slot.get('length'),
        'rotated': not bool(slot.get('rotated', False)),
    }


def _rotation_variants(slots):
    if not slots:
        return [slots]

    def _is_locked(slot):
        return bool(slot.get('lock_rotation', False))

    group_keys = []
    seen = set()
    for slot in slots:
        key = (str(slot.get('product_code', '')), str(slot.get('container_name', '')))
        if key in seen:
            continue
        seen.add(key)
        if _is_locked(slot):
            continue
        group_keys.append(key)

    variants = [slots]
    for target_key in group_keys:
        variants.append([
            _flip_slot_orientation(slot)
            if (str(slot.get('product_code', '')), str(slot.get('container_name', ''))) == target_key
            else slot
            for slot in slots
        ])

    if group_keys:
        variants.append([
            _flip_slot_orientation(slot) if not _is_locked(slot) else slot
            for slot in slots
        ])

    unique = []
    unique_keys = set()
    for variant in variants:
        signature = tuple(
            (str(slot.get('product_code', '')), str(slot.get('container_name', '')),
             str(slot.get('length', '')), str(slot.get('width', '')),
             bool(slot.get('rotated', False)))
            for slot in variant
        )
        if signature in unique_keys:
            continue
        unique_keys.add(signature)
        unique.append(variant)
    return unique


def _group_order_variants(slots):
    if not slots:
        return [slots]

    groups = {}
    order = []
    for slot in slots:
        key = (str(slot.get('product_code', '')), str(slot.get('container_name', '')))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(slot)

    def group_dims(key):
        first = groups[key][0]
        length = _to_decimal(first.get('length'))
        width = _to_decimal(first.get('width'))
        area = length * width
        count = Decimal(len(groups[key]))
        return length, width, area, count

    order_variants = [
        order,
        sorted(order, key=lambda k: (-group_dims(k)[1], -group_dims(k)[0], k[0], k[1])),
        sorted(order, key=lambda k: (-group_dims(k)[0], -group_dims(k)[1], k[0], k[1])),
        sorted(order, key=lambda k: (-group_dims(k)[2], -group_dims(k)[3], k[0], k[1])),
    ]

    variants = []
    seen = set()
    for group_order in order_variants:
        signature = tuple(group_order)
        if signature in seen:
            continue
        seen.add(signature)
        variant = []
        for key in group_order:
            variant.extend(groups[key])
        variants.append(variant)
    return variants


def _try_packers(bed_len, bed_wid, slots, packers):
    first_candidate = None
    best_ng_candidate = None
    best_ng_key = None
    seen = set()
    for rotation_variant in _rotation_variants(slots):
        for ordered_variant in _group_order_variants(rotation_variant):
            for variant in _sorted_slot_variants(ordered_variant):
                for packer in packers:
                    key = (packer.__name__, tuple(
                        (str(slot.get('product_code', '')), str(slot.get('container_name', '')),
                         str(slot.get('length', '')), str(slot.get('width', '')),
                         bool(slot.get('rotated', False)))
                        for slot in variant
                    ))
                    if key in seen:
                        continue
                    seen.add(key)
                    finalized = _finalize_pack_result(packer(bed_len, bed_wid, variant), bed_len, bed_wid)
                    if first_candidate is None:
                        first_candidate = finalized
                    if finalized['can_fit']:
                        return finalized, True
                    overflow_count = 0
                    overflow_area = Decimal('0')
                    for item in finalized['placed']:
                        px = _to_decimal(item['x'])
                        py = _to_decimal(item['y'])
                        pw = _to_decimal(item['w'])
                        pd = _to_decimal(item['d'])
                        if px + pw <= bed_len and py + pd <= bed_wid:
                            continue
                        overflow_count += 1
                        overflow_area += pw * pd
                    ng_key = (overflow_count, overflow_area)
                    if best_ng_candidate is None or ng_key < best_ng_key:
                        best_ng_candidate = finalized
                        best_ng_key = ng_key
    return best_ng_candidate or first_candidate, False


def _pack_slots(bed_len, bed_wid, slots):
    result, ok = _try_packers(bed_len, bed_wid, slots, (_pack_column,))
    if ok:
        return result['placed'], True, result['max_x'], result['max_y']
    result2, ok2 = _try_packers(bed_len, bed_wid, slots,
                                (_pack_guillotine, _pack_bay, _pack_shelf))
    if ok2:
        return result2['placed'], True, result2['max_x'], result2['max_y']
    fallback = result
    if result2:
        r1_of = sum(1 for p in result['placed']
                    if _to_decimal(p['x']) + _to_decimal(p['w']) > bed_len
                    or _to_decimal(p['y']) + _to_decimal(p['d']) > bed_wid)
        r2_of = sum(1 for p in result2['placed']
                    if _to_decimal(p['x']) + _to_decimal(p['w']) > bed_len
                    or _to_decimal(p['y']) + _to_decimal(p['d']) > bed_wid)
        if r2_of < r1_of:
            fallback = result2
    return fallback['placed'], fallback['can_fit'], fallback['max_x'], fallback['max_y']


def _quick_can_fit(bed_len, bed_wid, slots):
    result = _finalize_pack_result(_pack_column(bed_len, bed_wid, slots), bed_len, bed_wid, light=True)
    return result['can_fit']


def _calc_remaining(bed_len, bed_wid, base_slots, type_records):
    result = {}
    for record in type_records:
        label = record['label']
        extra_slot = {
            'product_code': '',
            'qty': Decimal('0'),
            'length': record['length'],
            'width': record['width'],
            'rotated': record['rotated'],
            'lock_rotation': record.get('lock_rotation', False),
        }
        lo, hi = 0, 50
        while lo < hi:
            mid = (lo + hi + 1) // 2
            test_slots = list(base_slots) + [dict(extra_slot) for _ in range(mid)]
            if _quick_can_fit(bed_len, bed_wid, test_slots):
                lo = mid
            else:
                hi = mid - 1
        if lo > 0:
            result[label] = max(result.get(label, 0), lo)
    return [{'label': key, 'count': value} for key, value in result.items()]


# ---------------------------------------------------------------------------
# メイン: calculate_truck_load（購買専用版）
# ---------------------------------------------------------------------------
# shipping版との違い:
#   グルーピングキーから capacity を除外。
#   同じ物理サイズ・同名の容器は capacity が異なっても1グループにまとめ、
#   製品別にコンテナ数を計算してからグループ内で合算して段積みする。

def calculate_truck_load(assignments, truck):
    from math import ceil

    bed_width = _to_decimal(truck.width)
    bed_depth = _to_decimal(truck.depth)
    bed_height = _to_decimal(truck.height)
    truck_max_weight = _to_decimal(truck.max_weight)
    container_gap = _to_decimal(getattr(truck, 'container_gap', 0) or 0)

    errors = []
    if bed_width <= 0 or bed_depth <= 0:
        errors.append('便マスタの荷台サイズが不正です。')
        return {
            'can_fit': False, 'occupancy_percent': Decimal('0'),
            'total_weight': Decimal('0'), 'placed': [], 'remaining': [],
            'errors': errors, 'warnings': [],
        }

    total_weight = Decimal('0')
    non_mix_products = set()
    all_products = set()
    type_records = []
    slots = []

    # capacity を除外したキーでグルーピング
    group_container_count = defaultdict(Decimal)
    group_child_count = defaultdict(Decimal)
    group_products = {}
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
        parent = container.get('parent') or {}
        child_count = None

        if parent and parent.get('width') and parent.get('depth'):
            child_capacity = _to_decimal(container.get('capacity'), default='1')
            if child_capacity <= 0:
                child_capacity = Decimal('1')
            child_count = (qty / child_capacity).to_integral_value(rounding=ROUND_CEILING)
            parent_cap = _to_decimal(parent.get('capacity'), default='1')
            if parent_cap <= 0:
                parent_cap = Decimal('1')
            container_count = (child_count / parent_cap).to_integral_value(rounding=ROUND_CEILING)
            cw = _to_decimal(parent.get('width'))
            cd = _to_decimal(parent.get('depth'))
            ch = _to_decimal(parent.get('height'))
            can_mix = bool(parent.get('can_mix', True))
            stackable = bool(parent.get('stackable', True))
            max_stack = int(parent.get('max_stack') or 999)
            use_container = parent
        else:
            capacity = _to_decimal(container.get('capacity'), default='1')
            if capacity <= 0:
                capacity = Decimal('1')
            container_count = (qty / capacity).to_integral_value(rounding=ROUND_CEILING)
            cw = _to_decimal(container.get('width'))
            cd = _to_decimal(container.get('depth'))
            ch = _to_decimal(container.get('height'))
            can_mix = bool(container.get('can_mix', True))
            stackable = bool(container.get('stackable', True))
            max_stack = int(container.get('max_stack') or 999)
            use_container = container

        if not can_mix and product_code:
            non_mix_products.add(product_code)
        if cw <= 0 or cd <= 0:
            continue

        # 親容器に入る子容器グループと、親容器そのものを使う製品は別グループにする。
        # これにより「汎用ポリ同士は同じ小アミへ混載可」だが、
        # 「最初から小アミを使う製品」は1箱として別扱いできる。
        if parent and parent.get('width') and parent.get('depth'):
            key_base = str(use_container.get('container_code') or '') or str(use_container.get('name') or '') or product_code
            key = f'parent:{key_base}'
            group_child_count[key] += child_count
            parent_cap = _to_decimal(parent.get('capacity'), default='1')
            if parent_cap <= 0:
                parent_cap = Decimal('1')
            group_container_count[key] = (group_child_count[key] / parent_cap).to_integral_value(rounding=ROUND_CEILING)
        else:
            key_base = str(use_container.get('container_code') or '') or str(use_container.get('name') or '') or product_code
            key = f'container:{key_base}'
            group_container_count[key] += container_count
        products = group_products.setdefault(key, [])
        merged = False
        for idx, (pcode, pqty) in enumerate(products):
            if pcode == product_code:
                products[idx] = (pcode, pqty + qty)
                merged = True
                break
        if not merged:
            products.append((product_code, qty))
        group_meta.setdefault(key, {
            'container': use_container,
            'cw': cw, 'cd': cd, 'ch': ch,
            'can_mix': can_mix,
            'stackable': stackable,
            'max_stack': max_stack,
            'parent_capacity': _to_decimal(parent.get('capacity'), default='1') if parent and parent.get('width') and parent.get('depth') else None,
            'uses_parent': bool(parent and parent.get('width') and parent.get('depth')),
        })

    for key, meta in group_meta.items():
        total_containers = group_container_count[key]
        container = meta['container']
        cw = meta['cw']
        cd = meta['cd']
        ch = meta['ch']
        stackable = meta['stackable']
        max_stack = meta['max_stack']
        uses_parent = meta.get('uses_parent', False)
        parent_capacity = meta.get('parent_capacity')

        layers = Decimal('1')
        if stackable and ch > 0 and bed_height > 0:
            truck_layers = int(bed_height // ch)
            if truck_layers > 0:
                layers = Decimal(str(min(truck_layers, max_stack if max_stack > 0 else truck_layers)))

        orientation = str(container.get('orientation') or 'free').strip().lower()
        cap_normal = int(bed_depth // cd) * int(bed_width // cw)
        cap_rotated = int(bed_depth // cw) * int(bed_width // cd)
        if orientation == 'long':
            rotated = cw > cd
            rotation_locked = True
        elif orientation == 'short':
            rotated = cd > cw
            rotation_locked = True
        else:
            rotated = cap_rotated > cap_normal
            rotation_locked = False

        length = cd if not rotated else cw
        width = cw if not rotated else cd

        if length <= 0 or width <= 0:
            continue

        group_products_list = group_products.get(key, [])
        container_name = str(container.get('name') or '') or (group_products_list[0][0] if group_products_list else '')
        type_records.append({
            'label': container_name,
            'length': length, 'width': width,
            'rotated': rotated, 'lock_rotation': rotation_locked,
        })

        # 製品別コンテナ数を算出（group_productsはqtyベースなので再計算）
        product_container_remaining = {}
        for item in assignments:
            pc = str(item.get('product_code') or '')
            if pc not in {p[0] for p in group_products_list}:
                continue
            q = _to_decimal(item.get('qty'))
            if q <= 0:
                continue
            cont = item.get('container') or {}
            par = cont.get('parent') or {}
            if par and par.get('width') and par.get('depth'):
                cc = _to_decimal(cont.get('capacity'), default='1')
                if cc <= 0:
                    cc = Decimal('1')
                cnt = int((q / cc).to_integral_value(rounding=ROUND_CEILING))
            else:
                cc = _to_decimal(cont.get('capacity'), default='1')
                if cc <= 0:
                    cc = Decimal('1')
                cnt = int((q / cc).to_integral_value(rounding=ROUND_CEILING))
            product_container_remaining[pc] = product_container_remaining.get(pc, 0) + cnt

        product_qty_map = {pcode: Decimal(str(pqty)) for pcode, pqty in group_products_list}
        # グループ全体でフットプリントを生成し、製品を順に詰める
        # （同じ容器なら製品が違っても段積み可能）
        total_floor = int((total_containers / layers).to_integral_value(rounding=ROUND_CEILING)) if layers > 0 else int(total_containers)
        remaining_total = int(total_containers)
        product_keys = [pc for pc in product_container_remaining if product_container_remaining[pc] > 0]
        for _ in range(total_floor):
            slot_layers = max(1, min(int(layers), remaining_total))
            remaining_total -= slot_layers
            first = None
            consumed = 0
            slot_products = []
            slot_capacity = slot_layers
            if uses_parent:
                parent_cap_int = int(parent_capacity or 1)
                if parent_cap_int <= 0:
                    parent_cap_int = 1
                slot_capacity = slot_layers * parent_cap_int
            for pcode in product_keys:
                if product_container_remaining[pcode] <= 0:
                    continue
                if first is None:
                    first = pcode
                take = min(slot_capacity - consumed, product_container_remaining[pcode])
                if take <= 0:
                    continue
                product_container_remaining[pcode] -= take
                consumed += take
                slot_products.append({
                    'product_code': pcode,
                    'container_count': take,
                })
                if consumed >= slot_capacity:
                    break
            footprint_qty = product_qty_map.get(first, Decimal('0')) if first else Decimal('0')
            slots.append({
                'product_code': first or '',
                'qty': str(footprint_qty),
                'container_name': container_name,
                'slot_products': slot_products,
                'layers': slot_layers,
                'length': length,
                'width': width,
                'rotated': rotated,
                'lock_rotation': rotation_locked,
            })

    total_footprints = len(slots)

    # 容器間隔: スロット寸法にgap加算 + パッキングエリアを縁からgap分縮小
    pack_bed_depth = bed_depth
    pack_bed_width = bed_width
    if container_gap > 0:
        for slot in slots:
            slot['length'] = _to_decimal(slot['length']) + container_gap
            slot['width'] = _to_decimal(slot['width']) + container_gap
        for rec in type_records:
            rec['length'] = _to_decimal(rec['length']) + container_gap
            rec['width'] = _to_decimal(rec['width']) + container_gap
        pack_bed_depth = bed_depth - container_gap
        pack_bed_width = bed_width - container_gap

    placed, can_fit, _, _ = _pack_slots(pack_bed_depth, pack_bed_width, slots)

    # 配置結果: 縁gap分オフセット + スロット寸法を実寸に戻す
    if container_gap > 0:
        for p in placed:
            p['x'] = _to_decimal(p['x']) + container_gap
            p['y'] = _to_decimal(p['y']) + container_gap
            p['w'] = _to_decimal(p['w']) - container_gap
            p['d'] = _to_decimal(p['d']) - container_gap

    bed_area = bed_width * bed_depth
    # 占有率はin-bed分のみ（オーバーフロー分を除外）
    in_bed_area = Decimal('0')
    n_overflow = 0
    for p in placed:
        px = _to_decimal(p.get('x'))
        py = _to_decimal(p.get('y'))
        pw = _to_decimal(p.get('w'))
        pd = _to_decimal(p.get('d'))
        if px + pw <= bed_depth and py + pd <= bed_width:
            in_bed_area += pw * pd
        else:
            n_overflow += 1
    occupancy_ratio = in_bed_area / bed_area if bed_area > 0 else Decimal('0')
    occupancy_percent = (occupancy_ratio * Decimal('100')).quantize(Decimal('0.1'))

    warnings = []
    if not can_fit:
        in_bed_count = total_footprints - n_overflow
        warnings.append(f'積載超過：{total_footprints}枠中{n_overflow}枠がはみ出し（配置可能{in_bed_count}枠）')
    if truck_max_weight > 0 and total_weight > truck_max_weight:
        errors.append('積載重量が最大積載重量を超えています。')
    mixed_blocked = bool(non_mix_products) and len(all_products) > 1
    if mixed_blocked:
        errors.append('混載不可容器を含むため、同一便に複数品番を割り付けできません。')

    remaining = []
    if can_fit:
        remaining = _calc_remaining(pack_bed_depth, pack_bed_width, slots, type_records)

    return {
        'can_fit': can_fit,
        'occupancy_percent': occupancy_percent,
        'total_weight': total_weight,
        'placed': placed,
        'remaining': remaining,
        'errors': errors,
        'warnings': warnings,
        'total_footprints': total_footprints,
        'overflow_count': n_overflow,
    }
