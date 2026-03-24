from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0040_laserpattern_is_budget_target'),
    ]

    operations = [
        migrations.AddField(
            model_name='laserpattern',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='有効'),
        ),
    ]
