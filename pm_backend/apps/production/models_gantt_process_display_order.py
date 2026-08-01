from django.conf import settings
from django.db import models

from masters.models import Line, Process


class GanttProcessDisplayOrder(models.Model):
    """ライン別の工程ガント表示順。"""

    line = models.ForeignKey(
        Line,
        on_delete=models.CASCADE,
        related_name='gantt_process_display_orders',
        verbose_name='ライン',
    )
    process = models.ForeignKey(
        Process,
        on_delete=models.CASCADE,
        related_name='gantt_process_display_orders',
        verbose_name='工程',
    )
    display_order = models.IntegerField(default=0, verbose_name='表示順')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='gantt_process_display_orders',
        verbose_name='更新者',
    )

    class Meta:
        db_table = 't_gantt_process_display_order'
        verbose_name = 'ガント工程表示順'
        verbose_name_plural = 'ガント工程表示順'
        unique_together = [['line', 'process']]
        ordering = ['line_id', 'display_order', 'process_id']
        indexes = [
            models.Index(fields=['line', 'display_order']),
            models.Index(fields=['process']),
        ]

    def __str__(self):
        line_code = self.line.line_code if self.line_id else ''
        process_code = self.process.process_code if self.process_id else ''
        return f'{line_code} / {process_code} ({self.display_order})'
