from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from masters.models import InterruptionReason, Line, Process
from production.models_process_realtime import ProcessRealtimeRecord


class BackfillProcessRealtimeInterruptionReasonCodeCommandTest(TestCase):
    def setUp(self):
        self.line = Line.objects.create(
            line_code='L9001',
            line_name='試験ライン',
        )
        self.process = Process.objects.create(
            process_code='9001',
            process_name='試験工程',
            line=self.line,
        )

        # 一般工程のマスタ（line_category='3'）
        InterruptionReason.objects.create(
            code='3101', line_category='3', category='1',
            display_name='設備トラブル', operation=InterruptionReason.OPERATION_PAUSE,
        )
        InterruptionReason.objects.create(
            code='3901', line_category='3', category='9',
            display_name='部品待ち', operation=InterruptionReason.OPERATION_PAUSE,
        )
        InterruptionReason.objects.create(
            code='3905', line_category='3', category='9',
            display_name='他へ製品切り替え', operation=InterruptionReason.OPERATION_TEMP_END,
        )
        InterruptionReason.objects.create(
            code='3997', line_category='3', category='9',
            display_name='その他', operation=InterruptionReason.OPERATION_PAUSE,
        )
        InterruptionReason.objects.create(
            code='3998', line_category='3', category='9',
            display_name='その他', operation=InterruptionReason.OPERATION_TEMP_END,
        )

        # 1) PAUSE 設備トラブル -> 3101 に一致する行
        self.pause_match = ProcessRealtimeRecord.objects.create(
            process=self.process,
            record_type='OPERATOR_ACTION',
            event_data={'action': 'PAUSE', 'pause_reason': '設備トラブル', 'operator_action_reason': '設備トラブル'},
            interruption_reason_code='',
        )

        # 2) PAUSE 部品ショート（表記ゆれ）-> 正規化後「部品待ち」で 3901 に一致する行
        self.pause_normalized_match = ProcessRealtimeRecord.objects.create(
            process=self.process,
            record_type='OPERATOR_ACTION',
            event_data={'action': 'PAUSE', 'pause_reason': '部品ショート', 'operator_action_reason': '部品ショート'},
            interruption_reason_code='',
        )

        # 3) TEMP_END 他へ製品切り替え -> 3905 に一致する行
        self.temp_end_match = ProcessRealtimeRecord.objects.create(
            process=self.process,
            record_type='OPERATOR_ACTION',
            event_data={'action': 'TEMP_END', 'temp_end_reason': '他へ製品切り替え', 'operator_action_reason': '他へ製品切り替え'},
            interruption_reason_code='',
        )

        # 4) 一致しない行（マスタに存在しない自由記述）
        self.unmatched_record = ProcessRealtimeRecord.objects.create(
            process=self.process,
            record_type='OPERATOR_ACTION',
            event_data={'action': 'TEMP_END', 'temp_end_reason': 'まちがった', 'operator_action_reason': 'まちがった'},
            interruption_reason_code='',
        )

        # 5) operation不一致の確認用: 表示名は「その他」でPAUSE用コードのみ存在する想定を再現するため、
        #    TEMP_END版「その他」(3998) も用意した上で、PAUSE理由の行が3998ではなく3997に一致することを確認する
        self.operation_check_record = ProcessRealtimeRecord.objects.create(
            process=self.process,
            record_type='OPERATOR_ACTION',
            event_data={'action': 'PAUSE', 'pause_reason': 'その他', 'operator_action_reason': 'その他'},
            interruption_reason_code='',
        )

        # 6) 対象外: record_type が違う
        self.other_record_type = ProcessRealtimeRecord.objects.create(
            process=self.process,
            record_type='PRODUCTION',
            event_data={'action': 'END'},
            interruption_reason_code='',
        )

        # 7) 対象外: action が PAUSE/TEMP_END 以外
        self.other_action_record = ProcessRealtimeRecord.objects.create(
            process=self.process,
            record_type='OPERATOR_ACTION',
            event_data={'action': 'START'},
            interruption_reason_code='',
        )

        # 8) 対象外: 既に interruption_reason_code が入っている行
        self.already_coded_record = ProcessRealtimeRecord.objects.create(
            process=self.process,
            record_type='OPERATOR_ACTION',
            event_data={'action': 'PAUSE', 'pause_reason': '設備トラブル', 'operator_action_reason': '設備トラブル'},
            interruption_reason_code='3101',
        )

    def _refresh(self, record):
        record.refresh_from_db()
        return record

    def test_dry_run_does_not_update_db(self):
        stdout = StringIO()
        call_command('backfill_process_realtime_interruption_reason_code', stdout=stdout)

        output = stdout.getvalue()
        self.assertIn('対象件数: 5', output)
        self.assertIn('完全一致候補件数: 4', output)
        self.assertIn('一致しない行: 1', output)
        self.assertIn('ドライラン実行のため、DBは更新していません', output)

        for record in (
            self.pause_match,
            self.pause_normalized_match,
            self.temp_end_match,
            self.unmatched_record,
            self.operation_check_record,
        ):
            self.assertEqual(self._refresh(record).interruption_reason_code, '')

    def test_apply_updates_matched_rows_only(self):
        stdout = StringIO()
        call_command('backfill_process_realtime_interruption_reason_code', '--apply', stdout=stdout)

        self.assertEqual(self._refresh(self.pause_match).interruption_reason_code, '3101')
        self.assertEqual(self._refresh(self.temp_end_match).interruption_reason_code, '3905')
        self.assertEqual(self._refresh(self.operation_check_record).interruption_reason_code, '3997')

        # 一致しない行は更新されず空文字のまま
        self.assertEqual(self._refresh(self.unmatched_record).interruption_reason_code, '')

        # 実更新件数の出力確認
        self.assertIn('実更新件数: 4', stdout.getvalue())

    def test_normalization_dict_maps_part_shortage_to_part_waiting(self):
        """表記ゆれ辞書（部品ショート→部品待ち）が機能し、PAUSE用の部品待ちコードに一致すること"""
        call_command('backfill_process_realtime_interruption_reason_code', '--apply')
        self.assertEqual(self._refresh(self.pause_normalized_match).interruption_reason_code, '3901')

    def test_operation_mismatch_is_not_assigned(self):
        """operationが一致しないコードが誤って割り当てられないこと（TEMP_END行にPAUSE専用コードが入らない）"""
        # PAUSE専用の「部品待ち」(3901) に対し、TEMP_END側に同名の理由を持つ行を用意するが、
        # TEMP_END用「部品待ち」コードはマスタに存在しないため、一致しない行として扱われるべき
        mismatched_record = ProcessRealtimeRecord.objects.create(
            process=self.process,
            record_type='OPERATOR_ACTION',
            event_data={'action': 'TEMP_END', 'temp_end_reason': '部品待ち', 'operator_action_reason': '部品待ち'},
            interruption_reason_code='',
        )

        call_command('backfill_process_realtime_interruption_reason_code', '--apply')

        self.assertEqual(self._refresh(mismatched_record).interruption_reason_code, '')

    def test_other_columns_are_not_touched(self):
        before_event_data = dict(self.pause_match.event_data)
        before_timestamp = self.pause_match.timestamp

        call_command('backfill_process_realtime_interruption_reason_code', '--apply')

        record = self._refresh(self.pause_match)
        self.assertEqual(record.event_data, before_event_data)
        self.assertEqual(record.timestamp, before_timestamp)

    def test_out_of_scope_rows_are_not_affected(self):
        call_command('backfill_process_realtime_interruption_reason_code', '--apply')

        # record_type違い
        self.assertEqual(self._refresh(self.other_record_type).interruption_reason_code, '')
        # action違い（START）
        self.assertEqual(self._refresh(self.other_action_record).interruption_reason_code, '')
        # 既にコードが入っている行は変化しないこと
        self.assertEqual(self._refresh(self.already_coded_record).interruption_reason_code, '3101')
