from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0070_processworksessionchangehistory'),
    ]

    operations = [
        migrations.AlterField(
            model_name='processworksessionchangehistory',
            name='operation_type',
            field=models.CharField(
                choices=[('ADD', '追加'), ('UPDATE', '変更'), ('DELETE', '削除')],
                max_length=10,
                verbose_name='操作区分',
            ),
        ),
    ]
