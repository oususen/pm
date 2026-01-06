from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0034_shipmentactual_shipmentactualhistory_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='scraprecord',
            name='event_type',
            field=models.CharField(
                choices=[('SCRAP', '仕損'), ('RETURN', '戻し')],
                default='SCRAP',
                max_length=20,
                verbose_name='イベント種別',
            ),
        ),
        migrations.AddField(
            model_name='scraprecord',
            name='return_for',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='return_records',
                to='orders.scraprecord',
                verbose_name='戻し対象仕損',
            ),
        ),
    ]
