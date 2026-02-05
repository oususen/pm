# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0028_contact'),
    ]

    operations = [
        migrations.AddField(
            model_name='bomitem',
            name='is_coproduct_driver',
            field=models.BooleanField(default=False, verbose_name='連産品代表品'),
        ),
    ]
