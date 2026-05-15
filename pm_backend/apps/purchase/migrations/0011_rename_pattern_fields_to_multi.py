from django.db import migrations, models


def convert_single_to_csv(apps, schema_editor):
    SupplierOrderPattern = apps.get_model('purchase', 'SupplierOrderPattern')
    for p in SupplierOrderPattern.objects.all():
        if p.day_of_week is not None:
            p.days_of_week = str(p.day_of_week)
        if p.day_of_month is not None:
            p.days_of_month = str(p.day_of_month)
        p.save(update_fields=['days_of_week', 'days_of_month'])


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0010_add_supplier_order_pattern'),
    ]

    operations = [
        migrations.AddField(
            model_name='supplierorderpattern',
            name='days_of_week',
            field=models.CharField(blank=True, default='', max_length=20, verbose_name='曜日(0=月〜6=日, カンマ区切り)'),
        ),
        migrations.AddField(
            model_name='supplierorderpattern',
            name='days_of_month',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='日付(1〜31, カンマ区切り)'),
        ),
        migrations.RunPython(convert_single_to_csv, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='supplierorderpattern',
            name='day_of_week',
        ),
        migrations.RemoveField(
            model_name='supplierorderpattern',
            name='day_of_month',
        ),
    ]
