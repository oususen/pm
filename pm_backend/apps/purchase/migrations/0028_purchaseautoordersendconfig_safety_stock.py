import decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0027_alter_purchaseautoordersendconfig_lead_time_days'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseautoordersendconfig',
            name='safety_stock_enabled',
            field=models.BooleanField(default=False, verbose_name='安全在庫確保'),
        ),
        migrations.AddField(
            model_name='purchaseautoordersendconfig',
            name='safety_stock_multiplier',
            field=models.DecimalField(
                decimal_places=1,
                default=decimal.Decimal('1'),
                max_digits=5,
                verbose_name='安全在庫倍数',
            ),
        ),
    ]
