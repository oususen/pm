from django.conf import settings
from django.db import models


class ProductionPlanLockSetting(models.Model):
    lock_days = models.PositiveIntegerField(default=0, verbose_name='ロック日数')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='production_plan_lock_settings'
    )

    class Meta:
        db_table = 'production_plan_lock_setting'

    def __str__(self):
        return f'ProductionPlanLockSetting(lock_days={self.lock_days})'
