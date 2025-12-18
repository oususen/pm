import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pm_backend.settings')
django.setup()

from orders.models import LineBacklog

recs = LineBacklog.objects.filter(line_id=6, product_id__in=[111, 113]).order_by('-updated_at')[:10]
print(f"\nTotal records: {recs.count()}")
print("\nRecent LineBacklog records:")
for r in recs:
    print(f"  ID:{r.id} product:{r.product_id} process:{r.process_id} date:{r.plan_date} plan_qty:{r.plan_qty} order_qty:{r.order_qty}")
