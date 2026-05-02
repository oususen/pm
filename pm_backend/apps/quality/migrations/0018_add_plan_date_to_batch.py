from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quality", "0017_alter_checksheet_field_template_nonnull"),
    ]

    operations = [
        migrations.AddField(
            model_name="productchecksheetbatch",
            name="plan_date",
            field=models.DateField(blank=True, null=True, verbose_name="計画日"),
        ),
        migrations.AddIndex(
            model_name="productchecksheetbatch",
            index=models.Index(
                fields=["plan_date", "line", "process", "product"],
                name="quality_pro_plan_da_idx",
            ),
        ),
    ]
