"""製品リードタイム自動計算コマンド"""
from django.core.management.base import BaseCommand
from masters.services.bom_service import BOMService
from masters.models import Product


class Command(BaseCommand):
    help = 'BOM構造から製品のリードタイムを自動計算します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product-code',
            type=str,
            help='特定の製品のみ計算する場合の品番コード'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には更新せず、計算結果のみ表示'
        )

    def handle(self, *args, **options):
        service = BOMService()
        product_code = options.get('product_code')
        dry_run = options.get('dry_run', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('ドライランモード: データベースは更新されません'))

        if product_code:
            # 特定製品のみ計算
            try:
                product = Product.objects.get(product_code=product_code)
                self.stdout.write(f'\n製品: {product.product_code} - {product.product_name}')

                if dry_run:
                    # ドライランの場合は、一時的に計算のみ実施
                    cache = {}
                    lt = service.calculate_intermediate_lt(product.id, cache)
                    # 再度読み込んで元の値を表示
                    product.refresh_from_db()
                    self.stdout.write(f'  現在のL/T: {product.standard_lt_days}日 (自工程: {product.self_lt_days}日)')
                    self.stdout.write(f'  計算後L/T: {lt}日')
                else:
                    old_lt = product.standard_lt_days
                    old_self_lt = product.self_lt_days
                    cache = {}
                    new_lt = service.calculate_intermediate_lt(product.id, cache)
                    product.refresh_from_db()

                    self.stdout.write(f'  更新前: {old_lt}日 (自工程: {old_self_lt}日)')
                    self.stdout.write(f'  更新後: {product.standard_lt_days}日 (自工程: {product.self_lt_days}日)')
                    self.stdout.write(self.style.SUCCESS('✓ 計算完了'))

            except Product.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'製品が見つかりません: {product_code}'))
                return

        else:
            # 全製品の一括計算
            self.stdout.write('\n全製品のリードタイムを計算中...\n')

            if dry_run:
                # ドライランでは計算のみ
                products = Product.objects.exclude(
                    category='PURCHASED'
                ).filter(is_active=True)

                cache = {}
                success_count = 0
                error_count = 0

                for product in products:
                    try:
                        lt = service.calculate_intermediate_lt(product.id, cache)
                        # 再度読み込んで元の値を表示
                        product.refresh_from_db()

                        if product.standard_lt_days != lt:
                            self.stdout.write(
                                f'  {product.product_code}: {product.standard_lt_days}日 → {lt}日'
                            )
                        success_count += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  エラー: {product.product_code} - {str(e)}')
                        )
                        error_count += 1

                self.stdout.write(f'\n計算対象: {success_count + error_count}件')
                self.stdout.write(f'成功: {success_count}件')
                if error_count > 0:
                    self.stdout.write(self.style.ERROR(f'エラー: {error_count}件'))

            else:
                # 実際に更新
                results = service.batch_calculate_all_lt()

                success_results = [r for r in results if r['status'] == 'success']
                error_results = [r for r in results if r['status'] == 'error']

                # 成功結果を表示
                if success_results:
                    self.stdout.write('\n✓ 計算完了:')
                    for result in success_results[:10]:  # 最初の10件のみ表示
                        self.stdout.write(
                            f'  {result["product_code"]}: {result["standard_lt_days"]}日 '
                            f'(自工程: {result["self_lt_days"]}日)'
                        )
                    if len(success_results) > 10:
                        self.stdout.write(f'  ... 他 {len(success_results) - 10}件')

                # エラー結果を表示
                if error_results:
                    self.stdout.write(self.style.ERROR('\n✗ エラー:'))
                    for result in error_results:
                        self.stdout.write(
                            self.style.ERROR(
                                f'  {result["product_code"]}: {result["error"]}'
                            )
                        )

                # サマリー
                self.stdout.write('\n' + '=' * 60)
                self.stdout.write(f'対象製品数: {len(results)}件')
                self.stdout.write(self.style.SUCCESS(f'成功: {len(success_results)}件'))
                if error_results:
                    self.stdout.write(self.style.ERROR(f'エラー: {len(error_results)}件'))
                self.stdout.write('=' * 60)

        self.stdout.write('\n')
