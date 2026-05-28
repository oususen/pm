from django.db import models
from masters.models import Line


class PlanDeviationLineConfig(models.Model):
    """計画乖離レポートでLineGanttPlanから計画数を取得するライン設定"""
    line = models.OneToOneField(Line, on_delete=models.CASCADE, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_plan_deviation_line_config'

    def __str__(self):
        return f"PlanDeviationConfig(line={self.line_id})"
