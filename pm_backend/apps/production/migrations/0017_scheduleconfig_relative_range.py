from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0016_scheduleconfig_range_dates'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduleconfig',
            name='range_base_day',
            field=models.CharField(choices=[('TODAY', '今日'), ('YESTERDAY', '昨日'), ('TWO_DAYS_AGO', '一昨日')], default='TODAY', max_length=20, verbose_name='計算期間開始基準日'),
        ),
        migrations.AddField(
            model_name='scheduleconfig',
            name='range_days_after',
            field=models.PositiveSmallIntegerField(default=45, verbose_name='計算期間終了日数（基準日から何日後）'),
        ),
    ]
