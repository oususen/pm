from django.db import models


class Product(models.Model):
    """製品マスタ"""
    CATEGORY_CHOICES = [
        ('ASSEMBLY', '組立品'),
        ('SINGLE', '単品'),
        ('MATERIAL', '材料'),
        ('PURCHASED', '購入品'),
        ('UNKNOWN', '未定'),
    ]
    MANAGEMENT_UNIT_CHOICES = [
        ('DAY', '日単位管理'),
        ('MINUTE', '分単位管理'),
    ]

    id = models.BigAutoField(primary_key=True)
    product_code = models.CharField(max_length=30, unique=True, verbose_name='品番コード')
    product_name = models.CharField(max_length=100, verbose_name='品名')
    product_name_halfwidth = models.CharField(max_length=100, null=True, blank=True, verbose_name='品名半角')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, null=True, blank=True, verbose_name='カテゴリ')
    unit = models.CharField(max_length=10, default='個', verbose_name='単位')
    standard_lt_days = models.IntegerField(null=True, blank=True, verbose_name='標準LT(日)')
    image_url = models.CharField(max_length=255, null=True, blank=True, verbose_name='画像URL')
    line = models.ForeignKey('Line', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='ライン情報')
    process = models.ForeignKey('Process', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='工程情報')
    management_unit = models.CharField(
        max_length=10,
        choices=MANAGEMENT_UNIT_CHOICES,
        null=True,
        blank=True,
        verbose_name='管理区分'
    )
    self_lt_days = models.IntegerField(null=True, blank=True, verbose_name='自工程LT(日)')
    is_final_product = models.BooleanField(default=False, verbose_name='最終製品')
    is_line_final_product = models.BooleanField(
        default=False,
        verbose_name='ライン最終品',
        help_text='そのラインで最後に出力される製品（次のラインへ渡す中間品）'
    )
    is_phantom = models.BooleanField(default=False, verbose_name='見なし組立')
    is_virtual_set = models.BooleanField(
        default=False,
        verbose_name='仮想セット品番',
        help_text='連産品を表す仮想的なセット品番（この品番自体は在庫を持たない）'
    )
    order_lot_min = models.PositiveIntegerField(null=True, blank=True, verbose_name='最小発注数')
    order_lot_multiple = models.PositiveIntegerField(default=1, verbose_name='発注倍数')

    # 出荷指示書用フィールド
    model_name = models.CharField(max_length=50, null=True, blank=True, verbose_name='機種名')
    product_group = models.ForeignKey('ProductGroup', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='製品グループ')
    used_container = models.ForeignKey('ContainerCapacity', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='使用容器')
    capacity = models.IntegerField(null=True, blank=True, verbose_name='容器入り数')

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
    UNIT_CHOICES = [
        ('DAY', '日単位管理'),
        ('MINUTE', '分単位管理'),
    ]

    id = models.BigAutoField(primary_key=True)
    process_code = models.CharField(max_length=20, unique=True, verbose_name='工程コード')
    process_name = models.CharField(max_length=50, verbose_name='工程名')
    line = models.ForeignKey('Line', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='ライン')
    is_outsource = models.BooleanField(default=False, verbose_name='外注工程')
    management_unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default='MINUTE',
        verbose_name='管理単位',
        help_text='日単位管理（マクロ計画）または分単位管理（ミクロ実行）'
    )
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
    LINE_TYPE_CHOICES = [
        ('PROD', '生産'),
        ('PURCHASE', '購買'),
        ('OUTSOURCE', '外作'),
        ('OTHER', 'その他'),
    ]

    id = models.BigAutoField(primary_key=True)
    line_code = models.CharField(max_length=20, unique=True, verbose_name='ラインコード')
    line_name = models.CharField(max_length=50, verbose_name='ライン名')
    calendar = models.ForeignKey('Calendar', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='勤務カレンダ')
    lead_time_days = models.IntegerField(null=True, blank=True, default=0, verbose_name='リードタイム（日）')
    line_type = models.CharField(
        max_length=20,
        choices=LINE_TYPE_CHOICES,
        default='PROD',
        verbose_name='ライン種別'
    )
    is_active = models.BooleanField(default=True, verbose_name='有効')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_line'
        verbose_name = 'ライン'
        verbose_name_plural = 'ライン'
        ordering = ['line_code']

    def __str__(self):
        return f"{self.line_code} - {self.line_name}"


class Supplier(models.Model):
    """仕入先マスタ"""
    id = models.BigAutoField(primary_key=True)
    supplier_code = models.CharField(max_length=20, unique=True, verbose_name='仕入先コード')
    supplier_name = models.CharField(max_length=100, verbose_name='仕入先名')
    order_email = models.EmailField(blank=True, default='', verbose_name='送信メールアドレス')
    calendar = models.ForeignKey(
        'Calendar',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='仕入先専用カレンダー'
    )

    class Meta:
        db_table = 'm_supplier'
        verbose_name = '仕入先'
        verbose_name_plural = '仕入先'
        ordering = ['supplier_code']

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
        ordering = ['calendar_code']

    def __str__(self):
        return f"{self.calendar_code} - {self.calendar_name}"


class WorkPattern(models.Model):
    """勤務パターンマスタ"""
    id = models.BigAutoField(primary_key=True)
    pattern_code = models.CharField(max_length=20, unique=True, verbose_name='パターンコード')
    pattern_name = models.CharField(max_length=50, verbose_name='パターン名')
    start_time = models.TimeField(verbose_name='開始時刻')
    end_time = models.TimeField(null=True, blank=True, verbose_name='終了時刻')
    description = models.TextField(null=True, blank=True, verbose_name='説明')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_work_pattern'
        verbose_name = '勤務パターン'
        verbose_name_plural = '勤務パターン'

    def __str__(self):
        return f"{self.pattern_code} - {self.pattern_name}"


class BreakTime(models.Model):
    """休憩時間マスタ"""
    id = models.BigAutoField(primary_key=True)
    work_pattern = models.ForeignKey(WorkPattern, on_delete=models.CASCADE, related_name='break_times', verbose_name='勤務パターン')
    break_start = models.TimeField(verbose_name='休憩開始時刻')
    break_end = models.TimeField(verbose_name='休憩終了時刻')
    order = models.IntegerField(default=1, verbose_name='順序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_break_time'
        verbose_name = '休憩時間'
        verbose_name_plural = '休憩時間'
        ordering = ['work_pattern', 'order']

    def __str__(self):
        return f"{self.work_pattern.pattern_name} - 休憩{self.order}"


class CalendarDay(models.Model):
    """カレンダ日マスタ"""
    id = models.BigAutoField(primary_key=True)
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE, verbose_name='カレンダ')
    target_date = models.DateField(verbose_name='対象日')
    is_working_day = models.BooleanField(verbose_name='稼働日')
    work_minutes = models.IntegerField(null=True, blank=True, verbose_name='稼働分')
    work_pattern = models.ForeignKey(WorkPattern, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='勤務パターン')
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
    is_coproduct = models.BooleanField(
        default=False,
        verbose_name='連産品BOM',
        help_text='1つの工程で複数の製品が同時に生産されるBOM（親製品は仮想セット品番）'
    )
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
    process = models.ForeignKey(Process, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='工程')
    line = models.ForeignKey(Line, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='ライン')
    TIME_UNIT_CHOICES = [
        ('DAY', '日'),
        ('MINUTE', '分'),
    ]
    time_unit = models.CharField(max_length=10, choices=TIME_UNIT_CHOICES, default='MINUTE', verbose_name='時間単位')
    lead_time_days = models.IntegerField(default=0, verbose_name='リードタイム(日)')
    duration_min = models.IntegerField(null=True, blank=True, verbose_name='所要時間(分)')
    is_coproduct_driver = models.BooleanField(default=False, verbose_name='連産品代表品')
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
        code = None
        if self.product_id:
            try:
                code = self.product.product_code
            except Product.DoesNotExist:
                code = f"(missing product id={self.product_id})"
        return f"{code or ''} - {self.routing_code}"


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
    output_product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='加工後品目')
    hierarchy_path = models.CharField(max_length=100, default='', blank=True, verbose_name='工程階層パス')
    hierarchy_depth = models.IntegerField(default=0, verbose_name='工程階層深さ')
    time_unit = models.CharField(max_length=10, choices=TIME_UNIT_CHOICES, default='DAY', verbose_name='時間単位')
    lead_time_days = models.IntegerField(default=0, verbose_name='リードタイム(日)')
    start_offset_min = models.IntegerField(null=True, blank=True, verbose_name='開始オフセット(分)')
    duration_min = models.IntegerField(null=True, blank=True, verbose_name='所要時間(分)')
    parallel_count = models.IntegerField(default=1, verbose_name='並列数')
    parallel_group = models.IntegerField(default=1, verbose_name='並列グループ')
    remark = models.CharField(max_length=200, null=True, blank=True, verbose_name='備考')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_routing_step'
        verbose_name = 'ルーティング工程'
        verbose_name_plural = 'ルーティング工程'
        unique_together = [['routing', 'step_no', 'parallel_group']]
        ordering = ['routing', 'step_no', 'parallel_group']

    def __str__(self):
        product_code = ''
        routing_code = ''
        if self.routing_id:
            try:
                routing = self.routing
                if routing.product_id:
                    product_code = routing.product.product_code
                routing_code = routing.routing_code or ''
            except Routing.DoesNotExist:
                product_code = f"(missing Routing id={self.routing_id})"

        output_code = ''
        if self.output_product_id:
            try:
                output_code = self.output_product.product_code
            except Product.DoesNotExist:
                output_code = f"(missing Product id={self.output_product_id})"

        label_mid = output_code or routing_code
        if label_mid and product_code:
            return f"{product_code} - {label_mid} - Step {self.step_no}"
        if product_code:
            return f"{product_code} - Step {self.step_no}"
        return f"Step {self.step_no}"


class RoutingStepMaterial(models.Model):
    """工程別部品消費"""
    CONSUME_TIMING_CHOICES = [
        ('START', '工程開始'),
        ('END', '工程完了'),
    ]

    id = models.BigAutoField(primary_key=True)
    routing_step = models.ForeignKey(RoutingStep, on_delete=models.CASCADE, related_name='materials', verbose_name='工程')
    component = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='routing_step_materials', verbose_name='部品')
    quantity = models.DecimalField(max_digits=12, decimal_places=3, verbose_name='数量')
    consume_timing = models.CharField(max_length=10, choices=CONSUME_TIMING_CHOICES, default='START', verbose_name='消費タイミング')
    remark = models.CharField(max_length=200, null=True, blank=True, verbose_name='備考')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_routing_step_material'
        verbose_name = '工程別部品消費'
        verbose_name_plural = '工程別部品消費'
        unique_together = [['routing_step', 'component']]

    def __str__(self):
        routing_label = ''
        if self.routing_step_id:
            try:
                routing_label = str(self.routing_step)
            except RoutingStep.DoesNotExist:
                routing_label = f"(missing RoutingStep id={self.routing_step_id})"
        component_code = ''
        if self.component_id:
            try:
                component_code = self.component.product_code
            except Product.DoesNotExist:
                component_code = f"(missing Product id={self.component_id})"
        return f"{routing_label} uses {component_code} x {self.quantity}"


class ProcessCycleTime(models.Model):
    """部品×工程の標準サイクル時間（多品種対応）"""
    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='製品'
    )
    process = models.ForeignKey(
        Process,
        on_delete=models.CASCADE,
        verbose_name='工程'
    )
    line = models.ForeignKey(
        Line,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='ライン'
    )
    cycle_time_min = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='標準サイクル時間(分)',
        help_text='1個あたりの標準加工時間（分）'
    )
    setup_time_min = models.IntegerField(
        default=0,
        verbose_name='段取り時間(分)',
        help_text='ロット開始時の準備時間（分）'
    )
    lot_size = models.IntegerField(
        default=1,
        verbose_name='標準ロットサイズ',
        help_text='標準的な生産ロットサイズ'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='有効'
    )
    valid_from = models.DateField(
        null=True,
        blank=True,
        verbose_name='有効開始日'
    )
    valid_to = models.DateField(
        null=True,
        blank=True,
        verbose_name='有効終了日'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_process_cycle_time'
        verbose_name = '工程別サイクル時間'
        verbose_name_plural = '工程別サイクル時間'
        unique_together = [['product', 'process', 'line', 'valid_from']]
        indexes = [
            models.Index(fields=['product', 'process']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.product.product_code} @ {self.process.process_code} ({self.cycle_time_min}分)"


class ProductGroup(models.Model):
    """製品グループマスタ"""
    id = models.BigAutoField(primary_key=True)
    group_code = models.CharField(max_length=50, unique=True, verbose_name='グループコード')
    group_name = models.CharField(max_length=100, verbose_name='グループ名')
    description = models.TextField(null=True, blank=True, verbose_name='説明')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_product_group'
        verbose_name = '製品グループ'
        verbose_name_plural = '製品グループ'

    def __str__(self):
        return f"{self.group_code} - {self.group_name}"


class ContainerCapacity(models.Model):
    """容器仕様マスタ"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, verbose_name='容器名')
    container_code = models.CharField(max_length=20, null=True, blank=True, verbose_name='容器コード')
    width = models.IntegerField(null=True, blank=True, verbose_name='幅')
    depth = models.IntegerField(null=True, blank=True, verbose_name='奥行')
    height = models.IntegerField(null=True, blank=True, verbose_name='高さ')
    max_weight = models.IntegerField(null=True, blank=True, default=0, verbose_name='最大重量')
    can_mix = models.BooleanField(null=True, blank=True, default=True, verbose_name='混載可能')
    stackable = models.BooleanField(null=True, blank=True, default=True, verbose_name='積み重ね可能')
    max_stack = models.IntegerField(null=True, blank=True, default=1, verbose_name='最大積み重ね段数')
    capacity = models.IntegerField(null=True, blank=True, verbose_name='入り数', help_text='容器に入る製品の個数')

    class Meta:
        db_table = 'm_container_capacity'
        verbose_name = '容器仕様'
        verbose_name_plural = '容器仕様'
        ordering = ['name']

    def __str__(self):
        if self.capacity:
            return f"{self.name} (入り数: {self.capacity})"
        return f"{self.name}"


class Contact(models.Model):
    """連絡先マスタ"""
    id = models.BigAutoField(primary_key=True)
    contact_type = models.CharField(max_length=50, verbose_name='連絡先種別')
    company_name = models.CharField(max_length=255, verbose_name='会社名')
    department = models.CharField(max_length=255, null=True, blank=True, verbose_name='部署名')
    contact_person = models.CharField(max_length=255, null=True, blank=True, verbose_name='担当者名')
    email = models.EmailField(verbose_name='メールアドレス')
    phone = models.CharField(max_length=50, null=True, blank=True, verbose_name='電話番号')
    is_active = models.BooleanField(default=True, verbose_name='有効フラグ')
    display_order = models.IntegerField(default=0, verbose_name='表示順')
    notes = models.TextField(null=True, blank=True, verbose_name='備考')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'm_contacts'
        verbose_name = '連絡先'
        verbose_name_plural = '連絡先'
        ordering = ['display_order', 'id']

    def __str__(self):
        return f"{self.company_name} - {self.contact_person or '担当者未設定'}"
