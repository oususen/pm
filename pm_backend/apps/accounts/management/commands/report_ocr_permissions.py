import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import (
    DepartmentPermission,
    DepartmentPositionPermission,
    PositionPermission,
    UserPermission,
)
from accounts.views import _build_effective_permissions


def describe_user(user):
    """ログイン時と同じ実効権限でOCR移行対象を判定する（更新しない）。"""
    permissions = {item['resource']: item for item in _build_effective_permissions(user)}

    def allowed(resource):
        item = permissions.get(resource, {})
        return bool(item.get('can_view') or item.get('can_edit'))

    old_ai = allowed('ai')
    ocr = bool(user.is_superuser or allowed('ocr'))
    if not (old_ai or ocr):
        return None
    return {
        'user_id': user.pk,
        'username': user.username,
        'is_active': user.is_active,
        'is_superuser': user.is_superuser,
        'legacy_ai_allowed': old_ai,
        'ocr_allowed': ocr,
        'needs_review': bool(user.is_active and old_ai and not ocr),
    }


class Command(BaseCommand):
    help = '旧ai権限の設定先とOCR移行確認対象をJSONで一覧化します（DB更新なし）'

    def handle(self, *args, **options):
        # 不許可の行も含め、旧キーの残存状況を4種類すべて確認する。
        legacy_settings = {
            'user': list(UserPermission.objects.filter(resource='ai').order_by('pk').values(
                'id', 'user_id', 'can_view', 'can_edit')),
            'department': list(DepartmentPermission.objects.filter(resource='ai').order_by('pk').values(
                'id', 'department_id', 'department__name', 'can_view', 'can_edit')),
            'position': list(PositionPermission.objects.filter(resource='ai').order_by('pk').values(
                'id', 'position_name', 'can_view', 'can_edit')),
            'department_position': list(DepartmentPositionPermission.objects.filter(resource='ai').order_by('pk').values(
                'id', 'department_id', 'department__name', 'position_name', 'can_view', 'can_edit')),
        }
        users = []
        for user in get_user_model().objects.select_related('profile').order_by('pk').iterator():
            # 1件ずつ取得するため、利用者ごとの詳細キャッシュは保持しない。
            row = describe_user(user)
            if row is not None:
                users.append(row)
        self.stdout.write(json.dumps({
            'read_only': True,
            'legacy_settings': legacy_settings,
            'users': users,
            'needs_review_count': sum(row['needs_review'] for row in users),
            'note': '旧ai権限はOCRの実利用履歴ではありません。管理者が継続対象を確認してください。権限の自動付与・変更・削除は行っていません。',
        }, ensure_ascii=False, indent=2))
