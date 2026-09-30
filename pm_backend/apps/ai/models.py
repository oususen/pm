from django.conf import settings
from django.db import models

from ai.config.models import AIDataPolicy, AIKnowledgeDocument, AIKnowledgeSource, AIProviderConfig, AIToolPolicy


class AISearchConfig(models.Model):
    """AIチャットのDB検索対象設定"""
    model_path = models.CharField(max_length=100, verbose_name='モデルパス')
    label = models.CharField(max_length=50, verbose_name='表示ラベル')
    search_fields = models.JSONField(verbose_name='検索フィールド')
    display_fields = models.JSONField(verbose_name='表示フィールド')
    display_template = models.CharField(max_length=300, verbose_name='表示テンプレート')
    filter_json = models.JSONField(default=dict, blank=True, verbose_name='フィルタ条件')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    display_order = models.IntegerField(default=0, verbose_name='表示順')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_search_config'
        ordering = ['display_order', 'label']
        verbose_name = 'AI検索設定'
        verbose_name_plural = 'AI検索設定'

    def __str__(self):
        return f'{self.label}（{self.model_path}）'


class AIConversation(models.Model):
    """社内AIチャットの会話履歴。利用者本人だけが一覧・再開・削除できる。"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_conversations', verbose_name='利用者',
    )
    screen_context = models.CharField(max_length=40, blank=True, default='', verbose_name='起点画面')
    provider = models.CharField(max_length=30, blank=True, default='', verbose_name='最後に使用したプロバイダ')
    title = models.CharField(max_length=100, blank=True, default='', verbose_name='会話タイトル')
    messages = models.JSONField(default=list, verbose_name='会話内容')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_conversation'
        ordering = ['-updated_at']
        verbose_name = '社内AI会話履歴'
        verbose_name_plural = '社内AI会話履歴'

    def __str__(self):
        return self.title or f'会話{self.pk}'
