from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0040_product_laser_material_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='routing',
            name='valid_from_datetime',
            field=models.DateTimeField(blank=True, null=True, verbose_name='有効開始日時'),
        ),
        migrations.AddField(
            model_name='routing',
            name='valid_to_datetime',
            field=models.DateTimeField(blank=True, null=True, verbose_name='有効終了日時'),
        ),
    ]
