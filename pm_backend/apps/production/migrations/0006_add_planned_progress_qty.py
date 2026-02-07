from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0005_scheduleconfig_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='linebacklog',
            name='planned_progress_qty',
            field=models.IntegerField(default=0, verbose_name='計画進度'),
        ),
    ]
