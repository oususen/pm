from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.approval_views import ApprovalRequestViewSet
from accounts.models import ApprovalRequest, ApprovalRouteConfig, ApprovalTask, Department, UserProfile
from production.views_laser_weekly_plan import LaserWeeklyPlanViewSet


class LaserMaterialOrderApprovalTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username='material-creator', password='test-pass')
        UserProfile.objects.create(user=self.user, role='leader', employee_code='MATERIAL-CREATOR')
        self.route = ApprovalRouteConfig.objects.create(
            item_key='laser_material_order',
            item_name='レーザー材料発注',
            creator_role='leader',
            reviewer1_role='supervisor',
            reviewer2_enabled=False,
            approver_role='manager',
        )

    def test_material_order_approval_returns_created_request_for_week(self):
        request = self.factory.post(
            '/api/laser-weekly-plans/material-order-approval/',
            {'start_date': '2026-09-07'},
            format='json',
        )
        force_authenticate(request, user=self.user)

        response = LaserWeeklyPlanViewSet.as_view({'post': 'material_order_approval'})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'created')
        self.assertEqual(response.data['current_stage'], 'creator')
        self.assertEqual(response.data['context']['start_date'], '2026-09-07')
        self.assertEqual(
            ApprovalRequest.objects.filter(
                route_config=self.route,
                creator=self.user,
                context__start_date='2026-09-07',
            ).count(),
            1,
        )

    def test_material_order_approval_rejects_invalid_date(self):
        request = self.factory.post(
            '/api/laser-weekly-plans/material-order-approval/',
            {'start_date': 'invalid'},
            format='json',
        )
        force_authenticate(request, user=self.user)

        response = LaserWeeklyPlanViewSet.as_view({'post': 'material_order_approval'})(request)

        self.assertEqual(response.status_code, 400)

    def test_submit_creates_reviewer_task_for_creators_supervisor(self):
        division = Department.objects.create(name='レーザ事業部', level='division', display_id=1)
        group = Department.objects.create(name='レーザ係', level='group', parent=division, display_id=2)
        team = Department.objects.create(name='レーザ班', level='team', parent=group, display_id=3)
        unit = Department.objects.create(name='レーザグループ', level='unit', parent=team, display_id=4)
        self.user.profile.division = division
        self.user.profile.group = group
        self.user.profile.team = team
        self.user.profile.unit = unit
        self.user.profile.role = 'leader'
        self.user.profile.save()
        reviewer = User.objects.create_user(username='wang', password='test-pass')
        reviewer_profile = UserProfile.objects.create(
            user=reviewer,
            role='supervisor',
            employee_code='WANG',
            division=division,
            group=group,
            team=team,
        )
        reviewer_profile.supervisor_teams.add(team)

        create_request = self.factory.post(
            '/api/laser-weekly-plans/material-order-approval/',
            {
                'start_date': '2026-09-07',
                'lock_start_date': '2026-09-14',
                'lock_end_date': '2026-09-18',
            },
            format='json',
        )
        force_authenticate(create_request, user=self.user)
        create_response = LaserWeeklyPlanViewSet.as_view({'post': 'material_order_approval'})(create_request)
        approval_id = create_response.data['id']

        submit_request = self.factory.post(f'/api/accounts/approval-requests/{approval_id}/submit/')
        force_authenticate(submit_request, user=self.user)
        submit_response = ApprovalRequestViewSet.as_view({'post': 'submit_for_review'})(submit_request, pk=approval_id)

        self.assertEqual(submit_response.status_code, 200)
        self.assertEqual(submit_response.data['status'], 'reviewing')
        self.assertTrue(
            ApprovalTask.objects.filter(
                request_id=approval_id,
                assigned_to=reviewer,
                task_type='REVIEWER1_REVIEW',
                status='PENDING',
            ).exists()
        )

        get_request = self.factory.get('/api/laser-weekly-plans/material-order-approval/', {'start_date': '2026-09-07'})
        force_authenticate(get_request, user=reviewer)
        get_response = LaserWeeklyPlanViewSet.as_view({'get': 'material_order_approval'})(get_request)

        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data['id'], approval_id)
