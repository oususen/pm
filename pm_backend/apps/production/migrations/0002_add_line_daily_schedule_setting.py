# Generated manually for LineDailyScheduleSetting

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0001_initial'),
        ('masters', '0027_alter_capacity_nullable'),
    ]

    operations = [
        migrations.CreateModel(
            name='LineDailyScheduleSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan_date', models.DateField(verbose_name='計画日')),
                ('final_process_start_time', models.TimeField(blank=True, null=True, verbose_name='最終工程開始時刻')),
                ('adjust_to_break_end', models.BooleanField(default=True, verbose_name='休憩時間終了に調整')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('line', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_schedule_settings', to='masters.line')),
            ],
            options={
                'db_table': 'line_daily_schedule_setting',
                'ordering': ['plan_date', 'line'],
            },
        ),
        migrations.AddIndex(
            model_name='linedailyschedule setting',
            index=models.Index(fields=['line', 'plan_date'], name='line_daily_line_id_plan_date_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='linedailyschedulesetting',
            unique_together={('line', 'plan_date')},
        ),
    ]
