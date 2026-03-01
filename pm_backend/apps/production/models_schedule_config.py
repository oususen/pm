from django.conf import settings
from django.db import models


class ScheduleConfig(models.Model):
    """定時タスクスケジュール設定"""
    RANGE_BASE_CHOICES = [
        ('TODAY', '今日'),
        ('YESTERDAY', '昨日'),
        ('TWO_DAYS_AGO', '一昨日'),
    ]
    TASK_CHOICES = [
        ('INVENTORY_RECALC', '在庫再計算'),
        ('PICKUP_ONLY', '取り込みのみ'),
        ('INVENTORY_ONLY', '在庫計算のみ'),
        ('PROGRESS_ONLY', '進度計算のみ'),
        ('AUTO_PLAN', '生産計画自動生成'),
        ('ORDER_EXPANSION', '自動受注展開'),
        ('AUTO_SAFETY_STOCK_INTERNAL', '自動安全在庫（社内）'),
        ('AUTO_SAFETY_STOCK_PURCHASE', '自動安全在庫（購入品）'),
        ('AUTO_PURCHASE_ORDER_CHECK', '発注タイミング日次チェック'),
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
    range_start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='計算期間開始日'
    )
    range_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='計算期間終了日'
    )
    range_base_day = models.CharField(
        max_length=20,
        choices=RANGE_BASE_CHOICES,
        default='TODAY',
        verbose_name='計算期間開始基準日'
    )
    range_days_after = models.PositiveSmallIntegerField(
        default=45,
        verbose_name='計算期間終了日数（基準日から何日後）'
    )
    average_days_window = models.PositiveSmallIntegerField(
        default=60,
        verbose_name='平均算出日数'
    )
    safety_days = models.PositiveSmallIntegerField(
        default=1,
        verbose_name='安全在庫日数'
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
    include_current_month = models.BooleanField(
        default=False,
        verbose_name='今月を対象'
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
    execution_order = models.PositiveIntegerField(
        default=100,
        verbose_name='実行順'
    )
    auto_plan_sequence_locked = models.BooleanField(
        default=False,
        verbose_name='順序運用ロック'
    )
    notify_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='schedule_config_notifications',
        verbose_name='通知先ユーザー'
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
