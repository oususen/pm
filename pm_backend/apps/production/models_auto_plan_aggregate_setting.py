from django.db import models
from django.conf import settings
from masters.models import Line, Product


class AutoPlanAggregateSetting(models.Model):
    """自動計画のまとめ生産設定（ライン×製品）"""

    line = models.ForeignKey(Line, on_delete=models.CASCADE, related_name='auto_plan_aggregate_settings')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='auto_plan_aggregate_settings')
    aggregate_weekday = models.PositiveSmallIntegerField(default=2, verbose_name='まとめ生産日(0=日..6=土)')
    aggregate_days = models.PositiveSmallIntegerField(default=7, verbose_name='まとめ対象期間(日数)')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='auto_plan_aggregate_settings',
    )

    class Meta:
        db_table = 't_auto_plan_aggregate_setting'
        verbose_name = '自動計画まとめ生産設定'
        verbose_name_plural = '自動計画まとめ生産設定'
        unique_together = [('line', 'product')]
        indexes = [
            models.Index(fields=['line', 'is_active']),
            models.Index(fields=['product', 'is_active']),
        ]

    def __str__(self):
        line_code = self.line.line_code if self.line_id else '-'
        product_code = self.product.product_code if self.product_id else '-'
        return f'{line_code} {product_code} wd={self.aggregate_weekday} days={self.aggregate_days}'

