from django.db import migrations


def backfill_units_from_teams(apps, schema_editor):
    Department = apps.get_model('accounts', 'Department')

    if Department.objects.filter(level='unit').exists():
        return

    teams = list(Department.objects.filter(level='team').order_by('display_id', 'id'))
    if not teams:
        return

    existing_names = set(Department.objects.filter(level='unit').values_list('name', flat=True))
    new_units = []

    for team in teams:
        base_name = team.name or f'チーム{team.id}'
        name = base_name
        suffix = 1
        while name in existing_names:
            suffix += 1
            name = f'{base_name}-{suffix}'
        existing_names.add(name)
        new_units.append(
            Department(
                name=name,
                level='unit',
                parent_id=team.id,
                display_id=0,
            )
        )

    if new_units:
        Department.objects.bulk_create(new_units)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0019_sync_profile_department_division'),
    ]

    operations = [
        migrations.RunPython(backfill_units_from_teams, migrations.RunPython.noop),
    ]

