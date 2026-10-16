from django.conf import settings
from django.db import models

from masters.models import Line, Product


class ProgressMonitorTarget(models.Model):
    """進度監視画面に表示する製品とラインの組み合わせ。"""

    MONITOR_TYPE_PROGRESS = 'progress'
    MONITOR_TYPE_INVENTORY = 'inventory'
    MONITOR_TYPE_CHOICES = [
        (MONITOR_TYPE_PROGRESS, '進度'),
        (MONITOR_TYPE_INVENTORY, '在庫'),
    ]

    monitor_type = models.CharField(
        max_length=20,
        choices=MONITOR_TYPE_CHOICES,
        default=MONITOR_TYPE_PROGRESS,
        verbose_name='監視モード',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='progress_monitor_targets',
        verbose_name='製品',
    )
    line = models.ForeignKey(
        Line,
        on_delete=models.CASCADE,
        related_name='progress_monitor_targets',
        verbose_name='ライン',
    )
    display_order = models.IntegerField(default=0, verbose_name='表示順')
    memo = models.CharField(max_length=500, blank=True, default='', verbose_name='メモ')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registered_progress_monitor_targets',
        verbose_name='登録者',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='登録日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'production_progress_monitor_target'
        verbose_name = '進度監視対象'
        verbose_name_plural = '進度監視対象'
        unique_together = [['product', 'line']]
        ordering = ['display_order', 'line__line_code', 'product__product_code', 'id']

    def __str__(self):
        return f'{self.line.line_code} - {self.product.product_code}'
