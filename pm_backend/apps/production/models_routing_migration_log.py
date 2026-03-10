from django.conf import settings
from django.db import models


class RoutingMigrationLog(models.Model):
    """
    ルーティング変更に伴う在庫移行の記録。
    旧ラインから新ラインへ stock_qty を移行した際の監査ログ。
    """
    migrated_at = models.DateTimeField(auto_now_add=True, verbose_name='移行日時')
    product = models.ForeignKey(
        'masters.Product',
        on_delete=models.CASCADE,
        related_name='routing_migration_logs',
        verbose_name='製品',
    )
    old_line = models.ForeignKey(
        'masters.Line',
        on_delete=models.SET_NULL,
        null=True,
        related_name='migration_from_logs',
        verbose_name='旧ライン',
    )
    old_process = models.ForeignKey(
        'masters.Process',
        on_delete=models.SET_NULL,
        null=True,
        related_name='migration_from_logs',
        verbose_name='旧工程',
    )
    new_line = models.ForeignKey(
        'masters.Line',
        on_delete=models.SET_NULL,
        null=True,
        related_name='migration_to_logs',
        verbose_name='新ライン',
    )
    new_process = models.ForeignKey(
        'masters.Process',
        on_delete=models.SET_NULL,
        null=True,
        related_name='migration_to_logs',
        verbose_name='新工程',
    )
    migrated_qty = models.IntegerField(verbose_name='移行数量')
    migration_date = models.DateField(verbose_name='移行基準日')
    migrated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='routing_migration_logs',
        verbose_name='実行者',
    )

    class Meta:
        db_table = 'production_routing_migration_log'
        verbose_name = 'ルーティング変更在庫移行ログ'
        verbose_name_plural = 'ルーティング変更在庫移行ログ'
        indexes = [
            models.Index(fields=['product', 'migrated_at']),
            models.Index(fields=['old_line', 'migrated_at']),
            models.Index(fields=['new_line', 'migrated_at']),
        ]

    def __str__(self):
        return (
            f"{self.migration_date} {self.product.product_code} "
            f"{getattr(self.old_line, 'line_code', '-')} → "
            f"{getattr(self.new_line, 'line_code', '-')} "
            f"{self.migrated_qty}個"
        )
