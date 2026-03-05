from django.conf import settings
from django.db import models

from .models_scrap import ScrapRecord, ScrapRecordDetail


class EquipmentInspectionTemplate(models.Model):
    """設備点検表テンプレート（承認ワークフロー付き）"""

    STATUS_DRAFT = "DRAFT"
    STATUS_REVIEW_PENDING = "REVIEW_PENDING"
    STATUS_APPROVAL_PENDING = "APPROVAL_PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "下書き"),
        (STATUS_REVIEW_PENDING, "確認待ち"),
        (STATUS_APPROVAL_PENDING, "承認待ち"),
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
        verbose_name="確認担当",
    )
    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspection_templates_approver",
        verbose_name="承認担当",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspection_templates_reviewed",
        verbose_name="確認実施者",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspection_templates_approved",
        verbose_name="承認実施者",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="確認日時")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="承認日時")
    rejection_comment = models.TextField(blank=True, default="", verbose_name="差戻しコメント")

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


class EquipmentInspectionWorkflowLog(models.Model):
    """設備点検表ワークフロー履歴"""

    ACTION_CREATED = "CREATED"
    ACTION_UPDATED = "UPDATED"
    ACTION_SUBMITTED = "SUBMITTED"
    ACTION_REVIEWED = "REVIEWED"
    ACTION_APPROVED = "APPROVED"
    ACTION_REJECTED = "REJECTED"

    ACTION_CHOICES = [
        (ACTION_CREATED, "作成"),
        (ACTION_UPDATED, "更新"),
        (ACTION_SUBMITTED, "確認依頼"),
        (ACTION_REVIEWED, "確認完了"),
        (ACTION_APPROVED, "承認"),
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
    "EquipmentInspectionWorkflowLog",
]
