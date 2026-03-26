"""
工程作業セッションモデル
"""
from django.db import models

from masters.models import Process, Product
from .models_process_realtime import ProcessRealtimeRecord


class ProcessWorkSession(models.Model):
    """開始〜終了の作業セッションを保持する。"""

    SESSION_TYPE_CHOICES = [
        ('WORK', '作業'),
        ('PAUSE', '中断'),
    ]

    STATUS_CHOICES = [
        ('OPEN', '進行中'),
        ('CLOSED', '終了'),
    ]

    id = models.BigAutoField(primary_key=True)
    process = models.ForeignKey(Process, on_delete=models.CASCADE, verbose_name='工程')
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='製品',
    )
    product_code = models.CharField(max_length=50, blank=True, default='', verbose_name='製品コード')
    product_name = models.CharField(max_length=100, blank=True, default='', verbose_name='品名')

    plan_date = models.DateField(verbose_name='計画日')
    session_no = models.IntegerField(default=1, verbose_name='セッション連番')
    session_type = models.CharField(
        max_length=10,
        choices=SESSION_TYPE_CHOICES,
        default='WORK',
        verbose_name='セッション種別',
    )
    start_action = models.CharField(max_length=20, blank=True, default='', verbose_name='開始アクション')
    end_action = models.CharField(max_length=20, blank=True, default='', verbose_name='終了アクション')

    started_at = models.DateTimeField(verbose_name='開始時刻', db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name='終了時刻', db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN', verbose_name='セッション状態')

    duration_seconds = models.IntegerField(default=0, verbose_name='継続秒数')
    production_qty = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        verbose_name='実績数量',
    )
    defect_qty = models.IntegerField(
        default=0,
        verbose_name='仕損数量',
    )

    start_record = models.ForeignKey(
        ProcessRealtimeRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='started_work_sessions',
        verbose_name='開始記録',
    )
    end_record = models.ForeignKey(
        ProcessRealtimeRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ended_work_sessions',
        verbose_name='終了記録',
    )

    issue_count = models.IntegerField(default=0, verbose_name='不整合件数')
    issue_flags = models.JSONField(default=list, blank=True, verbose_name='不整合フラグ')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_process_work_session'
        verbose_name = '工程作業セッション'
        verbose_name_plural = '工程作業セッション'
        ordering = ['-started_at', '-id']
        indexes = [
            models.Index(fields=['process', 'plan_date']),
            models.Index(fields=['process', 'product', 'status']),
            models.Index(fields=['session_type', 'status'], name='t_process_w_session_2968ba_idx'),
            models.Index(fields=['plan_date', 'status']),
            models.Index(fields=['issue_count']),
        ]

    def __str__(self):
        product_code = self.product_code or (self.product.product_code if self.product_id else '')
        return f"{self.process.process_code} {product_code} #{self.session_no}"
