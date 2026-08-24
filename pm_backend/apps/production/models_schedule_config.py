from datetime import datetime, timedelta

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
        ('KUBOTA_SAKAI_DUE_SYNC', 'クボタ堺納期調整 取込+再配分'),
        ('AUTO_PLAN', '生産計画自動生成'),
        ('ORDER_EXPANSION', '自動受注展開'),
        ('AUTO_SAFETY_STOCK_INTERNAL', '自動安全在庫（社内）'),
        ('AUTO_SAFETY_STOCK_PURCHASE', '自動安全在庫（購入品）'),
        ('AUTO_PURCHASE_ORDER_CHECK', '発注タイミング日次チェック'),
        ('PURCHASE_ACTUAL_RECONCILE_CHECK', '納入実績整合チェック'),
        ('PRODUCTION_ACTUAL_RECONCILE_CHECK', '生産実績整合チェック'),
        ('PLAN_TO_ACTUAL_COPY', '計画実績自動セット'),
        ('CONTAINER_IMPORT_TMP_CLEANUP', '荷姿設定Excel取込 一時ファイル削除'),
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
    process = models.ForeignKey(
        'masters.Process',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='schedule_configs',
        verbose_name='対象工程'
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
    kubota_due_auto_link_enabled = models.BooleanField(
        default=True,
        verbose_name='クボタ堺納期調整 自動紐づけ有効'
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
                fields=['task_name', 'line', 'process'],
                name='uniq_schedule_task_line'
            )
        ]

    def __str__(self):
        line_label = f' ({self.line.line_code})' if self.line_id else ''
        process_label = f' / {self.process.process_code}' if self.process_id else ''
        return f'{self.get_task_name_display()}{line_label}{process_label} - {self.scheduled_hour:02d}:{self.scheduled_minute:02d}'


RUN_LOG_RETENTION_DAYS = 30


class ScheduleRunLog(models.Model):
    """定時タスク実行履歴（1回の実行につき1レコード）"""

    config = models.ForeignKey(
        ScheduleConfig,
        on_delete=models.CASCADE,
        related_name='run_logs',
        verbose_name='タスク設定',
    )
    task_name = models.CharField(
        max_length=50,
        choices=ScheduleConfig.TASK_CHOICES,
        verbose_name='タスク名'
    )
    line = models.ForeignKey(
        'masters.Line',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name='対象ライン'
    )
    process = models.ForeignKey(
        'masters.Process',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name='対象工程'
    )
    started_at = models.DateTimeField(verbose_name='実行開始日時')
    finished_at = models.DateTimeField(verbose_name='実行終了日時')
    status = models.CharField(
        max_length=20,
        choices=ScheduleConfig.STATUS_CHOICES,
        verbose_name='結果'
    )
    message = models.TextField(blank=True, default='', verbose_name='実行メッセージ')
    duration_seconds = models.FloatField(null=True, blank=True, verbose_name='実行時間（秒）')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'production_schedule_run_log'
        verbose_name = 'タスク実行履歴'
        verbose_name_plural = 'タスク実行履歴'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['config', '-started_at']),
        ]

    def __str__(self):
        return f'{self.task_name} {self.started_at:%Y-%m-%d %H:%M} - {self.status}'


def record_schedule_run_log(config, *, status, message='', duration_seconds=None, started_at=None):
    """
    定時タスクの実行結果を履歴として1件記録し、
    直近RUN_LOG_RETENTION_DAYS日を超えた古い履歴は自動的に削除する。

    last_run_* は最新1回分しか保持しないため、過去の実行結果を追えるように
    このテーブルへ完了時（成功/失敗）ごとに1行ずつ積み上げる。
    """
    if config is None:
        return None

    now = datetime.now()
    log = ScheduleRunLog.objects.create(
        config=config,
        task_name=config.task_name,
        line=config.line,
        process=config.process,
        started_at=started_at or config.last_run_at or now,
        finished_at=now,
        status=status,
        message=message or '',
        duration_seconds=duration_seconds,
    )
    cutoff = now - timedelta(days=RUN_LOG_RETENTION_DAYS)
    ScheduleRunLog.objects.filter(config=config, started_at__lt=cutoff).delete()
    return log
