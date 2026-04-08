from django.conf import settings
from django.db import models

from masters.models import Line, Process, Product


class GanttDisplayProductMap(models.Model):
    """ガントチャート生成時に表示対象とする品目マップ"""

    line = models.ForeignKey(
        Line,
        on_delete=models.CASCADE,
        related_name='gantt_display_product_maps',
        verbose_name='ライン',
    )
    final_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='gantt_display_final_product_maps',
        verbose_name='ライン最終品',
    )
    process = models.ForeignKey(
        Process,
        on_delete=models.CASCADE,
        related_name='gantt_display_product_maps',
        verbose_name='工程',
    )
    display_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='gantt_display_target_maps',
        verbose_name='表示品',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='gantt_display_product_maps',
        verbose_name='更新者',
    )

    class Meta:
        db_table = 't_gantt_display_product_map'
        verbose_name = 'ガント表示品マップ'
        verbose_name_plural = 'ガント表示品マップ'
        unique_together = [['line', 'final_product', 'process', 'display_product']]
        indexes = [
            models.Index(fields=['line', 'final_product']),
            models.Index(fields=['process']),
            models.Index(fields=['display_product']),
        ]

    def __str__(self):
        line_code = self.line.line_code if self.line_id else ''
        final_code = self.final_product.product_code if self.final_product_id else ''
        process_code = self.process.process_code if self.process_id else ''
        display_code = self.display_product.product_code if self.display_product_id else ''
        return f'{line_code} / {final_code} / {process_code} -> {display_code}'
