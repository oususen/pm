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

        if not items:
            _finish(config, start_time, 'SUCCESS', f'{delivery_date} の納入予定品目なし（0件）')
            return

        excel_data = _generate_excel(items, delivery_date, coverage_dates, supplier)

        progress_excel = None
        days_back = config.progress_days_back or 7
        try:
            progress_excel = _generate_progress_excel(supplier, line, days_back)
        except Exception as e:
            logger.warning(f'進度表Excel生成エラー（送信は続行）: {e}')

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

        result = email_service.send_email_with_attachment(
            to_emails=[to_email],
            subject=f'【納品リスト】{supplier.supplier_name} {delivery_date}',
            body=(
                f'{supplier.supplier_name} 御中\n\n'
                'お世話になっております。\n'
                f'納品リスト（納入日: {delivery_date}）を送付いたします。\n\n'
                f'対象品目: {len(items)}件\n'
                f'カバー期間: {coverage_dates[0]} ～ {coverage_dates[-1]}\n\n'
                '添付のExcelをご確認のうえ、数量確認・修正後にご返送ください。\n'
                + ('進度表も添付しておりますのでご参照ください。\n' if progress_excel else '')
                + '\n------------------------------\n'
                'ダイソウ工業株式会社\n'
            ),
            attachment_data=excel_data,
            attachment_filename=filename,
            cc_emails=cc_list if cc_list else None,
            extra_attachments=extra if extra else None,
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


def _generate_progress_excel(supplier, line, days_back):
    """仕入先の全製品の進度表Excelを生成"""
    from collections import defaultdict
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    from production.models import LineDemand
    from production.models_line_backlog import LineBacklog

    from masters.models import Calendar
    from orders.utils.calendar_utils import WorkingDayCalculator

    today = date.today()
    daiso_cal = Calendar.objects.filter(calendar_code='daiso').first()
    calc = WorkingDayCalculator(daiso_cal)
    start_date = calc.subtract_working_days(today, days_back)
    end_date = today + timedelta(days=60)

    date_list = []
    d = start_date
    while d <= end_date:
        date_list.append(d)
        d += timedelta(days=1)

    demand_qs = LineDemand.objects.filter(
        line=line,
        plan_date__gte=start_date,
        plan_date__lte=end_date,
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
        line=line,
        plan_date__gte=start_date,
        plan_date__lte=end_date,
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

    sorted_pids = sorted(product_info.keys(), key=lambda pid: product_info[pid]['product_code'])

    wb = Workbook()
    ws = wb.active
    ws.title = '進度表'

    DAY_NAMES = ['月', '火', '水', '木', '金', '土', '日']
    ROW_DEFS = [
        ('forecast', '内示'),
        ('firm', '確定'),
        ('actual', '実績'),
        ('progress', '進度'),
        ('planned_progress', '計進'),
    ]

    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True, size=9)
    label_fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
    label_font = Font(bold=True, size=9)
    progress_font = Font(bold=True, size=9)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin'),
    )
    today_fill = PatternFill(start_color='FFFFCC', end_color='FFFFCC', fill_type='solid')
    negative_font = Font(color='FF0000', size=9)
    positive_font = Font(color='0000FF', size=9)
    weekend_fill = PatternFill(start_color='FFF0F0', end_color='FFF0F0', fill_type='solid')

    current_row = 1

    ws.cell(row=current_row, column=1, value=f'進度表 — {supplier.supplier_code} {supplier.supplier_name}')
    ws.cell(row=current_row, column=1).font = Font(bold=True, size=12)
    current_row += 1
    ws.cell(row=current_row, column=1, value=f'発行日: {today}　期間: {start_date} ～ {end_date}')
    ws.cell(row=current_row, column=1).font = Font(size=9, color='666666')
    current_row += 2

    for pid in sorted_pids:
        info = product_info[pid]
        demands = demand_by_product_date[pid]
        backlogs = backlog_by_product_date[pid]

        ws.cell(row=current_row, column=1, value=info['product_code'])
        ws.cell(row=current_row, column=1).font = Font(bold=True, size=10)
        ws.cell(row=current_row, column=2, value=info['product_name'])
        ws.cell(row=current_row, column=2).font = Font(size=9)

        date_header_row = current_row
        for col_idx, dt in enumerate(date_list, 3):
            dow = DAY_NAMES[dt.weekday()]
            cell = ws.cell(row=date_header_row, column=col_idx, value=f'{dt.month}/{dt.day}\n{dow}')
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center', wrap_text=True)
            cell.border = thin_border
        current_row += 1

        for row_key, row_label in ROW_DEFS:
            ws.cell(row=current_row, column=1, value='')
            label_cell = ws.cell(row=current_row, column=2, value=row_label)
            label_cell.fill = label_fill
            label_cell.font = label_font
            label_cell.border = thin_border

            for col_idx, dt in enumerate(date_list, 3):
                if row_key in ('forecast', 'firm'):
                    val = demands[dt].get(row_key, 0) if dt in demands else 0
                else:
                    val = backlogs[dt].get(row_key, 0) if dt in backlogs else 0

                cell = ws.cell(row=current_row, column=col_idx, value=val if val else '')
                cell.border = thin_border
                cell.alignment = Alignment(horizontal='right')

                is_weekend = dt.weekday() >= 5
                is_today = dt == today

                if row_key == 'progress' and val:
                    if val < 0:
                        cell.font = negative_font
                    elif val > 0:
                        cell.font = positive_font
                    else:
                        cell.font = progress_font

                if is_today:
                    cell.fill = today_fill
                elif is_weekend:
                    cell.fill = weekend_fill

            current_row += 1

        current_row += 1

    ws.column_dimensions['A'].width = 18
    ws.column_dimensions['B'].width = 10
    for col_idx in range(3, len(date_list) + 3):
        ws.column_dimensions[get_column_letter(col_idx)].width = 7
    ws.freeze_panes = 'C5'

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output
