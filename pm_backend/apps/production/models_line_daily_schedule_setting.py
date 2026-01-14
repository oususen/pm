from django.db import models
from masters.models import Line


class LineDailyScheduleSetting(models.Model):
    """
    ライン×日付ごとのスケジュール設定
    最終工程開始時刻などを管理
    """
    line = models.ForeignKey(Line, on_delete=models.CASCADE, related_name='daily_schedule_settings')
    plan_date = models.DateField(verbose_name="計画日")

    # 最終工程開始時刻 (HH:MM形式の文字列)
    final_process_start_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="最終工程開始時刻"
    )

    # 休憩時間終了に調整するかどうか
    adjust_to_break_end = models.BooleanField(
        default=True,
        verbose_name="休憩時間終了に調整"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'line_daily_schedule_setting'
        unique_together = [('line', 'plan_date')]
        indexes = [
            models.Index(fields=['line', 'plan_date']),
        ]
        ordering = ['plan_date', 'line']

    def __str__(self):
        return f"{self.line.line_code} - {self.plan_date} - {self.final_process_start_time or 'N/A'}"
