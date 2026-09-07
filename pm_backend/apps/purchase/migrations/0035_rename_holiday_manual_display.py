# 注文書自動送信履歴の表示名を「休日手動実行」に変更する。

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0034_purchaseautoordersendconfig_send_order_pdf'),
    ]

    operations = [
        migrations.AlterField(
            model_name='purchaseautoordersendhistory',
            name='trigger_type',
            field=models.CharField(choices=[('SCHEDULED', '自動実行'), ('MANUAL', '手動実行'), ('HOLIDAY_TRIAL', '休日手動実行')], default='SCHEDULED', max_length=20, verbose_name='実行種別'),
        ),
    ]
