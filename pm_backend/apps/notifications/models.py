from django.db import models
from django.conf import settings
from accounts.models import Department


class Notification(models.Model):
    """通知マスタ"""
    title = models.CharField(max_length=200, verbose_name='タイトル')
    category = models.CharField(max_length=50, verbose_name='カテゴリ')
    domain = models.CharField(max_length=50, verbose_name='種別')
    target_departments = models.ManyToManyField(
        Department,
        blank=True,
        related_name='notifications',
        verbose_name='対象部署'
    )
    target_positions = models.JSONField(default=list, blank=True, verbose_name='対象役職')
    target_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='targeted_notifications',
        verbose_name='対象ユーザー'
    )
    valid_from = models.DateField(null=True, blank=True, verbose_name='有効開始日')
    valid_to = models.DateField(null=True, blank=True, verbose_name='有効終了日')
    display_order = models.IntegerField(default=0, verbose_name='表示順')
    description = models.TextField(blank=True, verbose_name='説明')
    operator_name = models.CharField(max_length=100, blank=True, verbose_name='入力者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'notifications'
        ordering = ['display_order', 'id']
        verbose_name = '通知'
        verbose_name_plural = '通知'


class NotificationRead(models.Model):
    """通知既読状態（ユーザーごと）"""
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='reads',
        verbose_name='通知'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_reads',
        verbose_name='ユーザー'
    )
    read_at = models.DateTimeField(auto_now_add=True, verbose_name='既読日時')

    class Meta:
        db_table = 'notification_reads'
        unique_together = ['notification', 'user']
        verbose_name = '通知既読'
        verbose_name_plural = '通知既読'
