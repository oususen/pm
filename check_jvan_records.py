#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pm_backend'))

django.setup()

from orders.core.models import StgOrderRawKubota

# ファイル名からレコードを検索
files = [
    '20260304取込済_RCV_JVAN - 47sakai.csv',
    '20260305取込済_RCV_JVAN - 47satuika.csv'
]

total_records = 0
deletion_summary = {}

for filename in files:
    print(f'\n===== {filename} =====')
    records = StgOrderRawKubota.objects.filter(source_file=filename)
    count = records.count()
    print(f'レコード数: {count}')
    total_records += count
    deletion_summary[filename] = count
    
    if records.exists():
        first_rec = records.first()
        last_rec = records.last()
        print(f'ID範囲: {first_rec.id} - {last_rec.id}')
        print(f'顧客コード: {first_rec.customer_code}')
        print(f'取込日: {first_rec.created_at}')
        print(f'データ番号: {first_rec.data_no}')
        # サンプル表示
        for rec in records[:2]:
            print(f'  品番: {rec.product_code}, 数量: {rec.quantity}, 納期: {rec.delivery_date}')

print(f'\n===== 削除予定 =====')
print(f'総レコード数: {total_records}')
for filename, count in deletion_summary.items():
    print(f'{filename}: {count}件')
