from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models

from masters.models import Equipment


class LaserShiftRecord(models.Model):
    """レーザー設備シフト稼働記録（開始・終了の2段階入力）"""

    SHIFT_1 = 1
    SHIFT_2 = 2
    SHIFT_CHOICES = [
        (SHIFT_1, '1勤'),
        (SHIFT_2, '2勤'),
    ]

    id = models.BigAutoField(primary_key=True)
    work_date = models.DateField(verbose_name='作業日')
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,
        related_name='laser_shift_records',
        verbose_name='設備',
    )
    shift_no = models.PositiveSmallIntegerField(
        choices=SHIFT_CHOICES,
        verbose_name='シフト',
    )

    # 開始時に入力
    start_totalizer_hour = models.PositiveIntegerField(verbose_name='開始積算カウンター(H)')
    start_totalizer_min = models.PositiveIntegerField(
        verbose_name='開始積算カウンター(M)',
        validators=[MaxValueValidator(59)],
    )

    # 終了時に入力（null = 開始のみ登録済み）
    end_totalizer_hour = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='終了積算カウンター(H)'
    )
    end_totalizer_min = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MaxValueValidator(59)],
        verbose_name='終了積算カウンター(M)',
    )
    work_hours = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='仕事時間(H)',
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_laser_shift_records',
        verbose_name='作成者',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='updated_laser_shift_records',
        verbose_name='更新者',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_laser_shift_record'
        verbose_name = 'レーザーシフト稼働記録'
        verbose_name_plural = 'レーザーシフト稼働記録'
        ordering = ['-work_date', 'equipment', 'shift_no']
        unique_together = [['work_date', 'equipment', 'shift_no']]
        indexes = [
            models.Index(fields=['work_date']),
            models.Index(fields=['equipment', 'work_date']),
        ]

    def __str__(self):
        return f'{self.work_date} {self.get_shift_no_display()} {self.equipment_id}'
