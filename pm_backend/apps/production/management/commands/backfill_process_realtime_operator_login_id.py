"""工程リアルタイム記録の作業者ログインIDを確実な根拠だけで補完する。"""
from collections import Counter, defaultdict

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from production.models_process_realtime import ProcessRealtimeRecord
from production.models_process_work_session import ProcessWorkSession


TARGET_RECORD_TYPES = ('PRODUCTION', 'OPERATOR_ACTION', 'EQUIPMENT_STATE')
MANUAL_RECORD_EDIT_SOURCE = 'MANUAL_RECORD_EDIT'


def _parse_session_id(raw_value):
    if isinstance(raw_value, bool):
        return None
    try:
        session_id = int(raw_value)
    except (TypeError, ValueError):
        return None
    return session_id if session_id > 0 else None


class Command(BaseCommand):
    help = '工程実績の作業者ログインIDを確実な完全一致で照合（更新は --apply 指定時のみ）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='一人に確定した作業者ログインIDのみ適用',
        )

    def _write(self, text):
        # Windowsのコンソール(既定cp932)では、作業者名等に含まれる丸数字等の文字で
        # UnicodeEncodeErrorが発生しコマンドが途中で落ちることがあるため、
        # 出力先のエンコーディングで表現できない文字は\uXXXX形式に置き換えて書き込む。
        out = getattr(self.stdout, '_out', None)
        encoding = getattr(out, 'encoding', None) or 'utf-8'
        try:
            text.encode(encoding)
        except UnicodeEncodeError:
            text = text.encode(encoding, errors='backslashreplace').decode(encoding)
        self.stdout.write(text)

    def handle(self, *args, **options):
        apply_changes = options['apply']
        users_by_full_name = defaultdict(list)
        users_by_username_display = defaultdict(list)
        valid_usernames = set()

        for user in get_user_model().objects.all().iterator():
            username = user.username or ''
            if not username:
                continue
            valid_usernames.add(username)
            full_name = f'{user.last_name or ""} {user.first_name or ""}'.strip()
            if full_name:
                users_by_full_name[full_name].append(username)
            else:
                # 姓名が空のユーザーだけ、既存の表示規則どおりusernameを表示名として扱う。
                users_by_username_display[username].append(username)

        targets = ProcessRealtimeRecord.objects.filter(
            operator_login_id__isnull=True,
            record_type__in=TARGET_RECORD_TYPES,
        )
        before_by_type = Counter(
            targets.values_list('record_type', flat=True).iterator()
        )
        target_count = sum(before_by_type.values())

        session_ids = set()
        for event_data in targets.filter(
            record_type='PRODUCTION',
            event_data__source=MANUAL_RECORD_EDIT_SOURCE,
        ).values_list('event_data', flat=True).iterator():
            session_id = _parse_session_id((event_data or {}).get('work_session_id'))
            if session_id is not None:
                session_ids.add(session_id)

        sessions_by_id = {
            session.id: session
            for session in ProcessWorkSession.objects.filter(id__in=session_ids).select_related(
                'start_record', 'end_record'
            ).iterator()
        }

        candidate_by_source = Counter()
        candidate_by_record_type = Counter()
        unresolved_by_reason = Counter()
        candidate_count = updated_count = 0

        self._write(f'実行モード={"適用" if apply_changes else "照合のみ"}')
        self._write(
            '補完前NULL件数=' + str(target_count) + ' ' + self._format_type_counts(before_by_type)
        )

        with transaction.atomic():
            for record in targets.order_by('pk').iterator():
                username, source, reason, match_count, session_id = self._classify_record(
                    record=record,
                    sessions_by_id=sessions_by_id,
                    valid_usernames=valid_usernames,
                    users_by_full_name=users_by_full_name,
                    users_by_username_display=users_by_username_display,
                )
                if username is not None:
                    candidate_count += 1
                    candidate_by_source[source] += 1
                    candidate_by_record_type[record.record_type] += 1
                    if apply_changes:
                        updated_count += ProcessRealtimeRecord.objects.filter(
                            pk=record.pk,
                            operator_login_id__isnull=True,
                        ).update(operator_login_id=username)
                    continue

                unresolved_by_reason[reason] += 1
                self._write(
                    f'未補完: id={record.pk} record_type={record.record_type} '
                    f'timestamp={record.timestamp.isoformat()} '
                    f'operator_name={record.operator_name!r} work_session_id={session_id!r} '
                    f'理由={reason} 一致件数={match_count}'
                )

        remaining = ProcessRealtimeRecord.objects.filter(
            operator_login_id__isnull=True,
            record_type__in=TARGET_RECORD_TYPES,
        )
        after_by_type = Counter(
            remaining.values_list('record_type', flat=True).iterator()
        )
        remaining_count = sum(after_by_type.values())
        projected_remaining = target_count - candidate_count
        projected_by_type = Counter({
            record_type: before_by_type[record_type] - candidate_by_record_type[record_type]
            for record_type in TARGET_RECORD_TYPES
        })

        self._write(
            '候補内訳: '
            f'セッション一致={candidate_by_source["セッション一致"]} '
            f'姓名完全一致={candidate_by_source["姓名完全一致"]} '
            f'username表示名一致={candidate_by_source["username表示名一致"]}'
        )
        if unresolved_by_reason:
            self._write(
                '未補完理由内訳: '
                + ' '.join(
                    f'{reason}={count}'
                    for reason, count in sorted(unresolved_by_reason.items())
                )
            )
        self._write(
            f'対象件数={target_count} 候補件数={candidate_count} '
            f'未補完件数={target_count - candidate_count} 更新件数={updated_count}'
        )
        self._write(
            f'補完後実NULL件数={remaining_count} '
            f'補完後実{self._format_type_counts(after_by_type)}'
        )
        self._write(
            f'適用時見込NULL件数={projected_remaining} '
            f'適用時見込{self._format_type_counts(projected_by_type)}'
        )

    def _classify_record(
        self,
        *,
        record,
        sessions_by_id,
        valid_usernames,
        users_by_full_name,
        users_by_username_display,
    ):
        operator_name = record.operator_name or ''
        event_data = record.event_data or {}
        session_id = _parse_session_id(event_data.get('work_session_id'))

        if not operator_name:
            if not (
                record.record_type == 'PRODUCTION'
                and event_data.get('source') == MANUAL_RECORD_EDIT_SOURCE
            ):
                return None, None, '作業者名空・セッション根拠なし', 0, session_id
            if session_id is None:
                return None, None, 'work_session_id不正', 0, event_data.get('work_session_id')
            session = sessions_by_id.get(session_id)
            if session is None:
                return None, None, 'セッションなし', 0, session_id
            if session.start_record_id is None or session.end_record_id is None:
                return None, None, '開始・終了記録不足', 0, session_id
            start_login_id = session.start_record.operator_login_id or ''
            end_login_id = session.end_record.operator_login_id or ''
            if not start_login_id or not end_login_id:
                return None, None, '開始・終了ログインID不足', 0, session_id
            if start_login_id != end_login_id:
                return None, None, '開始・終了ログインID不一致', 0, session_id
            if start_login_id not in valid_usernames:
                return None, None, '一致ユーザーなし', 0, session_id
            return start_login_id, 'セッション一致', None, 1, session_id

        full_name_matches = users_by_full_name.get(operator_name, [])
        if len(full_name_matches) == 1:
            return full_name_matches[0], '姓名完全一致', None, 1, session_id
        if len(full_name_matches) > 1:
            return None, None, '姓名一致が曖昧', len(full_name_matches), session_id

        username_matches = users_by_username_display.get(operator_name, [])
        if len(username_matches) == 1:
            return username_matches[0], 'username表示名一致', None, 1, session_id
        if len(username_matches) > 1:
            return None, None, 'username表示名一致が曖昧', len(username_matches), session_id
        return None, None, '名前不一致', 0, session_id

    @staticmethod
    def _format_type_counts(counts):
        return '種別内訳=' + ','.join(
            f'{record_type}:{counts.get(record_type, 0)}'
            for record_type in TARGET_RECORD_TYPES
        )
