from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('overtime', '0008_alter_overtimeapplication_application_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='overtimeapplication',
            name='holiday_work_type',
            field=models.CharField(
                choices=[('full_day', '全日'), ('half_day', '半日')],
                default='full_day',
                max_length=20,
                verbose_name='休日出勤区分',
            ),
        ),
    ]
