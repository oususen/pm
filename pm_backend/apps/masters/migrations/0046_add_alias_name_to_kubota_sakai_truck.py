from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0045_kubota_sakai_truck_initial_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='kubotasakaitruck',
            name='alias_name',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='俗称'),
        ),
    ]

