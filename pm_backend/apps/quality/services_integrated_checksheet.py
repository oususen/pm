"""B案（工程一体チェックシート）PDF生成サービス"""
import io

from PIL import Image, ImageDraw

from .models_integrated_checksheet import (
    IntegratedChecksheetBatch,
    IntegratedChecksheetTemplate,
)
from .integrated_checksheet_assets import _font


# A4横 200dpi 相当
PAGE_W = 2339
PAGE_H = 1654
MARGIN = 60
DPI = 200.0

BLOCK_COLORS = [
    {"banner": (41, 98, 168), "banner_text": (255, 255, 255), "table_head": (210, 225, 245), "accent": (41, 98, 168)},
    {"banner": (46, 133, 80), "banner_text": (255, 255, 255), "table_head": (212, 238, 220), "accent": (46, 133, 80)},
    {"banner": (156, 110, 30), "banner_text": (255, 255, 255), "table_head": (245, 235, 200), "accent": (156, 110, 30)},
    {"banner": (80, 80, 80), "banner_text": (255, 255, 255), "table_head": (225, 225, 225), "accent": (80, 80, 80)},
    {"banner": (30, 130, 150), "banner_text": (255, 255, 255), "table_head": (205, 235, 242), "accent": (30, 130, 150)},
    {"banner": (111, 78, 55), "banner_text": (255, 255, 255), "table_head": (237, 224, 214), "accent": (111, 78, 55)},
    {"banner": (15, 118, 110), "banner_text": (255, 255, 255), "table_head": (214, 243, 239), "accent": (15, 118, 110)},
]


def _color_for_block(index):
    return BLOCK_COLORS[index % len(BLOCK_COLORS)]


def _new_page():
    img = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    return img, ImageDraw.Draw(img)


def _draw_header_page(template):
    """1ページ目: 帳票ヘッダ情報"""
    img, draw = _new_page()
    y = MARGIN

    title = template.document_title or template.name or "工程一体チェックシート"
    font_title = _font(48, bold=True)
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text(((PAGE_W - tw) / 2, y), title, fill="black", font=font_title)
    y += 80

    draw.line((MARGIN, y, PAGE_W - MARGIN, y), fill="#333333", width=3)
    y += 30

    font_label = _font(24, bold=True)
    font_val = _font(24)

    product_code = template.product.product_code if template.product else ""
    product_name = template.product.product_name if template.product else ""
    line_name = template.line.line_name if template.line else "共通"

    rows = [
        ("製品コード", product_code),
        ("製品名", product_name),
        ("ライン", line_name),
        ("版", f"v{template.version}"),
        ("状態", template.get_status_display()),
        ("元シート名", template.sheet_name or ""),
        ("改訂内容", template.revision_notes or ""),
        ("改訂日", str(template.revision_date) if template.revision_date else ""),
        ("運用開始日", str(template.effective_from) if template.effective_from else ""),
    ]

    def _user_display(u):
        if not u:
            return ""
        last = (u.last_name or "").strip()
        first = (u.first_name or "").strip()
        return f"{last} {first}".strip() or str(u)

    reviewer_name = _user_display(template.reviewer_user)
    chief_name = _user_display(template.chief_user)
    approver_name = _user_display(template.approver_user)

    rows.extend([
        ("作成者", _user_display(template.created_by)),
        ("班長担当", reviewer_name),
        ("係長担当", chief_name),
        ("部長担当", approver_name),
    ])

    label_x = MARGIN + 20
    val_x = MARGIN + 260
    for label, value in rows:
        if not value:
            continue
        draw.text((label_x, y), label, fill="#333333", font=font_label)
        draw.text((val_x, y), str(value), fill="black", font=font_val)
        y += 40

    y += 30

    blocks = list(
        template.process_blocks
        .select_related("process")
        .prefetch_related("items")
        .order_by("sort_order")
    )

    draw.text((label_x, y), "工程一覧", fill="black", font=_font(28, bold=True))
    y += 50

    font_proc = _font(22, bold=True)
    font_item = _font(18)
    for idx, block in enumerate(blocks):
        colors = _color_for_block(idx)
        cx = label_x + 20
        draw.ellipse((cx, y + 4, cx + 22, y + 26), fill=colors["banner"])
        draw.text((cx + 30, y), f"{idx + 1}. {block.process.process_name}", fill=colors["accent"], font=font_proc)
        item_count = block.items.count()
        draw.text((cx + 530, y), f"（{item_count}項目）", fill="#666666", font=font_item)
        y += 36
        if y > PAGE_H - MARGIN - 50:
            break

    return img


def _wrap_text(draw, text, font, max_w):
    if not text:
        return []
    lines = []
    for raw_line in text.split("\n"):
        if not raw_line:
            lines.append("")
            continue
        bbox = draw.textbbox((0, 0), raw_line, font=font)
        if bbox[2] - bbox[0] <= max_w:
            lines.append(raw_line)
            continue
        current = ""
        for ch in raw_line:
            test = current + ch
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_w:
                if current:
                    lines.append(current)
                current = ch
            else:
                current = test
        if current:
            lines.append(current)
    return lines or [""]


def _draw_item_table_header(draw, y, col_defs, total_w, row_h, colors):
    """項目テーブルのヘッダ行を描画"""
    table_x = MARGIN
    cx = table_x
    draw.rectangle((cx, y, cx + total_w, y + row_h), fill=colors["table_head"])
    for col_name, col_w in col_defs:
        draw.rectangle((cx, y, cx + col_w, y + row_h), outline="#999999")
        draw.text((cx + 4, y + 5), col_name, fill=colors["accent"], font=_font(16, bold=True))
        cx += col_w
    return y + row_h


def _calc_row_height(draw, values, col_defs, font, base_h, line_h):
    max_lines = 1
    for (_, col_w), val in zip(col_defs, values):
        wrapped = _wrap_text(draw, val, font, col_w - 8)
        if len(wrapped) > max_lines:
            max_lines = len(wrapped)
    return max(base_h, 12 + line_h * max_lines)


def _draw_item_rows(draw, y, items, start_idx, col_defs, total_w, row_h, bottom, record_type_labels):
    """項目行を描画し、描画した行数を返す"""
    table_x = MARGIN
    font_td = _font(14)
    line_h = 20
    drawn = 0
    for i, item in enumerate(items):
        if y + row_h > bottom:
            break
        idx = start_idx + i
        values = [
            str(idx + 1),
            item.item_name or "",
            item.standard or "",
            item.frequency or "",
            item.method or "",
            record_type_labels.get(item.record_type, item.record_type),
            item.unit or "",
            item.criteria or "",
            "●" if item.is_required else "",
        ]
        actual_h = _calc_row_height(draw, values, col_defs, font_td, row_h, line_h)
        if y + actual_h > bottom:
            break
        bg_fill = "#f8f8f8" if idx % 2 == 0 else "white"
        cx = table_x
        draw.rectangle((cx, y, cx + total_w, y + actual_h), fill=bg_fill)
        for (col_name, col_w), val in zip(col_defs, values):
            draw.rectangle((cx, y, cx + col_w, y + actual_h), outline="#cccccc")
            wrapped = _wrap_text(draw, val, font_td, col_w - 8)
            ty = y + 6
            for wl in wrapped:
                draw.text((cx + 4, ty), wl, fill="black", font=font_td)
                ty += line_h
            cx += col_w
        y += actual_h
        drawn += 1
    return drawn


def _make_col_defs():
    available_w = PAGE_W - MARGIN * 2
    col_defs = [
        ("No", 50),
        ("点検項目", 500),
        ("規格", 380),
        ("頻度", 100),
        ("方法", 380),
        ("記録種別", 90),
        ("単位", 70),
        ("判定基準", 380),
        ("必須", 50),
    ]
    total_w = sum(c[1] for c in col_defs)
    if total_w != available_w:
        scale_factor = available_w / total_w
        col_defs = [(name, int(w * scale_factor)) for name, w in col_defs]
        total_w = sum(c[1] for c in col_defs)
        diff = available_w - total_w
        if diff != 0:
            col_defs[1] = (col_defs[1][0], col_defs[1][1] + diff)
            total_w = sum(c[1] for c in col_defs)
    return col_defs, total_w


def _draw_continuation_banner(draw, block_index, total_blocks, process_name, product_code, page_num, colors):
    """続きページ用の小さめバナー"""
    banner_h = 44
    draw.rectangle((0, 0, PAGE_W, banner_h), fill=colors["banner"])
    side_bar_w = 8
    draw.rectangle((0, banner_h, side_bar_w, PAGE_H), fill=colors["banner"])
    draw.rectangle((PAGE_W - side_bar_w, banner_h, PAGE_W, PAGE_H), fill=colors["banner"])
    title_text = f"工程 {block_index + 1}/{total_blocks}: {process_name}    [{product_code}]  (続き {page_num})"
    font_title = _font(26, bold=True)
    bbox = draw.textbbox((0, 0), title_text, font=font_title)
    ty = (banner_h - (bbox[3] - bbox[1])) // 2
    draw.text((MARGIN, ty), title_text, fill=colors["banner_text"], font=font_title)
    return banner_h


def _draw_process_pages(template, block, block_index, total_blocks):
    """工程ブロックのページ群を生成（項目が多い場合は複数ページ）"""
    colors = _color_for_block(block_index)
    img, draw = _new_page()

    banner_h = 64
    draw.rectangle((0, 0, PAGE_W, banner_h), fill=colors["banner"])

    side_bar_w = 8
    draw.rectangle((0, banner_h, side_bar_w, PAGE_H), fill=colors["banner"])
    draw.rectangle((PAGE_W - side_bar_w, banner_h, PAGE_W, PAGE_H), fill=colors["banner"])

    product_code = template.product.product_code if template.product else ""
    title_text = f"工程 {block_index + 1}/{total_blocks}: {block.process.process_name}    [{product_code}]"
    font_title = _font(32, bold=True)
    bbox = draw.textbbox((0, 0), title_text, font=font_title)
    ty = (banner_h - (bbox[3] - bbox[1])) // 2
    draw.text((MARGIN, ty), title_text, fill=colors["banner_text"], font=font_title)

    y = banner_h + 16

    items = list(block.items.order_by("sort_order", "id"))
    has_sketch = bool(block.sketch_image)
    has_items = bool(items)

    content_bottom = PAGE_H - MARGIN
    content_h = max(content_bottom - y, 200)
    gap_between = 20
    row_h = 30
    MIN_SKETCH_H = 200

    if has_sketch and has_items:
        usable_h = max(content_h - gap_between, 120)
        required_table_h = (len(items) + 1) * row_h + 10
        default_sketch_h = int(usable_h * 4 / 5)
        if usable_h - default_sketch_h < required_table_h:
            sketch_area_h = max(usable_h - required_table_h, MIN_SKETCH_H)
        else:
            sketch_area_h = default_sketch_h
        table_area_h = usable_h - sketch_area_h
    elif has_sketch:
        sketch_area_h = max(content_h - 10, 120)
        table_area_h = 0
    else:
        sketch_area_h = 0
        table_area_h = max(content_h - 10, 120)

    if has_sketch:
        sketch_area_w = PAGE_W - MARGIN * 2

        try:
            bg = Image.open(block.sketch_image.path).convert("RGBA")
            scale = min(sketch_area_w / bg.width, sketch_area_h / bg.height)
            new_w = int(bg.width * scale)
            new_h = int(bg.height * scale)
            bg_resized = bg.resize((new_w, new_h), Image.LANCZOS)
            offset_x = MARGIN + (sketch_area_w - new_w) // 2
            offset_y = y + max((sketch_area_h - new_h) // 2, 0)

            bg_rgb = Image.new("RGB", bg_resized.size, "white")
            bg_rgb.paste(bg_resized, mask=bg_resized.split()[3] if bg_resized.mode == "RGBA" else None)
            img.paste(bg_rgb, (offset_x, offset_y))

            y += sketch_area_h + gap_between
        except Exception:
            draw.text((MARGIN + 20, y), "（台紙画像の読み込みに失敗）", fill="red", font=_font(18))
            y += 40 + (sketch_area_h if sketch_area_h > 40 else 0)
    elif not has_sketch and not has_items:
        pass

    pages = [img]

    if items:
        y += 10
        table_top = y
        table_bottom = content_bottom if table_area_h <= 0 else min(content_bottom, table_top + table_area_h)

        col_defs, total_w = _make_col_defs()
        record_type_labels = {
            "CHECK": "チェック",
            "NUMERIC": "数値",
            "PHOTO_NUMERIC": "写真＋数値",
            "PHOTO": "写真のみ",
            "TEXT": "文字",
        }

        y = _draw_item_table_header(draw, y, col_defs, total_w, row_h, colors)
        drawn = _draw_item_rows(draw, y, items, 0, col_defs, total_w, row_h, table_bottom, record_type_labels)
        remaining = items[drawn:]
        item_offset = drawn

        cont_page_num = 2
        while remaining:
            cont_img, cont_draw = _new_page()
            bh = _draw_continuation_banner(
                cont_draw, block_index, total_blocks,
                block.process.process_name, product_code, cont_page_num, colors,
            )
            cy = bh + 16
            cy = _draw_item_table_header(cont_draw, cy, col_defs, total_w, row_h, colors)
            d = _draw_item_rows(
                cont_draw, cy, remaining, item_offset,
                col_defs, total_w, row_h, PAGE_H - MARGIN, record_type_labels,
            )
            pages.append(cont_img)
            remaining = remaining[d:]
            item_offset += d
            cont_page_num += 1
            if d == 0:
                break

    return pages


def generate_integrated_template_pdf(template):
    """B案テンプレートのプレビューPDFを生成（複数ページ）。
    1ページ目: ヘッダ情報
    2ページ目以降: 工程ブロックごとに1ページ
    """
    blocks = list(
        template.process_blocks
        .select_related("process")
        .prefetch_related("items", "sketch_fields")
        .order_by("sort_order")
    )

    pages = []

    header_page = _draw_header_page(template)
    pages.append(header_page)

    for idx, block in enumerate(blocks):
        proc_pages = _draw_process_pages(template, block, idx, len(blocks))
        pages.extend(proc_pages)

    if not pages:
        return None

    output = io.BytesIO()
    first = pages[0]
    if len(pages) > 1:
        first.save(
            output, format="PDF", resolution=DPI,
            save_all=True, append_images=pages[1:],
        )
    else:
        first.save(output, format="PDF", resolution=DPI)
    output.seek(0)
    return output


def _user_display(u):
    if not u:
        return ""
    last = (u.last_name or "").strip()
    first = (u.first_name or "").strip()
    return f"{last} {first}".strip() or str(u)


def _pages_to_pdf(pages):
    if not pages:
        return None
    output = io.BytesIO()
    first = pages[0]
    if len(pages) > 1:
        first.save(output, format="PDF", resolution=DPI, save_all=True, append_images=pages[1:])
    else:
        first.save(output, format="PDF", resolution=DPI)
    output.seek(0)
    return output


def generate_integrated_batch_pdf(batch: IntegratedChecksheetBatch):
    """バッチの実績入りPDFを生成。工程ブロックごとに台目×項目のマトリクス表を出力。"""
    template = batch.template
    blocks = list(
        template.process_blocks
        .select_related("process")
        .prefetch_related("items")
        .order_by("sort_order")
    )
    units = list(batch.units.prefetch_related("checks__item").order_by("sequence_no"))
    if not blocks or not units:
        return None

    check_map = {}
    for unit in units:
        for check in unit.checks.all():
            check_map[(unit.id, check.item_id)] = check

    pages = []

    pages.append(_draw_batch_header_page(batch, template, units, blocks))

    for block_idx, block in enumerate(blocks):
        block_pages = _draw_batch_process_pages(batch, template, block, block_idx, len(blocks), units, check_map)
        pages.extend(block_pages)

    return _pages_to_pdf(pages)


def _draw_batch_header_page(batch, template, units, blocks):
    img, draw = _new_page()
    y = MARGIN

    title = template.document_title or template.name or "工程一体チェックシート"
    font_title = _font(44, bold=True)
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text(((PAGE_W - tw) / 2, y), title, fill="black", font=font_title)
    y += 72

    draw.line((MARGIN, y, PAGE_W - MARGIN, y), fill="#333333", width=3)
    y += 24

    font_label = _font(22, bold=True)
    font_val = _font(22)
    label_x = MARGIN + 20
    val_x = MARGIN + 240

    product_code = template.product.product_code if template.product else ""
    product_name = template.product.product_name if template.product else ""
    line_name = batch.line.line_name if batch.line else ""

    rows = [
        ("製品コード", product_code),
        ("製品名", product_name),
        ("ライン", line_name),
        ("計画日", str(batch.plan_date) if batch.plan_date else ""),
        ("ロットNo", batch.lot_no or ""),
        ("台数", str(batch.quantity)),
        ("版", f"v{template.version}"),
    ]

    if batch.leader_confirmed_by:
        rows.append(("リーダ確認", f"{_user_display(batch.leader_confirmed_by)}  {batch.leader_confirmed_at.strftime('%Y-%m-%d %H:%M') if batch.leader_confirmed_at else ''}"))
    if batch.supervisor_confirmed_by:
        rows.append(("班長確認", f"{_user_display(batch.supervisor_confirmed_by)}  {batch.supervisor_confirmed_at.strftime('%Y-%m-%d %H:%M') if batch.supervisor_confirmed_at else ''}"))

    for label, value in rows:
        if not value:
            continue
        draw.text((label_x, y), label, fill="#333333", font=font_label)
        draw.text((val_x, y), str(value), fill="black", font=font_val)
        y += 36

    y += 24
    draw.text((label_x, y), "工程一覧", fill="black", font=_font(26, bold=True))
    y += 44

    font_proc = _font(20, bold=True)
    for idx, block in enumerate(blocks):
        colors = _color_for_block(idx)
        cx = label_x + 20
        draw.ellipse((cx, y + 4, cx + 20, y + 24), fill=colors["banner"])
        item_count = block.items.count()
        draw.text((cx + 28, y), f"{idx + 1}. {block.process.process_name}（{item_count}項目）", fill=colors["accent"], font=font_proc)
        y += 32
        if y > PAGE_H - MARGIN - 40:
            break

    return img


def _draw_batch_process_pages(batch, template, block, block_index, total_blocks, units, check_map):
    """工程ブロックごとに台目×項目の実績マトリクスを描画。"""
    colors = _color_for_block(block_index)
    items = list(block.items.order_by("sort_order", "id"))
    if not items:
        return []

    product_code = template.product.product_code if template.product else ""
    process_name = block.process.process_name

    max_units_per_page = 20
    all_pages = []
    unit_offset = 0

    while unit_offset < len(units):
        page_units = units[unit_offset:unit_offset + max_units_per_page]
        item_offset = 0

        page_num = 0
        while item_offset < len(items):
            img, draw = _new_page()

            banner_h = 72
            draw.rectangle((0, 0, PAGE_W, banner_h), fill=colors["banner"])
            unit_range = f"台目 {unit_offset + 1}-{unit_offset + len(page_units)}"
            title_text = f"工程 {block_index + 1}/{total_blocks}: {process_name}  [{product_code}]  {unit_range}"
            if page_num > 0:
                title_text += f"  (続き {page_num + 1})"
            font_title = _font(36, bold=True)
            bbox = draw.textbbox((0, 0), title_text, font=font_title)
            ty = (banner_h - (bbox[3] - bbox[1])) // 2
            draw.text((MARGIN, ty), title_text, fill=colors["banner_text"], font=font_title)

            y = banner_h + 12

            available_w = PAGE_W - MARGIN * 2
            unit_col_w = 90
            item_col_w = available_w - unit_col_w * len(page_units)
            row_h = 44
            font_th = _font(28, bold=True)
            font_td = _font(26)
            line_h = 34

            hdr_x = MARGIN
            draw.rectangle((hdr_x, y, hdr_x + item_col_w, y + row_h), fill=colors["table_head"], outline="#999999")
            draw.text((hdr_x + 4, y + 5), "点検項目", fill=colors["accent"], font=font_th)
            hdr_x += item_col_w
            for u in page_units:
                draw.rectangle((hdr_x, y, hdr_x + unit_col_w, y + row_h), fill=colors["table_head"], outline="#999999")
                label = f"#{u.sequence_no}"
                draw.text((hdr_x + 4, y + 5), label, fill=colors["accent"], font=font_th)
                hdr_x += unit_col_w
            y += row_h

            bottom = PAGE_H - MARGIN
            drawn = 0
            for item in items[item_offset:]:
                name = item.item_name or ""
                wrapped = _wrap_text(draw, name, font_td, item_col_w - 8)
                actual_h = max(row_h, 8 + line_h * len(wrapped))
                if y + actual_h > bottom:
                    break
                bg = "#f8f8f8" if drawn % 2 == 0 else "white"
                cx = MARGIN
                draw.rectangle((cx, y, cx + item_col_w, y + actual_h), fill=bg, outline="#cccccc")
                ty = y + 5
                for wl in wrapped:
                    draw.text((cx + 4, ty), wl, fill="black", font=font_td)
                    ty += line_h
                cx += item_col_w

                for u in page_units:
                    draw.rectangle((cx, y, cx + unit_col_w, y + actual_h), fill=bg, outline="#cccccc")
                    chk = check_map.get((u.id, item.id))
                    if chk:
                        val = ""
                        if chk.judgement:
                            val = chk.judgement
                        elif chk.numeric_value is not None:
                            val = str(chk.numeric_value).rstrip("0").rstrip(".")
                        elif chk.text_value:
                            val = chk.text_value[:6]
                        elif chk.photo_url:
                            val = "[写真]"
                        color = "black"
                        if chk.judgement == "OK":
                            color = "#1a7a3a"
                        elif chk.judgement == "NG":
                            color = "#cc2222"
                        draw.text((cx + 4, y + 5), val, fill=color, font=font_td)
                    cx += unit_col_w

                y += actual_h
                drawn += 1

            all_pages.append(img)
            item_offset += drawn
            page_num += 1
            if drawn == 0:
                break

        unit_offset += max_units_per_page

    return all_pages
