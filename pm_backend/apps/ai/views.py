"""社内AIのHTTP API。"""
from ai.services.chat_service import AIChatAPIView


class AIChatView(AIChatAPIView):
    """正式な社内AIチャットAPI。"""
