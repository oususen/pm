from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0062_trip_notice_unique_with_type'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='KubotaSakaiDueAllocationOverride',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('product_code', models.CharField(max_length=50, verbose_name='品番')),
                ('ship_to_code', models.CharField(blank=True, max_length=40, null=True, verbose_name='納入場所コード')),
                ('source_order_no', models.CharField(blank=True, max_length=50, null=True, verbose_name='注番')),
                ('due_date', models.DateField(verbose_name='日付')),
                ('fixed_qty', models.DecimalField(decimal_places=3, default=0, max_digits=14, verbose_name='固定数量')),
                ('updated_at', models.DateTimeField(blank=True, null=True, verbose_name='更新日時')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='kubota_sakai_due_allocation_override_updated', to=settings.AUTH_USER_MODEL, verbose_name='更新者')),
            ],
            options={
                'db_table': 't_kubota_sakai_due_allocation_override',
                'verbose_name': 'クボタ堺納期調整固定',
                'verbose_name_plural': 'クボタ堺納期調整固定',
                'ordering': ['product_code', 'ship_to_code', 'source_order_no', 'due_date'],
            },
        ),
        migrations.AddIndex(
            model_name='kubotasakaidueallocationoverride',
            index=models.Index(fields=['product_code', 'ship_to_code'], name='kbt_due_ovr_prod_ship_idx'),
        ),
        migrations.AddIndex(
            model_name='kubotasakaidueallocationoverride',
            index=models.Index(fields=['due_date'], name='t_kubota_sa_due_dat_106a68_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='kubotasakaidueallocationoverride',
            unique_together={('product_code', 'ship_to_code', 'source_order_no', 'due_date')},
        ),
    ]
