from django.conf import settings
from django.db import models

from .models_scrap import ScrapRecord, ScrapRecordDetail


class EquipmentInspectionTemplate(models.Model):
    """設備点検表テンプレート（承認ワークフロー付き）"""

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

    sheet_code = models.CharField(max_length=40, verbose_name="設備コード")
    sheet_name = models.CharField(max_length=120, verbose_name="設備名")
    title = models.CharField(max_length=200, verbose_name="帳票タイトル")
    source_sheet_name = models.CharField(max_length=80, blank=True, default="", verbose_name="元シート名")
    revision_date = models.DateField(null=True, blank=True, verbose_name="改訂日")
    revision_notes = models.TextField(blank=True, default="", verbose_name="改定内容")
    effective_from = models.DateField(null=True, blank=True, verbose_name="運用開始日")
    version = models.PositiveIntegerField(default=1, verbose_name="版")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, verbose_name="ステータス")
    is_active = models.BooleanField(default=True, verbose_name="有効")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspection_templates_created",
        verbose_name="作成者",
    )
    reviewer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspection_templates_reviewer",
        verbose_name="班長担当",
    )
    chief_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspection_templates_chief",
        verbose_name="係長担当",
    )
    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspection_templates_approver",
        verbose_name="部長担当",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspection_templates_reviewed",
        verbose_name="班長確認実施者",
    )
    chief_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspection_templates_chief_reviewed",
        verbose_name="係長確認実施者",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspection_templates_approved",
        verbose_name="部長承認実施者",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="班長確認日時")
    chief_reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="係長確認日時")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="部長承認日時")
    rejection_comment = models.TextField(blank=True, default="", verbose_name="差戻しコメント")

    processes = models.ManyToManyField(
        "masters.Process",
        blank=True,
        verbose_name="対象工程",
        related_name="inspection_templates",
    )
    lines = models.ManyToManyField(
        "masters.Line",
        blank=True,
        verbose_name="対象ライン",
        related_name="inspection_templates",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "quality_equipment_inspection_template"
        verbose_name = "設備点検表テンプレート"
        verbose_name_plural = "設備点検表テンプレート"
        unique_together = [["sheet_code", "version"]]
        indexes = [
            models.Index(fields=["sheet_code", "status"]),
            models.Index(fields=["status", "is_active"]),
        ]
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return f"{self.sheet_code} v{self.version}"


class EquipmentInspectionItem(models.Model):
    """設備点検項目"""

    SECTION_DAILY = "DAILY"
    SECTION_QUARTERLY = "QUARTERLY"
    SECTION_CHOICES = [
        (SECTION_DAILY, "日次点検"),
        (SECTION_QUARTERLY, "定期実測"),
    ]

    RECORD_CHECK = "CHECK"
    RECORD_NUMERIC = "NUMERIC"
    RECORD_TEXT = "TEXT"
    RECORD_CHOICES = [
        (RECORD_CHECK, "チェック"),
        (RECORD_NUMERIC, "数値"),
        (RECORD_TEXT, "文字"),
    ]

    template = models.ForeignKey(
        EquipmentInspectionTemplate,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="テンプレート",
    )
    section_type = models.CharField(max_length=20, choices=SECTION_CHOICES, default=SECTION_DAILY, verbose_name="区分")
    display_order = models.PositiveIntegerField(default=1, verbose_name="表示順")
    inspection_no = models.PositiveIntegerField(null=True, blank=True, verbose_name="点検No")
    item_name = models.TextField(verbose_name="点検項目")
    standard = models.TextField(blank=True, default="", verbose_name="規格")
    frequency = models.CharField(max_length=50, blank=True, default="", verbose_name="確認頻度")
    method = models.TextField(blank=True, default="", verbose_name="方法")
    record_type = models.CharField(max_length=20, choices=RECORD_CHOICES, default=RECORD_CHECK, verbose_name="記録種別")
    unit = models.CharField(max_length=30, blank=True, default="", verbose_name="単位")
    criteria = models.TextField(blank=True, default="", verbose_name="判定基準")
    is_required = models.BooleanField(default=True, verbose_name="必須")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "quality_equipment_inspection_item"
        verbose_name = "設備点検項目"
        verbose_name_plural = "設備点検項目"
        indexes = [
            models.Index(fields=["template", "section_type", "display_order"]),
        ]
        ordering = ["section_type", "display_order", "id"]

    def __str__(self):
        return f"{self.template_id}:{self.section_type}:{self.display_order}"


class EquipmentInspectionItemAttachment(models.Model):
    """設備点検項目ごとの付表"""

    item = models.ForeignKey(
        EquipmentInspectionItem,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="点検項目",
    )
    display_order = models.PositiveIntegerField(default=1, verbose_name="表示順")
    title = models.CharField(max_length=200, blank=True, default="", verbose_name="タイトル")
    description = models.TextField(blank=True, default="", verbose_name="補足説明")
    check_point = models.TextField(blank=True, default="", verbose_name="確認ポイント")
    ok_example = models.TextField(blank=True, default="", verbose_name="OK例")
    ng_example = models.TextField(blank=True, default="", verbose_name="NG例")
    image_url = models.CharField(max_length=255, blank=True, default="", verbose_name="画像URL")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "quality_equipment_inspection_item_attachment"
        verbose_name = "設備点検項目付表"
        verbose_name_plural = "設備点検項目付表"
        indexes = [
            models.Index(fields=["item", "display_order"]),
        ]
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"{self.item_id}:{self.display_order}"


class EquipmentInspectionRecord(models.Model):
    """設備点検実施ヘッダ"""

    STATUS_DRAFT = "DRAFT"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "下書き"),
        (STATUS_COMPLETED, "完了"),
    ]

    RESULT_OK = "OK"
    RESULT_NG = "NG"
    RESULT_CHOICES = [
        (RESULT_OK, "OK"),
        (RESULT_NG, "NG"),
    ]

    template = models.ForeignKey(
        EquipmentInspectionTemplate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspection_records",
        verbose_name="使用テンプレート",
    )
    sheet_code = models.CharField(max_length=40, verbose_name="設備コード")
    sheet_name = models.CharField(max_length=120, verbose_name="設備名")
    template_title = models.CharField(max_length=200, blank=True, default="", verbose_name="帳票タイトル")
    template_version = models.PositiveIntegerField(default=1, verbose_name="テンプレート版")
    operation_date = models.DateField(verbose_name="点検日")
    section_type = models.CharField(
        max_length=20,
        choices=EquipmentInspectionItem.SECTION_CHOICES,
        default=EquipmentInspectionItem.SECTION_DAILY,
        verbose_name="区分",
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="equipment_inspection_records",
        verbose_name="実施者",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, verbose_name="状態")
    overall_result = models.CharField(
        max_length=10,
        choices=RESULT_CHOICES,
        blank=True,
        default="",
        verbose_name="総合判定",
    )
    memo = models.TextField(blank=True, default="", verbose_name="備考")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完了日時")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "quality_equipment_inspection_record"
        verbose_name = "設備点検実施"
        verbose_name_plural = "設備点検実施"
        unique_together = [["sheet_code", "operation_date", "section_type"]]
        indexes = [
            models.Index(fields=["sheet_code", "operation_date"]),
            models.Index(fields=["operation_date", "status"]),
        ]
        ordering = ["-operation_date", "-id"]

    def __str__(self):
        return f"{self.sheet_code}:{self.operation_date}:{self.section_type}"


class EquipmentInspectionResult(models.Model):
    """設備点検実施明細"""

    JUDGEMENT_OK = "OK"
    JUDGEMENT_NG = "NG"
    JUDGEMENT_CHOICES = [
        (JUDGEMENT_OK, "OK"),
        (JUDGEMENT_NG, "NG"),
    ]

    record = models.ForeignKey(
        EquipmentInspectionRecord,
        on_delete=models.CASCADE,
        related_name="results",
        verbose_name="点検実施",
    )
    item = models.ForeignKey(
        EquipmentInspectionItem,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspection_results",
        verbose_name="元点検項目",
    )
    display_order = models.PositiveIntegerField(default=1, verbose_name="表示順")
    inspection_no = models.PositiveIntegerField(null=True, blank=True, verbose_name="点検No")
    item_name = models.TextField(verbose_name="点検項目")
    standard = models.TextField(blank=True, default="", verbose_name="規格")
    frequency = models.CharField(max_length=50, blank=True, default="", verbose_name="確認頻度")
    method = models.TextField(blank=True, default="", verbose_name="方法")
    record_type = models.CharField(
        max_length=20,
        choices=EquipmentInspectionItem.RECORD_CHOICES,
        default=EquipmentInspectionItem.RECORD_CHECK,
        verbose_name="記録種別",
    )
    unit = models.CharField(max_length=30, blank=True, default="", verbose_name="単位")
    criteria = models.TextField(blank=True, default="", verbose_name="判定基準")
    is_required = models.BooleanField(default=True, verbose_name="必須")
    numeric_value = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name="数値記録",
    )
    text_value = models.TextField(blank=True, default="", verbose_name="文字記録")
    judgement = models.CharField(
        max_length=10,
        choices=JUDGEMENT_CHOICES,
        blank=True,
        default="",
        verbose_name="判定",
    )
    comment = models.TextField(blank=True, default="", verbose_name="コメント")
    measured_at = models.DateTimeField(null=True, blank=True, verbose_name="記録日時")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "quality_equipment_inspection_result"
        verbose_name = "設備点検実施明細"
        verbose_name_plural = "設備点検実施明細"
        indexes = [
            models.Index(fields=["record", "display_order"]),
        ]
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"{self.record_id}:{self.display_order}"


class EquipmentInspectionConfirmation(models.Model):
    """週次・月次確認"""

    TYPE_WEEKLY_LEADER = "WEEKLY_LEADER"
    TYPE_MONTHLY_CHIEF = "MONTHLY_CHIEF"
    TYPE_CHOICES = [
        (TYPE_WEEKLY_LEADER, "週間リーダ確認"),
        (TYPE_MONTHLY_CHIEF, "月間班長確認"),
    ]

    sheet_code = models.CharField(max_length=40, verbose_name="設備コード")
    sheet_name = models.CharField(max_length=120, verbose_name="設備名")
    target_month = models.DateField(verbose_name="対象月")
    confirm_type = models.CharField(max_length=30, choices=TYPE_CHOICES, verbose_name="確認種別")
    week_index = models.PositiveIntegerField(default=0, verbose_name="週番号")
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="equipment_inspection_confirmations",
        verbose_name="確認者",
    )
    comment = models.TextField(blank=True, default="", verbose_name="コメント")
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="確認日時")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "quality_equipment_inspection_confirmation"
        verbose_name = "設備点検確認"
        verbose_name_plural = "設備点検確認"
        unique_together = [["sheet_code", "target_month", "confirm_type", "week_index"]]
        indexes = [
            models.Index(fields=["sheet_code", "target_month"]),
            models.Index(fields=["target_month", "confirm_type"]),
        ]
        ordering = ["target_month", "confirm_type", "week_index", "id"]

    def __str__(self):
        return f"{self.sheet_code}:{self.target_month}:{self.confirm_type}:{self.week_index}"


class EquipmentInspectionTask(models.Model):
    """設備点検表承認タスク"""

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
        EquipmentInspectionTemplate,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="テンプレート",
    )
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES, verbose_name="タスク種別")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="equipment_inspection_tasks",
        verbose_name="担当者",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name="状態")
    due_date = models.DateField(null=True, blank=True, verbose_name="期限")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    done_at = models.DateTimeField(null=True, blank=True, verbose_name="完了日時")

    class Meta:
        db_table = "quality_equipment_inspection_task"
        verbose_name = "設備点検表タスク"
        verbose_name_plural = "設備点検表タスク"
        indexes = [
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["task_type", "status"]),
            models.Index(fields=["template"]),
        ]
        ordering = ["status", "due_date", "-created_at", "-id"]

    def __str__(self):
        return f"{self.template_id}:{self.task_type}:{self.assigned_to_id}:{self.status}"


class EquipmentInspectionWorkflowLog(models.Model):
    """設備点検表ワークフロー履歴"""

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
        EquipmentInspectionTemplate,
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
        related_name="inspection_template_workflow_logs",
        verbose_name="操作ユーザー",
    )
    comment = models.TextField(blank=True, default="", verbose_name="コメント")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        db_table = "quality_equipment_inspection_workflow_log"
        verbose_name = "設備点検表ワークフロー履歴"
        verbose_name_plural = "設備点検表ワークフロー履歴"
        indexes = [
            models.Index(fields=["template", "created_at"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.template_id}:{self.action}"


__all__ = [
    "ScrapRecord",
    "ScrapRecordDetail",
    "EquipmentInspectionTemplate",
    "EquipmentInspectionItem",
    "EquipmentInspectionItemAttachment",
    "EquipmentInspectionRecord",
    "EquipmentInspectionResult",
    "EquipmentInspectionConfirmation",
    "EquipmentInspectionTask",
    "EquipmentInspectionWorkflowLog",
]
