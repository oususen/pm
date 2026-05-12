from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0049_add_transfer_destination_to_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='unit_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='単価'),
        ),
    ]

