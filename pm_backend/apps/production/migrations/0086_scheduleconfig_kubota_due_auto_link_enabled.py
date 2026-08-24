from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0085_add_order_qty_actual'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduleconfig',
            name='kubota_due_auto_link_enabled',
            field=models.BooleanField(default=True, verbose_name='クボタ堺納期調整 自動紐づけ有効'),
        ),
    ]
