from django.conf import settings
from django.db import models

from masters.models import Line, Process, Product
from production.models import ProductionOrder


class ProductChecksheetTemplate(models.Model):
    """製品チェックシートの管理単位（承認ワークフロー付き）。ライン・工程・製品に紐づく。"""

    STATUS_DRAFT = "DRAFT"
    STATUS_SUPERVISOR_PENDING = "SUPERVISOR_PENDING"
    STATUS_CHIEF_PENDING = "CHIEF_PENDING"
    STATUS_MANAGER_PENDING = "MANAGER_PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "下書き"),
        (STATUS_SUPERVISOR_PENDING, "班長確認待ち"),
        (STATUS_CHIEF_PENDING, "係長確認待ち"),
        (STATUS_MANAGER_PENDING, "部長承認待ち"),
        (STATUS_APPROVED, "承認済み"),
        (STATUS_REJECTED, "差戻し"),
    ]

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=200, verbose_name="テンプレート名")
    line = models.ForeignKey(Line, on_delete=models.PROTECT, related_name="product_checksheet_templates", verbose_name="ライン")
    process = models.ForeignKey(Process, on_delete=models.PROTECT, related_name="product_checksheet_templates", verbose_name="工程")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="product_checksheet_templates", verbose_name="製品")
    version = models.PositiveIntegerField(default=1, verbose_name="版")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, verbose_name="ステータス")
    is_active = models.BooleanField(default=True, verbose_name="有効")

    # ヘッダー情報
    document_title = models.CharField(max_length=200, blank=True, default="", verbose_name="帳票タイトル")
    sheet_name = models.CharField(max_length=120, blank=True, default="", verbose_name="元シート名")
    revision_date = models.DateField(null=True, blank=True, verbose_name="改訂日")
    revision_notes = models.TextField(blank=True, default="", verbose_name="改訂内容")
    effective_from = models.DateField(null=True, blank=True, verbose_name="運用開始日")

    # 台紙情報
    source_type = models.CharField(
        max_length=20,
        choices=[("pdf", "PDF台紙"), ("image", "画像台紙")],
        default="image",
        verbose_name="台紙種別",
    )
    source_pdf = models.FileField(upload_to="product_checksheets/source_pdf/", blank=True, verbose_name="台紙PDF")
    source_image = models.ImageField(upload_to="product_checksheets/source_image/", blank=True, verbose_name="台紙画像")
    background_image = models.ImageField(upload_to="product_checksheets/background/", blank=True, verbose_name="編集用背景画像")
    background_width = models.PositiveIntegerField(default=1200, verbose_name="背景幅")
    background_height = models.PositiveIntegerField(default=1600, verbose_name="背景高さ")
    editor_notes = models.TextField(blank=True, default="", verbose_name="編集メモ")

    # 作成者
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="product_checksheet_templates_created",
        verbose_name="作成者",
    )

    # 承認ワークフロー: 担当者
    reviewer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="product_checksheet_templates_reviewer",
        verbose_name="班長担当",
    )
    chief_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="product_checksheet_templates_chief",
        verbose_name="係長担当",
    )
    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="product_checksheet_templates_approver",
        verbose_name="部長担当",
    )

    # 承認ワークフロー: 実施者
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="product_checksheet_templates_reviewed",
        verbose_name="班長確認実施者",
    )
    chief_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="product_checksheet_templates_chief_reviewed",
        verbose_name="係長確認実施者",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="product_checksheet_templates_approved",
        verbose_name="部長承認実施者",
    )

    # 承認ワークフロー: タイムスタンプ
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="班長確認日時")
    chief_reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="係長確認日時")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="部長承認日時")

    # 差戻し
    rejection_comment = models.TextField(blank=True, default="", verbose_name="差戻しコメント")
    submitted_fields_snapshot = models.JSONField(null=True, blank=True, verbose_name="提出時配置項目スナップショット")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "quality_product_checksheet_template"
        verbose_name = "製品チェックシートテンプレート"
        verbose_name_plural = "製品チェックシートテンプレート"
        unique_together = [["line", "process", "product", "version"]]
        indexes = [
            models.Index(fields=["line", "process", "product", "is_active"]),
            models.Index(fields=["product", "is_active"]),
            models.Index(fields=["status", "is_active"]),
        ]
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return f"{self.product.product_code} / {self.process.process_code} / v{self.version}"


class ProductChecksheetField(models.Model):
    """台紙上の入力項目。座標は背景画像のピクセル座標。"""

    FIELD_CHECKBOX = "checkbox"
    FIELD_TEXT = "text"
    FIELD_OKNG = "aggregate_okng"
    FIELD_DATE = "date"
    FIELD_PHOTO = "photo"
    FIELD_PEN = "pen"
    FIELD_WORKER = "worker_name"
    FIELD_SUPERVISOR_STAMP = "supervisor_stamp"
    FIELD_CHOICES = [
        (FIELD_CHECKBOX, "チェック"),
        (FIELD_TEXT, "テキスト"),
        (FIELD_OKNG, "OK/NG"),
        (FIELD_DATE, "日付"),
        (FIELD_PHOTO, "写真"),
        (FIELD_PEN, "手書き"),
        (FIELD_WORKER, "作業者名"),
        (FIELD_SUPERVISOR_STAMP, "監督者確認スタンプ"),
    ]
    DIRECTION_CHOICES = [
        ("horizontal", "横書き"),
        ("vertical", "縦書き"),
    ]

    id = models.BigAutoField(primary_key=True)
    template = models.ForeignKey(
        ProductChecksheetTemplate,
        on_delete=models.CASCADE,
        related_name="fields",
        verbose_name="テンプレート",
    )
    key = models.SlugField(max_length=80, verbose_name="内部キー")
    label = models.CharField(max_length=120, verbose_name="表示名")
    field_type = models.CharField(max_length=30, choices=FIELD_CHOICES, default=FIELD_TEXT, verbose_name="項目種類")
    description = models.CharField(max_length=200, blank=True, default="", verbose_name="説明")
    x = models.FloatField(default=0, verbose_name="左位置")
    y = models.FloatField(default=0, verbose_name="上位置")
    width = models.FloatField(default=160, verbose_name="幅")
    height = models.FloatField(default=36, verbose_name="高さ")
    required = models.BooleanField(default=False, verbose_name="必須")
    placeholder = models.CharField(max_length=120, blank=True, default="", verbose_name="初期表示")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="並び順")
    show_label = models.BooleanField(default=True, verbose_name="表示名を表示")
    text_direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES, default="horizontal", verbose_name="文字方向")
    counter_step = models.PositiveIntegerField(default=1, verbose_name="カウント加算値")

    class Meta:
        db_table = "quality_product_checksheet_field"
        verbose_name = "製品チェックシート項目"
        verbose_name_plural = "製品チェックシート項目"
        unique_together = [["template", "key"]]
        indexes = [
            models.Index(fields=["template", "sort_order"]),
        ]
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.template_id}:{self.key}"


class ProductChecksheetBatch(models.Model):
    """工程入力1回分の親。数量分の個別チェックシートを束ねる。"""

    STATUS_OPEN = "OPEN"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_CHOICES = [
        (STATUS_OPEN, "入力中"),
        (STATUS_COMPLETED, "入力完了"),
    ]

    id = models.BigAutoField(primary_key=True)
    template = models.ForeignKey(ProductChecksheetTemplate, on_delete=models.PROTECT, related_name="batches", verbose_name="テンプレート")
    production_order = models.ForeignKey(
        ProductionOrder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="product_checksheet_batches",
        verbose_name="製造指示",
    )
    line = models.ForeignKey(Line, on_delete=models.PROTECT, related_name="product_checksheet_batches", verbose_name="ライン")
    process = models.ForeignKey(Process, on_delete=models.PROTECT, related_name="product_checksheet_batches", verbose_name="工程")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="product_checksheet_batches", verbose_name="製品")
    lot_no = models.CharField(max_length=100, blank=True, default="", verbose_name="ロットNo")
    quantity = models.PositiveIntegerField(verbose_name="対象数量")
    operator_name = models.CharField(max_length=120, blank=True, default="", verbose_name="作業者")
    source_context = models.JSONField(default=dict, blank=True, verbose_name="工程入力元情報")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, verbose_name="状態")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="product_checksheet_batches_created",
        verbose_name="作成者",
    )
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="入力完了日時")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "quality_product_checksheet_batch"
        verbose_name = "製品チェックシート入力ロット"
        verbose_name_plural = "製品チェックシート入力ロット"
        indexes = [
            models.Index(fields=["production_order", "line", "process", "product"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["lot_no"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.product.product_code} {self.lot_no} x {self.quantity}"


class ProductChecksheetRecord(models.Model):
    """1製品1枚の品質チェック記録。出荷日・台目もここに持つ。"""

    STATUS_PENDING = "PENDING"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_APPROVED = "APPROVED"
    STATUS_CHOICES = [
        (STATUS_PENDING, "未入力"),
        (STATUS_COMPLETED, "入力完了"),
        (STATUS_APPROVED, "承認済み"),
    ]

    id = models.BigAutoField(primary_key=True)
    batch = models.ForeignKey(ProductChecksheetBatch, on_delete=models.CASCADE, related_name="records", verbose_name="入力ロット")
    template = models.ForeignKey(ProductChecksheetTemplate, on_delete=models.PROTECT, related_name="records", verbose_name="テンプレート")
    sequence_no = models.PositiveIntegerField(verbose_name="ロット内番号")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name="状態")
    responses_json = models.JSONField(default=dict, blank=True, verbose_name="回答データ")
    planned_ship_date = models.DateField(null=True, blank=True, verbose_name="出荷日")
    shipment_unit_no = models.PositiveIntegerField(null=True, blank=True, verbose_name="台目")
    shipment_sequence_no = models.PositiveIntegerField(null=True, blank=True, verbose_name="出荷分内番号")
    completed_by_name = models.CharField(max_length=120, blank=True, default="", verbose_name="入力者")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="入力完了日時")
    supervisor_name = models.CharField(max_length=120, blank=True, default="", verbose_name="確認者")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="承認日時")
    generated_pdf = models.FileField(upload_to="product_checksheets/approved_pdfs/", blank=True, verbose_name="完成PDF")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "quality_product_checksheet_record"
        verbose_name = "製品チェックシート記録"
        verbose_name_plural = "製品チェックシート記録"
        unique_together = [["batch", "sequence_no"]]
        indexes = [
            models.Index(fields=["batch", "status"]),
            models.Index(fields=["planned_ship_date", "shipment_unit_no"]),
            models.Index(fields=["status", "approved_at"]),
        ]
        ordering = ["batch_id", "sequence_no"]

    def __str__(self):
        return f"batch={self.batch_id} #{self.sequence_no}"


class ProductChecksheetPhoto(models.Model):
    """1製品チェックシートに添付する写真。"""

    id = models.BigAutoField(primary_key=True)
    record = models.ForeignKey(ProductChecksheetRecord, on_delete=models.CASCADE, related_name="photos", verbose_name="チェック記録")
    field_key = models.CharField(max_length=80, verbose_name="項目キー")
    image = models.ImageField(upload_to="product_checksheets/photos/", verbose_name="写真")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        db_table = "quality_product_checksheet_photo"
        verbose_name = "製品チェックシート写真"
        verbose_name_plural = "製品チェックシート写真"
        indexes = [
            models.Index(fields=["record", "field_key"]),
        ]
        ordering = ["id"]


class ProductChecksheetTask(models.Model):
    """製品チェックシート承認タスク"""

    TASK_SUPERVISOR_REVIEW = "SUPERVISOR_REVIEW"
    TASK_CHIEF_REVIEW = "CHIEF_REVIEW"
    TASK_MANAGER_APPROVE = "MANAGER_APPROVE"
    TASK_CREATOR_FIX = "CREATOR_FIX"
    TASK_TYPE_CHOICES = [
        (TASK_SUPERVISOR_REVIEW, "班長確認"),
        (TASK_CHIEF_REVIEW, "係長確認"),
        (TASK_MANAGER_APPROVE, "部長承認"),
        (TASK_CREATOR_FIX, "差戻し修正"),
    ]

    STATUS_PENDING = "PENDING"
    STATUS_DONE = "DONE"
    STATUS_SKIPPED = "SKIPPED"
    STATUS_CHOICES = [
        (STATUS_PENDING, "未対応"),
        (STATUS_DONE, "完了"),
        (STATUS_SKIPPED, "スキップ"),
    ]

    template = models.ForeignKey(
        ProductChecksheetTemplate,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="テンプレート",
    )
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES, verbose_name="タスク種別")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="product_checksheet_tasks",
        verbose_name="担当者",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name="状態")
    due_date = models.DateField(null=True, blank=True, verbose_name="期限")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    done_at = models.DateTimeField(null=True, blank=True, verbose_name="完了日時")

    class Meta:
        db_table = "quality_product_checksheet_task"
        verbose_name = "製品チェックシートタスク"
        verbose_name_plural = "製品チェックシートタスク"
        indexes = [
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["task_type", "status"]),
            models.Index(fields=["template"]),
        ]
        ordering = ["status", "due_date", "-created_at", "-id"]

    def __str__(self):
        return f"{self.template_id}:{self.task_type}:{self.assigned_to_id}:{self.status}"


class ProductChecksheetWorkflowLog(models.Model):
    """製品チェックシートワークフロー履歴"""

    ACTION_CREATED = "CREATED"
    ACTION_UPDATED = "UPDATED"
    ACTION_SUBMITTED = "SUBMITTED"
    ACTION_SUPERVISOR_REVIEWED = "SUPERVISOR_REVIEWED"
    ACTION_CHIEF_REVIEWED = "CHIEF_REVIEWED"
    ACTION_APPROVED = "APPROVED"
    ACTION_REJECTED = "REJECTED"

    ACTION_CHOICES = [
        (ACTION_CREATED, "作成"),
        (ACTION_UPDATED, "更新"),
        (ACTION_SUBMITTED, "確認依頼"),
        (ACTION_SUPERVISOR_REVIEWED, "班長確認完了"),
        (ACTION_CHIEF_REVIEWED, "係長確認完了"),
        (ACTION_APPROVED, "部長承認"),
        (ACTION_REJECTED, "差戻し"),
    ]

    template = models.ForeignKey(
        ProductChecksheetTemplate,
        on_delete=models.CASCADE,
        related_name="workflow_logs",
        verbose_name="テンプレート",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="操作")
    from_status = models.CharField(max_length=20, blank=True, default="", verbose_name="遷移前")
    to_status = models.CharField(max_length=20, blank=True, default="", verbose_name="遷移後")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="product_checksheet_workflow_logs",
        verbose_name="操作ユーザー",
    )
    comment = models.TextField(blank=True, default="", verbose_name="コメント")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        db_table = "quality_product_checksheet_workflow_log"
        verbose_name = "製品チェックシートワークフロー履歴"
        verbose_name_plural = "製品チェックシートワークフロー履歴"
        indexes = [
            models.Index(fields=["template", "created_at"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.template_id}:{self.action}"
