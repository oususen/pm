from django.conf import settings
from django.db import models


class ProductionLock(models.Model):
    """汎用ロックテーブル。lock_type + 対象キーの組み合わせでロックを管理する。"""

    lock_type = models.CharField(max_length=50, verbose_name='ロック種別')
    line = models.ForeignKey(
        'masters.Line',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name='ライン',
    )
    plan_date = models.DateField(null=True, blank=True, verbose_name='計画日')
    product = models.ForeignKey(
        'masters.Product',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name='製品',
    )
    locked_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='ロック時計画数')
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='ロック者',
    )
    locked_at = models.DateTimeField(auto_now_add=True, verbose_name='ロック日時')

    class Meta:
        db_table = 'production_lock'
        verbose_name = '生産ロック'
        verbose_name_plural = '生産ロック'
        unique_together = [['lock_type', 'line', 'plan_date', 'product']]
        indexes = [
            models.Index(fields=['lock_type', 'line', 'plan_date']),
        ]

    def __str__(self):
        return f'{self.lock_type} line={self.line_id} date={self.plan_date} product={self.product_id}'
