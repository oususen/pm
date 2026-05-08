"""
外作化9社の仕入ラインのPURCHASEバックログを外作工程に変換するコマンド

処理内容:
  2026-03-01 より前  : PURCHASE行・G行を全削除（古い履歴は不要）
  2026-03-01 以降    :
    1. G/外作工程行(process_id=17)の実績をPURCHASE行(process_id=18)のsequence_no=0行に転記
    2. G/外作工程行を削除
    3. PURCHASE行のprocess_idを17に変更（実績を引き継いだまま外作工程に）

使用方法:
  python manage.py convert_purchase_backlog_to_gaisaku          # dry-run
  python manage.py convert_purchase_backlog_to_gaisaku --apply  # 実際に変更
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Exists, OuterRef

from production.models_line_backlog import LineBacklog

PURCHASE_PROCESS_ID = 18
GAISAKU_PROCESS_ID = 17
INHERIT_FROM = date(2026, 3, 1)

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

LINE_IDS = list(SUPPLIER_LINES.keys())


class Command(BaseCommand):
    help = 'PURCHASE LineBacklog行を外作工程に変換（3/1以降の実績を引き継ぎ、以前は削除）'

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

        self.stdout.write(f'継承開始日: {INHERIT_FROM} 以降の実績を保持')
        self.stdout.write(f'          : {INHERIT_FROM} より前は全削除')
        self.stdout.write('')

        # ---- 3/1より前 ----
        old_purchase = LineBacklog.objects.filter(
            process_id=PURCHASE_PROCESS_ID,
            line_id__in=LINE_IDS,
            plan_date__lt=INHERIT_FROM,
        )
        old_g = LineBacklog.objects.filter(
            process_id=GAISAKU_PROCESS_ID,
            line_id__in=LINE_IDS,
            plan_date__lt=INHERIT_FROM,
        )
        self.stdout.write(f'【削除対象】{INHERIT_FROM}より前:')
        self.stdout.write(f'  PURCHASE行: {old_purchase.count()} 件')
        self.stdout.write(f'  G/外作工程行: {old_g.count()} 件')
        self.stdout.write('')

        # ---- 3/1以降 ----
        new_purchase = LineBacklog.objects.filter(
            process_id=PURCHASE_PROCESS_ID,
            line_id__in=LINE_IDS,
            plan_date__gte=INHERIT_FROM,
        )
        new_g = LineBacklog.objects.filter(
            process_id=GAISAKU_PROCESS_ID,
            line_id__in=LINE_IDS,
            plan_date__gte=INHERIT_FROM,
        )
        new_g_with_actual = new_g.filter(actual_qty__gt=0)

        self.stdout.write(f'【変換対象】{INHERIT_FROM}以降:')
        self.stdout.write(f'  PURCHASE行: {new_purchase.count()} 件 → process_id=17に変換')
        self.stdout.write(f'  G/外作工程行: {new_g.count()} 件 → 削除（実績あり: {new_g_with_actual.count()} 件）')
        self.stdout.write('')

        # G行実績の転記内容を表示
        g_actual_rows = list(new_g_with_actual.order_by('line_id', 'plan_date'))
        if g_actual_rows:
            self.stdout.write('--- G行実績 → PURCHASE行転記 ---')
            for g_row in g_actual_rows:
                name = SUPPLIER_LINES.get(g_row.line_id, f'line_id={g_row.line_id}')
                self.stdout.write(
                    f'  {name} {g_row.plan_date} product_id={g_row.product_id}'
                    f'  実績: {g_row.actual_qty}'
                )
            self.stdout.write('')

        if not apply:
            self.stdout.write(self.style.WARNING('DRY RUN 完了。--apply を付けて実行すると変更が適用されます。'))
            return

        with transaction.atomic():
            # Step0: 3/1より前を全削除
            del_old_p, _ = old_purchase.delete()
            del_old_g, _ = old_g.delete()
            self.stdout.write(self.style.SUCCESS(
                f'Step0完了: {INHERIT_FROM}より前 PURCHASE {del_old_p}件・G {del_old_g}件 削除'
            ))

            # Step1: G行実績をPURCHASE代表行(sequence_no=0)に転記
            if g_actual_rows:
                purchase_rep_map = {}
                purchase_reps = LineBacklog.objects.filter(
                    process_id=PURCHASE_PROCESS_ID,
                    line_id__in=LINE_IDS,
                    plan_date__gte=INHERIT_FROM,
                    sequence_no=0,
                ).only('id', 'line_id', 'product_id', 'plan_date', 'actual_qty')
                for row in purchase_reps:
                    key = (row.line_id, row.product_id, row.plan_date)
                    if key not in purchase_rep_map:
                        purchase_rep_map[key] = row

                to_update = []
                for g_row in g_actual_rows:
                    key = (g_row.line_id, g_row.product_id, g_row.plan_date)
                    p_rep = purchase_rep_map.get(key)
                    if p_rep:
                        p_rep.actual_qty = (p_rep.actual_qty or 0) + g_row.actual_qty
                        to_update.append(p_rep)

                if to_update:
                    LineBacklog.objects.bulk_update(to_update, ['actual_qty'])
                self.stdout.write(self.style.SUCCESS(f'Step1完了: G行実績 {len(to_update)} 件を転記'))
            else:
                self.stdout.write(self.style.SUCCESS('Step1完了: G行実績なし（転記スキップ）'))

            # Step2: PURCHASE行が存在するG行を削除
            purchase_exists = LineBacklog.objects.filter(
                process_id=PURCHASE_PROCESS_ID,
                line_id=OuterRef('line_id'),
                product_id=OuterRef('product_id'),
                plan_date=OuterRef('plan_date'),
            )
            del_g, _ = LineBacklog.objects.filter(
                process_id=GAISAKU_PROCESS_ID,
                line_id__in=LINE_IDS,
                plan_date__gte=INHERIT_FROM,
            ).filter(Exists(purchase_exists)).delete()
            self.stdout.write(self.style.SUCCESS(f'Step2完了: G行 {del_g} 件削除'))

            # Step3: PURCHASE行をprocess_id=17に変換
            converted = LineBacklog.objects.filter(
                process_id=PURCHASE_PROCESS_ID,
                line_id__in=LINE_IDS,
            ).update(process_id=GAISAKU_PROCESS_ID)
            self.stdout.write(self.style.SUCCESS(f'Step3完了: PURCHASE行 {converted} 件 → process_id=17に変換'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== 処理完了 ==='))
        self.stdout.write('次に画面から「過去から再計算」を実行してください。')
