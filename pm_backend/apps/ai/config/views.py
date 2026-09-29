"""AI管理設定API。権限判定はフロントエンドUIで行う。"""
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.config.models import AIDataPolicy, AIKnowledgeSource, AIProviderConfig, AIToolPolicy
from ai.config.serializers import (
    AIDataPolicySerializer,
    AIKnowledgeSourceSerializer,
    AIProviderConfigSerializer,
    AIToolPolicySerializer,
)
from ai.config.catalog import SCREEN_CATALOG
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
