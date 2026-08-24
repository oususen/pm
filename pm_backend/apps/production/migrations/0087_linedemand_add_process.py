from django.db import migrations, models
import django.db.models.deletion


def populate_linedemand_process(apps, schema_editor):
    if schema_editor.connection.vendor == 'mysql':
        schema_editor.execute(
            """
            UPDATE t_line_demand ld
            JOIN m_routing_step rs ON rs.id = ld.routing_step_id
            SET ld.process_id = rs.process_id
            WHERE ld.routing_step_id IS NOT NULL
            """
        )
        return

    LineDemand = apps.get_model('production', 'LineDemand')
    for demand in LineDemand.objects.select_related('routing_step').all():
        process_id = getattr(getattr(demand, 'routing_step', None), 'process_id', None)
        if demand.process_id != process_id:
            demand.process_id = process_id
            demand.save(update_fields=['process'])


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('masters', '0072_routingchangehistory'),
        ('production', '0086_scheduleconfig_kubota_due_auto_link_enabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='linedemand',
            name='process',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='masters.process', verbose_name='工程'),
        ),
        migrations.RunPython(populate_linedemand_process, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name='linedemand',
            unique_together={('line', 'product_code', 'plan_date', 'process')},
        ),
        migrations.AddIndex(
            model_name='linedemand',
            index=models.Index(fields=['process'], name='t_line_dema_process_b24f81_idx'),
        ),
    ]
