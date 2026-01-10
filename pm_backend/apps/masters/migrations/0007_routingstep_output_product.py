from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0006_bomitem_process_line_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='routingstep',
            name='output_product',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='masters.product', verbose_name='加工後品目'),
        ),
    ]
