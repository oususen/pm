from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


class UsernameImmutableApiTests(TestCase):
    """ユーザー名（login_id）は作成後に変更できないことの確認"""

    def setUp(self):
        self.admin = User.objects.create_superuser('admin_u', 'admin@example.com', 'pw')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.target = User.objects.create_user('000175', 'a@example.com', 'pw')
        self.detail_url = f'/api/accounts/users/{self.target.pk}/'

    def test_create_with_username_succeeds(self):
        res = self.client.post('/api/accounts/users/', {'username': '000200'}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertTrue(User.objects.filter(username='000200').exists())

    def test_create_duplicate_username_rejected(self):
        res = self.client.post('/api/accounts/users/', {'username': '000175'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_create_initial_password_is_username_without_employee_code(self):
        self.client.post('/api/accounts/users/', {'username': '000201'}, format='json')
        self.assertTrue(User.objects.get(username='000201').check_password('000201'))

    def test_create_initial_password_is_employee_code_when_given(self):
        res = self.client.post(
            '/api/accounts/users/',
            {'username': '000202', 'profile': {'employee_code': 'E202'}},
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertTrue(User.objects.get(username='000202').check_password('E202'))

    def test_put_other_username_rejected(self):
        res = self.client.put(self.detail_url, {'username': '999999'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('ユーザー名は作成後に変更できません。', res.json()['username'])
        self.target.refresh_from_db()
        self.assertEqual(self.target.username, '000175')

    def test_patch_other_username_rejected(self):
        res = self.client.patch(self.detail_url, {'username': '999999'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.target.refresh_from_db()
        self.assertEqual(self.target.username, '000175')

    def test_case_only_change_rejected(self):
        target = User.objects.create_user('abc', 'b@example.com', 'pw')
        res = self.client.patch(f'/api/accounts/users/{target.pk}/', {'username': 'ABC'}, format='json')
        self.assertEqual(res.status_code, 400)
        target.refresh_from_db()
        self.assertEqual(target.username, 'abc')

    def test_put_same_username_succeeds(self):
        res = self.client.put(
            self.detail_url, {'username': '000175', 'email': 'new@example.com'}, format='json'
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.target.refresh_from_db()
        self.assertEqual(self.target.username, '000175')
        self.assertEqual(self.target.email, 'new@example.com')

    def test_patch_email_only_succeeds(self):
        res = self.client.patch(self.detail_url, {'email': 'x@example.com'}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        self.target.refresh_from_db()
        self.assertEqual(self.target.email, 'x@example.com')
        self.assertEqual(self.target.username, '000175')

    def test_me_patch_username_change_rejected(self):
        client = APIClient()
        client.force_authenticate(self.target)
        res = client.patch('/api/accounts/users/me/', {'username': 'changed'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.target.refresh_from_db()
        self.assertEqual(self.target.username, '000175')

    def test_me_patch_email_succeeds(self):
        client = APIClient()
        client.force_authenticate(self.target)
        res = client.patch('/api/accounts/users/me/', {'email': 'me@example.com'}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        self.target.refresh_from_db()
        self.assertEqual(self.target.email, 'me@example.com')


class UsernameAdminReadonlyTests(TestCase):
    """Django管理画面: 編集時はusernameが読み取り専用、追加時は入力可"""

    def setUp(self):
        self.admin = User.objects.create_superuser('admin_u', 'admin@example.com', 'pw')
        self.client.force_login(self.admin)
        self.target = User.objects.create_user('000175', 'a@example.com', 'pw')

    def test_change_view_username_is_readonly(self):
        res = self.client.get(reverse('admin:auth_user_change', args=[self.target.pk]))
        self.assertEqual(res.status_code, 200)
        form = res.context['adminform'].form
        self.assertNotIn('username', form.fields)
        self.assertIn('username', res.context['adminform'].readonly_fields)

    def test_add_view_username_is_editable(self):
        res = self.client.get(reverse('admin:auth_user_add'))
        self.assertEqual(res.status_code, 200)
        self.assertIn('username', res.context['adminform'].form.fields)
        self.assertNotIn('username', res.context['adminform'].readonly_fields)
