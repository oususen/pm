from django.db import models
from masters.models import Line, Process, Product
from ..production.models_process_realtime import ProcessRealtimeRecord


class ScrapRecord(models.Model):
    """仕損記録（当面の簡易テーブル。将来 backlog へ統合予定）"""

    EVENT_TYPE_CHOICES = [
        ('SCRAP', '仕損'),
        ('RETURN', '戻し'),
    ]

    DISPOSITION_STATUS_CHOICES = [
        ('PENDING', '判定待ち'),
        ('APPROVED', '使用可'),
        ('REJECTED', '仕損確定'),
        ('PARTIAL', '一部使用可'),
    ]

    id = models.BigAutoField(primary_key=True)
    line = models.ForeignKey(
        Line,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='ライン'
    )
    process = models.ForeignKey(
        Process,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='工程'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='製品'
    )
    product_code = models.CharField(max_length=50, null=True, blank=True, verbose_name='製品コード', db_index=True)
    product_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='品名')

    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
        default='SCRAP',
        verbose_name='イベント種別'
    )
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='仕損数量')
    recorded_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='記録時刻')
    plan_date = models.DateField(null=True, blank=True, db_index=True, verbose_name='計画日')

    return_for = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='return_records',
        verbose_name='戻し対象仕損'
    )

    disposition_status = models.CharField(
        max_length=20,
        choices=DISPOSITION_STATUS_CHOICES,
        default='REJECTED',
        verbose_name='判定ステータス'
    )
    return_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='戻し数量')
    decided_at = models.DateTimeField(null=True, blank=True, verbose_name='判定日時')
    decided_by = models.CharField(max_length=50, null=True, blank=True, verbose_name='判定者')

    reason = models.CharField(max_length=100, null=True, blank=True, verbose_name='理由/区分')
    reason_detail = models.CharField(max_length=200, null=True, blank=True, verbose_name='理由詳細')
    batch_no = models.CharField(max_length=100, null=True, blank=True, verbose_name='ロット番号')
    operator_name = models.CharField(max_length=50, null=True, blank=True, verbose_name='作業者名')
    remarks = models.TextField(null=True, blank=True, verbose_name='備考')
    process_record = models.OneToOneField(
        ProcessRealtimeRecord,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='scrap_detail',
        verbose_name='工程実時間記録',
    )
    is_replenished = models.BooleanField(default=False, verbose_name='補充完了')
    replenished_at = models.DateTimeField(null=True, blank=True, verbose_name='補充完了日時')
    replenished_by = models.CharField(max_length=50, null=True, blank=True, verbose_name='補充完了者')

    class Meta:
        db_table = 't_scrap_record'
        verbose_name = '仕損記録'
        verbose_name_plural = '仕損記録'
        indexes = [
            models.Index(fields=['process', 'recorded_at']),
            models.Index(fields=['line', 'recorded_at']),
        ]
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.product_code or ''} {self.qty} ({self.recorded_at})"


class ScrapRecordDetail(models.Model):
    """仕損記録のBOM展開明細ごとの補充ステータス"""

    id = models.BigAutoField(primary_key=True)
    scrap_record = models.ForeignKey(ScrapRecord, on_delete=models.CASCADE, related_name='details', verbose_name='仕損記録')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='製品')
    product_code = models.CharField(max_length=50, null=True, blank=True, verbose_name='製品コード', db_index=True)
    product_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='品名')
    process_id = models.BigIntegerField(null=True, blank=True, verbose_name='工程ID')
    line_id = models.BigIntegerField(null=True, blank=True, verbose_name='ラインID')
    supplier_id = models.BigIntegerField(null=True, blank=True, verbose_name='仕入先ID')
    sourcing_type = models.CharField(max_length=20, null=True, blank=True, verbose_name='調達区分')
    deduct_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='減算数量')
    is_replenished = models.BooleanField(default=False, verbose_name='補充完了')
    replenished_at = models.DateTimeField(null=True, blank=True, verbose_name='補充完了日時')
    replenished_by = models.CharField(max_length=50, null=True, blank=True, verbose_name='補充完了者')

    class Meta:
        db_table = 't_scrap_record_detail'
        verbose_name = '仕損記録明細'
        verbose_name_plural = '仕損記録明細'
