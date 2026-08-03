from django.contrib.auth import get_user_model
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from accounts.models import Department, UserProfile
from masters.models import BreakTime, WorkPattern
from overtime.models import OvertimeApplication
from overtime.views import OvertimeApplicationViewSet


User = get_user_model()


class OvertimeApplicationViewSetTests(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.team = Department.objects.create(name='組立1班', level='team', display_id=1)
        self.unit_main = Department.objects.create(name='Aグループ', level='unit', display_id=2, parent=self.team)
        self.unit_sub = Department.objects.create(name='Bグループ', level='unit', display_id=3, parent=self.team)

        self.leader = User.objects.create_user(
            username='leader_multi_unit',
            password='testpass123',
            first_name='太郎',
            last_name='山田',
        )
        self.leader_profile = UserProfile.objects.create(
            user=self.leader,
            role='leader',
            team=self.team,
            unit=None,
        )
        self.leader_profile.leader_units.set([self.unit_main, self.unit_sub])

    def test_submit_allows_leader_own_application_even_without_primary_unit(self):
        application = OvertimeApplication.objects.create(
            applicant=self.leader,
            created_by=self.leader,
            work_date='2026-07-10',
            application_type='overtime',
            work_start_time='08:00',
            scheduled_end_time='17:05',
            start_time='17:15',
            end_time='19:00',
            reason='テスト申請',
            team=self.team,
            status='draft',
        )

        view = OvertimeApplicationViewSet.as_view({'post': 'submit'})
        request = self.factory.post(f'/api/overtime/applications/{application.id}/submit/')
        force_authenticate(request, user=self.leader)

        response = view(request, pk=application.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertNotEqual(application.status, 'draft')

    def test_holiday_without_work_pattern_keeps_first_example_at_8_hours(self):
        application = OvertimeApplication.objects.create(
            applicant=self.leader,
            created_by=self.leader,
            work_date='2026-07-11',
            application_type='holiday',
            start_time='19:15',
            end_time='04:30',
            reason='休日出勤テスト',
            team=self.team,
            status='draft',
        )

        self.assertEqual(application.hours, Decimal('2.0'))
        self.assertEqual(application.midnight_hours, Decimal('6.0'))
        self.assertEqual(application.hours + application.midnight_hours, Decimal('8.0'))

    def test_holiday_half_day_without_work_pattern_does_not_subtract_lunch_break(self):
        application = OvertimeApplication.objects.create(
            applicant=self.leader,
            created_by=self.leader,
            work_date='2026-07-11',
            application_type='holiday',
            holiday_work_type='half_day',
            start_time='21:25',
            end_time='02:20',
            reason='休日出勤テスト',
            team=self.team,
            status='draft',
        )

        self.assertEqual(application.hours, Decimal('0.5'))
        self.assertEqual(application.midnight_hours, Decimal('4.0'))
        self.assertEqual(application.hours + application.midnight_hours, Decimal('4.5'))

    def test_holiday_full_day_without_work_pattern_subtracts_lunch_break(self):
        application = OvertimeApplication.objects.create(
            applicant=self.leader,
            created_by=self.leader,
            work_date='2026-07-11',
            application_type='holiday',
            holiday_work_type='full_day',
            start_time='21:25',
            end_time='02:20',
            reason='休日出勤テスト',
            team=self.team,
            status='draft',
        )

        self.assertEqual(application.hours, Decimal('0.0'))
        self.assertEqual(application.midnight_hours, Decimal('4.0'))
        self.assertEqual(application.hours + application.midnight_hours, Decimal('4.0'))

    def test_holiday_without_work_pattern_keeps_second_example_at_9_5_hours(self):
        application = OvertimeApplication.objects.create(
            applicant=self.leader,
            created_by=self.leader,
            work_date='2026-07-11',
            application_type='holiday',
            start_time='19:15',
            end_time='06:00',
            reason='休日出勤テスト',
            team=self.team,
            status='draft',
        )

        self.assertEqual(application.hours, Decimal('3.0'))
        self.assertEqual(application.midnight_hours, Decimal('6.5'))
        self.assertEqual(application.hours + application.midnight_hours, Decimal('9.5'))

    def test_holiday_without_work_pattern_keeps_third_example_at_10_hours(self):
        application = OvertimeApplication.objects.create(
            applicant=self.leader,
            created_by=self.leader,
            work_date='2026-07-11',
            application_type='holiday',
            start_time='19:15',
            end_time='06:57',
            reason='休日出勤テスト',
            team=self.team,
            status='draft',
        )

        self.assertEqual(application.hours, Decimal('4.0'))
        self.assertEqual(application.midnight_hours, Decimal('6.0'))
        self.assertEqual(application.hours + application.midnight_hours, Decimal('10.0'))

    def test_holiday_with_work_pattern_keeps_midnight_ratio_based_on_break_adjusted_minutes(self):
        pattern = WorkPattern.objects.create(
            pattern_code='K-TEST',
            pattern_name='休日テスト',
            start_time='08:00',
            end_time='17:05',
        )
        BreakTime.objects.create(
            work_pattern=pattern,
            break_start='20:00',
            break_end='21:00',
            order=1,
        )

        application = OvertimeApplication.objects.create(
            applicant=self.leader,
            created_by=self.leader,
            work_date='2026-07-11',
            application_type='holiday',
            start_time='19:15',
            end_time='06:00',
            work_pattern=pattern,
            reason='休日出勤テスト',
            team=self.team,
            status='draft',
        )

        self.assertEqual(application.hours, Decimal('3.0'))
        self.assertEqual(application.midnight_hours, Decimal('6.5'))
