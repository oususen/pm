from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0028_purchaseautoordersendconfig_safety_stock'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseautoordersendconfig',
            name='send_delivery_note_pdf',
            field=models.BooleanField(default=True, verbose_name='外作納品書PDF送信'),
        ),
    ]
