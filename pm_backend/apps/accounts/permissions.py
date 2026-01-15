from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import DepartmentPositionPermission, UserPermission


def build_effective_permissions(user):
    resources = [choice[0] for choice in UserPermission.RESOURCE_CHOICES]
    permission_map = {}

    profile = getattr(user, 'profile', None)
    department_id = profile.department_id if profile else None
    position_name = profile.position.strip() if profile and profile.position else ''

    if department_id and position_name:
        combined_permissions = DepartmentPositionPermission.objects.filter(
            department_id=department_id,
            position_name=position_name,
        )
        for perm in combined_permissions:
            permission_map[perm.resource] = {
                'resource': perm.resource,
                'can_view': perm.can_view,
                'can_edit': perm.can_edit,
            }

    user_permissions = []
    if hasattr(user, 'permissions'):
        user_permissions = list(user.permissions.all())
    if user_permissions:
        for perm in user_permissions:
            permission_map[perm.resource] = {
                'resource': perm.resource,
                'can_view': perm.can_view,
                'can_edit': perm.can_edit,
            }

    if user.is_superuser:
        return [
            {'resource': resource, 'can_view': True, 'can_edit': True}
            for resource in resources
        ]

    if not permission_map:
        return []

    result = []
    for resource in resources:
        perm = permission_map.get(resource)
        if perm:
            result.append(perm)
        else:
            result.append({'resource': resource, 'can_view': False, 'can_edit': False})
    return result


def _effective_permissions_map(request):
    if hasattr(request, '_effective_permissions_map'):
        return request._effective_permissions_map
    permissions = build_effective_permissions(request.user)
    permission_map = {perm['resource']: perm for perm in permissions}
    request._effective_permissions_map = permission_map
    return permission_map


class HasResourcePermission(BasePermission):
    message = 'You do not have permission to access this resource.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        resource = getattr(view, 'permission_resource', None)
        if not resource:
            return False

        permission_map = _effective_permissions_map(request)
        perm = permission_map.get(resource)
        if not perm:
            return False

        if request.method in SAFE_METHODS:
            return bool(perm.get('can_view') or perm.get('can_edit'))
        return bool(perm.get('can_edit'))


class HasResourcePermissionOrReadOnly(BasePermission):
    """読み取りは認証のみ、書き込みはリソース権限が必要"""
    message = 'You do not have permission to modify this resource.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # 読み取りは認証済みなら許可
        if request.method in SAFE_METHODS:
            return True

        # 書き込みはリソース権限をチェック
        resource = getattr(view, 'permission_resource', None)
        if not resource:
            return False

        permission_map = _effective_permissions_map(request)
        perm = permission_map.get(resource)
        if not perm:
            return False

        return bool(perm.get('can_edit'))
