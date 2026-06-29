from django.conf import settings
from django.db import models

from masters.models import Process, Product
from .models_process_work_session import ProcessWorkSession


class ProcessWorkSessionChangeHistory(models.Model):
    OPERATION_TYPE_CHOICES = [
        ('ADD', '追加'),
        ('UPDATE', '変更'),
        ('DELETE', '削除'),
    ]

    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(
        ProcessWorkSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='change_histories',
        verbose_name='対象セッション',
    )
    session_record_id = models.BigIntegerField(verbose_name='対象セッションID', db_index=True)
    operation_type = models.CharField(max_length=10, choices=OPERATION_TYPE_CHOICES, verbose_name='操作区分')
    process = models.ForeignKey(
        Process,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='工程',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='製品',
    )
    product_code = models.CharField(max_length=50, blank=True, default='', verbose_name='品番')
    product_name = models.CharField(max_length=100, blank=True, default='', verbose_name='品名')
    plan_date = models.DateField(null=True, blank=True, verbose_name='作業日')
    reason = models.TextField(verbose_name='変更理由')
    change_summary = models.TextField(verbose_name='変更内容')
    before_data = models.JSONField(default=dict, blank=True, verbose_name='変更前データ')
    after_data = models.JSONField(default=dict, blank=True, verbose_name='変更後データ')
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='process_work_session_change_histories',
        verbose_name='変更者',
    )
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name='変更時刻')

    class Meta:
        db_table = 't_process_work_session_change_history'
        verbose_name = '工程作業セッション変更履歴'
        verbose_name_plural = '工程作業セッション変更履歴'
        ordering = ['-changed_at', '-id']
        indexes = [
            models.Index(fields=['session_record_id', 'changed_at'], name='t_pwschg_sid_changed_idx'),
            models.Index(fields=['operation_type', 'changed_at'], name='t_pwschg_type_changed_idx'),
        ]

    def __str__(self):
        return f'{self.session_record_id} {self.operation_type} {self.changed_at}'
