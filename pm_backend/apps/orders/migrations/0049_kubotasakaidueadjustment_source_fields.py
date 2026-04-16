from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0048_kubotasakaitripassignment'),
    ]

    operations = [
        migrations.AddField(
            model_name='kubotasakaidueadjustment',
            name='source_order_no',
            field=models.CharField(max_length=50, null=True, blank=True, verbose_name='元注番'),
        ),
        migrations.AddField(
            model_name='kubotasakaidueadjustment',
            name='source_due_date',
            field=models.DateField(null=True, blank=True, verbose_name='元納期'),
        ),
        migrations.AddField(
            model_name='kubotasakaidueadjustment',
            name='source_qty',
            field=models.DecimalField(max_digits=14, decimal_places=3, default=0, verbose_name='元数量'),
        ),
        migrations.AddField(
            model_name='kubotasakaidueadjustment',
            name='ship_to_code',
            field=models.CharField(max_length=40, null=True, blank=True, verbose_name='納入場所コード'),
        ),
        migrations.AddField(
            model_name='kubotasakaidueadjustment',
            name='ship_to_name',
            field=models.CharField(max_length=100, null=True, blank=True, verbose_name='納入場所名'),
        ),
        migrations.AddIndex(
            model_name='kubotasakaidueadjustment',
            index=models.Index(fields=['ship_to_code', 'source_order_no'], name='kbt_saki_due_shipto_ord_idx'),
        ),
    ]
