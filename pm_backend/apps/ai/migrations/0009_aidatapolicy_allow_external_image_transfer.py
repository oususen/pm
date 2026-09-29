from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('ai', '0008_aiknowledgedocument')]

    operations = [
        migrations.AddField(
            model_name='aidatapolicy',
            name='allow_external_image_transfer',
            field=models.BooleanField(default=True, verbose_name='添付画像の外部AI送信を許可'),
        ),
    ]
