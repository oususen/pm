from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0082_mobiledevicehistory'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('production', '0087_linedemand_add_process'),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyProcessTarget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan_date', models.DateField(verbose_name='計画日')),
                ('target_time', models.TimeField(verbose_name='目標時刻')),
                ('target_qty', models.IntegerField(verbose_name='目標台数')),
                ('product_label', models.CharField(max_length=100, verbose_name='製品俗称')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_daily_process_targets', to=settings.AUTH_USER_MODEL, verbose_name='作成者')),
                ('line', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masters.line', verbose_name='ライン')),
                ('process', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masters.process', verbose_name='工程')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_daily_process_targets', to=settings.AUTH_USER_MODEL, verbose_name='更新者')),
            ],
            options={
                'verbose_name': '日別工程目標',
                'verbose_name_plural': '日別工程目標',
                'db_table': 't_daily_process_target',
                'ordering': ['plan_date', 'target_time', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='dailyprocesstarget',
            index=models.Index(fields=['line', 'process', 'plan_date'], name='t_daily_pro_line_id_6d08f8_idx'),
        ),
        migrations.AddIndex(
            model_name='dailyprocesstarget',
            index=models.Index(fields=['plan_date'], name='t_daily_pro_plan_da_462831_idx'),
        ),
    ]
