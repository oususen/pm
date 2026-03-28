from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0039_add_product_next_process'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='specific_gravity',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True, verbose_name='比重(g/cm³)'),
        ),
        migrations.AddField(
            model_name='product',
            name='size_length',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='縦(mm)'),
        ),
        migrations.AddField(
            model_name='product',
            name='size_width',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='横(mm)'),
        ),
        migrations.AddField(
            model_name='product',
            name='size_thickness',
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=10, null=True, verbose_name='厚さ(mm)'),
        ),
    ]
