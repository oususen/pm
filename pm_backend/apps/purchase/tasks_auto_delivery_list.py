"""自動納入リスト送信タスク"""
import logging
import time
from datetime import date, datetime, timedelta
from io import BytesIO

from openpyxl import Workbook

logger = logging.getLogger('purchase')


def run_auto_delivery_list_send(config_id):
    from notifications.models import Notification
    from masters.models import Calendar
    from orders.utils.calendar_utils import WorkingDayCalculator
    from shipping.services.email_service import EmailService

    from .models import PurchaseAutoDeliveryListConfig, SupplierOrderSchedule
    from .order_proposal_views import _generate_raw_pattern_dates
    from .views import _calc_progress_quantities, _resolve_purchase_line

    start_time = time.time()
    config = PurchaseAutoDeliveryListConfig.objects.select_related('supplier').filter(id=config_id).first()
    if not config:
        logger.error(f'自動納入リスト設定が見つかりません: config_id={config_id}')
        return

    supplier = config.supplier
    config.last_run_at = datetime.now()
    config.last_run_status = 'RUNNING'
    config.last_run_message = '実行中...'
    config.save(update_fields=['last_run_at', 'last_run_status', 'last_run_message'])

    try:
        today = date.today()
        daiso_cal = Calendar.objects.filter(calendar_code='daiso').first()
        calc = WorkingDayCalculator(daiso_cal)
        delivery_date = calc.add_working_days(today, config.lead_time_days or 2)

        schedule = SupplierOrderSchedule.objects.filter(
            supplier_id=supplier.id, is_enabled=True,
        ).select_related('pattern').first()

        if not schedule or not schedule.pattern:
            _finish(config, start_time, 'SKIPPED', f'仕入先 {supplier.supplier_code} の納入パターンが未設定です')
            _notify_users(config.notify_on_non_delivery, f'自動納入リスト: {supplier.supplier_name} の納入パターンが未設定です')
            return

        window_start = delivery_date - timedelta(days=7)
        window_end = delivery_date + timedelta(days=90)
        pattern_dates = sorted(set(_generate_raw_pattern_dates(schedule, window_start, window_end, calc)))

        if delivery_date not in pattern_dates:
            _finish(config, start_time, 'SKIPPED', f'{delivery_date} は {supplier.supplier_code} の納入日ではありません')
            _notify_users(
                config.notify_on_non_delivery,
                f'自動納入リスト: {delivery_date} は {supplier.supplier_name} の納入日ではありません',
            )
            return

        future = [d for d in pattern_dates if d > delivery_date]
        next_delivery_date = future[0] if future else None

        if next_delivery_date:
            coverage_dates = []
            d = delivery_date
            while d < next_delivery_date:
                coverage_dates.append(d)
                d += timedelta(days=1)
        else:
            coverage_dates = [delivery_date]

        line = _resolve_purchase_line(supplier)
        if not line:
            _finish(config, start_time, 'FAILED', f'仕入先 {supplier.supplier_code} に対応するラインが見つかりません')
            _notify_users(config.notify_on_failure, f'自動納入リスト失敗: {supplier.supplier_name} に対応するラインが見つかりません')
            return

        product_map = _calc_progress_quantities(line, coverage_dates)
        items = sorted(product_map.values(), key=lambda x: x['product_code'])

        supplier_type = getattr(supplier, 'supplier_type', 'both') or 'both'
        if supplier_type == 'outsource':
            items = [i for i in items if i['product_code'].endswith('G')]
        elif supplier_type == 'purchase':
            items = [i for i in items if not i['product_code'].endswith('G')]

        if not items:
            _finish(config, start_time, 'SUCCESS', f'{delivery_date} の納入予定品目なし（0件）')
            return

        excel_data = _generate_excel(items, delivery_date, coverage_dates, supplier)

        progress_excel = None
        progress_pdf = None
        days_back = config.progress_days_back or 7
        days_forward = config.progress_days_forward or 30
        try:
            progress_excel = _generate_progress_excel(supplier, line, days_back, days_forward)
        except Exception as e:
            logger.warning(f'進度表Excel生成エラー（送信は続行）: {e}')
        try:
            progress_pdf = _generate_progress_pdf(supplier, line, days_back, days_forward)
        except Exception as e:
            logger.warning(f'進度表PDF生成エラー（送信は続行）: {e}')

        to_email = (supplier.order_email or '').strip()
        if not to_email:
            _finish(config, start_time, 'FAILED', f'仕入先 {supplier.supplier_code} のメールアドレスが未設定です')
            _notify_users(config.notify_on_failure, f'自動納入リスト失敗: {supplier.supplier_name} のメールアドレスが未設定です')
            return

        cc_list = [e.strip() for e in (config.cc_emails or '').splitlines() if e.strip()]

        email_service = EmailService()
        filename = f'納品リスト_{supplier.supplier_code}_{delivery_date}.xlsx'
        extra = []
        if progress_excel:
            extra.append({
                'data': progress_excel,
                'filename': f'進度表_{supplier.supplier_code}_{date.today()}.xlsx',
            })
        if progress_pdf:
            extra.append({
                'data': progress_pdf,
                'filename': f'進度表_{supplier.supplier_code}_{date.today()}.pdf',
            })

        reply_to = (config.reply_to_email or '').strip()
        reply_line = f'\n※ 返送先: {reply_to}\n（このメールは送信専用です。返信は上記アドレスへお願いいたします。）\n' if reply_to else ''

        result = email_service.send_email_with_attachment(
            to_emails=[to_email],
            subject=f'【納品リスト】{supplier.supplier_name} {delivery_date}',
            body=(
                f'{supplier.supplier_name} 御中\n\n'
                'お世話になっております。\n'
                f'納品リスト（納入日: {delivery_date}）を送付いたします。\n\n'
                f'対象品目: {len(items)}件\n'
                f'カバー期間: {coverage_dates[0]} ～ {coverage_dates[-1]}\n\n'
                '添付のExcelの「確認・修正方法」シートを参照のうえ、数量確認・修正後にご返送ください。\n'
                + ('進度表も添付しておりますのでご参照ください。\n' if progress_excel else '')
                + reply_line
                + '\n------------------------------\n'
                'ダイソウ工業株式会社\n'
            ),
            attachment_data=excel_data,
            attachment_filename=filename,
            cc_emails=cc_list if cc_list else None,
            extra_attachments=extra if extra else None,
            reply_to=reply_to or None,
        )

        if result.get('success'):
            cc_info = f' CC: {", ".join(cc_list)}' if cc_list else ''
            _finish(
                config, start_time, 'SUCCESS',
                f'{delivery_date} 納入リスト送信完了 ({len(items)}件) → {to_email}{cc_info}',
            )
        else:
            _finish(config, start_time, 'FAILED', f'メール送信失敗: {result.get("message", "")}')
            _notify_users(
                config.notify_on_failure,
                f'自動納入リスト送信失敗: {supplier.supplier_name}\n{result.get("message", "")}',
            )

    except Exception as e:
        logger.exception(f'自動納入リスト送信エラー: config_id={config_id}')
        _finish(config, start_time, 'FAILED', f'エラー: {str(e)[:500]}')
        _notify_users(config.notify_on_failure, f'自動納入リスト送信エラー: {supplier.supplier_name}\n{str(e)[:300]}')


def _finish(config, start_time, status_val, message):
    duration = round(time.time() - start_time, 2)
    config.last_run_status = status_val
    config.last_run_message = message
    config.last_run_duration_seconds = duration
    config.save(update_fields=['last_run_status', 'last_run_message', 'last_run_duration_seconds'])


def _notify_users(user_m2m, message):
    from notifications.models import Notification

    user_ids = list(user_m2m.values_list('id', flat=True))
    if not user_ids:
        return
    today = date.today()
    notification = Notification.objects.create(
        title=message[:200],
        category='購買',
        domain='PURCHASE_AUTO_DELIVERY',
        valid_from=today,
        valid_to=today + timedelta(days=7),
        description=message,
        operator_name='system',
    )
    notification.target_users.set(user_ids)


def _generate_excel(items, delivery_date, coverage_dates, supplier):
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()

    # --- シート1: 納品リスト ---
    ws = wb.active
    ws.title = '納品リスト'

    DAY_NAMES = ['月', '火', '水', '木', '金', '土', '日']
    date_headers = []
    for d in coverage_dates:
        dow = DAY_NAMES[d.weekday()]
        date_headers.append(f'{d.month}/{d.day}({dow})')

    left_headers = ['品番', '品名', '数量', '納品日']
    right_headers = ['仕入先コード', '伝票番号']
    headers = left_headers + date_headers + right_headers
    ws.append(headers)

    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True, size=10)
    date_fill = PatternFill(start_color='D9E2F3', end_color='D9E2F3', fill_type='solid')
    date_font = Font(bold=True, size=9)
    tail_fill = PatternFill(start_color='E2EFDA', end_color='E2EFDA', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin'),
    )

    date_start = len(left_headers) + 1
    date_end = date_start + len(date_headers) - 1
    tail_start = date_end + 1

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center', wrap_text=True)
        if col_idx <= len(left_headers):
            cell.fill = header_fill
            cell.font = header_font
        elif col_idx >= tail_start:
            cell.fill = tail_fill
            cell.font = Font(bold=True, size=10, color='375623')
        else:
            cell.fill = date_fill
            cell.font = date_font

    supplier_code = supplier.supplier_code or ''
    for row_idx, item in enumerate(items, 2):
        daily = item.get('daily', {})
        row_data = [
            item['product_code'],
            item['product_name'],
            item['expected_qty'],
            delivery_date.isoformat(),
        ]
        for d in coverage_dates:
            qty = daily.get(d.isoformat(), 0)
            row_data.append(qty if qty else '')
        row_data += [supplier_code, '']
        ws.append(row_data)
        for col_idx in range(1, len(row_data) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = thin_border
            if col_idx == 3 or (date_start <= col_idx <= date_end):
                cell.alignment = Alignment(horizontal='right')

    left_widths = [20, 30, 10, 14]
    for i, w in enumerate(left_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for i in range(date_start, date_end + 1):
        ws.column_dimensions[get_column_letter(i)].width = 10
    ws.column_dimensions[get_column_letter(tail_start)].width = 16
    ws.column_dimensions[get_column_letter(tail_start + 1)].width = 14

    ws.freeze_panes = 'A2'

    # --- シート2: 確認・修正方法 ---
    ws2 = wb.create_sheet('確認・修正方法')
    instructions = [
        ['【納品リストの確認・修正方法】'],
        [''],
        ['■ 基本ルール'],
        ['', '・「納品リスト」シートの「数量」列に納入予定数量が入っています。'],
        ['', '・数量を確認し、変更がなければそのまま弊社へ返送してください。'],
        ['', '・数量を変更したい場合は「数量」列の値を直接修正してください。'],
        [''],
        ['■ 数量の修正方法'],
        ['', '1. 数量を変更する場合 → 「数量」列を修正値に書き換え'],
        ['', '2. 納入しない製品がある場合 → 「数量」列を 0 に変更'],
        ['', '3. 数量が空白の行は取込時に除外されます（取消にはなりません）'],
        [''],
        ['■ 品番の追加'],
        ['', '・新しい品番を追加する場合は「製品リスト」シートから品番をコピーしてください。'],
        ['', '・品番を手入力すると不一致エラーの原因になります。'],
        [''],
        ['■ 注意事項'],
        ['', '・品番・品名・仕入先コードは変更しないでください。'],
        ['', '・このファイルをそのまま返送してください（ファイル形式を変えないこと）。'],
    ]
    for row in instructions:
        ws2.append(row)

    ws2.column_dimensions['A'].width = 4
    ws2.column_dimensions['B'].width = 70
    title_font = Font(bold=True, size=12)
    section_font = Font(bold=True, size=11)
    ws2.cell(row=1, column=1).font = title_font
    for r in [3, 8, 13, 17]:
        ws2.cell(row=r, column=1).font = section_font

    # --- シート3: 製品リスト ---
    ws3 = wb.create_sheet('製品リスト')
    ws3.append(['品番', '品名'])
    prod_header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    prod_header_font = Font(color='FFFFFF', bold=True, size=10)
    for col_idx in range(1, 3):
        cell = ws3.cell(row=1, column=col_idx)
        cell.fill = prod_header_fill
        cell.font = prod_header_font
        cell.border = thin_border

    from masters.models import Line, Product, RoutingStep
    line = Line.objects.filter(line_code=supplier.supplier_code).first()
    product_ids = set()
    if line:
        product_ids = set(
            RoutingStep.objects.filter(
                line=line,
                output_product__isnull=False,
                routing__is_active=True,
                routing__is_default=True,
            ).values_list('output_product_id', flat=True).distinct()
        )
    products = Product.objects.filter(id__in=product_ids).order_by('product_code') if product_ids else Product.objects.none()
    for row_idx, p in enumerate(products, 2):
        ws3.append([p.product_code or '', p.product_name or ''])
        for col_idx in range(1, 3):
            ws3.cell(row=row_idx, column=col_idx).border = thin_border

    ws3.column_dimensions['A'].width = 22
    ws3.column_dimensions['B'].width = 35
    ws3.freeze_panes = 'A2'

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


DAY_NAMES = ['月', '火', '水', '木', '金', '土', '日']
ROW_DEFS = [
    ('forecast', '内示'),
    ('firm', '確定'),
    ('actual', '実績'),
    ('progress', '進度'),
    ('planned_progress', '計進'),
]


def _collect_progress_data(line, days_back, days_forward=30):
    """進度表データを収集して返す。Excel/PDF共通。"""
    from collections import defaultdict
    from masters.models import Calendar
    from orders.utils.calendar_utils import WorkingDayCalculator
    from production.models import LineDemand
    from production.models_line_backlog import LineBacklog

    today = date.today()
    daiso_cal = Calendar.objects.filter(calendar_code='daiso').first()
    calc = WorkingDayCalculator(daiso_cal)
    start_date = calc.subtract_working_days(today, days_back)
    end_date = start_date + timedelta(days=days_forward)

    date_list = []
    d = start_date
    while d <= end_date:
        date_list.append(d)
        d += timedelta(days=1)

    demand_qs = LineDemand.objects.filter(
        line=line, plan_date__gte=start_date, plan_date__lte=end_date,
    ).select_related('product')

    demand_by_product_date = defaultdict(lambda: defaultdict(lambda: {'forecast': 0, 'firm': 0}))
    product_info = {}
    for dm in demand_qs:
        pid = dm.product_id
        if pid not in product_info:
            product_info[pid] = {
                'product_code': dm.product.product_code if dm.product else dm.product_code,
                'product_name': dm.product.product_name if dm.product else '',
            }
        dd = demand_by_product_date[pid][dm.plan_date]
        dd['forecast'] += int(dm.forecast_qty or 0)
        dd['firm'] += int(dm.firm_qty or 0)

    backlog_qs = LineBacklog.objects.filter(
        line=line, plan_date__gte=start_date, plan_date__lte=end_date,
    ).select_related('product')

    backlog_by_product_date = defaultdict(lambda: defaultdict(lambda: {
        'actual': 0, 'progress': 0, 'planned_progress': 0,
    }))
    for bl in backlog_qs:
        pid = bl.product_id
        if pid not in product_info and bl.product:
            product_info[pid] = {
                'product_code': bl.product.product_code,
                'product_name': bl.product.product_name,
            }
        bd = backlog_by_product_date[pid][bl.plan_date]
        bd['actual'] += int(bl.actual_qty or 0)
        bd['progress'] += int(bl.progress_qty or 0)
        bd['planned_progress'] += int(getattr(bl, 'planned_progress_qty', 0) or 0)

    if not product_info:
        return None

    # 繰越: 開始日前日の進度・計進を取得
    prev_date = start_date - timedelta(days=1)
    carryover_qs = LineBacklog.objects.filter(
        line=line, plan_date=prev_date, product_id__in=product_info.keys(),
    )
    carryover_by_pid = {}
    for bl in carryover_qs:
        pid = bl.product_id
        if pid not in carryover_by_pid:
            carryover_by_pid[pid] = {'progress': 0, 'planned_progress': 0}
        carryover_by_pid[pid]['progress'] += int(bl.progress_qty or 0)
        carryover_by_pid[pid]['planned_progress'] += int(getattr(bl, 'planned_progress_qty', 0) or 0)

    sorted_pids = sorted(product_info.keys(), key=lambda pid: product_info[pid]['product_code'])
    return {
        'today': today,
        'start_date': start_date,
        'end_date': end_date,
        'date_list': date_list,
        'product_info': product_info,
        'sorted_pids': sorted_pids,
        'demand_by_product_date': demand_by_product_date,
        'backlog_by_product_date': backlog_by_product_date,
        'carryover_by_pid': carryover_by_pid,
    }

def _generate_progress_excel(supplier, line, days_back, days_forward=30):
    """仕入先の全製品の進度表Excelを生成"""
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    data = _collect_progress_data(line, days_back, days_forward)
    if not data:
        return None

    today = data['today']
    start_date = data['start_date']
    end_date = data['end_date']
    date_list = data['date_list']
    product_info = data['product_info']
    sorted_pids = data['sorted_pids']
    demand_by_product_date = data['demand_by_product_date']
    backlog_by_product_date = data['backlog_by_product_date']
    carryover_by_pid = data['carryover_by_pid']

    wb = Workbook()
    ws = wb.active
    ws.title = '進度表'

    FONT_SIZE = 9
    base_font = Font(size=FONT_SIZE)
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True, size=FONT_SIZE)
    label_fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
    label_font = Font(bold=True, size=FONT_SIZE)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin'),
    )
    today_fill = PatternFill(start_color='D6EAFF', end_color='D6EAFF', fill_type='solid')
    negative_font = Font(color='FF0000', size=FONT_SIZE)
    positive_font = Font(color='0000FF', size=FONT_SIZE)
    weekend_fill = PatternFill(start_color='FFF0F0', end_color='FFF0F0', fill_type='solid')

    current_row = 1

    ws.cell(row=current_row, column=1, value=f'進度表 — {supplier.supplier_code} {supplier.supplier_name}')
    ws.cell(row=current_row, column=1).font = Font(bold=True, size=12)
    current_row += 1
    ws.cell(row=current_row, column=1, value=f'発行日: {today}　期間: {start_date} ～ {end_date}')
    ws.cell(row=current_row, column=1).font = Font(size=9, color='666666')
    current_row += 1
    legend_cell = ws.cell(row=current_row, column=1, value='■ 当日')
    legend_cell.font = Font(size=8, color='4A90D9')
    ws.cell(row=current_row, column=1).fill = PatternFill(start_color='D6EAFF', end_color='D6EAFF', fill_type='solid')
    ws.cell(row=current_row, column=2, value='■ 休日')
    ws.cell(row=current_row, column=2).font = Font(size=8, color='CC6666')
    ws.cell(row=current_row, column=2).fill = PatternFill(start_color='FFD9D9', end_color='FFD9D9', fill_type='solid')
    current_row += 2

    for pid in sorted_pids:
        info = product_info[pid]
        demands = demand_by_product_date[pid]
        backlogs = backlog_by_product_date[pid]

        ws.cell(row=current_row, column=1, value=info['product_code'])
        ws.cell(row=current_row, column=1).font = Font(bold=True, size=10)
        current_row += 1
        ws.cell(row=current_row, column=1, value=info['product_name'])
        ws.cell(row=current_row, column=1).font = Font(size=9, color='555555')

        date_header_row = current_row
        carry_col = 3
        carry_cell = ws.cell(row=date_header_row, column=carry_col, value='繰越')
        carry_cell.font = header_font
        carry_cell.fill = header_fill
        carry_cell.alignment = Alignment(horizontal='center')
        carry_cell.border = thin_border
        DATE_COL_START = 4
        for col_idx, dt in enumerate(date_list, DATE_COL_START):
            dow = DAY_NAMES[dt.weekday()]
            cell = ws.cell(row=date_header_row, column=col_idx, value=f'{dt.month}/{dt.day}\n{dow}')
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center', wrap_text=True)
            cell.border = thin_border
        current_row += 1

        carryover = carryover_by_pid.get(pid, {})
        for row_key, row_label in ROW_DEFS:
            ws.cell(row=current_row, column=1, value='')
            label_cell = ws.cell(row=current_row, column=2, value=row_label)
            label_cell.fill = label_fill
            label_cell.font = label_font
            label_cell.border = thin_border

            # 繰越列
            cv = carryover.get(row_key, 0) if row_key in ('progress', 'planned_progress') else ''
            cc = ws.cell(row=current_row, column=carry_col, value=cv if cv else '')
            cc.border = thin_border
            cc.alignment = Alignment(horizontal='right')
            cc.font = base_font
            if row_key in ('progress', 'planned_progress') and cv:
                cc.font = negative_font if cv < 0 else (positive_font if cv > 0 else base_font)

            for col_idx, dt in enumerate(date_list, DATE_COL_START):
                if row_key in ('forecast', 'firm'):
                    val = demands[dt].get(row_key, 0) if dt in demands else 0
                else:
                    val = backlogs[dt].get(row_key, 0) if dt in backlogs else 0

                cell = ws.cell(row=current_row, column=col_idx, value=val if val else '')
                cell.border = thin_border
                cell.alignment = Alignment(horizontal='right')
                cell.font = base_font

                is_weekend = dt.weekday() >= 5
                is_today = dt == today

                if row_key in ('progress', 'planned_progress') and val:
                    if val < 0:
                        cell.font = negative_font
                    elif val > 0:
                        cell.font = positive_font

                if is_today:
                    cell.fill = today_fill
                elif is_weekend:
                    cell.fill = weekend_fill

            current_row += 1

        current_row += 1

    ws.column_dimensions['A'].width = 18
    ws.column_dimensions['B'].width = 10
    ws.column_dimensions['C'].width = 8
    for col_idx in range(DATE_COL_START, len(date_list) + DATE_COL_START):
        ws.column_dimensions[get_column_letter(col_idx)].width = 7
    ws.freeze_panes = 'D5'

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def _generate_progress_pdf(supplier, line, days_back, days_forward=30):
    """仕入先の全製品の進度表PDFを生成（横向き）"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as pdf_canvas
    from shipping.services.shipping_pdf_generator import register_japanese_fonts

    data = _collect_progress_data(line, days_back, days_forward)
    if not data:
        return None

    register_japanese_fonts()

    today = data['today']
    start_date = data['start_date']
    end_date = data['end_date']
    date_list = data['date_list']
    product_info = data['product_info']
    sorted_pids = data['sorted_pids']
    demand_by_product_date = data['demand_by_product_date']
    backlog_by_product_date = data['backlog_by_product_date']
    carryover_by_pid = data['carryover_by_pid']

    page_w, page_h = landscape(A4)
    margin_left = 5 * mm
    margin_right = 3 * mm
    margin_top = 12 * mm
    margin_bottom = 6 * mm

    CARRY_W = 9 * mm
    LABEL_W = 8 * mm
    CODE_W = 16 * mm
    NAME_W = 10 * mm
    LEFT_W = CODE_W + NAME_W + LABEL_W + CARRY_W
    DATE_W = 7.5 * mm
    ROW_H = 3.2 * mm
    HEADER_H = 4.5 * mm
    FONT_NAME = 'MSGothic'
    FONT_SIZE = 5.5
    HEADER_FONT_SIZE = 5

    available_w = page_w - margin_left - margin_right - LEFT_W
    DATES_PER_PAGE = int(available_w / DATE_W)

    buf = BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=landscape(A4))

    date_chunks = [date_list[i:i + DATES_PER_PAGE] for i in range(0, len(date_list), DATES_PER_PAGE)]
    product_block_h = (len(ROW_DEFS) + 2) * ROW_H + HEADER_H
    usable_h = page_h - margin_top - margin_bottom - 10 * mm
    products_per_page = max(1, int(usable_h / product_block_h))

    total_pages = 0
    for _ in date_chunks:
        total_pages += max(1, -(-len(sorted_pids) // products_per_page))

    page_num = 0
    for date_chunk in date_chunks:
        pid_chunks = [sorted_pids[i:i + products_per_page] for i in range(0, len(sorted_pids), products_per_page)]

        for pid_chunk in pid_chunks:
            page_num += 1

            c.setFont(FONT_NAME, 9)
            c.drawString(margin_left, page_h - 7 * mm, f'進度表 — {supplier.supplier_code} {supplier.supplier_name}')
            c.setFont(FONT_NAME, 5)
            c.setFillColor(colors.grey)
            c.drawString(margin_left, page_h - 10.5 * mm, f'発行日: {today}　期間: {start_date} ～ {end_date}')
            c.drawRightString(page_w - margin_right, page_h - 7 * mm, f'PAGE {page_num}/{total_pages}')

            legend_y = page_h - 10.5 * mm
            legend_x = page_w - margin_right - 80 * mm
            box = 2.5 * mm
            c.setFillColor(colors.Color(0.84, 0.92, 1.0))
            c.rect(legend_x, legend_y - 0.5 * mm, box, box, fill=1, stroke=1)
            c.setFillColor(colors.grey)
            c.drawString(legend_x + box + 1 * mm, legend_y, '当日')
            legend_x += 16 * mm
            c.setFillColor(colors.Color(1, 0.85, 0.85))
            c.rect(legend_x, legend_y - 0.5 * mm, box, box, fill=1, stroke=1)
            c.setFillColor(colors.grey)
            c.drawString(legend_x + box + 1 * mm, legend_y, '休日')
            c.setFillColor(colors.black)

            y = page_h - margin_top - 2 * mm

            for pid in pid_chunk:
                info = product_info[pid]
                demands = demand_by_product_date[pid]
                backlogs = backlog_by_product_date[pid]

                # 品番行
                x = margin_left
                c.setFillColor(colors.black)
                c.setFont(FONT_NAME, 6)
                c.drawString(x, y - ROW_H * 0.75, info['product_code'])
                y -= ROW_H
                # 品名行
                c.setFont(FONT_NAME, 5)
                c.setFillColor(colors.Color(0.3, 0.3, 0.3))
                c.drawString(x + 1 * mm, y - ROW_H * 0.75, info['product_name'] or '')
                c.setFillColor(colors.black)
                y -= ROW_H

                GRID_COLOR = colors.Color(0.5, 0.5, 0.5)
                c.setLineWidth(0.25)
                WEEKEND_BG = colors.Color(1, 0.85, 0.85)
                TODAY_BG = colors.Color(0.84, 0.92, 1.0)

                # 繰越ヘッダー
                carry_x = margin_left + CODE_W + NAME_W + LABEL_W
                c.setStrokeColor(GRID_COLOR)
                c.rect(carry_x, y - HEADER_H, CARRY_W, HEADER_H, fill=0, stroke=1)
                c.setFillColor(colors.black)
                c.setFont(FONT_NAME, HEADER_FONT_SIZE)
                c.drawCentredString(carry_x + CARRY_W / 2, y - 3 * mm, '繰越')

                # 日付ヘッダー
                x = margin_left + LEFT_W
                prev_month = None

                for dt in date_chunk:
                    is_today = dt == today
                    is_weekend = dt.weekday() >= 5

                    if is_weekend:
                        c.setFillColor(WEEKEND_BG)
                        c.rect(x, y - HEADER_H, DATE_W, HEADER_H, fill=1, stroke=0)
                    if is_today:
                        c.setFillColor(TODAY_BG)
                        c.rect(x, y - HEADER_H, DATE_W, HEADER_H, fill=1, stroke=0)

                    c.setStrokeColor(GRID_COLOR)
                    c.rect(x, y - HEADER_H, DATE_W, HEADER_H, fill=0, stroke=1)

                    c.setFillColor(colors.black)
                    c.setFont(FONT_NAME, HEADER_FONT_SIZE)
                    label = f'{dt.day}日'
                    if prev_month is None or dt.month != prev_month:
                        label = f'{dt.month}/{dt.day}'
                    prev_month = dt.month
                    dow = DAY_NAMES[dt.weekday()]
                    c.drawCentredString(x + DATE_W / 2, y - 2.2 * mm, label)
                    c.setFont(FONT_NAME, 4)
                    c.drawCentredString(x + DATE_W / 2, y - HEADER_H + 0.5 * mm, dow)
                    x += DATE_W

                y -= HEADER_H

                # データ行
                carryover = carryover_by_pid.get(pid, {})
                for row_key, row_label in ROW_DEFS:
                    # ラベル
                    lx = margin_left + CODE_W + NAME_W
                    c.setFillColor(colors.Color(0.9, 0.9, 0.9))
                    c.rect(lx, y - ROW_H, LABEL_W, ROW_H, fill=1, stroke=0)
                    c.setStrokeColor(GRID_COLOR)
                    c.rect(lx, y - ROW_H, LABEL_W, ROW_H, fill=0, stroke=1)
                    c.setFillColor(colors.black)
                    c.setFont(FONT_NAME, FONT_SIZE)
                    c.drawString(lx + 0.5 * mm, y - ROW_H * 0.78, row_label)

                    # 繰越セル
                    c.setStrokeColor(GRID_COLOR)
                    c.rect(carry_x, y - ROW_H, CARRY_W, ROW_H, fill=0, stroke=1)
                    cv = carryover.get(row_key, 0) if row_key in ('progress', 'planned_progress') else 0
                    if cv:
                        if cv < 0:
                            c.setFillColor(colors.red)
                        elif cv > 0:
                            c.setFillColor(colors.blue)
                        else:
                            c.setFillColor(colors.black)
                        c.setFont(FONT_NAME, FONT_SIZE)
                        c.drawRightString(carry_x + CARRY_W - 0.5 * mm, y - ROW_H * 0.78, str(cv))
                        c.setFillColor(colors.black)

                    # 日付セル
                    x = margin_left + LEFT_W
                    for dt in date_chunk:
                        is_today = dt == today
                        is_weekend = dt.weekday() >= 5

                        if is_today:
                            c.setFillColor(TODAY_BG)
                            c.rect(x, y - ROW_H, DATE_W, ROW_H, fill=1, stroke=0)
                        elif is_weekend:
                            c.setFillColor(WEEKEND_BG)
                            c.rect(x, y - ROW_H, DATE_W, ROW_H, fill=1, stroke=0)

                        c.setStrokeColor(GRID_COLOR)
                        c.rect(x, y - ROW_H, DATE_W, ROW_H, fill=0, stroke=1)

                        if row_key in ('forecast', 'firm'):
                            val = demands[dt].get(row_key, 0) if dt in demands else 0
                        else:
                            val = backlogs[dt].get(row_key, 0) if dt in backlogs else 0

                        if val:
                            if row_key in ('progress', 'planned_progress') and val < 0:
                                c.setFillColor(colors.red)
                            elif row_key in ('progress', 'planned_progress') and val > 0:
                                c.setFillColor(colors.blue)
                            else:
                                c.setFillColor(colors.black)
                            c.setFont(FONT_NAME, FONT_SIZE)
                            c.drawRightString(x + DATE_W - 0.5 * mm, y - ROW_H * 0.78, str(val))
                            c.setFillColor(colors.black)

                        x += DATE_W
                    y -= ROW_H

                # 製品間の区切り線
                table_right = margin_left + LEFT_W + len(date_chunk) * DATE_W
                c.setLineWidth(0.5)
                c.setStrokeColor(colors.black)
                c.line(margin_left, y, table_right, y)
                c.setLineWidth(0.25)
                y -= 1.5 * mm

            c.showPage()

    c.save()
    buf.seek(0)
    return buf
