"""
外作工程RoutingStep・BOMアイテムのline_idを各社の仕入ラインに戻すコマンド

現状: process_id=17, line_id=14(外作ライン) になっている
変更後: process_id=17, line_id=仕入ライン（各社）に戻す

対象:
  RoutingStep: process_id=17 かつ line_id=14 の296件
  BOMItem: sourcing_type=SUBCON かつ line_id=14 の174件

使用方法:
  python manage.py revert_gaisaku_line_to_supplier          # dry-run
  python manage.py revert_gaisaku_line_to_supplier --apply  # 実際に変更
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from masters.models import BOMItem, RoutingStep

GAISAKU_LINE_ID = 14
GAISAKU_PROCESS_ID = 17

# supplier_id → 仕入ラインID のマッピング
SUPPLIER_TO_LINE = {
    10: 58,   # 000061 エムテック
    8:  56,   # 000095 ゼンツー
    4:  51,   # 000132 大豊製作所
    16: 63,   # 000180 ホウダテクニカル
    23: 91,   # 000259 抱月工業
    2:  54,   # 000352 積水製作所
    7:  52,   # 000387 三原金属工業
}

SUPPLIER_NAMES = {
    10: 'エムテック(000061)',
    8:  'ゼンツー(000095)',
    4:  '大豊製作所(000132)',
    16: 'ホウダテクニカル(000180)',
    23: '抱月工業(000259)',
    2:  '積水製作所(000352)',
    7:  '三原金属工業(000387)',
}

# BOMアイテム用: supplier_code → 仕入ラインID
# (BOMItemにはsupplier_id=Supplierオブジェクト参照、supplier_codeで引く)
BOM_SUPPLIER_CODE_TO_LINE = {
    '000061': 58,
    '000095': 56,
    '000132': 51,
    '000180': 63,
    '000259': 91,
    '000319': 90,   # イケモト
    '000352': 54,
    '000387': 52,
    '000543': 66,   # トリックス
}

BOM_SUPPLIER_NAMES = {
    '000061': 'エムテック',
    '000095': 'ゼンツー',
    '000132': '大豊製作所',
    '000180': 'ホウダテクニカル',
    '000259': '抱月工業',
    '000319': 'イケモト',
    '000352': '積水製作所',
    '000387': '三原金属工業',
    '000543': 'トリックス',
}


class Command(BaseCommand):
    help = '外作工程RoutingStep・BOMアイテムのline_idを各社の仕入ラインに戻す'

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

        self._handle_routing_steps(apply)
        self._handle_bom_items(apply)

        if not apply:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('DRY RUN 完了。--apply を付けて実行すると変更が適用されます。'))

    def _handle_routing_steps(self, apply):
        self.stdout.write('')
        self.stdout.write('=== RoutingStep: line_id=14 → 各社仕入ライン ===')

        target = RoutingStep.objects.filter(
            process_id=GAISAKU_PROCESS_ID,
            line_id=GAISAKU_LINE_ID,
            supplier_id__in=list(SUPPLIER_TO_LINE.keys()),
        )
        total = target.count()
        self.stdout.write(f'対象: {total} 件')

        from collections import defaultdict
        counts = defaultdict(int)
        for step in target:
            counts[step.supplier_id] += 1
        for supplier_id, cnt in sorted(counts.items()):
            name = SUPPLIER_NAMES.get(supplier_id, f'supplier_id={supplier_id}')
            target_line = SUPPLIER_TO_LINE.get(supplier_id, '?')
            self.stdout.write(f'  {name}: {cnt} 件 → line_id={target_line}')

        if not apply:
            return

        with transaction.atomic():
            updated = 0
            for supplier_id, line_id in SUPPLIER_TO_LINE.items():
                cnt = RoutingStep.objects.filter(
                    process_id=GAISAKU_PROCESS_ID,
                    line_id=GAISAKU_LINE_ID,
                    supplier_id=supplier_id,
                ).update(line_id=line_id)
                updated += cnt
                if cnt:
                    name = SUPPLIER_NAMES.get(supplier_id, f'supplier_id={supplier_id}')
                    self.stdout.write(f'  {name}: {cnt} 件 line_id → {line_id}')

        self.stdout.write(self.style.SUCCESS(f'RoutingStep完了: {updated} 件更新'))

    def _handle_bom_items(self, apply):
        self.stdout.write('')
        self.stdout.write('=== BOMアイテム: line_id=14 → 各社仕入ライン ===')

        target = BOMItem.objects.filter(
            sourcing_type='SUBCON',
            line_id=GAISAKU_LINE_ID,
            supplier__supplier_code__in=list(BOM_SUPPLIER_CODE_TO_LINE.keys()),
        ).select_related('supplier')
        total = target.count()
        self.stdout.write(f'対象: {total} 件')

        from collections import defaultdict
        counts = defaultdict(int)
        for item in target:
            counts[item.supplier.supplier_code] += 1
        for code, cnt in sorted(counts.items()):
            name = BOM_SUPPLIER_NAMES.get(code, code)
            target_line = BOM_SUPPLIER_CODE_TO_LINE.get(code, '?')
            self.stdout.write(f'  {name}({code}): {cnt} 件 → line_id={target_line}')

        if not apply:
            return

        with transaction.atomic():
            updated = 0
            for code, line_id in BOM_SUPPLIER_CODE_TO_LINE.items():
                cnt = BOMItem.objects.filter(
                    sourcing_type='SUBCON',
                    line_id=GAISAKU_LINE_ID,
                    supplier__supplier_code=code,
                ).update(line_id=line_id)
                updated += cnt
                if cnt:
                    name = BOM_SUPPLIER_NAMES.get(code, code)
                    self.stdout.write(f'  {name}: {cnt} 件 line_id → {line_id}')

        self.stdout.write(self.style.SUCCESS(f'BOMアイテム完了: {updated} 件更新'))
