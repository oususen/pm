from django.urls import include, path
from rest_framework.routers import DefaultRouter

from ai.views import AIChatView
from ai.views_ai_config import AISearchConfigViewSet, AISearchConfigModelsView

router = DefaultRouter()
router.register(r'ai-search-configs', AISearchConfigViewSet, basename='aisearchconfig')

urlpatterns = [
    path('', include(router.urls)),
    path('ai/chat/', AIChatView.as_view(), name='ai-chat'),
    path('ai-search-config-models/', AISearchConfigModelsView.as_view(), name='ai-search-config-models'),
]
