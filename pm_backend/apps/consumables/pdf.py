"""
消耗品 注文書PDF（syomohin の pdf_generator.py を移植）
- 承認欄は姓のみ・日付付き。氏名は承認申請（ApprovalStep）から取得する
- 商品名・備考は自動折り返し
- 明細が1ページに収まらない場合は次ページへ送る（ヘッダー行を繰り返す）
"""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from overtime.pdf_generator import register_japanese_fonts

FONT = 'MSGothic'
COMPANY_NAME = 'ダイソウ工業株式会社'
ISSUING_DEPARTMENT = '製缶事業部'


def _last_name(user):
    """姓のみ（未設定ならログインID）"""
    if not user:
        return ''
    return user.last_name or user.username


def _fmt_date(value):
    return value.strftime('%Y/%m/%d') if value else ''


def collect_approval_stamps(dispatch_order):
    """
    承認欄の押印情報を返す: [(見出し, 姓, 日付), ...]（左から 承認・確認②・確認・作成）
    却下後の再申請では、最後の却下より後の記録だけを使う。
    """
    confirmed = {}
    approval = dispatch_order.approval_request
    reviewer2_enabled = False
    if approval:
        reviewer2_enabled = approval.route_config.reviewer2_enabled
        for step in approval.steps.select_related('user').order_by('id'):
            if step.action == 'rejected':
                confirmed = {}
            else:
                confirmed[step.stage] = step

    def stamp(label, stage):
        step = confirmed.get(stage)
        return (label, _last_name(step.user), _fmt_date(step.acted_at)) if step else (label, '', '')

    stamps = [stamp('承認', 'approver')]
    if reviewer2_enabled:
        stamps.append(stamp('確認②', 'reviewer2'))
    stamps.append(stamp('確認', 'reviewer1'))
    stamps.append(('作成', _last_name(dispatch_order.created_by), _fmt_date(dispatch_order.created_at)))
    return stamps


def build_dispatch_order_pdf(dispatch_order):
    """注文書PDFを生成して bytes を返す"""
    register_japanese_fonts()
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 15 * mm

    pages = _split_item_table(_build_items_table(dispatch_order), width, height, margin)
    for page_no, table in enumerate(pages, start=1):
        if page_no == 1:
            _draw_title(c, width, height)
            _draw_header(c, dispatch_order, width, height, margin)
            _draw_approval_section(c, dispatch_order, width, height, margin)
            y_top = height - 115 * mm
        else:
            y_top = height - 20 * mm
        _, table_height = table.wrap(width, height)
        table.drawOn(c, margin, y_top - table_height)
        _draw_footer(c, dispatch_order, width, margin, page_no, len(pages))
        c.showPage()

    c.save()
    return buffer.getvalue()


def _draw_title(c, width, height):
    c.setFont(FONT, 24)
    title = '注文書'
    c.drawString((width - c.stringWidth(title, FONT, 24)) / 2, height - 30 * mm, title)


def _draw_header(c, order, width, height, margin):
    y_start = height - 50 * mm
    c.setFont(FONT, 12)
    c.drawString(margin, y_start, f'{order.supplier_name} 御中')
    contact_person = order.supplier.contact_person if order.supplier_id else ''
    if contact_person:
        c.setFont(FONT, 10)
        c.drawString(margin, y_start - 10 * mm, f'{contact_person} 様')

    right_x = width - margin - 70 * mm
    c.setFont(FONT, 14)
    c.drawString(right_x, y_start, COMPANY_NAME)
    c.setFont(FONT, 10)
    c.drawString(right_x, y_start - 8 * mm, f'発行日: {order.created_at.strftime("%Y年%m月%d日")}')
    c.drawString(right_x, y_start - 15 * mm, f'発行部門: {ISSUING_DEPARTMENT}')


def _draw_approval_section(c, order, width, height, margin):
    stamps = collect_approval_stamps(order)
    data = [
        [label for label, _, _ in stamps],
        [f'{name}\n{date}' if name else '' for _, name, date in stamps],
    ]
    col_width = 22 * mm if len(stamps) <= 3 else 17 * mm
    table = Table(data, colWidths=[col_width] * len(stamps), rowHeights=[8 * mm, 15 * mm])
    table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), FONT, 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
    ]))
    table.wrapOn(c, width, height)
    # 右端を揃える
    table.drawOn(c, width - margin - col_width * len(stamps), height - 70 * mm - 23 * mm)


def _build_items_table(order):
    wrap_style = ParagraphStyle('wrap', fontName=FONT, fontSize=7, leading=9, wordWrap='CJK')
    headers = ['No', '発注\nコード', '商品名・仕様', '数量', '単位', '単価', '金額', '納期', '稟議書No', '備考']
    rows = [headers]
    total_quantity = 0
    total_amount = 0
    for idx, item in enumerate(order.items.all(), start=1):
        total_quantity += item.quantity
        total_amount += item.total_amount
        rows.append([
            str(idx),
            item.order_code,
            Paragraph(item.name, wrap_style),
            str(item.quantity),
            item.unit,
            f'{int(item.unit_price):,}' if item.unit_price else '',
            f'{int(item.total_amount):,}' if item.total_amount else '',
            item.deadline,
            '',
            Paragraph(item.note or '-', wrap_style),
        ])
    rows.append(['合計', '', '', str(total_quantity), '', '', f'{int(total_amount):,}', '', '', ''])

    last_row = len(rows) - 1
    col_widths = [10 * mm, 18 * mm, 45 * mm, 12 * mm, 12 * mm, 18 * mm, 18 * mm, 15 * mm, 15 * mm, 15 * mm]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), FONT, 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
        ('ALIGN', (5, 1), (6, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('ALIGN', (0, last_row), (0, last_row), 'CENTER'),
        ('BACKGROUND', (0, last_row), (-1, last_row), colors.lightgrey),
        ('FONT', (0, last_row), (-1, last_row), FONT, 8),
    ]))
    return table


def _split_item_table(table, width, height, margin):
    """明細表をページごとに分割する（1ページ目は見出し・承認欄の下から）"""
    bottom = 22 * mm
    first_avail = height - 115 * mm - bottom
    next_avail = height - 20 * mm - bottom
    pages = []
    remaining = table
    avail = first_avail
    while True:
        _, h = remaining.wrap(width - 2 * margin, height)
        if h <= avail:
            pages.append(remaining)
            return pages
        parts = remaining.split(width - 2 * margin, avail)
        if len(parts) < 2:
            pages.append(remaining)
            return pages
        pages.append(parts[0])
        remaining = parts[1]
        avail = next_avail


def _draw_footer(c, order, width, margin, page_no, page_count):
    c.setFont(FONT, 8)
    c.drawString(margin, 15 * mm, f'注文書番号: {order.order_number}')
    c.drawRightString(width - margin, 15 * mm, f'{page_no} / {page_count}')


def dispatch_order_pdf_filename(order):
    """syomohin と同じ命名: {業務日}_{購入先}_{合計金額}_注文書_{当日回数}.pdf"""
    return (
        f'{order.business_date.strftime("%Y%m%d")}_{order.supplier_name}_'
        f'{int(order.total_amount)}_注文書_{order.daily_count}.pdf'
    )
