from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("masters", "0047_routingstep_supplier"),
        ("quality", "0019_integrated_checksheet"),
    ]

    operations = [
        migrations.AddField(
            model_name="integratedchecksheettemplate",
            name="line",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="integrated_checksheet_templates",
                to="masters.line",
                verbose_name="ライン",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="integratedchecksheettemplate",
            unique_together={("product", "line", "version")},
        ),
    ]
