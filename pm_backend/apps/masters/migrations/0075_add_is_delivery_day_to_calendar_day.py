from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0074_add_is_holiday_work_to_calendar_day'),
    ]

    operations = [
        migrations.AddField(
            model_name='calendarday',
            name='is_delivery_day',
            field=models.BooleanField(default=False, verbose_name='納入日'),
        ),
    ]
