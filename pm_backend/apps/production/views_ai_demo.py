"""社内AIチャットAPIの入口。業務ロジックはサービス層に置く。"""
from production.services.ai_demo_service import ProductionAIDemoView

__all__ = ['ProductionAIDemoView']
