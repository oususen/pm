"""
ProcessRealtimeRecord(OPERATOR_ACTION, PAUSE/TEMP_END)の既存データのうち、
interruption_reason_code が空文字の行を、イベント内の理由文字列から完全一致で補完する。

既定ではドライランのみで更新しない（--apply 指定時のみ実更新する）。
ファジーマッチングは行わない。一致しない行は一覧表示のみで、推測による割当ては行わない。
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from masters.models import InterruptionReason
from production.models_process_realtime import ProcessRealtimeRecord

# 一般工程における表記ゆれ辞書。
# 仕様書/ブレーキスポット入力整備実装計画.md の確定ルール「材料待ち・部品ショート→部品待ち」と同じ内容。
# 一般工程特有の表記ゆれを新たに追加しないこと。
REASON_NORMALIZATION_MAP = {
    '材料待ち': '部品待ち',
    '部品ショート': '部品待ち',
}

# 対象となる作業者アクション（= InterruptionReason.operation の値と同じ）
TARGET_ACTIONS = (InterruptionReason.OPERATION_PAUSE, InterruptionReason.OPERATION_TEMP_END)


def _resolve_raw_reason(event_data, action):
    """action に応じた理由文字列を優先順位に沿って取り出す。非空文字列が無ければ空文字を返す。"""
    if action == InterruptionReason.OPERATION_PAUSE:
        candidates = (event_data.get('pause_reason'), event_data.get('operator_action_reason'))
    elif action == InterruptionReason.OPERATION_TEMP_END:
        candidates = (event_data.get('temp_end_reason'), event_data.get('operator_action_reason'))
    else:
        candidates = ()
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return ''


def _normalize_reason(raw_reason):
    """表記ゆれ辞書で正規化する（辞書に無ければそのまま返す）。"""
    if not raw_reason:
        return ''
    return REASON_NORMALIZATION_MAP.get(raw_reason, raw_reason)


def _extract_plan_date(event_data):
    """一覧表示用に plan_date を参考情報として取り出す（一致判定には使わない）。"""
    plan_target = event_data.get('plan_target')
    if isinstance(plan_target, dict) and plan_target.get('plan_date'):
        return plan_target.get('plan_date')
    session = event_data.get('session')
    if isinstance(session, dict) and session.get('plan_date'):
        return session.get('plan_date')
    return ''


class Command(BaseCommand):
    help = (
        'ProcessRealtimeRecord(OPERATOR_ACTION, PAUSE/TEMP_END) のうち '
        'interruption_reason_code が空文字の行を、理由文字列との完全一致でコード補完する。'
        '既定はドライランのみ（--apply 指定時のみ実更新）。'
    )

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='実際に interruption_reason_code を更新する（既定はドライラン）')

    def handle(self, *args, **options):
        apply_changes = bool(options.get('apply'))

        # InterruptionReason(line_category='3') を (operation, display_name) をキーに事前マップ化
        reason_code_map = defaultdict(list)
        for row in InterruptionReason.objects.filter(
            line_category='3',
            operation__in=TARGET_ACTIONS,
            is_active=True,
        ).values('operation', 'display_name', 'code'):
            reason_code_map[(row['operation'], row['display_name'])].append(row['code'])

        targets = ProcessRealtimeRecord.objects.filter(
            record_type='OPERATOR_ACTION',
            interruption_reason_code='',
        ).order_by('pk')

        target_count = 0
        matched_rows = []  # [(record, code, raw_reason, normalized_reason)]
        unmatched_rows = []  # [{...}]

        for record in targets.iterator():
            event_data = record.event_data
            if not isinstance(event_data, dict):
                continue
            action = event_data.get('action')
            if action not in TARGET_ACTIONS:
                continue

            target_count += 1
            raw_reason = _resolve_raw_reason(event_data, action)
            normalized_reason = _normalize_reason(raw_reason)

            codes = reason_code_map.get((action, normalized_reason), []) if normalized_reason else []

            if len(codes) == 1:
                matched_rows.append((record, codes[0], raw_reason, normalized_reason))
            else:
                unmatched_rows.append({
                    'id': record.pk,
                    'action': action,
                    'raw_reason': raw_reason,
                    'normalized_reason': normalized_reason,
                    'plan_date': _extract_plan_date(event_data),
                    'process_id': record.process_id,
                    'ambiguous': len(codes) > 1,
                })

        updated_count = 0
        if apply_changes:
            with transaction.atomic():
                for record, code, _raw_reason, _normalized_reason in matched_rows:
                    # 並行更新事故防止のため、WHERE句で空文字条件を再確認してから更新する
                    updated_count += ProcessRealtimeRecord.objects.filter(
                        pk=record.pk,
                        interruption_reason_code='',
                    ).update(interruption_reason_code=code)

        # --- 集計結果の出力 ---
        self.stdout.write(f'対象件数: {target_count}')
        self.stdout.write(f'完全一致候補件数: {len(matched_rows)}')

        code_breakdown = defaultdict(int)
        for _record, code, _raw_reason, _normalized_reason in matched_rows:
            code_breakdown[code] += 1
        for code in sorted(code_breakdown):
            self.stdout.write(f'  code={code}: {code_breakdown[code]}件')

        self.stdout.write(f'一致しない行: {len(unmatched_rows)}件')
        for row in unmatched_rows:
            ambiguous_note = ' (複数候補あり)' if row['ambiguous'] else ''
            self.stdout.write(
                f'  id={row["id"]} action={row["action"]} reason={row["raw_reason"]!r} '
                f'正規化後={row["normalized_reason"]!r} plan_date={row["plan_date"]} '
                f'process_id={row["process_id"]}{ambiguous_note}'
            )

        if apply_changes:
            self.stdout.write(f'実更新件数: {updated_count}')
        else:
            self.stdout.write('ドライラン実行のため、DBは更新していません（--apply で実更新）')
