"""
工程実時間記録モデル（ライン実時間記録の工程版）
"""
from django.db import models
from masters.models import Process, Product


class ProcessRealtimeRecord(models.Model):
    """工程リアルタイム作業記録（シンプル版）"""

    RECORD_TYPE_CHOICES = [
        ('PRODUCTION', '生産完成'),
        ('SCRAP', '仕損'),
        ('EQUIPMENT_STATE', '設備状態変更'),
        ('OPERATOR_ACTION', '作業者アクション'),
    ]

    EQUIPMENT_STATE_CHOICES = [
        ('RUNNING', '運転中'),
        ('IDLE', '待機'),
        ('SETUP', '段取り中'),
        ('MAINTENANCE', '保全中'),
        ('BREAKDOWN', '故障'),
        ('STOPPED', '停止'),
    ]

    id = models.BigAutoField(primary_key=True)
    process = models.ForeignKey(Process, on_delete=models.CASCADE, verbose_name='工程')
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='製品'
    )
    product_code = models.CharField(max_length=50, null=True, blank=True, verbose_name='製品コード')
    product_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='品名')

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='記録時刻', db_index=True)

    record_type = models.CharField(
        max_length=20,
        choices=RECORD_TYPE_CHOICES,
        verbose_name='記録タイプ'
    )

    qty = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        verbose_name='数量'
    )

    equipment_state = models.CharField(
        max_length=20,
        choices=EQUIPMENT_STATE_CHOICES,
        null=True,
        blank=True,
        verbose_name='設備状態'
    )

    event_data = models.JSONField(null=True, blank=True, verbose_name='イベント詳細データ')

    batch_no = models.CharField(max_length=100, null=True, blank=True, verbose_name='ロット番号')
    operator_name = models.CharField(max_length=50, null=True, blank=True, verbose_name='作業者名')
    remarks = models.TextField(null=True, blank=True, verbose_name='備考')

    class Meta:
        db_table = 't_process_realtime_record'
        verbose_name = '工程実時間記録'
        verbose_name_plural = '工程実時間記録'
        indexes = [
            models.Index(fields=['process', 'timestamp']),
            models.Index(fields=['record_type']),
            models.Index(fields=['product_code']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.process.process_code} - {self.timestamp} ({self.get_record_type_display()})"

