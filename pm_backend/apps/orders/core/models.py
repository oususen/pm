from datetime import datetime

from django.conf import settings
from django.db import models
from masters.models import Customer, Product


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
    ORDER_TYPE_CHOICES = [
        ('FIRM', '確定'),
        ('FORECAST', '内示'),
    ]

    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='lines', verbose_name='受注')
    line_no = models.IntegerField(verbose_name='行番号')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='製品')
    product_code = models.CharField(max_length=50, verbose_name='製品コード')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, null=True, blank=True, verbose_name='受注タイプ')
    customer_order_no = models.CharField(max_length=50, null=True, blank=True, verbose_name='顧客発注番号')  # リーデンの発注番号 or ティエラの注文番号
    quantity = models.DecimalField(max_digits=14, decimal_places=3, verbose_name='数量')
    actual_shipment_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='出荷実績数')
    due_date = models.DateField(verbose_name='納期')
    plant_code = models.CharField(max_length=20, null=True, blank=True, verbose_name='工場コード')
    ship_to_code = models.CharField(max_length=40, null=True, blank=True, verbose_name='納入先コード')
    remark = models.CharField(max_length=200, null=True, blank=True, verbose_name='備考')
    is_expanded = models.BooleanField(default=False, verbose_name='展開済み')
    expanded_at = models.DateTimeField(null=True, blank=True, verbose_name='展開日時')
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
            models.Index(fields=['order_type', 'is_expanded']),
        ]

    def __str__(self):
        return f"{self.order.order_no} - Line {self.line_no}: {self.product_code}"


class KubotaSakaiDueAdjustment(models.Model):
    """クボタ堺向け納期調整（BACKLOG型）
    1行 = 品番 + 納入場所 + 注番 + 日付 の組み合わせ。
    取り込みで ORDER_LINE から demand_qty をスナップし、
    画面で delivery_qty を入力、remaining_qty を累積計算する。
    """

    ORDER_TYPE_CHOICES = [
        ('FIRM', '確定'),
        ('FORECAST', '内示'),
    ]

    id = models.BigAutoField(primary_key=True)
    product_code = models.CharField(max_length=50, verbose_name='品番')
    ship_to_code = models.CharField(max_length=40, null=True, blank=True, verbose_name='納入場所コード')
    source_order_no = models.CharField(max_length=50, null=True, blank=True, verbose_name='注番')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default='FORECAST', verbose_name='受注タイプ')
    due_date = models.DateField(verbose_name='日付')
    demand_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='受注数')
    delivery_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='納入数')
    remaining_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='残量')

    # 参照用（取り込み元）
    order_line = models.ForeignKey(
        OrderLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kubota_sakai_due_adjustments',
        verbose_name='受注明細',
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kubota_sakai_due_adj_updated',
        verbose_name='更新者',
    )
    updated_at = models.DateTimeField(null=True, blank=True, verbose_name='更新日時')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        db_table = 't_kubota_sakai_due_adjustment'
        verbose_name = 'クボタ堺納期調整'
        verbose_name_plural = 'クボタ堺納期調整'
        unique_together = [['product_code', 'ship_to_code', 'source_order_no', 'due_date']]
        indexes = [
            models.Index(fields=['due_date']),
            models.Index(fields=['product_code', 'ship_to_code'], name='kbt_saki_due_prod_ship_idx'),
        ]
        ordering = ['product_code', 'ship_to_code', 'source_order_no', 'due_date']

    def __str__(self):
        return f"{self.product_code} {self.ship_to_code} {self.source_order_no or '内示'} {self.due_date} D:{self.demand_qty} L:{self.delivery_qty}"


class KubotaSakaiTripAssignment(models.Model):
    """クボタ堺向け便割付
    納期調整(DueAdjustment)の delivery_qty を便に割り付ける。
    """

    id = models.BigAutoField(primary_key=True)
    due_adjustment = models.ForeignKey(
        KubotaSakaiDueAdjustment,
        on_delete=models.CASCADE,
        related_name='trip_assignments',
        verbose_name='納期調整',
    )
    truck = models.ForeignKey(
        'masters.KubotaSakaiTruck',
        on_delete=models.CASCADE,
        related_name='kubota_sakai_trip_assignments',
        verbose_name='便',
    )
    container = models.ForeignKey(
        'masters.ContainerCapacity',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kubota_sakai_trip_assignments',
        verbose_name='容器',
    )
    departure_date = models.DateField(verbose_name='出発日')
    qty = models.DecimalField(max_digits=14, decimal_places=3, verbose_name='割付数量')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kubota_sakai_trip_assignments',
        verbose_name='作成者',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_kubota_sakai_trip_assignment'
        verbose_name = 'クボタ堺便割付'
        verbose_name_plural = 'クボタ堺便割付'
        indexes = [
            models.Index(fields=['departure_date', 'truck']),
            models.Index(fields=['due_adjustment']),
        ]
        ordering = ['departure_date', 'truck_id', 'due_adjustment_id', 'id']

    def __str__(self):
        return f"{self.departure_date} truck={self.truck_id} adj={self.due_adjustment_id} qty={self.qty}"


class KubotaSakaiPseudoTruckProduct(models.Model):
    """擬似便対象製品マスタ。製品+納入場ごとに自動振分先の擬似便(A/P)を紐付ける。"""

    id = models.BigAutoField(primary_key=True)
    product_code = models.CharField(max_length=50, verbose_name='製品コード')
    ship_to_code = models.CharField(max_length=40, default='', blank=True, verbose_name='納入場コード')
    truck = models.ForeignKey(
        'masters.KubotaSakaiTruck',
        on_delete=models.CASCADE,
        related_name='pseudo_truck_products',
        verbose_name='擬似便',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_kubota_sakai_pseudo_truck_product'
        verbose_name = '擬似便対象製品'
        verbose_name_plural = '擬似便対象製品'
        unique_together = [('product_code', 'ship_to_code', 'truck')]
        ordering = ['product_code', 'ship_to_code', 'truck_id']

    def __str__(self):
        return f"{self.product_code}({self.ship_to_code}) → truck={self.truck_id}"


class ShippingRun(models.Model):
    """共通出荷業務ヘッダ。顧客/納入場単位で出荷実行を束ねる。"""

    STATUS_CHOICES = [
        ('OPEN', '進行中'),
        ('CLOSED', '完了'),
    ]

    id = models.BigAutoField(primary_key=True)
    business_type = models.CharField(max_length=40, verbose_name='業務種別')
    customer_code = models.CharField(max_length=20, verbose_name='得意先コード')
    ship_to_code = models.CharField(max_length=40, null=True, blank=True, verbose_name='納入場コード')
    target_date_from = models.DateField(verbose_name='対象開始日')
    target_date_to = models.DateField(verbose_name='対象終了日')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN', verbose_name='ステータス')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shipping_runs',
        verbose_name='作成者',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_shipping_run'
        verbose_name = '出荷業務'
        verbose_name_plural = '出荷業務'
        unique_together = [['business_type', 'customer_code', 'ship_to_code', 'target_date_from', 'target_date_to']]
        indexes = [
            models.Index(fields=['business_type', 'customer_code', 'ship_to_code']),
            models.Index(fields=['target_date_from', 'target_date_to']),
        ]

    def __str__(self):
        return f"{self.business_type}:{self.customer_code}:{self.ship_to_code or '-'} {self.target_date_from}~{self.target_date_to}"


class ShippingTrip(models.Model):
    """共通便ヘッダ。trip_ref で顧客固有便ID（堺は TRUCK:{id}）を保持する。"""

    STATUS_CHOICES = [
        ('PLANNED', '計画'),
        ('LOADING', '積込中'),
        ('DEPARTED', '出発済'),
        ('CLOSED', '完了'),
    ]

    id = models.BigAutoField(primary_key=True)
    run = models.ForeignKey(
        ShippingRun,
        on_delete=models.CASCADE,
        related_name='trips',
        verbose_name='出荷業務',
    )
    business_type = models.CharField(max_length=40, verbose_name='業務種別')
    customer_code = models.CharField(max_length=20, verbose_name='得意先コード')
    ship_to_code = models.CharField(max_length=40, null=True, blank=True, verbose_name='納入場コード')
    departure_date = models.DateField(verbose_name='出発日')
    trip_ref = models.CharField(max_length=80, verbose_name='便参照キー')
    trip_code = models.CharField(max_length=80, null=True, blank=True, verbose_name='便コード')
    departure_time_plan = models.TimeField(null=True, blank=True, verbose_name='予定出発時刻')
    departure_time_actual = models.DateTimeField(null=True, blank=True, verbose_name='実出発時刻')
    loading_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shipping_trip_loading_by',
        verbose_name='積込担当者',
    )
    departed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shipping_trip_departed_by',
        verbose_name='出発担当者',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED', verbose_name='ステータス')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_shipping_trip'
        verbose_name = '出荷便'
        verbose_name_plural = '出荷便'
        unique_together = [['business_type', 'customer_code', 'ship_to_code', 'departure_date', 'trip_ref']]
        indexes = [
            models.Index(fields=['run']),
            models.Index(fields=['departure_date', 'status']),
        ]

    def __str__(self):
        return f"{self.departure_date} {self.business_type} {self.trip_ref}"


class ShippingTripAllocation(models.Model):
    """共通便割付。source_type/source_id で元明細を表現する。"""

    id = models.BigAutoField(primary_key=True)
    trip = models.ForeignKey(
        ShippingTrip,
        on_delete=models.CASCADE,
        related_name='allocations',
        verbose_name='出荷便',
    )
    source_type = models.CharField(max_length=40, verbose_name='元データ種別')
    source_id = models.BigIntegerField(verbose_name='元データID')
    product_code = models.CharField(max_length=50, verbose_name='品番')
    ship_to_code = models.CharField(max_length=40, null=True, blank=True, verbose_name='納入場コード')
    due_date = models.DateField(null=True, blank=True, verbose_name='納期')
    qty = models.DecimalField(max_digits=14, decimal_places=3, verbose_name='割付数量')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_shipping_trip_allocation'
        verbose_name = '出荷便割付'
        verbose_name_plural = '出荷便割付'
        unique_together = [['trip', 'source_type', 'source_id']]
        indexes = [
            models.Index(fields=['source_type', 'source_id']),
            models.Index(fields=['product_code']),
        ]

    def __str__(self):
        return f"trip={self.trip_id} {self.source_type}:{self.source_id} qty={self.qty}"


class ShippingTripNotice(models.Model):
    """便番号×出発日単位の事務所連絡メモ。"""

    NOTICE_TYPE_CHOICES = [
        ('NORMAL', '普通'),
        ('URGENT', '緊急'),
    ]

    id = models.BigAutoField(primary_key=True)
    business_type = models.CharField(max_length=40, verbose_name='業務種別')
    customer_code = models.CharField(max_length=20, verbose_name='得意先コード')
    departure_date = models.DateField(verbose_name='出発日')
    trip_ref = models.CharField(max_length=80, verbose_name='便参照キー')
    notice_type = models.CharField(max_length=20, choices=NOTICE_TYPE_CHOICES, default='NORMAL', verbose_name='連絡種別')
    notice_text = models.CharField(max_length=200, blank=True, default='', verbose_name='連絡メモ')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shipping_trip_notices',
        verbose_name='更新者',
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        db_table = 't_shipping_trip_notice'
        verbose_name = '出荷便連絡メモ'
        verbose_name_plural = '出荷便連絡メモ'
        unique_together = [['business_type', 'customer_code', 'departure_date', 'trip_ref']]
        indexes = [
            models.Index(fields=['business_type', 'customer_code', 'departure_date']),
            models.Index(fields=['departure_date', 'trip_ref']),
        ]

    def __str__(self):
        return f"{self.departure_date} {self.business_type} {self.trip_ref}"


class StgOrderRaw(models.Model):
    """受注取込ステージング（生データ） - 旧モデル、互換性のため残す"""
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


class StgOrderRawTiera(models.Model):
    """ティエラ受注取込ステージング（生データ）"""
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

    # ティエラ固有フィールド
    data_type = models.CharField(max_length=10, null=True, blank=True, verbose_name='データ区分')  # B17/Y55
    delivery_no = models.CharField(max_length=50, null=True, blank=True, verbose_name='送付No')
    order_document_no = models.CharField(max_length=50, null=True, blank=True, verbose_name='注文番号')  # 製品ごとの顧客発注番号
    product_code = models.CharField(max_length=50, null=True, blank=True, verbose_name='製品コード(図番)')
    due_date = models.DateField(null=True, blank=True, verbose_name='納期')
    quantity = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True, verbose_name='数量')
    product_name = models.CharField(max_length=200, null=True, blank=True, verbose_name='納品書用品名')
    product_name_kana = models.CharField(max_length=200, null=True, blank=True, verbose_name='納品書用品名カナ')
    c_table_no = models.CharField(max_length=50, null=True, blank=True, verbose_name='C表No/不良通知No')

    raw_payload = models.JSONField(verbose_name='生データ（JSON）')
    parse_status = models.CharField(max_length=20, choices=PARSE_STATUS_CHOICES, default='PENDING', verbose_name='解析ステータス')
    error_message = models.TextField(null=True, blank=True, verbose_name='エラーメッセージ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'stg_order_raw_tiera'
        verbose_name = 'ティエラ受注取込ステージング（生データ）'
        verbose_name_plural = 'ティエラ受注取込ステージング（生データ）'
        indexes = [
            models.Index(fields=['customer_code']),
            models.Index(fields=['parse_status']),
            models.Index(fields=['source_file']),
        ]

    def __str__(self):
        return f"{self.customer_code} - {self.source_file} (Row {self.source_row_no})"


class StgOrderRawRieden(models.Model):
    """リーデン受注取込ステージング（生データ）"""
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

    # リーデン固有フィールド
    order_no = models.CharField(max_length=50, null=True, blank=True, verbose_name='発注番号')  # 顧客の発注番号
    order_date = models.DateField(null=True, blank=True, verbose_name='発注日')
    order_code = models.CharField(max_length=10, null=True, blank=True, verbose_name='発注先コード')  # 509
    product_code = models.CharField(max_length=50, null=True, blank=True, verbose_name='製品コード')
    due_date = models.DateField(null=True, blank=True, verbose_name='納期')
    quantity = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True, verbose_name='数量')

    raw_payload = models.JSONField(verbose_name='生データ（JSON）')
    parse_status = models.CharField(max_length=20, choices=PARSE_STATUS_CHOICES, default='PENDING', verbose_name='解析ステータス')
    error_message = models.TextField(null=True, blank=True, verbose_name='エラーメッセージ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'stg_order_raw_rieden'
        verbose_name = 'リーデン受注取込ステージング（生データ）'
        verbose_name_plural = 'リーデン受注取込ステージング（生データ）'
        indexes = [
            models.Index(fields=['customer_code']),
            models.Index(fields=['parse_status']),
            models.Index(fields=['source_file']),
        ]

    def __str__(self):
        return f"{self.customer_code} - {self.source_file} (Row {self.source_row_no})"


class StgOrderRawKubota(models.Model):
    """クボタ受注取込ステージング（生データ）"""
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

    # クボタ固有フィールド
    data_no = models.CharField(max_length=10, null=True, blank=True, verbose_name='データNo')  # 4/27/36/45/47/49
    record_type = models.CharField(max_length=10, null=True, blank=True, verbose_name='レコード識別')  # V2/V3
    product_code = models.CharField(max_length=50, null=True, blank=True, verbose_name='品番')
    inspection_type = models.CharField(max_length=10, null=True, blank=True, verbose_name='検査区分')  # N, NS, TS, $ など
    product_name = models.CharField(max_length=200, null=True, blank=True, verbose_name='品名')

    # 内示用（36番） - 横展開データ
    start_month = models.CharField(max_length=10, null=True, blank=True, verbose_name='スタート月度')  # 例：2512
    date_headers = models.JSONField(null=True, blank=True, verbose_name='日付ヘッダー配列')  # ["51201", "51202", ...]
    quantities = models.JSONField(null=True, blank=True, verbose_name='数量配列')  # [72, 56, 64, ...]

    # 確定用（27/45/47/49番）
    delivery_date = models.DateField(null=True, blank=True, verbose_name='納入指示日')
    quantity = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True, verbose_name='納入指示数')
    order_no = models.CharField(max_length=50, null=True, blank=True, verbose_name='注番')

    raw_payload = models.JSONField(verbose_name='生データ（JSON）')
    parse_status = models.CharField(max_length=20, choices=PARSE_STATUS_CHOICES, default='PENDING', verbose_name='解析ステータス')
    error_message = models.TextField(null=True, blank=True, verbose_name='エラーメッセージ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'stg_order_raw_kubota'
        verbose_name = 'クボタ受注取込ステージング（生データ）'
        verbose_name_plural = 'クボタ受注取込ステージング（生データ）'
        indexes = [
            models.Index(fields=['customer_code']),
            models.Index(fields=['parse_status']),
            models.Index(fields=['source_file']),
            models.Index(fields=['product_code', 'inspection_type']),
        ]

    def __str__(self):
        return f"{self.customer_code} - {self.source_file} (Row {self.source_row_no})"


class StgOrderDaily(models.Model):
    """受注取込ステージング（日別正規化） - 統一フォーマット"""
    ORDER_TYPE_CHOICES = [
        ('FIRM', '確定'),
        ('FORECAST', '内示'),
    ]

    id = models.BigAutoField(primary_key=True)

    # 元データへの参照（どれか一つのみNULLでない）
    raw = models.ForeignKey(StgOrderRaw, on_delete=models.CASCADE, null=True, blank=True, verbose_name='生データ（旧・非推奨）')
    raw_tiera = models.ForeignKey(StgOrderRawTiera, on_delete=models.CASCADE, null=True, blank=True, verbose_name='ティエラ生データ')
    raw_rieden = models.ForeignKey(StgOrderRawRieden, on_delete=models.CASCADE, null=True, blank=True, verbose_name='リーデン生データ')
    raw_kubota = models.ForeignKey(StgOrderRawKubota, on_delete=models.CASCADE, null=True, blank=True, verbose_name='クボタ生データ')

    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='得意先')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, verbose_name='受注タイプ')
    version_no = models.CharField(max_length=20, default='v1', verbose_name='版番号')
    product_code = models.CharField(max_length=50, verbose_name='製品コード')
    product_name = models.CharField(max_length=200, null=True, blank=True, verbose_name='品名')
    product_name_halfwidth = models.CharField(max_length=200, null=True, blank=True, verbose_name='品名半角')
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
            models.Index(fields=['product_code']),
        ]

    def __str__(self):
        return f"{self.product_code} - {self.due_date}: {self.quantity}"


class KubotaSakaiImportConfig(models.Model):
    """クボタ堺 確定取り込み通知設定（シングルトン）"""
    notify_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='kubota_sakai_import_notify',
        verbose_name='通知先ユーザー',
    )

    class Meta:
        db_table = 'kubota_sakai_import_config'
        verbose_name = 'クボタ堺取り込み通知設定'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class FirstArticleNoticeLog(models.Model):
    """お久しぶり製品通知の送信済み記録。同一内容の重複通知を防止する。"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='得意先')
    product_code = models.CharField(max_length=50, verbose_name='製品コード')
    due_date = models.DateField(verbose_name='納期')
    quantity = models.DecimalField(max_digits=14, decimal_places=3, verbose_name='数量')
    notified_at = models.DateTimeField(auto_now_add=True, verbose_name='通知日時')

    class Meta:
        db_table = 't_first_article_notice_log'
        verbose_name = 'お久しぶり製品通知履歴'
        verbose_name_plural = 'お久しぶり製品通知履歴'
        unique_together = [['customer', 'product_code', 'due_date', 'quantity']]
        indexes = [
            models.Index(fields=['product_code', 'due_date']),
        ]

    def __str__(self):
        return f"{self.customer_id} / {self.product_code} / {self.due_date} / {self.quantity}"
