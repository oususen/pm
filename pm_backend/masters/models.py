from django.db import models


class Product(models.Model):
    """製品マスタ"""
    CATEGORY_CHOICES = [
        ('UNKNOWN', '未定'),
        ('ASSEMBLY', '組立品'),
        ('SINGLE', '単品'),
        ('MATERIAL', '材料'),
        ('PURCHASED', '購入品'),
    ]

    id = models.BigAutoField(primary_key=True)
    product_code = models.CharField(max_length=30, unique=True, verbose_name='品番コード')
    product_name = models.CharField(max_length=100, verbose_name='品名')
    product_name_halfwidth = models.CharField(max_length=100, null=True, blank=True, verbose_name='品名半角')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='カテゴリ')
    unit = models.CharField(max_length=10, default='個', verbose_name='単位')
    standard_lt_days = models.IntegerField(null=True, blank=True, verbose_name='標準LT(日)')
    self_lt_days = models.IntegerField(null=True, blank=True, verbose_name='自工程LT(日)')
    is_final_product = models.BooleanField(default=False, verbose_name='最終製品')
    is_phantom = models.BooleanField(default=False, verbose_name='見なし組立')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_product'
        verbose_name = '製品'
        verbose_name_plural = '製品'

    def __str__(self):
        return f"{self.product_code} - {self.product_name}"


class Customer(models.Model):
    """得意先マスタ"""
    id = models.BigAutoField(primary_key=True)
    customer_code = models.CharField(max_length=20, unique=True, verbose_name='得意先コード')
    customer_name = models.CharField(max_length=100, verbose_name='得意先名')
    short_name = models.CharField(max_length=40, null=True, blank=True, verbose_name='略称')
    calendar = models.ForeignKey('Calendar', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='カレンダ')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_customer'
        verbose_name = '得意先'
        verbose_name_plural = '得意先'

    def __str__(self):
        return f"{self.customer_code} - {self.customer_name}"


class Process(models.Model):
    """工程マスタ"""
    id = models.BigAutoField(primary_key=True)
    process_code = models.CharField(max_length=20, unique=True, verbose_name='工程コード')
    process_name = models.CharField(max_length=50, verbose_name='工程名')
    line = models.ForeignKey('Line', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='ライン')
    is_outsource = models.BooleanField(default=False, verbose_name='外注工程')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_process'
        verbose_name = '工程'
        verbose_name_plural = '工程'

    def __str__(self):
        return f"{self.process_code} - {self.process_name}"


class Line(models.Model):
    """ラインマスタ"""
    id = models.BigAutoField(primary_key=True)
    line_code = models.CharField(max_length=20, unique=True, verbose_name='ラインコード')
    line_name = models.CharField(max_length=50, verbose_name='ライン名')
    lead_time_days = models.IntegerField(null=True, blank=True, default=0, verbose_name='リードタイム（日）')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_line'
        verbose_name = 'ライン'
        verbose_name_plural = 'ライン'

    def __str__(self):
        return f"{self.line_code} - {self.line_name}"


class Supplier(models.Model):
    """仕入先マスタ"""
    id = models.BigAutoField(primary_key=True)
    supplier_code = models.CharField(max_length=20, unique=True, verbose_name='仕入先コード')
    supplier_name = models.CharField(max_length=100, verbose_name='仕入先名')

    class Meta:
        db_table = 'm_supplier'
        verbose_name = '仕入先'
        verbose_name_plural = '仕入先'

    def __str__(self):
        return f"{self.supplier_code} - {self.supplier_name}"


class Calendar(models.Model):
    """カレンダマスタ"""
    id = models.BigAutoField(primary_key=True)
    calendar_code = models.CharField(max_length=20, unique=True, verbose_name='カレンダコード')
    calendar_name = models.CharField(max_length=50, verbose_name='カレンダ名')
    description = models.TextField(null=True, blank=True, verbose_name='説明')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_calendar'
        verbose_name = 'カレンダ'
        verbose_name_plural = 'カレンダ'

    def __str__(self):
        return f"{self.calendar_code} - {self.calendar_name}"


class CalendarDay(models.Model):
    """カレンダ日マスタ"""
    id = models.BigAutoField(primary_key=True)
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE, verbose_name='カレンダ')
    target_date = models.DateField(verbose_name='対象日')
    is_working_day = models.BooleanField(verbose_name='稼働日')
    work_minutes = models.IntegerField(null=True, blank=True, verbose_name='稼働分')
    note = models.CharField(max_length=100, null=True, blank=True, verbose_name='備考')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_calendar_day'
        verbose_name = 'カレンダ日'
        verbose_name_plural = 'カレンダ日'
        unique_together = [['calendar', 'target_date']]

    def __str__(self):
        return f"{self.calendar.calendar_code} - {self.target_date}"


class BOM(models.Model):
    """BOMヘッダ"""
    id = models.BigAutoField(primary_key=True)
    parent_product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='親製品')
    version = models.CharField(max_length=20, default='v1', verbose_name='版')
    valid_from = models.DateField(verbose_name='有効開始日')
    valid_to = models.DateField(null=True, blank=True, verbose_name='有効終了日')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_bom'
        verbose_name = 'BOM'
        verbose_name_plural = 'BOM'
        unique_together = [['parent_product', 'version', 'valid_from']]

    def __str__(self):
        return f"{self.parent_product.product_code} - {self.version}"


class BOMItem(models.Model):
    """BOM明細"""
    SOURCING_TYPE_CHOICES = [
        ('MAKE', '自社製造'),
        ('BUY', '購買'),
        ('SUBCON', '外注'),
    ]

    id = models.BigAutoField(primary_key=True)
    bom = models.ForeignKey(BOM, on_delete=models.CASCADE, related_name='items', verbose_name='BOM')
    child_product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='子製品')
    quantity = models.DecimalField(max_digits=12, decimal_places=3, verbose_name='数量')
    loss_rate = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True, verbose_name='ロス率')
    sourcing_type = models.CharField(max_length=20, choices=SOURCING_TYPE_CHOICES, default='MAKE', verbose_name='調達区分')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='仕入先')
    remark = models.CharField(max_length=200, null=True, blank=True, verbose_name='備考')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_bom_item'
        verbose_name = 'BOM明細'
        verbose_name_plural = 'BOM明細'

    def __str__(self):
        return f"{self.bom} -> {self.child_product.product_code} x {self.quantity}"


class Routing(models.Model):
    """ルーティングヘッダ"""
    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='製品')
    routing_code = models.CharField(max_length=30, verbose_name='ルーティングコード')
    description = models.TextField(null=True, blank=True, verbose_name='説明')
    is_default = models.BooleanField(default=False, verbose_name='既定')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_routing'
        verbose_name = 'ルーティング'
        verbose_name_plural = 'ルーティング'
        unique_together = [['product', 'routing_code']]

    def __str__(self):
        return f"{self.product.product_code} - {self.routing_code}"


class RoutingStep(models.Model):
    """ルーティング工程"""
    TIME_UNIT_CHOICES = [
        ('DAY', '日'),
        ('MINUTE', '分'),
    ]

    id = models.BigAutoField(primary_key=True)
    routing = models.ForeignKey(Routing, on_delete=models.CASCADE, related_name='steps', verbose_name='ルーティング')
    step_no = models.IntegerField(verbose_name='工程番号')
    process = models.ForeignKey(Process, on_delete=models.CASCADE, verbose_name='工程')
    line = models.ForeignKey(Line, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='ライン')
    time_unit = models.CharField(max_length=10, choices=TIME_UNIT_CHOICES, default='DAY', verbose_name='時間単位')
    lead_time_days = models.IntegerField(default=0, verbose_name='リードタイム(日)')
    start_offset_min = models.IntegerField(null=True, blank=True, verbose_name='開始オフセット(分)')
    duration_min = models.IntegerField(null=True, blank=True, verbose_name='所要時間(分)')
    remark = models.CharField(max_length=200, null=True, blank=True, verbose_name='備考')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_routing_step'
        verbose_name = 'ルーティング工程'
        verbose_name_plural = 'ルーティング工程'
        unique_together = [['routing', 'step_no']]
        ordering = ['routing', 'step_no']

    def __str__(self):
        return f"{self.routing} - Step {self.step_no}"
