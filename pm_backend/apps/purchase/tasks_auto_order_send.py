import logging
import time
from datetime import date, datetime, timedelta
from io import BytesIO

logger = logging.getLogger('purchase')


def _create_auto_order_send_history(config, trigger_type):
    from .models import PurchaseAutoOrderSendHistory

    supplier = config.supplier
    return PurchaseAutoOrderSendHistory.objects.create(
        config=config,
        supplier=supplier,
        supplier_code=getattr(supplier, 'supplier_code', '') or '',
        supplier_name=getattr(supplier, 'supplier_name', '') or '',
        trigger_type=trigger_type,
        status=PurchaseAutoOrderSendHistory.STATUS_RUNNING,
    )


def _save_history_order_excel(history, excel_buffer, filename):
    if not history or not excel_buffer:
        return
    from django.core.files.base import ContentFile

    excel_buffer.seek(0)
    history.order_excel_file.save(filename, ContentFile(excel_buffer.getvalue()), save=False)
    history.save(update_fields=['order_excel_file'])


def _finish_history(history, start_time, status_val, message, **extra_updates):
    if not history:
        return
    history.status = status_val
    history.message = message
    history.duration_seconds = round(time.time() - start_time, 2)
    history.finished_at = datetime.now()
    for key, value in extra_updates.items():
        setattr(history, key, value)
    history.save()


def _extract_attachment_labels(order_excel_enabled, delivery_note_enabled, progress_excel_enabled, progress_pdf_enabled):
    labels = []
    if order_excel_enabled:
        labels.append('注文書Excel')
    if delivery_note_enabled:
        labels.append('外作納品書PDF')
    if progress_excel_enabled:
        labels.append('進度表Excel')
    if progress_pdf_enabled:
        labels.append('進度表PDF')
    return labels


def run_auto_order_send(config_id, ignore_holiday=False, trigger_type='SCHEDULED'):
    from masters.models import Calendar
    from orders.utils.calendar_utils import WorkingDayCalculator
    from production.models_line_backlog import LineBacklog
    from shipping.services.email_service import EmailService

    from .models import PurchaseAutoOrderSendConfig
    from .process_resolver import resolve_purchase_line
    from .services_auto_order_send import (
        generate_order_excel,
        resolve_delivery_cycles,
        simulate_and_save_order_plans,
    )
    from .tasks_auto_delivery_list import (
        _dn_nohin,
        _dn_side,
        _generate_progress_excel,
        _generate_progress_pdf,
        _recalculate_supplier_progress_for_auto_delivery,
    )

    start_time = time.time()
    config = PurchaseAutoOrderSendConfig.objects.select_related('supplier').filter(id=config_id).first()
    if not config:
        logger.error('注文書自動送信設定が見つかりません: config_id=%s', config_id)
        return

    supplier = config.supplier
    history = _create_auto_order_send_history(config, trigger_type)
    config.last_run_at = datetime.now()
    config.last_run_status = 'RUNNING'
    config.last_run_message = '実行中...'
    config.save(update_fields=['last_run_at', 'last_run_status', 'last_run_message'])

    try:
        today = (datetime.now() - timedelta(hours=8)).date()
        daiso_cal = Calendar.objects.filter(calendar_code='daiso').first()
        if not daiso_cal:
            _finish(config, start_time, 'FAILED', 'ダイソウカレンダーが未設定のため、注文書自動送信を実行できません')
            _notify_users(config.notify_on_failure, '注文書自動送信失敗: ダイソウカレンダーが未設定です')
            return

        calc = WorkingDayCalculator(daiso_cal)
        if not ignore_holiday and not calc.is_working_day(today):
            message = f'本日は休日のため、{supplier.supplier_name} 向け注文書自動送信は実行しません'
            _finish(config, start_time, 'SKIPPED', message)
            _finish_history(history, start_time, 'SKIPPED', message)
            _notify_users(config.notify_on_non_delivery, f'注文書自動送信: {message}')
            return

        days_back = max(int(config.progress_days_back or 7), 1)
        days_forward = int(config.progress_days_forward or 30)
        line = resolve_purchase_line(supplier)

        # ── ステップ2: 納入サイクル解決 → 対象納入日を取得 ──
        cycle_result = resolve_delivery_cycles(config, base_date=today)
        if cycle_result['status'] == 'SUCCESS' and cycle_result['cycles'] and line:
            delivery_dates_to_clean = [c['delivery_date'] for c in cycle_result['cycles']]

            # ── ステップ3: 対象納入日の既存計画(sequence_no=1)を全削除 ──
            deleted_count, _ = LineBacklog.objects.filter(
                line_id=line.id,
                plan_date__in=delivery_dates_to_clean,
                sequence_no=1,
            ).delete()
            logger.info(
                '注文書自動送信: 既存計画削除 supplier=%s dates=%s deleted=%d',
                supplier.supplier_code, delivery_dates_to_clean, deleted_count,
            )

            # ── ステップ4: 計進・進度再計算（先頭）──
            _recalculate_supplier_progress_for_auto_delivery(
                supplier, line, days_back, days_forward,
            )
            logger.info(
                '注文書自動送信: 先頭進度再計算完了 supplier=%s',
                supplier.supplier_code,
            )

        # ── ステップ5: simulate_and_save_order_plans（既存）──
        result = simulate_and_save_order_plans(config, base_date=today)
        if result['status'] != 'SUCCESS':
            _finish(config, start_time, result['status'], result['message'])
            _finish_history(history, start_time, result['status'], result['message'])
            notify_target = config.notify_on_non_delivery if result['status'] == 'SKIPPED' else config.notify_on_failure
            _notify_users(notify_target, f'注文書自動送信: {result["message"]}')
            return

        items = result['items']
        line = result.get('line') or line

        # ── ステップ6: 計進・進度再計算（後尾）──
        if line:
            _recalculate_supplier_progress_for_auto_delivery(
                supplier, line, days_back, days_forward,
            )
            logger.info(
                '注文書自動送信: 後尾進度再計算完了 supplier=%s',
                supplier.supplier_code,
            )

        # ── ステップ7: 進度表Excel + PDF生成 ──
        progress_excel = None
        progress_pdf = None
        if line:
            try:
                progress_excel = _generate_progress_excel(supplier, line, days_back, days_forward)
            except Exception as e:
                logger.warning('進度表Excel生成エラー: %s', e)
            try:
                progress_pdf = _generate_progress_pdf(supplier, line, days_back, days_forward)
            except Exception as e:
                logger.warning('進度表PDF生成エラー: %s', e)

        # ── ステップ8: 注文書Excel生成 + 添付ファイル構築 ──
        all_attachments = []
        excel_filename = ''
        if items and config.send_order_excel:
            excel_data = generate_order_excel(items, supplier)
            excel_filename = f'注文書_{supplier.supplier_code}_{today}.xlsx'
            _save_history_order_excel(history, excel_data, excel_filename)
            all_attachments.append({
                'data': excel_data,
                'filename': excel_filename,
                'label': '注文書Excel',
            })
        delivery_note_pdf = None
        if items and config.send_delivery_note_pdf:
            try:
                delivery_note_pdf = _generate_order_send_delivery_note_pdf(items, supplier)
            except Exception as e:
                logger.warning('外作納品書PDF生成エラー: %s', e)
        if delivery_note_pdf:
            first_delivery_date = min(item['delivery_date'] for item in items)
            all_attachments.append({
                'data': delivery_note_pdf,
                'filename': f'外作納品書_{supplier.supplier_code}_{first_delivery_date}.pdf',
                'label': '外作納品書PDF',
            })
        if progress_excel and config.send_progress_excel:
            all_attachments.append({
                'data': progress_excel,
                'filename': f'進度表_{supplier.supplier_code}_{today}.xlsx',
                'label': '進度表Excel',
            })
        if progress_pdf and config.send_progress_pdf:
            all_attachments.append({
                'data': progress_pdf,
                'filename': f'進度表_{supplier.supplier_code}_{today}.pdf',
                'label': '進度表PDF',
            })

        if not all_attachments:
            message = result.get('message') or '対象データはありません'
            _finish(config, start_time, 'SUCCESS', message)
            _finish_history(
                history,
                start_time,
                'SUCCESS',
                message,
                order_item_count=len(items or []),
            )
            return

        if (
            not config.send_order_excel
            and not config.send_progress_excel
            and not config.send_progress_pdf
            and not delivery_note_pdf
        ):
            message = '送信ファイル設定がすべてOFFです'
            _finish(config, start_time, 'SKIPPED', message)
            _finish_history(
                history,
                start_time,
                'SKIPPED',
                message,
                order_item_count=len(items or []),
            )
            return

        to_email = (supplier.order_email or '').strip()
        if not to_email:
            message = f'仕入先 {supplier.supplier_code} のメールアドレスが未設定です'
            _finish(config, start_time, 'FAILED', message)
            _finish_history(
                history,
                start_time,
                'FAILED',
                message,
                order_item_count=len(items or []),
            )
            _notify_users(config.notify_on_failure, f'注文書自動送信失敗: {supplier.supplier_name} のメールアドレスが未設定です')
            return

        cc_list = [email.strip() for email in (config.cc_emails or '').splitlines() if email.strip()]
        reply_to = (config.reply_to_email or '').strip()
        attachment_labels = _extract_attachment_labels(
            order_excel_enabled=bool(items and config.send_order_excel),
            delivery_note_enabled=bool(delivery_note_pdf),
            progress_excel_enabled=bool(progress_excel and config.send_progress_excel),
            progress_pdf_enabled=bool(progress_pdf and config.send_progress_pdf),
        )
        attachment_labels_text = '\n'.join(attachment_labels)

        delivery_dates = sorted({item['delivery_date'] for item in items}) if items else []
        subject_parts = []
        if items and config.send_order_excel:
            subject_parts.append('注文書')
        if delivery_note_pdf:
            subject_parts.append('外作納品書')
        if (progress_excel and config.send_progress_excel) or (progress_pdf and config.send_progress_pdf):
            subject_parts.append('進度表')
        subject_label = '・'.join(subject_parts) or '添付資料'
        if delivery_dates:
            subject = f'【{subject_label}】{supplier.supplier_code} {delivery_dates[0]}'
        else:
            subject = f'【{subject_label}】{supplier.supplier_code} {today}'
        body = _build_mail_body(
            config,
            supplier,
            items,
            delivery_dates,
            has_order_excel=bool(items and config.send_order_excel),
            has_delivery_note_pdf=bool(delivery_note_pdf),
        )

        # ── ステップ9: メール送信 ──
        main_attach = all_attachments[0]
        extra = all_attachments[1:] if len(all_attachments) > 1 else None

        email_service = EmailService()
        send_result = email_service.send_email_with_attachment(
            to_emails=[to_email],
            subject=subject,
            body=body,
            attachment_data=main_attach['data'],
            attachment_filename=main_attach['filename'],
            cc_emails=cc_list if cc_list else None,
            extra_attachments=extra,
            reply_to=reply_to or None,
        )

        attach_summary = attachment_labels[:]
        if items and config.send_order_excel:
            attach_summary[0] = f'注文書Excel{len(items)}件'

        if send_result.get('success'):
            message = f'送信完了 ({", ".join(attach_summary)}) → {to_email}'
            _finish(
                config,
                start_time,
                'SUCCESS',
                message,
            )
            _finish_history(
                history,
                start_time,
                'SUCCESS',
                message,
                to_email=to_email,
                cc_emails='\n'.join(cc_list),
                subject=subject,
                attachment_labels=attachment_labels_text,
                first_delivery_date=delivery_dates[0] if delivery_dates else None,
                order_item_count=len(items or []),
            )
        else:
            message = f'メール送信失敗: {send_result.get("message", "")}'
            _finish(config, start_time, 'FAILED', message)
            _finish_history(
                history,
                start_time,
                'FAILED',
                message,
                to_email=to_email,
                cc_emails='\n'.join(cc_list),
                subject=subject,
                attachment_labels=attachment_labels_text,
                first_delivery_date=delivery_dates[0] if delivery_dates else None,
                order_item_count=len(items or []),
            )
            _notify_users(config.notify_on_failure, f'注文書自動送信失敗: {supplier.supplier_name}\n{message}')
    except Exception as exc:
        logger.exception('注文書自動送信エラー: config_id=%s', config_id)
        _finish(config, start_time, 'FAILED', f'エラー: {str(exc)[:500]}')
        _finish_history(history, start_time, 'FAILED', f'エラー: {str(exc)[:500]}')
        _notify_users(config.notify_on_failure, f'注文書自動送信エラー: {supplier.supplier_name}\n{str(exc)[:300]}')


def _build_mail_body(config, supplier, items, delivery_dates, has_order_excel=False, has_delivery_note_pdf=False):
    if config.email_body_custom.strip():
        return f'{supplier.supplier_name} 御中\n\n{config.email_body_custom.strip()}\n'

    body_lines = [
        f'{supplier.supplier_name} 御中',
        '',
        'お世話になっております。',
    ]

    if items and delivery_dates:
        first_date = delivery_dates[0].isoformat()
        intro = '注文書を送付いたします。' if has_order_excel else '添付資料を送付いたします。'
        body_lines.extend([
            intro,
            '',
            f'対象納入回: {len(delivery_dates)}回',
            f'対象納入日: {first_date}',
            f'対象品目: {len(items)}件',
        ])
    if has_delivery_note_pdf:
        body_lines.extend([
            '',
            '外作納品書を添付しておりますのでご利用ください。',
        ])
    body_lines.extend([
        '',
        '添付ファイルをご確認ください。',
    ])
    if config.reply_to_email:
        body_lines.extend([
            '',
            f'※ 返送先: {config.reply_to_email}',
            '（このメールは送信専用です。返信は上記アドレスへお願いいたします。）',
        ])
    body_lines.extend([
        '',
        '------------------------------',
        'ダイソウ工業株式会社',
        '',
    ])
    return '\n'.join(body_lines)


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
        domain='PURCHASE_AUTO_ORDER',
        valid_from=today,
        valid_to=today + timedelta(days=7),
        description=message,
        operator_name='system',
    )
    notification.target_users.set(user_ids)


def _generate_order_send_delivery_note_pdf(items, supplier):
    """注文書自動送信専用の外作納品書PDFを生成する。

    自動納入リスト送信とは異なり、カバー期間の日別明細へ展開せず、
    納期日単位で保存した計画数(expected_qty)をそのまま納品書数量として使う。
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as pdf_canvas
    from shipping.services.shipping_pdf_generator import register_japanese_fonts
    from masters.models import Product
    from .tasks_auto_delivery_list import _dn_nohin, _dn_side

    register_japanese_fonts()
    font_name = 'MSGothic'

    page_w, page_h = landscape(A4)
    margin_left, margin_right = 10 * mm, 10 * mm
    margin_top, margin_bottom = 3 * mm, 3 * mm
    usable_w = page_w - margin_left - margin_right
    usable_h = page_h - margin_top - margin_bottom
    per_page = 3
    block_h = usable_h / per_page
    sep = 5 * mm
    item_h = block_h - sep

    gap = 4 * mm
    nohin_w = usable_w * 0.50
    side_w = (usable_w - nohin_w - gap * 2) / 2

    sorted_items = sorted(
        [item for item in items if int(item.get('expected_qty') or 0) > 0],
        key=lambda item: (item['delivery_date'], item['product_code']),
    )

    product_codes = list({item['product_code'] for item in sorted_items})
    container_map = {}
    for p in Product.objects.filter(product_code__in=product_codes).select_related('used_container'):
        container = getattr(p, 'used_container', None)
        if container:
            cap = getattr(p, 'capacity', None) or getattr(container, 'capacity', None)
            container_map[p.product_code] = (container.name or '', int(cap) if cap else 0)

    buf = BytesIO()
    canvas = pdf_canvas.Canvas(buf, pagesize=landscape(A4))
    total_pages = max(1, -(-len(sorted_items) // per_page))

    for page_index in range(total_pages):
        page_items = sorted_items[page_index * per_page:(page_index + 1) * per_page]
        for item_index, item in enumerate(page_items):
            yt = page_h - margin_top - item_index * block_h
            product_code = item['product_code']
            product_name = item['product_name']
            qty = int(item.get('expected_qty') or 0)
            item_date = item['delivery_date']
            date_ymd = item_date.strftime('%Y/%m/%d')
            date_mmdd = f'{item_date.month:02d}/{item_date.day:02d}'
            qr_data = f'{product_code},{item_date.isoformat()},{qty}'
            c_name, c_cap = container_map.get(product_code, ('', 0))

            _dn_nohin(
                canvas, margin_left, yt, nohin_w, item_h,
                product_code, product_name, qty, date_ymd, date_mmdd,
                supplier.supplier_code or '', supplier.supplier_name or '', qr_data, font_name,
                container_name=c_name, container_capacity=c_cap,
            )
            _dn_side(
                canvas, margin_left + nohin_w + gap, yt, side_w, item_h,
                product_code, product_name, qty, date_ymd, date_mmdd,
                supplier.supplier_code or '', supplier.supplier_name or '', qr_data, font_name, '受領書',
            )
            _dn_side(
                canvas, margin_left + nohin_w + gap + side_w + gap, yt, side_w, item_h,
                product_code, product_name, qty, date_ymd, date_mmdd,
                supplier.supplier_code or '', supplier.supplier_name or '', qr_data, font_name, '購入先控',
            )

            if item_index < len(page_items) - 1:
                sep_y = yt - block_h + sep / 2
                canvas.saveState()
                canvas.setDash(4, 3)
                canvas.setLineWidth(0.3)
                canvas.setStrokeColor(colors.HexColor('#888888'))
                canvas.line(margin_left, sep_y, page_w - margin_right, sep_y)
                canvas.restoreState()
        canvas.showPage()

    canvas.save()
    buf.seek(0)
    return buf
