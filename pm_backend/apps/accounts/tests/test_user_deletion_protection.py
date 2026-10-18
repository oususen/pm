from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import UserProfile


DELETE_MESSAGE = 'ユーザーは削除できません。「有効」のチェックを外して無効化してください。'


class UserDeletionProtectionApiTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user('api-actor', password='pw')
        self.target = User.objects.create_user(
            'delete-target', email='target@example.com', password='pw'
        )
        self.profile = UserProfile.objects.create(
            user=self.target,
            employee_code='DELETE-TARGET',
        )
        self.detail_url = f'/api/accounts/users/{self.target.pk}/'
        self.client = APIClient()

    def test_authenticated_delete_returns_400_and_preserves_user_and_profile(self):
        self.client.force_authenticate(self.actor)
        user_before = User.objects.values(
            'username', 'email', 'is_active', 'is_staff', 'is_superuser'
        ).get(pk=self.target.pk)
        profile_before = UserProfile.objects.values(
            'employee_code', 'role', 'employment_type', 'is_system_admin'
        ).get(pk=self.target.pk)

        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {'detail': DELETE_MESSAGE})
        self.assertEqual(
            User.objects.values(
                'username', 'email', 'is_active', 'is_staff', 'is_superuser'
            ).get(pk=self.target.pk),
            user_before,
        )
        self.assertEqual(
            UserProfile.objects.values(
                'employee_code', 'role', 'employment_type', 'is_system_admin'
            ).get(pk=self.target.pk),
            profile_before,
        )

    def test_unauthenticated_delete_is_rejected_by_existing_authentication(self):
        response = self.client.delete(self.detail_url)

        self.assertIn(response.status_code, (401, 403))
        self.assertTrue(User.objects.filter(pk=self.target.pk).exists())

    def test_patch_can_still_deactivate_without_deleting(self):
        self.client.force_authenticate(self.actor)

        response = self.client.patch(
            self.detail_url,
            {'is_active': False},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)
        self.assertTrue(UserProfile.objects.filter(pk=self.target.pk).exists())


class UserDeletionProtectionAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            'admin-delete-test', 'admin@example.com', 'pw'
        )
        self.target = User.objects.create_user('admin-delete-target', password='pw')
        UserProfile.objects.create(user=self.target, employee_code='ADMIN-DELETE-TARGET')
        self.user_admin = admin.site._registry[User]
        self.request = RequestFactory().get('/admin/auth/user/')
        self.request.user = self.superuser
        self.client.force_login(self.superuser)

    def test_delete_permission_is_false_and_bulk_delete_action_is_absent(self):
        self.assertFalse(self.user_admin.has_delete_permission(self.request))
        self.assertFalse(self.user_admin.has_delete_permission(self.request, self.target))
        self.assertNotIn('delete_selected', self.user_admin.get_actions(self.request))

    def test_direct_delete_url_is_forbidden_and_user_remains(self):
        response = self.client.get(
            reverse('admin:auth_user_delete', args=[self.target.pk])
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.target.pk).exists())
        self.assertTrue(UserProfile.objects.filter(pk=self.target.pk).exists())

    def test_change_permission_and_is_active_field_remain_available(self):
        self.assertTrue(self.user_admin.has_change_permission(self.request, self.target))
        self.assertNotIn(
            'is_active',
            self.user_admin.get_readonly_fields(self.request, self.target),
        )

        response = self.client.get(
            reverse('admin:auth_user_change', args=[self.target.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="is_active"')
