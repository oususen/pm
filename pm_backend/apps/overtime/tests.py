from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from accounts.models import Department, UserProfile
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
