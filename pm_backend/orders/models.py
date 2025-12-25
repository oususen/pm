from django.db import models
from masters.models import Customer, Line, Product, RoutingStep
from .models_line_backlog import LineBacklog
from .models_line_gantt_plan import LineGanttPlan
from .models_production import StockAllocation, ProductionOrder, ProcessActual
from .models_line_realtime import LineRealtimeRecord, LineStatus
from .models_process_realtime import ProcessRealtimeRecord
from .models_scrap import ScrapRecord


class Order(models.Model):
    """受注ヘッダ"""
    ORDER_TYPE_CHOICES = [
        ('FIRM', '確定'),
        ('FORECAST', '内示'),
    ]

    STATUS_CHOICES = [
        ('OPEN', 'オープン'),
        ('CLOSED', 'クローズ'),
        ('CANCELED', 'キャンセル'),
        ('SUPERSEDED', '無効'),
    ]

    id = models.BigAutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='得意先')
    order_no = models.CharField(max_length=50, verbose_name='受注番号')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, verbose_name='受注タイプ')
    version_no = models.CharField(max_length=20, default='v1', verbose_name='版番号')
    source_system = models.CharField(max_length=50, null=True, blank=True, verbose_name='ソースシステム')
    source_file = models.CharField(max_length=200, null=True, blank=True, verbose_name='ソースファイル')
    order_date = models.DateField(null=True, blank=True, verbose_name='受注日')
    freeze_from = models.DateField(null=True, blank=True, verbose_name='凍結開始日')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN', verbose_name='ステータス')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_order'
        verbose_name = '受注'
        verbose_name_plural = '受注'
        unique_together = [['customer', 'order_no', 'order_type', 'version_no']]
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.customer.customer_code} - {self.order_no} ({self.get_order_type_display()})"


class OrderLine(models.Model):
    """受注明細"""
    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='lines', verbose_name='受注')
    line_no = models.IntegerField(verbose_name='行番号')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='製品')
    product_code = models.CharField(max_length=50, verbose_name='製品コード')
    quantity = models.DecimalField(max_digits=14, decimal_places=3, verbose_name='数量')
    due_date = models.DateField(verbose_name='納期')
    plant_code = models.CharField(max_length=20, null=True, blank=True, verbose_name='工場コード')
    ship_to_code = models.CharField(max_length=40, null=True, blank=True, verbose_name='納入先コード')
    remark = models.CharField(max_length=200, null=True, blank=True, verbose_name='備考')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_order_line'
        verbose_name = '受注明細'
        verbose_name_plural = '受注明細'
        unique_together = [['order', 'line_no']]
        indexes = [
            models.Index(fields=['due_date']),
            models.Index(fields=['product_code']),
        ]

    def __str__(self):
        return f"{self.order.order_no} - Line {self.line_no}: {self.product_code}"


class StgOrderRaw(models.Model):
    """受注取込ステージング（生データ）"""
    ORDER_TYPE_CHOICES = [
        ('FIRM', '確定'),
        ('FORECAST', '内示'),
    ]

    PARSE_STATUS_CHOICES = [
        ('PENDING', '未処理'),
        ('PARSED', '処理済'),
        ('ERROR', 'エラー'),
    ]

    id = models.BigAutoField(primary_key=True)
    customer_code = models.CharField(max_length=20, verbose_name='得意先コード')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, verbose_name='受注タイプ')
    source_system = models.CharField(max_length=50, null=True, blank=True, verbose_name='ソースシステム')
    source_file = models.CharField(max_length=200, null=True, blank=True, verbose_name='ソースファイル')
    source_row_no = models.IntegerField(verbose_name='ソース行番号')
    record_token = models.CharField(max_length=50, null=True, blank=True, verbose_name='レコード識別子')
    start_month = models.DateField(null=True, blank=True, verbose_name='開始月度')
    due_date = models.DateField(null=True, blank=True, verbose_name='納期')
    product_code = models.CharField(max_length=50, null=True, blank=True, verbose_name='製品コード')
    product_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='品名')
    product_name_halfwidth = models.CharField(max_length=100, null=True, blank=True, verbose_name='品名半角')
    quantity = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True, verbose_name='数量')
    raw_payload = models.JSONField(verbose_name='生データ（JSON）')
    parse_status = models.CharField(max_length=20, choices=PARSE_STATUS_CHOICES, default='PENDING', verbose_name='解析ステータス')
    error_message = models.CharField(max_length=200, null=True, blank=True, verbose_name='エラーメッセージ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'stg_order_raw'
        verbose_name = '受注取込ステージング（生データ）'
        verbose_name_plural = '受注取込ステージング（生データ）'
        indexes = [
            models.Index(fields=['customer_code']),
            models.Index(fields=['parse_status']),
        ]

    def __str__(self):
        return f"{self.customer_code} - {self.source_file} (Row {self.source_row_no})"


class StgOrderDaily(models.Model):
    """受注取込ステージング（日別正規化）"""
    ORDER_TYPE_CHOICES = [
        ('FIRM', '確定'),
        ('FORECAST', '内示'),
    ]

    id = models.BigAutoField(primary_key=True)
    raw = models.ForeignKey(StgOrderRaw, on_delete=models.CASCADE, verbose_name='生データ')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='得意先')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, verbose_name='受注タイプ')
    version_no = models.CharField(max_length=20, default='v1', verbose_name='版番号')
    product_code = models.CharField(max_length=50, verbose_name='製品コード')
    product_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='品名')
    product_name_halfwidth = models.CharField(max_length=100, null=True, blank=True, verbose_name='品名半角')
    due_date = models.DateField(verbose_name='納期')
    quantity = models.DecimalField(max_digits=14, decimal_places=3, verbose_name='数量')
    plant_code = models.CharField(max_length=20, null=True, blank=True, verbose_name='工場コード')
    ship_to_code = models.CharField(max_length=40, null=True, blank=True, verbose_name='納入先コード')
    source_system = models.CharField(max_length=50, null=True, blank=True, verbose_name='ソースシステム')
    source_file = models.CharField(max_length=200, null=True, blank=True, verbose_name='ソースファイル')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'stg_order_daily'
        verbose_name = '受注取込ステージング（日別）'
        verbose_name_plural = '受注取込ステージング（日別）'
        indexes = [
            models.Index(fields=['due_date']),
            models.Index(fields=['customer', 'due_date']),
        ]

    def __str__(self):
        return f"{self.product_code} - {self.due_date}: {self.quantity}"


class LineDemand(models.Model):
    """ライン別の需要展開（内示/確定 + 計画/実績）。"""

    id = models.BigAutoField(primary_key=True)
    line = models.ForeignKey(Line, on_delete=models.CASCADE, verbose_name='ライン')
    routing_step = models.ForeignKey(
        RoutingStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='ルーティング工程'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='製品'
    )
    product_code = models.CharField(max_length=50, verbose_name='製品コード')
    plan_date = models.DateField(verbose_name='必要日')
    lead_time_days = models.IntegerField(default=0, verbose_name='リードタイム(日)')

    forecast_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='内示数量')
    firm_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='確定数量')
    plan_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='計画数')
    actual_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='実績数')
    plan_progress = models.DecimalField(max_digits=9, decimal_places=3, default=0, verbose_name='計画進度')
    actual_progress = models.DecimalField(max_digits=9, decimal_places=3, default=0, verbose_name='実績進度')

    order_numbers = models.CharField(
        max_length=500,
        default='',
        blank=True,
        verbose_name='展開元受注番号'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_line_demand'
        verbose_name = 'ライン需要展開'
        verbose_name_plural = 'ライン需要展開'
        unique_together = [['line', 'product_code', 'plan_date']]
        indexes = [
            models.Index(fields=['line', 'plan_date']),
            models.Index(fields=['product_code']),
        ]

    def __str__(self):
        return f"{self.line.line_code if self.line_id else ''} {self.product_code} {self.plan_date}"
