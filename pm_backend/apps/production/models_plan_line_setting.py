from django.conf import settings
from django.db import models


class ProductionPlanLineSetting(models.Model):
    tab_key = models.CharField(max_length=30, unique=True, verbose_name='タブキー')
    tab_name = models.CharField(max_length=50, default='', blank=True, verbose_name='タブ表示名')
    sort_order = models.IntegerField(default=0, verbose_name='表示順')
    target_line_codes = models.JSONField(default=list, blank=True, verbose_name='対象ラインコード一覧')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='production_plan_line_settings',
        verbose_name='更新者',
    )

    class Meta:
        db_table = 'production_plan_line_setting'
        ordering = ['sort_order', 'id']
        verbose_name = '生産計画ライン設定'
        verbose_name_plural = '生産計画ライン設定'

    def __str__(self):
        return f'ProductionPlanLineSetting(tab_key={self.tab_key}, tab_name={self.tab_name})'
