from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0052_shippingrun_shippingtrip_shippingtripallocation_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='shippingtrip',
            name='departed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='shipping_trip_departed_by', to=settings.AUTH_USER_MODEL, verbose_name='出発担当者'),
        ),
        migrations.AddField(
            model_name='shippingtrip',
            name='loading_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='shipping_trip_loading_by', to=settings.AUTH_USER_MODEL, verbose_name='積込担当者'),
        ),
    ]
