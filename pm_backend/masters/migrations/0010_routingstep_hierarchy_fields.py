from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0009_drop_legacy_routing_step_output'),
    ]

    operations = [
        migrations.AddField(
            model_name='routingstep',
            name='hierarchy_depth',
            field=models.IntegerField(default=0, verbose_name='工程階層深さ'),
        ),
        migrations.AddField(
            model_name='routingstep',
            name='hierarchy_path',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='工程階層パス'),
        ),
    ]
