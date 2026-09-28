"""社内AIのHTTP API。"""
from ai.services.chat_service import ProductionAIDemoView


class AIChatView(ProductionAIDemoView):
    """正式な社内AIチャットAPI。既存チャットの互換動作を継承する。"""
