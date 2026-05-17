from django.db import migrations, models


def copy_legacy_supplied_to_issued(apps, schema_editor):
    MaterialRequirement = apps.get_model('outsource', 'MaterialRequirement')
    MaterialRequirement.objects.filter(supplied=True).update(
        shipment_planned=True,
        issued=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('outsource', '0007_add_outsource_material'),
    ]

    operations = [
        migrations.AddField(
            model_name='materialrequirement',
            name='issued',
            field=models.BooleanField(default=False, verbose_name='出庫済み'),
        ),
        migrations.AddField(
            model_name='materialrequirement',
            name='shipment_planned',
            field=models.BooleanField(default=False, verbose_name='便計画済み'),
        ),
        migrations.RunPython(copy_legacy_supplied_to_issued, migrations.RunPython.noop),
    ]

