from collections import defaultdict

import django.db.models.deletion
from django.db import migrations, models


def copy_detail_manual_quantities(apps, schema_editor):
    DetailManual = apps.get_model('production', 'LaserWeeklyPlanManualQuantity')
    PatternManual = apps.get_model('production', 'LaserWeeklyPatternManualQuantity')
    totals = defaultdict(int)
    for item in DetailManual.objects.values('target__laser_pattern_id', 'plan_date', 'sheets'):
        totals[(item['target__laser_pattern_id'], item['plan_date'])] += item['sheets']
    PatternManual.objects.bulk_create([
        PatternManual(laser_pattern_id=pattern_id, plan_date=plan_date, sheets=sheets)
        for (pattern_id, plan_date), sheets in totals.items()
    ])


class Migration(migrations.Migration):
    dependencies = [('production', '0093_laser_weekly_plan_manual_quantity')]

    operations = [
        migrations.CreateModel(
            name='LaserWeeklyPatternManualQuantity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan_date', models.DateField(verbose_name='レーザ計画日')),
                ('sheets', models.PositiveIntegerField(verbose_name='手動回数')),
                ('laser_pattern', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='weekly_manual_quantities', to='production.laserpattern')),
            ],
            options={'db_table': 't_laser_weekly_pattern_manual_quantity'},
        ),
        migrations.AddConstraint(
            model_name='laserweeklypatternmanualquantity',
            constraint=models.UniqueConstraint(fields=('laser_pattern', 'plan_date'), name='laser_weekly_pattern_manual_quantity_unique'),
        ),
        migrations.RunPython(copy_detail_manual_quantities, migrations.RunPython.noop),
    ]
