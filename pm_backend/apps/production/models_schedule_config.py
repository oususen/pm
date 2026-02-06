from django.conf import settings
from django.db import models


class ScheduleConfig(models.Model):
    """定時タスクスケジュール設定"""
    TASK_CHOICES = [
        ('INVENTORY_RECALC', '在庫再計算'),
    ]
    STATUS_CHOICES = [
        ('SUCCESS', '成功'),
        ('FAILED', '失敗'),
        ('RUNNING', '実行中'),
    ]

    task_name = models.CharField(
        max_length=50,
        unique=True,
        choices=TASK_CHOICES,
        verbose_name='タスク名'
    )
    is_enabled = models.BooleanField(default=True, verbose_name='有効')
    scheduled_hour = models.PositiveSmallIntegerField(
        default=7,
        verbose_name='実行時（時）'
    )
    scheduled_minute = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='実行時（分）'
    )
    last_run_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='最終実行日時'
    )
    last_run_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        null=True, blank=True,
        verbose_name='最終実行結果'
    )
    last_run_message = models.TextField(
        blank=True, default='',
        verbose_name='最終実行メッセージ'
    )
    last_run_duration_seconds = models.FloatField(
        null=True, blank=True,
        verbose_name='最終実行時間（秒）'
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='schedule_config_updates'
    )

    class Meta:
        db_table = 'production_schedule_config'
        verbose_name = 'スケジュール設定'
        verbose_name_plural = 'スケジュール設定'

    def __str__(self):
        return f'{self.get_task_name_display()} - {self.scheduled_hour:02d}:{self.scheduled_minute:02d}'
