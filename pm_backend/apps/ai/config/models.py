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
    allow_external_image_transfer = models.BooleanField(default=True, verbose_name='添付画像の外部AI送信を許可')
    max_external_result_rows = models.PositiveIntegerField(default=30, verbose_name='外部送信する最大集計行数')
    conversation_retention_days = models.PositiveIntegerField(default=0, verbose_name='会話履歴の保存期間(日、0は無期限)')
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


class AIKnowledgeDocument(models.Model):
    """設定画面から登録するPDF・Excel等のナレッジ原本。抽出本文はDBへ保存しない。"""
    category = models.CharField(max_length=30, choices=KNOWLEDGE_CATEGORY_CHOICES, verbose_name='区分')
    name = models.CharField(max_length=150, verbose_name='資料名')
    file = models.FileField(upload_to='ai_knowledge/', verbose_name='資料ファイル')
    description = models.CharField(max_length=300, blank=True, default='', verbose_name='説明')
    is_enabled = models.BooleanField(default=True, verbose_name='有効')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_knowledge_document'
        ordering = ['category', 'name', 'id']
        verbose_name = 'AIナレッジ資料'
        verbose_name_plural = 'AIナレッジ資料'


class AICrossScreenAccessPolicy(models.Model):
    """画面をまたぐ読み取り参照を、管理者定義と利用者承認の両方で制御する。"""
    source_screen_id = models.CharField(max_length=40, choices=list(SCREEN_CATALOG.items()), verbose_name='起点画面')
    target_screen_id = models.CharField(max_length=40, choices=list(SCREEN_CATALOG.items()), verbose_name='追加参照領域')
    purpose = models.CharField(max_length=200, verbose_name='利用目的')
    is_enabled = models.BooleanField(default=True, verbose_name='有効')
    allow_external_transfer = models.BooleanField(default=True, verbose_name='外部AIへの集計結果送信を許可')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_cross_screen_access_policy'
        constraints = [models.UniqueConstraint(fields=['source_screen_id', 'target_screen_id'], name='ai_cross_screen_access_unique')]
        ordering = ['source_screen_id', 'target_screen_id']
        verbose_name = 'AI横断参照定義'
        verbose_name_plural = 'AI横断参照定義'
