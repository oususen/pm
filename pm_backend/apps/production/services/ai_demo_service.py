"""旧生産AI APIの互換サービス。社内AI本体は ai.services に置く。"""
from ai.services.chat_service import ProductionAIDemoView

__all__ = ['ProductionAIDemoView']
