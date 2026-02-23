from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0031_alter_calendar_options_alter_line_options_and_more'),
        ('production', '0023_expand_schedule_task_choices'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LineBacklogAdjustment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan_date', models.DateField(verbose_name='対象日')),
                ('adjust_type', models.CharField(choices=[('STOCK', '在庫調整'), ('PLANNED_STOCK', '計画在庫調整'), ('PROGRESS', '進度調整'), ('PLANNED_PROGRESS', '計画進度調整')], max_length=30, verbose_name='調整種別')),
                ('adjust_qty', models.IntegerField(default=0, verbose_name='調整値')),
                ('reason', models.CharField(blank=True, default='', max_length=255, verbose_name='理由')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('line', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='backlog_adjustments', to='masters.line')),
                ('process', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='backlog_adjustments', to='masters.process')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='backlog_adjustments', to='masters.product')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='line_backlog_adjustments_updates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'ラインバックログ調整',
                'verbose_name_plural': 'ラインバックログ調整',
                'db_table': 'production_line_backlog_adjustment',
            },
        ),
        migrations.AddIndex(
            model_name='linebacklogadjustment',
            index=models.Index(fields=['line', 'plan_date', 'adjust_type'], name='production__line_id_6bd426_idx'),
        ),
        migrations.AddIndex(
            model_name='linebacklogadjustment',
            index=models.Index(fields=['product', 'plan_date'], name='production__product_39f39c_idx'),
        ),
        migrations.AddConstraint(
            model_name='linebacklogadjustment',
            constraint=models.UniqueConstraint(fields=('line', 'product', 'process', 'plan_date', 'adjust_type'), name='uniq_line_backlog_adjustment_key'),
        ),
    ]
