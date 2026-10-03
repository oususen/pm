from django.urls import include, path
from rest_framework.routers import DefaultRouter

from ai.views import AIChatView, AIConversationViewSet, AITranscribeView
from ai.views import AIAnalysisApproveView, AIAnalysisExternalPreviewView, AIAnalysisOptionsView, AIAnalysisPlansView, AIAnalysisPlanView, AIAnalysisPreviewView
from ai.config.views import AIAnalysisExecutionPolicyView, AICrossScreenAccessPolicyViewSet, AIDataPolicyView, AIKnowledgeDocumentViewSet, AIKnowledgeSourceViewSet, AIProviderConfigViewSet, AISQLDictionaryView, AIToolPolicyViewSet
from ai.views_ai_config import AISearchConfigViewSet, AISearchConfigModelsView

router = DefaultRouter()
router.register(r'ai-search-configs', AISearchConfigViewSet, basename='aisearchconfig')
router.register(r'ai/conversations', AIConversationViewSet, basename='ai-conversation')
router.register(r'ai/settings/providers', AIProviderConfigViewSet, basename='ai-provider-config')
router.register(r'ai/settings/tools', AIToolPolicyViewSet, basename='ai-tool-policy')
router.register(r'ai/settings/knowledge-sources', AIKnowledgeSourceViewSet, basename='ai-knowledge-source')
router.register(r'ai/settings/knowledge-documents', AIKnowledgeDocumentViewSet, basename='ai-knowledge-document')
router.register(r'ai/settings/cross-screen-access', AICrossScreenAccessPolicyViewSet, basename='ai-cross-screen-access')

urlpatterns = [
    path('', include(router.urls)),
    path('ai/chat/', AIChatView.as_view(), name='ai-chat'),
    path('ai/transcribe/', AITranscribeView.as_view(), name='ai-transcribe'),
    path('ai/analysis/options/', AIAnalysisOptionsView.as_view(), name='ai-analysis-options'),
    path('ai/analysis/external-preview/', AIAnalysisExternalPreviewView.as_view(), name='ai-analysis-external-preview'),
    path('ai/analysis/plans/', AIAnalysisPlansView.as_view(), name='ai-analysis-plans'),
    path('ai/analysis/plans/<uuid:plan_id>/', AIAnalysisPlanView.as_view(), name='ai-analysis-plan'),
    path('ai/analysis/plans/<uuid:plan_id>/approve/', AIAnalysisApproveView.as_view(), name='ai-analysis-approve'),
    path('ai/analysis/plans/<uuid:plan_id>/data-preview/', AIAnalysisPreviewView.as_view(), name='ai-analysis-preview'),
    path('ai/settings/data-policy/', AIDataPolicyView.as_view(), name='ai-data-policy'),
    path('ai/settings/analysis-execution-policy/', AIAnalysisExecutionPolicyView.as_view(), name='ai-analysis-execution-policy'),
    path('ai/settings/sql-dictionary/', AISQLDictionaryView.as_view(), name='ai-sql-dictionary'),
    path('ai-search-config-models/', AISearchConfigModelsView.as_view(), name='ai-search-config-models'),
]
