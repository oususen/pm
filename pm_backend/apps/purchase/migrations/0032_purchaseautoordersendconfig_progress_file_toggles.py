from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0031_purchaseautoordersendhistory'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseautoordersendconfig',
            name='send_progress_excel',
            field=models.BooleanField(default=True, verbose_name='進度表Excel送信'),
        ),
        migrations.AddField(
            model_name='purchaseautoordersendconfig',
            name='send_progress_pdf',
            field=models.BooleanField(default=True, verbose_name='進度表PDF送信'),
        ),
    ]
