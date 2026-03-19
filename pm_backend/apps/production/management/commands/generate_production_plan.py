import json
import logging
from collections import defaultdict
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from masters.models import Line, Product, Supplier
from production.models_line_backlog import LineBacklog
from production.models_line_plan import LinePlan
from production.models_line_gantt_plan import LineGanttPlan
from production.models_line_default_schedule_setting import LineDefaultScheduleSetting
from production.views import LineBacklogViewSet
from production.services.gantt_planning import generate_line_gantt_plans
from production.services.auto_plan_expansion import expand_processes_for_auto_plan

logger = logging.getLogger('production')


class DummyRequest:
    """簡易リクエスト（ViewSet呼び出し用）"""
    def __init__(self, data):
        self.data = data
        self.user = None


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
    # 翌月1日〜翌月末（既存互換）
    first = run_date.replace(day=1)
    next_month = (first + timedelta(days=32)).replace(day=1)
    start = next_month
    end = (next_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return start, end


def iter_lines(line_ids):
    if line_ids:
        # 自動計画から明示指定されたラインは種別を問わず対象化
        qs = Line.objects.filter(is_active=True, id__in=line_ids)
    else:
        qs = Line.objects.filter(is_active=True, line_type='PROD')
    return list(qs)


def run_pickup(line_id, start_date, end_date):
    """ライン種別に応じて需要取り込みを実行する。"""
    viewset = LineBacklogViewSet()
    viewset.format_kwarg = None
    viewset.kwargs = {}
    line = Line.objects.filter(id=line_id).first()
    if not line:
        raise CommandError(f'Line not found: {line_id}')

    if line.line_type == 'PURCHASE':
        supplier = Supplier.objects.filter(supplier_code=line.line_code).first()
        if not supplier:
            raise CommandError(
                f'PURCHASE line {line.line_code} に対応する仕入先が見つかりません'
            )
        req = DummyRequest({
            'supplier_id': supplier.id,
            'start_date': str(start_date),
            'end_date': str(end_date),
        })
        viewset.request = req
        viewset.pickup_purchase(req)
        return

    req = DummyRequest({
        'line_id': line_id,
        'start_date': str(start_date),
        'end_date': str(end_date),
    })
    viewset.request = req
    viewset.pickup(req)


def fetch_final_demands(line_id, start_date, end_date):
    """自動計画対象の需要行を取得（ライン種別に応じて条件を切り替え）"""
    line_type = Line.objects.filter(id=line_id).values_list('line_type', flat=True).first()
    base_qs = LineBacklog.objects.filter(
        line_id=line_id,
        plan_date__range=[start_date, end_date],
        sequence_no=0,
        demand_qty_plan__gt=0,
    )

    # 社内ライン(PROD)はライン最終品のみを対象にする。
    # 外作/購入ライン(OUTSOURCE/PURCHASE)は最終品フラグに依存せず需要行を対象にする。
    if line_type == 'PROD':
        base_qs = base_qs.filter(product__is_line_final_product=True)
    return base_qs.values('plan_date', 'process_id', 'product_id', 'demand_qty_plan')


def delete_existing(line_id, start_date, end_date):
    """
    指定期間の計画系を一括クリア（需要有無に関わらずライン最終品計画を再生成する方針）
    - LinePlan: 期間内すべて削除
    - LineGanttPlan: 期間内すべて削除
    - LineBacklog: plan_idひも付き計画行（sequence_no>0）のみ削除
    """
    plan_ids = list(LinePlan.objects.filter(
        line_id=line_id,
        plan_date__range=[start_date, end_date],
    ).values_list('plan_id', flat=True))

    LinePlan.objects.filter(
        line_id=line_id,
        plan_date__range=[start_date, end_date],
    ).delete()

    LineGanttPlan.objects.filter(
        line_id=line_id,
        plan_date__range=[start_date, end_date],
    ).delete()

    if plan_ids:
        LineBacklog.objects.filter(
            plan_id__in=plan_ids,
            sequence_no__gt=0,
        ).delete()
    return plan_ids


def build_product_code_cache(product_ids):
    cache = {}
    if not product_ids:
        return cache
    for pid, code in Product.objects.filter(id__in=product_ids).values_list('id', 'product_code'):
        cache[pid] = code
    return cache


def generate_line_plans(line_id, demand_rows):
    """ライン最終品需要からLinePlanを作成（手動save互換）"""
    items_by_date = defaultdict(list)
    product_ids = set()
    for row in demand_rows:
        items_by_date[row['plan_date']].append(row)
        product_ids.add(row['product_id'])

    product_code_cache = build_product_code_cache(product_ids)

    created = 0
    created_plan_ids = []

    # 既存の自動対象外計画を考慮したmax sequence取得
    existing_max = {
        rec['plan_date']: rec['max_seq']
        for rec in LinePlan.objects.filter(
            line_id=line_id,
            plan_date__in=items_by_date.keys(),
        ).exclude(product_id__in=product_ids).values('plan_date').annotate(max_seq=Max('sequence_no'))
    }

    for plan_date, items in items_by_date.items():
        # product_code -> process_id で安定ソート
        for it in items:
            if it['product_id'] not in product_code_cache:
                product_code_cache[it['product_id']] = Product.objects.filter(
                    id=it['product_id']
                ).values_list('product_code', flat=True).first() or str(it['product_id'])
        items.sort(key=lambda x: (product_code_cache.get(x['product_id'], ''), x['process_id'] or 0))

        next_seq = (existing_max.get(plan_date) or 0) + 1

        for it in items:
            plan_qty = int(Decimal(it['demand_qty_plan'] or 0))
            if plan_qty <= 0:
                continue
            product_code = product_code_cache.get(it['product_id'], str(it['product_id']))

            qty_label = str(plan_qty).rstrip('0').rstrip('.')
            if '.' in qty_label:
                qty_label = qty_label.replace('.', 'p')
            plan_id = f"{product_code}_{plan_date.strftime('%Y%m%d')}_{qty_label}_{next_seq}"

            LinePlan.objects.create(
                plan_date=plan_date,
                process_id=it['process_id'],
                product_id=it['product_id'],
                line_id=line_id,
                plan_qty=plan_qty,
                plan_id=plan_id,
                sequence_no=next_seq,
            )
            created += 1
            created_plan_ids.append(plan_id)
            next_seq += 1

    return created, created_plan_ids


def apply_purchase_plan_to_backlog(line_id, start_date, end_date, demand_rows):
    """
    購買ラインは LineBacklog(sequence_no=1) に plan_qty を保存する（1ロット固定）。
    sequence_no=0 は基礎データ行（需要・実績・在庫・進度・調整）として保護し、触らない。
    需要が消えた日の seq=1 レコードは削除する。
    """
    demand_map = {}
    process_map = {}
    product_ids = set()
    for row in demand_rows:
        plan_date = row['plan_date']
        product_id = row['product_id']
        key = (product_id, plan_date)
        qty = int(Decimal(row.get('demand_qty_plan') or 0))
        demand_map[key] = max(qty, 0)
        process_map[key] = row.get('process_id')
        product_ids.add(product_id)

    # plan_id 生成用に製品コードを取得
    product_code_map = {
        p.id: p.product_code
        for p in Product.objects.filter(id__in=product_ids).only('id', 'product_code')
    }

    # 期間内の seq=1 既存レコードを取得
    qs = LineBacklog.objects.filter(
        line_id=line_id,
        plan_date__range=[start_date, end_date],
        sequence_no=1,
    )
    existing_map = {(obj.product_id, obj.plan_date): obj for obj in qs}

    created = 0
    updated = 0
    to_update = []
    to_create = []
    to_delete_ids = []

    for key, qty_val in demand_map.items():
        product_id, plan_date = key
        obj = existing_map.pop(key, None)
        product_code = product_code_map.get(product_id, str(product_id))
        plan_id = f"{product_code}_{plan_date.strftime('%Y%m%d')}_{qty_val}_1"
        if obj is None:
            process_id = process_map.get(key)
            if not process_id:
                continue
            to_create.append(LineBacklog(
                plan_date=plan_date,
                process_id=process_id,
                product_id=product_id,
                line_id=line_id,
                sequence_no=1,
                plan_qty=qty_val,
                plan_id=plan_id,
            ))
            created += 1
            continue
        if int(obj.plan_qty or 0) != qty_val or obj.plan_id != plan_id:
            obj.plan_qty = qty_val
            obj.plan_id = plan_id
            to_update.append(obj)
            updated += 1

    # 需要が消えた seq=1 レコードは削除（plan_qty=0 に戻さず削除）
    for obj in existing_map.values():
        to_delete_ids.append(obj.id)

    if to_create:
        LineBacklog.objects.bulk_create(to_create, batch_size=1000)
    if to_update:
        LineBacklog.objects.bulk_update(to_update, ['plan_qty', 'plan_id'], batch_size=1000)
    if to_delete_ids:
        LineBacklog.objects.filter(id__in=to_delete_ids).delete()

    return created, updated


def generate_gantt(line_id, start_date, end_date):
    """LineGanttPlan再生成（手動generate互換）"""
    default_setting = LineDefaultScheduleSetting.objects.filter(line_id=line_id).first()
    if default_setting and default_setting.final_process_start_time:
        start_time_str = default_setting.final_process_start_time.strftime('%H:%M')
        adjust_break = default_setting.adjust_to_break_end
    else:
        start_time_str = '08:00'
        adjust_break = True

    plans = generate_line_gantt_plans(
        line_id=line_id,
        start_date=str(start_date),
        end_date=str(end_date),
        clear_existing=False,
        final_process_start_time=start_time_str,
        adjust_to_break_end=adjust_break,
    )

    new_plan_ids = []
    for plan in plans:
        LineGanttPlan.objects.update_or_create(
            plan_id=plan['plan_id'],
            defaults={
                'line_id': plan['line_id'],
                'product_id': plan['product_id'],
                'plan_date': plan['plan_date'],
                'plan_qty': plan['plan_qty'],
                'sequence_no': plan['sequence_no'],
                'start_datetime': plan['start_datetime'],
                'end_datetime': plan['end_datetime'],
                'processes_plan': plan['processes_plan'],
            }
        )
        new_plan_ids.append(plan['plan_id'])

    old_qs = LineGanttPlan.objects.filter(
        line_id=line_id,
        plan_date__range=[start_date, end_date],
    )
    if new_plan_ids:
        old_qs = old_qs.exclude(plan_id__in=new_plan_ids)
    old_qs.delete()


class Command(BaseCommand):
    help = 'LineDemandを元に生産計画を自動生成する（手動計画と同等の後処理込み）'

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

            with transaction.atomic():
                # Step1: pickup
                run_pickup(line.id, line_start, line_end)

                # Step2: ライン最終品需要抽出
                demand_rows = list(fetch_final_demands(line.id, line_start, line_end))
                if not demand_rows:
                    self.stdout.write(self.style.WARNING('  需要なし（ライン最終品）'))
                    if dry_run:
                        raise transaction.TransactionManagementError('dry-run rollback')
                    continue

                # Step3: カスケード削除（期間一括クリア）
                delete_existing(line.id, line_start, line_end)

                if line.line_type == 'PURCHASE':
                    # 購買は sequence_no=1 に計画を保存する（seq=0 は基礎データ行として保護）。
                    created_count, updated_count = apply_purchase_plan_to_backlog(
                        line.id, line_start, line_end, demand_rows
                    )
                    summary['created'] += created_count
                    summary['updated'] += updated_count
                else:
                    # Step4: LinePlan作成
                    created_count, _ = generate_line_plans(line.id, demand_rows)
                    summary['created'] += created_count

                    # Step5a: 工程展開
                    expand_processes_for_auto_plan(
                        line.id,
                        line_start,
                        line_end,
                        force_direct_process=bool(line.use_direct_process),
                    )

                    # Step5b: ガント生成（在庫計算は日次バッチに任せる）
                    generate_gantt(line.id, line_start, line_end)

                if dry_run:
                    raise transaction.TransactionManagementError('dry-run rollback')

            if stats is not None:
                stats.append({
                    'line_id': line.id,
                    'line_code': line.line_code,
                    'start': str(line_start),
                    'end': str(line_end),
                    'created': created_count,
                    'updated': updated_count if line.line_type == 'PURCHASE' else 0,
                })

        self.stdout.write(self.style.SUCCESS(
            f'完了 lines={summary["lines"]} created={summary["created"]} updated={summary["updated"]}'
        ))
