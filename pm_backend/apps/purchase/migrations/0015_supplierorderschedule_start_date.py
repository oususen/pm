from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0014_alter_supplierorderschedule_pattern'),
    ]

    operations = [
        migrations.AddField(
            model_name='supplierorderschedule',
            name='start_date',
            field=models.DateField(blank=True, null=True, verbose_name='開始基準日'),
        ),
    ]

