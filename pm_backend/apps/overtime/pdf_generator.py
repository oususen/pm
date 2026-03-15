# -*- coding: utf-8 -*-
"""時間外・休日出勤 申請書 PDF を生成するユーティリティ。"""

from __future__ import annotations

import os
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


def register_japanese_fonts() -> None:
    """
    ReportLab で日本語を扱えるようにフォントを登録する。

    Windows環境ではMSゴシックまたはメイリオ、
    Linux環境ではNoto Sans JP、IPAゴシック、TakaoPゴシック、
    Mac環境ではヒラギノを使用する。
    既に登録済みの場合は何もしない。
    """
    if "MSGothic" in pdfmetrics.getRegisteredFontNames():
        return

    # Windowsフォント候補
    windows_fonts = [
        Path("C:/Windows/Fonts/msgothic.ttc"),
        Path("C:/Windows/Fonts/meiryo.ttc"),
        Path("C:/Windows/Fonts/msmincho.ttc"),
        Path("C:/Windows/Fonts/yugothic.ttf"),
    ]

    # Linuxフォント候補（Docker/Ubuntu用）
    # ReportLabはTrueTypeフォントのみサポート（PostScript outlinesは非サポート）
    linux_fonts = [
        # Takao ゴシック（TrueType）- 実際のパス
        Path("/usr/share/fonts/truetype/takao-gothic/TakaoPGothic.ttf"),
        Path("/usr/share/fonts/truetype/takao-gothic/TakaoGothic.ttf"),
        # IPA ゴシック（TrueType）
        Path("/usr/share/fonts/truetype/fonts-ipafont-gothic/ipag.ttf"),
        Path("/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf"),
        Path("/usr/share/fonts/truetype/ipafont/ipag.ttf"),
        Path("/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"),
        # Noto Sans CJK JP（TrueType版があれば）
        Path("/usr/share/fonts/truetype/noto-cjk/NotoSansCJK-Regular.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-jp-Regular.otf"),
    ]

    # Macフォント候補
    mac_fonts = [
        Path("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"),
        Path("/System/Library/Fonts/ヒラギノ角ゴシック ProN W3.otf"),
        Path("/Library/Fonts/ヒラギノ角ゴ ProN W3.otc"),
    ]

    # OSに応じて候補を選択
    if os.name == "nt":
        candidates: Sequence[Path] = windows_fonts
    elif os.uname().sysname == "Darwin":
        candidates = mac_fonts
    else:
        candidates = linux_fonts

    # 全候補を順番に試す（見つからない場合は全環境の候補も試す）
    all_candidates = list(candidates) + [p for p in (windows_fonts + linux_fonts + mac_fonts) if p not in candidates]

    # 各フォントを試して、最初に成功したものを使用
    font_registered = False
    last_error = None

    for font_path in all_candidates:
        if not font_path.exists():
            continue

        try:
            # フォント登録を試みる
            pdfmetrics.registerFont(TTFont("MSGothic", str(font_path)))
            pdfmetrics.registerFont(TTFont("MSGothic-Bold", str(font_path)))
            font_registered = True
            print(f"✅ 日本語フォントを登録しました: {font_path}")
            break
        except Exception as e:
            # このフォントは使えないので次を試す
            last_error = e
            pass  # フォント読み込みエラー、次候補を試す
            continue

    if not font_registered:
        error_msg = (
            "日本語フォントが見つからないか、読み込みに失敗しました。\n\n"
            "Dockerコンテナの場合は、以下のコマンドでフォントをインストールしてください:\n"
            "  apt-get update && apt-get install -y fonts-ipafont-gothic fonts-takao-gothic\n\n"
            "Windowsの場合は、システムフォントが正しくインストールされているか確認してください。\n"
            "Linuxの場合は、以下のいずれかをインストールしてください:\n"
            "  - fonts-ipafont-gothic (推奨)\n"
            "  - fonts-takao-gothic\n\n"
        )
        if last_error:
            error_msg += f"最後のエラー: {str(last_error)}"
        raise FileNotFoundError(error_msg)


# ページサイズ・余白定数
PAGE_W, PAGE_H = A4  # ポイント単位
MARGIN_L = 15 * mm
MARGIN_R = 15 * mm
MARGIN_T = 15 * mm
MARGIN_B = 20 * mm

# カラー定数
COLOR_HEADER_BG = colors.HexColor("#f0f0f0")
COLOR_ALT_ROW = colors.HexColor("#fafafa")
COLOR_BORDER = colors.HexColor("#cccccc")

# テーブル列定義: (ヘッダ文字列, 幅mm)
_COL_DEFS = [
    ("No.", 8),
    ("申請者氏名", 28),
    ("実施日", 18),
    ("勤務時間", 30),
    ("残業時間帯", 30),
    ("時間数", 13),
    ("理由", None),  # 残り幅
    ("サイン", 30),
]

MAX_ROWS = 30


def _fmt_time(t) -> str:
    """time オブジェクトを HH:MM 形式文字列に変換する。None の場合は空文字。"""
    if t is None:
        return ""
    if hasattr(t, "strftime"):
        return t.strftime("%H:%M")
    return str(t)[:5]


def _fmt_hours(val) -> str:
    """時間数を X.XH 形式にフォーマットする。"""
    try:
        f = float(val)
    except (TypeError, ValueError):
        return "0.0H"
    return f"{f:.1f}H"


def generate_overtime_pdf(applications, filters=None):
    """
    時間外・休日出勤 申請書 PDF を生成する。

    applications: OvertimeApplication クエリセット or リスト
    filters: dict with keys 'team_name', 'group_name', 'date_from', 'date_to'
    Returns: BytesIO バッファ
    """
    register_japanese_fonts()

    if filters is None:
        filters = {}

    team_name = filters.get("team_name", "") or "全班"
    date_from = filters.get("date_from", "")
    date_to = filters.get("date_to", "")

    # 事業部名を申請データから取得
    division_name = ""
    if applications:
        try:
            division_name = applications[0].applicant.profile.division.name or ""
        except Exception:
            pass
    if not division_name:
        division_name = "製缶事業部"

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    # ---- 有効描画領域 ----
    content_w = PAGE_W - MARGIN_L - MARGIN_R  # ポイント単位

    # ---- タイトル ----
    title_y = MARGIN_B + (PAGE_H - MARGIN_T - MARGIN_B) - 0 * mm  # y=275mm from bottom
    title_y = 275 * mm
    # タイトルを申請種別に応じて変更
    types = set(getattr(a, "application_type", "overtime") for a in applications)
    if types == {"holiday"}:
        title_text = "休日出勤  申請書"
    elif types == {"overtime"}:
        title_text = "時間外  申請書"
    else:
        title_text = "時間外・休日出勤  申請書"

    c.setFont("MSGothic-Bold", 16)
    c.drawCentredString(PAGE_W / 2, title_y, title_text)

    # ---- 出力日・部門行 (y=268mm) ----
    info_y = 268 * mm
    today = datetime.now()
    date_str = f"出力日: {today.year}年{today.month}月{today.day}日"

    c.setFont("MSGothic", 9)
    # 左：部門（2行: 事業部名 / ***班）
    team_disp = f"{team_name}班" if team_name and not team_name.endswith("班") else (team_name or "全班")
    c.drawString(MARGIN_L, info_y, f"実施部門: {division_name}")
    c.drawString(MARGIN_L, info_y - 5 * mm, f"　　　　　{team_disp}")
    # 右：出力日
    c.drawRightString(PAGE_W - MARGIN_R, info_y, date_str)

    # ---- 承認押印欄 (y=245mm 基準、ボックス上端) ----
    # 4ボックス: 部長 / 課長 / 係長 / 班長
    stamp_labels = ["部長", "課長", "係長", "班長"]
    box_w = 22 * mm
    box_h = 18 * mm
    label_h = 5 * mm
    box_gap = 1 * mm
    total_stamp_w = len(stamp_labels) * box_w + (len(stamp_labels) - 1) * box_gap
    stamp_x_start = PAGE_W - MARGIN_R - total_stamp_w
    stamp_top_y = 262 * mm  # ボックス上端

    c.setFont("MSGothic", 8)
    for i, label in enumerate(stamp_labels):
        bx = stamp_x_start + i * (box_w + box_gap)
        by = stamp_top_y - box_h  # ボックス左下 y 座標
        # 枠線
        c.setStrokeColor(COLOR_BORDER)
        c.setLineWidth(0.5)
        c.rect(bx, by, box_w, box_h)
        # ラベル（ボックス下）
        label_y = by - label_h + 1 * mm
        c.drawCentredString(bx + box_w / 2, label_y, label)

    # ---- メインテーブル ----
    table_top_y = 238 * mm  # テーブル上端
    header_h = 8 * mm
    row_h = 7 * mm

    # 列幅計算
    col_headers = [d[0] for d in _COL_DEFS]
    col_widths_mm = [d[1] for d in _COL_DEFS]
    fixed_w = sum(w for w in col_widths_mm if w is not None) * mm
    remaining_w = content_w - fixed_w
    col_widths_pt = [
        (w * mm if w is not None else remaining_w) for w in col_widths_mm
    ]

    def draw_row_bg(row_idx, y_top, height, is_header=False):
        """行の背景色を描画する。"""
        if is_header:
            c.setFillColor(COLOR_HEADER_BG)
        elif row_idx % 2 == 1:
            c.setFillColor(COLOR_ALT_ROW)
        else:
            c.setFillColor(colors.white)
        c.rect(MARGIN_L, y_top - height, content_w, height, fill=1, stroke=0)

    def draw_cell_text(text, x, y_top, w, height, font="MSGothic", size=8, align="left"):
        """セル内テキストを描画する（中央揃え縦位置）。"""
        text_y = y_top - height / 2 - size / 2 * 0.8
        c.setFont(font, size)
        c.setFillColor(colors.black)
        padding = 2
        if align == "center":
            c.drawCentredString(x + w / 2, text_y, text)
        elif align == "right":
            c.drawRightString(x + w - padding, text_y, text)
        else:
            # はみ出す場合はトリミング（理由列以外）
            avail_w = w - padding * 2
            while text and c.stringWidth(text, font, size) > avail_w:
                text = text[:-1]
            c.drawString(x + padding, text_y, text)

    FONT_SIZE_DATA = 7
    LINE_H_PT = FONT_SIZE_DATA * 1.35  # 行間（ポイント）
    REASON_COL_IDX = 6  # 理由列のインデックス
    reason_col_w = col_widths_pt[REASON_COL_IDX]
    REASON_PAD = 3  # 理由列 左右パディング（ポイント）

    def wrap_reason(text):
        """理由テキストを列幅に合わせた行リストに分割する（stringWidth使用）。"""
        if not text:
            return [""]
        avail = reason_col_w - REASON_PAD * 2
        lines = []
        current = ""
        for char in text:
            test = current + char
            if c.stringWidth(test, "MSGothic", FONT_SIZE_DATA) <= avail:
                current = test
            else:
                if current:
                    lines.append(current)
                current = char
        if current:
            lines.append(current)
        return lines if lines else [""]

    # 1st pass: 各行高さを確定
    pre_data = []  # [(app_or_None, reason_lines, row_height)]
    for row_idx in range(MAX_ROWS):
        if row_idx < len(applications):
            app = applications[row_idx]
            reason = getattr(app, "reason", "") or ""
            rlines = wrap_reason(reason)
            rh = max(row_h, len(rlines) * LINE_H_PT + 4)
        else:
            app = None
            rlines = [""]
            rh = row_h
        pre_data.append((app, rlines, rh))

    # 累積y座標: row_top_y[i] = i行目の上端
    def get_row_top(row_idx):
        return table_top_y - header_h - sum(d[2] for d in pre_data[:row_idx])

    def draw_grid_lines_variable():
        """可変行高さ対応のテーブル罫線を描画する。"""
        c.setStrokeColor(COLOR_BORDER)
        c.setLineWidth(0.4)
        total_data_h = sum(d[2] for d in pre_data)
        total_h = header_h + total_data_h + row_h  # +row_h for total row
        # 外枠
        c.rect(MARGIN_L, table_top_y - total_h, content_w, total_h, fill=0, stroke=1)
        # ヘッダ下線
        c.line(MARGIN_L, table_top_y - header_h, MARGIN_L + content_w, table_top_y - header_h)
        # データ行区切り線
        for r in range(1, MAX_ROWS + 1):
            ly = get_row_top(r)
            c.line(MARGIN_L, ly, MARGIN_L + content_w, ly)
        # 合計行下線
        total_row_top = get_row_top(MAX_ROWS)
        c.line(MARGIN_L, total_row_top - row_h, MARGIN_L + content_w, total_row_top - row_h)
        # 列区切り線
        cx = MARGIN_L
        for cw_ in col_widths_pt[:-1]:
            cx += cw_
            c.line(cx, table_top_y, cx, table_top_y - total_h)

    def draw_reason_lines(rlines, x, y_top, height):
        """理由列の折り返し済み行リストを描画する。"""
        c.setFont("MSGothic", FONT_SIZE_DATA)
        c.setFillColor(colors.black)
        n_lines = len(rlines)
        total_text_h = n_lines * LINE_H_PT
        start_y = y_top - (height - total_text_h) / 2 - LINE_H_PT * 0.8
        for li, line in enumerate(rlines):
            ly = start_y - li * LINE_H_PT
            c.drawString(x + REASON_PAD, ly, line)

    # ヘッダ行
    draw_row_bg(-1, table_top_y, header_h, is_header=True)
    cx = MARGIN_L
    for i, (hdr, cw) in enumerate(zip(col_headers, col_widths_pt)):
        draw_cell_text(hdr, cx, table_top_y, cw, header_h, font="MSGothic-Bold", size=8, align="center")
        cx += cw

    # データ行（2nd pass: 描画）
    total_hours = 0.0

    for row_idx, (app, rlines, rh) in enumerate(pre_data):
        row_top = get_row_top(row_idx)
        draw_row_bg(row_idx, row_top, rh)

        if app is not None:
            # 申請者氏名
            applicant = getattr(app, "applicant", None)
            name = f"{applicant.last_name}{applicant.first_name}".strip() if applicant else ""

            # 実施日
            work_date = getattr(app, "work_date", None)
            date_disp = f"{work_date.month}/{work_date.day}" if work_date else ""

            # 勤務時間
            wst = _fmt_time(getattr(app, "work_start_time", None))
            set_ = _fmt_time(getattr(app, "scheduled_end_time", None))
            work_time_str = f"{wst} ~ {set_}" if wst and set_ else (wst or "")

            # 残業時間帯
            st = _fmt_time(getattr(app, "start_time", None))
            et = _fmt_time(getattr(app, "end_time", None))
            ot_time_str = f"{st} ~ {et}" if st and et else ""

            # 時間数
            hours = float(getattr(app, "hours", 0) or 0)
            midnight = float(getattr(app, "midnight_hours", 0) or 0)
            total_val = hours + midnight
            total_hours += total_val
            hours_str = _fmt_hours(total_val)

            # サイン画像パス
            sig_field = getattr(app, "signature", None)
            sig_path = sig_field.path if sig_field and sig_field.name else None

            # 理由以外のセル描画
            cells = [
                (str(row_idx + 1), "center"),
                (name, "left"),
                (date_disp, "center"),
                (work_time_str, "center"),
                (ot_time_str, "center"),
                (hours_str, "center"),
                None,  # 理由は別途描画
                ("", "center"),  # サイン
            ]
        else:
            sig_path = None
            cells = [("", "left")] * len(col_widths_pt)
            cells[REASON_COL_IDX] = None

        cx = MARGIN_L
        for col_i, cell in enumerate(cells):
            cw_ = col_widths_pt[col_i]
            if cell is not None:
                draw_cell_text(cell[0], cx, row_top, cw_, rh, size=FONT_SIZE_DATA, align=cell[1])
            else:
                # 理由列: 折り返し描画
                draw_reason_lines(rlines, cx, row_top, rh)
            cx += cw_

        # サイン画像の描画（最後の列）
        if sig_path:
            try:
                sign_col_w = col_widths_pt[-1]
                sign_x = MARGIN_L + sum(col_widths_pt[:-1])
                pad = 1 * mm
                img_w = sign_col_w - pad * 2
                img_h = rh - pad * 2
                c.drawImage(
                    sig_path, sign_x + pad, row_top - rh + pad,
                    width=img_w, height=img_h,
                    preserveAspectRatio=True, anchor='c',
                    mask='auto',
                )
            except Exception:
                pass

    # 合計行
    total_row_top = get_row_top(MAX_ROWS)
    c.setFillColor(COLOR_HEADER_BG)
    c.rect(MARGIN_L, total_row_top - row_h, content_w, row_h, fill=1, stroke=0)
    n = len(applications)
    c.setFont("MSGothic-Bold", 8)
    c.setFillColor(colors.black)
    c.drawString(MARGIN_L + 2, total_row_top - row_h / 2 - 3, f"合計 {n}件")
    hours_col_x = MARGIN_L + sum(col_widths_pt[:5])
    c.drawCentredString(
        hours_col_x + col_widths_pt[5] / 2,
        total_row_top - row_h / 2 - 3,
        _fmt_hours(total_hours),
    )

    # テーブル罫線（可変行高さ対応）
    draw_grid_lines_variable()

    # ---- フッター注意書き ----
    footer_notes = [
        "①　深夜残業区分に入った場合は残業時間数と深夜残業時間数を分けて記入すること",
        "②　申請書提出期限：残業実施日の午後4:00まで、休日出勤申請は前日の午後5:00まで",
        "③　申請なしで実施した場合は事故が発生しても会社として責任を持たず、残業と認めない",
        "④　申請時間より早く終了した場合はタイムカードの打刻を優先、遅くなった場合は翌日再申請",
        "⑤　夜勤者については事後処理も可の場合がある",
    ]
    c.setFont("MSGothic", 7)
    c.setFillColor(colors.black)
    note_start_y = 18 * mm + (len(footer_notes) - 1) * 4 * mm
    for i, note in enumerate(footer_notes):
        note_y = note_start_y - i * 4 * mm
        c.drawString(MARGIN_L, note_y, note)

    c.save()
    buf.seek(0)
    return buf


def _draw_row_cells(c, cells_with_widths, row_top, row_h):
    """cells_with_widths: [(text, align, width_pt), ...]"""
    cx = MARGIN_L
    for text, align, cw in cells_with_widths:
        size = 7
        text_y = row_top - row_h / 2 - size / 2 * 0.8
        c.setFont("MSGothic", size)
        c.setFillColor(colors.black)
        padding = 2
        if align == "center":
            c.drawCentredString(cx + cw / 2, text_y, text)
        elif align == "right":
            c.drawRightString(cx + cw - padding, text_y, text)
        else:
            max_chars = int(cw / (size * 0.6)) - 1
            if len(text) > max_chars and max_chars > 0:
                text = text[:max_chars] + "…"
            c.drawString(cx + padding, text_y, text)
        cx += cw
