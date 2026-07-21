"""
外作先ラインで誤ってPURCHASE工程に作られた重複LineBacklog行だけを削除する

対象条件:
  - ライン区分が PURCHASE
  - 現在行の工程コードが PURCHASE
  - 現在のマスタ解決では、その品目の正工程が PURCHASE 以外
  - 同一キー(line, 正工程, product, plan_date, sequence_no)の行が既に存在する

この条件に限定することで、BUY品のPURCHASE行は残しつつ、
外作品の誤PURCHASE重複だけを安全に掃除する。

使用方法:
  python manage.py delete_duplicate_outsource_purchase_backlog
  python manage.py delete_duplicate_outsource_purchase_backlog --apply
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from masters.models import Line, Supplier
from production.models_line_backlog import LineBacklog
from purchase.process_resolver import resolve_supplier_process


class Command(BaseCommand):
    help = '外作品の誤PURCHASE重複LineBacklogのみを削除する'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='実際に削除を適用する（デフォルトはdry-run）',
        )
        parser.add_argument(
            '--line-id',
            type=int,
            help='対象ラインを1本に絞る（例: --line-id 56）',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        filter_line_id = options.get('line_id')

        if not apply:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE (--apply を付けると実際に削除されます) ==='))

        purchase_lines_qs = Line.objects.filter(line_type='PURCHASE')
        if filter_line_id:
            purchase_lines_qs = purchase_lines_qs.filter(id=filter_line_id)
        purchase_lines = list(purchase_lines_qs.only('id', 'line_code', 'line_name'))
        if not purchase_lines:
            self.stdout.write('対象のPURCHASEラインはありません。')
            return

        supplier_by_line_id = {}
        for line in purchase_lines:
            supplier = Supplier.objects.filter(supplier_code=line.line_code).first()
            if supplier:
                supplier_by_line_id[line.id] = supplier

        if not supplier_by_line_id:
            self.stdout.write('supplier_code に対応する仕入先が見つかりません。')
            return

        line_ids = list(supplier_by_line_id.keys())
        target_qs = (
            LineBacklog.objects
            .filter(
                line_id__in=line_ids,
                line__line_type='PURCHASE',
                process__process_code='PURCHASE',
            )
            .select_related('line', 'process', 'product')
            .order_by('line_id', 'product_id', 'plan_date', 'sequence_no', 'id')
        )

        existing_keys = set(
            LineBacklog.objects.filter(line_id__in=line_ids)
            .values_list('line_id', 'process_id', 'product_id', 'plan_date', 'sequence_no')
        )

        delete_ids = []
        counts_by_line = defaultdict(int)
        sample_rows = []
        resolved_process_cache = {}

        for row in target_qs.iterator():
            supplier = supplier_by_line_id.get(row.line_id)
            if not supplier or not row.product_id:
                continue

            cache_key = (row.line_id, row.product_id)
            if cache_key not in resolved_process_cache:
                resolved_process_cache[cache_key] = resolve_supplier_process(
                    supplier=supplier,
                    line=row.line,
                    product=row.product,
                    preferred_process_id=None,
                    sourcing_type=None,
                    create_purchase_process=False,
                )
            resolved_process = resolved_process_cache.get(cache_key)
            if not resolved_process:
                continue
            if resolved_process.id == row.process_id:
                continue
            if str(getattr(resolved_process, 'process_code', '') or '').upper() == 'PURCHASE':
                continue

            target_key = (
                row.line_id,
                resolved_process.id,
                row.product_id,
                row.plan_date,
                row.sequence_no,
            )
            if target_key not in existing_keys:
                continue

            delete_ids.append(row.id)
            counts_by_line[row.line_id] += 1
            if len(sample_rows) < 30:
                sample_rows.append({
                    'id': row.id,
                    'line_code': getattr(row.line, 'line_code', ''),
                    'product_code': getattr(row.product, 'product_code', ''),
                    'plan_date': row.plan_date,
                    'sequence_no': row.sequence_no,
                    'from_process_id': row.process_id,
                    'to_process_id': resolved_process.id,
                    'order_qty': int(row.order_qty or 0),
                    'demand_qty_plan': int(row.demand_qty_plan or 0),
                    'plan_qty': int(row.plan_qty or 0),
                    'actual_qty': int(row.actual_qty or 0),
                })

        self.stdout.write(f'削除対象 LineBacklog: {len(delete_ids)} 件\n')

        for line_id in sorted(counts_by_line.keys()):
            line = next((x for x in purchase_lines if x.id == line_id), None)
            line_label = f'{getattr(line, "line_code", line_id)} {getattr(line, "line_name", "")}'.strip()
            self.stdout.write(f'  line_id={line_id} {line_label}: {counts_by_line[line_id]} 件')

        if sample_rows:
            self.stdout.write('\n--- サンプル ---')
            for row in sample_rows:
                self.stdout.write(
                    '  id={id} line={line_code} product={product_code} date={plan_date} seq={sequence_no} '
                    'PURCHASE->{to_process_id} order={order_qty} demand={demand_qty_plan} '
                    'plan={plan_qty} actual={actual_qty}'.format(**row)
                )

        if not apply:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('DRY RUN 完了。--apply を付けて実行すると削除が適用されます。'))
            return

        with transaction.atomic():
            deleted, _ = LineBacklog.objects.filter(id__in=delete_ids).delete()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'=== 削除完了: {deleted} 件 ==='))
        self.stdout.write('この後、対象ラインに対して pickup_purchase の再実行が必要です。')
