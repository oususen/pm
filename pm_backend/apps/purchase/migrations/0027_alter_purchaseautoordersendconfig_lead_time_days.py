from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0026_purchaseautoordersendconfig_delivery_day_mode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='purchaseautoordersendconfig',
            name='lead_time_days',
            field=models.PositiveSmallIntegerField(default=5, verbose_name='納入日（何営業日後）'),
        ),
    ]
