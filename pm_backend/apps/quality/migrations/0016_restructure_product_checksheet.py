"""
ProductChecksheetTemplateVersion を廃止し、Template に統合。
承認ワークフローフィールド、Task、WorkflowLog を追加。
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_version_to_template(apps, schema_editor):
    """既存の Version データを Template に統合する"""
    Template = apps.get_model("quality", "ProductChecksheetTemplate")
    Version = apps.get_model("quality", "ProductChecksheetTemplateVersion")
    Field = apps.get_model("quality", "ProductChecksheetField")
    Record = apps.get_model("quality", "ProductChecksheetRecord")
    Batch = apps.get_model("quality", "ProductChecksheetBatch")

    for tmpl in Template.objects.all():
        active_ver = Version.objects.filter(template=tmpl).order_by("-version_no").first()
        if not active_ver:
            continue

        tmpl.version = active_ver.version_no
        tmpl.status = "APPROVED" if active_ver.status == "ACTIVE" else "DRAFT"
        tmpl.document_title = active_ver.document_title or ""
        tmpl.sheet_name = active_ver.sheet_name or ""
        tmpl.revision_date = active_ver.revision_date
        tmpl.revision_notes = active_ver.revision_notes or ""
        tmpl.effective_from = active_ver.effective_from
        tmpl.source_type = active_ver.source_type or "image"
        tmpl.source_pdf = active_ver.source_pdf.name if active_ver.source_pdf else ""
        tmpl.source_image = active_ver.source_image.name if active_ver.source_image else ""
        tmpl.background_image = active_ver.background_image.name if active_ver.background_image else ""
        tmpl.background_width = active_ver.background_width or 1200
        tmpl.background_height = active_ver.background_height or 1600
        tmpl.editor_notes = getattr(active_ver, "editor_notes", "") or ""
        tmpl.save()

        # Field の FK を version → template に移行
        Field.objects.filter(version=active_ver).update(template=tmpl)

        # Record の FK を template_version → template に移行
        Record.objects.filter(template_version=active_ver).update(template=tmpl)

    # Batch の template_version FK はドロップするだけ（template FK は既にある）


class Migration(migrations.Migration):

    dependencies = [
        ("quality", "0015_productchecksheettemplateversion_document_title_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ===== 1. Template に新フィールドを追加 =====
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="version",
            field=models.PositiveIntegerField(default=1, verbose_name="版"),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="status",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("DRAFT", "下書き"),
                    ("SUPERVISOR_PENDING", "班長確認待ち"),
                    ("CHIEF_PENDING", "係長確認待ち"),
                    ("MANAGER_PENDING", "部長承認待ち"),
                    ("APPROVED", "承認済み"),
                    ("REJECTED", "差戻し"),
                ],
                default="DRAFT",
                verbose_name="ステータス",
            ),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="document_title",
            field=models.CharField(max_length=200, blank=True, default="", verbose_name="帳票タイトル"),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="sheet_name",
            field=models.CharField(max_length=120, blank=True, default="", verbose_name="元シート名"),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="revision_date",
            field=models.DateField(null=True, blank=True, verbose_name="改訂日"),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="revision_notes",
            field=models.TextField(blank=True, default="", verbose_name="改訂内容"),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="effective_from",
            field=models.DateField(null=True, blank=True, verbose_name="運用開始日"),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="source_type",
            field=models.CharField(
                max_length=20,
                choices=[("pdf", "PDF台紙"), ("image", "画像台紙")],
                default="image",
                verbose_name="台紙種別",
            ),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="source_pdf",
            field=models.FileField(upload_to="product_checksheets/source_pdf/", blank=True, verbose_name="台紙PDF"),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="source_image",
            field=models.ImageField(upload_to="product_checksheets/source_image/", blank=True, verbose_name="台紙画像"),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="background_image",
            field=models.ImageField(upload_to="product_checksheets/background/", blank=True, verbose_name="編集用背景画像"),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="background_width",
            field=models.PositiveIntegerField(default=1200, verbose_name="背景幅"),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="background_height",
            field=models.PositiveIntegerField(default=1600, verbose_name="背景高さ"),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="editor_notes",
            field=models.TextField(blank=True, default="", verbose_name="編集メモ"),
        ),
        # 承認ワークフロー: 担当者
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="reviewer_user",
            field=models.ForeignKey(
                null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="product_checksheet_templates_reviewer",
                to=settings.AUTH_USER_MODEL, verbose_name="班長担当",
            ),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="chief_user",
            field=models.ForeignKey(
                null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="product_checksheet_templates_chief",
                to=settings.AUTH_USER_MODEL, verbose_name="係長担当",
            ),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="approver_user",
            field=models.ForeignKey(
                null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="product_checksheet_templates_approver",
                to=settings.AUTH_USER_MODEL, verbose_name="部長担当",
            ),
        ),
        # 承認ワークフロー: 実施者
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="reviewed_by",
            field=models.ForeignKey(
                null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="product_checksheet_templates_reviewed",
                to=settings.AUTH_USER_MODEL, verbose_name="班長確認実施者",
            ),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="chief_reviewed_by",
            field=models.ForeignKey(
                null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="product_checksheet_templates_chief_reviewed",
                to=settings.AUTH_USER_MODEL, verbose_name="係長確認実施者",
            ),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="approved_by",
            field=models.ForeignKey(
                null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="product_checksheet_templates_approved",
                to=settings.AUTH_USER_MODEL, verbose_name="部長承認実施者",
            ),
        ),
        # 承認ワークフロー: タイムスタンプ
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="reviewed_at",
            field=models.DateTimeField(null=True, blank=True, verbose_name="班長確認日時"),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="chief_reviewed_at",
            field=models.DateTimeField(null=True, blank=True, verbose_name="係長確認日時"),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="approved_at",
            field=models.DateTimeField(null=True, blank=True, verbose_name="部長承認日時"),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="rejection_comment",
            field=models.TextField(blank=True, default="", verbose_name="差戻しコメント"),
        ),
        migrations.AddField(
            model_name="productchecksheettemplate",
            name="submitted_fields_snapshot",
            field=models.JSONField(null=True, blank=True, verbose_name="提出時配置項目スナップショット"),
        ),

        # ===== 2. Field に template FK を追加（null許可、後で not null にする） =====
        migrations.AddField(
            model_name="productchecksheetfield",
            name="template",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="fields",
                to="quality.productchecksheettemplate",
                verbose_name="テンプレート",
            ),
        ),

        # ===== 3. Record に template FK を追加 =====
        migrations.AddField(
            model_name="productchecksheetrecord",
            name="template",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="records",
                to="quality.productchecksheettemplate",
                verbose_name="テンプレート",
            ),
        ),

        # ===== 4. データ移行 =====
        migrations.RunPython(migrate_version_to_template, migrations.RunPython.noop),

        # ===== 5. 旧 index 削除（version FK 削除前に行う） =====
        migrations.RemoveIndex(
            model_name="productchecksheetfield",
            name="quality_pro_version_3a07ef_idx",
        ),

        # ===== 6. 旧FK削除 & unique_together 更新 =====
        # Field: version FK を削除
        migrations.AlterUniqueTogether(
            name="productchecksheetfield",
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name="productchecksheetfield",
            name="version",
        ),
        migrations.AlterUniqueTogether(
            name="productchecksheetfield",
            unique_together={("template", "key")},
        ),

        # Record: template_version FK を削除
        migrations.RemoveField(
            model_name="productchecksheetrecord",
            name="template_version",
        ),

        # Batch: template_version FK を削除
        migrations.RemoveField(
            model_name="productchecksheetbatch",
            name="template_version",
        ),

        # ===== 6. TemplateVersion テーブル削除 =====
        migrations.AlterUniqueTogether(
            name="productchecksheettemplateversion",
            unique_together=set(),
        ),
        migrations.DeleteModel(
            name="ProductChecksheetTemplateVersion",
        ),

        # ===== 7. Template の Meta 更新 =====
        migrations.AlterModelOptions(
            name="productchecksheettemplate",
            options={
                "ordering": ["-updated_at", "-id"],
                "verbose_name": "製品チェックシートテンプレート",
                "verbose_name_plural": "製品チェックシートテンプレート",
            },
        ),
        # 旧 unique_together 削除
        migrations.AlterUniqueTogether(
            name="productchecksheettemplate",
            unique_together={("line", "process", "product", "version")},
        ),
        # Index 追加
        migrations.AddIndex(
            model_name="productchecksheettemplate",
            index=models.Index(fields=["status", "is_active"], name="quality_pro_status_7cf9c8_idx"),
        ),
        # Field の index 更新
        migrations.AddIndex(
            model_name="productchecksheetfield",
            index=models.Index(fields=["template", "sort_order"], name="quality_pro_templat_b5c060_idx"),
        ),

        # ===== 8. 新モデル作成 =====
        migrations.CreateModel(
            name="ProductChecksheetTask",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("task_type", models.CharField(
                    max_length=30,
                    choices=[
                        ("SUPERVISOR_REVIEW", "班長確認"),
                        ("CHIEF_REVIEW", "係長確認"),
                        ("MANAGER_APPROVE", "部長承認"),
                        ("CREATOR_FIX", "差戻し修正"),
                    ],
                    verbose_name="タスク種別",
                )),
                ("status", models.CharField(
                    max_length=20,
                    choices=[("PENDING", "未対応"), ("DONE", "完了"), ("SKIPPED", "スキップ")],
                    default="PENDING",
                    verbose_name="状態",
                )),
                ("due_date", models.DateField(null=True, blank=True, verbose_name="期限")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="作成日時")),
                ("done_at", models.DateTimeField(null=True, blank=True, verbose_name="完了日時")),
                ("template", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="tasks",
                    to="quality.productchecksheettemplate",
                    verbose_name="テンプレート",
                )),
                ("assigned_to", models.ForeignKey(
                    null=True, blank=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="product_checksheet_tasks",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="担当者",
                )),
            ],
            options={
                "db_table": "quality_product_checksheet_task",
                "verbose_name": "製品チェックシートタスク",
                "verbose_name_plural": "製品チェックシートタスク",
                "ordering": ["status", "due_date", "-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="productchecksheettask",
            index=models.Index(fields=["assigned_to", "status"], name="quality_pro_assigne_9ec591_idx"),
        ),
        migrations.AddIndex(
            model_name="productchecksheettask",
            index=models.Index(fields=["task_type", "status"], name="quality_pro_task_ty_64ddcb_idx"),
        ),
        migrations.AddIndex(
            model_name="productchecksheettask",
            index=models.Index(fields=["template"], name="quality_pro_templat_90d844_idx"),
        ),

        migrations.CreateModel(
            name="ProductChecksheetWorkflowLog",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(
                    max_length=20,
                    choices=[
                        ("CREATED", "作成"),
                        ("UPDATED", "更新"),
                        ("SUBMITTED", "確認依頼"),
                        ("SUPERVISOR_REVIEWED", "班長確認完了"),
                        ("CHIEF_REVIEWED", "係長確認完了"),
                        ("APPROVED", "部長承認"),
                        ("REJECTED", "差戻し"),
                    ],
                    verbose_name="操作",
                )),
                ("from_status", models.CharField(max_length=20, blank=True, default="", verbose_name="遷移前")),
                ("to_status", models.CharField(max_length=20, blank=True, default="", verbose_name="遷移後")),
                ("comment", models.TextField(blank=True, default="", verbose_name="コメント")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="作成日時")),
                ("template", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="workflow_logs",
                    to="quality.productchecksheettemplate",
                    verbose_name="テンプレート",
                )),
                ("actor", models.ForeignKey(
                    null=True, blank=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="product_checksheet_workflow_logs",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="操作ユーザー",
                )),
            ],
            options={
                "db_table": "quality_product_checksheet_workflow_log",
                "verbose_name": "製品チェックシートワークフロー履歴",
                "verbose_name_plural": "製品チェックシートワークフロー履歴",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="productchecksheetworkflowlog",
            index=models.Index(fields=["template", "created_at"], name="quality_pro_templat_3629bf_idx"),
        ),

    ]
