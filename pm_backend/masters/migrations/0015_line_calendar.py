from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('masters', '0014_product_is_line_final_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='line',
            name='calendar',
            field=models.ForeignKey(
                on_delete=models.SET_NULL,
                blank=True,
                null=True,
                to='masters.calendar',
                verbose_name='勤務カレンダ'
            ),
        ),
    ]
