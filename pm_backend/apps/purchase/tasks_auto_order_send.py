import logging
import time
from datetime import date, datetime, timedelta

logger = logging.getLogger('purchase')


def run_auto_order_send(config_id, ignore_holiday=False):
    from masters.models import Calendar
    from orders.utils.calendar_utils import WorkingDayCalculator
    from shipping.services.email_service import EmailService

    from .models import PurchaseAutoOrderSendConfig
    from .services_auto_order_send import generate_order_excel, simulate_and_save_order_plans

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

        result = simulate_and_save_order_plans(config, base_date=today)
        if result['status'] != 'SUCCESS':
            _finish(config, start_time, result['status'], result['message'])
            notify_target = config.notify_on_non_delivery if result['status'] == 'SKIPPED' else config.notify_on_failure
            _notify_users(notify_target, f'注文書自動送信: {result["message"]}')
            return

        items = result['items']
        if not items:
            _finish(config, start_time, 'SUCCESS', result['message'] or '対象データはありません')
            return

        if not config.send_order_excel:
            _finish(config, start_time, 'SKIPPED', '注文書Excel送信がOFFです')
            return

        excel_data = generate_order_excel(items, supplier)
        to_email = (supplier.order_email or '').strip()
        if not to_email:
            _finish(config, start_time, 'FAILED', f'仕入先 {supplier.supplier_code} のメールアドレスが未設定です')
            _notify_users(config.notify_on_failure, f'注文書自動送信失敗: {supplier.supplier_name} のメールアドレスが未設定です')
            return

        cc_list = [email.strip() for email in (config.cc_emails or '').splitlines() if email.strip()]
        reply_to = (config.reply_to_email or '').strip()

        delivery_dates = sorted({item['delivery_date'] for item in items})
        subject = f'【注文書】{supplier.supplier_code} {delivery_dates[0]}'
        body = _build_mail_body(config, supplier, items, delivery_dates)

        email_service = EmailService()
        result = email_service.send_email_with_attachment(
            to_emails=[to_email],
            subject=subject,
            body=body,
            attachment_data=excel_data,
            attachment_filename=f'注文書_{supplier.supplier_code}_{today}.xlsx',
            cc_emails=cc_list if cc_list else None,
            reply_to=reply_to or None,
        )

        if result.get('success'):
            _finish(
                config,
                start_time,
                'SUCCESS',
                f'注文書送信完了 ({len(items)}件 / {len(delivery_dates)}納入回) → {to_email}',
            )
        else:
            message = f'メール送信失敗: {result.get("message", "")}'
            _finish(config, start_time, 'FAILED', message)
            _notify_users(config.notify_on_failure, f'注文書自動送信失敗: {supplier.supplier_name}\n{message}')
    except Exception as exc:
        logger.exception('注文書自動送信エラー: config_id=%s', config_id)
        _finish(config, start_time, 'FAILED', f'エラー: {str(exc)[:500]}')
        _notify_users(config.notify_on_failure, f'注文書自動送信エラー: {supplier.supplier_name}\n{str(exc)[:300]}')


def _build_mail_body(config, supplier, items, delivery_dates):
    if config.email_body_custom.strip():
        return f'{supplier.supplier_name} 御中\n\n{config.email_body_custom.strip()}\n'

    first_date = delivery_dates[0].isoformat()
    body_lines = [
        f'{supplier.supplier_name} 御中',
        '',
        'お世話になっております。',
        '注文書を送付いたします。',
        '',
        f'対象納入回: {len(delivery_dates)}回',
        f'対象納入日: {first_date}',
        f'対象品目: {len(items)}件',
        '',
        '添付Excelをご確認ください。',
    ]
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
