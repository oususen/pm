from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0021_routingstep_parallel_group'),
        ('orders', '0020_line_gantt_plan'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScrapRecord',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('product_code', models.CharField(blank=True, db_index=True, max_length=50, null=True, verbose_name='製品コード')),
                ('product_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='品名')),
                ('qty', models.DecimalField(decimal_places=3, default=0, max_digits=14, verbose_name='仕損数量')),
                ('recorded_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='記録時刻')),
                ('reason', models.CharField(blank=True, max_length=100, null=True, verbose_name='理由/区分')),
                ('batch_no', models.CharField(blank=True, max_length=100, null=True, verbose_name='ロット番号')),
                ('operator_name', models.CharField(blank=True, max_length=50, null=True, verbose_name='作業者名')),
                ('remarks', models.TextField(blank=True, null=True, verbose_name='備考')),
                ('line', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='masters.line', verbose_name='ライン')),
                ('process', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='masters.process', verbose_name='工程')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='masters.product', verbose_name='製品')),
            ],
            options={
                'verbose_name': '仕損記録',
                'verbose_name_plural': '仕損記録',
                'db_table': 't_scrap_record',
                'ordering': ['-recorded_at'],
            },
        ),
        migrations.AddIndex(
            model_name='scraprecord',
            index=models.Index(fields=['process', 'recorded_at'], name='orders_scr_process_2d11e6_idx'),
        ),
        migrations.AddIndex(
            model_name='scraprecord',
            index=models.Index(fields=['line', 'recorded_at'], name='orders_scr_line_id_23aeaf_idx'),
        ),
    ]
