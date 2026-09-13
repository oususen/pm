from django.db import migrations


def create_route(apps, schema_editor):
    ApprovalRouteConfig = apps.get_model('accounts', 'ApprovalRouteConfig')
    ApprovalRouteConfig.objects.update_or_create(
        item_key='purchase_order_proposal',
        defaults={
            'item_name': '発注提案',
            'creator_role': 'office_staff',
            'reviewer1_role': 'supervisor',
            'reviewer2_role': 'chief',
            'reviewer2_enabled': True,
            'approver_role': 'manager',
            'is_active': True,
            'note': '発注提案書の承認ルート',
        },
    )


def remove_route(apps, schema_editor):
    ApprovalRouteConfig = apps.get_model('accounts', 'ApprovalRouteConfig')
    ApprovalRouteConfig.objects.filter(item_key='purchase_order_proposal').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0059_alter_departmentpermission_resource_and_more'),
    ]

    operations = [
        migrations.RunPython(create_route, remove_route),
    ]
