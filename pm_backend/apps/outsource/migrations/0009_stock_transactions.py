from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('outsource', '0008_materialrequirement_shipment_flags'),
    ]

    operations = [
        migrations.CreateModel(
            name='MaterialStockTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('material_code', models.CharField(db_index=True, max_length=50, verbose_name='材料コード')),
                ('material_name', models.CharField(blank=True, default='', max_length=200, verbose_name='材料名称')),
                ('qty_change', models.IntegerField(verbose_name='増減数量（個）')),
                ('tx_type', models.CharField(choices=[('RECEIPT', '入庫'), ('ISSUE', '出庫'), ('ADJUST', '棚卸調整')], max_length=20, verbose_name='区分')),
                ('tx_date', models.DateField(verbose_name='取引日')),
                ('reason', models.CharField(blank=True, default='', max_length=200, verbose_name='理由')),
                ('ref_type', models.CharField(blank=True, default='', max_length=50, verbose_name='参照種別')),
                ('ref_id', models.IntegerField(blank=True, null=True, verbose_name='参照ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': '材料在庫トランザクション',
                'verbose_name_plural': '材料在庫トランザクション',
                'db_table': 'outsource_material_stock_tx',
                'ordering': ['-tx_date', '-id'],
            },
        ),
        migrations.CreateModel(
            name='ProductStockTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_code', models.CharField(db_index=True, max_length=50, verbose_name='品目コード')),
                ('item_name', models.CharField(blank=True, default='', max_length=200, verbose_name='品目名称')),
                ('qty_change', models.IntegerField(verbose_name='増減数量（個）')),
                ('tx_type', models.CharField(choices=[('RECEIPT', '入庫'), ('SHIP', '出庫'), ('ADJUST', '棚卸調整')], max_length=20, verbose_name='区分')),
                ('tx_date', models.DateField(verbose_name='取引日')),
                ('reason', models.CharField(blank=True, default='', max_length=200, verbose_name='理由')),
                ('ref_type', models.CharField(blank=True, default='', max_length=50, verbose_name='参照種別')),
                ('ref_id', models.IntegerField(blank=True, null=True, verbose_name='参照ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': '完成品在庫トランザクション',
                'verbose_name_plural': '完成品在庫トランザクション',
                'db_table': 'outsource_product_stock_tx',
                'ordering': ['-tx_date', '-id'],
            },
        ),
    ]

