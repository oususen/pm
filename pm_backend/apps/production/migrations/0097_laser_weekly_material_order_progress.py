from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('production', '0096_laser_processing_freq_pattern')]

    operations = [
        migrations.CreateModel(
            name='LaserWeeklyMaterialOrderProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan_start_date', models.DateField(verbose_name='計画開始日')),
                ('required_date', models.DateField(verbose_name='必要日')),
                ('delivery_date', models.DateField(verbose_name='納期')),
                ('supplier', models.CharField(choices=[('SATO', '佐藤商事'), ('MEISEI', '名成鋼機')], max_length=10, verbose_name='仕入先')),
                ('required_sheets', models.PositiveIntegerField(verbose_name='必要枚数')),
                ('lot_multiple', models.PositiveIntegerField(verbose_name='発注倍数')),
                ('required_lots', models.PositiveIntegerField(verbose_name='必要ロット数')),
                ('order_lots', models.PositiveIntegerField(verbose_name='発注ロット数')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('material', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='laser_weekly_order_progresses', to='masters.product')),
            ],
            options={'db_table': 't_laser_weekly_material_order_progress'},
        ),
        migrations.AddConstraint(
            model_name='laserweeklymaterialorderprogress',
            constraint=models.UniqueConstraint(fields=('plan_start_date', 'material', 'required_date', 'supplier'), name='laser_weekly_material_order_progress_unique'),
        ),
    ]
