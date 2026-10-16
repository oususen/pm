from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0119_process_realtime_operator_login_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='brakelinerecord',
            name='operator_login_id',
            field=models.CharField(blank=True, db_index=True, max_length=150, null=True, verbose_name='作業者ログインID'),
        ),
    ]
