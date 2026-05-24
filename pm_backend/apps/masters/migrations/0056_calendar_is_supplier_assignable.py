from django.db import migrations, models


def seed_supplier_assignable_flags(apps, schema_editor):
    Calendar = apps.get_model('masters', 'Calendar')
    Line = apps.get_model('masters', 'Line')

    Calendar.objects.all().update(is_supplier_assignable=True)
    Calendar.objects.filter(calendar_code__iexact='daiso').update(is_supplier_assignable=False)

    prod_calendar_ids = Line.objects.filter(
        line_type='PROD',
        calendar_id__isnull=False,
    ).values_list('calendar_id', flat=True)
    prod_calendar_ids = set(prod_calendar_ids)
    if prod_calendar_ids:
        Calendar.objects.filter(id__in=prod_calendar_ids).update(is_supplier_assignable=False)


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0055_calendar_is_line_assignable'),
    ]

    operations = [
        migrations.AddField(
            model_name='calendar',
            name='is_supplier_assignable',
            field=models.BooleanField(default=True, verbose_name='仕入先割当可'),
        ),
        migrations.RunPython(seed_supplier_assignable_flags, migrations.RunPython.noop),
    ]

