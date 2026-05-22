"""B案（工程一体チェックシート）PDF生成サービス"""
import io

from PIL import Image, ImageDraw

from .models_integrated_checksheet import IntegratedChecksheetTemplate
from .services_checksheet import _font


# A4横 200dpi 相当
PAGE_W = 2339
PAGE_H = 1654
MARGIN = 60
DPI = 200.0

BLOCK_COLORS = [
    {"banner": (41, 98, 168), "banner_text": (255, 255, 255), "table_head": (210, 225, 245), "accent": (41, 98, 168)},
    {"banner": (168, 56, 50), "banner_text": (255, 255, 255), "table_head": (245, 215, 213), "accent": (168, 56, 50)},
    {"banner": (46, 133, 80), "banner_text": (255, 255, 255), "table_head": (212, 238, 220), "accent": (46, 133, 80)},
    {"banner": (156, 110, 30), "banner_text": (255, 255, 255), "table_head": (245, 235, 200), "accent": (156, 110, 30)},
    {"banner": (106, 58, 148), "banner_text": (255, 255, 255), "table_head": (230, 218, 240), "accent": (106, 58, 148)},
    {"banner": (30, 130, 150), "banner_text": (255, 255, 255), "table_head": (205, 235, 242), "accent": (30, 130, 150)},
    {"banner": (180, 90, 40), "banner_text": (255, 255, 255), "table_head": (245, 225, 210), "accent": (180, 90, 40)},
    {"banner": (80, 80, 80), "banner_text": (255, 255, 255), "table_head": (225, 225, 225), "accent": (80, 80, 80)},
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


def _draw_process_page(template, block, block_index, total_blocks):
    """工程ブロック1ページ: 色付きヘッダ帯 + 台紙背景 + フィールド枠 + チェック項目テーブル"""
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
    sketch_fields = list(block.sketch_fields.order_by("sort_order", "id"))
    has_sketch = bool(block.sketch_image)
    has_items = bool(items)

    # 工程ページ内の縦レイアウト比率:
    # 台紙:項目 = 4:1（両方ある場合）
    content_bottom = PAGE_H - MARGIN
    content_h = max(content_bottom - y, 200)
    gap_between = 20
    if has_sketch and has_items:
        usable_h = max(content_h - gap_between, 120)
        sketch_area_h = int(usable_h * 4 / 5)
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
            # 3:2比率で確保した台紙エリア内に上下中央寄せ
            offset_y = y + max((sketch_area_h - new_h) // 2, 0)

            bg_rgb = Image.new("RGB", bg_resized.size, "white")
            bg_rgb.paste(bg_resized, mask=bg_resized.split()[3] if bg_resized.mode == "RGBA" else None)
            img.paste(bg_rgb, (offset_x, offset_y))

            overlay = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            for sf in sketch_fields:
                fx = int(sf.x * scale)
                fy = int(sf.y * scale)
                fw = int(sf.width * scale)
                fh = int(sf.height * scale)
                od.rectangle((fx, fy, fx + fw, fy + fh), outline=(30, 64, 175, 140), width=2)
                od.rectangle((fx + 1, fy + 1, fx + fw - 1, fy + fh - 1), fill=(230, 240, 255, 80))
                if sf.label:
                    fsz = max(min(fh - 4, 16), 8)
                    ff = _font(int(fsz * scale) if scale > 0.5 else fsz)
                    od.text((fx + 3, fy + 2), sf.label, fill=(30, 64, 175, 200), font=ff)

            overlay_rgb = overlay.convert("RGB")
            mask = overlay.split()[3]
            img.paste(overlay_rgb, (offset_x, offset_y), mask)

            y += sketch_area_h + gap_between
        except Exception:
            draw.text((MARGIN + 20, y), "（台紙画像の読み込みに失敗）", fill="red", font=_font(18))
            y += 40 + (sketch_area_h if sketch_area_h > 40 else 0)
    elif sketch_fields:
        draw.text((MARGIN + 20, y), "（台紙画像未設定 — フィールド定義あり）", fill="#888888", font=_font(16))
        y += 30

    if items:
        y += 10
        table_top = y
        table_bottom = content_bottom if table_area_h <= 0 else min(content_bottom, table_top + table_area_h)
        font_th = _font(16, bold=True)
        font_td = _font(14)
        row_h = 30

        col_defs = [
            ("No", 50),
            ("点検項目", 360),
            ("規格", 260),
            ("頻度", 100),
            ("方法", 260),
            ("記録種別", 90),
            ("単位", 70),
            ("判定基準", 260),
            ("必須", 50),
        ]

        total_w = sum(c[1] for c in col_defs)
        table_x = MARGIN
        if total_w + MARGIN * 2 > PAGE_W:
            scale_factor = (PAGE_W - MARGIN * 2) / total_w
            col_defs = [(name, int(w * scale_factor)) for name, w in col_defs]
            total_w = sum(c[1] for c in col_defs)

        cx = table_x
        draw.rectangle((cx, y, cx + total_w, y + row_h), fill=colors["table_head"])
        for col_name, col_w in col_defs:
            draw.rectangle((cx, y, cx + col_w, y + row_h), outline="#999999")
            draw.text((cx + 4, y + 5), col_name, fill=colors["accent"], font=font_th)
            cx += col_w
        y += row_h

        record_type_labels = {
            "CHECK": "チェック",
            "NUMERIC": "数値",
            "PHOTO_NUMERIC": "写真＋数値",
            "PHOTO": "写真のみ",
            "TEXT": "文字",
        }

        for idx, item in enumerate(items):
            if y + row_h > table_bottom:
                draw.text((table_x, y + 4), "... 以下省略 ...", fill="#888888", font=font_td)
                break
            cx = table_x
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
            bg_fill = "#f8f8f8" if idx % 2 == 0 else "white"
            draw.rectangle((cx, y, cx + total_w, y + row_h), fill=bg_fill)
            for (col_name, col_w), val in zip(col_defs, values):
                draw.rectangle((cx, y, cx + col_w, y + row_h), outline="#cccccc")
                text = val[:int(col_w / 8)] if len(val) > col_w / 8 else val
                draw.text((cx + 4, y + 6), text, fill="black", font=font_td)
                cx += col_w
            y += row_h

    return img


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
        proc_page = _draw_process_page(template, block, idx, len(blocks))
        pages.append(proc_page)

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
