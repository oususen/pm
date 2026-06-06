from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0060_product_stock_location_processing_area'),
        ('production', '0058_plan_deviation_line_config'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StocktakeRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stocktake_date', models.DateField(verbose_name='棚卸日')),
                ('system_stock_qty', models.IntegerField(default=0, verbose_name='机上在庫')),
                ('actual_stock_qty', models.IntegerField(default=0, verbose_name='現物数')),
                ('diff_qty', models.IntegerField(default=0, verbose_name='差異')),
                ('note', models.CharField(blank=True, default='', max_length=255, verbose_name='備考')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('line', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stocktake_records', to='masters.line')),
                ('process', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stocktake_records', to='masters.process')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stocktake_records', to='masters.product')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stocktake_record_updates', to=settings.AUTH_USER_MODEL, verbose_name='更新者')),
            ],
            options={
                'verbose_name': '棚卸現物入力',
                'verbose_name_plural': '棚卸現物入力',
                'db_table': 'production_stocktake_record',
            },
        ),
        migrations.AddConstraint(
            model_name='stocktakerecord',
            constraint=models.UniqueConstraint(fields=('stocktake_date', 'product'), name='uniq_stocktake_record_key'),
        ),
        migrations.AddIndex(
            model_name='stocktakerecord',
            index=models.Index(fields=['stocktake_date', 'updated_at'], name='production_s_stockta_a248cb_idx'),
        ),
        migrations.AddIndex(
            model_name='stocktakerecord',
            index=models.Index(fields=['product', 'stocktake_date'], name='production_s_product_08a4b0_idx'),
        ),
    ]
