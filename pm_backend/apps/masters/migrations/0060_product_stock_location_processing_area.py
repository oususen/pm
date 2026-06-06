from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0059_supplier_supplier_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='processing_area',
            field=models.CharField(blank=True, choices=[('LASER', 'レーザ'), ('BRAKE', 'ブレーキ'), ('NUT', 'ナット'), ('WELD', '溶接'), ('SPOT', 'スポット'), ('ASSY', '組立'), ('OTHER', 'その他')], max_length=20, null=True, verbose_name='加工先'),
        ),
        migrations.AddField(
            model_name='product',
            name='stock_location',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='保管場所'),
        ),
    ]
