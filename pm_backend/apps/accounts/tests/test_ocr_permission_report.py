import json
from contextlib import ExitStack
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.core.management import call_command

from accounts.management.commands.report_ocr_permissions import describe_user


class OCRPermissionReportTests(SimpleTestCase):
    def test_command_outputs_all_four_setting_groups_without_database_writes(self):
        prefix = 'accounts.management.commands.report_ocr_permissions.'
        with ExitStack() as stack:
            for model in ['UserPermission', 'DepartmentPermission', 'PositionPermission', 'DepartmentPositionPermission']:
                mocked = stack.enter_context(patch(prefix + model))
                mocked.objects.filter.return_value.order_by.return_value.values.return_value = []
            get_user = stack.enter_context(patch(prefix + 'get_user_model'))
            get_user.return_value.objects.select_related.return_value.order_by.return_value.iterator.return_value = []
            output = StringIO()
            call_command('report_ocr_permissions', stdout=output)
        report = json.loads(output.getvalue())
        self.assertTrue(report['read_only'])
        self.assertEqual(set(report['legacy_settings']), {'user', 'department', 'position', 'department_position'})
        self.assertEqual(report['needs_review_count'], 0)

    def row(self, permissions, *, active=True, superuser=False):
        user = SimpleNamespace(pk=1, username='test', is_active=active, is_superuser=superuser)
        with patch('accounts.management.commands.report_ocr_permissions._build_effective_permissions', return_value=permissions):
            return describe_user(user)

    def test_legacy_edit_requires_review(self):
        row = self.row([{'resource': 'ai', 'can_view': False, 'can_edit': True}])
        self.assertTrue(row['needs_review'])
        self.assertFalse(row['ocr_allowed'])

    def test_existing_ocr_does_not_require_review(self):
        row = self.row([{'resource': key, 'can_view': True} for key in ['ai', 'ocr']])
        self.assertFalse(row['needs_review'])
        self.assertTrue(row['ocr_allowed'])

    def test_chat_and_analysis_do_not_grant_ocr(self):
        self.assertIsNone(self.row([{'resource': key, 'can_view': True} for key in ['ai.chat', 'ai.analysis']]))

    def test_inactive_user_is_listed_but_not_counted(self):
        row = self.row([{'resource': 'ai', 'can_view': True}], active=False)
        self.assertFalse(row['needs_review'])
        self.assertTrue(row['legacy_ai_allowed'])

    def test_superuser_keeps_access_without_legacy_key(self):
        row = self.row([], superuser=True)
        self.assertTrue(row['ocr_allowed'])
        self.assertFalse(row['needs_review'])
