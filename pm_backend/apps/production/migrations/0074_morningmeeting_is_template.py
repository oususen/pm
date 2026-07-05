from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0073_morningmeetingattachment_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='morningmeeting',
            name='is_template',
            field=models.BooleanField(default=False, verbose_name='テンプレート'),
        ),
    ]
