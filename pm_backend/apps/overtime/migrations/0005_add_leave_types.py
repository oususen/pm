from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('overtime', '0004_alter_overtimeapplication_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='overtimeapplication',
            name='end_date',
            field=models.DateField(blank=True, null=True, verbose_name='終了日（連続有給用）'),
        ),
        migrations.AlterField(
            model_name='overtimeapplication',
            name='application_type',
            field=models.CharField(
                choices=[
                    ('overtime', '時間外'),
                    ('holiday', '休日出勤'),
                    ('half_day_am', '午前半休'),
                    ('half_day_pm', '午後半休'),
                    ('paid_leave', '前日有給'),
                    ('paid_leave_consec', '連続有給'),
                ],
                default='overtime',
                max_length=20,
                verbose_name='申請種別',
            ),
        ),
        migrations.AlterField(
            model_name='overtimeapplication',
            name='start_time',
            field=models.TimeField(blank=True, null=True, verbose_name='残業開始時刻'),
        ),
        migrations.AlterField(
            model_name='overtimeapplication',
            name='end_time',
            field=models.TimeField(blank=True, null=True, verbose_name='残業終了時刻'),
        ),
    ]
