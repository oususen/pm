from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0035_laseractual_operator_action_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='laseractualdetail',
            name='scrap_qty',
            field=models.DecimalField(decimal_places=3, default=0, max_digits=14, verbose_name='仕損数量'),
        ),
        migrations.AddField(
            model_name='laseractualdetail',
            name='scrap_reason',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='仕損理由'),
        ),
    ]
