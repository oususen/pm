from django.conf import settings
from django.db import models

from masters.models import Line, Process, Product, Supplier


class PurchasePlanLockSetting(models.Model):
    lock_days = models.PositiveIntegerField(default=0, verbose_name='ロック日数')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='purchase_plan_lock_settings'
    )

    class Meta:
        db_table = 'purchase_plan_lock_setting'

    def __str__(self):
        return f'PurchasePlanLockSetting(lock_days={self.lock_days})'


class SupplierOrderPattern(models.Model):
    RECURRENCE_WEEKLY = 'WEEKLY'
    RECURRENCE_MONTHLY_DATE = 'MONTHLY_DATE'
    RECURRENCE_MONTHLY_NTH_DOW = 'MONTHLY_NTH_DOW'
    RECURRENCE_EVERY_BUSINESS_DAY = 'EVERY_BUSINESS_DAY'
    RECURRENCE_EVERY_N_BUSINESS_DAYS = 'EVERY_N_BUSINESS_DAYS'

    RECURRENCE_TYPE_CHOICES = [
        (RECURRENCE_WEEKLY, '毎週曜日'),
        (RECURRENCE_MONTHLY_DATE, '毎月日付'),
        (RECURRENCE_MONTHLY_NTH_DOW, '月の第N週の曜日'),
        (RECURRENCE_EVERY_BUSINESS_DAY, '毎営業日'),
        (RECURRENCE_EVERY_N_BUSINESS_DAYS, 'N営業日ごと'),
    ]

    pattern_code = models.CharField(max_length=30, unique=True, verbose_name='パターンコード')
    pattern_name = models.CharField(max_length=100, verbose_name='パターン名')
    recurrence_type = models.CharField(max_length=30, choices=RECURRENCE_TYPE_CHOICES, verbose_name='繰返し種別')
    days_of_week = models.CharField(max_length=20, blank=True, default='', verbose_name='曜日(0=月〜6=日, カンマ区切り)')
    nth_weeks = models.CharField(max_length=20, blank=True, default='', verbose_name='第N週(1〜5, カンマ区切り)')
    days_of_month = models.CharField(max_length=100, blank=True, default='', verbose_name='日付(1〜31, カンマ区切り)')
    interval_days = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name='間隔営業日数')
    start_date = models.DateField(null=True, blank=True, verbose_name='開始基準日')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    note = models.CharField(max_length=200, blank=True, default='', verbose_name='備考')

    class Meta:
        db_table = 'supplier_order_pattern'
        ordering = ['pattern_code']

    def __str__(self):
        return f'{self.pattern_code} - {self.pattern_name}'


class SupplierOrderSchedule(models.Model):
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name='order_schedules',
    )
    pattern = models.ForeignKey(
        SupplierOrderPattern,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='schedules',
        verbose_name='納入パターン',
    )
    start_date = models.DateField(null=True, blank=True, verbose_name='開始基準日')
    lead_time_days = models.PositiveIntegerField(default=0)
    is_enabled = models.BooleanField(default=True)
    note = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = 'supplier_order_schedule'
        indexes = [
            models.Index(fields=['supplier', 'is_enabled']),
        ]

    def __str__(self):
        return f'{self.supplier_id}:{self.pattern_id}'


class PurchaseOrderProposal(models.Model):
    STATUS_DRAFT = 'DRAFT'
    STATUS_SUBMITTED = 'SUBMITTED'
    STATUS_APPROVED_L2 = 'APPROVED_L2'
    STATUS_APPROVED_L3 = 'APPROVED_L3'
    STATUS_APPROVED = 'APPROVED'
    STATUS_SENT = 'SENT'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CANCELED = 'CANCELED'

    STATUS_CHOICES = [
        (STATUS_DRAFT, '作成中'),
        (STATUS_SUBMITTED, '業務員サイン済'),
        (STATUS_APPROVED_L2, '班長承認済'),
        (STATUS_APPROVED_L3, '係長承認済'),
        (STATUS_APPROVED, '最終承認済'),
        (STATUS_SENT, '購入先送信済'),
        (STATUS_REJECTED, '差戻'),
        (STATUS_CANCELED, 'キャンセル'),
    ]

    proposal_no = models.CharField(max_length=30, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='order_proposals')
    order_date = models.DateField()
    desired_delivery_date = models.DateField()
    next_delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='purchase_order_proposals_created',
    )
    note = models.TextField(blank=True, default='')
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'purchase_order_proposal'
        indexes = [
            models.Index(fields=['supplier', 'order_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.proposal_no


class PurchaseOrderProposalLine(models.Model):
    proposal = models.ForeignKey(
        PurchaseOrderProposal,
        on_delete=models.CASCADE,
        related_name='lines',
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='purchase_order_proposal_lines')
    line = models.ForeignKey(Line, on_delete=models.PROTECT, related_name='purchase_order_proposal_lines')
    shortage_date = models.DateField(null=True, blank=True)
    shortage_qty = models.IntegerField(null=True, blank=True)
    next_delivery_date = models.DateField(null=True, blank=True)
    order_qty = models.IntegerField(default=0)
    snapshot_stock = models.IntegerField(null=True, blank=True)
    snapshot_min_stock = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        db_table = 'purchase_order_proposal_line'
        ordering = ['product__product_code']
        indexes = [
            models.Index(fields=['proposal']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return f'{self.proposal_id}:{self.product_id}'


class PurchaseOrderProposalApproval(models.Model):
    ACTION_APPROVED = 'APPROVED'
    ACTION_REJECTED = 'REJECTED'
    ACTION_CHOICES = [
        (ACTION_APPROVED, '承認'),
        (ACTION_REJECTED, '差戻'),
    ]

    proposal = models.ForeignKey(
        PurchaseOrderProposal,
        on_delete=models.CASCADE,
        related_name='approvals',
    )
    approval_level = models.SmallIntegerField()
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='purchase_order_proposal_approvals',
    )
    approved_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'purchase_order_proposal_approval'
        indexes = [
            models.Index(fields=['proposal', 'approval_level']),
        ]

    def __str__(self):
        return f'{self.proposal_id}:L{self.approval_level}:{self.action}'


class PurchaseOrderTask(models.Model):
    TASK_CREATE_PROPOSAL = 'CREATE_PROPOSAL'
    TASK_CREATE_ORDER_PDF = 'CREATE_ORDER_PDF'
    TASK_APPROVE_L2 = 'APPROVE_L2'
    TASK_APPROVE_L3 = 'APPROVE_L3'
    TASK_APPROVE_L4 = 'APPROVE_L4'
    TASK_SEND_TO_SUPPLIER = 'SEND_TO_SUPPLIER'
    TASK_TYPE_CHOICES = [
        (TASK_CREATE_PROPOSAL, '外作・購入品注文書作成'),
        (TASK_CREATE_ORDER_PDF, '注文書作成'),
        (TASK_APPROVE_L2, '班長承認'),
        (TASK_APPROVE_L3, '係長承認'),
        (TASK_APPROVE_L4, '事業部長承認'),
        (TASK_SEND_TO_SUPPLIER, '購入先送信'),
    ]

    STATUS_PENDING = 'PENDING'
    STATUS_DONE = 'DONE'
    STATUS_SKIPPED = 'SKIPPED'
    STATUS_CHOICES = [
        (STATUS_PENDING, '未対応'),
        (STATUS_DONE, '完了'),
        (STATUS_SKIPPED, 'スキップ'),
    ]

    proposal = models.ForeignKey(
        PurchaseOrderProposal,
        on_delete=models.CASCADE,
        related_name='tasks',
    )
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='purchase_order_tasks',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    done_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'purchase_order_task'
        indexes = [
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['task_type', 'status']),
            models.Index(fields=['proposal']),
        ]

    def __str__(self):
        return f'{self.task_type}:{self.assigned_to_id}:{self.status}'


class PurchasePlanChangeLog(models.Model):
    changed_at = models.DateTimeField(auto_now_add=True)
    plan_date = models.DateField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    line = models.ForeignKey(Line, on_delete=models.CASCADE)
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    sequence_no = models.IntegerField(null=True, blank=True)
    plan_id = models.CharField(max_length=255, null=True, blank=True)
    before_qty = models.IntegerField(default=0)
    after_qty = models.IntegerField(default=0)
    reason = models.TextField()
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='purchase_plan_change_logs'
    )

    class Meta:
        db_table = 'purchase_plan_change_log'
        indexes = [
            models.Index(fields=['plan_date', 'line']),
        ]

    def __str__(self):
        return f'{self.plan_date} {self.product_id} {self.before_qty}->{self.after_qty}'


class EngineeringChangeCase(models.Model):
    """設変管理ヘッダ（最終品単位）"""
    case_code = models.CharField(max_length=30, null=True, blank=True, unique=True, verbose_name='案件コード')
    case_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='案件名')
    final_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='engineering_change_cases'
    )
    switch_date = models.DateField(null=True, blank=True, verbose_name='切替予定日')
    note = models.CharField(max_length=255, null=True, blank=True, verbose_name='備考')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'engineering_change_case'
        indexes = [
            models.Index(fields=['switch_date']),
            models.Index(fields=['final_product']),
        ]


class EngineeringChangePart(models.Model):
    """設変対象部品（旧→新）"""
    case = models.ForeignKey(EngineeringChangeCase, on_delete=models.CASCADE, related_name='parts')
    switch_date = models.DateField(null=True, blank=True, verbose_name='切替予定日')
    old_part = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='engineering_change_old_parts')
    new_part = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='engineering_change_new_parts')
    required_qty_after_eol = models.IntegerField(default=0, verbose_name='打ち切り後必要量')
    remark = models.CharField(max_length=255, null=True, blank=True, verbose_name='備考')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'engineering_change_part'
        indexes = [
            models.Index(fields=['old_part']),
            models.Index(fields=['new_part']),
        ]


class DiscontinuationCase(models.Model):
    """打ち切り案件"""
    case_code = models.CharField(max_length=30, unique=True, verbose_name='案件コード')
    title = models.CharField(max_length=200, verbose_name='案件名')
    end_date = models.DateField(null=True, blank=True, verbose_name='終了時期')
    note = models.TextField(blank=True, default='', verbose_name='備考')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'discontinuation_case'
        indexes = [
            models.Index(fields=['end_date']),
        ]

    def __str__(self):
        return f'{self.case_code} {self.title}'


class DiscontinuationProduct(models.Model):
    """打ち切り完成品"""
    case = models.ForeignKey(DiscontinuationCase, on_delete=models.CASCADE, related_name='products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='discontinuation_products', verbose_name='完成品')
    end_date = models.DateField(null=True, blank=True, verbose_name='打ち切り時期')
    note = models.CharField(max_length=255, blank=True, default='', verbose_name='備考')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'discontinuation_product'
        indexes = [
            models.Index(fields=['product']),
        ]


class DiscontinuationPart(models.Model):
    """打ち切り構成品"""
    disc_product = models.ForeignKey(DiscontinuationProduct, on_delete=models.CASCADE, related_name='parts')
    part = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='discontinuation_parts', verbose_name='構成品')
    note = models.CharField(max_length=255, blank=True, default='', verbose_name='備考')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'discontinuation_part'
        indexes = [
            models.Index(fields=['part']),
        ]


class PurchaseAutoDeliveryListConfig(models.Model):
    """自動納入リスト送信設定"""
    STATUS_CHOICES = [
        ('SUCCESS', '成功'),
        ('FAILED', '失敗'),
        ('RUNNING', '実行中'),
        ('SKIPPED', 'スキップ'),
    ]

    supplier = models.OneToOneField(
        Supplier,
        on_delete=models.CASCADE,
        related_name='auto_delivery_list_config',
        verbose_name='対象仕入先',
    )
    is_enabled = models.BooleanField(default=True, verbose_name='有効')
    scheduled_hour = models.PositiveSmallIntegerField(default=7, verbose_name='実行時（時）')
    scheduled_minute = models.PositiveSmallIntegerField(default=0, verbose_name='実行時（分）')
    lead_time_days = models.PositiveSmallIntegerField(default=2, verbose_name='納入日（何営業日後）')
    progress_days_back = models.PositiveSmallIntegerField(default=7, verbose_name='進度表（何営業日前から）')
    progress_days_forward = models.PositiveSmallIntegerField(default=30, verbose_name='進度表（何日後まで）')
    send_delivery_list_excel = models.BooleanField(default=True, verbose_name='納品リストExcel送信')
    send_progress_excel = models.BooleanField(default=True, verbose_name='進度表Excel送信')
    send_progress_pdf = models.BooleanField(default=True, verbose_name='進度表PDF送信')
    send_delivery_note_pdf = models.BooleanField(default=True, verbose_name='外作納品書PDF送信')
    email_body_custom = models.TextField(blank=True, default='', verbose_name='メール本文（カスタム）')
    reply_to_email = models.EmailField(blank=True, default='', verbose_name='返信先メールアドレス')
    cc_emails = models.TextField(blank=True, default='', verbose_name='業務員CC送信先メール（改行区切り）')
    notify_on_failure = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='auto_delivery_list_failure_notifications',
        verbose_name='失敗時の通知先',
    )
    notify_on_non_delivery = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='auto_delivery_list_non_delivery_notifications',
        verbose_name='納入日でないときの通知先',
    )
    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name='最終実行日時')
    last_run_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, null=True, blank=True, verbose_name='最終実行結果',
    )
    last_run_message = models.TextField(blank=True, default='', verbose_name='最終実行メッセージ')
    last_run_duration_seconds = models.FloatField(null=True, blank=True, verbose_name='最終実行時間（秒）')

    class Meta:
        db_table = 'purchase_auto_delivery_list_config'
        verbose_name = '自動納入リスト送信設定'
        verbose_name_plural = '自動納入リスト送信設定'

    def __str__(self):
        return f'{self.supplier} {self.scheduled_hour:02d}:{self.scheduled_minute:02d}'


class PurchaseAutoOrderSendConfig(models.Model):
    """注文書自動送信設定"""

    STATUS_CHOICES = [
        ('SUCCESS', '成功'),
        ('FAILED', '失敗'),
        ('RUNNING', '実行中'),
        ('SKIPPED', 'スキップ'),
    ]

    CALC_MODE_DEMAND = 'DEMAND'
    CALC_MODE_LOT_ROUNDED = 'LOT_ROUNDED'
    CALC_MODE_CHOICES = [
        (CALC_MODE_DEMAND, '需要そのまま'),
        (CALC_MODE_LOT_ROUNDED, 'ロット丸め'),
    ]
    DELIVERY_DAY_MODE_PATTERN = 'PATTERN'
    DELIVERY_DAY_MODE_SUPPLIER_CALENDAR = 'SUPPLIER_CALENDAR'
    DELIVERY_DAY_MODE_CHOICES = [
        (DELIVERY_DAY_MODE_PATTERN, '納入パターン'),
        (DELIVERY_DAY_MODE_SUPPLIER_CALENDAR, '仕入れ先カレンダ'),
    ]

    supplier = models.OneToOneField(
        Supplier,
        on_delete=models.CASCADE,
        related_name='auto_order_send_config',
        verbose_name='対象仕入先',
    )
    is_enabled = models.BooleanField(default=True, verbose_name='有効')
    scheduled_hour = models.PositiveSmallIntegerField(default=7, verbose_name='実行時（時）')
    scheduled_minute = models.PositiveSmallIntegerField(default=0, verbose_name='実行時（分）')
    lead_time_days = models.PositiveSmallIntegerField(default=5, verbose_name='納入日（何営業日後）')
    progress_days_back = models.PositiveSmallIntegerField(default=7, verbose_name='進度表（何営業日前から）')
    progress_days_forward = models.PositiveSmallIntegerField(default=30, verbose_name='進度表（何日後まで）')
    calc_mode = models.CharField(
        max_length=20,
        choices=CALC_MODE_CHOICES,
        default=CALC_MODE_DEMAND,
        verbose_name='数量算出方式',
    )
    delivery_day_mode = models.CharField(
        max_length=30,
        choices=DELIVERY_DAY_MODE_CHOICES,
        default=DELIVERY_DAY_MODE_PATTERN,
        verbose_name='納入日判定方式',
    )
    safety_stock_enabled = models.BooleanField(default=False, verbose_name='安全在庫確保')
    safety_stock_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=1,
        verbose_name='安全在庫倍数',
    )
    send_order_excel = models.BooleanField(default=True, verbose_name='注文書Excel送信')
    send_order_pdf = models.BooleanField(default=False, verbose_name='注文書PDF送信')
    send_progress_excel = models.BooleanField(default=True, verbose_name='進度表Excel送信')
    send_progress_pdf = models.BooleanField(default=True, verbose_name='進度表PDF送信')
    send_delivery_note_pdf = models.BooleanField(default=True, verbose_name='外作納品書PDF送信')
    email_body_custom = models.TextField(blank=True, default='', verbose_name='メール本文（カスタム）')
    reply_to_email = models.EmailField(blank=True, default='', verbose_name='返信先メールアドレス')
    cc_emails = models.TextField(blank=True, default='', verbose_name='業務員CC送信先メール（改行区切り）')
    notify_on_failure = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='auto_order_send_failure_notifications',
        verbose_name='失敗時の通知先',
    )
    notify_on_non_delivery = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='auto_order_send_non_delivery_notifications',
        verbose_name='納入日でないときの通知先',
    )
    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name='最終実行日時')
    last_run_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        null=True,
        blank=True,
        verbose_name='最終実行結果',
    )
    last_run_message = models.TextField(blank=True, default='', verbose_name='最終実行メッセージ')
    last_run_duration_seconds = models.FloatField(null=True, blank=True, verbose_name='最終実行時間（秒）')

    class Meta:
        db_table = 'purchase_auto_order_send_config'
        verbose_name = '注文書自動送信設定'
        verbose_name_plural = '注文書自動送信設定'

    def __str__(self):
        return f'{self.supplier} {self.scheduled_hour:02d}:{self.scheduled_minute:02d}'


class PurchaseAutoOrderSendHistory(models.Model):
    """注文書自動送信の実行履歴"""

    TRIGGER_SCHEDULED = 'SCHEDULED'
    TRIGGER_MANUAL = 'MANUAL'
    TRIGGER_HOLIDAY_TRIAL = 'HOLIDAY_TRIAL'
    TRIGGER_CHOICES = [
        (TRIGGER_SCHEDULED, '自動実行'),
        (TRIGGER_MANUAL, '手動実行'),
        (TRIGGER_HOLIDAY_TRIAL, '休日手動実行'),
    ]

    STATUS_SUCCESS = 'SUCCESS'
    STATUS_FAILED = 'FAILED'
    STATUS_RUNNING = 'RUNNING'
    STATUS_SKIPPED = 'SKIPPED'
    STATUS_CHOICES = [
        (STATUS_SUCCESS, '成功'),
        (STATUS_FAILED, '失敗'),
        (STATUS_RUNNING, '実行中'),
        (STATUS_SKIPPED, 'スキップ'),
    ]

    config = models.ForeignKey(
        PurchaseAutoOrderSendConfig,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='histories',
        verbose_name='注文書自動送信設定',
    )
    supplier = models.ForeignKey(
        Supplier,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='auto_order_send_histories',
        verbose_name='仕入先',
    )
    supplier_code = models.CharField(max_length=50, blank=True, default='', verbose_name='仕入先コード')
    supplier_name = models.CharField(max_length=255, blank=True, default='', verbose_name='仕入先名')
    trigger_type = models.CharField(
        max_length=20,
        choices=TRIGGER_CHOICES,
        default=TRIGGER_SCHEDULED,
        verbose_name='実行種別',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_RUNNING,
        verbose_name='実行結果',
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='開始日時')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='終了日時')
    duration_seconds = models.FloatField(null=True, blank=True, verbose_name='実行時間（秒）')
    to_email = models.CharField(max_length=255, blank=True, default='', verbose_name='宛先メール')
    cc_emails = models.TextField(blank=True, default='', verbose_name='CCメール')
    subject = models.CharField(max_length=255, blank=True, default='', verbose_name='件名')
    message = models.TextField(blank=True, default='', verbose_name='結果メッセージ')
    attachment_labels = models.TextField(blank=True, default='', verbose_name='添付内容（改行区切り）')
    first_delivery_date = models.DateField(null=True, blank=True, verbose_name='先頭納入日')
    order_item_count = models.PositiveIntegerField(default=0, verbose_name='注文書品目数')
    order_excel_file = models.FileField(
        upload_to='purchase_auto_order_send/order_excel/',
        blank=True,
        verbose_name='注文書Excel',
    )

    class Meta:
        db_table = 'purchase_auto_order_send_history'
        verbose_name = '注文書自動送信履歴'
        verbose_name_plural = '注文書自動送信履歴'
        ordering = ['-started_at', '-id']

    def __str__(self):
        return f'{self.supplier_code} {self.started_at} {self.status}'




class PurchaseOrderProposalEmailConfig(models.Model):
    """外作・購入品注文の購入先送信メール設定"""

    supplier = models.OneToOneField(
        Supplier,
        on_delete=models.CASCADE,
        related_name='purchase_order_proposal_email_config',
        verbose_name='仕入先',
    )
    body = models.TextField(blank=True, default='', verbose_name='本文テンプレート')
    cc_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='purchase_order_proposal_email_configs',
        verbose_name='CCユーザー',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'purchase_order_proposal_email_config'
        verbose_name = '外作・購入品注文メール設定'
        verbose_name_plural = '外作・購入品注文メール設定'
        ordering = ['supplier__supplier_code']

    def __str__(self):
        return f'{self.supplier.supplier_code} {self.supplier.supplier_name}'


class PurchaseAutoOrderSendTruckLoadRequest(models.Model):
    """トラック積載判定の中断要求管理"""

    STATUS_RUNNING = 'RUNNING'
    STATUS_CANCELED = 'CANCELED'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CHOICES = [
        (STATUS_RUNNING, '実行中'),
        (STATUS_CANCELED, '中断'),
        (STATUS_COMPLETED, '完了'),
    ]

    request_id = models.CharField(max_length=64, unique=True, verbose_name='リクエストID')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_RUNNING,
        verbose_name='状態',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    canceled_at = models.DateTimeField(null=True, blank=True, verbose_name='中断要求日時')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完了日時')

    class Meta:
        db_table = 'purchase_auto_order_send_truck_load_request'
        verbose_name = '注文書自動送信トラック積載判定リクエスト'
        verbose_name_plural = '注文書自動送信トラック積載判定リクエスト'

    def __str__(self):
        return f'{self.request_id} {self.status}'
