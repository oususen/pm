import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pm_backend.settings')
django.setup()

from masters.models import BOMItem

print("\n=== BOM ID 16 のアイテム確認 ===")
items_16 = BOMItem.objects.filter(bom_id=16)
print(f"BOM ID 16のアイテム数: {items_16.count()}件")
for item in items_16:
    print(f"  - ID: {item.id}, child_product: {item.child_product.product_code}, bom: {item.bom_id}")

print("\n=== BOM ID 14 のアイテム確認 ===")
items_14 = BOMItem.objects.filter(bom_id=14)
print(f"BOM ID 14のアイテム数: {items_14.count()}件")
for item in items_14:
    print(f"  - ID: {item.id}, child_product: {item.child_product.product_code}, bom: {item.bom_id}")

print("\n=== 全BOMItemの確認 ===")
all_items = BOMItem.objects.all()
print(f"全BOMItemの件数: {all_items.count()}件")
for item in all_items:
    print(f"  - ID: {item.id}, bom: {item.bom_id}, child: {item.child_product.product_code}")
