from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0058_calendar_created_by_updated_by'),
        ('production', '0069_singleproc_finished_entry'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProcessWorkSessionChangeHistory',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('session_record_id', models.BigIntegerField(db_index=True, verbose_name='対象セッションID')),
                ('operation_type', models.CharField(choices=[('ADD', '追加'), ('UPDATE', '変更')], max_length=10, verbose_name='操作区分')),
                ('product_code', models.CharField(blank=True, default='', max_length=50, verbose_name='品番')),
                ('product_name', models.CharField(blank=True, default='', max_length=100, verbose_name='品名')),
                ('plan_date', models.DateField(blank=True, null=True, verbose_name='作業日')),
                ('reason', models.TextField(verbose_name='変更理由')),
                ('change_summary', models.TextField(verbose_name='変更内容')),
                ('before_data', models.JSONField(blank=True, default=dict, verbose_name='変更前データ')),
                ('after_data', models.JSONField(blank=True, default=dict, verbose_name='変更後データ')),
                ('changed_at', models.DateTimeField(auto_now_add=True, verbose_name='変更時刻')),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='process_work_session_change_histories', to=settings.AUTH_USER_MODEL, verbose_name='変更者')),
                ('process', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='masters.process', verbose_name='工程')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='masters.product', verbose_name='製品')),
                ('session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='change_histories', to='production.processworksession', verbose_name='対象セッション')),
            ],
            options={
                'verbose_name': '工程作業セッション変更履歴',
                'verbose_name_plural': '工程作業セッション変更履歴',
                'db_table': 't_process_work_session_change_history',
                'ordering': ['-changed_at', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='processworksessionchangehistory',
            index=models.Index(fields=['session_record_id', 'changed_at'], name='t_pwschg_sid_changed_idx'),
        ),
        migrations.AddIndex(
            model_name='processworksessionchangehistory',
            index=models.Index(fields=['operation_type', 'changed_at'], name='t_pwschg_type_changed_idx'),
        ),
    ]
