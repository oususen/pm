import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0057_calendar_type'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='calendar',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='created_calendars',
                to=settings.AUTH_USER_MODEL,
                verbose_name='作成者',
            ),
        ),
        migrations.AddField(
            model_name='calendar',
            name='updated_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='updated_calendars',
                to=settings.AUTH_USER_MODEL,
                verbose_name='最終更新者',
            ),
        ),
    ]
