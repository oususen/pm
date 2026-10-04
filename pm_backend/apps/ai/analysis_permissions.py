"""BOSS承認の分析API入口制御。分析タブと同じ明示資源・操作を使う。"""
from rest_framework.permissions import BasePermission

from ai.services.chat_service import _has_resource_permission


class CanUseAIAnalysis(BasePermission):
    message = 'AI分析の操作権限がありません。'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        level = 'view' if request.method in ('GET', 'HEAD', 'OPTIONS') else 'edit'
        try:
            return _has_resource_permission(request.user, 'ai.analysis', level)
        except Exception:
            # 判定できない場合も拒否。例外文や内部情報は応答へ出さない。
            return False
