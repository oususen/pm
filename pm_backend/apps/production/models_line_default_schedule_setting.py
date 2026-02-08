from django.conf import settings
from django.db import models

from masters.models import Line


class LineDefaultScheduleSetting(models.Model):
    """ライン別デフォルト最終工程開始時刻の設定"""

    line = models.OneToOneField(
        Line,
        on_delete=models.CASCADE,
        related_name='default_schedule_setting',
        verbose_name='ライン',
    )
    final_process_start_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name='最終工程開始時刻（デフォルト）',
    )
    adjust_to_break_end = models.BooleanField(
        default=True,
        verbose_name='休憩明けに補正',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='line_default_schedule_settings',
        verbose_name='更新者',
    )

    class Meta:
        db_table = 't_line_default_schedule_setting'
        verbose_name = 'ラインデフォルトスケジュール設定'
        verbose_name_plural = 'ラインデフォルトスケジュール設定'
        indexes = [
            models.Index(fields=['line']),
        ]

    def __str__(self):
        return f'{self.line.line_code if self.line_id else ""} {self.final_process_start_time or "未設定"}'
