from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0058_calendar_created_by_updated_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='supplier',
            name='supplier_type',
            field=models.CharField(
                choices=[('outsource', '外作'), ('purchase', '購入'), ('both', '両方')],
                default='both',
                max_length=20,
                verbose_name='仕入先区分',
            ),
        ),
    ]
