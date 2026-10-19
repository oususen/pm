from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from masters.models import Equipment, InterruptionReason, Line, Process, Product
from production.models_laser_actual import LASER_LINE_CODE, LASER_PROCESS_CODE, LaserActual
from production.models_laser_pattern import LaserPattern


class BackfillLaserActualInterruptionReasonCodeCommandTest(TestCase):
    def setUp(self):
        self.laser_line, _ = Line.objects.get_or_create(
            line_code=LASER_LINE_CODE, defaults={'line_name': 'レーザ'},
        )
        self.laser_process, _ = Process.objects.get_or_create(
            process_code=LASER_PROCESS_CODE,
            defaults={'process_name': 'レーザ加工', 'line': self.laser_line},
        )
        self.equipment = Equipment.objects.create(
            equipment_code='EQ-LASER-T',
            equipment_name='レーザ設備試験',
            line=self.laser_line,
            process=self.laser_process,
        )
        self.material = Product.objects.create(
            product_code='MAT-LASER-T',
            product_name='レーザ材料試験',
        )
        self.pattern = LaserPattern.objects.create(
            pattern_no='PT-LASER-T',
            material=self.material,
            equipment=self.equipment,
            process_time_min=1,
        )

        # レーザー用のマスタ（line_category='1'）
        InterruptionReason.objects.create(
            code='1904', line_category='1', category='9',
            display_name='材料待ち', operation=InterruptionReason.OPERATION_PAUSE,
        )
        InterruptionReason.objects.create(
            code='1997', line_category='1', category='9',
            display_name='その他', operation=InterruptionReason.OPERATION_TEMP_END,
        )
        # line_category が違う（一般工程）マスタ。表示名が同じでも誤ってマッチしないことを確認するため同名で用意
        InterruptionReason.objects.create(
            code='3904', line_category='3', category='9',
            display_name='材料待ち', operation=InterruptionReason.OPERATION_PAUSE,
        )

        # 1) PAUSE 材料待ち -> 1904 に一致する行
        self.pause_match = LaserActual.objects.create(
            work_date=date(2026, 3, 14),
            equipment=self.equipment,
            pattern=self.pattern,
            shot_count=1,
            pattern_no='PT-LASER-T',
            operator_action=LaserActual.OPERATOR_ACTION_PAUSE,
            operator_action_reason='材料待ち',
            interruption_reason_code='',
        )

        # 2) TEMP_END その他 -> 1997 に一致する行
        self.temp_end_match = LaserActual.objects.create(
            work_date=date(2026, 3, 14),
            equipment=self.equipment,
            pattern=self.pattern,
            shot_count=1,
            pattern_no='PT-LASER-T',
            operator_action=LaserActual.OPERATOR_ACTION_TEMP_END,
            operator_action_reason='その他',
            interruption_reason_code='',
        )

        # 3) 一致しない行（マスタに存在しない自由記述）
        self.unmatched_record = LaserActual.objects.create(
            work_date=date(2026, 3, 14),
            equipment=self.equipment,
            pattern=self.pattern,
            shot_count=1,
            pattern_no='PT-LASER-T',
            operator_action=LaserActual.OPERATOR_ACTION_PAUSE,
            operator_action_reason='未登録の理由',
            interruption_reason_code='',
        )

        # 4) 対象外: operator_action が START/END/RESUME
        self.start_record = LaserActual.objects.create(
            work_date=date(2026, 3, 14),
            equipment=self.equipment,
            pattern=self.pattern,
            shot_count=1,
            pattern_no='PT-LASER-T',
            operator_action=LaserActual.OPERATOR_ACTION_START,
            operator_action_reason='',
            interruption_reason_code='',
        )
        self.end_record = LaserActual.objects.create(
            work_date=date(2026, 3, 14),
            equipment=self.equipment,
            pattern=self.pattern,
            shot_count=1,
            pattern_no='PT-LASER-T',
            operator_action=LaserActual.OPERATOR_ACTION_END,
            operator_action_reason='',
            interruption_reason_code='',
        )
        self.resume_record = LaserActual.objects.create(
            work_date=date(2026, 3, 14),
            equipment=self.equipment,
            pattern=self.pattern,
            shot_count=1,
            pattern_no='PT-LASER-T',
            operator_action=LaserActual.OPERATOR_ACTION_RESUME,
            operator_action_reason='',
            interruption_reason_code='',
        )

        # 5) 対象外: interruption_reason_code が既に非空
        self.already_coded_record = LaserActual.objects.create(
            work_date=date(2026, 3, 14),
            equipment=self.equipment,
            pattern=self.pattern,
            shot_count=1,
            pattern_no='PT-LASER-T',
            operator_action=LaserActual.OPERATOR_ACTION_PAUSE,
            operator_action_reason='材料待ち',
            interruption_reason_code='1904',
        )

    def _refresh(self, record):
        record.refresh_from_db()
        return record

    def test_dry_run_does_not_update_db(self):
        stdout = StringIO()
        call_command('backfill_laser_actual_interruption_reason_code', stdout=stdout)

        output = stdout.getvalue()
        self.assertIn('対象件数: 3', output)
        self.assertIn('完全一致候補件数: 2', output)
        self.assertIn('一致しない行: 1', output)
        self.assertIn('ドライラン実行のため、DBは更新していません', output)

        for record in (self.pause_match, self.temp_end_match, self.unmatched_record):
            self.assertEqual(self._refresh(record).interruption_reason_code, '')

    def test_apply_updates_matched_rows_only(self):
        stdout = StringIO()
        call_command('backfill_laser_actual_interruption_reason_code', '--apply', stdout=stdout)

        self.assertEqual(self._refresh(self.pause_match).interruption_reason_code, '1904')
        self.assertEqual(self._refresh(self.temp_end_match).interruption_reason_code, '1997')

        # 一致しない行は更新されず空文字のまま
        self.assertEqual(self._refresh(self.unmatched_record).interruption_reason_code, '')

        self.assertIn('実更新件数: 2', stdout.getvalue())

    def test_other_columns_are_not_touched(self):
        before_reason = self.pause_match.operator_action_reason
        before_work_date = self.pause_match.work_date
        before_shot_count = self.pause_match.shot_count

        call_command('backfill_laser_actual_interruption_reason_code', '--apply')

        record = self._refresh(self.pause_match)
        self.assertEqual(record.operator_action_reason, before_reason)
        self.assertEqual(record.work_date, before_work_date)
        self.assertEqual(record.shot_count, before_shot_count)

    def test_already_coded_rows_are_not_affected(self):
        call_command('backfill_laser_actual_interruption_reason_code', '--apply')

        # 既にコードが入っている行は対象外のまま変化しないこと
        self.assertEqual(self._refresh(self.already_coded_record).interruption_reason_code, '1904')

    def test_non_interruption_actions_are_not_affected(self):
        call_command('backfill_laser_actual_interruption_reason_code', '--apply')

        self.assertEqual(self._refresh(self.start_record).interruption_reason_code, '')
        self.assertEqual(self._refresh(self.end_record).interruption_reason_code, '')
        self.assertEqual(self._refresh(self.resume_record).interruption_reason_code, '')

    def test_different_line_category_master_does_not_match(self):
        """line_categoryが違う（一般工程）のInterruptionReasonは、表示名が同じでも誤ってマッチしないこと"""
        call_command('backfill_laser_actual_interruption_reason_code', '--apply')

        # 1904(レーザー用「材料待ち」)に一致し、3904(一般工程用「材料待ち」)が誤って使われないこと
        self.assertEqual(self._refresh(self.pause_match).interruption_reason_code, '1904')
