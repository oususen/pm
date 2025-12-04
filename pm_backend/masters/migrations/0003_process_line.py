from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0002_product_product_name_halfwidth'),
    ]

    operations = [
        migrations.AddField(
            model_name='process',
            name='line',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='masters.line', verbose_name='ライン'),
        ),
    ]
