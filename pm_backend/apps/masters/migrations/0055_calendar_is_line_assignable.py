from django.db import migrations, models


def seed_line_assignable_flags(apps, schema_editor):
    Calendar = apps.get_model('masters', 'Calendar')
    Customer = apps.get_model('masters', 'Customer')
    Supplier = apps.get_model('masters', 'Supplier')

    Calendar.objects.all().update(is_line_assignable=True)
    Calendar.objects.filter(calendar_code__iexact='daiso').update(is_line_assignable=False)

    customer_calendar_ids = Customer.objects.exclude(calendar_id=None).values_list('calendar_id', flat=True)
    supplier_calendar_ids = Supplier.objects.exclude(calendar_id=None).values_list('calendar_id', flat=True)
    disallowed_ids = set(customer_calendar_ids) | set(supplier_calendar_ids)
    if disallowed_ids:
        Calendar.objects.filter(id__in=disallowed_ids).update(is_line_assignable=False)


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0054_productcodemapping'),
    ]

    operations = [
        migrations.AddField(
            model_name='calendar',
            name='is_line_assignable',
            field=models.BooleanField(default=True, verbose_name='ライン割当可'),
        ),
        migrations.RunPython(seed_line_assignable_flags, migrations.RunPython.noop),
    ]
