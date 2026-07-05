from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0074_morningmeeting_is_template'),
    ]

    operations = [
        migrations.AlterField(
            model_name='morningmeeting',
            name='meeting_date',
            field=models.DateField(blank=True, null=True, verbose_name='朝礼日'),
        ),
    ]
