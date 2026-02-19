from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0015_linebacklog_is_stocktake_fix'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduleconfig',
            name='range_end_date',
            field=models.DateField(blank=True, null=True, verbose_name='計算期間終了日'),
        ),
        migrations.AddField(
            model_name='scheduleconfig',
            name='range_start_date',
            field=models.DateField(blank=True, null=True, verbose_name='計算期間開始日'),
        ),
    ]
