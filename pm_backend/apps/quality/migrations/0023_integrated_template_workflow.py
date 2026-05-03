from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quality", "0022_processblock_source_pdf"),
    ]

    operations = [
        migrations.AlterField(
            model_name="integratedchecksheettemplate",
            name="status",
            field=models.CharField(
                choices=[
                    ("DRAFT", "下書き"),
                    ("SUPERVISOR_PENDING", "班長確認待ち"),
                    ("CHIEF_PENDING", "係長確認待ち"),
                    ("MANAGER_PENDING", "部長承認待ち"),
                    ("APPROVED", "承認済み"),
                    ("REJECTED", "差戻し"),
                ],
                default="DRAFT",
                max_length=20,
                verbose_name="状態",
            ),
        ),
        migrations.AddField(
            model_name="integratedchecksheettemplate",
            name="rejection_comment",
            field=models.TextField(blank=True, default="", verbose_name="差戻しコメント"),
        ),
    ]
