from rest_framework import permissions


def has_interruption_reason_edit_permission(user):
    """中断理由マスタの編集権限（can_edit）を持つか判定する。"""
    if getattr(user, 'is_superuser', False):
        return True
    from accounts.views import _build_effective_permissions
    perm = next(
        (p for p in _build_effective_permissions(user) if p['resource'] == 'masters.interruption_reason'),
        None,
    )
    return bool(perm and perm.get('can_edit'))


class InterruptionReasonPermission(permissions.BasePermission):
    """中断理由マスタ: 読み取りは認証済みなら誰でも許可、更新系はcan_editが必要。"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return has_interruption_reason_edit_permission(request.user)
