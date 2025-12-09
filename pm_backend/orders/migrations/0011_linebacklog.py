from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0009_drop_legacy_routing_step_output'),
        ('orders', '0008_linedemand'),
    ]

    operations = [
        migrations.CreateModel(
            name='LineBacklog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan_date', models.DateField()),
                ('demand_qty_plan', models.DecimalField(decimal_places=3, default=0, max_digits=14)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('line', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='backlogs', to='masters.line')),
                ('process', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='backlogs', to='masters.process')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='line_backlogs', to='masters.product')),
                ('source_line', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='backlog_sources', to='masters.line')),
                ('source_routing_step', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='backlog_sources', to='masters.routingstep')),
            ],
            options={
                'db_table': 'line_backlog',
                'unique_together': {('plan_date', 'process', 'product', 'line')},
            },
        ),
        migrations.AddIndex(
            model_name='linebacklog',
            index=models.Index(fields=['plan_date', 'line'], name='line_backl_plan_da_8b86d8_idx'),
        ),
    ]
