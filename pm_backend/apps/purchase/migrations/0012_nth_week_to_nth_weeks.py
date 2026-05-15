from django.db import migrations, models


def convert_nth_week(apps, schema_editor):
    SupplierOrderPattern = apps.get_model('purchase', 'SupplierOrderPattern')
    for p in SupplierOrderPattern.objects.all():
        if p.nth_week is not None:
            p.nth_weeks = str(p.nth_week)
            p.save(update_fields=['nth_weeks'])


class Migration(migrations.Migration):

    dependencies = [
        ('purchase', '0011_rename_pattern_fields_to_multi'),
    ]

    operations = [
        migrations.AddField(
            model_name='supplierorderpattern',
            name='nth_weeks',
            field=models.CharField(blank=True, default='', max_length=20, verbose_name='第N週(1〜5, カンマ区切り)'),
        ),
        migrations.RunPython(convert_nth_week, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='supplierorderpattern',
            name='nth_week',
        ),
    ]
