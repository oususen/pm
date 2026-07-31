from collections import defaultdict
from decimal import Decimal, ROUND_CEILING


def _to_decimal(value, default='0'):
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _pack_shelf(bed_len, bed_wid, slots):
    """
    Shelf方式（長手方向に1列ずつ敷き詰め、各スロットは回転も試す）。
    """
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
        for (length, width, rotated) in ((len_a, wid_a, rot_a), (wid_a, len_a, not rot_a)):
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
            'layers': slot.get('layers', 1),
            'x': str(x),
            'y': str(y),
            'w': str(length),
            'd': str(width),
            'rotated': rotated,
        })
        row_x = x + length
        row_h = max(row_h, width)
        max_x = max(max_x, row_x)
        max_y = max(max_y, y + width)
    return {'placed': placed, 'can_fit': can_fit, 'max_x': max_x, 'max_y': max_y}


def _pack_guillotine(bed_len, bed_wid, slots):
    """
    Guillotine 2Dパッキング（Best Short Side Fit）。
    - 各スロットを回転も考慮し、最も効率よく収まる自由矩形へ配置
    - 収まらないスロットは荷台の下（超過領域）に配置し（can_fit=False）、見えるようにする
    """
    placed = []
    free_rects = [(Decimal('0'), Decimal('0'), bed_len, bed_wid)]
    can_fit = True
    max_x = Decimal('0')
    max_y = Decimal('0')
    # 超過領域（荷台の下）へはみ出し分を並べるカーソル
    of_x = Decimal('0')
    of_y = bed_wid
    of_h = Decimal('0')

    for slot in slots:
        len_a = _to_decimal(slot.get('length'))
        wid_a = _to_decimal(slot.get('width'))
        rot_a = bool(slot.get('rotated', False))
        len_b = wid_a
        wid_b = len_a
        rot_b = not rot_a

        # 収まる自由矩形を探す（Best Short Side Fit）
        best = None
        for rect_idx, (fx, fy, fw, fh) in enumerate(free_rects):
            for (length, width, rotated) in ((len_a, wid_a, rot_a), (len_b, wid_b, rot_b)):
                if length <= fw and width <= fh:
                    rest_w = fw - length
                    rest_h = fh - width
                    score = min(rest_w, rest_h)
                    score_area = rest_w * rest_h
                    if best is None or score < best[0] or (score == best[0] and score_area < best[1]):
                        best = (score, score_area, rect_idx, fx, fy, length, width, rotated)

        if best is None:
            # 収まらない → 超過領域へ配置（can_fit=False）
            can_fit = False
            if of_x + len_a > bed_len:
                of_x = Decimal('0')
                of_y += of_h
                of_h = Decimal('0')
            placed.append({
                'product_code': slot.get('product_code', ''),
                'qty': str(slot.get('qty', Decimal('0'))),
                'container_name': slot.get('container_name', ''),
                'layers': slot.get('layers', 1),
                'x': str(of_x),
                'y': str(of_y),
                'w': str(len_a),
                'd': str(wid_a),
                'rotated': rot_a,
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
        # Guillotine分割: 余白の大きい側を全長維持して2つに分ける（重なり・隙間なし）
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
            'layers': slot.get('layers', 1),
            'x': str(fx),
            'y': str(fy),
            'w': str(length),
            'd': str(width),
            'rotated': rotated,
        })
        max_x = max(max_x, fx2)
        max_y = max(max_y, fy2)

    return {'placed': placed, 'can_fit': can_fit, 'max_x': max_x, 'max_y': max_y}


def _pack_bay(bed_len, bed_wid, slots):
    """
    ベイ（列）方式: 幅方向に容器を横並びで詰め（合計幅≦荷台幅）、そのベイを長手方向に並べる。
    「830+1540=2370≦2400」のような横並び配置を実現する。
    長手の大きい容器から並べ、幅方向に回転も試して詰める。
    """
    placed = []
    sorted_slots = sorted(
        slots,
        key=lambda s: max(_to_decimal(s.get('length')), _to_decimal(s.get('width'))),
        reverse=True,
    )
    col_x = Decimal('0')  # 現在のベイの長手位置
    bay_w = Decimal('0')  # 現在のベイの使用幅
    bay_len = Decimal('0')  # 現在のベイの長手最大長
    can_fit = True
    max_x = Decimal('0')
    max_y = Decimal('0')
    # 超過領域（荷台の下）
    of_x = Decimal('0')
    of_y = bed_wid
    of_h = Decimal('0')

    for slot in sorted_slots:
        len_a = _to_decimal(slot.get('length'))
        wid_a = _to_decimal(slot.get('width'))
        rot_a = bool(slot.get('rotated', False))
        options = ((len_a, wid_a, rot_a), (wid_a, len_a, not rot_a))

        chosen = None
        # 現在のベイの残り幅に収まる向きのうち、幅を最も埋める向きを選ぶ
        # （例: 830+1540=2370≦2400 のような横並びを優先）
        chosen = None
        best_opt = None
        for (length, width, rotated) in options:
            if bay_w + width <= bed_wid:
                if best_opt is None or width > best_opt[1]:
                    best_opt = (length, width, rotated)
        if best_opt is not None:
            chosen = best_opt
        else:
            # 現在のベイに入らない → 次のベイへ
            col_x += bay_len
            bay_w = Decimal('0')
            bay_len = Decimal('0')
            for (length, width, rotated) in options:
                if width <= bed_wid:
                    if chosen is None or width > chosen[1]:
                        chosen = (length, width, rotated)

        if chosen is None:
            # 幅自体に収まらない → 超過領域へ配置（can_fit=False）
            can_fit = False
            if of_x + len_a > bed_len:
                of_x = Decimal('0')
                of_y += of_h
                of_h = Decimal('0')
            placed.append({
                'product_code': slot.get('product_code', ''),
                'qty': str(slot.get('qty', Decimal('0'))),
                'container_name': slot.get('container_name', ''),
                'layers': slot.get('layers', 1),
                'x': str(of_x),
                'y': str(of_y),
                'w': str(len_a),
                'd': str(wid_a),
                'rotated': rot_a,
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
            'layers': slot.get('layers', 1),
            'x': str(col_x),
            'y': str(bay_w),
            'w': str(length),
            'd': str(width),
            'rotated': rotated,
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
    """
    DP向き決定＋製品別行方式:
    1. 製品タイプ（container_name）ごとにグループ化
    2. DPで各製品タイプの向き（幅）を決定（幅合計が荷台幅に最も近い組み合わせ）
    3. 各製品タイプは自分の行（幅帯）に、長手方向に同一製品を詰める → 隙間ゼロ
    """
    placed = []
    can_fit = True
    max_x = Decimal('0')
    max_y = Decimal('0')
    of_x = Decimal('0')
    of_y = bed_wid
    of_h = Decimal('0')

    # 製品タイプごとにグループ化
    groups = defaultdict(list)
    for slot in slots:
        name = slot.get('container_name', '') or slot.get('product_code', '')
        groups[name].append(slot)

    # 各グループの向き候補を算出（実効幅, 1行幅, 長さ, rotated, 行数）
    # 実効幅 = floor(荷台幅/1行幅) × 1行幅（複数行の場合も考慮）
    group_list = []
    for name, group_slots in groups.items():
        rep = group_slots[0]
        len_a = _to_decimal(rep.get('length'))
        wid_a = _to_decimal(rep.get('width'))
        fp_count = len(group_slots)
        options = []
        for (w, l, rotated) in [(wid_a, len_a, False), (len_a, wid_a, True)]:
            if w > bed_wid or w <= 0 or l <= 0:
                continue
            max_units = int(bed_wid // w)
            if max_units < 1:
                continue
            from math import ceil
            per_row = int(bed_len // l)
            needed = ceil(fp_count / per_row) if per_row > 0 else max_units
            units = min(max_units, needed)
            eff_w = w * units
            options.append((eff_w, w, l, rotated, units))
        if not options:
            options = [(wid_a, wid_a, len_a, False, 1)]
        group_list.append((name, group_slots, options))

    # DPで各グループの向きを決定（実効幅合計≦荷台幅で最大充填）
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

    # DPで選ばれなかったグループにはデフォルト向きを割り当て
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

    # DP選択グループを先に配置（幅帯を共有）、非選択グループは後
    ordered = [gi for gi in range(N) if gi in chosen_groups] + \
              [gi for gi in range(N) if gi not in chosen_groups]

    # DP選択グループ: 帯として長手方向に配置し、使用済みxを記録
    # 複数行（units>1）の場合は複数帯を作成
    bands = []  # [(row_y, band_w, used_x)]
    cur_y = Decimal('0')
    for gi in [g for g in ordered if g in chosen_groups]:
        name, group_slots, options = group_list[gi]
        w, l, rotated = orientation_map[gi]
        units = units_map[gi]
        group_bands = []
        for u in range(units):
            band_y = cur_y + w * u
            group_bands.append((band_y, w, Decimal('0')))
        slot_idx = 0
        for slot in group_slots:
            fitted = False
            for bi in range(len(group_bands)):
                band_y, band_w, band_x = group_bands[bi]
                if band_x + l <= bed_len:
                    placed.append({
                        'product_code': slot.get('product_code', ''),
                        'qty': str(slot.get('qty', Decimal('0'))),
                        'container_name': slot.get('container_name', ''),
                        'layers': slot.get('layers', 1),
                        'x': str(band_x), 'y': str(band_y),
                        'w': str(l), 'd': str(w), 'rotated': rotated,
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
                    'layers': slot.get('layers', 1),
                    'x': str(of_x), 'y': str(of_y),
                    'w': str(l), 'd': str(w), 'rotated': rotated,
                })
                of_x += l
                of_h = max(of_h, w)
                max_x = max(max_x, of_x)
                max_y = max(max_y, of_y + w)
        bands.extend(group_bands)
        cur_y += w * units
        max_y = max(max_y, cur_y)

    # 非選択グループ: DP帯の空きx領域に直接詰める（帯を新設しない）
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
                        'layers': slot.get('layers', 1),
                        'x': str(band_used_x), 'y': str(band_y),
                        'w': str(l), 'd': str(w), 'rotated': rotated,
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
                    'layers': slot.get('layers', 1),
                    'x': str(of_x), 'y': str(of_y),
                    'w': str(l), 'd': str(w), 'rotated': rotated,
                })
                of_x += l
                of_h = max(of_h, w)
                max_x = max(max_x, of_x)
                max_y = max(max_y, of_y + w)
    return {'placed': placed, 'can_fit': can_fit, 'max_x': max_x, 'max_y': max_y}


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


def _pack_score(placed, can_fit, bed_len, bed_wid):
    overflow_count = 0
    overflow_area = Decimal('0')
    max_overflow_y = Decimal('0')
    max_overflow_x = Decimal('0')
    in_bed_sum_x = Decimal('0')
    in_bed_sum_y = Decimal('0')
    for item in placed:
        px = _to_decimal(item['x'])
        py = _to_decimal(item['y'])
        pw = _to_decimal(item['w'])
        pd = _to_decimal(item['d'])
        if px + pw <= bed_len and py + pd <= bed_wid:
            in_bed_sum_x += px
            in_bed_sum_y += py
            continue
        overflow_count += 1
        overflow_area += pw * pd
        max_overflow_x = max(max_overflow_x, px + pw)
        max_overflow_y = max(max_overflow_y, py + pd)
    return (
        0 if can_fit else 1,
        overflow_count,
        overflow_area,
        max_overflow_y,
        max_overflow_x,
        in_bed_sum_x,
        in_bed_sum_y,
    )


def _finalize_pack_result(pack_result, bed_len, bed_wid):
    placed_all = pack_result['placed']
    in_bed, overflow = _split_in_bed_and_overflow(placed_all, bed_len, bed_wid)
    in_bed, overflow = _fill_gaps(in_bed, overflow, bed_len, bed_wid)
    placed = in_bed + overflow
    can_fit = pack_result['can_fit'] and not overflow
    max_x = max((_to_decimal(item['x']) + _to_decimal(item['w']) for item in placed), default=Decimal('0'))
    max_y = max((_to_decimal(item['y']) + _to_decimal(item['d']) for item in placed), default=Decimal('0'))
    return {
        'placed': placed,
        'can_fit': can_fit,
        'max_x': max_x,
        'max_y': max_y,
    }


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



def _pack_slots(bed_len, bed_wid, slots):
    """複数パッカーを試し、overflow が最も少ない結果を採用する。"""
    candidates = []
    seen = set()
    for variant in _sorted_slot_variants(slots):
        packers = (
            _pack_column,
            _pack_guillotine,
            _pack_bay,
            _pack_shelf,
        )
        for packer in packers:
            key = (packer.__name__, tuple(
                (
                    str(slot.get('product_code', '')),
                    str(slot.get('length', '')),
                    str(slot.get('width', '')),
                    bool(slot.get('rotated', False)),
                )
                for slot in variant
            ))
            if key in seen:
                continue
            seen.add(key)
            finalized = _finalize_pack_result(packer(bed_len, bed_wid, variant), bed_len, bed_wid)
            candidates.append(finalized)

    best = min(candidates, key=lambda item: _pack_score(item['placed'], item['can_fit'], bed_len, bed_wid))
    return best['placed'], best['can_fit'], best['max_x'], best['max_y']


def _split_free_rect(rect, box):
    """Maximal Rectangles方式: 配置箱で自由矩形を分割（フル幅/高さ保持）"""
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
    """完全に包含される矩形を除去"""
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


def _fill_gaps(in_bed, overflow, bed_len, bed_wid):
    """
    Maximal Rectangles方式で配置済みの隙間にoverflowの箱を詰める。
    帯を跨ぐ大きな空き領域も保持される。
    """
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
        best = None
        best_score = None
        for idx, (fx, fy, fw, fh) in enumerate(free_rects):
            for (length, width) in ((slot_len, slot_wid), (slot_wid, slot_len)):
                if length <= fw and width <= fh:
                    score = min(fw - length, fh - width)
                    if best_score is None or score < best_score:
                        best_score = score
                        best = (idx, length, width, fx, fy)
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

    # 同じ容器（同一寸法・入数）の割付を合算してから容器数・段数を計算する。
    # 別注番や別製品でも同じ容器なら合算し、段積みで効率よく詰められるようにする。
    group_qty = defaultdict(Decimal)
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
            str(cw), str(cd), str(ch), str(capacity),
            can_mix, stackable, max_stack,
            str(container.get('name') or ''),
        )
        group_qty[key] += qty
        group_meta.setdefault(key, {
            'container': container,
            'cw': cw,
            'cd': cd,
            'ch': ch,
            'capacity': capacity,
            'can_mix': can_mix,
            'stackable': stackable,
            'max_stack': max_stack,
        })
        # グループ内の製品別数量（同じ製品は合算して保持）
        products = group_products.setdefault(key, [])
        merged = False
        for idx, (pcode, pqty) in enumerate(products):
            if pcode == product_code:
                products[idx] = (pcode, pqty + qty)
                merged = True
                break
        if not merged:
            products.append((product_code, qty))

    for key, meta in group_meta.items():
        total_qty = group_qty[key]
        container = meta['container']
        cw = meta['cw']
        cd = meta['cd']
        ch = meta['ch']
        capacity = meta['capacity']
        stackable = meta['stackable']
        max_stack = meta['max_stack']

        container_count = (total_qty / capacity).to_integral_value(rounding=ROUND_CEILING)
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

        group_products_list = group_products.get(key, [])
        container_name = str(container.get('name') or '') or (group_products_list[0][0] if group_products_list else '')
        type_records.append({
            'label': container_name,
            'length': length,
            'width': width,
            'rotated': rotated,
        })

        # フットプリントへの製品割当（同じ容器に複数製品が混在する場合も、ユニットを順に充填）
        product_qty_map = {pcode: Decimal(str(pqty)) for pcode, pqty in group_products_list}
        unit_remaining = dict(product_qty_map)
        units_per_footprint = int(layers) * int(capacity)
        footprint_products = []
        for _ in range(int(floor_slots)):
            first = None
            take = units_per_footprint
            for pcode in list(unit_remaining.keys()):
                if unit_remaining[pcode] <= 0:
                    continue
                if first is None:
                    first = pcode
                used = min(take, unit_remaining[pcode])
                unit_remaining[pcode] -= used
                take -= used
                if take <= 0:
                    break
            footprint_products.append(first or '')
        if not footprint_products and group_products_list:
            footprint_products = [group_products_list[0][0]]

        for pcode in footprint_products:
            slots.append({
                'product_code': pcode,
                'qty': product_qty_map.get(pcode, total_qty),
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
