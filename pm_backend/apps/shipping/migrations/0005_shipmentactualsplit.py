from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shipping', '0004_kubotasakaitripdisplaysetting'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShipmentActualSplit',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('line_no', models.PositiveIntegerField(default=1, verbose_name='行番号')),
                ('production_date', models.DateField(verbose_name='生産日')),
                ('quantity', models.DecimalField(decimal_places=3, max_digits=14, verbose_name='数量')),
                ('source_order_no', models.CharField(blank=True, max_length=50, null=True, verbose_name='注番')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('shipment_actual', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='splits', to='shipping.shipmentactual', verbose_name='出荷実績')),
            ],
            options={
                'verbose_name': '出荷実績内訳',
                'verbose_name_plural': '出荷実績内訳',
                'db_table': 't_shipment_actual_split',
                'ordering': ['shipment_actual_id', 'line_no', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='shipmentactualsplit',
            index=models.Index(fields=['shipment_actual', 'line_no'], name='t_shipment__shipmen_458303_idx'),
        ),
        migrations.AddIndex(
            model_name='shipmentactualsplit',
            index=models.Index(fields=['production_date'], name='t_shipment__product_d39cce_idx'),
        ),
        migrations.AddIndex(
            model_name='shipmentactualsplit',
            index=models.Index(fields=['source_order_no'], name='t_shipment__source__e0d5fe_idx'),
        ),
    ]
