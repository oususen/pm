from django.db import migrations
from django.db.models import F, Subquery


def sync_profile_department_division(apps, schema_editor):
    UserProfile = apps.get_model('accounts', 'UserProfile')
    Department = apps.get_model('accounts', 'Department')

    division_ids = Department.objects.filter(level='division').values('id')

    UserProfile.objects.exclude(division_id__isnull=True).exclude(
        department_id=F('division_id')
    ).update(department_id=F('division_id'))

    UserProfile.objects.filter(
        division_id__isnull=True,
        department_id__in=Subquery(division_ids),
    ).update(division_id=F('department_id'))


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0018_alter_departmentpermission_resource_and_more'),
    ]

    operations = [
        migrations.RunPython(sync_profile_department_division, migrations.RunPython.noop),
    ]

