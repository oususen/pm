"""未処理例外(500エラー)発生時、管理者へアプリ内通知(Notification)を作成する"""
import logging
import sys
import traceback
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.signals import got_request_exception

logger = logging.getLogger('production')

DUPLICATE_SUPPRESS_MINUTES = 30
TRACEBACK_MAX_LENGTH = 3000


def _resolve_admin_users():
    User = get_user_model()
    return User.objects.filter(
        is_active=True,
        smtp_config__is_active=True,
        smtp_config__is_admin=True,
    )


def _notify_admins_of_request_exception(sender, request=None, **kwargs):
    from .models import Notification

    try:
        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_type is None:
            return

        path = getattr(request, 'path', '不明')
        method = getattr(request, 'method', '')
        title = f'[システムエラー] {exc_type.__name__}: {method} {path}'[:200]

        recent_cutoff = datetime.now() - timedelta(minutes=DUPLICATE_SUPPRESS_MINUTES)
        already_notified = Notification.objects.filter(
            category='システム',
            domain='システム',
            title=title,
            created_at__gte=recent_cutoff,
        ).exists()
        if already_notified:
            return

        admin_users = list(_resolve_admin_users())
        if not admin_users:
            return

        tb_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))[-TRACEBACK_MAX_LENGTH:]
        description = (
            f'発生日時: {datetime.now():%Y-%m-%d %H:%M:%S}\n'
            f'メソッド: {method}\n'
            f'パス: {path}\n\n'
            f'{tb_text}'
        )

        notification = Notification.objects.create(
            title=title,
            category='システム',
            domain='システム',
            description=description,
            valid_from=None,
            valid_to=datetime.now().date() + timedelta(days=7),
            operator_name='admin',
        )
        notification.target_users.set(admin_users)
    except Exception:
        logger.error('未処理例外の管理者通知作成に失敗', exc_info=True)


def register():
    got_request_exception.connect(_notify_admins_of_request_exception)
