from django.db import migrations


def add_readonly_sql_tool(apps, schema_editor):
    tool_policy_model = apps.get_model('ai', 'AIToolPolicy')
    for screen_id in ('ai_home', 'orders', 'production', 'quality', 'overtime'):
        tool_policy_model.objects.update_or_create(
            screen_id=screen_id,
            tool_code='execute_readonly_sql',
            defaults={'is_enabled': True, 'allow_external_transfer': True},
        )


class Migration(migrations.Migration):
    dependencies = [('ai', '0002_ai_management_settings')]

    operations = [migrations.RunPython(add_readonly_sql_tool, migrations.RunPython.noop)]
