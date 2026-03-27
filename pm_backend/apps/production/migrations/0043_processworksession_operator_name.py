from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0042_processworksession_defect_qty'),
    ]

    operations = [
        migrations.AddField(
            model_name='processworksession',
            name='operator_name',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='作業者名'),
        ),
    ]
