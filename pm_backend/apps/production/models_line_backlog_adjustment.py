from django.conf import settings
from django.db import models


class LineBacklogAdjustment(models.Model):
    """LineBacklog再計算に反映する手動調整"""

    ADJUST_TYPE_CHOICES = [
        ('STOCK', '在庫調整'),
        ('PLANNED_STOCK', '計画在庫調整'),
        ('PROGRESS', '進度調整'),
        ('PLANNED_PROGRESS', '計画進度調整'),
    ]

    line = models.ForeignKey('masters.Line', on_delete=models.CASCADE, related_name='backlog_adjustments')
    product = models.ForeignKey('masters.Product', on_delete=models.CASCADE, related_name='backlog_adjustments')
    process = models.ForeignKey('masters.Process', on_delete=models.SET_NULL, null=True, blank=True, related_name='backlog_adjustments')
    plan_date = models.DateField(verbose_name='対象日')
    adjust_type = models.CharField(max_length=30, choices=ADJUST_TYPE_CHOICES, verbose_name='調整種別')
    adjust_qty = models.IntegerField(default=0, verbose_name='調整値')
    reason = models.CharField(max_length=255, blank=True, default='', verbose_name='理由')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='line_backlog_adjustments_updates',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'production_line_backlog_adjustment'
        verbose_name = 'ラインバックログ調整'
        verbose_name_plural = 'ラインバックログ調整'
        constraints = [
            models.UniqueConstraint(
                fields=['line', 'product', 'process', 'plan_date', 'adjust_type'],
                name='uniq_line_backlog_adjustment_key',
            )
        ]
        indexes = [
            models.Index(fields=['line', 'plan_date', 'adjust_type']),
            models.Index(fields=['product', 'plan_date']),
        ]

    def __str__(self):
        process_code = self.process.process_code if self.process_id else '-'
        return f'{self.line.line_code}/{self.product.product_code}/{process_code}/{self.plan_date}/{self.adjust_type}'
