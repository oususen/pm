from datetime import datetime, timedelta

from django.conf import settings
from django.db import models


class SystemSetting(models.Model):
    """システム全体の汎用Key-Value設定"""
    key = models.CharField(max_length=100, unique=True, verbose_name='キー')
    value = models.TextField(verbose_name='値')
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

    @classmethod
    def get_lock_date(cls, category):
        """締め日を取得する汎用メソッド。
        category: 'kubota_sakai_due', 'inventory', 'progress' など
        値の形式: '2026-04-16'(固定日付) or 'days:3'(今日のN日前)
        """
        from orders.utils.calendar_utils import get_business_today
        try:
            setting = cls.objects.get(key=f'lock_date.{category}')
            if not setting.value:
                return None
            val = setting.value.strip()
            if val.startswith('days:'):
                n = int(val[5:])
                return get_business_today() - timedelta(days=n) if n > 0 else None
            return datetime.strptime(val, '%Y-%m-%d').date()
        except (cls.DoesNotExist, ValueError):
            return None
