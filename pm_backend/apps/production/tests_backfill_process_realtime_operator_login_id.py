from datetime import date, datetime
from io import StringIO
import re

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from masters.models import Process
from production.models_process_realtime import ProcessRealtimeRecord
from production.models_process_work_session import ProcessWorkSession


class ProcessRealtimeOperatorLoginIdBackfillTest(TestCase):
    def setUp(self):
        self.process = Process.objects.create(process_code='BF001', process_name='補完テスト工程')

    def _record(self, record_type='PRODUCTION', **kwargs):
        return ProcessRealtimeRecord.objects.create(
            process=self.process,
            record_type=record_type,
            **kwargs,
        )

    def _run(self, *args):
        stdout = StringIO()
        call_command('backfill_process_realtime_operator_login_id', *args, stdout=stdout)
        return stdout.getvalue()

    def _manual_record_for_session(self, session, **kwargs):
        return self._record(
            operator_name='',
            event_data={
                'source': 'MANUAL_RECORD_EDIT',
                'work_session_id': session.pk,
            },
            **kwargs,
        )

    def _reason_counts(self, output):
        line = next(
            line for line in output.splitlines()
            if line.startswith('未補完理由内訳: ')
        )
        return {
            reason: int(count)
            for reason, count in re.findall(r'([^ =]+)=(\d+)', line)
        }

    def test_default_is_dry_run_and_lists_ambiguous_and_unmatched_rows(self):
        get_user_model().objects.create_user(
            username='000175', last_name='一致', first_name='太郎'
        )
        for username in ('000176', '000177'):
            get_user_model().objects.create_user(
                username=username, last_name='同姓', first_name='同名'
            )
        get_user_model().objects.create_user(username='admin')

        exact = self._record(operator_name='一致 太郎')
        ambiguous = self._record(operator_name='同姓 同名')
        collapsed_space = self._record(operator_name='一致太郎')
        partial = self._record(operator_name='一致 太')
        surname_only = self._record(operator_name='一致')
        broken_name = self._record(operator_name='ィスミ')
        admin = self._record('OPERATOR_ACTION', operator_name='admin')
        self._record('EQUIPMENT_STATE', operator_name=None)
        existing = self._record(operator_name='一致 太郎', operator_login_id='existing')
        scrap = self._record('SCRAP', operator_name='一致 太郎')
        purchase = self._record(
            'PURCHASE',
            operator_name='一致 太郎',
            event_data={'source': 'PURCHASE_ACTUAL_INPUT'},
        )

        output = self._run()

        for record in (
            exact, ambiguous, collapsed_space, partial, surname_only, broken_name, admin,
        ):
            record.refresh_from_db()
            self.assertIsNone(record.operator_login_id)
        existing.refresh_from_db()
        self.assertEqual(existing.operator_login_id, 'existing')
        scrap.refresh_from_db()
        purchase.refresh_from_db()
        self.assertIsNone(scrap.operator_login_id)
        self.assertIsNone(purchase.operator_login_id)
        self.assertEqual(scrap.operator_name, '一致 太郎')
        self.assertEqual(purchase.event_data, {'source': 'PURCHASE_ACTUAL_INPUT'})
        self.assertIn('実行モード=照合のみ', output)
        self.assertIn('対象件数=8 候補件数=2 未補完件数=6 更新件数=0', output)
        self.assertIn('姓名完全一致=1 username表示名一致=1', output)
        self.assertIn(
            '補完後実NULL件数=8 '
            '補完後実種別内訳=PRODUCTION:6,OPERATOR_ACTION:1,EQUIPMENT_STATE:1',
            output,
        )
        self.assertIn(
            '適用時見込NULL件数=6 '
            '適用時見込種別内訳=PRODUCTION:5,OPERATOR_ACTION:0,EQUIPMENT_STATE:1',
            output,
        )
        self.assertIn(f'未補完: id={ambiguous.pk}', output)
        self.assertIn('理由=姓名一致が曖昧 一致件数=2', output)
        self.assertIn(f'未補完: id={collapsed_space.pk}', output)
        self.assertIn('理由=名前不一致 一致件数=0', output)
        for record in (partial, surname_only, broken_name):
            self.assertIn(f'未補完: id={record.pk}', output)
        reason_counts = self._reason_counts(output)
        self.assertEqual(sum(reason_counts.values()), 6)
        self.assertEqual(reason_counts['姓名一致が曖昧'], 1)
        self.assertEqual(reason_counts['名前不一致'], 4)
        self.assertEqual(reason_counts['作業者名空・セッション根拠なし'], 1)

    def test_apply_updates_only_exact_candidates_and_is_idempotent(self):
        get_user_model().objects.create_user(
            username='000175', last_name='一致', first_name='太郎'
        )
        get_user_model().objects.create_user(username='admin')
        get_user_model().objects.create_user(
            username='100960', last_name='イズミ', first_name='ケンジ', is_active=False
        )
        start_record = self._record('OPERATOR_ACTION', operator_login_id='100960')
        end_record = self._record('OPERATOR_ACTION', operator_login_id='100960')
        session = ProcessWorkSession.objects.create(
            process=self.process,
            product_code='',
            product_name='',
            plan_date=date(2026, 10, 1),
            started_at=datetime(2026, 10, 1, 8, 0),
            ended_at=datetime(2026, 10, 1, 9, 0),
            status='CLOSED',
            start_record=start_record,
            end_record=end_record,
        )

        manual = self._manual_record_for_session(session)
        exact = self._record(operator_name='一致 太郎')
        admin = self._record('OPERATOR_ACTION', operator_name='admin')
        unmatched = self._record('EQUIPMENT_STATE', operator_name='退職者')
        manual_event_data_before = dict(manual.event_data)
        session_before = {
            'operator_name': session.operator_name,
            'operator_login_id': session.operator_login_id,
            'start_record_id': session.start_record_id,
            'end_record_id': session.end_record_id,
            'status': session.status,
            'production_qty': session.production_qty,
        }

        output = self._run('--apply')

        for record, expected in (
            (manual, '100960'),
            (exact, '000175'),
            (admin, 'admin'),
        ):
            record.refresh_from_db()
            self.assertEqual(record.operator_login_id, expected)
        unmatched.refresh_from_db()
        self.assertIsNone(unmatched.operator_login_id)
        session.refresh_from_db()
        self.assertEqual(
            {
                'operator_name': session.operator_name,
                'operator_login_id': session.operator_login_id,
                'start_record_id': session.start_record_id,
                'end_record_id': session.end_record_id,
                'status': session.status,
                'production_qty': session.production_qty,
            },
            session_before,
        )
        manual.refresh_from_db()
        self.assertEqual(manual.operator_name, '')
        self.assertEqual(manual.event_data, manual_event_data_before)
        start_record.refresh_from_db()
        end_record.refresh_from_db()
        self.assertEqual(start_record.operator_login_id, '100960')
        self.assertEqual(end_record.operator_login_id, '100960')
        self.assertEqual(start_record.event_data, None)
        self.assertEqual(end_record.event_data, None)
        self.assertIn('対象件数=4 候補件数=3 未補完件数=1 更新件数=3', output)
        self.assertIn(
            '補完後実NULL件数=1 '
            '補完後実種別内訳=PRODUCTION:0,OPERATOR_ACTION:0,EQUIPMENT_STATE:1',
            output,
        )
        self.assertIn(
            '適用時見込NULL件数=1 '
            '適用時見込種別内訳=PRODUCTION:0,OPERATOR_ACTION:0,EQUIPMENT_STATE:1',
            output,
        )
        self.assertIn('セッション一致=1 姓名完全一致=1 username表示名一致=1', output)
        self.assertIn(
            '対象件数=1 候補件数=0 未補完件数=1 更新件数=0',
            self._run('--apply'),
        )

    def test_session_evidence_must_be_complete_equal_and_have_a_user(self):
        get_user_model().objects.create_user(username='worker-a')
        get_user_model().objects.create_user(username='worker-b')
        start_record = self._record('OPERATOR_ACTION', operator_login_id='worker-a')
        end_record = self._record('OPERATOR_ACTION', operator_login_id='worker-b')
        session = ProcessWorkSession.objects.create(
            process=self.process,
            product_code='',
            product_name='',
            plan_date=date(2026, 10, 1),
            started_at=datetime(2026, 10, 1, 8, 0),
            ended_at=datetime(2026, 10, 1, 9, 0),
            status='CLOSED',
            start_record=start_record,
            end_record=end_record,
        )
        mismatch = self._manual_record_for_session(session)
        missing_session = self._record(
            operator_name='',
            event_data={
                'source': 'MANUAL_RECORD_EDIT',
                'work_session_id': 999999,
            },
        )
        missing_login_end = self._record('OPERATOR_ACTION', operator_login_id=None)
        missing_login_session = ProcessWorkSession.objects.create(
            process=self.process,
            product_code='',
            product_name='',
            plan_date=date(2026, 10, 1),
            started_at=datetime(2026, 10, 1, 10, 0),
            ended_at=datetime(2026, 10, 1, 11, 0),
            status='CLOSED',
            start_record=start_record,
            end_record=missing_login_end,
        )
        missing_login = self._manual_record_for_session(missing_login_session)
        ghost_start = self._record('OPERATOR_ACTION', operator_login_id='deleted-user')
        ghost_end = self._record('OPERATOR_ACTION', operator_login_id='deleted-user')
        ghost_session = ProcessWorkSession.objects.create(
            process=self.process,
            product_code='',
            product_name='',
            plan_date=date(2026, 10, 1),
            started_at=datetime(2026, 10, 1, 12, 0),
            ended_at=datetime(2026, 10, 1, 13, 0),
            status='CLOSED',
            start_record=ghost_start,
            end_record=ghost_end,
        )
        missing_user = self._manual_record_for_session(ghost_session)
        no_records_session = ProcessWorkSession.objects.create(
            process=self.process,
            product_code='',
            product_name='',
            plan_date=date(2026, 10, 1),
            started_at=datetime(2026, 10, 1, 14, 0),
            ended_at=datetime(2026, 10, 1, 15, 0),
            status='CLOSED',
        )
        missing_records = self._manual_record_for_session(no_records_session)

        output = self._run('--apply')

        for record in (
            mismatch, missing_session, missing_login, missing_user, missing_records,
        ):
            record.refresh_from_db()
            self.assertIsNone(record.operator_login_id)
        self.assertIn('理由=開始・終了ログインID不一致', output)
        self.assertIn('理由=セッションなし', output)
        self.assertIn('理由=開始・終了ログインID不足', output)
        self.assertIn('理由=一致ユーザーなし', output)
        self.assertIn('理由=開始・終了記録不足', output)
        self.assertIn('候補件数=0 未補完件数=6 更新件数=0', output)
