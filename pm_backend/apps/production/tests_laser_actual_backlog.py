from datetime import date
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory

from masters.models import Equipment, InterruptionReason, Line, Process, Product, Routing, RoutingStep
from production.models_laser_actual import LASER_LINE_CODE, LASER_PROCESS_CODE, LaserActual
from production.models_process_work_session_change_history import ProcessWorkSessionChangeHistory
from production.models_laser_pattern import (
    LaserPattern,
    LaserPatternComponent,
    LaserPatternFinishedProduct,
)
from production.models_line_backlog import LineBacklog
from production.serializers import LaserActualSerializer
from production.views_laser import LaserActualDetailUpdateView, LaserActualViewSet


class LaserActualBacklogSyncTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.line = Line.objects.create(
            line_code='L-LASER-T',
            line_name='レーザ試験ライン',
        )
        self.process = Process.objects.create(
            process_code='P-LASER-T',
            process_name='レーザ試験工程',
            line=self.line,
        )
        self.nut_line = Line.objects.create(
            line_code='L-NUT-T',
            line_name='ナット試験ライン',
        )
        self.nut_process = Process.objects.create(
            process_code='4013',
            process_name='ナット',
            line=self.nut_line,
        )
        # 設備はレーザー実績を登録できる L0801 / 0801 に紐づける。
        # LineBacklog の反映先はルーティング由来(L-LASER-T)のままで、設備や新列とは独立。
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
        self.component = Product.objects.create(
            product_code='CMP-LASER-T',
            product_name='レーザ構成部品試験',
        )
        self.finished = Product.objects.create(
            product_code='FIN-LASER-T',
            product_name='レーザ完成品試験',
        )

        self.pattern = LaserPattern.objects.create(
            pattern_no='PT-LASER-T',
            material=self.material,
            equipment=self.equipment,
            process_time_min=1,
        )
        LaserPatternComponent.objects.create(
            pattern=self.pattern,
            component_product=self.component,
            take_qty=3,
        )
        LaserPatternFinishedProduct.objects.create(
            pattern=self.pattern,
            finished_product=self.finished,
            units_per_shot=1,
        )
        self.routing = Routing.objects.create(
            product=self.component,
            routing_code='ROUTE-LASER-T',
            is_default=True,
            is_active=True,
        )
        RoutingStep.objects.create(
            routing=self.routing,
            step_no=10,
            process=self.process,
            line=self.line,
            output_product=self.component,
        )
        # 中断理由マスタ(line_category='1'=レーザー)。
        # マスタ用データ移行での初期投入とは独立して、テストが必要とする行を明示的に用意する
        InterruptionReason.objects.get_or_create(
            code='1101',
            defaults={
                'line_category': '1', 'category': '1', 'display_name': '設備トラブル',
                'operation': 'PAUSE', 'is_active': True,
            },
        )
        InterruptionReason.objects.get_or_create(
            code='1102',
            defaults={
                'line_category': '1', 'category': '1', 'display_name': '本日設備復旧不可',
                'operation': 'TEMP_END', 'is_active': True,
            },
        )

    def _create_actual(self, shot_count=2, action='END', component_scraps=None):
        action_upper = str(action or '').upper()
        reason = '設備トラブル' if action_upper in {'PAUSE', 'TEMP_END'} else ''
        reason_code = {'PAUSE': '1101', 'TEMP_END': '1102'}.get(action_upper, '')
        serializer = LaserActualSerializer(data={
            'work_date': date(2026, 3, 14),
            'equipment': self.equipment.id,
            'pattern': self.pattern.id,
            'shot_count': shot_count,
            'operator_action': action_upper,
            'operator_action_reason': reason,
            'interruption_reason_code': reason_code,
            'component_scraps': component_scraps or [],
            'remarks': '',
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        return serializer.save()

    def _get_backlog(self):
        return LineBacklog.objects.get(
            plan_date=date(2026, 3, 14),
            line=self.line,
            process=self.process,
            product=self.component,
            sequence_no=0,
        )

    def test_create_reflects_component_qty_to_backlog(self):
        self._create_actual(shot_count=2, action='END')
        backlog = self._get_backlog()
        self.assertEqual(backlog.actual_qty, 6)
        self.assertFalse(LineBacklog.objects.filter(
            plan_date=date(2026, 3, 14),
            line=self.nut_line,
            process=self.nut_process,
            product=self.component,
            sequence_no=0,
        ).exists())
        # 設備のライン/工程(L0801/0801)にも LineBacklog は作られない(ルーティング由来のみ)
        self.assertFalse(LineBacklog.objects.filter(
            plan_date=date(2026, 3, 14),
            line=self.laser_line,
            process=self.laser_process,
            product=self.component,
        ).exists())

    def test_update_replaces_backlog_qty_with_delta(self):
        actual = self._create_actual(shot_count=2, action='END')
        serializer = LaserActualSerializer(
            actual,
            data={
                'work_date': date(2026, 3, 14),
                'equipment': self.equipment.id,
                'pattern': self.pattern.id,
                'shot_count': 5,
                'operator_action': 'PAUSE',
                'operator_action_reason': '設備トラブル',
                'interruption_reason_code': '1101',
                'remarks': '',
            },
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        backlog = self._get_backlog()
        self.assertEqual(backlog.actual_qty, 15)

    def test_scrap_is_subtracted_from_component_actual_qty(self):
        self._create_actual(
            shot_count=3,
            action='END',
            component_scraps=[{
                'product': self.component.id,
                'scrap_qty': 2,
                'scrap_reason': 'キズ',
            }],
        )
        backlog = self._get_backlog()
        self.assertEqual(backlog.actual_qty, 7)

    def test_destroy_rolls_back_backlog_qty(self):
        actual = self._create_actual(shot_count=4, action='PAUSE')
        backlog = self._get_backlog()
        self.assertEqual(backlog.actual_qty, 12)

        view = LaserActualViewSet.as_view({'delete': 'destroy'})
        request = self.factory.delete(
            f'/api/laser-actuals/{actual.id}/',
            {'change_reason': 'レーザー実績削除'},
            format='json',
        )
        response = view(request, pk=actual.id)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        backlog.refresh_from_db()
        self.assertEqual(backlog.actual_qty, 0)
        self.assertFalse(LaserActual.objects.filter(id=actual.id).exists())
        self.assertTrue(ProcessWorkSessionChangeHistory.objects.filter(
            session_record_id=actual.id,
            operation_type='DELETE',
            product_code=self.component.product_code,
            reason='レーザー実績削除',
        ).exists())

    def test_detail_update_creates_history(self):
        actual = self._create_actual(shot_count=2, action='END')
        detail = actual.details.filter(
            detail_type='COMPONENT',
            product=self.component,
        ).first()
        self.assertIsNotNone(detail)

        view = LaserActualDetailUpdateView.as_view()
        request = self.factory.patch(
            f'/api/laser-actual-details/{detail.id}/',
            {'total_qty': 8, 'change_reason': 'レーザー数量訂正'},
            format='json',
        )
        response = view(request, detail_id=detail.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        history = ProcessWorkSessionChangeHistory.objects.get(
            session_record_id=actual.id,
            operation_type='UPDATE',
            product_code=self.component.product_code,
        )
        self.assertEqual(history.reason, 'レーザー数量訂正')
        self.assertEqual(history.before_data['production_qty'], 6.0)
        self.assertEqual(history.after_data['production_qty'], 8.0)

    # ---- line / process の保存時決定と設備検証 ----

    def _payload(self, **extra):
        data = {
            'work_date': date(2026, 3, 14),
            'equipment': self.equipment.id,
            'pattern': self.pattern.id,
            'shot_count': 2,
            'operator_action': 'END',
            'operator_action_reason': '',
            'component_scraps': [],
            'remarks': '',
        }
        data.update(extra)
        return data

    def _assert_rejected(self, serializer):
        self.assertFalse(serializer.is_valid())
        self.assertIn('equipment', serializer.errors)
        self.assertIn('L0801', str(serializer.errors['equipment']))

    def test_create_sets_line_and_process(self):
        actual = self._create_actual()
        self.assertEqual(actual.line_id, self.laser_line.id)
        self.assertEqual(actual.process_id, self.laser_process.id)

    def test_rejects_equipment_with_other_line(self):
        self.equipment.line = self.nut_line
        self.equipment.save()
        self._assert_rejected(LaserActualSerializer(data=self._payload()))
        self.assertEqual(LaserActual.objects.count(), 0)
        self.assertEqual(LineBacklog.objects.count(), 0)

    def test_rejects_equipment_with_null_line(self):
        self.equipment.line = None
        self.equipment.save()
        self._assert_rejected(LaserActualSerializer(data=self._payload()))
        self.assertEqual(LaserActual.objects.count(), 0)

    def test_rejects_equipment_with_other_or_null_process(self):
        self.equipment.process = self.nut_process
        self.equipment.save()
        self._assert_rejected(LaserActualSerializer(data=self._payload()))
        self.equipment.process = None
        self.equipment.save()
        self._assert_rejected(LaserActualSerializer(data=self._payload()))
        self.assertEqual(LaserActual.objects.count(), 0)
        self.assertEqual(LineBacklog.objects.count(), 0)

    def test_client_line_process_are_ignored(self):
        serializer = LaserActualSerializer(data=self._payload(
            line=self.nut_line.id, process=self.nut_process.id,
        ))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        actual = serializer.save()
        self.assertEqual(actual.line_id, self.laser_line.id)
        self.assertEqual(actual.process_id, self.laser_process.id)

    def test_update_rejects_equipment_outside_laser_line(self):
        actual = self._create_actual()
        other = Equipment.objects.create(
            equipment_code='EQ-NUT-T', equipment_name='ナット設備',
            line=self.nut_line, process=self.nut_process,
        )
        self._assert_rejected(LaserActualSerializer(actual, data=self._payload(equipment=other.id)))
        actual.refresh_from_db()
        self.assertEqual(actual.equipment_id, self.equipment.id)

    def test_update_keeps_line_process(self):
        actual = self._create_actual()
        serializer = LaserActualSerializer(actual, data=self._payload(shot_count=3))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        actual = serializer.save()
        self.assertEqual(actual.line_id, self.laser_line.id)
        self.assertEqual(actual.process_id, self.laser_process.id)

    def test_missing_master_row_gives_explicit_error(self):
        # コードで引けない状態にする(L0801 のラインマスタが無い)
        self.laser_line.line_code = 'L0801-X'
        self.laser_line.save()
        serializer = LaserActualSerializer(data=self._payload())
        self.assertFalse(serializer.is_valid())
        self.assertIn('マスタ', str(serializer.errors['equipment']))

    def test_saved_values_do_not_follow_equipment_master_change(self):
        actual = self._create_actual()
        self.equipment.line = self.nut_line
        self.equipment.process = self.nut_process
        self.equipment.save()
        actual.refresh_from_db()
        self.assertEqual(actual.line_id, self.laser_line.id)
        self.assertEqual(actual.process_id, self.laser_process.id)

    # ---- 補完コマンド backfill_laser_actual_line_process ----

    def _make_null_actual(self, equipment):
        return LaserActual.objects.create(
            work_date=date(2026, 3, 14), equipment=equipment, pattern=self.pattern,
            shot_count=1, pattern_no='PT-LASER-T',
        )

    def _run_backfill(self, *args):
        out = StringIO()
        call_command('backfill_laser_actual_line_process', *args, stdout=out)
        return out.getvalue()

    def test_backfill_default_does_not_update(self):
        self._make_null_actual(self.equipment)
        output = self._run_backfill()
        self.assertEqual(LaserActual.objects.filter(line_id__isnull=True).count(), 1)
        self.assertIn('対象件数=1 候補件数=1 不一致件数=0 更新件数=0 未補完件数=1', output)

    def test_backfill_apply_updates_and_second_run_is_noop(self):
        actual = self._make_null_actual(self.equipment)
        output = self._run_backfill('--apply')
        self.assertIn('更新件数=1 未補完件数=0', output)
        actual.refresh_from_db()
        self.assertEqual(actual.line_id, self.laser_line.id)
        self.assertEqual(actual.process_id, self.laser_process.id)
        self.assertIn(
            '対象件数=0 候補件数=0 不一致件数=0 更新件数=0 未補完件数=0',
            self._run_backfill('--apply'),
        )

    def test_backfill_mismatched_equipment_is_listed_and_not_updated(self):
        other = Equipment.objects.create(
            equipment_code='EQ-NUT-T', equipment_name='ナット設備',
            line=self.nut_line, process=self.nut_process,
        )
        actual = self._make_null_actual(other)
        output = self._run_backfill('--apply')
        self.assertIn(f'不一致: id={actual.pk}', output)
        self.assertIn('対象件数=1 候補件数=0 不一致件数=1 更新件数=0 未補完件数=1', output)
        actual.refresh_from_db()
        self.assertIsNone(actual.line_id)

    def test_backfill_value_is_looked_up_by_code(self):
        actual = self._make_null_actual(self.equipment)
        self._run_backfill('--apply')
        actual.refresh_from_db()
        self.assertEqual(actual.line.line_code, LASER_LINE_CODE)
        self.assertEqual(actual.process.process_code, LASER_PROCESS_CODE)

    def test_backfill_missing_master_row_is_error(self):
        self.laser_line.line_code = 'L0801-X'
        self.laser_line.save()
        with self.assertRaises(CommandError):
            self._run_backfill()

    # ---- 中断理由コード(interruption_reason_code)の検証(単位C-7) ----

    def test_pause_without_reason_code_is_rejected(self):
        serializer = LaserActualSerializer(data=self._payload(
            operator_action='PAUSE', operator_action_reason='設備トラブル', interruption_reason_code='',
        ))
        self.assertFalse(serializer.is_valid())
        self.assertIn('interruption_reason_code', serializer.errors)
        self.assertEqual(LaserActual.objects.count(), 0)

    def test_pause_with_invalid_reason_code_is_rejected(self):
        serializer = LaserActualSerializer(data=self._payload(
            operator_action='PAUSE', operator_action_reason='設備トラブル', interruption_reason_code='9999',
        ))
        self.assertFalse(serializer.is_valid())
        self.assertIn('interruption_reason_code', serializer.errors)
        self.assertEqual(LaserActual.objects.count(), 0)

    def test_pause_with_wrong_line_category_reason_code_is_rejected(self):
        # '2101' はブレーキ・板金スポット(line_category='2')用のコード
        InterruptionReason.objects.create(
            code='2101', line_category='2', category='1', display_name='設備トラブル',
            operation='PAUSE', is_active=True,
        )
        serializer = LaserActualSerializer(data=self._payload(
            operator_action='PAUSE', operator_action_reason='設備トラブル', interruption_reason_code='2101',
        ))
        self.assertFalse(serializer.is_valid())
        self.assertIn('interruption_reason_code', serializer.errors)
        self.assertEqual(LaserActual.objects.count(), 0)

    def test_pause_with_temp_end_only_reason_code_is_rejected(self):
        # '1102' は TEMP_END専用コード(PAUSEでは使えない)
        serializer = LaserActualSerializer(data=self._payload(
            operator_action='PAUSE', operator_action_reason='本日設備復旧不可', interruption_reason_code='1102',
        ))
        self.assertFalse(serializer.is_valid())
        self.assertIn('interruption_reason_code', serializer.errors)
        self.assertEqual(LaserActual.objects.count(), 0)

    def test_pause_with_inactive_reason_code_is_rejected(self):
        InterruptionReason.objects.filter(code='1101').update(is_active=False)
        serializer = LaserActualSerializer(data=self._payload(
            operator_action='PAUSE', operator_action_reason='設備トラブル', interruption_reason_code='1101',
        ))
        self.assertFalse(serializer.is_valid())
        self.assertIn('interruption_reason_code', serializer.errors)
        self.assertEqual(LaserActual.objects.count(), 0)

    def test_temp_end_with_valid_reason_code_is_accepted_and_saved(self):
        serializer = LaserActualSerializer(data=self._payload(
            operator_action='TEMP_END', operator_action_reason='本日設備復旧不可', interruption_reason_code='1102',
        ))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        actual = serializer.save()
        actual.refresh_from_db()
        self.assertEqual(actual.interruption_reason_code, '1102')

    def test_start_end_resume_skip_reason_code_validation(self):
        # START/END/RESUMEでは理由コード未送信でも検証をスキップする
        actual = self._create_actual(shot_count=2, action='END')
        self.assertEqual(actual.interruption_reason_code, '')

        serializer = LaserActualSerializer(actual, data=self._payload(
            operator_action='END', operator_action_reason='', interruption_reason_code='',
        ))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        actual = serializer.save()
        self.assertEqual(actual.interruption_reason_code, '')

    def test_non_pause_action_clears_reason_code(self):
        # PAUSE/TEMP_END以外でコードが送られてきてもクリアされる(保存されない)
        serializer = LaserActualSerializer(data=self._payload(
            operator_action='END', operator_action_reason='', interruption_reason_code='1101',
        ))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        actual = serializer.save()
        self.assertEqual(actual.interruption_reason_code, '')

    def test_operator_action_reason_required_check_unchanged(self):
        # 既存の operator_action_reason 必須チェックが変更されていないことの確認
        serializer = LaserActualSerializer(data=self._payload(
            operator_action='PAUSE', operator_action_reason='', interruption_reason_code='1101',
        ))
        self.assertFalse(serializer.is_valid())
        self.assertIn('operator_action_reason', serializer.errors)
        self.assertEqual(LaserActual.objects.count(), 0)
