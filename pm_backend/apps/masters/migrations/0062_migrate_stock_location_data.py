from django.db import migrations


def migrate_stock_location_forward(apps, schema_editor):
    """既存のProduct.stock_locationをProductStockLocationにコピー"""
    Product = apps.get_model('masters', 'Product')
    ProductStockLocation = apps.get_model('masters', 'ProductStockLocation')

    rows = []
    for product in Product.objects.exclude(stock_location__isnull=True).exclude(stock_location__exact=''):
        rows.append(ProductStockLocation(
            product=product,
            location_name=product.stock_location,
            sort_order=0,
        ))
    if rows:
        ProductStockLocation.objects.bulk_create(rows, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0061_add_product_stock_location_table'),
    ]

    operations = [
        migrations.RunPython(migrate_stock_location_forward, migrations.RunPython.noop),
    ]
