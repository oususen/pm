from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("quality", "0024_rename_idx_intcs_batch_prod_date_quality_int_product_55e2c6_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="integratedchecksheetbatch",
            name="status",
            field=models.CharField(
                choices=[
                    ("OPEN", "実施中"),
                    ("COMPLETED", "完了"),
                    ("LEADER_CONFIRMED", "リーダ確認済"),
                    ("SUPERVISOR_CONFIRMED", "班長確認済"),
                ],
                default="OPEN",
                max_length=20,
                verbose_name="状態",
            ),
        ),
        migrations.AddField(
            model_name="integratedchecksheetbatch",
            name="leader_confirmed_by",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+", to=settings.AUTH_USER_MODEL,
                verbose_name="リーダ確認者",
            ),
        ),
        migrations.AddField(
            model_name="integratedchecksheetbatch",
            name="leader_confirmed_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="リーダ確認日時"),
        ),
        migrations.AddField(
            model_name="integratedchecksheetbatch",
            name="supervisor_confirmed_by",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+", to=settings.AUTH_USER_MODEL,
                verbose_name="班長確認者",
            ),
        ),
        migrations.AddField(
            model_name="integratedchecksheetbatch",
            name="supervisor_confirmed_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="班長確認日時"),
        ),
    ]
