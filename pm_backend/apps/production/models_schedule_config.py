from django.conf import settings
from django.db import models


class ScheduleConfig(models.Model):
    """定時タスクスケジュール設定"""
    TASK_CHOICES = [
        ('INVENTORY_RECALC', '在庫再計算'),
        ('AUTO_PLAN', '生産計画自動生成'),
    ]
    STATUS_CHOICES = [
        ('SUCCESS', '成功'),
        ('FAILED', '失敗'),
        ('RUNNING', '実行中'),
    ]

    task_name = models.CharField(
        max_length=50,
        choices=TASK_CHOICES,
        verbose_name='タスク名'
    )
    line = models.ForeignKey(
        'masters.Line',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='schedule_configs',
        verbose_name='対象ライン'
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
    scheduled_dom = models.PositiveSmallIntegerField(
        null=True, blank=True,
        verbose_name='実行日（1-31）'
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
    include_next_month = models.BooleanField(
        default=True,
        verbose_name='翌月を対象'
    )
    include_second_month = models.BooleanField(
        default=False,
        verbose_name='翌々月を対象'
    )
    include_third_month = models.BooleanField(
        default=False,
        verbose_name='翌々翌月を対象'
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
        constraints = [
            models.UniqueConstraint(
                fields=['task_name', 'line'],
                name='uniq_schedule_task_line'
            )
        ]

    def __str__(self):
        line_label = f' ({self.line.line_code})' if self.line_id else ''
        return f'{self.get_task_name_display()}{line_label} - {self.scheduled_hour:02d}:{self.scheduled_minute:02d}'
