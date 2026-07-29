from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shipping', '0009_alter_shipmentactualhistory_action'),
    ]

    operations = [
        migrations.AddField(
            model_name='shiptoleadtime',
            name='bg_color',
            field=models.CharField(blank=True, default='', max_length=10, verbose_name='背景色'),
        ),
        migrations.AddField(
            model_name='shiptoleadtime',
            name='text_color',
            field=models.CharField(blank=True, default='', max_length=10, verbose_name='文字色'),
        ),
    ]
