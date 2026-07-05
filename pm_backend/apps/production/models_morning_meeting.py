import os
import uuid

from django.conf import settings
from django.db import models


def morning_meeting_attachment_upload_to(instance, filename):
    _, ext = os.path.splitext(filename or '')
    return f'morning_meeting_attachments/{instance.meeting_id}/{uuid.uuid4().hex}{ext.lower()}'


class MorningMeeting(models.Model):
    STATUS_DRAFT = 'DRAFT'
    STATUS_READY = 'READY'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CHOICES = [
        (STATUS_DRAFT, '下書き'),
        (STATUS_READY, '準備完了'),
        (STATUS_IN_PROGRESS, '実行中'),
        (STATUS_COMPLETED, '完了'),
    ]

    meeting_date = models.DateField(verbose_name='朝礼日')
    title = models.CharField(max_length=200, verbose_name='タイトル')
    target_departments = models.ManyToManyField(
        'accounts.Department',
        blank=True,
        related_name='target_morning_meetings',
        verbose_name='対象部署',
    )
    target_lines = models.ManyToManyField(
        'masters.Line',
        blank=True,
        related_name='target_morning_meetings',
        verbose_name='対象ライン',
    )
    facilitator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='facilitated_morning_meetings',
        verbose_name='司会者',
    )
    agenda = models.TextField(blank=True, default='', verbose_name='議題')
    notices = models.TextField(blank=True, default='', verbose_name='連絡事項')
    cautions = models.TextField(blank=True, default='', verbose_name='注意事項')
    execution_note = models.TextField(blank=True, default='', verbose_name='実行メモ')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name='状態',
    )
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='開始日時')
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name='終了日時')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_morning_meetings',
        verbose_name='作成者',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_morning_meetings',
        verbose_name='更新者',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_morning_meeting'
        verbose_name = '朝礼'
        verbose_name_plural = '朝礼'
        ordering = ['-meeting_date', '-id']
        indexes = [
            models.Index(fields=['meeting_date', 'status'], name='pm_mm_date_stat_idx'),
        ]

    def __str__(self):
        return f'{self.meeting_date} {self.title}'


class MorningMeetingParticipant(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_PRESENT = 'PRESENT'
    STATUS_ABSENT = 'ABSENT'
    STATUS_LATE = 'LATE'
    ATTENDANCE_STATUS_CHOICES = [
        (STATUS_PENDING, '未確認'),
        (STATUS_PRESENT, '出席'),
        (STATUS_ABSENT, '欠席'),
        (STATUS_LATE, '遅刻'),
    ]

    meeting = models.ForeignKey(
        MorningMeeting,
        on_delete=models.CASCADE,
        related_name='participants',
        verbose_name='朝礼',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='morning_meeting_participants',
        verbose_name='参加者',
    )
    attendance_status = models.CharField(
        max_length=20,
        choices=ATTENDANCE_STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name='参加状態',
    )
    checked_at = models.DateTimeField(null=True, blank=True, verbose_name='確認日時')
    remark = models.CharField(max_length=255, blank=True, default='', verbose_name='備考')
    display_order = models.PositiveIntegerField(default=0, verbose_name='表示順')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_morning_meeting_participant'
        verbose_name = '朝礼参加者'
        verbose_name_plural = '朝礼参加者'
        unique_together = [['meeting', 'user']]
        ordering = ['display_order', 'id']
        indexes = [
            models.Index(fields=['meeting', 'attendance_status'], name='pm_mmp_meet_stat_idx'),
            models.Index(fields=['user'], name='pm_mmp_user_idx'),
        ]

    def __str__(self):
        return f'{self.meeting_id}:{self.user_id}'


class MorningMeetingAttachment(models.Model):
    TYPE_PDF = 'PDF'
    TYPE_IMAGE = 'IMAGE'
    TYPE_EXCEL = 'EXCEL'
    TYPE_CHOICES = [
        (TYPE_PDF, 'PDF'),
        (TYPE_IMAGE, '画像'),
        (TYPE_EXCEL, 'Excel'),
    ]

    meeting = models.ForeignKey(
        MorningMeeting,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name='朝礼',
    )
    file = models.FileField(upload_to=morning_meeting_attachment_upload_to, verbose_name='添付ファイル')
    original_name = models.CharField(max_length=255, verbose_name='元ファイル名')
    content_type = models.CharField(max_length=100, blank=True, default='', verbose_name='Content-Type')
    file_size = models.PositiveBigIntegerField(default=0, verbose_name='ファイルサイズ')
    attachment_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='添付種別')
    display_order = models.PositiveIntegerField(default=0, verbose_name='表示順')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_morning_meeting_attachment'
        verbose_name = '朝礼添付資料'
        verbose_name_plural = '朝礼添付資料'
        ordering = ['display_order', 'id']
        indexes = [
            models.Index(fields=['meeting', 'display_order'], name='pm_mma_meet_disp_idx'),
        ]

    def __str__(self):
        return f'{self.meeting_id}:{self.original_name}'
