"""
外作化した9社の仕入ラインに残っている旧PURCHASE(process_id=18)LineBacklog行を削除する

対象ライン（各社の仕入ライン）:
  line_id=58 エムテック(000061)
  line_id=56 ゼンツー(000095)
  line_id=51 大豊製作所(000132)
  line_id=63 ホウダテクニカル(000180)
  line_id=91 抱月工業(000259)
  line_id=90 イケモト(000319)
  line_id=54 積水製作所(000352)
  line_id=52 三原金属工業(000387)
  line_id=66 トリックス(000543)

使用方法:
  python manage.py delete_old_purchase_backlog          # dry-run
  python manage.py delete_old_purchase_backlog --apply  # 実際に削除
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from production.models_line_backlog import LineBacklog

PURCHASE_PROCESS_ID = 18

SUPPLIER_LINES = {
    58: 'エムテック(000061)',
    56: 'ゼンツー(000095)',
    51: '大豊製作所(000132)',
    63: 'ホウダテクニカル(000180)',
    91: '抱月工業(000259)',
    90: 'イケモト(000319)',
    54: '積水製作所(000352)',
    52: '三原金属工業(000387)',
    66: 'トリックス(000543)',
}


class Command(BaseCommand):
    help = '外作化した9社の仕入ラインに残る旧PURCHASE LineBacklog行を削除する'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='実際に削除を適用する（デフォルトはdry-run）',
        )

    def handle(self, *args, **options):
        apply = options['apply']

        if not apply:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE (--apply を付けると実際に削除されます) ==='))

        target = LineBacklog.objects.filter(
            process_id=PURCHASE_PROCESS_ID,
            line_id__in=list(SUPPLIER_LINES.keys()),
        )

        total = target.count()
        self.stdout.write(f'削除対象 LineBacklog: {total} 件\n')

        counts = defaultdict(int)
        for row in target.values('line_id').iterator():
            counts[row['line_id']] += 1

        for line_id, cnt in sorted(counts.items()):
            name = SUPPLIER_LINES.get(line_id, f'line_id={line_id}')
            self.stdout.write(f'  {name}: {cnt} 件')

        if not apply:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('DRY RUN 完了。--apply を付けて実行すると削除が適用されます。'))
            return

        with transaction.atomic():
            deleted, _ = target.delete()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'=== 削除完了: {deleted} 件 ==='))
        self.stdout.write('次に「過去から再計算」を実行してください。')
