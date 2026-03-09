from django.core.management.base import BaseCommand
from orders.core.models import StgOrderRawKubota, StgOrderDaily

class Command(BaseCommand):
    help = 'Delete JVAN import records by source file'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='確認なしで削除実行')

    def handle(self, *args, **options):
        files = [
            '20260303取込済_RCV_JVAN - 47sakaituikabun.csv',
            '20260303取込済_RCV_JVAN - 2026-03-03T075620.387_S_47.csv',
            '20260304取込済_RCV_JVAN - 47sakai.csv',
            '20260305取込済_RCV_JVAN - 47sa.csv',
            '20260305取込済_RCV_JVAN - 47satuika.csv',
            '20260306取込済_RCV_JVAN - 47sa.csv',
        ]

        # 全ファイルについてチェック
        self.stdout.write('\n===== 削除対象レコードの確認 =====')
        total_raw_records = 0
        total_daily_records = 0
        deletion_map = {}

        for filename in files:
            raw_records = StgOrderRawKubota.objects.filter(source_file=filename)
            raw_count = raw_records.count()
            
            daily_records = StgOrderDaily.objects.filter(source_file=filename)
            daily_count = daily_records.count()
            
            if raw_count > 0 or daily_count > 0:
                self.stdout.write(f'\n{filename}')
                if raw_count > 0:
                    self.stdout.write(f'  raw: {raw_count}件')
                    total_raw_records += raw_count
                if daily_count > 0:
                    self.stdout.write(f'  daily: {daily_count}件')
                    total_daily_records += daily_count
                
                deletion_map[filename] = {
                    'raw_count': raw_count,
                    'daily_count': daily_count,
                }
            else:
                self.stdout.write(f'\n{filename}: レコードなし')

        self.stdout.write(f'\n===== 削除予定サマリー =====')
        self.stdout.write(f'stg_order_raw_kubota: {total_raw_records}件')
        self.stdout.write(f'stg_order_daily: {total_daily_records}件')
        self.stdout.write(f'総レコード数: {total_raw_records + total_daily_records}件')

        if total_raw_records == 0 and total_daily_records == 0:
            self.stdout.write(self.style.WARNING('\n削除対象レコードがありません'))
            return

        if not options['confirm']:
            response = input('\n削除を実行しますか？ (y/n): ')
            if response.lower() != 'y':
                self.stdout.write(self.style.WARNING('キャンセルしました'))
                return

        # 削除実行
        self.stdout.write('\n===== 削除実行中 =====')
        for filename in deletion_map.keys():
            raw_records = StgOrderRawKubota.objects.filter(source_file=filename)
            daily_records = StgOrderDaily.objects.filter(source_file=filename)
            
            if daily_records.exists():
                daily_count = daily_records.count()
                daily_records.delete()
                self.stdout.write(f'{filename}: daily {daily_count}件を削除')
            
            if raw_records.exists():
                raw_count = raw_records.count()
                raw_records.delete()
                self.stdout.write(f'{filename}: raw {raw_count}件を削除')

        self.stdout.write(self.style.SUCCESS(f'\n削除完了! 合計 {total_raw_records + total_daily_records}件を削除しました'))
