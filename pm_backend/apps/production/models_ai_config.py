from django.db import models


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
