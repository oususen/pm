from rest_framework import permissions


class HasResourcePermissionOrReadOnly(permissions.BasePermission):
    """
    フロントエンドで権限管理を行うため、バックエンドでは常に許可する。
    権限チェックはフロントエンドUIレベルで行う。
    """
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return True