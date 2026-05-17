from django.db import migrations, models


def copy_required_to_order_qty(apps, schema_editor):
    MaterialRequirement = apps.get_model('outsource', 'MaterialRequirement')
    for row in MaterialRequirement.objects.all().only('id', 'required_qty'):
        row.order_qty = row.required_qty
        row.save(update_fields=['order_qty'])


class Migration(migrations.Migration):

    dependencies = [
        ('outsource', '0009_stock_transactions'),
    ]

    operations = [
        migrations.AddField(
            model_name='materialrequirement',
            name='order_qty',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=12, verbose_name='発注数'),
        ),
        migrations.RunPython(copy_required_to_order_qty, migrations.RunPython.noop),
    ]

