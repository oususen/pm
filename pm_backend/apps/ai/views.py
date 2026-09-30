"""社内AIのHTTP API。"""
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from ai.models import AIConversation
from ai.serializers import AIConversationListSerializer, AIConversationSerializer
from ai.services.chat_service import AIChatAPIView, _has_resource_permission


class AIChatView(AIChatAPIView):
    """正式な社内AIチャットAPI。"""


class AIConversationPagination(PageNumberPagination):
    page_size = 30


class AIConversationViewSet(viewsets.ModelViewSet):
    """本人の会話履歴だけを一覧・再開・削除できる。他の利用者の会話は一切見えない。"""
    permission_classes = [IsAuthenticated]
    pagination_class = AIConversationPagination

    def get_queryset(self):
        return AIConversation.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return AIConversationListSerializer
        return AIConversationSerializer

    def _check_ai_chat_permission(self):
        if not _has_resource_permission(self.request.user, 'ai.chat'):
            raise PermissionDenied('社内AIチャットを利用する権限がありません。')

    def perform_create(self, serializer):
        self._check_ai_chat_permission()
        messages = serializer.validated_data.get('messages') or []
        title = str(serializer.validated_data.get('title') or '').strip()
        if not title:
            first_user_message = next(
                (str(item.get('content', '')) for item in messages if item.get('role') == 'user'), '',
            )
            title = first_user_message.strip()[:40] or '新しい会話'
        serializer.save(user=self.request.user, title=title)

    def perform_update(self, serializer):
        self._check_ai_chat_permission()
        serializer.save()
