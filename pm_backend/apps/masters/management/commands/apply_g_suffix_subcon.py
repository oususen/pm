"""
外注加工先BOM品のG品番化コマンド

処理内容:
  1. 対象加工先のBOM child_product の product_code 末尾に G を追加
  2. 対象製品の category を OUTSOURCED に変更
  3. 対象 BOMItem の sourcing_type を BUY → SUBCON に変更

対象加工先:
  000061 有限会社エムテック
  000095 有限会社ゼンツー (BUY品のみ / SUBCON+G設定済みは除外)
  000132 株式会社大豊製作所
  000180 有限会社ホウダテクニカル
  000259 抱月工業株式会社
  000319 株式会社イケモト
  000352 有限会社積水製作所
  000387 株式会社三原金属工業 (Gサフィックス済み品は除外)
  000543 トリックス株式会社

使用方法:
  python manage.py apply_g_suffix_subcon          # dry-run (変更なし、確認のみ)
  python manage.py apply_g_suffix_subcon --apply  # 実際に変更を適用
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from masters.models import BOMItem, Product


TARGET_SUPPLIER_CODES = [
    '000061', '000095', '000132', '000180', '000259',
    '000319', '000352', '000387', '000543',
]


class Command(BaseCommand):
    help = '外注加工先BOM品にGサフィックスを付け、カテゴリをOUTSOURCED・BOMをSUBCONに変更する'

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

        # 対象: Gサフィックスなし かつ 対象加工先のBOMアイテムのchild_product
        target_items = BOMItem.objects.filter(
            supplier__supplier_code__in=TARGET_SUPPLIER_CODES,
        ).exclude(
            child_product__product_code__endswith='G',
        ).select_related(
            'child_product', 'supplier', 'bom__parent_product',
        )

        # ユニーク製品を収集
        unique_products = {}
        for item in target_items:
            pid = item.child_product_id
            if pid not in unique_products:
                unique_products[pid] = item.child_product

        bom_buy_count = target_items.filter(sourcing_type='BUY').count()
        bom_subcon_count = target_items.filter(sourcing_type='SUBCON').count()

        self.stdout.write(f'対象ユニーク品番数: {len(unique_products)} 件')
        self.stdout.write(f'対象BOMアイテム数: {target_items.count()} 件 (BUY:{bom_buy_count} / SUBCON:{bom_subcon_count})')
        self.stdout.write('')

        # G付き後の product_code 重複チェック
        new_codes = [p.product_code + 'G' for p in unique_products.values()]
        existing = Product.objects.filter(product_code__in=new_codes).values_list('product_code', flat=True)
        if existing:
            self.stdout.write(self.style.ERROR('=== 重複品番が存在します（処理を中断します） ==='))
            for code in existing:
                self.stdout.write(self.style.ERROR(f'  既存: {code}'))
            return

        # 変更内容を表示
        self.stdout.write('--- 品番変更一覧 ---')
        for product in sorted(unique_products.values(), key=lambda p: p.product_code):
            self.stdout.write(
                f'  {product.product_code:30s} → {product.product_code + "G":30s}  category={product.category} → OUTSOURCED'
            )

        self.stdout.write('')
        self.stdout.write(f'--- BOMアイテム BUY→SUBCON: {bom_buy_count} 件 ---')

        if not apply:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('DRY RUN 完了。--apply を付けて実行すると変更が適用されます。'))
            return

        # === 実際の変更 ===
        with transaction.atomic():
            # Step 1: 製品コード + カテゴリ変更
            renamed = 0
            for product in unique_products.values():
                old_code = product.product_code
                product.product_code = old_code + 'G'
                product.category = 'OUTSOURCED'
                product.save(update_fields=['product_code', 'category', 'updated_at'])
                renamed += 1

            self.stdout.write(self.style.SUCCESS(f'Step1 完了: {renamed} 品番を更新'))

            # Step 2: BOMアイテム sourcing_type BUY → SUBCON
            updated = BOMItem.objects.filter(
                supplier__supplier_code__in=TARGET_SUPPLIER_CODES,
                child_product_id__in=list(unique_products.keys()),
                sourcing_type='BUY',
            ).update(sourcing_type='SUBCON')

            self.stdout.write(self.style.SUCCESS(f'Step2 完了: {updated} BOMアイテムをBUY→SUBCONに更新'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== 処理完了 ==='))
