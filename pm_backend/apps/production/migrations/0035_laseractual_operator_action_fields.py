from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0034_laser_actual_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='laseractual',
            name='operator_action',
            field=models.CharField(
                choices=[
                    ('START', '開始'),
                    ('END', '終了'),
                    ('PAUSE', '中断'),
                    ('TEMP_END', '一時終了'),
                    ('RESUME', '再開'),
                ],
                default='END',
                max_length=20,
                verbose_name='作業時刻',
            ),
        ),
        migrations.AddField(
            model_name='laseractual',
            name='operator_action_reason',
            field=models.CharField(
                blank=True,
                default='',
                max_length=200,
                verbose_name='作業時刻理由',
            ),
        ),
    ]
