from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0025_auto_order_send_progress_window'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseautoordersendconfig',
            name='delivery_day_mode',
            field=models.CharField(
                choices=[('PATTERN', '納入パターン'), ('SUPPLIER_CALENDAR', '仕入れ先カレンダ')],
                default='PATTERN',
                max_length=30,
                verbose_name='納入日判定方式',
            ),
        ),
    ]
