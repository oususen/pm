# -*- coding: utf-8 -*-
"""北進納入リスト PDF 生成サービス（フロア配送向け）"""

from __future__ import annotations

import io
from datetime import date, datetime, timedelta
from typing import Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from masters.models import Line, Product
from production.models_line_backlog import LineBacklog
from production.services.floor_shipping_pdf import (
    PRODUCT_ORDER,
    PRODUCT_ORDER_LAP,
    PRODUCT_ORDER_NEW,
    PRODUCT_ALIAS_MAP,
    JPN_WEEKDAYS,
    PM_SEQUENCE_THRESHOLD,
    COLOR_HEADER_BG,
    COLOR_HEADER_TEXT,
    COLOR_TOTAL_BG,
    COLOR_WEEKEND_BG,
    COLOR_ROW_ODD_BG,
    COLOR_ROW_EVEN_BG,
    COLOR_GRID,
    _register_fonts,
    _extract_short_name,
    _resolve_order_product_code,
    _get_calendar_id,
    _build_working_day_cache,
    _is_working_day,
    _build_new_render_order,
)


COLOR_SECTION_AM = colors.HexColor('#70AD47')
COLOR_SECTION_PM = colors.HexColor('#FFC000')
COLOR_GRAND_TOTAL_BG = colors.HexColor('#B4C6E7')
SECTION_TITLE_AM = '午前便　AM 08:00頃'
SECTION_TITLE_PM = '午後便　PM 15:00頃'
PAGE_DAYS = 14


def _shift_business_days_forward(target_date: date, days: int, calendar_id, cache) -> date:
    """営業日で未来方向にシフト（days=1なら翌営業日）"""
    if days <= 0:
        return target_date
    current = target_date
    shifted = 0
    while shifted < days:
        current += timedelta(days=1)
        if _is_working_day(current, calendar_id, cache):
            shifted += 1
    return current


def _get_display_dates(start_date: date, end_date: date):
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def _chunk_dates(dates, size: int):
    for index in range(0, len(dates), size):
        yield dates[index:index + size]


def _collect_hokushin_delivery_list_data(line_id: int, start_date: date, end_date: date, calendar_id, cal_cache,
                                         product_order=None, use_alias=True):
    """計画を翌営業日に表示し、午前便/午後便に振り分ける。"""
    if product_order is None:
        product_order = PRODUCT_ORDER

    fetch_start = start_date - timedelta(days=14)
    fetch_end = end_date

    backlogs = LineBacklog.objects.filter(
        line_id=line_id,
        plan_date__gte=fetch_start,
        plan_date__lte=fetch_end,
        plan_qty__gt=0,
    ).select_related('product').order_by('plan_date', 'product_id', 'sequence_no')

    product_codes_set = {code for code, _, _ in product_order}
    raw_data = {}
    product_names = {}

    for backlog in backlogs:
        source_code = backlog.product.product_code if backlog.product else ''
        product_code = _resolve_order_product_code(source_code, product_codes_set, use_alias=use_alias)
        if not product_code:
            continue
        raw_data.setdefault((backlog.plan_date, product_code), []).append((int(backlog.plan_qty), backlog.sequence_no))
        if product_code not in product_names and backlog.product:
            product_names[product_code] = backlog.product.product_name or ''

    am_data: Dict[date, Dict[str, int]] = {}
    pm_data: Dict[date, Dict[str, int]] = {}

    for (plan_date, product_code), lots in raw_data.items():
        sorted_lots = sorted(
            lots,
            key=lambda item: item[1] if item[1] not in (None, 0) else 10**9,
        )

        display_date = _shift_business_days_forward(plan_date, 1, calendar_id, cal_cache)
        if display_date < start_date or display_date > end_date:
            continue

        for lot_index, (qty, sequence_no) in enumerate(sorted_lots):
            seq_val = sequence_no if sequence_no is not None else 10**9
            is_pm = (seq_val != 10**9 and seq_val > PM_SEQUENCE_THRESHOLD) or lot_index > 0
            if is_pm:
                pm_data.setdefault(display_date, {})
                pm_data[display_date][product_code] = pm_data[display_date].get(product_code, 0) + qty
            else:
                am_data.setdefault(display_date, {})
                am_data[display_date][product_code] = am_data[display_date].get(product_code, 0) + qty

    ordered_codes = [code for code, _, _ in product_order]
    master_name_map = {
        code: (name or '')
        for code, name in Product.objects.filter(product_code__in=ordered_codes).values_list('product_code', 'product_name')
    }
    for code in ordered_codes:
        if not product_names.get(code):
            product_names[code] = master_name_map.get(code, '') or ''

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


def generate_hokushin_delivery_list_pdf(
    line_id: int,
    start_date: date,
    end_date: date,
    creator_name: str = 'システム',
) -> bytes:
    """北進納入リストPDFを生成してバイト列で返す。"""
    _register_fonts()

    line = Line.objects.filter(id=line_id).first()
    if not line:
        raise ValueError('ライン未検出')

    calendar_id = _get_calendar_id(line)
    cal_cache = _build_working_day_cache(calendar_id, start_date - timedelta(days=14), end_date + timedelta(days=14))
    display_dates = _get_display_dates(start_date, end_date)
    am_data, pm_data, product_names = _collect_hokushin_delivery_list_data(
        line_id,
        start_date,
        end_date,
        calendar_id,
        cal_cache,
    )

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

    label_col_w = 58 * mm * (4 / 3)
    row_h = 5 * mm
    section_header_h = 5.5 * mm

    output_date = datetime.now().date()
    creator_label = str(creator_name or '').strip() or 'システム'

    def draw_page_header(y_pos, page_dates):
        c.setFont(font_name, font_size_title)
        c.drawString(
            margin_left,
            y_pos,
            '株式会社北進塗装　竹岡工場長様',
        )
        y2 = y_pos - 5.5 * mm
        c.setFont(font_name, 8 * font_scale)
        c.setFillColor(colors.HexColor('#666666'))

        right_text = f'ダイソウ工業　{creator_label}'
        tw = c.stringWidth(right_text, font_name, 8 * font_scale)
        c.drawString(page_w - margin_right - tw, y2, right_text)
        if page_dates:
            range_text = f'{page_dates[0].strftime("%Y/%m/%d")} ～ {page_dates[-1].strftime("%Y/%m/%d")}'
            c.drawString(margin_left, y2 - 4.5 * mm, range_text)

        created_text = output_date.strftime('%Y/%m/%d')
        dw = c.stringWidth(created_text, font_name, 8 * font_scale)
        c.drawString(page_w - margin_right - dw, y2 - 4.5 * mm, created_text)
        c.setFillColor(colors.black)
        return y_pos - 13 * mm

    def draw_date_header(y_pos, page_dates, date_col_w):
        x = margin_left
        c.setFillColor(COLOR_HEADER_BG)
        c.rect(x, y_pos - row_h, label_col_w, row_h, fill=1, stroke=0)
        x += label_col_w
        for day in page_dates:
            is_weekend = day.weekday() >= 5
            c.setFillColor(COLOR_WEEKEND_BG if is_weekend else COLOR_HEADER_BG)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=1, stroke=0)
            c.setFillColor(COLOR_HEADER_TEXT)
            c.setFont(font_name, font_size_header)
            label = f'{day.month}/{day.day}'
            tw = c.stringWidth(label, font_name, font_size_header)
            c.drawString(x + (date_col_w - tw) / 2, y_pos - row_h + 1 * mm, label)
            x += date_col_w

        y_pos -= row_h
        x = margin_left
        c.setFillColor(COLOR_HEADER_BG)
        c.rect(x, y_pos - row_h, label_col_w, row_h, fill=1, stroke=0)
        x += label_col_w
        for day in page_dates:
            is_weekend = day.weekday() >= 5
            c.setFillColor(COLOR_WEEKEND_BG if is_weekend else COLOR_HEADER_BG)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=1, stroke=0)
            c.setFillColor(COLOR_HEADER_TEXT)
            c.setFont(font_name, font_size_header)
            weekday = JPN_WEEKDAYS[day.weekday()]
            tw = c.stringWidth(weekday, font_name, font_size_header)
            c.drawString(x + (date_col_w - tw) / 2, y_pos - row_h + 1 * mm, weekday)
            x += date_col_w
        return y_pos - row_h

    def draw_section_header(y_pos, title, bg_color, table_w):
        c.setFillColor(bg_color)
        c.rect(margin_left, y_pos - section_header_h, table_w, section_header_h, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont(font_name, font_size_header + 1)
        c.drawString(margin_left + 2 * mm, y_pos - section_header_h + 1.5 * mm, title)
        return y_pos - section_header_h

    def draw_product_row(y_pos, product_code, label, name, data_by_date, page_dates, date_col_w, row_bg=None, label_color=None):
        x = margin_left
        if row_bg:
            c.setFillColor(row_bg)
            c.rect(x, y_pos - row_h, label_col_w, row_h, fill=1, stroke=0)
        c.setStrokeColor(COLOR_GRID)
        c.rect(x, y_pos - row_h, label_col_w, row_h, fill=0, stroke=1)
        c.setFillColor(label_color or colors.black)
        c.setFont(font_name, font_size_cell)
        display_code = product_code[:-1] if str(product_code).endswith('T') else str(product_code)
        short_name = _extract_short_name(name)
        text = f'{label}{display_code}{short_name}' if short_name else f'{label}{display_code}'
        c.drawString(x + 0.5 * mm, y_pos - row_h + 1 * mm, text)
        x += label_col_w

        for day in page_dates:
            is_weekend = day.weekday() >= 5
            bg = COLOR_WEEKEND_BG if is_weekend else row_bg
            if bg:
                c.setFillColor(bg)
                c.rect(x, y_pos - row_h, date_col_w, row_h, fill=1, stroke=0)
            c.setStrokeColor(COLOR_GRID)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=0, stroke=1)
            qty = data_by_date.get(day, 0)
            if qty > 0:
                c.setFillColor(label_color or colors.black)
                c.setFont(font_name, font_size_cell)
                txt = str(qty)
                tw = c.stringWidth(txt, font_name, font_size_cell)
                c.drawString(x + date_col_w - tw - 1 * mm, y_pos - row_h + 1 * mm, txt)
            x += date_col_w
        return y_pos - row_h

    def draw_total_row(y_pos, title, totals_by_date, page_dates, date_col_w, bg_color=COLOR_TOTAL_BG):
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

        for day in page_dates:
            is_weekend = day.weekday() >= 5
            c.setFillColor(COLOR_WEEKEND_BG if is_weekend else bg_color)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=1, stroke=0)
            c.setStrokeColor(COLOR_GRID)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=0, stroke=1)
            qty = totals_by_date.get(day, 0)
            if qty > 0:
                c.setFillColor(colors.black)
                c.setFont(font_name, font_size_cell + 1)
                txt = str(qty)
                tw = c.stringWidth(txt, font_name, font_size_cell + 1)
                c.drawString(x + date_col_w - tw - 1 * mm, y_pos - row_h + 1 * mm, txt)
            x += date_col_w
        return y_pos - row_h

    def calc_section_totals(section_data, page_dates):
        totals = {}
        for day in page_dates:
            totals[day] = sum(section_data.get(day, {}).get(code, 0) for code, _, _ in PRODUCT_ORDER)
        return totals

    for page_dates in _chunk_dates(display_dates, PAGE_DAYS):
        date_col_w = max(
            (page_w - margin_left - margin_right - label_col_w) / max(len(page_dates), 1),
            12 * mm,
        )
        table_w = label_col_w + date_col_w * len(page_dates)

        y = page_h - margin_top
        y = draw_page_header(y, page_dates)
        y = draw_date_header(y, page_dates, date_col_w)

        y = draw_section_header(y, SECTION_TITLE_AM, COLOR_SECTION_AM, table_w)
        for row_index, (product_code, label, label_color) in enumerate(PRODUCT_ORDER, start=1):
            name = product_names.get(product_code, '')
            row_data = {}
            for day in page_dates:
                qty = am_data.get(day, {}).get(product_code, 0)
                if qty > 0:
                    row_data[day] = qty
            row_bg = COLOR_ROW_ODD_BG if row_index % 2 == 1 else COLOR_ROW_EVEN_BG
            y = draw_product_row(
                y,
                product_code,
                label,
                name,
                row_data,
                page_dates,
                date_col_w,
                row_bg=row_bg,
                label_color=label_color,
            )
        am_totals = calc_section_totals(am_data, page_dates)
        y = draw_total_row(y, '午前便合計', am_totals, page_dates, date_col_w)

        y = draw_section_header(y, SECTION_TITLE_PM, COLOR_SECTION_PM, table_w)
        for row_index, (product_code, label, label_color) in enumerate(PRODUCT_ORDER, start=1):
            name = product_names.get(product_code, '')
            row_data = {}
            for day in page_dates:
                qty = pm_data.get(day, {}).get(product_code, 0)
                if qty > 0:
                    row_data[day] = qty
            row_bg = COLOR_ROW_ODD_BG if row_index % 2 == 1 else COLOR_ROW_EVEN_BG
            y = draw_product_row(
                y,
                product_code,
                label,
                name,
                row_data,
                page_dates,
                date_col_w,
                row_bg=row_bg,
                label_color=label_color,
            )
        pm_totals = calc_section_totals(pm_data, page_dates)
        y = draw_total_row(y, '午後便合計', pm_totals, page_dates, date_col_w)

        grand_totals = {day: am_totals.get(day, 0) + pm_totals.get(day, 0) for day in page_dates}
        y = draw_total_row(y, '総合計', grand_totals, page_dates, date_col_w, bg_color=COLOR_GRAND_TOTAL_BG)

        c.showPage()

    c.save()
    buf.seek(0)
    return buf.read()


def generate_hokushin_delivery_list_lap_pdf(
    line_id: int,
    start_date: date,
    end_date: date,
    creator_name: str = 'システム',
) -> bytes:
    """北進納入リスト ラップ期間用PDF（午前1ページ+午後1ページ、新旧品番併記）"""
    _register_fonts()

    line = Line.objects.filter(id=line_id).first()
    if not line:
        raise ValueError('ライン未検出')

    calendar_id = _get_calendar_id(line)
    cal_cache = _build_working_day_cache(calendar_id, start_date - timedelta(days=14), end_date + timedelta(days=14))
    display_dates = _get_display_dates(start_date, end_date)
    am_data, pm_data, product_names = _collect_hokushin_delivery_list_data(
        line_id, start_date, end_date, calendar_id, cal_cache,
        product_order=PRODUCT_ORDER_LAP, use_alias=False,
    )

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

    label_col_w = 58 * mm * (4 / 3)
    row_h = 5 * mm
    section_header_h = 5.5 * mm

    output_date = datetime.now().date()
    creator_label = str(creator_name or '').strip() or 'システム'

    def draw_page_header(y_pos, page_dates, section_label=''):
        c.setFont(font_name, font_size_title)
        title = '株式会社北進塗装　竹岡工場長様'
        if section_label:
            title += f'  【{section_label}】'
        c.drawString(margin_left, y_pos, title)
        y2 = y_pos - 5.5 * mm
        c.setFont(font_name, 8 * font_scale)
        c.setFillColor(colors.HexColor('#666666'))
        right_text = f'ダイソウ工業　{creator_label}'
        tw = c.stringWidth(right_text, font_name, 8 * font_scale)
        c.drawString(page_w - margin_right - tw, y2, right_text)
        if page_dates:
            range_text = f'{page_dates[0].strftime("%Y/%m/%d")} ～ {page_dates[-1].strftime("%Y/%m/%d")}'
            c.drawString(margin_left, y2 - 4.5 * mm, range_text)
        created_text = output_date.strftime('%Y/%m/%d')
        dw = c.stringWidth(created_text, font_name, 8 * font_scale)
        c.drawString(page_w - margin_right - dw, y2 - 4.5 * mm, created_text)
        c.setFillColor(colors.black)
        return y_pos - 13 * mm

    def draw_date_header(y_pos, page_dates, date_col_w):
        x = margin_left
        c.setFillColor(COLOR_HEADER_BG)
        c.rect(x, y_pos - row_h, label_col_w, row_h, fill=1, stroke=0)
        x += label_col_w
        for day in page_dates:
            is_weekend = day.weekday() >= 5
            c.setFillColor(COLOR_WEEKEND_BG if is_weekend else COLOR_HEADER_BG)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=1, stroke=0)
            c.setFillColor(COLOR_HEADER_TEXT)
            c.setFont(font_name, font_size_header)
            label = f'{day.month}/{day.day}'
            tw = c.stringWidth(label, font_name, font_size_header)
            c.drawString(x + (date_col_w - tw) / 2, y_pos - row_h + 1 * mm, label)
            x += date_col_w
        y_pos -= row_h
        x = margin_left
        c.setFillColor(COLOR_HEADER_BG)
        c.rect(x, y_pos - row_h, label_col_w, row_h, fill=1, stroke=0)
        x += label_col_w
        for day in page_dates:
            is_weekend = day.weekday() >= 5
            c.setFillColor(COLOR_WEEKEND_BG if is_weekend else COLOR_HEADER_BG)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=1, stroke=0)
            c.setFillColor(COLOR_HEADER_TEXT)
            c.setFont(font_name, font_size_header)
            weekday = JPN_WEEKDAYS[day.weekday()]
            tw = c.stringWidth(weekday, font_name, font_size_header)
            c.drawString(x + (date_col_w - tw) / 2, y_pos - row_h + 1 * mm, weekday)
            x += date_col_w
        return y_pos - row_h

    def draw_section_header(y_pos, title, bg_color, table_w):
        c.setFillColor(bg_color)
        c.rect(margin_left, y_pos - section_header_h, table_w, section_header_h, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont(font_name, font_size_header + 1)
        c.drawString(margin_left + 2 * mm, y_pos - section_header_h + 1.5 * mm, title)
        return y_pos - section_header_h

    def draw_product_row(y_pos, product_code, label, name, data_by_date, page_dates, date_col_w, row_bg=None, label_color=None):
        x = margin_left
        if row_bg:
            c.setFillColor(row_bg)
            c.rect(x, y_pos - row_h, label_col_w, row_h, fill=1, stroke=0)
        c.setStrokeColor(COLOR_GRID)
        c.rect(x, y_pos - row_h, label_col_w, row_h, fill=0, stroke=1)
        c.setFillColor(label_color or colors.black)
        c.setFont(font_name, font_size_cell)
        display_code = product_code[:-1] if str(product_code).endswith('T') else str(product_code)
        short_name = _extract_short_name(name)
        text = f'{label}{display_code}{short_name}' if short_name else f'{label}{display_code}'
        c.drawString(x + 0.5 * mm, y_pos - row_h + 1 * mm, text)
        x += label_col_w
        for day in page_dates:
            is_weekend = day.weekday() >= 5
            bg = COLOR_WEEKEND_BG if is_weekend else row_bg
            if bg:
                c.setFillColor(bg)
                c.rect(x, y_pos - row_h, date_col_w, row_h, fill=1, stroke=0)
            c.setStrokeColor(COLOR_GRID)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=0, stroke=1)
            qty = data_by_date.get(day, 0)
            if qty > 0:
                c.setFillColor(label_color or colors.black)
                c.setFont(font_name, font_size_cell)
                txt = str(qty)
                tw = c.stringWidth(txt, font_name, font_size_cell)
                c.drawString(x + date_col_w - tw - 1 * mm, y_pos - row_h + 1 * mm, txt)
            x += date_col_w
        return y_pos - row_h

    def draw_total_row(y_pos, title, totals_by_date, page_dates, date_col_w, bg_color=COLOR_TOTAL_BG):
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
        for day in page_dates:
            is_weekend = day.weekday() >= 5
            c.setFillColor(COLOR_WEEKEND_BG if is_weekend else bg_color)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=1, stroke=0)
            c.setStrokeColor(COLOR_GRID)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=0, stroke=1)
            qty = totals_by_date.get(day, 0)
            if qty > 0:
                c.setFillColor(colors.black)
                c.setFont(font_name, font_size_cell + 1)
                txt = str(qty)
                tw = c.stringWidth(txt, font_name, font_size_cell + 1)
                c.drawString(x + date_col_w - tw - 1 * mm, y_pos - row_h + 1 * mm, txt)
            x += date_col_w
        return y_pos - row_h

    def calc_section_totals(section_data, page_dates):
        totals = {}
        for day in page_dates:
            totals[day] = sum(section_data.get(day, {}).get(code, 0) for code, _, _ in PRODUCT_ORDER_LAP)
        return totals

    def draw_section_page(page_dates, date_col_w, table_w, section_title, section_color, section_data, section_label):
        y = page_h - margin_top
        y = draw_page_header(y, page_dates, section_label=section_label)
        y = draw_date_header(y, page_dates, date_col_w)
        y = draw_section_header(y, section_title, section_color, table_w)
        for row_index, (product_code, label, label_color) in enumerate(PRODUCT_ORDER_LAP, start=1):
            name = product_names.get(product_code, '')
            row_data = {}
            for day in page_dates:
                qty = section_data.get(day, {}).get(product_code, 0)
                if qty > 0:
                    row_data[day] = qty
            row_bg = COLOR_ROW_ODD_BG if row_index % 2 == 1 else COLOR_ROW_EVEN_BG
            y = draw_product_row(y, product_code, label, name, row_data, page_dates, date_col_w, row_bg=row_bg, label_color=label_color)
        section_totals = calc_section_totals(section_data, page_dates)
        y = draw_total_row(y, f'{section_label}合計', section_totals, page_dates, date_col_w)
        return section_totals

    for page_dates in _chunk_dates(display_dates, PAGE_DAYS):
        date_col_w = max(
            (page_w - margin_left - margin_right - label_col_w) / max(len(page_dates), 1),
            12 * mm,
        )
        table_w = label_col_w + date_col_w * len(page_dates)

        am_totals = draw_section_page(page_dates, date_col_w, table_w, SECTION_TITLE_AM, COLOR_SECTION_AM, am_data, '午前便')
        c.showPage()

        pm_totals = draw_section_page(page_dates, date_col_w, table_w, SECTION_TITLE_PM, COLOR_SECTION_PM, pm_data, '午後便')
        c.showPage()

    c.save()
    buf.seek(0)
    return buf.read()


def generate_hokushin_delivery_list_new_pdf(
    line_id: int,
    start_date: date,
    end_date: date,
    creator_name: str = 'システム',
) -> bytes:
    """新品番ベースの北進納入リストPDF。新品番は常時表示、旧品番はデータありのみ表示。"""
    _register_fonts()

    line = Line.objects.filter(id=line_id).first()
    if not line:
        raise ValueError('ライン未検出')

    calendar_id = _get_calendar_id(line)
    cal_cache = _build_working_day_cache(calendar_id, start_date - timedelta(days=14), end_date + timedelta(days=14))
    display_dates = _get_display_dates(start_date, end_date)

    collection_order = list(PRODUCT_ORDER_NEW) + [
        (code, label, color) for code, label, color in PRODUCT_ORDER
        if code not in {c for c, _, _ in PRODUCT_ORDER_NEW}
    ]
    am_data, pm_data, product_names = _collect_hokushin_delivery_list_data(
        line_id, start_date, end_date, calendar_id, cal_cache,
        product_order=collection_order, use_alias=False,
    )

    render_order = _build_new_render_order(am_data, pm_data, display_dates)

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

    label_col_w = 58 * mm * (4 / 3)
    row_h = 5 * mm
    section_header_h = 5.5 * mm

    output_date = datetime.now().date()
    creator_label = str(creator_name or '').strip() or 'システム'

    def draw_page_header(y_pos, page_dates):
        c.setFont(font_name, font_size_title)
        c.drawString(margin_left, y_pos, '株式会社北進塗装　竹岡工場長様')
        y2 = y_pos - 5.5 * mm
        c.setFont(font_name, 8 * font_scale)
        c.setFillColor(colors.HexColor('#666666'))
        right_text = f'ダイソウ工業　{creator_label}'
        tw = c.stringWidth(right_text, font_name, 8 * font_scale)
        c.drawString(page_w - margin_right - tw, y2, right_text)
        if page_dates:
            range_text = f'{page_dates[0].strftime("%Y/%m/%d")} ～ {page_dates[-1].strftime("%Y/%m/%d")}'
            c.drawString(margin_left, y2 - 4.5 * mm, range_text)
        created_text = output_date.strftime('%Y/%m/%d')
        dw = c.stringWidth(created_text, font_name, 8 * font_scale)
        c.drawString(page_w - margin_right - dw, y2 - 4.5 * mm, created_text)
        c.setFillColor(colors.black)
        return y_pos - 13 * mm

    def draw_date_header(y_pos, page_dates, date_col_w):
        x = margin_left
        c.setFillColor(COLOR_HEADER_BG)
        c.rect(x, y_pos - row_h, label_col_w, row_h, fill=1, stroke=0)
        x += label_col_w
        for day in page_dates:
            is_weekend = day.weekday() >= 5
            c.setFillColor(COLOR_WEEKEND_BG if is_weekend else COLOR_HEADER_BG)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=1, stroke=0)
            c.setFillColor(COLOR_HEADER_TEXT)
            c.setFont(font_name, font_size_header)
            label = f'{day.month}/{day.day}'
            tw = c.stringWidth(label, font_name, font_size_header)
            c.drawString(x + (date_col_w - tw) / 2, y_pos - row_h + 1 * mm, label)
            x += date_col_w
        y_pos -= row_h
        x = margin_left
        c.setFillColor(COLOR_HEADER_BG)
        c.rect(x, y_pos - row_h, label_col_w, row_h, fill=1, stroke=0)
        x += label_col_w
        for day in page_dates:
            is_weekend = day.weekday() >= 5
            c.setFillColor(COLOR_WEEKEND_BG if is_weekend else COLOR_HEADER_BG)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=1, stroke=0)
            c.setFillColor(COLOR_HEADER_TEXT)
            c.setFont(font_name, font_size_header)
            weekday = JPN_WEEKDAYS[day.weekday()]
            tw = c.stringWidth(weekday, font_name, font_size_header)
            c.drawString(x + (date_col_w - tw) / 2, y_pos - row_h + 1 * mm, weekday)
            x += date_col_w
        return y_pos - row_h

    def draw_section_header(y_pos, title, bg_color, table_w):
        c.setFillColor(bg_color)
        c.rect(margin_left, y_pos - section_header_h, table_w, section_header_h, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont(font_name, font_size_header + 1)
        c.drawString(margin_left + 2 * mm, y_pos - section_header_h + 1.5 * mm, title)
        return y_pos - section_header_h

    def draw_product_row(y_pos, product_code, label, name, data_by_date, page_dates, date_col_w, row_bg=None, label_color=None):
        x = margin_left
        if row_bg:
            c.setFillColor(row_bg)
            c.rect(x, y_pos - row_h, label_col_w, row_h, fill=1, stroke=0)
        c.setStrokeColor(COLOR_GRID)
        c.rect(x, y_pos - row_h, label_col_w, row_h, fill=0, stroke=1)
        c.setFillColor(label_color or colors.black)
        c.setFont(font_name, font_size_cell)
        display_code = product_code[:-1] if str(product_code).endswith('T') else str(product_code)
        short_name = _extract_short_name(name)
        text = f'{label}{display_code}{short_name}' if short_name else f'{label}{display_code}'
        c.drawString(x + 0.5 * mm, y_pos - row_h + 1 * mm, text)
        x += label_col_w
        for day in page_dates:
            is_weekend = day.weekday() >= 5
            bg = COLOR_WEEKEND_BG if is_weekend else row_bg
            if bg:
                c.setFillColor(bg)
                c.rect(x, y_pos - row_h, date_col_w, row_h, fill=1, stroke=0)
            c.setStrokeColor(COLOR_GRID)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=0, stroke=1)
            qty = data_by_date.get(day, 0)
            if qty > 0:
                c.setFillColor(label_color or colors.black)
                c.setFont(font_name, font_size_cell)
                txt = str(qty)
                tw = c.stringWidth(txt, font_name, font_size_cell)
                c.drawString(x + date_col_w - tw - 1 * mm, y_pos - row_h + 1 * mm, txt)
            x += date_col_w
        return y_pos - row_h

    def draw_total_row(y_pos, title, totals_by_date, page_dates, date_col_w, bg_color=COLOR_TOTAL_BG):
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
        for day in page_dates:
            is_weekend = day.weekday() >= 5
            c.setFillColor(COLOR_WEEKEND_BG if is_weekend else bg_color)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=1, stroke=0)
            c.setStrokeColor(COLOR_GRID)
            c.rect(x, y_pos - row_h, date_col_w, row_h, fill=0, stroke=1)
            qty = totals_by_date.get(day, 0)
            if qty > 0:
                c.setFillColor(colors.black)
                c.setFont(font_name, font_size_cell + 1)
                txt = str(qty)
                tw = c.stringWidth(txt, font_name, font_size_cell + 1)
                c.drawString(x + date_col_w - tw - 1 * mm, y_pos - row_h + 1 * mm, txt)
            x += date_col_w
        return y_pos - row_h

    def calc_section_totals(section_data, page_dates):
        totals = {}
        for day in page_dates:
            totals[day] = sum(section_data.get(day, {}).get(code, 0) for code, _, _ in render_order)
        return totals

    for page_dates in _chunk_dates(display_dates, PAGE_DAYS):
        date_col_w = max(
            (page_w - margin_left - margin_right - label_col_w) / max(len(page_dates), 1),
            12 * mm,
        )
        table_w = label_col_w + date_col_w * len(page_dates)

        y = page_h - margin_top
        y = draw_page_header(y, page_dates)
        y = draw_date_header(y, page_dates, date_col_w)

        y = draw_section_header(y, SECTION_TITLE_AM, COLOR_SECTION_AM, table_w)
        for row_index, (product_code, label, label_color) in enumerate(render_order, start=1):
            name = product_names.get(product_code, '')
            row_data = {}
            for day in page_dates:
                qty = am_data.get(day, {}).get(product_code, 0)
                if qty > 0:
                    row_data[day] = qty
            row_bg = COLOR_ROW_ODD_BG if row_index % 2 == 1 else COLOR_ROW_EVEN_BG
            y = draw_product_row(y, product_code, label, name, row_data, page_dates, date_col_w, row_bg=row_bg, label_color=label_color)
        am_totals = calc_section_totals(am_data, page_dates)
        y = draw_total_row(y, '午前便合計', am_totals, page_dates, date_col_w)

        y = draw_section_header(y, SECTION_TITLE_PM, COLOR_SECTION_PM, table_w)
        for row_index, (product_code, label, label_color) in enumerate(render_order, start=1):
            name = product_names.get(product_code, '')
            row_data = {}
            for day in page_dates:
                qty = pm_data.get(day, {}).get(product_code, 0)
                if qty > 0:
                    row_data[day] = qty
            row_bg = COLOR_ROW_ODD_BG if row_index % 2 == 1 else COLOR_ROW_EVEN_BG
            y = draw_product_row(y, product_code, label, name, row_data, page_dates, date_col_w, row_bg=row_bg, label_color=label_color)
        pm_totals = calc_section_totals(pm_data, page_dates)
        y = draw_total_row(y, '午後便合計', pm_totals, page_dates, date_col_w)

        grand_totals = {day: am_totals.get(day, 0) + pm_totals.get(day, 0) for day in page_dates}
        y = draw_total_row(y, '総合計', grand_totals, page_dates, date_col_w, bg_color=COLOR_GRAND_TOTAL_BG)

        c.showPage()

    c.save()
    buf.seek(0)
    return buf.read()
