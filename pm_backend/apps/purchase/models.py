from django.conf import settings
from django.db import models

from masters.models import Line, Process, Product


class PurchasePlanLockSetting(models.Model):
    lock_days = models.PositiveIntegerField(default=0, verbose_name='ロック日数')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='purchase_plan_lock_settings'
    )

    class Meta:
        db_table = 'purchase_plan_lock_setting'

    def __str__(self):
        return f'PurchasePlanLockSetting(lock_days={self.lock_days})'


class PurchasePlanChangeLog(models.Model):
    changed_at = models.DateTimeField(auto_now_add=True)
    plan_date = models.DateField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    line = models.ForeignKey(Line, on_delete=models.CASCADE)
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    sequence_no = models.IntegerField(null=True, blank=True)
    plan_id = models.CharField(max_length=255, null=True, blank=True)
    before_qty = models.IntegerField(default=0)
    after_qty = models.IntegerField(default=0)
    reason = models.TextField()
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='purchase_plan_change_logs'
    )

    class Meta:
        db_table = 'purchase_plan_change_log'
        indexes = [
            models.Index(fields=['plan_date', 'line']),
        ]

    def __str__(self):
        return f'{self.plan_date} {self.product_id} {self.before_qty}->{self.after_qty}'
