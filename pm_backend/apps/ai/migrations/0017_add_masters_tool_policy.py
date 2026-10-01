from django.db import migrations


SCREEN_ID = 'masters'
TOOL_CODES = ('search_product', 'count_products', 'execute_readonly_sql')


def add_masters_tool_policies(apps, schema_editor):
    tool_policy_model = apps.get_model('ai', 'AIToolPolicy')
    for tool_code in TOOL_CODES:
        tool_policy_model.objects.get_or_create(
            screen_id=SCREEN_ID,
            tool_code=tool_code,
            defaults={'is_enabled': True, 'allow_external_transfer': True},
        )


def remove_masters_tool_policies(apps, schema_editor):
    apps.get_model('ai', 'AIToolPolicy').objects.filter(
        screen_id=SCREEN_ID,
        tool_code__in=TOOL_CODES,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [('ai', '0016_ai_my_overtime_tool_policy')]

    operations = [migrations.RunPython(add_masters_tool_policies, remove_masters_tool_policies)]
