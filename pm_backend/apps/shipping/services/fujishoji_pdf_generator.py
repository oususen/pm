# -*- coding: utf-8 -*-
"""
富士商事向け出荷指示書 PDF（A4縦向き）

レイアウト:
  ┌──────────────────────────────────────────┐
  │ 富士商事様向け 出荷指示書      │確認│作成│
  │ 2026/02/20（金）                          │
  ├──────────┬──────────────────────────────────┤
  │凡例[1-5] │ 凡例[A-F]                       │
  ├─────────────────────────────────────────────┤
  │①8:00便                                      │
  │ col1 col2 col3 col4 col5 col6 col7         │
  │ row1 / row2                                 │
  ├─────────────────────────────────────────────┤
  │②8:00便                                      │
  │ col1 col2 col3 col4 col5 col6 col7         │
  │ row1 / row2                                 │
  ├──────────────────────┬──────────────────────┤
  │③追加_日商便           │④追加便              │
  │ [  ][  ]             │ [  ][  ]             │
  │ [  ][  ]             │ [  ][  ]             │
  └──────────────────────┴──────────────────────┘
  合計 XX台車（2個入り×14台車/便×2便）

グリッド埋め順: 列優先（列内で上→下、次の列へ）
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .shipping_pdf_generator import register_japanese_fonts, format_japanese_date

# ─────────────────────────────────────────────
# 定数
# ─────────────────────────────────────────────
FLOOR_PRODUCT_MAPPING = [
    {"product_code": "YD40006245", "number": "1", "label": "U-5 CAB",       "color": "#FFB6C1"},
    {"product_code": "YD40006630", "number": "2", "label": "U-5 CANOPY",    "color": "#87CEEB"},
    {"product_code": "YD40006237", "number": "3", "label": "55UR CAB",      "color": "#90EE90"},
    {"product_code": "YD40006618", "number": "4", "label": "55UR CANOPY",   "color": "#FFD700"},
    {"product_code": "YD40002946", "number": "5", "label": "30/40UR",       "color": "#FFA500"},
    {"product_code": "YD40006842", "number": "A", "label": "5t-EN CAB",     "color": "#CD853F"},
    {"product_code": "YD40007003", "number": "B", "label": "3t-EN CAB",     "color": "#D3D3D3"},
    {"product_code": "YD40007243", "number": "C", "label": "U-5NA CAB",     "color": "#4682B4"},
    {"product_code": "YD40007372", "number": "D", "label": "U-5NA CANOPY",  "color": "#2F4F4F"},
    {"product_code": "YD40007722", "number": "E", "label": "U-6EN 5tKTEG", "color": "#FF6347"},
    {"product_code": "YD40007688", "number": "F", "label": "55US-6 KTEG",   "color": "#9370DB"},
]

ITEMS_PER_CART = 2
CARTS_PER_TRIP = 14
COLS = 7   # 列数/便
ROWS = 2   # 行数/便
SIGN_AREA_WIDTH = 14 * mm
SIGN_AREA_GAP = 2
SIGN_BOX_SIZE = 11 * mm

LEGEND_LEFT  = [p for p in FLOOR_PRODUCT_MAPPING if p["number"] in ("1","2","3","4","5")]
LEGEND_RIGHT = [p for p in FLOOR_PRODUCT_MAPPING if p["number"] in ("A","B","C","D","E","F")]


# ─────────────────────────────────────────────
# カラーヘルパー
# ─────────────────────────────────────────────
def _hex(h: str) -> colors.Color:
    return colors.HexColor(h)


def _is_light(hex_str: str) -> bool:
    c = hex_str.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return (r * 299 + g * 587 + b * 114) / 1000 > 140


# ─────────────────────────────────────────────
# セルテキスト生成
# ─────────────────────────────────────────────
def _cell_lines(label: str, qty_in_cart: int) -> List[str]:
    """
    俗称 → [種別, モデル+数量記号] の2要素リストを返す。
    例: "U-5 CAB", qty=2  → ["キャブ", "U-5②"]
        "30/40UR",  qty=1  → ["30/40UR", "×1"]
    """
    sym = "②" if qty_in_cart == 2 else f"×{qty_in_cart}"
    s = label.strip()
    if s.endswith(" CAB"):
        return ["キャブ",  f"{s[:-4].strip()}{sym}"]
    if s.endswith(" CANOPY"):
        return ["キャノピ", f"{s[:-7].strip()}{sym}"]
    if s.endswith(" KTEG"):
        parts = s.rsplit(" ", 1)
        return [parts[-1], f"{parts[0]}{sym}"] if len(parts) == 2 else [s, sym]
    parts = s.split(" ", 1)
    return [parts[0], f"{parts[1]}{sym}"] if len(parts) == 2 else [s, sym]


# ─────────────────────────────────────────────
# セル描画
# ─────────────────────────────────────────────
def _draw_cell(c: canvas.Canvas, cart: Optional[Dict],
               cx: float, cy_bottom: float, cw: float, ch: float):
    """台車セル1つを描画（cart=None なら空セル）"""
    if cart:
        c.setFillColor(_hex(cart["color"]))
        c.setStrokeColor(_hex("#555555"))
        c.setLineWidth(0.8)
        c.rect(cx, cy_bottom, cw, ch, stroke=1, fill=1)

        tc = colors.black if _is_light(cart["color"]) else colors.white
        c.setFillColor(tc)

        # [番号] - 上部
        c.setFont("MSGothic-Bold", 10)
        c.drawCentredString(cx + cw / 2, cy_bottom + ch - 13, f"[{cart['number']}]")

        # 種別・モデル - 中央
        lines = _cell_lines(cart["label"], cart["qty_in_cart"])
        c.setFont("MSGothic-Bold", 12)
        c.drawCentredString(cx + cw / 2, cy_bottom + ch / 2 + 3, lines[0])
        c.setFont("MSGothic", 10)
        c.drawCentredString(cx + cw / 2, cy_bottom + ch / 2 - 12, lines[1])
    else:
        # 空セル
        c.setFillColor(_hex("#f2f2f2"))
        c.setStrokeColor(_hex("#cccccc"))
        c.setLineWidth(0.4)
        c.rect(cx, cy_bottom, cw, ch, stroke=1, fill=1)


def _draw_driver_sign_area(
    c: canvas.Canvas,
    x: float,
    y_top: float,
    area_h: float,
    area_w: float,
):
    """右側のサイン枠（四角のみ）を描画する。"""
    c.setStrokeColor(colors.black)
    sign_box = min(SIGN_BOX_SIZE, area_w)
    box_x = x + (area_w - sign_box) / 2
    box_y = y_top - area_h / 2 - sign_box / 2
    c.setLineWidth(0.8)
    c.rect(box_x, box_y, sign_box, sign_box, stroke=1, fill=0)


# ─────────────────────────────────────────────
# 便セクション描画（①②便）
# ─────────────────────────────────────────────
def _draw_trip(c: canvas.Canvas, label: str, carts: List[Dict],
               x: float, y_top: float,
               cell_w: float, cell_h: float, gap: float,
               sign_w: float = SIGN_AREA_WIDTH, sign_gap: float = SIGN_AREA_GAP,
               label_h: float = 7 * mm, label_box_w: float = 28 * mm) -> float:
    """
    ラベルボックス（上行）+ 7列×2行グリッド（下）を描画。
    グリッドは列優先埋め: cart[i] → col = i//ROWS, row = i%ROWS
    Returns: 描画後のY下端
    """
    # ── ラベルボックス（グリッドの上、独立した行）──
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.8)
    c.rect(x, y_top - label_h, label_box_w, label_h, stroke=1, fill=1)
    c.setFillColor(colors.black)
    c.setFont("MSGothic-Bold", 11)
    c.drawString(x + 2 * mm, y_top - label_h + 2 * mm, label)

    # ── グリッドセル（ラベルの下、列優先）──
    grid_y_top = y_top - label_h - gap
    grid_h     = ROWS * cell_h + (ROWS - 1) * gap
    grid_w     = COLS * cell_w + (COLS - 1) * gap

    for i in range(CARTS_PER_TRIP):
        col = i // ROWS
        row = i % ROWS
        cx        = x + col * (cell_w + gap)
        cy_bottom = grid_y_top - (row + 1) * cell_h - row * gap
        cart = carts[i] if i < len(carts) else None
        _draw_cell(c, cart, cx, cy_bottom, cell_w, cell_h)

    _draw_driver_sign_area(c, x + grid_w + sign_gap, grid_y_top, grid_h, sign_w)

    return grid_y_top - grid_h


# ─────────────────────────────────────────────
# 追加便セクション描画（③④便）
# ─────────────────────────────────────────────
def _draw_extra(c: canvas.Canvas, label: str,
                x: float, y_top: float,
                cell_w: float, cell_h: float, gap: float,
                n_cols: int = 2, n_rows: int = 2,
                sign_w: float = SIGN_AREA_WIDTH, sign_gap: float = SIGN_AREA_GAP,
                label_h: float = 7 * mm, label_box_w: float = 28 * mm) -> float:
    """
    追加便セクション（空グリッド）を描画。ラベルはグリッドの上行。
    Returns: 描画後のY下端
    """
    # ── ラベルボックス（上行）──
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.8)
    c.rect(x, y_top - label_h, label_box_w, label_h, stroke=1, fill=1)
    c.setFillColor(colors.black)
    c.setFont("MSGothic-Bold", 10)
    c.drawString(x + 2 * mm, y_top - label_h + 1.5 * mm, label)

    # ── 空セル（列優先）──
    grid_y_top = y_top - label_h - gap
    grid_h     = n_rows * cell_h + (n_rows - 1) * gap
    grid_w     = n_cols * cell_w + (n_cols - 1) * gap

    for i in range(n_cols * n_rows):
        col = i // n_rows
        row = i % n_rows
        cx        = x + col * (cell_w + gap)
        cy_bottom = grid_y_top - (row + 1) * cell_h - row * gap
        _draw_cell(c, None, cx, cy_bottom, cell_w, cell_h)

    _draw_driver_sign_area(c, x + grid_w + sign_gap, grid_y_top, grid_h, sign_w)

    return grid_y_top - grid_h


# ─────────────────────────────────────────────
# メイン生成関数
# ─────────────────────────────────────────────
def generate_fujishoji_pdf(
    doc_data: Dict[str, Any],
    output_path: str,
    creator_name: str = "システム",
) -> str:
    """富士商事出荷指示書 PDF（A4縦）を生成する。"""
    register_japanese_fonts()

    W, H = A4          # 595.28 × 841.89 pt（縦）
    MG   = 22          # 左右マージン（pt）
    cw   = W - 2 * MG  # コンテンツ幅 ≈ 551pt
    gap  = 2           # セル間隔（pt）

    # ①②便グリッド寸法
    sign_w = SIGN_AREA_WIDTH
    sign_gap = SIGN_AREA_GAP
    cell_w = (cw - sign_w - sign_gap - gap * (COLS - 1)) / COLS
    cell_h = 26 * mm                # セル高さ ≈ 74pt

    # ③④便グリッド寸法
    extra_half_w  = (cw - 8) / 2   # 各セクション幅
    extra_cell_w  = (extra_half_w - sign_w - sign_gap - gap) / 2
    extra_cell_h  = 20 * mm        # セル高さ ≈ 57pt

    legend_rh = 4.2 * mm            # 凡例行高さ

    # ── データ準備 ──
    trip1           = doc_data.get("trip1", [])
    trip2           = doc_data.get("trip2", [])
    target_date_str = doc_data.get("date")
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date() if target_date_str else None
    except ValueError:
        target_date = None
    date_text = format_japanese_date(target_date) if target_date else "未設定"

    # ── PDF 描画開始 ──
    c = canvas.Canvas(output_path, pagesize=A4)
    c.setTitle("富士商事出荷指示書")

    y = H - 7 * mm   # 描画開始Y（上から）

    # ════════════════════════════════════════
    # 1. タイトル行
    # ════════════════════════════════════════
    title_text = "富士商事様向け　出荷指示書"
    c.setFont("MSGothic-Bold", 13)
    c.setFillColor(colors.black)
    c.drawString(MG, y - 5 * mm, title_text)

    # 確認/作成ボックス（右上）
    bw, bh = 24 * mm, 14 * mm
    bx = W - MG - bw
    by = y  # ボックス上端

    # タイトル下ライン（タイトル幅に合わせて短くする）
    underline_end = min(
        MG + c.stringWidth(title_text, "MSGothic-Bold", 13) + 2 * mm,
        bx - 3 * mm,
    )
    c.setLineWidth(0.8)
    c.setStrokeColor(colors.black)
    c.line(MG, y - 7 * mm, underline_end, y - 7 * mm)

    # 確認/作成ボックス
    c.setFillColor(colors.white)
    c.rect(bx, by - bh, bw, bh, stroke=1, fill=1)
    header_h = bh * 0.45
    c.line(bx, by - header_h, bx + bw, by - header_h)
    c.line(bx + bw / 2, by, bx + bw / 2, by - bh)
    c.setFont("MSGothic-Bold", 7)
    c.setFillColor(colors.black)
    c.drawCentredString(bx + bw / 4, by - header_h + 1.2 * mm, "確認")
    c.drawCentredString(bx + 3 * bw / 4, by - header_h + 1.2 * mm, "作成")

    c.setFont("MSGothic-Bold", 7.5)
    c.drawCentredString(
        bx + 3 * bw / 4,
        by - header_h - (bh - header_h) / 2 + 0.8 * mm,
        creator_name or "システム",
    )

    y -= 9 * mm

    # ════════════════════════════════════════
    # 2. 日付（大）
    # ════════════════════════════════════════
    c.setFont("MSGothic-Bold", 18)
    c.setFillColor(colors.black)
    c.drawString(MG, y - 7 * mm, date_text)
    y -= 11 * mm

    # ════════════════════════════════════════
    # 3. 凡例（左: 1-5、右: A-F）
    # ════════════════════════════════════════
    leg_col_max_w = (cw - 8) / 2
    leg_x_r = MG + leg_col_max_w + 8
    legend_font_name = "MSGothic-Bold"
    legend_font_size = 7.5

    def _legend_text(p: Dict[str, str]) -> str:
        return f"[{p['number']}]{p['product_code']}  ({p['label']})"

    left_w = min(
        max(c.stringWidth(_legend_text(p), legend_font_name, legend_font_size) for p in LEGEND_LEFT) + 3 * mm,
        leg_col_max_w,
    )
    right_w = min(
        max(c.stringWidth(_legend_text(p), legend_font_name, legend_font_size) for p in LEGEND_RIGHT) + 3 * mm,
        leg_col_max_w,
    )

    for grp, lx, band_w in [
        (LEGEND_LEFT, float(MG), left_w),
        (LEGEND_RIGHT, leg_x_r, right_w),
    ]:
        cy = y
        for p in grp:
            # 色帯
            c.setFillColor(_hex(p["color"]))
            c.setStrokeColor(_hex("#aaaaaa"))
            c.setLineWidth(0.3)
            c.rect(lx, cy - legend_rh, band_w, legend_rh, stroke=1, fill=1)
            # テキスト（色帯の中に）
            tc = colors.black if _is_light(p["color"]) else colors.white
            c.setFillColor(tc)
            c.setFont(legend_font_name, legend_font_size)
            c.drawString(lx + 1.5 * mm, cy - legend_rh + 1 * mm,
                         _legend_text(p))
            cy -= legend_rh

    y -= max(len(LEGEND_LEFT), len(LEGEND_RIGHT)) * legend_rh + 4 * mm

    # ════════════════════════════════════════
    # 4. ①8:00便
    # ════════════════════════════════════════
    y = _draw_trip(c, "①8:00便", trip1, MG, y, cell_w, cell_h, gap, sign_w, sign_gap)
    y -= 3 * mm

    # ════════════════════════════════════════
    # 5. ②8:00便
    # ════════════════════════════════════════
    y = _draw_trip(c, "②8:00便", trip2, MG, y, cell_w, cell_h, gap, sign_w, sign_gap)
    y -= 4 * mm

    # ════════════════════════════════════════
    # 6. ③④追加便（横並び）
    # ════════════════════════════════════════
    extra_y = y
    extra_bottom_1 = _draw_extra(
        c, "③追加_日商便", MG, extra_y, extra_cell_w, extra_cell_h, gap, sign_w=sign_w, sign_gap=sign_gap
    )
    extra_bottom_2 = _draw_extra(
        c, "④追加便", MG + extra_half_w + 8, extra_y, extra_cell_w, extra_cell_h, gap, sign_w=sign_w, sign_gap=sign_gap
    )
    y = min(extra_bottom_1, extra_bottom_2) - 3 * mm

    # ════════════════════════════════════════
    # 7. フッター
    # ════════════════════════════════════════
    total = len(trip1) + len(trip2)
    over  = total - CARTS_PER_TRIP * 2
    summary = f"合計 {total}台車　（{ITEMS_PER_CART}個入り×{CARTS_PER_TRIP}台車/便×2便）"
    if over > 0:
        summary += f"  ★{over}台車超過"
    c.setFont("MSGothic", 8)
    c.setFillColor(colors.red if over > 0 else _hex("#555555"))
    c.drawString(MG, 6 * mm, summary)

    c.save()
    return output_path
