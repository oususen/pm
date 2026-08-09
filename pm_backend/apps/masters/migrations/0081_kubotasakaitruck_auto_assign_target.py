from django.db import migrations, models


def seed_auto_assign_target(apps, schema_editor):
    KubotaSakaiTruck = apps.get_model('masters', 'KubotaSakaiTruck')
    for truck in KubotaSakaiTruck.objects.all():
        marker = str(getattr(truck, 'alias_name', '') or getattr(truck, 'name', '') or '').strip()
        normalized = marker.replace(' ', '').replace('　', '').upper()
        is_pseudo = normalized in ('A', 'A便', 'Ａ', 'Ａ便', 'P', 'P便', 'Ｐ', 'Ｐ便')
        truck.auto_assign_target = bool(truck.is_active) and not is_pseudo
        truck.save(update_fields=['auto_assign_target'])


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0080_add_container_gap_to_trucks'),
    ]

    operations = [
        migrations.AddField(
            model_name='kubotasakaitruck',
            name='auto_assign_target',
            field=models.BooleanField(default=False, verbose_name='自動振分対象'),
        ),
        migrations.RunPython(seed_auto_assign_target, migrations.RunPython.noop),
    ]
