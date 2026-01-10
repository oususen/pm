from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0006_bomitem_process_line_time'),
        ('orders', '0004_alter_order_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='LinePlan',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('plan_date', models.DateField(verbose_name='計画日')),
                ('product_code', models.CharField(max_length=50, verbose_name='製品コード')),
                ('quantity', models.DecimalField(decimal_places=3, max_digits=14, verbose_name='数量')),
                ('remark', models.CharField(blank=True, max_length=200, null=True, verbose_name='備考')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('line', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='masters.line', verbose_name='ライン')),
                ('source_order_line', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='orders.orderline', verbose_name='元受注明細')),
            ],
            options={
                'verbose_name': 'ライン生産計画',
                'verbose_name_plural': 'ライン生産計画',
                'db_table': 't_line_plan',
            },
        ),
        migrations.AddIndex(
            model_name='lineplan',
            index=models.Index(fields=['line', 'plan_date'], name='idx_line_plan_date'),
        ),
        migrations.AddIndex(
            model_name='lineplan',
            index=models.Index(fields=['product_code'], name='idx_line_plan_product'),
        ),
    ]
