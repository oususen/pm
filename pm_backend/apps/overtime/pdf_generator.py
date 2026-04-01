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
MARGIN_B = 12 * mm

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

# フッター注意書き
_FOOTER_NOTES = [
    "①　深夜残業区分に入った場合は残業時間数と深夜残業時間数を分けて記入すること",
    "②　申請書提出期限：残業実施日の午後4:00まで、休日出勤申請は前日の午後5:00まで",
    "③　申請なしで実施した場合は事故が発生しても会社として責任を持たず、残業と認めない",
    "④　申請時間より早く終了した場合はタイムカードの打刻を優先、遅くなった場合は翌日再申請",
    "⑤　夜勤者については事後処理も可の場合がある",
]
FOOTER_H = len(_FOOTER_NOTES) * 4 * mm + 2 * mm  # フッター高さ

HEADER_H = 8 * mm   # テーブルヘッダ行高さ
ROW_H = 7 * mm       # データ行デフォルト高さ
TOTAL_ROW_H = 7 * mm  # 合計行高さ


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
    時間外・休日出勤 申請書 PDF を生成する（複数ページ対応）。

    applications: OvertimeApplication クエリセット or リスト
    filters: dict with keys 'team_name', 'group_name', 'date_from', 'date_to'
    Returns: BytesIO バッファ
    """
    register_japanese_fonts()

    if filters is None:
        filters = {}

    team_name = filters.get("team_name", "") or "全班"
    group_name = filters.get("group_name", "") or ""

    # グループ選択有無（'全グループ' でない場合はグループ指定あり）
    is_group_selected = bool(group_name) and group_name != "全グループ"

    # 事業部名・係名を申請データから取得
    division_name = ""
    section_name = ""
    if applications:
        try:
            division_name = applications[0].applicant.profile.division.name or ""
        except Exception:
            pass
        try:
            section_name = applications[0].applicant.profile.group.name or ""
        except Exception:
            pass
    if not division_name:
        division_name = "製缶事業部"

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    # ---- 有効描画領域 ----
    content_w = PAGE_W - MARGIN_L - MARGIN_R

    # タイトルテキスト決定
    types = set(getattr(a, "application_type", "overtime") for a in applications)
    if types == {"holiday"}:
        title_text = "休日出勤  申請書"
    elif types == {"overtime"}:
        title_text = "時間外  申請書"
    else:
        title_text = "時間外・休日出勤  申請書"

    # 列幅計算
    col_headers = [d[0] for d in _COL_DEFS]
    col_widths_mm = [d[1] for d in _COL_DEFS]
    fixed_w = sum(w for w in col_widths_mm if w is not None) * mm
    remaining_w = content_w - fixed_w
    col_widths_pt = [
        (w * mm if w is not None else remaining_w) for w in col_widths_mm
    ]

    FONT_SIZE_DATA = 7
    LINE_H_PT = FONT_SIZE_DATA * 1.35
    REASON_COL_IDX = 6
    reason_col_w = col_widths_pt[REASON_COL_IDX]
    REASON_PAD = 3

    def wrap_reason(text):
        """理由テキストを列幅に合わせた行リストに分割する。"""
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

    # 各申請の理由折返し・行高さを事前計算
    app_rows = []  # [(app, reason_lines, row_height), ...]
    for app in applications:
        reason = getattr(app, "reason", "") or ""
        rlines = wrap_reason(reason)
        rh = max(ROW_H, len(rlines) * LINE_H_PT + 4)
        app_rows.append((app, rlines, rh))

    # ---- ページ分割 ----
    # ヘッダ部（タイトル〜押印欄〜テーブルヘッダ前）の高さ
    page_header_top = 275 * mm  # タイトル上端
    table_top_y = 238 * mm     # テーブル上端

    # 1ページ目: テーブル上端からフッター注記の上までが使える領域
    first_page_avail = table_top_y - HEADER_H - MARGIN_B - FOOTER_H - TOTAL_ROW_H
    # 2ページ目以降: ページ上端余白からフッター注記の上まで
    cont_table_top = PAGE_H - MARGIN_T
    cont_page_avail = cont_table_top - HEADER_H - MARGIN_B - FOOTER_H - TOTAL_ROW_H

    # ページごとの行割り振り
    pages = []  # [[(app, rlines, rh), ...], ...]
    current_page = []
    used_h = 0
    avail = first_page_avail

    for item in app_rows:
        _, _, rh = item
        if current_page and used_h + rh > avail:
            # 現在ページに収まらない → ページ確定、次ページへ
            pages.append(current_page)
            current_page = [item]
            used_h = rh
            avail = cont_page_avail
        else:
            current_page.append(item)
            used_h += rh

    if current_page:
        pages.append(current_page)
    if not pages:
        pages = [[]]

    total_pages = len(pages)
    total_hours = 0.0
    row_no = 0  # 通し番号

    # ---- 描画ヘルパー ----
    def draw_page_header(page_idx):
        """ページヘッダ（タイトル・部門・押印欄）を描画する。"""
        if page_idx == 0:
            # 1ページ目: フルヘッダ
            c.setFont("MSGothic-Bold", 16)
            c.drawCentredString(PAGE_W / 2, 275 * mm, title_text)

            info_y = 268 * mm
            today = datetime.now()
            date_str = f"出力日: {today.year}年{today.month}月{today.day}日"

            c.setFont("MSGothic", 9)
            team_disp = f"{team_name}班" if team_name and not team_name.endswith("班") else (team_name or "全班")
            if is_group_selected:
                dept_lines = [
                    f"実施部門: {division_name}",
                    f"　　　　　{section_name}" if section_name else None,
                    f"　　　　　{team_disp}",
                    f"　　　　　{group_name}",
                ]
                dept_lines = [l for l in dept_lines if l is not None]
                for i, line in enumerate(dept_lines):
                    c.drawString(MARGIN_L, info_y - i * 4.5 * mm, line)
            else:
                c.drawString(MARGIN_L, info_y, f"実施部門: {division_name}")
                c.drawString(MARGIN_L, info_y - 5 * mm, f"　　　　　{team_disp}")
            c.drawRightString(PAGE_W - MARGIN_R, info_y, date_str)

            # 押印欄
            stamp_labels = ["部長", "課長", "係長", "班長"]
            box_w = 22 * mm
            box_h = 18 * mm
            label_h = 5 * mm
            box_gap = 1 * mm
            total_stamp_w = len(stamp_labels) * box_w + (len(stamp_labels) - 1) * box_gap
            stamp_x_start = PAGE_W - MARGIN_R - total_stamp_w
            stamp_top_y = 262 * mm

            c.setFont("MSGothic", 8)
            for i, label in enumerate(stamp_labels):
                bx = stamp_x_start + i * (box_w + box_gap)
                by = stamp_top_y - box_h
                c.setStrokeColor(COLOR_BORDER)
                c.setLineWidth(0.5)
                c.rect(bx, by, box_w, box_h)
                label_y = by - label_h + 1 * mm
                c.drawCentredString(bx + box_w / 2, label_y, label)

            return table_top_y
        else:
            # 2ページ目以降: タイトルのみ簡易表示
            c.setFont("MSGothic-Bold", 10)
            c.drawCentredString(PAGE_W / 2, PAGE_H - MARGIN_T + 5 * mm,
                                f"{title_text}（{page_idx + 1}/{total_pages}）")
            return cont_table_top

    def draw_table_header(tbl_top):
        """テーブルヘッダ行を描画する。"""
        c.setFillColor(COLOR_HEADER_BG)
        c.rect(MARGIN_L, tbl_top - HEADER_H, content_w, HEADER_H, fill=1, stroke=0)
        cx = MARGIN_L
        for i, (hdr, cw) in enumerate(zip(col_headers, col_widths_pt)):
            draw_cell_text(hdr, cx, tbl_top, cw, HEADER_H,
                           font="MSGothic-Bold", size=8, align="center")
            cx += cw

    def draw_cell_text(text, x, y_top, w, height, font="MSGothic", size=8, align="left"):
        """セル内テキストを描画する。"""
        text_y = y_top - height / 2 - size / 2 * 0.8
        c.setFont(font, size)
        c.setFillColor(colors.black)
        padding = 2
        if align == "center":
            c.drawCentredString(x + w / 2, text_y, text)
        elif align == "right":
            c.drawRightString(x + w - padding, text_y, text)
        else:
            avail_w = w - padding * 2
            while text and c.stringWidth(text, font, size) > avail_w:
                text = text[:-1]
            c.drawString(x + padding, text_y, text)

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

    def draw_footer_notes(bottom_y):
        """フッター注意書きを描画する。bottom_yはテーブル（合計行含む）の下端。"""
        c.setFont("MSGothic", 7)
        c.setFillColor(colors.black)
        note_y = bottom_y - 4 * mm
        for note in _FOOTER_NOTES:
            c.drawString(MARGIN_L, note_y, note)
            note_y -= 4 * mm

    def draw_grid(tbl_top, page_rows, total_row_top):
        """テーブル罫線を描画する。"""
        c.setStrokeColor(COLOR_BORDER)
        c.setLineWidth(0.4)
        total_bottom = total_row_top - TOTAL_ROW_H
        total_h = tbl_top - total_bottom
        # 外枠
        c.rect(MARGIN_L, total_bottom, content_w, total_h, fill=0, stroke=1)
        # ヘッダ下線
        c.line(MARGIN_L, tbl_top - HEADER_H, MARGIN_L + content_w, tbl_top - HEADER_H)
        # データ行区切り線
        cur_y = tbl_top - HEADER_H
        for _, _, rh in page_rows:
            cur_y -= rh
            c.line(MARGIN_L, cur_y, MARGIN_L + content_w, cur_y)
        # 列区切り線
        cx = MARGIN_L
        for cw_ in col_widths_pt[:-1]:
            cx += cw_
            c.line(cx, tbl_top, cx, total_bottom)

    # ---- 各ページ描画 ----
    for page_idx, page_rows in enumerate(pages):
        if page_idx > 0:
            c.showPage()

        tbl_top = draw_page_header(page_idx)
        draw_table_header(tbl_top)

        # データ行描画
        cur_y = tbl_top - HEADER_H
        for app, rlines, rh in page_rows:
            row_top = cur_y
            row_no += 1

            # 背景色
            if row_no % 2 == 0:
                c.setFillColor(COLOR_ALT_ROW)
            else:
                c.setFillColor(colors.white)
            c.rect(MARGIN_L, row_top - rh, content_w, rh, fill=1, stroke=0)

            # 申請者氏名
            applicant = getattr(app, "applicant", None)
            name = f"{applicant.last_name}　{applicant.first_name}".strip() if applicant else ""

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

            # セル描画
            cells = [
                (str(row_no), "center"),
                (name, "left"),
                (date_disp, "center"),
                (work_time_str, "center"),
                (ot_time_str, "center"),
                (hours_str, "center"),
                None,  # 理由は別途描画
                ("", "center"),  # サイン
            ]

            cx = MARGIN_L
            for col_i, cell in enumerate(cells):
                cw_ = col_widths_pt[col_i]
                if cell is not None:
                    draw_cell_text(cell[0], cx, row_top, cw_, rh,
                                   size=FONT_SIZE_DATA, align=cell[1])
                else:
                    draw_reason_lines(rlines, cx, row_top, rh)
                cx += cw_

            # サイン画像
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

            cur_y -= rh

        # 合計行
        total_row_top = cur_y
        c.setFillColor(COLOR_HEADER_BG)
        c.rect(MARGIN_L, total_row_top - TOTAL_ROW_H, content_w, TOTAL_ROW_H, fill=1, stroke=0)
        n = len(applications)
        c.setFont("MSGothic-Bold", 8)
        c.setFillColor(colors.black)
        c.drawString(MARGIN_L + 2, total_row_top - TOTAL_ROW_H / 2 - 3, f"合計 {n}件")
        hours_col_x = MARGIN_L + sum(col_widths_pt[:5])
        c.drawCentredString(
            hours_col_x + col_widths_pt[5] / 2,
            total_row_top - TOTAL_ROW_H / 2 - 3,
            _fmt_hours(total_hours),
        )

        # 罫線
        draw_grid(tbl_top, page_rows, total_row_top)

        # フッター注意書き
        draw_footer_notes(total_row_top - TOTAL_ROW_H)

    c.save()
    buf.seek(0)
    return buf
