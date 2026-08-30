from django.db import models
from masters.models import Line, Process, Product, RoutingStep

# Import all models to ensure they're registered with Django
from .models_line_daily_schedule_setting import LineDailyScheduleSetting
from .models_line_default_schedule_setting import LineDefaultScheduleSetting
from .models_line_backlog_adjustment import LineBacklogAdjustment
from .models_plan_change_log import ProductionPlanChangeLog
from .models_plan_lock_setting import ProductionPlanLockSetting
from .models_plan_line_setting import ProductionPlanLineSetting
from .models_record_inquiry_setting import ProductionRecordInquirySetting
from .models_process_work_session import ProcessWorkSession
from .models_process_work_session_change_history import ProcessWorkSessionChangeHistory
from .models_process_work_session_equipment import ProcessWorkSessionEquipment
from .models_schedule_config import ScheduleConfig
from .models_daily_process_target import DailyProcessTarget
from .models_purchase_actual_reconcile import (
    PurchaseActualReconcileReport,
    PurchaseActualReconcileReportDetail,
)
from .models_production_actual_reconcile import (
    ProductionActualReconcileReport,
    ProductionActualReconcileReportDetail,
)
from .models_routing_migration_log import RoutingMigrationLog
from .models_gantt_display_product_map import GanttDisplayProductMap
from .models_gantt_process_display_order import GanttProcessDisplayOrder
from .models_laser_pattern import LaserPattern, LaserPatternComponent, LaserPatternFinishedProduct
from .models_laser_actual import LaserActual, LaserActualDetail
from .models_record_confirmation import ProductionRecordConfirmation
from .models_production import ProcessActual, ProductionOrder, StockAllocation
from .models_camera_actual import CameraCountEvent, ProductionResultDaily
from .models_line_product_display_order import LineProductDisplayOrder
from .models_auto_plan_aggregate_setting import AutoPlanAggregateSetting
from .models_plan_deviation_config import PlanDeviationLineConfig
from .models_stocktake_record import StocktakeRecord
from .models_singleproc_finished_entry import SingleProcFinishedEntry
from .models_morning_meeting import MorningMeeting, MorningMeetingParticipant, MorningMeetingAttachment


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
    process = models.ForeignKey(
        Process,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='工程'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='製品'
    )
    product_code = models.CharField(max_length=50, verbose_name='製品コード')
    ship_to_code = models.CharField(max_length=40, default='', blank=True, verbose_name='納入先コード')
    plan_date = models.DateField(verbose_name='必要日')
    lead_time_days = models.IntegerField(default=0, verbose_name='リードタイム(日)')
    is_shifted = models.BooleanField(default=False, verbose_name='前倒し需要フラグ')
    firm_is_shifted = models.BooleanField(default=False, verbose_name='確定前倒し需要フラグ')
    forecast_is_shifted = models.BooleanField(default=False, verbose_name='内示前倒し需要フラグ')

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
    firm_order_numbers = models.CharField(
        max_length=500,
        default='',
        blank=True,
        verbose_name='展開元受注番号(確定)'
    )
    forecast_order_numbers = models.CharField(
        max_length=500,
        default='',
        blank=True,
        verbose_name='展開元受注番号(内示)'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_line_demand'
        verbose_name = 'ライン需要展開'
        verbose_name_plural = 'ライン需要展開'
        unique_together = [['line', 'product_code', 'plan_date', 'process', 'ship_to_code']]
        indexes = [
            models.Index(fields=['line', 'plan_date']),
            models.Index(fields=['product_code']),
            models.Index(fields=['process']),
            models.Index(fields=['ship_to_code']),
        ]

    def __str__(self):
        return f"{self.line.line_code if self.line_id else ''} {self.product_code} {self.plan_date}"
