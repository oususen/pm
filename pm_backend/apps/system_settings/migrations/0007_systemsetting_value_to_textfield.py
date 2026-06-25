from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system_settings', '0006_call_polling_settings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='systemsetting',
            name='value',
            field=models.TextField(verbose_name='値'),
        ),
    ]
