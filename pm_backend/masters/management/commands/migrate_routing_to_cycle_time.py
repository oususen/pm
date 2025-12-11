"""
RoutingStep.duration_min から ProcessCycleTime へのデータ移行コマンド

使用方法:
  python manage.py migrate_routing_to_cycle_time [--dry-run]
"""
from django.core.management.base import BaseCommand
from masters.models import RoutingStep, ProcessCycleTime, Product, Process, Line


class Command(BaseCommand):
    help = 'RoutingStep から ProcessCycleTime へデータを移行します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には保存せず、移行内容を表示のみ',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - 実際には保存しません'))
        
        # duration_min が設定されている RoutingStep を取得
        routing_steps = RoutingStep.objects.filter(
            duration_min__isnull=False
        ).select_related('routing__product', 'process', 'line')
        
        total_count = routing_steps.count()
        self.stdout.write(f'移行対象: {total_count}件')
        
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        for step in routing_steps:
            try:
                # 製品を取得
                product = step.routing.product
                if not product:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  SKIP: ルーティング {step.routing_id} に製品が設定されていません'
                        )
                    )
                    skipped_count += 1
                    continue
                
                # 工程を取得
                if not step.process:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  SKIP: RoutingStep {step.id} に工程が設定されていません'
                        )
                    )
                    skipped_count += 1
                    continue
                
                # 既存の ProcessCycleTime をチェック
                existing = ProcessCycleTime.objects.filter(
                    product=product,
                    process=step.process,
                    line=step.line,
                    is_active=True
                ).first()
                
                if existing:
                    self.stdout.write(
                        f'  SKIP: {product.product_code} x {step.process.process_code} は既に存在します'
                    )
                    skipped_count += 1
                    continue
                
                # ProcessCycleTime を作成
                cycle_time_data = {
                    'product': product,
                    'process': step.process,
                    'line': step.line,
                    'cycle_time_min': step.duration_min,
                    'setup_time_min': 0,  # デフォルト値
                    'lot_size': 1,  # デフォルト値
                    'is_active': True,
                    'valid_from': None,
                    'valid_to': None,
                }
                
                if not dry_run:
                    ProcessCycleTime.objects.create(**cycle_time_data)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  OK: {product.product_code} x {step.process.process_code} '
                        f'({step.duration_min}分) -> ProcessCycleTime'
                    )
                )
                created_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  ERROR: RoutingStep {step.id} の移行に失敗: {str(e)}'
                    )
                )
                error_count += 1
        
        self.stdout.write('-' * 60)
        self.stdout.write(f'移行完了:')
        self.stdout.write(f'  作成: {created_count}件')
        self.stdout.write(f'  スキップ: {skipped_count}件')
        self.stdout.write(f'  エラー: {error_count}件')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n※ DRY RUN MODE - 実際には保存されていません'))
            self.stdout.write('実際に移行するには --dry-run を外して実行してください')
