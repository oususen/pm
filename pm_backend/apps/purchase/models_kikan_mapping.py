from django.conf import settings
from django.db import models

from masters.models import Supplier


class PurchaseActualKikanMapping(models.Model):
    """仕入先納入実績 基幹システム入力用マッピング設定（仕入先ごと）"""

    supplier = models.OneToOneField(
        Supplier,
        on_delete=models.CASCADE,
        related_name='kikan_mapping',
        verbose_name='仕入先',
    )
    mappings = models.JSONField(default=list, blank=True, verbose_name='品番マッピング一覧')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='purchase_actual_kikan_mappings',
        verbose_name='更新者',
    )

    class Meta:
        db_table = 'purchase_actual_kikan_mapping'
        verbose_name = '仕入先納入基幹マッピング'
        verbose_name_plural = '仕入先納入基幹マッピング'

    def __str__(self):
        return f'PurchaseActualKikanMapping(supplier={self.supplier_id})'
