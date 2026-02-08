from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0001_initial'),
        ('production', '0009_linebacklog_sequence_default_zero'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LineDefaultScheduleSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('final_process_start_time', models.TimeField(blank=True, null=True, verbose_name='最終工程開始時刻（デフォルト）')),
                ('adjust_to_break_end', models.BooleanField(default=True, verbose_name='休憩明けに補正')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('line', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='default_schedule_setting', to='masters.line', verbose_name='ライン')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='line_default_schedule_settings', to=settings.AUTH_USER_MODEL, verbose_name='更新者')),
            ],
            options={
                'verbose_name': 'ラインデフォルトスケジュール設定',
                'verbose_name_plural': 'ラインデフォルトスケジュール設定',
                'db_table': 't_line_default_schedule_setting',
            },
        ),
        migrations.AddIndex(
            model_name='linedefaultschedulesetting',
            index=models.Index(fields=['line'], name='t_line_def_line_id_98e996_idx'),
        ),
    ]
