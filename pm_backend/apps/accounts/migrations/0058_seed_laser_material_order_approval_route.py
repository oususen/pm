from django.db import migrations


def create_route(apps, schema_editor):
    ApprovalRouteConfig = apps.get_model('accounts', 'ApprovalRouteConfig')
    ApprovalRouteConfig.objects.update_or_create(
        item_key='laser_material_order',
        defaults={
            'item_name': 'レーザー材料発注',
            'creator_role': 'leader',
            'reviewer1_role': 'supervisor',
            'reviewer2_role': 'chief',
            'reviewer2_enabled': False,
            'approver_role': 'manager',
            'is_active': True,
            'note': 'レーザー週次材料発注の承認ルート',
        },
    )


def remove_route(apps, schema_editor):
    ApprovalRouteConfig = apps.get_model('accounts', 'ApprovalRouteConfig')
    ApprovalRouteConfig.objects.filter(item_key='laser_material_order').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0057_approval_request_step_task'),
    ]

    operations = [
        migrations.RunPython(create_route, remove_route),
    ]