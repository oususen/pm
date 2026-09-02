from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('production', '0098_laser_weekly_material_initial_progress')]

    operations = [
        migrations.AddField(
            model_name='laserweeklymaterialinitialprogress',
            name='is_locked',
            field=models.BooleanField(default=False, verbose_name='ロック'),
        ),
    ]
