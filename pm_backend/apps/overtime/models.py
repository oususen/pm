from django.db import models
from django.conf import settings
from accounts.models import Department
from datetime import datetime, timedelta
from decimal import Decimal


def apply_breaks(wall_minutes):
    """2時間ごとに10分休憩を控除（130分サイクル）"""
    CYCLE = 130  # 2h work(120) + 10min break
    full_cycles = wall_minutes // CYCLE
    remainder = wall_minutes % CYCLE
    return full_cycles * 120 + min(remainder, 120)


def calculate_overtime_hours(start_time, end_time):
    """
    開始・終了時刻から通常残業時間・深夜残業時間を計算。
    深夜帯: 22:00〜翌05:00 / 2時間ごとに10分休憩を控除
    Returns: (regular_hours, midnight_hours) as Decimal
    """
    base = datetime(2000, 1, 1)
    start_dt = datetime.combine(base.date(), start_time)
    end_dt = datetime.combine(base.date(), end_time)

    # 日をまたぐ場合
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)

    midnight_zones = [
        (datetime(2000, 1, 1, 22, 0), datetime(2000, 1, 2, 0, 0)),  # 22:00-24:00
        (datetime(2000, 1, 2, 0, 0), datetime(2000, 1, 2, 5, 0)),   # 00:00-05:00
    ]

    wall_minutes = int((end_dt - start_dt).total_seconds() / 60)
    midnight_wall = 0

    for zone_start, zone_end in midnight_zones:
        overlap_start = max(start_dt, zone_start)
        overlap_end = min(end_dt, zone_end)
        if overlap_end > overlap_start:
            midnight_wall += int((overlap_end - overlap_start).total_seconds() / 60)

    regular_wall = wall_minutes - midnight_wall

    # 休憩控除後、30分単位で切り捨て
    work_minutes = (apply_breaks(wall_minutes) // 30) * 30
    ratio = work_minutes / wall_minutes if wall_minutes > 0 else 1
    # 深夜も30分単位で切り捨て、通常 = 合計 - 深夜
    midnight_minutes = (int(midnight_wall * ratio) // 30) * 30
    regular_minutes = work_minutes - midnight_minutes

    return (
        Decimal(str(regular_minutes / 60)),
        Decimal(str(midnight_minutes / 60)),
    )


class OvertimeApplication(models.Model):
    STATUS_CHOICES = [
        ('draft', '下書き'),
        ('submitted', '申請中'),
        ('approved_leader', 'リーダー承認済み'),
        ('approved_supervisor', '班長承認済み'),
        ('approved_chief', '係長承認済み'),
        ('approved_manager', '最終承認済み'),
        ('rejected', '却下'),
    ]
    TYPE_CHOICES = [
        ('overtime', '時間外'),
        ('holiday', '休日出勤'),
    ]

    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='overtime_applications',
        verbose_name='申請者',
    )
    work_date = models.DateField(verbose_name='実施日')
    application_type = models.CharField(
        max_length=10, choices=TYPE_CHOICES, default='overtime', verbose_name='申請種別'
    )
    work_start_time = models.TimeField(null=True, blank=True, verbose_name='勤務開始時刻')
    scheduled_end_time = models.TimeField(null=True, blank=True, verbose_name='定時終了時刻')
    start_time = models.TimeField(verbose_name='残業開始時刻')
    end_time = models.TimeField(verbose_name='残業終了時刻')
    hours = models.DecimalField(
        max_digits=5, decimal_places=1, default=0, verbose_name='時間外時間(H)'
    )
    midnight_hours = models.DecimalField(
        max_digits=5, decimal_places=1, default=0, verbose_name='深夜残業時間(H)'
    )
    reason = models.TextField(blank=True, verbose_name='発生理由')
    team = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='overtime_applications',
        verbose_name='班',
        limit_choices_to={'level': 'team'},
    )
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default='draft', verbose_name='ステータス'
    )
    signature = models.ImageField(
        upload_to='overtime_signatures/', null=True, blank=True, verbose_name='サイン'
    )
    rejection_reason = models.TextField(blank=True, verbose_name='却下理由')
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name='申請日時')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_overtime_application'
        ordering = ['-work_date', '-created_at']
        verbose_name = '残業申請'
        verbose_name_plural = '残業申請'

    def __str__(self):
        return f"{self.work_date} {self.applicant} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # 開始・終了時刻から時間数を自動計算
        self.hours, self.midnight_hours = calculate_overtime_hours(
            self.start_time, self.end_time
        )
        super().save(*args, **kwargs)


class OvertimeApprovalLog(models.Model):
    ROLE_CHOICES = [
        ('leader', 'リーダー'),
        ('supervisor', '班長'),
        ('chief', '係長'),
        ('manager', '課長/部長'),
    ]
    STATUS_CHOICES = [
        ('pending', '承認待ち'),
        ('approved', '承認済み'),
        ('rejected', '却下'),
    ]

    application = models.ForeignKey(
        OvertimeApplication,
        on_delete=models.CASCADE,
        related_name='approval_logs',
        verbose_name='申請',
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='overtime_approval_logs',
        verbose_name='承認者',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name='役割')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状態'
    )
    comment = models.TextField(blank=True, verbose_name='コメント')
    acted_at = models.DateTimeField(null=True, blank=True, verbose_name='対応日時')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        db_table = 't_overtime_approval_log'
        ordering = ['created_at']
        verbose_name = '残業承認ログ'
        verbose_name_plural = '残業承認ログ'

    def __str__(self):
        return f"{self.application} - {self.get_role_display()} ({self.get_status_display()})"
