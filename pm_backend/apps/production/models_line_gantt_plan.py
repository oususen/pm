from django.db import models
from masters.models import Line, Product


class LineGanttPlan(models.Model):
    """ガントチャート用ライン計画テーブル"""
    plan_id = models.CharField(max_length=160, primary_key=True)
    line = models.ForeignKey(Line, on_delete=models.CASCADE, related_name='gantt_plans')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gantt_plans')
    plan_date = models.DateField()
    plan_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    sequence_no = models.IntegerField(null=True, blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    processes_plan = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_line_gantt_plan'
        indexes = [
            models.Index(fields=['line', 'plan_date']),
        ]

    def __str__(self):
        return f"{self.plan_id} ({self.line_id} {self.product_id})"
