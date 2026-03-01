"""
製造実行系モデル
- 在庫引当（StockAllocation）
- 製造指示（ProductionOrder）
- 工程別製造実績（ProcessActual）
"""
from django.db import models
from masters.models import Product, Routing, RoutingStep, Process, Line


class StockAllocation(models.Model):
    """在庫引当マスタ"""
    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='製品'
    )
    location = models.CharField(
        max_length=50,
        verbose_name='保管場所',
        help_text='論理的な保管場所（倉庫、ロケーション等）'
    )
    current_stock = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        verbose_name='現在庫数'
    )
    reserved_qty = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        verbose_name='引当済数量'
    )
    min_stock_qty = models.PositiveIntegerField(
        verbose_name='最小在庫数',
        help_text='この数量を下回るとアラート'
    )
    is_bottleneck = models.BooleanField(
        default=False,
        verbose_name='ボトルネック品',
        help_text='在庫不足によるボトルネック部品フラグ'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_stock_allocation'
        verbose_name = '在庫引当'
        verbose_name_plural = '在庫引当'
        unique_together = [['product', 'location']]
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['is_bottleneck']),
        ]

    def __str__(self):
        return f"{self.product.product_code} @ {self.location} (在庫: {self.current_stock})"

    @property
    def available_qty(self):
        """引当可能数量"""
        return self.current_stock - self.reserved_qty


class ProductionOrder(models.Model):
    """製造指示"""
    STATUS_CHOICES = [
        ('PLANNED', '計画済'),
        ('RELEASED', '指示済'),
        ('IN_PROGRESS', '進行中'),
        ('COMPLETED', '完了'),
        ('CANCELED', '中止'),
    ]

    id = models.BigAutoField(primary_key=True)
    order_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='製造指示番号'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='製品'
    )
    routing = models.ForeignKey(
        Routing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='ルーティング'
    )
    line = models.ForeignKey(
        Line,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='ライン'
    )
    order_qty = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        verbose_name='指示数量'
    )
    scheduled_start_date = models.DateField(verbose_name='予定開始日')
    scheduled_end_date = models.DateField(verbose_name='予定完了日')
    actual_start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='実績開始日'
    )
    actual_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='実績完了日'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PLANNED',
        verbose_name='ステータス'
    )
    allocation = models.ForeignKey(
        StockAllocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='在庫引当',
        related_name='production_orders'
    )
    priority = models.IntegerField(
        default=0,
        verbose_name='優先度',
        help_text='数値が大きいほど優先度が高い'
    )
    remark = models.TextField(
        null=True,
        blank=True,
        verbose_name='備考'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_production_order'
        verbose_name = '製造指示'
        verbose_name_plural = '製造指示'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['scheduled_start_date']),
            models.Index(fields=['product']),
            models.Index(fields=['line']),
        ]

    def __str__(self):
        return f"{self.order_no} - {self.product.product_code} ({self.get_status_display()})"


class ProcessActual(models.Model):
    """工程別製造実績"""
    id = models.BigAutoField(primary_key=True)
    production_order = models.ForeignKey(
        ProductionOrder,
        on_delete=models.CASCADE,
        related_name='actuals',
        verbose_name='製造指示'
    )
    routing_step = models.ForeignKey(
        RoutingStep,
        on_delete=models.CASCADE,
        verbose_name='ルーティング工程'
    )
    process = models.ForeignKey(
        Process,
        on_delete=models.CASCADE,
        verbose_name='工程'
    )
    line = models.ForeignKey(
        Line,
        on_delete=models.CASCADE,
        verbose_name='ライン'
    )
    completed_qty = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        verbose_name='完了数量'
    )
    actual_duration_min = models.IntegerField(
        verbose_name='実績工数(分)',
        help_text='実際にかかった時間（分）'
    )
    completed_at = models.DateTimeField(verbose_name='完了日時')
    operator = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='作業者',
        help_text='作業者コードまたは名前'
    )
    remark = models.TextField(
        null=True,
        blank=True,
        verbose_name='備考'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_process_actual'
        verbose_name = '工程別製造実績'
        verbose_name_plural = '工程別製造実績'
        indexes = [
            models.Index(fields=['production_order', 'routing_step']),
            models.Index(fields=['completed_at']),
            models.Index(fields=['process']),
            models.Index(fields=['line']),
        ]

    def __str__(self):
        return f"{self.production_order.order_no} - {self.process.process_code} ({self.completed_qty})"
