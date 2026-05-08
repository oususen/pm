"""
購買工程RoutingStepを外作工程に変更するコマンド

変更内容:
  process_id: 18 (購買) → 17 (外作工程)
  line_id:    仕入ライン → 14 (外作ライン / GAISAKU)
  supplier_id: NULL → 対応する加工先ID

対象: 以下9社の仕入ラインを持つRoutingStep
  000061 有限会社エムテック      (line_id=58, supplier_id=10)
  000095 有限会社ゼンツー        (line_id=56, supplier_id=8)
  000132 株式会社大豊製作所      (line_id=51, supplier_id=4)
  000180 有限会社ホウダテクニカル (line_id=63, supplier_id=16)
  000259 抱月工業株式会社        (line_id=91, supplier_id=23)
  000352 有限会社積水製作所      (line_id=54, supplier_id=2)
  000387 株式会社三原金属工業    (line_id=52, supplier_id=7)

使用方法:
  python manage.py convert_purchase_to_gaisaku          # dry-run
  python manage.py convert_purchase_to_gaisaku --apply  # 実際に変更
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from masters.models import RoutingStep

GAISAKU_PROCESS_ID = 17
GAISAKU_LINE_ID = 14
PURCHASE_PROCESS_ID = 18

# 仕入ラインID → 加工先SupplierID のマッピング
LINE_TO_SUPPLIER = {
    58: 10,   # エムテック
    56: 8,    # ゼンツー
    51: 4,    # 大豊製作所
    63: 16,   # ホウダテクニカル
    91: 23,   # 抱月工業
    54: 2,    # 積水製作所
    52: 7,    # 三原金属工業
}


class Command(BaseCommand):
    help = '購買工程RoutingStepを外作工程・外作ラインに変更する'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='実際に変更を適用する（デフォルトはdry-run）',
        )

    def handle(self, *args, **options):
        apply = options['apply']

        if not apply:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE (--apply を付けると実際に変更されます) ==='))

        target_steps = RoutingStep.objects.filter(
            process_id=PURCHASE_PROCESS_ID,
            line_id__in=list(LINE_TO_SUPPLIER.keys()),
        ).select_related(
            'routing__product', 'output_product',
        ).order_by('line_id', 'id')

        total = target_steps.count()
        self.stdout.write(f'対象RoutingStep: {total} 件\n')

        # 仕入ラインごとの集計
        from collections import defaultdict
        counts = defaultdict(int)
        for step in target_steps:
            counts[step.line_id] += 1

        line_names = {
            58: 'エムテック(000061)',
            56: 'ゼンツー(000095)',
            51: '大豊製作所(000132)',
            63: 'ホウダテクニカル(000180)',
            91: '抱月工業(000259)',
            54: '積水製作所(000352)',
            52: '三原金属工業(000387)',
        }
        for line_id, cnt in sorted(counts.items()):
            self.stdout.write(f'  {line_names.get(line_id, f"line_id={line_id}")}: {cnt} 件')

        if not apply:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('DRY RUN 完了。--apply を付けて実行すると変更が適用されます。'))
            return

        with transaction.atomic():
            updated = 0
            for line_id, supplier_id in LINE_TO_SUPPLIER.items():
                cnt = RoutingStep.objects.filter(
                    process_id=PURCHASE_PROCESS_ID,
                    line_id=line_id,
                ).update(
                    process_id=GAISAKU_PROCESS_ID,
                    line_id=GAISAKU_LINE_ID,
                    supplier_id=supplier_id,
                )
                updated += cnt
                self.stdout.write(f'  {line_names.get(line_id)}: {cnt} 件更新')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'=== 処理完了: {updated} 件更新 ==='))
