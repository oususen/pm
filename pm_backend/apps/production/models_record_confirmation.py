from django.conf import settings
from django.db import models

from masters.models import Line, Process


class ProductionRecordConfirmation(models.Model):
    """生産実績確認済みフラグ（日付・ライン・工程単位）"""

    id = models.BigAutoField(primary_key=True)
    work_date = models.DateField(verbose_name='対象日')
    line = models.ForeignKey(
        Line,
        on_delete=models.CASCADE,
        related_name='record_confirmations',
        verbose_name='ライン',
    )
    process = models.ForeignKey(
        Process,
        on_delete=models.CASCADE,
        related_name='record_confirmations',
        verbose_name='工程',
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='record_confirmations',
        verbose_name='確認者',
    )
    confirmed_at = models.DateTimeField(auto_now_add=True, verbose_name='確認日時')

    class Meta:
        db_table = 't_production_record_confirmation'
        verbose_name = '生産実績確認'
        verbose_name_plural = '生産実績確認'
        unique_together = [('work_date', 'line', 'process')]
        indexes = [
            models.Index(fields=['work_date', 'line']),
        ]

    def __str__(self):
        return f'{self.work_date} {self.line_id} {self.process_id}'
