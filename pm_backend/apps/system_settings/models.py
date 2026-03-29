from django.conf import settings
from django.db import models


class SystemSetting(models.Model):
    """システム全体の汎用Key-Value設定"""
    key = models.CharField(max_length=100, unique=True, verbose_name='キー')
    value = models.CharField(max_length=500, verbose_name='値')
    description = models.CharField(max_length=200, blank=True, verbose_name='説明')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='更新者',
    )

    class Meta:
        db_table = 'system_settings'
        verbose_name = 'システム設定'
        verbose_name_plural = 'システム設定'
        ordering = ['key']

    def __str__(self):
        return f"{self.key} = {self.value}"
