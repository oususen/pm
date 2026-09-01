import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('production', '0092_laser_weekly_plan')]

    operations = [
        migrations.CreateModel(
            name='LaserWeeklyPlanManualQuantity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan_date', models.DateField(verbose_name='レーザ計画日')),
                ('sheets', models.PositiveIntegerField(verbose_name='手動回数')),
                ('target', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='manual_quantities', to='production.laserweeklyplantarget')),
            ],
            options={'db_table': 't_laser_weekly_plan_manual_quantity'},
        ),
        migrations.AddConstraint(
            model_name='laserweeklyplanmanualquantity',
            constraint=models.UniqueConstraint(fields=('target', 'plan_date'), name='laser_weekly_manual_quantity_unique'),
        ),
    ]
