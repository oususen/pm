from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0007_routingstep_output_product'),
        ('orders', '0005_lineplan'),
    ]

    operations = [
        migrations.AddField(
            model_name='lineplan',
            name='process',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='masters.process', verbose_name='工程'),
        ),
    ]
