from django.db import migrations


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
