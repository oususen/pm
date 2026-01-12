from django.db import models
from masters.models import Process, Product, Line


class LinePlan(models.Model):
    """
    ライン別生産計画（ユーザー入力）
    """
    plan_date = models.DateField()
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='line_plans')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='line_plans')
    line = models.ForeignKey(Line, on_delete=models.CASCADE, related_name='line_plans')

    plan_qty = models.IntegerField(default=0)
    sequence_no = models.IntegerField(null=True, blank=True, default=1)
    plan_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'line_plan'
        unique_together = [('plan_date', 'line', 'sequence_no')]
        indexes = [
            models.Index(fields=['plan_date', 'line']),
        ]

    def __str__(self):
        return f"{self.plan_date} {self.process} {self.product} {self.line} {self.plan_qty}"
