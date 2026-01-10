from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0026_scrap_disposition_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scraprecord',
            name='disposition_status',
            field=models.CharField(choices=[('PENDING', '判定待ち'), ('APPROVED', '使用可'), ('REJECTED', '仕損確定'), ('PARTIAL', '一部使用可')], default='REJECTED', max_length=20, verbose_name='判定ステータス'),
        ),
    ]
