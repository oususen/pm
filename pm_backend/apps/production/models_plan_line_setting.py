from django.conf import settings
from django.db import models


class ProductionPlanLineSetting(models.Model):
    tab_key = models.CharField(max_length=30, unique=True, verbose_name='対象タブ')
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
        verbose_name = '生産計画ライン設定'
        verbose_name_plural = '生産計画ライン設定'

    def __str__(self):
        return f'ProductionPlanLineSetting(tab_key={self.tab_key})'
