import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pm_backend.settings')
django.setup()

from orders.models import StgOrderRaw, StgOrderDaily

print(f'StgOrderRaw: {StgOrderRaw.objects.count()} records')
print(f'StgOrderDaily: {StgOrderDaily.objects.count()} records')
print('\n--- Latest StgOrderRaw (top 5) ---')
for raw in StgOrderRaw.objects.all().order_by('-id')[:5]:
    print(f'ID={raw.id}, product_code={raw.product_code}, parse_status={raw.parse_status}, customer_code={raw.customer_code}')

print('\n--- Latest StgOrderDaily (top 5) ---')
for daily in StgOrderDaily.objects.all().order_by('-id')[:5]:
    print(f'ID={daily.id}, product_code={daily.product_code}, raw_id={daily.raw_id}, customer={daily.customer}')
