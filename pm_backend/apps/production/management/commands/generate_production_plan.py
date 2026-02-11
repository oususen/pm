import json
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from masters.models import Line, RoutingStep, BOM, BOMItem, Product
from production.models_line_backlog import LineBacklog
from production.models_line_plan import LinePlan
from production.views import LineBacklogViewSet

logger = logging.getLogger('production')


def parse_date_safe(val):
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(val, '%Y-%m-%d').date()
    except Exception:
        raise CommandError(f'Invalid date format: {val}, expected YYYY-MM-DD')


def load_config(path_str):
    if not path_str:
        return None
    path = Path(path_str)
    if not path.exists():
        raise CommandError(f'Config file not found: {path}')
    try:
        if path.suffix.lower() in ['.yml', '.yaml']:
            import yaml  # type: ignore
            return yaml.safe_load(path.read_text(encoding='utf-8'))
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        raise CommandError(f'Failed to load config {path}: {e}')


def month_range(run_date: date):
    # 翌月1日〜翌月末
    first = run_date.replace(day=1)
    next_month = (first + timedelta(days=32)).replace(day=1)
    start = next_month
    end = (next_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return start, end


def iter_lines(line_ids):
    qs = Line.objects.filter(is_active=True, line_type='PROD')
    if line_ids:
        qs = qs.filter(id__in=line_ids)
    return list(qs)


def ensure_base_row(line_id, process_id, product_id, plan_date):
    obj, _ = LineBacklog.objects.get_or_create(
        line_id=line_id,
        process_id=process_id,
        product_id=product_id,
        plan_date=plan_date,
        sequence_no=0,
        defaults={
            'order_qty': 0,
            'plan_qty': 0,
            'demand_qty_plan': 0,
            'actual_qty': 0,
            'stock_qty': 0,
            'planned_stock_qty': 0,
            'adjust_qty': 0,
            'scrap_adjust_qty': 0,
            'scrap_qty': 0,
            'actual_shipment_qty': 0,
        },
    )
    return obj


def upsert_plan(line_id, process_id, product_id, plan_date, plan_qty, sequence_no=1):
    obj, created = LineBacklog.objects.update_or_create(
        line_id=line_id,
        process_id=process_id,
        product_id=product_id,
        plan_date=plan_date,
        sequence_no=sequence_no,
        defaults={
            'plan_qty': plan_qty,
            'order_qty': 0,
            'demand_qty_plan': 0,
        }
    )
    return obj, created


def collect_targets(line: Line):
    """
    ライン配下の工程×製品を収集。
    - RoutingStep.line が対象ライン
    - または RoutingStep.process.line が対象ライン（工程側にライン紐付けがあるケース）
    - BOMItem.line が対象ライン
    - 連産品代表品（is_coproduct_driver）も対象に含める
    """
    from django.db.models import Q

    steps = RoutingStep.objects.filter(
        Q(line=line) | Q(process__line=line),
        routing__is_active=True,
    ).select_related('output_product', 'routing__product', 'process')

    target_keys = set()
    for st in steps:
        # pickup() と同じく output_product → routing.product のフォールバック
        product_id = st.output_product_id or (st.routing.product_id if st.routing else None)
        if product_id and st.process_id:
            target_keys.add((st.process_id, product_id))

    bom_items = BOMItem.objects.filter(line=line, bom__is_active=True)
    for bi in bom_items:
        proc_id = bi.process_id or getattr(bi.bom, 'process_id', None)
        if proc_id and bi.child_product_id:
            target_keys.add((proc_id, bi.child_product_id))

    # 連産品代表品（is_coproduct_driver）: pickup()が需要を作成する製品を漏れなく含める
    copro_boms = BOM.objects.filter(
        is_coproduct=True, is_active=True,
    ).prefetch_related('items')
    for bom in copro_boms:
        for item in bom.items.all():
            if not item.is_coproduct_driver:
                continue
            # この代表品がラインの工程に紐づいているか確認
            driver_steps = RoutingStep.objects.filter(
                Q(line=line) | Q(process__line=line),
                routing__is_active=True,
            ).filter(
                Q(output_product_id=item.child_product_id) |
                Q(routing__product_id=item.child_product_id)
            ).select_related('process')
            for ds in driver_steps:
                if ds.process_id:
                    target_keys.add((ds.process_id, item.child_product_id))

    return target_keys


def get_demand_only(line_id, start_date, end_date):
    """需要取り込みだけ実行し、LineBacklogから需要列を取得する"""
    viewset = LineBacklogViewSet()
    viewset.format_kwarg = None
    viewset.kwargs = {}

    # パーサ依存を避けるため、data属性だけ持つダミーリクエストを渡す
    class DummyRequest:
        def __init__(self, data):
            self.data = data
            self.user = None

    req = DummyRequest({
        'line_id': line_id,
        'start_date': str(start_date),
        'end_date': str(end_date),
    })
    viewset.request = req
    viewset.pickup(req)

    return LineBacklog.objects.filter(
        line_id=line_id,
        plan_date__range=[start_date, end_date]
    ).values('plan_date', 'process_id', 'product_id', 'demand_qty_plan')


class Command(BaseCommand):
    help = 'LineDemandを元に生産計画を自動生成する（在庫再計算なし）'

    def add_arguments(self, parser):
        parser.add_argument('--line', dest='lines', nargs='+', type=int, help='対象ラインID（複数可）')
        parser.add_argument('--start', dest='start')
        parser.add_argument('--end', dest='end')
        parser.add_argument('--run-date', dest='run_date')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--config', dest='config_path')

    def handle(self, *args, **options):
        lines = options.get('lines') or []
        start_input = options.get('start')
        end_input = options.get('end')
        run_date_input = options.get('run_date')
        dry_run = options.get('dry_run')
        config_path = options.get('config_path')
        stats = options.get('stats', None)

        run_date = parse_date_safe(run_date_input) or datetime.now().date()
        default_start, default_end = month_range(run_date)
        start_date = parse_date_safe(start_input) or default_start
        end_date = parse_date_safe(end_input) or default_end

        config = load_config(config_path)

        targets = iter_lines(lines)
        if not targets:
            self.stdout.write(self.style.WARNING('対象ラインがありません（is_active=True）。'))
            return

        summary = {'lines': 0, 'created': 0, 'updated': 0}

        for line in targets:
            summary['lines'] += 1
            line_start, line_end = start_date, end_date
            if config and str(line.id) in (config.get('lines') or {}):
                cfg = config['lines'][str(line.id)]
                line_start = parse_date_safe(cfg.get('start')) or line_start
                line_end = parse_date_safe(cfg.get('end')) or line_end

            self.stdout.write(f'ライン {line.line_code} ({line.id}) 期間 {line_start}〜{line_end}')

            target_keys = collect_targets(line)
            if not target_keys:
                self.stdout.write(self.style.WARNING('  対象工程×製品なし'))
                continue

            with transaction.atomic():
                demand_rows = get_demand_only(line.id, line_start, line_end)

                # 需要から計画アイテムを収集
                plan_items = []
                for row in demand_rows:
                    proc_id = row['process_id']
                    prod_id = row['product_id']
                    if not proc_id or not prod_id:
                        continue
                    if (proc_id, prod_id) not in target_keys:
                        continue
                    demand_qty = row.get('demand_qty_plan') or 0
                    plan_qty = int(Decimal(demand_qty)) if demand_qty is not None else 0
                    if plan_qty > 0:
                        plan_items.append({
                            'product_id': prod_id,
                            'process_id': proc_id,
                            'plan_date': row['plan_date'],
                            'plan_qty': plan_qty,
                        })

                if plan_items:
                    affected_products = set(item['product_id'] for item in plan_items)

                    # 既存LinePlan・関連LineBacklog(計画行)を削除
                    old_plan_ids = list(LinePlan.objects.filter(
                        line_id=line.id,
                        plan_date__range=[line_start, line_end],
                        product_id__in=affected_products,
                    ).values_list('plan_id', flat=True))
                    LinePlan.objects.filter(
                        line_id=line.id,
                        plan_date__range=[line_start, line_end],
                        product_id__in=affected_products,
                    ).delete()
                    if old_plan_ids:
                        LineBacklog.objects.filter(
                            plan_id__in=old_plan_ids,
                            sequence_no__gt=0,
                        ).delete()

                    # LinePlan レコード作成（手動保存と同じテーブル）
                    seq_by_date = {}
                    product_code_cache = {}
                    items_for_expand = []
                    for item in plan_items:
                        pd = item['plan_date']
                        if pd not in seq_by_date:
                            max_seq = LinePlan.objects.filter(
                                line_id=line.id, plan_date=pd,
                            ).order_by('-sequence_no').values_list('sequence_no', flat=True).first()
                            seq_by_date[pd] = (max_seq or 0) + 1
                        seq = seq_by_date[pd]
                        seq_by_date[pd] = seq + 1

                        prod_id = item['product_id']
                        if prod_id not in product_code_cache:
                            product_code_cache[prod_id] = (
                                Product.objects.filter(id=prod_id)
                                .values_list('product_code', flat=True).first() or str(prod_id)
                            )
                        product_code = product_code_cache[prod_id]
                        plan_id = f"{product_code}_{pd.strftime('%Y%m%d')}_{item['plan_qty']}_{seq}"

                        LinePlan.objects.create(
                            plan_date=pd,
                            process_id=item['process_id'],
                            product_id=prod_id,
                            line_id=line.id,
                            plan_qty=item['plan_qty'],
                            plan_id=plan_id,
                            sequence_no=seq,
                        )
                        summary['created'] += 1
                        items_for_expand.append({
                            'product_id': prod_id,
                            'plan_date': str(pd),
                            'plan_qty': item['plan_qty'],
                            'sequence_no': seq,
                        })

                    # 計画を工程レベルに展開（手動操作の「expand_processes」に相当）
                    class DummyRequest:
                        def __init__(self, data):
                            self.data = data
                            self.user = None

                    viewset = LineBacklogViewSet()
                    viewset.format_kwarg = None
                    viewset.kwargs = {}
                    req = DummyRequest({
                        'line_id': line.id,
                        'start_date': str(line_start),
                        'end_date': str(line_end),
                        'items': items_for_expand,
                        'read_only': False,
                        'include_coproduct_children': True,
                    })
                    viewset.request = req
                    try:
                        viewset.expand_processes(req)
                    except Exception as e:
                        logger.error(f'expand_processes failed line={line.id}: {e}', exc_info=True)

                if dry_run:
                    raise transaction.TransactionManagementError('dry-run rollback')

            if stats is not None:
                stats.append({
                    'line_id': line.id,
                    'line_code': line.line_code,
                    'start': str(line_start),
                    'end': str(line_end),
                    'created': summary['created'],
                    'updated': summary['updated'],
                })

        self.stdout.write(self.style.SUCCESS(
            f'完了 lines={summary["lines"]} created={summary["created"]} updated={summary["updated"]}'
        ))
