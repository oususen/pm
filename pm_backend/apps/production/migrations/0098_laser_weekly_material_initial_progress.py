from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('production', '0097_laser_weekly_material_order_progress')]

    operations = [migrations.CreateModel(name='LaserWeeklyMaterialInitialProgress', fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ('plan_start_date', models.DateField(verbose_name='計画開始日')),
        ('initial_progress', models.IntegerField(default=0, verbose_name='期首進度')),
        ('is_locked', models.BooleanField(default=False, verbose_name='ロック')),
        ('material', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='laser_weekly_initial_progresses', to='masters.product')),
    ], options={'db_table': 't_laser_weekly_material_initial_progress'}), migrations.AddConstraint(model_name='laserweeklymaterialinitialprogress', constraint=models.UniqueConstraint(fields=('plan_start_date', 'material'), name='laser_weekly_material_initial_progress_unique'))]
