from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0069_containercapacity_code_unique'),
    ]

    operations = [
        migrations.AddField(
            model_name='kubotasakaitruck',
            name='physical_truck_code',
            field=models.CharField(
                blank=True,
                help_text='同じ物理トラックとして占有率を合算する便に同じ値を設定する',
                max_length=50,
                null=True,
                verbose_name='同一車両キー',
            ),
        ),
    ]
