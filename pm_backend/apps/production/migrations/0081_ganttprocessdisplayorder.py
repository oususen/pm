from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0066_containercapacityimage'),
        ('production', '0080_add_finished_ct_use_adjusted'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GanttProcessDisplayOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display_order', models.IntegerField(default=0, verbose_name='表示順')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('line', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gantt_process_display_orders', to='masters.line', verbose_name='ライン')),
                ('process', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gantt_process_display_orders', to='masters.process', verbose_name='工程')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gantt_process_display_orders', to=settings.AUTH_USER_MODEL, verbose_name='更新者')),
            ],
            options={
                'verbose_name': 'ガント工程表示順',
                'verbose_name_plural': 'ガント工程表示順',
                'db_table': 't_gantt_process_display_order',
                'ordering': ['line_id', 'display_order', 'process_id'],
            },
        ),
        migrations.AddIndex(
            model_name='ganttprocessdisplayorder',
            index=models.Index(fields=['line', 'display_order'], name='t_gantt_pro_line_id_4fdc2d_idx'),
        ),
        migrations.AddIndex(
            model_name='ganttprocessdisplayorder',
            index=models.Index(fields=['process'], name='t_gantt_pro_process_f9d6ec_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='ganttprocessdisplayorder',
            unique_together={('line', 'process')},
        ),
    ]
