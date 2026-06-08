from django.conf import settings
from django.db import models

from masters.models import Line, Process, Product


class IntegratedChecksheetTemplate(models.Model):
    """B案: 製品で1テンプレート。全工程のチェック項目を内包する。"""

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

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="integrated_checksheet_templates", verbose_name="製品")
    line = models.ForeignKey(
        Line, null=True, blank=True,
        on_delete=models.PROTECT,
        related_name="integrated_checksheet_templates",
        verbose_name="ライン",
    )
    name = models.CharField(max_length=200, verbose_name="テンプレート名")
    version = models.PositiveIntegerField(default=1, verbose_name="版")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, verbose_name="状態")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    document_title = models.CharField(max_length=300, blank=True, default="", verbose_name="帳票タイトル")
    sheet_name = models.CharField(max_length=200, blank=True, default="", verbose_name="元シート名")
    revision_notes = models.TextField(default="", verbose_name="改訂内容")
    revision_date = models.DateField(null=True, blank=True, verbose_name="改訂日")
    effective_from = models.DateField(null=True, blank=True, verbose_name="運用開始日")
    reviewer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+", verbose_name="班長担当",
    )
    chief_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+", verbose_name="係長担当",
    )
    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+", verbose_name="部長担当",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="班長確認日時")
    chief_reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="係長確認日時")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="部長承認日時")
    rejection_comment = models.TextField(blank=True, default="", verbose_name="差戻しコメント")
    submitted_items_snapshot = models.JSONField(null=True, blank=True, verbose_name="提出時点検項目スナップショット")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+", verbose_name="作成者",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "quality_integrated_checksheet_template"
        verbose_name = "工程一体チェックシートテンプレート"
        verbose_name_plural = "工程一体チェックシートテンプレート"
        unique_together = [["product", "line", "version"]]
        ordering = ["-version"]

    def __str__(self):
        return f"{self.product.product_code} v{self.version}"


class IntegratedChecksheetProcessBlock(models.Model):
    """テンプレート内の工程ブロック。工程順序を定義する。"""

    template = models.ForeignKey(
        IntegratedChecksheetTemplate, on_delete=models.CASCADE,
        related_name="process_blocks", verbose_name="テンプレート",
    )
    process = models.ForeignKey(Process, on_delete=models.PROTECT, related_name="+", verbose_name="工程")
    sort_order = models.PositiveIntegerField(default=1, verbose_name="工程順序")
    source_pdf = models.FileField(
        upload_to="integrated_checksheets/source_pdf/", blank=True,
        verbose_name="台紙PDF",
    )
    sketch_image = models.ImageField(
        upload_to="integrated_checksheets/sketches/", blank=True,
        verbose_name="台紙画像",
    )

    class Meta:
        db_table = "quality_integrated_cs_process_block"
        verbose_name = "工程ブロック"
        verbose_name_plural = "工程ブロック"
        unique_together = [["template", "process"]]
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.template} - {self.process.process_name}"


class IntegratedChecksheetItem(models.Model):
    """工程ブロック内のチェック項目。"""

    RECORD_CHECK = "CHECK"
    RECORD_NUMERIC = "NUMERIC"
    RECORD_NUMERIC_CHECK = "NUMERIC_CHECK"
    RECORD_PHOTO_NUMERIC = "PHOTO_NUMERIC"
    RECORD_PHOTO = "PHOTO"
    RECORD_TEXT = "TEXT"
    RECORD_CHOICES = [
        (RECORD_CHECK, "チェック"),
        (RECORD_NUMERIC, "数値"),
        (RECORD_NUMERIC_CHECK, "数値＋チェック"),
        (RECORD_PHOTO_NUMERIC, "写真＋数値"),
        (RECORD_PHOTO, "写真のみ"),
        (RECORD_TEXT, "文字"),
    ]

    process_block = models.ForeignKey(
        IntegratedChecksheetProcessBlock, on_delete=models.CASCADE,
        related_name="items", verbose_name="工程ブロック",
    )
    sort_order = models.PositiveIntegerField(default=1, verbose_name="表示順")
    item_name = models.CharField(max_length=300, verbose_name="点検項目")
    standard = models.TextField(blank=True, default="", verbose_name="規格")
    frequency = models.CharField(max_length=50, blank=True, default="", verbose_name="確認頻度")
    method = models.TextField(blank=True, default="", verbose_name="方法")
    record_type = models.CharField(max_length=20, choices=RECORD_CHOICES, default=RECORD_CHECK, verbose_name="記録種別")
    unit = models.CharField(max_length=30, blank=True, default="", verbose_name="単位")
    criteria = models.TextField(blank=True, default="", verbose_name="判定基準")
    is_required = models.BooleanField(default=True, verbose_name="必須")

    class Meta:
        db_table = "quality_integrated_cs_item"
        verbose_name = "チェック項目"
        verbose_name_plural = "チェック項目"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.process_block} - {self.item_name}"


class IntegratedChecksheetSketchField(models.Model):
    """台紙（略図）上に配置するフィールド。座標は画像ピクセル基準。"""

    FIELD_CHECKBOX = "checkbox"
    FIELD_TEXT = "text"
    FIELD_OKNG = "aggregate_okng"
    FIELD_DATE = "date"
    FIELD_PHOTO = "photo"
    FIELD_PEN = "pen"
    FIELD_WORKER = "worker_name"
    FIELD_CHOICES = [
        (FIELD_CHECKBOX, "チェック"),
        (FIELD_TEXT, "テキスト"),
        (FIELD_OKNG, "OK/NG"),
        (FIELD_DATE, "日付"),
        (FIELD_PHOTO, "写真"),
        (FIELD_PEN, "手書き"),
        (FIELD_WORKER, "作業者名"),
    ]

    process_block = models.ForeignKey(
        IntegratedChecksheetProcessBlock, on_delete=models.CASCADE,
        related_name="sketch_fields", verbose_name="工程ブロック",
    )
    key = models.SlugField(max_length=80, verbose_name="内部キー")
    label = models.CharField(max_length=120, verbose_name="表示名")
    field_type = models.CharField(max_length=30, choices=FIELD_CHOICES, default=FIELD_TEXT, verbose_name="項目種類")
    x = models.FloatField(default=0, verbose_name="左位置")
    y = models.FloatField(default=0, verbose_name="上位置")
    width = models.FloatField(default=160, verbose_name="幅")
    height = models.FloatField(default=36, verbose_name="高さ")
    required = models.BooleanField(default=False, verbose_name="必須")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="並び順")

    class Meta:
        db_table = "quality_integrated_cs_sketch_field"
        verbose_name = "台紙フィールド"
        verbose_name_plural = "台紙フィールド"
        unique_together = [["process_block", "key"]]
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.process_block} - {self.label}"


class IntegratedChecksheetBatch(models.Model):
    """製品で1バッチ。全工程共通。"""

    STATUS_OPEN = "OPEN"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_LEADER_CONFIRMED = "LEADER_CONFIRMED"
    STATUS_SUPERVISOR_CONFIRMED = "SUPERVISOR_CONFIRMED"
    STATUS_CHOICES = [
        (STATUS_OPEN, "実施中"),
        (STATUS_COMPLETED, "完了"),
        (STATUS_LEADER_CONFIRMED, "リーダ確認済"),
        (STATUS_SUPERVISOR_CONFIRMED, "班長確認済"),
    ]

    template = models.ForeignKey(
        IntegratedChecksheetTemplate, on_delete=models.PROTECT,
        related_name="batches", verbose_name="テンプレート",
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="integrated_checksheet_batches", verbose_name="製品")
    line = models.ForeignKey(Line, on_delete=models.PROTECT, related_name="integrated_checksheet_batches", verbose_name="ライン")
    plan_date = models.DateField(null=True, blank=True, verbose_name="計画日")
    quantity = models.PositiveIntegerField(verbose_name="台数")
    lot_no = models.CharField(max_length=100, blank=True, default="", verbose_name="ロットNo")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, verbose_name="状態")
    leader_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+", verbose_name="リーダ確認者",
    )
    leader_confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="リーダ確認日時")
    supervisor_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+", verbose_name="班長確認者",
    )
    supervisor_confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="班長確認日時")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+", verbose_name="作成者",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "quality_integrated_checksheet_batch"
        verbose_name = "工程一体チェックシートバッチ"
        verbose_name_plural = "工程一体チェックシートバッチ"
        indexes = [
            models.Index(fields=["product", "plan_date"]),
            models.Index(fields=["status", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.product_code} x{self.quantity} ({self.plan_date})"


class IntegratedChecksheetUnit(models.Model):
    """台目ごとのレコード。"""

    STATUS_PENDING = "PENDING"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_APPROVED = "APPROVED"
    STATUS_CHOICES = [
        (STATUS_PENDING, "未着手"),
        (STATUS_IN_PROGRESS, "入力中"),
        (STATUS_COMPLETED, "入力完了"),
        (STATUS_APPROVED, "承認済み"),
    ]

    batch = models.ForeignKey(
        IntegratedChecksheetBatch, on_delete=models.CASCADE,
        related_name="units", verbose_name="バッチ",
    )
    sequence_no = models.PositiveIntegerField(verbose_name="台目番号")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name="状態")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完了日時")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="承認日時")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+", verbose_name="承認者",
    )

    class Meta:
        db_table = "quality_integrated_checksheet_unit"
        verbose_name = "台目レコード"
        verbose_name_plural = "台目レコード"
        unique_together = [["batch", "sequence_no"]]
        ordering = ["sequence_no"]

    def __str__(self):
        return f"{self.batch} #{self.sequence_no}"


class IntegratedChecksheetCheck(models.Model):
    """台目×項目ごとのチェック結果。"""

    JUDGEMENT_OK = "OK"
    JUDGEMENT_NG = "NG"
    JUDGEMENT_CHOICES = [
        (JUDGEMENT_OK, "OK"),
        (JUDGEMENT_NG, "NG"),
    ]

    unit = models.ForeignKey(
        IntegratedChecksheetUnit, on_delete=models.CASCADE,
        related_name="checks", verbose_name="台目",
    )
    item = models.ForeignKey(
        IntegratedChecksheetItem, on_delete=models.PROTECT,
        related_name="+", verbose_name="チェック項目",
    )
    judgement = models.CharField(max_length=10, choices=JUDGEMENT_CHOICES, blank=True, default="", verbose_name="判定")
    numeric_value = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True, verbose_name="数値")
    text_value = models.TextField(blank=True, default="", verbose_name="テキスト")
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+", verbose_name="入力者",
    )
    checked_at = models.DateTimeField(null=True, blank=True, verbose_name="入力日時")

    class Meta:
        db_table = "quality_integrated_cs_check"
        verbose_name = "チェック結果"
        verbose_name_plural = "チェック結果"
        unique_together = [["unit", "item"]]

    def __str__(self):
        return f"#{self.unit.sequence_no} - {self.item.item_name}"


class IntegratedChecksheetSketchResponse(models.Model):
    """台目×工程ブロックごとの台紙データ（手書き描画＋フィールド回答）。"""

    unit = models.ForeignKey(
        IntegratedChecksheetUnit, on_delete=models.CASCADE,
        related_name="sketch_responses", verbose_name="台目",
    )
    process_block = models.ForeignKey(
        IntegratedChecksheetProcessBlock, on_delete=models.PROTECT,
        related_name="+", verbose_name="工程ブロック",
    )
    drawing_data = models.JSONField(default=dict, verbose_name="手書き描画データ")
    field_responses = models.JSONField(default=dict, verbose_name="フィールド回答")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "quality_integrated_cs_sketch_response"
        verbose_name = "台紙回答"
        verbose_name_plural = "台紙回答"
        unique_together = [["unit", "process_block"]]

    def __str__(self):
        return f"#{self.unit.sequence_no} - {self.process_block.process.process_name}"


class IntegratedChecksheetTask(models.Model):
    """工程一体チェックシート承認タスク"""

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
        IntegratedChecksheetTemplate, on_delete=models.CASCADE,
        related_name="tasks", verbose_name="テンプレート",
    )
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES, verbose_name="タスク種別")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="integrated_checksheet_tasks",
        verbose_name="担当者",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name="状態")
    due_date = models.DateField(null=True, blank=True, verbose_name="期限")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    done_at = models.DateTimeField(null=True, blank=True, verbose_name="完了日時")

    class Meta:
        db_table = "quality_integrated_cs_task"
        verbose_name = "工程一体CSタスク"
        verbose_name_plural = "工程一体CSタスク"

    def __str__(self):
        return f"{self.template} - {self.get_task_type_display()} -> {self.assigned_to}"


class IntegratedChecksheetWorkflowLog(models.Model):
    """工程一体チェックシートワークフロー履歴"""

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
        (ACTION_CHIEF_REVIEWED, "係長承認完了"),
        (ACTION_APPROVED, "部長承認"),
        (ACTION_REJECTED, "差戻し"),
    ]

    template = models.ForeignKey(
        IntegratedChecksheetTemplate,
        on_delete=models.CASCADE,
        related_name="workflow_logs",
        verbose_name="テンプレート",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="操作")
    from_status = models.CharField(max_length=20, blank=True, default="", verbose_name="遷移前")
    to_status = models.CharField(max_length=20, blank=True, default="", verbose_name="遷移後")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ics_template_workflow_logs",
        verbose_name="操作ユーザー",
    )
    comment = models.TextField(blank=True, default="", verbose_name="コメント")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        db_table = "quality_integrated_cs_workflow_log"
        verbose_name = "工程一体CSワークフロー履歴"
        verbose_name_plural = "工程一体CSワークフロー履歴"
        indexes = [
            models.Index(fields=["template", "created_at"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.template_id}:{self.action}"
