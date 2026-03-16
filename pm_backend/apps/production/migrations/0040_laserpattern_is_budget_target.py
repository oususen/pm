from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0039_brake_line_record'),
    ]

    operations = [
        migrations.AddField(
            model_name='laserpattern',
            name='is_budget_target',
            field=models.BooleanField(default=False, verbose_name='材料予算用'),
        ),
    ]

