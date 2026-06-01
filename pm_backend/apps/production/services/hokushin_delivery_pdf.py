# -*- coding: utf-8 -*-
"""㈱北進塗装様向け 納品書PDF生成

- 1ページ目: AM便（本日15時着）
- 2ページ目: 宵積み（翌営業日8時着）
"""

from __future__ import annotations

import io
from datetime import date, timedelta
from typing import Dict, List, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from masters.models import Line
from orders.utils.calendar_utils import get_business_today

from production.services.floor_shipping_pdf import (
    PRODUCT_ORDER,
    PRODUCT_ORDER_NEW,
    _collect_floor_shipping_data,
    _get_calendar_id,
    _build_working_day_cache,
    _extract_short_name,
    _register_fonts,
)


class EmptyDeliveryError(Exception):
    """両便とも明細が無い場合に送出される例外"""
    pass


def _get_prev_working_day(target_date: date, calendar_id, cache) -> date:
    """直前の営業日を取得（cache利用）"""
    current = target_date - timedelta(days=1)
    while True:
        if calendar_id and current in cache:
            if cache[current]:
                return current
        elif current.weekday() < 5:
            return current
        current -= timedelta(days=1)


def _get_next_working_day(target_date: date, calendar_id, cache) -> date:
    """直後の営業日を取得（cache利用）"""
    current = target_date + timedelta(days=1)
    while True:
        if calendar_id and current in cache:
            if cache[current]:
                return current
        elif current.weekday() < 5:
            return current
        current += timedelta(days=1)


def _format_jp_date(d: date) -> str:
    return f'{d.month}月{d.day}日'


def _collect_items_for_delivery(
    data_dict: Dict[date, Dict[str, int]],
    target_date: date,
    product_names: Dict[str, str],
    include_all: bool = False,
    product_order=None,
) -> List[Tuple[str, str, str, int, colors.Color]]:
    """納品書明細項目を取得

    Args:
        include_all: True なら数量0の製品も含める（納品書２用）
        product_order: 製品順序リスト（省略時PRODUCT_ORDER）

    Returns:
        [(label, product_code, short_name, qty, label_color), ...]
    """
    if product_order is None:
        product_order = PRODUCT_ORDER
    items = []
    day_map = data_dict.get(target_date, {})
    for code, label, label_color in product_order:
        qty = day_map.get(code, 0)
        if not include_all and qty <= 0:
            continue
        name = product_names.get(code, '')
        short_name = _extract_short_name(name)
        display_code = code[:-1] if code.endswith('T') else code
        items.append((label, display_code, short_name, qty, label_color))
    return items


def _draw_delivery_page(
    c: canvas.Canvas,
    page_w: float,
    page_h: float,
    font_name: str,
    convoy_label: str,
    delivery_date: date,
    delivery_hour: int,
    dispatch_date: date,
    dispatch_hour: int,
    items: List[Tuple[str, str, str, int, colors.Color]],
    show_row_lines: bool = False,
):
    """1便分の納品書を1ページ描画"""
    margin_left = 12 * mm
    margin_right = 12 * mm
    margin_top = 15 * mm

    # 上端
    y = page_h - margin_top

    # タイトル行: 左 "㈱北進塗装様向け 納品書 XX便", 右 "ダイソウ工業(株)"
    c.setFont(font_name, 14)
    title_left1 = '㈱北進塗装様向け  納品書  '
    c.drawString(margin_left, y, title_left1)
    # 便名は赤字で強調
    left_w = c.stringWidth(title_left1, font_name, 14)
    c.setFillColor(colors.red)
    c.drawString(margin_left + left_w, y, convoy_label)
    c.setFillColor(colors.black)

    right_text = 'ダイソウ工業(株)'
    right_w = c.stringWidth(right_text, font_name, 14)
    c.drawString(page_w - margin_right - right_w, y, right_text)

    y -= 12 * mm

    # ダイソウ工業発時間ラベル（小さく、発日時ボックスの上に表示）
    c.setFont(font_name, 8)
    dispatch_label = 'ダイソウ工業発時間'
    # 右寄せエリアの左端位置を計算
    dispatch_date_box_w = 28 * mm
    dispatch_hour_w = 16 * mm
    dispatch_total_w = dispatch_date_box_w + 2 * mm + dispatch_hour_w
    dispatch_x_start = page_w - margin_right - dispatch_total_w
    c.setFillColor(colors.HexColor('#606060'))
    c.drawString(dispatch_x_start, y + 5 * mm, dispatch_label)
    c.setFillColor(colors.black)

    # 納品日時ボックス（左側）
    date_box_w = 42 * mm
    date_box_h = 10 * mm
    hour_box_w = 16 * mm

    # 納品日ボックス
    c.setLineWidth(1.2)
    c.rect(margin_left, y - date_box_h + 2 * mm, date_box_w, date_box_h, fill=0, stroke=1)
    c.setFont(font_name, 14)
    date_text = _format_jp_date(delivery_date)
    tw = c.stringWidth(date_text, font_name, 14)
    c.drawString(margin_left + (date_box_w - tw) / 2, y - 4 * mm, date_text)

    # 納品時刻ボックス
    hour_x = margin_left + date_box_w + 3 * mm
    c.rect(hour_x, y - date_box_h + 2 * mm, hour_box_w, date_box_h, fill=0, stroke=1)
    hour_text = str(delivery_hour)
    hw = c.stringWidth(hour_text, font_name, 14)
    c.drawString(hour_x + (hour_box_w - hw) / 2, y - 4 * mm, hour_text)
    # "時"ラベル
    c.setFont(font_name, 11)
    c.drawString(hour_x + hour_box_w + 2 * mm, y - 4 * mm, '時')

    # ダイソウ工業発日時（右側）
    c.setFont(font_name, 12)
    c.setFillColor(colors.HexColor('#C00000'))
    dispatch_date_text = _format_jp_date(dispatch_date)
    dw = c.stringWidth(dispatch_date_text, font_name, 12)
    c.drawString(dispatch_x_start + (dispatch_date_box_w - dw) / 2, y - 4 * mm, dispatch_date_text)

    dispatch_hour_x = dispatch_x_start + dispatch_date_box_w + 2 * mm
    hour_full = f'{dispatch_hour}時'
    hw2 = c.stringWidth(hour_full, font_name, 12)
    c.drawString(dispatch_hour_x + (dispatch_hour_w - hw2) / 2, y - 4 * mm, hour_full)
    c.setFillColor(colors.black)

    # 明細表
    y -= 18 * mm

    # 区切り線（点線）
    c.setDash(2, 2)
    c.setLineWidth(0.8)
    c.line(margin_left, y, page_w - margin_right, y)
    c.setDash()

    y -= 6 * mm

    row_h = 8 * mm
    label_col_w = 10 * mm
    qty_col_w = 20 * mm
    unit_col_w = 10 * mm
    code_col_x = margin_left + label_col_w
    code_col_w = (page_w - margin_right) - code_col_x - qty_col_w - unit_col_w

    c.setFont(font_name, 12)
    row_right = page_w - margin_right
    for i, (label, code, short_name, qty, label_color) in enumerate(items):
        # 行間の罫線（先頭行以外、show_row_lines有効時のみ）
        if show_row_lines and i > 0:
            c.setStrokeColor(colors.HexColor('#CCCCCC'))
            c.setLineWidth(0.4)
            c.line(margin_left, y, row_right, y)
            c.setStrokeColor(colors.black)

        # ラベル
        c.setFillColor(label_color)
        c.drawString(margin_left, y - 5 * mm, label)
        c.setFillColor(colors.black)

        # 製品コード＋品名略
        code_text = f'{code}{short_name}' if short_name else code
        c.drawString(code_col_x, y - 5 * mm, code_text)

        # 数量（右寄せ）— 0以下は空白
        if qty > 0:
            qty_text = str(qty)
            qtw = c.stringWidth(qty_text, font_name, 12)
            c.drawString(code_col_x + code_col_w + qty_col_w - qtw, y - 5 * mm, qty_text)
            c.drawString(code_col_x + code_col_w + qty_col_w + 3 * mm, y - 5 * mm, '台')

        y -= row_h

    # 下端区切り点線
    y -= 2 * mm
    c.setDash(2, 2)
    c.setLineWidth(0.8)
    c.line(margin_left, y, page_w - margin_right, y)
    c.setDash()


def _resolve_hokushin_context(
    line_id: int,
    am_delivery_date: date = None,
    yoi_delivery_date: date = None,
    include_all: bool = False,
):
    """北進塗装納品書用のコンテキストを構築

    Returns:
        dict: { line, today, am_delivery_date, yoi_delivery_date,
                am_dispatch_date, yoi_dispatch_date,
                am_items, yoi_items }
    """
    product_order = PRODUCT_ORDER_NEW
    use_alias = False

    line = Line.objects.filter(id=line_id).first()
    if not line:
        raise ValueError('ライン未検出')

    today = get_business_today()
    calendar_id = _get_calendar_id(line)

    # キャッシュ対象は指定日付も含めて広めに
    cache_start = today - timedelta(days=30)
    cache_end = today + timedelta(days=30)
    if am_delivery_date:
        cache_start = min(cache_start, am_delivery_date - timedelta(days=10))
        cache_end = max(cache_end, am_delivery_date + timedelta(days=10))
    if yoi_delivery_date:
        cache_start = min(cache_start, yoi_delivery_date - timedelta(days=10))
        cache_end = max(cache_end, yoi_delivery_date + timedelta(days=10))
    cache = _build_working_day_cache(calendar_id, cache_start, cache_end)

    # デフォルト日付
    if am_delivery_date is None:
        am_delivery_date = today
    if yoi_delivery_date is None:
        yoi_delivery_date = _get_next_working_day(today, calendar_id, cache)

    # 発日 = 各便の前営業日 (宵積み) / 同日 (AM便)
    am_dispatch_date = am_delivery_date
    yoi_dispatch_date = _get_prev_working_day(yoi_delivery_date, calendar_id, cache)

    # 品目データ取得範囲
    all_dates = [am_delivery_date, yoi_delivery_date, am_dispatch_date, yoi_dispatch_date]
    fetch_start = min(all_dates) - timedelta(days=5)
    fetch_end = max(all_dates) + timedelta(days=5)

    am_data, pm_data, product_names = _collect_floor_shipping_data(
        line_id, fetch_start, fetch_end, calendar_id, cache,
        product_order=product_order, use_alias=use_alias,
    )

    am_items = _collect_items_for_delivery(pm_data, am_delivery_date, product_names, include_all=include_all, product_order=product_order)
    yoi_items = _collect_items_for_delivery(am_data, yoi_dispatch_date, product_names, include_all=include_all, product_order=product_order)

    return {
        'line': line,
        'today': today,
        'am_delivery_date': am_delivery_date,
        'yoi_delivery_date': yoi_delivery_date,
        'am_dispatch_date': am_dispatch_date,
        'yoi_dispatch_date': yoi_dispatch_date,
        'am_items': am_items,
        'yoi_items': yoi_items,
    }


def preview_hokushin_delivery(line_id: int) -> dict:
    """デフォルト日付と便の有無を返す（PDF生成せず）"""
    ctx = _resolve_hokushin_context(line_id)
    return {
        'am_delivery_date': ctx['am_delivery_date'].strftime('%Y-%m-%d'),
        'yoi_delivery_date': ctx['yoi_delivery_date'].strftime('%Y-%m-%d'),
        'am_has_items': len(ctx['am_items']) > 0,
        'yoi_has_items': len(ctx['yoi_items']) > 0,
    }


def generate_hokushin_delivery_pdf(
    line_id: int,
    am_delivery_date: date = None,
    yoi_delivery_date: date = None,
) -> bytes:
    """㈱北進塗装様向け 納品書PDF（AM便＋宵積み）を生成"""
    _register_fonts()

    ctx = _resolve_hokushin_context(line_id, am_delivery_date, yoi_delivery_date)
    am_items = ctx['am_items']
    yoi_items = ctx['yoi_items']
    am_delivery_date = ctx['am_delivery_date']
    yoi_delivery_date = ctx['yoi_delivery_date']
    am_dispatch_date = ctx['am_dispatch_date']
    yoi_dispatch_date = ctx['yoi_dispatch_date']

    # 両便とも空ならエラー扱い（呼び出し側でアラート表示）
    if not am_items and not yoi_items:
        raise EmptyDeliveryError('本日は対象便がありません')

    # --- PDF描画 ---
    buf = io.BytesIO()
    page_size = A4  # 縦
    c = canvas.Canvas(buf, pagesize=page_size)
    page_w, page_h = page_size
    font_name = 'MSGothic'

    # Page1: AM便（15時着、ダイソウ工業発=同日12時）
    # 明細ゼロならスキップ
    if am_items:
        _draw_delivery_page(
            c, page_w, page_h, font_name,
            convoy_label='AM便',
            delivery_date=am_delivery_date,
            delivery_hour=15,
            dispatch_date=am_dispatch_date,
            dispatch_hour=12,
            items=am_items,
        )
        c.showPage()

    # Page2: 宵積み（8時着、ダイソウ工業発=前営業日16時）
    # 明細ゼロならスキップ
    if yoi_items:
        _draw_delivery_page(
            c, page_w, page_h, font_name,
            convoy_label='宵積み',
            delivery_date=yoi_delivery_date,
            delivery_hour=8,
            dispatch_date=yoi_dispatch_date,
            dispatch_hour=16,
            items=yoi_items,
        )
        c.showPage()

    c.save()
    return buf.getvalue()


def preview_hokushin_delivery_all(line_id: int) -> dict:
    """全製品版: デフォルト日付と便の有無を返す（PDF生成せず）"""
    ctx = _resolve_hokushin_context(line_id, include_all=True)
    has_any_qty = any(qty > 0 for _, _, _, qty, _ in ctx['am_items']) or \
                  any(qty > 0 for _, _, _, qty, _ in ctx['yoi_items'])
    return {
        'am_delivery_date': ctx['am_delivery_date'].strftime('%Y-%m-%d'),
        'yoi_delivery_date': ctx['yoi_delivery_date'].strftime('%Y-%m-%d'),
        'am_has_items': any(qty > 0 for _, _, _, qty, _ in ctx['am_items']),
        'yoi_has_items': any(qty > 0 for _, _, _, qty, _ in ctx['yoi_items']),
    }


def generate_hokushin_delivery_all_pdf(
    line_id: int,
    am_delivery_date: date = None,
    yoi_delivery_date: date = None,
) -> bytes:
    """㈱北進塗装様向け 納品書PDF（全製品版）— 数量0の製品も表示"""
    _register_fonts()

    ctx = _resolve_hokushin_context(line_id, am_delivery_date, yoi_delivery_date, include_all=True)
    am_items = ctx['am_items']
    yoi_items = ctx['yoi_items']
    am_delivery_date = ctx['am_delivery_date']
    yoi_delivery_date = ctx['yoi_delivery_date']
    am_dispatch_date = ctx['am_dispatch_date']
    yoi_dispatch_date = ctx['yoi_dispatch_date']

    buf = io.BytesIO()
    page_size = A4
    c = canvas.Canvas(buf, pagesize=page_size)
    page_w, page_h = page_size
    font_name = 'MSGothic'

    if am_items:
        _draw_delivery_page(
            c, page_w, page_h, font_name,
            convoy_label='AM便',
            delivery_date=am_delivery_date,
            delivery_hour=15,
            dispatch_date=am_dispatch_date,
            dispatch_hour=12,
            items=am_items,
            show_row_lines=True,
        )
        c.showPage()

    if yoi_items:
        _draw_delivery_page(
            c, page_w, page_h, font_name,
            convoy_label='宵積み',
            delivery_date=yoi_delivery_date,
            delivery_hour=8,
            dispatch_date=yoi_dispatch_date,
            dispatch_hour=16,
            items=yoi_items,
            show_row_lines=True,
        )
        c.showPage()

    c.save()
    return buf.getvalue()


