from django.db import models
from masters.models import Line


class LineProductDisplayOrder(models.Model):
    line = models.ForeignKey(
        Line,
        on_delete=models.CASCADE,
        related_name='product_display_orders',
        verbose_name='ライン',
    )
    product_code = models.CharField(max_length=30, verbose_name='品番コード')
    display_order = models.IntegerField(default=0, verbose_name='表示順')
    context = models.CharField(max_length=30, default='default', verbose_name='コンテキスト')
    bg_color = models.CharField(max_length=10, blank=True, default='', verbose_name='行背景色')
    text_color = models.CharField(max_length=10, blank=True, default='', verbose_name='行文字色')
    plan_bg_color = models.CharField(max_length=10, blank=True, default='', verbose_name='ロット追加ボタン背景色')
    plan_text_color = models.CharField(max_length=10, blank=True, default='', verbose_name='ロット追加ボタン文字色')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_line_product_display_order'
        verbose_name = 'ライン別製品表示順'
        verbose_name_plural = 'ライン別製品表示順'
        unique_together = [['line', 'product_code', 'context']]
        ordering = ['line', 'display_order']
        indexes = [
            models.Index(fields=['line', 'display_order']),
        ]

    def __str__(self):
        return f"{self.line.line_code} - {self.product_code} ({self.display_order})"
