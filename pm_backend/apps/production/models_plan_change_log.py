from django.conf import settings
from django.db import models

from masters.models import Line, Process, Product


class ProductionPlanChangeLog(models.Model):
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
        related_name='production_plan_change_logs'
    )

    class Meta:
        db_table = 'production_plan_change_log'
        indexes = [
            models.Index(fields=['plan_date', 'line'], name='prod_plchg_date_line_idx'),
        ]

    def __str__(self):
        return f'{self.plan_date} {self.product_id} {self.before_qty}->{self.after_qty}'
