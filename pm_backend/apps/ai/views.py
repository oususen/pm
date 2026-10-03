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
from ai.services.analysis_plan_store import AnalysisError, AnalysisPlanStore, public_plan
from ai.services import analysis_codegen_service as codegen
from ai.services.analysis_planning_service import approve_plan, create_plan, external_send_preview, planning_options, preview_plan
from notifications.transcription import AudioTooLongError, transcribe_audio_file

logger = logging.getLogger('production')


class AIAnalysisOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(planning_options())


class AIAnalysisPlansView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(_codegen_response(create_plan(request.user.pk, request.data)), status=201)


class AIAnalysisExternalPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(external_send_preview(request.user.pk, request.data))


class AIAnalysisPlanView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, plan_id):
        return Response(_codegen_response(AnalysisPlanStore().get(str(plan_id), request.user.pk)))


class AIAnalysisApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, plan_id):
        if not isinstance(request.data, dict) or set(request.data) != {'revision', 'stage'}:
            raise AnalysisError('承認する版と段階のみを指定してください。')
        plan = approve_plan(AnalysisPlanStore(), str(plan_id), request.user.pk, request.data['revision'], request.data['stage'])
        return Response(_codegen_response(plan))


class AIAnalysisPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, plan_id):
        if not isinstance(request.data, dict) or set(request.data) != {'revision'}:
            raise AnalysisError('対象件数を確認する版のみを指定してください。')
        plan = preview_plan(AnalysisPlanStore(), str(plan_id), request.user.pk, request.data['revision'])
        return Response(_codegen_response(plan))


def _codegen_response(plan):
    return {**public_plan(plan), 'codegen_state': codegen.describe_codegen(plan)}


def _only(data, keys, message):
    if not isinstance(data, dict) or set(data) != set(keys):
        raise AnalysisError(message)
    return data


class AIAnalysisCodegenPreviewView(APIView):
    """コード生成で送る内容の確認(送信しない)。外部AIの場合は、確認コードを返す。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, plan_id):
        _only(request.data, {'revision'}, '対象の版のみを指定してください。')
        return Response(codegen.preview(request.user.pk, str(plan_id), request.data['revision']))


class AIAnalysisCodegenView(APIView):
    """SQL・Pythonの生成。外部AIは、確認コードが必要。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, plan_id):
        if not isinstance(request.data, dict) or not {'revision'} <= set(request.data) <= {'revision', 'confirmation'}:
            raise AnalysisError('対象の版と、(外部AIの場合は)確認コードのみを指定してください。')
        plan = codegen.generate(request.user.pk, str(plan_id), request.data['revision'], request.data.get('confirmation'))
        return Response(_codegen_response(plan))


class AIAnalysisCodegenTrialView(APIView):
    """試行実行(実DBなし。空のテーブルでSQLだけを確認する)。分析の実行ではなく、履歴には残さない。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, plan_id):
        _only(request.data, {'revision'}, '対象の版のみを指定してください。')
        plan, trial = codegen.run_trial(request.user.pk, str(plan_id), request.data['revision'])
        return Response({**_codegen_response(plan), 'trial': trial})


class AIAnalysisCodegenApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, plan_id):
        _only(request.data, {'revision', 'executed_code_sha256'}, '対象の版と、確認したコードのハッシュのみを指定してください。')
        plan = codegen.approve_code(request.user.pk, str(plan_id), request.data['revision'], request.data['executed_code_sha256'])
        return Response(_codegen_response(plan))


class AIAnalysisCodegenReleaseView(APIView):
    """状態不明の「生成中」を、明示の操作で解除する(生成回数は戻さず、有効期限は延長しない)。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, plan_id):
        _only(request.data, {'revision'}, '対象の版のみを指定してください。')
        return Response(_codegen_response(codegen.release_inflight(request.user.pk, str(plan_id), request.data['revision'])))


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
