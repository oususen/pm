from django.conf import settings
from django.db import models


class ConsumableSupplier(models.Model):
    """消耗品購入先マスタ（生産系の m_supplier とは別管理）"""
    name = models.CharField(max_length=255, unique=True, verbose_name='購入先名')
    contact_person = models.CharField(max_length=100, blank=True, default='', verbose_name='担当者')
    phone = models.CharField(max_length=50, blank=True, default='', verbose_name='電話番号')
    email = models.EmailField(blank=True, default='', verbose_name='メールアドレス')
    address = models.TextField(blank=True, default='', verbose_name='住所')
    note = models.TextField(blank=True, default='', verbose_name='備考')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_consumable_supplier'
        verbose_name = '消耗品購入先'
        verbose_name_plural = '消耗品購入先'
        ordering = ['name']

    def __str__(self):
        return self.name


class Consumable(models.Model):
    """消耗品マスタ（在庫数を保持）"""
    code = models.CharField(max_length=50, unique=True, verbose_name='コード')
    order_code = models.CharField(max_length=50, blank=True, default='', verbose_name='発注コード')
    name = models.CharField(max_length=255, verbose_name='品名')
    category = models.CharField(max_length=100, blank=True, default='', verbose_name='カテゴリ')
    unit = models.CharField(max_length=20, blank=True, default='', verbose_name='単位')
    storage_location = models.CharField(max_length=100, blank=True, default='', verbose_name='保管場所')
    stock_quantity = models.IntegerField(default=0, verbose_name='在庫数')
    safety_stock = models.IntegerField(default=0, verbose_name='安全在庫')
    order_unit = models.PositiveIntegerField(default=1, verbose_name='発注単位')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='単価')
    supplier = models.ForeignKey(
        ConsumableSupplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consumables',
        verbose_name='購入先',
    )
    image = models.ImageField(upload_to='consumables/images/', blank=True, default='', verbose_name='画像')
    note = models.TextField(blank=True, default='', verbose_name='備考')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_consumable'
        verbose_name = '消耗品'
        verbose_name_plural = '消耗品'
        ordering = ['code']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f'{self.code} - {self.name}'


class OrgSnapshotMixin(models.Model):
    """作業者・依頼者の組織名を記録時点で保存する（組織変更後も当時の部署で集計するため）"""
    division_name = models.CharField(max_length=100, blank=True, default='', verbose_name='事業部')
    group_name = models.CharField(max_length=100, blank=True, default='', verbose_name='係')
    team_name = models.CharField(max_length=100, blank=True, default='', verbose_name='班')
    unit_name = models.CharField(max_length=100, blank=True, default='', verbose_name='グループ')

    class Meta:
        abstract = True


class ConsumableRequest(OrgSnapshotMixin):
    """注文依頼"""
    STATUS_REQUESTED = 'requested'
    STATUS_PREPARING = 'preparing'
    STATUS_ORDERED = 'ordered'
    STATUS_RECEIVED = 'received'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_REQUESTED, '依頼中'),
        (STATUS_PREPARING, '発注準備'),
        (STATUS_ORDERED, '発注済'),
        (STATUS_RECEIVED, '入庫済'),
        (STATUS_REJECTED, '却下'),
        (STATUS_CANCELLED, 'キャンセル'),
    ]
    # 未完了（在庫計上前）の状態。自動依頼の重複判定・注文状態の導出に使う
    OPEN_STATUSES = (STATUS_REQUESTED, STATUS_PREPARING, STATUS_ORDERED)

    TYPE_CHOICES = [
        ('manual', '手動'),
        ('auto', '自動'),
    ]
    DEADLINE_CHOICES = [
        ('最短', '最短'),
        ('通常', '通常'),
        ('余裕あり', '余裕あり'),
    ]

    consumable = models.ForeignKey(
        Consumable, on_delete=models.PROTECT, related_name='requests', verbose_name='消耗品'
    )
    quantity = models.PositiveIntegerField(verbose_name='数量')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='単価')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='金額')
    deadline = models.CharField(max_length=20, choices=DEADLINE_CHOICES, default='通常', verbose_name='納期')
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consumable_requests',
        verbose_name='依頼者',
    )
    requester_name = models.CharField(max_length=100, blank=True, default='', verbose_name='依頼者名')
    request_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='manual', verbose_name='依頼種別')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_REQUESTED, verbose_name='ステータス')
    note = models.TextField(blank=True, default='', verbose_name='備考')
    requested_at = models.DateTimeField(verbose_name='依頼日時')
    ordered_at = models.DateTimeField(null=True, blank=True, verbose_name='発注日時')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完了日時')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='登録者',
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_consumable_request'
        verbose_name = '消耗品注文依頼'
        verbose_name_plural = '消耗品注文依頼'
        ordering = ['-requested_at', '-id']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['requested_at']),
        ]


class ConsumableDispatchOrder(models.Model):
    """注文書（購入先単位）。確認・承認は accounts.ApprovalRequest で管理する"""
    STATUS_UNSENT = 'unsent'
    STATUS_SENT = 'sent'
    STATUS_RECEIVED = 'received'
    STATUS_CHOICES = [
        (STATUS_UNSENT, '未送信'),
        (STATUS_SENT, '送信済'),
        (STATUS_RECEIVED, '入庫済'),
    ]

    order_number = models.CharField(max_length=50, unique=True, verbose_name='注文書番号')
    business_date = models.DateField(verbose_name='業務日')  # 日替わり8時ルールで判定した作成日
    daily_count = models.PositiveIntegerField(default=1, verbose_name='同一購入先の当日回数')
    supplier = models.ForeignKey(
        ConsumableSupplier, on_delete=models.PROTECT, related_name='dispatch_orders', verbose_name='購入先'
    )
    supplier_name = models.CharField(max_length=255, verbose_name='購入先名')
    total_items = models.PositiveIntegerField(default=0, verbose_name='明細数')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='合計金額')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_UNSENT, verbose_name='ステータス')
    approval_request = models.OneToOneField(
        'accounts.ApprovalRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consumable_dispatch_order',
        verbose_name='承認申請',
    )
    pdf_file = models.FileField(upload_to='consumables/purchase_orders/', blank=True, default='', verbose_name='PDF')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='送信日時')
    sent_email = models.CharField(max_length=255, blank=True, default='', verbose_name='送信先')
    received_at = models.DateTimeField(null=True, blank=True, verbose_name='入庫日時')
    note = models.TextField(blank=True, default='', verbose_name='備考')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='作成者',
    )
    created_at = models.DateTimeField(verbose_name='作成日時')

    class Meta:
        db_table = 't_consumable_dispatch_order'
        verbose_name = '消耗品注文書'
        verbose_name_plural = '消耗品注文書'
        ordering = ['-created_at', '-id']


class ConsumableDispatchOrderItem(models.Model):
    """注文書明細（作成時点の値を保存）"""
    dispatch_order = models.ForeignKey(
        ConsumableDispatchOrder, on_delete=models.CASCADE, related_name='items', verbose_name='注文書'
    )
    consumable = models.ForeignKey(
        Consumable, on_delete=models.PROTECT, related_name='dispatch_items', verbose_name='消耗品'
    )
    request = models.ForeignKey(
        ConsumableRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispatch_items',
        verbose_name='元の依頼',
    )
    code = models.CharField(max_length=50, verbose_name='コード')
    order_code = models.CharField(max_length=50, blank=True, default='', verbose_name='発注コード')
    name = models.CharField(max_length=255, verbose_name='品名')
    quantity = models.PositiveIntegerField(verbose_name='数量')
    unit = models.CharField(max_length=20, blank=True, default='', verbose_name='単位')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='単価')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='金額')
    deadline = models.CharField(max_length=20, blank=True, default='', verbose_name='納期')
    note = models.TextField(blank=True, default='', verbose_name='備考')

    class Meta:
        db_table = 't_consumable_dispatch_order_item'
        verbose_name = '消耗品注文書明細'
        verbose_name_plural = '消耗品注文書明細'
        ordering = ['id']


class ConsumableStockMovement(OrgSnapshotMixin):
    """入出庫履歴（入庫・出庫を1テーブルで管理）"""
    TYPE_INBOUND = 'inbound'
    TYPE_OUTBOUND = 'outbound'
    TYPE_CHOICES = [
        (TYPE_INBOUND, '入庫'),
        (TYPE_OUTBOUND, '出庫'),
    ]
    INBOUND_MANUAL = 'manual'
    INBOUND_DISPATCH = 'dispatch'
    INBOUND_TYPE_CHOICES = [
        (INBOUND_MANUAL, '手動'),
        (INBOUND_DISPATCH, '発注分'),
    ]

    consumable = models.ForeignKey(
        Consumable, on_delete=models.PROTECT, related_name='movements', verbose_name='消耗品'
    )
    movement_type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name='区分')
    inbound_type = models.CharField(
        max_length=10, choices=INBOUND_TYPE_CHOICES, blank=True, default='', verbose_name='入庫種別'
    )
    request = models.ForeignKey(
        ConsumableRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movements',
        verbose_name='対象の依頼',
    )
    quantity = models.PositiveIntegerField(verbose_name='数量')
    stock_after = models.IntegerField(verbose_name='処理後在庫')
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consumable_movements',
        verbose_name='作業者',
    )
    worker_name = models.CharField(max_length=100, blank=True, default='', verbose_name='作業者名')
    usage_line = models.CharField(max_length=100, blank=True, default='', verbose_name='使用ライン')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='単価')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='金額')
    note = models.TextField(blank=True, default='', verbose_name='備考')
    moved_at = models.DateTimeField(verbose_name='処理日時')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='登録者',
    )

    class Meta:
        db_table = 't_consumable_stock_movement'
        verbose_name = '消耗品入出庫履歴'
        verbose_name_plural = '消耗品入出庫履歴'
        ordering = ['-moved_at', '-id']
        indexes = [
            models.Index(fields=['movement_type', 'moved_at']),
            models.Index(fields=['consumable', 'moved_at']),
        ]
