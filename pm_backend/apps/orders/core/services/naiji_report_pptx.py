"""内示分析PPTXレポート生成

compute_naiji_report_data() の結果を受け取り、課題提起用のPPTXスライドを生成する。
"""
import io
from datetime import date, datetime

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# --- カラー定義 ---
NAVY = RGBColor(0x1B, 0x3A, 0x5C)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xF5, 0xF6, 0xF8)
BORDER_GRAY = RGBColor(0xCC, 0xCC, 0xCC)
DARK_TEXT = RGBColor(0x33, 0x33, 0x33)
GRAY_TEXT = RGBColor(0x66, 0x66, 0x66)
SUBTLE_TEXT = RGBColor(0x8C, 0x95, 0xA4)
RED = RGBColor(0xC6, 0x28, 0x28)
ORANGE = RGBColor(0xE8, 0x95, 0x0A)
BLUE = RGBColor(0x5C, 0x8A, 0xBE)
GREEN = RGBColor(0x2E, 0x7D, 0x32)
RED_BG = RGBColor(0xFF, 0xEB, 0xEE)
YELLOW_BG = RGBColor(0xFF, 0xF8, 0xE1)
BLUE_BG = RGBColor(0xE3, 0xF2, 0xFD)

SLIDE_W_IN = 13.333
SLIDE_H_IN = 7.5


# ---------------------------------------------------------------------------
# 描画ヘルパー
# ---------------------------------------------------------------------------
def _rect(slide, l, t, w, h, color, shape=MSO_SHAPE.RECTANGLE):
    shp = slide.shapes.add_shape(shape, Inches(l), Inches(t), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def _text(slide, l, t, w, h, text, size=12, bold=False, color=DARK_TEXT,
          align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, wrap=True):
    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return box


def _new_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _title_bar(slide, title, subtitle=None):
    height = 1.0 if not subtitle else 0.85
    _rect(slide, 0, 0, SLIDE_W_IN, height, NAVY)
    _text(slide, 0.5, 0.15, 12.0, 0.5, title, size=22, bold=True, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
    if subtitle:
        _text(slide, 0.5, 0.62, 12.0, 0.3, subtitle, size=11, color=RGBColor(0xC5, 0xD3, 0xE6))


def _pname(p):
    return f"{p['product_code']} ({p['ship_to']})" if p.get('ship_to') else p['product_code']


def _fmt(v, unit=''):
    if v is None:
        return '—'
    return f'{v}{unit}'


def _add_table(slide, l, t, w, h, headers, rows, col_widths=None,
                header_color=NAVY, alt_color=LIGHT_GRAY, font_size=11, header_font_size=None):
    """dark header row + alternating row colors のテーブルを描画"""
    n_rows = len(rows) + 1
    n_cols = len(headers)
    shp = slide.shapes.add_table(n_rows, n_cols, Inches(l), Inches(t), Inches(w), Inches(h))
    table = shp.table
    if col_widths:
        for i, cw in enumerate(col_widths):
            table.columns[i].width = Inches(cw)

    for c, htext in enumerate(headers):
        cell = table.cell(0, c)
        cell.text = str(htext)
        cell.fill.solid()
        cell.fill.fore_color.rgb = header_color
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = cell.margin_right = Inches(0.03)
        for para in cell.text_frame.paragraphs:
            para.alignment = PP_ALIGN.CENTER
            for r in para.runs:
                r.font.color.rgb = WHITE
                r.font.bold = True
                r.font.size = Pt(header_font_size or font_size)

    for ri, row in enumerate(rows, start=1):
        bg = alt_color if ri % 2 == 0 else WHITE
        for c, val in enumerate(row):
            cell = table.cell(ri, c)
            cell.text = str(val)
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = cell.margin_right = Inches(0.03)
            for para in cell.text_frame.paragraphs:
                para.alignment = PP_ALIGN.CENTER if c > 0 else PP_ALIGN.LEFT
                for r in para.runs:
                    r.font.size = Pt(font_size)
                    r.font.color.rgb = DARK_TEXT
    return table


def _stacked_bar(slide, l, t, w, h, segments, n_label=None):
    """segments: [(pct, count, color, label), ...]"""
    total = sum(s[0] for s in segments) or 1
    x = l
    for pct, count, color, _label in segments:
        seg_w = w * pct / total
        if seg_w > 0.001:
            _rect(slide, x, t, seg_w, h, color)
            if seg_w > 0.35:
                _text(slide, x, t, seg_w, h, f'{round(pct)}%', size=10, bold=True, color=WHITE,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        x += seg_w
    if n_label:
        _text(slide, l + w + 0.08, t, 0.8, h, n_label, size=10, color=GRAY_TEXT, anchor=MSO_ANCHOR.MIDDLE)


def _bar_chart(slide, l, t, w, h, points, color=BLUE, highlight_pred=None, highlight_color=RED):
    """points: [{'label': str, 'value': number}, ...] の縦棒グラフ"""
    n = len(points)
    if n == 0:
        return
    gap = min(0.06, w / n * 0.15)
    bar_w = (w - gap * (n - 1)) / n if n > 1 else min(w, 0.5)
    max_val = max(p['value'] for p in points) or 1
    x = l
    for p in points:
        val = p['value']
        bar_h = h * (val / max_val) if max_val else 0
        bar_h = max(bar_h, 0.03)
        color_i = highlight_color if (highlight_pred and highlight_pred(p)) else color
        _rect(slide, x, t + h - bar_h, bar_w, bar_h, color_i)
        val_str = str(int(val)) if isinstance(val, (int, float)) and val == int(val) else str(val)
        _text(slide, x - 0.15, t + h - bar_h - 0.2, bar_w + 0.3, 0.18, val_str, size=7,
              align=PP_ALIGN.CENTER)
        _text(slide, x - 0.15, t + h + 0.02, bar_w + 0.3, 0.16, p['label'], size=6.5,
              align=PP_ALIGN.CENTER, color=GRAY_TEXT)
        x += bar_w + gap


def _fmt_ym(iso_str):
    if not iso_str:
        return ''
    return iso_str.replace('-', '/')


def _fmt_md(iso_str):
    if not iso_str:
        return ''
    return iso_str[5:].replace('-', '/')


def _fmt_jp_date(iso_str):
    if not iso_str:
        return ''
    d = date.fromisoformat(iso_str)
    return f'{d.year}年{d.month}月{d.day}日'


# ---------------------------------------------------------------------------
# スライド1: タイトル
# ---------------------------------------------------------------------------
def _build_slide1(prs, data):
    slide = _new_slide(prs)
    _rect(slide, 0, 0, SLIDE_W_IN, SLIDE_H_IN, NAVY)
    _text(slide, 1.0, 1.5, 11.0, 0.71, '内示分析レポート', size=36, bold=True, color=WHITE)
    _text(slide, 1.0, 2.8, 11.0, 0.5, data['customer_name'], size=20, color=WHITE)

    stats = (
        f"確定注文（分析対象）: {_fmt(data['firm_due_min'])}〜{_fmt(data['firm_due_max'])}納期/品番 "
        f"({_fmt_ym(data['first_firm_date'])}〜{_fmt_ym(data['last_firm_date'])})"
        f"  |  内示データ: {data['snapshot_count']}回分"
    )
    _text(slide, 1.0, 5.0, 11.0, 0.34, stats, size=13, color=SUBTLE_TEXT)
    _text(slide, 1.0, 5.5, 11.0, 0.5, f'作成日: {_fmt_jp_date(date.today().isoformat())}', size=13, color=WHITE)


# ---------------------------------------------------------------------------
# スライド2: 概要
# ---------------------------------------------------------------------------
def _build_slide2(prs, data):
    slide = _new_slide(prs)
    _title_bar(slide, '概要 — 分析対象と4つの課題')

    products = data['products']
    _text(slide, 0.5, 1.2, 5.0, 0.4, f'分析対象製品（{len(products)}品番）', size=13, bold=True)
    max_show = 10
    shown = products[:max_show]
    row_h = min(0.35, 1.7 / max(len(shown), 1))
    y = 1.7
    for p in shown:
        _text(slide, 0.7, y, 2.0, row_h, p['product_code'], size=10)
        _text(slide, 2.8, y, 0.8, row_h, f"({p['ship_to']})" if p['ship_to'] else '', size=10, color=GRAY_TEXT)
        _text(slide, 3.7, y, 2.4, row_h, p['product_name'], size=10, color=GRAY_TEXT)
        y += row_h
    if len(products) > max_show:
        _text(slide, 0.7, y, 5.0, 0.3, f'…他 {len(products) - max_show} 品番', size=10, color=GRAY_TEXT)

    _text(slide, 0.5, 3.44, 12.0, 0.32,
          '以下4点の課題により、内示情報が生産計画の前提として機能していない状況です。', size=12)

    ov = data['overview']
    cards = [
        (f"{_fmt(ov['within7_pct_min'])}~{_fmt(ov['within7_pct_max'])}%", '収束7日以内の割合',
         '内示数＝確定数の日数が少なく直前まで内示が参照価値がない', RED_BG),
        (f"平均{_fmt(ov['avg_change_count_min'])}~{_fmt(ov['avg_change_count_max'])}回", '1納期あたり平均変動回数',
         '内示更新で毎回数量が変わる', RED_BG),
        (f"最大{_fmt(ov['max_divergence_pct'])}%", '確定直前の乖離',
         '納期5営業日前の内示と確定数量が大幅乖離', YELLOW_BG),
        (f"CV {_fmt(ov['cv_min'])}~{_fmt(ov['cv_max'])}%", '確定数量のばらつき',
         '同製品でも日ごとに確定数量が大きく異なる', YELLOW_BG),
    ]
    xs = [0.5, 3.55, 6.6, 9.65]
    for (val, label, desc, bg), x in zip(cards, xs):
        _rect(slide, x, 3.9, 2.85, 2.8, bg, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        _text(slide, x + 0.1, 4.1, 2.65, 0.6, val, size=20, bold=True)
        _text(slide, x + 0.1, 4.75, 2.65, 0.35, label, size=12, bold=True)
        _text(slide, x + 0.1, 5.2, 2.65, 1.2, desc, size=10, color=GRAY_TEXT)


# ---------------------------------------------------------------------------
# スライド3: 収束分布（帯グラフ）
# ---------------------------------------------------------------------------
def _build_slide3(prs, data):
    slide = _new_slide(prs)
    _title_bar(slide, '課題1: 収束が遅い — 納期まで参照できる日数が短い')

    ov = data['overview']
    _text(slide, 0.5, 1.2, 12.0, 0.6,
          f"収束日数が長いほど早期に安定 = 良い状態。"
          f"全製品で{_fmt(ov['within7_pct_min'])}~{_fmt(ov['within7_pct_max'])}%が<=7営業日でようやく収束。",
          size=12)
    _text(slide, 0.5, 1.8, 6.0, 0.4, '収束日数の分布（営業日ベース）', size=13, bold=True)

    products = data['products']
    max_rows = min(len(products), 10)
    row_h = min(0.65, 3.7 / max(max_rows, 1))
    bar_h = min(0.35, row_h - 0.1)
    y = 2.3
    for p in products[:max_rows]:
        dist = p['summary'].get('stable_days_dist')
        _text(slide, 0.5, y, 3.0, row_h, _pname(p), size=11)
        if dist:
            segments = [
                (dist['within_7_pct'], dist['within_7'], RED, '<=7日'),
                (dist['within_8_14_pct'], dist['within_8_14'], ORANGE, '8-14日'),
                (dist['within_15_21_pct'], dist['within_15_21'], BLUE, '15-21日'),
                (dist['over_21_pct'], dist['over_21'], GREEN, '22日+'),
            ]
            _stacked_bar(slide, 3.5, y + 0.05, 8.1, bar_h, segments,
                         n_label=f"n={p['summary'].get('stable_days_count') or 0}")
        else:
            _text(slide, 3.5, y, 8.0, bar_h, 'データなし', size=10, color=GRAY_TEXT)
        y += row_h
    if len(products) > max_rows:
        _text(slide, 0.5, y, 6.0, 0.25, f'…他 {len(products) - max_rows} 品番', size=9, color=GRAY_TEXT)
        y += 0.25

    legend_y = y + 0.15
    legend_items = [
        (RED, '<=7営業日（問題）'), (ORANGE, '8-14営業日（ギリギリ）'),
        (BLUE, '15-21営業日（許容）'), (GREEN, '22営業日+（良好）'),
    ]
    x = 0.5
    for color, label in legend_items:
        _rect(slide, x, legend_y, 0.2, 0.2, color)
        _text(slide, x + 0.3, legend_y - 0.05, 2.3, 0.3, label, size=10)
        x += 3.0

    _rect(slide, 0.5, 6.6, 12.3, 0.6, RED_BG)
    _text(slide, 0.7, 6.65, 11.8, 0.5,
          f"結論: 全製品で{_fmt(ov['within7_pct_min'])}~{_fmt(ov['within7_pct_max'])}%の納期が、"
          f"納期の7営業日前まで安定しない。直前まで計画の前提として機能していない。",
          size=12)


# ---------------------------------------------------------------------------
# スライド4: 収束日数サマリー表
# ---------------------------------------------------------------------------
def _build_slide4(prs, data):
    slide = _new_slide(prs)
    _title_bar(slide, '課題1: 収束日数サマリー')

    headers = ['品番', '納入地', '対象納期数', '平均', '中央値', '<=7日', '22日+']
    rows = []
    for p in data['products']:
        s = p['summary']
        dist = s.get('stable_days_dist')
        rows.append([
            p['product_code'],
            p['ship_to'] or '—',
            _fmt(s.get('stable_days_count')),
            f"{s['stable_days_mean']}日" if s.get('stable_days_mean') is not None else '—',
            f"{s['stable_days_median']}日" if s.get('stable_days_median') is not None else '—',
            f"{dist['within_7']} ({dist['within_7_pct']}%)" if dist else '—',
            f"{dist['over_21']} ({dist['over_21_pct']}%)" if dist else '—',
        ])
    _add_table(slide, 0.5, 1.3, 12.3, min(0.5 + 0.4 * len(rows), 5.0), headers, rows,
               col_widths=[2.3, 1.3, 1.7, 1.7, 1.7, 1.8, 1.8])

    ov = data['overview']
    _rect(slide, 0.5, 6.8, 12.3, 0.55, RED_BG)
    _text(slide, 0.7, 6.85, 11.8, 0.5,
          f"結論: 全製品で{_fmt(ov['within7_pct_min'])}~{_fmt(ov['within7_pct_max'])}%の納期が"
          f"7営業日以内でしか収束せず、材料調達・計画の参照として機能していない。",
          size=12)


# ---------------------------------------------------------------------------
# スライド5: 途中変動
# ---------------------------------------------------------------------------
def _build_slide5(prs, data):
    slide = _new_slide(prs)
    _title_bar(slide, '課題2: 途中変動が大きい — 日々の内示更新で数量が安定しない')
    _text(slide, 0.5, 1.15, 12.0, 0.5,
          '各納期に対して、内示が更新されるたびに前回と数量が変わった回数を計測。', size=12)

    products = data['products']
    _text(slide, 0.5, 1.7, 6.0, 0.4, '1納期あたり平均変動回数', size=13, bold=True)
    max_avg = max((p['volatility']['avg_change_count'] for p in products), default=1) or 1
    max_rows = min(len(products), 10)
    row_h = min(0.6, 3.75 / max(max_rows, 1))
    bar_h = min(0.25, row_h - 0.15)
    y = 2.15
    for p in products[:max_rows]:
        avg_c = p['volatility']['avg_change_count']
        _text(slide, 0.3, y, 2.8, row_h, _pname(p), size=10)
        _text(slide, 3.2, y, 0.8, row_h, f'{avg_c}', size=11, bold=True)
        _text(slide, 4.0, y, 0.3, row_h, '回', size=10)
        _rect(slide, 4.3, y + 0.05, 2.3, bar_h, LIGHT_GRAY)
        bar_w = 2.3 * avg_c / max_avg if max_avg else 0
        if bar_w > 0:
            _rect(slide, 4.3, y + 0.05, bar_w, bar_h, RED)
        y += row_h
    if len(products) > max_rows:
        _text(slide, 0.3, y, 6.0, 0.25, f'…他 {len(products) - max_rows} 品番', size=9, color=GRAY_TEXT)
        y += 0.25

    if products:
        counts = [(p, p['volatility']['max_change_count']) for p in products if p['volatility']['example']]
        min_c = min((c for _, c in counts), default=0)
        max_c = max((c for _, c in counts), default=0)
        _text(slide, 0.5, y + 0.15, 6.0, 0.3,
              f"内示更新に対して、各納期平均{_fmt(min_c)}~{_fmt(max_c)}回数量が変動", size=11)

    _rect(slide, 0.5, 6.6, 12.3, 0.7, RED_BG)
    ov = data['overview']
    _text(slide, 0.7, 6.65, 11.8, 0.6,
          f"結論: 1つの納期に対し平均{_fmt(ov['avg_change_count_min'])}~{_fmt(ov['avg_change_count_max'])}回の"
          f"数量変動が発生。内示を信頼した生産計画・部材手配が困難な状況。", size=12)


# ---------------------------------------------------------------------------
# スライド5b: 途中変動 具体例
# ---------------------------------------------------------------------------
def _build_slide5b(prs, data):
    products = data['products']
    best = None
    for p in products:
        ex = p['volatility']['example']
        if ex and (best is None or ex['change_count'] > best[1]['change_count']):
            best = (p, ex)
    if not best:
        return
    p, ex = best
    slide = _new_slide(prs)
    _title_bar(slide, '課題2: 途中変動 — 具体例')
    _text(slide, 0.5, 1.3, 12.0, 0.5,
          f"{_pname(p)}  納期 {ex['due_date']}  ({ex['change_count']}回変動)",
          size=18, bold=True)
    points = [{'label': s['snapshot_date'][5:], 'value': s['qty']} for s in ex['series']]
    max_idx = max(range(len(points)), key=lambda i: points[i]['value']) if points else None
    _bar_chart(slide, 0.8, 2.2, 11.5, 3.5, points, color=BLUE,
               highlight_pred=lambda pt: max_idx is not None and pt is points[max_idx])
    _text(slide, 0.8, 6.0, 11.0, 0.3, '内示受信日', size=11, color=GRAY_TEXT)
    series_str = '→'.join(str(int(pt['value'])) for pt in points[:8])
    _text(slide, 0.8, 6.4, 11.5, 0.5,
          f"{series_str}... 1つの納期に対して{ex['change_count']}回も数量変動。計画の前提にならない。",
          size=13, color=GRAY_TEXT)


# ---------------------------------------------------------------------------
# スライド6: 確定直前の急変イベント表
# ---------------------------------------------------------------------------
def _build_slide6(prs, data):
    slide = _new_slide(prs)
    _title_bar(slide, '課題3: 確定直前・確定日で急変 — 5営業日前の内示と確定が大幅乖離')
    _text(slide, 0.5, 1.2, 12.0, 0.32, '納期5営業日前時点の内示数量と、実際の確定注文数量を比較。', size=12)

    headers = ['品番', '納入地', '<=5日変動数\n（統計範囲内の回数）', 'うち大幅変動(>=20%)', '大幅変動率']
    rows = []
    for p in data['products']:
        lm = p['last_minute']
        rows.append([
            p['product_code'], p['ship_to'] or '—',
            lm['total_events'], lm['large_events'],
            f"{lm['large_rate']}%" if lm['large_rate'] is not None else '—',
        ])
    _add_table(slide, 0.8, 1.8, 11.0, min(0.5 + 0.45 * len(rows), 4.3), headers, rows,
               col_widths=[2.5, 1.5, 3.0, 2.5, 1.5])

    ov = data['overview']
    total_events = sum(p['last_minute']['total_events'] for p in data['products'])
    large_rates = [p['last_minute']['large_rate'] for p in data['products'] if p['last_minute']['large_rate'] is not None]
    _rect(slide, 0.5, 6.4, 12.3, 0.8, RED_BG)
    _text(slide, 0.7, 6.45, 11.8, 0.7,
          f"確定直前の変動イベント計{total_events}件のうち"
          f"{_fmt(round(min(large_rates)) if large_rates else None)}~{_fmt(round(max(large_rates)) if large_rates else None)}%"
          f"が20%以上の大幅変動。急減・急増パターンとも、先行手配した部材が過剰在庫・欠品となるリスクが恒常的に発生"
          f"（急減 {ov['overstock_events']}件 / 急増 {ov['shortage_events']}件）。",
          size=11)


# ---------------------------------------------------------------------------
# スライド7・8: 乖離事例
# ---------------------------------------------------------------------------
def _collect_events(products, direction, limit=15):
    events = []
    for p in products:
        for d in p['last_minute']['divergences']:
            if d['direction'] != direction or d['pct'] is None:
                continue
            events.append({**d, 'product_code': p['product_code'], 'ship_to': p['ship_to']})
    events.sort(key=lambda e: abs(e['pct']), reverse=True)
    return events[:limit]


def _build_slide7(prs, data):
    slide = _new_slide(prs)
    _title_bar(slide, '課題3: 確定直前 乖離事例（内示 ＞ 確定）')
    _text(slide, 0.5, 1.15, 12.0, 0.3, '急減パターン: 先行手配した部材が過剰在庫となるリスク', size=11, color=GRAY_TEXT)

    events = _collect_events(data['products'], 'overstock')
    headers = ['品番', '納入地', '納期', '5日前内示', '確定数量', '差', '乖離率']
    rows = [
        [e['product_code'], e['ship_to'] or '—', e['due_date'], e['snapshot_qty'], e['firm_qty'],
         f"{e['diff']:+g}", f"{e['pct']:+g}%"]
        for e in events
    ]
    if rows:
        _add_table(slide, 0.8, 1.6, 11.0, min(0.4 + 0.36 * len(rows), 5.2), headers, rows,
                   col_widths=[2.2, 1.2, 1.6, 1.7, 1.7, 1.3, 1.3])
    else:
        _text(slide, 0.8, 2.0, 10.0, 0.4, '該当する事例はありません', size=12, color=GRAY_TEXT)


def _build_slide8(prs, data):
    slide = _new_slide(prs)
    _title_bar(slide, '課題3: 確定直前 乖離事例（内示 ＜ 確定）')
    _text(slide, 0.5, 1.15, 12.0, 0.3,
          '急増パターン: 材料不足・ライン変更・残業対応を引き起こすリスク', size=11, color=GRAY_TEXT)

    events = _collect_events(data['products'], 'shortage')
    headers = ['品番', '納入地', '納期', '5日前内示', '確定数量', '差', '増加率']
    rows = [
        [e['product_code'], e['ship_to'] or '—', e['due_date'], e['snapshot_qty'], e['firm_qty'],
         f"{e['diff']:+g}", f"{e['pct']:+g}%"]
        for e in events
    ]
    if rows:
        _add_table(slide, 0.8, 1.6, 11.0, min(0.4 + 0.36 * len(rows), 4.2), headers, rows,
                   col_widths=[2.2, 1.2, 1.6, 1.7, 1.7, 1.3, 1.3])
    else:
        _text(slide, 0.8, 2.0, 10.0, 0.4, '該当する事例はありません', size=12, color=GRAY_TEXT)

    ov = data['overview']
    _text(slide, 0.8, 5.7, 8.0, 0.35, '急減 vs 急増 パターン比較', size=13, bold=True)
    _rect(slide, 0.8, 6.15, 4.5, 1.05, RED_BG)
    _text(slide, 1.0, 6.2, 4.1, 0.3, '急減（内示 > 確定）', size=11, bold=True)
    _text(slide, 1.0, 6.55, 4.1, 0.55,
          f"{ov['overstock_events']}件 — 過剰在庫・置き場リスク", size=10, color=GRAY_TEXT)
    _rect(slide, 5.6, 6.15, 4.5, 1.05, YELLOW_BG)
    _text(slide, 5.8, 6.2, 4.1, 0.3, '急増（確定 > 内示）', size=11, bold=True)
    _text(slide, 5.8, 6.55, 4.1, 0.55,
          f"{ov['shortage_events']}件 — 材料不足・緊急発注リスク", size=10, color=GRAY_TEXT)
    _text(slide, 10.4, 6.2, 2.4, 1.0, 'どちらのパターンも5営業日前の内示が計画根拠として機能していない証拠', size=9,
          color=GRAY_TEXT)


# ---------------------------------------------------------------------------
# スライド9: 確定数量のばらつき
# ---------------------------------------------------------------------------
def _build_slide9(prs, data):
    slide = _new_slide(prs)
    _title_bar(slide, '課題4: 確定数量のばらつき — 同製品でも日ごとに数量が大きく異なる')
    _text(slide, 0.5, 1.05, 12.0, 0.4,
          '同じ製品の確定注文数量が納期日ごとにどれだけばらつくかを統計。'
          'CV(変動係数)=標準偏差/平均で、数値が大きいほどばらつきが激しい。', size=11)

    headers = ['品番', '納入地', '納期数', '平均', '標準偏差', 'CV', '最小', '最大', 'レンジ', '日間差平均', '日間差最大']
    rows = []
    best_cv_product = None
    for p in data['products']:
        fv = p['firm_variability']
        if not fv:
            rows.append([p['product_code'], p['ship_to'] or '—'] + ['—'] * 9)
            continue
        if best_cv_product is None or fv['cv'] > best_cv_product[1]['cv']:
            best_cv_product = (p, fv)
        rows.append([
            p['product_code'], p['ship_to'] or '—', fv['count'], fv['mean'], fv['std_dev'],
            f"{fv['cv']}%", fv['min'], fv['max'], fv['range'],
            _fmt(fv['diff_mean']), _fmt(fv['diff_max']),
        ])
    _add_table(slide, 0.4, 1.6, 12.5, min(0.4 + 0.34 * len(rows), 2.2), headers, rows,
               col_widths=[1.7, 1.0, 0.9, 1.0, 1.1, 0.9, 0.9, 0.9, 0.9, 1.3, 1.3], font_size=9.5,
               header_font_size=9)

    if best_cv_product:
        p, fv = best_cv_product
        _text(slide, 0.5, 4.1, 12.0, 0.35,
              f"具体例: {_pname(p)} 確定数量の推移（直近25納期・CV最大）", size=12, bold=True)
        series = fv['series'][-25:]
        points = [{'label': s['due_date'][5:], 'value': s['qty']} for s in series]
        _bar_chart(slide, 0.7, 4.6, 12.0, 1.7, points, color=BLUE)

    ov = data['overview']
    _rect(slide, 0.5, 6.85, 12.3, 0.5, RED_BG)
    _text(slide, 0.7, 6.88, 11.8, 0.45,
          f"結論: 確定数量の変動係数(CV)が{_fmt(ov['cv_min'])}~{_fmt(ov['cv_max'])}%と高く、"
          f"同じ製品でも日によって数量が大きく異なる。安定した生産ロット編成が困難。", size=11)


# ---------------------------------------------------------------------------
# スライド9b: 3か月前内示と確定の月別乖離
# ---------------------------------------------------------------------------
def _build_slide9b(prs, data):
    slide = _new_slide(prs)
    _title_bar(slide, '課題5: 2か月前内示と確定の乖離 — 要員計画への影響')
    _text(slide, 0.5, 1.15, 12.0, 0.5,
          '各月の日当たり確定数量に対して、2か月前（前半月1〜15日）の日当たり内示数量がどれだけ乖離していたかを比較。'
          '乖離が大きいと要員の過不足が発生する。', size=12)

    products = data['products']
    all_months = sorted({
        d['month']
        for p in products if p.get('monthly_deviation')
        for d in p['monthly_deviation']['deviations']
    })

    if not all_months:
        _text(slide, 0.5, 2.5, 12.0, 0.5, 'データ不足のため表示できません。', size=14)
        return

    month_labels = [m[5:] + '月' for m in all_months]
    headers = ['品番', '納入地'] + month_labels
    rows = []
    for p in products:
        md = p.get('monthly_deviation')
        if not md:
            continue
        dev_map = {d['month']: d for d in md['deviations']}
        row = [p['product_code'], p['ship_to'] or '—']
        for m in all_months:
            d = dev_map.get(m)
            if d and d['pct'] is not None:
                row.append(f"{d['pct']:+.1f}%")
            else:
                row.append('—')
        rows.append(row)

    col_w_first = 2.0
    col_w_ship = 1.0
    remaining = 12.3 - col_w_first - col_w_ship
    col_w_month = min(1.2, remaining / len(all_months)) if all_months else 1.2
    col_widths = [col_w_first, col_w_ship] + [col_w_month] * len(all_months)

    _add_table(slide, 0.5, 2.0, 12.3, min(0.5 + 0.4 * len(rows), 4.0), headers, rows,
               col_widths=col_widths)

    avg_pcts = [p['monthly_deviation']['avg_pct'] for p in products
                if p.get('monthly_deviation') and p['monthly_deviation']['avg_pct'] is not None]
    if avg_pcts:
        overall_min = min(avg_pcts)
        overall_max = max(avg_pcts)
        _rect(slide, 0.5, 6.85, 12.3, 0.5, RED_BG)
        _text(slide, 0.7, 6.88, 11.8, 0.45,
              f"結論: 2か月前の内示と確定の平均乖離率が{_fmt(overall_min)}~{_fmt(overall_max)}%。"
              f"内示精度の低さが要員計画・材料調達の過不足に直結している。", size=11)


# ---------------------------------------------------------------------------
# スライド10: リードタイムと確定タイミング（簡易版）
# ---------------------------------------------------------------------------
def _build_slide10(prs, data):
    slide = _new_slide(prs)
    _title_bar(slide, '工程リードタイムと確定タイミングによる内示精度の必要性')

    _text(slide, 0.5, 1.2, 12.0, 0.4, '一般的な生産工程イメージ（材料調達 〜 出荷）', size=13, bold=True)
    steps = ['材料調達', '加工', '組立', '検査', '出荷']
    n = len(steps)
    seg_w = 10.5 / n
    x = 1.0
    for i, step in enumerate(steps):
        gray = 0x37 + i * 0x18
        color = RGBColor(gray, gray + 0x10, gray + 0x20)
        _rect(slide, x, 1.7, seg_w - 0.05, 0.55, color)
        _text(slide, x, 1.82, seg_w - 0.05, 0.3, step, size=11, color=WHITE, align=PP_ALIGN.CENTER)
        x += seg_w

    _text(slide, 1.0, 2.4, 10.0, 0.3, '← 納期に向けて工程を消化 →', size=10, color=GRAY_TEXT)

    ov = data['overview']
    _text(slide, 0.5, 3.0, 11.0, 0.35, '内示 vs 確定タイミングの構造的な問題', size=13, bold=True)
    _rect(slide, 0.5, 3.5, 3.9, 2.1, RED_BG)
    _rect(slide, 0.5, 3.5, 3.9, 0.06, RED)
    _text(slide, 0.7, 3.65, 3.5, 0.3, '材料調達が間に合わない', size=12, bold=True)
    _text(slide, 0.7, 4.0, 3.5, 1.5,
          '材料調達には一定のリードタイムが必要だが、内示は納期直前まで安定しないため、'
          '内示を信じて先行発注するしかない。', size=10, color=GRAY_TEXT)

    _rect(slide, 4.7, 3.5, 3.9, 2.1, YELLOW_BG)
    _rect(slide, 4.7, 3.5, 3.9, 0.06, ORANGE)
    _text(slide, 4.9, 3.65, 3.5, 0.3, '出荷・便手配のやり直し', size=12, bold=True)
    _text(slide, 4.9, 4.0, 3.5, 1.5,
          '先行生産・均し生産を実行後、確定日の急増・急減で出荷数量が変動すると、'
          '便手配のやり直しが必要になる。', size=10, color=GRAY_TEXT)

    _rect(slide, 8.9, 3.5, 3.9, 2.1, BLUE_BG)
    _rect(slide, 8.9, 3.5, 3.9, 0.06, RGBColor(0x15, 0x65, 0xC0))
    _text(slide, 9.1, 3.65, 3.5, 0.3, 'どちらに転んでもコスト増', size=12, bold=True)
    _text(slide, 9.1, 4.0, 3.5, 1.5,
          '内示で先行発注→急減で過剰在庫。確定を待つ→材料不足で欠品。'
          '緊急発注・残業・事務処理増が常態化。', size=10, color=GRAY_TEXT)

    _text(slide, 0.5, 5.9, 12.0, 0.4,
          f"確定5営業日前時点の内示が確定と乖離する割合は"
          f"{_fmt(min((p['last_minute']['large_rate'] for p in data['products'] if p['last_minute']['large_rate'] is not None), default=None))}"
          f"~{_fmt(max((p['last_minute']['large_rate'] for p in data['products'] if p['last_minute']['large_rate'] is not None), default=None))}%"
          f"。収束7日以内の割合も{_fmt(ov['within7_pct_min'])}~{_fmt(ov['within7_pct_max'])}%と高く、"
          f"内示が計画の参照として機能する期間が極めて短い。", size=11)


# ---------------------------------------------------------------------------
# スライド11: 影響と要望
# ---------------------------------------------------------------------------
def _build_slide11(prs, data):
    slide = _new_slide(prs)
    _title_bar(slide, '影響と要望 — 弊社への影響と改善のお願い')

    ov = data['overview']
    _rect(slide, 0.4, 1.15, 5.8, 0.4, WHITE)
    _text(slide, 0.55, 1.18, 5.5, 0.35, '現在発生している影響', size=13, bold=True)

    impacts = [
        f"収束7日以内の納期が{_fmt(ov['within7_pct_min'])}~{_fmt(ov['within7_pct_max'])}%を占め、"
        f"材料調達に使う受注情報がない",
        f"確定直前（5営業日以内）の急変が計"
        f"{sum(p['last_minute']['total_events'] for p in data['products'])}件"
        f"（急減{ov['overstock_events']}件・急増{ov['shortage_events']}件）",
        "確定の急変により生産計画の頻繁な変更と便手配やり直しが発生",
        "欠品リスク対策として過剰な安全在庫の保持を余儀なくされ、在庫コスト増加",
        "内示変動に伴う作業工数の浪費（計画変更、事務処理工数増、残業対応）",
    ]
    y = 2.2
    for txt in impacts:
        _rect(slide, 0.55, y + 0.1, 0.12, 0.12, RED)
        _text(slide, 0.8, y, 5.2, 0.5, txt, size=10.5)
        y += 0.55

    _rect(slide, 6.8, 1.15, 5.8, 0.4, WHITE)
    _text(slide, 6.95, 1.18, 5.5, 0.35, '改善のお願い', size=13, bold=True)

    requests = [
        ('1. 内示精度の向上',
         f"1納期あたり平均{_fmt(ov['avg_change_count_min'])}~{_fmt(ov['avg_change_count_max'])}回の数量変動が"
         f"発生しております。内示数量と確定数量の乖離を縮小していただけますよう、お願いいたします。"),
        ('2. 確定情報の早期化',
         f"収束7日以内の納期が{_fmt(ov['within7_pct_min'])}~{_fmt(ov['within7_pct_max'])}%を占めております。"
         f"より早期の内示安定化をお願いいたします。"),
        ('3. 確定直前の急変抑制',
         f"確定5営業日前の急変が計{sum(p['last_minute']['total_events'] for p in data['products'])}件"
         f"発生しております。確定直前の大幅な数量変更を抑制していただけますよう、お願いいたします。"),
        ('4. 確定数量のばらつき改善',
         f"同一品番の日々の確定数量にCV{_fmt(ov['cv_min'])}~{_fmt(ov['cv_max'])}%のばらつきが見られます。"
         f"確定数量の安定化にご協力いただけますよう、お願いいたします。"),
    ]
    y = 1.75
    for title, body in requests:
        _text(slide, 6.95, y, 5.5, 0.35, title, size=12, bold=True)
        _text(slide, 6.95, y + 0.35, 5.3, 0.9, body, size=10, color=GRAY_TEXT)
        y += 1.3


# ---------------------------------------------------------------------------
# スライド12: 希望条件
# ---------------------------------------------------------------------------
def _build_slide11b(prs, data):
    """確定日後の追加（5稼働日未満）の事例スライド"""
    slide = _new_slide(prs)
    _title_bar(slide, '確定日後の追加（5稼働日未満）— 事例一覧')
    _text(slide, 0.5, 1.15, 12.0, 0.5,
          '7月以降の確定注文のうち、標準の確定タイミング（5稼働日前）を過ぎてから追加された実例。'
          '短納期の追加確定は、生産計画・要員・材料手配の変更を強いる。', size=12)

    items = data.get('short_lead_firm', [])
    if not items:
        _text(slide, 0.5, 2.5, 12.0, 0.5, '該当データなし', size=14)
        return

    headers = ['品番', '納入地', '納期', '顧客作成日', 'ダイソウ受領日', '数量', '確定日数']
    rows = []
    for it in items:
        rows.append([
            it['product_code'],
            it['ship_to'] or '—',
            it['due_date'][5:].replace('-', '/'),
            it['issue_date'][5:].replace('-', '/'),
            it['received_date'][5:].replace('-', '/'),
            str(int(it['quantity'])),
            str(it['working_days']),
        ])

    col_widths = [2.5, 1.2, 1.4, 1.4, 1.4, 1.2, 1.2]
    _add_table(slide, 0.5, 2.0, 10.3, min(0.5 + 0.4 * len(rows), 5.0), headers, rows,
               col_widths=col_widths)

    _rect(slide, 0.5, 6.85, 12.3, 0.5, RED_BG)
    _text(slide, 0.7, 6.88, 11.8, 0.45,
          f"7月以降で5稼働日未満の追加確定が{len(items)}件。"
          f"生産計画確定後の急な追加は要員・材料の段取り変更を余儀なくされる。", size=11)


def _build_slide11c(prs, data):
    """まとめ注文の事例スライド"""
    slide = _new_slide(prs)
    _title_bar(slide, 'まとめ注文 — 事例一覧')
    _text(slide, 0.5, 1.15, 12.0, 0.5,
          'ある日の確定数量が平均の1.5倍を超え、翌稼働日に確定がないケース。'
          '日々の均等な生産計画が崩れ、特定日に負荷が集中する。', size=12)

    items = data.get('batch_orders', [])
    if not items:
        _text(slide, 0.5, 2.5, 12.0, 0.5, '該当データなし', size=14)
        return

    headers = ['品番', '納入地', '日付', '数量', '平均', '倍率', '翌稼働日']
    rows = []
    for it in items:
        rows.append([
            it['product_code'],
            it['ship_to'] or '—',
            it['due_date'][5:].replace('-', '/'),
            str(int(it['quantity'])),
            str(it['avg_quantity']),
            f"x{it['ratio']}",
            it['next_working_day'][5:].replace('-', '/') + ' なし',
        ])

    col_widths = [2.5, 1.2, 1.2, 1.0, 1.0, 1.0, 2.0]
    table_h = min(0.5 + 0.4 * len(rows), 5.0)
    _add_table(slide, 0.5, 2.0, 9.9, table_h, headers, rows,
               col_widths=col_widths)

    _rect(slide, 0.5, 6.85, 12.3, 0.5, RED_BG)
    _text(slide, 0.7, 6.88, 11.8, 0.45,
          f"まとめ注文が{len(items)}件。日々の均等発注への切り替えをお願いしたい。", size=11)


def _build_slide12(prs):
    slide = _new_slide(prs)
    _title_bar(slide, '今後の安定供給に向けたご相談（希望条件）')
    _text(slide, 0.5, 1.25, 12.0, 0.45,
          '生産計画および安定供給の実現に向け、下記条件での運用をご相談させてください。', size=13)

    headers = ['項目', '理想案', '妥協案', '暫定案']
    rows = [
        ['確定時期', '納期14日前までに確定',
         '納期10日前までに確定\n内示数量の変動は納期14日前までに5%以内に抑える',
         '納期5営業日前までに確定\n内示数量の変動は納期14日前までに5%以内に抑える'],
        ['2か月前内示と確定の乖離（月平均）', '±5％以内', '±7％以内', '±10％以内'],
        ['確定日後の追加（5稼働日未満）', '原則ゼロ', '追加は月1回まで', '追加時は事前協議を必須化'],
        ['まとめ注文', '廃止', '廃止', '廃止'],
    ]
    _add_table(slide, 0.45, 1.95, 12.45, 3.9, headers, rows,
               col_widths=[2.45, 2.55, 3.7, 3.75], font_size=11, header_font_size=12)

    _rect(slide, 0.5, 6.35, 12.3, 0.55, BLUE_BG)
    _text(slide, 0.7, 6.45, 11.8, 0.3,
          '※まとめ注文の廃止は、すべての案に共通するお願い事項です。', size=11, color=GRAY_TEXT)


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------
def generate_naiji_pptx_report(data):
    """compute_naiji_report_data() の結果からPPTXを生成しBytesIOで返す"""
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W_IN)
    prs.slide_height = Inches(SLIDE_H_IN)

    _build_slide1(prs, data)
    _build_slide2(prs, data)
    _build_slide3(prs, data)
    _build_slide4(prs, data)
    _build_slide5(prs, data)
    _build_slide5b(prs, data)
    _build_slide6(prs, data)
    _build_slide7(prs, data)
    _build_slide8(prs, data)
    _build_slide9(prs, data)
    _build_slide9b(prs, data)
    _build_slide10(prs, data)
    _build_slide11(prs, data)
    _build_slide11b(prs, data)
    _build_slide11c(prs, data)
    _build_slide12(prs)

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf
