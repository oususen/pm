"""テンプレートの通知(第3段階3-C): 管理者へのメール(確認依頼)と、作成者へのメール・PM通知(承認・却下・置換)。

BOSS承認(2026-10-05):
- 確認依頼は、システム管理者(実効のsettings.ai/edit)へ**メールだけ**(PM通知・タスクなし)。作成者のユーザー名と、テンプレートのID・版を載せる
- 承認・却下・置換は、作成者へ**メールとPM通知**
- 送信者は、`.env`の AI_TEMPLATE_NOTIFY_SENDER_USER で指定した既存ユーザーのSMTP設定(管理者の既定設定への切替はしない)。リンクは PM_PUBLIC_BASE_URL
  (Origin/Refererは使わない)。どちらかが未設定なら、メールは送らず、理由を記録する
- メール・PM通知は固定文。名称・目的・手順・コード・却下理由・実データは載せない(PM通知の一覧は全員に見え得るため、PM通知にはユーザー名も載せない)
- SMTPは20秒、PM通知の有効期間は30日。自動の再送はしない。通知の失敗で、保存・承認・却下を取り消さない(状態の確定後に、別スレッドで送る)
- 記録には、宛先のメールアドレス・本文・エラー文を保存しない(固定の理由コードだけ)
"""
import logging
import threading
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import close_old_connections, transaction

from accounts.models import UserSmtpConfig
from ai.models import AIAnalysisTemplate, AIAnalysisTemplateNotification as Record
from ai.services.analysis_plan_store import AnalysisError
from ai.services.chat_service import _has_resource_permission
from notifications.models import Notification
from shipping.services.email_service import EmailService

logger = logging.getLogger('production')

SMTP_TIMEOUT_SECONDS = 20  # BOSS承認(2026-10-05)。AI通知だけに適用する
PM_NOTICE_DAYS = 30        # BOSS承認(2026-10-05)
LINK_PATH = '/ai/chat'
DELETED_USER_LABEL = '削除済みユーザー'

RESULT_PHRASE = {'approved': '承認されました', 'rejected': '却下されました', 'superseded': '訂正版に置き換えられました'}
REASON_LABELS = {
    'sender_not_configured': '送信者のSMTP設定がありません',
    'base_url_not_configured': 'リンクの基準URLが未設定です',
    'recipient_unavailable': '宛先のユーザーがいません',
    'no_email': 'メールアドレスが未登録です',
    'no_recipient': '宛先(システム管理者)がいません',
    'smtp_error': '送信に失敗、または結果が不明です',
    'pm_error': 'PM通知を作成できませんでした',
    'unexpected_error': '通知の処理で想定外のエラーが起きました',
}


def _dispatch(kind, function, *args):
    """状態の確定(DBのコミット)の後に、別スレッドで通知する。失敗しても、保存・承認・却下には影響させない。

    スレッド内で例外が起きた場合は、ログに残し、通知の記録にも「想定外のエラー」を残す(静かに失わない。例外文は記録しない)。
    プロセスの終了・再起動で、送信中の通知が失われた場合は、記録が残らない(自動の再送もしない)。
    """
    def guarded():
        try:
            function(*args)
        except Exception:
            logger.exception('AI分析テンプレートの通知に失敗しました')  # 例外文はログだけ。DB・画面には出さない
            try:
                Record.objects.create(template_id=args[0], kind=kind, channel='mail', recipient=None, status='failed', reason='unexpected_error')
            except Exception:
                logger.exception('AI分析テンプレートの通知の失敗を記録できませんでした')
        finally:
            close_old_connections()

    def start():
        threading.Thread(target=guarded, daemon=True).start()

    try:
        transaction.on_commit(start)
    except Exception:
        logger.exception('AI分析テンプレートの通知を開始できませんでした')


def schedule_submitted(template_id):
    _dispatch('submitted', notify_submitted, template_id)


def schedule_result(template_id, kind, reviewer_id=None, replacement_id=None):
    _dispatch(kind, notify_result, template_id, kind, reviewer_id, replacement_id)


def _link():
    base = settings.PM_PUBLIC_BASE_URL
    return f'{base}{LINK_PATH}' if base else ''


def _record(template, kind, channel, recipient, status, reason='', pm_notification=None):
    return Record.objects.create(template=template, kind=kind, channel=channel, recipient=recipient, status=status, reason=reason,
                                 pm_notification=pm_notification)


def _is_admin(user):
    try:
        return bool(_has_resource_permission(user, 'settings.ai', 'edit'))
    except Exception:
        return False  # 判定できない人には送らない


def _sender():
    """送信者のユーザー。.envで指定した既存ユーザーで、有効なSMTP設定を持つこと。見つからなければNone(管理者の既定設定へは切り替えない)。"""
    name = settings.AI_TEMPLATE_NOTIFY_SENDER_USER
    if not name:
        return None
    sender = get_user_model().objects.filter(username=name, is_active=True).first()
    if sender is None:
        return None
    config = UserSmtpConfig.objects.filter(user=sender, is_active=True).first()
    return sender if config and config.smtp_host else None


def _deliver(recipient, subject, body):
    """1人へ1通を送り、(状態, 固定の理由コード)を返す。"""
    if recipient is None or not recipient.is_active:
        return 'skipped', 'recipient_unavailable'
    if not recipient.email:
        return 'skipped', 'no_email'
    sender = _sender()
    if sender is None:
        return 'skipped', 'sender_not_configured'
    try:
        result = EmailService().send_plain_email(
            to_emails=[recipient.email], subject=subject, body=body, user_id=sender.pk, timeout=SMTP_TIMEOUT_SECONDS,
        )
        ok = result.get('success') is True  # 戻りのメッセージ(宛先・例外文を含み得る)は使わない
    except Exception:
        ok = False
    return ('sent', '') if ok else ('failed', 'smtp_error')


def _send_mail(template, kind, recipient, subject, body):
    """1人へ1通。状態と固定の理由コードだけを記録する。"""
    status, reason = _deliver(recipient, subject, body)
    return _record(template, kind, 'mail', recipient, status, reason)


def _template_label(template):
    return f'ID {template.pk}・版{template.version}'


def _username(user):
    return user.get_username() if user else DELETED_USER_LABEL


def _submitted_mail(template, link):
    subject = f'[PM] AI分析テンプレートの確認依頼({_template_label(template)})'
    body = '\n'.join([
        'AI分析のテンプレートが、管理者の確認待ちで保存されました。',
        f'テンプレートID: {template.pk} / 版: {template.version}',
        f'作成者: {_username(template.approved_by)}',
        'PMの「AI」→「分析」の「テンプレート」で、内容を確認して承認または却下してください。',
        link,
        '※目的・SQL・Pythonなどの内容は、メールに載せていません。',
        '※このメールは自動送信です。',
    ])
    return subject, body


def _result_mail(template, kind, reviewer, replacement, link):
    phrase = RESULT_PHRASE[kind]
    lines = [f'あなたが保存したAI分析テンプレート({_template_label(template)})が、{phrase}。']
    if kind == 'approved':
        lines.append('状態: 正式')
    elif kind == 'rejected':
        lines.append('理由は、PMのテンプレートの詳細で確認してください。')
    elif replacement is not None:
        lines.append(f'訂正版: {_template_label(replacement)}')
    lines += [f'確認者: {_username(reviewer)}', '内容はPMの「AI」→「分析」の「テンプレート」で確認できます。', link, '※このメールは自動送信です。']
    return f'[PM] AI分析テンプレートが{phrase}({_template_label(template)})', '\n'.join(lines)


def notify_submitted(template_id):
    """保存されたテンプレートの確認依頼を、システム管理者へメールで送る(PM通知・タスクはなし)。"""
    template = AIAnalysisTemplate.objects.select_related('approved_by').get(pk=template_id)
    link = _link()
    admins = [user for user in get_user_model().objects.filter(is_active=True).order_by('id') if _is_admin(user)]
    if not admins:
        _record(template, 'submitted', 'mail', None, 'skipped', 'no_recipient')
        return
    if not link:
        for admin in admins:
            _record(template, 'submitted', 'mail', admin, 'skipped', 'base_url_not_configured')
        return
    subject, body = _submitted_mail(template, link)
    for admin in admins:
        _send_mail(template, 'submitted', admin, subject, body)


def notify_result(template_id, kind, reviewer_id=None, replacement_id=None):
    """承認・却下・置換の結果を、作成者へメールとPM通知で送る。"""
    if kind not in RESULT_PHRASE:
        raise ValueError('kindは approved / rejected / superseded です。')
    template = AIAnalysisTemplate.objects.select_related('approved_by').get(pk=template_id)
    creator = template.approved_by
    reviewer = get_user_model().objects.filter(pk=reviewer_id).first() if reviewer_id else None
    replacement = AIAnalysisTemplate.objects.filter(pk=replacement_id).first() if replacement_id else None
    phrase = RESULT_PHRASE[kind]
    link = _link()
    # メール
    if not link:
        _record(template, kind, 'mail', creator, 'skipped', 'base_url_not_configured')
    else:
        subject, body = _result_mail(template, kind, reviewer, replacement, link)
        _send_mail(template, kind, creator, subject, body)
    # PM通知(一覧は全員に見え得るため、ユーザー名・名称・理由は載せない)
    if creator is None or not creator.is_active:
        _record(template, kind, 'pm', creator, 'skipped', 'recipient_unavailable')
        return
    try:
        today = datetime.now().date()
        # 宛先の設定前の通知は「対象指定なし=全員向け」になるため、作成と宛先の設定を一体で確定する(失敗したら通知を残さない)
        with transaction.atomic():
            notification = Notification.objects.create(
                title=f'AI分析テンプレート: {phrase}'[:200], category='AI分析', domain='AI_ANALYSIS',
                valid_from=today, valid_to=today + timedelta(days=PM_NOTICE_DAYS), display_order=0,
                description=f'テンプレート{_template_label(template)}が{phrase}。AI分析のテンプレートで確認してください。',
            )
            notification.target_users.set([creator.pk])
        _record(template, kind, 'pm', creator, 'sent', pm_notification=notification)
    except Exception:
        logger.exception('AI分析テンプレートのPM通知を作成できませんでした')
        _record(template, kind, 'pm', creator, 'failed', 'pm_error')


def serialize_records(template):
    """詳細に出す通知の記録(作成者と管理者だけに返す)。宛先のメールアドレス・本文・エラー文は持たない。"""
    rows = []
    records = list(template.notifications.select_related('recipient').order_by('id'))
    counts = {}
    for record in records:
        counts[_group_key(record)] = counts.get(_group_key(record), 0) + 1
    for record in records:
        rows.append({
            'can_resend': _resendable(template, record, counts[_group_key(record)]),
            'id': record.pk, 'kind': record.kind, 'kind_label': record.get_kind_display(),
            'channel': record.channel, 'channel_label': record.get_channel_display(),
            'status': record.status, 'status_label': record.get_status_display(),
            'reason_label': REASON_LABELS.get(record.reason, '') if record.reason else '',
            'recipient': record.recipient.get_username() if record.recipient_id else None,
            'created_at': record.created_at.isoformat(),
        })
    return rows


# --- 手動の再送(BOSS承認 2026-10-05): 失敗・送れないメールを、同じ宛先へ1回だけ、作成者または管理者が明示的に再送する ---
RESEND_TEMPLATE_STATUS = {'submitted': 'pending_admin', 'approved': 'approved', 'rejected': 'rejected', 'superseded': 'superseded'}


def _group_key(record):
    return (record.kind, record.channel, record.recipient_id)


def _resendable(template, record, group_count):
    """再送できるのは、宛先のいるメールの失敗・送れないで、同じ(種別・宛先)の行がこの1行だけ(再送は1回まで)のとき。
    テンプレートの状態が、その通知の種別と合っていること(古い通知を今さら送らない)。"""
    return (record.channel == 'mail' and record.status in ('failed', 'skipped') and record.recipient_id is not None
            and group_count == 1 and template.status == RESEND_TEMPLATE_STATUS.get(record.kind))


def resend(user, record_id, admin):
    """再送する。元の行は変えず、新しい行を足す。同じ宛先へ、1回だけ。テンプレートの状態は変えない。

    先に新しい行を「失敗(送信に失敗、または結果が不明)」で確定してから送り、送れたら「送信済み」へ更新する
    (二重の再送を防ぐ。途中で止まっても、結果不明として残る)。元の行を行ロックして、同時の再送を直列にする。
    """
    original = Record.objects.select_related('template__approved_by', 'recipient').filter(pk=record_id).first()
    if original is None or not (admin or (original.template.approved_by_id is not None and original.template.approved_by_id == user.pk)):
        raise AnalysisError('通知の記録が見つかりません。', 404)
    with transaction.atomic():
        locked = Record.objects.select_for_update().select_related('recipient').filter(pk=record_id).first()
        if locked is None:
            raise AnalysisError('通知の記録が見つかりません。', 404)
        template = AIAnalysisTemplate.objects.select_related('approved_by', 'reviewed_by').get(pk=original.template_id)
        count = Record.objects.filter(template_id=template.pk, kind=locked.kind, channel='mail', recipient_id=locked.recipient_id).count()
        replacement = template.corrections.filter(status='approved').order_by('id').first() if locked.kind == 'superseded' else None
        if not _resendable(template, locked, count) or (locked.kind == 'superseded' and replacement is None):
            raise AnalysisError('この通知は再送できません(送信済み・再送済み・宛先なし、またはテンプレートの状態が変わりました)。', 409)
        row = _record(template, locked.kind, 'mail', locked.recipient, 'failed', 'smtp_error')
    kind, recipient, link = locked.kind, locked.recipient, _link()
    try:
        if not link:
            status, reason = 'skipped', 'base_url_not_configured'
        elif kind == 'submitted':
            if not _is_admin(recipient):
                status, reason = 'skipped', 'recipient_unavailable'
            else:
                status, reason = _deliver(recipient, *_submitted_mail(template, link))
        else:
            reviewer = replacement.reviewed_by if replacement is not None else template.reviewed_by
            status, reason = _deliver(recipient, *_result_mail(template, kind, reviewer, replacement, link))
        Record.objects.filter(pk=row.pk).update(status=status, reason=reason)
    except Exception:
        logger.exception('AI分析テンプレートの通知の再送に失敗しました')
        Record.objects.filter(pk=row.pk).update(status='failed', reason='unexpected_error')
    return template
