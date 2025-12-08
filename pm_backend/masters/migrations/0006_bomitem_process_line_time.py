from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0005_alter_product_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='bomitem',
            name='process',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='masters.process', verbose_name='工程'),
        ),
        migrations.AddField(
            model_name='bomitem',
            name='line',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='masters.line', verbose_name='ライン'),
        ),
        migrations.AddField(
            model_name='bomitem',
            name='time_unit',
            field=models.CharField(choices=[('DAY', '日'), ('MINUTE', '分')], default='MINUTE', max_length=10, verbose_name='時間単位'),
        ),
        migrations.AddField(
            model_name='bomitem',
            name='lead_time_days',
            field=models.IntegerField(default=0, verbose_name='リードタイム(日)'),
        ),
        migrations.AddField(
            model_name='bomitem',
            name='duration_min',
            field=models.IntegerField(blank=True, null=True, verbose_name='所要時間(分)'),
        ),
    ]
