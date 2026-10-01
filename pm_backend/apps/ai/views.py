"""社内AIのHTTP API。"""
import logging
import os
import tempfile
from datetime import datetime, timedelta

from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.config.service import get_data_policy
from ai.models import AIConversation
from ai.serializers import AIConversationListSerializer, AIConversationSerializer
from ai.services.chat_service import AIChatAPIView, _has_resource_permission
from notifications.transcription import AudioTooLongError, transcribe_audio_file

logger = logging.getLogger('production')


def purge_expired_conversations():
    """AI設定の保存期間を過ぎた会話を、全利用者分まとめて削除する。0日は無期限。"""
    retention_days = get_data_policy().conversation_retention_days
    if not retention_days:
        return 0
    deleted, _ = AIConversation.objects.filter(
        updated_at__lt=datetime.now() - timedelta(days=retention_days),
    ).delete()
    return deleted


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

    def list(self, request, *args, **kwargs):
        purge_expired_conversations()
        return super().list(request, *args, **kwargs)

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
        purge_expired_conversations()

    def perform_update(self, serializer):
        self._check_ai_chat_permission()
        serializer.save()
        purge_expired_conversations()


class AITranscribeView(APIView):
    """チャットの音声入力。短い音声をPC内のWhisperで文字にして返す。音声・文字は保存しない。"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]
    MAX_BYTES = 10 * 1024 * 1024
    MAX_SECONDS = 60
    ALLOWED_SUFFIXES = {'.webm', '.mp4', '.m4a', '.ogg', '.wav', '.mp3'}

    def post(self, request):
        if not _has_resource_permission(request.user, 'ai.chat'):
            return Response({'detail': '社内AIチャットを利用する権限がありません。'}, status=403)
        audio = request.FILES.get('audio')
        if not audio:
            return Response({'detail': '音声ファイルを指定してください。'}, status=400)
        if audio.size > self.MAX_BYTES:
            return Response({'detail': '音声ファイルは10MB以内にしてください。'}, status=400)
        suffix = os.path.splitext(audio.name or '')[1].lower()
        if suffix not in self.ALLOWED_SUFFIXES:
            suffix = '.webm'
        # 文字にしたらすぐ削除する一時ファイル。音声は保存しない。
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            for chunk in audio.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name
        try:
            text = transcribe_audio_file(temp_path, max_seconds=self.MAX_SECONDS)
        except AudioTooLongError as exc:
            return Response({'detail': str(exc)}, status=400)
        except Exception:
            logger.exception('チャット音声入力の文字起こしに失敗しました')
            return Response({'detail': '音声を文字にできませんでした。もう一度お試しください。'}, status=503)
        finally:
            os.remove(temp_path)
        return Response({'text': text})

