"""利用者からシステム管理者へのリクエスト（メール送信のみ・DB保存なし）"""

import os
from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.permissions import BasePermission
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from shipping.services.email_service import EmailService

from .models import UserRequestTask

REQUEST_TYPES = {
    'request': '要望',
    'bug': '不具合',
    'question': '問い合わせ',
    'other': 'その他',
}
MAX_FILES = 5
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 20 * 1024 * 1024

# 画像: 拡張子 -> MIMEサブタイプ（スクリーンショット貼り付けを含む）
IMAGE_SUBTYPES = {'.png': 'png', '.jpg': 'jpeg', '.jpeg': 'jpeg', '.gif': 'gif', '.webp': 'webp'}
# 書類: 拡張子 -> (MIMEメインタイプ, サブタイプ)。ここにない拡張子（実行ファイル・スクリプト・ZIP等）は受け付けない。
DOCUMENT_TYPES = {
    '.xlsx': ('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    '.xlsm': ('application', 'vnd.ms-excel.sheet.macroEnabled.12'),
    '.xls': ('application', 'vnd.ms-excel'),
    '.docx': ('application', 'vnd.openxmlformats-officedocument.wordprocessingml.document'),
    '.doc': ('application', 'msword'),
    '.pdf': ('application', 'pdf'),
    '.csv': ('text', 'csv'),
    '.txt': ('text', 'plain'),
}


def _safe_filename(name, index):
    """ヘッダ注入を防ぐため、制御文字とパス区切りを除いたファイル名にする"""
    base = os.path.basename((name or '').replace('\\', '/'))
    base = ''.join(ch for ch in base if ch >= ' ' and ch != '\x7f').strip()
    return base or f'file{index}'


class _MailFailed(Exception):
    """メール送信失敗（タスク作成・状況変更をロールバックするために使う）"""


class IsSystemAdmin(BasePermission):
    """システム管理者フラグ（UserProfile.is_system_admin）が付いたユーザーのみ許可する"""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        profile = getattr(user, 'profile', None)
        return bool(profile and profile.is_system_admin)


def _display_name(user):
    if not user:
        return ''
    return f'{user.last_name} {user.first_name}'.strip() or user.username


def _serialize_task(task):
    return {
        'id': task.id,
        'request_type': task.request_type,
        'request_type_label': task.get_request_type_display(),
        'subject': task.subject,
        'body': task.body,
        'requester_id': task.requester_id,
        'requester_name': _display_name(task.requester),
        'requester_email': task.requester.email if task.requester else '',
        'status': task.status,
        'status_label': task.get_status_display(),
        'reject_reason': task.reject_reason,
        'handled_by_name': _display_name(task.handled_by),
        'handled_at': task.handled_at.isoformat() if task.handled_at else None,
        'created_at': task.created_at.isoformat() if task.created_at else None,
    }


class UserRequestView(APIView):
    """POST /api/user-requests/ : システム管理者へリクエストをメール送信する"""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        type_key = (request.data.get('request_type') or '').strip()
        subject = ' '.join((request.data.get('subject') or '').split())
        body = (request.data.get('body') or '').strip()
        page_url = (request.data.get('page_url') or '').strip()

        if type_key not in REQUEST_TYPES:
            return Response({'detail': '種別を選択してください。'}, status=400)
        if not subject:
            return Response({'detail': '件名を入力してください。'}, status=400)
        if not body:
            return Response({'detail': '内容を入力してください。'}, status=400)

        attachments = []
        files = request.FILES.getlist('files')
        if len(files) > MAX_FILES:
            return Response({'detail': f'添付ファイルは最大{MAX_FILES}個までです。'}, status=400)
        total_bytes = 0
        for index, f in enumerate(files, start=1):
            filename = _safe_filename(f.name, index)
            ext = os.path.splitext(filename)[1].lower()
            if f.size > MAX_FILE_BYTES:
                return Response({'detail': f'{filename}: 1ファイル{MAX_FILE_BYTES // 1024 // 1024}MBまでです。'}, status=400)
            total_bytes += f.size
            if total_bytes > MAX_TOTAL_BYTES:
                return Response({'detail': f'添付ファイルの合計は{MAX_TOTAL_BYTES // 1024 // 1024}MBまでです。'}, status=400)
            if ext in IMAGE_SUBTYPES:
                attachments.append({'filename': filename, 'data': f.read(), 'maintype': 'image', 'subtype': IMAGE_SUBTYPES[ext]})
            elif ext in DOCUMENT_TYPES:
                maintype, subtype = DOCUMENT_TYPES[ext]
                attachments.append({'filename': filename, 'data': f.read(), 'maintype': maintype, 'subtype': subtype})
            else:
                return Response({'detail': f'{filename}: 対応していない形式です（画像・Excel・Word・PDF・CSV・テキストのみ）。'}, status=400)

        # 送信先: システム管理者フラグが付いた有効ユーザー全員（メールアドレス登録済みのみ）
        admin_emails = list(
            get_user_model().objects.filter(profile__is_system_admin=True, is_active=True)
            .exclude(email='')
            .values_list('email', flat=True)
            .distinct()
        )
        if not admin_emails:
            return Response({'detail': 'システム管理者（メールアドレス登録済み）が設定されていません。'}, status=400)

        user = request.user
        full_name = f'{user.last_name} {user.first_name}'.strip()
        profile = getattr(user, 'profile', None)
        employee_code = getattr(profile, 'employee_code', '') or ''
        file_names = '、'.join(a['filename'] for a in attachments) or 'なし'
        mail_body = (
            f'種別: {REQUEST_TYPES[type_key]}\n'
            f'依頼者: {full_name or user.username}（ユーザー名: {user.username} / 社員コード: {employee_code or "-"}）\n'
            f'依頼者メール: {user.email or "-"}\n'
            f'画面: {page_url or "-"}\n'
            f'添付ファイル: {len(attachments)}個（{file_names}）\n'
            '----------------------------------------\n'
            f'{body}\n'
        )

        # タスク作成とメール送信は1つのトランザクション。メール送信が失敗したらタスクも作らない。
        try:
            with transaction.atomic():
                UserRequestTask.objects.create(
                    request_type=type_key,
                    subject=subject[:200],
                    body=body,
                    requester=user,
                )
                result = EmailService().send_plain_email(
                    to_emails=admin_emails,
                    subject=f'[PMリクエスト] {REQUEST_TYPES[type_key]}: {subject}',
                    body=mail_body,
                    user_id=user.id,
                    reply_to=user.email or None,
                    file_attachments=attachments,
                )
                if not result.get('success'):
                    raise _MailFailed(result.get('message') or '送信に失敗しました。')
        except _MailFailed as exc:
            return Response({'detail': str(exc)}, status=502)
        return Response({'detail': 'システム管理者へ送信しました。'})


class UserRequestTaskListView(APIView):
    """GET /api/user-requests/tasks/ : システム管理者向けのリクエストタスク一覧（?status= で絞り込み）"""

    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def get(self, request):
        queryset = UserRequestTask.objects.select_related('requester', 'handled_by')
        status = (request.query_params.get('status') or '').strip()
        if status:
            queryset = queryset.filter(status=status)
        return Response([_serialize_task(task) for task in queryset])


class UserRequestHistoryView(APIView):
    """GET /api/user-requests/history/ : 全ユーザーが見られるリクエスト履歴（重複リクエストを避けるため）

    絞り込み: ?requester=<ユーザーID>&status=<状況>&q=<件名・内容のキーワード>
    見せない項目: 却下理由、対応者（最終対応者・日時）。最新200件まで。
    """

    permission_classes = [IsAuthenticated]
    LIMIT = 200

    def get(self, request):
        queryset = UserRequestTask.objects.select_related('requester')
        requester = (request.query_params.get('requester') or '').strip()
        status = (request.query_params.get('status') or '').strip()
        keyword = (request.query_params.get('q') or '').strip()
        if requester.isdigit():
            queryset = queryset.filter(requester_id=int(requester))
        if status:
            queryset = queryset.filter(status=status)
        if keyword:
            queryset = queryset.filter(Q(subject__icontains=keyword) | Q(body__icontains=keyword))

        results = [
            {
                'id': task.id,
                'request_type': task.request_type,
                'request_type_label': task.get_request_type_display(),
                'subject': task.subject,
                'body': task.body,
                'requester_id': task.requester_id,
                'requester_name': _display_name(task.requester),
                'status': task.status,
                'status_label': task.get_status_display(),
                'created_at': task.created_at.isoformat() if task.created_at else None,
            }
            for task in queryset[:self.LIMIT]
        ]
        # 依頼者の絞り込み用（依頼実績のあるユーザー）。絞り込み条件には影響されない。
        requester_ids = (
            UserRequestTask.objects.exclude(requester__isnull=True)
            .values_list('requester_id', flat=True).distinct()
        )
        requesters = [
            {'id': user.id, 'name': _display_name(user)}
            for user in get_user_model().objects.filter(id__in=list(requester_ids)).order_by('last_name', 'first_name', 'username')
        ]
        return Response({'results': results, 'requesters': requesters})


class UserRequestTaskDetailView(APIView):
    """PATCH: 状況の変更（却下は理由が必須で、依頼者へ返信メールを送る） / DELETE: 削除"""

    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def patch(self, request, pk):
        task = get_object_or_404(UserRequestTask.objects.select_related('requester', 'handled_by'), pk=pk)
        status = (request.data.get('status') or '').strip()
        reject_reason = (request.data.get('reject_reason') or '').strip()
        if status not in dict(UserRequestTask.STATUS_CHOICES):
            return Response({'detail': '状況が正しくありません。'}, status=400)
        if status == UserRequestTask.STATUS_REJECTED and not reject_reason:
            return Response({'detail': '却下する場合は却下理由を入力してください。'}, status=400)

        newly_rejected = status == UserRequestTask.STATUS_REJECTED and task.status != UserRequestTask.STATUS_REJECTED
        warning = ''
        try:
            with transaction.atomic():
                task.status = status
                task.reject_reason = reject_reason if status == UserRequestTask.STATUS_REJECTED else ''
                task.handled_by = request.user
                task.handled_at = datetime.now()
                task.save()
                if newly_rejected:
                    requester_email = task.requester.email if task.requester else ''
                    if requester_email:
                        result = EmailService().send_plain_email(
                            to_emails=[requester_email],
                            subject=f'[PMリクエスト] 却下: {task.subject}',
                            body=(
                                f'{_display_name(task.requester)} 様\n\n'
                                '送信いただいたリクエストは、次の理由により却下となりました。\n\n'
                                f'種別: {task.get_request_type_display()}\n'
                                f'件名: {task.subject}\n'
                                f'却下理由: {task.reject_reason}\n\n'
                                f'対応者: {_display_name(request.user)}\n'
                            ),
                            user_id=request.user.id,
                            reply_to=request.user.email or None,
                        )
                        if not result.get('success'):
                            raise _MailFailed(result.get('message') or '返信メールの送信に失敗しました。')
                    else:
                        warning = '依頼者のメールアドレスが未登録のため、返信メールは送信していません。'
        except _MailFailed as exc:
            return Response({'detail': f'却下を保存できませんでした（返信メール送信失敗）: {exc}'}, status=502)
        data = _serialize_task(task)
        if warning:
            data['warning'] = warning
        return Response(data)

    def delete(self, request, pk):
        task = get_object_or_404(UserRequestTask, pk=pk)
        task.delete()
        return Response(status=204)
