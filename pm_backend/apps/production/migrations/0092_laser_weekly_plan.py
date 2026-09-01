import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('production', '0091_linedemand_ship_to_code'), ('masters', '0001_initial')]
    operations = [
        migrations.CreateModel(name='LaserWeeklyPlanTarget', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('lead_time_days', models.PositiveIntegerField(default=0, verbose_name='LT(日)')),
            ('quantity_source', models.CharField(choices=[('ORDER_QTY', '需要（order_qty）'), ('PLAN_QTY', '後工程計画（plan_qty）')], default='ORDER_QTY', max_length=10, verbose_name='数量取得元')),
            ('sort_order', models.IntegerField(default=0)), ('is_active', models.BooleanField(default=True)),
            ('downstream_line', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='laser_weekly_targets', to='masters.line')),
            ('laser_pattern', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='weekly_plan_targets', to='production.laserpattern')),
            ('finished_product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='laser_weekly_finished_targets', to='masters.product')),
            ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='laser_weekly_targets', to='masters.product')),
        ], options={'db_table': 't_laser_weekly_plan_target', 'ordering': ['sort_order', 'downstream_line_id', 'product_id']}),
        migrations.CreateModel(name='LaserWeeklyMaterialGroup', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('group_name', models.CharField(max_length=120, unique=True)), ('material_type', models.CharField(blank=True, default='', max_length=20)),
            ('sheets_per_material', models.DecimalField(decimal_places=3, default=1, max_digits=14)), ('sort_order', models.IntegerField(default=0)), ('is_active', models.BooleanField(default=True)),
            ('patterns', models.ManyToManyField(blank=True, related_name='weekly_material_groups', to='production.laserpattern')),
        ], options={'db_table': 't_laser_weekly_material_group', 'ordering': ['sort_order', 'group_name']}),
        migrations.AddConstraint(model_name='laserweeklyplantarget', constraint=models.UniqueConstraint(fields=('downstream_line', 'product', 'laser_pattern', 'finished_product'), name='laser_weekly_target_unique')),
    ]
