"""社内AIの運用設定モデル。認証情報や業務明細は保存しない。"""
from django.db import models

from ai.config.catalog import KNOWLEDGE_CATEGORY_CHOICES, PROVIDER_CATALOG, SCREEN_CATALOG, TOOL_CATALOG


class AIProviderConfig(models.Model):
    """利用可能なAIプロバイダと既定モデルの設定。APIキーは環境変数で管理する。"""
    provider = models.CharField(max_length=30, unique=True, choices=[(key, value['label']) for key, value in PROVIDER_CATALOG.items()])
    default_model = models.CharField(max_length=100)
    is_enabled = models.BooleanField(default=True, verbose_name='有効')
    display_order = models.PositiveIntegerField(default=0, verbose_name='表示順')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_provider_config'
        ordering = ['display_order', 'provider']
        verbose_name = 'AIプロバイダ設定'
        verbose_name_plural = 'AIプロバイダ設定'


class AIToolPolicy(models.Model):
    """画面起点ごとに、AIへ公開する固定ツールを制御する。"""
    screen_id = models.CharField(max_length=40, choices=list(SCREEN_CATALOG.items()), verbose_name='画面領域')
    tool_code = models.CharField(max_length=80, choices=[(key, value['label']) for key, value in TOOL_CATALOG.items()], verbose_name='ツール')
    is_enabled = models.BooleanField(default=True, verbose_name='有効')
    allow_external_transfer = models.BooleanField(default=True, verbose_name='外部AIへの集計結果送信を許可')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_tool_policy'
        constraints = [models.UniqueConstraint(fields=['screen_id', 'tool_code'], name='ai_tool_policy_screen_tool_unique')]
        ordering = ['screen_id', 'tool_code']
        verbose_name = 'AIツール利用設定'
        verbose_name_plural = 'AIツール利用設定'


class AIDataPolicy(models.Model):
    """外部AIへ渡すデータ範囲の全体方針。常に1行だけ保持する。"""
    allow_aggregated_external_transfer = models.BooleanField(default=True, verbose_name='集計結果の外部送信を許可')
    allow_authorized_personal_data = models.BooleanField(default=True, verbose_name='権限者への個人別集計を許可')
    max_external_result_rows = models.PositiveIntegerField(default=30, verbose_name='外部送信する最大集計行数')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_data_policy'
        verbose_name = 'AIデータ送信設定'
        verbose_name_plural = 'AIデータ送信設定'


class AIKnowledgeSource(models.Model):
    """AI運用時に参照する、リポジトリ内ナレッジの登録情報。"""
    category = models.CharField(max_length=30, choices=KNOWLEDGE_CATEGORY_CHOICES, verbose_name='区分')
    name = models.CharField(max_length=100, verbose_name='名称')
    relative_path = models.CharField(max_length=300, unique=True, verbose_name='相対パス')
    description = models.CharField(max_length=300, blank=True, default='', verbose_name='説明')
    is_enabled = models.BooleanField(default=True, verbose_name='有効')
    display_order = models.PositiveIntegerField(default=0, verbose_name='表示順')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_knowledge_source'
        ordering = ['category', 'display_order', 'name']
        verbose_name = 'AIナレッジ登録'
        verbose_name_plural = 'AIナレッジ登録'
