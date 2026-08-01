from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0057_add_container_to_trip_assignment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ShippingTripNotice',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('business_type', models.CharField(max_length=40, verbose_name='業務種別')),
                ('customer_code', models.CharField(max_length=20, verbose_name='得意先コード')),
                ('departure_date', models.DateField(verbose_name='出発日')),
                ('trip_ref', models.CharField(max_length=80, verbose_name='便参照キー')),
                ('notice_text', models.CharField(blank=True, default='', max_length=200, verbose_name='連絡メモ')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='shipping_trip_notices', to=settings.AUTH_USER_MODEL, verbose_name='更新者')),
            ],
            options={
                'verbose_name': '出荷便連絡メモ',
                'verbose_name_plural': '出荷便連絡メモ',
                'db_table': 't_shipping_trip_notice',
                'unique_together': {('business_type', 'customer_code', 'departure_date', 'trip_ref')},
            },
        ),
        migrations.AddIndex(
            model_name='shippingtripnotice',
            index=models.Index(fields=['business_type', 'customer_code', 'departure_date'], name='t_shipping_t_busines_258278_idx'),
        ),
        migrations.AddIndex(
            model_name='shippingtripnotice',
            index=models.Index(fields=['departure_date', 'trip_ref'], name='t_shipping_t_departu_2371c5_idx'),
        ),
    ]
