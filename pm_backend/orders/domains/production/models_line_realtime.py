"""
ライン実時間記録モデル（品質管理機能は除く）
"""
from django.db import models
from masters.models import Line, Product


class LineRealtimeRecord(models.Model):
    """生産線リアルタイム生産記録（シンプル版）"""

    RECORD_TYPE_CHOICES = [
        ('PRODUCTION', '生産完成'),
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
    line = models.ForeignKey(Line, on_delete=models.CASCADE, verbose_name='ライン')
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='製品'
    )
    product_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='製品コード'
    )
    product_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='品名'
    )

    # 高精度タイムスタンプ
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='記録時刻', db_index=True)

    record_type = models.CharField(
        max_length=20,
        choices=RECORD_TYPE_CHOICES,
        verbose_name='記録タイプ'
    )

    # 生産数量
    qty = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        verbose_name='数量'
    )

    # 設備状態
    equipment_state = models.CharField(
        max_length=20,
        choices=EQUIPMENT_STATE_CHOICES,
        null=True,
        blank=True,
        verbose_name='設備状態'
    )

    # 追加情報（JSON）
    event_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name='イベント詳細データ'
    )

    # 追溯情報
    batch_no = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='ロット番号'
    )
    operator_name = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='作業者名'
    )

    # 備考
    remarks = models.TextField(
        null=True,
        blank=True,
        verbose_name='備考'
    )

    class Meta:
        db_table = 't_line_realtime_record'
        verbose_name = 'ライン実時間記録'
        verbose_name_plural = 'ライン実時間記録'
        indexes = [
            models.Index(fields=['line', 'timestamp']),
            models.Index(fields=['record_type']),
            models.Index(fields=['product_code']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.line.line_code} - {self.timestamp} ({self.get_record_type_display()})"


class LineStatus(models.Model):
    """ライン現在状態（最新状態のスナップショット）"""

    line = models.OneToOneField(
        Line,
        on_delete=models.CASCADE,
        primary_key=True,
        verbose_name='ライン'
    )

    # 現在の状態
    current_state = models.CharField(
        max_length=20,
        choices=LineRealtimeRecord.EQUIPMENT_STATE_CHOICES,
        default='STOPPED',
        verbose_name='現在の状態'
    )

    # 本日の累計生産数
    today_output = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        verbose_name='本日生産数'
    )

    # 本日の計画数
    today_plan = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        verbose_name='本日計画数'
    )

    # 現在生産中の品番
    current_product_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='現在生産品番'
    )
    current_product_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='現在生産品名'
    )

    # 最終更新時刻
    last_update = models.DateTimeField(
        auto_now=True,
        verbose_name='最終更新時刻'
    )

    class Meta:
        db_table = 't_line_status'
        verbose_name = 'ライン状態'
        verbose_name_plural = 'ライン状態'

    def __str__(self):
        return f"{self.line.line_code} - {self.get_current_state_display()}"
