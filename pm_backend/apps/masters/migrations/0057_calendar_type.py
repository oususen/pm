from django.db import migrations, models


def seed_calendar_type_and_flags(apps, schema_editor):
    Calendar = apps.get_model('masters', 'Calendar')
    Customer = apps.get_model('masters', 'Customer')
    Supplier = apps.get_model('masters', 'Supplier')
    Line = apps.get_model('masters', 'Line')

    Calendar.objects.all().update(calendar_type='OTHER')
    Calendar.objects.filter(calendar_code__iexact='daiso').update(calendar_type='COMPANY')

    customer_calendar_ids = set(
        Customer.objects.exclude(calendar_id=None).values_list('calendar_id', flat=True)
    )
    if customer_calendar_ids:
        Calendar.objects.filter(id__in=customer_calendar_ids).update(calendar_type='CUSTOMER')

    supplier_calendar_ids = set(
        Supplier.objects.exclude(calendar_id=None).values_list('calendar_id', flat=True)
    )
    if supplier_calendar_ids:
        Calendar.objects.filter(id__in=supplier_calendar_ids).update(calendar_type='SUPPLIER')

    internal_calendar_ids = set(
        Line.objects.filter(line_type='PROD', calendar_id__isnull=False).values_list('calendar_id', flat=True)
    )
    if internal_calendar_ids:
        Calendar.objects.filter(id__in=internal_calendar_ids).update(calendar_type='INTERNAL')

    Calendar.objects.filter(calendar_type='INTERNAL').update(
        is_line_assignable=True,
        is_supplier_assignable=False,
    )
    Calendar.objects.filter(calendar_type='SUPPLIER').update(
        is_line_assignable=False,
        is_supplier_assignable=True,
    )
    Calendar.objects.filter(calendar_type__in=['COMPANY', 'CUSTOMER', 'OTHER']).update(
        is_line_assignable=False,
        is_supplier_assignable=False,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0056_calendar_is_supplier_assignable'),
    ]

    operations = [
        migrations.AddField(
            model_name='calendar',
            name='calendar_type',
            field=models.CharField(
                choices=[
                    ('INTERNAL', '社内'),
                    ('SUPPLIER', '仕入れ'),
                    ('COMPANY', '会社'),
                    ('CUSTOMER', '顧客'),
                    ('OTHER', 'その他'),
                ],
                default='OTHER',
                max_length=20,
                verbose_name='カレンダ区分',
            ),
        ),
        migrations.RunPython(seed_calendar_type_and_flags, migrations.RunPython.noop),
    ]

