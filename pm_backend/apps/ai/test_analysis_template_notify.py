"""テンプレートの通知(第3段階3-C): 確認依頼(管理者へメールのみ)・結果(作成者へメールとPM通知)・記録・失敗時の扱いを検証する。

実ユーザー・実効権限・一時SQLiteを使う。メール送信(EmailService.send_plain_email)は模擬(実SMTPへは接続しない)。
別スレッドでの通知は、テストでは、その場で実行する(状態の確定=コミットの後に動くことは、on_commitのコールバックで再現する)。
"""
import json
import smtplib
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import override_settings

from accounts.models import UserPermission, UserProfile, UserSmtpConfig
from ai.models import AIAnalysisTemplate, AIAnalysisTemplateNotification as Record
from ai.services import analysis_template_notify_service as notify
from ai.services.analysis_plan_store import AnalysisPlanStore
from ai.test_analysis_template_review import ReviewBase
from ai.test_analysis_templates import make_plan
from notifications.models import Notification
from shipping.services.email_service import EmailService

BASE = 'https://10.0.1.232:8501'
ORIGINAL_SEND = EmailService.send_plain_email  # テストの模擬に置き換えられる前の、本物の送信関数
LEAK = 'SECRET-SMTP-LEAK <someone@example.com>'


class InlineThread:
    """threading.Threadの代わり。start()でその場で実行する。"""
    def __init__(self, target=None, args=(), kwargs=None, daemon=None):
        self.target, self.args, self.kwargs = target, args, kwargs or {}

    def start(self):
        self.target(*self.args, **self.kwargs)


@override_settings(AI_TEMPLATE_NOTIFY_SENDER_USER='mail-sender', PM_PUBLIC_BASE_URL=BASE)
class NotifyBase(ReviewBase):
    def setUp(self):
        super().setUp()
        users = get_user_model().objects
        self.sender = users.create_user(username='mail-sender', email='sender@example.com')
        UserSmtpConfig.objects.create(user=self.sender, smtp_host='smtp.example.com', smtp_port=587, smtp_user='s', smtp_password='p', is_active=True)
        for user, email in ((self.creator, 'creator@example.com'), (self.admin, 'admin@example.com'), (self.other, 'other@example.com')):
            user.email = email
            user.save()
        self.admin2.email = ''
        self.admin2.save()
        for user in (self.admin, self.admin2):  # 宛先は、システム管理者のフラグがある人だけ
            UserProfile.objects.update_or_create(user=user, defaults={'is_system_admin': True})
        self.mails = []
        patcher = patch.object(notify.EmailService, 'send_plain_email', side_effect=self.fake_send)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.fail_mail = False

    def fake_send(self, **kwargs):
        self.mails.append(kwargs)
        return {'success': not self.fail_mail, 'message': LEAK}

    def records(self, **filters):
        return list(Record.objects.filter(**filters).order_by('id'))


class SubmittedTests(NotifyBase):
    def test_mails_each_active_admin_with_template_number_creator_name_and_link_only(self):
        template = self.row()
        notify.notify_submitted(template.pk)
        recipients = {mail['to_emails'][0] for mail in self.mails}
        self.assertEqual(recipients, {'admin@example.com'})  # admin2はメール未登録で送れない。作成者・一般の利用者・他人には送らない
        mail = self.mails[0]
        self.assertEqual(mail['subject'], f'[PM] AI分析テンプレートの確認依頼(ID {template.pk}・版1)')
        for part in (f'テンプレートID: {template.pk} / 版: 1', '作成者: rv-creator', f'{BASE}/ai/chat', '管理者の確認待ちで保存されました'):
            self.assertIn(part, mail['body'])
        # 目的・SQL・Python・名称などの内容は載せない
        for hidden in (template.name, template.purpose, template.python_code, 'SELECT', 'emit_table', '秘密の条件'):
            self.assertNotIn(hidden, mail['body']); self.assertNotIn(hidden, mail['subject'])
        # 送信者は指定のユーザー(管理者の既定設定へ切り替えない)・タイムアウト20秒・宛先は1人ずつ
        self.assertEqual((mail['user_id'], mail['timeout'], len(mail['to_emails'])), (self.sender.pk, 20, 1))
        rows = [(r.recipient.username, r.channel, r.status, r.reason) for r in self.records(kind='submitted')]
        self.assertEqual(sorted(rows), [('rv-admin', 'mail', 'sent', ''), ('rv-admin2', 'mail', 'skipped', 'no_email')])
        self.assertEqual(Notification.objects.count(), 0, '確認依頼はメールだけ(PM通知なし)')

    def test_no_admin_is_recorded_as_no_recipient(self):
        UserPermission.objects.filter(resource='settings.ai').delete()
        template = self.row()
        notify.notify_submitted(template.pk)
        self.assertEqual(self.mails, [])
        self.assertEqual([(r.recipient_id, r.status, r.reason) for r in self.records()], [(None, 'skipped', 'no_recipient')])

    def test_permission_lookup_failure_does_not_send_to_anyone(self):
        template = self.row()
        with patch.object(notify, '_has_resource_permission', side_effect=RuntimeError('SECRET-DB')):
            notify.notify_submitted(template.pk)
        self.assertEqual(self.mails, [])
        self.assertEqual([r.reason for r in self.records()], ['no_recipient'])

    def test_inactive_admin_is_not_a_recipient(self):
        get_user_model().objects.filter(pk=self.admin.pk).update(is_active=False)
        template = self.row()
        notify.notify_submitted(template.pk)
        self.assertEqual(self.mails, [])

    def test_a_superuser_without_the_system_admin_flag_is_not_a_recipient(self):
        # スーパーユーザーは、実効の権限判定では「権限あり」になるが、システム管理者のフラグがなければ、送らない(BOSS指示 2026-10-06)
        users = get_user_model().objects
        kitayama = users.create_user(username='kitayama', email='kitayama@example.com', is_superuser=True)
        UserProfile.objects.update_or_create(user=kitayama, defaults={'is_system_admin': False})
        self.assertTrue(notify._has_resource_permission(kitayama, 'settings.ai', 'edit'))
        template = self.row()
        notify.notify_submitted(template.pk)
        self.assertEqual({mail['to_emails'][0] for mail in self.mails}, {'admin@example.com'})
        self.assertNotIn('kitayama', [r.recipient.username for r in self.records(kind='submitted') if r.recipient])

    def test_a_user_without_a_profile_is_not_a_recipient(self):
        users = get_user_model().objects
        users.create_user(username='no-profile', email='np@example.com', is_superuser=True)
        notify.notify_submitted(self.row().pk)
        self.assertNotIn('np@example.com', [mail['to_emails'][0] for mail in self.mails])

    def test_the_system_admin_flag_alone_is_not_enough_without_the_edit_permission(self):
        UserPermission.objects.filter(user=self.admin, resource='settings.ai').update(can_edit=False)
        notify.notify_submitted(self.row().pk)
        self.assertEqual(self.mails, [])  # admin2は、メール未登録

    def test_a_flagged_admin_loses_the_mail_when_the_flag_is_removed(self):
        UserProfile.objects.filter(user=self.admin).update(is_system_admin=False)
        notify.notify_submitted(self.row().pk)
        self.assertEqual(self.mails, [])


class SenderAndLinkTests(NotifyBase):
    def test_sender_not_configured_means_no_mail_and_never_falls_back_to_the_default_smtp(self):
        for label, change in (
            ('empty', lambda: override_settings(AI_TEMPLATE_NOTIFY_SENDER_USER='')),
            ('unknown_user', lambda: override_settings(AI_TEMPLATE_NOTIFY_SENDER_USER='nobody')),
        ):
            with self.subTest(label), change():
                template = self.row()
                notify.notify_submitted(template.pk)
                self.assertEqual(self.mails, [])
                self.assertTrue(all(r.status == 'skipped' and r.reason == 'sender_not_configured' for r in self.records(template=template, channel='mail')
                                    if r.recipient_id == self.admin.pk))
        # SMTP設定がない・無効なユーザーも同じ
        UserSmtpConfig.objects.filter(user=self.sender).update(is_active=False)
        template = self.row()
        notify.notify_submitted(template.pk)
        self.assertEqual(self.mails, [])
        UserSmtpConfig.objects.filter(user=self.sender).update(is_active=True, smtp_host='')
        notify.notify_submitted(template.pk)
        self.assertEqual(self.mails, [])

    def test_missing_base_url_means_no_mail_and_a_recorded_reason(self):
        with override_settings(PM_PUBLIC_BASE_URL=''):
            template = self.row()
            notify.notify_submitted(template.pk)
            notify.notify_result(template.pk, 'approved', self.admin.pk)
        self.assertEqual(self.mails, [])
        reasons = {(r.kind, r.channel, r.reason) for r in self.records()}
        self.assertIn(('submitted', 'mail', 'base_url_not_configured'), reasons)
        self.assertIn(('approved', 'mail', 'base_url_not_configured'), reasons)
        self.assertIn(('approved', 'pm', ''), reasons)  # PM通知は、URLがなくても作成する

    def test_smtp_failure_is_recorded_without_the_raw_message_or_address(self):
        template = self.row()
        self.fail_mail = True
        notify.notify_submitted(template.pk)
        self.assertEqual([(r.status, r.reason) for r in self.records(recipient=self.admin)], [('failed', 'smtp_error')])
        self.mails.clear()
        with patch.object(notify.EmailService, 'send_plain_email', side_effect=smtplib.SMTPException(LEAK)):
            notify.notify_result(template.pk, 'approved', self.admin.pk)
        mail_record = self.records(channel='mail', kind='approved')[0]
        self.assertEqual((mail_record.status, mail_record.reason), ('failed', 'smtp_error'))
        # DBの記録に、エラー文・宛先アドレスは残らない
        dumped = json.dumps([[getattr(r, f.name) for f in r._meta.fields if f.name != 'created_at'] for r in Record.objects.all()], default=str, ensure_ascii=False)
        self.assertNotIn('SECRET', dumped); self.assertNotIn('example.com', dumped)

    def test_the_timeout_is_passed_only_by_the_notification_and_the_email_service_stays_backward_compatible(self):
        service = EmailService()
        config = {'host': 'smtp.example.com', 'port': 587, 'user': 'u', 'password': 'p'}
        for timeout, expected in ((20, {'timeout': 20}), (None, {})):
            with self.subTest(timeout=timeout), patch.object(EmailService, 'get_smtp_config', return_value=config), \
                    patch('shipping.services.email_service.smtplib.SMTP') as smtp:
                smtp.return_value.__enter__.return_value = MagicMock(send_message=MagicMock(return_value={}))
                kwargs = {} if timeout is None else {'timeout': timeout}
                self.assertTrue(ORIGINAL_SEND(service, to_emails=['a@example.com'], subject='s', body='b', **kwargs)['success'])
                self.assertEqual(smtp.call_args.kwargs, expected)
                self.assertEqual(smtp.call_args.args, ('smtp.example.com', 587))


class AttachmentSenderUnchangedTests(NotifyBase):
    def test_send_email_with_attachment_is_unchanged_and_still_works(self):
        """今回のタイムアウト追加は、添付つきの送信(別の関数)に影響しない(待ち時間を指定せず、従来どおり動く)。"""
        from io import BytesIO
        config = {'host': 'smtp.example.com', 'port': 587, 'user': 'u', 'password': 'p'}
        with patch.object(EmailService, 'get_smtp_config', return_value=config), patch('shipping.services.email_service.smtplib.SMTP') as smtp:
            smtp.return_value.__enter__.return_value = MagicMock(send_message=MagicMock(return_value={}))
            result = EmailService().send_email_with_attachment(
                to_emails=['a@example.com'], subject='s', body='b', attachment_data=BytesIO(b'x'), attachment_filename='a.pdf',
            )
        self.assertTrue(result['success'])
        self.assertEqual((smtp.call_args.args, smtp.call_args.kwargs), (('smtp.example.com', 587), {}))


class ResultTests(NotifyBase):
    def test_creator_gets_mail_and_pm_notification_with_fixed_texts(self):
        template = self.row(status='approved')
        notify.notify_result(template.pk, 'approved', self.admin.pk)
        mail = self.mails[0]
        self.assertEqual((mail['to_emails'], mail['subject'], mail['timeout']), (['creator@example.com'], f'[PM] AI分析テンプレートが承認されました(ID {template.pk}・版1)', 20))
        for part in (f'あなたが保存したAI分析テンプレート(ID {template.pk}・版1)が、承認されました。', '状態: 正式', '確認者: rv-admin', f'{BASE}/ai/chat'):
            self.assertIn(part, mail['body'])
        notification = Notification.objects.get()
        self.assertEqual((notification.title, notification.category, notification.domain), ('AI分析テンプレート: 承認されました', 'AI分析', 'AI_ANALYSIS'))
        self.assertEqual(notification.description, f'テンプレートID {template.pk}・版1が承認されました。AI分析のテンプレートで確認してください。')
        self.assertEqual(list(notification.target_users.values_list('pk', flat=True)), [self.creator.pk])
        today = datetime.now().date()
        self.assertEqual((notification.valid_from, notification.valid_to), (today, today + timedelta(days=30)))
        # PM通知は全員に見え得るため、ユーザー名・名称・目的・理由を載せない
        for hidden in ('rv-creator', 'rv-admin', template.name, template.purpose):
            self.assertNotIn(hidden, notification.title + notification.description)
        self.assertEqual([(r.channel, r.status, r.pm_notification_id) for r in self.records()], [('mail', 'sent', None), ('pm', 'sent', notification.pk)])

    def test_rejection_never_includes_the_reason_text_and_supersede_names_the_correction(self):
        template = self.row(status='rejected', rejection_reason='却下理由の本文ＺＺＺ')
        notify.notify_result(template.pk, 'rejected', self.admin.pk)
        mail = self.mails[0]
        self.assertEqual(mail['subject'], f'[PM] AI分析テンプレートが却下されました(ID {template.pk}・版1)')
        self.assertIn('理由は、PMのテンプレートの詳細で確認してください。', mail['body'])
        self.assertNotIn('ＺＺＺ', mail['body']); self.assertNotIn('ＺＺＺ', Notification.objects.get().description)
        replacement = self.row(status='approved')
        notify.notify_result(template.pk, 'superseded', self.admin.pk, replacement.pk)
        mail = self.mails[-1]
        self.assertEqual(mail['subject'], f'[PM] AI分析テンプレートが訂正版に置き換えられました(ID {template.pk}・版1)')
        self.assertIn(f'訂正版: ID {replacement.pk}・版1', mail['body'])

    def test_deleted_or_inactive_creator_and_missing_email_are_recorded_as_skipped(self):
        template = self.row()
        AIAnalysisTemplate.objects.filter(pk=template.pk).update(approved_by=None)
        notify.notify_result(template.pk, 'approved', self.admin.pk)
        self.assertEqual({(r.channel, r.status, r.reason) for r in self.records()}, {('mail', 'skipped', 'recipient_unavailable'), ('pm', 'skipped', 'recipient_unavailable')})
        self.assertEqual((self.mails, Notification.objects.count()), ([], 0))
        no_email = self.row(self.other)
        get_user_model().objects.filter(pk=self.other.pk).update(email='')
        notify.notify_result(no_email.pk, 'rejected', self.admin.pk)
        mine = {(r.channel, r.status, r.reason) for r in self.records(template=no_email)}
        self.assertEqual(mine, {('mail', 'skipped', 'no_email'), ('pm', 'sent', '')})

    def test_pm_notification_failure_is_recorded_and_does_not_stop_the_mail(self):
        template = self.row(status='approved')
        with patch.object(notify.Notification.objects, 'create', side_effect=RuntimeError('SECRET-DB')):
            notify.notify_result(template.pk, 'approved', self.admin.pk)
        self.assertEqual(len(self.mails), 1)
        self.assertEqual({(r.channel, r.status, r.reason) for r in self.records()}, {('mail', 'sent', ''), ('pm', 'failed', 'pm_error')})

    def test_failure_while_setting_the_target_leaves_no_all_user_notification(self):
        template = self.row(status='approved')
        with patch('django.db.models.query.QuerySet.bulk_create', side_effect=RuntimeError('SECRET-DB')):
            notify.notify_result(template.pk, 'approved', self.admin.pk)
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual({(r.channel, r.status, r.reason) for r in self.records()}, {('mail', 'sent', ''), ('pm', 'failed', 'pm_error')})

    def test_unknown_kind_is_refused(self):
        with self.assertRaises(ValueError):
            notify.notify_result(self.row().pk, 'bogus')


@override_settings(AI_TEMPLATE_NOTIFY_SENDER_USER='mail-sender', PM_PUBLIC_BASE_URL=BASE)
class FlowIntegrationTests(NotifyBase):
    """保存・承認・却下のあとに、通知が動くこと。通知の失敗で、本体の処理を取り消さないこと。"""
    def setUp(self):
        super().setUp()
        patcher = patch.object(notify.threading, 'Thread', InlineThread)
        patcher.start()
        self.addCleanup(patcher.stop)

    def save(self, user, plan):
        with patch.object(notify.AIAnalysisTemplate.objects, 'select_related', wraps=AIAnalysisTemplate.objects.select_related), \
                patch('ai.services.analysis_template_service.AnalysisPlanStore.get', lambda _s, pid, owner: AnalysisPlanStore._decode(json.dumps(plan), owner)):
            with self.captureOnCommitCallbacks(execute=True):
                return self.call('ai-analysis-templates', user, data={'plan_id': plan['id'], 'category': 'shipment', 'revision': plan['revision']})

    def test_save_notifies_admins_once_and_a_resend_does_not_notify_again(self):
        plan = make_plan(self.creator.pk)
        first = self.save(self.creator, plan)
        self.assertEqual(first.status_code, 201)
        self.assertEqual([m['to_emails'] for m in self.mails], [['admin@example.com']])
        self.assertEqual(self.save(self.creator, plan).status_code, 200)
        self.assertEqual(len(self.mails), 1, '同じ内容の再送(既存の行を返す)では、通知しない')

    def test_notification_happens_only_after_the_commit(self):
        plan = make_plan(self.creator.pk)
        with patch('ai.services.analysis_template_service.AnalysisPlanStore.get', lambda _s, pid, owner: AnalysisPlanStore._decode(json.dumps(plan), owner)):
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                self.assertEqual(self.call('ai-analysis-templates', self.creator, data={'plan_id': plan['id'], 'category': 'shipment', 'revision': plan['revision']}).status_code, 201)
        self.assertEqual(self.mails, [], 'コミットの前には、送らない')
        self.assertEqual(len(callbacks), 1)

    def test_approval_rejection_and_supersede_notify_the_creators(self):
        template = self.row()
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.approve(self.admin, template).status_code, 200)
        self.assertEqual([(r.kind, r.channel, r.status) for r in self.records(template=template)], [('approved', 'mail', 'sent'), ('approved', 'pm', 'sent')])
        rejected = self.row(self.other)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.reject(self.admin, rejected).status_code, 200)
        self.assertEqual({(r.kind, r.channel) for r in self.records(template=rejected)}, {('rejected', 'mail'), ('rejected', 'pm')})
        # 訂正版の承認: 訂正版の作成者(admin)に承認、置き換えられた元の版の作成者(other)に置換を通知
        rejected.refresh_from_db()
        plan = make_plan(self.admin.pk, revision=2)
        plan['proposal'] = {**plan['proposal'], 'title': '訂正した分析'}
        with patch('ai.services.analysis_template_service.AnalysisPlanStore.get', lambda _s, pid, owner: AnalysisPlanStore._decode(json.dumps(plan), owner)):
            created = self.call('ai-analysis-templates', self.admin, data={'plan_id': plan['id'], 'category': 'shipment', 'revision': 2, 'replaces': rejected.pk})
        correction = AIAnalysisTemplate.objects.get(pk=created.data['id'])
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.approve(self.admin2, correction).status_code, 200)
        self.assertEqual({(r.kind, r.channel, r.status) for r in self.records(template=correction)}, {('approved', 'mail', 'sent'), ('approved', 'pm', 'sent')})
        self.assertEqual({(r.kind, r.channel, r.status) for r in self.records(template=rejected, kind='superseded')}, {('superseded', 'mail', 'sent'), ('superseded', 'pm', 'sent')})
        self.assertIn(f'訂正版: ID {correction.pk}・版2', [m for m in self.mails if m['to_emails'] == ['other@example.com']][-1]['body'])

    def test_a_failing_notification_never_undoes_the_approval_or_rejection(self):
        template, other = self.row(), self.row()
        with patch.object(notify, 'notify_result', side_effect=RuntimeError('SECRET-NOTIFY')), self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.approve(self.admin, template).status_code, 200)
            self.assertEqual(self.reject(self.admin, other).status_code, 200)
        template.refresh_from_db(); other.refresh_from_db()
        self.assertEqual((template.status, other.status), ('approved', 'rejected'))

    def test_a_failure_inside_the_thread_is_recorded_without_the_exception_text(self):
        template = self.row()
        with patch.object(notify, 'notify_result', side_effect=RuntimeError('SECRET-NOTIFY')), self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.approve(self.admin, template).status_code, 200)
        rows = [(r.kind, r.channel, r.status, r.reason, r.recipient_id) for r in self.records(template=template)]
        self.assertEqual(rows, [('approved', 'mail', 'failed', 'unexpected_error', None)])
        self.assertNotIn('SECRET', json.dumps(self.call('ai-analysis-template', self.admin, 'get', template_id=template.pk).data, ensure_ascii=False))
        template.refresh_from_db()
        self.assertEqual(template.status, 'approved')
        # 通知の失敗の記録自体が失敗しても、例外を外へ出さない
        other = self.row()
        with patch.object(notify, 'notify_submitted', side_effect=RuntimeError('SECRET-NOTIFY')), \
                patch.object(notify.Record.objects, 'create', side_effect=RuntimeError('SECRET-DB')), self.captureOnCommitCallbacks(execute=True):
            notify.schedule_submitted(other.pk)
        self.assertEqual(self.records(template=other), [])

    def test_a_failing_save_notification_keeps_the_saved_template(self):
        plan = make_plan(self.creator.pk)
        with patch.object(notify, 'notify_submitted', side_effect=RuntimeError('SECRET-NOTIFY')):
            response = self.save(self.creator, plan)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AIAnalysisTemplate.objects.count(), 1)

    def test_a_failed_approval_sends_nothing(self):
        template = self.row()
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.approve(self.admin, template, revision=9).status_code, 409)  # 版の不一致で承認できない
        self.assertEqual((self.mails, Record.objects.count(), Notification.objects.count()), ([], 0, 0))


class RecordVisibilityTests(NotifyBase):
    def test_records_are_shown_to_the_creator_and_admins_only_without_addresses_or_bodies(self):
        template = self.row()
        notify.notify_submitted(template.pk)
        notify.notify_result(template.pk, 'approved', self.admin.pk)
        for user, shown in ((self.creator, True), (self.admin, True), (self.other, False)):
            with self.subTest(user=user.username):
                data = self.call('ai-analysis-template', user, 'get', template_id=template.pk).data
                self.assertEqual('notifications' in data, shown)
        data = self.call('ai-analysis-template', self.creator, 'get', template_id=template.pk).data
        rows = data['notifications']
        self.assertEqual({(r['kind_label'], r['channel_label'], r['status_label']) for r in rows},
                         {('確認依頼', 'メール', '送信済み'), ('確認依頼', 'メール', '送れない'), ('承認', 'メール', '送信済み'), ('承認', 'PM通知', '送信済み')})
        self.assertIn('メールアドレスが未登録です', [r['reason_label'] for r in rows])
        dumped = json.dumps(data, ensure_ascii=False)
        self.assertNotIn('example.com', dumped); self.assertNotIn('SECRET', dumped); self.assertNotIn('smtp', dumped.lower())
        # 一覧には出さない(詳細だけ)
        listing = self.call('ai-analysis-templates', self.creator, 'get').data['results'][0]
        self.assertNotIn('notifications', listing)


class ResendTests(NotifyBase):
    """失敗・送れなかったメールの手動の再送(同じ宛先へ1回だけ。作成者と管理者)。"""

    def resend(self, user, record):
        return self.call('ai-analysis-template-notification-resend', user, record_id=record.pk)

    def failed_submitted(self, **overrides):
        """確認依頼を、メール送信が失敗する状態で一度送り、管理者(admin)宛ての失敗の行を返す。"""
        template = self.row(**overrides)
        self.fail_mail = True
        notify.notify_submitted(template.pk)
        self.fail_mail = False
        self.mails.clear()
        record = self.records(template=template, recipient=self.admin)[0]
        self.assertEqual((record.status, record.reason), ('failed', 'smtp_error'))
        return template, record

    def test_resend_sends_the_same_mail_once_and_adds_a_row_without_changing_the_original(self):
        template, record = self.failed_submitted()
        response = self.resend(self.creator, record)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.mails), 1)
        self.assertEqual((self.mails[0]['to_emails'], self.mails[0]['subject'], self.mails[0]['timeout']),
                         (['admin@example.com'], f'[PM] AI分析テンプレートの確認依頼(ID {template.pk}・版1)', 20))
        rows = self.records(template=template, recipient=self.admin)
        self.assertEqual([(r.status, r.reason) for r in rows], [('failed', 'smtp_error'), ('sent', '')])
        self.assertEqual(rows[0].pk, record.pk)
        self.assertEqual(self.resend(self.creator, record).status_code, 409)
        self.assertEqual(self.resend(self.admin, rows[1]).status_code, 409)
        self.assertEqual(len(self.mails), 1)

    def test_can_resend_flag_only_for_a_single_failed_or_skipped_mail_with_a_recipient(self):
        template, record = self.failed_submitted()
        flags = lambda: {(r['recipient'], r['status']): r['can_resend'] for r in self.call('ai-analysis-template', self.creator, 'get', template_id=template.pk).data['notifications']}
        self.assertEqual(flags(), {('rv-admin', 'failed'): True, ('rv-admin2', 'skipped'): True})
        self.resend(self.creator, record)
        after = [(r['status'], r['can_resend']) for r in self.call('ai-analysis-template', self.creator, 'get', template_id=template.pk).data['notifications'] if r['recipient'] == 'rv-admin']
        self.assertEqual(after, [('failed', False), ('sent', False)])

    def test_only_creator_and_admins_may_resend_and_others_see_nothing(self):
        _, record = self.failed_submitted()
        self.assertEqual(self.resend(self.other, record).status_code, 404)
        self.assertEqual(self.resend(None, record).status_code, 403)
        self.assertEqual(self.mails, [])
        self.assertEqual(self.resend(self.admin2, record).status_code, 200)
        self.assertEqual(len(self.mails), 1)

    def test_without_the_analysis_edit_permission_the_resend_is_refused(self):
        _, record = self.failed_submitted()
        UserPermission.objects.filter(user=self.creator, resource='ai.analysis').update(can_edit=False)
        self.assertEqual(self.resend(self.creator, record).status_code, 403)
        self.assertEqual(self.mails, [])

    def test_a_sent_row_a_pm_row_and_a_row_without_recipient_cannot_be_resent(self):
        template = self.row(status='approved')
        notify.notify_result(template.pk, 'approved', self.admin.pk)
        mail_row, pm_row = self.records(template=template)
        self.assertEqual((mail_row.status, pm_row.channel), ('sent', 'pm'))
        no_recipient = Record.objects.create(template=template, kind='approved', channel='mail', recipient=None, status='failed', reason='unexpected_error')
        for record in (mail_row, pm_row, no_recipient):
            with self.subTest(record=record.pk):
                self.assertEqual(self.resend(self.admin, record).status_code, 409)
        self.assertEqual(len(self.mails), 1)

    def test_a_notice_for_an_old_state_is_not_resent(self):
        template, record = self.failed_submitted()
        self.assertEqual(self.approve(self.admin, template).status_code, 200)
        self.mails.clear()
        self.assertEqual(self.resend(self.admin, record).status_code, 409)
        self.assertEqual(self.mails, [])
        self.assertEqual(len(self.records(template=template, kind='submitted', recipient=self.admin)), 1)

    def test_result_mail_is_resent_with_the_same_fixed_text_and_reviewer(self):
        template = self.row(status='rejected', rejection_reason='却下理由の本文ＺＺＺ', reviewed_by=self.admin, reviewed_at=datetime.now())
        self.fail_mail = True
        notify.notify_result(template.pk, 'rejected', self.admin.pk)
        self.fail_mail = False
        self.mails.clear()
        record = self.records(template=template, channel='mail')[0]
        response = self.resend(self.creator, record)
        self.assertEqual(response.status_code, 200)
        mail = self.mails[0]
        self.assertEqual((mail['to_emails'], mail['subject']), (['creator@example.com'], f'[PM] AI分析テンプレートが却下されました(ID {template.pk}・版1)'))
        self.assertIn('確認者: rv-admin', mail['body'])
        self.assertNotIn('ＺＺＺ', mail['body'])
        self.assertEqual(Notification.objects.count(), 1)  # 再送でPM通知は増えない(最初の分だけ)
        self.assertEqual([r.status for r in self.records(template=template, channel='mail')], ['failed', 'sent'])

    def test_without_the_base_url_the_resend_records_skipped_and_uses_up_the_single_resend(self):
        template, record = self.failed_submitted()
        with override_settings(PM_PUBLIC_BASE_URL=''):
            self.assertEqual(self.resend(self.creator, record).status_code, 200)
        self.assertEqual(self.mails, [])
        self.assertEqual([(r.status, r.reason) for r in self.records(template=template, recipient=self.admin)],
                         [('failed', 'smtp_error'), ('skipped', 'base_url_not_configured')])
        self.assertEqual(self.resend(self.creator, record).status_code, 409)

    def test_a_recipient_who_is_no_longer_an_admin_is_not_mailed_again(self):
        template, record = self.failed_submitted()
        UserPermission.objects.filter(user=self.admin, resource='settings.ai').delete()
        get_user_model().objects.filter(pk=self.admin.pk).update(is_superuser=False)
        self.assertEqual(self.resend(self.creator, record).status_code, 200)
        self.assertEqual(self.mails, [])
        self.assertEqual(self.records(template=template, recipient=self.admin)[-1].reason, 'recipient_unavailable')

    def test_a_recipient_whose_system_admin_flag_was_removed_is_not_mailed_again(self):
        template, record = self.failed_submitted()
        UserProfile.objects.filter(user=self.admin).update(is_system_admin=False)
        self.assertEqual(self.resend(self.creator, record).status_code, 200)
        self.assertEqual(self.mails, [])
        self.assertEqual(self.records(template=template, recipient=self.admin)[-1].reason, 'recipient_unavailable')

    def test_a_failure_during_the_resend_is_recorded_without_the_exception_text(self):
        template, record = self.failed_submitted()
        with patch.object(notify, '_deliver', side_effect=RuntimeError('SECRET-RESEND')):
            response = self.resend(self.creator, record)
        self.assertEqual(response.status_code, 200)
        last = self.records(template=template, recipient=self.admin)[-1]
        self.assertEqual((last.status, last.reason), ('failed', 'unexpected_error'))
        self.assertNotIn('SECRET', json.dumps(response.data, ensure_ascii=False))
        self.assertEqual(self.resend(self.creator, record).status_code, 409)

    def test_a_body_is_refused_and_the_record_stays_hidden_in_the_response(self):
        _, record = self.failed_submitted()
        response = self.call('ai-analysis-template-notification-resend', self.creator, data={'to': 'x@example.com'}, record_id=record.pk)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.mails, [])
        ok = self.resend(self.creator, record)
        dumped = json.dumps(ok.data, ensure_ascii=False)
        self.assertNotIn('example.com', dumped); self.assertNotIn('SECRET', dumped)

    def test_a_missing_record_is_404(self):
        self.assertEqual(self.call('ai-analysis-template-notification-resend', self.admin, record_id=999999).status_code, 404)

    def test_a_supersede_notice_without_an_approved_correction_is_not_resent(self):
        template = self.row(status='superseded')
        self.fail_mail = True
        notify.notify_result(template.pk, 'superseded', self.admin.pk)
        self.fail_mail = False
        self.mails.clear()
        record = self.records(template=template, channel='mail')[0]
        self.assertEqual(self.resend(self.creator, record).status_code, 409)
        self.assertEqual(self.mails, [])
