"""
ルーティングの入力ミスや後からのライン/工程変更により、現行の有効ルーティングには
もう存在しない(製品×ライン×工程)の組み合わせでLineBacklogが残ってしまうケースを検出する。
実体は production.services.orphan_backlog_service を使用する
(同ロジックは設定画面「孤立ライン実績メンテナンス」のAPIからも利用される)。

使用方法:
  python manage.py find_orphan_line_backlog                              # 全製品を対象にdry-run
  python manage.py find_orphan_line_backlog --product-code YD40007722-11SG # 製品を絞り込み
  python manage.py find_orphan_line_backlog --apply                       # ゴースト行のみ削除
"""
from django.core.management.base import BaseCommand

from production.services import orphan_backlog_service as svc


class Command(BaseCommand):
    help = (
        '現行の有効ルーティングに存在しない(製品×ライン×工程)のLineBacklog/LineDemand'
        '孤立グループを検出する。全項目ゼロのゴースト行のみ --apply で削除できる。'
    )

    def add_arguments(self, parser):
        parser.add_argument('--product-code', default=None, help='対象製品コードを1件に絞り込む')
        parser.add_argument(
            '--apply', action='store_true',
            help='ゴースト行(全項目ゼロ)を実際に削除する(デフォルトはdry-run)',
        )

    def _print_backlog_group(self, g):
        self.stdout.write(
            f"  {g['product_code']} / {g['line_name']}({g['line_code']}) / "
            f"{g['process_code']}: {g['count']}件 進度合計={g['sums']['progress_qty']} "
            f"実績合計={g['sums']['actual_qty']} 調整合計={g['sums']['adjust_qty']} "
            f"({g['min_date']}〜{g['max_date']})"
        )

    def _print_demand_group(self, g):
        self.stdout.write(
            f"  {g['product_code']} / {g['line_name']}({g['line_code']}): "
            f"{g['count']}件 内示合計={g['sums']['forecast_qty']} 確定合計={g['sums']['firm_qty']} "
            f"実績合計={g['sums']['actual_qty']} ({g['min_date']}〜{g['max_date']})"
        )

    def handle(self, *args, **options):
        apply = options['apply']
        product_code = options.get('product_code')

        report = svc.build_report(product_code)

        self.stdout.write(
            f"[LineBacklog] ゴースト(全項目ゼロ)={len(report['backlog_ghosts'])}件, "
            f"要確認(数値残存)={len(report['backlog_residuals'])}件"
        )
        self.stdout.write(
            f"[LineDemand] ゴースト(全項目ゼロ)={len(report['demand_ghosts'])}件, "
            f"要確認(数値残存)={len(report['demand_residuals'])}件\n"
        )

        if report['backlog_ghosts']:
            self.stdout.write(self.style.WARNING('--- LineBacklog ゴースト行(削除候補) ---'))
            for g in report['backlog_ghosts']:
                self._print_backlog_group(g)
        if report['backlog_residuals']:
            self.stdout.write(self.style.ERROR('--- LineBacklog 要確認行(手動確認必須、自動削除しない) ---'))
            for g in report['backlog_residuals']:
                self._print_backlog_group(g)
        if report['demand_ghosts']:
            self.stdout.write(self.style.WARNING('--- LineDemand ゴースト行(削除候補) ---'))
            for g in report['demand_ghosts']:
                self._print_demand_group(g)
        if report['demand_residuals']:
            self.stdout.write(self.style.ERROR('--- LineDemand 要確認行(手動確認必須、自動削除しない) ---'))
            for g in report['demand_residuals']:
                self._print_demand_group(g)

        if not apply:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                'DRY RUN 完了。--apply を付けるとゴースト行のみ削除されます(要確認行は削除されません)。'
            ))
            return

        backlog_targets = [
            {'product_id': g['product_id'], 'line_id': g['line_id'], 'process_id': g['process_id']}
            for g in report['backlog_ghosts']
        ]
        demand_targets = [
            {'product_id': g['product_id'], 'line_id': g['line_id']}
            for g in report['demand_ghosts']
        ]
        result = svc.apply_fix(backlog_targets=backlog_targets, demand_targets=demand_targets)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f"=== 削除完了: LineBacklog {result['deleted_backlog']}件, "
            f"LineDemand {result['deleted_demand']}件 ==="
        ))
        for msg in result['skipped']:
            self.stdout.write(self.style.WARNING(f'  スキップ: {msg}'))
