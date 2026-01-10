from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0025_fix_scrapdetail_meta'),
    ]

    operations = [
        migrations.AddField(
            model_name='scraprecord',
            name='decided_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='判定日時'),
        ),
        migrations.AddField(
            model_name='scraprecord',
            name='decided_by',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='判定者'),
        ),
        migrations.AddField(
            model_name='scraprecord',
            name='disposition_status',
            field=models.CharField(choices=[('PENDING', '判定待ち'), ('APPROVED', '使用可'), ('REJECTED', '仕損確定'), ('PARTIAL', '一部使用可')], default='PENDING', max_length=20, verbose_name='判定ステータス'),
        ),
        migrations.AddField(
            model_name='scraprecord',
            name='return_qty',
            field=models.DecimalField(decimal_places=3, default=0, max_digits=14, verbose_name='戻し数量'),
        ),
    ]
