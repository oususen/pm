"""ローカルQwenの本人残業照会を検証する。"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from ai.services.chat_service import _quick_my_overtime_response
from overtime.models import OvertimeApplication


class QwenMyOvertimeTest(TestCase):
    def setUp(self):
        patcher = patch('ai.services.chat_service.AI_DB_ALIAS', 'default')
        patcher.start()
        self.addCleanup(patcher.stop)
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='my-overtime', password='testpass')
        self.other_user = user_model.objects.create_user(username='other-overtime', password='testpass')
        self._application(self.user, '2026-09-03', 'overtime', 'submitted', '2.0')
        self._application(self.user, '2026-09-10', 'holiday', 'approved_manager', '1.0')
        self._application(self.user, '2026-09-15', 'overtime', 'draft', '9.0')
        self._application(self.other_user, '2026-09-18', 'overtime', 'submitted', '6.0')

    @staticmethod
    def _application(user, work_date, application_type, status, hours):
        OvertimeApplication.objects.create(
            applicant=user,
            created_by=user,
            work_date=work_date,
            application_type=application_type,
            status=status,
            hours=Decimal(hours),
        )

    def test_returns_only_logged_in_users_submitted_overtime(self):
        result = _quick_my_overtime_response('私の2026年9月の残業を教えて', self.user)

        self.assertEqual(result['facts']['total_hours'], 3.0)
        self.assertEqual(result['facts']['total_records'], 2)
        self.assertEqual(result['chart_title'], 'あなたの残業申請時間')
        self.assertNotIn('other-overtime', result['answer'])

    def test_ignores_questions_not_asking_for_the_logged_in_user(self):
        self.assertIsNone(_quick_my_overtime_response('2026年9月の残業を教えて', self.user))

    def test_ignores_group_and_other_people_questions(self):
        for question in ('私の班の9月の残業', '私達の9月の残業', '残業で私が困る', 'ズイさんの残業'):
            with self.subTest(question=question):
                self.assertIsNone(_quick_my_overtime_response(question, self.user))

    def test_accepts_natural_self_questions(self):
        for question in ('わたしの残業を報告して 9月の', '自分の2026年9月の残業', '私の9月の残業'):
            with self.subTest(question=question):
                result = _quick_my_overtime_response(question, self.user)
                self.assertEqual(result['facts']['total_hours'], 3.0)
