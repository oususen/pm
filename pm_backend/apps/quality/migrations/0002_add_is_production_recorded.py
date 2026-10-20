# Generated manually - add is_production_recorded field to t_scrap_record

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quality', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE t_scrap_record ADD COLUMN is_production_recorded BOOLEAN NOT NULL DEFAULT FALSE;",
            reverse_sql="ALTER TABLE t_scrap_record DROP COLUMN is_production_recorded;",
        ),
    ]
