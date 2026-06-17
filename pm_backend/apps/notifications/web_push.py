import json
import logging

from django.conf import settings


logger = logging.getLogger(__name__)


def get_web_push_config():
    public_key = (getattr(settings, 'WEB_PUSH_VAPID_PUBLIC_KEY', '') or '').strip()
    private_key = (getattr(settings, 'WEB_PUSH_VAPID_PRIVATE_KEY', '') or '').strip()
    subject = (getattr(settings, 'WEB_PUSH_VAPID_SUBJECT', '') or '').strip()
    enabled = bool(public_key and private_key and subject)
    return {
        'enabled': enabled,
        'public_key': public_key,
        'private_key': private_key,
        'subject': subject,
    }


def send_web_push(subscription, payload):
    config = get_web_push_config()
    if not config['enabled']:
        return False

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.warning('pywebpush が未インストールのため Push 通知を送信できません。')
        return False

    try:
        webpush(
            subscription_info={
                'endpoint': subscription.endpoint,
                'keys': {
                    'p256dh': subscription.p256dh_key,
                    'auth': subscription.auth_key,
                },
            },
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=config['private_key'],
            vapid_claims={'sub': config['subject']},
        )
        logger.info('Push 通知送信成功: user_id=%s, tag=%s', subscription.user_id, payload.get('tag', ''))
        return True
    except WebPushException as error:
        status_code = getattr(getattr(error, 'response', None), 'status_code', None)
        logger.warning('Push 通知送信に失敗しました: %s', error)
        if status_code in {404, 410}:
            subscription.delete()
        return False
    except Exception as error:
        logger.warning('Push 通知送信中に予期しないエラーが発生しました: %s', error)
        return False
