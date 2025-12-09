from django.db import models
from masters.models import Process, Product, Line, RoutingStep


class LineBacklog(models.Model):
    plan_date = models.DateField()
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='backlogs')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='line_backlogs')
    line = models.ForeignKey(Line, on_delete=models.CASCADE, related_name='backlogs')
    demand_qty_plan = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    source_line = models.ForeignKey(Line, on_delete=models.SET_NULL, null=True, blank=True, related_name='backlog_sources')
    source_routing_step = models.ForeignKey(RoutingStep, on_delete=models.SET_NULL, null=True, blank=True, related_name='backlog_sources')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'line_backlog'
        unique_together = [('plan_date', 'process', 'product', 'line')]
        indexes = [
            models.Index(fields=['plan_date', 'line']),
        ]

    def __str__(self):
        return f"{self.plan_date} {self.process} {self.product} {self.line} {self.demand_qty_plan}"
