from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Sum

from masters.models import Line, Process
from production.models_brake_line_record import BrakeLineRecord
from production.models_line_backlog import LineBacklog
from production.models_record_inquiry_setting import ProductionRecordInquirySetting


def parse_date_safe(raw_value):
    if not raw_value:
        raise CommandError('--date は必須です（YYYY-MM-DD）')
    try:
        return date.fromisoformat(str(raw_value))
    except ValueError as exc:
        raise CommandError('--date は YYYY-MM-DD 形式で指定してください') from exc


class Command(BaseCommand):
    help = 'スポットライン実績(BrakeLineRecord)を LineBacklog(sequence_no=0) に補正反映する'

    def add_arguments(self, parser):
        parser.add_argument('--date', required=True, help='対象計画日（YYYY-MM-DD）')
        parser.add_argument('--line-code', dest='line_codes', nargs='*', help='対象ラインコード。未指定時はTAB_SPOT設定を使用')
        parser.add_argument('--process-code', dest='process_codes', nargs='*', help='対象工程コード。未指定時は対象ライン配下の全工程')
        parser.add_argument('--dry-run', action='store_true', help='更新せず集計結果だけ確認する')
        parser.add_argument('--reset-missing', action='store_true', help='対象範囲のseq0実績を一旦0に戻してから集計値で再設定する')

    def handle(self, *args, **options):
        plan_date = parse_date_safe(options.get('date'))
        line_codes = [str(code).strip() for code in (options.get('line_codes') or []) if str(code).strip()]
        process_codes = [str(code).strip() for code in (options.get('process_codes') or []) if str(code).strip()]
        dry_run = bool(options.get('dry_run'))
        reset_missing = bool(options.get('reset_missing'))

        if not line_codes:
            setting = ProductionRecordInquirySetting.objects.filter(
                tab_key=ProductionRecordInquirySetting.TAB_SPOT
            ).first()
            if not setting or not setting.target_line_codes:
                raise CommandError('TAB_SPOT の対象ライン設定が見つかりません')
            line_codes = [str(code).strip() for code in setting.target_line_codes if str(code).strip()]

        lines = list(
            Line.objects.filter(line_code__in=line_codes, is_active=True)
            .values('id', 'line_code', 'line_name')
        )
        if not lines:
            raise CommandError(f'対象ラインが見つかりません: {line_codes}')
        line_ids = [row['id'] for row in lines]

        process_qs = Process.objects.filter(line_id__in=line_ids, is_active=True)
        if process_codes:
            process_qs = process_qs.filter(process_code__in=process_codes)
        processes = list(process_qs.values('id', 'process_code', 'process_name', 'line_id'))
        if not processes:
            raise CommandError('対象工程が見つかりません')
        process_ids = [row['id'] for row in processes]

        aggregated = list(
            BrakeLineRecord.objects
            .filter(
                plan_date=plan_date,
                line_id__in=line_ids,
                process_id__in=process_ids,
                operator_action__in=[
                    BrakeLineRecord.OPERATOR_ACTION_END,
                    BrakeLineRecord.OPERATOR_ACTION_PAUSE,
                ],
                qty__gt=0,
                product_id__isnull=False,
            )
            .values('line_id', 'process_id', 'product_id', 'product__product_code')
            .annotate(total_qty=Sum('qty'))
            .order_by('line_id', 'process_id', 'product__product_code')
        )

        if not aggregated:
            self.stdout.write(self.style.WARNING('対象実績がありません'))
            return

        def load_backlog_map():
            return {
                (row.line_id, row.process_id, row.product_id): row
                for row in LineBacklog.objects.filter(
                    plan_date=plan_date,
                    line_id__in=line_ids,
                    process_id__in=process_ids,
                    sequence_no=0,
                )
            }

        backlog_map = load_backlog_map()

        created = 0
        updated = 0
        unchanged = 0
        reset = 0
        total_qty = 0

        preview_rows = []

        with transaction.atomic():
            if reset_missing:
                reset_qs = LineBacklog.objects.filter(
                    plan_date=plan_date,
                    line_id__in=line_ids,
                    process_id__in=process_ids,
                    sequence_no=0,
                ).exclude(actual_qty=0)
                if not dry_run:
                    reset = reset_qs.update(actual_qty=0)
                else:
                    reset = reset_qs.count()
                backlog_map = load_backlog_map()

            for row in aggregated:
                key = (row['line_id'], row['process_id'], row['product_id'])
                target_qty = int(row['total_qty'] or 0)
                total_qty += target_qty
                backlog = backlog_map.get(key)
                before_qty = int(backlog.actual_qty or 0) if backlog else 0

                preview_rows.append({
                    'line_id': row['line_id'],
                    'process_id': row['process_id'],
                    'product_id': row['product_id'],
                    'product_code': row['product__product_code'] or '',
                    'before_qty': before_qty,
                    'after_qty': target_qty,
                })

                if backlog is None:
                    if not dry_run:
                        LineBacklog.objects.create(
                            plan_date=plan_date,
                            line_id=row['line_id'],
                            process_id=row['process_id'],
                            product_id=row['product_id'],
                            sequence_no=0,
                            actual_qty=target_qty,
                        )
                    created += 1
                    continue

                if before_qty == target_qty:
                    unchanged += 1
                    continue

                if not dry_run:
                    backlog.actual_qty = target_qty
                    backlog.save(update_fields=['actual_qty', 'updated_at'])
                updated += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            f'対象日: {plan_date} / ライン: {", ".join(row["line_code"] for row in lines)}'
        )
        self.stdout.write(
            f'工程: {", ".join(row["process_code"] for row in processes)} / 品番数: {len(aggregated)} / 実績合計: {total_qty}'
        )
        self.stdout.write(
            f'created={created} updated={updated} unchanged={unchanged} reset={reset} dry_run={dry_run}'
        )

        for row in preview_rows[:20]:
            self.stdout.write(
                f'  {row["product_code"]}: {row["before_qty"]} -> {row["after_qty"]}'
            )

        if len(preview_rows) > 20:
            self.stdout.write(f'  ... 他 {len(preview_rows) - 20} 件')
