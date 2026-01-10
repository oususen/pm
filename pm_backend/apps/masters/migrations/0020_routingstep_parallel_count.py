from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0019_product_line_process_management_unit'),
    ]

    operations = [
        migrations.AddField(
            model_name='routingstep',
            name='parallel_count',
            field=models.IntegerField(default=1, verbose_name='並列数'),
        ),
    ]
