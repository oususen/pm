# -*- coding: utf-8 -*-
"""フロア配送 8時着/15時着 明細PDF生成"""

from __future__ import annotations

import io
import math
import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from masters.models import Calendar, CalendarDay, Line, Product
from production.models_line_backlog import LineBacklog

# 製品順序 + ラベル + ラベル色
PRODUCT_ORDER = [
    ('YD40006245T', '[1]', colors.HexColor('#0070C0')),      # 青
    ('YD40006630T', '[2]', colors.HexColor('#00B050')),      # 緑
    ('YD40006237T', '[3]', colors.HexColor('#FF0000')),      # 赤
    ('YD40006618T', '[4]', colors.HexColor('#0070C0')),      # 青
    ('YD40006842T', '[A]', colors.HexColor('#D2691E')),      # チョコレート色
    ('YD40007003T', '[B]', colors.HexColor('#808080')),      # グレー
    ('YD40007243T', '[C]', colors.black),                     # 黒
    ('YD40007372T', '[D]', colors.HexColor('#FF69B4')),      # 桃
    ('YD40007722T', '[E]', colors.HexColor('#800080')),      # 紫
    ('YD40007688T', '[F]', colors.HexColor('#FF0000')),      # 赤
    ('YD40002946T', '[5]', colors.HexColor('#FF8C00')),      # オレンジ
]

PM_SEQUENCE_THRESHOLD = 50
JPN_WEEKDAYS = ['月', '火', '水', '木', '金', '土', '日']

# 色定義
COLOR_HEADER_BG = colors.HexColor('#4472C4')
COLOR_HEADER_TEXT = colors.white
COLOR_SECTION_15 = colors.HexColor('#FFC000')  # 15時着ヘッダ（オレンジ系）
COLOR_SECTION_08 = colors.HexColor('#70AD47')  # 8時着ヘッダ（緑系）
COLOR_TOTAL_BG = colors.HexColor('#D9E2F3')
COLOR_GRAND_TOTAL_BG = colors.HexColor('#B4C6E7')
COLOR_WEEKEND_BG = colors.HexColor('#F2F2F2')
COLOR_GRID = colors.HexColor('#808080')
SECTION_TITLE_15 = '１５時着（午前便　AM１１：３０頃）'
SECTION_TITLE_08 = '８時着（午後便　PM18：３０頃）'


def _register_fonts():
    """日本語フォント登録"""
    if 'MSGothic' in pdfmetrics.getRegisteredFontNames():
        return
    from shipping.services.shipping_pdf_generator import register_japanese_fonts
    register_japanese_fonts()


def _extract_short_name(name: str) -> str:
    """品名から括弧内情報だけを抜き出す（例: （U-5CAB））。"""
    text = str(name or '').strip()
    if not text:
        return ''
    # 半角/全角の括弧が混在しても抽出できるようにする（例: "(30/40UR）"）。
    mixed = re.search(r'[\(（]\s*([^)）]+?)\s*[)）]', text)
    if mixed:
        inner = mixed.group(1).strip()
        return f'({inner})' if inner else ''
    return ''


def _resolve_order_product_code(raw_code: str, ordered_codes_set: set[str]) -> Optional[str]:
    """
    PRODUCT_ORDER上のキーへ正規化する。
    - そのまま一致
    - 末尾Tを外して一致
    - 末尾Tを足して一致
    """
    code = str(raw_code or '').strip()
    if not code:
        return None
    if code in ordered_codes_set:
        return code
    if code.endswith('T') and code[:-1] in ordered_codes_set:
        return code[:-1]
    t_code = f'{code}T'
    if t_code in ordered_codes_set:
        return t_code
    return None


def _get_calendar_id(line: Line) -> Optional[int]:
    cal_id = getattr(line, 'calendar_id', None)
    if not cal_id:
        cal = Calendar.objects.filter(calendar_code='daiso').first()
        cal_id = cal.id if cal else None
    return cal_id


def _build_working_day_cache(calendar_id, start_date, end_date):
    cache = {}
    if calendar_id:
        for cd in CalendarDay.objects.filter(
            calendar_id=calendar_id,
            target_date__gte=start_date - timedelta(days=10),
            target_date__lte=end_date + timedelta(days=10),
        ):
            cache[cd.target_date] = cd.is_working_day
    return cache


def _is_working_day(d, calendar_id, cache):
    if not calendar_id:
        return d.weekday() < 5
    if d in cache:
        return cache[d]
    return d.weekday() < 5


def _shift_business_days_back(target_date, days, calendar_id, cache):
    """営業日で過去方向にシフト（days=1なら前営業日）"""
    if days <= 0:
        return target_date
    current = target_date
    shifted = 0
    while shifted < days:
        current -= timedelta(days=1)
        if _is_working_day(current, calendar_id, cache):
            shifted += 1
    return current


def _get_display_dates(start_date, end_date):
    """表示対象の日付リスト（暦日）"""
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def _collect_floor_shipping_data(line_id, start_date, end_date, calendar_id, cal_cache):
    """
    フロア配送のLineBacklogから8時着/15時着データを収集。
    8時着はLT=1（1営業日前にシフトして表示）、15時着はLT=0（当日）。
    """
    # LT=1のために前倒しでデータを取得
    fetch_start = start_date - timedelta(days=10)

    backlogs = LineBacklog.objects.filter(
        line_id=line_id,
        plan_date__gte=fetch_start,
        plan_date__lte=end_date,
        plan_qty__gt=0,
    ).select_related('product').order_by('plan_date', 'product_id', 'sequence_no')

    # 製品コードセット（PRODUCT_ORDERに含まれるもの）
    product_codes_set = {code for code, _, _ in PRODUCT_ORDER}

    # 日付×製品 → {am_qty, pm_qty} を組み立て
    # sequence_noでソート後、1件目=8時着、2件目=15時着（sequence_no>50は15時着）
    raw_data = {}  # (plan_date, product_code) → [(plan_qty, sequence_no), ...]
    product_names = {}  # product_code → product_name

    for b in backlogs:
        source_code = b.product.product_code if b.product else ''
        pc = _resolve_order_product_code(source_code, product_codes_set)
        if not pc:
            continue
        key = (b.plan_date, pc)
        raw_data.setdefault(key, []).append((int(b.plan_qty), b.sequence_no))
        if pc not in product_names and b.product:
            product_names[pc] = b.product.product_name or ''

    # AM/PM分離
    # am_data[display_date][product_code] = qty
    # pm_data[display_date][product_code] = qty
    am_data: Dict[date, Dict[str, int]] = {}
    pm_data: Dict[date, Dict[str, int]] = {}

    for (plan_date, pc), lots in raw_data.items():
        # sequence_noでソート
        def sort_key(item):
            seq = item[1]
            if seq is None or seq == 0:
                return 10**9
            return seq
        sorted_lots = sorted(lots, key=sort_key)

        for lot_index, (qty, seq_no) in enumerate(sorted_lots):
            seq_val = seq_no if seq_no is not None else 10**9
            is_pm = (seq_val != 10**9 and seq_val > PM_SEQUENCE_THRESHOLD) or lot_index > 0

            if is_pm:
                # 15時着: LT=0 → 表示日=plan_date
                display_date = plan_date
                pm_data.setdefault(display_date, {})
                pm_data[display_date][pc] = pm_data[display_date].get(pc, 0) + qty
            else:
                # 8時着: LT=1 → 表示日=plan_dateの前営業日
                display_date = _shift_business_days_back(plan_date, 1, calendar_id, cal_cache)
                am_data.setdefault(display_date, {})
                am_data[display_date][pc] = am_data[display_date].get(pc, 0) + qty

    # 製品マスタから品名を補完（表示期間に計画が無い品番でも名称表示するため）
    ordered_codes = [code for code, _, _ in PRODUCT_ORDER]
    master_name_map = {
        code: (name or '')
        for code, name in Product.objects.filter(product_code__in=ordered_codes).values_list('product_code', 'product_name')
    }
    for code in ordered_codes:
        if not product_names.get(code):
            product_names[code] = master_name_map.get(code, '') or ''

    # T品番で名称が取れない場合は、末尾Tなし品番の名称をフォールバック
    missing_t_codes = [code for code in ordered_codes if code.endswith('T') and not product_names.get(code)]
    if missing_t_codes:
        base_codes = [code[:-1] for code in missing_t_codes]
        base_name_map = {
            code: (name or '')
            for code, name in Product.objects.filter(product_code__in=base_codes).values_list('product_code', 'product_name')
        }
        for code in missing_t_codes:
            base_name = base_name_map.get(code[:-1], '') or ''
            if base_name:
                product_names[code] = base_name

    return am_data, pm_data, product_names


def generate_floor_shipping_pdf(line_id: int, start_date: date, end_date: date) -> bytes:
    """フロア配送 8時着/15時着 明細PDFを生成してバイト列で返す"""
    _register_fonts()

    line = Line.objects.filter(id=line_id).first()
    if not line:
        raise ValueError('ライン未検出')

    calendar_id = _get_calendar_id(line)
    cal_cache = _build_working_day_cache(calendar_id, start_date, end_date)
    display_dates = _get_display_dates(start_date, end_date)

    am_data, pm_data, product_names = _collect_floor_shipping_data(
        line_id, start_date, end_date, calendar_id, cal_cache
    )

    # --- PDF描画 ---
    buf = io.BytesIO()
    page_size = landscape(A4)
    c = canvas.Canvas(buf, pagesize=page_size)
    page_w, page_h = page_size

    margin_left = 8 * mm
    margin_top = 10 * mm
    margin_right = 8 * mm

    font_name = 'MSGothic'
    font_scale = 1.5
    font_size_header = 8 * font_scale
    font_size_cell = 8 * font_scale
    font_size_title = 12 * font_scale

    # 列幅計算
    label_col_w = 58 * mm * (4 / 3)  # 製品コード+名前列（現状の2/3）
    date_col_w = max(
        (page_w - margin_left - margin_right - label_col_w) / max(len(display_dates), 1),
        12 * mm
    )
    row_h = 5 * mm
    section_header_h = 5.5 * mm

    table_w = label_col_w + date_col_w * len(display_dates)

    def draw_page_header(y_pos):
        c.setFont(font_name, font_size_title)
        c.drawString(margin_left, y_pos, f'フロア配送明細  {start_date.strftime("%Y/%m/%d")} ～ {end_date.strftime("%Y/%m/%d")}')
        return y_pos - 6 * mm

    def draw_date_header(y_pos):
        """日付ヘッダー行"""
        x = margin_left
        # ラベル列
        c.setFillColor(COLOR_HEADER_BG)
        c.rect(x, y_pos - row_h, label_col_w, row_h, fill=1, stroke=0)
        c.setFillColor(COLOR_HEADER_TEXT)
        c.setFont(font_name, font_size_header)
        c.drawString(x + 1 * mm, y_pos - row_h + 1 * mm, '')
        x += label_col_w

        for d in display_dates:
            is_weekend = d.weekday() >= 5
            if is_weekend:
                c.setFillColor(COLOR_WEEKEND_BG)
            else:
                c.setFillColor(COLOR_HEADER_BG)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=1, stroke=0)

            c.setFillColor(COLOR_HEADER_TEXT if not is_weekend else colors.black)
            c.setFont(font_name, font_size_header)
            wd = JPN_WEEKDAYS[d.weekday()]
            label = f'{d.month}/{d.day}'
            tw = c.stringWidth(label, font_name, font_size_header)
            c.drawString(x + (date_col_w - tw) / 2, y_pos - row_h + 1 * mm, label)
            x += date_col_w

        # 2行目: 曜日
        y_pos -= row_h
        x = margin_left
        c.setFillColor(COLOR_HEADER_BG)
        c.rect(x, y_pos - row_h, label_col_w, row_h, fill=1, stroke=0)
        x += label_col_w

        for d in display_dates:
            is_weekend = d.weekday() >= 5
            if is_weekend:
                c.setFillColor(COLOR_WEEKEND_BG)
            else:
                c.setFillColor(COLOR_HEADER_BG)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=1, stroke=0)

            c.setFillColor(COLOR_HEADER_TEXT if not is_weekend else colors.black)
            c.setFont(font_name, font_size_header)
            wd = JPN_WEEKDAYS[d.weekday()]
            tw = c.stringWidth(wd, font_name, font_size_header)
            c.drawString(x + (date_col_w - tw) / 2, y_pos - row_h + 1 * mm, wd)
            x += date_col_w

        return y_pos - row_h

    def draw_section_header(y_pos, title, bg_color):
        """セクションヘッダー（15時着 / 8時着）"""
        x = margin_left
        c.setFillColor(bg_color)
        c.rect(x, y_pos - section_header_h, table_w, section_header_h, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont(font_name, font_size_header + 1)
        c.drawString(x + 2 * mm, y_pos - section_header_h + 1.5 * mm, title)
        return y_pos - section_header_h

    def draw_product_row(y_pos, product_code, label, name, data_by_date, row_bg=None, label_color=None):
        """製品行を描画"""
        x = margin_left

        # ラベル列
        if row_bg:
            c.setFillColor(row_bg)
            c.rect(x, y_pos - row_h, label_col_w, row_h, fill=1, stroke=0)
        c.setStrokeColor(COLOR_GRID)
        c.rect(x, y_pos - row_h, label_col_w, row_h, fill=0, stroke=1)
        c.setFillColor(label_color or colors.black)
        c.setFont(font_name, font_size_cell)
        display_code = product_code[:-1] if str(product_code).endswith('T') else str(product_code)
        short_name = _extract_short_name(name)
        cell_text = f'{label}{display_code}{short_name}' if short_name else f'{label}{display_code}'
        c.drawString(x + 0.5 * mm, y_pos - row_h + 1 * mm, cell_text)
        x += label_col_w

        for d in display_dates:
            is_weekend = d.weekday() >= 5
            bg = COLOR_WEEKEND_BG if is_weekend else row_bg
            if bg:
                c.setFillColor(bg)
                c.rect(x, y_pos - row_h, date_col_w, row_h, fill=1, stroke=0)
            c.setStrokeColor(COLOR_GRID)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=0, stroke=1)

            qty = data_by_date.get(d, 0)
            if qty > 0:
                c.setFillColor(label_color or colors.black)
                c.setFont(font_name, font_size_cell)
                txt = str(qty)
                tw = c.stringWidth(txt, font_name, font_size_cell)
                c.drawString(x + date_col_w - tw - 1 * mm, y_pos - row_h + 1 * mm, txt)
            x += date_col_w

        return y_pos - row_h

    def draw_total_row(y_pos, title, totals_by_date, bg_color=COLOR_TOTAL_BG):
        """合計行"""
        x = margin_left

        c.setFillColor(bg_color)
        c.rect(x, y_pos - row_h, label_col_w, row_h, fill=1, stroke=0)
        c.setStrokeColor(COLOR_GRID)
        c.rect(x, y_pos - row_h, label_col_w, row_h, fill=0, stroke=1)
        c.setFillColor(colors.black)
        c.setFont(font_name, font_size_cell + 1)
        tw = c.stringWidth(title, font_name, font_size_cell + 1)
        c.drawString(x + label_col_w - tw - 1 * mm, y_pos - row_h + 1 * mm, title)
        x += label_col_w

        for d in display_dates:
            c.setFillColor(bg_color)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=1, stroke=0)
            c.setStrokeColor(COLOR_GRID)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=0, stroke=1)

            qty = totals_by_date.get(d, 0)
            if qty > 0:
                c.setFillColor(colors.black)
                c.setFont(font_name, font_size_cell + 1)
                txt = str(qty)
                tw = c.stringWidth(txt, font_name, font_size_cell + 1)
                c.drawString(x + date_col_w - tw - 1 * mm, y_pos - row_h + 1 * mm, txt)
            x += date_col_w

        return y_pos - row_h

    def calc_section_totals(section_data):
        totals = {}
        for d in display_dates:
            total = 0
            for pc, _, _ in PRODUCT_ORDER:
                total += section_data.get(d, {}).get(pc, 0)
            totals[d] = total
        return totals

    # --- ページ描画 ---
    y = page_h - margin_top
    y = draw_page_header(y)
    y = draw_date_header(y)

    # 15時着セクション
    y = draw_section_header(y, SECTION_TITLE_15, COLOR_SECTION_15)
    for pc, label, lbl_color in PRODUCT_ORDER:
        name = product_names.get(pc, '')
        data_for_product = {}
        for d in display_dates:
            qty = pm_data.get(d, {}).get(pc, 0)
            if qty > 0:
                data_for_product[d] = qty
        y = draw_product_row(y, pc, label, name, data_for_product, row_bg=lbl_color, label_color=colors.white)

    pm_totals = calc_section_totals(pm_data)
    y = draw_total_row(y, '合計', pm_totals)

    # 8時着セクション
    y = draw_section_header(y, SECTION_TITLE_08, COLOR_SECTION_08)
    for pc, label, lbl_color in PRODUCT_ORDER:
        name = product_names.get(pc, '')
        data_for_product = {}
        for d in display_dates:
            qty = am_data.get(d, {}).get(pc, 0)
            if qty > 0:
                data_for_product[d] = qty
        y = draw_product_row(y, pc, label, name, data_for_product, row_bg=lbl_color, label_color=colors.white)

    am_totals = calc_section_totals(am_data)
    y = draw_total_row(y, '合計', am_totals)

    # 出荷数合計
    grand_totals = {}
    for d in display_dates:
        grand_totals[d] = am_totals.get(d, 0) + pm_totals.get(d, 0)
    y = draw_total_row(y, '出荷数合計', grand_totals, bg_color=COLOR_GRAND_TOTAL_BG)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()
