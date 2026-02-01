# Generated manually - quality app initial migration
# The tables t_scrap_record and t_scrap_record_detail already exist in the database.
# This migration marks the models as managed by Django without recreating the tables.

from django.db import migrations


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('masters', '0028_contact'),
        ('production', '0004_add_production_plan_lock_setting_and_change_log'),
    ]

    operations = [
        # No operations - tables already exist
        # This migration exists to establish the quality app in the migration history
    ]
