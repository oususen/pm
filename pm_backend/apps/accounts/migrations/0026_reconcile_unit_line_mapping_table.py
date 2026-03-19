from django.db import migrations


def reconcile_unit_line_mapping_table(apps, schema_editor):
    table_names = set(schema_editor.connection.introspection.table_names())
    has_group_table = 'accounts_group_line_mapping' in table_names
    has_unit_table = 'accounts_unit_line_mapping' in table_names

    if has_unit_table:
        return
    if not has_group_table:
        return

    with schema_editor.connection.cursor() as cursor:
        columns = {
            row.name
            for row in schema_editor.connection.introspection.get_table_description(
                cursor,
                'accounts_group_line_mapping',
            )
        }
        if 'group_id' in columns and 'unit_id' not in columns:
            schema_editor.execute(
                """
                ALTER TABLE accounts_group_line_mapping
                CHANGE COLUMN group_id unit_id bigint NOT NULL
                """
            )
        schema_editor.execute(
            """
            RENAME TABLE accounts_group_line_mapping TO accounts_unit_line_mapping
            """
        )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0025_sync_unit_line_mapping_table'),
    ]

    operations = [
        migrations.RunPython(reconcile_unit_line_mapping_table, migrations.RunPython.noop),
    ]
