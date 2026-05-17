from datetime import timedelta

from django.db import migrations, models


def set_material_due_date(apps, schema_editor):
    MaterialRequirement = apps.get_model('outsource', 'MaterialRequirement')
    for row in MaterialRequirement.objects.all().iterator():
        if row.material_due_date:
            continue
        if row.supply_date:
            row.material_due_date = row.supply_date - timedelta(days=1)
            row.save(update_fields=['material_due_date'])


class Migration(migrations.Migration):

    dependencies = [
        ('outsource', '0010_materialrequirement_order_qty'),
    ]

    operations = [
        migrations.AddField(
            model_name='materialrequirement',
            name='material_due_date',
            field=models.DateField(blank=True, null=True, verbose_name='材料納期'),
        ),
        migrations.RunPython(set_material_due_date, migrations.RunPython.noop),
    ]

