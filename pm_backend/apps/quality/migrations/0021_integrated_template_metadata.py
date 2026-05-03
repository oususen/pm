from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("quality", "0020_integrated_template_add_line"),
    ]

    operations = [
        migrations.AddField(
            model_name="integratedchecksheettemplate",
            name="document_title",
            field=models.CharField(blank=True, default="", max_length=300, verbose_name="帳票タイトル"),
        ),
        migrations.AddField(
            model_name="integratedchecksheettemplate",
            name="sheet_name",
            field=models.CharField(blank=True, default="", max_length=200, verbose_name="元シート名"),
        ),
        migrations.AddField(
            model_name="integratedchecksheettemplate",
            name="revision_notes",
            field=models.TextField(blank=True, default="", verbose_name="改訂内容"),
        ),
        migrations.AddField(
            model_name="integratedchecksheettemplate",
            name="revision_date",
            field=models.DateField(blank=True, null=True, verbose_name="改訂日"),
        ),
        migrations.AddField(
            model_name="integratedchecksheettemplate",
            name="effective_from",
            field=models.DateField(blank=True, null=True, verbose_name="運用開始日"),
        ),
        migrations.AddField(
            model_name="integratedchecksheettemplate",
            name="reviewer_user",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+", to=settings.AUTH_USER_MODEL,
                verbose_name="班長担当",
            ),
        ),
        migrations.AddField(
            model_name="integratedchecksheettemplate",
            name="chief_user",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+", to=settings.AUTH_USER_MODEL,
                verbose_name="係長担当",
            ),
        ),
        migrations.AddField(
            model_name="integratedchecksheettemplate",
            name="approver_user",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+", to=settings.AUTH_USER_MODEL,
                verbose_name="部長担当",
            ),
        ),
    ]
