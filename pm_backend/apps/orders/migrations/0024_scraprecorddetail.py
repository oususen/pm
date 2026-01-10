from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0023_scrap_replenish_flag'),
        ('masters', '0021_routingstep_parallel_group'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScrapRecordDetail',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('product_code', models.CharField(blank=True, db_index=True, max_length=50, null=True, verbose_name='製品コード')),
                ('product_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='品名')),
                ('process_id', models.BigIntegerField(blank=True, null=True, verbose_name='工程ID')),
                ('line_id', models.BigIntegerField(blank=True, null=True, verbose_name='ラインID')),
                ('supplier_id', models.BigIntegerField(blank=True, null=True, verbose_name='仕入先ID')),
                ('sourcing_type', models.CharField(blank=True, max_length=20, null=True, verbose_name='調達区分')),
                ('deduct_qty', models.DecimalField(decimal_places=3, default=0, max_digits=14, verbose_name='減算数量')),
                ('is_replenished', models.BooleanField(default=False, verbose_name='補充完了')),
                ('replenished_at', models.DateTimeField(blank=True, null=True, verbose_name='補充完了日時')),
                ('replenished_by', models.CharField(blank=True, max_length=50, null=True, verbose_name='補充完了者')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='masters.product', verbose_name='製品')),
                ('scrap_record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='details', to='orders.scraprecord', verbose_name='仕損記録')),
            ],
            options={
                'verbose_name': '仕損記録明細',
                'verbose_name_plural': '仕損記録明細',
                'db_table': 't_scrap_record_detail',
            },
        ),
    ]
