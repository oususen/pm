from django.db import migrations

# NOTE: Legacy m_routing_step_output was dropped because coproduct BOM handles
# multi-output cases, and RoutingStep.output_product is the canonical output.


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0008_routingstepmaterial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS m_routing_step_output;",
            reverse_sql="",
        ),
    ]
