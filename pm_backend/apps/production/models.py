from django.db import models
from masters.models import Line, Product, RoutingStep

# Import all models to ensure they're registered with Django
from .models_line_daily_schedule_setting import LineDailyScheduleSetting
from .models_line_default_schedule_setting import LineDefaultScheduleSetting
from .models_plan_change_log import ProductionPlanChangeLog
from .models_plan_lock_setting import ProductionPlanLockSetting
from .models_schedule_config import ScheduleConfig


class LineDemand(models.Model):
    """ライン別の需要展開（内示/確定 + 計画/実績）。"""

    id = models.BigAutoField(primary_key=True)
    line = models.ForeignKey(Line, on_delete=models.CASCADE, verbose_name='ライン')
    routing_step = models.ForeignKey(
        RoutingStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='ルーティング工程'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='製品'
    )
    product_code = models.CharField(max_length=50, verbose_name='製品コード')
    plan_date = models.DateField(verbose_name='必要日')
    lead_time_days = models.IntegerField(default=0, verbose_name='リードタイム(日)')

    forecast_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='内示数量')
    firm_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='確定数量')
    plan_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='計画数')
    actual_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='実績数')
    plan_progress = models.DecimalField(max_digits=9, decimal_places=3, default=0, verbose_name='計画進度')
    actual_progress = models.DecimalField(max_digits=9, decimal_places=3, default=0, verbose_name='実績進度')

    order_numbers = models.CharField(
        max_length=500,
        default='',
        blank=True,
        verbose_name='展開元受注番号'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_line_demand'
        verbose_name = 'ライン需要展開'
        verbose_name_plural = 'ライン需要展開'
        unique_together = [['line', 'product_code', 'plan_date']]
        indexes = [
            models.Index(fields=['line', 'plan_date']),
            models.Index(fields=['product_code']),
        ]

    def __str__(self):
        return f"{self.line.line_code if self.line_id else ''} {self.product_code} {self.plan_date}"
