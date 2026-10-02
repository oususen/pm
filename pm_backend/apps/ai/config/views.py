"""AI管理設定API。権限判定はフロントエンドUIで行う。"""
from rest_framework import mixins, parsers, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.config.models import AICrossScreenAccessPolicy, AIDataPolicy, AIKnowledgeDocument, AIKnowledgeSource, AIProviderConfig, AIToolPolicy
from ai.config.serializers import (
    AIAnalysisExecutionPolicySerializer,
    AIDataPolicySerializer,
    AIKnowledgeDocumentSerializer,
    AIKnowledgeSourceSerializer,
    AIProviderConfigSerializer,
    AIToolPolicySerializer,
    AICrossScreenAccessPolicySerializer,
)
from ai.config.catalog import SCREEN_CATALOG
from ai.config.service import get_analysis_execution_policy
from ai.services.sql_queries import PERSONAL_SQL_COLUMNS, SCREEN_SQL_TABLES, _schema_for_table


class AIProviderConfigViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = AIProviderConfig.objects.all()
    serializer_class = AIProviderConfigSerializer
    pagination_class = None

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    update = partial_update


class AIToolPolicyViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = AIToolPolicy.objects.all()
    serializer_class = AIToolPolicySerializer
    pagination_class = None

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    update = partial_update


class AIDataPolicyView(APIView):
    def get(self, request):
        return Response(AIDataPolicySerializer(AIDataPolicy.objects.get()).data)

    def put(self, request):
        policy = AIDataPolicy.objects.get()
        serializer = AIDataPolicySerializer(policy, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    patch = put


class AIAnalysisExecutionPolicyView(APIView):
    """分析実行設定の取得・一括保存。編集権限は設定画面で判定する。"""
    def get(self, request):
        return Response(AIAnalysisExecutionPolicySerializer(get_analysis_execution_policy()).data)

    def put(self, request):
        serializer = AIAnalysisExecutionPolicySerializer(get_analysis_execution_policy(), data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AISQLDictionaryView(APIView):
    """画面別に許可した読み取りSQL辞書を、AI設定画面へ返す。"""
    def get(self, request):
        return Response([
            {
                'screen_id': screen_id,
                'screen_label': label,
                'tables': [
                    {
                        'table': table,
                        'columns': list(_schema_for_table(table)),
                        'personal_columns': list(PERSONAL_SQL_COLUMNS.get(table, ())),
                    }
                    for table in sorted(SCREEN_SQL_TABLES.get(screen_id, ()))
                ],
            }
            for screen_id, label in SCREEN_CATALOG.items()
        ])


class AIKnowledgeSourceViewSet(viewsets.ModelViewSet):
    queryset = AIKnowledgeSource.objects.all()
    serializer_class = AIKnowledgeSourceSerializer
    pagination_class = None


class AIKnowledgeDocumentViewSet(viewsets.ModelViewSet):
    """ナレッジ原本の登録。権限制御はAI設定画面のUIで行う。"""
    queryset = AIKnowledgeDocument.objects.all()
    serializer_class = AIKnowledgeDocumentSerializer
    pagination_class = None
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]

    def perform_destroy(self, instance):
        """利用者が資料を削除した場合は、ナレッジ原本もmediaから削除する。"""
        instance.file.delete(save=False)
        instance.delete()


class AICrossScreenAccessPolicyViewSet(viewsets.ModelViewSet):
    """管理者が定義する横断参照の候補。利用者承認だけでは新規作成できない。"""
    queryset = AICrossScreenAccessPolicy.objects.all()
    serializer_class = AICrossScreenAccessPolicySerializer
    pagination_class = None
