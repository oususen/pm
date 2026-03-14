from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('overtime', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='overtimeapplication',
            name='work_start_time',
            field=models.TimeField(blank=True, null=True, verbose_name='勤務開始時刻'),
        ),
        migrations.AddField(
            model_name='overtimeapplication',
            name='scheduled_end_time',
            field=models.TimeField(blank=True, null=True, verbose_name='定時終了時刻'),
        ),
    ]
