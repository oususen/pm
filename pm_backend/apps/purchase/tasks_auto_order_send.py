import logging
import time
from datetime import date, datetime, timedelta

logger = logging.getLogger('purchase')


def run_auto_order_send(config_id, ignore_holiday=False):
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
    config.last_run_at = datetime.now()
    config.last_run_status = 'RUNNING'
    config.last_run_message = '実行中...'
    config.save(update_fields=['last_run_at', 'last_run_status', 'last_run_message'])

    try:
        today = date.today()
        daiso_cal = Calendar.objects.filter(calendar_code='daiso').first()
        if not daiso_cal:
            _finish(config, start_time, 'FAILED', 'ダイソウカレンダーが未設定のため、注文書自動送信を実行できません')
            _notify_users(config.notify_on_failure, '注文書自動送信失敗: ダイソウカレンダーが未設定です')
            return

        calc = WorkingDayCalculator(daiso_cal)
        if not ignore_holiday and not calc.is_working_day(today):
            message = f'本日は休日のため、{supplier.supplier_name} 向け注文書自動送信は実行しません'
            _finish(config, start_time, 'SKIPPED', message)
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
        if items:
            excel_data = generate_order_excel(items, supplier)
            all_attachments.append({
                'data': excel_data,
                'filename': f'注文書_{supplier.supplier_code}_{today}.xlsx',
            })
        if progress_excel:
            all_attachments.append({
                'data': progress_excel,
                'filename': f'進度表_{supplier.supplier_code}_{today}.xlsx',
            })
        if progress_pdf:
            all_attachments.append({
                'data': progress_pdf,
                'filename': f'進度表_{supplier.supplier_code}_{today}.pdf',
            })

        if not all_attachments:
            _finish(config, start_time, 'SUCCESS', result.get('message') or '対象データはありません')
            return

        if not config.send_order_excel:
            _finish(config, start_time, 'SKIPPED', '注文書Excel送信がOFFです')
            return

        to_email = (supplier.order_email or '').strip()
        if not to_email:
            _finish(config, start_time, 'FAILED', f'仕入先 {supplier.supplier_code} のメールアドレスが未設定です')
            _notify_users(config.notify_on_failure, f'注文書自動送信失敗: {supplier.supplier_name} のメールアドレスが未設定です')
            return

        cc_list = [email.strip() for email in (config.cc_emails or '').splitlines() if email.strip()]
        reply_to = (config.reply_to_email or '').strip()

        delivery_dates = sorted({item['delivery_date'] for item in items}) if items else []
        if delivery_dates:
            subject = f'【注文書】{supplier.supplier_code} {delivery_dates[0]}'
        else:
            subject = f'【進度表】{supplier.supplier_code} {today}'
        body = _build_mail_body(config, supplier, items, delivery_dates)

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

        attach_summary = []
        if items:
            attach_summary.append(f'注文書{len(items)}件')
        if progress_excel:
            attach_summary.append('進度表Excel')
        if progress_pdf:
            attach_summary.append('進度表PDF')

        if send_result.get('success'):
            _finish(
                config,
                start_time,
                'SUCCESS',
                f'送信完了 ({", ".join(attach_summary)}) → {to_email}',
            )
        else:
            message = f'メール送信失敗: {send_result.get("message", "")}'
            _finish(config, start_time, 'FAILED', message)
            _notify_users(config.notify_on_failure, f'注文書自動送信失敗: {supplier.supplier_name}\n{message}')
    except Exception as exc:
        logger.exception('注文書自動送信エラー: config_id=%s', config_id)
        _finish(config, start_time, 'FAILED', f'エラー: {str(exc)[:500]}')
        _notify_users(config.notify_on_failure, f'注文書自動送信エラー: {supplier.supplier_name}\n{str(exc)[:300]}')


def _build_mail_body(config, supplier, items, delivery_dates):
    if config.email_body_custom.strip():
        return f'{supplier.supplier_name} 御中\n\n{config.email_body_custom.strip()}\n'

    body_lines = [
        f'{supplier.supplier_name} 御中',
        '',
        'お世話になっております。',
    ]

    if items and delivery_dates:
        first_date = delivery_dates[0].isoformat()
        body_lines.extend([
            '注文書を送付いたします。',
            '',
            f'対象納入回: {len(delivery_dates)}回',
            f'対象納入日: {first_date}',
            f'対象品目: {len(items)}件',
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
