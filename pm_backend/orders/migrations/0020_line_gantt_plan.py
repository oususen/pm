from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0019_product_line_process_management_unit'),
        ('orders', '0019_processrealtimerecord'),
    ]

    operations = [
        migrations.CreateModel(
            name='LineGanttPlan',
            fields=[
                ('plan_id', models.CharField(max_length=160, primary_key=True, serialize=False)),
                ('plan_date', models.DateField()),
                ('plan_qty', models.DecimalField(decimal_places=3, default=0, max_digits=14)),
                ('sequence_no', models.IntegerField(blank=True, null=True)),
                ('start_datetime', models.DateTimeField()),
                ('end_datetime', models.DateTimeField()),
                ('processes_plan', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('line', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gantt_plans', to='masters.line')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gantt_plans', to='masters.product')),
            ],
            options={
                'db_table': 't_line_gantt_plan',
            },
        ),
        migrations.AddIndex(
            model_name='lineganttplan',
            index=models.Index(fields=['line', 'plan_date'], name='idx_line_gantt_plan_date'),
        ),
    ]
