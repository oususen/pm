from django.core.management.base import BaseCommand
from orders.core.models import StgOrderRawKubota

class Command(BaseCommand):
    help = 'Check records for JVAN file deletion'

    def handle(self, *args, **options):
        files = [
            '20260304取込済_RCV_JVAN - 47sakai.csv',
            '20260305取込済_RCV_JVAN - 47satuika.csv'
        ]

        total_records = 0
        deletion_summary = {}

        for filename in files:
            self.stdout.write(f'\n===== {filename} =====')
            records = StgOrderRawKubota.objects.filter(source_file=filename)
            count = records.count()
            self.stdout.write(f'レコード数: {count}')
            total_records += count
            deletion_summary[filename] = count
            
            if records.exists():
                first_rec = records.first()
                self.stdout.write(f'ID範囲: {first_rec.id} - {records.last().id}')
                self.stdout.write(f'顧客コード: {first_rec.customer_code}')
                self.stdout.write(f'取込日: {first_rec.created_at}')
                self.stdout.write(f'データ番号: {first_rec.data_no}')
                # サンプル表示
                for rec in records[:2]:
                    self.stdout.write(f'  品番: {rec.product_code}, 数量: {rec.quantity}, 納期: {rec.delivery_date}')

        self.stdout.write(f'\n===== 削除予定 =====')
        self.stdout.write(f'総レコード数: {total_records}')
        for filename, count in deletion_summary.items():
            self.stdout.write(f'{filename}: {count}件')
