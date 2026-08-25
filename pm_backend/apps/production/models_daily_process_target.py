from django.conf import settings
from django.db import models

from masters.models import Line, Process


class DailyProcessTarget(models.Model):
    """ライン×工程×日付ごとの目標台数指示。"""

    line = models.ForeignKey(Line, on_delete=models.CASCADE, verbose_name='ライン')
    process = models.ForeignKey(Process, on_delete=models.CASCADE, verbose_name='工程')
    plan_date = models.DateField(verbose_name='計画日')
    target_time = models.TimeField(verbose_name='目標時刻')
    target_qty = models.IntegerField(verbose_name='目標台数')
    product_label = models.CharField(max_length=100, verbose_name='製品俗称')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_daily_process_targets',
        verbose_name='作成者',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='updated_daily_process_targets',
        verbose_name='更新者',
    )

    class Meta:
        db_table = 't_daily_process_target'
        verbose_name = '日別工程目標'
        verbose_name_plural = '日別工程目標'
        indexes = [
            models.Index(fields=['line', 'process', 'plan_date']),
            models.Index(fields=['plan_date']),
        ]
        ordering = ['plan_date', 'target_time', 'id']

    def __str__(self):
        line_code = self.line.line_code if self.line_id else ''
        process_code = self.process.process_code if self.process_id else ''
        return f'{line_code} {process_code} {self.plan_date} {self.target_time} {self.product_label} {self.target_qty}'
