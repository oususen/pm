from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0091_rename_other_reason_codes'),
        ('production', '0121_brakelinerecord_interruption_reason_code_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProgressMonitorTarget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display_order', models.IntegerField(default=0, verbose_name='表示順')),
                ('memo', models.CharField(blank=True, default='', max_length=500, verbose_name='メモ')),
                ('is_active', models.BooleanField(default=True, verbose_name='有効')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='登録日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('line', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress_monitor_targets', to='masters.line', verbose_name='ライン')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress_monitor_targets', to='masters.product', verbose_name='製品')),
                ('registered_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='registered_progress_monitor_targets', to=settings.AUTH_USER_MODEL, verbose_name='登録者')),
            ],
            options={
                'verbose_name': '進度監視対象',
                'verbose_name_plural': '進度監視対象',
                'db_table': 'production_progress_monitor_target',
                'ordering': ['display_order', 'line__line_code', 'product__product_code', 'id'],
                'unique_together': {('product', 'line')},
            },
        ),
    ]
