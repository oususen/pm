from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0009_drop_legacy_routing_step_output'),
        ('orders', '0007_delete_lineplan'),
    ]

    operations = [
        migrations.CreateModel(
            name='LineDemand',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('product_code', models.CharField(max_length=50, verbose_name='製品コード')),
                ('plan_date', models.DateField(verbose_name='必要日')),
                ('lead_time_days', models.IntegerField(default=0, verbose_name='リードタイム(日)')),
                ('forecast_qty', models.DecimalField(decimal_places=3, default=0, max_digits=14, verbose_name='内示数量')),
                ('firm_qty', models.DecimalField(decimal_places=3, default=0, max_digits=14, verbose_name='確定数量')),
                ('plan_qty', models.DecimalField(decimal_places=3, default=0, max_digits=14, verbose_name='計画数')),
                ('actual_qty', models.DecimalField(decimal_places=3, default=0, max_digits=14, verbose_name='実績数')),
                ('plan_progress', models.DecimalField(decimal_places=3, default=0, max_digits=9, verbose_name='計画進度')),
                ('actual_progress', models.DecimalField(decimal_places=3, default=0, max_digits=9, verbose_name='実績進度')),
                ('order_numbers', models.CharField(blank=True, default='', max_length=500, verbose_name='展開元受注番号')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('line', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masters.line', verbose_name='ライン')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='masters.product', verbose_name='製品')),
                ('routing_step', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='masters.routingstep', verbose_name='ルーティング工程')),
            ],
            options={
                'verbose_name': 'ライン需要展開',
                'verbose_name_plural': 'ライン需要展開',
                'db_table': 't_line_demand',
                'unique_together': {('line', 'product_code', 'plan_date')},
            },
        ),
        migrations.AddIndex(
            model_name='linedemand',
            index=models.Index(fields=['line', 'plan_date'], name='idx_linedemand_line_date'),
        ),
        migrations.AddIndex(
            model_name='linedemand',
            index=models.Index(fields=['product_code'], name='idx_linedemand_product'),
        ),
    ]
