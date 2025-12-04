from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0003_process_line'),
    ]

    operations = [
        migrations.AddField(
            model_name='line',
            name='lead_time_days',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='リードタイム（日）'),
        ),
    ]
