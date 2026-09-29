from django.urls import include, path
from rest_framework.routers import DefaultRouter

from ai.views import AIChatView
from ai.config.views import AIDataPolicyView, AIKnowledgeDocumentViewSet, AIKnowledgeSourceViewSet, AIProviderConfigViewSet, AISQLDictionaryView, AIToolPolicyViewSet
from ai.views_ai_config import AISearchConfigViewSet, AISearchConfigModelsView

router = DefaultRouter()
router.register(r'ai-search-configs', AISearchConfigViewSet, basename='aisearchconfig')
router.register(r'ai/settings/providers', AIProviderConfigViewSet, basename='ai-provider-config')
router.register(r'ai/settings/tools', AIToolPolicyViewSet, basename='ai-tool-policy')
router.register(r'ai/settings/knowledge-sources', AIKnowledgeSourceViewSet, basename='ai-knowledge-source')
router.register(r'ai/settings/knowledge-documents', AIKnowledgeDocumentViewSet, basename='ai-knowledge-document')

urlpatterns = [
    path('', include(router.urls)),
    path('ai/chat/', AIChatView.as_view(), name='ai-chat'),
    path('ai/settings/data-policy/', AIDataPolicyView.as_view(), name='ai-data-policy'),
    path('ai/settings/sql-dictionary/', AISQLDictionaryView.as_view(), name='ai-sql-dictionary'),
    path('ai-search-config-models/', AISearchConfigModelsView.as_view(), name='ai-search-config-models'),
]
