import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quality", "0016_restructure_product_checksheet"),
    ]

    operations = [
        migrations.AlterField(
            model_name="productchecksheetfield",
            name="template",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="fields",
                to="quality.productchecksheettemplate",
                verbose_name="テンプレート",
            ),
        ),
        migrations.AlterField(
            model_name="productchecksheetrecord",
            name="template",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="records",
                to="quality.productchecksheettemplate",
                verbose_name="テンプレート",
            ),
        ),
        migrations.AlterField(
            model_name="productchecksheettask",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
        migrations.AlterField(
            model_name="productchecksheetworkflowlog",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
    ]
