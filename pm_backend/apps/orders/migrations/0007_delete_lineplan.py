from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0006_lineplan_process'),
    ]

    operations = [
        migrations.DeleteModel(
            name='LinePlan',
        ),
    ]
