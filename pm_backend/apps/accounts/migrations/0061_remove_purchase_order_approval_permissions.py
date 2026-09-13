from django.db import migrations


def remove_purchase_order_approval_permissions(apps, schema_editor):
    resource = 'settings.purchase_order_approval'
    for model_name in (
        'UserPermission',
        'DepartmentPermission',
        'PositionPermission',
        'DepartmentPositionPermission',
    ):
        model = apps.get_model('accounts', model_name)
        model.objects.filter(resource=resource).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0060_seed_purchase_order_proposal_approval_route'),
    ]

    operations = [
        migrations.RunPython(remove_purchase_order_approval_permissions, migrations.RunPython.noop),
    ]
