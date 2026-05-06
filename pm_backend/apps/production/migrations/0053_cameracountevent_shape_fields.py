from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("production", "0052_cameracountevent_productionresultdaily"),
    ]

    operations = [
        migrations.AddField(
            model_name="cameracountevent",
            name="shape_code",
            field=models.CharField(blank=True, default="", max_length=64, verbose_name="形状コード"),
        ),
        migrations.AddField(
            model_name="cameracountevent",
            name="shape_confidence",
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=6, null=True, verbose_name="形状信頼度"),
        ),
    ]

