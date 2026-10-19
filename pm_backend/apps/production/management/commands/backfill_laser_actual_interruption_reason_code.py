"""
LaserActual(operator_action PAUSE/TEMP_END)の既存データのうち、
interruption_reason_code が空文字の行を、operator_action_reason から完全一致で補完する。

既定ではドライランのみで更新しない（--apply 指定時のみ実更新する）。
ファジーマッチング・表記ゆれ辞書は使用しない。一致しない行は一覧表示のみ。
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from masters.models import InterruptionReason
from production.models_laser_actual import LaserActual

TARGET_ACTIONS = (LaserActual.OPERATOR_ACTION_PAUSE, LaserActual.OPERATOR_ACTION_TEMP_END)


class Command(BaseCommand):
    help = (
        'LaserActual(PAUSE/TEMP_END) のうち interruption_reason_code が空文字の行を、'
        'operator_action_reason との完全一致でコード補完する。'
        '既定はドライランのみ（--apply 指定時のみ実更新）。'
    )

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='実際に interruption_reason_code を更新する（既定はドライラン）')

    def handle(self, *args, **options):
        apply_changes = bool(options.get('apply'))

        reason_code_map = defaultdict(list)
        for row in InterruptionReason.objects.filter(
            line_category='1',
            operation__in=TARGET_ACTIONS,
            is_active=True,
        ).values('operation', 'display_name', 'code'):
            reason_code_map[(row['operation'], row['display_name'])].append(row['code'])

        targets = LaserActual.objects.filter(
            operator_action__in=TARGET_ACTIONS,
            interruption_reason_code='',
        ).order_by('pk')

        target_count = 0
        matched_rows = []
        unmatched_rows = []

        for record in targets.iterator():
            target_count += 1
            raw_reason = (record.operator_action_reason or '').strip()
            codes = reason_code_map.get((record.operator_action, raw_reason), []) if raw_reason else []

            if len(codes) == 1:
                matched_rows.append((record, codes[0], raw_reason))
            else:
                unmatched_rows.append({
                    'id': record.pk,
                    'action': record.operator_action,
                    'raw_reason': raw_reason,
                    'work_date': record.work_date,
                    'ambiguous': len(codes) > 1,
                })

        updated_count = 0
        if apply_changes:
            with transaction.atomic():
                for record, code, _raw_reason in matched_rows:
                    updated_count += LaserActual.objects.filter(
                        pk=record.pk,
                        interruption_reason_code='',
                    ).update(interruption_reason_code=code)

        self.stdout.write(f'対象件数: {target_count}')
        self.stdout.write(f'完全一致候補件数: {len(matched_rows)}')

        code_breakdown = defaultdict(int)
        for _record, code, _raw_reason in matched_rows:
            code_breakdown[code] += 1
        for code in sorted(code_breakdown):
            self.stdout.write(f'  code={code}: {code_breakdown[code]}件')

        self.stdout.write(f'一致しない行: {len(unmatched_rows)}件')
        for row in unmatched_rows:
            ambiguous_note = ' (複数候補あり)' if row['ambiguous'] else ''
            self.stdout.write(
                f'  id={row["id"]} action={row["action"]} reason={row["raw_reason"]!r} '
                f'work_date={row["work_date"]}{ambiguous_note}'
            )

        if apply_changes:
            self.stdout.write(f'実更新件数: {updated_count}')
        else:
            self.stdout.write('ドライラン実行のため、DBは更新していません（--apply で実更新）')
